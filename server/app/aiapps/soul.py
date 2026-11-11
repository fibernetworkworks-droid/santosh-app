"""v0.772 HOOLA AI APPS - the SOUL: everything an AI app is, as one checked object.

A soul may only promise what Hoola can do. The checker refuses an unknown action, an unknown field type, an unsafe
setting; everything she writes is kept as HER words (never re-written by a model behind her back).

    name, kind (chat | form), about (what the business is, in her words), persona (how it talks),
    facts: [ "Open 10 am - 8 pm", "Delivery free above Rs 500", ... ]   - the ONLY things a written answer may state
    knowledge: {"seva": true, "annotations": true}                       - her Seva KB + her approved answers
    actions: ["ticket", "slots", "book", "handover"]                     - what the app may DO (from ACTIONS only)
    opening: "Namaste! ..."      suggested: ["Timings?", ...]            - the first screen
    form: [{"key", "label", "type", "required", "options"}]              - kind=form: the inputs it asks for
    refuse: ["discounts", ...]                                          - topics it must hand over, in her words
    language: "auto" | "en" | "hi" | "mr" ...
    show_sources: bool, feedback: bool
    limits: {"monthly_cap_inr": 500, "max_reply_chars": 900}
    notice: the DPDP line shown before the first message (she can edit it, never empty)
"""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any

KINDS = ("chat", "form")
# What an app may DO for a visitor. Each one is safe by construction: nothing here moves money, sends a message to
# someone else, changes her prices or reads another customer's data.
ACTIONS = {
    "handover": "Pass the visitor to her team (a note in her chat; nothing is promised)",
    "ticket": "Open a support ticket in Seva for a real problem (the visitor gets the ticket number)",
    "slots": "Read her free appointment slots",
    "book": "Book one free slot for the visitor (her Employee hours and slot length)",
}
FIELD_TYPES = ("text", "long_text", "number", "phone", "email", "date", "choice")
LANGS = ("auto", "en", "hi", "mr", "gu", "ta", "te", "kn", "ml", "bn", "pa")
CAPS = {"name": 80, "about": 2000, "persona": 600, "fact": 300, "facts": 40, "opening": 400, "suggested": 6,
        "suggested_len": 80, "form": 12, "refuse": 20, "notice": 400}
DEFAULT_NOTICE = ("You are chatting with an AI assistant of this business. Messages are kept so the team can help you; "
                  "ask them to delete yours any time. Never share an OTP, PIN, password or card number here.")
DEFAULT_CAP_INR = 500.0
MAX_CAP_INR = 50000.0
_SECRET_WORDS = re.compile(r"\b(otp|pin|cvv|password|passcode)\b", re.I)


def blank(name: str = "", kind: str = "chat") -> dict[str, Any]:
    return {"name": name or "My assistant", "kind": kind if kind in KINDS else "chat", "about": "", "persona": "",
            "facts": [], "knowledge": {"seva": True, "annotations": True}, "actions": ["handover"],
            "opening": "", "suggested": [], "form": [], "refuse": [], "language": "auto",
            "show_sources": True, "feedback": True,
            "limits": {"monthly_cap_inr": DEFAULT_CAP_INR, "max_reply_chars": 900}, "notice": DEFAULT_NOTICE}


def _s(v: Any, n: int) -> str:
    return re.sub(r"\s+", " ", str(v or "")).strip()[:n]


def check(raw: Any) -> dict[str, Any]:
    """Whatever was written -> {soul, errors, warnings}. errors == [] means it can go live."""
    errors: list[str] = []
    warnings: list[str] = []
    raw = raw if isinstance(raw, dict) else {}
    out = blank()
    out["name"] = _s(raw.get("name"), CAPS["name"]) or out["name"]
    kind = str(raw.get("kind") or "chat").strip().lower()
    if kind not in KINDS:
        errors.append(f"kind '{kind}' is not something Hoola builds (only: {', '.join(KINDS)})")
        kind = "chat"
    out["kind"] = kind
    out["about"] = str(raw.get("about") or "").strip()[:CAPS["about"]]
    out["persona"] = _s(raw.get("persona"), CAPS["persona"])
    facts = raw.get("facts") if isinstance(raw.get("facts"), list) else []
    if len(facts) > CAPS["facts"]:
        warnings.append(f"{len(facts)} facts given, the first {CAPS['facts']} are kept")
    out["facts"] = [f for f in (_s(x, CAPS["fact"]) for x in facts[:CAPS["facts"]]) if f]
    for f in out["facts"]:
        if _SECRET_WORDS.search(f):
            errors.append(f"a fact mentions a secret word (OTP / PIN / password): '{f[:60]}'")
    kn = raw.get("knowledge") if isinstance(raw.get("knowledge"), dict) else {}
    out["knowledge"] = {"seva": bool(kn.get("seva", True)), "annotations": bool(kn.get("annotations", True))}
    acts = raw.get("actions") if isinstance(raw.get("actions"), list) else ["handover"]
    bad = [str(a) for a in acts if str(a) not in ACTIONS]
    if bad:
        errors.append(f"action '{bad[0]}' does not exist (only: {', '.join(ACTIONS)}) - an app cannot pay, send messages "
                      "to others or change prices")
    out["actions"] = sorted({str(a) for a in acts if str(a) in ACTIONS} | {"handover"})
    if "book" in out["actions"] and "slots" not in out["actions"]:
        out["actions"].append("slots")
        out["actions"].sort()
        warnings.append("'book' needs 'slots' to know what is free - added")
    out["opening"] = _s(raw.get("opening"), CAPS["opening"])
    sug = raw.get("suggested") if isinstance(raw.get("suggested"), list) else []
    out["suggested"] = [x for x in (_s(q, CAPS["suggested_len"]) for q in sug[:CAPS["suggested"]]) if x]
    form = raw.get("form") if isinstance(raw.get("form"), list) else []
    seen: set[str] = set()
    for i, f in enumerate(form[:CAPS["form"]]):
        if not isinstance(f, dict):
            continue
        key = re.sub(r"[^a-z0-9_]", "_", str(f.get("key") or f.get("label") or "").strip().lower())[:40].strip("_")
        typ = str(f.get("type") or "text").strip().lower()
        if not key or key in seen:
            errors.append(f"form field {i + 1}: a unique key is needed")
            continue
        if typ not in FIELD_TYPES:
            errors.append(f"form field '{key}': type '{typ}' does not exist (only: {', '.join(FIELD_TYPES)})")
            continue
        one = {"key": key, "label": _s(f.get("label") or key.replace("_", " ").title(), 60), "type": typ,
               "required": bool(f.get("required"))}
        if typ == "choice":
            one["options"] = [_s(o, 40) for o in (f.get("options") or []) if _s(o, 40)][:12]
            if not one["options"]:
                errors.append(f"form field '{key}': a choice needs options")
                continue
        seen.add(key)
        out["form"].append(one)
    if kind == "form" and not out["form"]:
        errors.append("a form app needs at least one form field")
    ref = raw.get("refuse") if isinstance(raw.get("refuse"), list) else []
    out["refuse"] = [x for x in (_s(r, 80) for r in ref[:CAPS["refuse"]]) if x]
    lang = str(raw.get("language") or "auto").strip().lower()
    out["language"] = lang if lang in LANGS else "auto"
    out["show_sources"] = bool(raw.get("show_sources", True))
    out["feedback"] = bool(raw.get("feedback", True))
    lim = raw.get("limits") if isinstance(raw.get("limits"), dict) else {}
    try:
        cap = float(lim.get("monthly_cap_inr", DEFAULT_CAP_INR))
    except (TypeError, ValueError):
        cap = DEFAULT_CAP_INR
        errors.append("limits.monthly_cap_inr must be a number of rupees")
    if cap <= 0:
        errors.append("limits.monthly_cap_inr must be more than 0 - a published app always has a cost ceiling")
        cap = DEFAULT_CAP_INR
    if cap > MAX_CAP_INR:
        warnings.append(f"monthly cap lowered to Rs {MAX_CAP_INR:,.0f}")
        cap = MAX_CAP_INR
    try:
        mx = int(lim.get("max_reply_chars", 900))
    except (TypeError, ValueError):
        mx = 900
    out["limits"] = {"monthly_cap_inr": round(cap, 2), "max_reply_chars": max(200, min(mx, 3000))}
    out["notice"] = _s(raw.get("notice"), CAPS["notice"]) or DEFAULT_NOTICE
    if not out["about"] and not out["facts"] and not out["knowledge"]["seva"]:
        warnings.append("no about, no facts and no knowledge base - it can only hand visitors over")
    return {"soul": out, "errors": errors[:30], "warnings": warnings[:20]}


def hash_of(soul: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(soul, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:16]
