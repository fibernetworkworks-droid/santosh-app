"""Santosh's agent loop: the brain (OmniRoute, GLM or Claude; see llm.py) decides, tools act, every step is streamed to the UI."""
from __future__ import annotations

import asyncio
import time
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
    from . import cache
    resp = await get_client().messages.create(**cache.shape(dict(
        model=settings.anthropic_model, max_tokens=settings.agent_max_tokens,
        system=system, tools=tools, messages=history), getattr(settings, "prompt_cache", True)))
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


class _Halted(Exception):
    """v0.91 The owner stopped the turn (Rokiye), or paused the job mid-turn: the running step was cancelled."""

    def __init__(self, why: str):
        super().__init__(why)
        self.why = why


HALT_EVERY_S = 0.1           # how often a running step checks for Rokiye / Pause (OpenDots checks 10x a second too)
HALTS = {"stop": 0, "pause": 0}


def _halt_reason(conversation_id: str, ctx: Ctx, state: dict | None = None) -> str:
    if conversation_id in _stopped:
        return "stop"
    actor = getattr(ctx, "actor", "owner") or "owner"
    if actor == "owner" or actor.startswith("approved:") or state is None or state.get("paused0") is None:
        return ""                      # her own turns: Pause holds job tools at the gate, her personal work goes on
    try:
        from ..employee import service as emp
        if emp.paused_now(ctx.tenant_id) and not state["paused0"]:
            return "pause"             # turned on while this routine / staff / customer turn was running
    except Exception:
        log.exception("pause check failed")
    return ""


async def _watched(work, conversation_id: str, ctx: Ctx, state: dict | None = None):
    """Run one model call or tool call, but cancel it the moment she taps Rokiye (or pauses the job), instead of
    waiting for the step to finish by itself. Exceptions of the work itself pass through unchanged."""
    task = asyncio.ensure_future(work)
    try:
        while True:
            done, _ = await asyncio.wait({task}, timeout=HALT_EVERY_S)
            if done:
                return task.result()
            why = _halt_reason(conversation_id, ctx, state)
            if why:
                task.cancel()
                try:
                    await task
                except BaseException:
                    pass
                HALTS[why] += 1
                raise _Halted(why)
    except asyncio.CancelledError:
        task.cancel()
        raise


HALTED_TEXT = {"stop": "Theek hai, maine kaam rok diya.",
               "pause": "Owner ne kaam rok diya (Pause), isliye main yahin ruk gaya. 'Kaam shuru' hone par aage karunga."}


async def _run_tool(name: str, args: dict, ctx: Ctx, settings, mcp_route: dict | None = None):
    """A tool call that can never hang the whole turn."""
    if mcp_route and name in mcp_route:   # a tool of one of the owner's MCP servers
        work = mcp_live.run(ctx, mcp_route, name, args or {})
    else:
        work = dispatch(name, args or {}, ctx)
    out = await asyncio.wait_for(work, timeout=max(5, settings.agent_tool_timeout_s))
    from ..scrub import scrub          # v0.91 a service that echoes one of our keys back never shows it to the model
    return scrub(out)


async def _steps(conversation_id: str, ctx: Ctx, gender: str, history: list[dict], settings, tenant_id: str,
                 user_text: str = "") -> str:
    """One turn with the v0.63 extras around it: seekhe hue kaam as hints, a circuit breaker, learning afterwards."""
    from .. import procedures
    from .breaker import Breaker
    from . import pakka
    state: dict = {"calls": [], "breaker": Breaker(), "used": [], "hint": "", "request": user_text, "t0": time.time()}
    actor = getattr(ctx, "actor", "owner") or "owner"
    if actor != "owner" and not actor.startswith("approved:"):
        try:   # v0.91 remember whether the job was paused when this turn began: turning Pause on mid-turn stops it
            from ..employee import service as _emp
            state["paused0"] = _emp.paused_now(tenant_id)
        except Exception:
            state["paused0"] = None
    if user_text and actor in ("owner", "routine"):
        try:
            state["hint"], state["used"] = await asyncio.to_thread(procedures.hint, tenant_id, user_text)
        except Exception:
            log.exception("procedure hint failed")
    text = await _steps_inner(conversation_id, ctx, gender, history, settings, tenant_id, state)
    ok = (bool(text.strip()) and not state["breaker"].stopped and conversation_id not in _stopped and not state.get("halted")
          and not text.startswith(("Yeh kaam lamba", "Maaf kijiye")))
    if user_text:
        lessons = await asyncio.to_thread(pakka.learn, tenant_id, state["calls"], ok, state.get("lessons_used", []))
        if lessons:
            bus.publish(conversation_id, "procedure", {"event": "lesson", "title": lessons[0][:120], "count": len(lessons)})
        outcome = ("stopped" if conversation_id in _stopped or state.get("halted") else "stuck" if state["breaker"].stopped else
                   "talk" if not state["calls"] else "partial" if state.get("left") else "done" if ok else "partial")
        await asyncio.to_thread(pakka.record, tenant_id, user_text, outcome, state["calls"], state,
                                time.time() - state["t0"], state.get("left", ""))
        learned = await asyncio.to_thread(procedures.after_turn, tenant_id, user_text, state["calls"], state["used"], ok, actor)
        if learned and learned.get("learned"):
            bus.publish(conversation_id, "procedure", {"event": "learned", "id": learned["learned"], "title": learned["title"]})
    return text


async def _steps_inner(conversation_id: str, ctx: Ctx, gender: str, history: list[dict], settings, tenant_id: str,
                       state: dict) -> str:
    """The think -> tools -> think loop of one turn. Returns the final text shown to the user."""
    from . import pakka
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
            try:   # stays on the brain that worked; Rokiye cancels the model call itself, not just the next step
                blocks, stop, brain = await _watched(_think(brain, system, history, settings, tools), conversation_id, ctx, state)
            except _Halted:
                raise
            except Exception as e:
                if not mcp_defs or not mcp_live.schema_trouble(e):
                    raise
                # a server's tool description the model refuses: go on without the direct MCP tools (bazar_run still works)
                log.warning("MCP tool schemas refused (%s); continuing without them", str(e)[:200])
                mcp_defs, mcp_route, tools = [], {}, TOOLS
                blocks, stop, brain = await _watched(_think(brain, system, history, settings, tools), conversation_id, ctx, state)
        except _Halted as h:
            state["halted"] = h.why
            final_text = HALTED_TEXT[h.why]
            bus.publish(conversation_id, "message", {"role": "assistant", "text": final_text, "source": "agent"})
            _save(conversation_id, "assistant", [{"type": "text", "text": final_text}], display=final_text)
            return final_text
        history.append({"role": "assistant", "content": blocks})
        texts = [b["text"] for b in blocks if b.get("type") == "text" and b.get("text", "").strip()]
        _save(conversation_id, "assistant", blocks, display="\n\n".join(texts) or None)
        if texts:
            final_text = "\n\n".join(texts)
            bus.publish(conversation_id, "message", {"role": "assistant", "text": final_text, "source": "agent"})
        if stop != "tool_use":
            nudge = await _pakka_check(state, final_text, settings, ran_tools, conversation_id)
            if nudge:
                history.append({"role": "user", "content": [{"type": "text", "text": nudge}]})
                _save(conversation_id, "user", [{"type": "text", "text": nudge}])
                continue
            if state.get("correct"):
                final_text = (final_text + "\n\n" + state.pop("correct")).strip()
                bus.publish(conversation_id, "message", {"role": "assistant", "text": final_text, "source": "agent"})
                _save(conversation_id, "assistant", [{"type": "text", "text": final_text}], display=final_text)
            break
        results = []
        for b in blocks:
            if b.get("type") != "tool_use":
                continue
            if conversation_id in _stopped or state.get("halted"):
                results.append({"type": "tool_result", "tool_use_id": b["id"], "is_error": True,
                                "content": "The user tapped Stop. Do not continue this task; say in one line what was done."})
                continue
            held = breaker.before(b["name"], b.get("input") or {})
            if held:                       # circuit breaker: steered / constrained / stopped, the call does not run
                results.append({"type": "tool_result", "tool_use_id": b["id"], "is_error": True, "content": held})
                continue
            ran_tools = True
            args_in = b.get("input") or {}
            from . import where as _where   # v0.93 the card / theatre name the place where it REALLY runs
            shown = _where.shown(b["name"], args_in, getattr(ctx, "place", ""))
            label = gendered(mcp_live.label(b["name"], mcp_route, mcp_snap) if b["name"] in mcp_route
                             else TOOL_LABELS.get(shown, shown), gender)
            bus.publish(conversation_id, "step", {"tool": shown, "label": label, "state": "running", "id": b["id"]})
            _work(conversation_id, b["id"], shown, label, "start", args_in)
            try:
                out = await _watched(_run_tool(b["name"], args_in, ctx, settings, mcp_route), conversation_id, ctx, state)
                fine = not (isinstance(out, dict) and out.get("error"))
                breaker.after(b["name"], fine)
                content = _short(out)
                call = {"tool": b["name"], "ok": fine, "error": "" if fine else str(out.get("error"))[:300],
                        "args": args_in, "key": _key(b["name"], args_in), "result": "" if not fine else content[:300]}
                if not fine:
                    content += await pakka.on_failure(tenant_id, b["name"], call["error"], state.get("request", ""), state)
                    call["internet_fix"] = (state.get("web_fix") or {}).get(b["name"], "")
                state["calls"].append(call)
                results.append({"type": "tool_result", "tool_use_id": b["id"], "content": content})
                bus.publish(conversation_id, "step", {"tool": shown, "label": label, "state": "done", "id": b["id"]})
                _work(conversation_id, b["id"], shown, label, theatre.phase_of(out), args_in, out)
            except _Halted as h:
                state["halted"] = h.why
                state["calls"].append({"tool": b["name"], "ok": False, "error": "stopped by the owner", "args": args_in,
                                       "key": _key(b["name"], args_in)})
                results.append({"type": "tool_result", "tool_use_id": b["id"], "is_error": True,
                                "content": "Stopped by the owner while this step was running; it may have partly happened."})
                bus.publish(conversation_id, "step", {"tool": shown, "label": label, "state": "error", "id": b["id"],
                                                      "detail": "roka gaya"})
                _work(conversation_id, b["id"], shown, label, "stopped", args_in, error="Roka gaya")
            except ToolError as e:
                breaker.after(b["name"], False)
                help_ = await pakka.on_failure(tenant_id, b["name"], str(e), state.get("request", ""), state)
                state["calls"].append({"tool": b["name"], "ok": False, "error": str(e)[:300], "args": args_in,
                                       "key": _key(b["name"], args_in),
                                       "internet_fix": (state.get("web_fix") or {}).get(b["name"], "")})
                results.append({"type": "tool_result", "tool_use_id": b["id"], "content": str(e) + help_, "is_error": True})
                bus.publish(conversation_id, "step", {"tool": shown, "label": label, "state": "error",
                                                      "id": b["id"], "detail": str(e)[:300]})
                _work(conversation_id, b["id"], shown, label, "error", args_in, error=str(e))
            except asyncio.TimeoutError:
                breaker.after(b["name"], False)
                state["calls"].append({"tool": b["name"], "ok": False, "error": "timeout", "args": args_in,
                                       "key": _key(b["name"], args_in)})
                msg = f"{b['name']} did not finish in {settings.agent_tool_timeout_s} seconds and was stopped. Tell the user and offer to try again."
                log.warning("tool %s timed out", b["name"])
                results.append({"type": "tool_result", "tool_use_id": b["id"], "content": msg, "is_error": True})
                bus.publish(conversation_id, "step", {"tool": shown, "label": label, "state": "error",
                                                      "id": b["id"], "detail": "bahut der lag rahi thi, rok diya"})
                _work(conversation_id, b["id"], shown, label, "error", args_in, error="Bahut der lag rahi thi, rok diya")
            except Exception as e:  # unexpected bug: tell the model, keep the turn alive
                breaker.after(b["name"], False)
                state["calls"].append({"tool": b["name"], "ok": False, "error": f"crash: {e}"[:300], "args": args_in,
                                       "key": _key(b["name"], args_in)})
                log.exception("tool %s crashed", b["name"])
                help_ = await pakka.on_failure(tenant_id, b["name"], f"internal error: {e}", state.get("request", ""), state)
                results.append({"type": "tool_result", "tool_use_id": b["id"],
                                "content": f"Internal error in {b['name']}: {e}" + help_, "is_error": True})
                bus.publish(conversation_id, "step", {"tool": shown, "label": label, "state": "error", "id": b["id"]})
                _work(conversation_id, b["id"], shown, label, "error", args_in, error="Kuch gadbad ho gayi")
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
        if conversation_id in _stopped or state.get("halted"):
            final_text = HALTED_TEXT.get(state.get("halted") or "stop", HALTED_TEXT["stop"])
            if state.get("halted"):
                final_text += " Jo kadam chal raha tha woh beech mein roka gaya; dobara karne se pehle dekh lijiye kitna hua."
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


def _key(name: str, args) -> str:
    from .breaker import _key as k
    return k(name, args)


async def _pakka_check(state: dict, final_text: str, settings, ran_tools: bool, conversation_id: str) -> str:
    """v0.78 self-check before the turn ends: real results vs. her request. Returns a nudge to keep working, or ''.
    Sets state['correct'] when the answer claims more than was done, state['left'] when something stays open."""
    from . import pakka
    calls = state.get("calls") or []
    if (not ran_tools or not calls or conversation_id in _stopped or state["breaker"].stopped or state.get("halted")
            or state.get("checks", 0) >= pakka.SELF_CHECKS_PER_TURN):
        return ""
    real = [c for c in calls if c.get("tool") not in pakka.SKIP]
    if not real:
        return ""
    failed = any(not c.get("ok") for c in real)
    if not failed and len(real) < 3:          # a simple job that went fine: no extra model call
        return ""
    state["checks"] = state.get("checks", 0) + 1
    v = await pakka.self_check(state.get("request", ""), calls, final_text, settings)
    if not v:
        return ""
    if v["done"]:
        state.pop("left", None)
        return ""
    state["left"] = v["missing"] or "kuch hissa baaki"
    if v["next"]:
        state["kept_going"] = state.get("kept_going", 0) + 1
        pakka.STATS["kept_going"] += 1
        return ("[System self-check, not the user] The task is NOT finished yet: " + (v["missing"] or "something is left")
                + ". Next step: " + v["next"] + ". Do it now with the tools (follow every card / approval rule as usual). "
                "If it truly cannot be done, say plainly what is done, what is left and what she can do.")
    if not v["claim_ok"]:
        pakka.STATS["corrected_claims"] += 1
        state["correct"] = "(Saaf baat: abhi yeh baaki hai — " + (v["missing"] or "kuch hissa") + ".)"
    return ""


def stop(conversation_id: str) -> None:
    """The owner tapped Stop: the running model call / tool call is cancelled at once (v0.91) and nothing more runs."""
    _stopped.add(conversation_id)
    bus.publish(conversation_id, "work", {"id": "stop", "tool": "", "scene": "work", "phase": "stopped",
                                          "label": "Roka gaya", "data": {}})


def _work(conversation_id: str, call_id: str, tool: str, label: str, phase: str, args=None, out=None, error: str = "") -> None:
    if phase == "start":
        from . import quick
        quick.note_step(conversation_id, label)
    try:
        bus.publish(conversation_id, "work", theatre.event(call_id, tool, label, phase, args, out, error))
    except Exception:
        log.exception("work event failed")


async def run_turn(conversation_id: str, user_text: str, tenant_id: str | None = None, voice: bool = False,
                   context: str = "", actor: str = "owner", place: str = "") -> str:
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
        try:   # v0.93 "mere PC pe" vs "apne browser mein": the place she named holds for this turn's tools
            from . import where
            ctx.place = place or where.remember(conversation_id, user_text)
        except Exception:
            log.exception("place check failed")
    lock = _locks[conversation_id]
    if lock.locked() and (actor or "owner") == "owner" and not voice:
        # v0.86 a long job holds the chat: answer this message NOW from the quick lane; only real work waits
        from . import quick
        got = await quick.answer(conversation_id, tenant_id, user_text)
        if got and not got["queued"]:
            return got["text"]
    async with lock:
        notes = _pending_worker_notes(conversation_id)
        from . import quick as _quick
        notes += _quick.take_notes(conversation_id)
        agent_text = f"{VOICE_NOTE}\n{user_text}" if voice else user_text
        if context:                         # e.g. files the owner attached (only the words show in the chat)
            agent_text += "\n\n" + context
        if ctx.place:                       # v0.93 the place she named, said plainly to the model
            from . import where
            agent_text += "\n\n" + where.note(ctx.place)
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
