"""Tables for Santosh YouTube. Imported by db.init_db so create_all makes them."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now


class YouTubeAccount(Base):
    """A Google account the user connected for YouTube (their channel). Tokens stored encrypted."""
    __tablename__ = "youtube_accounts"
    __table_args__ = (UniqueConstraint("tenant_id", "address", name="uq_youtube_account"),)
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("gyt"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    address: Mapped[str] = mapped_column(String(320))
    channel_id: Mapped[str] = mapped_column(String(64), default="")
    channel_title: Mapped[str] = mapped_column(String(200), default="")
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    access_token_enc: Mapped[str | None] = mapped_column(Text, nullable=True)
    refresh_token_enc: Mapped[str | None] = mapped_column(Text, nullable=True)
    expiry: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(12), default="ok")
    last_error: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class YouTubePending(Base):
    """A change the public will see (comment reply, video edit, upload). Runs only after the user's tap."""
    __tablename__ = "youtube_pending"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("ytp"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    conversation_id: Mapped[str] = mapped_column(String(40), default="")
    action: Mapped[str] = mapped_column(String(16))           # reply | update | upload
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    summary: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(12), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
