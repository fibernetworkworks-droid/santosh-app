"""Imported by db.init_db so create_all makes the tables."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, now


class VoiceMember(Base):
    """A person whose voice Hoola knows. relation 'self' = the owner. Only a voice fingerprint is kept (encrypted),
    never the recording."""
    __tablename__ = "voice_members"
    id: Mapped[str] = mapped_column(String(24), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    name: Mapped[str] = mapped_column(String(40))
    relation: Mapped[str] = mapped_column(String(20))           # self | maa | papa | behen | bhai | ...
    gender: Mapped[str] = mapped_column(String(1), default="m")
    level: Mapped[str] = mapped_column(String(10), default="family")   # owner | trusted | family
    prints: Mapped[str] = mapped_column(Text)                   # encrypted JSON {model: [floats]}
    consent: Mapped[dict] = mapped_column(JSON, default=dict)   # code, transcript, time, seconds
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class VoiceEnrol(Base):
    """A one-time script with a random code that the person reads aloud themselves (their own permission)."""
    __tablename__ = "voice_enrols"
    id: Mapped[str] = mapped_column(String(24), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    name: Mapped[str] = mapped_column(String(40))
    relation: Mapped[str] = mapped_column(String(20))
    gender: Mapped[str] = mapped_column(String(1), default="m")
    level: Mapped[str] = mapped_column(String(10), default="family")
    code: Mapped[str] = mapped_column(String(8))
    script: Mapped[str] = mapped_column(Text)
    used: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class VoiceLock(Base):
    """off | on (strangers are treated like the owner) | strict (owner-only work needs the owner's voice)."""
    __tablename__ = "voice_locks"
    tenant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    mode: Mapped[str] = mapped_column(String(8), default="on")
