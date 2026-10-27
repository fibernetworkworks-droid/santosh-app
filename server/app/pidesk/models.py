"""Tables of the PI Desk Sahayak, all prefixed pidesk_."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now


class PiSettings(Base):
    __tablename__ = "pidesk_settings"
    tenant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(120), default="")
    firm: Mapped[str] = mapped_column(String(160), default="")
    address: Mapped[str] = mapped_column(Text, default="")
    phone: Mapped[str] = mapped_column(String(20), default="")
    email: Mapped[str] = mapped_column(String(120), default="")
    retention_days: Mapped[int] = mapped_column(Integer, default=365)
    refused: Mapped[int] = mapped_column(Integer, default=0)            # how many requests the desk refused (no content kept)
    seq: Mapped[str] = mapped_column(Text, default="{}")


class PiCase(Base):
    __tablename__ = "pidesk_cases"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("pc"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(16), default="")
    kind: Mapped[str] = mapped_column(String(20), default="due_diligence")   # due_diligence | doc_check | fraud_file | employee_verify
    title: Mapped[str] = mapped_column(String(200), default="")
    purpose: Mapped[str] = mapped_column(Text, default="")
    subject: Mapped[str] = mapped_column(Text, default="{}")             # {name, kind, identifiers [{kind, value}], website}
    suspect: Mapped[str] = mapped_column(Text, default="")              # fraud: identifiers the other side USED (as she gives; never looked up)
    consent: Mapped[str] = mapped_column(Text, default="{}")             # employee_verify: {candidate, role, checks, signed_on, evidence, days}
    money: Mapped[str] = mapped_column(Text, default="{}")               # fraud: {lost, refs, mode, reported {cyber|police|bank: ref}}
    status: Mapped[str] = mapped_column(String(16), default="open")      # open | closed | forgotten
    files: Mapped[str] = mapped_column(Text, default="{}")               # {report|pack|complaint: {file_id, sha, name, at}}
    report_hash: Mapped[str] = mapped_column(String(64), default="")
    report_file_id: Mapped[str] = mapped_column(String(40), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PiFinding(Base):
    __tablename__ = "pidesk_findings"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("pf"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    case_id: Mapped[str] = mapped_column(String(40), index=True)
    section: Mapped[str] = mapped_column(String(16), default="note")     # identity | registry | court | news | document | note
    fact: Mapped[str] = mapped_column(Text, default="")
    source: Mapped[str] = mapped_column(String(200), default="")
    source_url: Mapped[str] = mapped_column(Text, default="")
    official: Mapped[bool] = mapped_column(Boolean, default=False)
    level: Mapped[str] = mapped_column(String(8), default="info")        # ok | info | flag
    text_sha: Mapped[str] = mapped_column(String(64), default="")         # sha256 of the page text read (custody)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class PiEvidence(Base):
    __tablename__ = "pidesk_evidence"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("pe"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    case_id: Mapped[str] = mapped_column(String(40), index=True)
    n: Mapped[str] = mapped_column(String(8), default="")                # E-01
    name: Mapped[str] = mapped_column(String(200), default="")
    kind: Mapped[str] = mapped_column(String(20), default="other")       # chat_export | receipt | screenshot | bank_sms | email | document | consent | other
    path: Mapped[str] = mapped_column(Text, default="")
    sha256: Mapped[str] = mapped_column(String(64), default="")
    size: Mapped[int] = mapped_column(Integer, default=0)
    mime: Mapped[str] = mapped_column(String(80), default="")
    note: Mapped[str] = mapped_column(Text, default="")
    happened_at: Mapped[str] = mapped_column(String(20), default="")
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    meta: Mapped[str] = mapped_column(Text, default="{}")                # signals, codes, chat counts


class PiEvent(Base):
    __tablename__ = "pidesk_events"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("pv"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    case_id: Mapped[str] = mapped_column(String(40), index=True)
    at: Mapped[str] = mapped_column(String(20), default="")              # ISO minutes
    what: Mapped[str] = mapped_column(Text, default="")
    who: Mapped[str] = mapped_column(String(80), default="")
    amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    ref: Mapped[str] = mapped_column(String(40), default="")
    source: Mapped[str] = mapped_column(String(40), default="her")       # her | E-01 ...
    important: Mapped[bool] = mapped_column(Boolean, default=False)


class PiCustody(Base):
    __tablename__ = "pidesk_custody"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("pk"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    case_id: Mapped[str] = mapped_column(String(40), index=True)
    seq: Mapped[int] = mapped_column(Integer, default=0)
    at: Mapped[str] = mapped_column(String(32), default="")
    action: Mapped[str] = mapped_column(String(32), default="")
    detail: Mapped[str] = mapped_column(Text, default="")
    by: Mapped[str] = mapped_column(String(60), default="")
    prev: Mapped[str] = mapped_column(String(64), default="")
    hash: Mapped[str] = mapped_column(String(64), default="")


class PiShare(Base):
    __tablename__ = "pidesk_shares"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("ps"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    case_id: Mapped[str] = mapped_column(String(40), index=True)
    what: Mapped[str] = mapped_column(String(16), default="report")      # report | pack | complaint
    to_name: Mapped[str] = mapped_column(String(160), default="")
    to_contact: Mapped[str] = mapped_column(String(160), default="")
    note: Mapped[str] = mapped_column(Text, default="")
    content_hash: Mapped[str] = mapped_column(String(64), default="")
    hash: Mapped[str] = mapped_column(String(64), default="")
    status: Mapped[str] = mapped_column(String(12), default="waiting")   # waiting | shared | rejected | stale
    file_id: Mapped[str] = mapped_column(String(40), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PiOnce(Base):
    __tablename__ = "pidesk_once"
    key: Mapped[str] = mapped_column(String(200), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
