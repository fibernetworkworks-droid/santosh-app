"""Tables for Santosh Notebook. Imported by db.init_db so create_all makes them."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now


class Notebook(Base):
    __tablename__ = "notebooks"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("nb"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    conversation_id: Mapped[str] = mapped_column(String(40), default="")
    title: Mapped[str] = mapped_column(String(200), default="Notebook")
    emoji: Mapped[str] = mapped_column(String(8), default="📒")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class NotebookSource(Base):
    __tablename__ = "notebook_sources"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("src"))
    notebook_id: Mapped[str] = mapped_column(String(40), index=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    kind: Mapped[str] = mapped_column(String(12))            # text | web | file | drive | email | sheet | youtube
    title: Mapped[str] = mapped_column(String(300), default="")
    origin: Mapped[str] = mapped_column(Text, default="")    # url / Drive ref / email id / file name
    text: Mapped[str] = mapped_column(Text, default="")
    chars: Mapped[int] = mapped_column(Integer, default=0)
    summary: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(12), default="ready")
    note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class NotebookNote(Base):
    """Something Santosh made from the sources (study guide, briefing, FAQ, timeline, mind map, quiz, saved answer)."""
    __tablename__ = "notebook_notes"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("nbn"))
    notebook_id: Mapped[str] = mapped_column(String(40), index=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    kind: Mapped[str] = mapped_column(String(16))
    title: Mapped[str] = mapped_column(String(300), default="")
    content: Mapped[str] = mapped_column(Text, default="")
    citations: Mapped[list | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class NotebookAudio(Base):
    __tablename__ = "notebook_audio"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("nba"))
    notebook_id: Mapped[str] = mapped_column(String(40), index=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    conversation_id: Mapped[str] = mapped_column(String(40), default="")
    language: Mapped[str] = mapped_column(String(12), default="hinglish")
    style: Mapped[str] = mapped_column(String(16), default="deep_dive")
    focus: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(12), default="writing")   # writing | speaking | ready | failed
    script: Mapped[str] = mapped_column(Text, default="")
    file_id: Mapped[str] = mapped_column(String(40), default="")
    seconds: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
