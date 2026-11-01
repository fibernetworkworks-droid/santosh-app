"""Tables of the Shodh Sahayak (research assistant, Shiksha suite Phase 4), prefix shodh_."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now


class ShodhSettings(Base):
    __tablename__ = "shodh_settings"
    tenant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    email: Mapped[str] = mapped_column(String(160), default="")       # contact email the open APIs ask for (OpenAlex / Unpaywall)
    s2_sealed: Mapped[str] = mapped_column(Text, default="")          # optional Semantic Scholar API key (app only, sealed)
    style: Mapped[str] = mapped_column(String(10), default="apa")     # apa | ieee | harvard
    seq: Mapped[str] = mapped_column(Text, default="{}")


class ShodhProject(Base):
    __tablename__ = "shodh_projects"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("sp"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(12), default="")        # SP-001
    title: Mapped[str] = mapped_column(String(300), default="")
    question: Mapped[str] = mapped_column(Text, default="")
    field: Mapped[str] = mapped_column(String(120), default="")
    status: Mapped[str] = mapped_column(String(10), default="open")    # open | closed
    log: Mapped[str] = mapped_column(Text, default="[]")               # searches + analyses (for the methods section)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class ShodhPaper(Base):
    """One work found through an official open API (never typed by the model): its identifiers are what make a
    citation real."""
    __tablename__ = "shodh_papers"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("spp"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    project_id: Mapped[str] = mapped_column(String(40), index=True)
    number: Mapped[str] = mapped_column(String(10), default="")        # P-001 inside the project
    doi: Mapped[str] = mapped_column(String(200), default="", index=True)
    title: Mapped[str] = mapped_column(Text, default="")
    authors: Mapped[str] = mapped_column(Text, default="[]")
    year: Mapped[int] = mapped_column(Integer, default=0)
    venue: Mapped[str] = mapped_column(String(300), default="")
    abstract: Mapped[str] = mapped_column(Text, default="")
    url: Mapped[str] = mapped_column(Text, default="")
    oa_url: Mapped[str] = mapped_column(Text, default="")
    citations: Mapped[int] = mapped_column(Integer, default=0)
    ids: Mapped[str] = mapped_column(Text, default="{}")               # {openalex, arxiv, pmid, s2}
    found_via: Mapped[str] = mapped_column(String(60), default="")
    status: Mapped[str] = mapped_column(String(10), default="found")   # found | included | excluded
    reason: Mapped[str] = mapped_column(Text, default="")
    summary: Mapped[str] = mapped_column(Text, default="{}")
    tags: Mapped[str] = mapped_column(Text, default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
