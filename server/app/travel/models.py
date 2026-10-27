"""Tables of the Yatra Sahayak (all prefixed travel_). Traveller ID numbers are NEVER stored here: only Pehchaan Locker
references ({id:...}) and their masked form."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now


class TravelSettings(Base):
    __tablename__ = "travel_settings"
    tenant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    mode: Mapped[str] = mapped_column(String(10), default="own")            # own (her family's trips) | agency (clients)
    agency_name: Mapped[str] = mapped_column(String(160), default="")
    contact: Mapped[str] = mapped_column(String(160), default="")            # her phone / email shown on client quotes
    home_city: Mapped[str] = mapped_column(String(80), default="")
    state: Mapped[str] = mapped_column(String(40), default="")
    markup_pct: Mapped[float] = mapped_column(Float, default=0.0)            # her service charge, her number only
    markup_flat_paise: Mapped[int] = mapped_column(Integer, default=0)
    gst_pct: Mapped[float] = mapped_column(Float, default=0.0)               # GST on her service charge, only if she sets it
    gstin: Mapped[str] = mapped_column(String(20), default="")
    terms: Mapped[str] = mapped_column(Text, default="")
    rules: Mapped[str] = mapped_column(Text, default="")
    morning_time: Mapped[str] = mapped_column(String(5), default="08:30")
    last_morning: Mapped[str] = mapped_column(String(10), default="")
    partner: Mapped[str] = mapped_column(Text, default="{}")                 # {provider: {sealed key / secret, env}} never shown
    seq: Mapped[int] = mapped_column(Integer, default=0)
    booking_seq: Mapped[int] = mapped_column(Integer, default=0)
    quote_seq: Mapped[int] = mapped_column(Integer, default=0)


class TravelTrip(Base):
    __tablename__ = "travel_trips"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("tt"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(16), default="")             # T-0001
    title: Mapped[str] = mapped_column(String(200), default="")
    for_client: Mapped[bool] = mapped_column(Boolean, default=False)
    client_name: Mapped[str] = mapped_column(String(120), default="")
    client_phone: Mapped[str] = mapped_column(String(20), default="")
    client_email: Mapped[str] = mapped_column(String(120), default="")
    origin: Mapped[str] = mapped_column(String(120), default="")
    destination: Mapped[str] = mapped_column(String(200), default="")
    country: Mapped[str] = mapped_column(String(40), default="")             # "" = India
    start_date: Mapped[str] = mapped_column(String(10), default="")
    end_date: Mapped[str] = mapped_column(String(10), default="")
    travellers: Mapped[str] = mapped_column(Text, default="[]")             # [{name, age, gender, berth, id_kind, id_ref, id_masked, passport_expiry}]
    budget_paise: Mapped[int | None] = mapped_column(Integer, nullable=True)
    prefs: Mapped[str] = mapped_column(Text, default="")
    kind: Mapped[str] = mapped_column(String(40), default="")                # family / pilgrimage / beach / hill / business ...
    status: Mapped[str] = mapped_column(String(16), default="draft")         # draft | planned | quoted | booking | booked | done | cancelled
    itinerary: Mapped[str] = mapped_column(Text, default="[]")
    docs: Mapped[str] = mapped_column(Text, default="{}")                    # {item_id: {have, file_id, note}}
    packing: Mapped[str] = mapped_column(Text, default="{}")                 # {item: true}
    reminded: Mapped[str] = mapped_column(Text, default="[]")
    notes: Mapped[str] = mapped_column(Text, default="")
    log: Mapped[str] = mapped_column(Text, default="[]")
    conv: Mapped[str] = mapped_column(String(40), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now)


class TravelOption(Base):
    __tablename__ = "travel_options"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("to"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    trip_id: Mapped[str] = mapped_column(String(40), index=True)
    mode: Mapped[str] = mapped_column(String(10), default="other")           # train | flight | bus | hotel | cab | other
    name: Mapped[str] = mapped_column(String(160), default="")
    code: Mapped[str] = mapped_column(String(20), default="")                # train no / flight no
    leg: Mapped[str] = mapped_column(String(10), default="out")              # out | back | stay | local
    day: Mapped[str] = mapped_column(String(10), default="")                 # travel / check-in date
    until: Mapped[str] = mapped_column(String(10), default="")               # check-out date (hotels)
    from_place: Mapped[str] = mapped_column(String(120), default="")
    to_place: Mapped[str] = mapped_column(String(120), default="")
    depart: Mapped[str] = mapped_column(String(5), default="")               # HH:MM only when given
    arrive: Mapped[str] = mapped_column(String(5), default="")
    duration_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    price_paise: Mapped[int | None] = mapped_column(Integer, nullable=True)  # her / partner number only
    per_night: Mapped[bool] = mapped_column(Boolean, default=False)
    rating: Mapped[float | None] = mapped_column(Float, nullable=True)
    stars: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cls: Mapped[str] = mapped_column(String(6), default="")
    quota: Mapped[str] = mapped_column(String(4), default="")
    refundable: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    source: Mapped[str] = mapped_column(String(16), default="pasted")       # pasted | her | partner:<name>
    link: Mapped[str] = mapped_column(Text, default="")
    raw: Mapped[str] = mapped_column(Text, default="")
    chosen: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class TravelBooking(Base):
    __tablename__ = "travel_bookings"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("tb"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    trip_id: Mapped[str] = mapped_column(String(40), index=True)
    option_id: Mapped[str] = mapped_column(String(40), default="")
    number: Mapped[str] = mapped_column(String(16), default="")             # B-0001
    status: Mapped[str] = mapped_column(String(16), default="waiting")       # waiting | approved | rejected | working | waiting_payment | booked | failed | cancelled | self
    card: Mapped[str] = mapped_column(Text, default="{}")
    hash: Mapped[str] = mapped_column(String(64), default="")
    site: Mapped[str] = mapped_column(String(20), default="")
    shop_order_id: Mapped[str] = mapped_column(String(40), default="")
    pnr: Mapped[str] = mapped_column(String(40), default="")
    paid_paise: Mapped[int | None] = mapped_column(Integer, nullable=True)
    note: Mapped[str] = mapped_column(Text, default="")
    conv: Mapped[str] = mapped_column(String(40), default="")
    decided_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class TravelQuote(Base):
    __tablename__ = "travel_quotes"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("tq"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    trip_id: Mapped[str] = mapped_column(String(40), index=True)
    number: Mapped[str] = mapped_column(String(16), default="")             # Q-0001
    status: Mapped[str] = mapped_column(String(16), default="waiting")       # waiting | approved | rejected | stale
    card: Mapped[str] = mapped_column(Text, default="{}")
    hash: Mapped[str] = mapped_column(String(64), default="")
    file_id: Mapped[str] = mapped_column(String(80), default="")
    conv: Mapped[str] = mapped_column(String(40), default="")
    decided_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
