"""Tables of the Shaadi Sahayak (all prefixed shaadi_). JSON kept in Text columns (pattern of interior / fleet)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now


class ShaadiSettings(Base):
    __tablename__ = "shaadi_settings"
    tenant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    firm: Mapped[str] = mapped_column(String(160), default="")
    mode: Mapped[str] = mapped_column(String(10), default="family")          # family (her own family) | agency (planner for clients)
    gstin: Mapped[str] = mapped_column(String(15), default="")
    phone: Mapped[str] = mapped_column(String(20), default="")
    upi_id: Mapped[str] = mapped_column(String(80), default="")
    fee_mode: Mapped[str] = mapped_column(String(10), default="none")       # none | percent | flat
    fee_value: Mapped[float] = mapped_column(Float, default=0.0)
    gst_pct: Mapped[float] = mapped_column(Float, default=18.0)             # her CA confirms (event management SAC 998596)
    stages: Mapped[str] = mapped_column(Text, default="")                   # client fee stages [{label, pct}] '' = starter
    terms: Mapped[str] = mapped_column(Text, default="")
    validity_days: Mapped[int] = mapped_column(Integer, default=15)
    morning_time: Mapped[str] = mapped_column(String(5), default="08:30")
    last_morning: Mapped[str] = mapped_column(String(10), default="")
    rules: Mapped[str] = mapped_column(Text, default="")
    wed_seq: Mapped[int] = mapped_column(Integer, default=0)
    card_seq: Mapped[int] = mapped_column(Integer, default=0)


class ShaadiWedding(Base):
    __tablename__ = "shaadi_weddings"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("sw"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(20), default="")
    title: Mapped[str] = mapped_column(String(160), default="")
    community: Mapped[str] = mapped_column(String(20), default="other")
    bride: Mapped[str] = mapped_column(String(120), default="")
    groom: Mapped[str] = mapped_column(String(120), default="")
    client: Mapped[str] = mapped_column(String(120), default="")
    client_phone: Mapped[str] = mapped_column(String(20), default="")
    city: Mapped[str] = mapped_column(String(60), default="")
    state: Mapped[str] = mapped_column(String(40), default="")
    venue: Mapped[str] = mapped_column(Text, default="")
    guests_estimate: Mapped[int] = mapped_column(Integer, default=0)
    budget: Mapped[str] = mapped_column(Text, default="{}")                 # {"total": n, "heads": {fn_id|all: {head: n}}}
    functions: Mapped[str] = mapped_column(Text, default="[]")
    checklist: Mapped[str] = mapped_column(Text, default="[]")
    status: Mapped[str] = mapped_column(String(12), default="planning")    # planning | done | cancelled
    log: Mapped[str] = mapped_column(Text, default="[]")
    forgotten: Mapped[bool] = mapped_column(Boolean, default=False)
    conv: Mapped[str] = mapped_column(String(40), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class ShaadiGuest(Base):
    __tablename__ = "shaadi_guests"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("sg"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    wedding_id: Mapped[str] = mapped_column(String(40), index=True)
    name: Mapped[str] = mapped_column(String(120), default="")
    side: Mapped[str] = mapped_column(String(8), default="common")
    grp: Mapped[str] = mapped_column(String(60), default="")
    phone: Mapped[str] = mapped_column(String(20), default="")
    adults: Mapped[int] = mapped_column(Integer, default=1)
    kids: Mapped[int] = mapped_column(Integer, default=0)
    invited: Mapped[str] = mapped_column(Text, default="[]")               # function ids ([] = all)
    rsvp: Mapped[str] = mapped_column(Text, default="{}")                  # {fn_id: yes|no|maybe|pending}
    diet: Mapped[str] = mapped_column(String(20), default="")
    city: Mapped[str] = mapped_column(String(60), default="")
    needs_room: Mapped[bool] = mapped_column(Boolean, default=False)
    room_id: Mapped[str] = mapped_column(String(40), default="")
    arrive: Mapped[str] = mapped_column(String(16), default="")             # YYYY-MM-DD[ HH:MM]
    depart: Mapped[str] = mapped_column(String(16), default="")
    travel: Mapped[str] = mapped_column(Text, default="{}")                # {mode, from, trip}
    notes: Mapped[str] = mapped_column(Text, default="")
    no_messages: Mapped[bool] = mapped_column(Boolean, default=False)
    invite_sent: Mapped[str] = mapped_column(Text, default="[]")           # message card ids she marked sent


class ShaadiRoom(Base):
    __tablename__ = "shaadi_rooms"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("sr"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    wedding_id: Mapped[str] = mapped_column(String(40), index=True)
    place: Mapped[str] = mapped_column(String(120), default="")             # hotel / homestay / relative's home
    label: Mapped[str] = mapped_column(String(40), default="")
    capacity: Mapped[int] = mapped_column(Integer, default=2)
    check_in: Mapped[str] = mapped_column(String(10), default="")
    check_out: Mapped[str] = mapped_column(String(10), default="")
    rate: Mapped[float | None] = mapped_column(Float, nullable=True)        # her number per night (hotel's quote)
    notes: Mapped[str] = mapped_column(Text, default="")


class ShaadiVendor(Base):
    __tablename__ = "shaadi_vendors"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("sv"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    wedding_id: Mapped[str] = mapped_column(String(40), index=True)
    name: Mapped[str] = mapped_column(String(120), default="")
    kind: Mapped[str] = mapped_column(String(20), default="other")
    phone: Mapped[str] = mapped_column(String(20), default="")
    functions: Mapped[str] = mapped_column(Text, default="[]")             # function ids ([] = all)
    quote: Mapped[float | None] = mapped_column(Float, nullable=True)      # HER word: what the vendor quoted (incl. GST as quoted)
    quote_note: Mapped[str] = mapped_column(Text, default="")              # what's included, in her words
    per_plate: Mapped[float | None] = mapped_column(Float, nullable=True)
    plates: Mapped[int | None] = mapped_column(Integer, nullable=True)
    schedule: Mapped[str] = mapped_column(Text, default="[]")              # [{id, label, amount, due, status, ref, paid_on}]
    status: Mapped[str] = mapped_column(String(12), default="quoted")      # quoted | waiting | booked | rejected | cancelled | done
    notes: Mapped[str] = mapped_column(Text, default="")


class ShaadiCard(Base):
    """Everything that waits for HER tap: vendor_book, vendor_pay, spend, client_quote, client_pay, message."""
    __tablename__ = "shaadi_cards"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("sc"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    wedding_id: Mapped[str] = mapped_column(String(40), index=True)
    number: Mapped[str] = mapped_column(String(20), default="")
    kind: Mapped[str] = mapped_column(String(14), default="")
    ref: Mapped[str] = mapped_column(String(40), default="")                # vendor id / schedule id / guest filter
    show: Mapped[str] = mapped_column(Text, default="{}")                  # exactly what the card shows (hashed)
    amount: Mapped[float] = mapped_column(Float, default=0.0)
    money: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(10), default="waiting")     # waiting | approved | rejected | stale | done
    hash: Mapped[str] = mapped_column(String(64), default="")
    asked_by: Mapped[str] = mapped_column(String(80), default="")
    result: Mapped[str] = mapped_column(Text, default="{}")
    reason: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ShaadiGift(Base):
    """Shagun / gift register: owner only, never shared, never shown to staff or other avatars."""
    __tablename__ = "shaadi_gifts"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("sgf"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    wedding_id: Mapped[str] = mapped_column(String(40), index=True)
    giver: Mapped[str] = mapped_column(String(120), default="")
    relation: Mapped[str] = mapped_column(String(60), default="")
    side: Mapped[str] = mapped_column(String(8), default="common")
    for_whom: Mapped[str] = mapped_column(String(8), default="both")       # bride | groom | both
    function_id: Mapped[str] = mapped_column(String(40), default="")
    kind: Mapped[str] = mapped_column(String(10), default="cash")         # cash | upi | cheque | gold | item | other
    what: Mapped[str] = mapped_column(Text, default="")
    value: Mapped[float | None] = mapped_column(Float, nullable=True)       # cash amount / approximate value (her word)
    day: Mapped[str] = mapped_column(String(10), default="")
    note: Mapped[str] = mapped_column(Text, default="")


class ShaadiAlert(Base):
    __tablename__ = "shaadi_alerts"
    key: Mapped[str] = mapped_column(String(200), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
