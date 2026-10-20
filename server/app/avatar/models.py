"""Imported by db.init_db so create_all makes the table."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, now


class Avatar(Base):
    __tablename__ = "avatars"
    tenant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(40), default="Santosh")
    gender: Mapped[str] = mapped_column(String(1), default="m")          # m | f (Hindi verb forms + voice)
    voice: Mapped[str] = mapped_column(String(40), default="")
    look: Mapped[str | None] = mapped_column(String(8), nullable=True)   # v0.48: f001..f100 (female 3D looks); none = Santosh
    setup_done: Mapped[bool] = mapped_column(Boolean, default=False)
    rules: Mapped[dict] = mapped_column(JSON, default=dict)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
