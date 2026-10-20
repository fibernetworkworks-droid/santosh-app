from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now


class ReelLook(Base):
    """What Hoola understood from one reel. Public YouTube reels are shared by everyone (key = platform + id), so a
    viral reel is understood once; an owner's own video file is keyed per owner and never shared."""
    __tablename__ = "reel_looks"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("reel"))
    key: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    tenant_id: Mapped[str] = mapped_column(String(64), default="")       # "" = public (shared cache)
    platform: Mapped[str] = mapped_column(String(20), default="")
    url: Mapped[str] = mapped_column(Text, default="")
    data: Mapped[str] = mapped_column(Text, default="{}")                # JSON
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class SavedReel(Base):
    """A reel the owner kept (Reel memory): searchable later by voice or in the app."""
    __tablename__ = "saved_reels"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("srl"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    look_id: Mapped[str] = mapped_column(String(40), index=True)
    note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class ScrollDay(Base):
    """One day of the owner's time in reel apps (from Android Usage Access): numbers only, no content."""
    __tablename__ = "scroll_days"
    __table_args__ = (UniqueConstraint("tenant_id", "day", name="uq_scroll_day"),)
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("scd"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    day: Mapped[str] = mapped_column(String(10))                         # 2026-10-20 (phone's local date)
    data: Mapped[str] = mapped_column(Text, default="{}")                # {"apps": {...}, "hours": [24]}
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class ScrollTaste(Base):
    """What the owner watches, from their own official history download (Instagram / YouTube). Only the summary is
    kept: topics, top creators, time pattern. The uploaded history itself is never stored."""
    __tablename__ = "scroll_tastes"
    __table_args__ = (UniqueConstraint("tenant_id", "source", name="uq_scroll_taste"),)
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("sct"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    source: Mapped[str] = mapped_column(String(20))                      # instagram | youtube
    data: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class ScrollSettings(Base):
    __tablename__ = "scroll_settings"
    tenant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    budget_min: Mapped[int] = mapped_column(Integer, default=0)          # 0 = no daily limit set
