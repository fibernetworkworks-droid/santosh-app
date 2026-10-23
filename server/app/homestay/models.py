"""Tables of the Homestay Sahayak (homestay / B&B / farm stay / villa host). All prefixed homestay_."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now


class HsSettings(Base):
    __tablename__ = "homestay_settings"
    tenant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    business: Mapped[str] = mapped_column(String(160), default="")
    host_name: Mapped[str] = mapped_column(String(160), default="")
    phone: Mapped[str] = mapped_column(String(16), default="")
    address: Mapped[str] = mapped_column(Text, default="")
    city: Mapped[str] = mapped_column(String(80), default="")
    state: Mapped[str] = mapped_column(String(4), default="")
    pin: Mapped[str] = mapped_column(String(6), default="")
    map_link: Mapped[str] = mapped_column(String(300), default="")
    kind: Mapped[str] = mapped_column(String(16), default="homestay")         # homestay | bnb | farmstay | villa
    in_flat: Mapped[bool] = mapped_column(Boolean, default=False)              # in a housing society (society NOC)
    serves_food: Mapped[bool] = mapped_column(Boolean, default=False)
    upi_id: Mapped[str] = mapped_column(String(120), default="")
    upi_name: Mapped[str] = mapped_column(String(80), default="")
    gstin: Mapped[str] = mapped_column(String(15), default="")
    checkin_time: Mapped[str] = mapped_column(String(5), default="")
    checkout_time: Mapped[str] = mapped_column(String(5), default="")
    house_rules: Mapped[str] = mapped_column(Text, default="")
    checkin_info: Mapped[str] = mapped_column(Text, default="")                # directions / key / parking (no passwords)
    advance_pct: Mapped[float] = mapped_column(Float, default=0.0)
    hold_hours: Mapped[int] = mapped_column(Integer, default=24)
    policy: Mapped[str] = mapped_column(Text, default="[]")                    # [{days, pct}] HER cancellation policy
    menu: Mapped[str] = mapped_column(Text, default="{}")                      # {"breakfast": 250, "breakfast__per": "person_day"}
    count_children: Mapped[bool] = mapped_column(Boolean, default=False)
    review_link: Mapped[str] = mapped_column(String(300), default="")
    police_intimation: Mapped[bool] = mapped_column(Boolean, default=False)    # her thana asks for every guest
    registration: Mapped[str] = mapped_column(Text, default="{}")              # {number, valid_to, done: {item: on}, ...}
    staff: Mapped[str] = mapped_column(Text, default="[]")                     # [{name, phone, role}]
    morning_time: Mapped[str] = mapped_column(String(5), default="08:00")
    last_morning: Mapped[str] = mapped_column(String(10), default="")
    rules: Mapped[str] = mapped_column(Text, default="")
    seq: Mapped[str] = mapped_column(Text, default="{}")


class HsRoom(Base):
    __tablename__ = "homestay_rooms"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("hsr"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(12), default="")               # R-01
    name: Mapped[str] = mapped_column(String(80), default="")                 # "Neem room"
    kind: Mapped[str] = mapped_column(String(16), default="room")             # room | suite | cottage | dorm_bed | whole
    beds: Mapped[str] = mapped_column(String(60), default="")
    base_guests: Mapped[int] = mapped_column(Integer, default=2)
    max_guests: Mapped[int] = mapped_column(Integer, default=3)
    base_rate: Mapped[float] = mapped_column(Float, default=0.0)              # HER rate per night
    weekend_rate: Mapped[float] = mapped_column(Float, default=0.0)
    extra_person: Mapped[float] = mapped_column(Float, default=0.0)
    special: Mapped[str] = mapped_column(Text, default="{}")                  # {"2026-12-31": 6000}
    ota_names: Mapped[str] = mapped_column(Text, default="[]")                # names used on OTAs (to match mails / files)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class HsGuest(Base):
    """A guest (lead guest of a booking). ID numbers only as Pehchaan Locker references."""
    __tablename__ = "homestay_guests"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("hsg"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(12), default="")               # G-001
    name: Mapped[str] = mapped_column(String(160), default="")
    phone: Mapped[str] = mapped_column(String(20), default="", index=True)
    email: Mapped[str] = mapped_column(String(160), default="")
    country: Mapped[str] = mapped_column(String(40), default="IN")            # IN = Indian guest
    city: Mapped[str] = mapped_column(String(80), default="")
    ids: Mapped[str] = mapped_column(Text, default="[]")                      # [{kind, ref, masked, rid}]
    form_c: Mapped[str] = mapped_column(Text, default="{}")                   # non-secret Form C fields (+ passport_ref / visa_ref)
    no_messages: Mapped[bool] = mapped_column(Boolean, default=False)
    stays: Mapped[int] = mapped_column(Integer, default=0)
    forgotten: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class HsBooking(Base):
    __tablename__ = "homestay_bookings"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("hsb"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(12), default="")               # B-0001 (blocks: K-0001)
    kind: Mapped[str] = mapped_column(String(8), default="stay")              # stay | block
    rooms: Mapped[str] = mapped_column(Text, default="[]")                    # [room ids]
    guest_id: Mapped[str] = mapped_column(String(40), default="")
    source: Mapped[str] = mapped_column(String(12), default="direct")
    ota_ref: Mapped[str] = mapped_column(String(40), default="", index=True)
    ical_uid: Mapped[str] = mapped_column(String(200), default="", index=True)
    check_in: Mapped[str] = mapped_column(String(10), default="", index=True)
    check_out: Mapped[str] = mapped_column(String(10), default="")
    adults: Mapped[int] = mapped_column(Integer, default=1)
    children: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(12), default="hold")           # hold | confirmed | checked_in | checked_out | cancelled | no_show | blocked
    hold_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    addons: Mapped[str] = mapped_column(Text, default="[]")
    quote: Mapped[str] = mapped_column(Text, default="{}")                    # lines / gst / total / missing
    total: Mapped[float] = mapped_column(Float, default=0.0)                  # HER price (or OTA payout as given in her mail)
    advance: Mapped[float] = mapped_column(Float, default=0.0)
    paid: Mapped[float] = mapped_column(Float, default=0.0)
    refund_due: Mapped[float] = mapped_column(Float, default=0.0)
    refunded: Mapped[float] = mapped_column(Float, default=0.0)
    checklist: Mapped[str] = mapped_column(Text, default="{}")                # {id_seen, form_c, police, ...: {on, ref}}
    arrived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    left_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    log: Mapped[str] = mapped_column(Text, default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class HsPayment(Base):
    __tablename__ = "homestay_payments"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("hsp"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    booking_id: Mapped[str] = mapped_column(String(40), index=True)
    kind: Mapped[str] = mapped_column(String(10), default="advance")          # advance | balance | addon | refund | ota
    amount: Mapped[float] = mapped_column(Float, default=0.0)
    on: Mapped[str] = mapped_column(String(10), default="")
    mode: Mapped[str] = mapped_column(String(10), default="upi")
    ref: Mapped[str] = mapped_column(String(60), default="")
    void: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class HsCard(Base):
    """Everything that waits for HER tap: a message to a guest (kind message), cancel / refund / spend (money)."""
    __tablename__ = "homestay_cards"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("hsc"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(12), default="")               # C-0001
    kind: Mapped[str] = mapped_column(String(10), default="message")          # message | cancel | refund | spend
    sub: Mapped[str] = mapped_column(String(16), default="")                  # message kind: confirmation | checkin_info | ...
    target: Mapped[str] = mapped_column(String(40), default="")               # booking id (spend: '')
    show: Mapped[str] = mapped_column(Text, default="{}")
    hash: Mapped[str] = mapped_column(String(64), default="")
    status: Mapped[str] = mapped_column(String(10), default="waiting")        # waiting | sent | approved | rejected | stale | dropped | paid
    via: Mapped[str] = mapped_column(String(10), default="")
    reason: Mapped[str] = mapped_column(Text, default="")
    asked_by: Mapped[str] = mapped_column(String(80), default="")
    conv: Mapped[str] = mapped_column(String(40), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class HsTask(Base):
    """Turnover between stays: cleaning, laundry, linen, restock, check."""
    __tablename__ = "homestay_tasks"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("hst"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    booking_id: Mapped[str] = mapped_column(String(40), default="", index=True)
    room_id: Mapped[str] = mapped_column(String(40), default="")
    what: Mapped[str] = mapped_column(String(120), default="")
    kind: Mapped[str] = mapped_column(String(12), default="clean")            # clean | laundry | linen | restock | check | other
    day: Mapped[str] = mapped_column(String(10), default="")
    due: Mapped[str] = mapped_column(String(16), default="")                  # 'YYYY-MM-DD HH:MM' (next check-in) or ''
    assigned: Mapped[str] = mapped_column(String(80), default="")
    status: Mapped[str] = mapped_column(String(8), default="open")            # open | done | skipped
    done_by: Mapped[str] = mapped_column(String(80), default="")
    note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class HsAlert(Base):
    __tablename__ = "homestay_alerts"
    key: Mapped[str] = mapped_column(String(200), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
