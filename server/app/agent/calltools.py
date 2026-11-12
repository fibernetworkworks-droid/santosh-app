"""G8 of docs/LANGGRAPH_TURN_PLAN.md - the tools Gemini Live calls ITSELF on a call (declared in voice.VOICE_TOOL_NAMES,
not handed to santosh_kaam) go through the same funnel and ledger as a graph turn's tools (only when `chat_graph` and
`graph_call_tools` are on; off = voice.Call._execute calls dispatch exactly as before).

No model step and no wait is added to a call: one small indexed ledger row before a changing tool and one after it.

THE FUNNEL. Every direct call tool runs through santosh._run_tool (the harness log, the memory capture, TEEN MODE, the
key scrub - the same as a chat tool), with the call's own dispatch.

THE LEDGER (agent/toolledger.py rows) is keyed on the call's CHAT: thread "<chat>:call" (a split call's record maps
to the chat behind it, so a re-dial after a server restart - a new call id, a new record - is the same thread).
Gemini re-issues a tool call after a reconnect (GoAway, a park / wake, a 1011 rebuild, a re-dial): the newest
changing row on the thread is compared with the new call -

    the same tool + the same arguments, `done`, within `graph_call_tools_window_m`  -> NOT run again; the stored result
                                                                                       comes back with a plain note
    the same tool + the same arguments, `intent` (a restart cut it mid-run)        -> NOT run again; the honest
                                                                                       "it may already have run" error
    the same, still running in this process                                         -> "already running" (never twice)
    anything else (another tool in between, other arguments, a failed one)          -> runs normally

Only the NEWEST changing row counts, so "light on, light off, light on" runs three times, while a send repeated
right after itself is caught. Look-ups (draftcheck's read classification) skip the ledger: they change nothing.

THE FACTS. Each direct tool's outcome is one G3 fact (turnfacts.classify on its call record + ledger row: did / card
/ read / failed / ambiguous), written into the call's run slot. voice.Call keeps it per `did` entry: the spoken
"ho gaya" check judges a direct tool by it (a card is not done) and the call's receipt in the chat after hang-up says
"waiting for your tap" for a card instead of "done". The receipt is told once through a G5 record
("call:<call id>:receipt")."""
from __future__ import annotations

import asyncio
import logging
import time
from datetime import timedelta

from sqlalchemy import select

log = logging.getLogger("santosh.calltools")

STATS = {"runs": 0, "reads": 0, "ledgered": 0, "reused": 0, "ambiguous": 0, "in_flight": 0, "facts": 0}
_INFLIGHT: set = set()


def on(settings=None) -> bool:
    try:
        if settings is None:
            from ..config import get_settings
            settings = get_settings()
        return bool(getattr(settings, "chat_graph", False) and getattr(settings, "graph_call_tools", False))
    except Exception:   # noqa: BLE001
        return False


def thread(call) -> str:
    """The ledger thread of a call's direct tools: the call's chat (the record's chat for a split call)."""
    conv = str(getattr(call, "conv", "") or "")
    chat = conv
    try:
        from .. import callconv
        chat = callconv.chat_of(conv) or conv
    except Exception:   # noqa: BLE001
        pass
    return f"{chat or 'call'}:call"[:160]


def _newest(th: str, since) -> dict | None:
    from . import toolledger as L
    L.ensure_table()
    from ..db import session
    with session() as s:
        r = s.scalars(select(L.TurnToolLedger).where(L.TurnToolLedger.thread_id == th,
                                                     L.TurnToolLedger.updated_at >= since)
                      .order_by(L.TurnToolLedger.created_at.desc()).limit(1)).first()
        if r is None:
            return None
        return {"tool_use_id": r.tool_use_id, "tool": r.tool, "args_hash": r.args_hash, "state": r.state,
                "result": r.result, "error_kind": r.error_kind, "error": r.error}


def _fact(name: str, out, err: str, row: dict | None, read_only: bool) -> dict:
    from . import turnfacts
    call = None
    if err != "__none__":
        ok = not err and not (isinstance(out, dict) and (out.get("error") or out.get("ok") is False))
        call = {"tool": name, "ok": ok, "error": err or (str(out.get("error")) if isinstance(out, dict)
                                                         and out.get("error") else ""),
                "result": "" if not ok else str(out)[:300]}
    eff, why = turnfacts.classify(call, None, row, read_only)
    STATS["facts"] += 1
    return {"tool": name, "effect": eff, "object": "", "error": why[:160]}


def _slot_fact(fact: dict, args: dict) -> None:
    try:
        from .. import voice
        from . import turnfacts
        fact["object"] = turnfacts._obj(args) or fact.get("object", "")
        slot = voice._RUN_SLOT.get()
        if isinstance(slot, dict):
            slot["fact"] = fact
    except Exception:   # noqa: BLE001
        log.debug("call fact slot failed", exc_info=True)


async def run(call, name: str, args: dict):
    """One direct call tool through santosh._run_tool, with the ledger + the fact (see the module note)."""
    from . import santosh as S
    from . import toolledger as L
    from .tools import ToolError
    from .. import voice
    from ..config import get_settings
    settings = get_settings()
    ctx = call.ctx
    STATS["runs"] += 1
    ro = L.read_only({"name": name, "input": args})
    if ro:                                  # a look-up: no ledger, nothing to repeat
        STATS["reads"] += 1
        try:
            out = await S._run_tool(name, args, ctx, settings, None, dispatch_fn=voice.dispatch)
        except BaseException as e:
            _slot_fact(_fact(name, None, f"{type(e).__name__}: {e}"[:160] or "failed", None, True), args)
            raise
        _slot_fact(_fact(name, out, "", None, True), args)
        return out
    th = thread(call)
    h = L.args_hash(args)
    key = (th, name, h)
    if key in _INFLIGHT:
        STATS["in_flight"] += 1
        _slot_fact({"tool": name, "effect": "ambiguous", "object": "", "error": "already running"}, args)
        raise ToolError(f"This exact {name} step is already running from a moment ago - do not start it again; "
                        "wait for its result and tell her that.")
    win = float(getattr(settings, "graph_call_tools_window_m", 30.0) or 0)
    if win > 0:
        from ..db import now
        last = _newest(th, now() - timedelta(minutes=win))
        if last and last["tool"] == name[:120] and last["args_hash"] == h:
            if last["state"] == "done":
                STATS["reused"] += 1
                L.STATS["reused"] += 1
                import json
                try:
                    out = json.loads(last["result"])
                except Exception:   # noqa: BLE001
                    out = last["result"]
                _slot_fact(_fact(name, out, "", last, False), args)
                note = (f"ALREADY DONE a moment ago in this call - this exact {name} was NOT run again. Do not repeat "
                        "it; tell her it was already done.")
                return {**out, "already_done": note} if isinstance(out, dict) else {"result": out, "already_done": note}
            if last["state"] == "intent":
                STATS["ambiguous"] += 1
                L.STATS["ambiguous"] += 1
                _slot_fact({"tool": name, "effect": "ambiguous", "object": "", "error": "outcome unknown"}, args)
                raise ToolError(L.ambiguous_text(name))
    tid = f"{getattr(call, 'call_id', 'call')}:{int(time.time() * 1000)}:{name}"[:120]
    STATS["ledgered"] += 1
    _INFLIGHT.add(key)
    try:
        try:
            L.intent(th, tid, name, h)
        except Exception:   # noqa: BLE001 - a ledger that cannot be written never stops the call's tool
            log.exception("call tool ledger intent failed")
        try:
            out = await S._run_tool(name, args, ctx, settings, None, dispatch_fn=voice.dispatch)
        except ToolError as e:
            _led(L.failed, th, tid, "tool_error", str(e))
            _slot_fact(_fact(name, None, str(e)[:160] or "failed", {"state": "failed"}, False), args)
            raise
        except asyncio.TimeoutError:
            _led(L.failed, th, tid, "timeout", "")
            _slot_fact(_fact(name, None, "timeout", {"state": "failed", "error_kind": "timeout"}, False), args)
            raise
        except BaseException as e:
            if not isinstance(e, asyncio.CancelledError):
                _led(L.failed, th, tid, "crash", f"{type(e).__name__}: {e}")
                _slot_fact(_fact(name, None, f"crash: {e}"[:160], {"state": "failed"}, False), args)
            raise                               # cancelled (a restart): stays `intent` - never re-run blindly
        _led(L.done, th, tid, out)
        _slot_fact(_fact(name, out, "", {"state": "done"}, False), args)
        return out
    finally:
        _INFLIGHT.discard(key)


def _led(fn, *a) -> None:
    try:
        fn(*a)
    except Exception:   # noqa: BLE001
        log.exception("call tool ledger %s failed", getattr(fn, "__name__", "?"))


def receipt_once(call) -> bool:
    """True = make the call's receipt now (its G5 record says it was never told); False = already told."""
    try:
        from . import turndeliver as D
        cid = str(getattr(call, "call_id", "") or "")
        if not cid:
            return True
        key = f"call:{cid}:receipt"[:200]
        target = D.target_chat(str(getattr(call, "conv", "") or ""), str(getattr(call, "tenant", "") or ""))
        did = list(getattr(call, "did", []) or [])
        n_did = sum(1 for d in did if d.get("effect") == "did")
        n_card = sum(1 for d in did if d.get("effect") == "card")
        n_bad = sum(1 for d in did if d.get("effect") in ("failed", "ambiguous"))
        D.record(key, str(getattr(call, "tenant", "") or ""), target, thread=thread(call), kind="call",
                 outcome="done" if not (n_card or n_bad) else "partial")
        if D.done(key, "chat"):
            return False
        D.stamp(key, "chat", D.SENT, by="call receipt", did=n_did, cards=n_card, failed=n_bad,
                facts=[{"tool": d.get("tool"), "effect": d.get("effect")} for d in did if d.get("effect")][-40:])
        return True
    except Exception:   # noqa: BLE001
        log.exception("call receipt record failed")
        return True
