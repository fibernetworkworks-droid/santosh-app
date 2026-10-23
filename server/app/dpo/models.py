"""Tables of the DPO Sahayak (all prefixed dpo_). JSON kept as Text."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now


class DpoSettings(Base):
    __tablename__ = "dpo_settings"
    tenant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    org: Mapped[str] = mapped_column(String(160), default="")              # business name as the Data Fiduciary
    contact_name: Mapped[str] = mapped_column(String(120), default="")     # DPO / person who answers (s.8(9), Rule 9)
    contact_email: Mapped[str] = mapped_column(String(120), default="")
    contact_phone: Mapped[str] = mapped_column(String(15), default="")
    link: Mapped[str] = mapped_column(String(300), default="")             # page / form where people withdraw / ask (Rule 3(c), 14(1))
    identifiers: Mapped[str] = mapped_column(Text, default="")             # how she identifies a person (Rule 14(1)): "registered mobile"
    reply_days: Mapped[int] = mapped_column(Integer, default=30)           # her own target (law: max 90)
    languages: Mapped[str] = mapped_column(String(40), default="hi,en")
    sdf: Mapped[bool] = mapped_column(Boolean, default=False)              # notified Significant Data Fiduciary
    third_schedule: Mapped[str] = mapped_column(String(20), default="")    # ecommerce | gaming | social | ""
    morning_time: Mapped[str] = mapped_column(String(5), default="09:30")
    last_morning: Mapped[str] = mapped_column(String(10), default="")
    rules: Mapped[str] = mapped_column(Text, default="")
    seq: Mapped[str] = mapped_column(Text, default="{}")


class DpoActivity(Base):
    """Record of processing (one purpose)."""
    __tablename__ = "dpo_activities"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("dpa"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(12), default="")            # PA-01
    source: Mapped[str] = mapped_column(String(30), default="own")         # catalog key or "own"
    name: Mapped[str] = mapped_column(String(160), default="")
    people: Mapped[str] = mapped_column(String(160), default="")
    items: Mapped[str] = mapped_column(Text, default="[]")
    purpose: Mapped[str] = mapped_column(Text, default="")
    basis: Mapped[str] = mapped_column(String(16), default="consent")
    retention: Mapped[str] = mapped_column(String(200), default="")
    retention_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    processors: Mapped[str] = mapped_column(Text, default="[]")
    children: Mapped[bool] = mapped_column(Boolean, default=False)
    abroad: Mapped[bool] = mapped_column(Boolean, default=False)
    law_hold: Mapped[bool] = mapped_column(Boolean, default=False)         # another law makes her keep records
    records: Mapped[int] = mapped_column(Integer, default=0)                # rows seen in the module (count only)
    status: Mapped[str] = mapped_column(String(10), default="active")      # active | stopped
    confirmed: Mapped[bool] = mapped_column(Boolean, default=False)        # she checked the pre-filled entry
    dpia: Mapped[str] = mapped_column(Text, default="{}")                  # {answers, score, level, notes, on}
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class DpoNotice(Base):
    __tablename__ = "dpo_notices"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("dpn"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    lang: Mapped[str] = mapped_column(String(4), default="hi")
    activity_ids: Mapped[str] = mapped_column(Text, default="[]")
    text: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(10), default="draft")       # draft | waiting | published | old | rejected
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    files: Mapped[str] = mapped_column(Text, default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class DpoConsent(Base):
    __tablename__ = "dpo_consents"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("dpc"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    name: Mapped[str] = mapped_column(String(120), default="")
    phone: Mapped[str] = mapped_column(String(10), default="", index=True)
    activity_ids: Mapped[str] = mapped_column(Text, default="[]")
    notice_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    how: Mapped[str] = mapped_column(String(40), default="")               # form | whatsapp | paper | app | website | call
    proof: Mapped[str] = mapped_column(String(200), default="")            # file id / reference (never the content of an ID)
    child: Mapped[bool] = mapped_column(Boolean, default=False)
    parent_name: Mapped[str] = mapped_column(String(120), default="")
    parent_check: Mapped[str] = mapped_column(String(200), default="")     # how verified (Rule 10) + reference only
    given_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    withdrawn_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    withdraw_how: Mapped[str] = mapped_column(String(60), default="")
    status: Mapped[str] = mapped_column(String(10), default="active")      # active | withdrawn | forgotten


class DpoRequest(Base):
    __tablename__ = "dpo_requests"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("dpr"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(12), default="")            # R-0001
    kind: Mapped[str] = mapped_column(String(12), default="grievance")
    name: Mapped[str] = mapped_column(String(120), default="")
    phone: Mapped[str] = mapped_column(String(10), default="")
    email: Mapped[str] = mapped_column(String(120), default="")
    via: Mapped[str] = mapped_column(String(20), default="")
    text: Mapped[str] = mapped_column(Text, default="")                   # their words (scrubbed) = data
    received_on: Mapped[str] = mapped_column(String(10), default="")
    due_on: Mapped[str] = mapped_column(String(10), default="")
    id_check: Mapped[str] = mapped_column(String(10), default="pending")   # pending | done | failed
    id_how: Mapped[str] = mapped_column(String(200), default="")           # method + reference only
    found: Mapped[str] = mapped_column(Text, default="[]")                 # [{module, label, ref, can_erase}]
    reply: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(12), default="new")        # new | working | waiting | replied | closed | rejected
    result: Mapped[str] = mapped_column(Text, default="{}")
    log: Mapped[str] = mapped_column(Text, default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class DpoBreach(Base):
    __tablename__ = "dpo_breaches"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("dpb"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(12), default="")            # B-01
    title: Mapped[str] = mapped_column(String(200), default="")
    aware_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    report_due: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    facts: Mapped[str] = mapped_column(Text, default="{}")                 # nature / extent / when / ... (her words)
    affected: Mapped[str] = mapped_column(Text, default="[]")              # [{name, phone, email}] to tell
    activity_ids: Mapped[str] = mapped_column(Text, default="[]")
    cert_in: Mapped[str] = mapped_column(Text, default="{}")               # IT Helpdesk incident link {incident, due, applies}
    initial_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)    # sent to Board (her word)
    report_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    people_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    refs: Mapped[str] = mapped_column(Text, default="{}")                  # her references per send
    status: Mapped[str] = mapped_column(String(10), default="open")        # open | closed
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class DpoVendor(Base):
    """A Data Processor she uses."""
    __tablename__ = "dpo_vendors"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("dpv"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    name: Mapped[str] = mapped_column(String(160), default="")
    service: Mapped[str] = mapped_column(String(200), default="")
    items: Mapped[str] = mapped_column(Text, default="[]")
    country: Mapped[str] = mapped_column(String(60), default="")
    dpa_signed: Mapped[bool] = mapped_column(Boolean, default=False)
    dpa_on: Mapped[str] = mapped_column(String(10), default="")
    review_on: Mapped[str] = mapped_column(String(10), default="")
    clauses: Mapped[str] = mapped_column(Text, default="{}")               # {clause key: true/false}
    file_id: Mapped[str] = mapped_column(String(60), default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class DpoCard(Base):
    """Something only HER app tap decides: notice publish, reply to a person, erasure, breach notices."""
    __tablename__ = "dpo_cards"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("dpk"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    kind: Mapped[str] = mapped_column(String(16), default="")               # notice | reply | erase | breach_initial | breach_report | breach_people
    target: Mapped[str] = mapped_column(String(40), default="")
    title: Mapped[str] = mapped_column(String(200), default="")
    hash: Mapped[str] = mapped_column(String(64), default="")
    data: Mapped[str] = mapped_column(Text, default="{}")
    status: Mapped[str] = mapped_column(String(10), default="waiting")     # waiting | approved | rejected | stale
    reason: Mapped[str] = mapped_column(Text, default="")
    result: Mapped[str] = mapped_column(Text, default="{}")
    asked_by: Mapped[str] = mapped_column(String(80), default="")
    conv: Mapped[str] = mapped_column(String(40), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class DpoAlert(Base):
    __tablename__ = "dpo_alerts"
    key: Mapped[str] = mapped_column(String(200), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
