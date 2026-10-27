"""Community Sahayak tables (all prefixed samudaay_)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now


class SamBot(Base):
    """Her own platform bot (Telegram). Token sealed with the bazar vault; webhook secret kept only as a hash."""
    __tablename__ = "samudaay_bots"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("sbot"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    platform: Mapped[str] = mapped_column(String(16), default="telegram")
    token_enc: Mapped[str] = mapped_column(Text, default="")
    username: Mapped[str] = mapped_column(String(80), default="")
    bot_user_id: Mapped[str] = mapped_column(String(40), default="")
    hook_id: Mapped[str] = mapped_column(String(48), index=True, unique=True)
    secret_hash: Mapped[str] = mapped_column(String(64), default="")
    status: Mapped[str] = mapped_column(String(12), default="active")       # active | error | removed
    last_update_id: Mapped[int] = mapped_column(Integer, default=0)
    last_error: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class SamCommunity(Base):
    __tablename__ = "samudaay_communities"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("scom"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    platform: Mapped[str] = mapped_column(String(16), default="telegram")  # telegram | hoola | fake (tests)
    chat_id: Mapped[str] = mapped_column(String(80), index=True)           # Telegram chat id / Mandali gid
    name: Mapped[str] = mapped_column(String(160), default="")
    kind: Mapped[str] = mapped_column(String(16), default="group")
    language: Mapped[str] = mapped_column(String(12), default="hinglish")
    rules: Mapped[str] = mapped_column(Text, default="")
    welcome_on: Mapped[bool] = mapped_column(Boolean, default=True)
    faq_auto: Mapped[bool] = mapped_column(Boolean, default=True)
    join_mode: Mapped[str] = mapped_column(String(8), default="ask")       # ask | auto | off
    links_policy: Mapped[str] = mapped_column(String(8), default="new_no")  # allow | new_no | none
    links_allowed: Mapped[str] = mapped_column(Text, default="[]")
    ignore_words: Mapped[str] = mapped_column(Text, default="[]")         # words she said are fine here
    owner_ref: Mapped[str] = mapped_column(String(80), default="")         # her own user id on the platform
    report_day: Mapped[int] = mapped_column(Integer, default=0)            # 0 = Monday
    report_time: Mapped[str] = mapped_column(String(5), default="09:00")
    last_report: Mapped[str] = mapped_column(String(10), default="")
    status: Mapped[str] = mapped_column(String(10), default="active")     # active | paused | left
    bot_id: Mapped[str] = mapped_column(String(40), default="")
    cursor: Mapped[str] = mapped_column(String(40), default="")            # Hoola Mandali: last post time seen
    last_welcome_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class SamMember(Base):
    __tablename__ = "samudaay_members"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("smem"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    community_id: Mapped[str] = mapped_column(String(40), index=True)
    user_ref: Mapped[str] = mapped_column(String(200), index=True)
    name: Mapped[str] = mapped_column(String(120), default="")
    username: Mapped[str] = mapped_column(String(80), default="")
    joined_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    source: Mapped[str] = mapped_column(String(60), default="")            # invite link name | join_request | added | seen | hoola
    roles: Mapped[str] = mapped_column(Text, default="[]")                 # owner | admin | moderator | vip | member
    status: Mapped[str] = mapped_column(String(10), default="active")     # active | left | removed | banned | muted | forgotten
    muted_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    left_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    posts: Mapped[int] = mapped_column(Integer, default=0)
    last_post_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    warnings: Mapped[int] = mapped_column(Integer, default=0)
    welcomed: Mapped[bool] = mapped_column(Boolean, default=False)
    welcome_due: Mapped[bool] = mapped_column(Boolean, default=False)
    note: Mapped[str] = mapped_column(Text, default="")


class SamPost(Base):
    __tablename__ = "samudaay_posts"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("spst"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    community_id: Mapped[str] = mapped_column(String(40), index=True)
    member_id: Mapped[str] = mapped_column(String(40), index=True)
    msg_ref: Mapped[str] = mapped_column(String(80), default="")
    text: Mapped[str] = mapped_column(Text, default="")                   # masked, kept RETAIN_DAYS
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, index=True)
    flags: Mapped[str] = mapped_column(Text, default="[]")
    risk: Mapped[str] = mapped_column(String(8), default="")
    mood: Mapped[int] = mapped_column(Integer, default=0)
    topic: Mapped[str] = mapped_column(String(16), default="")
    question: Mapped[bool] = mapped_column(Boolean, default=False)
    faq_id: Mapped[str] = mapped_column(String(40), default="")
    answered_by: Mapped[str] = mapped_column(String(8), default="")       # faq | owner
    forwarded: Mapped[bool] = mapped_column(Boolean, default=False)
    deleted: Mapped[bool] = mapped_column(Boolean, default=False)


class SamFaq(Base):
    __tablename__ = "samudaay_faqs"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("sfaq"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    community_id: Mapped[str] = mapped_column(String(40), default="")      # "" = every community
    question: Mapped[str] = mapped_column(Text, default="")
    answer: Mapped[str] = mapped_column(Text, default="")
    keywords: Mapped[str] = mapped_column(Text, default="[]")
    language: Mapped[str] = mapped_column(String(12), default="")
    approved: Mapped[bool] = mapped_column(Boolean, default=False)
    uses: Mapped[int] = mapped_column(Integer, default=0)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class SamQuestion(Base):
    """A member's question the FAQ could not answer: she is asked once; similar ones are counted, not re-asked."""
    __tablename__ = "samudaay_questions"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("sq"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    community_id: Mapped[str] = mapped_column(String(40), index=True)
    post_id: Mapped[str] = mapped_column(String(40), default="")
    msg_ref: Mapped[str] = mapped_column(String(80), default="")
    member_id: Mapped[str] = mapped_column(String(40), default="")
    text: Mapped[str] = mapped_column(Text, default="")
    count: Mapped[int] = mapped_column(Integer, default=1)
    likely_faq: Mapped[str] = mapped_column(String(40), default="")
    status: Mapped[str] = mapped_column(String(10), default="open")       # open | answered | ignored
    answer: Mapped[str] = mapped_column(Text, default="")
    pinged: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    answered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class SamAlert(Base):
    __tablename__ = "samudaay_alerts"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("sal"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    community_id: Mapped[str] = mapped_column(String(40), index=True)
    kind: Mapped[str] = mapped_column(String(16), default="")   # scam spam abuse threat hate harassment pii misinfo flood raid negativity leaving complaints
    severity: Mapped[str] = mapped_column(String(8), default="low")
    member_id: Mapped[str] = mapped_column(String(40), default="")
    post_id: Mapped[str] = mapped_column(String(40), default="")
    title: Mapped[str] = mapped_column(Text, default="")
    evidence: Mapped[str] = mapped_column(Text, default="{}")
    suggest: Mapped[str] = mapped_column(Text, default="[]")
    key: Mapped[str] = mapped_column(String(160), index=True, default="")
    status: Mapped[str] = mapped_column(String(10), default="open")       # open | handled | dismissed
    note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    handled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class SamAction(Base):
    """Moderation / announcement waiting for HER tap. Runs only through decide(by_tap=True) from the app API."""
    __tablename__ = "samudaay_actions"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("sact"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    community_id: Mapped[str] = mapped_column(String(40), index=True)
    kind: Mapped[str] = mapped_column(String(12), default="")
    member_id: Mapped[str] = mapped_column(String(40), default="")
    post_id: Mapped[str] = mapped_column(String(40), default="")
    text: Mapped[str] = mapped_column(Text, default="")
    reason: Mapped[str] = mapped_column(Text, default="")
    hours: Mapped[int] = mapped_column(Integer, default=0)                # mute length
    alert_id: Mapped[str] = mapped_column(String(40), default="")
    hash: Mapped[str] = mapped_column(String(64), default="")
    status: Mapped[str] = mapped_column(String(10), default="pending")    # pending | done | rejected | failed | expired
    result: Mapped[str] = mapped_column(Text, default="")
    asked_by: Mapped[str] = mapped_column(String(60), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class SamTemplate(Base):
    __tablename__ = "samudaay_templates"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("stpl"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    community_id: Mapped[str] = mapped_column(String(40), default="")
    kind: Mapped[str] = mapped_column(String(10), default="welcome")
    language: Mapped[str] = mapped_column(String(12), default="hinglish")
    text: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(10), default="draft")      # draft | approved
    approved_hash: Mapped[str] = mapped_column(String(64), default="")
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class SamJoinRequest(Base):
    __tablename__ = "samudaay_join_requests"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("sjr"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    community_id: Mapped[str] = mapped_column(String(40), index=True)
    user_ref: Mapped[str] = mapped_column(String(200), default="")
    name: Mapped[str] = mapped_column(String(120), default="")
    username: Mapped[str] = mapped_column(String(80), default="")
    bio: Mapped[str] = mapped_column(Text, default="")
    flags: Mapped[str] = mapped_column(Text, default="[]")
    status: Mapped[str] = mapped_column(String(10), default="pending")    # pending | approved | declined | expired
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class SamLog(Base):
    """Joins, leaves, removals, bans, approvals - for growth numbers and the reason log."""
    __tablename__ = "samudaay_log"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("slog"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    community_id: Mapped[str] = mapped_column(String(40), index=True)
    member_id: Mapped[str] = mapped_column(String(40), default="")
    kind: Mapped[str] = mapped_column(String(16), default="")   # join leave removed banned muted unbanned deleted announce warn answer welcome
    note: Mapped[str] = mapped_column(Text, default="")
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, index=True)
