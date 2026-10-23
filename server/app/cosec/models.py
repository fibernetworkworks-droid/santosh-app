"""Tables of the Cosec Sahayak (company secretary's desk), all prefixed cosec_."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now


class CosecSettings(Base):
    __tablename__ = "cosec_settings"
    tenant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    firm: Mapped[str] = mapped_column(String(160), default="")            # her CS practice / company name
    cs_name: Mapped[str] = mapped_column(String(120), default="")
    membership_no: Mapped[str] = mapped_column(String(30), default="")    # ACS / FCS (public on documents)
    email: Mapped[str] = mapped_column(String(120), default="")
    phone: Mapped[str] = mapped_column(String(20), default="")
    windows: Mapped[str] = mapped_column(String(60), default="30,15,7,1,0")
    morning_time: Mapped[str] = mapped_column(String(5), default="09:00")
    last_morning: Mapped[str] = mapped_column(String(10), default="")
    rules: Mapped[str] = mapped_column(Text, default="")
    seq: Mapped[str] = mapped_column(Text, default="{}")


class CosecEntity(Base):
    __tablename__ = "cosec_entities"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("ce"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(10), default="")          # E-001
    name: Mapped[str] = mapped_column(String(200), default="")
    kind: Mapped[str] = mapped_column(String(12), default="private")     # private | opc | public | listed | section8 | llp
    small: Mapped[bool | None] = mapped_column(Boolean, nullable=True)   # None = not known
    holding_or_sub: Mapped[bool] = mapped_column(Boolean, default=False)
    cin: Mapped[str] = mapped_column(String(21), default="")
    llpin: Mapped[str] = mapped_column(String(10), default="")
    roc: Mapped[str] = mapped_column(String(60), default="")
    incorporated_on: Mapped[str] = mapped_column(String(10), default="")
    paid_up: Mapped[float | None] = mapped_column(Float, nullable=True)
    turnover: Mapped[float | None] = mapped_column(Float, nullable=True)
    registered_office: Mapped[str] = mapped_column(Text, default="")
    email: Mapped[str] = mapped_column(String(120), default="")
    auditor: Mapped[str] = mapped_column(Text, default="{}")             # {name, frn, appointed_on, term_to_agm (FY end year)}
    flags: Mapped[str] = mapped_column(Text, default="{}")               # {deposits, msme_dues, dormant, startup, first_fy}
    last_agm: Mapped[str] = mapped_column(String(10), default="")
    status: Mapped[str] = mapped_column(String(12), default="active")    # active | closed | struck_off
    notes: Mapped[str] = mapped_column(Text, default="")
    forgotten: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class CosecPerson(Base):
    __tablename__ = "cosec_persons"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("cp"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    entity_id: Mapped[str] = mapped_column(String(40), index=True)
    role: Mapped[str] = mapped_column(String(10), default="director")    # director | partner | kmp | member
    name: Mapped[str] = mapped_column(String(160), default="")
    din: Mapped[str] = mapped_column(String(8), default="")              # DIN / DPIN only
    designation: Mapped[str] = mapped_column(String(80), default="")
    appointed_on: Mapped[str] = mapped_column(String(10), default="")
    ceased_on: Mapped[str] = mapped_column(String(10), default="")
    din_on: Mapped[str] = mapped_column(String(10), default="")
    kyc_on: Mapped[str] = mapped_column(String(10), default="")
    email: Mapped[str] = mapped_column(String(120), default="")
    phone: Mapped[str] = mapped_column(String(20), default="")
    address: Mapped[str] = mapped_column(Text, default="")
    id_ref: Mapped[str] = mapped_column(String(80), default="")          # {id:...} Pehchaan Locker reference only
    folio: Mapped[str] = mapped_column(String(20), default="")
    shares: Mapped[float] = mapped_column(Float, default=0.0)
    share_class: Mapped[str] = mapped_column(String(30), default="Equity")
    nominal: Mapped[float | None] = mapped_column(Float, nullable=True)  # nominal value per share
    member_since: Mapped[str] = mapped_column(String(10), default="")
    history: Mapped[str] = mapped_column(Text, default="[]")             # [{on, what, shares}]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class CosecMeeting(Base):
    __tablename__ = "cosec_meetings"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("cm"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    entity_id: Mapped[str] = mapped_column(String(40), index=True)
    number: Mapped[str] = mapped_column(String(20), default="")          # BM-001 / AGM-001 / EGM-001
    kind: Mapped[str] = mapped_column(String(10), default="board")       # board | agm | egm | committee
    fy: Mapped[str] = mapped_column(String(10), default="")              # AGM: which FY's accounts
    on: Mapped[str] = mapped_column(String(10), default="")
    time: Mapped[str] = mapped_column(String(8), default="")
    place: Mapped[str] = mapped_column(Text, default="")
    mode: Mapped[str] = mapped_column(String(10), default="physical")    # physical | vc | hybrid
    agenda: Mapped[str] = mapped_column(Text, default="[]")
    notice_mode: Mapped[str] = mapped_column(String(12), default="email")
    notice_sent_on: Mapped[str] = mapped_column(String(10), default="")
    notice_plan_on: Mapped[str] = mapped_column(String(10), default="")   # send date the waiting card was made for
    shorter_consent: Mapped[bool] = mapped_column(Boolean, default=False)
    notice_text: Mapped[str] = mapped_column(Text, default="")
    notice_hash: Mapped[str] = mapped_column(String(64), default="")
    notice_file: Mapped[str] = mapped_column(String(60), default="")
    attendance: Mapped[str] = mapped_column(Text, default="[]")          # [{person_id, name, present, interested}]
    quorum: Mapped[str] = mapped_column(Text, default="{}")
    chair: Mapped[str] = mapped_column(String(120), default="")
    minutes: Mapped[str] = mapped_column(Text, default="")
    minutes_hash: Mapped[str] = mapped_column(String(64), default="")
    minutes_file: Mapped[str] = mapped_column(String(60), default="")
    minutes_signed_on: Mapped[str] = mapped_column(String(10), default="")
    status: Mapped[str] = mapped_column(String(16), default="draft")
    # draft | notice_waiting | notice_sent | held | minutes_waiting | minuted | cancelled
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class CosecResolution(Base):
    __tablename__ = "cosec_resolutions"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("cr"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    entity_id: Mapped[str] = mapped_column(String(40), index=True)
    meeting_id: Mapped[str] = mapped_column(String(40), default="")
    number: Mapped[str] = mapped_column(String(20), default="")
    kind: Mapped[str] = mapped_column(String(12), default="board")       # board | ordinary | special | circular
    text: Mapped[str] = mapped_column(Text, default="")
    passed_on: Mapped[str] = mapped_column(String(10), default="")
    votes_for: Mapped[float | None] = mapped_column(Float, nullable=True)
    votes_against: Mapped[float | None] = mapped_column(Float, nullable=True)
    result: Mapped[str] = mapped_column(String(10), default="passed")    # passed | failed
    filing_id: Mapped[str] = mapped_column(String(40), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class CosecFiling(Base):
    __tablename__ = "cosec_filings"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("cf"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    entity_id: Mapped[str] = mapped_column(String(40), index=True)
    key: Mapped[str] = mapped_column(String(160), index=True)            # form|period (unique per entity)
    form: Mapped[str] = mapped_column(String(20), default="")
    period: Mapped[str] = mapped_column(String(80), default="")
    source: Mapped[str] = mapped_column(String(10), default="annual")    # annual | event | kyc
    event: Mapped[str] = mapped_column(Text, default="{}")
    due: Mapped[str] = mapped_column(String(10), default="")
    basis: Mapped[str] = mapped_column(Text, default="")
    est: Mapped[bool] = mapped_column(Boolean, default=False)
    note: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(12), default="todo")      # todo | waiting | approved | filed | not_needed | stale
    hash: Mapped[str] = mapped_column(String(64), default="")
    card: Mapped[str] = mapped_column(Text, default="{}")
    srn: Mapped[str] = mapped_column(String(40), default="")
    filed_on: Mapped[str] = mapped_column(String(10), default="")
    fee_paid: Mapped[float | None] = mapped_column(Float, nullable=True)
    reason: Mapped[str] = mapped_column(Text, default="")
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class CosecCharge(Base):
    __tablename__ = "cosec_charges"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("cc"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    entity_id: Mapped[str] = mapped_column(String(40), index=True)
    holder: Mapped[str] = mapped_column(String(160), default="")
    amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    property: Mapped[str] = mapped_column(Text, default="")
    created_on: Mapped[str] = mapped_column(String(10), default="")
    charge_id: Mapped[str] = mapped_column(String(30), default="")
    satisfied_on: Mapped[str] = mapped_column(String(10), default="")


class CosecOnce(Base):
    __tablename__ = "cosec_once"
    key: Mapped[str] = mapped_column(String(200), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    n: Mapped[int] = mapped_column(Integer, default=1)
