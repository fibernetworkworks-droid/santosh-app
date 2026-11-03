"""HOOLA CODER modes - the taxonomy is data, not code (v0.473.0).

claude-mem's modes lesson, ported whole: WHAT the observer records (the observation types, the
knowledge concepts) and HOW it words things (the prompt fragments) live in a mode object, not in
logic. The builtin mode is `code` (English); a JSON file dropped in coder_dir/modes/<name>.json
overrides any fragment, so a Hinglish mode or a law-study mode is a file, never a release.

Only the observer's prompts and taxonomy change - never the session, the tools, or her language.
"""
from __future__ import annotations

import json
import logging
import os

log = logging.getLogger("coder.modes")

BUILTIN_CODE = {
    "name": "code",
    "observation_types": [
        {"id": "bugfix", "icon": "\U0001f41b"},
        {"id": "feature", "icon": "\u2728"},
        {"id": "refactor", "icon": "\U0001f527"},
        {"id": "change", "icon": "\U0001f4dd"},
        {"id": "discovery", "icon": "\U0001f50d"},
        {"id": "decision", "icon": "\U0001f3af"},
        {"id": "security_alert", "icon": "\U0001f6a8"},
        {"id": "security_note", "icon": "\U0001f512"},
        {"id": "sensitive", "icon": "\u26a0\ufe0f"},
    ],
    "observation_concepts": [
        "how-it-works", "why-it-exists", "what-changed", "problem-solution", "gotcha", "pattern",
        "trade-off",
    ],
    "prompts": {
        "system_identity": (
            "You are the HOOLA CODER observer, a specialized note-taker creating searchable memory "
            "FOR FUTURE SESSIONS of this project.\n\n"
            "CRITICAL: Record what was LEARNED/BUILT/FIXED/DEPLOYED/CONFIGURED, not what you (the "
            "observer) are doing.\n\n"
            "You do not have access to tools. All information you need arrives in "
            "<observed_from_santosh_session> messages. Create observations from what you observe - "
            "no investigation needed."),
        "observer_role": (
            "Your job is to monitor a Santosh agent session happening RIGHT NOW. You are NOT the one "
            "doing the work - you are ONLY observing. SILENT BY DESIGN: the session you are watching "
            "does not know it is being observed. NO CONTACT: never contact, message, ping or notify "
            "anyone. You are a one-way recorder: observations in, XML out, nothing else."),
        "recording_focus": (
            "Focus on durable technical signal: what the system NOW DOES differently. Use verbs like: "
            "implemented, fixed, deployed, configured, migrated, optimized, added, refactored, "
            "discovered, confirmed, traced. Before writing an observation, check your own prior "
            "messages: if you already recorded the same fact, do not record it again. Good: "
            "'Authentication now supports OTP retry with a 3-attempt cap'. Bad: 'Analyzed "
            "authentication implementation and stored findings'."),
        "skip_guidance": (
            "Skip routine operations: a fact you already recorded, empty status checks, simple file "
            "listings, package installs with no errors. If skipping, reply with exactly "
            "<skip_summary reason=\"noise\" />. Never reply with an empty response."),
        "field_guidance": (
            "facts: concise self-contained statements, one fact per element, no pronouns, include "
            "filenames/functions/values. narrative: the full context - what was done, how it works, "
            "why it matters. files: full paths from the project root when known."),
        "footer": (
            "IMPORTANT! Do no work right now other than generating OBSERVATIONS from the tool-use "
            "messages. Never reference yourself or your own actions. Spend your tokens wisely."),
        "summary_instruction": (
            "Write progress notes of what was done, what was learned, and what is next. This is a "
            "checkpoint at the end of a session. Write 'next_steps' as the current trajectory of the "
            "work. Always write at least a minimal summary."),
    },
}

_TYPES = {t["id"] for t in BUILTIN_CODE["observation_types"]}
_CONCEPTS = set(BUILTIN_CODE["observation_concepts"])


def modes_dir() -> str:
    import os
    from ..config import get_settings
    d = os.path.join(getattr(get_settings(), "coder_dir", "./data/coder") or "./data/coder", "modes")
    os.makedirs(d, exist_ok=True)
    return d


def load_mode(name: str | None = None) -> dict:
    """Builtin `code` mode, deep-merged with an optional override file. Never raises."""
    from ..config import get_settings
    want = name or getattr(get_settings(), "coder_mode", "code") or "code"
    mode = json.loads(json.dumps(BUILTIN_CODE))          # deep copy
    if want == "code":
        return mode
    try:
        p = os.path.join(modes_dir(), f"{want}.json")
        if os.path.exists(p):
            with open(p, encoding="utf-8") as f:
                over = json.load(f)
            for k, v in over.items():
                if k == "prompts" and isinstance(v, dict):
                    mode["prompts"].update(v)
                else:
                    mode[k] = v
            mode["name"] = want
    except Exception:
        log.exception("coder mode %s failed to load - the builtin code mode stays", want)
    return mode


def valid_type(t: str, mode: dict) -> bool:
    ids = {x["id"] for x in mode.get("observation_types", [])} or _TYPES
    return t in ids


def valid_concepts(cs: list[str], mode: dict) -> list[str]:
    allowed = set(mode.get("observation_concepts", [])) or _CONCEPTS
    return [c for c in cs if c in allowed]
