"""Tables of the Developer Sahayak (all prefixed devsahayak_)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now


class DevSettings(Base):
    __tablename__ = "devsahayak_settings"
    tenant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    token_sealed: Mapped[str] = mapped_column(Text, default="")          # her GitHub token, sealed with the bazar vault
    token_label: Mapped[str] = mapped_column(String(120), default="")    # "@login · fine-grained"
    login: Mapped[str] = mapped_column(String(100), default="")
    default_repo: Mapped[str] = mapped_column(String(200), default="")
    review_post: Mapped[str] = mapped_column(String(10), default="draft")  # draft (her tap) | direct (COMMENT reviews only)
    ask_before_pr: Mapped[bool] = mapped_column(Boolean, default=False)   # private repos: PR at once; public repos ALWAYS ask
    draft_pr: Mapped[bool] = mapped_column(Boolean, default=False)
    allow_workflows: Mapped[bool] = mapped_column(Boolean, default=False)
    merge_method: Mapped[str] = mapped_column(String(8), default="squash")
    max_files: Mapped[int] = mapped_column(Integer, default=20)
    max_lines: Mapped[int] = mapped_column(Integer, default=1500)
    rules: Mapped[str] = mapped_column(Text, default="")                 # her coding rules (style, stack)
    seq: Mapped[int] = mapped_column(Integer, default=0)


class DevRepo(Base):
    __tablename__ = "devsahayak_repos"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("dr"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    full_name: Mapped[str] = mapped_column(String(200), default="")      # owner/repo
    default_branch: Mapped[str] = mapped_column(String(100), default="main")
    private: Mapped[bool] = mapped_column(Boolean, default=True)
    language: Mapped[str] = mapped_column(String(40), default="")
    deploy_workflow: Mapped[str] = mapped_column(String(200), default="")  # .github/workflows/deploy.yml (her own)
    deploy_ref: Mapped[str] = mapped_column(String(100), default="")       # '' = default branch
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class DevTask(Base):
    """One piece of work: write / fix / tests / docs / explain. Lives on a hoola/<task> branch + a pull request."""
    __tablename__ = "devsahayak_tasks"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("dt"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(12), default="")          # D-0001
    kind: Mapped[str] = mapped_column(String(10), default="write")       # write | fix | tests | docs | explain
    repo: Mapped[str] = mapped_column(String(200), default="")
    text: Mapped[str] = mapped_column(Text, default="")                  # her words / issue / trace (secrets scrubbed)
    issue: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(14), default="new")
    # new | refused | ready (prepared, waits for her tap to open the PR) | pr_open | checks_failed | merged | closed | explained | failed | cancelled
    base: Mapped[str] = mapped_column(String(100), default="")
    base_sha: Mapped[str] = mapped_column(String(40), default="")
    branch: Mapped[str] = mapped_column(String(160), default="")
    explain: Mapped[str] = mapped_column(Text, default="")
    found: Mapped[str] = mapped_column(Text, default="{}")               # trace files, errors, words, files read
    changes: Mapped[str] = mapped_column(Text, default="[]")             # [{path, why, old_sha, new (content), added, removed}]
    checks: Mapped[str] = mapped_column(Text, default="[]")              # secure-coding warnings
    pr_title: Mapped[str] = mapped_column(String(200), default="")
    pr_body: Mapped[str] = mapped_column(Text, default="")
    test_plan: Mapped[str] = mapped_column(Text, default="")
    risk: Mapped[str] = mapped_column(Text, default="")
    hash: Mapped[str] = mapped_column(String(32), default="")            # push card hash
    pr_number: Mapped[int] = mapped_column(Integer, default=0)
    pr_url: Mapped[str] = mapped_column(Text, default="")
    head_sha: Mapped[str] = mapped_column(String(40), default="")
    ci: Mapped[str] = mapped_column(Text, default="{}")
    ci_told: Mapped[str] = mapped_column(String(60), default="")         # head_sha:state already told
    error: Mapped[str] = mapped_column(Text, default="")
    rounds: Mapped[int] = mapped_column(Integer, default=0)
    conv: Mapped[str] = mapped_column(String(40), default="")
    log: Mapped[str] = mapped_column(Text, default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)


class DevReview(Base):
    """Hoola's review of a PR: a DRAFT until her tap posts it (or COMMENT-only reviews when she set review_post=direct)."""
    __tablename__ = "devsahayak_reviews"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("dv"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    repo: Mapped[str] = mapped_column(String(200), default="")
    pr_number: Mapped[int] = mapped_column(Integer, default=0)
    pr_title: Mapped[str] = mapped_column(String(200), default="")
    author: Mapped[str] = mapped_column(String(100), default="")
    head_sha: Mapped[str] = mapped_column(String(40), default="")
    summary: Mapped[str] = mapped_column(Text, default="")
    suggest: Mapped[str] = mapped_column(String(16), default="COMMENT")   # COMMENT | REQUEST_CHANGES (Hoola never suggests APPROVE alone)
    comments: Mapped[str] = mapped_column(Text, default="[]")             # [{path, line, body, severity}]
    findings: Mapped[str] = mapped_column(Text, default="[]")             # code checks + secrets on added lines
    hash: Mapped[str] = mapped_column(String(32), default="")
    status: Mapped[str] = mapped_column(String(10), default="draft")     # draft | posted | discarded | stale | failed
    posted_event: Mapped[str] = mapped_column(String(16), default="")
    url: Mapped[str] = mapped_column(Text, default="")
    conv: Mapped[str] = mapped_column(String(40), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, index=True)


class DevAction(Base):
    """A merge or a deploy waiting for HER tap. Only POST /api/devsahayak/actions/{id}/decide runs it."""
    __tablename__ = "devsahayak_actions"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("da"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    kind: Mapped[str] = mapped_column(String(8), default="merge")        # merge | deploy
    repo: Mapped[str] = mapped_column(String(200), default="")
    pr_number: Mapped[int] = mapped_column(Integer, default=0)
    pr_title: Mapped[str] = mapped_column(String(200), default="")
    base: Mapped[str] = mapped_column(String(100), default="")
    head_sha: Mapped[str] = mapped_column(String(40), default="")         # merge: PR head; deploy: the ref's commit
    method: Mapped[str] = mapped_column(String(8), default="squash")
    workflow: Mapped[str] = mapped_column(String(200), default="")
    ref: Mapped[str] = mapped_column(String(100), default="")
    inputs: Mapped[str] = mapped_column(Text, default="{}")
    ci_state: Mapped[str] = mapped_column(String(10), default="none")
    ci: Mapped[str] = mapped_column(Text, default="{}")
    notes: Mapped[str] = mapped_column(Text, default="[]")
    hash: Mapped[str] = mapped_column(String(32), default="")
    status: Mapped[str] = mapped_column(String(10), default="waiting")   # waiting | done | rejected | failed | stale | running
    force_reason: Mapped[str] = mapped_column(Text, default="")
    task_id: Mapped[str] = mapped_column(String(40), default="")
    result: Mapped[str] = mapped_column(Text, default="{}")              # merge sha / run id + url + conclusion
    conv: Mapped[str] = mapped_column(String(40), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, index=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
