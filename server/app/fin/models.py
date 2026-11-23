"""F0 of docs/FINANCE_GLOBAL_PLAN.md - the finance data spine. All new tables; every column has a default (house DB rule).

Money is never a float here: `amount_minor` is an integer in the currency's smallest unit, with its ISO 4217 code beside it.
Every row carries the workspace it belongs to and where it came from (`source`)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Float, Integer, String, Text, UniqueConstraint
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
    meta: Mapped[str | None] = mapped_column(Text, nullable=True, default="{}")    # F7: prepared_by, reviews, signer, signature, shared


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


class FinCoa(Base):
    """F3 chart of accounts, one per workspace. `sub` marks the accounts the books need to find (bank, ar, ap, tax_out ...)."""
    __tablename__ = "fin_coa"
    __table_args__ = (UniqueConstraint("tenant_id", "workspace_id", "code", name="uq_fin_coa_code"),)
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("fk"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    workspace_id: Mapped[str] = mapped_column(String(40), index=True, default="")
    code: Mapped[str] = mapped_column(String(16), default="")
    name: Mapped[str] = mapped_column(String(120), default="")
    type: Mapped[str] = mapped_column(String(12), default="expense")             # asset | liability | equity | income | expense
    sub: Mapped[str] = mapped_column(String(24), default="")


class FinJournal(Base):
    __tablename__ = "fin_journal"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("fj"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    workspace_id: Mapped[str] = mapped_column(String(40), index=True, default="")
    day: Mapped[str] = mapped_column(String(10), default="", index=True)
    period: Mapped[str] = mapped_column(String(7), default="", index=True)
    memo: Mapped[str] = mapped_column(String(240), default="")
    source: Mapped[str] = mapped_column(String(16), default="manual")              # manual | invoice | bill | payment | bank | depreciation | fx | reval
    source_ref: Mapped[str] = mapped_column(String(80), default="", index=True)    # unique per workspace when set: posting twice is refused
    posted_by: Mapped[str] = mapped_column(String(80), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class FinLine(Base):
    __tablename__ = "fin_line"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("fl"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    workspace_id: Mapped[str] = mapped_column(String(40), index=True, default="")
    journal_id: Mapped[str] = mapped_column(String(40), index=True, default="")
    code: Mapped[str] = mapped_column(String(16), default="", index=True)
    debit_minor: Mapped[int] = mapped_column(BigInteger, default=0)                 # book currency
    credit_minor: Mapped[int] = mapped_column(BigInteger, default=0)
    party: Mapped[str] = mapped_column(String(120), default="")
    txn_id: Mapped[str] = mapped_column(String(40), default="", index=True)         # the bank line this posting came from
    dim: Mapped[str | None] = mapped_column(String(80), nullable=True, default="")   # v0.999.159 the cost centre of this line


class FinInvoice(Base):
    """A sales invoice (kind sales) or a bill she owes (kind purchase). Amounts in the document's own currency."""
    __tablename__ = "fin_invoice"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("fi"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    workspace_id: Mapped[str] = mapped_column(String(40), index=True, default="")
    kind: Mapped[str] = mapped_column(String(10), default="sales")
    number: Mapped[str] = mapped_column(String(40), default="", index=True)
    party: Mapped[str] = mapped_column(String(120), default="")
    issue: Mapped[str] = mapped_column(String(10), default="")
    due: Mapped[str] = mapped_column(String(10), default="")
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    net_minor: Mapped[int] = mapped_column(BigInteger, default=0)
    tax_minor: Mapped[int] = mapped_column(BigInteger, default=0)
    total_minor: Mapped[int] = mapped_column(BigInteger, default=0)
    paid_minor: Mapped[int] = mapped_column(BigInteger, default=0)
    rate: Mapped[float] = mapped_column(Float, default=1.0)                         # to the book currency when it was booked
    carried_rate: Mapped[float] = mapped_column(Float, default=1.0)                 # after a revaluation
    rate_date: Mapped[str] = mapped_column(String(10), default="")
    rate_source: Mapped[str] = mapped_column(String(120), default="")
    code: Mapped[str] = mapped_column(String(16), default="")                        # income / expense account
    lines: Mapped[str] = mapped_column(Text, default="[]")
    supply: Mapped[str | None] = mapped_column(Text, nullable=True, default="{}")    # F4: where it was supplied {country, state, b2b, buyer_tax_id}
    status: Mapped[str] = mapped_column(String(10), default="draft")                # draft | open | paid | void
    source: Mapped[str] = mapped_column(String(16), default="manual")               # manual | receipt
    cost_centre: Mapped[str | None] = mapped_column(String(80), nullable=True, default="")   # v0.999.159 its income / expense line's cost centre
    ic_ws: Mapped[str | None] = mapped_column(String(40), nullable=True, default="")         # v0.999.159 the group company it is with (intercompany)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class FinAsset(Base):
    __tablename__ = "fin_asset"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("fx"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    workspace_id: Mapped[str] = mapped_column(String(40), index=True, default="")
    name: Mapped[str] = mapped_column(String(160), default="")
    cost_minor: Mapped[int] = mapped_column(BigInteger, default=0)
    salvage_minor: Mapped[int] = mapped_column(BigInteger, default=0)
    start: Mapped[str] = mapped_column(String(7), default="")                       # YYYY-MM, first month depreciated
    life_months: Mapped[int] = mapped_column(Integer, default=36)
    method: Mapped[str] = mapped_column(String(12), default="straight")             # straight | reducing
    rate_pct: Mapped[float] = mapped_column(Float, default=0.0)                     # reducing balance, a year


class FinPeriod(Base):
    __tablename__ = "fin_period"
    __table_args__ = (UniqueConstraint("tenant_id", "workspace_id", "period", name="uq_fin_period"),)
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("fz"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    workspace_id: Mapped[str] = mapped_column(String(40), index=True, default="")
    period: Mapped[str] = mapped_column(String(7), default="")
    locked_by: Mapped[str] = mapped_column(String(120), default="")
    exceptions: Mapped[str] = mapped_column(Text, default="")
    hash: Mapped[str] = mapped_column(String(64), default="")
    locked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class FinBooksMember(Base):
    """v0.999.159 a person who works on one business's books, with a role. The owner is the workspace's tenant and is never a row."""
    __tablename__ = "fin_books_member"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("fbm"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)                  # the owner of the books
    workspace_id: Mapped[str] = mapped_column(String(40), index=True, default="")
    email: Mapped[str] = mapped_column(String(320), index=True, default="")
    user_id: Mapped[str] = mapped_column(String(64), index=True, default="")        # filled when they first open the books
    name: Mapped[str] = mapped_column(String(120), default="")
    role: Mapped[str] = mapped_column(String(16), default="viewer")                 # admin | accountant | approver | auditor | viewer
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    added_by: Mapped[str] = mapped_column(String(160), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class FinBooksRequest(Base):
    """v0.999.159 a posting waiting for a second person: what, its arguments' hash, the amount, who made it and who approved."""
    __tablename__ = "fin_books_request"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("fbr"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    workspace_id: Mapped[str] = mapped_column(String(40), index=True, default="")
    action: Mapped[str] = mapped_column(String(24), default="")
    args: Mapped[str] = mapped_column(Text, default="{}")
    hash: Mapped[str] = mapped_column(String(64), default="")
    what: Mapped[str] = mapped_column(String(240), default="")
    amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    needs: Mapped[int] = mapped_column(Integer, default=1)
    maker: Mapped[str] = mapped_column(String(160), default="")
    maker_id: Mapped[str] = mapped_column(String(64), default="")
    approvals: Mapped[str] = mapped_column(Text, default="[]")
    status: Mapped[str] = mapped_column(String(10), default="pending", index=True)   # pending | done | failed | rejected
    result: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class FinBooksInbox(Base):
    """v0.999.163 one invoice / bill that came in by itself - her mail, Hoola's own address, another program, her shop -
    read by Hoola, checked in code, and the books document it became (or why not)."""
    __tablename__ = "fin_books_inbox"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("fbi"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    workspace_id: Mapped[str] = mapped_column(String(40), index=True, default="")
    source: Mapped[str] = mapped_column(String(16), default="")                    # email | hoola_mail | software | api | shop
    source_ref: Mapped[str] = mapped_column(String(200), index=True, default="")   # the mail / record it came from (read once)
    sender: Mapped[str] = mapped_column(String(200), default="")
    subject: Mapped[str] = mapped_column(String(300), default="")
    file_name: Mapped[str] = mapped_column(String(200), default="")
    file_sha: Mapped[str] = mapped_column(String(64), index=True, default="")
    kind: Mapped[str] = mapped_column(String(10), default="")                      # sales | purchase
    fields: Mapped[str] = mapped_column(Text, default="{}")
    checks: Mapped[str] = mapped_column(Text, default="[]")
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    reader: Mapped[str] = mapped_column(String(16), default="")                    # ai | text | data
    status: Mapped[str] = mapped_column(String(16), default="new", index=True)     # posted | draft | waiting | duplicate | not_invoice | failed | dropped
    doc_id: Mapped[str] = mapped_column(String(40), default="")
    note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


TABLES = (FinBooksInbox, FinBooksMember, FinBooksRequest, FinCoa, FinJournal, FinLine, FinInvoice, FinAsset, FinPeriod, FinWorkspace, FinEntity, FinBook, FinAccount, FinTxn, FinDoc, FinParty, FinObligation, FinCase, FinDraft, FinEvent)
_READY: set[int] = set()


def ensure() -> None:
    from .. import db as _db
    eng = getattr(_db, "_engine", None)
    if eng is not None and id(eng) not in _READY:
        for m in TABLES:
            m.__table__.create(eng, checkfirst=True)
        _db.add_missing_columns_for(eng, FinLine.__table__, FinInvoice.__table__)   # v0.999.159 dim / cost_centre / ic_ws on old rows
        _READY.add(id(eng))
