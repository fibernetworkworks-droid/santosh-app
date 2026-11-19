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
SOURCES = ("her_words", "her_memory", "her_answer", "her_default", "recipe", "hoola_guess")
SOURCE_LABEL = {"her_words": "from your words", "her_memory": "from your business", "her_answer": "your answer",
                "her_default": "your usual choice", "recipe": "from the recipe", "hoola_guess": "Hoola's suggestion"}
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
    "script": ("script", "screenplay", "dialogue", "voice over", "voiceover", "reel script", "ad film", "storyboard",
               "reel", "youtube short", "video ad", "tv ad"),
    "image": ("poster", "image", "photo", "picture", "banner", "logo", "thumbnail", "pamphlet", "flyer", "creative",
              "wallpaper", "tasveer", "illustration", "instagram post", "greeting"),
    "web": ("website", "web site", "site", "landing page", "webpage", "web page", "portal", "homepage", "online store",
            "web app"),
    "app": ("app", "android app", "mobile app", "phone app", "iphone app", "ios app", "play store", "application"),
    "video": ("video", "clip", "animation", "animated", "footage", "b-roll", "slow motion", "cinematic shot"),
    "music": ("song", "jingle", "music", "gaana", "gana", "lyrics", "beat", "instrumental", "bgm", "background music",
              "tune", "dhun"),
    "marketing": ("whatsapp message", "broadcast", "email", "e-mail", "mail", "sms", "caption", "campaign",
                  "newsletter", "facebook ad", "google ad", "ad copy", "message to customers", "promo message",
                  "offer message", "follow up message", "follow-up message"),
    "doc": ("proposal", "quotation", "quote", "letter", "report", "policy", "notice", "circular", "agreement",
            "contract", "invoice letter", "minutes", "sop", "offer letter", "application letter", "estimate"),
    "code": ("bug", "code", "coding", "error", "traceback", "exception", "stack trace", "pull request", "repo", "github",
             "function", "api endpoint", "unit test", "tests failing", "refactor", "python", "javascript", "flutter", "kotlin",
             "crash", "crashes", "500 error", "404"),
    "research": ("research", "find out", "compare", "comparison", "market size", "competitors", "which is best",
                 "best option", "pros and cons", "sources", "study", "survey", "trends", "statistics", "data on",
                 "how much does", "kitna kharcha"),
    "data": ("excel", "spreadsheet", "sheet", "csv", "xlsx", "chart", "graph", "pivot", "formula", "vlookup", "dashboard",
             "average", "total sales", "my sales", "my numbers", "analyse", "analyze", "analysis"),
    "aiapp": ("chatbot", "chat bot", "ai assistant", "ai app", "bot for my customers", "answer my customers",
              "reply to customers automatically", "auto reply", "virtual assistant", "ai receptionist", "ai agent for"),
}
# when two sections both match, the more specific one wins (a 'video script' is a script, a 'song video' a video)
_PRIORITY = ("aiapp", "code", "script", "music", "doc", "marketing", "data", "app", "image", "video", "research", "web")


def guess_section(text: str) -> str:
    """Which section her words belong to. '' when they name none (the page then asks; chat stays chat)."""
    t = " " + norm(text) + " "
    hits = {s: sum(1 for w in words if re.search(r"(?<![a-z])" + re.escape(w) + r"(?![a-z])", t))
            for s, words in _SECTION_WORDS.items()}
    if re.search(r"(?<![a-z])script(?![a-z])", t) and hits["script"]:
        return "script"
    if hits["web"] and re.search(r"(?<![a-z])(?:website|web site|web app|landing page|web ?page)(?![a-z])", t):
        hits["app"] = 0                          # 'a website with an app-like login' stays a website
    weak = ("reel", "youtube short")         # a 'reel' alone is a format word; with 'video of ...' it is a clip
    if hits["video"] and hits["script"] and not any(re.search(r"(?<![a-z])" + re.escape(w) + r"(?![a-z])", t)
                                                     for w in _SECTION_WORDS["script"] if w not in weak):
        hits["script"] = 0
    best = max(_PRIORITY, key=lambda k: (hits[k], -_PRIORITY.index(k)))
    if hits["video"] and hits["image"] and best == "image" and not re.search(r"(?<![a-z])(poster|logo|banner)(?![a-z])", t):
        best = "video"                           # 'a video of a product photo' is a video
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


_APP_PLATFORM = (("Android and iPhone", ("android and iphone", "android aur iphone", "both phones", "iphone and android",
                                         "android and ios", "ios and android")),
                 ("iPhone", ("iphone", "ios", "app store")), ("Android", ("android", "play store")))
_MONEY = (("UPI to my account", ("upi", "gpay", "phonepe", "paytm", "online payment", "pay online")),
          ("Cash on delivery", ("cash on delivery", "cod")), ("Credit (udhaar) book", ("udhaar", "udhar", "credit book", "khata")))
_JOB = (("Place an order", ("order", "delivery", "cart")), ("Book a slot", ("booking", "appointment", "book a", "slot")),
        ("Mark attendance", ("attendance", "hajiri")), ("Track a delivery", ("track", "tracking")),
        ("See and pay a bill", ("fee", "fees", "bill", "bills")))
_CAMERA = (("Slow push in", ("push in", "zoom in", "dolly in", "close in")), ("Orbit around", ("orbit", "360", "around it")),
           ("Slow pan left to right", ("pan", "panning")), ("Top-down", ("top down", "top-down", "overhead", "flat lay")),
           ("Still camera", ("static", "still camera", "locked off", "tripod")))
_VSIZE = (("9:16", ("reel", "story", "status", "shorts", "vertical")), ("16:9", ("youtube", "wide", "landscape", "banner")),
          ("1:1", ("square", "instagram post", "post")))
_GENRE = (("Devotional", ("bhajan", "aarti", "devotional", "bhakti")), ("Folk", ("folk", "lavani", "lok geet")),
          ("Lo-fi", ("lofi", "lo-fi", "lo fi", "chill")), ("EDM", ("edm", "dj", "remix", "electronic")),
          ("Indie acoustic", ("acoustic", "guitar", "indie")), ("Bollywood pop", ("bollywood", "filmi", "pop")))
_MOOD = (("Festive", ("festive", "festival", "diwali", "holi", "navratri", "wedding", "shaadi")),
         ("Romantic", ("romantic", "love", "pyaar")), ("Calm", ("calm", "soft", "peaceful", "soothing", "slow")),
         ("Energetic", ("energetic", "josh", "dance", "party", "upbeat")),
         ("Emotional", ("emotional", "sad", "touching")), ("Happy", ("happy", "cheerful", "khushi", "fun")))
_USE = (("Shop jingle", ("jingle",)), ("Reel background", ("reel", "background", "bgm")),
        ("Festival song", ("festival", "diwali", "holi", "navratri", "ganpati")), ("Ad music", ("ad ", "advert")),
        ("Event / wedding", ("wedding", "shaadi", "event", "sangeet")))
_VOCALS = (("Instrumental, no singing", ("instrumental", "no vocals", "no singing", "without vocals", "bina awaaz", "only music")),
           ("Duet", ("duet",)), ("Female voice", ("female", "ladki", "woman singer")), ("Male voice", ("male", "ladka", "man singer")),
           ("Children's chorus", ("children", "kids chorus", "bachche")))
_SONG_LANG = (("Marathi", ("marathi",)), ("Punjabi", ("punjabi",)), ("Hinglish", ("hinglish",)), ("Hindi", ("hindi",)),
              ("English", ("english",)))
_CHANNEL = (("WhatsApp message", ("whatsapp", "broadcast")), ("Email", ("email", "e-mail", "mail", "newsletter")),
            ("SMS", ("sms", "text message")), ("Instagram caption", ("caption", "instagram", "insta")),
            ("Facebook / Google ad", ("facebook ad", "google ad", "ad copy", "fb ad")))
_DOC_KIND = (("Quotation", ("quotation", "quote", "estimate")), ("Proposal", ("proposal",)), ("Report", ("report", "minutes")),
             ("Policy", ("policy", "sop", "rules")), ("Notice", ("notice", "circular")),
             ("Letter", ("letter", "application", "agreement", "contract")))
_FORMAT = (("PDF", ("pdf",)), ("Word document", ("word", "docx", ".doc")), ("Text in the chat", ("text only", "in the chat")))


_CODE_KIND = (("Fix a bug", ("bug", "error", "fix", "crash", "crashes", "broken", "not working", "fails", "failing",
                             "traceback", "exception", "kaam nahi")),
              ("Add tests", ("add tests", "write tests", "unit test", "test coverage")),
              ("Explain the code", ("explain", "how does", "samjhao")), ("Docs", ("readme", "docs", "documentation")),
              ("Change how something looks", ("design", "colour", "color", "css", "layout", "looks")),
              ("New feature", ("add", "feature", "build", "new page", "new screen", "implement")))
_SOURCES = (("Official / government sites first", ("official", "government", "govt", "sarkari", ".gov")),
            ("Research papers", ("paper", "papers", "academic", "study", "studies", "journal")),
            ("Company websites", ("company website", "brand website")))
_FORM = (("A comparison table", ("compare", "comparison", "table", "vs", "versus")), ("A PDF report", ("pdf",)),
         ("A report with sources", ("report", "detailed")), ("A short answer", ("short", "quick", "one line")))
_REGION = (("India", ("india", "indian", "bharat")), ("Maharashtra", ("maharashtra",)), ("Pune", ("pune",)),
           ("Mumbai", ("mumbai",)), ("Delhi", ("delhi",)), ("Akola", ("akola",)), ("Nagpur", ("nagpur",)))
_OUTPUT = (("A chart", ("chart", "graph", "plot")), ("A formula for my sheet", ("formula", "vlookup", "xlookup", "sumif")),
           ("An Excel file", ("excel file", "xlsx file", "download")), ("A table", ("table", "pivot", "list")),
           ("A short summary", ("summary", "summarise", "summarize")))
_AI_ROLE = (("Take bookings", ("booking", "bookings", "appointment", "appointments", "book")),
            ("Take orders", ("order", "orders")),
            ("Collect enquiries", ("enquiry", "inquiry", "lead", "leads")), ("Support after a sale", ("support", "complaint", "warranty")),
            ("Answer questions", ("answer", "questions", "faq", "reply")))
_AI_CHANNEL = (("My WhatsApp number", ("whatsapp",)), ("My website", ("website", "site")), ("A link I share", ("link",)))
_CHAT_FORM = (("A message I can send", ("reply to", "message to", "message for", "draft a reply", "jawab likho")),
              ("Steps", ("steps", "how do i", "how to", "kaise")), ("A table", ("table",)),
              ("A list of ideas", ("ideas", "names", "suggestions")), ("A short answer", ("short", "quick", "one line")))


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
    elif section == "app":
        for key, table in (("platform", _APP_PLATFORM), ("money", _MONEY), ("job", _JOB)):
            v = _first(t, table)
            if v:
                out[key] = v
    elif section == "video":
        for key, table in (("camera", _CAMERA), ("size", _VSIZE)):
            v = _first(t, table)
            if v:
                out[key] = v
        m = re.search(r"\b(\d{1,2})\s*(?:-\s*)?(?:seconds?|secs?|sec\b|s\b|second ka|sec ka)", t)
        if m and 2 <= int(m.group(1)) <= 60:
            out["length"] = f"{int(m.group(1))} seconds"
    elif section == "music":
        for key, table in (("use", _USE), ("genre", _GENRE), ("mood", _MOOD), ("vocals", _VOCALS), ("language", _SONG_LANG)):
            v = _first(t, table)
            if v:
                out[key] = v
        quoted = [f["text"] for f in facts_of(text) if f["kind"] == "words"]
        if quoted:
            out["lyrics"] = quoted[0]
        m = re.search(r"\b(\d{1,3})\s*(?:-\s*)?(?:seconds?|secs?|sec\b|s\b)", t)
        mm = re.search(r"\b(\d{1,2})\s*(?:-\s*)?(?:minutes?|mins?|min\b)", t)
        if m and 5 <= int(m.group(1)) <= 600:
            out["length"] = f"{int(m.group(1))} seconds"
        elif mm and 1 <= int(mm.group(1)) <= 10:
            out["length"] = f"{int(mm.group(1))} minute" + ("s" if int(mm.group(1)) > 1 else "")
    elif section == "marketing":
        v = _first(t, _CHANNEL)
        if v:
            out["channel"] = v
        a = _first(t, (("Reply on WhatsApp", ("reply", "whatsapp karo", "message us")), ("Call now", ("call",)),
                       ("Book online", ("book", "booking", "appointment")), ("Visit the shop", ("visit", "aaiye", "come to")),
                       ("Order online", ("order",))))
        if a:
            out["action"] = a
        out["language"] = lang_of(text)
    elif section == "doc":
        for key, table in (("kind", _DOC_KIND), ("format", _FORMAT)):
            v = _first(t, table)
            if v:
                out[key] = v
    elif section == "code":
        v = _first(t, _CODE_KIND)
        if v:
            out["kind"] = v
        paths = re.findall(r"(?<![\w/.-])((?:[\w.-]+/)*[\w-]+\.(?:py|js|ts|tsx|jsx|dart|kt|swift|java|go|rb|php|css|html|sql|yml|yaml|json))\b",
                           text or "")
        if paths:
            out["where"] = ", ".join(dict.fromkeys(paths))[:MAX_VALUE]
        cmd = re.search(r"(?:pytest[^\n,;]*|npm (?:run )?test[^\n,;]*|flutter test[^\n,;]*|go test[^\n,;]*|cargo test[^\n,;]*)",
                        text or "")
        if cmd:
            out["check"] = cmd.group(0).strip()[:120]
    elif section == "research":
        v = _first(t, _SOURCES)
        if v:
            out["sources"] = v
        v = _first(t, _FORM)
        if v:
            out["form"] = v
        y = re.search(r"\b(20[1-3]\d)\b", t)
        if y:
            out["asof"] = y.group(1)
        elif re.search(r"(?<![a-z])(latest|current|today|abhi ka|aaj ka)(?![a-z])", t):
            out["asof"] = "The latest"
        places = [v for v, words in _REGION if any(re.search(r"(?<![a-z])" + re.escape(w) + r"(?![a-z])", t) for w in words)]
        if places:
            out["region"] = ", ".join(places)
    elif section == "data":
        v = _first(t, _OUTPUT)
        if v:
            out["output"] = v
        f = re.findall(r"[\w.-]+\.(?:xlsx|xls|csv|ods)\b", text or "", re.I)
        if f:
            out["data"] = ", ".join(dict.fromkeys(f))
    elif section == "aiapp":
        for key, table in (("role", _AI_ROLE), ("channel", _AI_CHANNEL)):
            v = _first(t, table)
            if v:
                out[key] = v
    elif section == "chat":
        v = _first(t, _CHAT_FORM)
        if v:
            out["form"] = v
    main = {"code": "task", "research": "question", "data": "question", "chat": "goal"}.get(section)
    if main and len(_content_words(text)) >= 4:          # her own sentence IS the ask in these sections - said as hers
        out[main] = _tidy(text)
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


def _required(sec: str) -> list[str]:
    """The parts worth a question - minus any the owner stopped asking because the answer made no difference (P10)."""
    try:
        from . import khud as K
        off = K.asked_off(sec)
    except Exception:       # noqa: BLE001
        off = set()
    return [k for k in A.required(sec) if k not in off]


def _finish(brief: dict[str, Any]) -> dict[str, Any]:
    sec = brief["section"]
    slots = brief["slots"]
    said = " ".join([brief["intent"], *[v["value"] for v in slots.values() if v["source"] in ("her_answer", "her_words", "recipe")]])
    brief["facts"] = facts_of(said)
    brief["missing"] = [k for k in _required(sec) if k not in slots]
    qs = []
    for k in _required(sec):
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
    try:                                         # P10: her own usual choices (after her yes), then defaults that kept best
        from . import khud as K
        for k, v in K.her_usual(tenant, sec).items():
            slots.setdefault(k, {"value": v, "source": "her_default"})
        for k, v in K.default_for(sec).items():
            slots.setdefault(k, {"value": v, "source": "hoola_guess"})
    except Exception:       # noqa: BLE001 - learning never breaks a prompt
        log.debug("prompting: khud defaults not read", exc_info=True)
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


def _num(v: str) -> int:
    m = re.search(r"\d+", v or "")
    return int(m.group(0)) if m else 0


def _section_limits(sec: str, slots: dict[str, Any], brief: dict[str, Any], reasons: list[dict[str, Any]]) -> bool:
    """P5: each new section's engine limits and the facts it cannot do without. True = nothing against the brief."""
    v = lambda k: (slots.get(k) or {}).get("value", "")
    kinds = {f["kind"] for f in (brief.get("facts") or [])}
    ok = True
    if sec == "video":
        if _num(v("length")) > 10:
            ok = False
            reasons.append({"ok": False, "key": "length", "text": "One AI clip is usually 4 to 10 seconds. A longer video is "
                            "several shots - the Director in Create makes those."})
        if re.search(r"\b(?:and then|then|after that|phir|uske baad)\b", norm(v("action"))):
            ok = False
            reasons.append({"ok": False, "key": "action", "text": "One clip should show ONE thing happening. Split the rest "
                            "into more shots."})
    elif sec == "music":
        lyr = v("lyrics")
        if lyr and v("vocals").lower().startswith("instrumental"):
            ok = False
            reasons.append({"ok": False, "key": "vocals", "text": "There are lyrics but the voice is 'instrumental'. Keep one."})
        if len(lyr.split()) > 120:
            ok = False
            reasons.append({"ok": False, "key": "lyrics", "text": "More than 120 words of lyrics rarely fit a short song. "
                            "Keep a verse and a chorus."})
    elif sec == "marketing":
        if kinds & {"price", "percent"} and "date" not in kinds:
            ok = False
            reasons.append({"ok": False, "key": "offer", "text": "The offer has no end date. Say until when it runs."})
        if v("channel") == "SMS" and len(v("offer")) > 120:
            ok = False
            reasons.append({"ok": False, "key": "offer", "text": "An SMS is 160 characters. Shorten the offer line."})
        if v("channel") in ("WhatsApp message", "Email", "SMS"):
            reasons.append({"ok": True, "text": "Nothing is sent from here. A message to many people goes only on your tap, "
                            "with a way for them to stop."})
    elif sec == "doc":
        if v("kind") == "Quotation" and "price" not in kinds:
            ok = False
            reasons.append({"ok": False, "key": "content", "text": "A quotation needs prices. Give them, or the price table "
                            "stays a marked blank."})
        if v("kind") == "Report" and not (kinds & {"date"}) and not re.search(r"\b(?:month|week|year|quarter|20\d\d)\b",
                                                                              norm(brief["intent"] + " " + v("content"))):
            reasons.append({"ok": False, "key": "content", "text": "Say which period the report covers."})
    elif sec == "code":
        if v("task") and len(_content_words(v("task"))) < 3:
            ok = False
            reasons.append({"ok": False, "key": "task", "text": "Too short to act on. Say what you see, what you expected, "
                            "and paste the error if there is one."})
        if v("kind") == "Fix a bug" and not v("check"):
            reasons.append({"ok": False, "key": "check", "text": "Name a check (a test or the build) - a bug fix proved by a "
                            "failing test first is the one you can trust."})
    elif sec == "research":
        q = norm(v("question") + " " + brief["intent"])
        if re.search(r"(?<![a-z])(price|prices|rate|rates|cost|fees|tariff|bhav)(?![a-z])", q) and not v("asof"):
            ok = False
            reasons.append({"ok": False, "key": "asof", "text": "Prices change. Say how recent they must be."})
        if re.search(r"(?<![a-z])best(?![a-z])", q) and not v("decision"):
            reasons.append({"ok": False, "key": "decision", "text": "'Best' for what? Say what you will decide, so Hoola "
                            "knows what to compare."})
        reasons.append({"ok": True, "text": "Every figure in the answer must come from a page Hoola opened, with its link."})
    elif sec == "data":
        if v("output") == "A chart" and not re.search(r"(?<![a-z])(by|per|over|vs|against|each|har)(?![a-z])",
                                                      norm(v("question") + " " + brief["intent"])):
            reasons.append({"ok": False, "key": "question", "text": "Say what the chart compares - sales by month, by "
                            "product, by shop."})
        reasons.append({"ok": True, "text": "Numbers are worked out in Python on your data, never guessed."})
    elif sec == "aiapp":
        if v("knows") and not ({f["kind"] for f in (brief.get("facts") or [])} & {"price", "time", "phone", "date"}):
            ok = False
            reasons.append({"ok": False, "key": "knows", "text": "Give it real facts - timings, prices, policies. Without "
                            "them it can only say 'I don't know'."})
        if not v("handoff"):
            reasons.append({"ok": False, "key": "handoff", "text": "Say when it must hand over to you, for example a complaint."})
        reasons.append({"ok": True, "text": "It answers only from your facts and goes live only when you publish it."})
    elif sec == "app":
        if v("money") == "UPI to my account":
            reasons.append({"ok": True, "text": "Money reaches your own UPI or gateway; Hoola never holds or moves it."})
    return ok


def score(brief: dict[str, Any]) -> dict[str, Any]:
    """0-100 from checks a program can run on the brief, with the reason for every point lost."""
    sec = brief["section"]
    slots = brief["slots"]
    reasons: list[dict[str, Any]] = []
    req = _required(sec) or A.required(sec)
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
    limit_ok = _section_limits(sec, slots, brief, reasons) and limit_ok
    pts += 5.0 if limit_ok else 0.0
    magic = [m for m in MAGIC if m in text]
    neg = _NEG.findall(brief["intent"]) if sec in ("image", "video") else []
    if magic:
        reasons.append({"ok": False, "text": f"Words like '{magic[0]}' do not help current engines. Describe what you want instead."})
    if neg:
        reasons.append({"ok": False, "text": f"Picture engines handle 'no {neg[0]}' badly. Say what should be there instead."})
    pts += 10.0 if not magic and not neg else 5.0 if not (magic and neg) else 0.0
    facts = brief.get("facts") or []
    if sec in ("web", "script", "marketing", "doc", "aiapp") and not facts:
        reasons.append({"ok": True, "text": "No price, date or offer given. Hoola will leave marked blanks, never invent them."})
    return {"score": int(round(min(100.0, pts))), "reasons": reasons, "note": NOTE,
            "missing": brief.get("missing") or [], "facts": len(facts)}
