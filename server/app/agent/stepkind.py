"""v0.863 R3s (docs/HOOLA_APP_REDESIGN_PLAN.md): what KIND of step a tool step is, said by the server.

The new phone chat draws one icon per step and hides Hoola's own housekeeping (loading tools, planning, checking its
own answer) from the "Used N steps" count. Until now the phone guessed both from the label's words. Every `step`
event now carries:

  kind          search | read | write | edit | web | run | agent | skill | question | card | memory | other
  housekeeping  True for steps Hoola does for itself, not for her (tool search, plan, self-check, memory lookups)

Added in ONE place (events.bus.publish), so every publisher - the main loop, crews, research, the answer check - gets
it without being touched. Old phones ignore the two extra fields. Pure functions, no I/O.
"""
from __future__ import annotations

import re

KINDS = ("search", "read", "write", "edit", "web", "run", "agent", "skill", "question", "card", "memory", "other")

# tools that are Hoola working on its own process, not on her ask
HOUSEKEEPING = {
    "tool_search", "kaam_plan", "jaanch", "plan", "think", "skill_manage", "kaam_status", "officehours_dekho",
    "yaad_khojo", "haal_ki_chats", "remember", "forget", "data_note",
}
HOUSEKEEPING_PREFIX = ("toolsearch", "mcp_list")

# (pattern on the tool name, kind) - first match wins; the label is the fallback
_BY_TOOL: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"^agent:|^crew|team|delegate|_crew$|subagent"), "agent"),
    (re.compile(r"^skill|^kala$|uiux|speckit"), "skill"),
    (re.compile(r"yaad|remember|forget|memory|^coder_"), "memory"),
    (re.compile(r"ask_user|_ask$|question|ask_form|officehours$"), "question"),
    (re.compile(r"approv|confirm|_card$|payment|upi|_send$|send_|bulk|campaign|_draft$|draft_"), "card"),
    (re.compile(r"search|khoj|find|lookup|_list$|dekho$|nearby|_nearest"), "search"),
    (re.compile(r"web|browse|scrape|crawl|fetch|reach|duniya|jharokha|url|site|maps"), "web"),
    (re.compile(r"pylab|python|run|exec|calc|compute|shell|code|devlab|bhandar"), "run"),
    (re.compile(r"edit|update|patch|rename|move|replace|fix"), "edit"),
    (re.compile(r"read|open|get_|_get$|fetch|download|view|pdf|file|drive|sheet|doc"), "read"),
    (re.compile(r"make|create|write|build|generate|banao|studio|artifact|frames|image|video|music|report"), "write"),
]

_BY_LABEL: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bagent|team|helper"), "agent"),
    (re.compile(r"search|looking up|finding|khoj"), "search"),
    (re.compile(r"website|web page|browser|internet|online"), "web"),
    (re.compile(r"reading|opening|read |checking the file"), "read"),
    (re.compile(r"writing|drafting|making|creating|building"), "write"),
    (re.compile(r"editing|updating|changing|fixing"), "edit"),
    (re.compile(r"running|calculat|python|code"), "run"),
    (re.compile(r"asking|question|waiting for your"), "question"),
    (re.compile(r"remember|memory"), "memory"),
]


def classify(tool: str, label: str = "") -> tuple[str, bool]:
    """(kind, housekeeping) for one step. Never raises; unknown = ('other', False)."""
    t = str(tool or "").strip().lower()
    base = t.split(":", 1)[0] if not t.startswith("agent:") else t
    house = base in HOUSEKEEPING or base.startswith(HOUSEKEEPING_PREFIX) or base == "jaanch"
    if base in ("jaanch", "tool_search", "kaam_plan"):
        return ("other" if base != "kaam_plan" else "write", True)
    for rx, kind in _BY_TOOL:
        if rx.search(t):
            return kind, house
    lab = str(label or "").lower()
    for rx, kind in _BY_LABEL:
        if rx.search(lab):
            return kind, house
    return "other", house


def enrich(payload: object) -> object:
    """Add kind / housekeeping to a step payload in place (only when absent). Returns the payload."""
    if isinstance(payload, dict) and payload.get("tool") is not None:
        try:
            kind, house = classify(str(payload.get("tool") or ""), str(payload.get("label") or ""))
            payload.setdefault("kind", kind)
            payload.setdefault("housekeeping", house)
        except Exception:   # a display hint must never break publishing
            pass
    return payload
