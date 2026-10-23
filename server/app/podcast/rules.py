"""Podcast Sahayak rules: pure functions (time codes, transcripts, chapters, disclosure, loudness, artwork, feed XML, stats).

Nothing here invents a fact: chapters snap to real transcript times, quotes must be found in the transcript, sponsor reads must
carry an allowed ASCI label at the start AND the end, loudness verdicts follow Apple's published target."""
from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import uuid
from datetime import datetime, timezone
from email.utils import format_datetime
from typing import Any
from xml.sax.saxutils import escape

# ---------------------------------------------------------------- published numbers (sources in WIRING.md)
LUFS_TARGET = -16.0          # Apple Podcasts: "around -16 dB LKFS", +/- 1 dB, ITU-R BS.1770
LUFS_TOL = 1.0
TRUE_PEAK_MAX = -1.0         # Apple: true peak should not exceed -1 dBFS
ART_MIN, ART_MAX = 1400, 3000    # Apple: 1400-3000 px square, JPG / PNG, RGB
SPOTIFY_CHAPTER_GAP = 30     # Spotify for Creators: first at 00:00, >= 3 chapters, >= 30 s apart, plain text
YOUTUBE_CHAPTER_GAP = 10     # YouTube: first at 00:00, >= 3 timestamps ascending, each >= 10 s
GUID_NS = uuid.UUID("ead4c236-bf58-58c6-a2c6-a6b28d128cb6")   # podcast:guid namespace (Podcast Index)
ASCI_LABELS = ("#advertisement", "#ad", "#sponsored", "#collaboration", "#partnership", "#employee", "#free gift")
# spoken forms of the same labels (audio: said at the start and the end of the promotion)
SPOKEN_LABELS = ("advertisement", "sponsored", "sponsor", "paid partnership", "partnership", "collaboration", "ad hai",
                 "yeh ek ad", "ye ek ad", "vigyapan", "vigyaapan", "prayojit", "प्रायोजित", "विज्ञापन", "जाहिरात", "प्रायोजक")
APPLE_CATEGORIES = ("Arts", "Business", "Comedy", "Education", "Fiction", "Government", "History", "Health & Fitness",
                    "Kids & Family", "Leisure", "Music", "News", "Religion & Spirituality", "Science", "Society & Culture",
                    "Sports", "Technology", "True Crime", "TV & Film")
LICENCE_OK = ("own", "commissioned", "cc0", "cc_by", "royalty_free", "paid")
LICENCE_LABEL = {"own": "Apna banaya", "commissioned": "Bana ke liya (likhit)", "cc0": "CC0 (free)", "cc_by": "CC BY (naam dena zaroori)",
                 "royalty_free": "Royalty-free licence", "paid": "Kharida hua licence", "unknown": "Pata nahi (licence nahi)"}
PLATFORM_WORDS = {"spotify": ("spotify",), "apple": ("apple", "itunes"), "youtube": ("youtube", "yt"), "jiosaavn": ("jiosaavn", "saavn"),
                  "amazon": ("amazon", "audible"), "gaana": ("gaana",), "hoola": ("hoola",), "other": ()}
CONSENT_WORDS = ("consent", "agree", "i agree", "permission", "ijazat", "izazat", "anumati", "manzoor", "haan record", "record kar sakte",
                 "publish kar sakte", "sehmat", "सहमत", "अनुमति", "परवानगी", "मंजूर")


class RuleError(ValueError):
    pass


def clean(t: Any, n: int = 2000) -> str:
    s = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", " ", str(t or "")).strip()
    return s[:n]


def digest(obj: Any) -> str:
    return hashlib.sha256(json.dumps(obj, ensure_ascii=False, sort_keys=True, default=str).encode()).hexdigest()


def phone(v: Any) -> str:
    d = re.sub(r"\D", "", str(v or ""))
    if len(d) == 12 and d.startswith("91"):
        d = d[2:]
    if len(d) == 11 and d.startswith("0"):
        d = d[1:]
    return d if len(d) == 10 and d[0] in "6789" else ""


def scrub(text: str) -> str:
    """Card-like / Aadhaar-like numbers and OTP / PIN values never get stored from pasted text."""
    t = re.sub(r"(?i)\b(otp|pin|cvv|password|passcode)\s*[:\-]?\s*\S+", r"\1 [hataya]", str(text or ""))
    return re.sub(r"\b(?:\d[ -]?){12,19}\b", "[number hataya]", t)


# ---------------------------------------------------------------- time codes
def ts(v: Any) -> float | None:
    """'1:02:03' / '02:03' / '00:01:02.500' / '62' / 62.5 -> seconds."""
    if v is None or v == "":
        return None
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return float(v) if v >= 0 else None
    s = str(v).strip().strip("()[]").replace(",", ".")
    if re.fullmatch(r"\d+(\.\d+)?", s):
        return float(s)
    m = re.fullmatch(r"(?:(\d+):)?(\d{1,2}):(\d{1,2}(?:\.\d+)?)", s)
    if not m:
        return None
    h, mi, se = int(m.group(1) or 0), int(m.group(2)), float(m.group(3))
    if mi >= 60 or se >= 60:
        return None
    return h * 3600 + mi * 60 + se


def hms(sec: float, long: bool | None = None) -> str:
    """Seconds -> '05:07' or '1:05:07' (Spotify / YouTube description chapters)."""
    s = int(max(0, round(sec or 0)))
    h, m, x = s // 3600, (s % 3600) // 60, s % 60
    if long or (long is None and h):
        return f"{h:02d}:{m:02d}:{x:02d}"
    return f"{m:02d}:{x:02d}"


def _vtt_t(sec: float, sep: str = ".") -> str:
    ms = int(round(max(0.0, sec) * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d}{sep}{ms:03d}"


# ---------------------------------------------------------------- transcripts
def parse_captions(text: str) -> list[dict]:
    """Her own SRT / WebVTT file (from Riverside, Descript, Audacity ...) -> segments. Speaker 'Name:' prefixes kept."""
    out: list[dict] = []
    blocks = re.split(r"\n\s*\n", str(text or "").replace("\r\n", "\n").replace("\r", "\n"))
    for b in blocks:
        lines = [x for x in b.strip().split("\n") if x.strip()]
        if not lines:
            continue
        i = next((k for k, x in enumerate(lines) if "-->" in x), -1)
        if i < 0:
            continue
        a, _, z = lines[i].partition("-->")
        st, en = ts(a.strip().split(" ")[0]), ts(z.strip().split(" ")[0])
        body = " ".join(re.sub(r"<[^>]+>", "", x).strip() for x in lines[i + 1:]).strip()
        if st is None or en is None or not body:
            continue
        spk = ""
        m = re.match(r"^([A-Za-zऀ-ॿ][\wऀ-ॿ .]{0,30}):\s+(.*)$", body)
        if m:
            spk, body = m.group(1).strip(), m.group(2).strip()
        out.append({"start": round(st, 2), "end": round(max(en, st), 2), "text": clean(body, 1200), "speaker": spk})
    out.sort(key=lambda s: s["start"])
    return out


def segments_from_words(words: list[dict], max_words: int = 18, gap: float = 0.9) -> list[dict]:
    """faster-whisper word timestamps -> sentence-ish segments (split at pauses / sentence ends / length)."""
    out, cur = [], []
    for w in words:
        if cur and (len(cur) >= max_words or float(w["start"]) - float(cur[-1]["end"]) > gap
                    or re.search(r"[.?!।]$", str(cur[-1]["word"]))):
            out.append({"start": round(float(cur[0]["start"]), 2), "end": round(float(cur[-1]["end"]), 2),
                        "text": " ".join(x["word"] for x in cur).strip(), "speaker": ""})
            cur = []
        cur.append(w)
    if cur:
        out.append({"start": round(float(cur[0]["start"]), 2), "end": round(float(cur[-1]["end"]), 2),
                    "text": " ".join(x["word"] for x in cur).strip(), "speaker": ""})
    return [s for s in out if s["text"]]


def clean_segments(segs: Any, duration: float | None = None) -> list[dict]:
    out = []
    for s in segs if isinstance(segs, list) else []:
        if not isinstance(s, dict):
            continue
        st, en = ts(s.get("start")), ts(s.get("end"))
        txt = clean(s.get("text") or s.get("body"), 1200)
        if st is None or not txt:
            continue
        en = en if en is not None and en >= st else st
        if duration and st > duration + 1:
            continue
        out.append({"start": round(st, 2), "end": round(min(en, duration) if duration else en, 2), "text": txt,
                    "speaker": clean(s.get("speaker"), 40)})
    out.sort(key=lambda s: s["start"])
    return out


def to_vtt(segs: list[dict]) -> str:
    lines = ["WEBVTT", ""]
    for s in segs:
        lines.append(f"{_vtt_t(s['start'])} --> {_vtt_t(max(s['end'], s['start'] + 0.5))}")
        lines.append((f"<v {s['speaker']}>" if s.get("speaker") else "") + s["text"])
        lines.append("")
    return "\n".join(lines)


def to_srt(segs: list[dict]) -> str:
    lines = []
    for i, s in enumerate(segs, 1):
        lines += [str(i), f"{_vtt_t(s['start'], ',')} --> {_vtt_t(max(s['end'], s['start'] + 0.5), ',')}",
                  (f"{s['speaker']}: " if s.get("speaker") else "") + s["text"], ""]
    return "\n".join(lines)


def to_json(segs: list[dict]) -> str:
    """Podcast Index JSON transcript format (version 1.0.0)."""
    return json.dumps({"version": "1.0.0", "segments": [
        {**({"speaker": s["speaker"]} if s.get("speaker") else {}), "startTime": s["start"], "endTime": s["end"], "body": s["text"]}
        for s in segs]}, ensure_ascii=False)


def to_text(segs: list[dict]) -> str:
    return "\n".join((f"[{hms(s['start'])}] " + (f"{s['speaker']}: " if s.get("speaker") else "") + s["text"]) for s in segs)


def norm(t: str) -> str:
    t = str(t or "").lower()
    t = re.sub(r"[‘’“”\"'`]", "", t)
    t = re.sub(r"[^\wऀ-ॿ]+", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def find_quote(quote: str, segs: list[dict]) -> dict | None:
    """A quote is kept only if its words are really in the transcript (window of up to 4 segments). Returns its real time."""
    q = norm(quote)
    if len(q) < 8:
        return None
    for i in range(len(segs)):
        win = " ".join(norm(s["text"]) for s in segs[i:i + 4])
        if q in win:
            # earliest segment of the window that still contains the start of the quote
            first = " ".join(q.split(" ")[:3])
            best = i
            for k in range(i, min(i + 4, len(segs))):
                if first in " ".join(norm(s["text"]) for s in segs[k:i + 4]):
                    best = k
            return {"start": segs[best]["start"], "text": clean(quote, 400), "speaker": segs[best].get("speaker", "")}
    return None


def numbers_of(t: str) -> set[str]:
    return {re.sub(r"[,\s]", "", n) for n in re.findall(r"\d[\d,]*(?:\.\d+)?", str(t or ""))}


def unbacked_numbers(text: str, sources: list[str]) -> list[str]:
    pool: set[str] = set()
    for s in sources:
        pool |= numbers_of(s)
    return sorted(n for n in numbers_of(text) if n not in pool and len(n) > 0)


# ---------------------------------------------------------------- chapters
def fix_chapters(raw: Any, segs: list[dict], duration: float, gap: int = SPOTIFY_CHAPTER_GAP) -> list[dict]:
    """Chapters from the model / her words -> valid for Spotify AND YouTube: snapped to a real segment start, first at 00:00,
    sorted, >= `gap` s apart, plain-text titles <= 60 chars, none past the end."""
    starts = [s["start"] for s in segs] or [0.0]
    items = []
    for c in raw if isinstance(raw, list) else []:
        if not isinstance(c, dict):
            continue
        t = ts(c.get("start") if c.get("start") is not None else c.get("t"))
        title = re.sub(r"<[^>]+>", "", clean(c.get("title"), 80))
        title = re.sub(r"[\U0001F300-\U0001FAFF☀-➿]", "", title).strip(" -:·")[:60]
        if t is None or not title or (duration and t >= duration):
            continue
        t = min(starts, key=lambda x: abs(x - t))
        items.append({"start": round(t, 2), "title": title})
    items.sort(key=lambda c: c["start"])
    out: list[dict] = []
    for c in items:
        if not out:
            out.append({"start": 0.0, "title": c["title"]})
        elif c["start"] - out[-1]["start"] >= gap and (not duration or duration - c["start"] >= gap):
            out.append(c)
    return out


def chapter_problems(ch: list[dict], duration: float) -> list[str]:
    p = []
    if len(ch) < 3:
        p.append("Kam se kam 3 chapter chahiye (Spotify / YouTube).")
    if ch and ch[0]["start"] != 0:
        p.append("Pehla chapter 00:00 par hona chahiye.")
    for a, b in zip(ch, ch[1:]):
        if b["start"] - a["start"] < SPOTIFY_CHAPTER_GAP:
            p.append(f"'{a['title']}' 30 sec se chhota hai (Spotify).")
    if ch and duration and duration - ch[-1]["start"] < YOUTUBE_CHAPTER_GAP:
        p.append("Aakhri chapter 10 sec se chhota (YouTube).")
    return p


def chapters_json(ch: list[dict], title: str = "") -> str:
    """Podcast Index JSON chapters (application/json+chapters), version 1.2.0."""
    return json.dumps({"version": "1.2.0", **({"title": title} if title else {}),
                       "chapters": [{"startTime": c["start"], "title": c["title"]} for c in ch]}, ensure_ascii=False)


def chapters_text(ch: list[dict], duration: float = 0) -> str:
    long = duration >= 3600 or any(c["start"] >= 3600 for c in ch)
    return "\n".join(f"{hms(c['start'], long)} {c['title']}" for c in ch)


def even_chapters(segs: list[dict], duration: float, every: float = 600) -> list[dict]:
    """No model: chapters every ~10 min at a real segment, titled with that segment's own first words (labelled as such)."""
    if not segs or duration < 3 * SPOTIFY_CHAPTER_GAP:
        return []
    out = []
    t = 0.0
    while t < duration - SPOTIFY_CHAPTER_GAP:
        s = min(segs, key=lambda x: abs(x["start"] - t))
        words = s["text"].split()
        out.append({"start": s["start"], "title": " ".join(words[:6]) + ("…" if len(words) > 6 else "")})
        t += every
    return fix_chapters(out, segs, duration)


# ---------------------------------------------------------------- disclosure (ASCI / CCPA)
def _has_label(t: str) -> bool:
    low = " " + str(t or "").lower() + " "
    if any(lb in low for lb in ASCI_LABELS):
        return True
    return any(re.search(r"(?<![a-z])" + re.escape(w) + r"(?![a-z])", low) for w in SPOKEN_LABELS)


def read_disclosure(script: str) -> dict:
    """ASCI: in audio / podcasts the disclosure must be at the START and at the END of the promotion."""
    s = str(script or "").strip()
    sents = [x.strip() for x in re.split(r"(?<=[.!?।])\s+|\n+", s) if x.strip()]
    if not sents:
        return {"ok": False, "start": False, "end": False, "why": "Script khaali hai."}
    start = _has_label(" ".join(sents[:1]) if len(sents) > 1 else s[:120])
    end = _has_label(" ".join(sents[-1:]) if len(sents) > 1 else s[-120:])
    why = [] if start else ["shuru mein '#Ad / sponsored' nahi"]
    if not end:
        why.append("aakhir mein '#Ad / sponsored' nahi")
    return {"ok": start and end, "start": start, "end": end, "why": "; ".join(why)}


def add_disclosure(script: str, brand: str, lang: str = "hinglish") -> str:
    """Wraps her script with an opening and closing disclosure (her words stay as they are)."""
    s = str(script or "").strip()
    lead = {"hi": f"यह एपिसोड {brand} द्वारा प्रायोजित है (#Ad).", "mr": f"हा भाग {brand} प्रायोजित आहे (#Ad).",
            "en": f"This part is sponsored by {brand} (#Ad)."}.get(lang, f"Yeh hissa {brand} ki taraf se sponsored hai (#Ad).")
    tail = {"hi": "यह एक विज्ञापन था (#Ad).", "mr": "ही जाहिरात होती (#Ad).", "en": "That was a paid advertisement (#Ad)."
            }.get(lang, "Yeh ek paid advertisement tha (#Ad).")
    d = read_disclosure(s)
    if not d["start"]:
        s = lead + " " + s
    if not d["end"]:
        s = s + " " + tail
    return s.strip()


def transcript_disclosure(segs: list[dict], brand: str, window: float = 60.0) -> dict:
    """In the real audio: around the brand's mentions, was a disclosure word said near the first and the last mention?"""
    b = norm(brand)
    if not b:
        return {"found": False}
    hits = [s for s in segs if b in norm(s["text"])]
    if not hits:
        return {"found": False}
    first, last, last_seg = hits[0]["start"], hits[-1]["end"], hits[-1]["start"]
    near_start = any(_has_label(s["text"]) for s in segs if first - window <= s["start"] <= first)
    near_end = any(_has_label(s["text"]) for s in segs if last_seg <= s["start"] <= last + window)
    return {"found": True, "first": first, "last": last, "start": near_start, "end": near_end, "ok": near_start and near_end}


PROMISE_WORDS = ("guarantee", "guaranteed", "100%", "sure shot", "pakka fayda", "risk free", "risk-free", "no risk", "double",
                 "cure", "ilaaj", "theek ho jayega", "assured return", "fixed return", "number 1", "no. 1", "best in india")


def risky_claims(script: str) -> list[str]:
    low = str(script or "").lower()
    return [w for w in PROMISE_WORDS if w in low]


# ---------------------------------------------------------------- loudness / artwork
def loudness_verdict(lufs: float | None, tp: float | None, target: float = LUFS_TARGET) -> dict:
    if lufs is None:
        return {"ok": None, "say": "Loudness naap nahi paya (ffmpeg nahi?)."}
    probs = []
    if abs(lufs - target) > LUFS_TOL:
        probs.append(f"Awaaz {lufs:.1f} LUFS hai; Apple {target:.0f} ±1 LUFS maangta hai ({'dheemi' if lufs < target else 'tez'}).")
    if tp is not None and tp > TRUE_PEAK_MAX:
        probs.append(f"True peak {tp:.1f} dBTP hai; -1 dBTP se upar nahi hona chahiye (phatne ka dar).")
    return {"ok": not probs, "problems": probs,
            "say": "Awaaz sahi level par hai (Apple -16 LUFS ±1, peak -1 dBTP ke andar)." if not probs else " ".join(probs)}


def artwork_problems(w: int, h: int, fmt: str, mode: str) -> list[str]:
    p = []
    if w != h:
        p.append(f"Square nahi hai ({w}x{h}).")
    if min(w, h) < ART_MIN:
        p.append(f"Chhoti hai: kam se kam {ART_MIN}x{ART_MIN} chahiye (Apple).")
    if max(w, h) > ART_MAX:
        p.append(f"Badi hai: {ART_MAX}x{ART_MAX} tak (Apple).")
    if fmt.upper() not in ("JPEG", "PNG"):
        p.append("Sirf JPG ya PNG.")
    if mode not in ("RGB",):
        p.append(f"Colour {mode} hai; RGB chahiye (CMYK nahi).")
    return p


def feed_guid(feed_url: str) -> str:
    """podcast:guid = UUIDv5(podcast namespace, feed URL without scheme and trailing slashes)."""
    u = re.sub(r"^[a-zA-Z][a-zA-Z0-9+.\-]*://", "", str(feed_url or "").strip()).rstrip("/")
    return str(uuid.uuid5(GUID_NS, u))


# ---------------------------------------------------------------- RSS 2.0 + itunes + podcast namespace
def _x(t: Any) -> str:
    return escape(str(t or ""), {'"': "&quot;"})


def rss(channel: dict, items: list[dict]) -> str:
    """channel: title, link, description, language, author, owner_name, owner_email, image, category, subcategory, explicit,
    type, copyright, guid, self_url, locked(owner email) ; items: title, guid, pub (datetime), enclosure {url, length, type},
    duration (s), description (plain), html, season, episode, kind, explicit, transcripts [{url, type, rel}], chapters url,
    persons [{name, role}]."""
    c = channel
    out = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd" '
           'xmlns:podcast="https://podcastindex.org/namespace/1.0" xmlns:content="http://purl.org/rss/1.0/modules/content/" '
           'xmlns:atom="http://www.w3.org/2005/Atom">', "<channel>",
           f"<title>{_x(c.get('title'))}</title>", f"<link>{_x(c.get('link'))}</link>",
           f"<description>{_x(c.get('description'))}</description>", f"<language>{_x(c.get('language') or 'hi')}</language>",
           f"<itunes:author>{_x(c.get('author'))}</itunes:author>",
           f"<itunes:explicit>{'true' if c.get('explicit') else 'false'}</itunes:explicit>",
           f"<itunes:type>{_x(c.get('type') or 'episodic')}</itunes:type>", f"<podcast:guid>{_x(c.get('guid'))}</podcast:guid>",
           "<generator>Hoola Podcast Sahayak</generator>"]
    if c.get("self_url"):
        out.append(f'<atom:link href="{_x(c["self_url"])}" rel="self" type="application/rss+xml"/>')
    if c.get("copyright"):
        out.append(f"<copyright>{_x(c['copyright'])}</copyright>")
    if c.get("image"):
        out.append(f'<itunes:image href="{_x(c["image"])}"/>')
        out.append(f"<image><url>{_x(c['image'])}</url><title>{_x(c.get('title'))}</title><link>{_x(c.get('link'))}</link></image>")
    if c.get("category"):
        sub = f'<itunes:category text="{_x(c["subcategory"])}"/>' if c.get("subcategory") else ""
        out.append(f'<itunes:category text="{_x(c["category"])}">{sub}</itunes:category>')
    if c.get("owner_email"):
        out.append(f"<itunes:owner><itunes:name>{_x(c.get('owner_name') or c.get('author'))}</itunes:name>"
                   f"<itunes:email>{_x(c['owner_email'])}</itunes:email></itunes:owner>")
        out.append(f'<podcast:locked owner="{_x(c["owner_email"])}">yes</podcast:locked>')
    else:
        out.append("<podcast:locked>no</podcast:locked>")
    for it in items:
        pub = it.get("pub") or datetime.now(timezone.utc)
        enc = it.get("enclosure") or {}
        out += ["<item>", f"<title>{_x(it.get('title'))}</title>",
                f'<guid isPermaLink="false">{_x(it.get("guid"))}</guid>',
                f"<pubDate>{format_datetime(pub if pub.tzinfo else pub.replace(tzinfo=timezone.utc))}</pubDate>",
                f"<description>{_x(it.get('description'))}</description>"]
        if it.get("html"):
            out.append("<content:encoded><![CDATA[" + str(it["html"]).replace("]]>", "]]&gt;") + "]]></content:encoded>")
        if enc.get("url"):
            out.append(f'<enclosure url="{_x(enc["url"])}" length="{int(enc.get("length") or 0)}" type="{_x(enc.get("type") or "audio/mpeg")}"/>')
        if it.get("duration"):
            out.append(f"<itunes:duration>{int(round(it['duration']))}</itunes:duration>")
        out.append(f"<itunes:episodeType>{_x(it.get('kind') or 'full')}</itunes:episodeType>")
        if it.get("season"):
            out += [f"<itunes:season>{int(it['season'])}</itunes:season>", f"<podcast:season>{int(it['season'])}</podcast:season>"]
        if it.get("episode"):
            out += [f"<itunes:episode>{int(it['episode'])}</itunes:episode>", f"<podcast:episode>{int(it['episode'])}</podcast:episode>"]
        out.append(f"<itunes:explicit>{'true' if it.get('explicit') else 'false'}</itunes:explicit>")
        for tr in it.get("transcripts") or []:
            rel = f' rel="{_x(tr["rel"])}"' if tr.get("rel") else ""
            out.append(f'<podcast:transcript url="{_x(tr["url"])}" type="{_x(tr["type"])}"{rel}/>')
        if it.get("chapters"):
            out.append(f'<podcast:chapters url="{_x(it["chapters"])}" type="application/json+chapters"/>')
        for p in it.get("persons") or []:
            out.append(f'<podcast:person role="{_x(p.get("role") or "guest")}">{_x(p.get("name"))}</podcast:person>')
        out.append("</item>")
    out += ["</channel>", "</rss>"]
    return "\n".join(out)


# ---------------------------------------------------------------- analytics she pastes / exports
_COLS = {
    "label": ("episode", "episode title", "title", "name", "content", "video title", "episode name"),
    "day": ("date", "day", "published", "release date", "publish date"),
    "plays": ("plays", "streams", "starts", "downloads", "listens", "views", "total plays", "total streams"),
    "listeners": ("listeners", "audience", "unique listeners", "unique viewers", "engaged listeners", "reach"),
    "followers": ("followers", "subscribers", "follows"),
    "consumption": ("consumption", "average consumption", "avg consumption", "average listen", "completion",
                    "average percentage viewed", "avg % viewed", "% listened", "listen through"),
}


def _col(header: str) -> str:
    h = re.sub(r"\s+", " ", re.sub(r"[_\-()]+", " ", header.strip().lower())).strip()
    for k, names in _COLS.items():
        if h in names:
            return k
    for k, names in _COLS.items():
        if any(h.startswith(n) for n in names if len(n) > 4):
            return k
    return ""


def _n(v: Any) -> float | None:
    s = re.sub(r"[^\d.\-]", "", str(v or "").replace(",", ""))
    try:
        return float(s) if s not in ("", "-", ".") else None
    except ValueError:
        return None


def parse_stats(text: str) -> list[dict]:
    """CSV / tab text from Spotify for Creators, Apple Podcasts Connect, YouTube Studio or any sheet -> rows. Only numbers that
    are in her file; a column we don't recognise is ignored (never guessed)."""
    t = str(text or "").strip().lstrip("﻿")
    if not t:
        return []
    dialect = "\t" if t.count("\t") > t.count(",") else ","
    rows = list(csv.reader(io.StringIO(t), delimiter=dialect))
    hdr_i = next((i for i, r in enumerate(rows[:15]) if sum(1 for c in r if _col(c)) >= 2), -1)
    if hdr_i < 0:
        return []
    keys = [_col(c) for c in rows[hdr_i]]
    out = []
    for r in rows[hdr_i + 1:]:
        d: dict[str, Any] = {}
        for k, v in zip(keys, r):
            if not k or k in d:
                continue
            if k in ("label", "day"):
                d[k] = clean(v, 300)
            else:
                d[k] = _n(v)
        if not d.get("label") or (d.get("label", "").lower() in ("total", "totals", "sum")):
            continue
        if all(d.get(k) is None for k in ("plays", "listeners", "followers", "consumption")):
            continue
        if d.get("consumption") is not None and d["consumption"] <= 1 and "%" not in t:
            d["consumption"] = round(d["consumption"] * 100, 1)
        out.append(d)
    return out


def platform_of(text: str) -> str:
    low = str(text or "").lower()
    for k, words in PLATFORM_WORDS.items():
        if any(w in low for w in words):
            return k
    return "other"
