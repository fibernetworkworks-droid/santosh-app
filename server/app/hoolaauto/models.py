"""HOOLA AUTO tables (all prefixed auto_). Registered in db.init_db and self-healed by ensure_tables()."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now

_READY: set[int] = set()


class AutoProject(Base):
    """One client project. `phase`: setup | intake | review | design | plan | build | uat | golive | handover | done."""
    __tablename__ = "auto_projects"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("ap"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    name: Mapped[str] = mapped_column(String(120), default="")
    slug: Mapped[str] = mapped_column(String(60), default="")
    client_name: Mapped[str] = mapped_column(String(120), default="")
    client_contact: Mapped[str] = mapped_column(String(120), default="")
    client_email: Mapped[str] = mapped_column(String(160), default="")
    repos: Mapped[str] = mapped_column(Text, default="[]")          # JSON list of her GitHub repos (owner/name); first = main
    role_repo: Mapped[str] = mapped_column(Text, default="{}")      # JSON {role: repo} when a role works in another repo
    env_id: Mapped[str] = mapped_column(String(40), default="")     # Hoola Code environment ('' = each repo's own settings)
    phase: Mapped[str] = mapped_column(String(12), default="setup")
    paused: Mapped[bool] = mapped_column(Boolean, default=False)
    archived: Mapped[bool] = mapped_column(Boolean, default=False)
    cap_inr: Mapped[float] = mapped_column(Float, default=1500.0)   # model-use ceiling for the whole project
    planning_inr: Mapped[float] = mapped_column(Float, default=0.0)  # Hoola Auto's own planning / chat calls (estimate)
    plan: Mapped[str] = mapped_column(Text, default="{}")           # stories, scope, timeline, team (JSON)
    design: Mapped[str] = mapped_column(Text, default="{}")         # architecture, data, screens, api, risks (JSON)
    branch: Mapped[str] = mapped_column(String(160), default="")    # hoola/auto-<slug>, made at G3
    sprint: Mapped[int] = mapped_column(Integer, default=0)
    sprints: Mapped[int] = mapped_column(Integer, default=0)
    golive: Mapped[str] = mapped_column(Text, default="[]")         # [{repo, pr, url, sha, state}] the PRs to her main branch
    client_hash: Mapped[str] = mapped_column(String(64), default="", index=True)   # sha256 of the client link token
    client_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    client_tail: Mapped[str] = mapped_column(String(8), default="")
    client_signed: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    client_msgs: Mapped[str] = mapped_column(Text, default="[]")    # the client page's conversation [{who, text, at}]
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)


class AutoAnswer(Base):
    """One intake answer and where it came from. state: missing | found (client to confirm) | confirmed | conflict."""
    __tablename__ = "auto_answers"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("aa"))
    project_id: Mapped[str] = mapped_column(String(40), index=True)
    key: Mapped[str] = mapped_column(String(40), default="")
    value: Mapped[str] = mapped_column(Text, default="")
    source: Mapped[str] = mapped_column(String(12), default="")     # form | doc | call | repo | chat | you | client
    source_ref: Mapped[str] = mapped_column(String(200), default="")   # "requirements.pdf, page 3", "kickoff call, 12:40"
    state: Mapped[str] = mapped_column(String(10), default="missing")
    alt: Mapped[str] = mapped_column(Text, default="")              # JSON {value, source, source_ref} when two sources disagree
    asked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)


class AutoSource(Base):
    """Something the Intake agent read: the client link, a document, a recording, a pasted email / WhatsApp chat, a repo."""
    __tablename__ = "auto_sources"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("as"))
    project_id: Mapped[str] = mapped_column(String(40), index=True)
    kind: Mapped[str] = mapped_column(String(10), default="doc")    # link | doc | recording | text | repo
    name: Mapped[str] = mapped_column(String(200), default="")
    status: Mapped[str] = mapped_column(String(10), default="reading")   # reading | done | failed
    answers: Mapped[int] = mapped_column(Integer, default=0)
    note: Mapped[str] = mapped_column(Text, default="")
    text: Mapped[str] = mapped_column(Text, default="")             # what was read (capped), never shown to the client
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class AutoGate(Base):
    """A client gate G1..G8 (G4 once per sprint, G5 once per change). state: wait | now | approved | changes."""
    __tablename__ = "auto_gates"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("ag"))
    project_id: Mapped[str] = mapped_column(String(40), index=True)
    code: Mapped[str] = mapped_column(String(4), default="G1")
    n: Mapped[int] = mapped_column(Integer, default=0)              # the sprint (G4) or change number (G5)
    state: Mapped[str] = mapped_column(String(10), default="wait")
    body: Mapped[str] = mapped_column(Text, default="{}")           # what she is asked to approve (JSON)
    hash: Mapped[str] = mapped_column(String(32), default="")       # her tap must carry this (what she saw is what is approved)
    note: Mapped[str] = mapped_column(Text, default="")
    opened_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AutoTask(Base):
    """One planned piece of work for one agent. state: todo | queued | working | needs | done | failed | skipped."""
    __tablename__ = "auto_tasks"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("at"))
    project_id: Mapped[str] = mapped_column(String(40), index=True)
    role: Mapped[str] = mapped_column(String(20), default="")
    seq: Mapped[int] = mapped_column(Integer, default=0)
    title: Mapped[str] = mapped_column(String(200), default="")
    detail: Mapped[str] = mapped_column(Text, default="")
    story: Mapped[str] = mapped_column(String(12), default="")
    sprint: Mapped[int] = mapped_column(Integer, default=1)
    depends: Mapped[str] = mapped_column(Text, default="[]")        # JSON list of seq numbers that must be done first
    state: Mapped[str] = mapped_column(String(10), default="todo")
    dev_task_id: Mapped[str] = mapped_column(String(40), default="", index=True)
    repo: Mapped[str] = mapped_column(String(200), default="")
    proof: Mapped[str] = mapped_column(Text, default="{}")          # {pr, url, tests, files, added, removed, ci, merged_sha}
    why: Mapped[str] = mapped_column(Text, default="")              # what she needs to do / what went wrong
    cost_inr: Mapped[float] = mapped_column(Float, default=0.0)
    change_id: Mapped[str] = mapped_column(String(40), default="")  # added by an approved change request
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    done_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AutoEvent(Base):
    """One line of the live feed. kind: done | step | need | info."""
    __tablename__ = "auto_events"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("ae"))
    project_id: Mapped[str] = mapped_column(String(40), index=True)
    role: Mapped[str] = mapped_column(String(20), default="")
    kind: Mapped[str] = mapped_column(String(6), default="step")
    text: Mapped[str] = mapped_column(Text, default="")
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, index=True)


class AutoChange(Base):
    """A change request (CR-01 ...): something she asked an agent for that is not in the approved plan."""
    __tablename__ = "auto_changes"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("ac"))
    project_id: Mapped[str] = mapped_column(String(40), index=True)
    n: Mapped[int] = mapped_column(Integer, default=1)
    role: Mapped[str] = mapped_column(String(20), default="")
    title: Mapped[str] = mapped_column(String(200), default="")
    detail: Mapped[str] = mapped_column(Text, default="")
    minutes: Mapped[int] = mapped_column(Integer, default=0)
    cost_inr: Mapped[float] = mapped_column(Float, default=0.0)
    state: Mapped[str] = mapped_column(String(10), default="wait")   # wait | approved | declined
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class AutoMsg(Base):
    """Her conversation with one agent. who: you | agent. tag: 'Applied to task 9' etc. change_id: a CR card."""
    __tablename__ = "auto_msgs"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("am"))
    project_id: Mapped[str] = mapped_column(String(40), index=True)
    role: Mapped[str] = mapped_column(String(20), default="")
    who: Mapped[str] = mapped_column(String(6), default="you")
    text: Mapped[str] = mapped_column(Text, default="")
    tag: Mapped[str] = mapped_column(String(120), default="")
    change_id: Mapped[str] = mapped_column(String(40), default="")
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class AutoWatch(Base):
    """v0.949 the Monitor agent after go-live: what it watches for one project. One row per project.
    feeds = [{app, what}] read-only reads of her connected apps (an error tracker, a cloud console, Slack ...)."""
    __tablename__ = "auto_watch"
    project_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    on: Mapped[bool] = mapped_column(Boolean, default=False)
    url: Mapped[str] = mapped_column(String(400), default="")       # the live app (checked from the server, public hosts only)
    every_min: Mapped[int] = mapped_column(Integer, default=60)
    feeds: Mapped[str] = mapped_column(Text, default="[]")
    seen: Mapped[str] = mapped_column(Text, default="{}")            # {feed_key: hash of what it read last time}
    last_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_say: Mapped[str] = mapped_column(Text, default="")          # the last check, in words
    checks: Mapped[int] = mapped_column(Integer, default=0)


class AutoAlert(Base):
    """One problem the Monitor found. sig = what makes it the same problem (never two open alerts for one).
    state: open | fixing | dismissed | resolved. dev_task_id = the Hoola Code fix session she started with her tap."""
    __tablename__ = "auto_alerts"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("aa"))
    project_id: Mapped[str] = mapped_column(String(40), index=True)
    kind: Mapped[str] = mapped_column(String(12), default="")        # site | slow | ci | feed
    sig: Mapped[str] = mapped_column(String(80), default="", index=True)
    title: Mapped[str] = mapped_column(String(200), default="")
    detail: Mapped[str] = mapped_column(Text, default="")
    repo: Mapped[str] = mapped_column(String(160), default="")
    state: Mapped[str] = mapped_column(String(10), default="open")
    times: Mapped[int] = mapped_column(Integer, default=1)
    dev_task_id: Mapped[str] = mapped_column(String(40), default="")
    first_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    last_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


TABLES = (AutoProject, AutoAnswer, AutoSource, AutoGate, AutoTask, AutoEvent, AutoChange, AutoMsg, AutoWatch, AutoAlert)


def ensure_tables() -> None:
    """Self-heal (the v0.190.1 rule): created checkfirst once per engine, so a DB born before this module still works."""
    from .. import db as _db
    eng = getattr(_db, "_engine", None)
    if eng is None or id(eng) in _READY:
        return
    for t in TABLES:
        t.__table__.create(eng, checkfirst=True)
    _READY.add(id(eng))
