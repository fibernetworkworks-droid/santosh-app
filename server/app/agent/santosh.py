"""Santosh's agent loop: Claude decides, tools act, every step is streamed to the UI."""
from __future__ import annotations

import asyncio
import json
import logging
from collections import defaultdict

from sqlalchemy import select

from ..config import get_settings
from ..db import Message, session
from ..events import bus
from ..life import context_block
from .prompts import system_prompt
from .tools import TOOL_LABELS, TOOLS, Ctx, ToolError, dispatch

log = logging.getLogger("santosh.agent")

_client = None
_locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)
HISTORY_LIMIT = 60


def get_client():
    global _client
    if _client is None:
        from anthropic import AsyncAnthropic
        key = get_settings().anthropic_api_key
        if not key:
            raise RuntimeError("ANTHROPIC_API_KEY is not set, so Santosh cannot think yet.")
        _client = AsyncAnthropic(api_key=key)
    return _client


def set_client(client) -> None:
    global _client
    _client = client


def _block_to_dict(b) -> dict:
    if isinstance(b, dict):
        return b
    t = getattr(b, "type", None)
    if t == "text":
        return {"type": "text", "text": b.text}
    if t == "tool_use":
        return {"type": "tool_use", "id": b.id, "name": b.name, "input": b.input}
    if hasattr(b, "model_dump"):
        return b.model_dump(exclude_none=True)
    return dict(b)


def _load_history(conversation_id: str) -> list[dict]:
    with session() as s:
        rows = s.scalars(select(Message).where(Message.conversation_id == conversation_id, Message.in_history.is_(True))
                         .order_by(Message.id)).all()
        msgs = [{"role": r.role, "content": r.content} for r in rows]
    if len(msgs) > HISTORY_LIMIT:
        msgs = msgs[-HISTORY_LIMIT:]
        # never start on a tool_result or an assistant turn
        while msgs and not (msgs[0]["role"] == "user" and isinstance(msgs[0]["content"], str)):
            msgs.pop(0)
    return _sanitize(msgs)


def _as_blocks(c) -> list[dict]:
    return c if isinstance(c, list) else [{"type": "text", "text": c}]


def _sanitize(msgs: list[dict]) -> list[dict]:
    """Repair history after a crash: drop tool calls that never got results and merge
    back-to-back turns from the same role, so the API always accepts the history."""
    out: list[dict] = []
    for i, m in enumerate(msgs):
        c = m["content"]
        if m["role"] == "assistant" and isinstance(c, list) and any(b.get("type") == "tool_use" for b in c):
            nxt = msgs[i + 1] if i + 1 < len(msgs) else None
            answered = (nxt is not None and nxt["role"] == "user" and isinstance(nxt["content"], list)
                        and any(b.get("type") == "tool_result" for b in nxt["content"]))
            if not answered:
                texts = [b for b in c if b.get("type") == "text"]
                if not texts:
                    continue
                m = {"role": "assistant", "content": texts}
        if m["role"] == "user" and isinstance(m["content"], list) and m["content"] and m["content"][0].get("type") == "tool_result":
            prev = out[-1] if out else None
            if not (prev and prev["role"] == "assistant" and any(b.get("type") == "tool_use" for b in _as_blocks(prev["content"]))):
                continue   # orphan results
        if out and out[-1]["role"] == m["role"]:
            out[-1] = {"role": m["role"], "content": _as_blocks(out[-1]["content"]) + _as_blocks(m["content"])}
        else:
            out.append(m)
    return out


def _save(conversation_id: str, role: str, content, display: str | None = None) -> None:
    with session() as s:
        s.add(Message(conversation_id=conversation_id, role=role, content=content, display=display, in_history=True))


def _pending_worker_notes(conversation_id: str) -> list[str]:
    with session() as s:
        rows = s.scalars(select(Message).where(Message.conversation_id == conversation_id,
                                               Message.in_history.is_(False),
                                               Message.delivered_to_agent.is_(False)).order_by(Message.id)).all()
        notes = [r.display or "" for r in rows]
        for r in rows:
            r.delivered_to_agent = True
        return notes


def _short(obj, limit: int = 6000) -> str:
    s = json.dumps(obj, ensure_ascii=False, default=str)
    return s if len(s) <= limit else s[:limit] + "…(truncated)"


VOICE_NOTE = ("[Voice mode: the user is speaking to you and your reply will be read aloud by the phone. Reply in 1-3 short, "
              "natural spoken sentences with no lists, markdown, emoji or URLs. If the user speaks Hindi or Hinglish, write your "
              "reply in Devanagari script so the voice pronounces it correctly; for other Indian languages use their own script.]")


async def run_turn(conversation_id: str, user_text: str, tenant_id: str | None = None, voice: bool = False) -> str:
    """Handle one user message end to end. Returns Santosh's final reply text."""
    settings = get_settings()
    tenant_id = tenant_id or settings.tenant_id
    ctx = Ctx(tenant_id=tenant_id, conversation_id=conversation_id)
    async with _locks[conversation_id]:
        notes = _pending_worker_notes(conversation_id)
        agent_text = f"{VOICE_NOTE}\n{user_text}" if voice else user_text
        if notes:
            agent_text = "\n".join(f"[Santosh worker update] {n}" for n in notes) + "\n\n" + agent_text
        _save(conversation_id, "user", agent_text, display=user_text)
        bus.publish(conversation_id, "typing", {"on": True})

        history = _load_history(conversation_id)
        final_text = ""
        try:
            client = get_client()
            for _ in range(settings.agent_max_steps):
                resp = await client.messages.create(
                    model=settings.anthropic_model, max_tokens=settings.agent_max_tokens,
                    system=system_prompt(settings.wa_dry_run, context_block(tenant_id)), tools=TOOLS, messages=history)
                blocks = [_block_to_dict(b) for b in resp.content]
                history.append({"role": "assistant", "content": blocks})
                texts = [b["text"] for b in blocks if b.get("type") == "text" and b.get("text", "").strip()]
                _save(conversation_id, "assistant", blocks, display="\n\n".join(texts) or None)
                if texts:
                    final_text = "\n\n".join(texts)
                    bus.publish(conversation_id, "message", {"role": "assistant", "text": final_text, "source": "agent"})
                if resp.stop_reason != "tool_use":
                    break
                results = []
                for b in blocks:
                    if b.get("type") != "tool_use":
                        continue
                    label = TOOL_LABELS.get(b["name"], b["name"])
                    bus.publish(conversation_id, "step", {"tool": b["name"], "label": label, "state": "running", "id": b["id"]})
                    try:
                        out = await dispatch(b["name"], b.get("input") or {}, ctx)
                        results.append({"type": "tool_result", "tool_use_id": b["id"], "content": _short(out)})
                        bus.publish(conversation_id, "step", {"tool": b["name"], "label": label, "state": "done", "id": b["id"]})
                    except ToolError as e:
                        results.append({"type": "tool_result", "tool_use_id": b["id"], "content": str(e), "is_error": True})
                        bus.publish(conversation_id, "step", {"tool": b["name"], "label": label, "state": "error",
                                                              "id": b["id"], "detail": str(e)[:300]})
                    except Exception as e:  # unexpected bug: tell Claude, keep the turn alive
                        log.exception("tool %s crashed", b["name"])
                        results.append({"type": "tool_result", "tool_use_id": b["id"],
                                        "content": f"Internal error in {b['name']}: {e}", "is_error": True})
                        bus.publish(conversation_id, "step", {"tool": b["name"], "label": label, "state": "error", "id": b["id"]})
                history.append({"role": "user", "content": results})
                _save(conversation_id, "user", results)
            else:
                final_text = final_text or "Yeh kaam lamba ho gaya, main yahin ruk raha hoon. Aage kya karoon?"
                bus.publish(conversation_id, "message", {"role": "assistant", "text": final_text, "source": "agent"})
        except Exception as e:
            log.exception("agent turn failed")
            final_text = f"Maaf kijiye, abhi kuch gadbad ho gayi: {e}"
            bus.publish(conversation_id, "message", {"role": "assistant", "text": final_text, "source": "error"})
            _save(conversation_id, "assistant", [{"type": "text", "text": final_text}], display=final_text)
        finally:
            bus.publish(conversation_id, "typing", {"on": False})
        return final_text
