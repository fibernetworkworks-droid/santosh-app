"""G2 of docs/LANGGRAPH_TURN_PLAN.md - one run per chat, and Stop as state (only when `chat_graph` is on).

ONE RUN PER CHAT. Before G2 the per-chat asyncio lock was the only rule, and two holes let a chat run twice or out of
order (bug class 6):
  * the lock is taken AFTER the turn's pre-lock work (the operator OTP check, the research plan gate - a model call -,
    the approval words, the stop words), so a later message with less pre-lock work reached the lock first and ran
    before an earlier one;
  * `asyncio.Lock.release()` frees the lock one loop step before the next waiter owns it, and a queued turn waits
    with its inbox row already 'running'. The restart sweep asks `turn_running(conv)` (= lock.locked()), so in that
    window it saw a free chat and started the SAME inbox row a second time.
Now every turn takes a TICKET the moment `run_turn` is entered (arrival order) and may take the chat lock only when
its ticket is the oldest of that chat; the ticket is given back when the turn is over (whatever way it ends). A
second message arriving while a run is live therefore never starts a second run: it is that chat's next input -
her own words still reach a live job of hers at its next step through the existing steer queue (agent/steer.py,
unchanged), anything else (a wake, a routine, a goal round, her message when the steer did not take it) runs right
after, in arrival order. A ticket for an inbox row that already has a ticket in this process is refused (that row
is already running or queued here - never run twice), and the sweep skips a chat that has any ticket.
The old lock is still taken inside the ticket, so every reader of `_locks` (typing dots, kaamstop, kaamwatch, the
compaction route, the call's side records) keeps working unchanged.

STOP AS STATE (bug class 8). A Stop (the Stop button `santosh.stop`, `kaamstop.cancel` / her stop words - both end in
`santosh.stop`) marks the chat's LIVE run stopped: a flag every graph node checks at its boundary, an event that wakes
the running model / tool call's watcher at once (`santosh._watched` cancels the work task), the run's inbox row
marked 'stopped' at once (the restart sweep only takes accepted / running rows) and the flag written into the graph
checkpoint (a stopped thread is never resumable). Queued messages behind a stopped run keep today's semantics: the
Stop button stops the run that is live, the next queued message still runs after it; kaamstop additionally marks
every accepted / running inbox row of that chat 'stopped' (unchanged), so a restart never re-runs them, while the
ones already queued in this process still run in order.

Nothing here runs when `chat_graph` is off: no ticket is ever made, so every function below answers "no run".
"""
from __future__ import annotations

import asyncio
import contextvars
import itertools
import logging
import time
from typing import Any

log = logging.getLogger("santosh.turnrun")

STATS = {"tickets": 0, "waited": 0, "refused_duplicate": 0, "stopped": 0, "stale_dropped": 0}
_SEQ = itertools.count(1)


class Run:
    """One turn's place in its chat: queued -> live -> gone."""

    __slots__ = ("conv", "inbox_id", "actor", "seq", "state", "stopped", "stop_at", "event", "fut", "loop", "at",
                 "resume", "graph_taken")

    def __init__(self, conv: str, inbox_id: str | None, actor: str, resume: bool = False):
        self.conv, self.inbox_id, self.actor = conv, inbox_id or None, actor or "owner"
        self.resume = bool(resume and inbox_id)    # G1: this run continues the inbox row's checkpoint
        self.graph_taken = False
        self.seq = next(_SEQ)
        self.state = "queued"
        self.stopped = False
        self.stop_at = 0.0
        self.event: asyncio.Event | None = None
        self.fut: asyncio.Future | None = None
        try:
            self.loop = asyncio.get_running_loop()
        except RuntimeError:
            self.loop = None
        self.at = time.time()

    def __repr__(self) -> str:
        return f"<Run {self.conv} #{self.seq} {self.actor} {self.state}{' stopped' if self.stopped else ''}>"


_CHATS: dict[str, list[Run]] = {}
CURRENT: contextvars.ContextVar = contextvars.ContextVar("turnrun_current", default=None)
_STOPPED_INBOX: dict[str, float] = {}          # inbox ids whose run was stopped (run_owned keeps them 'stopped')


def _alive(r: Run) -> bool:
    """A run of an event loop that is gone (a test's earlier asyncio.run, a crashed loop) can never give its ticket
    back - it must not hold the chat for ever."""
    lp = r.loop
    return lp is None or not lp.is_closed()


def _runs(conv: str) -> list[Run]:
    rs = _CHATS.get(conv) or []
    if any(not _alive(r) for r in rs):
        keep = [r for r in rs if _alive(r)]
        STATS["stale_dropped"] += len(rs) - len(keep)
        if keep:
            _CHATS[conv] = keep
        else:
            _CHATS.pop(conv, None)
        rs = keep
    return rs


_OWNER: dict[str, Any] = {}                    # inbox id -> the run_owned task that runs it


def claim_inbox(inbox_id: str | None) -> None:
    """run_owned: THIS task runs this inbox row (a background task the turn spawns inherits the inbox context
    variables, but it is another task - it must not pass itself off as the row's turn)."""
    if inbox_id:
        try:
            _OWNER[inbox_id] = asyncio.current_task()
        except RuntimeError:
            pass


def release_inbox(inbox_id: str | None) -> None:
    if inbox_id:
        _OWNER.pop(inbox_id, None)


def inbox_for(conv: str) -> tuple[str | None, bool]:
    """(inbox id, resume?) of the turn run_turn is entering - only when the CALLING TASK is the row's run_owned."""
    from .. import turn_inbox
    g = turn_inbox.GRAPH_TURN.get()
    if not g or g[1] != conv or not g[0]:
        return None, False
    try:
        me = asyncio.current_task()
    except RuntimeError:
        me = None
    if me is None or _OWNER.get(g[0]) is not me:
        return None, False
    return g[0], bool(turn_inbox.GRAPH_RESUME.get())


def take_graph(conv: str) -> tuple[str | None, bool] | None:
    """turngraph: the ticket's (inbox id, resume?) once; None = no ticket of this chat (the G1 context path answers)."""
    r = CURRENT.get()
    if r is None or r.conv != conv:
        return None
    if r.graph_taken:
        return None, False
    r.graph_taken = True
    return r.inbox_id, r.resume


def owns(inbox_id: str | None) -> bool:
    """This process already has a turn (live or queued) for this inbox row."""
    if not inbox_id:
        return False
    return any(r.inbox_id == inbox_id for conv in list(_CHATS) for r in _runs(conv))


def enter(conv: str, inbox_id: str | None, actor: str, resume: bool = False) -> Run | None:
    """Take a ticket (arrival order). None = this inbox row already has a ticket here: do not run it again."""
    if inbox_id and any(r.inbox_id == inbox_id for r in _runs(conv)):
        STATS["refused_duplicate"] += 1
        log.warning("turn run: inbox row %s of %s is already running or queued here - not run twice", inbox_id, conv)
        return None
    r = Run(conv, inbox_id, actor, resume)
    _CHATS.setdefault(conv, []).append(r)
    STATS["tickets"] += 1
    return r


async def wait_turn(r: Run) -> None:
    """Wait until this ticket is the oldest of its chat (the caller then takes the chat lock)."""
    waited = False
    while True:
        rs = _runs(r.conv)
        if not rs or rs[0] is r:
            break
        if r not in rs:                  # given back from outside (should not happen): never wait for nothing
            break
        waited = True
        r.fut = asyncio.get_running_loop().create_future()
        try:
            await r.fut
        finally:
            r.fut = None
    if waited:
        STATS["waited"] += 1


def go_live(r: Run) -> None:
    """The ticket holds the chat lock: this is the chat's one live run."""
    r.state = "live"
    r.event = asyncio.Event()


def leave(r: Run | None) -> None:
    """The turn is over: the ticket goes and the next one of the chat may take the lock."""
    if r is None:
        return
    r.state = "gone"
    rs = _CHATS.get(r.conv) or []
    try:
        rs.remove(r)
    except ValueError:
        pass
    if not rs:
        _CHATS.pop(r.conv, None)
        return
    for nxt in list(rs):
        if not _alive(nxt):
            continue
        f = nxt.fut
        if f is not None and not f.done():
            try:
                f.set_result(None)
            except Exception:   # noqa: BLE001 - a future of a dead loop
                pass
        break


def live_run(conv: str) -> Run | None:
    for r in _runs(conv):
        if r.state == "live":
            return r
    return None


def busy(conv: str) -> bool:
    """A run of this chat is live or queued here (the restart sweep must leave it alone)."""
    return bool(_runs(conv))


def stopped(conv: str) -> bool:
    """The chat's live run was stopped (False when no graph run is live - the old path never has one)."""
    r = live_run(conv)
    return bool(r is not None and r.stopped)


def stop_event(conv: str) -> asyncio.Event | None:
    """The live run's stop event (santosh._watched wakes on it at once); None on the old path."""
    r = live_run(conv)
    return r.event if r is not None else None


def stop(conv: str) -> bool:
    """She tapped Stop (or said a stop word): the live run of this chat is stopped. False = no live graph run."""
    r = live_run(conv)
    if r is None:
        return False
    if not r.stopped:
        STATS["stopped"] += 1
    r.stopped, r.stop_at = True, time.time()
    if r.event is not None:
        try:
            here = asyncio.get_running_loop()
        except RuntimeError:
            here = None
        if r.loop is not None and here is not r.loop:
            # kaamstop.cancel runs in a worker thread (asyncio.to_thread): an asyncio.Event is not thread-safe
            try:
                r.loop.call_soon_threadsafe(r.event.set)
            except RuntimeError:          # the run's loop is gone
                pass
        else:
            r.event.set()
    if r.inbox_id:
        _STOPPED_INBOX[r.inbox_id] = time.time()
        for k in [k for k, t in _STOPPED_INBOX.items() if time.time() - t > 86400]:
            _STOPPED_INBOX.pop(k, None)
        try:   # at once: a restart in the next second must not re-run (or resume) a stopped turn
            from .. import turn_inbox
            turn_inbox.mark(r.inbox_id, "stopped")
        except Exception:   # noqa: BLE001
            log.debug("inbox stop mark failed", exc_info=True)
    return True


def was_stopped(inbox_id: str | None) -> bool:
    """run_owned: this inbox row's run was stopped - it stays 'stopped', never 'done'."""
    return bool(inbox_id and inbox_id in _STOPPED_INBOX)


def snapshot() -> dict[str, Any]:
    """Diagnostics / tests: every chat's tickets in order."""
    return {c: [repr(r) for r in rs] for c, rs in _CHATS.items()}
