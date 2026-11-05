"""Tables for KAAN PACK (transcripts). Imported by db.init_db so create_all makes them.

One row = one finished transcription of one audio/video file. Words and speakers are separate
JSON columns so W1 (diarization) and W2 (streaming) can fill them without a migration on text.
Every column added later must be nullable or defaulted (the house rule for older databases).
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now


class KaanTranscript(Base):
    __tablename__ = "kaan_transcripts"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("kn"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    conversation_id: Mapped[str] = mapped_column(String(40), default="")
    source: Mapped[str] = mapped_column(String(20), default="file")          # file | mic | call (W2)
    file_id: Mapped[str] = mapped_column(String(64), default="")             # the mailbox file it came from
    file_name: Mapped[str] = mapped_column(String(300), default="")
    language: Mapped[str] = mapped_column(String(12), default="")            # detected or given (hi, mr, en...)
    task: Mapped[str] = mapped_column(String(20), default="transcribe")      # transcribe | translate (W4 uses it)
    model: Mapped[str] = mapped_column(String(24), default="")               # tiny/base/small/medium/turbo/large-v3
    duration_s: Mapped[float] = mapped_column(Float, default=0.0)
    n_segments: Mapped[int] = mapped_column(Integer, default=0)
    text: Mapped[str] = mapped_column(Text, default="")
    segments: Mapped[dict | None] = mapped_column(JSON, nullable=True)       # [{start, end, text}]
    words: Mapped[dict | None] = mapped_column(JSON, nullable=True)          # [{start, end, word}] (engine DTW)
    speakers: Mapped[dict | None] = mapped_column(JSON, nullable=True)       # W1 diarization
    status: Mapped[str] = mapped_column(String(12), default="ready")         # ready | empty | failed
    note: Mapped[str] = mapped_column(Text, default="")                      # honest line (silence-only, guards)
    pinned: Mapped[bool] = mapped_column(Boolean, default=False)             # survive the W6 retention sweep
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
