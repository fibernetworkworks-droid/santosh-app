"""HOOLA CODER injection - the session-start primer (v0.478.0).

claude-mem's context primer, ported with the house ordering rules: her KAAM YAAD block stays
first (undelivered news outranks history); the coder primer rides AFTER it and NEVER displaces
it. Structure, in order: open work-state lists -> recent observations grouped by day -> the last
session summary -> a footer advertising the deeper layers.

Budget discipline is the point: the voice primer is capped at 10,000 chars (claude-mem's
CONTEXT_OUTPUT_LIMIT) and the chat-turn compact block at 1,600. When over budget, WHOLE items
drop in a fixed order (narratives first, then summaries, then older rows) - header and at least
one row always survive. Resume sessions inject nothing new (cache stability), matching voice's
resume path.

v0.484 SKILL DESK hooks: every matched skill that rides the block marks the telemetry ledger
(kind='shown' - the desk's usage column and the share nominations' evidence), a skill the
telemetry saw recently (30 days) outranks an equally-ranked cold one, a PARKED skill (the
owner's enabled=false) never rides at all, and child_skills() gives a swarm worker the same
matched-skills lines inside its own 400-char budget (it reads the full skill itself via
skill_manage, which a child owns - the same read-before-follow law).
"""
from __future__ import annotations

import json
import time

from . import store

VOICE_BUDGET = 10_000
COMPACT_BUDGET = 1_600
SKILLS_VOICE_BUDGET = 1_200      # v0.477 the matched-skills carve-out inside the coder block
SKILLS_COMPACT_BUDGET = 400
HEADER = "CODER MEMORY (what was built here before; never ask her to repeat it):"


def _skills_enabled() -> bool:
    try:
        from ..config import get_settings
        return bool(getattr(get_settings(), "coder_enabled", True)
                    and getattr(get_settings(), "coder_skills", True))
    except Exception:
        return False


def _line(r: dict) -> str:
    """One injected skill line. An imported skill's description can run to 1,024 chars (Claude's
    limit) - the prompt carries only the first 110; skill_manage read gives the rest."""
    d = " ".join(str(r.get("description") or "").split())
    if len(d) > 110:
        d = d[:107].rstrip() + "..."
    return f"- {r['name']}: {d}"


def _matched(tenant: str, query: str, limit: int = 4) -> list[dict]:
    """The matched skills, FTS-ranked, with the recency boost on top: a skill telemetry saw in
    the last 30 days outranks an equally-ranked cold one (used beats written). Disabled rows
    never leave the store."""
    try:
        rows = store.skills_search(tenant, query, limit=limit)
    except Exception:
        return []
    if not rows:
        return []
    try:
        hot = store.skill_recent(tenant, 30)
        if hot:
            rows.sort(key=lambda r: r["name"] not in hot)   # stable: rank order kept inside each class
    except Exception:
        pass
    return rows[:2]


def skills_block(tenant: str, query: str, compact: bool = False, conv: str = "",
                 surface: str = "") -> str:
    """Top matched LEARNED SKILLS for the current ask (zero model calls - pure FTS5). Name +
    description only: she reads the full skill via skill_manage before following it (Hermes's
    read-before-follow discipline). Empty on no match, empty query or the switch off.
    v0.481: every shown match lands in the telemetry ledger (fail-open bookkeeping)."""
    if not query or not _skills_enabled():
        return ""
    rows = _matched(tenant, query)
    if not rows:
        return ""
    for r in rows:
        store.skill_use_mark(tenant, r["name"], "shown", conv=conv, surface=surface)
    lines = [_line(r) for r in rows]
    block = ("LEARNED SKILLS matching this ask (skill_manage read the skill before you follow "
             "it):\n" + "\n".join(lines))
    return block[:SKILLS_COMPACT_BUDGET if compact else SKILLS_VOICE_BUDGET]


def child_skills(tenant: str, query: str, budget: int = 400) -> str:
    """v0.484 the swarm worker's carve-out: the same matched-skills lines inside the child's own
    budget, telling it to read the full skill via skill_manage (a child owns the tool - the
    read-before-follow law survives delegation). Zero model cost, fail-open."""
    if not query or not _skills_enabled():
        return ""
    try:
        rows = store.skills_search(tenant, query, limit=2)
    except Exception:
        return ""
    if not rows:
        return ""
    lines = [_line(r) for r in rows]
    block = ("LEARNED SKILLS for this task (skill_manage read a skill before you follow it):\n"
             + "\n".join(lines))
    return block[:budget]


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


def primer(tenant: str, conv: str | None = None, compact: bool = False, query: str = "") -> str:
    """The block. compact=True is the per-chat-turn version (small); voice uses the full 10k.
    query is her current ask: matched skills ride at the TOP of the coder block (how-to outranks
    what-was-built), inside the same budget, never displacing the header."""
    budget = COMPACT_BUDGET if compact else VOICE_BUDGET
    try:
        store.ensure()
    except Exception:
        return ""
    header = HEADER
    sk = skills_block(tenant, query, compact=compact, conv=conv or "",
                      surface="voice" if not compact else "chat")
    if sk:
        header += "\n" + sk
    work = _work_lines()
    if work:
        header += "\nStill open:\n" + "\n".join(work[:6])
    limit = 6 if compact else 30
    rows = store.recent_observations(tenant, limit=limit, conv=conv)
    if not rows and not work and not sk:
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


def turn_block(tenant: str, conv: str, query: str = "") -> str:
    """The compact per-chat-turn block (rides beside yaad.turn_block, never instead of it).
    query = her current ask, for the matched-skills lines."""
    try:
        from ..config import get_settings
        if not getattr(get_settings(), "coder_enabled", True):
            return ""
        return primer(tenant, conv=None, compact=True, query=query)
    except Exception:
        return ""


def voice_block(tenant: str, conv: str, query: str = "") -> str:
    """The full call-start block (rides after the KAAM YAAD block in the voice context)."""
    try:
        from ..config import get_settings
        if not getattr(get_settings(), "coder_enabled", True):
            return ""
        return primer(tenant, conv=conv, compact=False, query=query)
    except Exception:
        return ""
