from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now


class MotionVideo(Base):
    """One Hoola Motion video: what it shows (template + data, or Hoola's own code), and the rendered MP4."""
    __tablename__ = "motion_videos"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("mv"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    conversation_id: Mapped[str] = mapped_column(String(40), default="")
    kind: Mapped[str] = mapped_column(String(20))                       # explainer | recipe | logo | offer | custom
    title: Mapped[str] = mapped_column(String(200), default="")
    aspect: Mapped[str] = mapped_column(String(8), default="9:16")
    music: Mapped[str] = mapped_column(String(12), default="upbeat")
    data: Mapped[str] = mapped_column(Text, default="{}")
    html: Mapped[str] = mapped_column(Text, default="")                  # custom kind only
    status: Mapped[str] = mapped_column(String(12), default="queued")   # queued | rendering | done | failed
    progress: Mapped[float] = mapped_column(Float, default=0.0)
    error: Mapped[str] = mapped_column(Text, default="")
    path: Mapped[str] = mapped_column(Text, default="")
    thumb: Mapped[str] = mapped_column(Text, default="")
    size: Mapped[int] = mapped_column(Integer, default=0)
    duration: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
