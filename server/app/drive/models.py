"""Tables for Google Drive. Imported by db.init_db so create_all makes them."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now


class DriveAccount(Base):
    """A Google account the user connected for Google Drive (scope: drive). Tokens stored encrypted."""
    __tablename__ = "drive_accounts"
    __table_args__ = (UniqueConstraint("tenant_id", "address", name="uq_drive_account"),)
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("gdr"))
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


class DrivePending(Base):
    """A Drive change that reaches other people or is hard to undo (share, public link, trash). Runs after a tap."""
    __tablename__ = "drive_pending"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("drp"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    conversation_id: Mapped[str] = mapped_column(String(40), default="")
    action: Mapped[str] = mapped_column(String(16))           # share | public | trash
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    summary: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(12), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class DriveRecent(Base):
    """Drive files the user worked with through Santosh, so "woh quotation wali file" is found quickly."""
    __tablename__ = "drive_recent"
    __table_args__ = (UniqueConstraint("tenant_id", "file_id", name="uq_drive_recent"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    account: Mapped[str] = mapped_column(String(40), default="")
    file_id: Mapped[str] = mapped_column(String(200))
    name: Mapped[str] = mapped_column(String(400), default="")
    mime: Mapped[str] = mapped_column(String(200), default="")
    used_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
