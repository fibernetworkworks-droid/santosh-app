"""HOOLA CODER injection - the session-start primer (v0.473.0).

claude-mem's context primer, ported with the house ordering rules: her KAAM YAAD block stays
first (undelivered news outranks history); the coder primer rides AFTER it and NEVER displaces
it. Structure, in order: open work-state lists -> recent observations grouped by day -> the last
session summary -> a footer advertising the deeper layers.

Budget discipline is the point: the voice primer is capped at 10,000 chars (claude-mem's
CONTEXT_OUTPUT_LIMIT) and the chat-turn compact block at 1,600. When over budget, WHOLE items
drop in a fixed order (narratives first, then summaries, then older rows) - header and at least
one row always survive. Resume sessions inject nothing new (cache stability), matching voice's
resume path.
"""
from __future__ import annotations

import json
import time

from . import store

VOICE_BUDGET = 10_000
COMPACT_BUDGET = 1_600
HEADER = "CODER MEMORY (what was built here before; never ask her to repeat it):"


def _decode(r: dict) -> dict:
    for k in ("facts", "concepts", "files_read", "files_modified"):
        try:
            r[k] = json.loads(r.get(k) or "[]")
        except Exception:
            r[k] = []
    return r


def _work_lines() -> list[str]:
    out: list[str] = []
    try:
        for lst, items in store.work_read().items():
            for it in items[:8]:
                status = it.get("status") or "todo"
                mark = "[todo]" if status == "todo" else "[doing]"
                out.append(f"- {mark} {str(it.get('text', ''))[:160]}")
    except Exception:
        pass
    return out


def _row(r: dict, full: bool = False) -> str:
    day = str(r.get("created_at", ""))[:10]
    line = f"{r['id']} ({day}) {r['type']}: {r['title']}"
    if full:
        facts = "; ".join(r.get("facts") or [])[:400]
        if facts:
            line += f"\n    {facts}"
    return line


def _fit(items_full: list[str], items_plain: list[str], summary_block: str, header: str,
         footer: str, budget: int) -> str:
    """Whole-item fitter: drop full narratives first, then the summary, then plain rows."""
    parts = [header] + items_plain + ([summary_block] if summary_block else []) + [footer]
    if len("\n".join(parts)) <= budget:
        return "\n".join(parts)
    # add full narratives one by one while they fit
    base = [header] + items_plain + [footer]
    if len("\n".join(base)) <= budget:
        for i, full in enumerate(items_full):
            trial = [header] + items_plain[:i + 1] + [footer]
            if len("\n".join(trial)) > budget:
                break
        parts = [header] + items_plain + [footer]
    # still over: halve the plain rows (>=1 always survives), then drop the summary
    while len("\n".join([header] + items_plain + [footer])) > budget and len(items_plain) > 1:
        items_plain = items_plain[:max(1, len(items_plain) // 2)]
    parts = [header] + items_plain + [footer]
    if len("\n".join(parts)) > budget:
        parts = [header, items_plain[0] if items_plain else "", footer]
    return "\n".join(p for p in parts if p)[:budget]


def primer(tenant: str, conv: str | None = None, compact: bool = False) -> str:
    """The block. compact=True is the per-chat-turn version (small); voice uses the full 10k."""
    budget = COMPACT_BUDGET if compact else VOICE_BUDGET
    try:
        store.ensure()
    except Exception:
        return ""
    header = HEADER
    work = _work_lines()
    if work:
        header += "\nStill open:\n" + "\n".join(work[:6])
    limit = 6 if compact else 30
    rows = store.recent_observations(tenant, limit=limit, conv=conv)
    if not rows and not work:
        return ""
    rows = [_decode(r) for r in rows]
    plain = [_row(r) for r in rows]
    full = [_row(r, full=True) for r in rows]
    s = store.last_summary(tenant, conv)
    summary_block = ""
    if s and not compact:
        summary_block = "Last session: " + " | ".join(
            f"**{k}**: {s[k][:220]}" for k in ("investigated", "completed", "next_steps") if s.get(k))
    footer = ("Details via coder memory tools: search the index first (GET /api/coder/search), "
              "timeline around an id, then full rows by id. Filter before you fetch.")
    return _fit(full, plain, summary_block, header, footer, budget)


def turn_block(tenant: str, conv: str) -> str:
    """The compact per-chat-turn block (rides beside yaad.turn_block, never instead of it)."""
    try:
        from ..config import get_settings
        if not getattr(get_settings(), "coder_enabled", True):
            return ""
        return primer(tenant, conv=None, compact=True)
    except Exception:
        return ""


def voice_block(tenant: str, conv: str) -> str:
    """The full call-start block (rides after the KAAM YAAD block in the voice context)."""
    try:
        from ..config import get_settings
        if not getattr(get_settings(), "coder_enabled", True):
            return ""
        return primer(tenant, conv=conv, compact=False)
    except Exception:
        return ""
