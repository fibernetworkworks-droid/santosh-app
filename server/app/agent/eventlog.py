"""v0.193 HARNESS-3, part 1: the event-sourced session log (the deepseek-harness study's foundation).

dsh runs its whole harness on one append-only session log: every turn, tool call, result, spawn and wake is an
event with a type and a payload, and everything else (replay, audit, "what did I just do", crash forensics) reads
from it. HOOLA already HAS half of this - the Event table carries the chat's story - but the agent's own actions
were never written as a machine-readable sequence, so "AI doesn't know what happened end to end" stayed half-true
and debugging a live turn meant reading pm2 logs.

This module is that log, at HOOLA's scale:

- `harness_events` rows: (id autoincrement, tenant, conversation, turn_id, actor, kind, payload JSON, ts).
- `log_event()` is BEST-EFFORT and NEVER raises (a broken log must never break a turn); after a write failure it
  silences itself for 60 s instead of spamming a dying DB (the v0.190.1 lesson the other way around).
- kinds (the HOOLA vocabulary, dsh-inspired): turn_started, turn_finished, turn_failed, tool_call, tool_result,
  agent_spawned, agent_finished, team_synthesized, wake, inbox, halted.
- `recent()` reads a chat's log newest-last; the `session_log` tool (registered in team.py) hands it to the BRAIN
  itself, so "tune kya kiya tha / pichhla turn dikhao" is answered from facts, not from memory; the console reads
  the same rows through GET /api/conversations/{id}/harness-events.
- Retention: `forget_old(days)` in a daily worker slot; per-chat rows are also capped so one noisy chat can never
  grow the table without bound.

The v0.190.1 P0 rule applied on day one: the model is imported by db.init_db AND ensure_table() self-heals the
table on the first write on old databases - a lazily-imported model never reaches create_all().
"""
from __future__ import annotations

import contextvars
import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import DateTime, Integer, String, Text, delete, func, select
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, now, session

log = logging.getLogger("santosh.eventlog")

# which turn / actor is logging right now (set by santosh._run_turn and by each sub-agent; read by the
# _run_tool instrumentation - a ContextVar so sub-agents log under their own name inside the same task chain)
CURRENT: contextvars.ContextVar[dict] = contextvars.ContextVar("hoola_harness_turn", default={})

STATS: dict[str, int] = {"written": 0, "failed": 0, "muted": 0, "trimmed": 0}
KINDS = ("turn_started", "turn_finished", "turn_failed", "tool_call", "tool_result",
         "agent_spawned", "agent_finished", "team_synthesized", "wake", "inbox", "halted")

# after a write failure, stay quiet for this long (a dying DB must not get one INSERT per tool step)
_MUTE_S = 60.0
_muted_until = 0.0
_table_ready = False

MAX_PER_CONV = 4000        # per-chat cap: the oldest rows go when a chat crosses this


def ensure_table() -> None:
    """v0.190.1 P0 self-heal: databases born before this model was registered with init_db have no
    harness_events table; the first event after deploy creates it in place - no manual SQL, no restore."""
    global _table_ready
    if _table_ready:
        return
    from .. import db as _db
    eng = getattr(_db, "_engine", None)
    if eng is not None:
        HarnessEvent.__table__.create(eng, checkfirst=True)
    _table_ready = True


class HarnessEvent(Base):
    __tablename__ = "harness_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    conversation_id: Mapped[str] = mapped_column(String(64), index=True)
    turn_id: Mapped[str] = mapped_column(String(40), default="", index=True)
    actor: Mapped[str] = mapped_column(String(40), default="")     # owner | wake | routine | team:<name>
    kind: Mapped[str] = mapped_column(String(24), index=True)
    payload: Mapped[str] = mapped_column(Text, default="{}")       # JSON, small by contract
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


def log_event(tenant: str, conversation_id: str, kind: str, payload: dict[str, Any] | None = None,
              turn_id: str = "", actor: str = "") -> None:
    """Append one event. Best-effort: never raises, self-mutes for 60 s after a failure."""
    global _muted_until
    if _muted_until and time.time() < _muted_until:
        return
    try:
        from ..config import get_settings
        if not getattr(get_settings(), "agent_event_log", True):
            return
        import json as _json
        ensure_table()
        with session() as s:
            s.add(HarnessEvent(tenant_id=(tenant or "")[:64], conversation_id=(conversation_id or "")[:64],
                               turn_id=(turn_id or "")[:40], actor=(actor or "")[:40], kind=kind[:24],
                               payload=_json.dumps(payload or {}, ensure_ascii=False, default=str)[:4000]))
            # per-chat cap: one noisy chat never grows the table without bound (cheap, indexed by conversation)
            n = s.scalar(select(func.count()).select_from(HarnessEvent)
                         .where(HarnessEvent.conversation_id == conversation_id)) or 0
            if n > MAX_PER_CONV:
                old = s.scalars(select(HarnessEvent.id).where(HarnessEvent.conversation_id == conversation_id)
                                .order_by(HarnessEvent.id).limit(n - MAX_PER_CONV)).all()
                if old:
                    s.execute(delete(HarnessEvent).where(HarnessEvent.id.in_(old)))
                    STATS["trimmed"] += len(old)
        STATS["written"] += 1
    except Exception:
        STATS["failed"] += 1
        STATS["muted"] += 1
        _muted_until = time.time() + _MUTE_S
        log.debug("event log write failed (muted %ss)", _MUTE_S, exc_info=True)


def _aware(d: datetime | None) -> datetime | None:
    if d is None:
        return None
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def recent(conversation_id: str, limit: int = 40, kinds: list[str] | None = None,
           turn_id: str = "") -> list[dict[str, Any]]:
    """A chat's log, OLDEST LAST (the way a story reads). `kinds` filters; `turn_id` narrows to one turn."""
    limit = max(1, min(int(limit or 40), 200))
    try:
        ensure_table()
        import json as _json
        with session() as s:
            q = select(HarnessEvent).where(HarnessEvent.conversation_id == conversation_id)
            if kinds:
                q = q.where(HarnessEvent.kind.in_([k[:24] for k in kinds]))
            if turn_id:
                q = q.where(HarnessEvent.turn_id == turn_id[:40])
            rows = s.scalars(q.order_by(HarnessEvent.id.desc()).limit(limit)).all()
            out = [{"id": r.id, "kind": r.kind, "actor": r.actor, "turn": r.turn_id,
                    "at": (_aware(r.created_at) or now()).isoformat(),
                    "payload": _json.loads(r.payload or "{}")} for r in reversed(rows)]
            return out
    except Exception:
        log.debug("event log read failed", exc_info=True)
        return []


def render(rows: list[dict[str, Any]]) -> str:
    """The human/brain-readable rendering of already-fetched rows: one line per event."""
    out = []
    for r in rows:
        p = r["payload"] or {}
        head = str(p.get("line") or p.get("tool") or p.get("agent") or p.get("why") or "")
        extra = ", ".join(f"{k}={str(p[k])[:80]}" for k in p if k not in ("line", "tool", "agent", "why")
                          and p[k] not in ("", None))[:220]
        out.append(f"- {r['at'][11:19]} [{r['actor'] or 'agent'}] {r['kind']}: {head}"
                   + (f" ({extra})" if extra else ""))
    return "\n".join(out)


def brief(conversation_id: str, limit: int = 30, kinds: list[str] | None = None) -> str:
    """The chat's log, rendered."""
    return render(recent(conversation_id, limit, kinds=kinds))


def forget_old(days: int = 14) -> int:
    """The daily sweep: rows older than `days` go (the log is a harness substrate, not an archive)."""
    try:
        ensure_table()
        cut = now() - timedelta(days=max(1, days))
        with session() as s:
            n = s.execute(delete(HarnessEvent).where(HarnessEvent.created_at < cut)).rowcount or 0
        return int(n)
    except Exception:
        log.debug("event log forget_old failed", exc_info=True)
        return 0


def stats() -> dict[str, Any]:
    import json as _json
    return {**STATS, "muted_now": bool(_muted_until and time.time() < _muted_until),
            "kinds": list(KINDS)}
