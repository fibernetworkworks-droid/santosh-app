"""v0.772 HOOLA INTERACTIVE, the whole product: what the twelve console pages stand on, beside studio.py.

studio.py is the film itself (draft -> scenes -> make). This module is everything around it that needs NO GPU, so each
page does real work today:

    brand        her name, closing line and colour: every new video starts with them, the colour is drawn into the film
    glossary     words to keep as written / always translate one way - checked by CODE on every translation
    templates    a video saved as a shape with {variables}; using one fills them from HER values, never a guess
    batch        many scripts at once -> one draft each, split into scenes by code (no model call)
    personalise  one video with {name} -> a draft per name (opted-in people are hers to choose; nothing is sent here)
    translate    a Hoola-made video into another language as a NEW draft she proofreads: one model call for the words,
                 then code checks that every number survived and every glossary rule held; a line that fails is flagged
    trash        delete = 30 days in the trash with its video, restore brings both back
    brains       what a live avatar may know (saved now; the live stream itself still waits for the engine test)
    usage        minutes really made this month, read from the videos on disk

Laws (test_v0772_interactive_hub.py):
  HERS      a template or a name list only ever inserts her own values; a missing value refuses, never fills in;
  NUMBERS   a translated line whose digits differ from the source line is FLAGGED and the source is kept beside it;
  SAID      what is not connected (twin, cloned voice, lip-matched dubbing of outside videos, live stream, API) is
            reported as not connected by status() - the page prints that, it never pretends;
  OWNERS    everything is in the tenant's own studio.json under studio._LOCK - no cross-tenant read exists.
"""
from __future__ import annotations

import copy
import re
import time
import uuid
from typing import Any, Callable

from . import studio as S

MAX_TEMPLATES = 40
MAX_GLOSSARY = 200
MAX_BRAINS = 10
MAX_BATCH = 20
TRASH_DAYS = 30
VAR = re.compile(r"\{([a-z][a-z0-9_]{0,23})\}")
HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")
TEXT_KEYS = ("text", "label", "title", "sub", "unit")          # look strings that are words (translated, templated)
ALL_KEYS = TEXT_KEYS + ("value", "new", "old")

# Six starter shapes. Every changing word is a {variable}: nothing here states a price, date or name.
BUILTIN: list[dict[str, Any]] = [
    {"id": "tp_offer", "name": "Festival offer", "group": "Offers", "shape": "talking_head", "aspect": "16:9", "closing": "{shop}",
     "scenes": [{"say": "This {festival}, a special offer at {shop}.", "look": {"kind": "title", "text": "{festival} offer"}},
                {"say": "{item} is now only {price}.", "look": {"kind": "price", "new": "{price}", "label": "{item}"}},
                {"say": "The offer runs until {last_date}. Come in today.", "look": {"kind": "lower_third", "title": "{shop}", "sub": "Offer until {last_date}"}}]},
    {"id": "tp_rate", "name": "Rate update", "group": "Updates", "shape": "talking_head", "aspect": "16:9", "closing": "{shop}",
     "labels": {"item": ("What the rate is for", "e.g. Gold, per ounce"), "rate": ("Today's rate", "with its unit, e.g. $2,341")},
     "scenes": [{"say": "Here is today's rate for {item}.", "look": {"kind": "title", "text": "{item} rate"}},
                {"say": "The rate for {item} is {rate}.", "look": {"kind": "big_number", "value": "{rate}", "label": "{item}"}}]},
    {"id": "tp_batch", "name": "New batch opening", "group": "Lessons", "shape": "talking_head", "aspect": "16:9", "closing": "{institute}",
     "scenes": [{"say": "A new batch of {course} is starting at {institute}.", "look": {"kind": "title", "text": "{course}"}},
                {"say": "The batch starts on {start_date}.", "look": {"kind": "lower_third", "title": "Starts: {start_date}", "sub": "{institute}"}},
                {"say": "Contact us today to confirm your seat.", "look": {"kind": "none"}}]},
    {"id": "tp_timing", "name": "Timing change", "group": "Updates", "shape": "talking_head", "aspect": "16:9", "closing": "{place}",
     "scenes": [{"say": "The timings of {place} have changed.", "look": {"kind": "title", "text": "New timings"}},
                {"say": "We are now open {hours}, {days}.", "look": {"kind": "lower_third", "title": "{hours}", "sub": "{days}"}}]},
    {"id": "tp_thanks", "name": "Thank you", "group": "Greetings", "shape": "talking_head", "aspect": "16:9", "closing": "{shop}",
     "scenes": [{"say": "{name}, thank you for trusting {shop}.", "look": {"kind": "title", "text": "Thank you, {name}"}},
                {"say": "We are always here to serve you.", "look": {"kind": "none"}}]},
    {"id": "tp_reel", "name": "Quick reel", "group": "Reels", "shape": "reel", "aspect": "9:16", "closing": "{shop}",
     "scenes": [{"say": "{hook}", "look": {"kind": "none"}}, {"say": "{point}", "look": {"kind": "none"}},
                {"say": "Visit {shop} today.", "look": {"kind": "none"}}]},
]
# The same starters as they are spoken when the video's language is Hindi (Hindi words in Latin script). Same variables.
BUILTIN += [
    {"id": "tp_remind", "name": "Appointment reminder", "group": "Reminders", "shape": "talking_head", "aspect": "16:9", "closing": "{place}",
     "scenes": [{"say": "Hello {name}, this is a reminder of your appointment at {place}.", "look": {"kind": "title", "text": "See you {date}"}},
                {"say": "We will see you on {date} at {time}.", "look": {"kind": "lower_third", "title": "{date}, {time}", "sub": "{place}"}},
                {"say": "If you need to change the time, reply to this message.", "look": {"kind": "none"}}]},
    {"id": "tp_event", "name": "Event invitation", "group": "Events", "shape": "talking_head", "aspect": "16:9", "closing": "{host}",
     "scenes": [{"say": "You are invited to {event}.", "look": {"kind": "title", "text": "{event}"}},
                {"say": "Join us on {date} at {place}.", "look": {"kind": "lower_third", "title": "{date}", "sub": "{place}"}},
                {"say": "{host} would love to see you there.", "look": {"kind": "none"}},
                {"say": "Let us know if you are coming.", "look": {"kind": "none"}}]},
]
# v0.999.174: what each ready-made one is for, and a plain label + a worldwide example for every blank
TPL_LINES = {
    "tp_offer": "A special price for a festival or holiday, and the last day of the offer.",
    "tp_rate": "Today's rate or price for one thing, said clearly with the number on screen.",
    "tp_batch": "A new class or course starting, with the date and how to book a seat.",
    "tp_timing": "Tell customers your new hours or days, so nobody arrives to a closed door.",
    "tp_thanks": "A personal thank-you to one customer by name. Make one for many names at once.",
    "tp_reel": "A vertical reel: a hook, one point and where to find you. Made for social feeds.",
    "tp_remind": "A friendly reminder of a booking, with the time, the place and how to change it.",
    "tp_event": "Invite people to an event: what it is, when, where, and how to say they are coming.",
}
BLANK_LABELS: dict[str, tuple[str, str]] = {
    "festival": ("Festival or holiday", "e.g. Christmas, Eid, Diwali, Lunar New Year"),
    "shop": ("Your business name", "e.g. Bloom Florist"),
    "item": ("What it is about", "e.g. Pastel de nata box"),
    "price": ("Price", "with its currency, e.g. $12, €9, ¥980"),
    "last_date": ("Last day of the offer", "e.g. 31 December"),
    "rate": ("The rate", "with its unit, e.g. $2,341 an ounce"),
    "course": ("Course or class", "e.g. Spanish for beginners"),
    "institute": ("Your school or institute", "e.g. Lingua House"),
    "start_date": ("Start date", "e.g. 6 January"),
    "place": ("The place", "e.g. Riverside Clinic"),
    "hours": ("Opening hours", "e.g. 9 am to 7 pm"),
    "days": ("Days", "e.g. Monday to Saturday"),
    "name": ("Their name", "e.g. Amara"),
    "hook": ("The first line, to stop the scroll", "e.g. Three things nobody tells you about coffee"),
    "point": ("The one point", "e.g. Fresh beans taste better for two weeks"),
    "date": ("Date", "e.g. Thursday 14 March"),
    "time": ("Time", "e.g. 3:30 pm"),
    "event": ("The event", "e.g. our open house"),
    "host": ("Who invites", "e.g. Studio Nord"),
}
MAX_BLANKS = 12
MAX_ROWS = 50
KEY_RE = re.compile(r"^[a-z][a-z0-9_]{0,23}$")


BUILTIN_HI: dict[str, list[dict[str, Any]]] = {
    "tp_offer": [{"say": "Is {festival} par {shop} mein khaas offer.", "look": {"kind": "title", "text": "{festival} offer"}},
                 {"say": "{item} ab sirf {price} mein.", "look": {"kind": "price", "new": "{price}", "label": "{item}"}},
                 {"say": "Offer {last_date} tak. Aaj hi aaiye.", "look": {"kind": "lower_third", "title": "{shop}", "sub": "Offer {last_date} tak"}}],
    "tp_rate": [{"say": "Aaj ka {item} rate sun lijiye.", "look": {"kind": "title", "text": "{item} rate"}},
                {"say": "{item} ka rate {rate} hai.", "look": {"kind": "big_number", "value": "{rate}", "label": "{item}"}}],
    "tp_batch": [{"say": "{institute} mein {course} ka naya batch shuru ho raha hai.", "look": {"kind": "title", "text": "{course}"}},
                 {"say": "Batch {start_date} se shuru hoga.", "look": {"kind": "lower_third", "title": "Shuru: {start_date}", "sub": "{institute}"}},
                 {"say": "Seat pakki karne ke liye aaj hi sampark kijiye.", "look": {"kind": "none"}}],
    "tp_timing": [{"say": "{place} ka samay badal gaya hai.", "look": {"kind": "title", "text": "Naya samay"}},
                  {"say": "Ab hum {days} ko {hours} khule rahenge.", "look": {"kind": "lower_third", "title": "{hours}", "sub": "{days}"}}],
    "tp_thanks": [{"say": "{name} ji, {shop} par bharosa karne ke liye dhanyavaad.", "look": {"kind": "title", "text": "Dhanyavaad, {name} ji"}},
                  {"say": "Aapki seva mein hum hamesha taiyaar hain.", "look": {"kind": "none"}}],
    "tp_reel": [{"say": "{hook}", "look": {"kind": "none"}}, {"say": "{point}", "look": {"kind": "none"}},
                {"say": "Aaj hi {shop} aaiye.", "look": {"kind": "none"}}],
}


def _clip(v: Any, n: int) -> str:
    return re.sub(r"\s+", " ", str(v or "").strip())[:n]


def _d(tenant: str) -> dict[str, Any]:
    d = S._load(tenant)
    d.setdefault("brand", {})
    for k in ("glossary", "templates", "trash", "brains"):
        d.setdefault(k, [])
    return d


def _strings(scenes: list[dict[str, Any]], closing: str = "") -> list[str]:
    out = [closing]
    for s in scenes:
        out.append(str(s.get("say") or ""))
        lk = s.get("look") or {}
        out += [str(lk.get(k) or "") for k in ALL_KEYS]
        out += [str(b.get(k) or "") for b in (lk.get("bars") or []) for k in ("label", "value")]
    return out


def variables(scenes: list[dict[str, Any]], closing: str = "") -> list[str]:
    seen: list[str] = []
    for t in _strings(scenes, closing):
        for v in VAR.findall(t):
            if v not in seen:
                seen.append(v)
    return seen


def _fill(scenes: list[dict[str, Any]], values: dict[str, str]) -> list[dict[str, Any]]:
    sub = lambda t: VAR.sub(lambda m: values.get(m.group(1), m.group(0)), str(t or ""))  # noqa: E731
    out = []
    for s in scenes:
        lk = dict(s.get("look") or {"kind": "none"})
        for k in ALL_KEYS:
            if lk.get(k):
                lk[k] = sub(lk[k])
        if lk.get("bars"):
            lk["bars"] = [{"label": sub(b.get("label")), "value": sub(b.get("value"))} for b in lk["bars"]]
        out.append({"say": sub(s.get("say")), "look": lk})
    return out


def _new_project(tenant: str, d: dict[str, Any], *, title: str, scenes: list[dict[str, Any]], shape: str, lang: str,
                 aspect: str, closing: str = "", avatar_id: str = "", facts: list[str] | None = None,
                 extra: dict[str, Any] | None = None) -> dict[str, Any]:
    facts = [str(f) for f in (facts or [])]
    her = " ".join(facts)
    shape = shape if shape in S.SHAPES else "talking_head"
    if avatar_id and not any(a["id"] == avatar_id for a in d["avatars"]):
        avatar_id = ""
    p = {"id": "iv_" + uuid.uuid4().hex[:10], "title": _clip(title, 80) or "Untitled", "ask": "", "facts": facts,
         "shape": shape, "lang": S.lang_of(lang),
         "aspect": "9:16" if shape == "reel" else (aspect if aspect in ("16:9", "1:1") else "16:9"),
         "avatar_id": avatar_id, "brand": _clip(d["brand"].get("name"), 40),
         "scenes": [S.clean_scene(s, her, trust_numbers=True) for s in scenes[:S.MAX_SCENES]],
         "items": [], "closing": _clip(closing, 80), "status": "draft", "error": "", "video": None,
         "created": S._now_iso(), "updated": S._now_iso(), **(extra or {})}
    p["scenes"] = [s for s in p["scenes"] if s["say"]]
    if not p["scenes"]:
        raise S.StudioError("There is nothing to say in this video.")
    d["projects"].insert(0, p)
    d["projects"] = d["projects"][:S.MAX_PROJECTS]
    return p


# ------------------------------------------------------------------ brand + glossary ---
def brand_set(tenant: str, body: dict[str, Any]) -> dict[str, Any]:
    color = str(body.get("color") or "").strip()
    if color and not HEX.match(color):
        raise S.StudioError("The colour must look like #5B45E0.")
    with S._LOCK:
        d = _d(tenant)
        d["brand"] = {"name": _clip(body.get("name"), 40), "closing": _clip(body.get("closing"), 80), "color": color.upper()}
        S._store(tenant, d)
        return d["brand"]


def glossary_add(tenant: str, term: str, mode: str = "keep", to: str = "", lang: str = "") -> list[dict[str, Any]]:
    term, to = _clip(term, 40), _clip(to, 60)
    if len(term) < 2:
        raise S.StudioError("Type the word.")
    if mode not in ("keep", "as"):
        raise S.StudioError("Choose: keep as written, or always translate as.")
    if mode == "as" and (not to or S.lang_of(lang) != lang):
        raise S.StudioError("Say what it becomes, and in which language.")
    with S._LOCK:
        d = _d(tenant)
        d["glossary"] = [g for g in d["glossary"] if not (g["term"].lower() == term.lower() and g.get("lang", "") == (lang if mode == "as" else ""))]
        if len(d["glossary"]) >= MAX_GLOSSARY:
            raise S.StudioError(f"The glossary holds {MAX_GLOSSARY} words - remove one first.")
        d["glossary"].insert(0, {"id": "gl_" + uuid.uuid4().hex[:8], "term": term, "mode": mode,
                                 "to": to if mode == "as" else "", "lang": lang if mode == "as" else ""})
        S._store(tenant, d)
        return d["glossary"]


def glossary_remove(tenant: str, gid: str) -> list[dict[str, Any]]:
    with S._LOCK:
        d = _d(tenant)
        d["glossary"] = [g for g in d["glossary"] if g["id"] != gid]
        S._store(tenant, d)
        return d["glossary"]


# ------------------------------------------------------------------ templates ---
def _seconds(t: dict[str, Any]) -> float:
    """About how long it plays: 2.6 spoken words a second per scene (a blank counts as two words), plus the closing card."""
    n = 0.0
    for s in t["scenes"]:
        words = len(VAR.sub("w w", str(s.get("say") or "")).split())
        n += max(2.0, words / 2.6) + .35
    return round(n + (2.2 if t.get("closing") else 1.2), 1)


def _blanks(t: dict[str, Any]) -> list[dict[str, Any]]:
    labels = t.get("labels") or {}
    out = []
    order = variables(t["scenes"]) + [v for v in variables([], t.get("closing", "")) if v not in variables(t["scenes"])]
    for v in order:
        where = [i + 1 for i, sc in enumerate(t["scenes"]) if any(v in VAR.findall(x) for x in _strings([sc]))]
        lab, ex = labels.get(v) or BLANK_LABELS.get(v) or (v.replace("_", " ").capitalize(), "")
        out.append({"key": v, "label": lab, "example": ex, "where": where, "closing": v in VAR.findall(t.get("closing", ""))})
    return out


def _tpl_view(t: dict[str, Any], mine: bool, used: int = 0) -> dict[str, Any]:
    return {**t, "mine": mine, "variables": variables(t["scenes"], t.get("closing", "")), "count": len(t["scenes"]),
            "blanks": _blanks(t), "seconds": _seconds(t), "line": t.get("line") or TPL_LINES.get(t["id"], ""),
            "lang": t.get("lang") or "en", "used": used}


def templates(tenant: str) -> list[dict[str, Any]]:
    d = _d(tenant)
    used: dict[str, int] = {}
    for p in d["projects"]:
        if p.get("template"):
            used[p["template"]] = used.get(p["template"], 0) + 1
    return ([_tpl_view(t, True, used.get(t["id"], 0)) for t in d["templates"]]
            + [_tpl_view(t, False, used.get(t["id"], 0)) for t in BUILTIN])


# ---- a word she marks as a blank: found by code in her video's own words
_MON = "jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec"
_SUGGEST = [
    ("price", re.compile(r"(?:[$\u20ac\u00a3\u00a5\u20b9\u20a9\u20ba\u20a6\u20b1]|R\$|AED|SAR|USD|EUR|GBP|INR|Rs\.?)\s?\d[\d,.]*|\d[\d,.]*\s?(?:[$\u20ac\u00a3\u00a5\u20b9]|USD|EUR|GBP|INR|AED|SAR|yen|euros?|dollars?|rupees?)\b", re.I)),
    ("percent", re.compile(r"\d[\d.,]*\s?%")),
    ("time", re.compile(r"\b\d{1,2}(?::\d{2})?\s?(?:am|pm)\b|\b\d{1,2}:\d{2}\b", re.I)),
    ("date", re.compile(rf"\b\d{{1,2}}(?:st|nd|rd|th)?\s(?:{_MON})[a-z]*\b|\b(?:{_MON})[a-z]*\s\d{{1,2}}(?:st|nd|rd|th)?\b|\b\d{{1,2}}/\d{{1,2}}(?:/\d{{2,4}})?\b", re.I)),
    ("day", re.compile(r"\b(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b", re.I)),
    ("number", re.compile(r"\b\d[\d,.]{1,}\b")),
]


def blank_suggestions(tenant: str, pid: str) -> list[dict[str, Any]]:
    """Words in HER video that look like they change: prices, percents, times, dates, days, numbers, her business name.
    Code only - nothing is sent anywhere; she picks which become blanks."""
    with S._LOCK:
        d = _d(tenant)
        p = copy.deepcopy(S._find(d, pid))
    texts = _strings(p["scenes"], p.get("closing", ""))
    out: list[dict[str, Any]] = []
    seen: set[str] = set()

    def add(text: str, kind: str) -> None:
        text = text.strip(" .,;:")
        if not text or text.lower() in seen or len(out) >= 10:
            return
        if any(text.lower() in x["text"].lower() for x in out):
            return
        seen.add(text.lower())
        key = kind if kind not in [x["key"] for x in out] else f"{kind}_{sum(1 for x in out if x['kind'] == kind) + 1}"
        out.append({"text": text, "key": key, "kind": kind})
    for name in (p.get("brand"), d["brand"].get("name")):
        if name and any(name in t for t in texts):
            add(str(name), "shop")
    for kind, rx in _SUGGEST:
        for t in texts:
            for m in rx.finditer(t):
                if kind == "number" and any(m.group(0) in x["text"] for x in out):
                    continue
                add(m.group(0), kind)
    return out


def _key(v: Any) -> str:
    k = re.sub(r"[^a-z0-9_]+", "_", str(v or "").strip().lower()).strip("_")[:24]
    return k if KEY_RE.match(k) else ""


def _blank_out(scenes: list[dict[str, Any]], closing: str, blanks: list[Any]) -> tuple[list[dict[str, Any]], str, dict[str, Any]]:
    """Each {text, key, label} she marked becomes {key} wherever that exact text is in the words. A text that is not there refuses."""
    scenes = copy.deepcopy(scenes)
    labels: dict[str, tuple[str, str]] = {}
    if len(blanks) > MAX_BLANKS:
        raise S.StudioError(f"A template can have up to {MAX_BLANKS} blanks.")
    for b in sorted([x for x in blanks if isinstance(x, dict)], key=lambda x: -len(str(x.get("text") or ""))):
        text, key = _clip(b.get("text"), 60), _key(b.get("key") or b.get("label") or b.get("text"))
        if not text:
            continue
        if not key:
            raise S.StudioError(f"Give \u201c{text}\u201d a short name, like price or date.")
        tag = "{" + key + "}"
        hits = 0

        def sub(v: Any) -> str:
            nonlocal hits
            v = str(v or "")
            hits += v.count(text)
            return v.replace(text, tag)
        for sc in scenes:
            sc["say"] = sub(sc.get("say"))
            lk = sc.get("look") or {}
            for k in ALL_KEYS:
                if lk.get(k):
                    lk[k] = sub(lk[k])
            for bar in lk.get("bars") or []:
                for k in ("label", "value"):
                    if bar.get(k):
                        bar[k] = sub(bar[k])
        if text in closing:
            hits += 1
            closing = closing.replace(text, tag)
        if not hits:
            raise S.StudioError(f"\u201c{text}\u201d is not in this video's words.")
        labels[key] = (_clip(b.get("label"), 40) or key.replace("_", " ").capitalize(), _clip(b.get("example"), 60) or f"e.g. {text}")
    return scenes, closing, labels


def template_save(tenant: str, pid: str, name: str = "", blanks: list[Any] | None = None) -> dict[str, Any]:
    """Her video as a template. The words she marked become blanks; the video itself is not changed."""
    with S._LOCK:
        d = _d(tenant)
        p = S._find(d, pid)
        if len(d["templates"]) >= MAX_TEMPLATES:
            raise S.StudioError(f"You have {MAX_TEMPLATES} templates - remove one first.")
        scenes, closing, labels = _blank_out([{"say": s["say"], "look": copy.deepcopy(s["look"])} for s in p["scenes"]],
                                             p.get("closing", ""), list(blanks or []))
        t = {"id": "tp_" + uuid.uuid4().hex[:10], "name": _clip(name, 60) or p["title"], "group": "Mine",
             "shape": p["shape"], "aspect": p["aspect"], "closing": closing, "lang": p.get("lang") or "en",
             "labels": labels, "from": p["title"], "line": f"From \u201c{_clip(p['title'], 60)}\u201d",
             "scenes": scenes, "created": S._now_iso()}
        d["templates"].insert(0, t)
        S._store(tenant, d)
        return _tpl_view(t, True)


def template_remove(tenant: str, tid: str) -> bool:
    with S._LOCK:
        d = _d(tenant)
        keep = [t for t in d["templates"] if t["id"] != tid]
        if len(keep) == len(d["templates"]):
            raise S.StudioError("That template was not found.")
        d["templates"] = keep
        S._store(tenant, d)
        return True


def _template(d: dict[str, Any], tid: str, lang: str = "") -> dict[str, Any]:
    for t in d["templates"] + BUILTIN:
        if t["id"] == tid:
            if lang == "hi" and tid in BUILTIN_HI and t in BUILTIN:
                return {**t, "scenes": BUILTIN_HI[tid]}
            return t
    raise S.StudioError("That template was not found.")


def _use_one(tenant: str, d: dict[str, Any], t: dict[str, Any], vals: dict[str, str], lang: str, avatar_id: str,
             title: str) -> dict[str, Any]:
    missing = [v for v in variables(t["scenes"], t.get("closing", "")) if not vals.get(v)]
    if missing:
        names = {b["key"]: b["label"] for b in _blanks(t)}
        raise S.StudioError("Fill in: " + ", ".join(names.get(m, m.replace("_", " ")).lower() for m in missing) + ".")
    closing = VAR.sub(lambda m: vals.get(m.group(1), ""), t.get("closing", ""))
    return _new_project(tenant, d, title=title or t["name"], scenes=_fill(t["scenes"], vals), shape=t["shape"], lang=lang,
                        aspect=t["aspect"], closing=closing or d["brand"].get("closing", ""), avatar_id=avatar_id,
                        facts=list(vals.values()), extra={"template": t["id"]})


def _settle(tenant: str, p: dict[str, Any], opts: dict[str, Any]) -> dict[str, Any]:
    """Her picks on the Use page - frame, voice, engine, where the face sits - through the Studio's own save."""
    body = {k: opts[k] for k in ("aspect", "voice", "engine", "face_layout") if opts.get(k) not in (None, "")}
    if opts.get("aspect") == "9:16" and p["shape"] != "reel":
        body = {**body, "shape": "reel"}
        body.pop("aspect", None)
    return S.save(tenant, p["id"], body) if body else p


def template_use(tenant: str, tid: str, values: dict[str, Any], lang: str = "en", avatar_id: str = "",
                 title: str = "", opts: dict[str, Any] | None = None,
                 think: Callable[[str, str], dict[str, Any]] | None = None) -> dict[str, Any]:
    """Fill a template from HER values. A blank she left empty refuses by name - nothing is ever filled in for her.
    In a language the template is not written in, the filled words are translated (names, prices and dates checked)."""
    vals = {str(k): _clip(v, 60) for k, v in (values or {}).items()}
    with S._LOCK:
        d = _d(tenant)
        base = next((x for x in d["templates"] + BUILTIN if x["id"] == tid), None)
        if base is None:
            raise S.StudioError("That template was not found.")
        src = base.get("lang") or "en"
        lang = src if lang in ("", "auto") else lang
        direct = lang == src or (lang == "hi" and tid in BUILTIN_HI and base in BUILTIN)
        t = _template(d, tid, lang if direct else src)
        p = _use_one(tenant, d, t, vals, lang if direct else src, avatar_id, title)
        S._store(tenant, d)
    note = ""
    if not direct:
        try:
            tr = translate(tenant, p["id"], lang, think=think)
            with S._LOCK:
                d = _d(tenant)
                d["projects"] = [x for x in d["projects"] if x["id"] != p["id"]]
                for x in d["projects"]:
                    if x["id"] == tr["id"]:
                        x["template"], x["title"] = tid, _clip(title, 80) or t["name"]
                        tr = x
                S._store(tenant, d)
            p = tr
        except S.StudioError:
            note = f"Hoola could not translate it just now, so the draft is in {S.lang_label(src)}. Use Translate in the Studio."
    p = _settle(tenant, p, opts or {})
    return {**p, "notice": note} if note else p


def template_many(tenant: str, tid: str, rows: list[Any], lang: str = "en", avatar_id: str = "",
                  opts: dict[str, Any] | None = None, think: Callable[[str, str], dict[str, Any]] | None = None) -> dict[str, Any]:
    """One draft per row of her sheet. A row with an empty blank is skipped and named, never filled in."""
    rows = [r for r in (rows or []) if isinstance(r, dict)]
    if not rows:
        raise S.StudioError("The sheet has no rows.")
    if len(rows) > MAX_ROWS:
        raise S.StudioError(f"Up to {MAX_ROWS} rows at a time.")
    made: list[str] = []
    skipped: list[dict[str, Any]] = []
    for n, row in enumerate(rows, start=1):
        vals = {_key(k): v for k, v in row.items() if _key(k)}
        title = str(row.get("title") or "")
        try:
            p = template_use(tenant, tid, vals, lang=lang, avatar_id=avatar_id, title=title, opts=opts, think=think)
            made.append(p["id"])
        except S.StudioError as e:
            if "not found" in str(e):
                raise
            skipped.append({"row": n, "why": str(e)})
    return {"made": made, "skipped": skipped}


# ------------------------------------------------------------------ batch + names ---
def _sentences(text: str) -> list[str]:
    parts = [p.strip() for p in re.split(r"(?<=[.!?।])\s+", _clip(text, 2400)) if p.strip()]
    out: list[str] = []
    for part in parts:                                    # a sentence longer than one scene is cut at a comma or a space
        while len(part) > S.MAX_SAY:
            cut = max(part.rfind(",", 0, S.MAX_SAY), part.rfind(" ", 0, S.MAX_SAY))
            cut = cut if cut > 40 else S.MAX_SAY
            out.append(part[:cut].strip(" ,"))
            part = part[cut:].strip(" ,")
        if part:
            out.append(part)
    return out[:S.MAX_SCENES]


def batch(tenant: str, scripts: list[Any], shape: str = "talking_head", lang: str = "en", avatar_id: str = "") -> list[dict[str, Any]]:
    """Many scripts -> one draft each. Scenes are cut at sentence ends by code; her words are not rewritten."""
    texts = [_clip(s, 2400) for s in (scripts or []) if _clip(s, 2400)]
    if not texts:
        raise S.StudioError("Write at least one script.")
    if len(texts) > MAX_BATCH:
        raise S.StudioError(f"At most {MAX_BATCH} scripts at a time.")
    made = []
    with S._LOCK:
        d = _d(tenant)
        for t in texts:
            scenes = [{"say": s, "look": {"kind": "none"}} for s in _sentences(t)]
            made.append(_new_project(tenant, d, title=t[:60], scenes=scenes, shape=shape, lang=lang, aspect="16:9",
                                     closing=d["brand"].get("closing", ""), avatar_id=avatar_id, facts=[t], extra={"batch": True}))
        S._store(tenant, d)
    return made


def personalise(tenant: str, pid: str, names: list[Any]) -> list[dict[str, Any]]:
    """One video that says {name} -> a draft per name. Sending is never done here; the people are hers to choose."""
    clean: list[str] = []
    for n in names or []:
        n = _clip(n, 40)
        if n and n.lower() not in [c.lower() for c in clean]:
            clean.append(n)
    if not clean:
        raise S.StudioError("Add at least one name.")
    if len(clean) > MAX_BATCH:
        raise S.StudioError(f"At most {MAX_BATCH} names at a time.")
    made = []
    with S._LOCK:
        d = _d(tenant)
        src = S._find(d, pid)
        if "name" not in variables(src["scenes"], src.get("closing", "")):
            raise S.StudioError("Write {name} in the script where the person's name should be said.")
        for n in clean:
            vals = {"name": n}
            closing = VAR.sub(lambda m: vals.get(m.group(1), m.group(0)), src.get("closing", ""))
            made.append(_new_project(tenant, d, title=f"{src['title']} - {n}", scenes=_fill(src["scenes"], vals),
                                     shape=src["shape"], lang=src["lang"], aspect=src["aspect"], closing=closing,
                                     avatar_id=src.get("avatar_id", ""), facts=[n] + src.get("facts", []) + [src.get("ask", "")],
                                     extra={"personal": pid}))
        S._store(tenant, d)
    return made


# ------------------------------------------------------------------ projects: copy, trash ---
def duplicate(tenant: str, pid: str) -> dict[str, Any]:
    with S._LOCK:
        d = _d(tenant)
        src = S._find(d, pid)
        p = copy.deepcopy(src)
        p.update(id="iv_" + uuid.uuid4().hex[:10], title=_clip(src["title"] + " (copy)", 80), status="draft", error="",
                 video=None, created=S._now_iso(), updated=S._now_iso())
        d["projects"].insert(0, p)
        d["projects"] = d["projects"][:S.MAX_PROJECTS]
        S._store(tenant, d)
        return p


def _purge(tenant: str, d: dict[str, Any], everything: bool = False) -> int:
    limit = time.time() - TRASH_DAYS * 86400
    keep, gone = [], 0
    for p in d["trash"]:
        if everything or float(p.get("trashed_ts") or 0) < limit:
            S.video_path(tenant, p["id"]).unlink(missing_ok=True)
            gone += 1
        else:
            keep.append(p)
    d["trash"] = keep
    return gone


def trash(tenant: str, pid: str) -> bool:
    with S._LOCK:
        if S.running_for(tenant) == pid:
            raise S.StudioError("This video is being made - stop it first.")
        d = _d(tenant)
        p = S._find(d, pid)
        d["projects"] = [x for x in d["projects"] if x["id"] != pid]
        p["trashed"], p["trashed_ts"] = S._now_iso(), time.time()
        d["trash"].insert(0, p)
        _purge(tenant, d)
        S._store(tenant, d)
        return True


def restore(tenant: str, pid: str) -> dict[str, Any]:
    with S._LOCK:
        d = _d(tenant)
        p = next((x for x in d["trash"] if x["id"] == pid), None)
        if p is None:
            raise S.StudioError("That video is not in the trash.")
        d["trash"] = [x for x in d["trash"] if x["id"] != pid]
        p.pop("trashed", None)
        p.pop("trashed_ts", None)
        if p.get("status") == "ready" and not S.video_path(tenant, pid).is_file():
            p["status"], p["video"] = "draft", None            # the file is gone: say so by state, never show a dead player
        d["projects"].insert(0, p)
        S._store(tenant, d)
        return p


def empty_trash(tenant: str) -> int:
    with S._LOCK:
        d = _d(tenant)
        n = _purge(tenant, d, everything=True)
        S._store(tenant, d)
        return n


# ------------------------------------------------------------------ translate ---
_TR_SYSTEM = """You translate the lines of a short business video for a business or person anywhere in the world. Translate each
line into the target language the way a local shopkeeper would say it aloud (Roman script unless the source line is in
another script). Keep every number, price, percentage, date, phone number and proper name EXACTLY as written. Follow
the glossary: a KEEP word stays exactly as written; an AS word must be written the given way. Return ONLY JSON:
{"lines": ["...", "..."]} with exactly as many lines as you were given, in the same order. An empty line stays empty."""


def _think(system: str, prompt: str) -> dict[str, Any]:
    return S._brain(system, prompt)


def _line_flag(src: str, out: str, rules: list[dict[str, Any]], lang: str) -> str:
    if S._digits(src) != S._digits(out):
        return "A number changed - check this line"
    for g in rules:
        if re.search(r"(?<!\w)" + re.escape(g["term"]) + r"(?!\w)", src, re.I):
            if g["mode"] == "keep" and g["term"].lower() not in out.lower():
                return f"'{g['term']}' must stay as written"
            if g["mode"] == "as" and g.get("lang") == lang and g["to"].lower() not in out.lower():
                return f"'{g['term']}' should be '{g['to']}'"
    return ""


def translate(tenant: str, pid: str, lang: str, think: Callable[[str, str], dict[str, Any]] | None = None) -> dict[str, Any]:
    """A NEW draft of the same video in `lang`. Words by one model call; numbers and glossary rules checked by code."""
    if not lang or S.lang_of(lang) != lang:
        raise S.StudioError("Choose a language.")
    with S._LOCK:
        d = _d(tenant)
        src = copy.deepcopy(S._find(d, pid))
        rules = [g for g in d["glossary"] if g["mode"] == "keep" or g.get("lang") == lang]
    if src["lang"] == lang:
        raise S.StudioError(f"This video is already in {S.lang_label(lang)}.")
    slots: list[tuple[int, str]] = []                      # (scene index, key) for every string that is words
    lines: list[str] = []
    for i, s in enumerate(src["scenes"]):
        slots.append((i, "say"))
        lines.append(s["say"])
        for k in TEXT_KEYS:
            if (s["look"] or {}).get(k):
                slots.append((i, k))
                lines.append(str(s["look"][k]))
    gl = "\n".join(f"KEEP {g['term']}" if g["mode"] == "keep" else f"AS {g['term']} => {g['to']}" for g in rules) or "(none)"
    prompt = (f"Source language: {S.lang_label(src['lang'])}\nTarget language: {S.lang_label(lang)}\nGlossary:\n{gl}\n"
              "Lines:\n" + "\n".join(f"{n + 1}. {t}" for n, t in enumerate(lines)))
    out = (think or _think)(_TR_SYSTEM, prompt)
    got = out.get("lines") if isinstance(out, dict) else None
    if not isinstance(got, list) or len(got) != len(lines):
        raise S.StudioError("Hoola could not translate this just now. Try again in a minute.")
    scenes = copy.deepcopy(src["scenes"])
    notes: list[dict[str, Any]] = [{"src": s["say"], "flag": ""} for s in scenes]
    for (i, key), a, b in zip(slots, lines, got):
        b = _clip(b, S.MAX_SAY if key == "say" else 60)
        flag = _line_flag(a, b, rules, lang) if b else "Not translated - check this line"
        if key == "say":
            scenes[i]["say"] = b or a
        else:
            scenes[i]["look"][key] = b or a
        if flag and not notes[i]["flag"]:
            notes[i]["flag"] = flag
    with S._LOCK:
        d = _d(tenant)
        p = _new_project(tenant, d, title=f"{src['title']} ({S.lang_label(lang)})", scenes=scenes, shape=src["shape"], lang=lang,
                         aspect=src["aspect"], closing=src.get("closing", ""), avatar_id=src.get("avatar_id", ""),
                         facts=src.get("facts", []) + [src.get("ask", "")] + _strings(src["scenes"]),
                         extra={"from": pid, "from_lang": src["lang"], "tr": notes, "items": src.get("items", [])})
        S._store(tenant, d)
        return p


# ------------------------------------------------------------------ live brains ---
def brain_save(tenant: str, body: dict[str, Any]) -> dict[str, Any]:
    name, knows = _clip(body.get("name"), 40), str(body.get("knows") or "").strip()[:4000]
    if not name:
        raise S.StudioError("Give it a name.")
    if len(knows) < 20:
        raise S.StudioError("Write what it should know - your timings, products, prices, address.")
    links = [_clip(u, 200) for u in (body.get("links") or []) if re.match(r"^https?://", _clip(u, 200))][:5]
    with S._LOCK:
        d = _d(tenant)
        bid = str(body.get("id") or "")
        row = next((b for b in d["brains"] if b["id"] == bid), None)
        if row is None:
            if len(d["brains"]) >= MAX_BRAINS:
                raise S.StudioError(f"You have {MAX_BRAINS} brains - remove one first.")
            row = {"id": "br_" + uuid.uuid4().hex[:8], "created": S._now_iso()}
            d["brains"].insert(0, row)
        row.update(name=name, knows=knows, opening=_clip(body.get("opening"), 160), links=links,
                   lang=body.get("lang") if body.get("lang") and S.lang_of(body.get("lang")) == body.get("lang") else "hi", updated=S._now_iso())
        S._store(tenant, d)
        return row


def brain_remove(tenant: str, bid: str) -> bool:
    with S._LOCK:
        d = _d(tenant)
        d["brains"] = [b for b in d["brains"] if b["id"] != bid]
        S._store(tenant, d)
        return True


# ------------------------------------------------------------------ usage + status ---
def usage(tenant: str, d: dict[str, Any] | None = None) -> dict[str, Any]:
    d = d or _d(tenant)
    month = time.strftime("%Y-%m")
    rows = [p for p in d["projects"] if p.get("video") and str(p["video"].get("made") or "").startswith(month)]
    secs = sum(float(p["video"].get("duration") or 0) for p in rows)
    by: dict[str, float] = {}
    for p in rows:
        by[p["lang"]] = by.get(p["lang"], 0.0) + float(p["video"].get("duration") or 0)
    return {"month": month, "videos": len(rows), "minutes": round(secs / 60, 1),
            "by_language": [{"lang": S.lang_label(k), "minutes": round(v / 60, 1)} for k, v in sorted(by.items(), key=lambda kv: -kv[1])],
            "recent": [{"title": p["title"], "made": p["video"].get("made"), "seconds": round(float(p["video"].get("duration") or 0))}
                       for p in sorted(rows, key=lambda p: str(p["video"].get("made")), reverse=True)[:8]],
            "stored": len([p for p in d["projects"] if p.get("video")]), "kept_max": S.MAX_VIDEOS}


def status() -> dict[str, Any]:
    """What is connected on THIS server right now - the page prints exactly this, good or not."""
    from . import lab
    r = S.readiness()
    return {**r, "connected": {
        "video": bool(r["draw"]), "voice": bool(r["voice"]), "photo_avatar": True, "templates": True, "translate_words": True,
        "twin": False, "ai_face": False, "voice_clone": False, "dub_outside_video": False, "live_stream": False, "api": False},
        "engine": bool(lab.configured())}


def overview(tenant: str) -> dict[str, Any]:
    with S._LOCK:
        d = _d(tenant)
        if _purge(tenant, d):
            S._store(tenant, d)
    return {"projects": d["projects"], "avatars": d["avatars"], "running": S.running_for(tenant), "brand": d["brand"],
            "glossary": d["glossary"], "templates": templates(tenant), "trash": d["trash"], "brains": d["brains"],
            "usage": usage(tenant, d), "status": status(), "limits": {"batch": MAX_BATCH, "trash_days": TRASH_DAYS}}


# ------------------------------------------------------------------ apps (v0.999.175) ---
APPS: list[dict[str, Any]] = [
    {"id": "podcast", "group": "voice", "name": "Podcast with two hosts", "where": "vocal", "page": "dialogue", "cost": "priced",
     "line": "A script from your document or notes, two voices talking, music under it.", "needs": "the voice engine"},
    {"id": "cleanup", "group": "voice", "name": "Clean up a recording", "where": "vocal", "page": "cleanup", "cost": "free",
     "line": "Background noise out, loud words softened, long pauses shortened.", "needs": "the sound tools on the server"},
    {"id": "ownvoice", "group": "voice", "name": "Your own voice", "where": "vocal", "page": "mine", "cost": "priced",
     "line": "Your voice, copied with your spoken consent, or a new one designed from words.", "needs": "a voice engine that can copy or design voices"},
    {"id": "music", "group": "voice", "name": "Music under a video", "where": "create", "page": "music", "cost": "priced",
     "line": "A short jingle or a song in any language, for your video.", "needs": "the music engine"},
    {"id": "broll", "group": "shots", "name": "A B-roll shot", "where": "here", "page": "broll", "cost": "priced",
     "line": "A few seconds of the shop, the product or the street. No person in it.", "needs": "the B-roll engine"},
    {"id": "translate", "group": "shots", "name": "Translate a video", "where": "here", "page": "translate", "cost": "free_draft",
     "line": "A new draft of any video in another language. Names, prices and dates kept.", "needs": ""},
    {"id": "dub", "group": "shots", "name": "Dub a video", "where": "vocal", "page": "dub", "cost": "priced",
     "line": "A video you have, spoken in another language by matched voices.", "needs": "the dubbing engine"},
    {"id": "lipsync", "group": "shots", "name": "Lip sync a video", "where": "create", "page": "cinema", "cost": "priced",
     "line": "A video of you, its lips moved to new words. Your consent is asked first.", "needs": "the lip-sync engine"},
    {"id": "batch", "group": "many", "name": "A batch of videos", "where": "here", "page": "batch", "cost": "free_drafts",
     "line": "Paste several scripts; each becomes its own draft with your face and voice.", "needs": ""},
    {"id": "names", "group": "many", "name": "One video, many names", "where": "here", "page": "names", "cost": "free_drafts",
     "line": "The same video, said to each person by name.", "needs": ""},
    {"id": "sheet", "group": "many", "name": "From a sheet", "where": "here", "page": "sheet", "cost": "free_drafts",
     "line": "A template filled from each row of your spreadsheet: names, prices, dates.", "needs": ""},
    {"id": "aiface", "group": "many", "name": "An AI-made face", "where": "create", "page": "image", "cost": "priced",
     "line": "A presenter who is no real person, marked as AI wherever it is used.", "needs": "the picture engine"},
]


def _app_ready() -> dict[str, bool]:
    """Each app's real state on THIS server, read from the engines it uses - never a guess."""
    from . import engines as EN
    out: dict[str, bool] = {a["id"]: True for a in APPS}
    try:
        from ..vocal import service as VS
        c = VS.connected()
        out.update(podcast=bool(c["dialogue"]), cleanup=bool(c["cleanup"]), ownvoice=bool(c["clone"] or c["design"]), dub=bool(c["dub"]))
    except Exception:   # noqa: BLE001
        out.update(podcast=False, cleanup=False, ownvoice=False, dub=False)
    try:
        from ..create import service as CS
        r = CS.ready()
        out.update(music=bool(r.get("song")), aiface=bool(r.get("image")))
    except Exception:   # noqa: BLE001
        out.update(music=False, aiface=False)
    try:
        from ..cinema import kie
        out["lipsync"] = bool(kie.configured())
    except Exception:   # noqa: BLE001
        out["lipsync"] = False
    try:
        out["broll"] = bool(EN.connected("gemini_broll"))
    except Exception:   # noqa: BLE001
        out["broll"] = False
    return out


def apps(tenant: str) -> dict[str, Any]:
    ready = _app_ready()
    used = dict(_d(tenant).get("apps_used") or {})
    rows = [{**a, "ready": ready.get(a["id"], False), "used": used.get(a["id"], "")} for a in APPS]
    return {"apps": rows, "recent": [a for a in sorted(rows, key=lambda x: x["used"], reverse=True) if a["used"]][:3]}


def app_used(tenant: str, aid: str) -> dict[str, Any]:
    if aid not in {a["id"] for a in APPS}:
        raise S.StudioError("That app was not found.")
    with S._LOCK:
        d = _d(tenant)
        d.setdefault("apps_used", {})[aid] = S._now_iso()
        S._store(tenant, d)
    return {"ok": True}


def voice_sample(lang: str) -> bytes:
    """A short spoken line in the Hoola voice, so she can hear it before she picks. Needs the engine."""
    from . import lab
    line = {"hi": "Namaste, aapke video mein meri awaaz aisi sunai degi.", "mr": "Namaskar, tumchya video madhe mi asa bolto."}.get(
        lang, "Hello, this is how I sound in your videos.")
    return lab.voice(line, lang=S.lang_of(lang))
