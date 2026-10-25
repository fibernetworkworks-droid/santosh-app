"""v0.173 PC operator memory: what Santosh recently did on this person's PC survives between tasks,
so she never starts from zero (owner, 25 Oct 2026: "WhatsApp Chrome mein khola tha, Hoola ne dobara
Edge mein khol diya" — ab nahi karega). One row per tenant; only the last pc_memory_runs finished
tasks are kept, and every entry dies after pc_memory_hours."""
from __future__ import annotations

import time
from typing import Any

from sqlalchemy import select

from ..config import get_settings
from ..db import PcMemory, session

PROMPT_RUNS = 6          # at most this many entries go into the operator's system prompt


def _caps() -> tuple[int, int]:
    st = get_settings()
    try:
        runs, hours = int(st.pc_memory_runs), int(st.pc_memory_hours)
    except (TypeError, ValueError):
        runs, hours = 8, 24
    return max(1, runs), max(1, hours)


def remember(tenant_id: str, task: str, actions: list[str], status: str, answer: str, window: str) -> None:
    """Called when an operator run ends (any outcome). Never raises into the caller."""
    runs, _hours = _caps()
    entry: dict[str, Any] = {"t": int(time.time()), "task": (task or "").strip()[:220],
                             "did": [str(a).strip()[:120] for a in (actions or []) if str(a).strip()][:14],
                             "status": status or "done", "answer": (answer or "").strip()[:260],
                             "window": (window or "").strip()[:120]}

    from .service import _bg

    def w() -> None:
        with session() as s:
            row = s.scalars(select(PcMemory).where(PcMemory.tenant_id == tenant_id)).first()
            data = list(row.entries or []) if row is not None else []
            data.append(entry)
            if row is None:
                row = PcMemory(tenant_id=tenant_id, entries=data[-runs:])
                s.add(row)
            else:
                row.entries = data[-runs:]        # reassign: JSON columns only track whole-value changes
            row.updated_at = row.updated_at       # onupdate fires on any change
    _bg(w)


def recall(tenant_id: str) -> list[dict[str, Any]]:
    """Surviving entries (oldest first), TTL applied."""
    _runs, hours = _caps()
    cutoff = time.time() - hours * 3600
    with session() as s:
        row = s.scalars(select(PcMemory).where(PcMemory.tenant_id == tenant_id)).first()
        data = list(row.entries or []) if row is not None else []
    return [e for e in data if isinstance(e, dict) and int(e.get("t") or 0) >= cutoff]


def forget(tenant_id: str) -> None:
    """PC removed (unpair): her memory of that PC goes with it."""
    from sqlalchemy import delete
    from .service import _bg

    def w() -> None:
        with session() as s:
            s.execute(delete(PcMemory).where(PcMemory.tenant_id == tenant_id))
    _bg(w)


def _ago(ts: int) -> str:
    m = max(0, int((time.time() - ts) / 60))
    return "abhi" if m < 1 else f"{m} min pehle" if m < 120 else f"{m // 60} ghante pehle"


def prompt_block(tenant_id: str) -> str:
    """The YAAD block for the operator's system prompt ('' when there is nothing to remember)."""
    entries = recall(tenant_id)[-PROMPT_RUNS:]
    if not entries:
        return ""
    lines = []
    for e in reversed(entries):                    # newest first
        did = "; ".join(e.get("did") or []) or "screen dekhi"
        line = f'- ({_ago(int(e.get("t") or 0))}) Task: "{e.get("task", "")}". You did: {did}. ' \
               f'Result ({e.get("status", "done")}): "{e.get("answer", "")}"'
        if e.get("window"):
            line += f'. Last active window: "{e["window"]}"'
        lines.append(line)
    return ("YAAD - your own recent finished work on THIS PC (newest first). It is probably still open on the "
            "screen; build on it, never redo it:\n" + "\n".join(lines))
