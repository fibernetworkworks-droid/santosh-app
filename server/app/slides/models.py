"""Tables for Google Slides. Imported by db.init_db so create_all makes them."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now


class SlidesAccount(Base):
    """A Google account the user connected for Google Slides (scopes: presentations + Drive file list). Encrypted tokens."""
    __tablename__ = "slides_accounts"
    __table_args__ = (UniqueConstraint("tenant_id", "address", name="uq_slides_account"),)
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("gsl"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    address: Mapped[str] = mapped_column(String(320))
    display_name: Mapped[str] = mapped_column(String(120), default="")
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    access_token_enc: Mapped[str | None] = mapped_column(Text, nullable=True)
    refresh_token_enc: Mapped[str | None] = mapped_column(Text, nullable=True)
    expiry: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(12), default="ok")
    last_error: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class SlidesPending(Base):
    """A Slides change that reaches people or is hard to undo (share, delete slides). Runs after the user's tap."""
    __tablename__ = "slides_pending"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("slp"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    conversation_id: Mapped[str] = mapped_column(String(40), default="")
    action: Mapped[str] = mapped_column(String(16))
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    summary: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(12), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class SlidesRecent(Base):
    __tablename__ = "slides_recent"
    __table_args__ = (UniqueConstraint("tenant_id", "presentation_id", name="uq_slides_recent"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    account: Mapped[str] = mapped_column(String(40), default="")
    presentation_id: Mapped[str] = mapped_column(String(200))
    title: Mapped[str] = mapped_column(String(300), default="")
    used_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
