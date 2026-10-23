"""Tables of the Customs Sahayak (all prefixed customs_)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now


class CustomsSettings(Base):
    __tablename__ = "customs_settings"
    tenant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    firm: Mapped[str] = mapped_column(String(160), default="")
    address: Mapped[str] = mapped_column(Text, default="")
    iec: Mapped[str] = mapped_column(String(10), default="")
    gstin: Mapped[str] = mapped_column(String(15), default="")
    cha_name: Mapped[str] = mapped_column(String(120), default="")          # her customs broker (CHA / CB)
    cha_phone: Mapped[str] = mapped_column(String(20), default="")
    cha_email: Mapped[str] = mapped_column(String(120), default="")
    morning_time: Mapped[str] = mapped_column(String(5), default="09:15")
    last_morning: Mapped[str] = mapped_column(String(10), default="")
    rules: Mapped[str] = mapped_column(Text, default="")
    seq: Mapped[int] = mapped_column(Integer, default=0)
    filing_seq: Mapped[int] = mapped_column(Integer, default=0)


class CustomsShipment(Base):
    __tablename__ = "customs_shipments"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("cs"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(12), default="", index=True)     # I-0001
    status: Mapped[str] = mapped_column(String(16), default="draft")           # draft | active | done | cancelled
    stage: Mapped[str] = mapped_column(String(16), default="")                 # furthest rules.STAGES key reached
    supplier: Mapped[str] = mapped_column(String(160), default="")
    supplier_country: Mapped[str] = mapped_column(String(2), default="")
    origin: Mapped[str] = mapped_column(String(2), default="")                 # country of origin of the goods
    incoterm: Mapped[str] = mapped_column(String(3), default="FOB")
    place: Mapped[str] = mapped_column(String(80), default="")
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    fx: Mapped[float] = mapped_column(Float, default=0.0)                       # HER rupees per unit (CBIC notified rate)
    invoice_no: Mapped[str] = mapped_column(String(40), default="")
    invoice_date: Mapped[str] = mapped_column(String(10), default="")
    invoice_value: Mapped[float] = mapped_column(Float, default=0.0)            # at the Incoterm, in currency
    freight: Mapped[float] = mapped_column(Float, default=0.0)                  # real amount she knows (0 = not known)
    insurance: Mapped[float] = mapped_column(Float, default=0.0)
    mode: Mapped[str] = mapped_column(String(8), default="sea")                 # sea | air | courier | land
    port: Mapped[str] = mapped_column(String(80), default="")                   # port / air cargo / ICD of import
    be_type: Mapped[str] = mapped_column(String(10), default="home")
    igm_no: Mapped[str] = mapped_column(String(20), default="")
    igm_date: Mapped[str] = mapped_column(String(10), default="")
    bl_no: Mapped[str] = mapped_column(String(40), default="")                  # BL / AWB / courier waybill
    bl_date: Mapped[str] = mapped_column(String(10), default="")
    containers: Mapped[str] = mapped_column(String(120), default="")
    shipping_line: Mapped[str] = mapped_column(String(80), default="")
    cha: Mapped[str] = mapped_column(String(120), default="")                   # broker for this one (else her default)
    eta: Mapped[str] = mapped_column(String(10), default="")
    free_days: Mapped[int | None] = mapped_column(Integer, nullable=True)       # port / CFS storage free days (she enters)
    demurrage_per_day: Mapped[float | None] = mapped_column(Float, nullable=True)
    detention_free_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    detention_per_day: Mapped[float | None] = mapped_column(Float, nullable=True)
    fta: Mapped[int] = mapped_column(Integer, default=0)                       # 1 = she claims FTA preference
    licence: Mapped[int] = mapped_column(Integer, default=0)                   # 1 = restricted item with a DGFT licence
    be_no: Mapped[str] = mapped_column(String(20), default="")
    be_date: Mapped[str] = mapped_column(String(10), default="")
    duty_paid: Mapped[float | None] = mapped_column(Float, nullable=True)      # what she / CHA says was paid (record only)
    charges: Mapped[str] = mapped_column(Text, default="{}")                   # her other landing costs {cha_fee, cfs, transport, ...}
    lines: Mapped[str] = mapped_column(Text, default="[]")
    docs: Mapped[str] = mapped_column(Text, default="{}")                      # key -> {status have|missing|na, note, file_id, at}
    timeline: Mapped[str] = mapped_column(Text, default="[]")
    told: Mapped[str] = mapped_column(Text, default="{}")
    log: Mapped[str] = mapped_column(Text, default="[]")
    notes: Mapped[str] = mapped_column(Text, default="")
    conv: Mapped[str] = mapped_column(String(40), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class CustomsFiling(Base):
    """Her Haan card before the Bill of Entry data goes to the CHA (or she files herself). Hoola never files."""
    __tablename__ = "customs_filings"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("cf"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    shipment_id: Mapped[str] = mapped_column(String(40), index=True)
    number: Mapped[str] = mapped_column(String(12), default="")                # F-0001
    status: Mapped[str] = mapped_column(String(10), default="waiting")         # waiting | approved | rejected | stale
    hash: Mapped[str] = mapped_column(String(64), default="")
    summary: Mapped[str] = mapped_column(Text, default="{}")
    warnings: Mapped[str] = mapped_column(Text, default="[]")
    reason: Mapped[str] = mapped_column(Text, default="")
    conv: Mapped[str] = mapped_column(String(40), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class CustomsHsMemory(Base):
    """Codes she confirmed for her goods (learned; used first next time). key = tenant:normalised description."""
    __tablename__ = "customs_hs_memory"
    key: Mapped[str] = mapped_column(String(200), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    desc: Mapped[str] = mapped_column(String(200), default="")
    hs: Mapped[str] = mapped_column(String(8), default="")
    used: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
