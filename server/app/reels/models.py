from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String, Text
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
