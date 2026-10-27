"""Tables of the Rentdesk Sahayak (property manager). All prefixed rentdesk_."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now


class RdSettings(Base):
    __tablename__ = "rentdesk_settings"
    tenant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    business: Mapped[str] = mapped_column(String(160), default="")
    landlord_name: Mapped[str] = mapped_column(String(160), default="")       # licensor / owner name on receipts
    landlord_address: Mapped[str] = mapped_column(Text, default="")
    landlord_phone: Mapped[str] = mapped_column(String(16), default="")
    pan_ref: Mapped[str] = mapped_column(String(40), default="")              # {id:...} in her Pehchaan Locker (never the number)
    receipt_full_pan: Mapped[bool] = mapped_column(Boolean, default=False)    # print the full PAN on the receipt PDF (her choice)
    state: Mapped[str] = mapped_column(String(4), default="")                 # MH ...
    city: Mapped[str] = mapped_column(String(80), default="")
    upi_id: Mapped[str] = mapped_column(String(120), default="")              # "" = Employee profile UPI ID
    upi_name: Mapped[str] = mapped_column(String(80), default="")
    gstin: Mapped[str] = mapped_column(String(15), default="")
    agency: Mapped[bool] = mapped_column(Boolean, default=False)              # she manages other owners' units
    remind_before: Mapped[int] = mapped_column(Integer, default=3)
    grace_days: Mapped[int] = mapped_column(Integer, default=5)
    renewal_windows: Mapped[str] = mapped_column(Text, default="[60, 30, 15, 7]")
    minor_repair_limit: Mapped[float] = mapped_column(Float, default=0.0)     # tenant pays repairs up to this (her agreement rule)
    mirror_dues: Mapped[bool] = mapped_column(Boolean, default=True)          # also a BizDue so WhatsApp tenants see their dues
    morning_time: Mapped[str] = mapped_column(String(5), default="09:00")
    last_morning: Mapped[str] = mapped_column(String(10), default="")
    rules: Mapped[str] = mapped_column(Text, default="")
    seq: Mapped[str] = mapped_column(Text, default="{}")                      # {"unit": n, "tenancy": n, "receipt:2627": n, ...}


class RdUnit(Base):
    __tablename__ = "rentdesk_units"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("rdu"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(12), default="")               # U-001
    label: Mapped[str] = mapped_column(String(120), default="")               # Flat 302 / Shop 4 / Bed B2
    building: Mapped[str] = mapped_column(String(160), default="")
    kind: Mapped[str] = mapped_column(String(12), default="flat")             # flat | house | room | pg_bed | shop | office | godown | other
    use: Mapped[str] = mapped_column(String(12), default="residential")       # residential | commercial
    address: Mapped[str] = mapped_column(Text, default="")
    city: Mapped[str] = mapped_column(String(80), default="")
    pin: Mapped[str] = mapped_column(String(6), default="")
    area_sqft: Mapped[float] = mapped_column(Float, default=0.0)              # her number (carpet / built-up as she says)
    area_note: Mapped[str] = mapped_column(String(40), default="")
    furnished: Mapped[str] = mapped_column(String(12), default="")            # unfurnished | semi | full
    inventory: Mapped[str] = mapped_column(Text, default="[]")                # [{item, qty}]
    owner_name: Mapped[str] = mapped_column(String(120), default="")          # agency: whose unit
    owner_phone: Mapped[str] = mapped_column(String(16), default="")
    rent_ask: Mapped[float] = mapped_column(Float, default=0.0)
    deposit_ask: Mapped[float] = mapped_column(Float, default=0.0)
    maintenance: Mapped[float] = mapped_column(Float, default=0.0)            # society maintenance per month (her number)
    electricity_no: Mapped[str] = mapped_column(String(40), default="")
    archived: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class RdPerson(Base):
    """A tenant / licensee (person or firm). ID numbers only as Pehchaan Locker references."""
    __tablename__ = "rentdesk_people"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("rdp"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(12), default="")               # P-001
    name: Mapped[str] = mapped_column(String(160), default="")
    phone: Mapped[str] = mapped_column(String(10), default="", index=True)
    email: Mapped[str] = mapped_column(String(160), default="")
    kind: Mapped[str] = mapped_column(String(12), default="individual")       # individual | family | student | company | firm
    employer: Mapped[str] = mapped_column(String(160), default="")
    address: Mapped[str] = mapped_column(Text, default="")                    # permanent address
    members: Mapped[str] = mapped_column(Text, default="[]")                  # occupants' names
    emergency: Mapped[str] = mapped_column(String(160), default="")
    gstin: Mapped[str] = mapped_column(String(15), default="")
    composition: Mapped[bool] = mapped_column(Boolean, default=False)         # GST composition taxpayer (RCM exclusion)
    ids: Mapped[str] = mapped_column(Text, default="{}")                      # {kind: {ref, masked, record}}
    lang: Mapped[str] = mapped_column(String(10), default="hinglish")
    no_messages: Mapped[bool] = mapped_column(Boolean, default=False)
    forgotten: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class RdTenancy(Base):
    """One leave & licence / rent agreement for one unit."""
    __tablename__ = "rentdesk_tenancies"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("rdt"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(12), default="")               # T-0001
    unit_id: Mapped[str] = mapped_column(String(40), index=True)
    person_id: Mapped[str] = mapped_column(String(40), index=True)
    kind: Mapped[str] = mapped_column(String(14), default="leave_licence")    # leave_licence | rent | mta
    status: Mapped[str] = mapped_column(String(10), default="draft")          # draft | active | notice | ended | cancelled
    start: Mapped[str] = mapped_column(String(10), default="")
    end: Mapped[str] = mapped_column(String(10), default="")
    months: Mapped[int] = mapped_column(Integer, default=11)
    rent: Mapped[float] = mapped_column(Float, default=0.0)                   # current monthly rent / licence fee
    rent_history: Mapped[str] = mapped_column(Text, default="[]")             # [{from, rent, why}]
    deposit: Mapped[float] = mapped_column(Float, default=0.0)
    maintenance: Mapped[float] = mapped_column(Float, default=0.0)
    maintenance_by: Mapped[str] = mapped_column(String(8), default="owner")   # tenant | owner
    due_day: Mapped[int] = mapped_column(Integer, default=0)                  # 0 = same day as the licence month starts
    escalation_pct: Mapped[float] = mapped_column(Float, default=0.0)
    escalation_every: Mapped[int] = mapped_column(Integer, default=0)         # months (0 = no escalation clause)
    lock_in_months: Mapped[int] = mapped_column(Integer, default=0)
    notice_months: Mapped[int] = mapped_column(Integer, default=1)
    purpose: Mapped[str] = mapped_column(String(160), default="")
    stamp_duty: Mapped[float | None] = mapped_column(Float, nullable=True)    # HER number from IGR / sub-registrar
    reg_fee: Mapped[float | None] = mapped_column(Float, nullable=True)
    registration: Mapped[str] = mapped_column(Text, default="{}")             # {status, doc_no, date, office}
    police: Mapped[str] = mapped_column(Text, default="{}")                   # {status, ref, date, station}
    checklist: Mapped[str] = mapped_column(Text, default="{}")                # {item_id: done date}
    advance: Mapped[float] = mapped_column(Float, default=0.0)                # paid ahead, not yet allocated
    notice_on: Mapped[str] = mapped_column(String(10), default="")
    notice_by: Mapped[str] = mapped_column(String(10), default="")            # tenant | owner
    vacate_on: Mapped[str] = mapped_column(String(10), default="")
    files: Mapped[str] = mapped_column(Text, default="[]")                    # agreement drafts / notices [{file_id, name, kind}]
    alerts: Mapped[str] = mapped_column(Text, default="{}")
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class RdCharge(Base):
    """One line of the ledger the tenant owes (rent, deposit, maintenance, bills, repairs she approved)."""
    __tablename__ = "rentdesk_charges"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("rdc"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    tenancy_id: Mapped[str] = mapped_column(String(40), index=True)
    kind: Mapped[str] = mapped_column(String(12), default="rent")             # rent | deposit | maintenance | electricity | water | late_fee | repair | other
    period: Mapped[str] = mapped_column(String(10), default="")               # 2026-10 (licence month) / "" for one-off
    due_on: Mapped[str] = mapped_column(String(10), default="")
    amount: Mapped[float] = mapped_column(Float, default=0.0)
    paid: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(8), default="open")            # open | part | paid | waived
    note: Mapped[str] = mapped_column(String(200), default="")
    biz_due_id: Mapped[str] = mapped_column(String(40), default="")
    reminded: Mapped[str] = mapped_column(Text, default="[]")                 # stages done: before | due | late
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class RdPayment(Base):
    __tablename__ = "rentdesk_payments"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("rdy"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    tenancy_id: Mapped[str] = mapped_column(String(40), index=True)
    receipt_no: Mapped[str] = mapped_column(String(24), default="")
    amount: Mapped[float] = mapped_column(Float, default=0.0)
    on: Mapped[str] = mapped_column(String(10), default="")
    mode: Mapped[str] = mapped_column(String(8), default="upi")               # upi | bank | cash | cheque | deposit (adjusted)
    ref_tail: Mapped[str] = mapped_column(String(8), default="")
    alloc: Mapped[str] = mapped_column(Text, default="[]")                    # [{charge_id, kind, period, amount}]
    hint: Mapped[str] = mapped_column(String(300), default="")                # Galla UPI credit seen (only a hint)
    by: Mapped[str] = mapped_column(String(60), default="Owner")
    void: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class RdVendor(Base):
    __tablename__ = "rentdesk_vendors"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("rdv"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    name: Mapped[str] = mapped_column(String(120), default="")
    phone: Mapped[str] = mapped_column(String(10), default="")
    trade: Mapped[str] = mapped_column(String(20), default="other")
    notes: Mapped[str] = mapped_column(Text, default="")


class RdRequest(Base):
    """A maintenance / repair request (M-0001)."""
    __tablename__ = "rentdesk_requests"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("rdr"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(12), default="")
    unit_id: Mapped[str] = mapped_column(String(40), index=True)
    tenancy_id: Mapped[str] = mapped_column(String(40), default="")
    text: Mapped[str] = mapped_column(Text, default="")
    category: Mapped[str] = mapped_column(String(16), default="other")
    urgent: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(14), default="open")           # open | assigned | waiting_haan | approved | done | closed | rejected
    vendor_id: Mapped[str] = mapped_column(String(40), default="")
    quote: Mapped[float] = mapped_column(Float, default=0.0)
    who_pays: Mapped[str] = mapped_column(String(8), default="owner")         # owner | tenant
    paid: Mapped[float] = mapped_column(Float, default=0.0)
    raised_by: Mapped[str] = mapped_column(String(60), default="Owner")
    log: Mapped[str] = mapped_column(Text, default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class RdInspection(Base):
    __tablename__ = "rentdesk_inspections"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("rdi"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    tenancy_id: Mapped[str] = mapped_column(String(40), index=True)
    kind: Mapped[str] = mapped_column(String(10), default="move_in")          # move_in | move_out
    on: Mapped[str] = mapped_column(String(10), default="")
    items: Mapped[str] = mapped_column(Text, default="[]")                    # [{key, room, item, condition, note, photos[]}]
    meters: Mapped[str] = mapped_column(Text, default="{}")                   # {electricity: 12345, water: ..., gas: ...}
    keys: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(8), default="open")            # open | closed
    signed_by: Mapped[str] = mapped_column(String(160), default="")


class RdPhoto(Base):
    __tablename__ = "rentdesk_photos"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("rdf"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    owner_kind: Mapped[str] = mapped_column(String(10), default="inspection")  # inspection | request
    owner_id: Mapped[str] = mapped_column(String(40), index=True)
    item: Mapped[str] = mapped_column(String(80), default="")
    path: Mapped[str] = mapped_column(Text, default="")
    width: Mapped[int] = mapped_column(Integer, default=0)
    height: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class RdSettlement(Base):
    __tablename__ = "rentdesk_settlements"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("rds"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    tenancy_id: Mapped[str] = mapped_column(String(40), index=True)
    lines: Mapped[str] = mapped_column(Text, default="[]")                    # her deductions [{what, amount, reason, photos}]
    status: Mapped[str] = mapped_column(String(10), default="draft")          # draft | waiting | approved | paid | rejected
    refund_paid: Mapped[float] = mapped_column(Float, default=0.0)
    refund_ref: Mapped[str] = mapped_column(String(40), default="")
    approval_id: Mapped[str] = mapped_column(String(40), default="")
    calc: Mapped[str] = mapped_column(Text, default="{}")                     # numbers frozen at her approval
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class RdApproval(Base):
    """A card only HER app tap decides: deduction | rent_change | notice | repair."""
    __tablename__ = "rentdesk_approvals"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("rda"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(12), default="")               # A-0001
    kind: Mapped[str] = mapped_column(String(12), default="")
    target: Mapped[str] = mapped_column(String(40), default="", index=True)
    show: Mapped[str] = mapped_column(Text, default="{}")
    hash: Mapped[str] = mapped_column(String(64), default="")
    status: Mapped[str] = mapped_column(String(10), default="waiting")        # waiting | approved | rejected | stale
    reason: Mapped[str] = mapped_column(String(300), default="")
    asked_by: Mapped[str] = mapped_column(String(60), default="Owner")
    conv: Mapped[str] = mapped_column(String(40), default="")
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class RdMessage(Base):
    """A message for a tenant: always a DRAFT until her tap sends it (her own WhatsApp / SMS, or the business number)."""
    __tablename__ = "rentdesk_messages"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("rdm"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    tenancy_id: Mapped[str] = mapped_column(String(40), index=True)
    person_id: Mapped[str] = mapped_column(String(40), default="")
    kind: Mapped[str] = mapped_column(String(14), default="custom")           # reminder | late | receipt | notice | rent_change | renewal | refund | repair | custom
    ref: Mapped[str] = mapped_column(String(40), default="")
    text: Mapped[str] = mapped_column(Text, default="")
    hash: Mapped[str] = mapped_column(String(64), default="")
    status: Mapped[str] = mapped_column(String(8), default="draft")           # draft | sent | dropped
    via: Mapped[str] = mapped_column(String(10), default="")
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class RdAlert(Base):
    """Once-only keys (reminder / renewal / police / morning)."""
    __tablename__ = "rentdesk_alerts"
    key: Mapped[str] = mapped_column(String(200), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
