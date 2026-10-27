"""Tables of the Banquet Sahayak (all prefixed banquet_). JSON kept in Text columns (pattern of interior / fleet)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now


class BanquetSettings(Base):
    __tablename__ = "banquet_settings"
    tenant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    venue: Mapped[str] = mapped_column(String(160), default="")
    gstin: Mapped[str] = mapped_column(String(15), default="")
    address: Mapped[str] = mapped_column(Text, default="")
    phone: Mapped[str] = mapped_column(String(20), default="")
    email: Mapped[str] = mapped_column(String(120), default="")
    upi_id: Mapped[str] = mapped_column(String(80), default="")
    specified: Mapped[bool] = mapped_column(Boolean, default=False)       # 'specified premises' (hotel with a room > Rs 7,500 / opt-in)
    gst_food: Mapped[float | None] = mapped_column(Float, nullable=True)  # None = 5 / 18 by `specified`
    gst_hall: Mapped[float] = mapped_column(Float, default=18.0)          # hall rent WITHOUT her food
    gst_extra: Mapped[float] = mapped_column(Float, default=18.0)
    slots: Mapped[str] = mapped_column(Text, default="")                  # {slot: {from, to}}
    hold_hours: Mapped[int] = mapped_column(Integer, default=48)
    lock_days: Mapped[int] = mapped_column(Integer, default=3)
    stages: Mapped[str] = mapped_column(Text, default="")                 # payment schedule [{label, pct, days_before}]
    cancel: Mapped[str] = mapped_column(Text, default="")                 # [{days_before, refund_pct}]
    terms: Mapped[str] = mapped_column(Text, default="")
    music_end: Mapped[str] = mapped_column(String(5), default="22:00")
    validity_days: Mapped[int] = mapped_column(Integer, default=7)
    morning_time: Mapped[str] = mapped_column(String(5), default="09:00")
    last_morning: Mapped[str] = mapped_column(String(10), default="")
    rules: Mapped[str] = mapped_column(Text, default="")
    enq_seq: Mapped[int] = mapped_column(Integer, default=0)
    bk_seq: Mapped[int] = mapped_column(Integer, default=0)
    rc_seq: Mapped[int] = mapped_column(Integer, default=0)


class BanquetHall(Base):
    __tablename__ = "banquet_halls"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("bh"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    name: Mapped[str] = mapped_column(String(120), default="")
    kind: Mapped[str] = mapped_column(String(12), default="hall")
    seated: Mapped[int] = mapped_column(Integer, default=0)
    floating: Mapped[int] = mapped_column(Integer, default=0)
    rent: Mapped[float | None] = mapped_column(Float, nullable=True)      # HER rent per slot (None = only with food / not said)
    rent_full: Mapped[float | None] = mapped_column(Float, nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class BanquetPackage(Base):
    __tablename__ = "banquet_packages"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("bp"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    name: Mapped[str] = mapped_column(String(120), default="")
    diet: Mapped[str] = mapped_column(String(8), default="veg")
    price: Mapped[float] = mapped_column(Float, default=0.0)               # HER price per plate before GST
    items: Mapped[str] = mapped_column(Text, default="[]")
    min_plates: Mapped[int] = mapped_column(Integer, default=0)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class BanquetExtra(Base):
    __tablename__ = "banquet_extras"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("bx"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    name: Mapped[str] = mapped_column(String(120), default="")
    kind: Mapped[str] = mapped_column(String(10), default="other")
    price: Mapped[float] = mapped_column(Float, default=0.0)
    unit: Mapped[str] = mapped_column(String(10), default="event")        # event | plate | room_night | hour | nos
    gst_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class BanquetLead(Base):
    __tablename__ = "banquet_leads"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("bl"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(12), default="")
    name: Mapped[str] = mapped_column(String(120), default="")
    phone: Mapped[str] = mapped_column(String(20), default="")
    source: Mapped[str] = mapped_column(String(16), default="call")       # call | whatsapp | walk_in | paste | website | referral
    event_type: Mapped[str] = mapped_column(String(20), default="")
    day: Mapped[str] = mapped_column(String(10), default="")
    slot: Mapped[str] = mapped_column(String(8), default="")
    guests: Mapped[int | None] = mapped_column(Integer, nullable=True)
    diet: Mapped[str] = mapped_column(String(8), default="")
    budget: Mapped[float | None] = mapped_column(Float, nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(10), default="new")        # new|contacted|visit|quoted|hold|booked|lost
    lost_reason: Mapped[str] = mapped_column(Text, default="")
    follow_up: Mapped[str] = mapped_column(String(10), default="")
    tele_lead: Mapped[str] = mapped_column(String(40), default="")
    booking_id: Mapped[str] = mapped_column(String(40), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class BanquetBooking(Base):
    __tablename__ = "banquet_bookings"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("bb"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(12), default="")
    lead_id: Mapped[str] = mapped_column(String(40), default="")
    hall_id: Mapped[str] = mapped_column(String(40), default="")
    day: Mapped[str] = mapped_column(String(10), default="", index=True)
    slot: Mapped[str] = mapped_column(String(8), default="evening")
    event_type: Mapped[str] = mapped_column(String(20), default="other")
    client: Mapped[str] = mapped_column(String(120), default="")
    phone: Mapped[str] = mapped_column(String(20), default="")
    email: Mapped[str] = mapped_column(String(120), default="")
    client_gstin: Mapped[str] = mapped_column(String(15), default="")
    guests: Mapped[int | None] = mapped_column(Integer, nullable=True)     # expected
    guarantee: Mapped[int | None] = mapped_column(Integer, nullable=True)  # minimum plates billed
    final_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    actual_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    locked: Mapped[bool] = mapped_column(Boolean, default=False)
    menu: Mapped[str] = mapped_column(Text, default="[]")                 # [{package_id, plates or share}]
    extras: Mapped[str] = mapped_column(Text, default="[]")               # [{extra_id or name, qty, price}]
    hall_rent: Mapped[bool] = mapped_column(Boolean, default=True)        # charge her hall rent line
    discount: Mapped[float] = mapped_column(Float, default=0.0)           # approved by her tap only
    discount_note: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(10), default="draft")      # draft|hold|confirmed|done|cancelled
    hold_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    quote_no: Mapped[int] = mapped_column(Integer, default=0)
    quote_sent: Mapped[str] = mapped_column(Text, default="")             # hash of the quote she approved
    contract_ok: Mapped[str] = mapped_column(Text, default="")
    payments: Mapped[str] = mapped_column(Text, default="[]")             # [{id, receipt, amount, mode, ref, day, kind}]
    stages: Mapped[str] = mapped_column(Text, default="[]")               # snapshot at confirm [{label, pct, amount, due}]
    bill: Mapped[str] = mapped_column(Text, default="{}")
    beo_notes: Mapped[str] = mapped_column(Text, default="")
    timeline: Mapped[str] = mapped_column(Text, default="[]")             # [{at, what}]
    notes: Mapped[str] = mapped_column(Text, default="")
    cancel: Mapped[str] = mapped_column(Text, default="{}")
    log: Mapped[str] = mapped_column(Text, default="[]")
    forgotten: Mapped[bool] = mapped_column(Boolean, default=False)
    conv: Mapped[str] = mapped_column(String(40), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class BanquetBlock(Base):
    """One hall + day + slot held or confirmed. Clashes are refused in code under the module lock."""
    __tablename__ = "banquet_blocks"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("bk"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    hall_id: Mapped[str] = mapped_column(String(40), index=True)
    day: Mapped[str] = mapped_column(String(10), index=True)
    slot: Mapped[str] = mapped_column(String(8))
    kind: Mapped[str] = mapped_column(String(10), default="hold")         # hold | confirmed | closed (her own block)
    booking_id: Mapped[str] = mapped_column(String(40), default="")
    note: Mapped[str] = mapped_column(Text, default="")
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class BanquetCard(Base):
    """Everything that waits for HER tap: quote | contract | confirm | discount | refund | message | pay | bill."""
    __tablename__ = "banquet_cards"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("bc"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    booking_id: Mapped[str] = mapped_column(String(40), index=True, default="")
    kind: Mapped[str] = mapped_column(String(10))
    show: Mapped[str] = mapped_column(Text, default="{}")
    hash: Mapped[str] = mapped_column(String(64), default="")
    status: Mapped[str] = mapped_column(String(10), default="waiting")    # waiting|approved|rejected|stale
    asked_by: Mapped[str] = mapped_column(String(80), default="")
    reason: Mapped[str] = mapped_column(Text, default="")
    result: Mapped[str] = mapped_column(Text, default="{}")
    conv: Mapped[str] = mapped_column(String(40), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class BanquetAlert(Base):
    __tablename__ = "banquet_alerts"
    key: Mapped[str] = mapped_column(String(200), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
