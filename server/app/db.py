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
    pinned: Mapped[bool | None] = mapped_column(Boolean, nullable=True, default=False)   # v0.63 "hamesha yaad"


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
    # added in v0.20 (all nullable so old databases gain them with ALTER TABLE)
    bcc_addr: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    account: Mapped[str | None] = mapped_column(String(40), nullable=True)        # mailbox key (MailAccount id / "google" / "env")
    thread_id: Mapped[str | None] = mapped_column(String(200), nullable=True)     # provider thread (Gmail threadId)
    kind: Mapped[str | None] = mapped_column(String(12), nullable=True)           # new | reply | forward
    attachments: Mapped[list | None] = mapped_column(JSON, nullable=True)         # [{type: email|file|artifact, ...}]
    send_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)   # scheduled send
    follow_up_days: Mapped[int | None] = mapped_column(Integer, nullable=True)    # remind if no reply after N days
    sent_message_id: Mapped[str | None] = mapped_column(String(500), nullable=True)


class MailAccount(Base):
    """A mailbox the user connected: Gmail / Outlook by OAuth, or any provider by IMAP + app password.
    Tokens and passwords are stored encrypted."""
    __tablename__ = "mail_accounts"
    __table_args__ = (UniqueConstraint("tenant_id", "address", name="uq_mail_account"),)
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("mbx"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    kind: Mapped[str] = mapped_column(String(12))                  # gmail | outlook | imap
    address: Mapped[str] = mapped_column(String(320))
    display_name: Mapped[str] = mapped_column(String(120), default="")
    signature: Mapped[str] = mapped_column(Text, default="")
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    access_token_enc: Mapped[str | None] = mapped_column(Text, nullable=True)
    refresh_token_enc: Mapped[str | None] = mapped_column(Text, nullable=True)
    expiry: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    password_enc: Mapped[str | None] = mapped_column(Text, nullable=True)
    imap_host: Mapped[str] = mapped_column(String(200), default="")
    imap_port: Mapped[int] = mapped_column(Integer, default=993)
    smtp_host: Mapped[str] = mapped_column(String(200), default="")
    smtp_port: Mapped[int] = mapped_column(Integer, default=587)
    status: Mapped[str] = mapped_column(String(12), default="ok")   # ok | error
    last_error: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class CalendarAccount(Base):
    """A Google Calendar the user connected by Google sign-in (scope: calendar). Tokens stored encrypted."""
    __tablename__ = "calendar_accounts"
    __table_args__ = (UniqueConstraint("tenant_id", "address", name="uq_calendar_account"),)
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("cal"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    kind: Mapped[str] = mapped_column(String(12), default="google")
    address: Mapped[str] = mapped_column(String(320))
    display_name: Mapped[str] = mapped_column(String(120), default="")
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    access_token_enc: Mapped[str | None] = mapped_column(Text, nullable=True)
    refresh_token_enc: Mapped[str | None] = mapped_column(Text, nullable=True)
    expiry: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(12), default="ok")
    last_error: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class SheetsAccount(Base):
    """A Google account the user connected for Google Sheets (scopes: spreadsheets + Drive file list). Encrypted tokens."""
    __tablename__ = "sheets_accounts"
    __table_args__ = (UniqueConstraint("tenant_id", "address", name="uq_sheets_account"),)
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("gsh"))
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


class SheetsPending(Base):
    """A Sheets change that is hard to undo or reaches other people (delete rows, big update, share). Runs after a tap."""
    __tablename__ = "sheets_pending"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("shp"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    conversation_id: Mapped[str] = mapped_column(String(40), default="")
    action: Mapped[str] = mapped_column(String(16))
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    summary: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(12), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class SheetsRecent(Base):
    """Sheets the user worked with through Santosh, so "meri sales sheet" is found quickly."""
    __tablename__ = "sheets_recent"
    __table_args__ = (UniqueConstraint("tenant_id", "spreadsheet_id", name="uq_sheets_recent"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    account: Mapped[str] = mapped_column(String(40), default="")
    spreadsheet_id: Mapped[str] = mapped_column(String(200))
    title: Mapped[str] = mapped_column(String(300), default="")
    used_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class CalendarPrefs(Base):
    """Per person: which calendars Santosh reads, where new events go, meeting alerts."""
    __tablename__ = "calendar_prefs"
    tenant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    read_calendars: Mapped[list | None] = mapped_column(JSON, nullable=True)     # ["<acct>~<calendarId>"]; None = primary
    default_calendar: Mapped[str | None] = mapped_column(String(400), nullable=True)
    alert_minutes: Mapped[int] = mapped_column(Integer, default=10)              # 0 = no meeting alerts
    alert_conversation_id: Mapped[str | None] = mapped_column(String(40), nullable=True)


class CalendarPending(Base):
    """A calendar change that informs other people (invite, reschedule, cancel). Runs only after the user's tap."""
    __tablename__ = "calendar_pending"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("calp"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    conversation_id: Mapped[str] = mapped_column(String(40), default="")
    action: Mapped[str] = mapped_column(String(12))            # create | update | cancel
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    summary: Mapped[dict] = mapped_column(JSON, default=dict)  # what the card shows
    status: Mapped[str] = mapped_column(String(12), default="pending")   # pending | done | failed
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class CalendarAlert(Base):
    """Meeting alerts already sent (so each meeting is announced once)."""
    __tablename__ = "calendar_alerts"
    __table_args__ = (UniqueConstraint("tenant_id", "event_key", name="uq_calendar_alert"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    event_key: Mapped[str] = mapped_column(String(600))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class MailLinkState(Base):
    """Anti-CSRF state while the user connects a mailbox by OAuth (remembers whose mailbox it is)."""
    __tablename__ = "mail_link_states"
    state: Mapped[str] = mapped_column(String(80), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64))
    provider: Mapped[str] = mapped_column(String(12))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class MailContact(Base):
    """People the user emails with, learned from their own mail, so "Swati ko mail karo" finds the address."""
    __tablename__ = "mail_contacts"
    __table_args__ = (UniqueConstraint("tenant_id", "email", name="uq_mail_contact"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    email: Mapped[str] = mapped_column(String(320))
    name: Mapped[str] = mapped_column(String(200), default="")
    score: Mapped[float] = mapped_column(Float, default=0)        # higher = emailed more / more recently
    sent_to: Mapped[int] = mapped_column(Integer, default=0)
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class MailWatch(Base):
    """A follow-up: tell the user if nobody replied to a mail (their_reply), or if the user hasn't replied (my_reply)."""
    __tablename__ = "mail_watches"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("mw"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    conversation_id: Mapped[str] = mapped_column(String(40), default="")
    account: Mapped[str] = mapped_column(String(40), default="")
    mode: Mapped[str] = mapped_column(String(12))                  # their_reply | my_reply
    message_id: Mapped[str] = mapped_column(String(500), default="")
    thread_id: Mapped[str] = mapped_column(String(200), default="")
    email_ref: Mapped[str] = mapped_column(String(300), default="")   # Santosh email id, for "reply now"
    subject: Mapped[str] = mapped_column(String(500), default="")
    peer: Mapped[str] = mapped_column(String(320), default="")
    since: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    status: Mapped[str] = mapped_column(String(12), default="waiting")   # waiting | replied | reminded | cancelled
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class BulkMail(Base):
    """One email sent separately to many people (mail merge). Starts only after the user approves the card."""
    __tablename__ = "bulk_mails"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("bulk"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    conversation_id: Mapped[str] = mapped_column(String(40), default="")
    account: Mapped[str] = mapped_column(String(40), default="")
    subject: Mapped[str] = mapped_column(String(500))
    body: Mapped[str] = mapped_column(Text)
    attachments: Mapped[list | None] = mapped_column(JSON, nullable=True)
    source: Mapped[str] = mapped_column(String(300), default="")
    status: Mapped[str] = mapped_column(String(12), default="pending")   # pending | sending | done | cancelled
    total: Mapped[int] = mapped_column(Integer, default=0)
    sent: Mapped[int] = mapped_column(Integer, default=0)
    failed: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class BulkRecipient(Base):
    __tablename__ = "bulk_recipients"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    bulk_id: Mapped[str] = mapped_column(String(40), index=True)
    email: Mapped[str] = mapped_column(String(320))
    name: Mapped[str] = mapped_column(String(200), default="")
    fields: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(10), default="queued")    # queued | sent | failed
    error: Mapped[str] = mapped_column(Text, default="")
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
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)      # v0.70: why Google refused the refresh
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


class PcDevice(Base):
    """A computer paired with Santosh (Santosh Desktop). Only a hash of its token is stored."""
    __tablename__ = "pc_devices"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("pc"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    name: Mapped[str] = mapped_column(String(120), default="PC")
    os: Mapped[str] = mapped_column(String(60), default="")
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    info: Mapped[dict] = mapped_column(JSON, default=dict)       # folders, tally, version (reported by the PC)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    last_seen: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)


class PcPairCode(Base):
    __tablename__ = "pc_pair_codes"
    code_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used: Mapped[bool] = mapped_column(Boolean, default=False)


class PcJob(Base):
    """Activity log: everything Santosh asked a PC to do."""
    __tablename__ = "pc_jobs"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("job"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    device_id: Mapped[str] = mapped_column(String(40), index=True)
    action: Mapped[str] = mapped_column(String(40))
    summary: Mapped[str] = mapped_column(String(300), default="")
    status: Mapped[str] = mapped_column(String(16), default="sent")   # sent | done | error | timeout
    error: Mapped[str] = mapped_column(String(300), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PcFile(Base):
    """A file passing between the PC and the phone. Kept on the server for a short time only."""
    __tablename__ = "pc_files"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("file"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    device_id: Mapped[str] = mapped_column(String(40), default="")
    direction: Mapped[str] = mapped_column(String(10))               # to_phone | to_pc
    name: Mapped[str] = mapped_column(String(255))
    size: Mapped[int] = mapped_column(Integer, default=0)
    sha256: Mapped[str] = mapped_column(String(64), default="")
    pc_path: Mapped[str] = mapped_column(Text, default="")
    stored_path: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Artifact(Base):
    """A page Santosh built for the user (app, calculator, tracker, chart, document...). Content lives in versions."""
    __tablename__ = "artifacts"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("art"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    conversation_id: Mapped[str] = mapped_column(String(40), default="")
    title: Mapped[str] = mapped_column(String(160), default="Santosh page")
    summary: Mapped[str] = mapped_column(String(300), default="")
    version: Mapped[int] = mapped_column(Integer, default=0)            # latest ready version (0 = none yet)
    status: Mapped[str] = mapped_column(String(12), default="building")  # building | ready | failed
    error: Mapped[str] = mapped_column(String(300), default="")
    share_token: Mapped[str] = mapped_column(String(40), default="", index=True)
    deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class ArtifactVersion(Base):
    __tablename__ = "artifact_versions"
    __table_args__ = (UniqueConstraint("artifact_id", "version"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    artifact_id: Mapped[str] = mapped_column(String(40), index=True)
    version: Mapped[int] = mapped_column(Integer)
    html: Mapped[str] = mapped_column(Text)
    note: Mapped[str] = mapped_column(String(300), default="")         # what was asked for this version
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class ArtifactState(Base):
    """What a page saved through window.santosh.storage (per artifact, per key)."""
    __tablename__ = "artifact_state"
    __table_args__ = (UniqueConstraint("artifact_id", "key"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    artifact_id: Mapped[str] = mapped_column(String(40), index=True)
    key: Mapped[str] = mapped_column(String(120))
    value: Mapped[dict] = mapped_column(JSON, default=dict)            # {"v": <any json>}
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class PushToken(Base):
    """A phone's Firebase Cloud Messaging token (where Santosh sends pushes when the app is closed)."""
    __tablename__ = "push_tokens"
    token: Mapped[str] = mapped_column(String(300), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    platform: Mapped[str] = mapped_column(String(16), default="android")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    last_ok: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


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
    from .drive import models as _drive_models  # noqa: F401
    from .forms import models as _forms_models  # noqa: F401
    from .slides import models as _slides_models  # noqa: F401
    from .photos import models as _photos_models  # noqa: F401
    from .notebook import models as _notebook_models  # noqa: F401
    from .youtube import models as _youtube_models  # noqa: F401
    from .appcheck import models as _appcheck_models  # noqa: F401
    from .avatar import models as _avatar_models  # noqa: F401
    from .voiceid import models as _voiceid_models  # noqa: F401
    from .publicapis import models as _publicapi_models  # noqa: F401
    from .reels import models as _reels_models  # noqa: F401
    from .motion import models as _motion_models  # noqa: F401
    from . import idvault as _idvault  # noqa: F401
    from .net import models as _net_models  # noqa: F401
    from .net import share as _net_share  # noqa: F401
    from .net import groups as _net_groups  # noqa: F401
    from .net import learning as _net_learning  # noqa: F401
    from .net import community as _net_community  # noqa: F401
    from .net import chain as _net_chain  # noqa: F401
    from .net import business as _net_business  # noqa: F401
    from .net import deal as _net_deal  # noqa: F401  (v0.102 deals: tables + envelope kinds)
    from .bt import models as _bt_models  # noqa: F401
    from . import procedures as _procedures  # noqa: F401
    from .shop import service as _shop  # noqa: F401
    from .darzi import service as _darzi  # noqa: F401
    from .galla import service as _galla  # noqa: F401
    from .chai import service as _chai  # noqa: F401
    from .mshop import service as _mshop  # noqa: F401
    from .phonedoc import service as _phonedoc  # noqa: F401
    from .gstp import service as _gstp  # noqa: F401
    from .payroll import service as _payroll  # noqa: F401
    from .analyst import service as _analyst  # noqa: F401
    from .audit import service as _audit  # noqa: F401
    from .insure import service as _insure  # noqa: F401
    from .telecall import service as _telecall  # noqa: F401
    from .kalam import service as _kalam  # noqa: F401
    from .seo import service as _seo  # noqa: F401
    from .office import service as _office  # noqa: F401
    from .lekhak import service as _lekhak  # noqa: F401
    from .agent import pakka as _pakka  # noqa: F401
    from .employee import models as _employee_models  # noqa: F401
    from .employee import network as _employee_net  # noqa: F401
    from .videoedit import models as _videoedit_models  # noqa: F401
    from .operator import models as _operator_models  # noqa: F401
    from . import mcp_prefs as _mcp_prefs  # noqa: F401
    from . import approvekey as _approvekey  # noqa: F401
    from . import askform as _askform  # noqa: F401
    from . import usage as _usage  # noqa: F401
    from . import callrating as _callrating  # noqa: F401
    Base.metadata.create_all(_engine)
    _add_missing_columns(_engine)
    from .bazar.db import init_tables as _bazar_tables
    _bazar_tables(_engine)
    _Session = sessionmaker(_engine, expire_on_commit=False)
    return _engine


def _add_missing_columns(engine) -> None:
    """create_all() makes new tables but never new columns: add nullable columns added in later versions."""
    from sqlalchemy import inspect, text
    insp = inspect(engine)
    for table in Base.metadata.sorted_tables:
        if not insp.has_table(table.name):
            continue
        have = {c["name"] for c in insp.get_columns(table.name)}
        for col in table.columns:
            if col.name in have or not col.nullable or col.primary_key:
                continue
            ddl = f'ALTER TABLE {table.name} ADD COLUMN "{col.name}" {col.type.compile(dialect=engine.dialect)}'
            with engine.begin() as conn:
                conn.execute(text(ddl))


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
