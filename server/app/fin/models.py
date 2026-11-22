"""F0 of docs/FINANCE_GLOBAL_PLAN.md - the finance data spine. All new tables; every column has a default (house DB rule).

Money is never a float here: `amount_minor` is an integer in the currency's smallest unit, with its ISO 4217 code beside it.
Every row carries the workspace it belongs to and where it came from (`source`)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Float, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now


class FinWorkspace(Base):
    """One workspace = one person / household / business / firm / institution, or one client book inside a firm."""
    __tablename__ = "fin_workspace"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("fw"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    parent_id: Mapped[str] = mapped_column(String(40), default="", index=True)   # a firm's client book points at the firm
    name: Mapped[str] = mapped_column(String(160), default="")
    size: Mapped[str] = mapped_column(String(16), default="personal")             # personal | solo | business | firm | institution
    entity_type: Mapped[str] = mapped_column(String(32), default="individual")
    countries: Mapped[str] = mapped_column(Text, default="[]")                    # JSON list of ISO 3166 alpha-2
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    answers: Mapped[str] = mapped_column(Text, default="{}")                      # the setup answers as she gave them
    settings: Mapped[str] = mapped_column(Text, default="{}")                     # what the size turned on (derived, shown before apply)
    hash: Mapped[str] = mapped_column(String(64), default="")
    status: Mapped[str] = mapped_column(String(12), default="active")             # active | archived
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class FinEntity(Base):
    __tablename__ = "fin_entity"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("fe"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    workspace_id: Mapped[str] = mapped_column(String(40), index=True, default="")
    name: Mapped[str] = mapped_column(String(160), default="")
    kind: Mapped[str] = mapped_column(String(32), default="individual")
    country: Mapped[str] = mapped_column(String(2), default="")
    tax_id_masked: Mapped[str] = mapped_column(String(40), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class FinBook(Base):
    __tablename__ = "fin_book"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("fb"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    workspace_id: Mapped[str] = mapped_column(String(40), index=True, default="")
    entity_id: Mapped[str] = mapped_column(String(40), default="")
    name: Mapped[str] = mapped_column(String(160), default="Main book")
    kind: Mapped[str] = mapped_column(String(16), default="household")            # household | business
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    year_end: Mapped[str] = mapped_column(String(5), default="12-31")             # MM-DD
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class FinAccount(Base):
    __tablename__ = "fin_account"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("fa"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    workspace_id: Mapped[str] = mapped_column(String(40), index=True, default="")
    book_id: Mapped[str] = mapped_column(String(40), default="")
    name: Mapped[str] = mapped_column(String(160), default="")
    kind: Mapped[str] = mapped_column(String(16), default="bank")                 # bank | card | wallet | loan | investment | payable | receivable
    institution: Mapped[str] = mapped_column(String(120), default="")
    number_masked: Mapped[str] = mapped_column(String(24), default="")            # never more than the last 4
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    source: Mapped[str] = mapped_column(String(24), default="manual")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class FinTxn(Base):
    __tablename__ = "fin_txn"
    __table_args__ = (UniqueConstraint("tenant_id", "account_id", "dedup", name="uq_fin_txn_dedup"),)
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("ft"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    workspace_id: Mapped[str] = mapped_column(String(40), index=True, default="")
    account_id: Mapped[str] = mapped_column(String(40), index=True, default="")
    day: Mapped[str] = mapped_column(String(10), default="", index=True)          # YYYY-MM-DD
    amount_minor: Mapped[int] = mapped_column(BigInteger, default=0)              # + money in, - money out
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    narration: Mapped[str] = mapped_column(String(240), default="")
    ref: Mapped[str] = mapped_column(String(80), default="")
    category: Mapped[str] = mapped_column(String(40), default="")
    fx_rate: Mapped[float] = mapped_column(Float, default=0.0)                    # to the book currency, 0 = same currency
    fx_source: Mapped[str] = mapped_column(String(120), default="")
    source: Mapped[str] = mapped_column(String(24), default="manual")             # csv | ofx | qif | mt940 | camt053 | ...
    source_ref: Mapped[str] = mapped_column(String(80), default="")               # the import batch
    dedup: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class FinDoc(Base):
    __tablename__ = "fin_doc"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("fd"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    workspace_id: Mapped[str] = mapped_column(String(40), index=True, default="")
    kind: Mapped[str] = mapped_column(String(24), default="other")                # statement | bill | invoice | contract | notice | return | other
    title: Mapped[str] = mapped_column(String(200), default="")
    file_id: Mapped[str] = mapped_column(String(64), default="")
    fields: Mapped[str] = mapped_column(Text, default="{}")                       # read-out fields with confidence
    source: Mapped[str] = mapped_column(String(24), default="upload")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class FinParty(Base):
    __tablename__ = "fin_party"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("fp"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    workspace_id: Mapped[str] = mapped_column(String(40), index=True, default="")
    name: Mapped[str] = mapped_column(String(160), default="")
    kind: Mapped[str] = mapped_column(String(16), default="other")                # customer | supplier | employee | lender | other
    country: Mapped[str] = mapped_column(String(2), default="")
    tax_id_masked: Mapped[str] = mapped_column(String(40), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class FinObligation(Base):
    __tablename__ = "fin_obligation"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("fo"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    workspace_id: Mapped[str] = mapped_column(String(40), index=True, default="")
    kind: Mapped[str] = mapped_column(String(24), default="other")                # tax | filing | payment | covenant | renewal | other
    title: Mapped[str] = mapped_column(String(200), default="")
    due: Mapped[str] = mapped_column(String(10), default="", index=True)
    country: Mapped[str] = mapped_column(String(2), default="")
    pack_path: Mapped[str] = mapped_column(String(120), default="")               # where the rule came from
    status: Mapped[str] = mapped_column(String(12), default="open")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class FinCase(Base):
    __tablename__ = "fin_case"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("fc"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    workspace_id: Mapped[str] = mapped_column(String(40), index=True, default="")
    employee: Mapped[str] = mapped_column(String(24), default="")
    part: Mapped[str] = mapped_column(String(40), default="")
    title: Mapped[str] = mapped_column(String(200), default="")
    state: Mapped[str] = mapped_column(String(20), default="open")                # open | gathering | drafted | waiting_decider | sent | tracking | closed
    decider: Mapped[str] = mapped_column(String(120), default="")
    due: Mapped[str] = mapped_column(String(10), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class FinDraft(Base):
    __tablename__ = "fin_draft"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("fr"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    workspace_id: Mapped[str] = mapped_column(String(40), index=True, default="")
    case_id: Mapped[str] = mapped_column(String(40), default="")
    kind: Mapped[str] = mapped_column(String(24), default="letter")
    body: Mapped[str] = mapped_column(Text, default="")
    hash: Mapped[str] = mapped_column(String(64), default="")
    state: Mapped[str] = mapped_column(String(16), default="waiting")             # waiting | approved | rejected
    approved_by: Mapped[str] = mapped_column(String(120), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class FinEvent(Base):
    """Append-only audit log. Each row carries the hash of the one before it in the same tenant, so a removed or edited row shows."""
    __tablename__ = "fin_event"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("fv"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    workspace_id: Mapped[str] = mapped_column(String(40), index=True, default="")
    seq: Mapped[int] = mapped_column(Integer, default=0, index=True)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    actor: Mapped[str] = mapped_column(String(80), default="")
    kind: Mapped[str] = mapped_column(String(24), default="")                     # tool | profile | import | refused | pack
    what: Mapped[str] = mapped_column(String(200), default="")
    detail_hash: Mapped[str] = mapped_column(String(64), default="")              # hash of the inputs, never the inputs
    prev: Mapped[str] = mapped_column(String(64), default="")
    hash: Mapped[str] = mapped_column(String(64), default="")


TABLES = (FinWorkspace, FinEntity, FinBook, FinAccount, FinTxn, FinDoc, FinParty, FinObligation, FinCase, FinDraft, FinEvent)
_READY: set[int] = set()


def ensure() -> None:
    from .. import db as _db
    eng = getattr(_db, "_engine", None)
    if eng is not None and id(eng) not in _READY:
        for m in TABLES:
            m.__table__.create(eng, checkfirst=True)
        _READY.add(id(eng))
