"""Tables of the Daftar Sahayak (school admin operations, Shiksha suite Phase 3), prefix daftar_. Marks go into the
Shiksha gradebook (shiksha_marks) as unsigned rows; only a teacher signs them off."""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Date, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now


class DaftarAttendance(Base):
    __tablename__ = "daftar_attendance"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("da"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    class_id: Mapped[str] = mapped_column(String(40), index=True)
    learner_id: Mapped[str] = mapped_column(String(40), index=True)
    day: Mapped[date] = mapped_column(Date, index=True)
    status: Mapped[str] = mapped_column(String(8), default="present")   # present | absent | late | leave
    by: Mapped[str] = mapped_column(String(80), default="")
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class DaftarGrading(Base):
    """One grading run (an assessment for a class): the key, where answers came from, every learner's result."""
    __tablename__ = "daftar_gradings"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("dg"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(12), default="")        # GR-001
    class_id: Mapped[str] = mapped_column(String(40), default="")
    assessment: Mapped[str] = mapped_column(String(80), default="")
    subject: Mapped[str] = mapped_column(String(80), default="")
    source: Mapped[str] = mapped_column(String(10), default="sheet")   # sheet | omr | forms | code | rubric
    key: Mapped[str] = mapped_column(Text, default="[]")
    results: Mapped[str] = mapped_column(Text, default="[]")
    stats: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class DaftarTimetable(Base):
    __tablename__ = "daftar_timetables"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("dt"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(12), default="")        # TT-001
    spec: Mapped[str] = mapped_column(Text, default="{}")
    grid: Mapped[str] = mapped_column(Text, default="{}")              # {class: {day: [subject/teacher per period]}}
    status: Mapped[str] = mapped_column(String(10), default="draft")   # draft | approved
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class DaftarShare(Base):
    """Absence alerts / a report card going to guardians: only her app tap decides; she sends each draft herself."""
    __tablename__ = "daftar_shares"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("dsh"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(12), default="")        # SH-001
    kind: Mapped[str] = mapped_column(String(14), default="absent")    # absent | report_card
    payload: Mapped[str] = mapped_column(Text, default="{}")
    hash: Mapped[str] = mapped_column(String(64), default="")
    status: Mapped[str] = mapped_column(String(10), default="waiting")  # waiting | shared | rejected | stale
    result: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
