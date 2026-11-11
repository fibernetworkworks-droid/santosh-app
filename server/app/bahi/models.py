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


TABLES = (AccDoc, AccPeriod, AccEvent, AccGstConn, AccWbCall)


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
