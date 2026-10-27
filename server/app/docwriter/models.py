"""Docs Sahayak tables (all prefixed docwriter_)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now


class DocSettings(Base):
    __tablename__ = "docwriter_settings"
    tenant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    product_name: Mapped[str] = mapped_column(String(160), default="")
    audience: Mapped[str] = mapped_column(String(300), default="")       # "dukaan ke staff, pehli baar smartphone"
    tone: Mapped[str] = mapped_column(String(200), default="")
    langs: Mapped[str] = mapped_column(Text, default='["en"]')
    glossary: Mapped[str] = mapped_column(Text, default="[]")            # [{term, avoid, note}]
    keep: Mapped[str] = mapped_column(Text, default="[]")                # words never translated (brand / feature names)
    rules: Mapped[str] = mapped_column(Text, default="[]")
    contact: Mapped[str] = mapped_column(String(300), default="")        # her business support line (allowed in docs)
    seq: Mapped[int] = mapped_column(Integer, default=0)


class DocProduct(Base):
    """What the docs are about: a Hoola-built app / site, her own live web app (ownership proved), her GitHub repo, her files."""
    __tablename__ = "docwriter_products"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("dp"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    kind: Mapped[str] = mapped_column(String(12))                       # hoola_app | hoola_site | web | github | files
    ref: Mapped[str] = mapped_column(String(300), default="")           # app / site id, base url, owner/repo, file ids
    name: Mapped[str] = mapped_column(String(160), default="")
    host: Mapped[str] = mapped_column(String(200), default="")
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    verify_token: Mapped[str] = mapped_column(String(40), default="")
    verify_how: Mapped[str] = mapped_column(String(20), default="")      # hoola | meta | file | dns
    version: Mapped[str] = mapped_column(String(60), default="")         # the product version the snapshot was taken at
    parts: Mapped[str] = mapped_column(Text, default="{}")              # {part_id: {label, hash, kind, facts, shot}}
    extra: Mapped[str] = mapped_column(Text, default="{}")              # openapi, releases, prs, readme ...
    auto_sync: Mapped[bool] = mapped_column(Boolean, default=True)
    checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class DocFlow(Base):
    """A recorded walk through her live product in the safe step language; re-run to re-shoot screenshots."""
    __tablename__ = "docwriter_flows"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("df"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    product_id: Mapped[str] = mapped_column(String(40), index=True)
    name: Mapped[str] = mapped_column(String(160), default="")
    steps: Mapped[str] = mapped_column(Text, default="[]")
    device: Mapped[str] = mapped_column(String(10), default="phone")
    shots: Mapped[str] = mapped_column(Text, default="[]")              # [{step, file, alt, phash, ok}]
    last_run: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error: Mapped[str] = mapped_column(Text, default="")


class DocDoc(Base):
    __tablename__ = "docwriter_docs"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("dd"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(16), default="")          # D-0001
    product_id: Mapped[str] = mapped_column(String(40), index=True, default="")
    kind: Mapped[str] = mapped_column(String(16), default="manual")
    lang: Mapped[str] = mapped_column(String(10), default="en")
    title: Mapped[str] = mapped_column(String(200), default="")
    sections: Mapped[str] = mapped_column(Text, default="[]")           # [{id, title, part, part_hash, body, shots, stale, why}]
    translation_of: Mapped[str] = mapped_column(String(40), default="")
    status: Mapped[str] = mapped_column(String(12), default="draft")    # draft | stale | ready | waiting | published
    version: Mapped[int] = mapped_column(Integer, default=1)
    product_version: Mapped[str] = mapped_column(String(60), default="")
    versions: Mapped[str] = mapped_column(Text, default="[]")
    checks: Mapped[str] = mapped_column(Text, default="{}")
    publish: Mapped[str] = mapped_column(Text, default="{}")            # pending card {dest, hash, opts} + done [{dest, url, at}]
    page_token: Mapped[str] = mapped_column(String(40), default="")
    page_html: Mapped[str] = mapped_column(Text, default="")
    conv: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class DocKey(Base):
    """Her GitHub token, sealed with the bazar vault; typed only in the app, never shown to the model."""
    __tablename__ = "docwriter_keys"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("dk"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    provider: Mapped[str] = mapped_column(String(20), default="github")
    sealed: Mapped[str] = mapped_column(Text, default="")
    label: Mapped[str] = mapped_column(String(80), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
