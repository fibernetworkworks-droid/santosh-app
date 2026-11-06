"""v0.410 Principal Software Architect: her architecture designs and the PR reviews made against them."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now


class ArchProject(Base):
    """One system she wants designed (greenfield from her brief, or her GitHub repo read first).
    status: reading -> designing -> drawing -> waiting_her -> approved ; failed / cancelled."""
    __tablename__ = "arch_projects"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("arch"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    conversation_id: Mapped[str] = mapped_column(String(64), default="")
    title: Mapped[str] = mapped_column(String(160), default="")
    brief: Mapped[str] = mapped_column(Text, default="")
    repo: Mapped[str] = mapped_column(String(160), default="")          # owner/name, '' = greenfield
    scale: Mapped[dict] = mapped_column(JSON, default=dict)             # her numbers (dau, ...)
    status: Mapped[str] = mapped_column(String(16), default="reading")
    stage: Mapped[str] = mapped_column(String(160), default="")
    error: Mapped[str] = mapped_column(Text, default="")
    version: Mapped[int] = mapped_column(Integer, default=0)
    design: Mapped[dict] = mapped_column(JSON, default=dict)            # the model's structured design (validated)
    capacity: Mapped[dict] = mapped_column(JSON, default=dict)          # capacity.compute() - numbers made in code
    diagrams: Mapped[list] = mapped_column(JSON, default=list)          # [{name, mermaid, ok, error, svg, png}]
    repo_facts: Mapped[dict] = mapped_column(JSON, default=dict)        # files read, languages, manifests
    changes: Mapped[list] = mapped_column(JSON, default=list)           # her change requests, oldest first
    kind: Mapped[str | None] = mapped_column(String(16), nullable=True)  # MASTER: design|assess|migrate|decide|threat|scale (None = design)
    extra: Mapped[dict | None] = mapped_column(JSON, nullable=True)      # MASTER: kind sections + sums made in code + peer review + checks
    watch_prs: Mapped[bool | None] = mapped_column(Boolean, nullable=True)       # review new PRs against the approved design
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)


class ArchReview(Base):
    """A pull request read against the APPROVED design: findings stay here until her tap posts them."""
    __tablename__ = "arch_reviews"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("arv"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    project_id: Mapped[str] = mapped_column(String(40), index=True)
    repo: Mapped[str] = mapped_column(String(160), default="")
    pr_number: Mapped[int] = mapped_column(Integer, default=0)
    pr_title: Mapped[str] = mapped_column(String(300), default="")
    head_sha: Mapped[str] = mapped_column(String(64), default="")
    status: Mapped[str] = mapped_column(String(16), default="draft")    # draft | posted | discarded | failed
    verdict: Mapped[str] = mapped_column(String(20), default="")        # fits | drifts | breaks
    summary: Mapped[str] = mapped_column(Text, default="")
    findings: Mapped[list] = mapped_column(JSON, default=list)          # [{severity, area, adr, finding, fix}]
    error: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
