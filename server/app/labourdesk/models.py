"""The Labour & Wages desk's tables. Attendance (ld_marks) and money (runs, advances, levies, withholding) are append-only or
frozen once a person signed; a mistake in the muster is a counter-row with a reason and who made it, never an edit."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now


class LdSettings(Base):
    __tablename__ = "ld_settings"
    tenant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    company: Mapped[str] = mapped_column(String(120), default="")
    project: Mapped[str] = mapped_column(String(120), default="")
    country: Mapped[str] = mapped_column(String(4), default="")
    region: Mapped[str] = mapped_column(String(40), default="")              # state / province (levies and floors follow it)
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    pay_cycle: Mapped[str] = mapped_column(String(12), default="weekly")    # weekly | fortnightly | monthly
    week_start: Mapped[int] = mapped_column(Integer, default=0)             # 0 = Monday
    day_hours: Mapped[float] = mapped_column(Float, default=8.0)
    week_hours: Mapped[float] = mapped_column(Float, default=48.0)
    max_day_hours: Mapped[float] = mapped_column(Float, default=12.0)       # her limit, flagged above
    ot_x: Mapped[float] = mapped_column(Float, default=0.0)                 # her contract's multiplier (only counts if higher than the pack's)
    cutoff: Mapped[str] = mapped_column(String(5), default="11:00")
    advance_cap: Mapped[float] = mapped_column(Float, default=50.0)        # % of one period's pay after deductions
    second_limit: Mapped[float] = mapped_column(Float, default=0.0)         # a run above this needs a second approver (0 = never)
    gate_tol: Mapped[int] = mapped_column(Integer, default=0)               # people of difference allowed against the gate count
    burst: Mapped[int] = mapped_column(Integer, default=5)                  # people checked in from one device inside a minute
    deductions: Mapped[list] = mapped_column(JSON, default=list)            # her rows: {name, pct, base, cap, employer_pct, source}
    required: Mapped[list] = mapped_column(JSON, default=list)              # person papers a worker must hold to be mustered
    language: Mapped[str] = mapped_column(String(10), default="en")
    packs_off: Mapped[list] = mapped_column(JSON, default=list)
    legacy_done: Mapped[dict] = mapped_column(JSON, default=dict)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class LdSite(Base):
    __tablename__ = "ld_sites"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("lsi"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    name: Mapped[str] = mapped_column(String(80), default="")
    project: Mapped[str] = mapped_column(String(120), default="")
    region: Mapped[str] = mapped_column(String(40), default="")
    planned: Mapped[int] = mapped_column(Integer, default=0)                 # planned headcount a day
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class LdEmployer(Base):
    __tablename__ = "ld_employers"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("lem"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    name: Mapped[str] = mapped_column(String(120), default="")
    kind: Mapped[str] = mapped_column(String(8), default="sub")              # own | sub
    status: Mapped[str] = mapped_column(String(14), default="")             # tax status: individual | firm | registered | unregistered | gross
    tax_id_last4: Mapped[str] = mapped_column(String(4), default="")
    tax_id_ok: Mapped[bool] = mapped_column(Boolean, default=False)          # the id was checked as valid
    checked_on: Mapped[str] = mapped_column(String(10), default="")          # when that check was made (CIS verification, PAN check)
    checked_by: Mapped[str] = mapped_column(String(80), default="")
    contact: Mapped[str] = mapped_column(String(120), default="")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class LdWorker(Base):
    __tablename__ = "ld_workers"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("lwk"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    code: Mapped[str] = mapped_column(String(30), default="")
    name: Mapped[str] = mapped_column(String(120), default="")
    employer_id: Mapped[str] = mapped_column(String(40), index=True, default="")
    trade: Mapped[str] = mapped_column(String(60), default="")
    skill: Mapped[str] = mapped_column(String(30), default="")              # her grade: unskilled | semi-skilled | skilled | ...
    gang: Mapped[str] = mapped_column(String(60), default="")
    site_id: Mapped[str] = mapped_column(String(40), default="")
    id_last4: Mapped[str] = mapped_column(String(4), default="")
    bank_last4: Mapped[str] = mapped_column(String(4), default="")
    phone_last4: Mapped[str] = mapped_column(String(4), default="")
    language: Mapped[str] = mapped_column(String(10), default="")
    joined: Mapped[str] = mapped_column(String(10), default="")
    left: Mapped[str] = mapped_column(String(10), default="")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class LdPaper(Base):
    __tablename__ = "ld_papers"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("lpp"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    whose: Mapped[str] = mapped_column(String(10), default="worker")        # company | employer | worker | site
    owner_id: Mapped[str] = mapped_column(String(40), index=True, default="")
    kind: Mapped[str] = mapped_column(String(40), default="")
    name: Mapped[str] = mapped_column(String(120), default="")
    number_last4: Mapped[str] = mapped_column(String(4), default="")
    issuer: Mapped[str] = mapped_column(String(120), default="")
    valid_from: Mapped[str] = mapped_column(String(10), default="")
    valid_to: Mapped[str] = mapped_column(String(10), index=True, default="")
    file_id: Mapped[str] = mapped_column(String(60), default="")
    note: Mapped[str] = mapped_column(String(300), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class LdRate(Base):
    __tablename__ = "ld_rates"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("lrt"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    kind: Mapped[str] = mapped_column(String(6), default="pay")              # pay | floor (a minimum / prevailing rate)
    trade: Mapped[str] = mapped_column(String(60), default="")               # "" = any trade (with a skill)
    skill: Mapped[str] = mapped_column(String(30), default="")
    site_id: Mapped[str] = mapped_column(String(40), default="")
    region: Mapped[str] = mapped_column(String(40), default="")
    worker_id: Mapped[str] = mapped_column(String(40), default="")
    basis: Mapped[str] = mapped_column(String(6), default="day")             # day | hour | piece
    rate: Mapped[float] = mapped_column(Float, default=0.0)
    unit: Mapped[str] = mapped_column(String(20), default="")                # piece unit
    wef: Mapped[str] = mapped_column(String(10), default="")
    source: Mapped[str] = mapped_column(String(240), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class LdMark(Base):
    __tablename__ = "ld_marks"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("lmk"))
    seq: Mapped[int] = mapped_column(Integer, index=True, default=0)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    day: Mapped[str] = mapped_column(String(10), index=True, default="")
    site_id: Mapped[str] = mapped_column(String(40), index=True, default="")
    worker_id: Mapped[str] = mapped_column(String(40), index=True, default="")   # "" = a gang head count
    employer_id: Mapped[str] = mapped_column(String(40), default="")
    gang: Mapped[str] = mapped_column(String(60), default="")
    value: Mapped[float] = mapped_column(Float, default=1.0)                    # 1 present, 0.5 half, 0 absent
    count: Mapped[int] = mapped_column(Integer, default=0)                      # head-count rows only
    hours: Mapped[float] = mapped_column(Float, default=0.0)                    # 0 = a normal day
    ot_hours: Mapped[float] = mapped_column(Float, default=0.0)
    pieces: Mapped[float] = mapped_column(Float, default=0.0)
    source: Mapped[str] = mapped_column(String(10), default="typed")           # typed | voice | photo | device | phone | legacy
    device: Mapped[str] = mapped_column(String(60), default="")
    who: Mapped[str] = mapped_column(String(80), default="")
    at: Mapped[str] = mapped_column(String(19), default="")                     # when it was marked (her time)
    corrects: Mapped[str] = mapped_column(String(40), default="")
    reason: Mapped[str] = mapped_column(String(200), default="")
    note: Mapped[str] = mapped_column(String(200), default="")


class LdGate(Base):
    __tablename__ = "ld_gate"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("lga"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    site_id: Mapped[str] = mapped_column(String(40), default="")
    day: Mapped[str] = mapped_column(String(10), index=True, default="")
    count: Mapped[int] = mapped_column(Integer, default=0)
    source: Mapped[str] = mapped_column(String(120), default="")
    who: Mapped[str] = mapped_column(String(80), default="")


class LdUnknown(Base):
    __tablename__ = "ld_unknown"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("lun"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    site_id: Mapped[str] = mapped_column(String(40), default="")
    day: Mapped[str] = mapped_column(String(10), index=True, default="")
    name: Mapped[str] = mapped_column(String(120), default="")
    value: Mapped[float] = mapped_column(Float, default=1.0)
    source: Mapped[str] = mapped_column(String(10), default="")
    guesses: Mapped[list] = mapped_column(JSON, default=list)
    resolved: Mapped[str] = mapped_column(String(40), default="")              # worker id, or "dropped"
    who: Mapped[str] = mapped_column(String(80), default="")


class LdDayClose(Base):
    __tablename__ = "ld_dayclose"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("ldc"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    site_id: Mapped[str] = mapped_column(String(40), default="")
    day: Mapped[str] = mapped_column(String(10), index=True, default="")
    who: Mapped[str] = mapped_column(String(80), default="")
    seq: Mapped[int] = mapped_column(Integer, default=0)                       # the last mark it covered
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class LdAdvance(Base):
    __tablename__ = "ld_advances"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("lad"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    worker_id: Mapped[str] = mapped_column(String(40), index=True, default="")
    amount: Mapped[float] = mapped_column(Float, default=0.0)
    per_run: Mapped[float] = mapped_column(Float, default=0.0)                 # her schedule; 0 = as much as the cap allows
    recovered: Mapped[float] = mapped_column(Float, default=0.0)
    day: Mapped[str] = mapped_column(String(10), default="")
    given_by: Mapped[str] = mapped_column(String(80), default="")
    note: Mapped[str] = mapped_column(String(200), default="")
    history: Mapped[list] = mapped_column(JSON, default=list)


class LdRun(Base):
    __tablename__ = "ld_runs"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("lrn"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(30), default="")
    employer_id: Mapped[str] = mapped_column(String(40), default="")
    site_id: Mapped[str] = mapped_column(String(40), default="")              # "" = every site
    start: Mapped[str] = mapped_column(String(10), default="")
    end: Mapped[str] = mapped_column(String(10), default="")
    status: Mapped[str] = mapped_column(String(12), default="draft")          # draft | checked | approved | paid | cancelled
    inputs: Mapped[dict] = mapped_column(JSON, default=dict)                   # allowances / piece qty she gave
    lines: Mapped[list] = mapped_column(JSON, default=list)                    # the frozen paper once checked
    total: Mapped[float] = mapped_column(Float, default=0.0)
    hash: Mapped[str] = mapped_column(String(64), default="")
    prepared_by: Mapped[str] = mapped_column(String(80), default="")
    checked_by: Mapped[str] = mapped_column(String(80), default="")
    approved_by: Mapped[str] = mapped_column(String(80), default="")
    approved_by2: Mapped[str] = mapped_column(String(80), default="")
    log: Mapped[list] = mapped_column(JSON, default=list)
    paid: Mapped[dict] = mapped_column(JSON, default=dict)                     # {ref, on, by, failed: {worker_id: why}}
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class LdRule(Base):
    __tablename__ = "ld_rules"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("lru"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    kind: Mapped[str] = mapped_column(String(12), default="levy")             # levy | withholding
    name: Mapped[str] = mapped_column(String(120), default="")
    region: Mapped[str] = mapped_column(String(40), default="")
    base: Mapped[str] = mapped_column(String(14), default="cost_of_work")     # cost_of_work | gross_wages | per_head | per_permit | payment
    rate_pct: Mapped[float] = mapped_column(Float, default=0.0)
    per_unit: Mapped[float] = mapped_column(Float, default=0.0)
    rates: Mapped[dict] = mapped_column(JSON, default=dict)                   # withholding: by status
    limits: Mapped[dict] = mapped_column(JSON, default=dict)                  # {single, year, year_start "04-01", ex_materials}
    due: Mapped[dict] = mapped_column(JSON, default=dict)                     # {type: days_after|monthly, days, day, march}
    source: Mapped[str] = mapped_column(String(300), default="")
    checked_by: Mapped[str] = mapped_column(String(80), default="")
    checked_on: Mapped[str] = mapped_column(String(10), default="")
    review_by: Mapped[str] = mapped_column(String(10), default="")
    pack_id: Mapped[str] = mapped_column(String(40), default="")
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class LdLevy(Base):
    __tablename__ = "ld_levies"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("llv"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    rule_id: Mapped[str] = mapped_column(String(40), default="")
    ref: Mapped[str] = mapped_column(String(80), default="")
    site_id: Mapped[str] = mapped_column(String(40), default="")
    base_amount: Mapped[float] = mapped_column(Float, default=0.0)
    base_source: Mapped[str] = mapped_column(String(200), default="")
    amount: Mapped[float] = mapped_column(Float, default=0.0)
    day: Mapped[str] = mapped_column(String(10), default="")
    due: Mapped[str] = mapped_column(String(10), default="")
    status: Mapped[str] = mapped_column(String(8), default="due")             # due | paid
    receipt_last4: Mapped[str] = mapped_column(String(4), default="")
    paid_on: Mapped[str] = mapped_column(String(10), default="")
    paid_by: Mapped[str] = mapped_column(String(80), default="")
    say: Mapped[str] = mapped_column(String(300), default="")


class LdPayment(Base):
    __tablename__ = "ld_payments"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("lpy"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    employer_id: Mapped[str] = mapped_column(String(40), index=True, default="")
    rule_id: Mapped[str] = mapped_column(String(40), default="")
    ref: Mapped[str] = mapped_column(String(80), default="")
    day: Mapped[str] = mapped_column(String(10), index=True, default="")
    amount: Mapped[float] = mapped_column(Float, default=0.0)
    materials: Mapped[float] = mapped_column(Float, default=0.0)
    base: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(14), default="")              # the status at the time
    rate_pct: Mapped[float] = mapped_column(Float, default=0.0)
    withheld: Mapped[float] = mapped_column(Float, default=0.0)
    why: Mapped[str] = mapped_column(String(400), default="")
    deposited: Mapped[str] = mapped_column(String(10), default="")
    receipt_last4: Mapped[str] = mapped_column(String(4), default="")


class LdFiling(Base):
    __tablename__ = "ld_filings"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("lfi"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    key: Mapped[str] = mapped_column(String(80), index=True, default="")      # what + period
    what: Mapped[str] = mapped_column(String(160), default="")
    due: Mapped[str] = mapped_column(String(10), default="")
    filed_by: Mapped[str] = mapped_column(String(80), default="")
    filed_on: Mapped[str] = mapped_column(String(10), default="")
    ref: Mapped[str] = mapped_column(String(80), default="")


class LdEvidence(Base):
    __tablename__ = "ld_evidence"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("lev"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    employer_id: Mapped[str] = mapped_column(String(40), index=True, default="")
    start: Mapped[str] = mapped_column(String(10), default="")
    end: Mapped[str] = mapped_column(String(10), default="")
    kind: Mapped[str] = mapped_column(String(14), default="")                 # register | payment | contribution | headcount
    people: Mapped[int] = mapped_column(Integer, default=0)
    names: Mapped[list] = mapped_column(JSON, default=list)
    amount: Mapped[float] = mapped_column(Float, default=0.0)
    file_id: Mapped[str] = mapped_column(String(60), default="")
    ref: Mapped[str] = mapped_column(String(80), default="")
    received: Mapped[str] = mapped_column(String(10), default="")
    note: Mapped[str] = mapped_column(String(300), default="")


class LdDecision(Base):
    __tablename__ = "ld_decisions"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("ldd"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    employer_id: Mapped[str] = mapped_column(String(40), default="")
    start: Mapped[str] = mapped_column(String(10), default="")
    end: Mapped[str] = mapped_column(String(10), default="")
    status: Mapped[str] = mapped_column(String(10), default="draft")          # draft | hold | release | direct
    text: Mapped[str] = mapped_column(Text, default="")
    who: Mapped[str] = mapped_column(String(80), default="")
    note: Mapped[str] = mapped_column(String(300), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


ALL = [LdSettings, LdSite, LdEmployer, LdWorker, LdPaper, LdRate, LdMark, LdGate, LdUnknown, LdDayClose, LdAdvance, LdRun, LdRule,
       LdLevy, LdPayment, LdFiling, LdEvidence, LdDecision]
