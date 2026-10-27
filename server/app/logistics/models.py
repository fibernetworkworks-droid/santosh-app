"""Tables of the Logistics Sahayak (all prefixed logistics_)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now


class LogiSettings(Base):
    __tablename__ = "logistics_settings"
    tenant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    firm: Mapped[str] = mapped_column(String(160), default="")
    role: Mapped[str] = mapped_column(String(12), default="trader")          # trader | manufacturer | transporter
    gstin: Mapped[str] = mapped_column(String(15), default="")
    address: Mapped[str] = mapped_column(Text, default="")
    place: Mapped[str] = mapped_column(String(80), default="")
    pincode: Mapped[str] = mapped_column(String(6), default="")
    phone: Mapped[str] = mapped_column(String(15), default="")
    carrier_reg: Mapped[str] = mapped_column(String(80), default="")        # Carriage by Road Act registration (transporter)
    gta_rate: Mapped[float] = mapped_column(Float, default=0.0)            # 5 | 18 when she is a GTA
    lr_prefix: Mapped[str] = mapped_column(String(8), default="LR")
    lr_seq: Mapped[int] = mapped_column(Integer, default=0)
    dc_prefix: Mapped[str] = mapped_column(String(8), default="DC")
    dc_seq: Mapped[int] = mapped_column(Integer, default=0)
    seq: Mapped[int] = mapped_column(Integer, default=0)
    grace_h: Mapped[float] = mapped_column(Float, default=2.0)
    silent_h: Mapped[float] = mapped_column(Float, default=12.0)            # no update for this long while moving -> ask driver
    morning_time: Mapped[str] = mapped_column(String(5), default="08:30")
    last_morning: Mapped[str] = mapped_column(String(10), default="")
    terms: Mapped[str] = mapped_column(Text, default="")
    ewb_provider: Mapped[str] = mapped_column(String(10), default="manual")  # manual | gsp
    ewb_sealed: Mapped[str] = mapped_column(Text, default="")               # bazar vault
    ewb_label: Mapped[str] = mapped_column(String(80), default="")


class LogiParty(Base):
    __tablename__ = "logistics_parties"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("lp"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    name: Mapped[str] = mapped_column(String(160), default="")
    gstin: Mapped[str] = mapped_column(String(15), default="")
    address: Mapped[str] = mapped_column(Text, default="")
    place: Mapped[str] = mapped_column(String(80), default="")
    pincode: Mapped[str] = mapped_column(String(6), default="")
    state: Mapped[str] = mapped_column(String(2), default="")
    phone: Mapped[str] = mapped_column(String(15), default="")
    no_messages: Mapped[bool] = mapped_column(Boolean, default=False)
    kind: Mapped[str] = mapped_column(String(12), default="customer")      # customer | supplier | transporter
    trans_id: Mapped[str] = mapped_column(String(15), default="")          # transporter's GSTIN / EWB TRANSIN


class LogiShipment(Base):
    __tablename__ = "logistics_shipments"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("ls"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(12), default="", index=True)
    direction: Mapped[str] = mapped_column(String(8), default="out")       # out (she sends) | in (she receives) | carry (she transports)
    consignor: Mapped[str] = mapped_column(Text, default="{}")
    consignee: Mapped[str] = mapped_column(Text, default="{}")
    consignee_id: Mapped[str] = mapped_column(String(40), default="", index=True)
    goods: Mapped[str] = mapped_column(Text, default="[]")                 # [{name, hsn, qty, unit, value, gst}]
    value: Mapped[float] = mapped_column(Float, default=0.0)               # taxable value
    tax: Mapped[float] = mapped_column(Float, default=0.0)
    doc_type: Mapped[str] = mapped_column(String(16), default="invoice")
    doc_no: Mapped[str] = mapped_column(String(20), default="")
    doc_date: Mapped[str] = mapped_column(String(10), default="")
    reason: Mapped[str] = mapped_column(String(20), default="supply")
    thok_order: Mapped[str] = mapped_column(String(40), default="")
    weight_kg: Mapped[float] = mapped_column(Float, default=0.0)
    packages: Mapped[int] = mapped_column(Integer, default=0)
    package_kind: Mapped[str] = mapped_column(String(20), default="")
    mode: Mapped[str] = mapped_column(String(8), default="road")           # road | rail | air | ship | courier
    fleet: Mapped[str] = mapped_column(String(8), default="hired")         # own | hired | courier
    transporter: Mapped[str] = mapped_column(Text, default="{}")           # {name, gstin, phone}
    vehicle_no: Mapped[str] = mapped_column(String(16), default="")
    odc: Mapped[bool] = mapped_column(Boolean, default=False)
    driver: Mapped[str] = mapped_column(Text, default="{}")                # {name, phone}
    courier: Mapped[str] = mapped_column(String(30), default="")
    awb: Mapped[str] = mapped_column(String(40), default="")
    lr_no: Mapped[str] = mapped_column(String(20), default="")
    lr_date: Mapped[str] = mapped_column(String(10), default="")
    freight: Mapped[float] = mapped_column(Float, default=0.0)
    freight_by: Mapped[str] = mapped_column(String(8), default="")          # paid | to_pay | tbb
    from_place: Mapped[str] = mapped_column(String(80), default="")
    to_place: Mapped[str] = mapped_column(String(80), default="")
    distance_km: Mapped[float] = mapped_column(Float, default=0.0)
    dispatch_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    eta: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(18), default="booked", index=True)
    ewb: Mapped[str] = mapped_column(Text, default="{}")                   # {no, date, valid_upto, part_b, cewb, ...}
    timeline: Mapped[str] = mapped_column(Text, default="[]")
    last_update_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_location: Mapped[str] = mapped_column(Text, default="{}")
    pod: Mapped[str] = mapped_column(Text, default="{}")                   # {receiver, remarks, short, damaged, photos}
    alerts: Mapped[str] = mapped_column(Text, default="[]")                # keys already told (once each)
    note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class LogiMessage(Base):
    """A customer update draft. Goes out only when she sends it (wa.me) or taps 'Business WhatsApp se bhejo' in the app."""
    __tablename__ = "logistics_messages"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("lm"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    shipment_id: Mapped[str] = mapped_column(String(40), index=True)
    kind: Mapped[str] = mapped_column(String(20), default="dispatch")
    phone: Mapped[str] = mapped_column(String(15), default="")
    text: Mapped[str] = mapped_column(Text, default="")
    hash: Mapped[str] = mapped_column(String(64), default="")
    status: Mapped[str] = mapped_column(String(10), default="draft")       # draft | sent | dropped
    via: Mapped[str] = mapped_column(String(10), default="")               # self | business
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class LogiEwbAsk(Base):
    """An e-way bill filing step waiting for her tap (generate / part_b / extend / consolidated)."""
    __tablename__ = "logistics_ewb_asks"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("le"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    shipment_id: Mapped[str] = mapped_column(String(40), index=True)
    kind: Mapped[str] = mapped_column(String(14), default="generate")
    payload: Mapped[str] = mapped_column(Text, default="{}")
    checks: Mapped[str] = mapped_column(Text, default="{}")
    hash: Mapped[str] = mapped_column(String(64), default="")
    status: Mapped[str] = mapped_column(String(10), default="waiting")     # waiting | done | manual | failed | rejected | stale
    result: Mapped[str] = mapped_column(Text, default="{}")
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class LogiPhoto(Base):
    __tablename__ = "logistics_photos"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("lf"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    shipment_id: Mapped[str] = mapped_column(String(40), index=True)
    stage: Mapped[str] = mapped_column(String(10), default="pod")          # pod | loading | damage
    path: Mapped[str] = mapped_column(String(400), default="")
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
