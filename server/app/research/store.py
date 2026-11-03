"""v0.475 R4 LAMBA KAAM - the persisted research run (table `research_runs`).

One row per background run: the question and approved goals, the policy overrides, the status, the CHECKPOINT (everything the
engine needs to carry on after a restart: the goals already finished with their notes / calcs / pages, the links admitted, the page
texts kept for the final checks, the counts and the clock already used), the progress line, and at the end the DOSSIER. The table is
a lazily imported model module: registered in `db.init_db` and self-healing through `ensure_table()`."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime, Integer, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now, session


class ResearchRun(Base):
    __tablename__ = "research_runs"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("rr"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    conversation_id: Mapped[str] = mapped_column(String(64), index=True, default="")
    question: Mapped[str] = mapped_column(Text, default="")
    goals: Mapped[str] = mapped_column(Text, default="[]")
    policy: Mapped[str] = mapped_column(Text, default="{}")          # {"over": {...}, "hi": bool, "asked": [...]}
    status: Mapped[str] = mapped_column(String(12), default="queued", index=True)   # queued|running|done|failed|stopped
    tries: Mapped[int] = mapped_column(Integer, default=0)
    checkpoint: Mapped[str] = mapped_column(Text, default="")
    progress: Mapped[str] = mapped_column(Text, default="{}")
    dossier: Mapped[str] = mapped_column(Text, default="")
    error: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)


_ready = False


def ensure_table() -> None:
    global _ready
    if _ready:
        return
    from .. import db as _db
    eng = getattr(_db, "_engine", None)
    if eng is not None:
        ResearchRun.__table__.create(eng, checkfirst=True)
    _ready = True


def aware(d: datetime | None) -> datetime | None:
    if d is None:
        return None
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def _j(s: str, default: Any) -> Any:
    try:
        return json.loads(s) if s else default
    except ValueError:
        return default


def create(tenant: str, conv: str, question: str, goals: list[str], policy: dict) -> str:
    ensure_table()
    with session() as s:
        row = ResearchRun(tenant_id=tenant, conversation_id=conv, question=question[:3000],
                          goals=json.dumps(goals, ensure_ascii=False), policy=json.dumps(policy, ensure_ascii=False))
        s.add(row)
        s.flush()
        return row.id


def view(row: ResearchRun) -> dict[str, Any]:
    return {"id": row.id, "tenant": row.tenant_id, "conv": row.conversation_id, "question": row.question,
            "goals": _j(row.goals, []), "policy": _j(row.policy, {}), "status": row.status, "tries": row.tries,
            "checkpoint": _j(row.checkpoint, None), "progress": _j(row.progress, {}), "error": row.error,
            "dossier": _j(row.dossier, None), "updated_at": aware(row.updated_at), "created_at": aware(row.created_at)}


def get(run_id: str) -> dict[str, Any] | None:
    ensure_table()
    with session() as s:
        row = s.get(ResearchRun, run_id)
        return view(row) if row is not None else None


def set_status(run_id: str, status: str, error: str = "", only_from: tuple[str, ...] | None = None) -> bool:
    ensure_table()
    with session() as s:
        row = s.get(ResearchRun, run_id)
        if row is None or (only_from is not None and row.status not in only_from):
            return False
        row.status, row.updated_at = status, now()
        if error:
            row.error = error[:600]
        return True


def save_checkpoint(run_id: str, cp: dict, progress: dict | None = None) -> None:
    with session() as s:
        row = s.get(ResearchRun, run_id)
        if row is not None and row.status in ("queued", "running"):
            row.checkpoint = json.dumps(cp, ensure_ascii=False, default=str)
            if progress is not None:
                row.progress = json.dumps(progress, ensure_ascii=False)
            row.updated_at = now()


def touch(run_id: str, progress: dict | None = None) -> None:
    with session() as s:
        row = s.get(ResearchRun, run_id)
        if row is not None and row.status in ("queued", "running"):
            if progress is not None:
                row.progress = json.dumps(progress, ensure_ascii=False)
            row.updated_at = now()


def finish(run_id: str, status: str, dossier: dict | None, error: str = "") -> bool:
    """Close a run. A run she stopped stays stopped (the stop already went out)."""
    with session() as s:
        row = s.get(ResearchRun, run_id)
        if row is None or row.status == "stopped":
            return False
        row.status, row.error, row.updated_at = status, error[:600], now()
        if dossier is not None:
            row.dossier = json.dumps(dossier, ensure_ascii=False, default=str)
        row.checkpoint = ""                       # the dossier is the result; the checkpoint is no longer needed
        return True


def recent(tenant: str, conv: str = "", limit: int = 8) -> list[dict[str, Any]]:
    ensure_table()
    with session() as s:
        q = select(ResearchRun).where(ResearchRun.tenant_id == tenant)
        if conv:
            q = q.where(ResearchRun.conversation_id == conv)
        return [view(r) for r in s.scalars(q.order_by(ResearchRun.created_at.desc()).limit(limit)).all()]


def candidates(stale_before: datetime, per_tenant_running_max: int, tries_max: int) -> list[str]:
    """Run ids to start now: queued ones (within each tenant's running cap) and running ones that stopped heartbeating."""
    ensure_table()
    out: list[str] = []
    with session() as s:
        running: dict[str, int] = {}
        for r in s.scalars(select(ResearchRun).where(ResearchRun.status == "running")).all():
            running[r.tenant_id] = running.get(r.tenant_id, 0) + 1
            u = aware(r.updated_at)
            if u is not None and u < stale_before and r.tries < tries_max:
                out.append(r.id)
        for r in s.scalars(select(ResearchRun).where(ResearchRun.status == "queued").order_by(ResearchRun.created_at).limit(8)).all():
            if running.get(r.tenant_id, 0) < per_tenant_running_max:
                running[r.tenant_id] = running.get(r.tenant_id, 0) + 1
                out.append(r.id)
        for r in s.scalars(select(ResearchRun).where(ResearchRun.status == "running")).all():   # out of tries: give up, say so
            u = aware(r.updated_at)
            if u is not None and u < stale_before and r.tries >= tries_max:
                r.status, r.error, r.updated_at = "failed", "the run stopped moving and was restarted too many times", now()
    return out


def forget_old(days: int = 14) -> int:
    from datetime import timedelta
    ensure_table()
    n = 0
    with session() as s:
        for r in s.scalars(select(ResearchRun).where(ResearchRun.status.in_(("done", "failed", "stopped")),
                                                     ResearchRun.updated_at < now() - timedelta(days=days)).limit(200)).all():
            s.delete(r)
            n += 1
    return n
