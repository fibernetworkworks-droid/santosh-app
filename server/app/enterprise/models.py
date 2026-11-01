"""Tables for the Enterprise Systems suite. One set for all ten roles: the role is a column, not a table, because
the work has the same shape everywhere (see rules.py)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now


class EntSystem(Base):
    """A system she connected, per role. Hoola never stores the secret itself - `linked` only records that the app
    made the link (Composio / the system's own OAuth hold the credential), exactly like v0.297 key apps."""
    __tablename__ = "ent_systems"
    __table_args__ = (UniqueConstraint("tenant_id", "role", "system", name="uq_ent_system"),)
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("es"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    role: Mapped[str] = mapped_column(String(24), index=True)
    system: Mapped[str] = mapped_column(String(24))
    label: Mapped[str] = mapped_column(String(80), default="")
    env: Mapped[str] = mapped_column(String(10), default="test")      # test | production - written on every action
    account: Mapped[str] = mapped_column(String(120), default="")     # the account id the app got back; never a secret
    linked: Mapped[bool] = mapped_column(Boolean, default=False)
    note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class EntProject(Base):
    """One piece of work inside a role: a migration, an integration, a compliance year."""
    __tablename__ = "ent_projects"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("ep"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    role: Mapped[str] = mapped_column(String(24), index=True)
    title: Mapped[str] = mapped_column(String(160))
    goal: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(12), default="open")   # open | done | parked
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class EntArtifact(Base):
    """What the job produces: a spec, a field mapping, a plan, a checklist, a register, a report, a test plan."""
    __tablename__ = "ent_artifacts"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("ea"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    role: Mapped[str] = mapped_column(String(24), index=True)
    project_id: Mapped[str] = mapped_column(String(40), default="", index=True)
    kind: Mapped[str] = mapped_column(String(16))                     # rules.ARTIFACTS
    title: Mapped[str] = mapped_column(String(160), default="")
    body: Mapped[str] = mapped_column(Text, default="")               # markdown
    rows: Mapped[str] = mapped_column(Text, default="[]")             # a mapping / register is rows, not prose
    source: Mapped[str] = mapped_column(Text, default="")             # where every fact came from
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class EntItem(Base):
    """A line of work or a finding: a gap, a risk, a due date, a reorder point, a BOM change."""
    __tablename__ = "ent_items"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("ei"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    role: Mapped[str] = mapped_column(String(24), index=True)
    project_id: Mapped[str] = mapped_column(String(40), default="", index=True)
    kind: Mapped[str] = mapped_column(String(16), default="task")     # task | gap | risk | due | finding
    title: Mapped[str] = mapped_column(String(200))
    detail: Mapped[str] = mapped_column(Text, default="")
    owner: Mapped[str] = mapped_column(String(80), default="")
    due: Mapped[str] = mapped_column(String(10), default="")          # YYYY-MM-DD
    severity: Mapped[str] = mapped_column(String(8), default="")      # high | medium | low
    status: Mapped[str] = mapped_column(String(12), default="open")   # open | doing | done | dropped
    amount_paise: Mapped[int] = mapped_column(Integer, default=0)     # a saving / an exposure, when there is one
    source: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class EntSettings(Base):
    __tablename__ = "ent_settings"
    __table_args__ = (UniqueConstraint("tenant_id", "role", name="uq_ent_settings"),)
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("en"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    role: Mapped[str] = mapped_column(String(24))
    company: Mapped[str] = mapped_column(String(120), default="")
    env_default: Mapped[str] = mapped_column(String(10), default="test")
    rules: Mapped[str] = mapped_column(Text, default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
