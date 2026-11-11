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
     "scenes": [{"say": "Here is today's rate for {item}.", "look": {"kind": "title", "text": "{item} rate"}},
                {"say": "The rate for {item} is {rate}.", "look": {"kind": "big_number", "value": "{rate}", "label": "{item}"}}]},
    {"id": "tp_batch", "name": "New batch opening", "group": "Lessons", "shape": "talking_head", "aspect": "16:9", "closing": "{institute}",
     "scenes": [{"say": "A new batch of {course} is starting at {institute}.", "look": {"kind": "title", "text": "{course}"}},
                {"say": "The batch starts on {start_date}.", "look": {"kind": "lower_third", "title": "Starts: {start_date}", "sub": "{institute}"}},
                {"say": "Contact us today to confirm your seat.", "look": {"kind": "none"}}]},
    {"id": "tp_timing", "name": "Timing change", "group": "Updates", "shape": "talking_head", "aspect": "16:9", "closing": "{place}",
     "scenes": [{"say": "The timings of {place} have changed.", "look": {"kind": "title", "text": "New timings"}},
                {"say": "We are now open {hours}, {days}.", "look": {"kind": "lower_third", "title": "{hours}", "sub": "{days}"}}]},
    {"id": "tp_thanks", "name": "Thank-you to a customer", "group": "Greetings", "shape": "talking_head", "aspect": "16:9", "closing": "{shop}",
     "scenes": [{"say": "{name}, thank you for trusting {shop}.", "look": {"kind": "title", "text": "Thank you, {name}"}},
                {"say": "We are always here to serve you.", "look": {"kind": "none"}}]},
    {"id": "tp_reel", "name": "Quick reel", "group": "Offers", "shape": "reel", "aspect": "9:16", "closing": "{shop}",
     "scenes": [{"say": "{hook}", "look": {"kind": "none"}}, {"say": "{point}", "look": {"kind": "none"}},
                {"say": "Visit {shop} today.", "look": {"kind": "none"}}]},
]
# The same starters as they are spoken when the video's language is Hindi (Hindi words in Latin script). Same variables.
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
         "shape": shape, "lang": lang if lang in S.LANGS else "hi",
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
    if mode == "as" and (not to or lang not in S.LANGS):
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
def _tpl_view(t: dict[str, Any], mine: bool) -> dict[str, Any]:
    return {**t, "mine": mine, "variables": variables(t["scenes"], t.get("closing", "")), "count": len(t["scenes"])}


def templates(tenant: str) -> list[dict[str, Any]]:
    return [_tpl_view(t, True) for t in _d(tenant)["templates"]] + [_tpl_view(t, False) for t in BUILTIN]


def template_save(tenant: str, pid: str, name: str = "") -> dict[str, Any]:
    with S._LOCK:
        d = _d(tenant)
        p = S._find(d, pid)
        if len(d["templates"]) >= MAX_TEMPLATES:
            raise S.StudioError(f"You have {MAX_TEMPLATES} templates - remove one first.")
        t = {"id": "tp_" + uuid.uuid4().hex[:10], "name": _clip(name, 60) or p["title"], "group": "Mine",
             "shape": p["shape"], "aspect": p["aspect"], "closing": p.get("closing", ""),
             "scenes": [{"say": s["say"], "look": copy.deepcopy(s["look"])} for s in p["scenes"]], "created": S._now_iso()}
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


def template_use(tenant: str, tid: str, values: dict[str, Any], lang: str = "en", avatar_id: str = "",
                 title: str = "") -> dict[str, Any]:
    """Fill a template from HER values. A variable she left empty refuses by name - nothing is ever filled in for her."""
    with S._LOCK:
        d = _d(tenant)
        t = _template(d, tid, lang)
        vals = {str(k): _clip(v, 60) for k, v in (values or {}).items()}
        missing = [v for v in variables(t["scenes"], t.get("closing", "")) if not vals.get(v)]
        if missing:
            raise S.StudioError("Fill in: " + ", ".join(m.replace("_", " ") for m in missing) + ".")
        closing = VAR.sub(lambda m: vals.get(m.group(1), ""), t.get("closing", ""))
        p = _new_project(tenant, d, title=title or t["name"], scenes=_fill(t["scenes"], vals), shape=t["shape"], lang=lang,
                         aspect=t["aspect"], closing=closing or d["brand"].get("closing", ""), avatar_id=avatar_id,
                         facts=list(vals.values()), extra={"template": tid})
        S._store(tenant, d)
        return p


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
_TR_SYSTEM = """You translate the lines of a short business video for an Indian small-business owner. Translate each
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
    if lang not in S.LANGS:
        raise S.StudioError("Choose a language.")
    with S._LOCK:
        d = _d(tenant)
        src = copy.deepcopy(S._find(d, pid))
        rules = [g for g in d["glossary"] if g["mode"] == "keep" or g.get("lang") == lang]
    if src["lang"] == lang:
        raise S.StudioError(f"This video is already in {S.LANGS[lang]}.")
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
    prompt = (f"Source language: {S.LANGS.get(src['lang'], src['lang'])}\nTarget language: {S.LANGS[lang]}\nGlossary:\n{gl}\n"
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
        p = _new_project(tenant, d, title=f"{src['title']} ({S.LANGS[lang]})", scenes=scenes, shape=src["shape"], lang=lang,
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
                   lang=body.get("lang") if body.get("lang") in S.LANGS else "hi", updated=S._now_iso())
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
            "by_language": [{"lang": S.LANGS.get(k, k), "minutes": round(v / 60, 1)} for k, v in sorted(by.items(), key=lambda kv: -kv[1])],
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


def voice_sample(lang: str) -> bytes:
    """A short spoken line in the Hoola voice, so she can hear it before she picks. Needs the engine."""
    from . import lab
    line = {"hi": "Namaste, aapke video mein meri awaaz aisi sunai degi.", "mr": "Namaskar, tumchya video madhe mi asa bolto."}.get(
        lang, "Hello, this is how I sound in your videos.")
    return lab.voice(line, lang=lang if lang in S.LANGS else "hi")
