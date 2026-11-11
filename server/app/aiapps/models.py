"""v0.772 HOOLA AI APPS - tables (all prefixed ai_app_).

An AI app is an AI that answers HER CUSTOMERS (not her): a chat page, an embed bubble on a website, her business
WhatsApp number, an API key or an MCP tool. Its settings are a SOUL (see soul.py) kept like code: one editable draft,
immutable published versions, restore any of them. Everything a visitor says is logged (masked) so she can see it,
correct an answer, and count what it costs.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now


class AiApp(Base):
    __tablename__ = "ai_apps"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("aia"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    name: Mapped[str] = mapped_column(String(120), default="")
    kind: Mapped[str] = mapped_column(String(12), default="chat")          # chat | form
    status: Mapped[str] = mapped_column(String(12), default="draft")       # draft | live | paused
    code: Mapped[str] = mapped_column(String(24), index=True, default="")  # public address /a/<code>
    draft: Mapped[str] = mapped_column(Text, default="{}")                 # the editable soul (JSON)
    draft_hash: Mapped[str] = mapped_column(String(20), default="")
    live_version: Mapped[int] = mapped_column(Integer, default=0)          # 0 = never published
    template: Mapped[str] = mapped_column(String(40), default="")          # the template it was copied from
    origin: Mapped[str] = mapped_column(String(12), default="blank")       # blank | builder | template | import | proof
    channels: Mapped[str] = mapped_column(Text, default="{}")              # {"page": true, "embed": true, "whatsapp": "<pnid>", "api": true, "mcp": true}
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class AiAppVersion(Base):
    """Immutable: a published soul. Restore = publish an old one again as the newest version (history never rewritten)."""
    __tablename__ = "ai_app_versions"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("aiv"))
    app_id: Mapped[str] = mapped_column(String(40), index=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    soul: Mapped[str] = mapped_column(Text, default="{}")
    hash: Mapped[str] = mapped_column(String(20), default="")
    note: Mapped[str] = mapped_column(Text, default="")
    op: Mapped[str] = mapped_column(String(16), default="publish")         # publish | restore | import
    by: Mapped[str] = mapped_column(String(40), default="owner")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class AiAppKey(Base):
    """An API key for one app. Only the sha256 is kept; the key is shown once."""
    __tablename__ = "ai_app_keys"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("aik"))
    app_id: Mapped[str] = mapped_column(String(40), index=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    name: Mapped[str] = mapped_column(String(80), default="")
    key_hash: Mapped[str] = mapped_column(String(64), index=True, default="")
    tail: Mapped[str] = mapped_column(String(8), default="")               # last 4 chars, to tell keys apart
    rpm: Mapped[int] = mapped_column(Integer, default=20)                  # calls a minute
    rph: Mapped[int] = mapped_column(Integer, default=300)                 # calls an hour
    concurrent: Mapped[int] = mapped_column(Integer, default=3)            # calls running at once
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class AiAppSession(Base):
    """One visitor's conversation with one app (a page visitor, a WhatsApp number, an API caller's user id)."""
    __tablename__ = "ai_app_sessions"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("ais"))
    app_id: Mapped[str] = mapped_column(String(40), index=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    channel: Mapped[str] = mapped_column(String(12), default="page")       # page | embed | whatsapp | api | mcp | preview | trial | proof
    visitor: Mapped[str] = mapped_column(String(120), default="")          # an opaque id (never a phone in clear for page / embed)
    token_hash: Mapped[str] = mapped_column(String(64), index=True, default="")
    consent: Mapped[bool] = mapped_column(Boolean, default=False)          # DPDP: she saw the notice line
    turns: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    last_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class AiAppMessage(Base):
    """One question and its answer: the log she reads, corrects and counts."""
    __tablename__ = "ai_app_messages"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("aim"))
    app_id: Mapped[str] = mapped_column(String(40), index=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    session_id: Mapped[str] = mapped_column(String(40), index=True, default="")
    channel: Mapped[str] = mapped_column(String(12), default="page")
    version: Mapped[int] = mapped_column(Integer, default=0)               # the soul version that answered (0 = draft)
    question: Mapped[str] = mapped_column(Text, default="")                # masked
    answer: Mapped[str] = mapped_column(Text, default="")
    outcome: Mapped[str] = mapped_column(String(14), default="answered")
    # answered (from her knowledge) | annotated (her approved answer) | model (written from her facts) | unknown (handed
    # over) | refused (a trap: payment, OTP, another customer's data) | action (ticket / booking done) | cap (cost cap reached)
    # | error
    sources: Mapped[str] = mapped_column(Text, default="[]")
    action: Mapped[str] = mapped_column(Text, default="")                  # JSON of what was DONE, if anything
    ms: Mapped[int] = mapped_column(Integer, default=0)
    calls: Mapped[int] = mapped_column(Integer, default=0)                 # model calls made for this answer
    tok_in: Mapped[int] = mapped_column(Integer, default=0)
    tok_out: Mapped[int] = mapped_column(Integer, default=0)
    inr: Mapped[float] = mapped_column(Float, default=0.0)
    feedback: Mapped[int] = mapped_column(Integer, default=0)              # 1 = good, -1 = not right, 0 = none
    corrected: Mapped[str] = mapped_column(Text, default="")               # her corrected answer, if she gave one
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, index=True)


_READY: set[int] = set()


def ensure_tables() -> None:
    """Self-heal (the v0.190.1 rule): created checkfirst once per engine, so a DB born before this module still works."""
    from .. import db as _db
    eng = getattr(_db, "_engine", None)
    if eng is None or id(eng) in _READY:
        return
    for t in (AiApp, AiAppVersion, AiAppKey, AiAppSession, AiAppMessage):
        t.__table__.create(eng, checkfirst=True)
    _READY.add(id(eng))
