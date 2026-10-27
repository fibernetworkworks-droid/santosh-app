"""Tables of the Product Sahayak (all prefixed product_). Nullable / defaulted columns only."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now


class ProductSettings(Base):
    __tablename__ = "product_settings"
    tenant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    product: Mapped[str] = mapped_column(String(160), default="")              # what she builds (app / site / service)
    who: Mapped[str] = mapped_column(Text, default="")                          # main users
    north_star: Mapped[str] = mapped_column(Text, default="{}")                 # {name, definition, unit, target}
    kpis: Mapped[str] = mapped_column(Text, default="[]")                       # [{id, name, definition, unit, target, better: up|down}]
    capacity: Mapped[str] = mapped_column(Text, default="{}")                   # {now, next, later} person-months
    cycle_weeks: Mapped[int] = mapped_column(Integer, default=6)
    scoring: Mapped[str] = mapped_column(String(8), default="rice")             # rice | ice
    language: Mapped[str] = mapped_column(String(12), default="hinglish")
    repo: Mapped[str] = mapped_column(String(140), default="")                  # owner/repo for merged PRs + releases
    app_ref: Mapped[str] = mapped_column(String(40), default="")                # linked App Sahayak project
    site_ref: Mapped[str] = mapped_column(String(40), default="")               # linked Website Sahayak site
    harvest_days: Mapped[int] = mapped_column(Integer, default=90)
    morning_time: Mapped[str] = mapped_column(String(5), default="10:00")
    last_day: Mapped[str] = mapped_column(String(10), default="")
    rules: Mapped[str] = mapped_column(Text, default="")
    seq_opp: Mapped[int] = mapped_column(Integer, default=0)
    seq_spec: Mapped[int] = mapped_column(Integer, default=0)
    seq_rel: Mapped[int] = mapped_column(Integer, default=0)


class ProductKey(Base):
    """Her GitHub token (typed only in the app), sealed with the bazar vault; never shown again."""
    __tablename__ = "product_keys"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("pk"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    provider: Mapped[str] = mapped_column(String(16), default="github")
    sealed: Mapped[str] = mapped_column(Text, default="")
    label: Mapped[str] = mapped_column(String(120), default="")
    can_write: Mapped[bool | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class ProductOpportunity(Base):
    """A customer problem with evidence (opportunity, not a solution), scored with HER numbers, placed on the roadmap."""
    __tablename__ = "product_opportunities"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("po"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(12), default="")                 # O-001
    title: Mapped[str] = mapped_column(String(200), default="")
    problem: Mapped[str] = mapped_column(Text, default="")
    who: Mapped[str] = mapped_column(String(200), default="")
    solutions: Mapped[str] = mapped_column(Text, default="[]")                  # [{text, chosen, assumption}]
    evidence: Mapped[str] = mapped_column(Text, default="[]")                   # [{source, key, count, people, quotes, rupees, at, note}]
    keys: Mapped[str] = mapped_column(Text, default="[]")                       # source keys merged in ("feedback:delivery:neg")
    reach: Mapped[float | None] = mapped_column(Float, nullable=True)
    impact: Mapped[float | None] = mapped_column(Float, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    effort: Mapped[float | None] = mapped_column(Float, nullable=True)         # person-months
    ease: Mapped[float | None] = mapped_column(Float, nullable=True)           # ICE
    ice_impact: Mapped[float | None] = mapped_column(Float, nullable=True)
    ice_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    kano: Mapped[str] = mapped_column(String(16), default="")
    kano_counts: Mapped[str] = mapped_column(Text, default="{}")
    status: Mapped[str] = mapped_column(String(10), default="new")
    bucket: Mapped[str] = mapped_column(String(8), default="")                 # now | next | later
    theme: Mapped[str] = mapped_column(String(80), default="")                 # roadmap theme
    goal: Mapped[str] = mapped_column(String(40), default="")                  # kpi id
    depends: Mapped[str] = mapped_column(Text, default="[]")                   # [opportunity ids]
    merged_into: Mapped[str] = mapped_column(String(40), default="")
    note: Mapped[str] = mapped_column(Text, default="")
    shipped_on: Mapped[str] = mapped_column(String(10), default="")
    release_id: Mapped[str] = mapped_column(String(40), default="")
    result: Mapped[str] = mapped_column(Text, default="{}")                     # before / after once 30 days passed
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class ProductSpec(Base):
    __tablename__ = "product_specs"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("ps"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(12), default="")                 # SP-001
    opp_id: Mapped[str] = mapped_column(String(40), default="", index=True)
    title: Mapped[str] = mapped_column(String(200), default="")
    body: Mapped[str] = mapped_column(Text, default="{}")
    versions: Mapped[str] = mapped_column(Text, default="[]")                  # last 20 bodies
    version: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(10), default="draft")          # draft | ready
    checks: Mapped[str] = mapped_column(Text, default="[]")
    ai: Mapped[bool | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class ProductRelease(Base):
    __tablename__ = "product_releases"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("pr"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(12), default="")                 # R-001
    version: Mapped[str] = mapped_column(String(40), default="")
    title: Mapped[str] = mapped_column(String(200), default="")
    day: Mapped[str] = mapped_column(String(10), default="")
    items: Mapped[str] = mapped_column(Text, default="[]")                     # [{type, text, customer, opp, pr, internal}]
    notes: Mapped[str] = mapped_column(Text, default="{}")                     # {hinglish, english, play: {hi, en}, appstore, changelog}
    sources: Mapped[str] = mapped_column(Text, default="{}")                   # {prs, app, site, opps}
    checks: Mapped[str] = mapped_column(Text, default="[]")
    status: Mapped[str] = mapped_column(String(12), default="draft")          # draft | waiting | published | rejected
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class ProductPublish(Base):
    """A card waiting for HER tap: roadmap or release notes going outside (GitHub release, public page, copy)."""
    __tablename__ = "product_publish"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("pp"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    what: Mapped[str] = mapped_column(String(10), default="release")          # release | roadmap
    ref: Mapped[str] = mapped_column(String(40), default="")
    dest: Mapped[str] = mapped_column(String(10), default="copy")             # github | page | copy
    text: Mapped[str] = mapped_column(Text, default="")
    hash: Mapped[str] = mapped_column(String(32), default="")
    status: Mapped[str] = mapped_column(String(12), default="waiting")       # waiting | published | rejected | failed | stale
    token: Mapped[str] = mapped_column(String(48), default="")                # public page token
    url: Mapped[str] = mapped_column(Text, default="")
    error: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ProductMetric(Base):
    """One number she reports for a KPI / north star (her numbers; Hoola never makes one up)."""
    __tablename__ = "product_metrics"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("pm"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    kpi: Mapped[str] = mapped_column(String(40), default="", index=True)       # kpi id or "north_star"
    day: Mapped[str] = mapped_column(String(10), default="")
    value: Mapped[float] = mapped_column(Float, default=0.0)
    note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
