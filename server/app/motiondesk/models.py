"""Tables of the Motion designer desk (all prefixed motiondesk_). JSON kept in Text columns (banquet / interior pattern)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now


class MotiondeskSettings(Base):
    __tablename__ = "motiondesk_settings"
    tenant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    studio: Mapped[str] = mapped_column(String(160), default="")
    gstin: Mapped[str] = mapped_column(String(15), default="")
    address: Mapped[str] = mapped_column(Text, default="")
    phone: Mapped[str] = mapped_column(String(20), default="")
    email: Mapped[str] = mapped_column(String(120), default="")
    upi_id: Mapped[str] = mapped_column(String(80), default="")
    gst_pct: Mapped[float] = mapped_column(Float, default=18.0)
    sac: Mapped[str] = mapped_column(String(8), default="998391")
    rounds: Mapped[int] = mapped_column(Integer, default=2)               # revision rounds included in a quote (starter)
    round_fee: Mapped[float | None] = mapped_column(Float, nullable=True)  # HER price for one extra round (None = not said)
    advance_pct: Mapped[float] = mapped_column(Float, default=50.0)
    pay_days: Mapped[int] = mapped_column(Integer, default=15)
    rights: Mapped[str] = mapped_column(String(12), default="licence")    # licence | assign (what the handover note says)
    rights_years: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rights_territory: Mapped[str] = mapped_column(String(60), default="")
    terms: Mapped[str] = mapped_column(Text, default="")
    rules: Mapped[str] = mapped_column(Text, default="")
    morning_time: Mapped[str] = mapped_column(String(5), default="09:30")
    last_morning: Mapped[str] = mapped_column(String(10), default="")
    job_seq: Mapped[int] = mapped_column(Integer, default=0)
    client_seq: Mapped[int] = mapped_column(Integer, default=0)
    inv_seq: Mapped[int] = mapped_column(Integer, default=0)
    inv_fy: Mapped[str] = mapped_column(String(4), default="")


class MotiondeskClient(Base):
    __tablename__ = "motiondesk_clients"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("mdc"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(12), default="")
    name: Mapped[str] = mapped_column(String(160), default="")
    contact: Mapped[str] = mapped_column(String(120), default="")
    phone: Mapped[str] = mapped_column(String(20), default="")
    email: Mapped[str] = mapped_column(String(120), default="")
    gstin: Mapped[str] = mapped_column(String(15), default="")
    state: Mapped[str] = mapped_column(String(40), default="")
    kit: Mapped[str] = mapped_column(Text, default="{}")                 # {colors, fonts[], tone, dos, donts, tagline}
    logo_path: Mapped[str] = mapped_column(Text, default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    forgotten: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class MotiondeskAsset(Base):
    """Licence register: fonts, music, stock, templates, 3D models she uses (proof of the right to use them)."""
    __tablename__ = "motiondesk_assets"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("mda"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    kind: Mapped[str] = mapped_column(String(16), default="other")
    name: Mapped[str] = mapped_column(String(160), default="")
    source: Mapped[str] = mapped_column(String(40), default="")
    licence: Mapped[str] = mapped_column(String(24), default="unknown")
    licence_ref: Mapped[str] = mapped_column(String(160), default="")
    proof_file: Mapped[str] = mapped_column(String(80), default="")
    credit: Mapped[str] = mapped_column(String(200), default="")
    valid_until: Mapped[str] = mapped_column(String(10), default="")
    project_job: Mapped[str] = mapped_column(String(40), default="")      # single-project licences: the job it is registered to
    jobs: Mapped[str] = mapped_column(Text, default="[]")
    note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class MotiondeskTemplate(Base):
    """Her own template library: an engine + its data saved from a job (re-used with another client's colours)."""
    __tablename__ = "motiondesk_templates"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("mdt"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    name: Mapped[str] = mapped_column(String(120), default="")
    engine: Mapped[str] = mapped_column(String(12), default="motion")
    kind: Mapped[str] = mapped_column(String(20), default="")
    data: Mapped[str] = mapped_column(Text, default="{}")
    frames: Mapped[str] = mapped_column(Text, default="[]")
    assets: Mapped[str] = mapped_column(Text, default="[]")
    uses: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class MotiondeskJob(Base):
    __tablename__ = "motiondesk_jobs"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("mdj"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(12), default="")
    client_id: Mapped[str] = mapped_column(String(40), default="")
    title: Mapped[str] = mapped_column(String(200), default="")
    brief: Mapped[str] = mapped_column(Text, default="")
    engine: Mapped[str] = mapped_column(String(12), default="motion")      # motion | blender3d | brand | photo
    kind: Mapped[str] = mapped_column(String(20), default="explainer")     # motion kind / brand kind
    data: Mapped[str] = mapped_column(Text, default="{}")                   # engine data (motion plan fields)
    deliverables: Mapped[str] = mapped_column(Text, default="[]")
    deadline: Mapped[str] = mapped_column(String(10), default="")
    status: Mapped[str] = mapped_column(String(16), default="brief")
    frames: Mapped[str] = mapped_column(Text, default="[]")
    sb_version: Mapped[int] = mapped_column(Integer, default=0)
    sb_hash: Mapped[str] = mapped_column(String(64), default="")            # storyboard the client said yes to
    sb_by: Mapped[str] = mapped_column(String(200), default="")
    quote: Mapped[str] = mapped_column(Text, default="[]")                  # [{text, qty, rate}] HER prices
    rounds: Mapped[int] = mapped_column(Integer, default=2)
    rounds_used: Mapped[int] = mapped_column(Integer, default=0)
    rounds_paid: Mapped[int] = mapped_column(Integer, default=0)
    renders: Mapped[str] = mapped_column(Text, default="[]")
    feedback: Mapped[str] = mapped_column(Text, default="[]")
    assets: Mapped[str] = mapped_column(Text, default="[]")
    template_id: Mapped[str] = mapped_column(String(40), default="")
    delivered: Mapped[str] = mapped_column(Text, default="{}")
    log: Mapped[str] = mapped_column(Text, default="[]")
    conv: Mapped[str] = mapped_column(String(40), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class MotiondeskCard(Base):
    __tablename__ = "motiondesk_cards"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("mdk"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    job_id: Mapped[str] = mapped_column(String(40), default="", index=True)
    kind: Mapped[str] = mapped_column(String(16), default="")              # storyboard | final | invoice | extra_round | message
    show: Mapped[str] = mapped_column(Text, default="{}")
    hash: Mapped[str] = mapped_column(String(64), default="")
    status: Mapped[str] = mapped_column(String(10), default="waiting")     # waiting | approved | rejected | stale
    asked_by: Mapped[str] = mapped_column(String(80), default="")
    reason: Mapped[str] = mapped_column(Text, default="")
    result: Mapped[str] = mapped_column(Text, default="{}")
    conv: Mapped[str] = mapped_column(String(40), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class MotiondeskInvoice(Base):
    __tablename__ = "motiondesk_invoices"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("mdi"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    job_id: Mapped[str] = mapped_column(String(40), default="")
    number: Mapped[str] = mapped_column(String(24), default="")
    kind: Mapped[str] = mapped_column(String(10), default="final")         # advance | final | extra
    lines: Mapped[str] = mapped_column(Text, default="[]")
    taxable: Mapped[float] = mapped_column(Float, default=0.0)
    gst: Mapped[str] = mapped_column(Text, default="{}")
    total: Mapped[float] = mapped_column(Float, default=0.0)
    paid: Mapped[float] = mapped_column(Float, default=0.0)
    paid_ref: Mapped[str] = mapped_column(String(60), default="")
    status: Mapped[str] = mapped_column(String(10), default="issued")      # issued | paid | part | void
    day: Mapped[str] = mapped_column(String(10), default="")
    due: Mapped[str] = mapped_column(String(10), default="")
    reminded: Mapped[str] = mapped_column(String(40), default="")


class MotiondeskAlert(Base):
    __tablename__ = "motiondesk_alerts"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("mdx"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    key: Mapped[str] = mapped_column(String(160), default="", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
