"""Tables of the Graphic Sahayak (all prefixed graphic_). JSON lives in Text columns (pattern of banquet / interior)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now


class GraphicSettings(Base):
    __tablename__ = "graphic_settings"
    tenant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    studio: Mapped[str] = mapped_column(String(160), default="")
    designer: Mapped[str] = mapped_column(String(120), default="")     # her name (copyright assignor)
    gstin: Mapped[str] = mapped_column(String(15), default="")
    state: Mapped[str] = mapped_column(String(20), default="")         # 27 / MH when no GSTIN
    address: Mapped[str] = mapped_column(Text, default="")
    phone: Mapped[str] = mapped_column(String(20), default="")
    email: Mapped[str] = mapped_column(String(120), default="")
    upi_id: Mapped[str] = mapped_column(String(80), default="")
    gst_rate: Mapped[float] = mapped_column(Float, default=18.0)
    sac: Mapped[str] = mapped_column(String(10), default="998391")
    lut: Mapped[str] = mapped_column(String(40), default="")           # LUT ARN for exports (zero-rated)
    udyam: Mapped[str] = mapped_column(String(30), default="")         # MSME number -> 45-day payment note
    rounds: Mapped[int] = mapped_column(Integer, default=2)            # revision rounds included by default
    extra_round: Mapped[float | None] = mapped_column(Float, nullable=True)   # HER price per extra round (None = not said)
    advance_pct: Mapped[float] = mapped_column(Float, default=50.0)
    pay_days: Mapped[int] = mapped_column(Integer, default=15)
    validity_days: Mapped[int] = mapped_column(Integer, default=15)
    handover_after_pay: Mapped[bool] = mapped_column(Boolean, default=True)
    assign_copyright: Mapped[bool] = mapped_column(Boolean, default=True)    # written assignment in the handover pack
    terms: Mapped[str] = mapped_column(Text, default="")
    rules: Mapped[str] = mapped_column(Text, default="[]")
    morning_time: Mapped[str] = mapped_column(String(5), default="09:30")
    last_morning: Mapped[str] = mapped_column(String(10), default="")
    job_seq: Mapped[int] = mapped_column(Integer, default=0)
    inv_seq: Mapped[int] = mapped_column(Integer, default=0)
    q_seq: Mapped[int] = mapped_column(Integer, default=0)


class GraphicClient(Base):
    __tablename__ = "graphic_clients"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("gc"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(10), default="")       # C-001
    name: Mapped[str] = mapped_column(String(120), default="")
    business: Mapped[str] = mapped_column(String(160), default="")
    kind: Mapped[str] = mapped_column(String(10), default="business")  # business | individual
    phone: Mapped[str] = mapped_column(String(20), default="")
    email: Mapped[str] = mapped_column(String(120), default="")
    gstin: Mapped[str] = mapped_column(String(15), default="")
    state: Mapped[str] = mapped_column(String(20), default="")
    country: Mapped[str] = mapped_column(String(40), default="India")
    tds_pct: Mapped[float | None] = mapped_column(Float, nullable=True)       # what the CLIENT says it deducts
    # the client's brand kit (rendered by the brand engine with THESE values, not her own kit)
    tagline: Mapped[str] = mapped_column(String(160), default="")
    colors: Mapped[str] = mapped_column(Text, default="{}")
    colors_set: Mapped[bool] = mapped_column(Boolean, default=False)
    palette: Mapped[str] = mapped_column(Text, default="[]")
    font: Mapped[str] = mapped_column(String(20), default="poppins")
    logo_path: Mapped[str] = mapped_column(String(300), default="")
    logo_hash: Mapped[str] = mapped_column(String(64), default="")
    contact: Mapped[str] = mapped_column(Text, default="{}")             # what goes ON their designs
    language: Mapped[str] = mapped_column(String(10), default="hinglish")
    notes: Mapped[str] = mapped_column(Text, default="")
    no_messages: Mapped[bool] = mapped_column(Boolean, default=False)
    forgotten: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class GraphicVendor(Base):
    __tablename__ = "graphic_vendors"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("gv"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    name: Mapped[str] = mapped_column(String(120), default="")
    phone: Mapped[str] = mapped_column(String(20), default="")
    email: Mapped[str] = mapped_column(String(120), default="")
    does: Mapped[str] = mapped_column(Text, default="")                 # offset, digital, flex, packaging ...
    spec: Mapped[str] = mapped_column(Text, default="{}")              # {color, dpi, bleed, safe, format, pdfx, min_font_pt}
    notes: Mapped[str] = mapped_column(Text, default="")
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class GraphicJob(Base):
    __tablename__ = "graphic_jobs"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("gj"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(10), default="")       # G-0001
    client_id: Mapped[str] = mapped_column(String(40), index=True, default="")
    kind: Mapped[str] = mapped_column(String(16), default="other")
    title: Mapped[str] = mapped_column(String(160), default="")
    brief: Mapped[str] = mapped_column(Text, default="")               # client's / her words (data, scrubbed)
    facts: Mapped[str] = mapped_column(Text, default="")               # what may go on the design (her words)
    sizes: Mapped[str] = mapped_column(Text, default="[]")            # brand engine screen sizes
    print_fmt: Mapped[str] = mapped_column(String(20), default="")    # rules.FORMATS key or 'custom'
    print_custom: Mapped[str] = mapped_column(Text, default="{}")     # {w_mm, h_mm, bleed_mm, safe_mm}
    print_job: Mapped[str] = mapped_column(Text, default="{}")        # {qty, stock, finish, sides, notes}
    vendor_id: Mapped[str] = mapped_column(String(40), default="")
    due: Mapped[str] = mapped_column(String(10), default="")
    lines: Mapped[str] = mapped_column(Text, default="[]")            # quote lines [{name, qty, rate}] HER prices
    discount: Mapped[float] = mapped_column(Float, default=0.0)        # only by her fingerprint tap
    rounds_included: Mapped[int] = mapped_column(Integer, default=2)
    rounds_used: Mapped[int] = mapped_column(Integer, default=0)
    extra_rounds: Mapped[int] = mapped_column(Integer, default=0)      # paid extra rounds she approved
    extra_round_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    waived_rounds: Mapped[int] = mapped_column(Integer, default=0)
    advance_pct: Mapped[float] = mapped_column(Float, default=50.0)
    status: Mapped[str] = mapped_column(String(12), default="brief")   # brief|quoted|accepted|proof|approved|delivered|done|cancelled
    feedback: Mapped[str] = mapped_column(Text, default="[]")         # [{at, version, text, by, round}]
    pending_feedback: Mapped[bool] = mapped_column(Boolean, default=False)
    client_ok: Mapped[str] = mapped_column(Text, default="{}")        # {version, at, evidence}
    assets: Mapped[str] = mapped_column(Text, default="[]")           # fonts / pictures / icons with licence
    tm: Mapped[str] = mapped_column(Text, default="{}")               # logo: {classes, result, notes, at}
    assignment: Mapped[str] = mapped_column(Text, default="{}")       # {rights, years, territory}
    payments: Mapped[str] = mapped_column(Text, default="[]")         # [{amount, mode, ref, day}]
    invoices: Mapped[str] = mapped_column(Text, default="[]")         # [{number, kind, total, day, file_id}]
    quote_ok: Mapped[str] = mapped_column(Text, default="")            # hash of the quote she sent
    accepted: Mapped[str] = mapped_column(Text, default="{}")         # {at, evidence}
    handover: Mapped[str] = mapped_column(Text, default="{}")
    log: Mapped[str] = mapped_column(Text, default="[]")
    conv: Mapped[str] = mapped_column(String(40), default="")
    forgotten: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class GraphicVersion(Base):
    """One proof version of a job: made by the brand engine (render) or her own artwork file (upload)."""
    __tablename__ = "graphic_versions"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("gr"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    job_id: Mapped[str] = mapped_column(String(40), index=True)
    n: Mapped[int] = mapped_column(Integer, default=1)
    source: Mapped[str] = mapped_column(String(8), default="render")   # render | upload
    content: Mapped[str] = mapped_column(Text, default="{}")
    layout: Mapped[str] = mapped_column(String(20), default="hero")
    sizes: Mapped[str] = mapped_column(Text, default="[]")
    proofs: Mapped[str] = mapped_column(Text, default="{}")           # size -> file name in the job folder
    file_name: Mapped[str] = mapped_column(String(200), default="")   # upload: her artwork file in the job folder
    file_mime: Mapped[str] = mapped_column(String(60), default="")
    preflight: Mapped[str] = mapped_column(Text, default="{}")
    checks: Mapped[str] = mapped_column(Text, default="[]")
    file_hash: Mapped[str] = mapped_column(String(64), default="")
    round: Mapped[int] = mapped_column(Integer, default=0)             # which revision round made it (0 = first)
    status: Mapped[str] = mapped_column(String(10), default="draft")   # draft | sent | client_ok | final | old
    note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class GraphicCard(Base):
    """Everything that waits for HER tap: quote | proof | extra | handover | vendor | invoice | discount | message."""
    __tablename__ = "graphic_cards"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("gk"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    job_id: Mapped[str] = mapped_column(String(40), index=True, default="")
    kind: Mapped[str] = mapped_column(String(10))
    show: Mapped[str] = mapped_column(Text, default="{}")
    hash: Mapped[str] = mapped_column(String(64), default="")
    status: Mapped[str] = mapped_column(String(10), default="waiting")  # waiting|approved|rejected|stale
    asked_by: Mapped[str] = mapped_column(String(80), default="")
    reason: Mapped[str] = mapped_column(Text, default="")
    result: Mapped[str] = mapped_column(Text, default="{}")
    conv: Mapped[str] = mapped_column(String(40), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class GraphicAlert(Base):
    __tablename__ = "graphic_alerts"
    key: Mapped[str] = mapped_column(String(200), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
