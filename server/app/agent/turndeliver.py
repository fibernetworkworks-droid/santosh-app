"""G5 of docs/LANGGRAPH_TURN_PLAN.md - the turn's outcome in state + ONE delivery record (only when `chat_graph` is on).

Bug class 2 (a result told late / twice / never / in the wrong chat: v0.260, v0.552, v0.553, v0.657, v0.714, v0.722)
came from ~five delivery paths each guessing "was she already told?" by TIMING - a reply row newer than the job's
finish, her last words older than the job's start, a title's words in the last four rows. On the graph path that guess
is replaced by a RECORD written by the graph's `deliver` node (agent/turngraph.py), the one place on that path that
tells her a turn's / a job's result:

    turn_deliveries row, key = the outcome's idempotency key
        turn:<thread>:<nonce>   one graph run (a plain turn, one segment of a long job)
        news:<followup id>      a finished job's wake report (kaam_followup._wake_turn opens it before the turn runs)
        job:<job key>:<state>   an alias: "this job's <state> was told by <turn / news key>" - what kaam_followup asks
    target chat, outcome (done / partial / stuck / stopped / failed), the newest message id when it opened (`mark`),
    and per channel {state: intent | sent, at, ...}:
        chat   the reply row (written by the turn's own step - the live stream - or by the node when no step wrote it)
        push   the reply's own `message` event went through push.on_event (quiet hours, live call, night hold: today's
               gates, nothing re-implemented)
        call   the quiet note into her live call(s) (kaamwatch._voice) - only for news: a wake report / a job that
               ended in a background run
        ring   the voice ring (kaam_followup._ring -> push.on_event voice_ring: her switch, quiet hours, daily cap,
               never over a live call) - the same news only

TOLD ONCE ACROSS A RESTART. Each channel is stamped `intent` BEFORE it is sent and `sent` after (the tool-ledger rule):
a re-run of the node (a restart between its send and its checkpoint) finds the stamp and sends nothing again - an
`intent` with no `sent` is treated as maybe-sent, never re-sent (at most once; the chat row is exactly once because
the node writes the row and its stamp in one transaction). The record is a database row, not the checkpoint, so it
survives the checkpoint being cleaned or never written.

G6 (voice as a channel, agent/turnchannel.py). A call's brain ask runs through the same graph; voice.Call._delegate sets
`CALL` (a ticket: the call, the record it runs on, the inbox row) around the job's task. The deliver node of that run
fills the ticket (the record key, the result word, the run's G3 facts) and stamps the `call` channel `due`; the CALL
then tells it - the tool answer when the run finished inside the call's first wait, else Call._late_result - through
`once(key, "call", ...)`, so a result is told on the call exactly once and never from a stale outcome. While a live
call holds the run's conversation the reply's push is recorded `held` (push.on_event's live-call gate kept it off the
phone: she hears it). A call that ended before the result: the reply row + its push are the delivery, and the call's
`call` channel is stamped `skipped` (told in the chat) so the next call does not tell it again.

Nothing here runs when `chat_graph` is off (kaam_followup / turn_inbox ask `graph_on()` first)."""
from __future__ import annotations

import contextvars
import json
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import DateTime, Integer, String, Text, delete, func, select
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, now, session

log = logging.getLogger("santosh.turndeliver")

STATS = {"opened": 0, "chat_step": 0, "chat_node": 0, "push": 0, "call": 0, "ring": 0, "skipped_told": 0,
         "jobs_told": 0, "news_recovered": 0}
SENT, INTENT = "sent", "intent"
RESULTS = ("done", "partial", "stuck", "stopped", "failed")

# kaam_followup._wake_turn: the finished job this wake turn reports (its record key, the job key + state, the title).
# Read by the graph's deliver node (only for the same conversation - a nested turn elsewhere never takes it).
NEWS: contextvars.ContextVar = contextvars.ContextVar("turndeliver_news", default=None)
# G6: the live call that asked this run (voice.Call._delegate): {call, conv, origin, inbox, request} - the deliver
# node adds {key, result, facts, did, cards, live, left}. A nested turn in another conversation never takes it.
CALL: contextvars.ContextVar = contextvars.ContextVar("turndeliver_call", default=None)
DUE, HELD, SKIPPED = "due", "held", "skipped"

_ready_engine = None


class TurnDelivery(Base):
    __tablename__ = "turn_deliveries"
    key: Mapped[str] = mapped_column(String(200), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True, default="")
    conversation_id: Mapped[str] = mapped_column(String(64), index=True, default="")   # the TARGET chat
    thread: Mapped[str] = mapped_column(String(160), default="")
    kind: Mapped[str] = mapped_column(String(12), default="turn")          # turn | news | job
    job_key: Mapped[str] = mapped_column(String(160), index=True, default="")
    job_state: Mapped[str] = mapped_column(String(16), default="")
    outcome: Mapped[str] = mapped_column(String(16), default="")
    told_by: Mapped[str] = mapped_column(String(200), default="")          # job alias: the record that told it
    mark: Mapped[int] = mapped_column(Integer, default=0)                  # newest message id when it opened
    channels: Mapped[str] = mapped_column(Text, default="{}")              # JSON {channel: {state, at, ...}}
    created_at = mapped_column(DateTime(timezone=True), default=now)
    updated_at = mapped_column(DateTime(timezone=True), default=now, onupdate=now)


def ensure_table() -> None:
    """Self-heal (the v0.190.1 rule): a database born before this model gets the table on first use."""
    global _ready_engine
    from .. import db as _db
    eng = getattr(_db, "_engine", None)
    if eng is None or eng is _ready_engine:
        return
    TurnDelivery.__table__.create(eng, checkfirst=True)
    _ready_engine = eng


def graph_on() -> bool:
    try:
        from ..config import get_settings
        return bool(getattr(get_settings(), "chat_graph", False))
    except Exception:   # noqa: BLE001
        return False


def _chans(r: TurnDelivery | None) -> dict:
    if r is None:
        return {}
    try:
        v = json.loads(r.channels or "{}")
        return v if isinstance(v, dict) else {}
    except ValueError:
        return {}


def _view(r: TurnDelivery | None) -> dict | None:
    if r is None:
        return None
    return {"key": r.key, "tenant_id": r.tenant_id, "conversation_id": r.conversation_id, "thread": r.thread,
            "kind": r.kind, "job_key": r.job_key, "job_state": r.job_state, "outcome": r.outcome,
            "told_by": r.told_by, "mark": int(r.mark or 0), "channels": _chans(r)}


def max_msg_id(conversation_id: str) -> int:
    from ..db import Message
    try:
        with session() as s:
            return int(s.scalar(select(func.max(Message.id)).where(Message.conversation_id == conversation_id)) or 0)
    except Exception:   # noqa: BLE001
        log.exception("message mark failed")
        return 0


def record(key: str, tenant: str, conversation_id: str, thread: str = "", kind: str = "turn", job_key: str = "",
         job_state: str = "", outcome: str = "", mark: int | None = None) -> dict:
    """The record of one outcome (created once; a second open of the same key only fills what was empty)."""
    ensure_table()
    with session() as s:
        r = s.get(TurnDelivery, key)
        if r is None:
            r = TurnDelivery(key=key, tenant_id=tenant or "", conversation_id=conversation_id or "",
                             thread=(thread or "")[:160], kind=kind, job_key=(job_key or "")[:160],
                             job_state=job_state or "", outcome=outcome or "",
                             mark=int(mark if mark is not None else max_msg_id(conversation_id)), channels="{}")
            s.add(r)
            STATS["opened"] += 1
        else:
            if outcome:
                r.outcome = outcome
            if conversation_id and not r.conversation_id:
                r.conversation_id = conversation_id
            if job_key and not r.job_key:
                r.job_key, r.job_state = job_key[:160], job_state or r.job_state
        s.flush()
        return _view(r)


def get(key: str) -> dict | None:
    ensure_table()
    with session() as s:
        return _view(s.get(TurnDelivery, key))


def stamp(key: str, channel: str, state: str, **info) -> None:
    """One channel's state, read-modify-written in one transaction."""
    ensure_table()
    with session() as s:
        r = s.get(TurnDelivery, key)
        if r is None:
            return
        ch = _chans(r)
        ch[channel] = {**(ch.get(channel) or {}), **info, "state": state, "at": now().isoformat()}
        r.channels = json.dumps(ch, ensure_ascii=False, default=str)


def done(key: str, channel: str) -> bool:
    """This channel was sent - or started (intent) and maybe sent: either way it is never sent again."""
    rec = get(key)
    return bool(rec and (rec["channels"].get(channel) or {}).get("state") in (INTENT, SENT))


def once(key: str, channel: str, send) -> bool | None:
    """Send on this channel at most once: intent -> send -> sent. None = it was already sent (nothing done now)."""
    if done(key, channel):
        return None
    stamp(key, channel, INTENT)
    ok = False
    try:
        ok = bool(send())
    except Exception:   # noqa: BLE001 - a channel that fails never breaks the delivery of the others
        log.exception("delivery channel %s failed", channel)
    stamp(key, channel, SENT, ok=ok)
    STATS[channel] = STATS.get(channel, 0) + 1
    return ok


def final_row_since(conversation_id: str, mark: int, text: str = "") -> int | None:
    """The reply row a turn wrote after `mark`: an assistant row she was shown, in history, not a tool step - the one
    carrying the turn's final text when it is known, else the newest (a "(Kaam: ...)" receipt note is not the reply)."""
    from ..db import Message
    want = " ".join(str(text or "").split())
    fallback = None
    try:
        with session() as s:
            rows = s.scalars(select(Message).where(Message.conversation_id == conversation_id,
                                                   Message.role == "assistant", Message.in_history.is_(True),
                                                   Message.display.is_not(None), Message.id > int(mark or 0))
                             .order_by(Message.id.desc()).limit(40)).all()
            for m in rows:
                c = m.content
                if isinstance(c, list) and any(isinstance(b, dict) and b.get("type") == "tool_use" for b in c):
                    continue
                shown = " ".join(str(m.display or "").split())
                if want and shown == want:
                    return int(m.id)
                if fallback is None and not shown.startswith("(Kaam:"):
                    fallback = int(m.id)
    except Exception:   # noqa: BLE001
        log.exception("reply row lookup failed")
    return fallback


def write_chat(key: str, conversation_id: str, text: str) -> int | None:
    """The reply row + its stamp in ONE transaction (exactly once), then the SSE / push event. Used only when no step
    of the turn wrote it."""
    from ..db import Message
    from ..events import bus
    ensure_table()
    with session() as s:
        r = s.get(TurnDelivery, key)
        if r is None:
            return None
        ch = _chans(r)
        if (ch.get("chat") or {}).get("state") in (INTENT, SENT):
            return None
        m = Message(conversation_id=conversation_id, role="assistant", content=[{"type": "text", "text": text}],
                    display=text, in_history=True)
        s.add(m)
        s.flush()
        ch["chat"] = {"state": SENT, "at": now().isoformat(), "row": int(m.id), "by": "deliver"}
        r.channels = json.dumps(ch, ensure_ascii=False, default=str)
        row = int(m.id)
    bus.publish(conversation_id, "message", {"role": "assistant", "text": text, "source": "agent"})
    STATS["chat_node"] += 1
    return row


def job_told(job_key: str, job_state: str, by: str, tenant: str, conversation_id: str, since: float = 0.0) -> None:
    """The alias kaam_followup asks: this job's <state> was told by record `by` - the occurrence that happened between
    `since` (the telling run's start) and now. A job key that comes back later (a site built again) is a NEW occurrence:
    its report is queued after this alias was written, so the alias does not cover it."""
    if not job_key or not job_state:
        return
    import time as _t
    k = f"job:{job_key}:{job_state}"[:200]
    record(k, tenant, conversation_id, kind="job", job_key=job_key, job_state=job_state, outcome=job_state, mark=0)
    ensure_table()
    with session() as s:
        r = s.get(TurnDelivery, k)
        if r is not None:
            r.told_by, r.conversation_id = by[:200], conversation_id or r.conversation_id
            r.channels = json.dumps({"chat": {"state": SENT, "at": now().isoformat(), "by": by,
                                              "since": float(since or 0.0), "written": _t.time()}}, ensure_ascii=False)
    STATS["jobs_told"] += 1


def told(job_key: str, job_state: str, at: datetime | None = None) -> bool:
    """Was this job's result (this state) already told on the graph path? The record, never a reply-timing guess.
    `at` = when the report asking was queued: it must be the occurrence the alias covers (queued during the run that
    told it, before the alias was written)."""
    if not job_key or not job_state:
        return False
    rec = get(f"job:{job_key}:{job_state}"[:200])
    ch = (rec or {}).get("channels", {}).get("chat") or {}
    if ch.get("state") != SENT:
        return False
    if at is None:
        return True
    a = at if at.tzinfo else at.replace(tzinfo=timezone.utc)
    ts = a.timestamp()
    return float(ch.get("since") or 0.0) - 2.0 <= ts <= float(ch.get("written") or 0.0) + 2.0


def news_landed(key: str) -> dict | None:
    """kaam_followup after a restart: the wake turn of this report already wrote its reply (the record's chat stamp,
    or a reply row after the record's mark - row ids, not a time window). The record view, or None."""
    rec = get(key)
    if rec is None:
        return None
    if (rec["channels"].get("chat") or {}).get("state") == SENT:
        return rec
    row = final_row_since(rec["conversation_id"], rec["mark"])
    if row is not None:
        stamp(key, "chat", SENT, row=row, by="step (found after a restart)")
        STATS["news_recovered"] += 1
        return get(key)
    return None


def reply_text(row_id: int | None) -> str:
    from ..db import Message
    if not row_id:
        return ""
    try:
        with session() as s:
            m = s.get(Message, int(row_id))
            return str((m.display if m is not None else "") or "")
    except Exception:   # noqa: BLE001
        return ""


def news_channels(key: str, tenant: str, conversation_id: str, text: str, job_key: str, job_state: str,
                  title: str, settings) -> None:
    """The out-of-chat part of a result that is NEWS (a wake report, a job that ended in a background run): the quiet
    note into her live call(s) and the voice ring, each at most once, each by today's own helper and gates."""
    from .. import kaam_followup, kaamwatch

    def call():
        kaamwatch._voice(tenant, conversation_id, " ".join(str(text or "").split())[:700])
        return True

    def ring():
        kaam_followup._ring(conversation_id, job_key or key, job_state or "done", title or "", settings)
        return bool(getattr(settings, "voice_ring", False))

    if str(text or "").strip():
        once(key, "call", call)
    once(key, "ring", ring)


def call_live(conversation_id: str, attached: bool = True) -> bool:
    """G6: is a live call on this conversation (a call record / side record / the chat an old phone called on)?
    `attached` = only one whose phone is attached; False = registered at all (what push._heard_on_call's gate reads)."""
    try:
        import sys as _sys
        v = _sys.modules.get(__package__.rsplit(".", 1)[0] + ".voice")
        if v is None:
            return False
        for _loop, c in list((getattr(v, "ACTIVE", {}) or {}).get(conversation_id, []) or []):
            closed = getattr(c, "closed", None)
            if closed is not None and closed.is_set():
                continue
            if not attached or getattr(c, "ws", True) is not None:
                return True
    except Exception:   # noqa: BLE001
        log.debug("live call check failed", exc_info=True)
    return False


def fact_digest(facts: list | None) -> list[dict]:
    """G6: the run's G3 facts as the call needs them (what the spoken-claim check judges by)."""
    out = []
    for f in facts or []:
        if isinstance(f, dict) and f.get("tool"):
            out.append({"tool": str(f.get("tool")), "effect": str(f.get("effect") or ""),
                        "object": str(f.get("object") or "")[:120]})
    return out[-60:]


def target_chat(conversation_id: str, tenant: str) -> str:
    """v0.714: a turn's result lands in the turn's OWN chat (a call record's result in the chat behind it); a chat
    that is gone sends it to her pinned 'Hoola updates' chat - never to the chat she happens to have open."""
    from ..db import Conversation
    try:
        with session() as s:
            c = s.get(Conversation, conversation_id)
            alive = c is not None and not bool(getattr(c, "deleted", False))
        if alive:
            return conversation_id
        if tenant:
            from .. import convs
            return convs.updates_chat(tenant) or conversation_id
    except Exception:   # noqa: BLE001
        log.debug("target chat lookup failed", exc_info=True)
    return conversation_id


def ended_jobs(conversation_id: str, t0: float) -> list[dict]:
    """The jobs whose end this run's reply tells: a long job (kaam_plan goal) of this chat that ended during the run
    (finished, failed, or stopped by her Stop), and any other watched job that both STARTED and ended during it (the
    run ran it - v0.552: a job started earlier that merely finished while she asked something else is NOT told)."""
    out: list[dict] = []
    since = datetime.fromtimestamp(float(t0 or 0), timezone.utc) - timedelta(seconds=1)
    try:
        from . import goal as _goal
        with session() as s:
            for g in s.scalars(select(_goal.GoalRun).where(
                    _goal.GoalRun.conversation_id == conversation_id,
                    _goal.GoalRun.status.in_(("done", "failed", "stopped")),
                    _goal.GoalRun.updated_at >= since).limit(5)).all():
                out.append({"key": f"goal:{g.id}", "state": g.status, "title": (g.goal or "")[:200], "goal": g.id})
    except Exception:   # noqa: BLE001
        log.debug("ended goals lookup failed", exc_info=True)
    try:
        from ..kaamwatch import KaamJob
        with session() as s:
            for j in s.scalars(select(KaamJob).where(
                    KaamJob.conversation_id == conversation_id, KaamJob.state.in_(("done", "failed", "stopped")),
                    KaamJob.updated_at >= since, KaamJob.started_at >= since).limit(20)).all():
                if j.key.startswith("goal:") or any(o["key"] == j.key for o in out):
                    continue
                out.append({"key": j.key, "state": j.state, "title": (j.title or "")[:200]})
    except Exception:   # noqa: BLE001
        log.debug("ended jobs lookup failed", exc_info=True)
    return out


def forget_old(days: int = 7) -> int:
    ensure_table()
    with session() as s:
        res = s.execute(delete(TurnDelivery).where(TurnDelivery.created_at < now() - timedelta(days=days)))
        return int(getattr(res, "rowcount", 0) or 0)


def rows(conversation_id: str = "") -> list[dict]:
    """Tests / diagnostics."""
    ensure_table()
    with session() as s:
        q = select(TurnDelivery)
        if conversation_id:
            q = q.where(TurnDelivery.conversation_id == conversation_id)
        return [_view(r) for r in s.scalars(q.order_by(TurnDelivery.created_at)).all()]
