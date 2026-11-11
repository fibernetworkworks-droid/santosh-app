"""v0.814 one row per App Engine app (the files live on disk under data/appengine/<tenant>/<id>/)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now

_ready_engine = None


class AppProject(Base):
    __tablename__ = "ae_projects"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("ae"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[int] = mapped_column(Integer, default=1)
    name: Mapped[str] = mapped_column(String(120), default="My app")
    slug: Mapped[str] = mapped_column(String(80), index=True, unique=True)
    brief: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(16), default="new")       # new | ready | building | failed
    version: Mapped[int] = mapped_column(Integer, default=0)             # newest built version
    live_version: Mapped[int] = mapped_column(Integer, default=0)
    dirty: Mapped[bool] = mapped_column(Boolean, default=True)           # source changed since the last build
    look: Mapped[str] = mapped_column(Text, default="{}")                # the token values (tokens.resolve input)
    preview_token: Mapped[str] = mapped_column(String(64), index=True, default="")
    conversation_id: Mapped[str] = mapped_column(String(64), default="")
    last_build: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    published_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


def ensure_table() -> None:
    """Registered in db.init_db AND self-heals (the v0.190.1 rule)."""
    global _ready_engine
    from .. import db as _db
    eng = getattr(_db, "_engine", None)
    if eng is None or eng is _ready_engine:
        return
    AppProject.__table__.create(eng, checkfirst=True)
    _ready_engine = eng
