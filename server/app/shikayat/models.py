"""Shikayat Sahayak tables (all prefixed `shikayat_`)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now


class ShikayatSettings(Base):
    __tablename__ = "shikayat_settings"
    tenant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    business: Mapped[str] = mapped_column(String(160), default="")
    sector: Mapped[str] = mapped_column(String(20), default="general")
    ack_hours: Mapped[float] = mapped_column(Float, default=0.0)          # 0 = the sector's rule
    resolve_days: Mapped[float] = mapped_column(Float, default=0.0)
    reopen_days: Mapped[int] = mapped_column(Integer, default=30)
    silence_days: Mapped[int] = mapped_column(Integer, default=14)        # no reply after the closing message = may close
    officer: Mapped[str] = mapped_column(Text, default="{}")              # grievance officer {name, phone, email}
    comp_limit: Mapped[float] = mapped_column(Float, default=0.0)         # her own "above this, think twice" (0 = none)
    month_limit: Mapped[float] = mapped_column(Float, default=0.0)        # compensation this month ceiling (0 = none)
    close_template: Mapped[str] = mapped_column(Text, default="")
    rules: Mapped[str] = mapped_column(Text, default="[]")                # her rule sentences
    team: Mapped[str] = mapped_column(Text, default="[]")                 # [{name, phone}] who can own a complaint
    learned: Mapped[str] = mapped_column(Text, default="{}")              # cause -> {cases, days, comp}
    morning_time: Mapped[str] = mapped_column(String(5), default="09:30")
    last_morning: Mapped[str] = mapped_column(String(10), default="")
    seq: Mapped[int] = mapped_column(Integer, default=0)
    comp_seq: Mapped[int] = mapped_column(Integer, default=0)


class ShikayatCase(Base):
    __tablename__ = "shikayat_cases"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("sk"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(20), index=True)           # SH-0001
    customer: Mapped[str] = mapped_column(String(120), default="")
    phone: Mapped[str] = mapped_column(String(15), default="", index=True)   # last 10 digits
    contact_id: Mapped[str] = mapped_column(String(40), default="")       # business WhatsApp contact (if any)
    channel: Mapped[str] = mapped_column(String(12), default="chat")
    ticket_ref: Mapped[str] = mapped_column(String(40), default="")       # hoola_tickets number (Network / WhatsApp)
    product: Mapped[str] = mapped_column(String(160), default="")
    product_key: Mapped[str] = mapped_column(String(80), default="", index=True)
    order_ref: Mapped[str] = mapped_column(String(80), default="")
    amount: Mapped[float] = mapped_column(Float, default=0.0)            # value of what was bought (commission level)
    text: Mapped[str] = mapped_column(Text, default="")
    causes: Mapped[str] = mapped_column(Text, default="[]")
    flags: Mapped[str] = mapped_column(Text, default="[]")               # safety / legal_threat / angry / repeat_customer / product_pattern
    severity: Mapped[str] = mapped_column(String(8), default="normal")
    sector: Mapped[str] = mapped_column(String(20), default="general")
    stage: Mapped[str] = mapped_column(String(22), default="new", index=True)
    owner: Mapped[str] = mapped_column(String(80), default="")            # who handles it (her or a team member)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    ack_by: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ack_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    told_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)   # closing message went to the customer
    resolution: Mapped[str] = mapped_column(Text, default="")
    fix_proof: Mapped[str] = mapped_column(Text, default="")             # her words on how the fix was proved
    confirmed: Mapped[bool | None] = mapped_column(Boolean, nullable=True)   # the customer said it is fixed
    satisfaction: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 1-5
    feedback: Mapped[str] = mapped_column(Text, default="")
    reopen_count: Mapped[int] = mapped_column(Integer, default=0)
    parent: Mapped[str] = mapped_column(String(40), default="")           # an old case this one came back from
    escalated: Mapped[str] = mapped_column(Text, default="")              # {to, ref, on} when the customer went outside
    external_ref: Mapped[str] = mapped_column(String(80), default="")     # her principal's docket / NCH docket
    reminded: Mapped[str] = mapped_column(Text, default="[]")
    log: Mapped[str] = mapped_column(Text, default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class ShikayatProof(Base):
    __tablename__ = "shikayat_proofs"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("sp"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    case_id: Mapped[str] = mapped_column(String(40), index=True)
    kind: Mapped[str] = mapped_column(String(12), default="photo")        # photo | screenshot | video | doc | audio
    stage: Mapped[str] = mapped_column(String(10), default="complaint")   # complaint | fix | other
    name: Mapped[str] = mapped_column(String(180), default="")
    path: Mapped[str] = mapped_column(Text, default="")
    mime: Mapped[str] = mapped_column(String(80), default="")
    size: Mapped[int] = mapped_column(Integer, default=0)
    sha256: Mapped[str] = mapped_column(String(64), default="")
    cleaned: Mapped[bool] = mapped_column(Boolean, default=False)         # metadata (EXIF / GPS / author) removed
    note: Mapped[str] = mapped_column(String(300), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class ShikayatComp(Base):
    __tablename__ = "shikayat_comps"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("sc"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    case_id: Mapped[str] = mapped_column(String(40), index=True)
    number: Mapped[str] = mapped_column(String(20), default="")           # C-0001
    kind: Mapped[str] = mapped_column(String(14), default="refund")
    amount: Mapped[float] = mapped_column(Float, default=0.0)            # rupees (value for a replacement)
    item: Mapped[str] = mapped_column(String(200), default="")
    reason: Mapped[str] = mapped_column(Text, default="")
    checks: Mapped[str] = mapped_column(Text, default="[]")
    status: Mapped[str] = mapped_column(String(10), default="pending")    # pending | approved | rejected | given | cancelled
    hash: Mapped[str] = mapped_column(String(64), default="")
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    given_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    given_how: Mapped[str] = mapped_column(String(200), default="")
    note: Mapped[str] = mapped_column(Text, default="")
    conv: Mapped[str] = mapped_column(String(40), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
