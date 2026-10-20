"""Imported by db.init_db so create_all makes the tables."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, now


class VoiceProfile(Base):
    """A voice an avatar can speak in. kind: own (the owner's voice, consent recorded) | design (made from words)."""
    __tablename__ = "voice_profiles"
    id: Mapped[str] = mapped_column(String(24), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    kind: Mapped[str] = mapped_column(String(10))
    name: Mapped[str] = mapped_column(String(60))
    gender: Mapped[str] = mapped_column(String(1), default="m")
    lang: Mapped[str] = mapped_column(String(10), default="hi")
    status: Mapped[str] = mapped_column(String(12), default="ready")       # ready | failed | deleted
    worker_voice_id: Mapped[str] = mapped_column(String(64))
    seconds: Mapped[float] = mapped_column(Float, default=0.0)
    description: Mapped[str] = mapped_column(Text, default="")
    consent: Mapped[dict] = mapped_column(JSON, default=dict)                # own voice: code, transcript, time
    sample_file: Mapped[str] = mapped_column(String(300), default="")       # encrypted reference recording
    error: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class VoiceConsent(Base):
    """A one-time script with a random code. The owner reads it aloud in the app; that recording is both the
    proof of consent and the voice sample."""
    __tablename__ = "voice_consents"
    id: Mapped[str] = mapped_column(String(24), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    code: Mapped[str] = mapped_column(String(8))
    script: Mapped[str] = mapped_column(Text)
    gender: Mapped[str] = mapped_column(String(1), default="m")
    used: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
