"""One Computer Operator job: a task on websites that Hoola does for the owner in its own browser."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now


class OperatorTask(Base):
    __tablename__ = "operator_tasks"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: new_id("op"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    conversation_id: Mapped[str] = mapped_column(String(64), default="")
    task: Mapped[str] = mapped_column(Text, default="")
    start_url: Mapped[str] = mapped_column(Text, default="")
    files: Mapped[str] = mapped_column(Text, default="[]")          # owner file ids she gave for this job (uploads)
    status: Mapped[str] = mapped_column(String(20), default="queued")   # queued|running|waiting|done|failed|stopped|cancelled
    stage: Mapped[str] = mapped_column(Text, default="")
    steps: Mapped[int] = mapped_column(Integer, default=0)
    url: Mapped[str] = mapped_column(Text, default="")
    title: Mapped[str] = mapped_column(Text, default="")
    pending: Mapped[str] = mapped_column(Text, default="")          # JSON of the request waiting for the owner
    summary: Mapped[str] = mapped_column(Text, default="")
    proof: Mapped[str] = mapped_column(Text, default="[]")          # reference numbers, confirmation lines
    outputs: Mapped[str] = mapped_column(Text, default="[]")        # downloaded files -> owner file ids
    recipe: Mapped[str] = mapped_column(String(120), default="")
    log: Mapped[str] = mapped_column(Text, default="[]")            # the last steps (plain words, no values)
    error: Mapped[str] = mapped_column(Text, default="")
    created_by: Mapped[str] = mapped_column(String(64), default="owner")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)
