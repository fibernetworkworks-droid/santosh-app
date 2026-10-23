"""Tables of the DevOps Sahayak (all prefixed devops_). Nullable / defaulted columns only."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now


class DevopsSettings(Base):
    __tablename__ = "devops_settings"
    tenant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    gh_sealed: Mapped[str] = mapped_column(Text, default="")              # her GitHub token, sealed with the bazar vault
    gh_login: Mapped[str] = mapped_column(String(100), default="")
    gh_checked: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    team: Mapped[str] = mapped_column(String(160), default="")
    morning_time: Mapped[str] = mapped_column(String(5), default="09:30")
    last_morning: Mapped[str] = mapped_column(String(10), default="")
    last_sync: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_watch: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deploy_seq: Mapped[int] = mapped_column(Integer, default=0)
    rules: Mapped[str] = mapped_column(Text, default="")


class DevopsRepo(Base):
    __tablename__ = "devops_repos"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("dr"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    full_name: Mapped[str] = mapped_column(String(200), default="")        # owner/repo
    default_branch: Mapped[str] = mapped_column(String(100), default="main")
    private: Mapped[bool] = mapped_column(Boolean, default=True)
    deploy_workflow: Mapped[str] = mapped_column(String(200), default="")  # file name, e.g. deploy.yml
    rollback_workflow: Mapped[str] = mapped_column(String(200), default="")
    environment: Mapped[str] = mapped_column(String(80), default="production")
    deploy_inputs: Mapped[str] = mapped_column(Text, default="[]")          # input names her deploy workflow declares
    watch: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class DevopsRun(Base):
    __tablename__ = "devops_runs"
    id: Mapped[str] = mapped_column(String(60), primary_key=True)            # "<repo id>:<run id>:<attempt>"
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    repo: Mapped[str] = mapped_column(String(200), index=True, default="")
    run_id: Mapped[int] = mapped_column(Integer, default=0)
    attempt: Mapped[int] = mapped_column(Integer, default=1)
    workflow: Mapped[str] = mapped_column(String(200), default="")         # name
    workflow_path: Mapped[str] = mapped_column(String(200), default="")    # .github/workflows/x.yml
    branch: Mapped[str] = mapped_column(String(200), default="")
    sha: Mapped[str] = mapped_column(String(40), default="")
    event: Mapped[str] = mapped_column(String(40), default="")
    title: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(20), default="")            # queued | in_progress | waiting | completed
    conclusion: Mapped[str] = mapped_column(String(20), default="")        # success | failure | cancelled | timed_out ...
    commit_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    seconds: Mapped[int] = mapped_column(Integer, default=0)
    url: Mapped[str] = mapped_column(Text, default="")
    is_deploy: Mapped[bool] = mapped_column(Boolean, default=False)
    is_rollback: Mapped[bool] = mapped_column(Boolean, default=False)
    diagnosis: Mapped[str] = mapped_column(Text, default="")               # JSON: failed jobs, step, category, explanation
    flaky: Mapped[bool] = mapped_column(Boolean, default=False)
    told: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class DevopsTest(Base):
    """A test name seen failing; `flips` = failed in a run whose same commit later passed (flaky signal)."""
    __tablename__ = "devops_tests"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("dt"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    repo: Mapped[str] = mapped_column(String(200), default="")
    name: Mapped[str] = mapped_column(String(300), default="")
    fails: Mapped[int] = mapped_column(Integer, default=0)
    flips: Mapped[int] = mapped_column(Integer, default=0)
    shas: Mapped[str] = mapped_column(Text, default="[]")
    last_seen: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class DevopsCluster(Base):
    """One kind of error in her logs (signature with numbers / ids / times taken out). Only masked samples are kept."""
    __tablename__ = "devops_clusters"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("dc"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    source: Mapped[str] = mapped_column(String(120), default="")           # server / app name
    fmt: Mapped[str] = mapped_column(String(20), default="")               # pm2 | nginx | docker | systemd | python | node | java | text
    signature: Mapped[str] = mapped_column(String(64), index=True, default="")
    pattern: Mapped[str] = mapped_column(Text, default="")
    category: Mapped[str] = mapped_column(String(40), default="")
    level: Mapped[str] = mapped_column(String(10), default="error")
    count: Mapped[int] = mapped_column(Integer, default=0)
    samples: Mapped[str] = mapped_column(Text, default="[]")
    first_seen: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_seen: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(12), default="new")          # new | seen | fixed | ignored
    told: Mapped[bool] = mapped_column(Boolean, default=False)


class DevopsCollector(Base):
    __tablename__ = "devops_collectors"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("dcl"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    name: Mapped[str] = mapped_column(String(120), default="")
    sealed: Mapped[str] = mapped_column(Text, default="")                  # HMAC secret, sealed
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_seen: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    batches: Mapped[int] = mapped_column(Integer, default=0)
    host: Mapped[str] = mapped_column(String(120), default="")
    disk: Mapped[str] = mapped_column(Text, default="[]")                   # last df numbers [{mount, used_pct, free_gb}]
    load: Mapped[str] = mapped_column(Text, default="{}")
    seen_sigs: Mapped[str] = mapped_column(Text, default="[]")             # replay guard
    hour_key: Mapped[str] = mapped_column(String(13), default="")
    hour_count: Mapped[int] = mapped_column(Integer, default=0)
    told: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class DevopsScript(Base):
    __tablename__ = "devops_scripts"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("dsc"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    kind: Mapped[str] = mapped_column(String(30), default="")
    lang: Mapped[str] = mapped_column(String(16), default="bash")           # bash | powershell | yaml | dockerfile | nginx | js | ini
    name: Mapped[str] = mapped_column(String(160), default="")
    ask: Mapped[str] = mapped_column(Text, default="")
    content: Mapped[str] = mapped_column(Text, default="")
    findings: Mapped[str] = mapped_column(Text, default="[]")
    file_id: Mapped[str] = mapped_column(String(80), default="")
    status: Mapped[str] = mapped_column(String(12), default="draft")         # draft | reviewed
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class DevopsChecklist(Base):
    __tablename__ = "devops_checklists"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("dck"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    kind: Mapped[str] = mapped_column(String(30), default="deploy")
    title: Mapped[str] = mapped_column(String(200), default="")
    items: Mapped[str] = mapped_column(Text, default="[]")                  # [{id, section, text, done, by}]
    deploy_id: Mapped[str] = mapped_column(String(40), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class DevopsEndpoint(Base):
    __tablename__ = "devops_endpoints"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("de"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    name: Mapped[str] = mapped_column(String(120), default="")
    url: Mapped[str] = mapped_column(Text, default="")
    expect_status: Mapped[int] = mapped_column(Integer, default=200)
    keyword: Mapped[str] = mapped_column(String(120), default="")
    fails: Mapped[int] = mapped_column(Integer, default=0)
    down_told: Mapped[bool] = mapped_column(Boolean, default=False)
    down_since: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_check: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_ms: Mapped[float] = mapped_column(Float, default=0.0)
    last_problem: Mapped[str] = mapped_column(Text, default="")
    checks: Mapped[int] = mapped_column(Integer, default=0)
    ups: Mapped[int] = mapped_column(Integer, default=0)
    ssl_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ssl_checked: Mapped[str] = mapped_column(String(10), default="")
    ssl_told: Mapped[str] = mapped_column(String(20), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class DevopsDeploy(Base):
    """A production deploy / rollback card. Only her tap (API decide, by_tap) dispatches her own workflow."""
    __tablename__ = "devops_deploys"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("dd"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(16), default="")           # DEP-0001
    kind: Mapped[str] = mapped_column(String(12), default="deploy")       # deploy | rollback | env_review
    repo: Mapped[str] = mapped_column(String(200), default="")
    ref: Mapped[str] = mapped_column(String(200), default="")
    sha: Mapped[str] = mapped_column(String(40), default="")
    environment: Mapped[str] = mapped_column(String(80), default="production")
    workflow: Mapped[str] = mapped_column(String(200), default="")
    inputs: Mapped[str] = mapped_column(Text, default="{}")
    checks: Mapped[str] = mapped_column(Text, default="{}")              # {state, total, failed, pending, names}
    changes: Mapped[str] = mapped_column(Text, default="{}")             # {base, commits, lines, files}
    rollback: Mapped[str] = mapped_column(Text, default="{}")            # {sha, workflow, how}
    review: Mapped[str] = mapped_column(Text, default="{}")              # env_review: {run_id, environment_ids, environments}
    hash: Mapped[str] = mapped_column(String(32), default="")
    status: Mapped[str] = mapped_column(String(16), default="card")       # card | dispatched | running | success | failed | rejected | cancelled | stale
    forced: Mapped[str] = mapped_column(Text, default="")                 # her reason when checks were not green
    reason: Mapped[str] = mapped_column(Text, default="")
    run_id: Mapped[int] = mapped_column(Integer, default=0)
    run_url: Mapped[str] = mapped_column(Text, default="")
    error: Mapped[str] = mapped_column(Text, default="")
    conv: Mapped[str] = mapped_column(String(40), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
