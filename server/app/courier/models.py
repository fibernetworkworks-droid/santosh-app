"""Courier Sahayak tables (all prefixed courier_)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now


class CourierSettings(Base):
    __tablename__ = "courier_settings"
    tenant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    business: Mapped[str] = mapped_column(String(160), default="")
    gstin: Mapped[str] = mapped_column(String(15), default="")
    warehouse: Mapped[str] = mapped_column(Text, default="{}")            # pickup place: name, phone, address, city, state, pincode, email
    keys: Mapped[str] = mapped_column(Text, default="{}")                 # {provider: sealed JSON} - never returned
    default_carrier: Mapped[str] = mapped_column(String(20), default="")  # shiprocket | delhivery | manual
    rules: Mapped[str] = mapped_column(Text, default="{}")
    rules_text: Mapped[str] = mapped_column(Text, default="")
    divisor: Mapped[float] = mapped_column(Float, default=5000.0)
    remit_days: Mapped[int] = mapped_column(Integer, default=0)            # her own expectation; 0 = not set (no "late" flag)
    manifest_time: Mapped[str] = mapped_column(String(5), default="17:00")
    morning_time: Mapped[str] = mapped_column(String(5), default="09:30")
    last_manifest: Mapped[str] = mapped_column(String(10), default="")
    last_morning: Mapped[str] = mapped_column(String(10), default="")
    last_poll: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    seq: Mapped[int] = mapped_column(Integer, default=0)
    bk_seq: Mapped[int] = mapped_column(Integer, default=0)


class CourierParcel(Base):
    __tablename__ = "courier_parcels"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("cp"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(20), default="")            # P-0001
    kind: Mapped[str] = mapped_column(String(10), default="forward")       # forward | reverse
    order_ref: Mapped[str] = mapped_column(String(80), default="")
    customer: Mapped[str] = mapped_column(Text, default="{}")              # name, phone, email, address, city, state, pincode
    phone: Mapped[str] = mapped_column(String(10), default="", index=True)
    items: Mapped[str] = mapped_column(Text, default="[]")                 # name, qty, price, sku
    value: Mapped[float] = mapped_column(Float, default=0.0)
    payment: Mapped[str] = mapped_column(String(8), default="prepaid")     # prepaid | cod
    cod_amount: Mapped[float] = mapped_column(Float, default=0.0)
    weight: Mapped[str] = mapped_column(Text, default="{}")                # rules.weights() + dims
    eway_no: Mapped[str] = mapped_column(String(20), default="")
    serviceable: Mapped[str] = mapped_column(Text, default="{}")           # last check {provider, ok, cod, at, raw}
    quotes: Mapped[str] = mapped_column(Text, default="[]")                # the carrier's own quotes
    pick: Mapped[str] = mapped_column(Text, default="{}")                  # chosen quote + why
    provider: Mapped[str] = mapped_column(String(20), default="")          # shiprocket | delhivery | bluedart | manual
    carrier: Mapped[str] = mapped_column(String(40), default="")           # the courier that carries it (name as the API said)
    awb: Mapped[str] = mapped_column(String(40), default="", index=True)
    status: Mapped[str] = mapped_column(String(20), default="draft")
    raw: Mapped[str] = mapped_column(String(200), default="")              # the carrier's own last words, exactly
    edd: Mapped[str] = mapped_column(String(30), default="")               # expected delivery, only when the carrier gave it
    booking: Mapped[str] = mapped_column(Text, default="{}")               # shipment_id, order_id, pickup, label_url, charged
    label: Mapped[str] = mapped_column(Text, default="{}")                 # her file {file_id, name} / path
    events: Mapped[str] = mapped_column(Text, default="[]")
    ndr: Mapped[str] = mapped_column(Text, default="{}")                   # {reason, raw, attempts, at, action, answered}
    cod: Mapped[str] = mapped_column(Text, default="{}")                   # {remitted, amount, utr, date, diff}
    wapsi_ref: Mapped[str] = mapped_column(String(40), default="")         # reverse pickups for a Wapsi return
    note: Mapped[str] = mapped_column(Text, default="")
    log: Mapped[str] = mapped_column(Text, default="[]")
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class CourierCard(Base):
    """A step that waits for her tap: pickup booking (may charge her courier wallet), return label, NDR action, cancel."""
    __tablename__ = "courier_cards"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("cc"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    parcel_id: Mapped[str] = mapped_column(String(40), index=True, default="")
    number: Mapped[str] = mapped_column(String(20), default="")            # B-0001
    kind: Mapped[str] = mapped_column(String(12), default="book")          # book | reverse | ndr | cancel
    body: Mapped[str] = mapped_column(Text, default="{}")                  # exactly what the card shows
    hash: Mapped[str] = mapped_column(String(64), default="")
    status: Mapped[str] = mapped_column(String(12), default="waiting")     # waiting | done | rejected | stale | failed
    result: Mapped[str] = mapped_column(Text, default="{}")
    money: Mapped[bool] = mapped_column(Boolean, default=False)            # may charge her wallet
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class CourierRemit(Base):
    """A line of a COD remittance statement she uploaded (her carrier's CSV / Excel)."""
    __tablename__ = "courier_remits"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("cr"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    awb: Mapped[str] = mapped_column(String(40), default="", index=True)
    order_ref: Mapped[str] = mapped_column(String(80), default="")
    amount: Mapped[float] = mapped_column(Float, default=0.0)
    utr: Mapped[str] = mapped_column(String(60), default="")
    date: Mapped[str] = mapped_column(String(20), default="")
    source: Mapped[str] = mapped_column(String(120), default="")
    parcel_id: Mapped[str] = mapped_column(String(40), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
