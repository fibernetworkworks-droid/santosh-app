"""v0.777 CHAT JAISA - what one chat turn cost, in rupees, from the server's own meter (L1 of docs/LOVABLE_STUDIO_PLAN.md).

`santosh.run_turn` runs every turn inside `usage.turn_meter()`: each model call the turn makes (and the work it starts in
the same context) adds its USD to that turn's own dict. At the end of the turn ONE row is written here: when it started /
ended, the calls and the USD; `recent()` gives the rows of a conversation with rupees (`usage_usd_inr`), newest last.

The Web Studio shows it as "Worked for 42s · 5 steps · Rs 3.10" above the answer. Rupees are list price x the server's
rate - an honest estimate, not an invoice. A turn that made no model call writes no row. The table is registered in
`db.init_db` AND self-heals with `ensure_table()` (the v0.190.1 rule). Old rows are trimmed to the newest 400 per chat."""
from __future__ import annotations

import logging
from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, delete, select
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base, new_id, now, session

log = logging.getLogger("santosh.turncost")
KEEP = 400
_ready_engine = None


class TurnCost(Base):
    __tablename__ = "turn_costs"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("tc"))
    tenant_id: Mapped[str] = mapped_column(String(80), index=True, default="")
    conversation_id: Mapped[str] = mapped_column(String(80), index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    ended_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    calls: Mapped[int] = mapped_column(Integer, default=0)
    usd: Mapped[float] = mapped_column(Float, default=0.0)


def ensure_table() -> None:
    global _ready_engine
    from . import db as _db
    eng = getattr(_db, "_engine", None)
    if eng is None or eng is _ready_engine:
        return
    TurnCost.__table__.create(eng, checkfirst=True)
    _ready_engine = eng


def record(tenant: str | None, conversation_id: str, started: datetime, acc: dict | None) -> None:
    """One row for a finished turn (never raises - counting must never break a reply)."""
    try:
        if not conversation_id or not acc or not int(acc.get("calls") or 0):
            return
        ensure_table()
        with session() as s:
            s.add(TurnCost(tenant_id=tenant or "", conversation_id=conversation_id, started_at=started, ended_at=now(),
                           calls=int(acc.get("calls") or 0), usd=round(float(acc.get("usd") or 0.0), 6)))
            ids = s.scalars(select(TurnCost.id).where(TurnCost.conversation_id == conversation_id)
                            .order_by(TurnCost.ended_at.desc()).offset(KEEP)).all()
            if ids:
                s.execute(delete(TurnCost).where(TurnCost.id.in_(ids)))
            s.commit()
    except Exception:
        log.exception("turn cost not recorded")


def _iso(d: datetime | None) -> str:
    return d.replace(microsecond=0).isoformat() if d else ""


def recent(conversation_id: str, limit: int = 60) -> list[dict]:
    from .config import get_settings
    rate = float(getattr(get_settings(), "usage_usd_inr", 88.0) or 88.0)
    ensure_table()
    with session() as s:
        rows = s.scalars(select(TurnCost).where(TurnCost.conversation_id == conversation_id)
                         .order_by(TurnCost.ended_at.desc()).limit(max(1, min(int(limit or 60), 200)))).all()
        out = [{"start": _iso(r.started_at), "end": _iso(r.ended_at), "calls": r.calls, "usd": round(r.usd, 6),
                "inr": round(r.usd * rate, 4)} for r in rows]
    return list(reversed(out))
