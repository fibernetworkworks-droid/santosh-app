"""Her words -> a BRIEF, and the Prompt Score.

Order of trust, enforced in code:
1. CODE reads what a program can read for certain: prices, percentages, phone numbers, times, dates, quoted words
   (these are FACTS and are locked - copied, never reworded), the picture's shape, the video's length and platform.
2. Hoola's own knowledge of her business (context.py) fills a slot she left empty - labelled "from your business".
3. ONE small model call proposes the remaining slots. Code then checks the model: a value it says came from her words
   must really share its words with her text, a number it gives must be in her text, else the value is relabelled a
   SUGGESTION or dropped. The model can never add a fact.
4. Whatever is still missing in a required slot becomes a question (three at most) - never a silent invention.

The brief is stateless: the page holds it and sends it back; `validate` rebuilds it safely every time."""
from __future__ import annotations

import hashlib
import json
import logging
import re
from typing import Any, Callable

from . import anatomy as A

log = logging.getLogger("santosh.prompting")

BRIEF_V = 1
SOURCES = ("her_words", "her_memory", "her_answer", "recipe", "hoola_guess")
SOURCE_LABEL = {"her_words": "from your words", "her_memory": "from your business", "her_answer": "your answer",
                "recipe": "from the recipe", "hoola_guess": "Hoola's suggestion"}
MAX_TEXT, MAX_VALUE, MAX_Q = 2000, 400, 3
# wording that measures as useless or harmful on current models - never added by Hoola, and pointed out in hers
MAGIC = ("act as", "you are an expert", "you are a world", "think step by step", "take a deep breath", "i will tip",
         "best quality", "masterpiece", "8k", "4k uhd", "ultra realistic", "award winning", "trending on artstation")
_HINGLISH = set("hai hain ka ki ke ko mein me se par aur ya nahi nahin kya kaise banao bana do chahiye karo karna "
                "mera meri mere hamara hamari apna apni liye wala wali waala sab kuch thoda bahut accha achha "
                "dukaan dukan ghar kaam paisa abhi kal aaj bhai didi ji likho likhna dikhao batao wali".split())
_STOP = set("a an the of for to in on at and or with my our your is are be it this that as by from into about "
            "make create build need want give please banao bana do chahiye ke ki ka ko liye mere meri mera".split())


def norm(s: Any) -> str:
    t = str(s or "").lower().replace("₹", " rs ")
    t = re.sub(r"(?<=\d),(?=\d)", "", t)
    return re.sub(r"\s+", " ", t).strip()


def _tidy(s: Any, n: int = MAX_VALUE) -> str:
    return re.sub(r"\s+", " ", str(s or "")).strip()[:n]


# ---------------------------------------------------------------- 1. what code can read for certain
_SECTION_WORDS = {
    "script": ("script", "screenplay", "dialogue", "voice over", "voiceover", "reel", "youtube short", "ad film", "video ad",
               "tv ad", "storyboard"),
    "image": ("poster", "image", "photo", "picture", "banner", "logo", "thumbnail", "pamphlet", "flyer", "creative",
              "wallpaper", "tasveer", "illustration", "instagram post", "greeting"),
    "web": ("website", "web site", "site", "landing page", "webpage", "web page", "portal", "homepage", "online store"),
}


def guess_section(text: str) -> str:
    """Which section her words belong to. '' when they name none (the page then asks; chat stays chat)."""
    t = " " + norm(text) + " "
    hits = {s: sum(1 for w in words if re.search(r"(?<![a-z])" + re.escape(w) + r"(?![a-z])", t))
            for s, words in _SECTION_WORDS.items()}
    if "script" in t and hits["script"]:
        return "script"
    best = max(hits, key=lambda k: hits[k])
    return best if hits[best] else ""


_FACT_RX = [
    ("price", re.compile(r"(?:₹|\brs\.?|\binr)\s*\d[\d,]*(?:\.\d+)?(?:\s*(?:lakh|lac|crore|k)\b)?(?:\s*/-)?|"
                         r"\b\d[\d,]*(?:\.\d+)?\s*(?:rupees|rupaye|rupay|/-)", re.I)),
    ("percent", re.compile(r"\b\d{1,3}(?:\.\d+)?\s*(?:%|percent\b|per cent\b)", re.I)),
    ("phone", re.compile(r"(?<!\d)(?:\+91[\s-]?)?[6-9]\d{4}[\s-]?\d{5}(?!\d)")),
    ("time", re.compile(r"\b\d{1,2}(?::\d{2})?\s*(?:am|pm|baje)\b(?:\s*(?:to|se|-)\s*\d{1,2}(?::\d{2})?\s*(?:am|pm|baje)\b)?", re.I)),
    ("date", re.compile(r"\b\d{1,2}(?:st|nd|rd|th)?\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.?(?:\s+\d{4})?\b|"
                        r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b", re.I)),
    ("words", re.compile(r"[\"“”]([^\"“”\n]{2,120})[\"“”]")),
]


def facts_of(text: str) -> list[dict[str, str]]:
    """The facts in her words, in the order she wrote them. Each is copied exactly as written."""
    found: list[tuple[int, str, str]] = []
    taken: list[tuple[int, int]] = []
    for kind, rx in _FACT_RX:
        for m in rx.finditer(text or ""):
            a, b = m.span()
            if any(a < y and x < b for x, y in taken) and kind != "words":
                continue
            taken.append((a, b))
            found.append((a, kind, (m.group(1) if kind == "words" else m.group(0)).strip()))
    out, seen = [], set()
    for _, kind, t in sorted(found):
        if t and norm(t) not in seen:
            seen.add(norm(t))
            out.append({"text": t[:160], "kind": kind})
    return out[:20]


def lang_of(text: str) -> str:
    if re.search(r"[ऀ-ॿ]", text or ""):
        return "Hindi"
    words = re.findall(r"[a-z]+", (text or "").lower())
    return "Hinglish" if sum(1 for w in words if w in _HINGLISH) >= 2 else "English"


_SIZE = (("9:16", ("story", "reel", "status", "shorts", "vertical", "mobile wallpaper")),
         ("16:9", ("banner", "thumbnail", "youtube", "cover", "wide", "landscape", "website header", "hero")),
         ("4:5", ("poster", "pamphlet", "flyer", "portrait")),
         ("1:1", ("instagram post", "insta post", "square", "logo", "dp", "profile picture", "post")))
_PLATFORM = (("WhatsApp status video", ("whatsapp status", "status video")), ("YouTube Short", ("youtube short", "shorts")),
             ("YouTube video", ("youtube",)), ("Instagram reel", ("reel", "instagram", "insta")),
             ("TV / cable ad", ("tv ad", "cable", "television")), ("Facebook video", ("facebook", "fb video")))
_ACTION = (("Message on WhatsApp", ("whatsapp",)), ("Book an appointment", ("booking", "appointment", "book a", "slot")),
           ("Buy online", ("online order", "cart", "buy online", "sell online", "online bik", "checkout", "online store")),
           ("Send an enquiry", ("enquiry", "inquiry", "lead", "quote")), ("Call us", ("call us", "phone call")))
_COLOURS = ("red", "blue", "green", "yellow", "orange", "pink", "purple", "violet", "black", "white", "gold", "golden",
            "silver", "brown", "maroon", "saffron", "cream", "beige", "teal", "navy", "grey", "gray", "pastel", "neon")


def _first(t: str, table) -> str:
    for value, words in table:
        if any(re.search(r"(?<![a-z])" + re.escape(w) + r"(?![a-z])", t) for w in words):
            return value
    return ""


def code_slots(section: str, text: str) -> dict[str, str]:
    """Slots a program can fill from her words with certainty."""
    t = norm(text)
    out: dict[str, str] = {}
    if section == "image":
        size = _first(t, _SIZE)
        m = re.search(r"\b(1:1|4:5|3:4|9:16|16:9)\b", t)
        if m or size:
            out["size"] = m.group(1) if m else size
        quoted = [f["text"] for f in facts_of(text) if f["kind"] == "words"]
        if quoted:
            out["words"] = quoted[0]
        cols = [c for c in _COLOURS if re.search(r"(?<![a-z])" + c + r"(?![a-z])", t)]
        if cols:
            out["colours"] = ", ".join(dict.fromkeys(cols))
    elif section == "script":
        p = _first(t, _PLATFORM)
        if p:
            out["platform"] = p
        m = re.search(r"\b(\d{1,3})\s*(?:-\s*)?(?:seconds?|secs?|sec\b|s\b|second ka|sec ka)", t)
        mm = re.search(r"\b(\d{1,2})\s*(?:-\s*)?(?:minutes?|mins?|min\b)", t)
        if m and 5 <= int(m.group(1)) <= 180:
            out["length"] = f"{int(m.group(1))} seconds"
        elif mm and 1 <= int(mm.group(1)) <= 10:
            out["length"] = f"{int(mm.group(1)) * 60} seconds"
        out["language"] = lang_of(text)
    elif section == "web":
        a = _first(t, _ACTION)
        if a:
            out["action"] = a
    return out


# ---------------------------------------------------------------- 3. the one model call, and the check on it
FILL_SYSTEM = (
    "You fill a form from one short request written by an Indian small-business owner (English or Hinglish). "
    "Fill ONLY the keys listed. For each key give {\"value\": short plain English, \"from\": \"her\" | \"memory\" | \"guess\"}: "
    "\"her\" when her request itself says it, \"memory\" when it comes from the BUSINESS NOTES, \"guess\" when it is your "
    "sensible suggestion. Leave a key out when you have nothing useful. Never write a price, phone number, date, "
    "discount, address or any number that is not in her request. Never add praise words or instructions to an AI. "
    "Keep each value under 25 words.")


def _default_ask(system: str, prompt: str) -> dict[str, Any]:
    from ..net.ai import llm_json
    return llm_json(system, prompt, 700)


ASK: list[Callable[[str, str], dict[str, Any]]] = [_default_ask]       # tests replace ASK[0]


def _content_words(s: str) -> set[str]:
    return {w for w in re.findall(r"[a-zऀ-ॿ]{3,}", norm(s)) if w not in _STOP}


def supported(value: str, source_text: str) -> bool:
    """Does `value` really come from `source_text`? At least half of its content words must be there (stems of 4)."""
    vw = _content_words(value)
    if not vw:
        return False
    src = norm(source_text)
    hit = sum(1 for w in vw if w[:4] in src)
    return hit * 2 >= len(vw)


def _numbers_ok(value: str, allowed_text: str) -> bool:
    nums = re.findall(r"\d[\d.]*", norm(value))
    pool = norm(allowed_text)
    return all(n.rstrip(".") in pool for n in nums)


def model_slots(section: str, text: str, want: list[str], memory: str = "") -> dict[str, dict[str, str]]:
    """The model's proposals for `want`, each already checked and labelled by code. {} when the model is unavailable."""
    if not want:
        return {}
    lines = [f"- {k}: {A.slot(section, k)['label']}" + (f" (one of: {', '.join(A.slot(section, k)['options'])})"
                                                        if A.slot(section, k).get("options") and k != "size" else "")
             for k in want]
    prompt = (f"WHAT SHE IS MAKING: {A.SECTIONS[section]['makes']}\nHER REQUEST: {text[:MAX_TEXT]}\n"
              f"BUSINESS NOTES: {memory[:700] or '(none)'}\nKEYS TO FILL:\n" + "\n".join(lines))
    try:
        raw = ASK[0](FILL_SYSTEM, prompt) or {}
    except Exception as e:      # noqa: BLE001 - no model = a brief from code alone, never an error for her
        log.info("prompting fill model unavailable: %s", e)
        return {}
    out: dict[str, dict[str, str]] = {}
    for k in want:
        v = raw.get(k)
        if isinstance(v, str):
            v = {"value": v, "from": "guess"}
        if not isinstance(v, dict):
            continue
        value = _tidy(v.get("value"))
        if not value or any(m in value.lower() for m in MAGIC) or not _numbers_ok(value, text + " " + memory):
            continue
        said = str(v.get("from") or "guess").lower()
        if said == "her" and supported(value, text):
            src = "her_words"
        elif said in ("her", "memory") and memory and supported(value, memory):
            src = "her_memory"
        else:
            src = "hoola_guess"
        out[k] = {"value": value, "source": src}
    return out


# ---------------------------------------------------------------- the brief
def hash_of(brief: dict[str, Any]) -> str:
    core = {"section": brief.get("section"), "intent": brief.get("intent"),
            "slots": {k: v.get("value") for k, v in sorted((brief.get("slots") or {}).items())}}
    return hashlib.sha256(json.dumps(core, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:16]


def _finish(brief: dict[str, Any]) -> dict[str, Any]:
    sec = brief["section"]
    slots = brief["slots"]
    said = " ".join([brief["intent"], *[v["value"] for v in slots.values() if v["source"] in ("her_answer", "her_words", "recipe")]])
    brief["facts"] = facts_of(said)
    brief["missing"] = [k for k in A.required(sec) if k not in slots]
    qs = []
    for k in A.required(sec):
        cur = slots.get(k)
        if cur is None or cur["source"] == "hoola_guess":
            s = A.slot(sec, k)
            qs.append({"key": k, "q": s["q"], "options": s.get("options") or [], "option_labels": s.get("option_labels") or [],
                       "eg": s.get("eg", ""), "suggested": cur["value"] if cur else ""})
    brief["questions"] = qs[:MAX_Q]
    brief["hash"] = hash_of(brief)
    return brief


def understand(tenant: str, text: str, section: str = "", use_model: bool = True) -> dict[str, Any]:
    """Her rough line -> a brief. Never raises for a model outage; raises ValueError for an empty / unknown ask."""
    from . import context as C
    intent = str(text or "").strip()[:MAX_TEXT]
    if len(intent) < 3:
        raise ValueError("Write one line about what you want to make.")
    sec = section if section in A.SECTIONS else guess_section(intent)
    if not sec:
        raise ValueError("choose_section")
    known = C.known(tenant)
    slots: dict[str, dict[str, Any]] = {k: {"value": v, "source": "her_words"} for k, v in code_slots(sec, intent).items()}
    for k, v in C.fill(sec, known).items():
        slots.setdefault(k, {"value": v, "source": "her_memory"})
    if use_model:
        want = [k for k in A.keys(sec) if k not in slots]
        for k, v in model_slots(sec, intent, want, known.get("about", "")).items():
            slots.setdefault(k, v)
    brief = {"v": BRIEF_V, "anatomy": A.ANATOMY_V, "section": sec, "intent": intent, "lang": lang_of(intent),
             "slots": {k: slots[k] for k in A.keys(sec) if k in slots}, "recipe_id": ""}
    return _finish(brief)


def validate(raw: Any) -> dict[str, Any]:
    """A brief that came back from the page, rebuilt safely: only known slots and sources, cut to size, facts and
    questions recomputed. Her intent is never altered."""
    if not isinstance(raw, dict) or raw.get("section") not in A.SECTIONS:
        raise ValueError("That is not a prompt brief.")
    sec = raw["section"]
    intent = str(raw.get("intent") or "").strip()[:MAX_TEXT]
    slots: dict[str, dict[str, Any]] = {}
    for k in A.keys(sec):
        v = (raw.get("slots") or {}).get(k)
        if not isinstance(v, dict):
            continue
        value = _tidy(v.get("value"))
        if value:
            slots[k] = {"value": value, "source": v.get("source") if v.get("source") in SOURCES else "hoola_guess"}
    brief = {"v": BRIEF_V, "anatomy": A.ANATOMY_V, "section": sec, "intent": intent, "lang": lang_of(intent),
             "slots": slots, "recipe_id": _tidy(raw.get("recipe_id"), 60)}
    return _finish(brief)


def apply(raw: Any, set_: dict[str, Any] | None = None, drop: list[str] | None = None) -> dict[str, Any]:
    """Her edits: `set_` values become HER ANSWERS (the strongest source), `drop` removes a slot (a suggestion she
    does not want). Returns the rebuilt brief."""
    b = validate(raw)
    for k in drop or []:
        b["slots"].pop(str(k), None)
    for k, v in (set_ or {}).items():
        if k in A.keys(b["section"]):
            value = _tidy(v)
            if value:
                b["slots"][k] = {"value": value, "source": "her_answer"}
            else:
                b["slots"].pop(k, None)
    b["slots"] = {k: b["slots"][k] for k in A.keys(b["section"]) if k in b["slots"]}
    return _finish(b)


# ---------------------------------------------------------------- the Prompt Score (code, not opinion)
_CLASH = ((("dark", "black background", "night"), ("white background", "bright white", "airy", "light and bright")),
          (("minimal", "plain", "simple"), ("busy", "crowded", "lots of elements", "maximal")),
          (("traditional", "classic", "vintage"), ("futuristic", "cyber", "neon")))
_NEG = re.compile(r"\b(?:no|without|don't|do not|never|avoid)\s+([a-z]+(?:\s[a-z]+)?)", re.I)
NOTE = "This counts what is in your prompt. It cannot promise the result."


def score(brief: dict[str, Any]) -> dict[str, Any]:
    """0-100 from checks a program can run on the brief, with the reason for every point lost."""
    sec = brief["section"]
    slots = brief["slots"]
    reasons: list[dict[str, Any]] = []
    req = A.required(sec)
    got = 0.0
    for k in req:
        s = A.slot(sec, k)
        cur = slots.get(k)
        if cur is None:
            reasons.append({"ok": False, "key": k, "text": f"{s['label']}: missing. {s['q']}"})
        elif cur["source"] == "hoola_guess":
            got += 0.5
            reasons.append({"ok": False, "key": k, "text": f"{s['label']}: only Hoola's suggestion ({cur['value']}). Confirm or change it."})
        else:
            got += 1.0
    pts = 60.0 * got / len(req)
    extra = [k for k in A.keys(sec) if k not in req]
    have = sum(1 for k in extra if k in slots)
    pts += 15.0 * min(1.0, have / max(1, min(3, len(extra))))
    if have == 0 and extra:
        reasons.append({"ok": False, "key": extra[0], "text": "No detail beyond the basics yet. "
                        + " or ".join(A.slot(sec, k)["label"].lower() for k in extra[:2]) + " would sharpen it."})
    text = norm(" ".join([brief["intent"], *[v["value"] for v in slots.values()]]))
    clash = next(((a, b) for xs, ys in _CLASH for a in xs for b in ys if a in text and b in text), None)
    if clash:
        reasons.append({"ok": False, "text": f"Two instructions pull against each other: '{clash[0]}' and '{clash[1]}'. Keep one."})
    else:
        pts += 10.0
    limit_ok = True
    if sec == "image" and "words" in slots and len(slots["words"]["value"].split()) > 12:
        limit_ok = False
        reasons.append({"ok": False, "key": "words", "text": "More than 12 words on a picture rarely come out right. Shorten the line."})
    if sec == "script" and "length" in slots:
        m = re.search(r"\d+", slots["length"]["value"])
        if m and int(m.group(0)) > 90 and "reel" in norm(slots.get("platform", {}).get("value", "")):
            limit_ok = False
            reasons.append({"ok": False, "key": "length", "text": "A reel over 90 seconds loses most viewers. 15 to 45 seconds is usual."})
    pts += 5.0 if limit_ok else 0.0
    magic = [m for m in MAGIC if m in text]
    neg = _NEG.findall(brief["intent"]) if sec == "image" else []
    if magic:
        reasons.append({"ok": False, "text": f"Words like '{magic[0]}' do not help current engines. Describe what you want instead."})
    if neg:
        reasons.append({"ok": False, "text": f"Picture engines handle 'no {neg[0]}' badly. Say what should be there instead."})
    pts += 10.0 if not magic and not neg else 5.0 if not (magic and neg) else 0.0
    facts = brief.get("facts") or []
    if sec in ("web", "script") and not facts:
        reasons.append({"ok": True, "text": "No price, date or offer given. Hoola will leave marked blanks, never invent them."})
    return {"score": int(round(min(100.0, pts))), "reasons": reasons, "note": NOTE,
            "missing": brief.get("missing") or [], "facts": len(facts)}
