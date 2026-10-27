"""Tables for Google Photos. Imported by db.init_db so create_all makes them."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now


class PhotosAccount(Base):
    """A Google account the user connected for Google Photos (Picker + app-created Library scopes). Encrypted tokens."""
    __tablename__ = "photos_accounts"
    __table_args__ = (UniqueConstraint("tenant_id", "address", name="uq_photos_account"),)
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("gph"))
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


class PhotosPick(Base):
    """One Google Photos Picker session: the user opens the link, picks photos, Santosh gets just those."""
    __tablename__ = "photos_picks"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("pick"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    conversation_id: Mapped[str] = mapped_column(String(40), default="")
    account: Mapped[str] = mapped_column(String(40), default="")
    session_id: Mapped[str] = mapped_column(String(200))
    picker_uri: Mapped[str] = mapped_column(Text, default="")
    purpose: Mapped[str] = mapped_column(String(300), default="")
    status: Mapped[str] = mapped_column(String(12), default="waiting")   # waiting | ready | expired
    items: Mapped[list | None] = mapped_column(JSON, nullable=True)
    item_count: Mapped[int] = mapped_column(Integer, default=0)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class PhotosPending(Base):
    """A big upload into Google Photos (more than 20 files) waiting for the user's tap."""
    __tablename__ = "photos_pending"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("php"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    conversation_id: Mapped[str] = mapped_column(String(40), default="")
    action: Mapped[str] = mapped_column(String(16))
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    summary: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(12), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
