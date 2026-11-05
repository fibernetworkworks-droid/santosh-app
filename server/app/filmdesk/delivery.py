"""Film Desk DELIVERY layer: a deliverables tracker (what each buyer / festival / platform must receive, by when) and a localisation tracker
(subtitles and dubbing per language) that checks every AI voice against the consent register. All in CODE.

Register: docs/research/film_industry/00_INDEX.md  (#64 deliverables manager, #93 subtitle and dub localisation project manager,
#107/#110 digital-replica consent). Pure functions: no database, no network, no model.

What it will never do: decide what a buyer's delivery specification is (the starter lists below are only a starting set of ITEMS; the
buyer's own spec decides what is really required), accept a delivery on a buyer's behalf, translate or dub anything, or clear an AI voice.
Dates, vendors and statuses are HERS. The one cross-check it makes on its own is the consent register: an AI-voice dub names a person,
and that person's recorded consent must cover `ai_voice` today, otherwise the line is flagged (the film desk's existing rule, applied here).
"""
from __future__ import annotations

import re
from datetime import date
from typing import Any, Callable

D_STATUSES = ("todo", "in_progress", "delivered", "qc_failed", "accepted", "waived")
D_DONE = ("delivered", "accepted", "waived")
L_STATUSES = ("todo", "translating", "recording", "qc", "delivered", "accepted", "blocked")
L_DONE = ("delivered", "accepted")
L_KINDS = ("subtitles", "dub", "both")
DUB_MODES = ("human", "ai_voice")
ITEM_MAX, LOC_MAX, QA_WARN = 80, 60, 3

# A starting set of ITEM NAMES per kind of delivery. NOT a specification: each buyer / festival publishes its own.
STARTERS: dict[str, list[str]] = {
    "festival": ["Screener (link or file)", "Poster / key art", "Stills (3-5)", "Trailer", "Synopsis and credits", "Subtitles (English)",
                 "Director and producer bios", "Press kit"],
    "ott": ["Video master", "Audio mix and stems", "Music and effects track (M&E)", "Subtitles and closed captions", "Trailer", "Key art and stills",
            "Metadata sheet", "Chain-of-title documents", "Music cue sheet", "E&O insurance certificate", "Technical QC report"],
    "theatrical": ["DCP (cinema package)", "Trailer", "Poster / key art", "Subtitle files", "Censor / rating certificate", "Music cue sheet",
                   "Press kit", "Chain-of-title documents"],
    "tv": ["Broadcast master", "Audio mix and stems", "Closed captions", "Promos", "Metadata sheet", "Music cue sheet", "Rating / compliance papers"],
}


def _clean(v: Any, n: int) -> str:
    return re.sub(r"\s+", " ", str(v or "")).strip()[:n]


def _day(v: Any) -> str:
    try:
        return date.fromisoformat(str(v or "").strip()[:10]).isoformat()
    except ValueError:
        return ""


def _days_left(due: str, today: date) -> int | None:
    return (date.fromisoformat(due) - today).days if due else None


# ---------------------------------------------------------------- deliverables
def norm_deliverable(raw: dict[str, Any], seq: int) -> dict[str, Any]:
    label = _clean(raw.get("label"), 120)
    if not label:
        raise ValueError("Deliverable ka naam (label) batao.")
    status = _clean(raw.get("status"), 12).lower() or "todo"
    if status not in D_STATUSES:
        raise ValueError(f"status inme se: {', '.join(D_STATUSES)}")
    return {"id": f"d{seq}", "label": label, "buyer": _clean(raw.get("buyer"), 80), "due": _day(raw.get("due")), "status": status,
            "notes": _clean(raw.get("notes"), 300)}


def starter_items(kind: str) -> list[str]:
    k = _clean(kind, 16).lower()
    if k not in STARTERS:
        raise ValueError(f"kind inme se: {', '.join(STARTERS)}")
    return list(STARTERS[k])


def deliverables_view(items: list[dict[str, Any]], today: date) -> dict[str, Any]:
    rows, flags = [], []
    for it in items:
        r = dict(it)
        r["days_left"] = _days_left(it["due"], today)
        open_ = it["status"] not in D_DONE
        if open_ and it["due"]:
            if r["days_left"] < 0:
                flags.append(f"{it['label']}: due {it['due']} nikal chuki ({-r['days_left']} din), status '{it['status']}'.")
            elif r["days_left"] <= 7:
                flags.append(f"{it['label']}: {r['days_left']} din me due ({it['due']}).")
        if it["status"] == "qc_failed":
            flags.append(f"{it['label']}: QC fail hui: theek karke dobara bhejna hai.")
        rows.append(r)
    rows.sort(key=lambda r: (r["status"] in D_DONE, r["due"] or "9999", r["label"]))
    total = len(items)
    done = sum(1 for it in items if it["status"] in D_DONE)
    return {"deliverables": rows, "total": total, "done": done, "progress_pct": round(100.0 * done / total, 1) if total else 0.0,
            "counts": {s: sum(1 for it in items if it["status"] == s) for s in D_STATUSES}, "flags": flags,
            "note": "Yeh list ek shuruaati set hai. Har buyer / festival ki apni specification final hai: usse milaiye."}


# ---------------------------------------------------------------- localisation
def norm_loc(raw: dict[str, Any], seq: int) -> dict[str, Any]:
    lang = _clean(raw.get("language"), 40).title()
    if not lang:
        raise ValueError("Bhasha (language) batao.")
    kind = _clean(raw.get("kind"), 12).lower() or "subtitles"
    if kind not in L_KINDS:
        raise ValueError(f"kind inme se: {', '.join(L_KINDS)}")
    status = _clean(raw.get("status"), 12).lower() or "todo"
    if status not in L_STATUSES:
        raise ValueError(f"status inme se: {', '.join(L_STATUSES)}")
    mode = _clean(raw.get("dub_mode"), 10).lower()
    if kind == "subtitles":
        mode = ""
    elif mode not in DUB_MODES:
        mode = "human"
    try:
        qa = max(0, int(raw.get("qa_rounds") or 0))
    except (TypeError, ValueError):
        qa = 0
    return {"id": f"l{seq}", "language": lang, "kind": kind, "dub_mode": mode, "voice_person": _clean(raw.get("voice_person"), 40),
            "vendor": _clean(raw.get("vendor"), 80), "due": _day(raw.get("due")), "status": status, "qa_rounds": min(qa, 20),
            "notes": _clean(raw.get("notes"), 300)}


def loc_view(items: list[dict[str, Any]], today: date, consent_check: Callable[[str], str] | None = None) -> dict[str, Any]:
    """`consent_check(person_ref)` returns '' when that person's consent covers an AI voice today, else the plain reason."""
    rows, flags = [], []
    for it in items:
        r = dict(it)
        r["days_left"] = _days_left(it["due"], today)
        open_ = it["status"] not in L_DONE
        label = f"{it['language']} ({it['kind']})"
        if open_ and it["due"] and r["days_left"] < 0:
            flags.append(f"{label}: due {it['due']} nikal chuki ({-r['days_left']} din).")
        elif open_ and it["due"] and r["days_left"] <= 7:
            flags.append(f"{label}: {r['days_left']} din me due ({it['due']}).")
        if it["status"] == "blocked":
            flags.append(f"{label}: ruka hua hai: wajah notes me likhiye.")
        if it["qa_rounds"] >= QA_WARN and open_:
            flags.append(f"{label}: {it['qa_rounds']} QA round ho gaye, abhi bhi khula hai: vendor se seedhi baat kijiye.")
        r["voice_check"] = ""
        if it["dub_mode"] == "ai_voice":
            if not it["voice_person"]:
                r["voice_check"] = "AI awaaz kiski hai? consent register me vyakti ka number (P-001) dijiye."
            elif consent_check is not None:
                r["voice_check"] = consent_check(it["voice_person"])
            if r["voice_check"]:
                flags.append(f"{label}: AI awaaz roki gayi: {r['voice_check']}")
        rows.append(r)
    rows.sort(key=lambda r: (r["status"] in L_DONE, r["due"] or "9999", r["language"]))
    total = len(items)
    done = sum(1 for it in items if it["status"] in L_DONE)
    return {"localisation": rows, "total": total, "done": done, "progress_pct": round(100.0 * done / total, 1) if total else 0.0,
            "counts": {s: sum(1 for it in items if it["status"] == s) for s in L_STATUSES}, "flags": flags,
            "ai_voice_blocked": sum(1 for r in rows if r["voice_check"]),
            "note": "Hoola na anuvaad karta hai na dubbing: yeh sirf vendor, tareekh aur ijazat ka hisaab rakhta hai."}
