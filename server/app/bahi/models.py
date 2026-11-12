"""The BAHI tables. All new; every column has a default so old rows / partial writes never break (house DB rule)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now


class AccDoc(Base):
    """One document in her register - a sale, a purchase bill, a credit note... - exactly once per (source, source_ref)."""
    __tablename__ = "acc_docs"
    __table_args__ = (UniqueConstraint("tenant_id", "source", "source_ref", name="uq_acc_doc_source"),)
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("ad"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    gstin: Mapped[str] = mapped_column(String(15), default="", index=True)          # her own GSTIN this document belongs to
    period: Mapped[str] = mapped_column(String(7), default="", index=True)          # YYYY-MM (from the document date)
    direction: Mapped[str] = mapped_column(String(3), default="out")                # out (sales) | in (purchases)
    kind: Mapped[str] = mapped_column(String(8), default="inv")                     # inv | cn | dn | bill
    number: Mapped[str] = mapped_column(String(60), default="")
    doc_date: Mapped[str] = mapped_column(String(10), default="")                   # YYYY-MM-DD
    party_name: Mapped[str] = mapped_column(String(160), default="")
    party_gstin: Mapped[str] = mapped_column(String(15), default="", index=True)
    pos: Mapped[str] = mapped_column(String(2), default="")
    taxable: Mapped[float] = mapped_column(Float, default=0.0)
    cgst: Mapped[float] = mapped_column(Float, default=0.0)
    sgst: Mapped[float] = mapped_column(Float, default=0.0)
    igst: Mapped[float] = mapped_column(Float, default=0.0)
    cess: Mapped[float] = mapped_column(Float, default=0.0)
    tax: Mapped[float] = mapped_column(Float, default=0.0)                          # total tax (when the source does not split it)
    total: Mapped[float] = mapped_column(Float, default=0.0)
    irn: Mapped[str] = mapped_column(String(70), default="")
    source: Mapped[str] = mapped_column(String(24), default="manual")               # gst_sahayak | office | thok | app | intake...
    source_ref: Mapped[str] = mapped_column(String(80), default="")
    fingerprint: Mapped[str] = mapped_column(String(64), default="")
    status: Mapped[str] = mapped_column(String(12), default="confirmed")            # draft | confirmed | gone (left its source)
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    reason: Mapped[str] = mapped_column(Text, default="")                           # why Hoola believes this row (shown to her)
    problems: Mapped[str] = mapped_column(Text, default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class AccPeriod(Base):
    """A month for one of her GSTINs: open, or LOCKED (filed / closed by her CA) - a locked month is never edited, only amended."""
    __tablename__ = "acc_periods"
    __table_args__ = (UniqueConstraint("tenant_id", "gstin", "period", name="uq_acc_period"),)
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("ap"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    gstin: Mapped[str] = mapped_column(String(15), default="")
    period: Mapped[str] = mapped_column(String(7), default="")
    state: Mapped[str] = mapped_column(String(10), default="open")                  # open | locked
    locked_by: Mapped[str] = mapped_column(String(80), default="")
    note: Mapped[str] = mapped_column(Text, default="")
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class AccEvent(Base):
    """Append-only trail: who did what to which row, with before / after. Nothing updates or deletes these."""
    __tablename__ = "acc_events"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("ae"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    actor: Mapped[str] = mapped_column(String(40), default="hoola")
    what: Mapped[str] = mapped_column(String(40), default="")
    ref: Mapped[str] = mapped_column(String(80), default="")
    before: Mapped[str] = mapped_column(Text, default="")
    after: Mapped[str] = mapped_column(Text, default="")


class AccGstConn(Base):
    """Her GSTIN's connection through the GSP. No portal password is ever kept. IRP / EWB API passwords are SEALED
    (accounts.encrypt) and returned by no route. Filled by the A1 connect walk; A0 only creates the table."""
    __tablename__ = "acc_gst_conn"
    __table_args__ = (UniqueConstraint("tenant_id", "gstin", name="uq_acc_conn"),)
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("ac"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    gstin: Mapped[str] = mapped_column(String(15), default="")
    state_cd: Mapped[str] = mapped_column(String(2), default="")
    gst_username: Mapped[str] = mapped_column(String(60), default="")
    txn: Mapped[str] = mapped_column(String(120), default="")
    enabled_until: Mapped[str] = mapped_column(String(25), default="")
    last_refresh: Mapped[str] = mapped_column(String(25), default="")
    status: Mapped[str] = mapped_column(String(16), default="new")                  # new | otp_sent | connected | lapsed
    einv_username: Mapped[str] = mapped_column(String(60), default="")
    einv_password_enc: Mapped[str] = mapped_column(Text, default="")
    einv_token: Mapped[str] = mapped_column(Text, default="")
    einv_token_at: Mapped[str] = mapped_column(String(25), default="")
    einv_seller: Mapped[str] = mapped_column(Text, default="{}")                    # seller name / address / pin for INV-01 (not secret)
    einv_irp: Mapped[str] = mapped_column(String(8), default="")
    ewb_username: Mapped[str] = mapped_column(String(60), default="")
    ewb_password_enc: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class AccWbCall(Base):
    """The WhiteBooks call meter (they bill per call): one row per call, never the request or the reply."""
    __tablename__ = "acc_wb_calls"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("aw"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, index=True)
    product: Mapped[str] = mapped_column(String(6), default="gst")
    op: Mapped[str] = mapped_column(String(60), default="")
    ok: Mapped[bool] = mapped_column(Boolean, default=False)
    code: Mapped[str] = mapped_column(String(40), default="")
    ms: Mapped[int] = mapped_column(Integer, default=0)


class AccTwoB(Base):
    """One invoice / note in her GSTR-2B as GSTN sent it (A2), with HER IMS decision. Replaced per (gstin, period) on a new pull."""
    __tablename__ = "acc_2b"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("a2"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    gstin: Mapped[str] = mapped_column(String(15), default="", index=True)
    period: Mapped[str] = mapped_column(String(6), default="", index=True)          # MMYYYY as GSTN uses it
    section: Mapped[str] = mapped_column(String(8), default="b2b")                 # b2b | b2ba | cdnr | cdnra | ecom
    ctin: Mapped[str] = mapped_column(String(15), default="", index=True)
    trdnm: Mapped[str] = mapped_column(String(160), default="")
    inum: Mapped[str] = mapped_column(String(60), default="")
    doc_type: Mapped[str] = mapped_column(String(4), default="")                    # R invoice | C credit note | D debit note
    dt: Mapped[str] = mapped_column(String(10), default="")                         # YYYY-MM-DD
    val: Mapped[float] = mapped_column(Float, default=0.0)
    txval: Mapped[float] = mapped_column(Float, default=0.0)
    igst: Mapped[float] = mapped_column(Float, default=0.0)
    cgst: Mapped[float] = mapped_column(Float, default=0.0)
    sgst: Mapped[float] = mapped_column(Float, default=0.0)
    cess: Mapped[float] = mapped_column(Float, default=0.0)
    rev: Mapped[bool] = mapped_column(Boolean, default=False)
    itcavl: Mapped[bool] = mapped_column(Boolean, default=True)
    rsn: Mapped[str] = mapped_column(String(60), default="")
    action: Mapped[str] = mapped_column(String(8), default="")                      # her decision: accept | reject | pending | ""
    reason: Mapped[str] = mapped_column(Text, default="")                           # why Hoola proposed it
    applied_at: Mapped[str] = mapped_column(String(25), default="")                 # when the decision reached the portal
    ext: Mapped[str] = mapped_column(Text, default="{}")                            # supplier period, POS, invoice type - for the IMS body


class AccIrn(Base):
    """One e-invoice attempt for one document (A5). The row is written BEFORE the call and the raw reply is stored the moment it arrives, so a
    timeout or a restart can never lose or double-issue an IRN."""
    __tablename__ = "acc_irn"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("ai"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    gstin: Mapped[str] = mapped_column(String(15), default="", index=True)
    doc_id: Mapped[str] = mapped_column(String(40), default="", index=True)          # acc_docs.id
    doc_type: Mapped[str] = mapped_column(String(3), default="INV")                 # INV | CRN | DBN
    doc_no: Mapped[str] = mapped_column(String(16), default="")
    doc_date: Mapped[str] = mapped_column(String(10), default="")
    status: Mapped[str] = mapped_column(String(12), default="pending")             # pending | generated | cancelled | failed | unknown
    irn: Mapped[str] = mapped_column(String(70), default="", index=True)
    ack_no: Mapped[str] = mapped_column(String(30), default="")
    ack_dt: Mapped[str] = mapped_column(String(25), default="")
    irp: Mapped[str] = mapped_column(String(8), default="")
    ewb_no: Mapped[str] = mapped_column(String(20), default="")
    ewb_dt: Mapped[str] = mapped_column(String(25), default="")
    error: Mapped[str] = mapped_column(Text, default="")
    raw: Mapped[str] = mapped_column(Text, default="")                              # the reply as received (no secrets in it)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class AccIntake(Base):
    """A purchase bill that came in as a photo / PDF / text and was read (A6). Always a DRAFT until her tap; nothing enters the register silently."""
    __tablename__ = "acc_intake"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("an"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    gstin: Mapped[str] = mapped_column(String(15), default="", index=True)          # HER GSTIN the bill is for
    channel: Mapped[str] = mapped_column(String(16), default="upload")             # upload | whatsapp | email | chat | pc
    file_id: Mapped[str] = mapped_column(String(60), default="")
    text_hash: Mapped[str] = mapped_column(String(40), default="", index=True)
    fields: Mapped[str] = mapped_column(Text, default="{}")
    checks: Mapped[str] = mapped_column(Text, default="[]")
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    ocr_conf: Mapped[float] = mapped_column(Float, default=100.0)
    status: Mapped[str] = mapped_column(String(12), default="draft")               # draft | confirmed | rejected
    doc_id: Mapped[str] = mapped_column(String(40), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class AccBankLine(Base):
    """One line of a bank statement she imported (A7). Stored once: a re-import of the same statement adds nothing."""
    __tablename__ = "acc_bank_lines"
    __table_args__ = (UniqueConstraint("tenant_id", "line_hash", name="uq_acc_bank_line"),)
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("ab"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    account: Mapped[str] = mapped_column(String(40), default="")                    # her label, e.g. "HDFC current 0123" (never the full number)
    line_hash: Mapped[str] = mapped_column(String(40), default="")
    date: Mapped[str] = mapped_column(String(10), default="", index=True)           # YYYY-MM-DD
    narration: Mapped[str] = mapped_column(String(200), default="")
    debit: Mapped[float] = mapped_column(Float, default=0.0)
    credit: Mapped[float] = mapped_column(Float, default=0.0)
    balance: Mapped[float] = mapped_column(Float, default=0.0)
    mode: Mapped[str] = mapped_column(String(8), default="other")                   # upi | neft | imps | rtgs | cheque | card | cash | other
    ref: Mapped[str] = mapped_column(String(40), default="", index=True)            # UTR / RRN / cheque no read from the narration
    payer: Mapped[str] = mapped_column(String(80), default="")
    vpa: Mapped[str] = mapped_column(String(60), default="", index=True)
    status: Mapped[str] = mapped_column(String(10), default="open")                 # open | proposed | matched | ignored
    match_doc_id: Mapped[str] = mapped_column(String(40), default="")
    match_kind: Mapped[str] = mapped_column(String(16), default="")
    match_reason: Mapped[str] = mapped_column(Text, default="")
    match_conf: Mapped[float] = mapped_column(Float, default=0.0)
    category: Mapped[str] = mapped_column(String(40), default="")
    settlement: Mapped[str] = mapped_column(Text, default="")                       # JSON: gateway settlement split, when this credit is one
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class AccBankLearn(Base):
    """What she confirmed once, remembered: a payer's UPI id -> who they are; a narration word -> a category."""
    __tablename__ = "acc_bank_learn"
    __table_args__ = (UniqueConstraint("tenant_id", "kind", "key", name="uq_acc_bank_learn"),)
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("al"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    kind: Mapped[str] = mapped_column(String(8), default="vpa")                    # vpa | word
    key: Mapped[str] = mapped_column(String(80), default="")
    party_name: Mapped[str] = mapped_column(String(160), default="")
    party_gstin: Mapped[str] = mapped_column(String(15), default="")
    category: Mapped[str] = mapped_column(String(40), default="")


class AccBankRecon(Base):
    """A stored month-end bank reconciliation statement."""
    __tablename__ = "acc_bank_recon"
    __table_args__ = (UniqueConstraint("tenant_id", "account", "month", name="uq_acc_bank_recon"),)
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("ar"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    account: Mapped[str] = mapped_column(String(40), default="")
    month: Mapped[str] = mapped_column(String(7), default="")
    body: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


TABLES = (AccDoc, AccPeriod, AccEvent, AccGstConn, AccWbCall, AccTwoB, AccIrn, AccIntake, AccBankLine, AccBankLearn, AccBankRecon)


_READY: set[int] = set()


def ensure_tables() -> None:
    """Self-heal (the v0.190.1 lesson): a DB born before BAHI was registered gets its tables on first use. Keyed by engine id so a
    fresh engine (tests, a restart) checks exactly once."""
    from .. import db as _db
    eng = getattr(_db, "_engine", None)
    if eng is None or id(eng) in _READY:
        return
    for t in TABLES:
        t.__table__.create(bind=eng, checkfirst=True)
    _READY.add(id(eng))
