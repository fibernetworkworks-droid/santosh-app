"""v0.451 ECC PHASE 4 - how much ceremony this piece of work deserves, and the plan card's own text.

Adapted from ECC's `orch-pipeline` skill (MIT, github.com/affaan-m/ECC): "Ceremony scales to blast radius. Score the
request on three signals, take the HIGHEST tier any signal reaches, and state the result in one line so the user can
override." Their tiers and the tie-breaker (anything touching a security trigger or a public API / contract is AT LEAST
standard) are kept; the signals are read from HER ask in CODE here, because the tier has to be known before any model
call so that a small job costs nothing extra.

  trivial   one obvious thing          -> straight to work, nothing shown (an explain, a typo, one named file)
  small     one file / one function    -> straight to work
  standard  2-5 files, one real choice -> a read-only PLAN pass first; the plan is SHOWN and the work starts at once
  large     cross-cutting / ambiguous  -> plan pass, and the work WAITS for her Haan (ECC's Gate 1)

Hoola's deviation from ECC, on purpose: ECC gates `standard` too. Here the owner's own rule is "no back-and-forth", and
opening the PR already needs her tap (that is ECC's Gate 2), so only `large` stops. `dev_plan_gate` off = nothing ever
waits; `dev_plan_first` off = no plan pass at all."""
from __future__ import annotations

import re
from typing import Any

TIERS = ("trivial", "small", "standard", "large")

# a trust boundary / a contract other code or other people depend on: ECC's tie-breaker, in her words and in English
TRIGGER = re.compile(r"(?i)\b(auth|authe?nticat\w*|login|logout|signup|sign-?in|password|passwd|token|jwt|session|"
                     r"permission|role|admin|secret|key|encrypt\w*|decrypt\w*|payment|pay|upi|razorpay|stripe|refund|"
                     r"invoice|gst|price|pricing|billing|checkout|webhook|migration|migrate|schema|database|db|"
                     r"public api|api|endpoint|route|contract|aadhaar|pan|otp|kyc|bank|paisa|paise|rupee|suraksha)\b")
# words that mean "the whole thing", in Hinglish and English
WIDE = re.compile(r"(?i)\b(poora|pura|sab|saara|sara|whole|entire|all|every|complete|completely|end.to.end|"
                  r"refactor\w*|rewrite|redesign|re-?architect|migrat\w*|overhaul|system|module|pipeline|revamp)\b")
# "something is wrong, you work out what" - no symptom, no file, no error
VAGUE = re.compile(r"(?i)\b(theek karo|thik karo|sahi karo|dekh lo|dekho zara|kuch gadbad|gadbad hai|kaam nahi kar|"
                   r"behtar|better|improve|improv\w*|optimi[sz]e|clean ?up|tidy|nicer|acchha karo|achha karo)\b")
SMALLISH = re.compile(r"(?i)\b(chhot[aiy]|chota|ek|sirf|simple|saral|helper|function|method|button|label|text|typo|"
                      r"spelling|rename|comment|constant|tiny|small|single|one)\b")
ERRORY = re.compile(r"(?i)(traceback|exception|error|errno|stack ?trace|\bline \d+|\.py[:\s]|\.ts[:\s]|\.js[:\s]|"
                    r"\.dart[:\s]|\.kt[:\s]|[A-Z][A-Za-z]*Error|[A-Z][A-Za-z]*Exception|\b4\d\d\b|\b5\d\d\b)")
# she listed several things: "a, b aur c", "1. x 2. y", bullet lines
AND_PARTS = re.compile(r"(?i)(,|;|\baur\b|\band\b|\+|\n\s*[-*•]|\n\s*\d+[.)])")


def _parts(text: str) -> int:
    """How many things the ask asks for. A colon list ("X banao: a, b, c") counts its items, else the joiners."""
    body = text.split(":", 1)[1] if ":" in text[:120] and len(text.split(":", 1)) > 1 else text
    n = len(AND_PARTS.findall(body)) + 1
    return min(n, 9)


def _rank(name: str) -> int:
    return TIERS.index(name)


def assess(kind: str, text: str, files: list[str] | None = None, issue_txt: str = "") -> dict[str, Any]:
    """(tier, why) for this ask - no model call. The highest tier any signal reaches wins, exactly like ECC's table."""
    text = (text or "").strip()
    named = [f for f in (files or []) if f]
    all_txt = f"{text}\n{issue_txt or ''}"
    parts, trigger = _parts(text), bool(TRIGGER.search(all_txt))
    wide, vague = bool(WIDE.search(text)), bool(VAGUE.search(text))
    errory = bool(ERRORY.search(all_txt))
    why: list[str] = []
    tier = "small"
    if kind == "explain":
        return {"tier": "trivial", "why": ["an explain task: no change"], "parts": parts, "trigger": trigger}
    if kind == "docs":
        tier = "trivial" if len(named) == 1 or parts <= 1 else "small"
        why.append("a docs task")
    elif kind == "fix":
        tier = "small" if (errory or named) and parts <= 2 else "standard"
        why.append("the error / file is stated clearly" if errory or named else "have to find where the bug is")
    elif kind == "tests":
        tier = "small" if named else "standard"
        why.append("the files that need tests are named" if named else "have to find which code needs tests")
    else:                                   # write
        small_ask = parts <= 1 and not trigger and not wide and (named or bool(SMALLISH.search(text)))
        tier = "small" if small_ask else "standard"
        why.append("one small new piece" if small_ask else "new code has to be written")
    if parts >= 3 and _rank(tier) < _rank("standard"):
        tier = "standard"
        why.append(f"{parts} things asked for at once")
    elif parts >= 3:
        why.append(f"{parts} things asked for at once")
    if trigger and _rank(tier) < _rank("standard"):     # ECC's tie-breaker
        tier = "standard"
    if trigger:
        why.append("it touches a part like login / money / API, so at least 'standard'")
    if wide and kind != "docs":
        tier = "large"
        why.append("it is about the whole system / a refactor")
    if parts >= 4:
        tier = "large"
        why.append("it has many parts")
    if vague and _rank(tier) < _rank("standard"):
        tier = "standard"                               # a vague ask is NOT made 'large': v0.371 POOCHH LO already
        why.append("the task is open-ended")                    # answers it with ONE question instead of guessing
    if kind == "docs" and _rank(tier) > _rank("small"):
        tier = "small"                                  # docs never becomes a cross-cutting change
    return {"tier": tier, "why": why[:4], "parts": parts, "trigger": trigger, "wide": wide, "vague": vague,
            "errory": errory, "named": len(named)}


def needs_plan(tier: str) -> bool:
    return _rank(tier) >= _rank("standard")


def waits(tier: str) -> bool:
    return tier == "large"


def as_text(plan: dict[str, Any]) -> str:
    """The approved plan, as the edit loop is shown it (ECC: 'the planning docs ARE the handoff')."""
    if not plan:
        return ""
    out = [f"<approved_plan>\nGoal: {plan.get('goal', '')}"]
    if plan.get("files"):
        out.append("Files: " + "; ".join(f"{f.get('path')} ({f.get('why')})" for f in plan["files"][:30]))
    if plan.get("steps"):
        out.append("Steps, in order:\n" + "\n".join(f"{i}. {s}" for i, s in enumerate(plan["steps"][:20], 1)))
    if plan.get("done_when"):
        out.append("DONE WHEN (these are the acceptance criteria - the work is not finished until every one of them is "
                   "true, and if one cannot be met you say so in risk instead of dropping it quietly):\n"
                   + "\n".join(f"- {d}" for d in plan["done_when"][:12]))
    if plan.get("risk"):
        out.append("Known risk: " + str(plan["risk"]))
    if plan.get("note"):
        out.append("What SHE said about this plan (follow it): " + str(plan["note"]))
    out.append("This plan was approved. Follow it; do not widen the work. If the repo turns out different from the plan, "
               "do the smaller honest thing and say what changed in risk.\n</approved_plan>")
    return "\n".join(out)


def card_say(number: str, plan: dict[str, Any], tier: str, waiting: bool) -> str:
    """One human line for the chat (the detail lives on the card, per v0.240 CHHOTA JAWAB)."""
    n_f, n_s = len(plan.get("files") or []), len(plan.get("steps") or [])
    q = (plan.get("questions") or [])
    head = f"{number}: plan ready - {n_f} file(s), {n_s} step(s)"
    if q:
        return f"{head}. One thing to ask: {q[0]}"
    if waiting:
        return f"{head}. This task is big, so your approval is needed before starting (see the card)."
    return f"{head}. Starting work on this plan."
