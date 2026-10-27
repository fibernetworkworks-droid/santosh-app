"""Tables of the Front Office Sahayak (hotel / lodge / guest house front desk). All prefixed frontoffice_."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now


class FoSettings(Base):
    __tablename__ = "frontoffice_settings"
    tenant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    hotel_name: Mapped[str] = mapped_column(String(160), default="")
    address: Mapped[str] = mapped_column(Text, default="")
    city: Mapped[str] = mapped_column(String(80), default="")
    state: Mapped[str] = mapped_column(String(40), default="")                 # for Form C / place of supply notes
    phone: Mapped[str] = mapped_column(String(16), default="")
    email: Mapped[str] = mapped_column(String(160), default="")
    gstin: Mapped[str] = mapped_column(String(15), default="")                # "" = not registered -> no GST on bills
    specified_premises: Mapped[bool] = mapped_column(Boolean, default=False)  # restaurant 18% (any room > 7,500 last FY / her declaration)
    extra_gst: Mapped[str] = mapped_column(Text, default="{}")                # {kind: pct} her CA's rates for extras
    upi_id: Mapped[str] = mapped_column(String(120), default="")
    upi_name: Mapped[str] = mapped_column(String(80), default="")
    check_in_time: Mapped[str] = mapped_column(String(5), default="12:00")
    check_out_time: Mapped[str] = mapped_column(String(5), default="11:00")
    weekend_days: Mapped[str] = mapped_column(Text, default="[4, 5]")         # nights of Fri, Sat (Mon=0)
    cancel_policy: Mapped[str] = mapped_column(Text, default="{}")            # {free_days, fee first_night|pct|full, pct}
    hold_hours: Mapped[int] = mapped_column(Integer, default=24)
    review_link: Mapped[str] = mapped_column(Text, default="")                # her Google review link (same for every guest)
    morning_time: Mapped[str] = mapped_column(String(5), default="08:00")
    last_morning: Mapped[str] = mapped_column(String(10), default="")
    rules: Mapped[str] = mapped_column(Text, default="")
    seq: Mapped[str] = mapped_column(Text, default="{}")


class FoRoomType(Base):
    __tablename__ = "frontoffice_room_types"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("fot"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    code: Mapped[str] = mapped_column(String(12), default="")                 # DLX
    name: Mapped[str] = mapped_column(String(80), default="")                 # Deluxe
    aliases: Mapped[str] = mapped_column(Text, default="")                    # OTA names: "Deluxe Double Room, Premium"
    max_adults: Mapped[int] = mapped_column(Integer, default=2)
    base: Mapped[float] = mapped_column(Float, default=0.0)                   # HER weekday rate per night
    weekend: Mapped[float] = mapped_column(Float, default=0.0)
    seasons: Mapped[str] = mapped_column(Text, default="[]")                  # [{name, from, to, rate}]
    extra_adult: Mapped[float] = mapped_column(Float, default=0.0)            # per night (extra bed)
    extra_child: Mapped[float] = mapped_column(Float, default=0.0)
    meal_plan: Mapped[str] = mapped_column(String(4), default="EP")
    archived: Mapped[bool] = mapped_column(Boolean, default=False)


class FoRoom(Base):
    __tablename__ = "frontoffice_rooms"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("for"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(12), default="")               # 101
    type_id: Mapped[str] = mapped_column(String(40), index=True)
    floor: Mapped[str] = mapped_column(String(12), default="")
    status: Mapped[str] = mapped_column(String(14), default="clean")          # dirty | clean | inspected | out_of_order
    ooo_from: Mapped[str] = mapped_column(String(10), default="")
    ooo_until: Mapped[str] = mapped_column(String(10), default="")            # "" with out_of_order = till she says
    ooo_reason: Mapped[str] = mapped_column(String(200), default="")
    archived: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str] = mapped_column(Text, default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class FoGuest(Base):
    """A guest. ID numbers only as Pehchaan Locker references ({id:...} + masked)."""
    __tablename__ = "frontoffice_guests"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("fog"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(12), default="")               # G-0001
    name: Mapped[str] = mapped_column(String(160), default="")
    phone: Mapped[str] = mapped_column(String(10), default="", index=True)
    email: Mapped[str] = mapped_column(String(160), default="")
    address: Mapped[str] = mapped_column(Text, default="")
    nationality: Mapped[str] = mapped_column(String(40), default="Indian")
    gstin: Mapped[str] = mapped_column(String(15), default="")                # company guest (B2B bill)
    company: Mapped[str] = mapped_column(String(160), default="")
    ids: Mapped[str] = mapped_column(Text, default="{}")                      # {kind: {ref, masked, record}}
    visa: Mapped[str] = mapped_column(Text, default="{}")                     # {type, expiry, issued_at, number: {ref, masked, record}}
    arrived_india_on: Mapped[str] = mapped_column(String(10), default="")
    no_messages: Mapped[bool] = mapped_column(Boolean, default=False)
    forgotten: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class FoBooking(Base):
    __tablename__ = "frontoffice_bookings"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("fob"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(12), default="")               # R-0001
    guest_id: Mapped[str] = mapped_column(String(40), index=True, default="")
    source: Mapped[str] = mapped_column(String(14), default="walk_in")
    ota_ref: Mapped[str] = mapped_column(String(40), default="", index=True)
    type_id: Mapped[str] = mapped_column(String(40), index=True, default="")
    room_id: Mapped[str] = mapped_column(String(40), index=True, default="")
    arrive: Mapped[str] = mapped_column(String(10), default="")
    depart: Mapped[str] = mapped_column(String(10), default="")
    adults: Mapped[int] = mapped_column(Integer, default=1)
    children: Mapped[int] = mapped_column(Integer, default=0)
    meal_plan: Mapped[str] = mapped_column(String(4), default="EP")
    nights: Mapped[str] = mapped_column(Text, default="[]")                   # [{date, rate (None = blank), why}]
    discount: Mapped[float] = mapped_column(Float, default=0.0)               # APPROVED discount (her tap)
    complimentary: Mapped[bool] = mapped_column(Boolean, default=False)       # APPROVED comp (her tap)
    status: Mapped[str] = mapped_column(String(12), default="confirmed")      # hold | confirmed | in_house | checked_out | cancelled | no_show
    hold_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ota_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    paid_online: Mapped[bool] = mapped_column(Boolean, default=False)
    pay_at_hotel: Mapped[float | None] = mapped_column(Float, nullable=True)
    commission: Mapped[float | None] = mapped_column(Float, nullable=True)
    policy: Mapped[str] = mapped_column(Text, default="{}")                   # cancellation policy at booking time
    companions: Mapped[str] = mapped_column(Text, default="[]")
    purpose: Mapped[str] = mapped_column(String(80), default="")
    coming_from: Mapped[str] = mapped_column(String(120), default="")
    going_to: Mapped[str] = mapped_column(String(120), default="")
    checked_in_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    checked_out_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancel_fee: Mapped[float] = mapped_column(Float, default=0.0)
    alerts: Mapped[str] = mapped_column(Text, default="[]")
    notes: Mapped[str] = mapped_column(Text, default="")
    created_by: Mapped[str] = mapped_column(String(60), default="Owner")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class FoCharge(Base):
    """Folio line other than room nights (food, laundry, extra bed, cancellation fee ...)."""
    __tablename__ = "frontoffice_charges"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("foc"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    booking_id: Mapped[str] = mapped_column(String(40), index=True)
    kind: Mapped[str] = mapped_column(String(16), default="other")
    text: Mapped[str] = mapped_column(String(200), default="")
    qty: Mapped[float] = mapped_column(Float, default=1.0)
    rate: Mapped[float] = mapped_column(Float, default=0.0)
    on: Mapped[str] = mapped_column(String(10), default="")
    by: Mapped[str] = mapped_column(String(60), default="Owner")
    void: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class FoPayment(Base):
    __tablename__ = "frontoffice_payments"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("fop"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    booking_id: Mapped[str] = mapped_column(String(40), index=True)
    receipt_no: Mapped[str] = mapped_column(String(24), default="")
    amount: Mapped[float] = mapped_column(Float, default=0.0)                 # refunds are negative
    mode: Mapped[str] = mapped_column(String(8), default="upi")               # upi | cash | card | bank | ota
    ref_tail: Mapped[str] = mapped_column(String(8), default="")
    on: Mapped[str] = mapped_column(String(10), default="")
    by: Mapped[str] = mapped_column(String(60), default="Owner")
    void: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class FoBill(Base):
    __tablename__ = "frontoffice_bills"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("fbl"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    booking_id: Mapped[str] = mapped_column(String(40), index=True)
    number: Mapped[str] = mapped_column(String(24), default="")               # INV/2627/0001 only when final
    status: Mapped[str] = mapped_column(String(8), default="draft")           # draft | final
    data: Mapped[str] = mapped_column(Text, default="{}")                     # lines + totals frozen at her tap
    final_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    file_id: Mapped[str] = mapped_column(String(60), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class FoCard(Base):
    """A card only HER app tap decides: discount | comp | cancel_fee | refund | bill."""
    __tablename__ = "frontoffice_cards"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("fok"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(12), default="")               # C-0001
    kind: Mapped[str] = mapped_column(String(12), default="")
    target: Mapped[str] = mapped_column(String(40), default="", index=True)   # booking id
    show: Mapped[str] = mapped_column(Text, default="{}")
    hash: Mapped[str] = mapped_column(String(64), default="")
    status: Mapped[str] = mapped_column(String(10), default="waiting")        # waiting | approved | rejected | stale
    reason: Mapped[str] = mapped_column(String(300), default="")
    asked_by: Mapped[str] = mapped_column(String(60), default="Owner")
    conv: Mapped[str] = mapped_column(String(40), default="")
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class FoMessage(Base):
    """A message for a guest: always a DRAFT until her tap sends it."""
    __tablename__ = "frontoffice_messages"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("fom"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    booking_id: Mapped[str] = mapped_column(String(40), index=True)
    guest_id: Mapped[str] = mapped_column(String(40), default="")
    kind: Mapped[str] = mapped_column(String(14), default="custom")           # confirmation | pre_arrival | payment | review | bill | cancel | custom
    text: Mapped[str] = mapped_column(Text, default="")
    hash: Mapped[str] = mapped_column(String(64), default="")
    status: Mapped[str] = mapped_column(String(8), default="draft")           # draft | sent | dropped
    via: Mapped[str] = mapped_column(String(10), default="")
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class FoFormC(Base):
    """Form III (C-Form) entry for a foreign guest: arrival or departure, due 24 h after; SHE submits on indianfrro.gov.in."""
    __tablename__ = "frontoffice_formc"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("foc3"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    booking_id: Mapped[str] = mapped_column(String(40), index=True)
    guest_id: Mapped[str] = mapped_column(String(40), index=True)
    kind: Mapped[str] = mapped_column(String(10), default="arrival")          # arrival | departure
    event_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(10), default="due")            # due | submitted
    ref: Mapped[str] = mapped_column(String(60), default="")
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class FoAlert(Base):
    __tablename__ = "frontoffice_alerts"
    key: Mapped[str] = mapped_column(String(200), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
