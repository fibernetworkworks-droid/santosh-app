"""P9 SEEKHO (learn): short lessons made from HER OWN prompts. One idea per lesson.

Each lesson is a pattern code can find for certain in her words or in her brief (a vague word an engine cannot see, a
'magic' phrase, 'no X' in a picture, an offer with no end date, the same part missing again and again...). The lesson
shows HER line, why it hurts, and a better way written BY CODE from her own brief - no model is asked to rewrite her.

'Before / after from real runs' is said only when her own record holds it:
  - the outcome ledger: how often her results were kept WITH that part filled vs WITHOUT it (shown from 8 graded runs on
    each side, the same bar as the score check), and
  - her own compares (P8): how often the side that had the part won her pick.
Otherwise the lesson says plainly it is Hoola's starter guidance, not yet proven on her prompts.
Her read: 'Got it' hides a lesson for 30 days; 'Not useful' hides it for good and is counted.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import DateTime, Integer, String, select
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, as_utc, now, session
from . import anatomy as A
from . import brief as B

GOT_IT_DAYS = 30
MIN_SIDE = 8                 # graded runs needed on each side before a 'kept with / without' number is shown
MIN_PICKS = 3                # her compare picks needed before 'won your pick' is shown

# vague words an engine cannot see -> what to say instead, per kind of prompt
VAGUE: dict[str, dict[str, str]] = {
    "premium": {"image": "black and gold, a serif heading, lots of empty space", "web": "a dark background, one gold accent, a serif heading, wide margins",
                "*": "name the colours, the font and how much empty space"},
    "attractive": {"image": "one clear subject, warm light, bright colours", "*": "what should catch the eye first"},
    "beautiful": {"image": "soft morning light, a clean background, the subject in the centre", "*": "name the colours and the mood"},
    "modern": {"image": "flat colours, a sans-serif heading, simple shapes", "web": "white space, a sans-serif font, big photos, few colours",
               "*": "name what makes it look new: colours, font, layout"},
    "professional": {"web": "a clean white layout, one brand colour, real photos, clear prices", "doc": "formal tone, numbered sections, a price table",
                     "*": "who reads it and what tone they expect"},
    "nice": {"*": "exactly what you like - a colour, a feeling, an example"},
    "good": {"*": "what 'good' means here - more calls, more orders, fewer questions"},
    "catchy": {"script": "open on a question or a surprising sight in the first 3 seconds", "marketing": "put the offer and the last date in the first line",
               "music": "a short chorus that repeats the shop's name", "*": "what should be remembered"},
    "viral": {"script": "a hook in the first 3 seconds, one message, under 30 seconds", "*": "who should share it and why"},
    "best": {"research": "best for what - cheapest, fastest, most reliable?", "*": "what 'best' is measured by"},
    "eye-catching": {"image": "one bold colour against a plain background, big words", "*": "what should be seen first"},
    "stylish": {"*": "name the style: traditional, minimal, bold, playful..."},
    "unique": {"*": "what must be different from others - a colour, a symbol, a line"},
}
_WORD = {w: re.compile(r"(?<![a-z])" + re.escape(w) + r"(?![a-z])", re.I) for w in VAGUE}


class LessonSeen(Base):
    __tablename__ = "prompt_lessons"
    id: Mapped[str] = mapped_column(String(120), primary_key=True)        # tenant:lesson
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    lesson: Mapped[str] = mapped_column(String(60))
    state: Mapped[str] = mapped_column(String(12), default="")            # got_it | not_useful
    shown: Mapped[int] = mapped_column(Integer, default=0)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


_OK: set[int] = set()


def ensure_table() -> None:
    from .. import db as _db
    eng = getattr(_db, "_engine", None)
    if eng is not None and id(eng) not in _OK:
        LessonSeen.__table__.create(eng, checkfirst=True)
        _OK.add(id(eng))


# ---------------------------------------------------------------- lessons on one brief
def _v(b: dict[str, Any], k: str) -> str:
    return ((b.get("slots") or {}).get(k) or {}).get("value", "")


def _snip(text: str, at: int, n: int = 70) -> str:
    a = max(0, at - n // 2)
    s = text[a:a + n].strip()
    return ("…" if a > 0 else "") + s + ("…" if a + n < len(text) else "")


def on_brief(b: dict[str, Any]) -> list[dict[str, Any]]:
    """Lessons this one prompt teaches. Each: id, title, idea, hers (her own words), instead, slot."""
    sec, intent = b["section"], b.get("intent") or ""
    text = " ".join([intent] + [v.get("value", "") for v in (b.get("slots") or {}).values() if v.get("source") != "hoola_guess"])
    out: list[dict[str, Any]] = []
    low = text.lower()
    for w, rx in _WORD.items():
        src = intent if rx.search(intent) else text
        lsrc = src.lower()
        m = next((m for m in rx.finditer(src)
                  if not any(x in lsrc[max(0, m.start() - 14):m.end() + 14] and w in x for x in B.MAGIC)), None)
        if m:
            tip = VAGUE[w].get(sec) or VAGUE[w]["*"]
            out.append({"id": f"vague:{w}", "title": f"An engine cannot see '{w}'",
                        "idea": f"'{w.capitalize()}' means something different to every engine. Describe what you see instead.",
                        "hers": _snip(src, m.start()), "instead": f"Instead of '{w}': {tip}.", "slot": "style"})
    magic = [x for x in B.MAGIC if x in low]
    if magic:
        out.append({"id": "magic", "title": "Magic words do nothing",
                    "idea": "Phrases like 'best quality', '8k' or 'act as an expert' do not help current engines. Spend the words on what you want.",
                    "hers": (_snip(intent, intent.lower().index(magic[0])) if magic[0] in intent.lower() else _snip(text, low.index(magic[0]))), "instead": "Delete them and add one real detail - the light, the place, who it is for.",
                    "slot": ""})
    if sec in ("image", "video"):
        m = re.search(r"\b(?:no|without|don't|do not|avoid)\s+([a-z]+(?:\s[a-z]+)?)", intent, re.I)
        if m:
            out.append({"id": "negative", "title": "Say what IS there, not what is not",
                        "idea": f"Picture and video engines often draw the thing you said 'no' to. Describe the empty space instead.",
                        "hers": _snip(intent, m.start()), "instead": f"Instead of '{m.group(0)}', say what fills that space - "
                        "'an empty street', 'a plain wall', 'a clean table'.", "slot": "scene"})
    kinds = {f["kind"] for f in (b.get("facts") or [])}
    if sec in ("image", "marketing", "script") and kinds & {"price", "percent"} and "date" not in kinds:
        out.append({"id": "offer_date", "title": "An offer needs its last date",
                    "idea": "An offer with no end date reads as forever - customers wait, and you cannot stop it cleanly.",
                    "hers": _snip(intent, 0, 90), "instead": "Add 'till 15 Nov' (or your real last date) right after the offer.",
                    "slot": "offer" if sec == "marketing" else "words"})
    if sec == "image" and len(_v(b, "words").split()) > 12:
        out.append({"id": "poster_words", "title": "Fewer words on a picture",
                    "idea": "Picture engines spell short lines well and long ones badly. Keep the words on the picture under 8.",
                    "hers": _v(b, "words")[:90], "instead": "Keep the offer and the shop name on the picture; put the rest in the caption.",
                    "slot": "words"})
    asks = re.split(r"\b(?:and also|also|plus|aur saath mein|and then)\b", intent, flags=re.I)
    if len([a for a in asks if B._content_words(a)]) >= 3:
        out.append({"id": "one_ask", "title": "One ask at a time",
                    "idea": "Three jobs in one prompt get three half-answers. Make one prompt per result.",
                    "hers": _snip(intent, 0, 90), "instead": "Split it: one prompt for the first thing, then the next.", "slot": ""})
    who = {"web": "who", "script": "audience", "marketing": "audience"}.get(sec)
    if who and re.search(r"(?<![a-z])(everyone|everybody|all people|sab log|sabke liye)(?![a-z])", low):
        out.append({"id": "everyone", "title": "'Everyone' is no one",
                    "idea": "A message for everyone speaks to nobody in particular. Pick the one group that matters most.",
                    "hers": _snip(text, low.find("every") if "every" in low else 0), "instead": "Say 'working mothers in Pune' or 'my regular customers'.",
                    "slot": who})
    return out


# ---------------------------------------------------------------- her record: the same part missing again and again
def _saved_briefs(tenant: str, limit: int = 60) -> list[dict[str, Any]]:
    from . import store as S
    out = []
    for row in S.listing(tenant)[:limit]:
        got = S.get(tenant, row["id"])
        if got and isinstance(got.get("brief"), dict) and got["brief"].get("section") in A.SECTIONS:
            try:
                out.append(B.validate(got["brief"]))
            except ValueError:
                continue
    return out


def _missing_often(briefs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    count: dict[tuple[str, str], int] = {}
    per_sec: dict[str, int] = {}
    for b in briefs:
        per_sec[b["section"]] = per_sec.get(b["section"], 0) + 1
        for k in b.get("missing") or []:
            count[(b["section"], k)] = count.get((b["section"], k), 0) + 1
    out = []
    for (sec, k), n in sorted(count.items(), key=lambda x: -x[1]):
        if n >= 3 and n * 2 >= per_sec[sec]:
            s = A.slot(sec, k)
            out.append({"id": f"missing:{sec}:{k}", "title": f"You often leave out: {s['label'].lower()}",
                        "idea": f"{n} of your {per_sec[sec]} saved {A.SECTIONS[sec]['label'].lower()} prompts have no "
                                f"{s['label'].lower()}. The engine then guesses it.",
                        "hers": f"{n} of {per_sec[sec]} saved prompts", "instead": s["q"] + (f" For example: {s['eg']}." if s.get("eg") else ""),
                        "slot": k, "section": sec})
    return out[:4]


# ---------------------------------------------------------------- real before / after from her own record
def evidence(tenant: str, section: str, slot: str) -> dict[str, Any] | None:
    """Her own numbers for 'with this part' vs 'without it'. None until there is enough to say."""
    if not slot or section not in A.SECTIONS:
        return None
    out: dict[str, Any] = {}
    try:
        from . import ledger as L
        L.ensure_table()
        with session() as s:
            rows = list(s.execute(select(L.PromptRun).where(L.PromptRun.tenant_id == tenant, L.PromptRun.section == section,
                                                            L.PromptRun.grade != "", L.PromptRun.grade != "unused")).scalars())
        def has(r):
            src = json.loads(r.slots or "{}").get(slot, "")
            return bool(src) and src != "hoola_guess"
        w = [r for r in rows if has(r)]
        wo = [r for r in rows if not has(r)]
        if len(w) >= MIN_SIDE and len(wo) >= MIN_SIDE:
            kw, kwo = sum(r.grade in L.KEPT for r in w), sum(r.grade in L.KEPT for r in wo)
            out["ledger"] = {"with": {"kept": kw, "of": len(w)}, "without": {"kept": kwo, "of": len(wo)},
                             "say": f"With it, {kw} of {len(w)} of your results were kept; without it, {kwo} of {len(wo)}."}
    except Exception:       # noqa: BLE001 - a lesson never fails for want of numbers
        pass
    try:
        from . import compare as CM
        CM.ensure_table()
        with session() as s:
            rows = list(s.execute(select(CM.PromptCompare).where(CM.PromptCompare.tenant_id == tenant,
                                                                 CM.PromptCompare.section == section,
                                                                 CM.PromptCompare.pick.in_(("a", "b")))).scalars())
        won = n = 0
        for c in rows:
            ha = json.loads(c.a_slots or "{}").get(slot, "") not in ("", "hoola_guess")
            hb = json.loads(c.b_slots or "{}").get(slot, "") not in ("", "hoola_guess")
            if ha == hb:
                continue
            n += 1
            won += (c.pick == "a") == ha
        if n >= MIN_PICKS:
            out["compare"] = {"won": won, "of": n, "say": f"In your own compares, the prompt that had it won {won} of {n} times."}
    except Exception:       # noqa: BLE001
        pass
    return out or None


# ---------------------------------------------------------------- her read
def _seen(tenant: str) -> dict[str, LessonSeen]:
    ensure_table()
    with session() as s:
        rows = list(s.execute(select(LessonSeen).where(LessonSeen.tenant_id == tenant)).scalars())
        s.expunge_all()
        return {r.lesson: r for r in rows}


def _hidden(r: LessonSeen | None) -> bool:
    if r is None or not r.state:
        return False
    if r.state == "not_useful":
        return True
    return as_utc(r.at) > now() - timedelta(days=GOT_IT_DAYS)


def mark(tenant: str, lesson: str, state: str) -> dict[str, Any]:
    if state not in ("got_it", "not_useful", ""):
        raise ValueError("got_it, not_useful or '' (show it again)")
    lesson = str(lesson)[:60]
    ensure_table()
    with session() as s:
        r = s.get(LessonSeen, f"{tenant}:{lesson}")
        if r is None:
            r = LessonSeen(id=f"{tenant}:{lesson}", tenant_id=tenant, lesson=lesson)
            s.add(r)
        r.state, r.at = state, now()
    return {"lesson": lesson, "state": state}


def _dress(tenant: str, lessons: list[dict[str, Any]], section: str, seen: dict[str, LessonSeen]) -> list[dict[str, Any]]:
    out = []
    for x in lessons:
        if _hidden(seen.get(x["id"])):
            continue
        ev = evidence(tenant, x.get("section") or section, x.get("slot") or "")
        out.append({**x, "proof": ev, "starter": ev is None,
                    "basis": "From your own results." if ev else "Hoola's starter guidance - not yet proven on your prompts."})
    return out


def for_brief(tenant: str, b: dict[str, Any]) -> list[dict[str, Any]]:
    """The workbench's 'Learn from this prompt': this brief's lessons she has not hidden."""
    return _dress(tenant, on_brief(b), b["section"], _seen(tenant))[:3]


def page(tenant: str) -> dict[str, Any]:
    """The Learn page: what her saved prompts teach, most frequent first, with her own numbers where they exist."""
    briefs = _saved_briefs(tenant)
    tally: dict[str, dict[str, Any]] = {}
    for b in briefs:
        for x in on_brief(b):
            t = tally.setdefault(x["id"], {**x, "section": b["section"], "times": 0})
            t["times"] += 1
    found = sorted(tally.values(), key=lambda x: -x["times"]) + _missing_often(briefs)
    seen = _seen(tenant)
    lessons = _dress(tenant, found, "", seen)
    return {"lessons": lessons[:12], "from": len(briefs),
            "hidden": sum(1 for r in seen.values() if _hidden(r)),
            "not_useful": sum(1 for r in seen.values() if r.state == "not_useful"),
            "note": "" if briefs else "Save a few prompts and Hoola will make lessons from them."}
