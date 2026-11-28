"""The Material Store desk's tables. One append-only movement ledger (sd_moves) carries every quantity that ever moved; stock in a
place is what came into it minus what left it. Everything else is a register around it. Nothing in sd_moves is ever edited: a
mistake gets a counter-row (kind 'reverse') with the approver's name."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now


class SdSettings(Base):
    __tablename__ = "sd_settings"
    tenant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    company: Mapped[str] = mapped_column(String(120), default="")
    project: Mapped[str] = mapped_column(String(120), default="")
    country: Mapped[str] = mapped_column(String(4), default="")
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    units: Mapped[str] = mapped_column(String(10), default="metric")          # metric | imperial (how new items are offered)
    valuation: Mapped[str] = mapped_column(String(10), default="wavg")        # fifo | wavg | lifo (lifo only with gaap usgaap)
    gaap: Mapped[str] = mapped_column(String(10), default="ifrs")             # ifrs | usgaap | local
    language: Mapped[str] = mapped_column(String(10), default="en")
    tolerance: Mapped[float] = mapped_column(Float, default=2.0)              # count tolerance %, default for every item
    receive_tol: Mapped[float] = mapped_column(Float, default=2.0)            # delivery vs note tolerance %, default
    wastage: Mapped[float] = mapped_column(Float, default=3.0)                # allowance %, default when an item has none
    tiers: Mapped[list] = mapped_column(JSON, default=list)                   # [[up_to_value, "role"], ...] last one = above
    count_days: Mapped[dict] = mapped_column(JSON, default=dict)              # {"A": 30, "B": 90, "C": 180}
    lead_days: Mapped[int] = mapped_column(Integer, default=7)
    service_z: Mapped[float] = mapped_column(Float, default=1.65)             # safety stock factor (1.65 = about 95% of days)
    stale_days: Mapped[int] = mapped_column(Integer, default=45)
    transit_days: Mapped[int] = mapped_column(Integer, default=2)
    hold_days: Mapped[int] = mapped_column(Integer, default=3)
    overdue_days: Mapped[int] = mapped_column(Integer, default=1)
    packs_off: Mapped[list] = mapped_column(JSON, default=list)               # country-pack rows she switched off
    legacy_done: Mapped[dict] = mapped_column(JSON, default=dict)             # old store rows already brought in
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class SdStore(Base):
    __tablename__ = "sd_stores"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("sst"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    name: Mapped[str] = mapped_column(String(80), default="")
    project: Mapped[str] = mapped_column(String(120), default="")
    kind: Mapped[str] = mapped_column(String(12), default="main")             # main | yard | sub | container
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class SdItem(Base):
    __tablename__ = "sd_items"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("sit"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    code: Mapped[str] = mapped_column(String(40), default="")
    name: Mapped[str] = mapped_column(String(120), default="")
    category: Mapped[str] = mapped_column(String(12), default="bulk")         # bulk | consumable | tool | client
    unit: Mapped[str] = mapped_column(String(12), default="no")               # the base unit every quantity is kept in
    conv: Mapped[dict] = mapped_column(JSON, default=dict)                    # {"bag": 50} = 1 bag is 50 base units
    cls: Mapped[str] = mapped_column(String(2), default="")                   # her A/B/C; empty = worked out
    critical: Mapped[bool] = mapped_column(Boolean, default=False)
    min_qty: Mapped[float] = mapped_column(Float, default=0.0)
    max_qty: Mapped[float] = mapped_column(Float, default=0.0)
    lead_days: Mapped[int] = mapped_column(Integer, default=0)                # 0 = the company's
    shelf_days: Mapped[int] = mapped_column(Integer, default=0)
    trace: Mapped[str] = mapped_column(String(8), default="none")            # none | batch | heat | serial
    inspect: Mapped[bool] = mapped_column(Boolean, default=False)            # lands on quality hold
    tol_pct: Mapped[float] = mapped_column(Float, default=-1.0)               # receiving tolerance %, -1 = the company's
    wastage: Mapped[float] = mapped_column(Float, default=-1.0)               # allowance %, -1 = the company's
    mass_per_m: Mapped[float] = mapped_column(Float, default=0.0)             # her figure (kg/m) for a bar weight check
    mass_src: Mapped[str] = mapped_column(String(200), default="")
    max_minutes: Mapped[int] = mapped_column(Integer, default=0)              # ready-mix: batch to arrival limit from her spec
    price: Mapped[float] = mapped_column(Float, default=0.0)                  # last known unit cost (base unit)
    docs: Mapped[list] = mapped_column(JSON, default=list)                    # country-pack document rows that apply
    note: Mapped[str] = mapped_column(String(300), default="")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class SdLot(Base):
    __tablename__ = "sd_lots"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("slt"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    item_id: Mapped[str] = mapped_column(String(40), index=True)
    ref: Mapped[str] = mapped_column(String(60), default="")                  # heat / batch / serial
    made: Mapped[str] = mapped_column(String(10), default="")                 # manufacture date
    expires: Mapped[str] = mapped_column(String(10), default="")
    cert: Mapped[str] = mapped_column(String(80), default="")                 # mill test certificate / DoP / test report
    receipt_id: Mapped[str] = mapped_column(String(40), default="")
    cost: Mapped[float] = mapped_column(Float, default=0.0)                   # unit cost (base unit)
    received: Mapped[str] = mapped_column(String(10), default="")             # the day it came in (FIFO)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class SdMove(Base):
    __tablename__ = "sd_moves"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("smv"))
    seq: Mapped[int] = mapped_column(Integer, index=True, default=0)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    kind: Mapped[str] = mapped_column(String(14), default="")
    item_id: Mapped[str] = mapped_column(String(40), index=True)
    lot_id: Mapped[str] = mapped_column(String(40), default="")
    qty: Mapped[float] = mapped_column(Float, default=0.0)                    # base unit, always > 0
    qty_in: Mapped[float] = mapped_column(Float, default=0.0)                 # as entered
    unit_in: Mapped[str] = mapped_column(String(12), default="")
    from_store: Mapped[str] = mapped_column(String(40), default="")
    from_pos: Mapped[str] = mapped_column(String(12), default="")             # outside | hold | available | blocked | transit | holder | used | vendor | scrap | adjust
    to_store: Mapped[str] = mapped_column(String(40), default="")
    to_pos: Mapped[str] = mapped_column(String(12), default="")
    holder: Mapped[str] = mapped_column(String(120), default="")
    work: Mapped[str] = mapped_column(String(80), default="")                 # work package / cost code
    cost: Mapped[float] = mapped_column(Float, default=0.0)                   # unit cost at the time
    doc: Mapped[dict] = mapped_column(JSON, default=dict)                     # receipt / slip / po / count / legacy refs
    who: Mapped[str] = mapped_column(String(80), default="")
    approver: Mapped[str] = mapped_column(String(80), default="")
    note: Mapped[str] = mapped_column(String(300), default="")
    day: Mapped[str] = mapped_column(String(10), index=True, default="")
    reverses: Mapped[str] = mapped_column(String(40), default="")
    reversed_by: Mapped[str] = mapped_column(String(40), default="")
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class SdDoc(Base):
    """Every paper of the desk that waits for a person: receipts (GRN), issue / return / transfer slips, purchase orders, indents,
    counts, adjustments, recovery drafts. `lines` and `data` hold the paper; posting it writes sd_moves."""
    __tablename__ = "sd_docs"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("sdc"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    kind: Mapped[str] = mapped_column(String(10), index=True)                 # grn | slip | po | indent | count | adjust | recovery
    number: Mapped[str] = mapped_column(String(20), default="")
    status: Mapped[str] = mapped_column(String(12), default="draft")
    store_id: Mapped[str] = mapped_column(String(40), default="")
    party: Mapped[str] = mapped_column(String(160), default="")               # supplier / holder / requester
    lines: Mapped[list] = mapped_column(JSON, default=list)
    data: Mapped[dict] = mapped_column(JSON, default=dict)
    who: Mapped[str] = mapped_column(String(80), default="")
    approver: Mapped[str] = mapped_column(String(80), default="")
    day: Mapped[str] = mapped_column(String(10), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class SdBudget(Base):
    """What a work package should use: theoretical quantity from the QS take-off (her number), the allowance, how far the work is
    done (her number), and what is still unused at the work front (her entry)."""
    __tablename__ = "sd_budgets"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("sbg"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    work: Mapped[str] = mapped_column(String(80), default="")
    name: Mapped[str] = mapped_column(String(120), default="")
    item_id: Mapped[str] = mapped_column(String(40), index=True)
    qty: Mapped[float] = mapped_column(Float, default=0.0)                    # theoretical for the whole package (base unit)
    allowance: Mapped[float] = mapped_column(Float, default=-1.0)             # -1 = the item's / company's
    done: Mapped[float] = mapped_column(Float, default=0.0)                   # her % complete 0..100
    unused: Mapped[float] = mapped_column(Float, default=0.0)                 # left at the work front, her entry
    need_by: Mapped[str] = mapped_column(String(10), default="")
    need_qty: Mapped[float] = mapped_column(Float, default=0.0)               # look-ahead: still to come by need_by
    source: Mapped[str] = mapped_column(String(200), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class SdHolder(Base):
    """A subcontractor or gang that holds free-issue material: the allowance and the recovery rate come from HER subcontract."""
    __tablename__ = "sd_holders"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("shd"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    name: Mapped[str] = mapped_column(String(120), default="")
    allowance: Mapped[float] = mapped_column(Float, default=-1.0)
    rate: Mapped[dict] = mapped_column(JSON, default=dict)                    # {item_id: unit rate (base unit)}
    uplift: Mapped[float] = mapped_column(Float, default=0.0)                 # % on top of the rate
    clause: Mapped[str] = mapped_column(String(200), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


ALL = (SdSettings, SdStore, SdItem, SdLot, SdMove, SdDoc, SdBudget, SdHolder)
