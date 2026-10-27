"""Tables of the QA Sahayak (all prefixed qa_)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now


class QaSettings(Base):
    __tablename__ = "qa_settings"
    tenant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    team_name: Mapped[str] = mapped_column(String(120), default="")
    rules: Mapped[str] = mapped_column(Text, default="")                    # her own testing rules (shown to the model)
    target_seq: Mapped[int] = mapped_column(Integer, default=0)
    case_seq: Mapped[int] = mapped_column(Integer, default=0)
    run_seq: Mapped[int] = mapped_column(Integer, default=0)
    bug_seq: Mapped[int] = mapped_column(Integer, default=0)


class QaTarget(Base):
    """What is being tested: a Hoola-built site / app, her own website (ownership verified) or a preview APK (checklist)."""
    __tablename__ = "qa_targets"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("qat"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(12), default="")             # T-01
    name: Mapped[str] = mapped_column(String(160), default="")
    kind: Mapped[str] = mapped_column(String(8), default="url")             # site | app | url | apk
    ref: Mapped[str] = mapped_column(String(40), default="")                # site id / app project id
    url: Mapped[str] = mapped_column(Text, default="")                      # start URL (kind url)
    host: Mapped[str] = mapped_column(String(253), default="")
    verify_token: Mapped[str] = mapped_column(String(64), default="")
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    verified_how: Mapped[str] = mapped_column(String(20), default="")      # hoola_site | hoola_app | hoola_host | dns | meta | file
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    allow_writes: Mapped[bool] = mapped_column(Boolean, default=False)      # forms may really submit (staging sites only)
    govt_facing: Mapped[bool] = mapped_column(Boolean, default=False)       # GIGW 3.0 / IS 17802: accessibility failures block release
    sector: Mapped[str] = mapped_column(String(16), default="general")     # general | govt | securities | bank | health | edu
    map: Mapped[str] = mapped_column(Text, default="{}")                    # discovery: pages, forms, links, screens
    spec: Mapped[str] = mapped_column(Text, default="")                     # the spec text the cases came from (trimmed)
    schedule: Mapped[str] = mapped_column(String(5), default="")            # HH:MM daily regression run, "" = off
    last_sched: Mapped[str] = mapped_column(String(10), default="")
    status: Mapped[str] = mapped_column(String(10), default="active")      # active | removed
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class QaAccount(Base):
    """A TEST account she typed in the app (never her real one), sealed with the bazar vault; only the runner opens it."""
    __tablename__ = "qa_accounts"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("qaa"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    target_id: Mapped[str] = mapped_column(String(40), index=True)
    label: Mapped[str] = mapped_column(String(40), default="test")
    sealed_user: Mapped[str] = mapped_column(Text, default="")
    sealed_pass: Mapped[str] = mapped_column(Text, default="")
    hint: Mapped[str] = mapped_column(String(80), default="")               # masked username shown in the app
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class QaCase(Base):
    __tablename__ = "qa_cases"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("qac"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    target_id: Mapped[str] = mapped_column(String(40), index=True)
    number: Mapped[str] = mapped_column(String(12), default="")             # TC-0001
    title: Mapped[str] = mapped_column(String(200), default="")
    area: Mapped[str] = mapped_column(String(80), default="")              # page / screen / feature
    type: Mapped[str] = mapped_column(String(14), default="functional")    # rules.TYPES
    priority: Mapped[str] = mapped_column(String(3), default="P3")
    technique: Mapped[str] = mapped_column(String(14), default="")         # rules.TECHNIQUES
    preconditions: Mapped[str] = mapped_column(Text, default="")
    steps_text: Mapped[str] = mapped_column(Text, default="[]")             # human lines
    steps: Mapped[str] = mapped_column(Text, default="[]")                  # the safe step language (steps.py); [] = manual
    expected: Mapped[str] = mapped_column(Text, default="")
    account: Mapped[str] = mapped_column(String(40), default="")           # test account label used by {account.*}
    viewport: Mapped[int] = mapped_column(Integer, default=1280)
    tags: Mapped[str] = mapped_column(Text, default="[]")                   # smoke | regression | ...
    source: Mapped[str] = mapped_column(String(10), default="code")        # code | model | her | spec | checklist
    requirement: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(10), default="active")      # active | retired
    last_result: Mapped[str] = mapped_column(String(10), default="")       # pass | fail | blocked | manual | error | skipped
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class QaRun(Base):
    __tablename__ = "qa_runs"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("qar"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    target_id: Mapped[str] = mapped_column(String(40), index=True)
    number: Mapped[str] = mapped_column(String(12), default="")             # R-0001
    which: Mapped[str] = mapped_column(String(20), default="all")          # all | smoke | regression | failed | cases
    status: Mapped[str] = mapped_column(String(10), default="running")     # running | done | failed
    results: Mapped[str] = mapped_column(Text, default="[]")
    counts: Mapped[str] = mapped_column(Text, default="{}")
    bugs: Mapped[str] = mapped_column(Text, default="{}")                   # {new: [...], reopened: [...], verified: [...]}
    by: Mapped[str] = mapped_column(String(60), default="owner")
    error: Mapped[str] = mapped_column(Text, default="")
    conv: Mapped[str] = mapped_column(String(64), default="")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class QaBug(Base):
    __tablename__ = "qa_bugs"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("qab"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    target_id: Mapped[str] = mapped_column(String(40), index=True)
    case_id: Mapped[str] = mapped_column(String(40), default="")
    number: Mapped[str] = mapped_column(String(12), default="")             # B-0001
    title: Mapped[str] = mapped_column(String(240), default="")
    area: Mapped[str] = mapped_column(String(80), default="")
    type: Mapped[str] = mapped_column(String(14), default="functional")
    severity: Mapped[str] = mapped_column(String(10), default="major")     # critical | major | minor | trivial
    priority: Mapped[str] = mapped_column(String(3), default="P3")
    status: Mapped[str] = mapped_column(String(10), default="open")        # open | fixed | verified | reopened | wont_fix | duplicate | closed
    fingerprint: Mapped[str] = mapped_column(String(40), index=True, default="")
    steps: Mapped[str] = mapped_column(Text, default="[]")
    expected: Mapped[str] = mapped_column(Text, default="")
    actual: Mapped[str] = mapped_column(Text, default="")
    console: Mapped[str] = mapped_column(Text, default="[]")
    shot: Mapped[str] = mapped_column(String(160), default="")              # <run id>/<file>
    page_url: Mapped[str] = mapped_column(Text, default="")
    viewport: Mapped[int] = mapped_column(Integer, default=0)
    found_run: Mapped[str] = mapped_column(String(40), default="")
    last_run: Mapped[str] = mapped_column(String(40), default="")
    seen: Mapped[int] = mapped_column(Integer, default=1)
    regression: Mapped[bool] = mapped_column(Boolean, default=False)       # came back after it was verified fixed
    reason: Mapped[str] = mapped_column(Text, default="")
    duplicate_of: Mapped[str] = mapped_column(String(12), default="")
    tracker: Mapped[str] = mapped_column(Text, default="{}")                # {github: {repo, number, url}}
    log: Mapped[str] = mapped_column(Text, default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    fixed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class QaExport(Base):
    """A bug -> her GitHub issue: a card with exactly what will be filed; ONLY her tap files it."""
    __tablename__ = "qa_exports"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("qae"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    bug_id: Mapped[str] = mapped_column(String(40), index=True)
    tracker: Mapped[str] = mapped_column(String(10), default="github")
    repo: Mapped[str] = mapped_column(String(140), default="")              # owner/name
    title: Mapped[str] = mapped_column(String(240), default="")
    body: Mapped[str] = mapped_column(Text, default="")
    labels: Mapped[str] = mapped_column(Text, default="[]")
    hash: Mapped[str] = mapped_column(String(32), default="")
    status: Mapped[str] = mapped_column(String(10), default="card")        # card | done | failed | cancelled
    url: Mapped[str] = mapped_column(Text, default="")
    error: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
