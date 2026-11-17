"""P4 THE HAND-OVER, LIVE (plan 5.2 + 5.3 + 6.8): every model call of a Box part goes through `call`.

  error / refusal / empty answer   -> the next backup at the SAME level, at once
  no first word in time            -> chat / background: the slow call is stopped and the backup starts
                                      call: the backup starts AT THE SAME TIME and the first answer wins (head start)
  the part outgrew the window      -> a same-level model with a bigger window
  at most two changes per part; after that the last error goes up as it is (the turn says it plainly, as today)

A call waits its turn in the per-user and per-company queues (`limits.slot`). A model's failures go into the Box's
outage record (two in ten minutes = paused for the next message), never against the whole OpenRouter brain.
The decisions themselves are `handover.next_move` (P1, pure); this file only carries them out.
"""
from __future__ import annotations

import asyncio
import contextvars
import logging
import re
import time
from typing import Any, Awaitable, Callable

from . import handover as H
from . import limits as LM

log = logging.getLogger("santosh.pipeline")

HAND: contextvars.ContextVar[dict | None] = contextvars.ContextVar("hoola_box_hand", default=None)
STATS = {"calls": 0, "switches": 0, "races": 0, "race_backup_won": 0, "late": 0, "errors": 0, "empty": 0,
         "bigger": 0, "gave_up": 0}
TOO_LONG = re.compile(r"(?i)context[_ ]length|maximum context|too many tokens|prompt is too long|context window|"
                      r"reduce the length|exceeds? the (?:max|context)")
REFUSED = re.compile(r"(?i)content[_ ]filter|refus|safety|policy violation")
# v0.970 her live v0.969 test: OpenRouter answered 403 "Model google/gemini-4-carbon-... is banned" for her account -
# a model that cannot answer at all (banned / gone / not offered to her) is off for a day, not tried every message
HARD = re.compile(r"(?i)\bis banned\b|\bbanned\b|no endpoints found|not a valid model|model[^.]{0,60}(?:not found|does not "
                  r"exist|no longer available)|no allowed providers|not available in your region")
KEY_LEVEL = re.compile(r"(?i)key limit|insufficient credits|credit|quota|rate.?limit|\b429\b|unauthor|\b401\b")
# failed model id -> the model that took over, for THIS message only (turnbox.begin opens it, end drops it; the turn's
# tasks share the one dict). A Box part's own attempt always runs on exactly the model it names (EXACT).
TURN_SWAP: contextvars.ContextVar[dict | None] = contextvars.ContextVar("hoola_box_swap", default=None)
EXACT: contextvars.ContextVar[bool] = contextvars.ContextVar("hoola_box_exact", default=False)


def _swapped(old: str, new: str) -> None:
    d = TURN_SWAP.get()
    if d is not None and old and new and old != new:
        d[old] = new


def live(model: str) -> str:
    """'openrouter:<id>' with a model handed over in this message replaced by the one that took over (followed
    again if that one was handed over too), so the rest of the turn never asks the failed model again."""
    if not model.startswith("openrouter:") or EXACT.get():
        return model
    d = TURN_SWAP.get()
    if not d:
        return model
    mid = model.split(":", 1)[1]
    for _ in range(3):
        if mid not in d:
            break
        mid = d[mid]
    return "openrouter:" + mid


def hard(why: str) -> bool:
    return bool(HARD.search(why or "")) and not KEY_LEVEL.search(why or "")


def model_failed(model: str, why: str) -> None:
    """A call of a Box turn outside a Box part failed (a check, a title, the facts): the failure goes to that model's
    outage record; a banned / gone model is off for a day. The whole OpenRouter brain is never paused for it."""
    mid = model.split(":", 1)[1] if model.startswith("openrouter:") else model
    if not mid:
        return
    _note(mid, False)
    if hard(why):
        _dead(mid, why)


def _dead(mid: str, why: str) -> None:
    try:
        from . import turnbox as TB
        TB.mark_dead(mid, why)
    except Exception:   # noqa: BLE001
        log.debug("mark dead failed", exc_info=True)


class Late(Exception):
    pass


def new_hand(*, kind: str, level: str, surface: str, model: dict, backups: list[dict], tenant: str = "",
             doc: dict | None = None, sheet: dict | None = None, n: int = 0, language: str = "") -> dict[str, Any]:
    """What one Box part carries while it runs: the hand-over state, the model in use, the backups left."""
    return {"part": H.new_part(kind, level, surface), "current": dict(model or {}), "backups": list(backups or []),
            "tenant": tenant, "doc": doc or {}, "sheet": sheet, "n": n, "language": language, "used": [model.get("id")]}


def _empty(blocks: list[dict]) -> bool:
    for b in blocks or []:
        if not isinstance(b, dict):
            continue
        if b.get("type") == "tool_use":
            return False
        if b.get("type") == "text" and str(b.get("text") or "").strip():
            return False
    return True


def _event_of(e: BaseException) -> str:
    m = str(e)
    if TOO_LONG.search(m):
        return "too_long"
    if REFUSED.search(m):
        return "refusal"
    return "error"


def _bigger(hand: dict) -> dict | None:
    """A same-level model with a bigger window than the one in use (from the tables copy this message holds)."""
    doc = hand.get("doc") or {}
    models = doc.get("models") or {}
    cur = hand["current"].get("id")
    have = int((models.get(cur) or {}).get("ctx") or 0)
    pool = [m for m in hand["backups"] if m.get("id") not in hand["used"]]
    try:
        from .choose import table_for
        t, _k, _n = table_for(doc, hand["part"]["kind"], hand.get("language") or "")
        pool += [m for m in ((t or {}).get("levels") or {}).get(hand["part"]["level"], []) or []
                 if m.get("id") not in hand["used"]]
    except Exception:   # noqa: BLE001
        pass
    best = None
    for m in pool:
        if m.get("route") != "openrouter":
            continue
        c = int((models.get(m.get("id")) or {}).get("ctx") or 0)
        if c > have and (best is None or c > best[0]):
            best = (c, m)
    return best[1] if best else None


def _next_model(hand: dict, mv: dict) -> dict | None:
    if mv["action"] == "bigger":
        return _bigger(hand)
    for m in hand["backups"]:
        if m.get("id") not in hand["used"] and m.get("route") == "openrouter":
            return m
    return None


def _switch(hand: dict, event: str, why: str) -> bool:
    """Move the part to its next model. False = no move left (stop)."""
    mv = H.next_move(hand["part"], event)
    if mv["action"] not in ("backup", "race", "bigger"):
        STATS["gave_up"] += 1
        return False
    m = _next_model(hand, mv)
    if not m:
        STATS["gave_up"] += 1
        return False
    old = hand["current"].get("id")
    hand["current"] = dict(m)
    hand["used"].append(m.get("id"))
    _swapped(old, m.get("id"))
    STATS["switches"] += 1
    if mv["action"] == "bigger":
        STATS["bigger"] += 1
    _record(hand, {"event": event, "from": old, "to": m.get("id"), "why": why[:160], "at": round(time.time(), 1)})
    log.warning("pipeline box hand-over: %s -> %s (%s: %s)", old, m.get("id"), event, why[:120])
    try:   # v0.979 P7: the hand-over written down for the week's read-back
        from . import watch as W
        W.outage(old or "", "handover", f"{event} -> {m.get('id')}: {why[:120]}")
    except Exception:   # noqa: BLE001
        pass
    return True


def _record(hand: dict, row: dict) -> None:
    sh = hand.get("sheet")
    n = int(hand.get("n") or 0)
    if not sh or not n or n > len(sh.get("parts") or []):
        return
    try:
        p = sh["parts"][n - 1]
        p.setdefault("handover", []).append(row)
        if row.get("to"):
            p["ran_on"] = row["to"]
        from . import sheet as S
        S.save(sh)
    except Exception:   # noqa: BLE001 - the record never breaks the answer
        log.debug("hand-over record failed", exc_info=True)


def _note(model_id: str, ok: bool) -> None:
    try:
        from . import turnbox as TB
        TB.note(model_id, ok)
    except Exception:   # noqa: BLE001
        pass


Make = Callable[[Callable[[], None]], Awaitable[tuple]]


async def _attempt(hand: dict, make: Make, first: Callable[[], None]) -> tuple:
    """One call on the part's current model, in its queue slot, with the Box owning the failure."""
    from ..agent import llm
    m = hand["current"]
    tok = llm.MODEL_NOW.set("openrouter:" + str(m.get("id")))
    own = llm.BOX_OWNS.set(True)
    ex = EXACT.set(True)
    try:
        async with LM.slot(hand.get("tenant") or "", m.get("id")):
            return await make(first)
    finally:
        EXACT.reset(ex)
        llm.BOX_OWNS.reset(own)
        llm.MODEL_NOW.reset(tok)


async def call(hand: dict, make: Make, *, streaming: bool = False, reset: Callable[[], None] | None = None) -> tuple:
    """One model call of a Box part, with the hand-over rules carried out. `make(first)` starts the call; `first()`
    must be called when the first word / thought / tool call arrives (streaming). Returns (blocks, stop, usage)."""
    surface = hand["part"].get("surface") or "chat"
    limit = H.first_word_limit(surface)
    while True:
        STATS["calls"] += 1
        started = asyncio.Event()
        model_id = hand["current"].get("id")
        task = asyncio.ensure_future(_attempt(hand, make, started.set))
        try:
            if surface == "call" and not streaming:
                out = await _race(hand, make, task, limit)
            elif streaming:
                out = await _watch_first_word(task, started, limit)
            else:
                out = await task
        except asyncio.CancelledError:
            task.cancel()
            raise
        except Late:
            STATS["late"] += 1
            if not _switch(hand, "late", f"no first word in {limit:g} s"):
                raise TimeoutError(f"{model_id}: no first word in {limit:g} s and no backup left") from None
            continue
        except Exception as e:   # noqa: BLE001 - the rules decide: backup, bigger window, or give up
            STATS["errors"] += 1
            _note(model_id, False)
            if hard(str(e)):
                _dead(model_id, str(e))
            if reset is not None and started.is_set():
                reset()          # words of the failed try already on her screen go away before the backup writes
            if not _switch(hand, _event_of(e), str(e)):
                raise
            continue
        blocks, stop = out[0], out[1]
        if _empty(blocks):
            STATS["empty"] += 1
            _note(model_id, False)
            if _switch(hand, "empty", f"empty answer (stop {stop})"):
                continue
            return out
        _note(hand["current"].get("id"), True)
        return out


async def _watch_first_word(task: asyncio.Future, started: asyncio.Event, limit: float) -> tuple:
    """Streaming: the call must show its first word within `limit`; a late one is stopped (the backup starts)."""
    waiter = asyncio.ensure_future(started.wait())
    try:
        done, _ = await asyncio.wait({task, waiter}, timeout=limit, return_when=asyncio.FIRST_COMPLETED)
    finally:
        if not waiter.done():
            waiter.cancel()
    if not done:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
        raise Late()
    return await task


async def _race(hand: dict, make: Make, first_task: asyncio.Future, limit: float) -> tuple:
    """A live call (5.2): no answer within `limit` = the backup starts at the same time; the first good answer is
    used and the other is stopped. Silence on a call is the worst case."""
    done, _ = await asyncio.wait({first_task}, timeout=limit)
    if done:
        return first_task.result()
    STATS["races"] += 1
    first_model = hand["current"].get("id")
    mv = H.next_move(hand["part"], "late")
    nxt = _next_model(hand, mv) if mv["action"] in ("race", "backup") else None
    if not nxt:
        return await first_task
    racer = dict(hand)
    racer["current"] = dict(nxt)
    hand["used"].append(nxt.get("id"))
    second = asyncio.ensure_future(_attempt(racer, make, lambda: None))
    pending = {first_task, second}
    last_exc: BaseException | None = None
    while pending:
        done, pending = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)
        for t in done:
            if t.exception() is None and not _empty(t.result()[0]):
                for p in pending:
                    p.cancel()
                if pending:
                    await asyncio.gather(*pending, return_exceptions=True)
                if t is second:
                    STATS["race_backup_won"] += 1
                    hand["current"] = dict(nxt)
                    _swapped(first_model, nxt.get("id"))
                    _record(hand, {"event": "late", "from": first_model, "to": nxt.get("id"),
                                   "why": f"call: backup started at {limit:g} s and answered first",
                                   "at": round(time.time(), 1)})
                return t.result()
            last_exc = t.exception() or last_exc
    if last_exc is not None:
        raise last_exc
    return first_task.result()
