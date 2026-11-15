"""v0.877 HOOLA AGENT API - tables (all prefixed hapi_).

Money is ALWAYS a whole number of micro-INR (1 INR = 1,000,000). The wallet balance must equal the sum of the ledger; the
ledger is append-only (an ORM guard here + a trigger on SQLite). Keys are stored as a sha256 only.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Integer, String, Text, UniqueConstraint, event
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now


class HapiKey(Base):
    """A company's API key. Acts as that company's own Hoola account (tenant), only for the tools in `tools`."""
    __tablename__ = "hapi_keys"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("hk"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    name: Mapped[str] = mapped_column(String(80), default="")
    key_hash: Mapped[str] = mapped_column(String(64), index=True, default="")
    tail: Mapped[str] = mapped_column(String(8), default="")
    tools: Mapped[str] = mapped_column(Text, default="[]")                  # JSON list of allowed tool names; [] = every catalogue tool
    rpm: Mapped[int] = mapped_column(Integer, default=60)
    rph: Mapped[int] = mapped_column(Integer, default=2000)
    concurrent: Mapped[int] = mapped_column(Integer, default=5)
    daily_limit_micro: Mapped[int | None] = mapped_column(BigInteger, nullable=True)   # None = no daily spend cap on this key
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class HapiWallet(Base):
    __tablename__ = "hapi_wallets"
    tenant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    balance_micro: Mapped[int] = mapped_column(BigInteger, default=0)
    suspended: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class HapiLedger(Base):
    """APPEND ONLY. One row per money event; (type, ref_type, ref_id) is unique so a retried event never counts twice."""
    __tablename__ = "hapi_ledger"
    __table_args__ = (UniqueConstraint("type", "ref_type", "ref_id", name="uq_hapi_ledger_event"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    type: Mapped[str] = mapped_column(String(12))                           # topup | charge | refund | adjustment
    amount_micro: Mapped[int] = mapped_column(BigInteger)                   # signed: credit +, debit -
    balance_after_micro: Mapped[int] = mapped_column(BigInteger)
    ref_type: Mapped[str] = mapped_column(String(12), default="")           # request | payment | admin
    ref_id: Mapped[str] = mapped_column(String(64), default="")
    note: Mapped[str] = mapped_column(String(200), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, index=True)


class HapiCall(Base):
    """Usage log: metadata only. The arguments and the result are NEVER stored."""
    __tablename__ = "hapi_calls"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("hr"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    key_id: Mapped[str] = mapped_column(String(40), index=True, default="")
    kind: Mapped[str] = mapped_column(String(12), default="tool")          # tool (employee / voice come later)
    name: Mapped[str] = mapped_column(String(60), default="")
    status: Mapped[str] = mapped_column(String(12), default="ok")          # ok | failed | rejected
    charged_micro: Mapped[int] = mapped_column(BigInteger, default=0)      # what the customer finally paid (0 when failed)
    ms: Mapped[int] = mapped_column(Integer, default=0)
    error_code: Mapped[str] = mapped_column(String(40), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, index=True)


@event.listens_for(HapiLedger, "before_update")
@event.listens_for(HapiLedger, "before_delete")
def _ledger_is_append_only(mapper, connection, target):   # noqa: ARG001
    raise RuntimeError("hapi_ledger is append-only")


_READY: set[int] = set()

_SQLITE_TRIGGERS = (
    "CREATE TRIGGER IF NOT EXISTS hapi_ledger_no_update BEFORE UPDATE ON hapi_ledger "
    "BEGIN SELECT RAISE(ABORT, 'hapi_ledger is append-only'); END",
    "CREATE TRIGGER IF NOT EXISTS hapi_ledger_no_delete BEFORE DELETE ON hapi_ledger "
    "BEGIN SELECT RAISE(ABORT, 'hapi_ledger is append-only'); END",
)


def ensure_tables() -> None:
    """Self-heal (the v0.190.1 rule): created checkfirst once per engine, so a DB born before this module still works."""
    from .. import db as _db
    eng = getattr(_db, "_engine", None)
    if eng is None or id(eng) in _READY:
        return
    for t in (HapiKey, HapiWallet, HapiLedger, HapiCall):
        t.__table__.create(eng, checkfirst=True)
    if eng.dialect.name == "sqlite":
        from sqlalchemy import text
        with eng.begin() as c:
            for ddl in _SQLITE_TRIGGERS:
                c.execute(text(ddl))
    _READY.add(id(eng))
