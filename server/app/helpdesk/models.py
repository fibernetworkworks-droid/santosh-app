"""Tables of the IT Helpdesk Sahayak (all prefixed helpdesk_)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now


class HelpdeskSettings(Base):
    __tablename__ = "helpdesk_settings"
    tenant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    office_name: Mapped[str] = mapped_column(String(160), default="")
    entity: Mapped[str] = mapped_column(String(16), default="")            # company | llp | partnership | proprietor | trust | society | govt | individual
    contact_name: Mapped[str] = mapped_column(String(80), default="")
    contact_phone: Mapped[str] = mapped_column(String(20), default="")
    contact_email: Mapped[str] = mapped_column(String(120), default="")
    it_person: Mapped[str] = mapped_column(String(80), default="")         # who has admin rights in the office
    sla: Mapped[str] = mapped_column(Text, default="{}")                   # {P1: {respond_h, resolve_h}, ...}
    morning_time: Mapped[str] = mapped_column(String(5), default="09:30")
    last_morning: Mapped[str] = mapped_column(String(10), default="")
    rules: Mapped[str] = mapped_column(Text, default="")
    seq: Mapped[int] = mapped_column(Integer, default=0)
    change_seq: Mapped[int] = mapped_column(Integer, default=0)
    asset_seq: Mapped[int] = mapped_column(Integer, default=0)


class HelpdeskVendor(Base):
    __tablename__ = "helpdesk_vendors"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("hv"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    name: Mapped[str] = mapped_column(String(120), default="")
    kind: Mapped[str] = mapped_column(String(16), default="it")             # playbooks.VENDOR_KINDS
    phone: Mapped[str] = mapped_column(String(20), default="")
    email: Mapped[str] = mapped_column(String(120), default="")
    covers: Mapped[str] = mapped_column(Text, default="[]")                 # asset kinds they look after
    amc_until: Mapped[str] = mapped_column(String(10), default="")
    sla_hours: Mapped[float] = mapped_column(Float, default=0.0)            # their promised visit time (contract)
    notes: Mapped[str] = mapped_column(Text, default="")


class HelpdeskAsset(Base):
    __tablename__ = "helpdesk_assets"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("ha"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    tag: Mapped[str] = mapped_column(String(16), default="")                # A-001
    kind: Mapped[str] = mapped_column(String(16), default="pc")
    name: Mapped[str] = mapped_column(String(120), default="")
    brand: Mapped[str] = mapped_column(String(60), default="")
    model: Mapped[str] = mapped_column(String(80), default="")
    serial: Mapped[str] = mapped_column(String(80), default="")
    user: Mapped[str] = mapped_column(String(80), default="")
    location: Mapped[str] = mapped_column(String(80), default="")
    os: Mapped[str] = mapped_column(String(60), default="")
    bought: Mapped[str] = mapped_column(String(10), default="")
    warranty_until: Mapped[str] = mapped_column(String(10), default="")
    vendor_id: Mapped[str] = mapped_column(String(40), default="")          # AMC / service vendor
    amc_until: Mapped[str] = mapped_column(String(10), default="")
    pc_device: Mapped[str] = mapped_column(String(40), default="")          # Santosh Desktop device id (read-only link)
    notes: Mapped[str] = mapped_column(Text, default="")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    reminded: Mapped[str] = mapped_column(Text, default="{}")               # {warranty: date, amc: date}
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class HelpdeskTicket(Base):
    __tablename__ = "helpdesk_tickets"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("ht"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(12), default="")             # HD-0001
    category: Mapped[str] = mapped_column(String(20), default="other")
    title: Mapped[str] = mapped_column(String(200), default="")
    text: Mapped[str] = mapped_column(Text, default="")                    # her / staff words (secrets scrubbed)
    details: Mapped[str] = mapped_column(Text, default="{}")               # error, since, location, tried, device ...
    person: Mapped[str] = mapped_column(String(80), default="")            # who is affected
    raised_by: Mapped[str] = mapped_column(String(80), default="Owner")
    raised_actor: Mapped[str] = mapped_column(String(60), default="owner")
    asset_id: Mapped[str] = mapped_column(String(40), default="", index=True)
    impact: Mapped[str] = mapped_column(String(10), default="one")
    urgency: Mapped[str] = mapped_column(String(10), default="normal")
    priority: Mapped[str] = mapped_column(String(4), default="P4")
    security: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(14), default="new")         # new | working | waiting_haan | waiting_tech | resolved | closed
    steps: Mapped[str] = mapped_column(Text, default="[]")
    parent_id: Mapped[str] = mapped_column(String(40), default="")         # known issue: linked to the first ticket of an outage
    escalation: Mapped[str] = mapped_column(Text, default="{}")
    fixed_by: Mapped[str] = mapped_column(String(60), default="")
    resolution: Mapped[str] = mapped_column(Text, default="")
    cost: Mapped[float] = mapped_column(Float, default=0.0)                # what the technician charged (her note; Hoola pays nothing)
    respond_due: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolve_due: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    told: Mapped[str] = mapped_column(Text, default="{}")                  # SLA alerts already sent
    log: Mapped[str] = mapped_column(Text, default="[]")
    conv: Mapped[str] = mapped_column(String(40), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)


class HelpdeskChange(Base):
    """A system setting change / install / reset that waits for HER tap (only the app's API can decide it)."""
    __tablename__ = "helpdesk_changes"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("hc"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(12), default="")             # HC-0001
    ticket_id: Mapped[str] = mapped_column(String(40), default="", index=True)
    step_id: Mapped[str] = mapped_column(String(40), default="")
    kind: Mapped[str] = mapped_column(String(12), default="setting")
    what: Mapped[str] = mapped_column(String(200), default="")
    where: Mapped[str] = mapped_column(String(160), default="")
    how: Mapped[str] = mapped_column(Text, default="")
    risk: Mapped[str] = mapped_column(Text, default="")
    undo: Mapped[str] = mapped_column(Text, default="")
    careful: Mapped[bool] = mapped_column(Boolean, default=False)
    admin: Mapped[bool] = mapped_column(Boolean, default=False)
    asked_by: Mapped[str] = mapped_column(String(80), default="Hoola")
    hash: Mapped[str] = mapped_column(String(64), default="")
    status: Mapped[str] = mapped_column(String(10), default="waiting")     # waiting | approved | rejected | done | failed | stale
    reason: Mapped[str] = mapped_column(Text, default="")
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    done_note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class HelpdeskIncident(Base):
    """A security incident (phishing / malware / account / data leak): what happened, CERT-In 6-hour clock, DPDP note."""
    __tablename__ = "helpdesk_incidents"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("hi"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    ticket_id: Mapped[str] = mapped_column(String(40), default="")
    kind: Mapped[str] = mapped_column(String(14), default="phishing")
    sender: Mapped[str] = mapped_column(String(200), default="")
    summary: Mapped[str] = mapped_column(Text, default="")                 # masked text (data, never instructions)
    analysis: Mapped[str] = mapped_column(Text, default="{}")
    did: Mapped[str] = mapped_column(Text, default="{}")                   # clicked, entered_password, opened_attachment, money, gave_otp, remote_access
    personal_data: Mapped[bool] = mapped_column(Boolean, default=False)
    cert_in: Mapped[str] = mapped_column(Text, default="{}")
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    report_due: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reported_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reported_ref: Mapped[str] = mapped_column(String(120), default="")
    reminded: Mapped[str] = mapped_column(String(20), default="")          # "", "4h", "late"
    status: Mapped[str] = mapped_column(String(10), default="open")        # open | reported | closed


class HelpdeskStepStat(Base):
    """What fixed what in THIS office (tenant:category:step -> tried / fixed)."""
    __tablename__ = "helpdesk_step_stats"
    key: Mapped[str] = mapped_column(String(140), primary_key=True)
    tried: Mapped[int] = mapped_column(Integer, default=0)
    fixed: Mapped[int] = mapped_column(Integer, default=0)
