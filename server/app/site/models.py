"""v0.121 Website Sahayak tables."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now


class Site(Base):
    __tablename__ = "site_sites"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("site"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(16), default="")           # S-0001
    name: Mapped[str] = mapped_column(String(160), default="")            # business / site name
    brief: Mapped[str] = mapped_column(Text, default="")                  # her words
    field: Mapped[str] = mapped_column(String(60), default="")
    goal: Mapped[str] = mapped_column(String(20), default="")
    style: Mapped[str] = mapped_column(String(30), default="")
    styles: Mapped[str] = mapped_column(Text, default="[]")               # the 3 looks offered
    languages: Mapped[str] = mapped_column(Text, default='["en"]')
    facts: Mapped[str] = mapped_column(Text, default="{}")                # what Hoola knows (her words + profile)
    answers: Mapped[str] = mapped_column(Text, default="{}")              # her answers to the questions
    plan: Mapped[str] = mapped_column(Text, default="{}")                 # pages, sections, sitemap
    looks: Mapped[str] = mapped_column(Text, default="[]")                # 3 looks: tokens + hero + screenshots
    look: Mapped[str] = mapped_column(Text, default="{}")                 # chosen tokens
    photos: Mapped[str] = mapped_column(Text, default="[]")               # her photos (asset names)
    status: Mapped[str] = mapped_column(String(16), default="draft")
    # draft | planned (waiting her Haan) | looks (waiting her choice) | building | checking | ready | failed | stopped
    stage: Mapped[str] = mapped_column(String(20), default="brief")       # brief plan look build checks preview ...
    board: Mapped[str] = mapped_column(Text, default="{}")                # pages -> sections -> state, current line
    version: Mapped[int] = mapped_column(Integer, default=0)
    checks: Mapped[str] = mapped_column(Text, default="{}")               # last check report
    scores: Mapped[str] = mapped_column(Text, default="{}")
    preview_token: Mapped[str] = mapped_column(String(64), default="")
    stop: Mapped[bool] = mapped_column(Boolean, default=False)
    queued: Mapped[str] = mapped_column(Text, default="[]")               # changes asked while building
    error: Mapped[str] = mapped_column(Text, default="")
    client: Mapped[str] = mapped_column(String(120), default="")          # agency: which client
    staff: Mapped[str] = mapped_column(String(60), default="")            # agency: staff member id who may work on it
    conv: Mapped[str] = mapped_column(String(64), default="")
    cost_usd: Mapped[float] = mapped_column(default=0.0)
    recovered: Mapped[int | None] = mapped_column(Integer, nullable=True)  # v0.223 auto-restarts after a dead job
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class SiteVersion(Base):
    __tablename__ = "site_versions"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("sv"))
    site_id: Mapped[str] = mapped_column(String(40), index=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    note: Mapped[str] = mapped_column(Text, default="")
    files: Mapped[int] = mapped_column(Integer, default=0)
    bytes: Mapped[int] = mapped_column(Integer, default=0)
    scores: Mapped[str] = mapped_column(Text, default="{}")
    passed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class SiteLead(Base):
    __tablename__ = "site_leads"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("lead"))
    site_id: Mapped[str] = mapped_column(String(40), index=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    name: Mapped[str] = mapped_column(String(120), default="")
    phone: Mapped[str] = mapped_column(String(20), default="")
    email: Mapped[str] = mapped_column(String(160), default="")
    message: Mapped[str] = mapped_column(Text, default="")
    page: Mapped[str] = mapped_column(String(160), default="")
    ip_hash: Mapped[str] = mapped_column(String(32), default="")
    status: Mapped[str] = mapped_column(String(12), default="new")       # new | called | done | spam (+ booking: confirmed | declined)
    kind: Mapped[str | None] = mapped_column(String(10), nullable=True, default="enquiry")   # v0.296 enquiry | booking
    slot: Mapped[str | None] = mapped_column(String(40), nullable=True, default="")          # v0.296 the time a visitor asked for
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class SiteLibStat(Base):
    """Library learning: counts only (field, kind, key), never anyone's words."""
    __tablename__ = "site_lib_stats"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    field: Mapped[str] = mapped_column(String(60), index=True)
    kind: Mapped[str] = mapped_column(String(12))
    key: Mapped[str] = mapped_column(String(60))
    count: Mapped[int] = mapped_column(Integer, default=0)
