"""v0.772 HOOLA AI APPS - D1: her one line about her business -> a CHECKED soul (nothing saved).

The idea (Dify's one-sentence generator, ideas only): a planner call writes the whole draft, a validator refuses
anything Hoola cannot do, bad output gets ONE repair round. Hoola's own laws on top:

  - The model is told the EXACT soul shape (soul.py): its fields, the ACTIONS keys, the FIELD_TYPES, the KINDS.
  - `facts` = ONLY things she wrote. A fact (or an about / opening sentence) carrying a number that is not in her
    words is DROPPED with a warning - no invented prices, timings or offers, ever.
  - Anything she did not say becomes a QUESTION back to her, never a guess.
  - The cost cap and the DPDP notice are the house defaults; the model cannot set money.
  - Nothing is saved here. She looks, edits, then creates (origin 'builder') through the owner routes.
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any, Callable

from . import soul as SO
from .store import AppError

log = logging.getLogger("santosh.aiapps.builder")

MAX_WORDS = 3000
MAX_QUESTIONS = 6
_NUM = re.compile(r"\d+(?:[.,]\d+)?")


def _default(system: str, prompt: str, max_tokens: int) -> dict[str, Any]:
    from ..net.ai import llm_json
    return llm_json(system, prompt, max_tokens) or {}


ASK: list[Callable[[str, str, int], dict[str, Any]]] = [_default]     # tests put a fake model here


def _shape() -> str:
    acts = "\n".join(f'    "{k}": {v}' for k, v in SO.ACTIONS.items())
    return f"""THE SOUL (exactly these keys, nothing else):
{{
  "name": "the app's name (max {SO.CAPS['name']} chars)",
  "kind": one of {list(SO.KINDS)} ("form" only when the visitor must fill fields first),
  "about": "what the business is, in HER words (max {SO.CAPS['about']} chars)",
  "persona": "how the assistant talks, e.g. warm and short (max {SO.CAPS['persona']} chars)",
  "facts": ["one short fact per line, ONLY things she wrote", ... max {SO.CAPS['facts']}],
  "knowledge": {{"seva": true, "annotations": true}},
  "actions": a list of these keys ONLY:
{acts}
  "opening": "the first line a visitor sees",
  "suggested": ["up to {SO.CAPS['suggested']} short questions a visitor might tap"],
  "form": [{{"key": "snake_case", "label": "Label", "type": one of {list(SO.FIELD_TYPES)}, "required": true,
             "options": ["only for type choice"]}}] (empty for kind chat),
  "refuse": ["topics the assistant must hand to her team, e.g. discounts, medical advice"],
  "language": one of {list(SO.LANGS)}
}}"""


SYSTEM = """You design a customer-facing AI assistant for a small Indian business, from the owner's own words.
The assistant answers HER CUSTOMERS (not her). It can never pay, refund, send messages to others or change prices.
{shape}
LAWS:
- "facts" holds ONLY facts the owner actually wrote. NEVER invent a price, timing, date, phone number, address,
  discount or offer. If a detail is missing, leave it out and ask for it in "questions".
- "about" restates her words; do not add numbers she did not write.
- Pick "actions" sensibly: "ticket" for shops/services with complaints, "slots" + "book" only for appointment
  businesses (clinic, salon, coaching demo...). "handover" is always on.
- Put money, medical, legal or anything risky the assistant must not decide into "refuse".
- Never mention OTP, PIN, password or card numbers in facts.
- English for every text you write unless she clearly wants another language.
Reply with ONE JSON object: {{"soul": {{...the soul...}}, "questions": ["what you still need to ask her, max {nq}"],
"says": "one short plain sentence for her about this draft"}}"""


def _system() -> str:
    return SYSTEM.format(shape=_shape(), nq=MAX_QUESTIONS)


def _call(prompt: str) -> dict[str, Any]:
    try:
        out = ASK[0](_system(), prompt, 1800)
    except Exception as e:                              # noqa: BLE001
        log.info("aiapps planner failed: %s", e)
        return {}
    if isinstance(out, str):
        m = re.search(r"\{.*\}", out, re.S)
        try:
            out = json.loads(m.group(0)) if m else {}
        except ValueError:
            out = {}
    return out if isinstance(out, dict) else {}


def _unpack(got: dict[str, Any]) -> tuple[dict[str, Any], list[str], str]:
    raw = got.get("soul") if isinstance(got.get("soul"), dict) else (got if "name" in got or "about" in got else {})
    qs = got.get("questions") if isinstance(got.get("questions"), list) else []
    return raw, [str(q).strip()[:200] for q in qs if str(q).strip()], str(got.get("says") or "").strip()[:300]


def _house(raw: dict[str, Any]) -> dict[str, Any]:
    """The model never sets money or the DPDP line."""
    raw = dict(raw)
    raw["limits"] = {"monthly_cap_inr": SO.DEFAULT_CAP_INR, "max_reply_chars": 900}
    raw.pop("notice", None)
    return raw


def _nums(text: str) -> set[str]:
    return {n.replace(",", "") for n in _NUM.findall(text or "")}


def _scrub(sl: dict[str, Any], words: str) -> list[str]:
    """The 'no invented numbers' law. Mutates the checked soul, returns warnings."""
    allowed = _nums(words)
    warns: list[str] = []

    def bad(t: str) -> str:
        extra = [n for n in _nums(t) if n not in allowed]
        return extra[0] if extra else ""

    keep = []
    for f in sl.get("facts") or []:
        n = bad(f)
        if n:
            warns.append(f"dropped a fact with a number you did not write ({n}): '{f[:80]}'")
        else:
            keep.append(f)
    sl["facts"] = keep
    if bad(sl.get("about") or ""):
        parts = re.split(r"(?<=[.!?])\s+", sl["about"])
        good = [p for p in parts if not bad(p)]
        warns.append("removed a sentence from 'about' with a number you did not write")
        sl["about"] = " ".join(good).strip()
    for key in ("opening", "persona"):
        n = bad(sl.get(key) or "")
        if n:
            warns.append(f"cleared '{key}': it had a number you did not write ({n})")
            sl[key] = ""
    sug = [q for q in sl.get("suggested") or [] if not bad(q)]
    if len(sug) != len(sl.get("suggested") or []):
        warns.append("dropped a suggested question with a number you did not write")
    sl["suggested"] = sug
    return warns


def _auto_questions(sl: dict[str, Any]) -> list[str]:
    out = []
    if not sl.get("facts"):
        out.append("What are your timings, and which days are you open?")
    if not any(re.search(r"(rs\.?|₹|price|fee|charge|cost)", f, re.I) for f in sl.get("facts") or []):
        out.append("Which prices or fees may the assistant tell customers?")
    if "book" in (sl.get("actions") or []):
        out.append("Are your working hours and slot length set in your AI Employee profile? Booking uses them.")
    return out


def _fallback_name(words: str) -> str:
    w = re.sub(r"\s+", " ", words).strip()
    return (w[:40].rsplit(" ", 1)[0] if len(w) > 40 else w) + " assistant" if w else "My assistant"


def plan(tenant: str, words: str) -> dict[str, Any]:
    """-> {soul, errors, warnings, questions, says}. Nothing is saved."""
    words = re.sub(r"[ \t]+", " ", str(words or "")).strip()
    if not words:
        raise AppError("Tell me about your business in one line.", 400)
    if len(words) > MAX_WORDS:
        raise AppError(f"Please keep it under {MAX_WORDS} characters.", 413)
    prompt = f"THE OWNER WROTE:\n{words}"
    got = _call(prompt)
    raw, questions, says = _unpack(got)
    warnings: list[str] = []
    if not raw:
        warnings.append("The planner did not answer; this is a plain starting draft from your words.")
        raw = {"name": _fallback_name(words), "about": words, "actions": ["handover"]}
    res = SO.check(_house(raw))
    if res["errors"]:
        fix = (prompt + "\n\nYOUR LAST DRAFT:\n" + json.dumps(raw, ensure_ascii=False)[:6000]
               + "\n\nTHE CHECKER REFUSED IT:\n- " + "\n- ".join(res["errors"]) + "\nFix every error and reply again.")
        raw2, q2, s2 = _unpack(_call(fix))
        if raw2:
            res2 = SO.check(_house(raw2))
            if len(res2["errors"]) < len(res["errors"]):
                res, questions, says = res2, (q2 or questions), (s2 or says)
                warnings.append("The first draft had problems; it was repaired once.")
    sl = res["soul"]
    warnings += _scrub(sl, words)
    final = SO.check(sl)
    sl = final["soul"]
    for q in _auto_questions(sl):
        if q not in questions:
            questions.append(q)
    errors = final["errors"]
    # what the checker had to throw away from the model's draft is said, never laundered silently
    removed = [f"removed from the draft: {e}" for e in res["errors"] if e not in errors]
    warnings = (warnings + removed + res["warnings"]
                + [w for w in final["warnings"] if w not in res["warnings"]])[:20]
    if not says:
        says = (f"Here is a draft for '{sl['name']}'. Check it, answer the questions, then create it."
                if not errors else f"The draft for '{sl['name']}' still needs fixing: {errors[0]}")
    return {"soul": sl, "errors": errors, "warnings": warnings, "questions": questions[:MAX_QUESTIONS], "says": says,
            "hash": SO.hash_of(sl)}
