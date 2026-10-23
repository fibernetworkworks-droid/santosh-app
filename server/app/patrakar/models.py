"""Tables of the Patrakar Sahayak (all prefixed patrakar_). JSON kept in Text columns (pattern of banquet / interior)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now


class PatrakarSettings(Base):
    __tablename__ = "patrakar_settings"
    tenant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    outlet: Mapped[str] = mapped_column(String(160), default="")              # her portal / channel / paper
    kind: Mapped[str] = mapped_column(String(16), default="portal")           # portal | youtube | stringer | print | freelance
    reporter: Mapped[str] = mapped_column(String(120), default="")            # byline name
    place: Mapped[str] = mapped_column(String(120), default="")               # dateline
    language: Mapped[str] = mapped_column(String(16), default="hindi")
    contact: Mapped[str] = mapped_column(String(160), default="")             # what goes on right-of-reply letters
    gro_name: Mapped[str] = mapped_column(String(120), default="")            # grievance officer (IT Rules 2021, digital news)
    gro_contact: Mapped[str] = mapped_column(String(160), default="")
    style: Mapped[str] = mapped_column(Text, default="")                      # [{from, to}]
    avoid: Mapped[str] = mapped_column(Text, default="")                      # [words]
    rules: Mapped[str] = mapped_column(Text, default="")                      # her own desk rules (text)
    reply_days: Mapped[int] = mapped_column(Integer, default=2)
    elections: Mapped[str] = mapped_column(Text, default="")                  # [{area, phases:[{start,end}]}]
    corrections_url: Mapped[str] = mapped_column(String(300), default="")
    morning_time: Mapped[str] = mapped_column(String(5), default="09:00")
    last_morning: Mapped[str] = mapped_column(String(10), default="")
    st_seq: Mapped[int] = mapped_column(Integer, default=0)
    src_seq: Mapped[int] = mapped_column(Integer, default=0)
    rep_seq: Mapped[int] = mapped_column(Integer, default=0)
    cor_seq: Mapped[int] = mapped_column(Integer, default=0)
    gr_seq: Mapped[int] = mapped_column(Integer, default=0)


class PatrakarStory(Base):
    __tablename__ = "patrakar_stories"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("pk"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(16), default="")
    slug: Mapped[str] = mapped_column(String(160), default="")
    beat: Mapped[str] = mapped_column(String(60), default="")
    kind: Mapped[str] = mapped_column(String(16), default="news")
    status: Mapped[str] = mapped_column(String(16), default="pitch")
    pitch: Mapped[str] = mapped_column(Text, default="")
    notes: Mapped[str] = mapped_column(Text, default="")                     # her reporting notes (data)
    headline: Mapped[str] = mapped_column(Text, default="")
    dek: Mapped[str] = mapped_column(Text, default="")
    body: Mapped[str] = mapped_column(Text, default="")
    language: Mapped[str] = mapped_column(String(16), default="")
    deadline: Mapped[str] = mapped_column(String(16), default="")
    area: Mapped[str] = mapped_column(String(120), default="")              # constituency / district for election checks
    embargo: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    protect_sealed: Mapped[str] = mapped_column(Text, default="")            # sealed JSON list of names never to print
    sources: Mapped[str] = mapped_column(Text, default="")                   # [source ids]
    ai_media: Mapped[bool] = mapped_column(Boolean, default=False)
    sponsored_label: Mapped[bool] = mapped_column(Boolean, default=False)
    reply_state: Mapped[str] = mapped_column(String(16), default="")         # sent | answered | no_response | not_needed
    versions: Mapped[str] = mapped_column(Text, default="")
    checks: Mapped[str] = mapped_column(Text, default="")
    published: Mapped[str] = mapped_column(Text, default="")                 # {where, url, at, post_id}
    log: Mapped[str] = mapped_column(Text, default="")
    conv: Mapped[str] = mapped_column(String(40), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class PatrakarSource(Base):
    """A source. Her identity (name, phone, how to reach, private notes) is SEALED with the vault; everything the model or staff
    ever sees is the masked ref S-001 + beat + kind + terms."""
    __tablename__ = "patrakar_sources"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("ps"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    ref: Mapped[str] = mapped_column(String(12), default="")
    beat: Mapped[str] = mapped_column(String(60), default="")
    kind: Mapped[str] = mapped_column(String(16), default="other")
    terms: Mapped[str] = mapped_column(String(20), default="background")
    reliability: Mapped[int] = mapped_column(Integer, default=0)            # her 1-5 rating, 0 = not rated
    sealed: Mapped[str] = mapped_column(Text, default="")                   # vault-sealed JSON {name, phone, contact, notes}
    said: Mapped[str] = mapped_column(Text, default="")                     # [{text, off_record, at}] what they told her (quote pool)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class PatrakarClaim(Base):
    __tablename__ = "patrakar_claims"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("pc"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    story_id: Mapped[str] = mapped_column(String(40), index=True)
    text: Mapped[str] = mapped_column(Text, default="")
    kind: Mapped[str] = mapped_column(String(16), default="other")
    status: Mapped[str] = mapped_column(String(16), default="unchecked")
    evidence: Mapped[str] = mapped_column(Text, default="")                 # [{type web|source|document|her, url, title, quote, read_at}]
    note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class PatrakarInterview(Base):
    __tablename__ = "patrakar_interviews"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("pi"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    story_id: Mapped[str] = mapped_column(String(40), index=True)
    source_id: Mapped[str] = mapped_column(String(40), default="")
    who: Mapped[str] = mapped_column(String(120), default="")               # on-record speaker label (or the source ref)
    terms: Mapped[str] = mapped_column(String(20), default="on_record")
    consent: Mapped[bool] = mapped_column(Boolean, default=False)          # she says the person agreed to the recording
    file_id: Mapped[str] = mapped_column(String(64), default="")
    transcript: Mapped[str] = mapped_column(Text, default="")
    quotes: Mapped[str] = mapped_column(Text, default="")                   # [exact substrings]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class PatrakarReply(Base):
    __tablename__ = "patrakar_replies"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("pr"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    story_id: Mapped[str] = mapped_column(String(40), index=True)
    number: Mapped[str] = mapped_column(String(12), default="")
    party: Mapped[str] = mapped_column(String(160), default="")
    phone: Mapped[str] = mapped_column(String(20), default="")
    email: Mapped[str] = mapped_column(String(160), default="")
    allegations: Mapped[str] = mapped_column(Text, default="")
    questions: Mapped[str] = mapped_column(Text, default="")
    deadline: Mapped[str] = mapped_column(String(16), default="")
    letter: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(16), default="draft")       # draft | waiting | sent | answered | no_response
    response: Mapped[str] = mapped_column(Text, default="")                 # their words = data
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class PatrakarCorrection(Base):
    __tablename__ = "patrakar_corrections"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("pq"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    story_id: Mapped[str] = mapped_column(String(40), index=True)
    number: Mapped[str] = mapped_column(String(12), default="")
    kind: Mapped[str] = mapped_column(String(16), default="correction")
    wrong: Mapped[str] = mapped_column(Text, default="")
    right: Mapped[str] = mapped_column(Text, default="")
    line: Mapped[str] = mapped_column(Text, default="")
    why: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(16), default="draft")       # draft | waiting | published | rejected
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class PatrakarGrievance(Base):
    __tablename__ = "patrakar_grievances"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("pg"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(12), default="")
    story_id: Mapped[str] = mapped_column(String(40), default="")
    who: Mapped[str] = mapped_column(String(160), default="")
    contact: Mapped[str] = mapped_column(String(160), default="")
    text: Mapped[str] = mapped_column(Text, default="")                     # their words = data
    received: Mapped[str] = mapped_column(String(10), default="")
    due: Mapped[str] = mapped_column(String(10), default="")
    answer: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(16), default="open")        # open | waiting | answered | closed
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class PatrakarCard(Base):
    __tablename__ = "patrakar_cards"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("pd"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    kind: Mapped[str] = mapped_column(String(16), default="")
    target: Mapped[str] = mapped_column(String(40), default="")             # story / reply / correction / grievance id
    show: Mapped[str] = mapped_column(Text, default="")
    hash: Mapped[str] = mapped_column(String(64), default="")
    status: Mapped[str] = mapped_column(String(12), default="waiting")     # waiting | approved | rejected | stale
    asked_by: Mapped[str] = mapped_column(String(80), default="")
    reason: Mapped[str] = mapped_column(Text, default="")
    result: Mapped[str] = mapped_column(Text, default="")
    conv: Mapped[str] = mapped_column(String(40), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PatrakarAlert(Base):
    __tablename__ = "patrakar_alerts"
    key: Mapped[str] = mapped_column(String(200), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
