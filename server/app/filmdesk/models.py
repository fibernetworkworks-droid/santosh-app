"""Tables of the Film Desk (all prefixed filmdesk_). JSON kept in Text columns (pattern of banquet / interior)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now


class FilmSettings(Base):
    __tablename__ = "filmdesk_settings"
    tenant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    banner: Mapped[str] = mapped_column(String(160), default="")          # production house / banner name
    producer: Mapped[str] = mapped_column(String(120), default="")
    email: Mapped[str] = mapped_column(String(120), default="")
    phone: Mapped[str] = mapped_column(String(20), default="")
    language: Mapped[str] = mapped_column(String(20), default="Hindi")
    month_budget_inr: Mapped[float | None] = mapped_column(Float, nullable=True)   # her own cap on AI shots per month
    morning_time: Mapped[str] = mapped_column(String(5), default="09:00")
    last_morning: Mapped[str] = mapped_column(String(10), default="")
    rules: Mapped[str] = mapped_column(Text, default="")
    proj_seq: Mapped[int] = mapped_column(Integer, default=0)
    person_seq: Mapped[int] = mapped_column(Integer, default=0)
    right_seq: Mapped[int] = mapped_column(Integer, default=0)


class FilmProject(Base):
    __tablename__ = "filmdesk_projects"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("fp"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(12), default="")            # F-0001
    title: Mapped[str] = mapped_column(String(160), default="")
    logline: Mapped[str] = mapped_column(Text, default="")
    genre: Mapped[str] = mapped_column(String(60), default="")
    fmt: Mapped[str] = mapped_column(String(20), default="short")
    language: Mapped[str] = mapped_column(String(20), default="Hindi")
    aspect: Mapped[str] = mapped_column(String(6), default="16:9")
    style: Mapped[str] = mapped_column(String(20), default="cinematic")
    runtime_s: Mapped[int | None] = mapped_column(Integer, nullable=True)
    targets: Mapped[str] = mapped_column(Text, default="[]")
    budget_inr: Mapped[float | None] = mapped_column(Float, nullable=True)   # HER cap for AI shots on this film
    status: Mapped[str] = mapped_column(String(16), default="idea")
    script: Mapped[str] = mapped_column(Text, default="")
    script_versions: Mapped[str] = mapped_column(Text, default="[]")
    scenes: Mapped[str] = mapped_column(Text, default="[]")
    shots: Mapped[str] = mapped_column(Text, default="[]")
    cast: Mapped[str] = mapped_column(Text, default="{}")                  # character -> {person, kind fictional|real, description}
    studio_project: Mapped[str] = mapped_column(String(80), default="")
    studio_shots: Mapped[str] = mapped_column(Text, default="[]")          # shot ids pushed to the studio (for checks)
    rating: Mapped[str] = mapped_column(String(6), default="")             # OTT self-classification
    descriptors: Mapped[str] = mapped_column(Text, default="")
    cbfc: Mapped[str] = mapped_column(Text, default="{}")                  # {category, number, date, applied}
    ticks: Mapped[str] = mapped_column(Text, default="{}")                 # manual checklist ticks
    released: Mapped[str] = mapped_column(Text, default="{}")
    log: Mapped[str] = mapped_column(Text, default="[]")
    conv: Mapped[str] = mapped_column(String(40), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class FilmPerson(Base):
    """Consent register: one row per real (or fictional-but-voiced) person; consent JSON is the recorded proof trail."""
    __tablename__ = "filmdesk_people"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("fpe"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(12), default="")            # P-001
    name: Mapped[str] = mapped_column(String(120), default="")
    role: Mapped[str] = mapped_column(String(16), default="actor")
    phone: Mapped[str] = mapped_column(String(15), default="")
    email: Mapped[str] = mapped_column(String(120), default="")
    real: Mapped[bool] = mapped_column(Boolean, default=True)
    public_figure: Mapped[bool] = mapped_column(Boolean, default=False)
    minor: Mapped[bool] = mapped_column(Boolean, default=False)
    consent: Mapped[str] = mapped_column(Text, default="{}")              # {status, how, uses, until, projects, proof, guardian, at, history}
    photo_files: Mapped[str] = mapped_column(Text, default="[]")         # her file_ids of reference photos (copied by studio)
    notes: Mapped[str] = mapped_column(Text, default="")
    forgotten: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class FilmRight(Base):
    """Rights register: music / songs / voices / stock / fonts / lyrics / footage used in a film."""
    __tablename__ = "filmdesk_rights"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("fr"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(12), default="")            # R-001
    project_id: Mapped[str] = mapped_column(String(40), default="", index=True)
    kind: Mapped[str] = mapped_column(String(12), default="music")
    title: Mapped[str] = mapped_column(String(160), default="")
    owner: Mapped[str] = mapped_column(String(160), default="")
    licence: Mapped[str] = mapped_column(String(16), default="")
    sync: Mapped[bool] = mapped_column(Boolean, default=False)
    platforms: Mapped[str] = mapped_column(Text, default="[]")
    territory: Mapped[str] = mapped_column(String(60), default="")
    until: Mapped[str] = mapped_column(String(10), default="")
    fee_inr: Mapped[float | None] = mapped_column(Float, nullable=True)   # HER number (what she paid / agreed)
    isrc: Mapped[str] = mapped_column(String(15), default="")
    proof: Mapped[str] = mapped_column(Text, default="{}")                # {path, name, sha256}
    notes: Mapped[str] = mapped_column(Text, default="")


class FilmCard(Base):
    __tablename__ = "filmdesk_cards"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("fc"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    project_id: Mapped[str] = mapped_column(String(40), default="", index=True)
    kind: Mapped[str] = mapped_column(String(12), default="message")     # message | release
    status: Mapped[str] = mapped_column(String(10), default="waiting")
    show: Mapped[str] = mapped_column(Text, default="{}")
    hash: Mapped[str] = mapped_column(String(64), default="")
    asked_by: Mapped[str] = mapped_column(String(80), default="")
    reason: Mapped[str] = mapped_column(Text, default="")
    result: Mapped[str] = mapped_column(Text, default="{}")
    conv: Mapped[str] = mapped_column(String(40), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class FilmAlert(Base):
    __tablename__ = "filmdesk_alerts"
    key: Mapped[str] = mapped_column(String(200), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    at: Mapped[datetime] = mapped_column(DateTime, default=now)
