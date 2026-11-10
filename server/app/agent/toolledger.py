"""G1 of docs/LANGGRAPH_TURN_PLAN.md - the tool ledger of a graph turn (only used when `chat_graph` is on).

One row per tool_use of a turn thread: `intent` is written BEFORE the tool runs, `done` (with the tool's result) or
`failed` (with its error) AFTER. A turn resumed from its checkpoint after a restart reads the ledger first:

    done            -> the stored result is used again; the tool is NOT called a second time
    failed          -> the same failure is given again (the tool is not called)
    intent, no end  -> a read-only tool is simply run again; any other tool (a send, an order, a delete, a payment)
                       is NEVER re-run automatically: the model gets an honest "it may already have run, the outcome is
                       unknown, check before any retry" result instead (fixes bug class 9 of the plan)

Read-only = the classification the honesty check already uses (`draftcheck._is_read`: the READS set, the
`_dekho` family and the read-name patterns minus change words), plus `santosh._parallel_ok` for the one tool whose
kind depends on its arguments (kaam_status action=stop is a change).

The table is registered in `db.init_db` AND self-heals with `ensure_table()` (the v0.190.1 rule)."""
from __future__ import annotations

import hashlib
import json
import logging
from datetime import timedelta

from sqlalchemy import DateTime, String, Text, delete, select
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now, session

log = logging.getLogger("santosh.toolledger")

STATS = {"intent": 0, "done": 0, "failed": 0, "reused": 0, "rerun_read": 0, "ambiguous": 0}
_ready_engine = None


class TurnToolLedger(Base):
    __tablename__ = "turn_tool_ledger"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("tl"))
    thread_id: Mapped[str] = mapped_column(String(160), index=True)
    tool_use_id: Mapped[str] = mapped_column(String(120), index=True)
    tool: Mapped[str] = mapped_column(String(120), default="")
    args_hash: Mapped[str] = mapped_column(String(64), default="")
    state: Mapped[str] = mapped_column(String(12), default="intent")     # intent | done | failed
    result: Mapped[str] = mapped_column(Text, default="")                # done: the tool's output as JSON
    error_kind: Mapped[str] = mapped_column(String(20), default="")      # failed: tool_error | timeout | crash
    error: Mapped[str] = mapped_column(Text, default="")
    created_at = mapped_column(DateTime(timezone=True), default=now)
    updated_at = mapped_column(DateTime(timezone=True), default=now, onupdate=now)


def ensure_table() -> None:
    """Self-heal: a database born before this model existed gets the table on first use (keyed on the engine, so a
    fresh test database is healed too)."""
    global _ready_engine
    from .. import db as _db
    eng = getattr(_db, "_engine", None)
    if eng is None or eng is _ready_engine:
        return
    TurnToolLedger.__table__.create(eng, checkfirst=True)
    _ready_engine = eng


def args_hash(args) -> str:
    try:
        raw = json.dumps(args or {}, sort_keys=True, ensure_ascii=False, default=str)
    except Exception:   # noqa: BLE001
        raw = repr(args)
    return hashlib.sha256(raw.encode("utf-8", "replace")).hexdigest()


def read_only(block: dict) -> bool:
    """Is this tool_use only a look-up? Reuses the honesty check's read classification (no new list)."""
    from . import draftcheck
    from . import santosh as S
    name = str(block.get("name") or "")
    if name in S.PARALLEL_SAFE and not S._parallel_ok(block):
        return False          # kaam_status action=stop: a change, whatever its name says
    try:
        return bool(draftcheck._is_read(name))
    except Exception:   # noqa: BLE001 - unsure = not read-only (never re-run a maybe-send)
        return False


def get(thread_id: str, tool_use_id: str) -> dict | None:
    ensure_table()
    with session() as s:
        r = s.scalars(select(TurnToolLedger).where(TurnToolLedger.thread_id == thread_id,
                                                   TurnToolLedger.tool_use_id == tool_use_id)
                      .order_by(TurnToolLedger.created_at.desc()).limit(1)).first()
        if r is None:
            return None
        return {"tool": r.tool, "args_hash": r.args_hash, "state": r.state, "result": r.result,
                "error_kind": r.error_kind, "error": r.error}


def intent(thread_id: str, tool_use_id: str, tool: str, ahash: str) -> None:
    """Written BEFORE the tool runs (committed when this returns)."""
    ensure_table()
    with session() as s:
        r = s.scalars(select(TurnToolLedger).where(TurnToolLedger.thread_id == thread_id,
                                                   TurnToolLedger.tool_use_id == tool_use_id).limit(1)).first()
        if r is None:
            s.add(TurnToolLedger(thread_id=thread_id, tool_use_id=tool_use_id, tool=tool[:120], args_hash=ahash))
        else:
            r.tool, r.args_hash, r.state, r.result, r.error_kind, r.error = tool[:120], ahash, "intent", "", "", ""
    STATS["intent"] += 1


def _finish(thread_id: str, tool_use_id: str, **fields) -> None:
    ensure_table()
    with session() as s:
        r = s.scalars(select(TurnToolLedger).where(TurnToolLedger.thread_id == thread_id,
                                                   TurnToolLedger.tool_use_id == tool_use_id).limit(1)).first()
        if r is not None:
            for k, v in fields.items():
                setattr(r, k, v)


def done(thread_id: str, tool_use_id: str, out) -> None:
    try:
        raw = json.dumps(out, ensure_ascii=False, default=str)
    except Exception:   # noqa: BLE001
        raw = json.dumps(str(out), ensure_ascii=False)
    _finish(thread_id, tool_use_id, state="done", result=raw)
    STATS["done"] += 1


def failed(thread_id: str, tool_use_id: str, kind: str, error: str) -> None:
    _finish(thread_id, tool_use_id, state="failed", error_kind=kind[:20], error=str(error or "")[:4000])
    STATS["failed"] += 1


def forget(thread_id: str, older_than_h: float = 24.0) -> None:
    """A finished thread's rows go, and any row older than the window (threads that never finished)."""
    ensure_table()
    with session() as s:
        if thread_id:
            s.execute(delete(TurnToolLedger).where(TurnToolLedger.thread_id == thread_id))
        if older_than_h and older_than_h > 0:
            s.execute(delete(TurnToolLedger).where(
                TurnToolLedger.updated_at < now() - timedelta(hours=float(older_than_h))))


def rows(thread_id: str) -> list[dict]:
    """Tests / diagnostics."""
    ensure_table()
    with session() as s:
        return [{"tool_use_id": r.tool_use_id, "tool": r.tool, "state": r.state}
                for r in s.scalars(select(TurnToolLedger).where(TurnToolLedger.thread_id == thread_id)
                                   .order_by(TurnToolLedger.created_at)).all()]


def ambiguous_text(name: str) -> str:
    return (f"This step ({name}) was started before a server restart and MAY ALREADY HAVE RUN - its outcome is "
            "unknown. Do NOT run it again automatically. First check what really happened (its own status / list / "
            "sent tool, or the record it would have changed). Only retry if you can see that it did not happen; if "
            "you cannot check, tell her plainly that it may or may not have gone through.")
