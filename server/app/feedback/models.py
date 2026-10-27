"""Feedback Sahayak tables (all prefixed `feedback_`)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now


class FbSettings(Base):
    __tablename__ = "feedback_settings"
    tenant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    business: Mapped[str] = mapped_column(String(160), default="")
    phone: Mapped[str] = mapped_column(String(20), default="")            # business phone allowed in public replies
    email: Mapped[str] = mapped_column(String(160), default="")
    sign_off: Mapped[str] = mapped_column(String(120), default="")        # "- Team Annapurna"
    language: Mapped[str] = mapped_column(String(12), default="hinglish")  # survey + default reply language
    period_days: Mapped[int] = mapped_column(Integer, default=30)
    avg_order_value: Mapped[float] = mapped_column(Float, default=0.0)    # her number; 0 = no rupee figure
    orders_per_year: Mapped[float] = mapped_column(Float, default=0.0)    # her number; 0 = one order only
    review_link: Mapped[str] = mapped_column(String(400), default="")     # her Google review link, shown to EVERY respondent
    reply_rules: Mapped[str] = mapped_column(Text, default="[]")          # her lines for replies
    report_day: Mapped[int] = mapped_column(Integer, default=1)           # day of month for the monthly report
    last_report: Mapped[str] = mapped_column(String(7), default="")       # YYYY-MM sent
    last_check: Mapped[str] = mapped_column(String(10), default="")       # daily spike / sync check
    seq: Mapped[int] = mapped_column(Integer, default=0)


class FbItem(Base):
    """One review / survey answer / customer message / call note."""
    __tablename__ = "feedback_items"
    __table_args__ = (UniqueConstraint("tenant_id", "ext_id", name="uq_feedback_item"),)
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("fb"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    ext_id: Mapped[str] = mapped_column(String(200))                      # source + its own id (dedupe)
    source: Mapped[str] = mapped_column(String(20), default="text", index=True)
    author: Mapped[str] = mapped_column(String(120), default="")
    author_key: Mapped[str] = mapped_column(String(24), default="")      # hashed identity (phone / reviewer name)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, index=True)
    stars: Mapped[float | None] = mapped_column(Float, nullable=True)     # 1..5
    score: Mapped[int | None] = mapped_column(Integer, nullable=True)     # 0..10 (NPS)
    text: Mapped[str] = mapped_column(Text, default="")
    lang: Mapped[str] = mapped_column(String(10), default="")
    sentiment: Mapped[float] = mapped_column(Float, default=0.0)
    label: Mapped[str] = mapped_column(String(8), default="neu")          # pos | neg | neu | mixed
    aspects: Mapped[str] = mapped_column(Text, default="[]")              # [{aspect, pol}]
    themes: Mapped[str] = mapped_column(Text, default="[]")               # ["delivery:neg", ...]
    urgent: Mapped[bool] = mapped_column(Boolean, default=False)
    flags: Mapped[str] = mapped_column(Text, default="[]")                # suspicious signals [{kind, why}]
    amount: Mapped[float | None] = mapped_column(Float, nullable=True)   # order value when the export has it
    product: Mapped[str] = mapped_column(String(160), default="")
    place: Mapped[str] = mapped_column(String(120), default="")           # outlet / branch
    reply: Mapped[str] = mapped_column(Text, default="")                  # reply already on the platform
    meta: Mapped[str] = mapped_column(Text, default="{}")
    ai: Mapped[bool] = mapped_column(Boolean, default=False)              # model refined the aspects
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class FbTheme(Base):
    """Her notes on a theme: own name, 'theek kiya' date (to measure before / after), note."""
    __tablename__ = "feedback_themes"
    __table_args__ = (UniqueConstraint("tenant_id", "key", name="uq_feedback_theme"),)
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("ft"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    key: Mapped[str] = mapped_column(String(80))
    label: Mapped[str] = mapped_column(String(120), default="")
    fixed_on: Mapped[str] = mapped_column(String(10), default="")
    note: Mapped[str] = mapped_column(Text, default="")
    ignored: Mapped[bool] = mapped_column(Boolean, default=False)


class FbReply(Base):
    """A reply draft to one review. Public only after HER tap (decide) with the hash of the exact text."""
    __tablename__ = "feedback_replies"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("fr"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    item_id: Mapped[str] = mapped_column(String(40), index=True)
    text: Mapped[str] = mapped_column(Text, default="")
    lang: Mapped[str] = mapped_column(String(10), default="")
    status: Mapped[str] = mapped_column(String(10), default="draft")       # draft | approved | posted | rejected
    hash: Mapped[str] = mapped_column(String(20), default="")
    problems: Mapped[str] = mapped_column(Text, default="[]")
    where: Mapped[str] = mapped_column(String(20), default="")            # google_api | copy
    error: Mapped[str] = mapped_column(Text, default="")
    conv: Mapped[str] = mapped_column(String(40), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class FbSurvey(Base):
    __tablename__ = "feedback_surveys"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("fs"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    title: Mapped[str] = mapped_column(String(160), default="")
    kind: Mapped[str] = mapped_column(String(6), default="nps")            # nps | csat
    question: Mapped[str] = mapped_column(Text, default="")
    follow_up: Mapped[str] = mapped_column(Text, default="")
    language: Mapped[str] = mapped_column(String(12), default="hinglish")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    responses: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class FbAlert(Base):
    __tablename__ = "feedback_alerts"
    __table_args__ = (UniqueConstraint("tenant_id", "key", name="uq_feedback_alert"),)
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("fa"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    key: Mapped[str] = mapped_column(String(120))
    kind: Mapped[str] = mapped_column(String(12), default="")              # urgent | spike | rating
    text: Mapped[str] = mapped_column(Text, default="")
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, index=True)


class FbGoogle(Base):
    """Her Google Business Profile sign-in (scope business.manage), tokens encrypted."""
    __tablename__ = "feedback_google"
    tenant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    address: Mapped[str] = mapped_column(String(200), default="")
    access_token_enc: Mapped[str | None] = mapped_column(Text, nullable=True)
    refresh_token_enc: Mapped[str | None] = mapped_column(Text, nullable=True)
    expiry: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    location: Mapped[str] = mapped_column(String(160), default="")         # accounts/1/locations/2
    location_title: Mapped[str] = mapped_column(String(200), default="")
    status: Mapped[str] = mapped_column(String(10), default="")
    last_error: Mapped[str] = mapped_column(Text, default="")
    last_sync: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
