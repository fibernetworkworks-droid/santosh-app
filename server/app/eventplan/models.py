"""Tables of the Event Sahayak (all prefixed eventplan_). JSON kept in Text columns (pattern of interior / fleet)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now


class EpSettings(Base):
    __tablename__ = "eventplan_settings"
    tenant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    firm: Mapped[str] = mapped_column(String(160), default="")
    gstin: Mapped[str] = mapped_column(String(15), default="")
    state_code: Mapped[str] = mapped_column(String(2), default="")
    address: Mapped[str] = mapped_column(Text, default="")
    phone: Mapped[str] = mapped_column(String(20), default="")
    email: Mapped[str] = mapped_column(String(120), default="")
    upi_id: Mapped[str] = mapped_column(String(80), default="")
    margin_pct: Mapped[float] = mapped_column(Float, default=15.0)          # her default mark-up on vendor cost
    head_margins: Mapped[str] = mapped_column(Text, default="{}")           # {head: pct}
    fee_mode: Mapped[str] = mapped_column(String(10), default="markup")    # markup | fee (cost at actual + her fee %) | none
    fee_pct: Mapped[float] = mapped_column(Float, default=0.0)
    gst_pct: Mapped[float] = mapped_column(Float, default=18.0)             # event management SAC 998596 (her CA confirms)
    sac: Mapped[str] = mapped_column(String(10), default="998596")
    validity_days: Mapped[int] = mapped_column(Integer, default=10)
    terms: Mapped[str] = mapped_column(Text, default="")
    sound_till: Mapped[str] = mapped_column(String(5), default="22:00")     # loudspeaker cut-off (Noise Rules); her state may relax
    morning_time: Mapped[str] = mapped_column(String(5), default="08:30")
    last_morning: Mapped[str] = mapped_column(String(10), default="")
    team: Mapped[str] = mapped_column(Text, default="[]")                    # [{name, phone, role}]
    rules: Mapped[str] = mapped_column(Text, default="")
    ev_seq: Mapped[int] = mapped_column(Integer, default=0)
    doc_seq: Mapped[int] = mapped_column(Integer, default=0)
    inv_seq: Mapped[int] = mapped_column(Integer, default=0)
    bk_seq: Mapped[int] = mapped_column(Integer, default=0)
    sp_seq: Mapped[int] = mapped_column(Integer, default=0)


class EpEvent(Base):
    __tablename__ = "eventplan_events"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("ev"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(20), default="")
    name: Mapped[str] = mapped_column(String(160), default="")
    kind: Mapped[str] = mapped_column(String(20), default="other")
    client: Mapped[str] = mapped_column(String(120), default="")
    client_phone: Mapped[str] = mapped_column(String(20), default="")
    client_email: Mapped[str] = mapped_column(String(120), default="")
    client_gstin: Mapped[str] = mapped_column(String(15), default="")
    client_state: Mapped[str] = mapped_column(String(2), default="")
    day: Mapped[str] = mapped_column(String(10), default="")                # YYYY-MM-DD
    start: Mapped[str] = mapped_column(String(5), default="")
    end: Mapped[str] = mapped_column(String(5), default="")
    venue: Mapped[str] = mapped_column(Text, default="")
    city: Mapped[str] = mapped_column(String(60), default="")
    headcount: Mapped[int] = mapped_column(Integer, default=0)
    budget: Mapped[float | None] = mapped_column(Float, nullable=True)      # client's budget (their words)
    facts: Mapped[str] = mapped_column(Text, default="{}")                  # venue_kind, sound, food, music, alcohol, pandal ...
    brief: Mapped[str] = mapped_column(Text, default="")
    budget_lines: Mapped[str] = mapped_column(Text, default="[]")
    cues: Mapped[str] = mapped_column(Text, default="[]")
    permits: Mapped[str] = mapped_column(Text, default="[]")
    report: Mapped[str] = mapped_column(Text, default="{}")
    status: Mapped[str] = mapped_column(String(14), default="enquiry")     # enquiry|planning|confirmed|live|done|cancelled
    accepted_doc: Mapped[str] = mapped_column(String(40), default="")
    client_paid: Mapped[str] = mapped_column(Text, default="[]")            # [{amount, ref, on}] her word
    log: Mapped[str] = mapped_column(Text, default="[]")
    forgotten: Mapped[bool] = mapped_column(Boolean, default=False)
    conv: Mapped[str] = mapped_column(String(40), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class EpVendor(Base):
    __tablename__ = "eventplan_vendors"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("epv"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    name: Mapped[str] = mapped_column(String(120), default="")
    head: Mapped[str] = mapped_column(String(20), default="misc")
    phone: Mapped[str] = mapped_column(String(20), default="")
    upi_id: Mapped[str] = mapped_column(String(80), default="")
    gstin: Mapped[str] = mapped_column(String(15), default="")
    fssai: Mapped[str] = mapped_column(String(14), default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class EpVendorQuote(Base):
    """What a vendor quoted HER (never invented)."""
    __tablename__ = "eventplan_vquotes"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("epq"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    event_id: Mapped[str] = mapped_column(String(40), index=True)
    vendor_id: Mapped[str] = mapped_column(String(40), default="")
    head: Mapped[str] = mapped_column(String(20), default="misc")
    what: Mapped[str] = mapped_column(Text, default="")
    amount: Mapped[float] = mapped_column(Float, default=0.0)               # as quoted
    gst_included: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    gst_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    per: Mapped[str] = mapped_column(String(10), default="")                # '' | plate | person | hour | day
    qty: Mapped[float | None] = mapped_column(Float, nullable=True)
    advance_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    cancel_terms: Mapped[str] = mapped_column(Text, default="")
    includes: Mapped[str] = mapped_column(Text, default="")
    valid_till: Mapped[str] = mapped_column(String(10), default="")
    file_id: Mapped[str] = mapped_column(String(60), default="")
    chosen: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class EpBooking(Base):
    """Vendor booking (+ advance) card: only her tap (+ fingerprint when an advance goes)."""
    __tablename__ = "eventplan_bookings"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("epb"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    event_id: Mapped[str] = mapped_column(String(40), index=True)
    vendor_id: Mapped[str] = mapped_column(String(40), default="")
    quote_id: Mapped[str] = mapped_column(String(40), default="")
    number: Mapped[str] = mapped_column(String(20), default="")
    head: Mapped[str] = mapped_column(String(20), default="misc")
    amount: Mapped[float] = mapped_column(Float, default=0.0)
    advance: Mapped[float] = mapped_column(Float, default=0.0)
    advance_due: Mapped[str] = mapped_column(String(10), default="")
    arrive: Mapped[str] = mapped_column(String(5), default="")              # vendor arrival / setup time on the day
    terms: Mapped[str] = mapped_column(Text, default="")
    checks: Mapped[str] = mapped_column(Text, default="[]")
    status: Mapped[str] = mapped_column(String(12), default="waiting")     # waiting|approved|rejected|advance_paid|cancelled
    hash: Mapped[str] = mapped_column(String(64), default="")
    paid: Mapped[float] = mapped_column(Float, default=0.0)
    paid_ref: Mapped[str] = mapped_column(String(80), default="")
    asked_by: Mapped[str] = mapped_column(String(80), default="")
    reason: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class EpDoc(Base):
    """Client quotation or invoice: goes out only on her tap."""
    __tablename__ = "eventplan_docs"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("epd"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    event_id: Mapped[str] = mapped_column(String(40), index=True)
    kind: Mapped[str] = mapped_column(String(10), default="quote")          # quote | invoice
    number: Mapped[str] = mapped_column(String(30), default="")
    lines: Mapped[str] = mapped_column(Text, default="[]")
    totals: Mapped[str] = mapped_column(Text, default="{}")
    blanks: Mapped[str] = mapped_column(Text, default="[]")
    status: Mapped[str] = mapped_column(String(12), default="draft")       # draft|waiting|approved|sent|accepted|rejected|superseded
    hash: Mapped[str] = mapped_column(String(64), default="")
    valid_until: Mapped[str] = mapped_column(String(10), default="")
    file_id: Mapped[str] = mapped_column(String(60), default="")
    reason: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class EpSpend(Base):
    """Any other spend (permit fee, transport, petty): only her tap (+ fingerprint)."""
    __tablename__ = "eventplan_spends"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("eps"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    event_id: Mapped[str] = mapped_column(String(40), index=True)
    number: Mapped[str] = mapped_column(String(20), default="")
    head: Mapped[str] = mapped_column(String(20), default="misc")
    what: Mapped[str] = mapped_column(Text, default="")
    payee: Mapped[str] = mapped_column(String(120), default="")
    amount: Mapped[float] = mapped_column(Float, default=0.0)
    checks: Mapped[str] = mapped_column(Text, default="[]")
    status: Mapped[str] = mapped_column(String(12), default="waiting")     # waiting|approved|rejected|paid
    hash: Mapped[str] = mapped_column(String(64), default="")
    paid_ref: Mapped[str] = mapped_column(String(80), default="")
    asked_by: Mapped[str] = mapped_column(String(80), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class EpMessage(Base):
    """Invites / messages to guests, vendors or the client: drafts; the links appear only after her tap."""
    __tablename__ = "eventplan_messages"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("epm"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    event_id: Mapped[str] = mapped_column(String(40), index=True)
    kind: Mapped[str] = mapped_column(String(12), default="invite")         # invite|reminder|vendor|client|custom
    text: Mapped[str] = mapped_column(Text, default="")
    to: Mapped[str] = mapped_column(Text, default="[]")                     # [{name, phone, guest_id|vendor_id}]
    status: Mapped[str] = mapped_column(String(12), default="waiting")     # waiting|approved|rejected|sent
    hash: Mapped[str] = mapped_column(String(64), default="")
    asked_by: Mapped[str] = mapped_column(String(80), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class EpGuest(Base):
    __tablename__ = "eventplan_guests"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("epg"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    event_id: Mapped[str] = mapped_column(String(40), index=True)
    name: Mapped[str] = mapped_column(String(120), default="")
    phone: Mapped[str] = mapped_column(String(20), default="")
    group: Mapped[str] = mapped_column(String(60), default="")
    invited: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(8), default="")              # '' | yes | no | maybe
    plus: Mapped[int] = mapped_column(Integer, default=0)
    note: Mapped[str] = mapped_column(Text, default="")
    no_messages: Mapped[bool] = mapped_column(Boolean, default=False)
    came: Mapped[bool | None] = mapped_column(Boolean, nullable=True)


class EpTask(Base):
    __tablename__ = "eventplan_tasks"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("ept"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    event_id: Mapped[str] = mapped_column(String(40), index=True)
    what: Mapped[str] = mapped_column(String(200), default="")
    area: Mapped[str] = mapped_column(String(20), default="")
    owner: Mapped[str] = mapped_column(String(80), default="")
    due: Mapped[str] = mapped_column(String(10), default="")
    status: Mapped[str] = mapped_column(String(10), default="open")        # open|done|skipped
    auto: Mapped[bool] = mapped_column(Boolean, default=False)


class EpAlert(Base):
    __tablename__ = "eventplan_alerts"
    key: Mapped[str] = mapped_column(String(200), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
