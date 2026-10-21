from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now


class VideoJob(Base):
    """One editing job: the owner's sources + her brief -> versions of the finished video."""
    __tablename__ = "video_jobs"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("vj"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    conversation_id: Mapped[str] = mapped_column(String(64), default="")
    status: Mapped[str] = mapped_column(String(20), default="queued")   # queued watching planning rendering checking done failed cancelled
    stage_note: Mapped[str] = mapped_column(String(200), default="")
    progress: Mapped[int] = mapped_column(Integer, default=0)
    brief: Mapped[str] = mapped_column(Text, default="")
    options: Mapped[str] = mapped_column(Text, default="{}")          # platform, length_s, captions, logo / music file ids, title
    sources: Mapped[str] = mapped_column(Text, default="[]")          # [{"file_id", "name", "key"}]
    analysis: Mapped[str] = mapped_column(Text, default="{}")         # per source: probe, scenes, speech, transcript, highlights
    timeline: Mapped[str] = mapped_column(Text, default="")           # the current vedit timeline (JSON)
    plan: Mapped[str] = mapped_column(Text, default="{}")             # title, post_caption, hashtags, notes, thumbnail_time
    versions: Mapped[str] = mapped_column(Text, default="[]")         # [{"n", "file_id", "url", "thumb", "report", "check", "change"}]
    pending: Mapped[str] = mapped_column(Text, default="")            # a change waiting to be made ("revise")
    error: Mapped[str] = mapped_column(Text, default="")
    created_by: Mapped[str] = mapped_column(String(64), default="owner")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
