"""Edit Desk tables (prefix editdesk_). New columns must be nullable / defaulted (old databases get them by db._add_missing_columns)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now


class EditdeskSettings(Base):
    __tablename__ = "editdesk_settings"
    tenant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    studio: Mapped[str] = mapped_column(String(160), default="")
    gstin: Mapped[str] = mapped_column(String(20), default="")
    gst_on: Mapped[bool] = mapped_column(Boolean, default=False)
    gst_pct: Mapped[float] = mapped_column(Float, default=18.0)
    sac: Mapped[str] = mapped_column(String(12), default="998386")
    upi_id: Mapped[str] = mapped_column(String(80), default="")
    phone: Mapped[str] = mapped_column(String(20), default="")
    email: Mapped[str] = mapped_column(String(120), default="")
    address: Mapped[str] = mapped_column(Text, default="")
    rounds: Mapped[int] = mapped_column(Integer, default=2)               # revision rounds in a quote unless she says otherwise
    extra_round_fee: Mapped[float | None] = mapped_column(Float, nullable=True)   # HER number; None = ask
    advance_pct: Mapped[float] = mapped_column(Float, default=50.0)
    rate_card: Mapped[str] = mapped_column(Text, default="[]")          # [{code, what, rate, unit}] HER prices
    hold_final_unpaid: Mapped[bool] = mapped_column(Boolean, default=False)   # final files only after the balance
    review_days: Mapped[int] = mapped_column(Integer, default=3)        # client silent this long -> reminder draft
    unpaid_days: Mapped[int] = mapped_column(Integer, default=7)
    terms: Mapped[str] = mapped_column(Text, default="")
    rules: Mapped[str] = mapped_column(Text, default="")
    morning_time: Mapped[str] = mapped_column(String(5), default="09:30")
    last_morning: Mapped[str] = mapped_column(String(10), default="")
    seq: Mapped[str] = mapped_column(Text, default="{}")                # counters per kind / FY


class EditdeskClient(Base):
    __tablename__ = "editdesk_clients"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("edc"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(12), default="")
    name: Mapped[str] = mapped_column(String(160), default="")
    company: Mapped[str] = mapped_column(String(160), default="")
    phone: Mapped[str] = mapped_column(String(20), default="")
    email: Mapped[str] = mapped_column(String(160), default="")
    gstin: Mapped[str] = mapped_column(String(20), default="")
    state: Mapped[str] = mapped_column(String(4), default="")           # GST state code
    country: Mapped[str] = mapped_column(String(40), default="India")
    business: Mapped[bool] = mapped_column(Boolean, default=True)       # brand / business client = commercial use
    notes: Mapped[str] = mapped_column(Text, default="")
    no_messages: Mapped[bool] = mapped_column(Boolean, default=False)
    forgotten: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class EditdeskProject(Base):
    __tablename__ = "editdesk_projects"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("edp"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(12), default="")
    client_id: Mapped[str] = mapped_column(String(40), default="")
    title: Mapped[str] = mapped_column(String(200), default="")
    kind: Mapped[str] = mapped_column(String(20), default="other")
    brief: Mapped[str] = mapped_column(Text, default="")
    facts: Mapped[str] = mapped_column(Text, default="{}")              # parsed brief (only what is written)
    deliverables: Mapped[str] = mapped_column(Text, default="[]")       # [{id, platform, length_s, label, job_id, status}]
    footage: Mapped[str] = mapped_column(Text, default="[]")            # [{item, have, file_ids, note}]
    files: Mapped[str] = mapped_column(Text, default="[]")              # source file_ids for the engine
    music_file_id: Mapped[str] = mapped_column(String(60), default="")
    logo_file_id: Mapped[str] = mapped_column(String(60), default="")
    captions: Mapped[bool] = mapped_column(Boolean, default=True)
    due: Mapped[str] = mapped_column(String(10), default="")
    status: Mapped[str] = mapped_column(String(20), default="brief")
    rounds_quoted: Mapped[int] = mapped_column(Integer, default=2)
    rounds_used: Mapped[int] = mapped_column(Integer, default=0)
    free_rounds: Mapped[int] = mapped_column(Integer, default=0)        # extra rounds she gave free
    extras: Mapped[str] = mapped_column(Text, default="[]")            # approved extra charges [{what, amount, round}]
    approved: Mapped[str] = mapped_column(Text, default="{}")           # client OK {deliverable_id: version n}
    delivered: Mapped[str] = mapped_column(Text, default="{}")
    review_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    log: Mapped[str] = mapped_column(Text, default="[]")
    conv: Mapped[str] = mapped_column(String(64), default="")
    created_by: Mapped[str] = mapped_column(String(64), default="owner")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class EditdeskComment(Base):
    __tablename__ = "editdesk_comments"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("edn"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    project_id: Mapped[str] = mapped_column(String(40), index=True)
    deliverable: Mapped[str] = mapped_column(String(20), default="")    # deliverable id ("" = all)
    version: Mapped[int] = mapped_column(Integer, default=0)
    at_s: Mapped[float | None] = mapped_column(Float, nullable=True)
    text: Mapped[str] = mapped_column(Text, default="")                 # the client's words (data)
    scope: Mapped[str] = mapped_column(String(10), default="fix")       # fix | extra (looks outside the quote)
    by: Mapped[str] = mapped_column(String(20), default="client")
    status: Mapped[str] = mapped_column(String(12), default="open")     # open | sent | done | wontfix
    round: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class EditdeskLicence(Base):
    __tablename__ = "editdesk_licences"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("edl"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(12), default="")
    project_id: Mapped[str] = mapped_column(String(40), default="")
    kind: Mapped[str] = mapped_column(String(20), default="music")
    title: Mapped[str] = mapped_column(String(200), default="")
    source: Mapped[str] = mapped_column(String(200), default="")
    licence_type: Mapped[str] = mapped_column(String(20), default="unknown")
    licence_ref: Mapped[str] = mapped_column(String(200), default="")
    proof_file_id: Mapped[str] = mapped_column(String(60), default="")
    file_id: Mapped[str] = mapped_column(String(60), default="")        # the music / stock file this covers
    commercial: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    expires: Mapped[str] = mapped_column(String(10), default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class EditdeskQuote(Base):
    __tablename__ = "editdesk_quotes"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("edq"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    project_id: Mapped[str] = mapped_column(String(40), index=True)
    number: Mapped[str] = mapped_column(String(24), default="")
    lines: Mapped[str] = mapped_column(Text, default="[]")
    rounds: Mapped[int] = mapped_column(Integer, default=2)
    extra_round_fee: Mapped[float | None] = mapped_column(Float, nullable=True)
    advance_pct: Mapped[float] = mapped_column(Float, default=50.0)
    valid_until: Mapped[str] = mapped_column(String(10), default="")
    terms: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(12), default="draft")    # draft | sent | accepted | rejected | old
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class EditdeskInvoice(Base):
    __tablename__ = "editdesk_invoices"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("edi"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    project_id: Mapped[str] = mapped_column(String(40), index=True)
    number: Mapped[str] = mapped_column(String(24), default="")
    kind: Mapped[str] = mapped_column(String(10), default="final")      # advance | final | extra
    lines: Mapped[str] = mapped_column(Text, default="[]")
    subtotal: Mapped[float] = mapped_column(Float, default=0.0)
    gst: Mapped[str] = mapped_column(Text, default="{}")
    total: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(12), default="draft")    # draft | sent | part | paid | void
    payments: Mapped[str] = mapped_column(Text, default="[]")           # [{amount, tds, mode, ref, at, receipt}]
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class EditdeskCard(Base):
    __tablename__ = "editdesk_cards"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("edk"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    project_id: Mapped[str] = mapped_column(String(40), default="")
    kind: Mapped[str] = mapped_column(String(16), default="")           # quote | invoice | delivery | extra_round | message | refund
    show: Mapped[str] = mapped_column(Text, default="{}")
    hash: Mapped[str] = mapped_column(String(64), default="")
    status: Mapped[str] = mapped_column(String(12), default="waiting")  # waiting | approved | rejected | stale
    asked_by: Mapped[str] = mapped_column(String(80), default="")
    reason: Mapped[str] = mapped_column(Text, default="")
    result: Mapped[str] = mapped_column(Text, default="{}")
    conv: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class EditdeskAlert(Base):
    """Once-each reminders (key = what + id + date)."""
    __tablename__ = "editdesk_alerts"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("eda"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    key: Mapped[str] = mapped_column(String(160), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
