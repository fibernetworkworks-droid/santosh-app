"""Tables for Hoola Notebook (NotebookLM / Gemini Notebook style). Imported by db.init_db so create_all makes them.

v0.155: every column added to an older table is nullable or has a default (old databases get it via
db._add_missing_columns). New tables: notebook_chat (saved chat history), notebook_outputs (Studio items)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Integer, String, Text
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
    # v0.155
    chat_config: Mapped[dict | None] = mapped_column(JSON, nullable=True)   # {goal, custom, length, language}
    guide: Mapped[dict | None] = mapped_column(JSON, nullable=True)         # {key, overview, questions}
    color: Mapped[str | None] = mapped_column(String(12), nullable=True)


class NotebookSource(Base):
    __tablename__ = "notebook_sources"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("src"))
    notebook_id: Mapped[str] = mapped_column(String(40), index=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    kind: Mapped[str] = mapped_column(String(12))   # text | web | file | drive | email | sheet | youtube | image | audio | note | research
    title: Mapped[str] = mapped_column(String(300), default="")
    origin: Mapped[str] = mapped_column(Text, default="")    # url / Drive ref / email id / file name
    text: Mapped[str] = mapped_column(Text, default="")
    chars: Mapped[int] = mapped_column(Integer, default=0)
    summary: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(12), default="ready")
    note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    # v0.155
    enabled: Mapped[bool | None] = mapped_column(Boolean, nullable=True)    # None = on (old rows)
    guide: Mapped[dict | None] = mapped_column(JSON, nullable=True)         # {summary, topics, questions}
    src_ref: Mapped[dict | None] = mapped_column(JSON, nullable=True)       # how to read it again (drive / sheet / url)


class NotebookNote(Base):
    """Her own notes, saved chat answers, and (before v0.155) the things Hoola wrote from the sources."""
    __tablename__ = "notebook_notes"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("nbn"))
    notebook_id: Mapped[str] = mapped_column(String(40), index=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    kind: Mapped[str] = mapped_column(String(16))       # user | answer | (old) summary / study_guide / ...
    title: Mapped[str] = mapped_column(String(300), default="")
    content: Mapped[str] = mapped_column(Text, default="")
    citations: Mapped[list | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class NotebookAudio(Base):
    """Before v0.155 audio overviews lived here (their files expired with the 24 h phone files). Kept for old rows."""
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


class NotebookChat(Base):
    """Saved chat history per notebook (NotebookLM keeps it across sessions; she can clear it)."""
    __tablename__ = "notebook_chat"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("nbc"))
    notebook_id: Mapped[str] = mapped_column(String(40), index=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    role: Mapped[str] = mapped_column(String(10))        # user | assistant
    text: Mapped[str] = mapped_column(Text, default="")
    citations: Mapped[list | None] = mapped_column(JSON, nullable=True)
    meta: Mapped[dict | None] = mapped_column(JSON, nullable=True)   # {followups, steps, found}
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class NotebookOutput(Base):
    """One Studio item: audio / video overview, slide deck, infographic, mind map, report, flashcards, quiz, data
    table, deep research. Files live in data/notebook/<tenant>/<notebook>/<output>/ (kept, not the 24 h phone files)."""
    __tablename__ = "notebook_outputs"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("nbo"))
    notebook_id: Mapped[str] = mapped_column(String(40), index=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    conversation_id: Mapped[str] = mapped_column(String(40), default="")
    kind: Mapped[str] = mapped_column(String(16))
    title: Mapped[str] = mapped_column(String(300), default="")
    status: Mapped[str] = mapped_column(String(12), default="queued")     # queued | working | ready | failed
    stage: Mapped[str] = mapped_column(String(200), default="")
    pct: Mapped[int] = mapped_column(Integer, default=0)
    options: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    files: Mapped[dict | None] = mapped_column(JSON, nullable=True)       # {name: {size, kind}}
    error: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
