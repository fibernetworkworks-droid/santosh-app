"""Tables of the IT Admin Sahayak (all prefixed itadmin_). Devices are NOT here: they are the IT Helpdesk's helpdesk_assets."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now


class ItadminSettings(Base):
    __tablename__ = "itadmin_settings"
    tenant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    org_name: Mapped[str] = mapped_column(String(160), default="")
    domain: Mapped[str] = mapped_column(String(120), default="")            # her email domain (ingletraders.in)
    admin_name: Mapped[str] = mapped_column(String(80), default="")         # who holds the admin console rights
    standard_systems: Mapped[str] = mapped_column(Text, default="[]")       # what every new person gets ("Email", "Tally", "Wi-Fi")
    windows: Mapped[str] = mapped_column(String(60), default="[60, 30, 15, 7, 1, 0]")
    review_months: Mapped[int] = mapped_column(Integer, default=3)          # access review every N months (ISO 27001 5.18)
    morning_time: Mapped[str] = mapped_column(String(5), default="09:45")
    last_morning: Mapped[str] = mapped_column(String(10), default="")
    last_review: Mapped[str] = mapped_column(String(10), default="")
    practices: Mapped[str] = mapped_column(Text, default="{}")              # {mfa_admins: true, logs_180: ..., ntp: ..., poc: ...}
    rules: Mapped[str] = mapped_column(Text, default="")
    lic_seq: Mapped[int] = mapped_column(Integer, default=0)
    person_seq: Mapped[int] = mapped_column(Integer, default=0)
    change_seq: Mapped[int] = mapped_column(Integer, default=0)
    guide_seq: Mapped[int] = mapped_column(Integer, default=0)
    review_seq: Mapped[int] = mapped_column(Integer, default=0)


class ItadminLicence(Base):
    """A software licence / subscription / renewal: M365 / Workspace seats, Tally TSS, antivirus, domain, SSL, cloud plan..."""
    __tablename__ = "itadmin_licences"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("il"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(10), default="")             # L-001
    kind: Mapped[str] = mapped_column(String(16), default="software")       # rules.LIC_KINDS
    name: Mapped[str] = mapped_column(String(160), default="")
    vendor: Mapped[str] = mapped_column(String(120), default="")
    plan: Mapped[str] = mapped_column(String(120), default="")
    seats_bought: Mapped[int | None] = mapped_column(Integer, nullable=True)
    seats_used: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cost: Mapped[float | None] = mapped_column(Float, nullable=True)        # her number, rupees
    cost_per: Mapped[str] = mapped_column(String(10), default="year")       # month | year | once
    per_seat: Mapped[bool] = mapped_column(Boolean, default=False)
    renews_on: Mapped[str] = mapped_column(String(10), default="")
    auto_renew: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    owner: Mapped[str] = mapped_column(String(80), default="")             # who looks after / pays (a name)
    login_with: Mapped[str] = mapped_column(String(120), default="")        # which account manages it (never the password)
    notes: Mapped[str] = mapped_column(Text, default="")
    source: Mapped[str] = mapped_column(String(12), default="manual")       # manual | google | microsoft
    sku: Mapped[str] = mapped_column(String(80), default="")                # provider sku id (M365 skuId GUID / Google skuId)
    product: Mapped[str] = mapped_column(String(80), default="")            # Google productId
    history: Mapped[str] = mapped_column(Text, default="[]")                # renewals: [{on, cost}]
    reminded: Mapped[str] = mapped_column(Text, default="{}")               # {renews_on: [windows told]}
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class ItadminPerson(Base):
    __tablename__ = "itadmin_people"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("ip"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(10), default="")             # P-001
    name: Mapped[str] = mapped_column(String(120), default="")
    email: Mapped[str] = mapped_column(String(160), default="")
    phone: Mapped[str] = mapped_column(String(20), default="")
    role: Mapped[str] = mapped_column(String(80), default="")
    department: Mapped[str] = mapped_column(String(80), default="")
    manager: Mapped[str] = mapped_column(String(80), default="")
    status: Mapped[str] = mapped_column(String(10), default="active")      # joining | active | moving | leaving | left | forgotten
    join_date: Mapped[str] = mapped_column(String(10), default="")
    leave_date: Mapped[str] = mapped_column(String(10), default="")
    google_id: Mapped[str] = mapped_column(String(80), default="")
    ms_id: Mapped[str] = mapped_column(String(80), default="")
    source: Mapped[str] = mapped_column(String(12), default="manual")
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class ItadminAccess(Base):
    """That an access EXISTS (who has which account / admin right / shared login). Never the password itself."""
    __tablename__ = "itadmin_access"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("ia"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    person_id: Mapped[str] = mapped_column(String(40), default="", index=True)   # "" = account nobody is linked to yet
    system: Mapped[str] = mapped_column(String(120), default="")           # "Google Workspace", "Tally", "GST portal", "Wi-Fi"
    account: Mapped[str] = mapped_column(String(160), default="")          # login name / email (no secret)
    level: Mapped[str] = mapped_column(String(10), default="user")         # user | admin | owner
    shared: Mapped[bool] = mapped_column(Boolean, default=False)            # a shared login: password known to several people
    mfa: Mapped[str] = mapped_column(String(8), default="unknown")         # yes | no | unknown
    source: Mapped[str] = mapped_column(String(12), default="manual")
    external_id: Mapped[str] = mapped_column(String(80), default="")
    last_login: Mapped[str] = mapped_column(String(25), default="")
    status: Mapped[str] = mapped_column(String(10), default="active")      # active | disabled | removed
    licence_id: Mapped[str] = mapped_column(String(40), default="")
    reviewed_at: Mapped[str] = mapped_column(String(10), default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class ItadminChecklist(Base):
    """Joiner / mover / leaver checklist for one person."""
    __tablename__ = "itadmin_checklists"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("ic"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    person_id: Mapped[str] = mapped_column(String(40), default="", index=True)
    kind: Mapped[str] = mapped_column(String(8), default="joiner")         # joiner | mover | leaver
    due: Mapped[str] = mapped_column(String(10), default="")
    items: Mapped[str] = mapped_column(Text, default="[]")
    status: Mapped[str] = mapped_column(String(8), default="open")         # open | done
    told: Mapped[str] = mapped_column(String(20), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class ItadminChange(Base):
    """An access / settings change that waits for HER tap. Only POST /api/itadmin/changes/{id}/decide can approve it."""
    __tablename__ = "itadmin_changes"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("ich"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(10), default="")             # AC-0001
    kind: Mapped[str] = mapped_column(String(16), default="other")         # rules.CHANGE_KINDS
    provider: Mapped[str] = mapped_column(String(12), default="manual")    # google | microsoft | manual
    person_id: Mapped[str] = mapped_column(String(40), default="")
    access_id: Mapped[str] = mapped_column(String(40), default="")
    licence_id: Mapped[str] = mapped_column(String(40), default="")
    target: Mapped[str] = mapped_column(String(160), default="")           # account / user the change is about
    system: Mapped[str] = mapped_column(String(120), default="")
    what: Mapped[str] = mapped_column(Text, default="")
    api: Mapped[str] = mapped_column(Text, default="{}")                   # {method, url, body} exactly as it would be sent
    steps: Mapped[str] = mapped_column(Text, default="[]")                 # console steps when it is not done by the API
    risk: Mapped[str] = mapped_column(Text, default="")
    undo: Mapped[str] = mapped_column(Text, default="")
    asked_by: Mapped[str] = mapped_column(String(80), default="Hoola")
    checklist_id: Mapped[str] = mapped_column(String(40), default="")
    item_id: Mapped[str] = mapped_column(String(40), default="")
    hash: Mapped[str] = mapped_column(String(64), default="")
    status: Mapped[str] = mapped_column(String(10), default="waiting")     # waiting | approved | done | failed | rejected | stale
    result: Mapped[str] = mapped_column(Text, default="")
    reason: Mapped[str] = mapped_column(Text, default="")
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class ItadminGuide(Base):
    __tablename__ = "itadmin_guides"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("ig"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(10), default="")             # G-001
    title: Mapped[str] = mapped_column(String(200), default="")
    tags: Mapped[str] = mapped_column(Text, default="[]")
    audience: Mapped[str] = mapped_column(String(80), default="Sab staff")
    language: Mapped[str] = mapped_column(String(10), default="hinglish")
    steps: Mapped[str] = mapped_column(Text, default="[]")                 # [{n, text, shot}]
    notes: Mapped[str] = mapped_column(Text, default="")
    version: Mapped[int] = mapped_column(Integer, default=1)
    versions: Mapped[str] = mapped_column(Text, default="[]")              # older versions (last 20)
    status: Mapped[str] = mapped_column(String(10), default="draft")       # draft | published | archived
    source: Mapped[str] = mapped_column(Text, default="")                  # her setup words (masked)
    asked: Mapped[int] = mapped_column(Integer, default=0)
    helped: Mapped[int] = mapped_column(Integer, default=0)
    not_helped: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class ItadminShot(Base):
    """A screenshot she added to a guide step (re-encoded, EXIF dropped, kept in data/itadmin/<tenant>/guides)."""
    __tablename__ = "itadmin_shots"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("is"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    guide_id: Mapped[str] = mapped_column(String(40), default="", index=True)
    path: Mapped[str] = mapped_column(Text, default="")
    mime: Mapped[str] = mapped_column(String(30), default="image/png")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class ItadminConn(Base):
    """Her admin console connection (Google Workspace OAuth / Microsoft Entra app). Secrets sealed, never shown."""
    __tablename__ = "itadmin_conns"
    id: Mapped[str] = mapped_column(String(100), primary_key=True)        # "<tenant>:google" | "<tenant>:microsoft"
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    provider: Mapped[str] = mapped_column(String(12), default="google")
    mode: Mapped[str] = mapped_column(String(8), default="read")           # read | manage
    account: Mapped[str] = mapped_column(String(160), default="")          # admin email / Entra directory id (shown)
    client_id: Mapped[str] = mapped_column(String(120), default="")        # Microsoft app (client) id (not secret, shown)
    secret_sealed: Mapped[str] = mapped_column(Text, default="")           # Microsoft client secret (sealed)
    access_sealed: Mapped[str] = mapped_column(Text, default="")
    refresh_sealed: Mapped[str] = mapped_column(Text, default="")
    scopes: Mapped[str] = mapped_column(Text, default="")
    expiry: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(10), default="ok")
    last_error: Mapped[str] = mapped_column(Text, default="")
    last_sync: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sync_note: Mapped[str] = mapped_column(Text, default="{}")


class ItadminQuestion(Base):
    """A staff IT question (masked) and how it was answered: guide | playbook | ticket | access_request | unknown."""
    __tablename__ = "itadmin_questions"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("iq"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    text: Mapped[str] = mapped_column(Text, default="")
    asked_by: Mapped[str] = mapped_column(String(80), default="")
    answer: Mapped[str] = mapped_column(String(16), default="unknown")
    ref: Mapped[str] = mapped_column(String(40), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, index=True)


class ItadminReview(Base):
    """Quarterly access review: every active access, flags, her keep / remove per line."""
    __tablename__ = "itadmin_reviews"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("ir"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(14), default="")             # R-2026-Q4
    items: Mapped[str] = mapped_column(Text, default="[]")
    status: Mapped[str] = mapped_column(String(8), default="open")         # open | done
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    done_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
