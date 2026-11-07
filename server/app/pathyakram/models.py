"""Tables of the Pathyakram Sahayak (curriculum & exam designer), prefix pathyakram_. Questions live in the shared
Shiksha bank (shiksha_questions); a paper only points at them."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now


class PathyakramPlan(Base):
    __tablename__ = "pathyakram_plans"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("pp"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(12), default="")        # YP-001 / LP-001 / RB-001
    kind: Mapped[str] = mapped_column(String(10), default="year")      # year | lesson | rubric
    board: Mapped[str] = mapped_column(String(20), default="CBSE")
    grade: Mapped[str] = mapped_column(String(12), default="")
    subject: Mapped[str] = mapped_column(String(80), default="")
    title: Mapped[str] = mapped_column(String(240), default="")
    body: Mapped[str] = mapped_column(Text, default="{}")
    status: Mapped[str] = mapped_column(String(10), default="draft")   # draft | approved
    approved_by: Mapped[str] = mapped_column(String(80), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class PathyakramPaper(Base):
    __tablename__ = "pathyakram_papers"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("pa"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(12), default="")        # P-0001
    board: Mapped[str] = mapped_column(String(20), default="CBSE")
    grade: Mapped[str] = mapped_column(String(12), default="")
    subject: Mapped[str] = mapped_column(String(80), default="")
    title: Mapped[str] = mapped_column(String(240), default="")
    duration_min: Mapped[int] = mapped_column(Integer, default=0)
    max_marks: Mapped[float] = mapped_column(Float, default=0.0)
    blueprint: Mapped[str] = mapped_column(Text, default="{}")         # {sections:[...], source, verified}
    items: Mapped[str] = mapped_column(Text, default="[]")             # [{section, n, question_id, marks}]
    gaps: Mapped[str] = mapped_column(Text, default="[]")              # sections the bank could not fill
    instructions: Mapped[str] = mapped_column(Text, default="[]")
    status: Mapped[str] = mapped_column(String(12), default="draft")   # draft | approved | shared
    approved_by: Mapped[str] = mapped_column(String(80), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class PathyakramShare(Base):
    """A paper / plan going outside (file for print / parents / a Google Forms quiz): only her app tap decides."""
    __tablename__ = "pathyakram_shares"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("psh"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(12), default="")        # SH-001
    what: Mapped[str] = mapped_column(String(10), default="paper")     # paper | plan
    ref_id: Mapped[str] = mapped_column(String(40), default="")
    via: Mapped[str] = mapped_column(String(12), default="file")       # file | form | whatsapp | email
    to_name: Mapped[str] = mapped_column(String(160), default="")
    to_contact: Mapped[str] = mapped_column(String(160), default="")
    with_key: Mapped[str] = mapped_column(String(5), default="no")     # yes = answer key goes too
    note: Mapped[str] = mapped_column(Text, default="")
    hash: Mapped[str] = mapped_column(String(64), default="")
    status: Mapped[str] = mapped_column(String(12), default="waiting")  # waiting | shared | rejected | stale
    result: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
