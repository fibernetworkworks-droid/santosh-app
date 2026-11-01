"""Tables of the Guru Sahayak (personal tutor, Shiksha suite Phase 2), prefix guru_. Learners and questions live in the
Shiksha foundation (shiksha_learners / shiksha_questions)."""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now


class GuruSettings(Base):
    __tablename__ = "guru_settings"
    tenant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    day_minutes: Mapped[int] = mapped_column(Integer, default=60)       # a child's daily tutoring time (adults: no cap)
    exam_mode: Mapped[bool] = mapped_column(Boolean, default=False)     # hints only, never a final answer (exam / test days)
    report_weekday: Mapped[int] = mapped_column(Integer, default=6)     # 0 = Monday ... 6 = Sunday
    language: Mapped[str] = mapped_column(String(20), default="")      # teaching language (else the school medium)
    sent: Mapped[str] = mapped_column(Text, default="{}")               # once-keys for weekly reports


class GuruSession(Base):
    __tablename__ = "guru_sessions"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("gs"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(14), default="")        # GS-00001
    learner_id: Mapped[str] = mapped_column(String(40), index=True)
    mode: Mapped[str] = mapped_column(String(10), default="doubt")      # doubt | practice | language
    subject: Mapped[str] = mapped_column(String(80), default="")
    grade: Mapped[str] = mapped_column(String(12), default="")
    topic: Mapped[str] = mapped_column(String(200), default="")
    language: Mapped[str] = mapped_column(String(20), default="")
    ladder: Mapped[str] = mapped_column(Text, default="{}")             # current doubt: {problem, levels[], shown, verified...}
    status: Mapped[str] = mapped_column(String(10), default="open")    # open | closed
    seconds: Mapped[int] = mapped_column(Integer, default=0)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    last_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class GuruTurn(Base):
    __tablename__ = "guru_turns"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("gt"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    session_id: Mapped[str] = mapped_column(String(40), index=True)
    role: Mapped[str] = mapped_column(String(8), default="tutor")      # learner | tutor
    kind: Mapped[str] = mapped_column(String(12), default="text")      # doubt | hint | step | answer | check | feedback | practice | language
    text: Mapped[str] = mapped_column(Text, default="")
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class GuruAttempt(Base):
    __tablename__ = "guru_attempts"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("ga"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    learner_id: Mapped[str] = mapped_column(String(40), index=True)
    session_id: Mapped[str] = mapped_column(String(40), default="")
    question_id: Mapped[str] = mapped_column(String(40), default="")
    topic: Mapped[str] = mapped_column(String(200), default="")
    given: Mapped[str] = mapped_column(Text, default="")
    score: Mapped[float] = mapped_column(Float, default=-1.0)          # 0..1; -1 = not checked yet
    judged_by: Mapped[str] = mapped_column(String(8), default="")      # code | ai
    hints: Mapped[int] = mapped_column(Integer, default=0)
    feedback: Mapped[str] = mapped_column(Text, default="")
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class GuruMastery(Base):
    """How well one learner knows one topic: a 0..1 score that moves with every checked answer, and the next revision day
    (spaced repetition: right -> the gap doubles, wrong -> tomorrow)."""
    __tablename__ = "guru_mastery"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("gm"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    learner_id: Mapped[str] = mapped_column(String(40), index=True)
    subject: Mapped[str] = mapped_column(String(80), default="")
    topic: Mapped[str] = mapped_column(String(200), default="")
    score: Mapped[float] = mapped_column(Float, default=0.3)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    correct: Mapped[int] = mapped_column(Integer, default=0)
    interval_days: Mapped[int] = mapped_column(Integer, default=1)
    due: Mapped[date | None] = mapped_column(Date, nullable=True)
    last_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class GuruShare(Base):
    """A weekly progress report going to the guardian: only her app tap decides (a WhatsApp / email draft she sends)."""
    __tablename__ = "guru_shares"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("gsh"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    learner_id: Mapped[str] = mapped_column(String(40), index=True)
    report: Mapped[str] = mapped_column(Text, default="{}")
    via: Mapped[str] = mapped_column(String(10), default="whatsapp")
    hash: Mapped[str] = mapped_column(String(64), default="")
    status: Mapped[str] = mapped_column(String(10), default="waiting")  # waiting | shared | rejected | stale
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
