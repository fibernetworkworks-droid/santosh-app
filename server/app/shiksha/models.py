"""Shiksha suite foundation tables (prefix shiksha_): her institution, classes, learners (with guardian consent for
minors), the ONE question bank every education employee shares, and the gradebook."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now


class ShikshaSettings(Base):
    __tablename__ = "shiksha_settings"
    tenant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    institution: Mapped[str] = mapped_column(String(200), default="")   # school / coaching / tutor name
    kind: Mapped[str] = mapped_column(String(20), default="school")     # school | coaching | tutor | college | university
    board: Mapped[str] = mapped_column(String(20), default="CBSE")      # default board for new classes / questions
    medium: Mapped[str] = mapped_column(String(20), default="English")  # language of papers by default
    academic_year: Mapped[str] = mapped_column(String(12), default="")  # e.g. 2026-27
    city: Mapped[str] = mapped_column(String(80), default="")
    seq: Mapped[str] = mapped_column(Text, default="{}")


class ShikshaClass(Base):
    __tablename__ = "shiksha_classes"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("sc"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(12), default="")         # C-01
    name: Mapped[str] = mapped_column(String(80), default="")           # "10-A", "JEE batch 2027"
    grade: Mapped[str] = mapped_column(String(12), default="")          # "10" (K-12) or "UG-1" / "PG" / "PhD"
    board: Mapped[str] = mapped_column(String(20), default="CBSE")
    section: Mapped[str] = mapped_column(String(20), default="")
    subjects: Mapped[str] = mapped_column(Text, default="[]")
    teacher: Mapped[str] = mapped_column(String(120), default="")
    year: Mapped[str] = mapped_column(String(12), default="")
    status: Mapped[str] = mapped_column(String(12), default="active")   # active | archived
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class ShikshaLearner(Base):
    __tablename__ = "shiksha_learners"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("sl"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(12), default="")         # S-0001
    name: Mapped[str] = mapped_column(String(120), default="")
    class_id: Mapped[str] = mapped_column(String(40), default="", index=True)
    roll: Mapped[str] = mapped_column(String(20), default="")
    birth_year: Mapped[int] = mapped_column(Integer, default=0)         # year only (no full date of birth kept)
    adult: Mapped[bool] = mapped_column(Boolean, default=False)         # 18+ (else treated as a child under DPDP s.9)
    guardian_name: Mapped[str] = mapped_column(String(120), default="")
    guardian_relation: Mapped[str] = mapped_column(String(30), default="")
    guardian_phone: Mapped[str] = mapped_column(String(20), default="")
    guardian_email: Mapped[str] = mapped_column(String(160), default="")
    language: Mapped[str] = mapped_column(String(20), default="")
    consent: Mapped[str] = mapped_column(String(12), default="none")    # none | given | withdrawn (child's data)
    consent_log: Mapped[str] = mapped_column(Text, default="[]")        # [{at, status, by, method, note}]
    status: Mapped[str] = mapped_column(String(12), default="active")   # active | left | forgotten
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class ShikshaQuestion(Base):
    """The shared question bank (Pathyakram writes it; the tutor and grading will read it)."""
    __tablename__ = "shiksha_questions"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("sq"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(12), default="")         # Q-00001
    board: Mapped[str] = mapped_column(String(20), default="CBSE")
    grade: Mapped[str] = mapped_column(String(12), default="", index=True)
    subject: Mapped[str] = mapped_column(String(80), default="", index=True)
    chapter: Mapped[str] = mapped_column(String(200), default="")
    topic: Mapped[str] = mapped_column(String(200), default="")
    standards: Mapped[str] = mapped_column(Text, default="[]")          # learning-outcome / standard codes she or the framework gives
    qtype: Mapped[str] = mapped_column(String(20), default="mcq")       # see rules.QTYPES
    bloom: Mapped[str] = mapped_column(String(12), default="understand")
    difficulty: Mapped[str] = mapped_column(String(8), default="medium")  # easy | medium | hard
    competency: Mapped[bool] = mapped_column(Boolean, default=False)    # competency / application based (CBSE pattern)
    marks: Mapped[float] = mapped_column(Float, default=1.0)
    text: Mapped[str] = mapped_column(Text, default="")
    options: Mapped[str] = mapped_column(Text, default="[]")
    answer: Mapped[str] = mapped_column(Text, default="")
    steps: Mapped[str] = mapped_column(Text, default="[]")              # worked solution, step by step
    scheme: Mapped[str] = mapped_column(Text, default="[]")             # marking points [{point, marks}]
    language: Mapped[str] = mapped_column(String(20), default="English")
    source: Mapped[str] = mapped_column(String(12), default="ai")       # ai | teacher | import
    status: Mapped[str] = mapped_column(String(10), default="draft")    # draft | approved | retired
    checks: Mapped[str] = mapped_column(Text, default="[]")             # what the code check found
    used: Mapped[str] = mapped_column(Text, default="[]")               # paper numbers that used it
    fingerprint: Mapped[str] = mapped_column(String(64), default="", index=True)
    approved_by: Mapped[str] = mapped_column(String(80), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class ShikshaMark(Base):
    """Gradebook row: one learner, one assessment. Final marks need a teacher's sign-off (Phase 3 grades into it)."""
    __tablename__ = "shiksha_marks"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("sm"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    learner_id: Mapped[str] = mapped_column(String(40), index=True)
    assessment: Mapped[str] = mapped_column(String(80), default="")     # paper number (P-0001) or her label
    subject: Mapped[str] = mapped_column(String(80), default="")
    marks: Mapped[float] = mapped_column(Float, default=0.0)
    max_marks: Mapped[float] = mapped_column(Float, default=0.0)
    by: Mapped[str] = mapped_column(String(80), default="")             # who entered it
    signed_off: Mapped[bool] = mapped_column(Boolean, default=False)
    note: Mapped[str] = mapped_column(Text, default="")
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
