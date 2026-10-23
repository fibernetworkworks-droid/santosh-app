"""v0.128 App Sahayak tables."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now


class AppProject(Base):
    __tablename__ = "app_projects"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("app"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(16), default="")            # A-0001
    name: Mapped[str] = mapped_column(String(160), default="")             # the app's name (her business)
    brief: Mapped[str] = mapped_column(Text, default="")                   # her words
    field: Mapped[str] = mapped_column(String(60), default="")
    goal: Mapped[str] = mapped_column(String(20), default="")
    style: Mapped[str] = mapped_column(String(30), default="")
    styles: Mapped[str] = mapped_column(Text, default="[]")                # the 3 looks offered
    language: Mapped[str] = mapped_column(String(12), default="en")
    facts: Mapped[str] = mapped_column(Text, default="{}")
    answers: Mapped[str] = mapped_column(Text, default="{}")
    plan: Mapped[str] = mapped_column(Text, default="{}")                  # screens, tabs, flow, code screens, rules
    looks: Mapped[str] = mapped_column(Text, default="[]")
    look: Mapped[str] = mapped_column(Text, default="{}")                  # chosen tokens
    status: Mapped[str] = mapped_column(String(16), default="draft")
    # draft | planned (her Haan) | looks (her choice) | designing | checking | ready (her 'Design pakka') | approved | failed | stopped
    stage: Mapped[str] = mapped_column(String(20), default="brief")
    board: Mapped[str] = mapped_column(Text, default="{}")
    version: Mapped[int] = mapped_column(Integer, default=0)
    versions: Mapped[str] = mapped_column(Text, default="[]")              # [{version, note, at, passed, screens}]
    checks: Mapped[str] = mapped_column(Text, default="{}")
    preview_token: Mapped[str] = mapped_column(String(64), default="")
    stop: Mapped[bool] = mapped_column(Boolean, default=False)
    queued: Mapped[str] = mapped_column(Text, default="[]")
    error: Mapped[str] = mapped_column(Text, default="")
    approved_hash: Mapped[str] = mapped_column(String(40), default="")     # her 'Design pakka' tap (hash of the design)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    conv: Mapped[str] = mapped_column(String(64), default="")
    android: Mapped[str | None] = mapped_column(Text, nullable=True)   # v0.132 native build state (JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class AppLibStat(Base):
    """Library learning: counts only (field, kind, key), never anyone's words."""
    __tablename__ = "app_lib_stats"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    field: Mapped[str] = mapped_column(String(60), index=True)
    kind: Mapped[str] = mapped_column(String(12))
    key: Mapped[str] = mapped_column(String(60))
    count: Mapped[int] = mapped_column(Integer, default=0)
