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
    # v0.999.67 global: the business's country (a number written without + is in it), her currency, her registered
    # telemarketing line (India 140 / 1600), and the countries whose calling law she confirmed she checked
    country: Mapped[str] = mapped_column(String(2), default="IN")
    currency: Mapped[str] = mapped_column(String(3), default="")
    registered_line: Mapped[bool] = mapped_column(Boolean, default=False)
    confirmed: Mapped[str] = mapped_column(Text, default="[]")
    warm_transfer: Mapped[bool | None] = mapped_column(Boolean, nullable=True, default=True)   # G3 the person hears the summary first
    wa_calls: Mapped[str | None] = mapped_column(String(10), nullable=True, default="callback")  # G3 WhatsApp voice calls: callback | off
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
    whisper: Mapped[str | None] = mapped_column(Text, nullable=True, default="")
    transfer_status: Mapped[str | None] = mapped_column(String(12), nullable=True, default="")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # v0.999.67 AI TELECALLER: a call Hoola MADE (direction out) belongs to one person on one call list
    direction: Mapped[str] = mapped_column(String(4), default="in")           # in | out
    campaign_id: Mapped[str] = mapped_column(String(40), default="", index=True)
    target_id: Mapped[str] = mapped_column(String(40), default="", index=True)
    answered_by: Mapped[str] = mapped_column(String(12), default="")         # human | machine | unknown (provider's check)


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
    reply_wait_ms: Mapped[int | None] = mapped_column(Integer, nullable=True, default=0)     # G3 learned wait before replying


# ---------------------------------------------------------------- v0.999.67 the Business Brain + AI calls out
class CcSource(Base):
    """One place the business's knowledge comes from: her words, a file, a web page, a sheet, her own API, or a system
    she joined to Hoola (SAP / Salesforce / any Composio app). `mode` facts = read in, kept as facts she approves;
    live = asked during a call (an order's status by the caller's number), never stored."""
    __tablename__ = "callcentre_sources"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("ccsrc"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    kind: Mapped[str] = mapped_column(String(12), default="text")           # text | file | url | sheet | api | system
    name: Mapped[str] = mapped_column(String(120), default="")
    mode: Mapped[str] = mapped_column(String(6), default="facts")           # facts | live
    config: Mapped[str] = mapped_column(Text, default="{}")                 # url / file_id / role+system+target / fields
    secret: Mapped[str] = mapped_column(Text, default="")                   # sealed API key (never returned)
    status: Mapped[str] = mapped_column(String(10), default="new")          # new | waiting | approved | failed | off
    trust_updates: Mapped[bool] = mapped_column(Boolean, default=False)     # a re-read that changes facts stays approved
    refresh_h: Mapped[int] = mapped_column(Integer, default=24)             # 0 = never re-read by itself
    hash: Mapped[str] = mapped_column(String(32), default="")               # of the facts she approved
    facts: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str] = mapped_column(Text, default="")
    synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class CcFact(Base):
    """One piece of the business's knowledge (a product with its price, a policy, a branch, an answer)."""
    __tablename__ = "callcentre_facts"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("ccf"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    source_id: Mapped[str] = mapped_column(String(40), index=True)
    kind: Mapped[str] = mapped_column(String(12), default="info")           # product | price | service | policy | place |
    title: Mapped[str] = mapped_column(String(200), default="")             # people | hours | faq | info
    text: Mapped[str] = mapped_column(Text, default="")
    words: Mapped[str] = mapped_column(Text, default="")                    # search words (lower case)
    status: Mapped[str] = mapped_column(String(10), default="draft")        # draft | approved
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class CcCampaign(Base):
    """A call list Hoola calls by itself: HER people, HER approved script, started only by her tap."""
    __tablename__ = "callcentre_campaigns"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("cccmp"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    name: Mapped[str] = mapped_column(String(120), default="")
    goal: Mapped[str] = mapped_column(Text, default="")                     # why Hoola calls (said in the opening)
    purpose: Mapped[str] = mapped_column(String(16), default="sales")       # sales | followup | renewal | dues | appointment |
    status: Mapped[str] = mapped_column(String(10), default="draft")        # feedback | reminder | survey | service
    country: Mapped[str] = mapped_column(String(2), default="IN")           # draft | ready | running | paused | done | stopped
    basis: Mapped[str] = mapped_column(String(10), default="asked")         # asked | customer | cold (what she said of the list)
    start_hour: Mapped[str] = mapped_column(String(5), default="10:00")
    end_hour: Mapped[str] = mapped_column(String(5), default="19:00")
    at_once: Mapped[int] = mapped_column(Integer, default=2)
    max_tries: Mapped[int] = mapped_column(Integer, default=3)
    retry_min: Mapped[int] = mapped_column(Integer, default=120)
    daily_cap: Mapped[float] = mapped_column(Float, default=0.0)            # money a day (her currency); 0 = no calls
    voicemail: Mapped[str] = mapped_column(Text, default="")                # the message left on an answering machine
    fields: Mapped[str] = mapped_column(Text, default="[]")                 # [{name, ask}] answers Hoola must bring back
    start_hash: Mapped[str] = mapped_column(String(32), default="")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class CcTarget(Base):
    """One person on a call list (from HER data only)."""
    __tablename__ = "callcentre_targets"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("cct"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    campaign_id: Mapped[str] = mapped_column(String(40), index=True)
    name: Mapped[str] = mapped_column(String(120), default="")
    phone: Mapped[str] = mapped_column(String(20), default="", index=True)  # E.164
    country: Mapped[str] = mapped_column(String(2), default="")
    tz: Mapped[str] = mapped_column(String(40), default="")
    lang: Mapped[str] = mapped_column(String(8), default="")
    basis: Mapped[str] = mapped_column(String(10), default="")              # asked | customer | cold | unknown
    data: Mapped[str] = mapped_column(Text, default="{}")                   # her columns (need, amount, order ...)
    lead_id: Mapped[str] = mapped_column(String(40), default="")            # the Telecaller lead it came from
    status: Mapped[str] = mapped_column(String(10), default="queued")       # queued | calling | retry | done | skipped | dnd
    tries: Mapped[int] = mapped_column(Integer, default=0)
    next_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    outcome: Mapped[str] = mapped_column(String(16), default="")
    result: Mapped[str] = mapped_column(Text, default="{}")                 # the fields Hoola brought back
    why: Mapped[str] = mapped_column(Text, default="")                      # why skipped / held
    call_id: Mapped[str] = mapped_column(String(40), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
