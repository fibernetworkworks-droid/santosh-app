"""Tables of the Photo Sahayak (all prefixed photoassist_). JSON kept in Text columns (pattern of banquet / interior)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now


class PhotoassistSettings(Base):
    __tablename__ = "photoassist_settings"
    tenant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    studio: Mapped[str] = mapped_column(String(160), default="")
    gstin: Mapped[str] = mapped_column(String(15), default="")
    address: Mapped[str] = mapped_column(Text, default="")
    phone: Mapped[str] = mapped_column(String(20), default="")
    email: Mapped[str] = mapped_column(String(120), default="")
    upi_id: Mapped[str] = mapped_column(String(80), default="")
    gst_pct: Mapped[float] = mapped_column(Float, default=18.0)                 # used only when she has a GSTIN
    buffer_minutes: Mapped[int] = mapped_column(Integer, default=60)            # travel / setup gap between two shoots
    hold_hours: Mapped[int] = mapped_column(Integer, default=48)
    delivery_days: Mapped[int] = mapped_column(Integer, default=30)
    retention_days: Mapped[int] = mapped_column(Integer, default=90)            # raw files after delivery (DPDP: keep only as needed)
    copyright: Mapped[str] = mapped_column(String(10), default="keep")          # keep (photographer) | client
    stages: Mapped[str] = mapped_column(Text, default="")
    cancel: Mapped[str] = mapped_column(Text, default="")
    terms: Mapped[str] = mapped_column(Text, default="")
    rpc_number: Mapped[str] = mapped_column(String(40), default="")             # drone Remote Pilot Certificate (her word)
    rpc_until: Mapped[str] = mapped_column(String(10), default="")
    morning_time: Mapped[str] = mapped_column(String(5), default="08:00")
    last_morning: Mapped[str] = mapped_column(String(10), default="")
    rules: Mapped[str] = mapped_column(Text, default="")
    shoot_seq: Mapped[int] = mapped_column(Integer, default=0)
    rc_seq: Mapped[int] = mapped_column(Integer, default=0)
    inv_seq: Mapped[int] = mapped_column(Integer, default=0)


class PhotoassistPackage(Base):
    __tablename__ = "photoassist_packages"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("pp"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    name: Mapped[str] = mapped_column(String(120), default="")
    price: Mapped[float] = mapped_column(Float, default=0.0)                    # HER price before GST
    unit: Mapped[str] = mapped_column(String(10), default="shoot")              # shoot | day | hour | photo | nos
    includes: Mapped[str] = mapped_column(Text, default="[]")
    edits: Mapped[int] = mapped_column(Integer, default=0)                      # retouched photos included
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class PhotoassistGear(Base):
    __tablename__ = "photoassist_gear"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("pg"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    name: Mapped[str] = mapped_column(String(120), default="")
    kind: Mapped[str] = mapped_column(String(12), default="other")
    serial: Mapped[str] = mapped_column(String(60), default="")
    uin: Mapped[str] = mapped_column(String(40), default="")                    # drone UIN (Digital Sky)
    weight_g: Mapped[int | None] = mapped_column(Integer, nullable=True)
    insured_until: Mapped[str] = mapped_column(String(10), default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class PhotoassistShoot(Base):
    __tablename__ = "photoassist_shoots"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("ps"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(12), default="")
    kind: Mapped[str] = mapped_column(String(16), default="other")
    client: Mapped[str] = mapped_column(String(120), default="")
    phone: Mapped[str] = mapped_column(String(20), default="")
    email: Mapped[str] = mapped_column(String(120), default="")
    client_kind: Mapped[str] = mapped_column(String(10), default="personal")    # personal | business
    client_gstin: Mapped[str] = mapped_column(String(15), default="")
    day: Mapped[str] = mapped_column(String(10), default="", index=True)
    end_day: Mapped[str] = mapped_column(String(10), default="")
    start: Mapped[str] = mapped_column(String(5), default="")
    end: Mapped[str] = mapped_column(String(5), default="")
    location: Mapped[str] = mapped_column(Text, default="")
    place: Mapped[str] = mapped_column(String(10), default="other")
    drone: Mapped[bool] = mapped_column(Boolean, default=False)
    minors: Mapped[bool] = mapped_column(Boolean, default=False)
    commercial: Mapped[bool] = mapped_column(Boolean, default=False)
    shooters: Mapped[str] = mapped_column(Text, default='["main"]')             # who is busy (clash checked per person)
    lines: Mapped[str] = mapped_column(Text, default="[]")                      # [{package_id?, name, qty, price}]
    discount: Mapped[float] = mapped_column(Float, default=0.0)                 # only by her tap
    status: Mapped[str] = mapped_column(String(10), default="draft")            # draft|hold|confirmed|shot|delivered|done|cancelled
    hold_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    portfolio_ok: Mapped[str] = mapped_column(String(6), default="")            # '' unknown | yes | no (client's own choice)
    shot_list: Mapped[str] = mapped_column(Text, default="[]")
    gear_list: Mapped[str] = mapped_column(Text, default="[]")
    checks_done: Mapped[str] = mapped_column(Text, default="[]")                # permission keys she ticked
    deliverables: Mapped[str] = mapped_column(Text, default="[]")
    edits: Mapped[str] = mapped_column(Text, default="[]")
    gallery: Mapped[str] = mapped_column(Text, default="{}")
    payments: Mapped[str] = mapped_column(Text, default="[]")
    stages: Mapped[str] = mapped_column(Text, default="[]")
    invoice: Mapped[str] = mapped_column(Text, default="{}")
    cancel: Mapped[str] = mapped_column(Text, default="{}")
    delivered_on: Mapped[str] = mapped_column(String(10), default="")
    raw_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str] = mapped_column(Text, default="")
    log: Mapped[str] = mapped_column(Text, default="[]")
    forgotten: Mapped[bool] = mapped_column(Boolean, default=False)
    conv: Mapped[str] = mapped_column(String(40), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class PhotoassistRelease(Base):
    __tablename__ = "photoassist_releases"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("pr"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    shoot_id: Mapped[str] = mapped_column(String(40), index=True, default="")
    kind: Mapped[str] = mapped_column(String(10), default="model")              # model | minor | property
    person: Mapped[str] = mapped_column(String(120), default="")
    guardian: Mapped[str] = mapped_column(String(120), default="")
    place: Mapped[str] = mapped_column(Text, default="")
    uses: Mapped[str] = mapped_column(Text, default="[]")
    lang: Mapped[str] = mapped_column(String(4), default="en")
    text: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(10), default="draft")            # draft | signed | withdrawn
    signed_on: Mapped[str] = mapped_column(String(10), default="")
    proof_path: Mapped[str] = mapped_column(Text, default="")
    withdrawn_on: Mapped[str] = mapped_column(String(10), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class PhotoassistPhoto(Base):
    __tablename__ = "photoassist_photos"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("ph"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    shoot_id: Mapped[str] = mapped_column(String(40), index=True, default="")
    name: Mapped[str] = mapped_column(String(160), default="")
    path: Mapped[str] = mapped_column(Text, default="")
    phash: Mapped[str] = mapped_column(String(64), default="")
    signals: Mapped[str] = mapped_column(Text, default="{}")
    hint: Mapped[str] = mapped_column(String(8), default="")                    # keep | maybe | reject (suggestion)
    pick: Mapped[str] = mapped_column(String(8), default="")                    # her choice
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class PhotoassistCard(Base):
    """Everything that waits for HER tap: quote | contract | confirm | pay | delivery | invoice | message | discount | refund."""
    __tablename__ = "photoassist_cards"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("pc"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    shoot_id: Mapped[str] = mapped_column(String(40), index=True, default="")
    kind: Mapped[str] = mapped_column(String(10))
    show: Mapped[str] = mapped_column(Text, default="{}")
    hash: Mapped[str] = mapped_column(String(64), default="")
    status: Mapped[str] = mapped_column(String(10), default="waiting")          # waiting|approved|rejected|stale
    asked_by: Mapped[str] = mapped_column(String(80), default="")
    reason: Mapped[str] = mapped_column(Text, default="")
    result: Mapped[str] = mapped_column(Text, default="{}")
    conv: Mapped[str] = mapped_column(String(40), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PhotoassistAlert(Base):
    __tablename__ = "photoassist_alerts"
    key: Mapped[str] = mapped_column(String(200), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
