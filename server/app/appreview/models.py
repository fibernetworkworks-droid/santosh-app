"""Tables of the App Review Sahayak (all prefixed appreview_)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now


class AppReviewSettings(Base):
    __tablename__ = "appreview_settings"
    tenant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    stack: Mapped[str] = mapped_column(String(16), default="")             # android | flutter | react_native | web ("" = detect)
    kids: Mapped[bool] = mapped_column(Boolean, default=False)              # app is (also) for children under 18
    ios: Mapped[bool] = mapped_column(Boolean, default=False)               # there is an iPhone version too
    developer: Mapped[str] = mapped_column(String(120), default="")         # her developer's name (fix list header)
    gh_sealed: Mapped[str] = mapped_column(Text, default="")                # GitHub read-only token, sealed with the bazar vault
    gh_label: Mapped[str] = mapped_column(String(80), default="")
    seq: Mapped[int] = mapped_column(Integer, default=0)
    last_tick: Mapped[str] = mapped_column(String(10), default="")


class AppReviewFile(Base):
    """An APK / AAB / source ZIP she uploaded for review (kept in data/appreview/<tenant>/uploads, removed after 7 days)."""
    __tablename__ = "appreview_files"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("arf"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    name: Mapped[str] = mapped_column(String(200), default="")
    path: Mapped[str] = mapped_column(Text, default="")
    size: Mapped[int] = mapped_column(Integer, default=0)
    sha256: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class AppReview(Base):
    __tablename__ = "appreview_reviews"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("arv"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(16), default="")             # AR-0001
    kind: Mapped[str] = mapped_column(String(10), default="")               # apk | aab | source | repo | web
    target: Mapped[str] = mapped_column(String(200), index=True, default="")  # apk:<package> | repo:<o/r> | web:<host> | zip:<name>
    title: Mapped[str] = mapped_column(String(200), default="")
    stack: Mapped[str] = mapped_column(String(16), default="")
    score: Mapped[int] = mapped_column(Integer, default=0)
    facts: Mapped[dict] = mapped_column(JSON, default=dict)
    risks: Mapped[list] = mapped_column(JSON, default=list)
    compare: Mapped[dict] = mapped_column(JSON, default=dict)               # {previous, fixed:[...], still_open, new}
    limits: Mapped[list] = mapped_column(JSON, default=list)
    files: Mapped[list] = mapped_column(JSON, default=list)
    conv: Mapped[str] = mapped_column(String(40), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class AppReviewDomain(Base):
    """A website domain she proved is hers (DNS TXT or a file), so deeper passive checks may run on it."""
    __tablename__ = "appreview_domains"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("ard"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    host: Mapped[str] = mapped_column(String(200), index=True, default="")
    token: Mapped[str] = mapped_column(String(64), default="")
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    method: Mapped[str] = mapped_column(String(8), default="")              # dns | file
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class AppReviewHandoff(Base):
    """Fix list going to the Developer Sahayak (or her developer) - only after her tap on the card."""
    __tablename__ = "appreview_handoffs"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("arh"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    review_id: Mapped[str] = mapped_column(String(40), index=True, default="")
    to: Mapped[str] = mapped_column(String(16), default="devsahayak")       # devsahayak | developer
    keys: Mapped[list] = mapped_column(JSON, default=list)
    hash: Mapped[str] = mapped_column(String(64), default="")
    status: Mapped[str] = mapped_column(String(12), default="card")         # card | sent | rejected | failed
    result: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
