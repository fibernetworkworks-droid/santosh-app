"""v0.191 HARNESS-2, part 3: the durable accepted-message inbox.

The study's lesson about HOOLA's 202: POST /messages returns "accepted" and the turn runs as a Fire-and-forget
FastAPI BackgroundTask - a pm2 restart (deploy, crash, OOM) between the 202 and the reply silently ate her
message. She stared at a chat that never answered. dsh solves the same with a durable, event-sourced session
log; HOOLA's own scale needs only one table:

- `accept()` inserts the accepted message BEFORE the 202 goes out (committed, so a restart cannot unwrite it).
- The background task is `run_owned()`: accepted -> running -> done/failed around the normal run_turn.
- The worker slot `sweep()` (every ~15 s) finds rows that outlived their task:
    * accepted but never started for TURN_INBOX_STALE_S  -> the task died before it ran;
    * running but its lock is free for 5 minutes         -> the process died mid-turn (a LIVE turn always holds
      the conversation lock, so a running row with a free lock is dead by definition);
  and re-runs each once (tries cap 2), idempotently:
    * an in_history assistant reply created after acceptance = the turn really answered -> mark done, skip;
    * the re-run passes save_user=False when her message row already exists, so history never doubles;
  and marks stale done rows gone after a day.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import DateTime, Integer, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column

from .config import get_settings
from .db import Base, new_id, now, session

log = logging.getLogger("santosh.turn_inbox")

_BG: set = set()
STATS: dict[str, int] = {"accepted": 0, "done": 0, "rerun": 0, "skipped_answered": 0}
_table_ready = False


def ensure_table() -> None:
    """v0.190.1 P0 self-heal (the live lesson): a database born before this model was registered with init_db
    has no turn_inbox table (create_all never saw it), and every query would die 'no such table'. The first
    accept / sweep after deploy creates it in place - no manual SQL, no restore."""
    global _table_ready
    if _table_ready:
        return
    from . import db as _db
    eng = getattr(_db, "_engine", None)
    if eng is not None:
        TurnInbox.__table__.create(eng, checkfirst=True)
    _table_ready = True


class TurnInbox(Base):
    __tablename__ = "turn_inbox"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("ti"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    conversation_id: Mapped[str] = mapped_column(String(64), index=True)
    client_id: Mapped[str] = mapped_column(String(80), default="")
    text: Mapped[str] = mapped_column(Text, default="")
    voice: Mapped[int] = mapped_column(Integer, default=0)
    context: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(12), default="accepted", index=True)
    tries: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)


def _aware(d: datetime | None) -> datetime | None:
    if d is None:
        return None
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def accept(tenant: str, conversation_id: str, text: str, voice: bool, context: str, client_id: str) -> str | None:
    """Persist the accepted message BEFORE the 202. None = feature off / failed (the old fire-and-forget path)."""
    st = get_settings()
    if not getattr(st, "agent_turn_inbox", True):
        return None
    try:
        from .agent import eventlog
        eventlog.log_event(tenant, conversation_id, "inbox", {"line": "accepted (turn saved before the 202)"})
        ensure_table()
        with session() as s:
            row = TurnInbox(tenant_id=tenant, conversation_id=conversation_id, client_id=(client_id or "")[:80],
                            text=text or "", voice=1 if voice else 0, context=context or "")
            s.add(row)
            s.flush()
            STATS["accepted"] += 1
            return row.id
    except Exception:
        log.exception("turn inbox accept failed (the turn still runs the old way)")
        return None


def mark(inbox_id: str | None, status: str) -> None:
    if not inbox_id:
        return
    try:
        with session() as s:
            r = s.get(TurnInbox, inbox_id)
            if r is not None:
                r.status = status
                r.updated_at = now()
    except Exception:
        log.exception("turn inbox mark %s failed", status)


async def run_owned(inbox_id: str | None, conversation_id: str, text: str, tenant: str, voice: bool,
                    context: str = "", client_id: str = "", save_user: bool = True) -> str:
    """The background task: the normal turn, wrapped in the inbox states. Used by the endpoint (fresh) and by
    the sweep's re-run (save_user decided there)."""
    from .agent import run_turn
    mark(inbox_id, "running")
    try:
        out = await run_turn(conversation_id, text, tenant, voice, context=context, client_id=client_id,
                             save_user=save_user)
        mark(inbox_id, "done")
        STATS["done"] += 1
        return out
    except asyncio.CancelledError:
        raise
    except Exception:
        mark(inbox_id, "failed")
        raise


def _answered_since(conversation_id: str, since: datetime) -> bool:
    """A real (in_history) assistant reply after `since` = the turn already answered; never re-run it."""
    try:
        from .db import Message
        with session() as s:
            row = s.scalars(select(Message.id).where(Message.conversation_id == conversation_id,
                                                     Message.role == "assistant",
                                                     Message.in_history.is_(True),
                                                     Message.created_at >= since).limit(1)).first()
        return row is not None
    except Exception:
        return False


def _user_row_since(conversation_id: str, since: datetime) -> bool:
    try:
        from .db import Message
        with session() as s:
            row = s.scalars(select(Message.id).where(Message.conversation_id == conversation_id,
                                                     Message.role == "user",
                                                     Message.created_at >= since).limit(1)).first()
        return row is not None
    except Exception:
        return False


async def sweep() -> int:
    """The worker slot: re-run dead turns once, mark answered ones done, forget old done rows."""
    st = get_settings()
    if not getattr(st, "agent_turn_inbox", True):
        return 0
    out = 0
    try:
        ensure_table()
        acc_cut = now() - timedelta(seconds=int(getattr(st, "turn_inbox_stale_s", 120) or 120))
        run_cut = now() - timedelta(seconds=300)
        with session() as s:
            rows = s.scalars(select(TurnInbox).where(
                TurnInbox.status == "accepted", TurnInbox.created_at < acc_cut, TurnInbox.tries < 2
            ).order_by(TurnInbox.created_at).limit(5)).all()
            rows += s.scalars(select(TurnInbox).where(
                TurnInbox.status == "running", TurnInbox.updated_at < run_cut, TurnInbox.tries < 2
            ).order_by(TurnInbox.updated_at).limit(5)).all()
            rows = [dict(id=r.id, tenant_id=r.tenant_id, conversation_id=r.conversation_id, client_id=r.client_id,
                         text=r.text, voice=bool(r.voice), context=r.context, tries=r.tries,
                         created_at=_aware(r.created_at) or now()) for r in rows]
        from .agent import santosh
        for r in rows:
            conv = r["conversation_id"]
            if not conv or santosh.turn_running(conv):
                continue                       # a live turn (maybe queued behind her previous one) owns this chat
            if _answered_since(conv, r["created_at"]):
                mark(r["id"], "done")
                STATS["skipped_answered"] += 1
                continue
            save_user = not _user_row_since(conv, r["created_at"])
            from .agent import eventlog
            eventlog.log_event(r["tenant_id"], conv, "inbox",
                               {"line": f"re-running dead turn (tries {r['tries'] + 1}, save_user={save_user})"})
            with session() as s:
                row = s.get(TurnInbox, r["id"])
                if row is None or row.status not in ("accepted", "running"):
                    continue
                row.status, row.tries, row.updated_at = "running", row.tries + 1, now()
            STATS["rerun"] += 1
            out += 1
            log.warning("turn inbox: re-running dead turn %s (conv %s, tries %s, save_user=%s)",
                        r["id"], conv, r["tries"] + 1, save_user)
            t = asyncio.ensure_future(run_owned(r["id"], conv, r["text"], r["tenant_id"], r["voice"],
                                                context=r["context"], client_id=r["client_id"],
                                                save_user=save_user))
            _BG.add(t)
            t.add_done_callback(_BG.discard)
        if out == 0:   # light housekeeping on the quiet pass
            with session() as s:
                for r in s.scalars(select(TurnInbox).where(
                        TurnInbox.status.in_(("done", "failed", "skipped")),
                        TurnInbox.updated_at < now() - timedelta(days=1)).limit(200)).all():
                    s.delete(r)
    except Exception:
        log.exception("turn inbox sweep failed")
    return out


def pending(tenant: str) -> list[dict[str, Any]]:
    """Diagnostics: the inbox right now."""
    with session() as s:
        rows = s.scalars(select(TurnInbox).where(TurnInbox.tenant_id == tenant,
                                                 TurnInbox.status.in_(("accepted", "running")))
                         .order_by(TurnInbox.created_at).limit(20)).all()
        return [{"id": r.id, "conversation_id": r.conversation_id, "status": r.status, "tries": r.tries,
                 "created_at": (_aware(r.created_at) or now()).isoformat()} for r in rows]
