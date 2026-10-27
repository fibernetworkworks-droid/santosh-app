"""Artist Sahayak rules (pure functions): words -> facts, gig time windows and the double-booking test, ISRC / UPC / IPI
checks, royalty-registration checklist, release plan dates, fee / TDS / GST notes, settlement maths and splits.

Everything here only reads what is written; nothing is guessed. Notes are plain-words guidance with sources (CLAUDE.md v0.1xx),
never legal or tax advice."""
from __future__ import annotations

import hashlib
import json
import re
from datetime import date, datetime, time, timedelta
from typing import Any

MONTHS = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6, "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12}

KINDS = ("singer", "band", "dj", "instrumentalist", "composer", "lyricist", "rapper", "classical", "folk", "other")
KIND_LABEL = {"singer": "Singer", "band": "Band", "dj": "DJ", "instrumentalist": "Instrumentalist", "composer": "Composer",
              "lyricist": "Lyricist", "rapper": "Rapper", "classical": "Classical artist", "folk": "Folk artist", "other": "Artist"}

EVENT_WORDS = {
    "wedding": ("shaadi", "shadi", "wedding", "sangeet", "mehendi", "mehndi", "reception", "haldi", "शादी", "संगीत", "लग्न"),
    "corporate": ("corporate", "office", "company", "annual day", "offsite", "conference", "launch", "award"),
    "college": ("college", "fest", "university", "iit", "campus", "school"),
    "club": ("club", "pub", "bar", "lounge", "cafe", "restaurant"),
    "concert": ("concert", "ticketed", "show", "tour", "auditorium", "stadium"),
    "festival": ("festival", "mahotsav", "utsav", "navratri", "garba", "ganpati", "durga puja", "diwali", "holi"),
    "private": ("birthday", "anniversary", "private", "house party", "party"),
    "recording": ("recording", "studio", "jingle", "dubbing", "film song", "ad film", "playback"),
}
EVENT_LABEL = {"wedding": "Shaadi / sangeet", "corporate": "Corporate", "college": "College fest", "club": "Club / cafe",
               "concert": "Concert / ticketed show", "festival": "Festival", "private": "Private party", "recording": "Recording / studio",
               "other": "Event"}

GIG_STATUS = ("enquiry", "hold", "confirmed", "done", "cancelled")
BLOCKING = ("hold", "confirmed")

# Royalty / identity registrations a working musician in India keeps (status per artist: none | applied | done | na).
REGS = {
    "iprs": {"label": "IPRS membership + works registered",
             "who": "lyricist / composer / music publisher",
             "why": "Gaane ke bol aur dhun (musical + literary work) ki public performance / broadcast royalty. IPRS registered copyright society hai.",
             "how": "iprs.org par membership; har gaana (work) writer splits ke saath register karein."},
    "isamra": {"label": "ISAMRA (singers + musicians) membership",
               "who": "singer / musician (performer)",
               "why": "Performer ki royalty (Copyright Act s.38A): recording ke commercial use par. ISAMRA (pehle ISRA) singers aur musicians ka registered society hai.",
               "how": "ISAMRA par membership + apne gaane / performances list karein."},
    "ppl": {"label": "PPL (sound recording owner)",
            "who": "jo master recording ka owner / label hai",
            "why": "Sound recording ki public performance royalty. PPL 11 Jun 2026 se registered copyright society (s.33(3)).",
            "how": "Agar artist khud apne masters ka owner hai to PPL membership; label ke paas masters hon to label karta hai."},
    "isrc": {"label": "ISRC registrant code",
             "who": "jo recording release karta hai (artist-label / label)",
             "why": "Har recording ka ek pakka ISRC (IN-XXX-YY-NNNNN). Ek recording = ek code, kabhi dobara use nahi.",
             "how": "India ki ISRC agency IMI (isrc@indianmi.org) se registrant code, ya distributor se ISRC lein."},
    "ipi": {"label": "IPI name number",
            "who": "lyricist / composer",
            "why": "Duniya bhar mein writer ki pehchaan (CISAC); IPRS member banne par milta hai.",
            "how": "IPRS membership ke saath."},
    "distributor": {"label": "Distributor account (Spotify / JioSaavn / YouTube Music ...)",
                    "who": "artist / label",
                    "why": "Streaming par release + royalty statement. Terms (share, payout, lead time) jo aap batayein wahi.",
                    "how": "Aapka chuna hua distributor; uske terms Niyam mein likhiye."},
    "content_id": {"label": "YouTube Content ID (distributor ke through)",
                   "who": "recording owner",
                   "why": "Doosron ke video mein aapka gaana chale to claim / earning.",
                   "how": "Distributor ka Content ID option (sirf apne masters par)."},
    "copyright": {"label": "Copyright registration (optional)",
                  "who": "work / sound recording owner",
                  "why": "Copyright bina registration ke bhi hota hai; registration court mein saboot ke kaam aata hai.",
                  "how": "copyright.gov.in e-filing (Form XIV)."},
    "pan_gst": {"label": "PAN + GST (agar turnover limit ke upar)",
                "who": "artist / agency",
                "why": "TDS credit 26AS mein PAN par; GST registration services ke liye Rs 20 lakh (special states Rs 10 lakh) ke upar.",
                "how": "Apna CA."},
}
REG_STATUS = ("none", "applied", "done", "na")

# The organiser's side of a live show (listed in contract / checklist; she never files them).
ORGANISER_DUTIES = [
    "Police / local permission for the event (state Police Act / Collector) - organiser ki zimmedaari.",
    "Music licences for the event: IPRS (gaane ke bol + dhun) aur sound recordings ke liye PPL / jo society / owner repertoire rakhta ho - organiser / venue.",
    "Noise Rules 2000 (Rule 5): khuli jagah par loudspeaker raat 10 se subah 6 tak nahi (state 15 tyohaar ke din midnight tak de sakta hai).",
    "Stage, sound, light, power backup rider ke hisaab se; security aur crowd control.",
    "Artist ka travel, stay, local transport, khana: contract mein jo tay ho.",
]

PERFORMER_CLAUSE = ("Artist ke live performance ki audio / video recording, live streaming ya broadcast sirf artist ki likhit ijazat "
                    "se (Copyright Act 1957 s.38A). Ijazat milne par bhi artist ka naam dikhana hoga (s.38B moral rights).")


def digest(obj: Any) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()


def clean(text: Any, n: int = 500) -> str:
    """Promoter / her words: secrets never kept (OTP / PIN / password values, card-like and Aadhaar-like numbers)."""
    t = str(text or "")
    t = re.sub(r"\b(otp|pin|cvv|password|upi pin)\b\s*(?:is|hai|:|=)?\s*\S+", lambda m: f"{m.group(1)} [hataya]", t, flags=re.I)
    t = re.sub(r"\b(?:\d[ -]?){12,19}\b", "[hataya]", t)
    return t.strip()[:n]


def phone(text: Any) -> str:
    d = re.sub(r"\D", "", str(text or ""))
    if len(d) == 12 and d.startswith("91"):
        d = d[2:]
    if len(d) == 11 and d.startswith("0"):
        d = d[1:]
    return d if re.fullmatch(r"[6-9]\d{9}", d) else ""


def key_of(name: Any) -> str:
    return re.sub(r"[^a-z0-9]", "", str(name or "").lower())


# ---------------------------------------------------------------- words -> facts
def date_of(text: Any, today: date) -> date | None:
    s = str(text or "").lower()
    if re.search(r"\b(aaj|today)\b", s):
        return today
    if re.search(r"\b(kal|tomorrow)\b", s):
        return today + timedelta(days=1)
    m = re.search(r"\b(20\d\d)-(\d{1,2})-(\d{1,2})\b", s)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            return None
    m = re.search(r"\b(\d{1,2})\s*(?:st|nd|rd|th)?\s*(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?(?:\s*,?\s*(20\d\d))?", s)
    if m:
        return _mk(int(m.group(1)), MONTHS[m.group(2)], m.group(3), today)
    m = re.search(r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+(\d{1,2})\b(?:\s*,?\s*(20\d\d))?", s)
    if m:
        return _mk(int(m.group(2)), MONTHS[m.group(1)], m.group(3), today)
    m = re.search(r"\b(\d{1,2})[/.-](\d{1,2})(?:[/.-](\d{2,4}))?\b(?!\s*(?:lakh|lac|l\b|k\b|cr\b|crore|hazaar|hazar|%|min|ghant|hour|hr))", s)
    if m:
        return _mk(int(m.group(1)), int(m.group(2)), m.group(3), today)
    return None


def _mk(d: int, mo: int, y: Any, today: date) -> date | None:
    try:
        if y:
            yy = int(y)
            yy = yy + 2000 if yy < 100 else yy
            return date(yy, mo, d)
        x = date(today.year, mo, d)
        return x if x >= today else date(today.year + 1, mo, d)
    except ValueError:
        return None


def hhmm(v: Any) -> str:
    """'20:30', '8:30 pm', 'raat 9 baje', '9 pm' -> 'HH:MM'; '' when not said."""
    s = str(v or "").lower().strip()
    if not s:
        return ""
    m = re.search(r"\b(\d{1,2})[:.](\d{2})\s*(am|pm)?", s)
    h = mi = None
    ap = ""
    if m:
        h, mi, ap = int(m.group(1)), int(m.group(2)), (m.group(3) or "")
    else:
        m = re.search(r"\b(\d{1,2})\s*(am|pm|baje|bje)\b", s)
        if m:
            h, mi, ap = int(m.group(1)), 0, m.group(2)
    if h is None:
        return ""
    if ap == "pm" and h < 12:
        h += 12
    elif ap == "am" and h == 12:
        h = 0
    elif ap in ("baje", "bje", "") and h < 12 and re.search(r"shaam|sham|raat|night|evening|dopahar|afternoon|शाम|रात", s):
        if not (h <= 3 and re.search(r"raat|night|रात", s)):
            h += 12
    if not (0 <= h <= 23 and 0 <= mi <= 59):
        return ""
    return f"{h:02d}:{mi:02d}"


def money_of(text: Any) -> float | None:
    """'1.5 lakh', '75k', 'Rs 80,000', '₹ 2,00,000', '50 hazaar' -> rupees; None when no amount."""
    s = str(text or "").lower().replace(",", "")
    m = re.search(r"(?:rs\.?|₹|inr|fee|fees|budget|amount|paisa|payment)\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*(lakh|lac|l|k|hazaar|hazar|thousand|cr|crore)?\b", s)
    if not m:
        m = re.search(r"\b(\d+(?:\.\d+)?)\s*(lakh|lac|k|hazaar|hazar|thousand|cr|crore)\b", s)
    if not m:
        return None
    v = float(m.group(1))
    mult = {"lakh": 1e5, "lac": 1e5, "l": 1e5, "k": 1e3, "hazaar": 1e3, "hazar": 1e3, "thousand": 1e3, "cr": 1e7, "crore": 1e7}
    v *= mult.get((m.group(2) or "").lower(), 1)
    return round(v, 2) if v > 0 else None


def minutes_of(text: Any) -> int | None:
    s = str(text or "").lower()
    m = re.search(r"(\d+(?:\.\d+)?)\s*(?:ghante|ghanta|hours?|hrs?|hr)\b", s)
    if m:
        return int(round(float(m.group(1)) * 60))
    m = re.search(r"(\d{2,3})\s*(?:min|minute|minutes|mins)\b", s)
    return int(m.group(1)) if m else None


def event_of(text: Any) -> str:
    t = str(text or "").lower()
    for k, words in EVENT_WORDS.items():
        if any(w in t for w in words):
            return k
    return ""


def city_of(text: Any, known: list[str] | None = None) -> str:
    t = str(text or "")
    for c in known or []:
        if c and re.search(rf"\b{re.escape(c)}\b", t, re.I):
            return c
    m = re.search(r"\b(?:in|at|venue|city|shehar|mein)\s*[:\-]?\s*([A-Z][a-zA-Z]{2,20})\b", t)
    if m and m.group(1).lower() not in ("the", "our", "my", "aapke", "hamare", "shaam", "raat", "dec", "jan"):
        return m.group(1)
    m = re.search(r"\b([A-Z][a-zA-Z]{2,20})\s+(?:mein|me|main)\b", t)
    return m.group(1) if m else ""


def parse_offer(text: str, today: date, cities: list[str] | None = None) -> dict:
    """Facts from a pasted / forwarded show offer (WhatsApp, email, call note). Only what is written; the rest stays blank."""
    t = clean(text, 3000)
    out: dict[str, Any] = {}
    for m in re.finditer(r"(?:\+?91[\s-]?)?[6-9]\d{4}[\s-]?\d{5}", t):
        p = phone(m.group(0))
        if p:
            out["phone"] = p
            break
    m = re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", t)
    if m:
        out["email"] = m.group(0)[:120]
    d = date_of(t, today)
    if d:
        out["day"] = d.isoformat()
    tm = hhmm(t)
    if tm:
        out["start"] = tm
    f = money_of(t)
    if f:
        out["fee"] = f
    mins = minutes_of(t)
    if mins:
        out["set_minutes"] = mins
    ev = event_of(t)
    if ev:
        out["event_type"] = ev
    c = city_of(t, cities)
    if c:
        out["city"] = c
    m = re.search(r"\b(?i:i am|i'm|main|mera naam|naam|this is)\s*[:\-]?\s*([A-Z][A-Za-z .]{1,40}?)(?:\s+(?:hai|hoon|hu|here|from)\b|[,.\n]|$)", t)
    if m:
        out["promoter"] = m.group(1).strip()
    if re.search(r"\bticket|ticketed|tickets\b", t, re.I):
        out["ticketed"] = True
    return out


# ---------------------------------------------------------------- time windows and the double-booking test
def window(day: date, start: str, end: str = "", set_minutes: int | None = None) -> tuple[datetime, datetime]:
    """Naive local window of a gig. No start = the whole day. End before start = next day (late-night set)."""
    if not start:
        return datetime.combine(day, time(0, 0)), datetime.combine(day, time(23, 59))
    h, m = (int(x) for x in start.split(":"))
    a = datetime.combine(day, time(h, m))
    if end:
        h2, m2 = (int(x) for x in end.split(":"))
        b = datetime.combine(day, time(h2, m2))
        if b <= a:
            b += timedelta(days=1)
    else:
        b = a + timedelta(minutes=set_minutes or 120)
    return a, b


def gap_needed(city_a: str, city_b: str, same_min: int, other_min: int) -> int:
    """Minutes the artist needs between two gigs: same city = her same-city buffer, other / unknown city = her travel buffer."""
    if city_a and city_b and key_of(city_a) == key_of(city_b):
        return max(0, int(same_min))
    return max(0, int(other_min))


def clashes(a: tuple[datetime, datetime], b: tuple[datetime, datetime], gap_min: int) -> bool:
    g = timedelta(minutes=gap_min)
    return a[0] < b[1] + g and b[0] < a[1] + g


# ---------------------------------------------------------------- codes
ISRC_RE = re.compile(r"^([A-Z]{2})-?([A-Z0-9]{3})-?(\d{2})-?(\d{5})$")


def isrc(v: Any) -> str:
    """Canonical 12-char ISRC (CC XXX YY NNNNN) or '' when the shape is wrong."""
    s = re.sub(r"\s", "", str(v or "").upper())
    m = ISRC_RE.match(s)
    return "".join(m.groups()) if m else ""


def isrc_pretty(code: str) -> str:
    return f"{code[:2]}-{code[2:5]}-{code[5:7]}-{code[7:]}" if len(code) == 12 else code


def upc_ok(v: Any) -> bool:
    d = re.sub(r"\D", "", str(v or ""))
    if len(d) not in (12, 13):
        return False
    digits = [int(x) for x in d]
    body, chk = digits[:-1], digits[-1]
    w = [3, 1] if len(d) == 12 else [1, 3]
    tot = sum(x * w[i % 2] for i, x in enumerate(body))
    return (10 - tot % 10) % 10 == chk


def ipi_ok(v: Any) -> bool:
    return bool(re.fullmatch(r"\d{9,11}", re.sub(r"\D", "", str(v or ""))))


def gstin_ok(v: Any) -> bool:
    g = str(v or "").strip().upper()
    try:
        from ..india.money import gstin_ok as _ok
        return bool(_ok(g))
    except Exception:
        return bool(re.fullmatch(r"\d{2}[A-Z]{5}\d{4}[A-Z][1-9A-Z]Z[0-9A-Z]", g))


# ---------------------------------------------------------------- splits and money
def split_problems(rows: list[dict], field: str = "split_pct") -> list[str]:
    vals = [r.get(field) for r in rows if r.get(field) is not None]
    if not rows or not vals:
        return []
    probs = []
    if any(float(v) < 0 for v in vals):
        probs.append("Hissa minus nahi ho sakta.")
    tot = round(sum(float(v) for v in vals), 2)
    if len(vals) != len(rows):
        probs.append("Har member / writer ka hissa likhiye (kuch khaali hain).")
    elif abs(tot - 100) > 0.01:
        probs.append(f"Hisse milkar {tot:g}% hain, 100% hone chahiye.")
    return probs


def share(amount: float, rows: list[dict], field: str = "split_pct") -> list[dict]:
    """Splits an amount by % exactly (paise rounding goes to the first row)."""
    out = []
    left = round(amount, 2)
    for i, r in enumerate(rows):
        part = round(amount * float(r.get(field) or 0) / 100, 2)
        out.append({**r, "amount": part})
        left = round(left - part, 2)
    if out and abs(left) >= 0.01:
        out[0]["amount"] = round(out[0]["amount"] + left, 2)
    return out


def settlement(fee: float | None, received: float, tds: float, commission_pct: float | None, expenses: list[dict]) -> dict:
    """Gig money in plain numbers. Commission is HER % on the agreed fee (blank % = no line). TDS is the promoter's deduction:
    it is the artist's tax credit (Form 16A / 26AS), not money lost. Expenses she paid for the artist come back to her."""
    exp_recover = round(sum(float(e.get("amount") or 0) for e in expenses if e.get("paid_by") == "manager"), 2)
    exp_artist = round(sum(float(e.get("amount") or 0) for e in expenses if e.get("paid_by") == "artist"), 2)
    comm = round((fee or 0) * commission_pct / 100, 2) if (commission_pct is not None and fee) else None
    due_from_promoter = round((fee or 0) - tds - received, 2) if fee is not None else None
    net = round(received - (comm or 0) - exp_recover, 2)
    return {"fee": fee, "received": round(received, 2), "tds": round(tds, 2), "commission": comm,
            "commission_pct": commission_pct, "expenses_recover": exp_recover, "expenses_artist": exp_artist,
            "due_from_promoter": due_from_promoter, "net_to_artist": net,
            "fully_paid": fee is not None and due_from_promoter is not None and due_from_promoter <= 0.5}


def tds_note(event_type: str, fee: float | None) -> str:
    if event_type == "recording":
        return ("Film / ad ke liye recording: Income-tax Rules mein 'film artist' (singer, music director, lyricist...) professional "
                "hain -> s.393(1) professional fees 10% (saal mein Rs 50,000 se upar). Apne CA se pakka karein.")
    return ("Live show ki payment par promoter TDS kaat sakta hai: ITAT Delhi (C.J. International Hotels, 10 Mar 2016) ne live "
            "performance ko contract (purana 194C, ab s.393(1) contract: 1% individual / 2% firm, ek payment Rs 30,000 ya saal mein "
            "Rs 1 lakh se upar) mana; kuch promoter professional 10% kaatte hain. Jo kata uska Form 16A maangiye. Apne CA se pakka karein.")


def gst_note(issuer_gstin: str, art_form: str, fee: float | None, brand: bool = False) -> tuple[float, str]:
    """(gst %, note). No GSTIN = no GST on the invoice. Folk / classical performance up to Rs 1.5 lakh per performance is exempt
    (Notfn 12/2017-CT(R) entry 13(b)), not for a brand ambassador. Else 18%. Her CA confirms."""
    if not issuer_gstin:
        return 0.0, "Invoice dene wale ka GSTIN nahi: GST nahi lagaya (Rs 20 lakh se upar turnover par registration zaroori)."
    if art_form in ("folk", "classical") and not brand and fee is not None and fee <= 150000:
        return 0.0, "Folk / classical performance Rs 1.5 lakh tak: GST chhoot (Notfn 12/2017-CT(R) entry 13(b)). CA se pakka karein."
    return 18.0, "Performance / artist service par GST 18%. CA se pakka karein."


def gst_lines(base: float, pct: float, same_state: bool) -> dict:
    tax = round(base * pct / 100, 2)
    if not pct:
        return {"tax": 0.0, "cgst": 0.0, "sgst": 0.0, "igst": 0.0}
    if same_state:
        half = round(tax / 2, 2)
        return {"tax": round(half * 2, 2), "cgst": half, "sgst": half, "igst": 0.0}
    return {"tax": tax, "cgst": 0.0, "sgst": 0.0, "igst": tax}


# ---------------------------------------------------------------- release plan
def release_plan(release_day: date, lead_days: int | None, today: date) -> list[dict]:
    """Steps with dates. Distributor lead time only from HER distributor terms (unknown = said, never guessed)."""
    steps = []
    if lead_days is not None:
        steps.append({"key": "deliver", "what": f"Distributor ko audio + artwork + metadata (aapke terms: {lead_days} din pehle)",
                      "by": (release_day - timedelta(days=lead_days)).isoformat()})
    else:
        steps.append({"key": "deliver", "what": "Distributor ko delivery: unka lead time Niyam mein likhiye (pata nahi)", "by": ""})
    steps.append({"key": "pitch", "what": "Spotify for Artists pitch (release se kam se kam 7 din pehle; ek waqt ek gaana)",
                  "by": (release_day - timedelta(days=7)).isoformat()})
    steps.append({"key": "iprs", "what": "IPRS mein gaana (work) writer splits ke saath register", "by": release_day.isoformat()})
    steps.append({"key": "release", "what": "Release", "by": release_day.isoformat()})
    for s in steps:
        s["late"] = bool(s["by"]) and s["by"] < today.isoformat()
    return steps


def track_problems(t: dict) -> list[str]:
    p = []
    nm = t.get("title") or "?"
    if not t.get("isrc"):
        p.append(f"'{nm}': ISRC nahi (IMI registrant code ya distributor se).")
    elif not isrc(t["isrc"]):
        p.append(f"'{nm}': ISRC '{t['isrc']}' ka roop galat (IN-XXX-YY-NNNNN).")
    ws = t.get("writers") or []
    if not ws:
        p.append(f"'{nm}': lyricist / composer ke naam aur hisse nahi.")
    else:
        p += [f"'{nm}': {x}" for x in split_problems(ws, "share")]
        for w in ws:
            if w.get("ipi") and not ipi_ok(w["ipi"]):
                p.append(f"'{nm}': {w.get('name', '?')} ka IPI {w['ipi']} 9-11 ank ka hona chahiye.")
    return p
