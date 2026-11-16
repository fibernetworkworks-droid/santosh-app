"""P1 LEVELS (plan section 3): how a part of an ask gets its level - code only, no model call.

  start level per kind (3.1) + one raise per signal (3.2) -> limits (3.3):
    her choice wins; a part she waits for on a live call stops at HIGH; ULTRA only when she asked for it, a MAX try
    failed the check, or the job is both hard AND costly; inside one message the level never goes down (floor).

Pure: the same text + the same context always give the same level and the same reasons.
"""
from __future__ import annotations

import re
from typing import Any

from .kinds import LEVELS

# 3.1 starting level per kind of work (a kind not listed starts at MID - everyday work)
START = {
    "route": "LOW", "plan": "LOW", "extract": "LOW", "summarise": "LOW", "embed": "LOW", "speech.in": "LOW",
    "speech.in.indian": "LOW",
    "chat": "MID", "write": "MID", "translate": "MID", "research": "MID", "read.pdf": "MID", "read.image": "MID",
    "check": "MID", "code.small": "MID", "speech.out": "MID", "speech.out.indian": "MID", "image.make": "MID",
    "image.edit": "MID", "music.make": "MID",
    "reason": "HIGH", "tools": "HIGH", "code": "HIGH", "read.long": "HIGH", "facts": "HIGH", "video.make": "HIGH",
}
INDIAN = {"hi", "mr", "bn", "ta", "te", "kn", "ml", "gu", "pa", "or", "ur", "as", "sa", "ne", "kok", "mai"}

# 3.2 the signals. Each raises a part ONE level.
COSTLY = re.compile(
    r"(?i)\b(paisa|paise|payment|pay\b|refund|invoice|bill\b|gst|tax|itr|tds|income tax|audit|loan|emi|salary|"
    r"payroll|bank|upi|transfer|contract|agreement|legal|lawyer|court|notice|fir\b|compliance|medical|medicine|"
    r"dose|doctor|diagnos\w*|prescription|symptom\w*|deploy\w*|production|go live|live karo|merge|"
    r"customers?\b|clients?\b|grahak|campaign|bulk|sab ko bhej\w*|all (?:my )?customers)")
EXACT = re.compile(
    r"(?i)(\b\d[\d,]*(?:\.\d+)?\s*(?:%|lakh|crore|rs\b|inr|usd|\$|kg|km)|₹\s*\d|\bexact\w*\b|\bsahi (?:number|figure|"
    r"amount|date)\b|\bkitn[aeiy]\b|\bhow (?:much|many)\b|\bprice\w*\b|\brate\b|\bdate\b|\bdeadline\b|\bfigures?\b|"
    r"\bstatistic\w*\b|\bdata\b)")
DEEP = re.compile(r"(?i)\b(deep|detailed|in.depth|thorough|gehra[iy]?|vistaar|poori research|full research|"
                  r"comprehensive|exhaustive|report)\b")
LONG_WORDS = 400                       # an input this long is a big job on its own
BIG_PARTS = 3                          # several things asked at once


# a signal that is what made the kind does not raise it again (a hard ask is `reason` because it is hard; research
# gathers facts with sources and is checked against them - plan 11 keeps five-company research at MID)
INHERENT = {"reason": {"hard", "exact"}, "facts": {"exact"}, "research": {"hard", "exact"}, "code": {"exact"},
            "code.small": {"exact"}, "image.make": {"exact"}, "image.edit": {"exact"}, "video.make": {"exact"},
            "music.make": {"exact"}, "speech.out": {"exact"}, "speech.out.indian": {"exact"}}


def for_kind(kind: str, sigs: list[str]) -> list[str]:
    drop = INHERENT.get(kind, set())
    return [s for s in sigs if s not in drop]


def _num(level: str) -> int:
    return LEVELS.index(level)


def start_level(kind: str, language: str = "") -> str:
    if kind == "write.lang" and (language or "").lower() in INDIAN:
        return "HIGH"                  # 3.1: long writing in an Indian language starts high
    return START.get(kind, "MID")


def signals(text: str, *, parts: int = 1, input_words: int = 0, failed_check: bool = False,
            costly: bool | None = None, hard: bool | None = None) -> list[str]:
    """3.2 - which signals this part shows, in a fixed order. `hard` / `costly` may be given by the caller (already
    known); otherwise read from her words (hard = the hard-ask check Hoola already has)."""
    t = str(text or "")
    out: list[str] = []
    if hard is None:
        try:
            from ..agent import hard as H
            a = H.assess(t)
            hard, deep_research = bool(a.get("hard")), "research" in (a.get("why") or [])
        except Exception:   # noqa: BLE001 - the check never blocks choosing
            hard, deep_research = False, False
    else:
        deep_research = False
    if hard:
        out.append("hard")
    words = len(t.split())
    if parts >= BIG_PARTS or max(input_words, words) >= LONG_WORDS:
        out.append("big")
    if costly if costly is not None else bool(COSTLY.search(t)):
        out.append("costly")
    if EXACT.search(t):
        out.append("exact")
    if deep_research and DEEP.search(t):
        out.append("deep_research")
    if failed_check:
        out.append("failed_check")
    return out


def level_for(kind: str, sigs: list[str], *, language: str = "", her_level: str = "", her_ultra: bool = False,
              call_waiting: bool = False, max_failed: bool = False, floor: str = "") -> dict[str, Any]:
    """The level for one part + the reasons, in order. Never below `floor` (the level this part already reached in
    this message - 3.3: the level only goes up inside one message)."""
    why: list[str] = []
    if her_level:
        lv = her_level.upper()
        if lv not in LEVELS:
            raise ValueError(f"unknown level {her_level!r}")
        return {"level": lv, "start": start_level(kind, language), "why": [f"she chose {lv}"], "signals": sigs}
    start = start_level(kind, language)
    n = _num(start)
    why.append(f"{kind} starts at {start}")
    for s in sigs:
        if n < _num("ULTRA"):
            n += 1
            why.append(f"{s} -> {LEVELS[n]}")
    ultra_ok = her_ultra or max_failed or ("hard" in sigs and "costly" in sigs)
    if her_ultra:
        n = _num("ULTRA")
        why.append("she asked for the best -> ULTRA")
    elif max_failed:
        n = _num("ULTRA")
        why.append("a MAX try failed the check -> ULTRA")
    if n == _num("ULTRA") and not ultra_ok:
        n = _num("MAX")
        why.append("ULTRA only when she asks, a MAX try failed, or hard and costly -> MAX")
    if call_waiting and n > _num("HIGH") and not her_ultra:
        n = _num("HIGH")
        why.append("she is waiting on a live call -> HIGH at most")
    if floor and floor.upper() in LEVELS and n < _num(floor.upper()):
        n = _num(floor.upper())
        why.append(f"already at {floor.upper()} in this message -> never lower")
    return {"level": LEVELS[n], "start": start, "why": why, "signals": sigs}


def up_one(level: str) -> str:
    return LEVELS[min(_num(level) + 1, len(LEVELS) - 1)]
