"""Tables for Google Forms. Imported by db.init_db so create_all makes them."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now


class FormsAccount(Base):
    """A Google account the user connected for Google Forms. Tokens stored encrypted."""
    __tablename__ = "forms_accounts"
    __table_args__ = (UniqueConstraint("tenant_id", "address", name="uq_forms_account"),)
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("gfm"))
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


class FormsPending(Base):
    """A Forms change that reaches other people or loses answers (share, delete answered questions). Runs after a tap."""
    __tablename__ = "forms_pending"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("fmp"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    conversation_id: Mapped[str] = mapped_column(String(40), default="")
    action: Mapped[str] = mapped_column(String(16))
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    summary: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(12), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class FormWatch(Base):
    """Tell the user when new answers arrive on a form."""
    __tablename__ = "forms_watches"
    __table_args__ = (UniqueConstraint("tenant_id", "form_id", name="uq_forms_watch"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    conversation_id: Mapped[str] = mapped_column(String(40), default="")
    account: Mapped[str] = mapped_column(String(40), default="")
    form_id: Mapped[str] = mapped_column(String(200))
    title: Mapped[str] = mapped_column(String(300), default="")
    last_seen: Mapped[str] = mapped_column(String(40), default="")     # RFC3339 lastSubmittedTime of the newest seen
    seen_count: Mapped[int] = mapped_column(Integer, default=0)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class FormsRecent(Base):
    """Forms the user worked with through Santosh, so "meri feedback form" is found quickly."""
    __tablename__ = "forms_recent"
    __table_args__ = (UniqueConstraint("tenant_id", "form_id", name="uq_forms_recent"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    account: Mapped[str] = mapped_column(String(40), default="")
    form_id: Mapped[str] = mapped_column(String(200))
    title: Mapped[str] = mapped_column(String(300), default="")
    used_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
