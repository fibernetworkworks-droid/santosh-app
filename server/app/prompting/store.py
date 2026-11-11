"""Her saved prompts (plan P3: Save). One row per saved brief; versions and scheduled runs are plan P7."""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, as_utc, new_id, now, session

MAX_SAVED = 200


class PromptSaved(Base):
    __tablename__ = "prompt_saved"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    title: Mapped[str] = mapped_column(String(160), default="")
    section: Mapped[str] = mapped_column(String(20), default="")
    brief: Mapped[str] = mapped_column(Text, default="{}")
    prompt: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


_OK: set[int] = set()


def ensure_table() -> None:
    """Self-heal, keyed on the engine (a fresh test database is a new engine)."""
    from .. import db as _db
    eng = getattr(_db, "_engine", None)
    if eng is not None and id(eng) not in _OK:
        PromptSaved.__table__.create(eng, checkfirst=True)
        _OK.add(id(eng))


def _view(r: PromptSaved, full: bool = False) -> dict[str, Any]:
    out = {"id": r.id, "title": r.title, "section": r.section, "prompt": r.prompt if full else r.prompt[:200],
           "updated_at": as_utc(r.updated_at).isoformat() if r.updated_at else None}
    if full:
        try:
            out["brief"] = json.loads(r.brief or "{}")
        except ValueError:
            out["brief"] = {}
    return out


def save(tenant: str, brief: dict[str, Any], prompt: str, title: str = "", pid: str = "") -> dict[str, Any]:
    ensure_table()
    title = (title or brief.get("intent") or "Prompt").strip()[:160]
    with session() as s:
        r = s.get(PromptSaved, pid) if pid else None
        if r is not None and r.tenant_id != tenant:
            r = None
        if r is None:
            n = len(s.execute(select(PromptSaved.id).where(PromptSaved.tenant_id == tenant)).all())
            if n >= MAX_SAVED:
                raise ValueError(f"You have {MAX_SAVED} saved prompts. Delete one you no longer use first.")
            r = PromptSaved(id=new_id("pr"), tenant_id=tenant)
            s.add(r)
        r.title, r.section = title, str(brief.get("section") or "")[:20]
        r.brief, r.prompt, r.updated_at = json.dumps(brief, ensure_ascii=False), str(prompt or "")[:6000], now()
        s.flush()
        return _view(r, full=True)


def listing(tenant: str, section: str = "") -> list[dict[str, Any]]:
    ensure_table()
    with session() as s:
        q = select(PromptSaved).where(PromptSaved.tenant_id == tenant).order_by(PromptSaved.updated_at.desc()).limit(MAX_SAVED)
        return [_view(r) for r in s.execute(q).scalars() if not section or r.section == section]


def get(tenant: str, pid: str) -> dict[str, Any] | None:
    ensure_table()
    with session() as s:
        r = s.get(PromptSaved, pid)
        return _view(r, full=True) if r is not None and r.tenant_id == tenant else None


def delete(tenant: str, pid: str) -> bool:
    ensure_table()
    with session() as s:
        r = s.get(PromptSaved, pid)
        if r is None or r.tenant_id != tenant:
            return False
        s.delete(r)
        return True
