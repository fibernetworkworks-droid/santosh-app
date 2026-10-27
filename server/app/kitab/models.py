"""Tables of the Kitab Sahayak (all prefixed kitab_). JSON kept in Text columns (pattern of banquet / interior)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now


class KitabSettings(Base):
    __tablename__ = "kitab_settings"
    tenant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(160), default="")            # her name / pen name
    role: Mapped[str] = mapped_column(String(16), default="author")       # author | editor | publisher
    imprint: Mapped[str] = mapped_column(String(160), default="")         # her publishing imprint (if she publishes)
    address: Mapped[str] = mapped_column(Text, default="")
    phone: Mapped[str] = mapped_column(String(20), default="")
    email: Mapped[str] = mapped_column(String(120), default="")
    gstin: Mapped[str] = mapped_column(String(15), default="")
    sac: Mapped[str] = mapped_column(String(10), default="")              # her CA's SAC for editing services (blank = ask CA)
    upi_id: Mapped[str] = mapped_column(String(80), default="")
    lang: Mapped[str] = mapped_column(String(8), default="")              # hi | mr | en (default language)
    rate: Mapped[str] = mapped_column(Text, default="")                   # freelance editing rates {per: word|page|hour|flat, amount, pass}
    follow_days: Mapped[int] = mapped_column(Integer, default=90)         # submission follow-up after N days
    morning_time: Mapped[str] = mapped_column(String(5), default="09:00")
    last_morning: Mapped[str] = mapped_column(String(10), default="")
    rules: Mapped[str] = mapped_column(Text, default="")
    book_seq: Mapped[int] = mapped_column(Integer, default=0)
    sug_seq: Mapped[int] = mapped_column(Integer, default=0)
    perm_seq: Mapped[int] = mapped_column(Integer, default=0)
    sub_seq: Mapped[int] = mapped_column(Integer, default=0)
    inv_seq: Mapped[int] = mapped_column(Integer, default=0)


class KitabBook(Base):
    __tablename__ = "kitab_books"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("kb"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(12), default="")          # K-001
    title: Mapped[str] = mapped_column(String(240), default="")
    subtitle: Mapped[str] = mapped_column(String(240), default="")
    author: Mapped[str] = mapped_column(String(160), default="")
    lang: Mapped[str] = mapped_column(String(8), default="en")
    genre: Mapped[str] = mapped_column(String(60), default="")
    kind: Mapped[str] = mapped_column(String(16), default="fiction")     # fiction | nonfiction | poetry | academic | children | translation
    status: Mapped[str] = mapped_column(String(16), default="drafting")  # drafting | editing | submission | production | published | done
    mine: Mapped[bool] = mapped_column(Boolean, default=True)            # her own book (False = a client's book she edits)
    target_words: Mapped[int | None] = mapped_column(Integer, nullable=True)
    deadline: Mapped[str] = mapped_column(String(10), default="")
    published_on: Mapped[str] = mapped_column(String(10), default="")
    blurb: Mapped[str] = mapped_column(Text, default="")                  # her facts for pitches
    facts: Mapped[str] = mapped_column(Text, default="")                  # {hook, bio, comps, audience, publisher, price, edition, printer, year}
    style: Mapped[str] = mapped_column(Text, default="")                  # style sheet JSON
    isbns: Mapped[str] = mapped_column(Text, default="")                  # {format: isbn}
    checklist: Mapped[str] = mapped_column(Text, default="")              # {item: {status, ref, at}}
    contract: Mapped[str] = mapped_column(Text, default="")               # {publisher, rates, advance, period_months, notes}
    client: Mapped[str] = mapped_column(Text, default="")                 # freelance: {name, phone, email, rate}
    rights: Mapped[str] = mapped_column(Text, default="")                 # translation / adaptation rights note
    log: Mapped[str] = mapped_column(Text, default="")
    conv: Mapped[str] = mapped_column(String(40), default="")
    forgotten: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class KitabChapter(Base):
    __tablename__ = "kitab_chapters"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("kc"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    book_id: Mapped[str] = mapped_column(String(40), index=True)
    n: Mapped[int] = mapped_column(Integer, default=1)
    title: Mapped[str] = mapped_column(String(240), default="")
    text: Mapped[str] = mapped_column(Text, default="")                   # HER accepted text (only she / her accepted suggestions change it)
    words: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(16), default="draft")     # draft | editing | edited | final
    versions: Mapped[str] = mapped_column(Text, default="")               # [{at, why, text}] last 20
    translations: Mapped[str] = mapped_column(Text, default="")           # [{lang, doc, at}] Lekhak docs
    letter: Mapped[str] = mapped_column(Text, default="")                 # developmental editor's letter (her reading, not a change)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class KitabSuggestion(Base):
    __tablename__ = "kitab_suggestions"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("ks"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    chapter_id: Mapped[str] = mapped_column(String(40), index=True)
    number: Mapped[str] = mapped_column(String(12), default="")          # S-0001
    pass_: Mapped[str] = mapped_column("pass", String(14), default="proof")  # developmental | line | copy | proof
    kind: Mapped[str] = mapped_column(String(16), default="spelling")
    src: Mapped[str] = mapped_column(Text, default="")                    # exact text in her chapter
    dst: Mapped[str | None] = mapped_column(Text, nullable=True)          # None = a query / comment (no change)
    why: Mapped[str] = mapped_column(Text, default="")
    ctx: Mapped[str] = mapped_column(Text, default="")                    # a few characters before src (to find the right place)
    at: Mapped[int] = mapped_column(Integer, default=0)
    by: Mapped[str] = mapped_column(String(10), default="code")          # code | model
    status: Mapped[str] = mapped_column(String(10), default="open")      # open | accepted | rejected | stale | resolved
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class KitabPermission(Base):
    __tablename__ = "kitab_permissions"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("kp"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    book_id: Mapped[str] = mapped_column(String(40), index=True)
    number: Mapped[str] = mapped_column(String(12), default="")          # P-001
    chapter: Mapped[str] = mapped_column(String(240), default="")
    excerpt: Mapped[str] = mapped_column(Text, default="")                # the first words (never the whole work)
    words: Mapped[int] = mapped_column(Integer, default=0)
    kind: Mapped[str] = mapped_column(String(14), default="prose")       # prose | poem | lyrics | image | map | epigraph | translation | other
    source: Mapped[str] = mapped_column(Text, default="")                 # work, author
    holder: Mapped[str] = mapped_column(Text, default="")                 # rights holder (publisher / estate / lyricist's publisher)
    contact: Mapped[str] = mapped_column(Text, default="")                # email / address she gives
    death_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(14), default="needed")    # needed | asked | granted | refused | fair_dealing | public_domain | own | removed
    fee: Mapped[float | None] = mapped_column(Float, nullable=True)
    credit: Mapped[str] = mapped_column(Text, default="")
    ref: Mapped[str] = mapped_column(Text, default="")
    note: Mapped[str] = mapped_column(Text, default="")
    key: Mapped[str] = mapped_column(String(64), default="")              # dedupe
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class KitabSubmission(Base):
    __tablename__ = "kitab_submissions"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("kx"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    book_id: Mapped[str] = mapped_column(String(40), index=True)
    number: Mapped[str] = mapped_column(String(12), default="")          # X-001
    to: Mapped[str] = mapped_column(String(200), default="")
    kind: Mapped[str] = mapped_column(String(12), default="publisher")   # publisher | agent | contest | journal | platform
    email: Mapped[str] = mapped_column(String(160), default="")
    guidelines: Mapped[str] = mapped_column(Text, default="")             # what THEY asked for (her paste: data)
    exclusive: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(14), default="draft")     # draft | sent | full_asked | offer | rejected | withdrawn | no_reply
    sent_on: Mapped[str] = mapped_column(String(10), default="")
    follow_on: Mapped[str] = mapped_column(String(10), default="")
    response: Mapped[str] = mapped_column(Text, default="")
    pitch: Mapped[str] = mapped_column(Text, default="")                  # {subject, letter, synopsis, blanks}
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class KitabStatement(Base):
    __tablename__ = "kitab_statements"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("kr"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    book_id: Mapped[str] = mapped_column(String(40), index=True)
    period: Mapped[str] = mapped_column(String(40), default="")
    period_end: Mapped[str] = mapped_column(String(10), default="")
    format: Mapped[str] = mapped_column(String(14), default="paperback")
    source: Mapped[str] = mapped_column(String(20), default="publisher")  # publisher | kdp | pothi | notionpress | other
    units: Mapped[int] = mapped_column(Integer, default=0)
    returns: Mapped[int] = mapped_column(Integer, default=0)
    price: Mapped[float | None] = mapped_column(Float, nullable=True)     # MRP per copy (her / statement number)
    net: Mapped[float | None] = mapped_column(Float, nullable=True)       # publisher's net receipts (when royalty is on net)
    stated: Mapped[float | None] = mapped_column(Float, nullable=True)    # what the statement says she earned
    tds: Mapped[float | None] = mapped_column(Float, nullable=True)
    expected: Mapped[float | None] = mapped_column(Float, nullable=True)  # by code from HER contract (None = can't say)
    note: Mapped[str] = mapped_column(Text, default="")
    received: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class KitabCard(Base):
    __tablename__ = "kitab_cards"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("kk"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    book_id: Mapped[str] = mapped_column(String(40), default="")
    kind: Mapped[str] = mapped_column(String(12), default="")           # accept | permission | submission | invoice | deliver
    target: Mapped[str] = mapped_column(String(40), default="")         # chapter / permission / submission id
    show: Mapped[str] = mapped_column(Text, default="")
    hash: Mapped[str] = mapped_column(String(64), default="")
    status: Mapped[str] = mapped_column(String(10), default="waiting")  # waiting | approved | rejected | stale
    asked_by: Mapped[str] = mapped_column(String(80), default="")
    reason: Mapped[str] = mapped_column(Text, default="")
    result: Mapped[str] = mapped_column(Text, default="")
    conv: Mapped[str] = mapped_column(String(40), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class KitabAlert(Base):
    __tablename__ = "kitab_alerts"
    key: Mapped[str] = mapped_column(String(200), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
