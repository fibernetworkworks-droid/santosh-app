"""Godown Sahayak tables (all prefixed warehouse_). Prices are NOT kept here: they come from the Hoola Deals stock list
(`hoola_stock`) and Thok's average cost (`thok_items`). Bin quantities live in `warehouse_lots` (one row per SKU + bin + batch)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now


class WhSettings(Base):
    __tablename__ = "warehouse_settings"
    tenant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(120), default="Godown")
    count_days: Mapped[dict] = mapped_column(JSON, default=dict)          # {A: 30, B: 90, C: 180}
    abc_split: Mapped[list] = mapped_column(JSON, default=list)           # [80, 95]
    tolerance: Mapped[dict] = mapped_column(JSON, default=dict)           # {A: {units, pct}, ...}
    near_expiry_days: Mapped[int] = mapped_column(Integer, default=30)
    slow_days: Mapped[int] = mapped_column(Integer, default=60)
    dead_days: Mapped[int] = mapped_column(Integer, default=180)
    count_bins_per_day: Mapped[int] = mapped_column(Integer, default=10)
    food: Mapped[bool] = mapped_column(Boolean, default=False)
    rules: Mapped[str] = mapped_column(Text, default="")
    morning_time: Mapped[str] = mapped_column(String(5), default="09:00")
    last_morning: Mapped[str] = mapped_column(String(10), default="")
    seq: Mapped[dict] = mapped_column(JSON, default=dict)                 # {grn, pick, count, adj, sku}


class WhBin(Base):
    __tablename__ = "warehouse_bins"
    __table_args__ = (UniqueConstraint("tenant_id", "code", name="uq_warehouse_bin"),)
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("wb"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    code: Mapped[str] = mapped_column(String(40))                        # A-12, B-03-R2-4
    zone: Mapped[str] = mapped_column(String(8), default="")
    aisle: Mapped[str] = mapped_column(String(8), default="")
    rack: Mapped[str] = mapped_column(String(8), default="")
    bin: Mapped[str] = mapped_column(String(8), default="")
    kind: Mapped[str] = mapped_column(String(12), default="pick")        # rules.BIN_KINDS
    capacity: Mapped[float | None] = mapped_column(Float, nullable=True)  # units it holds (None = not set)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    note: Mapped[str] = mapped_column(String(200), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class WhSku(Base):
    __tablename__ = "warehouse_skus"
    __table_args__ = (UniqueConstraint("tenant_id", "key", name="uq_warehouse_sku"),)
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("ws"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    key: Mapped[str] = mapped_column(String(140))                        # = hoola_stock.key when it is on her stock list
    name: Mapped[str] = mapped_column(String(140))
    code: Mapped[str] = mapped_column(String(30), default="", index=True)  # SKU-0001 (or her own code)
    barcode: Mapped[str] = mapped_column(String(40), default="")         # her own GTIN / barcode if the pack has one
    unit: Mapped[str] = mapped_column(String(20), default="")
    track: Mapped[str] = mapped_column(String(8), default="none")        # none | batch | serial
    abc: Mapped[str] = mapped_column(String(1), default="C")
    abc_manual: Mapped[bool] = mapped_column(Boolean, default=False)
    last_counted: Mapped[str] = mapped_column(String(10), default="")
    home_bin: Mapped[str] = mapped_column(String(40), default="")
    note: Mapped[str] = mapped_column(String(200), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class WhLot(Base):
    """Stock in one bin: one SKU, one batch (expiry / mfg), serials when serial-tracked."""
    __tablename__ = "warehouse_lots"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("wl"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    sku_id: Mapped[str] = mapped_column(String(40), index=True)
    bin_id: Mapped[str] = mapped_column(String(40), index=True)
    batch: Mapped[str] = mapped_column(String(40), default="")
    expiry: Mapped[str] = mapped_column(String(10), default="")
    mfg: Mapped[str] = mapped_column(String(10), default="")
    qty: Mapped[float] = mapped_column(Float, default=0.0)
    serials: Mapped[list] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(10), default="ok")        # ok | hold
    received_on: Mapped[str] = mapped_column(String(10), default="")
    grn_id: Mapped[str] = mapped_column(String(40), default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class WhMove(Base):
    """The movement ledger (Rule 56 stock account): every in / out / move / adjustment, per bin."""
    __tablename__ = "warehouse_moves"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("wm"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, index=True)
    day: Mapped[str] = mapped_column(String(10), default="", index=True)
    kind: Mapped[str] = mapped_column(String(10))                        # opening | grn | putaway | move | pick | adjust | writeoff
    sku_id: Mapped[str] = mapped_column(String(40), index=True)
    bin_id: Mapped[str] = mapped_column(String(40), index=True)
    lot_id: Mapped[str] = mapped_column(String(40), default="")
    batch: Mapped[str] = mapped_column(String(40), default="")
    qty: Mapped[float] = mapped_column(Float, default=0.0)               # + in / - out of this bin
    ref: Mapped[str] = mapped_column(String(30), default="")             # GRN-0001 / PL-0001 / ADJ-0001
    by: Mapped[str] = mapped_column(String(80), default="")
    reason: Mapped[str] = mapped_column(String(12), default="")
    note: Mapped[str] = mapped_column(String(240), default="")
    synced: Mapped[bool] = mapped_column(Boolean, default=False)         # the shared stock count (hoola_stock) changed too


class WhGrn(Base):
    __tablename__ = "warehouse_grns"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("wg"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(20), default="")
    supplier: Mapped[str] = mapped_column(String(140), default="")
    doc: Mapped[str] = mapped_column(String(60), default="")             # challan / PO / invoice number as printed
    source: Mapped[str] = mapped_column(String(16), default="challan")   # challan | po | photo | file | list | thok_purchase
    source_ref: Mapped[str] = mapped_column(String(40), default="")
    sync: Mapped[bool] = mapped_column(Boolean, default=True)            # add to the shared stock count on receipt
    lines: Mapped[list] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(10), default="received")  # received | putaway
    notes: Mapped[list] = mapped_column(JSON, default=list)
    file_id: Mapped[str] = mapped_column(String(60), default="")
    by: Mapped[str] = mapped_column(String(80), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class WhPick(Base):
    __tablename__ = "warehouse_picks"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("wp"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(20), default="")
    source: Mapped[str] = mapped_column(String(10), default="list")      # list | deal | thok | wave
    refs: Mapped[list] = mapped_column(JSON, default=list)               # [{kind, id, number, party}]
    sync: Mapped[bool] = mapped_column(Boolean, default=True)            # take out of the shared stock count when picked
    lines: Mapped[list] = mapped_column(JSON, default=list)              # [{sku_id, name, unit, qty, orders, short, note}]
    tasks: Mapped[list] = mapped_column(JSON, default=list)              # walk order: [{n, bin, bin_id, lot_id, sku_id, name, batch, expiry, qty, picked, done}]
    status: Mapped[str] = mapped_column(String(10), default="open")      # open | done | cancelled
    picker: Mapped[str] = mapped_column(String(80), default="")
    notes: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    done_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class WhCount(Base):
    __tablename__ = "warehouse_counts"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("wc"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(20), default="")
    kind: Mapped[str] = mapped_column(String(8), default="cycle")        # cycle | spot | full | recount
    bins: Mapped[list] = mapped_column(JSON, default=list)               # bin ids to count
    lines: Mapped[list] = mapped_column(JSON, default=list)              # [{bin_id, sku_id, batch, lot_id, system (hidden), counted, by, at}]
    status: Mapped[str] = mapped_column(String(10), default="open")      # open | closed
    reason: Mapped[str] = mapped_column(String(200), default="")
    adjust_id: Mapped[str] = mapped_column(String(40), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class WhAdjust(Base):
    """A stock adjustment / write-off card. Decided ONLY by her tap (POST /api/warehouse/adjustments/{id}/decide with the hash)."""
    __tablename__ = "warehouse_adjusts"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("wa"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(20), default="")
    kind: Mapped[str] = mapped_column(String(10), default="count")       # count | writeoff
    count_id: Mapped[str] = mapped_column(String(40), default="")
    lines: Mapped[list] = mapped_column(JSON, default=list)
    value: Mapped[float | None] = mapped_column(Float, nullable=True)    # rupee value of the change (from her costs), None = unknown
    hash: Mapped[str] = mapped_column(String(32), default="")
    status: Mapped[str] = mapped_column(String(10), default="waiting")   # waiting | approved | rejected | stale
    asked_by: Mapped[str] = mapped_column(String(80), default="")
    reason: Mapped[str] = mapped_column(Text, default="")
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
