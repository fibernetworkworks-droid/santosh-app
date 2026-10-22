"""v0.98 Call rating: after a call she taps 👍 / 👎 (+ what went wrong), so voice quality is measured by her, not guessed.

Stored per call (counts and her chosen reasons only, no audio or words) and summed into `GET /api/voice/stats`
(`ratings`: good %, top reasons) next to the machine numbers (reply start, interruptions...), so every voice change can
be judged by both.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import Boolean, DateTime, Integer, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base, new_id, now, session

REASONS = {
    "cut_off": "Beech mein kaat diya",
    "slow": "Jawab der se aaya",
    "misheard": "Galat samjha",
    "audio": "Awaaz saaf nahi thi",
    "not_done": "Kaam nahi hua",
    "too_long": "Bahut lamba bola",
    "robotic": "Machine jaisa laga",
}


class CallRating(Base):
    __tablename__ = "call_ratings"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("cr"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    call_id: Mapped[str] = mapped_column(String(64), index=True)
    good: Mapped[bool] = mapped_column(Boolean)
    reasons: Mapped[str] = mapped_column(Text, default="")
    seconds: Mapped[int] = mapped_column(Integer, default=0)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


def rate(tenant: str, call_id: str, good: bool, reasons: list[str] | None = None, seconds: int = 0) -> dict[str, Any]:
    rs = [r for r in (reasons or []) if r in REASONS][:5] if not good else []
    with session() as s:
        row = s.scalars(select(CallRating).where(CallRating.tenant_id == tenant, CallRating.call_id == call_id)).first()
        if row is None:
            row = CallRating(tenant_id=tenant, call_id=str(call_id)[:64], good=bool(good))
            s.add(row)
        row.good, row.reasons, row.seconds = bool(good), ",".join(rs), int(seconds or 0)
    try:      # the in-memory call stats get it too, for /api/voice/stats right away
        from . import voice
        for st in reversed(voice.STATS):
            if st.get("call_id") == call_id:
                st["rating"] = {"good": bool(good), "reasons": rs}
                break
    except Exception:
        pass
    return {"ok": True, "good": bool(good), "reasons": [REASONS[r] for r in rs],
            "say": "Shukriya! Isse calls behtar banengi." if good else "Shukriya, yeh theek karne mein madad karega."}


def summary(tenant: str | None = None, days: int = 30) -> dict[str, Any]:
    since = datetime.now(timezone.utc) - timedelta(days=max(1, int(days)))
    with session() as s:
        q = select(CallRating).where(CallRating.at >= since)
        if tenant:
            q = q.where(CallRating.tenant_id == tenant)
        rows = s.scalars(q).all()
        data = [(r.good, r.reasons) for r in rows]
    n = len(data)
    good = sum(1 for g, _ in data if g)
    counts: dict[str, int] = {}
    for g, rs in data:
        if not g:
            for r in (rs or "").split(","):
                if r:
                    counts[r] = counts.get(r, 0) + 1
    top = sorted(counts.items(), key=lambda x: -x[1])[:5]
    return {"rated_calls": n, "good_pct": round(100 * good / n, 1) if n else None,
            "top_reasons": [{"reason": r, "label": REASONS.get(r, r), "calls": c} for r, c in top]}
