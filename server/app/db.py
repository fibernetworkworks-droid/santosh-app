"""Database models. SQLite by default; set DATABASE_URL to a postgresql+psycopg URL in production."""
from __future__ import annotations

import uuid
from contextlib import contextmanager
from datetime import datetime, timezone

from sqlalchemy import (JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text,
                        UniqueConstraint, create_engine, event)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from .config import get_settings


def now() -> datetime:
    return datetime.now(timezone.utc)


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


class Base(DeclarativeBase):
    pass


class Conversation(Base):
    __tablename__ = "conversations"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("conv"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Message(Base):
    """One turn in the conversation.

    in_history=True rows are replayed to Claude exactly (content is the API content JSON).
    in_history=False rows are notices from the background worker; they are shown in the
    chat and handed to Claude as context at the start of the next user turn.
    """
    __tablename__ = "messages"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    conversation_id: Mapped[str] = mapped_column(ForeignKey("conversations.id"), index=True)
    role: Mapped[str] = mapped_column(String(16))
    content: Mapped[list | str] = mapped_column(JSON)
    display: Mapped[str | None] = mapped_column(Text, nullable=True)
    in_history: Mapped[bool] = mapped_column(Boolean, default=True)
    delivered_to_agent: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class LeadList(Base):
    __tablename__ = "lead_lists"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("list"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    name: Mapped[str] = mapped_column(String(200))
    source_filename: Mapped[str] = mapped_column(String(300))
    columns: Mapped[list] = mapped_column(JSON, default=list)
    has_consent_column: Mapped[bool] = mapped_column(Boolean, default=False)
    total_rows: Mapped[int] = mapped_column(Integer, default=0)
    valid: Mapped[int] = mapped_column(Integer, default=0)
    invalid: Mapped[int] = mapped_column(Integer, default=0)
    duplicates: Mapped[int] = mapped_column(Integer, default=0)
    opted_in: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Lead(Base):
    __tablename__ = "leads"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    list_id: Mapped[str] = mapped_column(ForeignKey("lead_lists.id"), index=True)
    name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    phone: Mapped[str] = mapped_column(String(20), index=True)       # E.164 digits, no "+"
    opted_in: Mapped[bool | None] = mapped_column(Boolean, nullable=True)  # None = no consent column
    extra: Mapped[dict] = mapped_column(JSON, default=dict)


class Template(Base):
    __tablename__ = "templates"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("tpl"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    name: Mapped[str] = mapped_column(String(512))
    language: Mapped[str] = mapped_column(String(16))
    category: Mapped[str] = mapped_column(String(32))
    body: Mapped[str] = mapped_column(Text)
    footer: Mapped[str | None] = mapped_column(String(60), nullable=True)
    example_values: Mapped[list] = mapped_column(JSON, default=list)
    meta_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(32), default="DRAFT")   # PENDING / APPROVED / REJECTED / PAUSED / DISABLED
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Campaign(Base):
    __tablename__ = "campaigns"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("camp"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    conversation_id: Mapped[str] = mapped_column(ForeignKey("conversations.id"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    lead_list_id: Mapped[str] = mapped_column(ForeignKey("lead_lists.id"))
    template_id: Mapped[str] = mapped_column(ForeignKey("templates.id"))
    param_mapping: Mapped[list] = mapped_column(JSON, default=list)
    # awaiting_approval -> ready (waits for a yes) -> sending -> completed
    # also: paused, waiting_limit, failed, cancelled
    status: Mapped[str] = mapped_column(String(32), default="awaiting_approval")
    auto_send: Mapped[bool] = mapped_column(Boolean, default=False)
    status_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_template_poll: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    report_sent: Mapped[bool] = mapped_column(Boolean, default=False)


class OutboundMessage(Base):
    __tablename__ = "outbound_messages"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    campaign_id: Mapped[str] = mapped_column(ForeignKey("campaigns.id"), index=True)
    lead_id: Mapped[int] = mapped_column(ForeignKey("leads.id"))
    phone: Mapped[str] = mapped_column(String(20), index=True)
    params: Mapped[list] = mapped_column(JSON, default=list)
    wa_message_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(16), default="queued")   # queued/sent/delivered/read/failed
    replied: Mapped[bool] = mapped_column(Boolean, default=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Event(Base):
    """Everything the UI shows live: chat messages, task steps, logs and progress."""
    __tablename__ = "events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    conversation_id: Mapped[str] = mapped_column(String(40), index=True)
    campaign_id: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    kind: Mapped[str] = mapped_column(String(24))   # message / step / log / campaign / typing
    payload: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Profile(Base):
    """What Santosh knows about the user's setup (one row per tenant for now)."""
    __tablename__ = "profiles"
    tenant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    city: Mapped[str | None] = mapped_column(String(120), nullable=True)
    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lon: Mapped[float | None] = mapped_column(Float, nullable=True)
    language: Mapped[str | None] = mapped_column(String(32), nullable=True)
    timezone: Mapped[str] = mapped_column(String(64), default="Asia/Kolkata")
    briefing_time: Mapped[str | None] = mapped_column(String(5), nullable=True)   # "07:30" local
    briefing_conversation_id: Mapped[str | None] = mapped_column(String(40), nullable=True)
    last_briefing_date: Mapped[str | None] = mapped_column(String(10), nullable=True)


class Reminder(Base):
    __tablename__ = "reminders"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("rem"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    conversation_id: Mapped[str] = mapped_column(String(40), index=True)
    text: Mapped[str] = mapped_column(String(500))
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)   # UTC
    repeat: Mapped[str] = mapped_column(String(16), default="none")   # none/daily/weekdays/weekly/monthly
    status: Mapped[str] = mapped_column(String(16), default="active")  # active/done/cancelled
    fired_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Routine(Base):
    """A job Santosh runs by himself on a schedule (the user does not need the app open)."""
    __tablename__ = "routines"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("rtn"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    conversation_id: Mapped[str] = mapped_column(String(40), index=True)
    title: Mapped[str] = mapped_column(String(200))
    instruction: Mapped[str] = mapped_column(String(2000))
    next_run: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)   # UTC
    repeat: Mapped[str] = mapped_column(String(16), default="daily")   # none/hourly/daily/weekdays/weekly/monthly
    status: Mapped[str] = mapped_column(String(16), default="active")  # active/done/cancelled
    run_count: Mapped[int] = mapped_column(Integer, default=0)
    last_run: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_result: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class MemoryFact(Base):
    __tablename__ = "memory_facts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    text: Mapped[str] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class ListItem(Base):
    __tablename__ = "list_items"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    list_name: Mapped[str] = mapped_column(String(80), index=True)
    text: Mapped[str] = mapped_column(String(200))
    done: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class DeviceAction(Base):
    """Something only the phone can do (alarm, timer, calendar entry). The app runs it and reports back."""
    __tablename__ = "device_actions"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("act"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    conversation_id: Mapped[str] = mapped_column(String(40), index=True)
    type: Mapped[str] = mapped_column(String(32))
    payload: Mapped[dict] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(16), default="pending")   # pending/done/failed/expired
    result: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class EmailDraft(Base):
    """An email Santosh wrote. It is sent only after the user approves it in the app."""
    __tablename__ = "email_drafts"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("eml"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    conversation_id: Mapped[str] = mapped_column(String(40), index=True)
    to_addr: Mapped[str] = mapped_column(String(1000))
    cc_addr: Mapped[str] = mapped_column(String(1000), default="")
    subject: Mapped[str] = mapped_column(String(500))
    body: Mapped[str] = mapped_column(Text)
    in_reply_to: Mapped[str | None] = mapped_column(String(500), nullable=True)   # Message-ID being replied to
    references: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="pending")   # pending/sent/cancelled/failed
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class User(Base):
    """A person with their own Santosh. The user's id is their tenant_id everywhere else."""
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("usr"))
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200), default="")
    google_sub: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)   # stable Google user id
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    last_login: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class OAuthConnection(Base):
    """A user's link to an outside account (google, microsoft, ...). Tokens are stored encrypted."""
    __tablename__ = "oauth_connections"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(40), index=True)
    provider: Mapped[str] = mapped_column(String(32))            # "google"
    account_email: Mapped[str] = mapped_column(String(320), default="")
    access_token_enc: Mapped[str | None] = mapped_column(Text, nullable=True)
    refresh_token_enc: Mapped[str | None] = mapped_column(Text, nullable=True)
    scopes: Mapped[str] = mapped_column(Text, default="")
    expiry: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)
    __table_args__ = (UniqueConstraint("user_id", "provider", name="uq_user_provider"),)


class AppSession(Base):
    """A logged-in session on the phone. The app sends its token as the Bearer on every call."""
    __tablename__ = "app_sessions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    user_id: Mapped[str] = mapped_column(String(40), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    last_seen: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class OAuthState(Base):
    """Short-lived anti-CSRF value for an in-progress OAuth sign-in."""
    __tablename__ = "oauth_states"
    state: Mapped[str] = mapped_column(String(64), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class UserLocation(Base):
    """The phone's last known position (sent by the app), for 'near me', directions and cab pickup."""
    __tablename__ = "user_locations"
    tenant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    lat: Mapped[float] = mapped_column(Float)
    lng: Mapped[float] = mapped_column(Float)
    accuracy_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class PhoneSeen(Base):
    """Last time the tenant's phone talked to the server (live stream ping or any API call)."""
    __tablename__ = "phone_seen"
    tenant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    digest_upto_id: Mapped[int] = mapped_column(Integer, default=0)       # last notice already emailed
    digest_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class KV(Base):
    __tablename__ = "kv"
    key: Mapped[str] = mapped_column(String(200), primary_key=True)
    value: Mapped[float] = mapped_column(Float, default=0)


_engine = None
_Session = None


def init_db(url: str | None = None):
    global _engine, _Session
    url = url or get_settings().database_url
    kwargs = {}
    if url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
    _engine = create_engine(url, **kwargs)
    if url.startswith("sqlite"):
        @event.listens_for(_engine, "connect")
        def _pragmas(dbapi_conn, _):
            cur = dbapi_conn.cursor()
            cur.execute("PRAGMA journal_mode=WAL")
            cur.execute("PRAGMA foreign_keys=ON")
            cur.close()
    Base.metadata.create_all(_engine)
    from .bazar.db import init_tables as _bazar_tables
    _bazar_tables(_engine)
    _Session = sessionmaker(_engine, expire_on_commit=False)
    return _engine


@contextmanager
def session():
    if _Session is None:
        init_db()
    s = _Session()
    try:
        yield s
        s.commit()
    except Exception:
        s.rollback()
        raise
    finally:
        s.close()


def as_utc(dt: datetime | None) -> datetime | None:
    """SQLite drops tzinfo; treat naive datetimes as UTC."""
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
