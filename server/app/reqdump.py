"""v0.732 CLAUDE PARITY Phase 0 - the request dump: exactly what the model received, per chat turn step.

Most of the bugs of the week before the parity plan were found by READING WHAT THE MODEL SAW. This keeps it: every call
through the one model-call funnel (`santosh._call_brain`) writes one row - the system prompt text, the tool NAMES (not
their schemas), the messages, the brain + model and max_tokens - for the conversation and turn it belongs to.

Rules:
- fail-open: a dump that cannot be written is a log line, never a broken turn; the write runs off the event loop.
- bounded: the newest `request_dump_turns` turns per conversation are kept (older rows deleted on write); the system
  text, each message part and the message count are capped and the caps are said in the row (`cut`).
- masked: secrets (keys, tokens, `password=` ...) via coder.redact, card / Aadhaar / PAN / bank numbers via
  pii.mask_sensitive - before the row is written.
- read: GET /api/conversations/{id}/request (the turns) and /request/{turn} (turn number 1..n or its turn id), behind
  the key AND the conversation's own tenant.
Switch: `request_dump` (default on).
"""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Integer, String, Text, delete, select
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base, now, session

log = logging.getLogger("santosh.reqdump")

SYSTEM_CAP = 200_000        # chars of system text kept (the plan measured ~50-57k)
PART_CAP = 8_000            # chars of any one text / tool input / tool result part
MSG_CAP = 400               # newest messages kept per call
MSG_TOTAL_CAP = 400_000     # chars of messages kept per call (newest first; the dropped count is in `sizes`)
KEEP_DAYS = 14              # rows older than this are swept (every SWEEP_EVERY writes)
SWEEP_EVERY = 200
STATS = {"written": 0, "failed": 0, "skipped": 0}


class RequestDump(Base):
    __tablename__ = "request_dumps"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True, default="")
    conversation_id: Mapped[str] = mapped_column(String(40), index=True)
    turn_id: Mapped[str] = mapped_column(String(40), default="")
    turn_no: Mapped[int] = mapped_column(Integer, default=1)
    step: Mapped[int] = mapped_column(Integer, default=1)
    brain: Mapped[str] = mapped_column(String(24), default="")
    model: Mapped[str] = mapped_column(String(120), default="")
    max_tokens: Mapped[int] = mapped_column(Integer, default=0)
    system: Mapped[str] = mapped_column(Text, default="")
    tools: Mapped[list] = mapped_column(JSON, default=list)
    messages: Mapped[list] = mapped_column(JSON, default=list)
    sizes: Mapped[dict] = mapped_column(JSON, default=dict)
    ok: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    error: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


_ready_engines: set[int] = set()


def ensure_table() -> None:
    """Self-heal (the v0.190.1 lesson): an old DB gets the table on the first write."""
    from . import db as _db
    eng = getattr(_db, "_engine", None)
    if eng is None or id(eng) in _ready_engines:
        return
    RequestDump.__table__.create(eng, checkfirst=True)
    _ready_engines.add(id(eng))


def on() -> bool:
    try:
        from .config import get_settings
        return bool(getattr(get_settings(), "request_dump", True))
    except Exception:
        return False


# ---------------------------------------------------------------- masking + shaping

def mask(text: Any) -> str:
    t = str(text or "")
    try:
        from .coder.redact import redact_secrets
        t = redact_secrets(t)
    except Exception:
        pass
    try:
        from .pii import mask_sensitive
        t = mask_sensitive(t)
    except Exception:
        pass
    return t


def _cut(text: Any, cap: int, cuts: list) -> str:
    t = mask(text)
    if len(t) > cap:
        cuts.append(len(t))
        return t[:cap] + f"\n[... {len(t) - cap} more chars cut by the dump]"
    return t


def _part(b: Any, cuts: list) -> Any:
    if isinstance(b, str):
        return {"type": "text", "text": _cut(b, PART_CAP, cuts)}
    if not isinstance(b, dict):
        return {"type": "?", "text": _cut(b, PART_CAP, cuts)}
    t = b.get("type")
    if t == "text":
        return {"type": "text", "text": _cut(b.get("text"), PART_CAP, cuts)}
    if t == "tool_use":
        return {"type": "tool_use", "id": b.get("id"), "name": b.get("name"),
                "input": _cut(json.dumps(b.get("input"), ensure_ascii=False, default=str), PART_CAP, cuts)}
    if t == "tool_result":
        c = b.get("content")
        inner = c if isinstance(c, str) else json.dumps(c, ensure_ascii=False, default=str)
        return {"type": "tool_result", "tool_use_id": b.get("tool_use_id"), "is_error": bool(b.get("is_error")),
                "content": _cut(inner, PART_CAP, cuts)}
    if t in ("image", "document"):
        return {"type": t, "note": "[file bytes not kept]"}
    if t in ("thinking", "redacted_thinking"):
        return {"type": t, "note": "[thinking not kept]"}
    return {"type": str(t), "text": _cut(json.dumps(b, ensure_ascii=False, default=str), PART_CAP, cuts)}


def shape(system: Any, tools: list | None, history: list[dict]) -> dict:
    """The row's body: masked system text, tool names, messages (each part capped)."""
    cuts: list = []
    if isinstance(system, list):
        sys_txt = "".join(str(b.get("text", "")) if isinstance(b, dict) else str(b) for b in system)
    else:
        sys_txt = str(system or "")
    names = []
    for t in tools or []:
        if isinstance(t, dict):
            n = t.get("name") or t.get("type") or "?"
            names.append(f"{n} (deferred)" if t.get("defer_loading") else str(n))
    hist = list(history or [])
    dropped = max(0, len(hist) - MSG_CAP)
    msgs, total = [], 0
    for m in reversed(hist[-MSG_CAP:]):            # newest first, so a budget cut drops the OLDEST messages
        c = m.get("content") if isinstance(m, dict) else m
        parts = [_part(x, cuts) for x in c] if isinstance(c, list) else [_part(c, cuts)]
        size = len(json.dumps(parts, ensure_ascii=False, default=str))
        if msgs and total + size > MSG_TOTAL_CAP:
            dropped += len(hist[-MSG_CAP:]) - len(msgs)
            break
        total += size
        msgs.append({"role": (m.get("role") if isinstance(m, dict) else "?"), "content": parts})
    msgs.reverse()
    sys_out = _cut(sys_txt, SYSTEM_CAP, cuts)
    sizes = {"system_chars": len(sys_txt), "tools": len(names),
             "tools_loaded": sum(1 for n in names if not n.endswith("(deferred)")),
             "messages": len(hist), "messages_dropped": dropped,
             "message_chars": sum(len(str(m.get("content"))) for m in hist if isinstance(m, dict)),
             "parts_cut": len(cuts)}
    return {"system": sys_out, "tools": names, "messages": msgs, "sizes": sizes}


# ---------------------------------------------------------------- write

def _where() -> tuple[str, str, str]:
    """(conversation, turn id, tenant) of the call being made, from the turn's own context vars."""
    conv = turn = tenant = ""
    try:
        from .convs import TURN
        conv = TURN.get() or ""
    except Exception:
        pass
    try:
        from .agent.eventlog import CURRENT
        turn = str((CURRENT.get() or {}).get("turn_id") or "")
    except Exception:
        pass
    try:
        from . import usage
        tenant = usage.current()[0] or ""
    except Exception:
        pass
    return conv, turn, tenant


def write(conv: str, turn_id: str, tenant: str, brain: str, model: str, max_tokens: int, system: Any,
          tools: list | None, history: list[dict], prep=None) -> int | None:
    """One row (sync - call it off the loop). Returns the row id, or None. Never raises.
    `prep` = the funnel's own message repair (santosh._api_ready), run here so the row holds what really went out."""
    if not conv:
        STATS["skipped"] += 1
        return None
    try:
        if prep is not None:
            try:
                history = prep(history)
            except Exception:
                pass
        from .config import get_settings
        keep = max(1, int(getattr(get_settings(), "request_dump_turns", 20) or 20))
        body = shape(system, tools, history)
        ensure_table()
        with session() as s:
            last = s.scalars(select(RequestDump).where(RequestDump.conversation_id == conv)
                             .order_by(RequestDump.id.desc()).limit(1)).first()
            if last is None:
                turn_no, step = 1, 1
            elif turn_id and last.turn_id == turn_id:
                turn_no, step = last.turn_no, last.step + 1
            else:
                turn_no, step = last.turn_no + 1, 1
            if not tenant:
                from .db import Conversation
                c = s.get(Conversation, conv)
                tenant = c.tenant_id if c else ""
            row = RequestDump(tenant_id=tenant or "", conversation_id=conv, turn_id=turn_id or "", turn_no=turn_no,
                              step=step, brain=str(brain or "")[:24], model=str(model or "")[:120],
                              max_tokens=int(max_tokens or 0), **body)
            s.add(row)
            s.flush()
            rid = row.id
            if turn_no > keep:
                s.execute(delete(RequestDump).where(RequestDump.conversation_id == conv,
                                                    RequestDump.turn_no <= turn_no - keep))
            if STATS["written"] % SWEEP_EVERY == 0:     # chats no one reads again do not grow the DB for ever
                from datetime import timedelta
                # v0.734: synchronize_session=False - the in-session evaluator compared a naive row time with the
                # aware cutoff and failed EVERY first write on her server ("can't compare offset-naive and
                # offset-aware datetimes"), so no request was ever dumped live; the sweep is plain SQL now
                cutoff = (now() - timedelta(days=KEEP_DAYS)).replace(tzinfo=None)
                s.execute(delete(RequestDump).where(RequestDump.created_at < cutoff)
                          .execution_options(synchronize_session=False))
        STATS["written"] += 1
        return rid
    except Exception as e:   # noqa: BLE001 - fail-open
        STATS["failed"] += 1
        log.warning("request dump not written: %s", str(e)[:200])
        return None


def finish(row_id: int | None, ok: bool, error: str = "") -> None:
    if not row_id:
        return
    try:
        with session() as s:
            r = s.get(RequestDump, row_id)
            if r is not None:
                r.ok = bool(ok)
                r.error = mask(error)[:500]
    except Exception:
        pass


_PENDING: set = set()


def start(brain: str, model: str, max_tokens: int, system: Any, tools: list | None, history: list[dict], prep=None):
    """From the funnel: schedules the write off the loop and returns a handle for `done()`. Never raises."""
    if not on():
        return None
    try:
        conv, turn, tenant = _where()
        if not conv:
            STATS["skipped"] += 1
            return None
        hist = list(history or [])
        fut = asyncio.get_running_loop().run_in_executor(
            None, write, conv, turn, tenant, brain, model, max_tokens, system, list(tools or []), hist, prep)
        _PENDING.add(fut)
        fut.add_done_callback(_PENDING.discard)
        return fut
    except Exception:
        return None


def done(handle, ok: bool, error: str = "") -> None:
    """Marks the step's row answered / failed once its write landed (off the loop). Never raises."""
    if handle is None:
        return
    try:
        loop = asyncio.get_running_loop()

        def _after(f):
            try:
                rid = f.result()
            except Exception:
                return
            if rid:
                g = loop.run_in_executor(None, finish, rid, ok, error)
                _PENDING.add(g)
                g.add_done_callback(_PENDING.discard)
        handle.add_done_callback(_after)
    except Exception:
        pass


async def drain() -> None:
    """Tests / the card: wait for the dump writes still in flight."""
    for _ in range(4):
        await asyncio.sleep(0)
        while _PENDING:
            await asyncio.gather(*list(_PENDING), return_exceptions=True)
            await asyncio.sleep(0)


# ---------------------------------------------------------------- read

def turns(conv: str, tenant: str) -> list[dict]:
    try:
        ensure_table()
        with session() as s:
            rows = s.scalars(select(RequestDump).where(RequestDump.conversation_id == conv,
                                                       RequestDump.tenant_id == tenant)
                             .order_by(RequestDump.id)).all()
            out: dict[int, dict] = {}
            for r in rows:
                t = out.setdefault(r.turn_no, {"turn": r.turn_no, "turn_id": r.turn_id, "steps": 0, "brains": [],
                                               "at": r.created_at.isoformat() if r.created_at else ""})
                t["steps"] += 1
                label = f"{r.brain}:{r.model}" if r.model else r.brain
                if label not in t["brains"]:
                    t["brains"].append(label)
            return list(out.values())
    except Exception:
        return []


def turn(conv: str, tenant: str, which: str) -> dict | None:
    """One turn's steps. `which` = the turn number (1..n, or -1 for the newest) or its turn id."""
    try:
        ensure_table()
        with session() as s:
            q = select(RequestDump).where(RequestDump.conversation_id == conv, RequestDump.tenant_id == tenant)
            w = str(which or "").strip()
            if w.lstrip("-").isdigit():
                n = int(w)
                if n < 0:
                    last = s.scalars(q.order_by(RequestDump.id.desc()).limit(1)).first()
                    if last is None:
                        return None
                    n = last.turn_no
                q = q.where(RequestDump.turn_no == n)
            else:
                q = q.where(RequestDump.turn_id == w)
            rows = s.scalars(q.order_by(RequestDump.step, RequestDump.id)).all()
            if not rows:
                return None
            return {"conversation_id": conv, "turn": rows[0].turn_no, "turn_id": rows[0].turn_id,
                    "steps": [{"step": r.step, "brain": r.brain, "model": r.model, "max_tokens": r.max_tokens,
                               "ok": r.ok, "error": r.error, "sizes": r.sizes, "tools": r.tools,
                               "system": r.system, "messages": r.messages,
                               "at": r.created_at.isoformat() if r.created_at else ""} for r in rows]}
    except Exception:
        return None
