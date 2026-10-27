"""Tables of the Call Centre Sahayak (all prefixed callcentre_)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now


class CcSettings(Base):
    __tablename__ = "callcentre_settings"
    tenant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    line_on: Mapped[bool] = mapped_column(Boolean, default=False)         # the AI answers the line
    provider: Mapped[str] = mapped_column(String(12), default="plivo")     # plivo | exotel | fake
    number: Mapped[str] = mapped_column(String(20), default="")            # her rented number (shown, matched to "To")
    token: Mapped[str] = mapped_column(String(48), default="", index=True) # route token in the webhook URLs
    creds: Mapped[str] = mapped_column(Text, default="")                   # sealed JSON (auth_id / auth_token / api_key ...)
    ws_user: Mapped[str] = mapped_column(String(32), default="")            # Exotel Basic Auth for the stream URL
    ws_pass: Mapped[str] = mapped_column(Text, default="")                  # sealed
    agent_name: Mapped[str] = mapped_column(String(40), default="")         # '' = her avatar's name
    voice: Mapped[str] = mapped_column(String(30), default="")
    hours: Mapped[str] = mapped_column(Text, default="")                    # {open, close, days}; '' = Employee hours
    after_hours: Mapped[str] = mapped_column(String(10), default="message")  # message (AI takes a message) | closed
    max_concurrent: Mapped[int] = mapped_column(Integer, default=2)
    queue_max: Mapped[int] = mapped_column(Integer, default=3)              # times a caller hears "please hold" (15 s each)
    overflow: Mapped[str] = mapped_column(String(10), default="callback")   # callback | transfer
    handover: Mapped[str] = mapped_column(Text, default="[]")              # [{name, phone, role}] people a call can go to
    transfer_on: Mapped[bool] = mapped_column(Boolean, default=True)
    record: Mapped[bool] = mapped_column(Boolean, default=False)           # provider records the call (announced)
    max_minutes: Mapped[int] = mapped_column(Integer, default=10)
    rate_inr_per_min: Mapped[float] = mapped_column(Float, default=0.0)    # her provider's per-minute rate (she enters it)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class CcScript(Base):
    """Every version of her script. Only status=approved (her tap, hash-checked) is ever spoken on a call."""
    __tablename__ = "callcentre_scripts"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("ccs"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(10), default="draft")       # draft | waiting | approved | retired | rejected
    content: Mapped[str] = mapped_column(Text, default="{}")
    hash: Mapped[str] = mapped_column(String(32), default="")
    note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class CcCall(Base):
    __tablename__ = "callcentre_calls"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("ccc"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    provider: Mapped[str] = mapped_column(String(12), default="")
    provider_call: Mapped[str] = mapped_column(String(80), default="", index=True)
    stream_id: Mapped[str] = mapped_column(String(80), default="")
    caller: Mapped[str] = mapped_column(String(20), default="")             # +91..., needed for the call-back
    caller_name: Mapped[str] = mapped_column(String(80), default="")
    status: Mapped[str] = mapped_column(String(12), default="ringing")      # ringing | queued | live | ended
    outcome: Mapped[str] = mapped_column(String(16), default="")           # answered | message | appointment | transferred |
    #                                                                        callback | complaint | closed | busy | dropped | failed
    intent: Mapped[str] = mapped_column(String(16), default="")
    lang: Mapped[str] = mapped_column(String(8), default="")
    script_id: Mapped[str] = mapped_column(String(40), default="")
    script_version: Mapped[int] = mapped_column(Integer, default=0)
    queue_tries: Mapped[int] = mapped_column(Integer, default=0)
    handover_reason: Mapped[str] = mapped_column(String(20), default="")
    transfer_to: Mapped[str] = mapped_column(String(20), default="")       # +91... set only when a transfer is asked
    summary: Mapped[str] = mapped_column(Text, default="")
    transcript: Mapped[str] = mapped_column(Text, default="[]")            # [[who, masked text]]
    flags: Mapped[str] = mapped_column(Text, default="[]")
    tools: Mapped[str] = mapped_column(Text, default="[]")
    stats: Mapped[str] = mapped_column(Text, default="{}")
    seconds: Mapped[float] = mapped_column(Float, default=0.0)
    ai_usd: Mapped[float] = mapped_column(Float, default=0.0)
    phone_inr: Mapped[float] = mapped_column(Float, default=0.0)
    disclosed: Mapped[bool] = mapped_column(Boolean, default=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class CcMessage(Base):
    """A message / call-back the line took for her (anything outside the script lands here)."""
    __tablename__ = "callcentre_messages"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("ccm"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    call_id: Mapped[str] = mapped_column(String(40), default="", index=True)
    caller: Mapped[str] = mapped_column(String(20), default="")
    name: Mapped[str] = mapped_column(String(80), default="")
    text: Mapped[str] = mapped_column(Text, default="")
    kind: Mapped[str] = mapped_column(String(12), default="message")       # message | callback | missed | outside
    callback_at: Mapped[str] = mapped_column(String(16), default="")        # local "YYYY-MM-DD HH:MM" the caller asked for
    status: Mapped[str] = mapped_column(String(8), default="open")         # open | done
    reminded: Mapped[bool] = mapped_column(Boolean, default=False)
    note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class CcCaller(Base):
    """What the line remembers about a number: their language and how many times they called (no audio, no content)."""
    __tablename__ = "callcentre_callers"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("ccp"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    key: Mapped[str] = mapped_column(String(10), index=True)                # last 10 digits
    name: Mapped[str] = mapped_column(String(80), default="")
    lang: Mapped[str] = mapped_column(String(8), default="")
    calls: Mapped[int] = mapped_column(Integer, default=0)
    last_intent: Mapped[str] = mapped_column(String(16), default="")
    last_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
