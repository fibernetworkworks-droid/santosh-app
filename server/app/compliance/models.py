"""Tables of the Compliance Sahayak (compliance officer), all prefixed compliance_."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now


class CompSettings(Base):
    __tablename__ = "compliance_settings"
    tenant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    firm: Mapped[str] = mapped_column(String(160), default="")
    signatory: Mapped[str] = mapped_column(String(120), default="")        # who signs the monthly certificate (her name)
    designation: Mapped[str] = mapped_column(String(80), default="")
    facts: Mapped[str] = mapped_column(Text, default="{}")                 # rules.clean_facts
    owners: Mapped[str] = mapped_column(Text, default="{}")                # {area: person name}
    team: Mapped[str] = mapped_column(Text, default="[]")                  # [{name, phone}]
    windows: Mapped[str] = mapped_column(String(40), default="7,3,1,0")    # reminder days before due
    morning_time: Mapped[str] = mapped_column(String(5), default="09:00")
    last_morning: Mapped[str] = mapped_column(String(10), default="")
    last_build: Mapped[str] = mapped_column(String(10), default="")
    seq: Mapped[str] = mapped_column(Text, default="{}")


class CompItem(Base):
    """One obligation for one period (GSTR-3B Oct 2026, PF Oct 2026, FSSAI renew for exp 2027-03-31 ...)."""
    __tablename__ = "compliance_items"
    __table_args__ = (UniqueConstraint("tenant_id", "key", "period", name="uq_compliance_item"),)
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("ci"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(16), default="")
    key: Mapped[str] = mapped_column(String(40), default="")               # catalogue key or custom:<n>
    area: Mapped[str] = mapped_column(String(16), default="custom")
    period: Mapped[str] = mapped_column(String(40), default="")
    label: Mapped[str] = mapped_column(String(200), default="")
    due: Mapped[str] = mapped_column(String(10), default="")               # "" = she must give the date
    due_override: Mapped[str] = mapped_column(String(10), default="")      # her own date (wins)
    owner: Mapped[str] = mapped_column(String(80), default="")
    status: Mapped[str] = mapped_column(String(16), default="open")       # open | file_ok | done | na
    done_how: Mapped[str] = mapped_column(String(10), default="")          # evidence | word
    done_on: Mapped[str] = mapped_column(String(10), default="")
    done_by: Mapped[str] = mapped_column(String(80), default="")
    ack: Mapped[str] = mapped_column(String(80), default="")               # ARN / SRN / challan no. (her words)
    evidence: Mapped[str] = mapped_column(Text, default="[]")             # [{file_id, name, note, at, by}]
    note: Mapped[str] = mapped_column(Text, default="")
    log: Mapped[str] = mapped_column(Text, default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)


class CompFiling(Base):
    """'Portal par file karo' card for one item: only her tap approves; she still logs in / pays / submits herself."""
    __tablename__ = "compliance_filings"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("cf"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    item_id: Mapped[str] = mapped_column(String(40), index=True)
    number: Mapped[str] = mapped_column(String(16), default="")
    show: Mapped[str] = mapped_column(Text, default="{}")
    hash: Mapped[str] = mapped_column(String(64), default="")
    status: Mapped[str] = mapped_column(String(12), default="waiting")    # waiting | approved | rejected | stale
    reason: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class CompCert(Base):
    """Monthly compliance certificate draft -> her sign-off tap."""
    __tablename__ = "compliance_certs"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("cc"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    month: Mapped[str] = mapped_column(String(7), default="")             # YYYY-MM
    number: Mapped[str] = mapped_column(String(16), default="")
    content: Mapped[str] = mapped_column(Text, default="{}")
    hash: Mapped[str] = mapped_column(String(64), default="")
    status: Mapped[str] = mapped_column(String(12), default="waiting")    # waiting | signed | rejected | stale
    reason: Mapped[str] = mapped_column(Text, default="")
    file_id: Mapped[str] = mapped_column(String(60), default="")
    signed_on: Mapped[str] = mapped_column(String(10), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class CompOnce(Base):
    __tablename__ = "compliance_once"
    key: Mapped[str] = mapped_column(String(200), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    n: Mapped[int] = mapped_column(Integer, default=1)
    amount: Mapped[float] = mapped_column(Float, default=0.0)
