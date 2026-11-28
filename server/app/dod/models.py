"""HOOLA DOD tables: one coworker profile per account, her tasks, her OpenClaw gateway."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now


class DodProfile(Base):
    """Her coworker: separate from the main Hoola avatar (that one is untouched)."""
    __tablename__ = "dod_profiles"
    tenant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(40), default="")
    look: Mapped[str] = mapped_column(String(16), default="")
    gender: Mapped[str] = mapped_column(String(2), default="f")
    voice: Mapped[str] = mapped_column(String(24), default="warm")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class DodTask(Base):
    """One piece of work. status: queued | working | needs_you | done | failed | stopped."""
    __tablename__ = "dod_tasks"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("dod"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    title: Mapped[str] = mapped_column(String(160), default="")
    ask: Mapped[str] = mapped_column(Text, default="")
    kind: Mapped[str] = mapped_column(String(16), default="task")      # task | browser | code | long
    status: Mapped[str] = mapped_column(String(16), default="queued", index=True)
    steps: Mapped[str] = mapped_column(Text, default="[]")             # JSON list of {at, title, detail, state}
    files: Mapped[str] = mapped_column(Text, default="[]")             # JSON list of {name, size, path}
    notes: Mapped[str] = mapped_column(Text, default="[]")             # her words while it works, not yet read
    question: Mapped[str] = mapped_column(Text, default="")            # JSON: the open question / approval
    reply: Mapped[str] = mapped_column(Text, default="")               # what the coworker said at the end
    thought: Mapped[str] = mapped_column(Text, default="")             # the latest words it is writing
    response_id: Mapped[str] = mapped_column(String(80), default="")   # OpenClaw's last response id (continuation)
    rounds: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, index=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class DodGateway(Base):
    """Her own OpenClaw Gateway (one per user - OpenClaw's own trust rule). The token and her model key are sealed."""
    __tablename__ = "dod_gateways"
    tenant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    container: Mapped[str] = mapped_column(String(64), default="")
    port: Mapped[int] = mapped_column(Integer, default=0)
    token_enc: Mapped[str] = mapped_column(Text, default="")
    key_enc: Mapped[str] = mapped_column(Text, default="")              # her own OpenRouter key (spending limit)
    key_hash: Mapped[str] = mapped_column(String(80), default="")       # OpenRouter's id for that key
    state: Mapped[str] = mapped_column(String(16), default="none")      # none | starting | awake | asleep | failed
    error: Mapped[str] = mapped_column(Text, default="")
    image: Mapped[str] = mapped_column(String(160), default="")
    mcp_enc: Mapped[str] = mapped_column(Text, default="")              # her coworker's key to Hoola's MCP door (sealed)
    mcp_hash: Mapped[str] = mapped_column(String(80), default="", index=True)
    subnet: Mapped[str] = mapped_column(String(40), default="")         # her container network: the MCP door answers only it
    usage_seen: Mapped[float] = mapped_column(Float, default=0.0)       # her key's usage already charged as credits
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


def ensure_tables() -> None:
    """Self-heal: create the three tables when an older database lacks them."""
    from .. import db
    eng = db._engine
    if eng is not None:
        Base.metadata.create_all(eng, tables=[DodProfile.__table__, DodTask.__table__, DodGateway.__table__])
