"""Edit Desk rules: pure functions (no database). Brief words, timecodes, scope, licences, money, GST / TDS notes.

Nothing here invents a fact: a brief keeps only what is written, a price only what she gave, a licence is 'ok' only with
her proof / reference."""
from __future__ import annotations

import hashlib
import json
import re
from datetime import date, timedelta
from typing import Any

# videoedit.PLATFORMS keys (the engine's shapes). Words -> key.
PLATFORM_WORDS = [
    ("status", ("status", "whatsapp status")),
    ("short", ("short", "shorts", "yt short", "youtube short")),
    ("reel", ("reel", "reels", "insta", "instagram", "story", "stories", "9:16", "vertical", "moj", "josh")),
    ("portrait", ("4:5", "feed post", "portrait")),
    ("square", ("square", "1:1")),
    ("youtube", ("youtube", "yt video", "16:9", "landscape", "horizontal", "long video", "full video", "film", "highlight")),
]
PLATFORM_LABEL = {"reel": "Instagram Reel (9:16)", "short": "YouTube Short (9:16)", "status": "WhatsApp Status (9:16)",
                  "youtube": "YouTube video (16:9)", "square": "Square post (1:1)", "portrait": "Feed post (4:5)",
                  "same": "Same shape as footage"}

KINDS = {
    "reel": {"label": "Reel / short", "platforms": ["reel"],
             "footage": ["Raw clips", "Brand logo (PNG)", "Music (licence ke saath)", "Caption / text lines", "Reference reel"]},
    "youtube": {"label": "YouTube video", "platforms": ["youtube", "short"],
                "footage": ["A-roll (camera)", "B-roll", "Audio (mic) file", "Thumbnail photo", "Intro / outro", "Music (licence ke saath)",
                            "Script / chapters"]},
    "wedding": {"label": "Wedding film / teaser", "platforms": ["youtube", "reel"],
                "footage": ["Haldi", "Mehendi", "Sangeet", "Pheras / main ceremony", "Reception", "Drone shots", "Couple shoot",
                            "Audio of vows / speeches", "Song choice (licence ke saath)"]},
    "corporate": {"label": "Corporate / brand film", "platforms": ["youtube", "square"],
                  "footage": ["Interview A-roll", "B-roll", "Logo + brand kit", "Script / approved claims", "Music (licence ke saath)",
                              "Lower-third names + titles"]},
    "ad": {"label": "Ad / product video", "platforms": ["reel", "portrait", "square"],
           "footage": ["Product shots", "Logo + brand kit", "Offer text (approved)", "Music (licence ke saath)", "Voice-over"]},
    "podcast": {"label": "Podcast / interview", "platforms": ["youtube", "short"],
                "footage": ["Camera 1", "Camera 2", "Audio (each mic)", "Guest names", "Chapter points"]},
    "event": {"label": "Event highlight", "platforms": ["youtube", "reel"],
              "footage": ["Stage shots", "Crowd / B-roll", "Speeches audio", "Logo", "Music (licence ke saath)"]},
    "music_video": {"label": "Music video", "platforms": ["youtube", "reel"],
                    "footage": ["Performance takes", "Story shots", "Final mixed song (owner's rights)", "Lyrics"]},
    "other": {"label": "Other", "platforms": ["reel"], "footage": ["Raw clips", "Music (licence ke saath)"]},
}
KIND_WORDS = [("wedding", ("wedding", "shaadi", "shadi", "vivah", "lagna", "reception", "haldi", "sangeet", "pre wedding", "prewedding")),
              ("podcast", ("podcast", "interview")),
              ("corporate", ("corporate", "company film", "brand film", "office", "testimonial")),
              ("ad", ("ad ", "advert", "product video", "promo", "offer video")),
              ("music_video", ("music video", "song video", "gaana shoot")),
              ("event", ("event", "conference", "seminar", "function highlight")),
              ("youtube", ("youtube video", "vlog", "yt video")),
              ("reel", ("reel", "short", "insta"))]

STATUS = {"brief": "Brief", "footage": "Footage coming in", "editing": "Editing", "review": "Client review",
          "revising": "Revisions in progress", "approved": "Client approved", "delivered": "Final delivered",
          "closed": "Closed (fully paid)", "cancelled": "Cancelled"}

LIC_KINDS = ("music", "stock_video", "stock_photo", "sfx", "font", "footage", "other")
LIC_TYPES = {"royalty_free": "Royalty-free (proof needed)", "subscription": "Subscription licence (like Artlist / Epidemic)",
             "sync": "Sync licence (from the label / publisher)", "cc": "Creative Commons (check the attribution)",
             "client_owned": "Client's own (the client's responsibility, in writing)", "own": "Own recording / made by you",
             "public_domain": "Public domain", "platform_only": "App library only (Instagram / YouTube in-app)",
             "unknown": "Unknown"}
# Sources that never cover a brand / client's commercial video by themselves.
RISKY_SOURCES = [
    (re.compile(r"\b(insta(gram)?|reels?)\b.*\b(library|music|audio|gaana|song)\b|\b(insta|instagram) (ka|se) (gaana|song|audio)", re.I),
     "Instagram's in-app music library is only for non-commercial use; a sync licence is needed for a brand / client video "
     "(Zee v Nykaa, Delhi HC, May 2026, was a case on exactly this)."),
    (re.compile(r"\b(youtube|yt)\b.*\b(download|se liya|se uthaya|rip)\b|\bmp3 download|\bpagalworld|\bsong download", re.I),
     "A song taken from YouTube / a download site is not licensed; there is a risk of a Content ID claim / takedown and a copyright notice."),
    (re.compile(r"\b(bollywood|film|filmi|t-series|zee music|saregama|sony music|tips)\b", re.I),
     "A film / label song needs a sync licence from the label or publisher (and IPRS / PPL / Novex for public performance)."),
]

OUT_OF_SCOPE = re.compile(r"\b(naya video|nayi video|ek aur (video|reel)|aur ek (video|reel)|extra (video|reel)|new video|another (video|reel)|"
                          r"reshoot|dobara shoot|phir se shoot|naya shoot|different song|alag concept|poora badal|completely change|"
                          r"from scratch|translate (in|into)|dub|dubbing|voice ?over (bhi|add)|naya version banao)\b", re.I)

URL = re.compile(r"https?://[^\s<>\"']+", re.I)
SECRET = re.compile(r"\b(otp|pin|cvv|password|upi pin|passcode)\b\s*(?:is|hai|:|=)?\s*\S+", re.I)


def digest(obj: Any) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()


def clean(text: Any, n: int = 600) -> str:
    """Client / her words: secrets never kept (OTP / PIN / password values, card- and Aadhaar-like numbers)."""
    t = str(text or "")
    t = SECRET.sub(lambda m: f"{m.group(1)} [hataya]", t)
    t = re.sub(r"\b(?:\d[ -]?){12,19}\b", "[hataya]", t)
    return t.strip()[:n]


def phone(text: Any) -> str:
    d = re.sub(r"\D", "", str(text or ""))
    if len(d) == 12 and d.startswith("91"):
        d = d[2:]
    if len(d) == 11 and d.startswith("0"):
        d = d[1:]
    return d if re.fullmatch(r"[6-9]\d{9}", d) else ""


def platform_of(text: Any) -> str:
    t = " " + str(text or "").lower().strip() + " "
    if t.strip() in PLATFORM_LABEL:
        return t.strip()
    for key, words in PLATFORM_WORDS:
        if any(w in t for w in words):
            return key
    return ""


def platforms_in(text: Any) -> list[str]:
    t = " " + URL.sub(" ", str(text or "")).lower() + " "
    out = []
    for key, words in PLATFORM_WORDS:
        for w in sorted(words, key=len, reverse=True):
            rx = r"(?<![a-z])" + re.escape(w) + r"(?![a-z])"
            if re.search(rx, t):
                if key not in out:
                    out.append(key)
                t = re.sub(rx, " ", t)          # 'youtube short' is a Short, not also a YouTube video
    return out


def kind_of(text: Any) -> str:
    t = " " + str(text or "").lower() + " "
    if t.strip() in KINDS:
        return t.strip()
    for k, words in KIND_WORDS:
        if any(w in t for w in words):
            return k
    return ""


_MONTHS = {m: i for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}


def date_of(text: Any, today: date) -> date | None:
    t = str(text or "").lower().strip()
    if not t:
        return None
    if re.search(r"\b(aaj|today)\b", t):
        return today
    if re.search(r"\b(kal|tomorrow)\b", t):
        return today + timedelta(days=1)
    if re.search(r"\b(parso|day after)\b", t):
        return today + timedelta(days=2)
    m = re.search(r"\b(\d+)\s*(din|days?)\s*(mein|me|main|in)?\b", t)
    if m and int(m.group(1)) <= 120:
        return today + timedelta(days=int(m.group(1)))
    m = re.search(r"\b(20\d\d)-(\d{1,2})-(\d{1,2})\b", t)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            return None
    m = re.search(r"\b(\d{1,2})[/.\-](\d{1,2})(?:[/.\-](\d{2,4}))?\b", t)
    if m:
        d, mo = int(m.group(1)), int(m.group(2))
        y = int(m.group(3)) if m.group(3) else today.year
        y = y + 2000 if y < 100 else y
        try:
            out = date(y, mo, d)
        except ValueError:
            return None
        return out if m.group(3) or out >= today else date(y + 1, mo, d)
    m = re.search(r"\b(\d{1,2})\s*(?:st|nd|rd|th)?\s*([a-z]{3})[a-z]*\b", t)
    if m and m.group(2) in _MONTHS:
        try:
            out = date(today.year, _MONTHS[m.group(2)], int(m.group(1)))
        except ValueError:
            return None
        return out if out >= today else date(today.year + 1, out.month, out.day)
    return None


def seconds_of(text: Any) -> int | None:
    """'30 sec', '1 min', '1.5 minute', '90 second', '2 min 30 sec' -> seconds."""
    t = str(text or "").lower()
    m = re.search(r"(\d+)\s*(?:min|minute|minat)\w*\s*(\d+)\s*(?:s|sec|second)", t)
    if m:
        return int(m.group(1)) * 60 + int(m.group(2))
    m = re.search(r"(\d+(?:\.\d+)?)\s*(?:min|minute|minat)\b", t)
    if m:
        return int(round(float(m.group(1)) * 60))
    m = re.search(r"(\d+)\s*(?:s|sec|secs|second|seconds|saikand)\b", t)
    if m:
        return int(m.group(1))
    return None


def parse_brief(text: Any, today: date) -> dict[str, Any]:
    """Only what is written in the brief (client's words = data)."""
    t = clean(text, 4000)
    low = t.lower()
    out: dict[str, Any] = {"text": t}
    pf = platforms_in(t)
    if pf:
        out["platforms"] = pf
    k = kind_of(t)
    if k:
        out["kind"] = k
    m = re.search(r"(\d+(?:\.\d+)?\s*(?:min|minute|minat)\w*(?:\s*\d+\s*(?:s|sec|second)\w*)?|\d+\s*(?:s|sec|secs|second|seconds|saikand)\b)", low)
    if m:
        out["length_s"] = seconds_of(m.group(1))
    dm = re.search(r"\b(?:by|tak|before|deadline|delivery|chahiye)\b[^.\n]{0,25}", low)
    d = date_of(dm.group(0), today) if dm else None
    if d is None:
        d = date_of(low, today) if re.search(r"\b(kal|tomorrow|parso|\d+\s*din|\d{1,2}[/.\-]\d{1,2})", low) else None
    if d:
        out["due"] = d.isoformat()
    if re.search(r"\b(subtitle|caption|captions|text on screen|likha hua)\b", low):
        out["captions"] = not re.search(r"\b(no|bina|without|nahi)\s+(subtitle|caption)", low)
    for lang, words in (("hindi", ("hindi",)), ("marathi", ("marathi",)), ("english", ("english",)), ("hinglish", ("hinglish",))):
        if any(w in low for w in words):
            out.setdefault("languages", []).append(lang)
    refs = URL.findall(t)
    if refs:
        out["references"] = refs[:6]
    if re.search(r"\b(music|gaana|song|bgm|track|audio)\b", low):
        out["music_said"] = True
    if re.search(r"\b(logo|brand kit|brand colou?r)\b", low):
        out["logo_said"] = True
    if re.search(r"\b(urgent|jaldi|asap|rush|aaj hi)\b", low):
        out["rush"] = True
    return out


def brief_questions(facts: dict, has_music_licence: bool, has_footage: bool) -> list[str]:
    q = []
    if not facts.get("platforms"):
        q.append("Which platform is it for? (Insta reel / YouTube / Short / Status / feed post)")
    if not facts.get("length_s"):
        q.append("How long should the video be? (seconds / minutes)")
    if not facts.get("due"):
        q.append("By when is the final needed (date)?")
    if "captions" not in facts:
        q.append("Are captions / subtitles needed? In which language?")
    if facts.get("music_said") and not has_music_licence:
        q.append("Where is the music from, and whose name is the licence in? (A song taken from Insta / YouTube will not work in a brand video)")
    if not facts.get("references"):
        q.append("Is there a reference video link for the style you want?")
    if not has_footage:
        q.append("How will the footage be sent? (Drive link / files in chat)")
    return q


TC = re.compile(r"(?<![\d:])(?:(\d{1,2}):)?(\d{1,2}):(\d{2})(?:[.,]\d+)?(?![\d:])|(?<![\d.])(\d{1,2})\.(\d{2})(?=\s*(?:pe|par|par|pr|-|–|:|\s+mein|\s+me))|"
                r"(?<![\w.])(\d{1,4})\s*(?:s|sec|second|seconds|saikand)\b(?:\s*(?:pe|par|pr|mein|me|at))?", re.I)


def timecode_at(text: str) -> tuple[float | None, str]:
    """First timecode in a line -> (seconds, the line with the timecode removed)."""
    m = TC.search(text or "")
    if not m:
        return None, (text or "").strip()
    if m.group(2) is not None:
        h = int(m.group(1) or 0)
        s = h * 3600 + int(m.group(2)) * 60 + int(m.group(3)) if m.group(1) else int(m.group(2)) * 60 + int(m.group(3))
    elif m.group(4) is not None:
        s = int(m.group(4)) * 60 + int(m.group(5))
    else:
        s = int(m.group(6))
    rest = (text[:m.start()] + text[m.end():]).strip(" -–:,.\t")
    rest = re.sub(r"^(pe|par|pr|at|mein|me)\b\s*", "", rest, flags=re.I).strip(" -–:,.")
    return float(s), rest


def fmt_tc(sec: float | None) -> str:
    if sec is None:
        return ""
    s = int(round(sec))
    return f"{s // 3600}:{s % 3600 // 60:02d}:{s % 60:02d}" if s >= 3600 else f"{s // 60}:{s % 60:02d}"


def parse_comments(text: Any) -> list[dict[str, Any]]:
    """A client's pasted notes -> one comment per line / bullet (their words = data). Timecode when written."""
    t = clean(text, 6000)
    parts: list[str] = []
    for line in re.split(r"[\n\r]+|(?<=[.!?])\s+(?=\d{1,2}[:.]\d{2})", t):
        line = re.sub(r"^\s*(?:[-*•]|\d{1,2}[).]\s)\s*", "", line).strip()
        if len(line) >= 2:
            parts.append(line)
    out = []
    for p in parts[:60]:
        at, rest = timecode_at(p)
        rest = rest or p
        out.append({"at_s": at, "text": rest[:500], "scope": "extra" if OUT_OF_SCOPE.search(rest) else "fix"})
    return out


def licence_problems(lic: dict, commercial: bool, today: date) -> tuple[list[str], list[str]]:
    """(blockers, warnings) for one licence record. Never says 'cleared' without her proof / reference."""
    block, warn = [], []
    typ = lic.get("licence_type") or "unknown"
    src = f"{lic.get('source', '')} {lic.get('title', '')} {lic.get('notes', '')}"
    if typ in ("unknown", ""):
        block.append("The licence type is not known: no final delivery without proof.")
    if typ == "platform_only" and commercial:
        block.append("A song from an in-app library (Instagram / YouTube) gives no licence for a brand / client video.")
    for rx, why in RISKY_SOURCES:
        if rx.search(src) and typ not in ("sync", "client_owned", "own"):
            (block if commercial else warn).append(why)
            break
    if typ in ("royalty_free", "subscription", "sync", "cc") and not (lic.get("proof_file_id") or lic.get("licence_ref")):
        block.append("The licence proof (licence PDF / download certificate / order number) is not attached.")
    if typ == "subscription":
        warn.append("Subscription licence: download / register for this project within its terms (on many sites "
                    "the video must be cleared under the project's name).")
    if typ == "cc":
        warn.append("Creative Commons: check the licence (BY / NC / ND); NC is not allowed in a commercial video; credit must be given.")
    if typ == "client_owned":
        warn.append("Given by the client: get it in writing that the client holds the rights (their responsibility).")
    if lic.get("commercial") is False and commercial:
        block.append("This licence does not say commercial use is allowed.")
    exp = lic.get("expires")
    if exp:
        try:
            ed = date.fromisoformat(str(exp)[:10])
            if ed < today:
                block.append(f"The licence expired on {ed.isoformat()}.")
            elif ed <= today + timedelta(days=15):
                warn.append(f"The licence expires on {ed.isoformat()}.")
        except ValueError:
            pass
    return block, warn


# ---------------------------------------------------------------- money
def gst_split(state_code_her: str, state_code_client: str, gst_pct: float, base: float) -> dict[str, Any]:
    """CGST + SGST inside her state, IGST outside (place of supply = client's location for B2B services, IGST Act s.12(2))."""
    tax = round(base * gst_pct / 100, 2)
    if not state_code_client or state_code_client == state_code_her:
        half = round(tax / 2, 2)
        return {"pct": gst_pct, "cgst": half, "sgst": round(tax - half, 2), "igst": 0.0, "tax": tax, "kind": "intra"}
    return {"pct": gst_pct, "cgst": 0.0, "sgst": 0.0, "igst": tax, "tax": tax, "kind": "inter"}


TDS_NOTE = ("TDS: a business client may deduct it under Income-tax Act 2025 s.393(1): professional fees 10% (above Rs 50,000 a year) "
            "or contract work 1% / 2%; which category applies is decided by the client. Record what was deducted in 'payment received'; "
            "match it with Form 26AS / AIS. An individual client (personal use) does not deduct TDS.")
GST_NOTE = ("GST: video editing / post-production SAC 998386, 18% (even after GST 2.0). Registration is required above Rs 20 lakh a year "
            "turnover (Rs 10 lakh in special category states); a client abroad = export of services, zero-rated with an LUT. "
            "Have your CA confirm this.")
COPYRIGHT_NOTE = ("Copyright: the first owner of a commissioned video (cinematograph film) is the paying client unless "
                  "it says otherwise in writing (Copyright Act 1957 s.17(b)); state the rights to raw footage / project files / music "
                  "clearly in the terms of the quote.")


def money(v: Any) -> float | None:
    if v is None or v == "" or isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).lower().replace(",", "").strip()
    mult = 1.0
    if re.search(r"\d\s*(k|hazaar|hazar|thousand)\b", s):
        mult = 1000.0
    elif re.search(r"\d\s*(lakh|lac|l)\b", s):
        mult = 100000.0
    m = re.search(r"-?\d+(?:\.\d+)?", s)
    return round(float(m.group(0)) * mult, 2) if m else None
