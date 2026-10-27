"""Tables of the Tour Guide Sahayak. All prefixed tourguide_."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now


class TgSettings(Base):
    __tablename__ = "tourguide_settings"
    tenant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    business: Mapped[str] = mapped_column(String(160), default="")
    guide_name: Mapped[str] = mapped_column(String(120), default="")
    phone: Mapped[str] = mapped_column(String(16), default="")
    city: Mapped[str] = mapped_column(String(80), default="")
    state: Mapped[str] = mapped_column(String(4), default="")
    upi_id: Mapped[str] = mapped_column(String(120), default="")              # "" = Employee profile UPI ID
    upi_name: Mapped[str] = mapped_column(String(80), default="")
    gstin: Mapped[str] = mapped_column(String(15), default="")
    gst_mode: Mapped[str] = mapped_column(String(8), default="none")          # none | guide | tour5 | tour18 (note only)
    languages: Mapped[str] = mapped_column(Text, default="[]")                # her guiding languages
    cancel_policy: Mapped[str] = mapped_column(Text, default="")              # her words, shown upfront in every confirmation
    review_link: Mapped[str] = mapped_column(String(300), default="")         # her Google / TripAdvisor review link
    parallel_tours: Mapped[int] = mapped_column(Integer, default=1)           # how many tours can run at the same time (her team)
    morning_time: Mapped[str] = mapped_column(String(5), default="08:00")
    last_morning: Mapped[str] = mapped_column(String(10), default="")
    rules: Mapped[str] = mapped_column(Text, default="")
    seq: Mapped[str] = mapped_column(Text, default="{}")


class TgTour(Base):
    """A tour product: HER price / duration / group size; places with timings only as she gave them."""
    __tablename__ = "tourguide_tours"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("tgt"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(12), default="")               # TP-01
    title: Mapped[str] = mapped_column(String(160), default="")
    kind: Mapped[str] = mapped_column(String(12), default="city_walk")
    city: Mapped[str] = mapped_column(String(80), default="")
    duration_min: Mapped[int] = mapped_column(Integer, default=0)
    price_pp: Mapped[float | None] = mapped_column(Float, nullable=True)
    price_group: Mapped[float | None] = mapped_column(Float, nullable=True)
    group_max: Mapped[int] = mapped_column(Integer, default=0)                # 0 = she hasn't said (bookings refused)
    min_guests: Mapped[int] = mapped_column(Integer, default=1)
    meeting_point: Mapped[str] = mapped_column(Text, default="")
    includes: Mapped[str] = mapped_column(Text, default="")
    excludes: Mapped[str] = mapped_column(Text, default="")
    languages: Mapped[str] = mapped_column(Text, default="[]")
    difficulty: Mapped[str] = mapped_column(String(20), default="")
    places: Mapped[str] = mapped_column(Text, default="[]")                   # [{name, stop_min, open, close, closed_on, ticket_in, ticket_foreign, source, asi}]
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class TgBooking(Base):
    __tablename__ = "tourguide_bookings"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("tgb"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(12), default="")               # B-0001
    tour_id: Mapped[str] = mapped_column(String(40), default="")
    day: Mapped[str] = mapped_column(String(10), default="")                  # YYYY-MM-DD
    start_time: Mapped[str] = mapped_column(String(5), default="")
    lead_name: Mapped[str] = mapped_column(String(120), default="")
    phone: Mapped[str] = mapped_column(String(10), default="", index=True)
    email: Mapped[str] = mapped_column(String(160), default="")
    guests: Mapped[int] = mapped_column(Integer, default=0)
    language: Mapped[str] = mapped_column(String(12), default="")
    pickup: Mapped[str] = mapped_column(Text, default="")
    special_needs: Mapped[str] = mapped_column(Text, default="")
    emergency_name: Mapped[str] = mapped_column(String(120), default="")
    emergency_ref: Mapped[str] = mapped_column(String(40), default="")        # {id:...} in the Pehchaan Locker
    emergency_masked: Mapped[str] = mapped_column(String(20), default="")
    guest_list: Mapped[str] = mapped_column(Text, default="[]")               # [{name, age, nationality in|foreign, id_ref, id_masked}]
    source: Mapped[str] = mapped_column(String(40), default="")               # whatsapp | call | ota | walk_in | agent | website...
    price_total: Mapped[float | None] = mapped_column(Float, nullable=True)   # HER number (else from the tour)
    discount: Mapped[float] = mapped_column(Float, default=0.0)               # only via her approved card
    paid: Mapped[float] = mapped_column(Float, default=0.0)                   # what she says she received
    status: Mapped[str] = mapped_column(String(12), default="enquiry")        # enquiry | held | confirmed | done | cancelled | no_show
    roll: Mapped[str] = mapped_column(Text, default="[]")                     # [{at, checkpoint, present:[...], missing:[...]}]
    travel_trip: Mapped[str] = mapped_column(String(20), default="")          # Yatra Sahayak trip number (T-0001)
    enquiry_text: Mapped[str] = mapped_column(Text, default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    log: Mapped[str] = mapped_column(Text, default="[]")
    forgotten: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class TgCard(Base):
    """Everything that waits for HER tap: confirm (booking + message), message, refund, discount, spend."""
    __tablename__ = "tourguide_cards"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("tgc"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(12), default="")               # C-0001
    kind: Mapped[str] = mapped_column(String(12), default="message")
    target: Mapped[str] = mapped_column(String(40), default="")               # booking id ("" for a general spend)
    show: Mapped[str] = mapped_column(Text, default="{}")
    hash: Mapped[str] = mapped_column(String(64), default="")
    status: Mapped[str] = mapped_column(String(12), default="waiting")        # waiting | approved | sent | rejected | stale | done
    via: Mapped[str] = mapped_column(String(12), default="")
    reason: Mapped[str] = mapped_column(Text, default="")
    asked_by: Mapped[str] = mapped_column(String(80), default="")
    conv: Mapped[str] = mapped_column(String(40), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class TgLicence(Base):
    __tablename__ = "tourguide_licences"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("tgl"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    kind: Mapped[str] = mapped_column(String(16), default="other")
    ref: Mapped[str] = mapped_column(String(60), default="")                  # certificate / licence no (she gives)
    holder: Mapped[str] = mapped_column(String(120), default="")              # her or a team guide
    authority: Mapped[str] = mapped_column(String(160), default="")
    issued: Mapped[str] = mapped_column(String(10), default="")
    valid_to: Mapped[str] = mapped_column(String(10), default="")
    note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class TgLedger(Base):
    """Her register: commission in / out, tips, payments she received, spends / refunds she paid. Hoola moves no money."""
    __tablename__ = "tourguide_ledger"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("tgx"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    kind: Mapped[str] = mapped_column(String(16), default="tip")              # payment | tip | commission_in | commission_out | spend | refund
    booking_id: Mapped[str] = mapped_column(String(40), default="")
    amount: Mapped[float] = mapped_column(Float, default=0.0)
    party: Mapped[str] = mapped_column(String(160), default="")
    mode: Mapped[str] = mapped_column(String(12), default="")
    ref: Mapped[str] = mapped_column(String(60), default="")
    card_id: Mapped[str] = mapped_column(String(40), default="")
    on: Mapped[str] = mapped_column(String(10), default="")
    note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class TgAlert(Base):
    """Once-only keys (licence windows, day-before drafts, morning note)."""
    __tablename__ = "tourguide_alerts"
    key: Mapped[str] = mapped_column(String(200), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
