"""Tables of the Interior Sahayak (all prefixed interior_). JSON kept in Text columns (pattern of fleet / theka)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now


class InteriorSettings(Base):
    __tablename__ = "interior_settings"
    tenant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    firm: Mapped[str] = mapped_column(String(160), default="")
    title: Mapped[str] = mapped_column(String(80), default="Interior Designer")
    coa_reg: Mapped[str] = mapped_column(String(30), default="")            # Council of Architecture no (only if she is one)
    gstin: Mapped[str] = mapped_column(String(15), default="")
    state_code: Mapped[str] = mapped_column(String(2), default="")          # from GSTIN, or her choice
    address: Mapped[str] = mapped_column(Text, default="")
    phone: Mapped[str] = mapped_column(String(20), default="")
    email: Mapped[str] = mapped_column(String(120), default="")
    upi_id: Mapped[str] = mapped_column(String(80), default="")             # else the Employee profile's UPI ID
    fee_mode: Mapped[str] = mapped_column(String(10), default="none")       # none | percent | sqft | flat
    fee_value: Mapped[float] = mapped_column(Float, default=0.0)
    gst_works: Mapped[float] = mapped_column(Float, default=18.0)           # her CA confirms
    gst_design: Mapped[float] = mapped_column(Float, default=18.0)
    stages: Mapped[str] = mapped_column(Text, default="")                   # her payment stage template (JSON list; '' = starter)
    terms: Mapped[str] = mapped_column(Text, default="")
    validity_days: Mapped[int] = mapped_column(Integer, default=15)
    warranty: Mapped[str] = mapped_column(Text, default="{}")               # {kind: her warranty words}
    measure_unit: Mapped[str] = mapped_column(String(4), default="ft")
    morning_time: Mapped[str] = mapped_column(String(5), default="08:30")
    last_morning: Mapped[str] = mapped_column(String(10), default="")
    rules: Mapped[str] = mapped_column(Text, default="")
    proj_seq: Mapped[int] = mapped_column(Integer, default=0)
    quote_seq: Mapped[int] = mapped_column(Integer, default=0)
    wo_seq: Mapped[int] = mapped_column(Integer, default=0)
    co_seq: Mapped[int] = mapped_column(Integer, default=0)


class InteriorRate(Base):
    __tablename__ = "interior_rates"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("ir"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    code: Mapped[str] = mapped_column(String(30), default="")
    kind: Mapped[str] = mapped_column(String(20), default="other")
    name: Mapped[str] = mapped_column(String(200), default="")
    unit: Mapped[str] = mapped_column(String(10), default="nos")
    rate: Mapped[float] = mapped_column(Float, default=0.0)                 # HER selling rate per unit (before GST)
    spec: Mapped[str] = mapped_column(Text, default="")                     # material / finish / brand words she wrote
    hsn_sac: Mapped[str] = mapped_column(String(10), default="")
    gst_pct: Mapped[float | None] = mapped_column(Float, nullable=True)     # None = her default
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)


class InteriorProject(Base):
    __tablename__ = "interior_projects"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("ip"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(20), default="")
    name: Mapped[str] = mapped_column(String(160), default="")
    client: Mapped[str] = mapped_column(String(120), default="")
    phone: Mapped[str] = mapped_column(String(20), default="")
    email: Mapped[str] = mapped_column(String(120), default="")
    site: Mapped[str] = mapped_column(Text, default="")
    city: Mapped[str] = mapped_column(String(60), default="")
    pin: Mapped[str] = mapped_column(String(6), default="")
    client_state: Mapped[str] = mapped_column(String(2), default="")       # state code of the place of supply
    client_gstin: Mapped[str] = mapped_column(String(15), default="")
    home: Mapped[str] = mapped_column(String(40), default="")               # 2BHK / office / shop ...
    carpet_sqft: Mapped[float] = mapped_column(Float, default=0.0)          # her / client's figure (for a per-sqft fee)
    budget: Mapped[float] = mapped_column(Float, default=0.0)               # client's budget (their words)
    style: Mapped[str] = mapped_column(String(30), default="")
    brief: Mapped[str] = mapped_column(Text, default="{}")                  # {must, avoid, notes, family, timeline}
    rooms: Mapped[str] = mapped_column(Text, default="[]")
    boq: Mapped[str] = mapped_column(Text, default="[]")
    concept: Mapped[str] = mapped_column(Text, default="{}")                # {palette, items[], style}
    status: Mapped[str] = mapped_column(String(14), default="brief")
    contract_quote: Mapped[str] = mapped_column(String(40), default="")
    target_handover: Mapped[str] = mapped_column(String(10), default="")
    handed_over: Mapped[str] = mapped_column(String(10), default="")
    log: Mapped[str] = mapped_column(Text, default="[]")
    forgotten: Mapped[bool] = mapped_column(Boolean, default=False)
    conv: Mapped[str] = mapped_column(String(40), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class InteriorQuote(Base):
    __tablename__ = "interior_quotes"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("iq"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    project_id: Mapped[str] = mapped_column(String(40), index=True)
    number: Mapped[str] = mapped_column(String(24), default="")
    rev: Mapped[int] = mapped_column(Integer, default=1)
    lines: Mapped[str] = mapped_column(Text, default="[]")
    totals: Mapped[str] = mapped_column(Text, default="{}")
    blanks: Mapped[str] = mapped_column(Text, default="[]")
    status: Mapped[str] = mapped_column(String(12), default="draft")       # draft|waiting|approved|sent|accepted|rejected|superseded
    hash: Mapped[str] = mapped_column(String(64), default="")
    valid_until: Mapped[str] = mapped_column(String(10), default="")
    file_id: Mapped[str] = mapped_column(String(60), default="")
    reason: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class InteriorStage(Base):
    __tablename__ = "interior_stages"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("is"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    project_id: Mapped[str] = mapped_column(String(40), index=True)
    seq: Mapped[int] = mapped_column(Integer, default=0)
    label: Mapped[str] = mapped_column(String(160), default="")
    pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    amount: Mapped[float] = mapped_column(Float, default=0.0)
    due_on: Mapped[str] = mapped_column(String(10), default="")
    status: Mapped[str] = mapped_column(String(12), default="planned")     # planned|waiting|requested|paid|cancelled
    hash: Mapped[str] = mapped_column(String(64), default="")
    paid_amount: Mapped[float] = mapped_column(Float, default=0.0)
    paid_ref: Mapped[str] = mapped_column(String(80), default="")
    paid_on: Mapped[str] = mapped_column(String(10), default="")
    source: Mapped[str] = mapped_column(String(40), default="")             # change order id for a CO stage


class InteriorVendor(Base):
    __tablename__ = "interior_vendors"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("iv"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    name: Mapped[str] = mapped_column(String(120), default="")
    trade: Mapped[str] = mapped_column(String(20), default="carpenter")
    phone: Mapped[str] = mapped_column(String(20), default="")
    gstin: Mapped[str] = mapped_column(String(15), default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class InteriorOrder(Base):
    __tablename__ = "interior_orders"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("io"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    project_id: Mapped[str] = mapped_column(String(40), index=True)
    vendor_id: Mapped[str] = mapped_column(String(40), default="")
    number: Mapped[str] = mapped_column(String(20), default="")
    lines: Mapped[str] = mapped_column(Text, default="[]")
    amount: Mapped[float] = mapped_column(Float, default=0.0)
    start: Mapped[str] = mapped_column(String(10), default="")
    finish: Mapped[str] = mapped_column(String(10), default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(12), default="waiting")     # waiting|approved|rejected|done|cancelled
    hash: Mapped[str] = mapped_column(String(64), default="")
    checks: Mapped[str] = mapped_column(Text, default="[]")
    file_id: Mapped[str] = mapped_column(String(60), default="")
    asked_by: Mapped[str] = mapped_column(String(80), default="")
    reason: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class InteriorChange(Base):
    __tablename__ = "interior_changes"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("ic"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    project_id: Mapped[str] = mapped_column(String(40), index=True)
    number: Mapped[str] = mapped_column(String(20), default="")
    what: Mapped[str] = mapped_column(Text, default="")
    add: Mapped[str] = mapped_column(Text, default="[]")
    remove: Mapped[str] = mapped_column(Text, default="[]")                 # BOQ line ids
    delta: Mapped[float] = mapped_column(Float, default=0.0)                # with GST
    status: Mapped[str] = mapped_column(String(12), default="waiting")     # waiting|approved|rejected|applied
    hash: Mapped[str] = mapped_column(String(64), default="")
    asked_by: Mapped[str] = mapped_column(String(80), default="")
    reason: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class InteriorTask(Base):
    __tablename__ = "interior_tasks"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("it"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    project_id: Mapped[str] = mapped_column(String(40), index=True)
    kind: Mapped[str] = mapped_column(String(20), default="other")
    room: Mapped[str] = mapped_column(String(60), default="")
    what: Mapped[str] = mapped_column(String(200), default="")
    vendor_id: Mapped[str] = mapped_column(String(40), default="")
    start: Mapped[str] = mapped_column(String(10), default="")
    end: Mapped[str] = mapped_column(String(10), default="")
    status: Mapped[str] = mapped_column(String(12), default="planned")     # planned|started|done|delayed|cancelled
    note: Mapped[str] = mapped_column(Text, default="")


class InteriorSnag(Base):
    __tablename__ = "interior_snags"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("isg"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    project_id: Mapped[str] = mapped_column(String(40), index=True)
    number: Mapped[int] = mapped_column(Integer, default=0)
    room: Mapped[str] = mapped_column(String(60), default="")
    what: Mapped[str] = mapped_column(Text, default="")
    vendor_id: Mapped[str] = mapped_column(String(40), default="")
    photos: Mapped[str] = mapped_column(Text, default="[]")                 # [{id, path, stage before|fixed}]
    status: Mapped[str] = mapped_column(String(10), default="open")        # open|fixed|closed
    by: Mapped[str] = mapped_column(String(80), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class InteriorAlert(Base):
    __tablename__ = "interior_alerts"
    key: Mapped[str] = mapped_column(String(200), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
