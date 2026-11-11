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
    archive_after_merge: Mapped[bool | None] = mapped_column(Boolean, nullable=True)   # Phase 2: a merged session leaves the list by itself


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
    setup_cmd: Mapped[str | None] = mapped_column(Text, nullable=True)        # her own dependency-install command for this repo (the box's one-time setup)
    test_cmd: Mapped[str | None] = mapped_column(Text, nullable=True)         # her own test command for this repo (always wins, never needs a tap)
    env_vars: Mapped[str | None] = mapped_column(Text, nullable=True)         # {NAME: value} set for every command in the box - NOT for secrets
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
    ci_round: Mapped[int | None] = mapped_column(Integer, nullable=True)     # v0.351 CI fix rounds done before the PR is ready
    ci_since: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)   # v0.351 when this CI wait began
    self_round: Mapped[int | None] = mapped_column(Integer, nullable=True)   # v0.445 own-review fix rounds done before the PR is ready
    tier: Mapped[str | None] = mapped_column(String(12), nullable=True)     # v0.451 trivial | small | standard | large
    plan: Mapped[str | None] = mapped_column(Text, nullable=True)           # v0.451 the read-only plan pass's plan (JSON)
    proof: Mapped[str | None] = mapped_column(Text, nullable=True)          # v0.447 proof of the bug: the test-first commit + what her CI said
    self_review: Mapped[str | None] = mapped_column(Text, nullable=True)     # v0.445 the last own review (JSON) + has_ci
    conv: Mapped[str] = mapped_column(String(40), default="")
    log: Mapped[str] = mapped_column(Text, default="[]")
    steps: Mapped[str | None] = mapped_column(Text, nullable=True)          # v0.748 HOOLA CODE: structured steps (JSON) for the console
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)          # v0.748 her notes while it works, not yet read (JSON)
    title: Mapped[str | None] = mapped_column(String(200), nullable=True)    # v0.768 her own name for the session (rename)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)   # v0.768 archived = out of the list, kept
    auto_fix: Mapped[bool | None] = mapped_column(Boolean, nullable=True)        # Phase 2: False = a red CI run on THIS PR is not fixed by itself (None = on)
    mode: Mapped[str | None] = mapped_column(String(8), nullable=True)          # Phase 3: ask | auto | plan (None = her setting decides)
    model: Mapped[str | None] = mapped_column(String(80), nullable=True)        # Phase 3: the model she picked for THIS session (None = the server's)
    effort: Mapped[str | None] = mapped_column(String(8), nullable=True)        # Phase 3: low | medium | high
    attach: Mapped[str | None] = mapped_column(Text, nullable=True)             # Phase 3: [{name, kind: image|text, size, file | text}] she attached
    cost: Mapped[str | None] = mapped_column(Text, nullable=True)               # Phase 3: {usd, calls, tok_in, tok_out} of this session's own model calls
    job: Mapped[str | None] = mapped_column(Text, nullable=True)                # the background run in flight {what, words, beat, tries} - a restart picks it up again
    share: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)   # Phase 5: the read-only link's token (None = not shared)
    share_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)   # ... and when it stops working
    hint: Mapped[str | None] = mapped_column(Text, nullable=True)               # Phase 5: a suggested next message for her (ghost text), made once when a round ends
    sched_id: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)   # Phase 5: the scheduled task / trigger that started this session
    pr_notes: Mapped[str | None] = mapped_column(Text, nullable=True)           # Phase 5: reviewers' comments on the PR {seen: [ids], open: [{id, who, path, line, text}]}
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)


class DevSchedule(Base):
    """Phase 5 (Hoola Code): a coding task that starts by itself - on a schedule, on her "Run now", or when her own
    program calls its trigger address with its token. Every run is an ordinary session (DevTask.sched_id points here),
    so the PR tap, the safety checks and her merge tap are exactly the same."""
    __tablename__ = "devsahayak_schedules"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("ds"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    title: Mapped[str] = mapped_column(String(200), default="")
    repo: Mapped[str] = mapped_column(String(200), default="")
    base: Mapped[str] = mapped_column(String(100), default="")
    kind: Mapped[str] = mapped_column(String(10), default="auto")
    text: Mapped[str] = mapped_column(Text, default="")
    mode: Mapped[str] = mapped_column(String(8), default="ask")              # ask | auto (a public repo always asks)
    days: Mapped[str] = mapped_column(String(16), default="off")             # off | daily | weekdays | weekly:<0-6, Monday = 0>
    at: Mapped[str] = mapped_column(String(5), default="09:00")              # HH:MM, India time
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    next_run: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_run: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_task: Mapped[str] = mapped_column(String(40), default="")
    last_note: Mapped[str] = mapped_column(Text, default="")                 # why the last due run did not start (still running, no repo...)
    trigger_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)   # sha256 of the trigger token (the token itself is shown once, never stored)
    trigger_hits: Mapped[str | None] = mapped_column(Text, nullable=True)     # timestamps of recent trigger calls (the hourly limit)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


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
