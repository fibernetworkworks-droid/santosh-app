"""Site Sahayak tables (all prefixed sitesup_). A site may sit ON a Theka project (theka_project_id): then BOQ, measurement
book, RA bills and the hindrance diary stay in theka; this module adds what a supervisor does."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now


class SsSettings(Base):
    __tablename__ = "sitesup_settings"
    tenant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    firm: Mapped[str] = mapped_column(String(160), default="")
    supervisor: Mapped[str] = mapped_column(String(120), default="")
    morning_time: Mapped[str] = mapped_column(String(5), default="08:00")
    dpr_time: Mapped[str] = mapped_column(String(5), default="18:30")
    day_hours: Mapped[float] = mapped_column(Float, default=8.0)
    week_hours: Mapped[float] = mapped_column(Float, default=48.0)
    lookahead_days: Mapped[int] = mapped_column(Integer, default=21)
    behind_pct: Mapped[float] = mapped_column(Float, default=10.0)
    rates: Mapped[str] = mapped_column(Text, default="{}")             # her daily rate per trade (for contractor bill check only)
    cube_limits: Mapped[str] = mapped_column(Text, default="{}")       # her QA plan: individual_minus, mean_plus, sd
    rules: Mapped[str] = mapped_column(Text, default="[]")
    seq: Mapped[str] = mapped_column(Text, default="{}")               # per kind counters
    last_morning: Mapped[str] = mapped_column(String(10), default="")
    last_dpr_nudge: Mapped[str] = mapped_column(String(10), default="")
    told: Mapped[str] = mapped_column(Text, default="[]")              # once-only alert keys (newest 400)


class SsSite(Base):
    __tablename__ = "sitesup_sites"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("ss"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    name: Mapped[str] = mapped_column(String(200), default="")
    address: Mapped[str] = mapped_column(Text, default="")
    client: Mapped[str] = mapped_column(String(160), default="")
    client_phone: Mapped[str] = mapped_column(String(20), default="")
    client_email: Mapped[str] = mapped_column(String(160), default="")
    engineer: Mapped[str] = mapped_column(String(120), default="")
    theka_project_id: Mapped[str] = mapped_column(String(40), default="")
    start: Mapped[str] = mapped_column(String(10), default="")
    finish: Mapped[str] = mapped_column(String(10), default="")
    status: Mapped[str] = mapped_column(String(12), default="running")  # running | stopped | done | closed
    stop_id: Mapped[str] = mapped_column(String(40), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class SsActivity(Base):
    __tablename__ = "sitesup_activities"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("sa"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    site_id: Mapped[str] = mapped_column(String(40), index=True)
    code: Mapped[str] = mapped_column(String(20), default="")
    name: Mapped[str] = mapped_column(String(200), default="")
    location: Mapped[str] = mapped_column(String(160), default="")
    unit: Mapped[str] = mapped_column(String(12), default="")
    qty: Mapped[float] = mapped_column(Float, default=0.0)
    start: Mapped[str] = mapped_column(String(10), default="")
    finish: Mapped[str] = mapped_column(String(10), default="")
    boq_item: Mapped[str] = mapped_column(String(40), default="")      # theka BOQ item code (link only)
    needs: Mapped[str] = mapped_column(Text, default="[]")              # [{item, qty, unit}] material it needs
    contractor: Mapped[str] = mapped_column(String(120), default="")


class SsProgress(Base):
    __tablename__ = "sitesup_progress"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("sp"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    site_id: Mapped[str] = mapped_column(String(40), index=True)
    activity_id: Mapped[str] = mapped_column(String(40), index=True)
    day: Mapped[str] = mapped_column(String(10), index=True)
    qty: Mapped[float] = mapped_column(Float, default=0.0)
    note: Mapped[str] = mapped_column(Text, default="")
    delay: Mapped[str] = mapped_column(Text, default="")
    delay_kind: Mapped[str] = mapped_column(String(16), default="")
    by_client: Mapped[bool] = mapped_column(Boolean, default=False)
    lost_hours: Mapped[float] = mapped_column(Float, default=0.0)
    by: Mapped[str] = mapped_column(String(80), default="")


class SsLabour(Base):
    __tablename__ = "sitesup_labour"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("sl"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    site_id: Mapped[str] = mapped_column(String(40), index=True)
    day: Mapped[str] = mapped_column(String(10), index=True)
    contractor: Mapped[str] = mapped_column(String(120), default="")
    trade: Mapped[str] = mapped_column(String(20), default="other")
    worker: Mapped[str] = mapped_column(String(120), default="")       # empty = a group row
    count: Mapped[int] = mapped_column(Integer, default=1)
    hours: Mapped[float] = mapped_column(Float, default=8.0)
    normal: Mapped[float] = mapped_column(Float, default=8.0)
    ot: Mapped[float] = mapped_column(Float, default=0.0)
    gender: Mapped[str] = mapped_column(String(1), default="")
    id_ref: Mapped[str] = mapped_column(String(60), default="")       # Pehchaan Locker {id:...} only
    by: Mapped[str] = mapped_column(String(80), default="")


class SsMaterial(Base):
    __tablename__ = "sitesup_material"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("sm"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    site_id: Mapped[str] = mapped_column(String(40), index=True)
    day: Mapped[str] = mapped_column(String(10), default="")
    item: Mapped[str] = mapped_column(String(80), default="")
    unit: Mapped[str] = mapped_column(String(12), default="")
    qty: Mapped[float] = mapped_column(Float, default=0.0)           # + received, - used / returned
    kind: Mapped[str] = mapped_column(String(10), default="in")     # in | used | return | waste
    supplier: Mapped[str] = mapped_column(String(160), default="")
    challan: Mapped[str] = mapped_column(String(60), default="")
    vehicle: Mapped[str] = mapped_column(String(20), default="")
    ok: Mapped[bool] = mapped_column(Boolean, default=True)
    note: Mapped[str] = mapped_column(String(300), default="")
    indent_id: Mapped[str] = mapped_column(String(40), default="")
    by: Mapped[str] = mapped_column(String(80), default="")


class SsIndent(Base):
    __tablename__ = "sitesup_indents"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("si"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    site_id: Mapped[str] = mapped_column(String(40), index=True)
    number: Mapped[str] = mapped_column(String(20), default="")
    items: Mapped[str] = mapped_column(Text, default="[]")            # [{item, qty, unit, rate?}]
    need_by: Mapped[str] = mapped_column(String(10), default="")
    reason: Mapped[str] = mapped_column(Text, default="")
    supplier: Mapped[str] = mapped_column(String(160), default="")
    supplier_phone: Mapped[str] = mapped_column(String(20), default="")
    amount: Mapped[float] = mapped_column(Float, default=0.0)         # only from her / supplier's quote; 0 = not known
    checks: Mapped[str] = mapped_column(Text, default="[]")
    status: Mapped[str] = mapped_column(String(12), default="waiting")  # waiting | approved | rejected | ordered | received | stale
    hash: Mapped[str] = mapped_column(String(64), default="")
    reason_no: Mapped[str] = mapped_column(String(300), default="")
    asked_by: Mapped[str] = mapped_column(String(80), default="")
    conv: Mapped[str] = mapped_column(String(40), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class SsSafety(Base):
    """Toolbox talks, checklists and the incident register (kind talk | check | incident)."""
    __tablename__ = "sitesup_safety"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("sf"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    site_id: Mapped[str] = mapped_column(String(40), index=True)
    kind: Mapped[str] = mapped_column(String(10), default="talk")
    number: Mapped[str] = mapped_column(String(20), default="")
    day: Mapped[str] = mapped_column(String(10), index=True)
    at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sub: Mapped[str] = mapped_column(String(20), default="")          # topic id / checklist kind / incident kind
    text: Mapped[str] = mapped_column(Text, default="")
    data: Mapped[str] = mapped_column(Text, default="{}")
    people: Mapped[int] = mapped_column(Integer, default=0)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reported: Mapped[str] = mapped_column(String(160), default="")   # her reference once she filed Form XI
    by: Mapped[str] = mapped_column(String(80), default="")


class SsStop(Base):
    __tablename__ = "sitesup_stops"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("sw"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    site_id: Mapped[str] = mapped_column(String(40), index=True)
    number: Mapped[str] = mapped_column(String(20), default="")
    area: Mapped[str] = mapped_column(String(200), default="")
    reason: Mapped[str] = mapped_column(Text, default="")
    source: Mapped[str] = mapped_column(String(40), default="")       # safety row id
    contractor: Mapped[str] = mapped_column(String(120), default="")
    status: Mapped[str] = mapped_column(String(12), default="waiting")  # waiting | active | rejected | lifted | stale
    hash: Mapped[str] = mapped_column(String(64), default="")
    lift_note: Mapped[str] = mapped_column(String(300), default="")
    asked_by: Mapped[str] = mapped_column(String(80), default="")
    conv: Mapped[str] = mapped_column(String(40), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class SsPour(Base):
    __tablename__ = "sitesup_pours"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("pc"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    site_id: Mapped[str] = mapped_column(String(40), index=True)
    number: Mapped[str] = mapped_column(String(20), default="")
    element: Mapped[str] = mapped_column(String(200), default="")
    grade: Mapped[str] = mapped_column(String(12), default="")
    cement: Mapped[str] = mapped_column(String(40), default="")
    volume: Mapped[float] = mapped_column(Float, default=0.0)
    day: Mapped[str] = mapped_column(String(10), default="")
    source: Mapped[str] = mapped_column(String(120), default="")      # RMC plant / site mix
    slump: Mapped[str] = mapped_column(String(20), default="")
    checks: Mapped[str] = mapped_column(Text, default="{}")
    samples: Mapped[int] = mapped_column(Integer, default=1)
    curing_until: Mapped[str] = mapped_column(String(10), default="")
    by: Mapped[str] = mapped_column(String(80), default="")


class SsCube(Base):
    __tablename__ = "sitesup_cubes"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("cb"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    pour_id: Mapped[str] = mapped_column(String(40), index=True)
    sample: Mapped[int] = mapped_column(Integer, default=1)
    age: Mapped[int] = mapped_column(Integer, default=28)
    due: Mapped[str] = mapped_column(String(10), index=True)
    results: Mapped[str] = mapped_column(Text, default="[]")
    verdict: Mapped[str] = mapped_column(String(16), default="")      # "" = pending
    lab: Mapped[str] = mapped_column(String(120), default="")
    tested_on: Mapped[str] = mapped_column(String(10), default="")


class SsSnag(Base):
    __tablename__ = "sitesup_snags"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("sn"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    site_id: Mapped[str] = mapped_column(String(40), index=True)
    number: Mapped[str] = mapped_column(String(20), default="")
    location: Mapped[str] = mapped_column(String(160), default="")
    text: Mapped[str] = mapped_column(Text, default="")
    trade: Mapped[str] = mapped_column(String(20), default="")
    contractor: Mapped[str] = mapped_column(String(120), default="")
    due: Mapped[str] = mapped_column(String(10), default="")
    status: Mapped[str] = mapped_column(String(10), default="open")    # open | fixed | verified
    day: Mapped[str] = mapped_column(String(10), default="")
    by: Mapped[str] = mapped_column(String(80), default="")


class SsPhoto(Base):
    __tablename__ = "sitesup_photos"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("ph"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    site_id: Mapped[str] = mapped_column(String(40), index=True)
    ref: Mapped[str] = mapped_column(String(40), index=True)          # snag / safety / pour / progress / material id ("" = site)
    stage: Mapped[str] = mapped_column(String(12), default="site")    # site | snag | fixed | incident | pour | material | progress
    day: Mapped[str] = mapped_column(String(10), default="")
    path: Mapped[str] = mapped_column(String(300), default="")
    note: Mapped[str] = mapped_column(String(200), default="")


class SsReport(Base):
    """DPR and other things going to the client: draft -> waiting (card with hash) -> approved (her tap) -> sent."""
    __tablename__ = "sitesup_reports"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("dp"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    site_id: Mapped[str] = mapped_column(String(40), index=True)
    kind: Mapped[str] = mapped_column(String(10), default="dpr")     # dpr | message
    number: Mapped[str] = mapped_column(String(20), default="")
    day: Mapped[str] = mapped_column(String(10), default="")
    data: Mapped[str] = mapped_column(Text, default="{}")
    text: Mapped[str] = mapped_column(Text, default="")
    file_id: Mapped[str] = mapped_column(String(80), default="")
    to_phone: Mapped[str] = mapped_column(String(20), default="")
    status: Mapped[str] = mapped_column(String(12), default="draft")  # draft | waiting | approved | sent | rejected | stale
    hash: Mapped[str] = mapped_column(String(64), default="")
    via: Mapped[str] = mapped_column(String(10), default="")
    conv: Mapped[str] = mapped_column(String(40), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
