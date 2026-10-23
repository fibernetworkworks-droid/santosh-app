"""Tables of the Archassist Sahayak (architect's assistant), all prefixed archassist_."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now


class ArchSettings(Base):
    __tablename__ = "archassist_settings"
    tenant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    firm: Mapped[str] = mapped_column(String(160), default="")
    architect: Mapped[str] = mapped_column(String(120), default="")
    coa_no: Mapped[str] = mapped_column(String(40), default="")          # CoA registration number (public on every drawing)
    coa_valid_to: Mapped[str] = mapped_column(String(10), default="")
    gstin: Mapped[str] = mapped_column(String(15), default="")
    address: Mapped[str] = mapped_column(Text, default="")
    phone: Mapped[str] = mapped_column(String(20), default="")
    email: Mapped[str] = mapped_column(String(120), default="")
    upi_id: Mapped[str] = mapped_column(String(80), default="")
    ruleset: Mapped[str] = mapped_column(String(20), default="udcpr")
    fee_stages: Mapped[str] = mapped_column(Text, default="")             # her own stage split JSON ("" = starter)
    terms: Mapped[str] = mapped_column(Text, default="")
    rules: Mapped[str] = mapped_column(Text, default="")
    morning_time: Mapped[str] = mapped_column(String(5), default="09:00")
    last_morning: Mapped[str] = mapped_column(String(10), default="")
    inv_prefix: Mapped[str] = mapped_column(String(12), default="AR")
    seq: Mapped[str] = mapped_column(Text, default="{}")                 # counters {project, transmittal, rfi, meeting, sub, inv:<fy>}


class ArchProject(Base):
    __tablename__ = "archassist_projects"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("ap"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(16), default="")
    name: Mapped[str] = mapped_column(String(160), default="")
    client: Mapped[str] = mapped_column(String(160), default="")
    client_phone: Mapped[str] = mapped_column(String(20), default="")
    client_email: Mapped[str] = mapped_column(String(120), default="")
    client_gstin: Mapped[str] = mapped_column(String(15), default="")
    client_pan_ref: Mapped[str] = mapped_column(String(80), default="")   # {id:...} Pehchaan Locker reference only
    site: Mapped[str] = mapped_column(Text, default="")
    pin: Mapped[str] = mapped_column(String(6), default="")
    city: Mapped[str] = mapped_column(String(80), default="")
    authority: Mapped[str] = mapped_column(String(20), default="maha_bpms")
    ruleset: Mapped[str] = mapped_column(String(20), default="udcpr")
    use: Mapped[str] = mapped_column(String(20), default="residential")
    plot: Mapped[str] = mapped_column(Text, default="{}")                 # survey / cts no, area_sqm, road_width_m, deductions, flags
    proposal: Mapped[str] = mapped_column(Text, default="{}")             # floors, height, margins, units, parking
    overrides: Mapped[str] = mapped_column(Text, default="{}")            # HER rule numbers
    docs: Mapped[str] = mapped_column(Text, default="{}")                 # {key: {state have|missing|na, file_id, note}}
    approvals: Mapped[str] = mapped_column(Text, default="{}")            # {stage/noc key: {status, ref, on, valid_to, file_id, why}}
    area: Mapped[str] = mapped_column(Text, default="{}")                 # last area statement
    fee: Mapped[str] = mapped_column(Text, default="{}")                  # {basis, percent, project_cost, lump, stages[]}
    rera_no: Mapped[str] = mapped_column(String(40), default="")
    status: Mapped[str] = mapped_column(String(16), default="active")    # active | on_hold | done | dropped
    notes: Mapped[str] = mapped_column(Text, default="")
    forgotten: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class ArchDrawing(Base):
    __tablename__ = "archassist_drawings"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("ad"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    project_id: Mapped[str] = mapped_column(String(40), index=True)
    sheet: Mapped[str] = mapped_column(String(24), default="")
    title: Mapped[str] = mapped_column(String(160), default="")
    discipline: Mapped[str] = mapped_column(String(2), default="A")
    scale: Mapped[str] = mapped_column(String(20), default="")
    rev: Mapped[str] = mapped_column(String(10), default="")
    status: Mapped[str] = mapped_column(String(16), default="draft")     # draft | for_approval | for_construction | superseded
    revisions: Mapped[str] = mapped_column(Text, default="[]")           # [{rev, on, note, file_id, by}]
    issued: Mapped[str] = mapped_column(Text, default="[]")              # [{transmittal, rev, to, on}]
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)


class ArchTransmittal(Base):
    __tablename__ = "archassist_transmittals"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("at"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    project_id: Mapped[str] = mapped_column(String(40), index=True)
    number: Mapped[str] = mapped_column(String(16), default="")
    to_kind: Mapped[str] = mapped_column(String(16), default="client")
    to_name: Mapped[str] = mapped_column(String(160), default="")
    to_contact: Mapped[str] = mapped_column(String(120), default="")
    purpose: Mapped[str] = mapped_column(String(20), default="for_approval")
    items: Mapped[str] = mapped_column(Text, default="[]")               # [{drawing_id, sheet, rev, title, file_id, copies, format}]
    note: Mapped[str] = mapped_column(Text, default="")
    hash: Mapped[str] = mapped_column(String(64), default="")
    status: Mapped[str] = mapped_column(String(12), default="draft")     # draft | waiting | issued | rejected | stale
    reason: Mapped[str] = mapped_column(Text, default="")
    file_id: Mapped[str] = mapped_column(String(60), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ArchSubmission(Base):
    __tablename__ = "archassist_submissions"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("as"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    project_id: Mapped[str] = mapped_column(String(40), index=True)
    number: Mapped[str] = mapped_column(String(16), default="")
    stage: Mapped[str] = mapped_column(String(20), default="building_permission")
    authority: Mapped[str] = mapped_column(String(20), default="")
    snapshot: Mapped[str] = mapped_column(Text, default="{}")            # documents, drawings, area numbers as on the card
    hash: Mapped[str] = mapped_column(String(64), default="")
    status: Mapped[str] = mapped_column(String(12), default="waiting")   # waiting | approved | submitted | granted | query | refused | rejected | stale
    ref: Mapped[str] = mapped_column(String(80), default="")             # inward / application number from the portal
    on: Mapped[str] = mapped_column(String(10), default="")
    valid_to: Mapped[str] = mapped_column(String(10), default="")
    note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ArchConsultant(Base):
    __tablename__ = "archassist_consultants"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("ac"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    name: Mapped[str] = mapped_column(String(120), default="")
    firm: Mapped[str] = mapped_column(String(160), default="")
    kind: Mapped[str] = mapped_column(String(16), default="structural")
    phone: Mapped[str] = mapped_column(String(20), default="")
    email: Mapped[str] = mapped_column(String(120), default="")
    licence: Mapped[str] = mapped_column(String(60), default="")


class ArchRfi(Base):
    __tablename__ = "archassist_rfis"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("ar"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    project_id: Mapped[str] = mapped_column(String(40), index=True)
    number: Mapped[str] = mapped_column(String(16), default="")
    direction: Mapped[str] = mapped_column(String(4), default="out")     # out (we ask) | in (they ask us)
    party: Mapped[str] = mapped_column(String(160), default="")
    consultant_id: Mapped[str] = mapped_column(String(40), default="")
    subject: Mapped[str] = mapped_column(String(200), default="")
    question: Mapped[str] = mapped_column(Text, default="")
    sheets: Mapped[str] = mapped_column(Text, default="[]")
    due: Mapped[str] = mapped_column(String(10), default="")
    status: Mapped[str] = mapped_column(String(10), default="open")      # open | answered | closed
    answer: Mapped[str] = mapped_column(Text, default="")
    reminded: Mapped[str] = mapped_column(String(10), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class ArchMeeting(Base):
    __tablename__ = "archassist_meetings"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("am"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    project_id: Mapped[str] = mapped_column(String(40), index=True)
    number: Mapped[str] = mapped_column(String(16), default="")
    on: Mapped[str] = mapped_column(String(10), default="")
    place: Mapped[str] = mapped_column(String(160), default="")
    attendees: Mapped[str] = mapped_column(Text, default="[]")
    points: Mapped[str] = mapped_column(Text, default="[]")              # [{n, point, by, due, done}]
    file_id: Mapped[str] = mapped_column(String(60), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class ArchInvoice(Base):
    __tablename__ = "archassist_invoices"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("ai"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    project_id: Mapped[str] = mapped_column(String(40), index=True)
    stage: Mapped[str] = mapped_column(String(20), default="")
    label: Mapped[str] = mapped_column(String(160), default="")
    amount: Mapped[float] = mapped_column(Float, default=0.0)
    tax: Mapped[str] = mapped_column(Text, default="{}")
    tds: Mapped[float] = mapped_column(Float, default=0.0)
    total: Mapped[float] = mapped_column(Float, default=0.0)
    number: Mapped[str] = mapped_column(String(24), default="")
    hash: Mapped[str] = mapped_column(String(64), default="")
    status: Mapped[str] = mapped_column(String(12), default="waiting")   # waiting | issued | paid | rejected | cancelled | stale
    reason: Mapped[str] = mapped_column(Text, default="")
    issued_on: Mapped[str] = mapped_column(String(10), default="")
    file_id: Mapped[str] = mapped_column(String(60), default="")
    paid_amount: Mapped[float] = mapped_column(Float, default=0.0)
    tds_deducted: Mapped[float] = mapped_column(Float, default=0.0)
    paid_on: Mapped[str] = mapped_column(String(10), default="")
    paid_ref: Mapped[str] = mapped_column(String(60), default="")
    reminded: Mapped[str] = mapped_column(String(10), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class ArchOnce(Base):
    __tablename__ = "archassist_once"
    key: Mapped[str] = mapped_column(String(200), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    n: Mapped[int] = mapped_column(Integer, default=1)
