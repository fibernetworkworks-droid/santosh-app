"""Tables of the Society Sahayak (all prefixed society_). Money in paise (int)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now


class SocietySettings(Base):
    __tablename__ = "society_settings"
    tenant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(160), default="")
    reg_no: Mapped[str] = mapped_column(String(80), default="")
    address: Mapped[str] = mapped_column(Text, default="")
    state: Mapped[str] = mapped_column(String(4), default="")              # MH ... ("" = her bye-laws only)
    upi_id: Mapped[str] = mapped_column(String(80), default="")             # the SOCIETY's UPI ID
    upi_name: Mapped[str] = mapped_column(String(80), default="")
    heads: Mapped[str] = mapped_column(Text, default="")                   # JSON list of bill heads ("" = starter heads, no rates)
    noc_pct: Mapped[float] = mapped_column(Float, default=0.0)             # non-occupancy % of service charges
    interest_pct: Mapped[float] = mapped_column(Float, default=0.0)        # general body rate (MH max 12% simple)
    grace_days: Mapped[int] = mapped_column(Integer, default=0)
    due_days: Mapped[int] = mapped_column(Integer, default=15)             # bill date -> due date
    bill_day: Mapped[int] = mapped_column(Integer, default=1)
    gstin: Mapped[str] = mapped_column(String(20), default="")
    gst_on: Mapped[bool] = mapped_column(Boolean, default=False)
    committee: Mapped[str] = mapped_column(Text, default="[]")             # [{name, role, phone, flat}]
    term_ends: Mapped[str] = mapped_column(String(10), default="")         # managing committee term end (her date)
    auditor: Mapped[str] = mapped_column(String(160), default="")
    audit_done: Mapped[str] = mapped_column(Text, default="{}")            # {fy: date}
    agm_done: Mapped[str] = mapped_column(Text, default="{}")              # {fy: date}
    visitor_days: Mapped[int] = mapped_column(Integer, default=90)
    morning_time: Mapped[str] = mapped_column(String(5), default="09:00")
    last_morning: Mapped[str] = mapped_column(String(10), default="")
    rules: Mapped[str] = mapped_column(Text, default="")
    seq: Mapped[str] = mapped_column(Text, default="{}")                   # {kind: n}


class SocietyFlat(Base):
    __tablename__ = "society_flats"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("sf"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    unit: Mapped[str] = mapped_column(String(20), default="", index=True)  # A-101
    wing: Mapped[str] = mapped_column(String(10), default="")
    carpet_sqft: Mapped[float] = mapped_column(Float, default=0.0)
    cost: Mapped[int] = mapped_column(Integer, default=0)                  # architect-certified construction cost (paise)
    taps: Mapped[int | None] = mapped_column(Integer, nullable=True)
    lift: Mapped[bool] = mapped_column(Boolean, default=True)
    owner_name: Mapped[str] = mapped_column(String(160), default="")
    owner_phone: Mapped[str] = mapped_column(String(15), default="")
    owner_email: Mapped[str] = mapped_column(String(120), default="")
    joint: Mapped[str] = mapped_column(Text, default="[]")                 # joint members' names
    member_since: Mapped[str] = mapped_column(String(10), default="")
    share_cert: Mapped[str] = mapped_column(String(40), default="")
    shares: Mapped[str] = mapped_column(String(40), default="")            # distinctive numbers "101-105"
    nominations: Mapped[str] = mapped_column(Text, default="[]")           # [{name, relation, share_pct, on, revoked}]
    occupancy: Mapped[str] = mapped_column(String(10), default="self")     # self | tenant | vacant
    tenant_name: Mapped[str] = mapped_column(String(160), default="")
    tenant_phone: Mapped[str] = mapped_column(String(15), default="")
    tenant_from: Mapped[str] = mapped_column(String(10), default="")
    tenant_to: Mapped[str] = mapped_column(String(10), default="")
    parking: Mapped[str] = mapped_column(Text, default="[]")               # [{slot, kind, resolution}]
    opening_due: Mapped[int] = mapped_column(Integer, default=0)           # arrears she carried in (paise)
    no_messages: Mapped[bool] = mapped_column(Boolean, default=False)
    history: Mapped[str] = mapped_column(Text, default="[]")               # ownership changes
    status: Mapped[str] = mapped_column(String(10), default="active")      # active | forgotten
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class SocietyBill(Base):
    __tablename__ = "society_bills"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("sb"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(24), default="")
    flat_id: Mapped[str] = mapped_column(String(40), index=True)
    period: Mapped[str] = mapped_column(String(7), default="")             # 2026-10
    bill_date: Mapped[str] = mapped_column(String(10), default="")
    due_date: Mapped[str] = mapped_column(String(10), default="")
    lines: Mapped[str] = mapped_column(Text, default="[]")
    principal: Mapped[int] = mapped_column(Integer, default=0)             # lines without interest / GST
    interest: Mapped[int] = mapped_column(Integer, default=0)
    gst: Mapped[int] = mapped_column(Integer, default=0)
    total: Mapped[int] = mapped_column(Integer, default=0)
    paid: Mapped[int] = mapped_column(Integer, default=0)
    batch_id: Mapped[str] = mapped_column(String(40), default="", index=True)
    status: Mapped[str] = mapped_column(String(12), default="draft")      # draft | issued | paid | part | cancelled | stale
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class SocietyReceipt(Base):
    __tablename__ = "society_receipts"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("sr"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(24), default="")
    flat_id: Mapped[str] = mapped_column(String(40), index=True)
    day: Mapped[str] = mapped_column(String(10), default="")
    amount: Mapped[int] = mapped_column(Integer, default=0)
    mode: Mapped[str] = mapped_column(String(10), default="upi")           # upi | cash | cheque | neft
    ref_tail: Mapped[str] = mapped_column(String(8), default="")
    applied: Mapped[str] = mapped_column(Text, default="[]")               # [{bill, amount}]
    advance: Mapped[int] = mapped_column(Integer, default=0)
    by: Mapped[str] = mapped_column(String(60), default="Owner")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class SocietyCard(Base):
    """Anything that waits for HER tap: bills batch | notice | message | spend | penalty. hash = what she saw."""
    __tablename__ = "society_cards"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("sc"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    kind: Mapped[str] = mapped_column(String(12), default="")
    target: Mapped[str] = mapped_column(String(40), default="", index=True)
    title: Mapped[str] = mapped_column(String(200), default="")
    hash: Mapped[str] = mapped_column(String(64), default="")
    data: Mapped[str] = mapped_column(Text, default="{}")
    status: Mapped[str] = mapped_column(String(10), default="waiting")     # waiting | approved | rejected | stale
    reason: Mapped[str] = mapped_column(Text, default="")
    asked_by: Mapped[str] = mapped_column(String(80), default="Hoola")
    conv: Mapped[str] = mapped_column(String(40), default="")
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class SocietyNotice(Base):
    __tablename__ = "society_notices"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("sn"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(24), default="")
    kind: Mapped[str] = mapped_column(String(12), default="notice")       # notice | circular | agm | sgm | committee | defaulters | minutes
    title: Mapped[str] = mapped_column(String(200), default="")
    body: Mapped[str] = mapped_column(Text, default="")
    audience: Mapped[str] = mapped_column(String(20), default="all")      # all | committee | flats
    flats: Mapped[str] = mapped_column(Text, default="[]")
    meeting_id: Mapped[str] = mapped_column(String(40), default="")
    status: Mapped[str] = mapped_column(String(10), default="draft")      # draft | waiting | approved | rejected
    issued_on: Mapped[str] = mapped_column(String(10), default="")
    file_id: Mapped[str] = mapped_column(String(60), default="")
    checks: Mapped[str] = mapped_column(Text, default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class SocietyMeeting(Base):
    __tablename__ = "society_meetings"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("sm"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(24), default="")
    kind: Mapped[str] = mapped_column(String(10), default="agm")          # agm | sgm | committee
    day: Mapped[str] = mapped_column(String(10), default="")
    time: Mapped[str] = mapped_column(String(5), default="")
    place: Mapped[str] = mapped_column(String(200), default="")
    agenda: Mapped[str] = mapped_column(Text, default="[]")
    quorum: Mapped[int] = mapped_column(Integer, default=0)
    present: Mapped[str] = mapped_column(Text, default="[]")              # flat units / names present
    minutes: Mapped[str] = mapped_column(Text, default="")
    resolutions: Mapped[str] = mapped_column(Text, default="[]")          # [{no, text, proposer, seconder, for, against, passed}]
    status: Mapped[str] = mapped_column(String(12), default="planned")    # planned | held | adjourned | minuted | cancelled
    notice_id: Mapped[str] = mapped_column(String(40), default="")
    fy: Mapped[str] = mapped_column(String(6), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class SocietyComplaint(Base):
    __tablename__ = "society_complaints"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("sq"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(24), default="")
    flat_id: Mapped[str] = mapped_column(String(40), default="", index=True)
    kind: Mapped[str] = mapped_column(String(10), default="complaint")    # complaint | request
    category: Mapped[str] = mapped_column(String(20), default="other")
    text: Mapped[str] = mapped_column(Text, default="")
    urgent: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(12), default="open")       # open | assigned | working | resolved | closed
    contract_id: Mapped[str] = mapped_column(String(40), default="")
    log: Mapped[str] = mapped_column(Text, default="[]")
    by: Mapped[str] = mapped_column(String(60), default="Owner")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)


class SocietyContract(Base):
    """Vendors and AMC: lift, security, housekeeping, tank cleaning..."""
    __tablename__ = "society_contracts"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("sv"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    kind: Mapped[str] = mapped_column(String(14), default="other")
    vendor: Mapped[str] = mapped_column(String(160), default="")
    phone: Mapped[str] = mapped_column(String(15), default="")
    amount: Mapped[int] = mapped_column(Integer, default=0)               # her number (paise)
    per: Mapped[str] = mapped_column(String(6), default="year")           # month | year | visit
    start: Mapped[str] = mapped_column(String(10), default="")
    end: Mapped[str] = mapped_column(String(10), default="")
    visits: Mapped[str] = mapped_column(Text, default="")                 # what the contract covers
    individual: Mapped[bool] = mapped_column(Boolean, default=False)      # vendor is an individual / HUF (TDS 1%)
    reminded: Mapped[str] = mapped_column(Text, default="{}")
    status: Mapped[str] = mapped_column(String(10), default="active")
    notes: Mapped[str] = mapped_column(Text, default="")


class SocietySpend(Base):
    __tablename__ = "society_spends"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("sx"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(24), default="")
    kind: Mapped[str] = mapped_column(String(10), default="other")
    what: Mapped[str] = mapped_column(Text, default="")
    amount: Mapped[int] = mapped_column(Integer, default=0)
    vendor: Mapped[str] = mapped_column(String(160), default="")
    contract_id: Mapped[str] = mapped_column(String(40), default="")
    fund: Mapped[str] = mapped_column(String(10), default="general")
    resolution: Mapped[str] = mapped_column(String(200), default="")      # GB resolution ref (sinking fund / over the limit)
    checks: Mapped[str] = mapped_column(Text, default="[]")
    status: Mapped[str] = mapped_column(String(10), default="waiting")    # waiting | approved | rejected | done
    paid_amount: Mapped[int | None] = mapped_column(Integer, nullable=True)
    paid_ref: Mapped[str] = mapped_column(String(80), default="")
    paid_on: Mapped[str] = mapped_column(String(10), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class SocietyPenalty(Base):
    __tablename__ = "society_penalties"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("sp"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(24), default="")
    flat_id: Mapped[str] = mapped_column(String(40), index=True)
    what: Mapped[str] = mapped_column(Text, default="")
    amount: Mapped[int] = mapped_column(Integer, default=0)
    rule: Mapped[str] = mapped_column(String(200), default="")            # bye-law / GB resolution that allows it
    status: Mapped[str] = mapped_column(String(10), default="waiting")    # waiting | approved | rejected | billed
    bill_id: Mapped[str] = mapped_column(String(40), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class SocietyMessage(Base):
    __tablename__ = "society_messages"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("sg"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    kind: Mapped[str] = mapped_column(String(12), default="custom")       # dues | bill | complaint | custom
    flat_ids: Mapped[str] = mapped_column(Text, default="[]")
    text: Mapped[str] = mapped_column(Text, default="")                   # may hold {name} {unit} {amount} {link}
    status: Mapped[str] = mapped_column(String(10), default="waiting")    # waiting | approved | rejected | sent
    result: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class SocietyStaff(Base):
    __tablename__ = "society_staff"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("st"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    name: Mapped[str] = mapped_column(String(120), default="")
    role: Mapped[str] = mapped_column(String(20), default="other")
    agency: Mapped[str] = mapped_column(String(120), default="")          # society staff or agency name
    flats: Mapped[str] = mapped_column(Text, default="[]")                # domestic help: which flats
    phone: Mapped[str] = mapped_column(String(15), default="")
    verified_on: Mapped[str] = mapped_column(String(10), default="")      # police verification date (her word)
    status: Mapped[str] = mapped_column(String(10), default="active")
    reminded: Mapped[str] = mapped_column(String(20), default="")


class SocietyVisit(Base):
    """Visitor / delivery / daily-help entries. Kept visitor_days (DPDP), phone only as last 4."""
    __tablename__ = "society_visits"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("sz"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    kind: Mapped[str] = mapped_column(String(10), default="visitor")      # visitor | delivery | staff | vendor
    name: Mapped[str] = mapped_column(String(120), default="")
    flat_id: Mapped[str] = mapped_column(String(40), default="")
    purpose: Mapped[str] = mapped_column(String(200), default="")
    phone_tail: Mapped[str] = mapped_column(String(4), default="")
    vehicle: Mapped[str] = mapped_column(String(20), default="")
    in_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    out_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    by: Mapped[str] = mapped_column(String(60), default="Gate")


class SocietyAlert(Base):
    __tablename__ = "society_alerts"
    key: Mapped[str] = mapped_column(String(200), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
