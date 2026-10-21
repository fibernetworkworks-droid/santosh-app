"""Santosh's agent loop: the brain (OmniRoute, GLM or Claude; see llm.py) decides, tools act, every step is streamed to the UI."""
from __future__ import annotations

import asyncio
import json
import logging
from collections import defaultdict

from sqlalchemy import select

from ..config import get_settings
from ..db import Message, session
from ..events import bus
from .. import theatre
from ..avatar.service import gendered, persona
from ..life import context_block
from . import llm
from .prompts import system_prompt
from . import mcp_live
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


def _claude_ready() -> bool:
    return bool(get_settings().anthropic_api_key or _client is not None)


async def _call_brain(brain: str, system: str, history: list[dict], settings, tools: list[dict] | None = None) -> tuple[list[dict], str]:
    """One model call on one brain. Raises when that brain fails."""
    tools = tools if tools is not None else TOOLS
    if brain in ("glm", "omniroute"):
        blocks, stop, usage = await llm.openai_create(brain, system, tools, history, settings.agent_max_tokens)
        log.info("%s in=%s out=%s %s", llm.describe(), usage.get("prompt_tokens"), usage.get("completion_tokens"),
                 usage.get("route", ""))
        return blocks, stop
    resp = await get_client().messages.create(
        model=settings.anthropic_model, max_tokens=settings.agent_max_tokens,
        system=system, tools=tools, messages=history)
    return [_block_to_dict(b) for b in resp.content], resp.stop_reason


async def _think(brain: str, system: str, history: list[dict], settings, tools: list[dict] | None = None) -> tuple[list[dict], str, str]:
    """One model call that survives a failing brain: the chosen brain first, then the other one, so an outage of
    either never leaves the user without an answer. Returns (blocks, stop_reason, the brain that answered)."""
    order = [brain]
    if brain == "claude":
        cheap = llm.cheap_brain()
        if cheap and not llm._has_media(history[-1:]):   # pictures and PDFs need Claude; plain text can go to the cheap brain
            order.append(cheap)
    elif _claude_ready():
        order.append("claude")
    last: Exception | None = None
    for b in order:
        try:
            blocks, stop = await _call_brain(b, system, history, settings, tools)
            return blocks, stop, b
        except asyncio.CancelledError:
            raise
        except Exception as e:
            last = e
            log.warning("%s failed%s: %s", b, "; trying the other brain" if b != order[-1] else "", e)
    assert last is not None
    raise last


def _friendly_error(e: BaseException) -> str:
    s = str(e)
    busy = any(x in s.lower() for x in ("not reachable", "error 429", "error 5", "overloaded", "rate limit", "timed out", "broken answer"))
    head = ("Abhi AI service busy ya unreachable hai, thodi der baad phir bolna." if busy
            else "Maaf kijiye, abhi kuch gadbad ho gayi.")
    return f"{head} ({s[:200]})" if s else head


async def _run_tool(name: str, args: dict, ctx: Ctx, settings, mcp_route: dict | None = None):
    """A tool call that can never hang the whole turn."""
    if mcp_route and name in mcp_route:   # a tool of one of the owner's MCP servers
        work = mcp_live.run(ctx, mcp_route, name, args or {})
    else:
        work = dispatch(name, args or {}, ctx)
    return await asyncio.wait_for(work, timeout=max(5, settings.agent_tool_timeout_s))


async def _steps(conversation_id: str, ctx: Ctx, gender: str, history: list[dict], settings, tenant_id: str,
                 user_text: str = "") -> str:
    """One turn with the v0.63 extras around it: seekhe hue kaam as hints, a circuit breaker, learning afterwards."""
    from .. import procedures
    from .breaker import Breaker
    state: dict = {"calls": [], "breaker": Breaker(), "used": [], "hint": ""}
    actor = getattr(ctx, "actor", "owner") or "owner"
    if user_text and actor in ("owner", "routine"):
        try:
            state["hint"], state["used"] = await asyncio.to_thread(procedures.hint, tenant_id, user_text)
        except Exception:
            log.exception("procedure hint failed")
    text = await _steps_inner(conversation_id, ctx, gender, history, settings, tenant_id, state)
    ok = (bool(text.strip()) and not state["breaker"].stopped and conversation_id not in _stopped
          and not text.startswith(("Yeh kaam lamba", "Maaf kijiye")))
    if user_text:
        learned = await asyncio.to_thread(procedures.after_turn, tenant_id, user_text, state["calls"], state["used"], ok, actor)
        if learned and learned.get("learned"):
            bus.publish(conversation_id, "procedure", {"event": "learned", "id": learned["learned"], "title": learned["title"]})
    return text


async def _steps_inner(conversation_id: str, ctx: Ctx, gender: str, history: list[dict], settings, tenant_id: str,
                       state: dict) -> str:
    """The think -> tools -> think loop of one turn. Returns the final text shown to the user."""
    breaker = state["breaker"]
    final_text = ""
    ran_tools = False
    brain = llm.choose(history)
    system = system_prompt(settings.wa_dry_run, context_block(tenant_id), tenant_id)
    # the owner's MCP connections: known to the avatar, and their tools callable directly
    mcp_snap = await asyncio.to_thread(mcp_live.snapshot, tenant_id)
    mcp_defs, mcp_route = mcp_live.tool_defs(mcp_snap, settings.mcp_native_tools)
    system += "\n\n" + mcp_live.prompt_block(mcp_snap, mcp_route)
    system += state.get("hint") or ""
    tools = TOOLS + mcp_defs
    for _ in range(settings.agent_max_steps):
        try:
            blocks, stop, brain = await _think(brain, system, history, settings, tools)   # stays on the brain that worked
        except Exception as e:
            if not mcp_defs or not mcp_live.schema_trouble(e):
                raise
            # a server's tool description the model refuses: go on without the direct MCP tools (bazar_run still works)
            log.warning("MCP tool schemas refused (%s); continuing without them", str(e)[:200])
            mcp_defs, mcp_route, tools = [], {}, TOOLS
            blocks, stop, brain = await _think(brain, system, history, settings, tools)
        history.append({"role": "assistant", "content": blocks})
        texts = [b["text"] for b in blocks if b.get("type") == "text" and b.get("text", "").strip()]
        _save(conversation_id, "assistant", blocks, display="\n\n".join(texts) or None)
        if texts:
            final_text = "\n\n".join(texts)
            bus.publish(conversation_id, "message", {"role": "assistant", "text": final_text, "source": "agent"})
        if stop != "tool_use":
            break
        results = []
        for b in blocks:
            if b.get("type") != "tool_use":
                continue
            if conversation_id in _stopped:
                results.append({"type": "tool_result", "tool_use_id": b["id"], "is_error": True,
                                "content": "The user tapped Stop. Do not continue this task; say in one line what was done."})
                continue
            held = breaker.before(b["name"], b.get("input") or {})
            if held:                       # circuit breaker: steered / constrained / stopped, the call does not run
                results.append({"type": "tool_result", "tool_use_id": b["id"], "is_error": True, "content": held})
                continue
            ran_tools = True
            label = gendered(mcp_live.label(b["name"], mcp_route, mcp_snap) if b["name"] in mcp_route
                             else TOOL_LABELS.get(b["name"], b["name"]), gender)
            args_in = b.get("input") or {}
            bus.publish(conversation_id, "step", {"tool": b["name"], "label": label, "state": "running", "id": b["id"]})
            _work(conversation_id, b["id"], b["name"], label, "start", args_in)
            try:
                out = await _run_tool(b["name"], args_in, ctx, settings, mcp_route)
                fine = not (isinstance(out, dict) and out.get("error"))
                breaker.after(b["name"], fine)
                state["calls"].append({"tool": b["name"], "ok": fine, "error": "" if fine else str(out.get("error"))[:200]})
                results.append({"type": "tool_result", "tool_use_id": b["id"], "content": _short(out)})
                bus.publish(conversation_id, "step", {"tool": b["name"], "label": label, "state": "done", "id": b["id"]})
                _work(conversation_id, b["id"], b["name"], label, theatre.phase_of(out), args_in, out)
            except ToolError as e:
                breaker.after(b["name"], False)
                state["calls"].append({"tool": b["name"], "ok": False, "error": str(e)[:200]})
                results.append({"type": "tool_result", "tool_use_id": b["id"], "content": str(e), "is_error": True})
                bus.publish(conversation_id, "step", {"tool": b["name"], "label": label, "state": "error",
                                                      "id": b["id"], "detail": str(e)[:300]})
                _work(conversation_id, b["id"], b["name"], label, "error", args_in, error=str(e))
            except asyncio.TimeoutError:
                breaker.after(b["name"], False)
                state["calls"].append({"tool": b["name"], "ok": False, "error": "timeout"})
                msg = f"{b['name']} did not finish in {settings.agent_tool_timeout_s} seconds and was stopped. Tell the user and offer to try again."
                log.warning("tool %s timed out", b["name"])
                results.append({"type": "tool_result", "tool_use_id": b["id"], "content": msg, "is_error": True})
                bus.publish(conversation_id, "step", {"tool": b["name"], "label": label, "state": "error",
                                                      "id": b["id"], "detail": "bahut der lag rahi thi, rok diya"})
                _work(conversation_id, b["id"], b["name"], label, "error", args_in, error="Bahut der lag rahi thi, rok diya")
            except Exception as e:  # unexpected bug: tell the model, keep the turn alive
                breaker.after(b["name"], False)
                state["calls"].append({"tool": b["name"], "ok": False, "error": "crash"})
                log.exception("tool %s crashed", b["name"])
                results.append({"type": "tool_result", "tool_use_id": b["id"],
                                "content": f"Internal error in {b['name']}: {e}", "is_error": True})
                bus.publish(conversation_id, "step", {"tool": b["name"], "label": label, "state": "error", "id": b["id"]})
                _work(conversation_id, b["id"], b["name"], label, "error", args_in, error="Kuch gadbad ho gayi")
        history.append({"role": "user", "content": results})
        _save(conversation_id, "user", results)
        if breaker.stopped:                # stuck: stop here and say so plainly
            log.warning("circuit breaker stopped a turn: %s", breaker.stopped)
            final_text = gendered(breaker.final_text(), gender)
            bus.publish(conversation_id, "message", {"role": "assistant", "text": final_text, "source": "agent"})
            bus.publish(conversation_id, "work", {"id": "breaker", "tool": "", "scene": "work", "phase": "stopped",
                                                  "label": "Atak gaya, roka gaya", "data": {}})
            _save(conversation_id, "assistant", [{"type": "text", "text": final_text}], display=final_text)
            return final_text
        if conversation_id in _stopped:
            final_text = "Theek hai, maine kaam rok diya."
            bus.publish(conversation_id, "message", {"role": "assistant", "text": final_text, "source": "agent"})
            _save(conversation_id, "assistant", [{"type": "text", "text": final_text}], display=final_text)
            return final_text
    else:
        if not final_text:
            final_text = "Yeh kaam lamba ho gaya, main yahin ruk raha hoon. Aage kya karoon?"
            bus.publish(conversation_id, "message", {"role": "assistant", "text": final_text, "source": "agent"})
        return final_text
    if not final_text.strip():
        # the model finished without a word: never leave the user staring at a silent chat
        final_text = gendered("Kaam ho gaya. Aur kuch karna hai?", gender) if ran_tools else \
            "Maaf kijiye, main samajh nahi paya. Ek baar phir bata dein?"
        bus.publish(conversation_id, "message", {"role": "assistant", "text": final_text, "source": "agent"})
        _save(conversation_id, "assistant", [{"type": "text", "text": final_text}], display=final_text)
    return final_text


_stopped: set[str] = set()


def stop(conversation_id: str) -> None:
    """The owner tapped Stop: the running turn finishes the current tool call and does nothing more."""
    _stopped.add(conversation_id)
    bus.publish(conversation_id, "work", {"id": "stop", "tool": "", "scene": "work", "phase": "stopped",
                                          "label": "Roka gaya", "data": {}})


def _work(conversation_id: str, call_id: str, tool: str, label: str, phase: str, args=None, out=None, error: str = "") -> None:
    try:
        bus.publish(conversation_id, "work", theatre.event(call_id, tool, label, phase, args, out, error))
    except Exception:
        log.exception("work event failed")


async def run_turn(conversation_id: str, user_text: str, tenant_id: str | None = None, voice: bool = False,
                   context: str = "", actor: str = "owner") -> str:
    """Handle one user message end to end. Returns Santosh's final reply text."""
    settings = get_settings()
    tenant_id = tenant_id or settings.tenant_id
    ctx = Ctx(tenant_id=tenant_id, conversation_id=conversation_id, actor=actor or "owner")
    _gender = persona(tenant_id)[1]
    # v0.75 ID numbers the OWNER writes go into her Pehchaan Locker; the model and the saved chat get references.
    # Customers' / other avatars' messages are never captured into her locker.
    if (actor or "owner") == "owner" and not user_text.lstrip().startswith("[Hoola Network]"):
        # v0.76 a website job is waiting for an OTP / CAPTCHA and she just said it: straight into the page box, never
        # into chat history, memory or the model (like telling the Setu operator the OTP)
        try:
            from ..operator import service as _ops
            got = await _ops.answer_from_chat(tenant_id, user_text)
        except Exception:
            log.exception("operator chat answer failed")
            got = None
        if got:
            shown = ("OTP " if got["kind"] == "otp" else "CAPTCHA ") + got.get("masked", "••••")
            _save(conversation_id, "user", shown, display=shown)
            _save(conversation_id, "assistant", [{"type": "text", "text": got["say"]}], display=got["say"])
            bus.publish(conversation_id, "message", {"role": "assistant", "text": got["say"], "source": "operator"})
            return got["say"]
        try:
            from ..idvault import capture
            user_text, _ids = capture(tenant_id, user_text)
        except Exception:
            log.exception("id capture failed")
    async with _locks[conversation_id]:
        notes = _pending_worker_notes(conversation_id)
        agent_text = f"{VOICE_NOTE}\n{user_text}" if voice else user_text
        if context:                         # e.g. files the owner attached (only the words show in the chat)
            agent_text += "\n\n" + context
        if notes:
            agent_text = "\n".join(f"[Santosh worker update] {n}" for n in notes) + "\n\n" + agent_text
        _save(conversation_id, "user", agent_text, display=user_text)
        bus.publish(conversation_id, "typing", {"on": True})

        history = _load_history(conversation_id)
        final_text = ""
        _stopped.discard(conversation_id)
        try:
            # one stuck call must never keep this conversation locked forever
            final_text = await asyncio.wait_for(
                _steps(conversation_id, ctx, _gender, history, settings, tenant_id, user_text),
                timeout=max(30, settings.agent_turn_timeout_s))
        except asyncio.TimeoutError:
            log.error("agent turn timed out after %ss", settings.agent_turn_timeout_s)
            final_text = "Yeh kaam bahut der se chal raha tha, isliye maine ise rok diya. Thoda chhota karke phir bolein?"
            bus.publish(conversation_id, "message", {"role": "assistant", "text": final_text, "source": "error"})
            _save(conversation_id, "assistant", [{"type": "text", "text": final_text}], display=final_text)
        except Exception as e:
            log.exception("agent turn failed")
            final_text = _friendly_error(e)
            bus.publish(conversation_id, "message", {"role": "assistant", "text": final_text, "source": "error"})
            _save(conversation_id, "assistant", [{"type": "text", "text": final_text}], display=final_text)
        finally:
            bus.publish(conversation_id, "typing", {"on": False})
        return final_text
