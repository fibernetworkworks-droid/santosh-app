"""v0.122 Website hosting tables: where a site is live, DNS plans with their snapshots (undo), her hosting / DNS keys."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now


class SiteHost(Base):
    __tablename__ = "site_hosts"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("host"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    site_id: Mapped[str] = mapped_column(String(40), index=True)
    hostname: Mapped[str] = mapped_column(String(253), index=True)
    kind: Mapped[str] = mapped_column(String(12), default="free")          # free (<slug>.<base>) | custom (her domain)
    role: Mapped[str] = mapped_column(String(10), default="main")          # main | apex / redirect (redirects to main) | www
    status: Mapped[str] = mapped_column(String(14), default="pending")
    # pending (waiting DNS / SSL) | active | error | removed
    ssl_status: Mapped[str] = mapped_column(String(30), default="")
    cf_id: Mapped[str] = mapped_column(String(64), default="")             # Cloudflare for SaaS custom hostname id
    mode: Mapped[str | None] = mapped_column(String(10), nullable=True, default="")   # v0.276 saas | proxy | direct
    verify: Mapped[str] = mapped_column(Text, default="[]")                # records Cloudflare asks for (TXT / CNAME)
    live_version: Mapped[int] = mapped_column(Integer, default=0)
    launched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_check: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    fails: Mapped[int] = mapped_column(Integer, default=0)
    down_told: Mapped[bool] = mapped_column(Boolean, default=False)
    problem: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class SiteDnsPlan(Base):
    __tablename__ = "site_dns_plans"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("dns"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    site_id: Mapped[str] = mapped_column(String(40), default="")
    domain: Mapped[str] = mapped_column(String(253), default="")
    purpose: Mapped[str] = mapped_column(String(20), default="website")    # website | email | verify | custom
    provider: Mapped[str] = mapped_column(String(20), default="manual")    # cloudflare (her zone) | porkbun | manual
    zone: Mapped[str] = mapped_column(String(64), default="")
    changes: Mapped[str] = mapped_column(Text, default="[]")
    snapshot: Mapped[str] = mapped_column(Text, default="[]")              # the zone's records before applying (undo)
    done: Mapped[str] = mapped_column(Text, default="[]")                  # what was really applied (ids) for undo
    hash: Mapped[str] = mapped_column(String(32), default="")
    status: Mapped[str] = mapped_column(String(12), default="planned")     # planned | applied | undone | failed | manual
    error: Mapped[str] = mapped_column(Text, default="")
    applied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class SiteHostingKey(Base):
    """Her own provider keys (typed only in the app), sealed with the bazar vault."""
    __tablename__ = "site_hosting_keys"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("hk"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    provider: Mapped[str] = mapped_column(String(20))                       # cloudflare | porkbun
    sealed: Mapped[str] = mapped_column(Text, default="")
    sealed2: Mapped[str] = mapped_column(Text, default="")                  # second secret (Porkbun secret key)
    label: Mapped[str] = mapped_column(String(120), default="")
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
