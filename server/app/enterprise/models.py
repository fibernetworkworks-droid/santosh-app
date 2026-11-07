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

# ---------------------------------------------------------------- v0.363 real read / write against her ERP
class EntEndpoint(Base):
    """Her own ERP endpoint when Composio does not carry it (SAP OData, Windchill, any REST the vendor publishes).

    The credential is SEALED (bazar.security vault) exactly like v0.290's custom MCP: the clear value never sits in
    the database, in a listing, or in anything the model can read. `auth_masked` is all anyone else ever sees."""
    __tablename__ = "ent_endpoints"
    __table_args__ = (UniqueConstraint("tenant_id", "role", "system", name="uq_ent_endpoint"),)
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("ee"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    role: Mapped[str] = mapped_column(String(24), index=True)
    system: Mapped[str] = mapped_column(String(24))
    base_url: Mapped[str] = mapped_column(String(400), default="")
    env: Mapped[str] = mapped_column(String(10), default="test")      # test | production
    auth_kind: Mapped[str] = mapped_column(String(12), default="bearer")   # bearer | basic | header
    auth_enc: Mapped[str] = mapped_column(Text, default="")           # sealed; never read back out to the model
    auth_masked: Mapped[str] = mapped_column(String(60), default="")
    header_name: Mapped[str] = mapped_column(String(60), default="")
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class EntRun(Base):
    """One real operation against her ERP: a read, or a write job of many rows.

    A write run is never one call. It is plan -> dry run -> HER TAP -> batches -> verify, and it must survive
    dying half way: `rows` carry their own idempotency key, so a resume can never post the same record twice."""
    __tablename__ = "ent_runs"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("er"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    role: Mapped[str] = mapped_column(String(24), index=True)
    job: Mapped[str] = mapped_column(String(24), default="")
    project_id: Mapped[str] = mapped_column(String(40), default="")
    system: Mapped[str] = mapped_column(String(24), default="")
    env: Mapped[str] = mapped_column(String(10), default="test")
    rail: Mapped[str] = mapped_column(String(12), default="")         # composio | odata
    op: Mapped[str] = mapped_column(String(10), default="read")       # read | write
    verb: Mapped[str] = mapped_column(String(16), default="")         # create | update | upsert | get | query
    api: Mapped[str] = mapped_column(String(10), default="data")      # data = records | tooling = configuration
    target: Mapped[str] = mapped_column(String(120), default="")      # the entity / tool slug
    title: Mapped[str] = mapped_column(String(200), default="")
    plan: Mapped[str] = mapped_column(Text, default="{}")
    status: Mapped[str] = mapped_column(String(14), default="planned")
    # planned | dry_run | waiting_owner | running | done | failed | stopped
    total: Mapped[int] = mapped_column(Integer, default=0)
    ok_count: Mapped[int] = mapped_column(Integer, default=0)
    fail_count: Mapped[int] = mapped_column(Integer, default=0)
    approved_by: Mapped[str] = mapped_column(String(80), default="")
    error: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, index=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    done_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class EntRunRow(Base):
    """One record inside a write run. `key` is hers (the natural key); `idem` is what makes a resume safe."""
    __tablename__ = "ent_run_rows"
    __table_args__ = (UniqueConstraint("run_id", "idem", name="uq_ent_run_row"),)
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("rr"))
    run_id: Mapped[str] = mapped_column(String(40), index=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    n: Mapped[int] = mapped_column(Integer, default=0)
    key: Mapped[str] = mapped_column(String(160), default="")
    idem: Mapped[str] = mapped_column(String(64), default="")
    payload: Mapped[str] = mapped_column(Text, default="{}")
    before: Mapped[str] = mapped_column(Text, default="")             # what it looked like first: the rollback material
    status: Mapped[str] = mapped_column(String(10), default="todo")   # todo | done | failed | skipped
    result: Mapped[str] = mapped_column(Text, default="")
    error: Mapped[str] = mapped_column(Text, default="")
    at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

