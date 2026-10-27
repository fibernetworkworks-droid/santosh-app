"""Pure rules of the Banquet Sahayak (no DB): slots and clashes, words -> enquiry facts, GST per line, quotation maths,
payment schedule, cancellation refund by HER policy, noise note, hashing and cleaning.

GST (checked 23 Oct 2026, her CA confirms; every rate is HER setting per line):
  * catering / banquet food at premises that are NOT 'specified premises' = 5% without ITC; at specified premises (a hotel that
    gave any room above Rs 7,500 a day in the previous FY, or opted in) = 18% with ITC (GST 2.0, 22 Sep 2025);
  * hall / lawn rent alone (no food from her) = 18%; hall bundled with her catering = one composite supply taxed at the rate of
    the principal supply (catering) -> same rate as the food;
  * rooms: up to Rs 7,500 per unit per day 5% (no ITC), above 18%;
  * decor / DJ / other extras = 18% starter (event services), her setting;
  * place of supply for a function at her venue = the venue (IGST Act s.12(3)(c)) -> always CGST + SGST.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import date, timedelta
from typing import Any

SLOTS = ("morning", "evening", "full")
SLOT_LABEL = {"morning": "Subah", "evening": "Shaam", "full": "Pura din"}
DEFAULT_SLOTS = {"morning": {"from": "08:00", "to": "15:00"}, "evening": {"from": "18:00", "to": "23:30"},
                 "full": {"from": "08:00", "to": "23:30"}}
DIETS = ("veg", "nonveg", "jain")
DIET_LABEL = {"veg": "Veg", "nonveg": "Non-veg", "jain": "Jain"}
HALL_KINDS = ("hall", "lawn", "terrace", "poolside", "room")
OPEN_AIR = ("lawn", "terrace", "poolside")
EXTRA_KINDS = ("decor", "dj", "rooms", "sound", "lights", "photo", "valet", "other")
EVENT_WORDS = {
    "wedding": ("shaadi", "shadi", "wedding", "vivah", "lagna", "lagn", "marriage", "pheras", "शादी", "विवाह", "लग्न"),
    "reception": ("reception", "receptn", "रिसेप्शन"),
    "engagement": ("engagement", "sagai", "mangni", "sakharpuda", "ring ceremony", "सगाई", "साखरपुडा"),
    "haldi_mehendi": ("haldi", "mehendi", "mehndi", "sangeet", "हल्दी", "मेहंदी", "संगीत"),
    "birthday": ("birthday", "janamdin", "janmdin", "bday", "वाढदिवस", "जन्मदिन"),
    "corporate": ("corporate", "conference", "meeting", "seminar", "launch", "office party", "agm", "offsite"),
    "religious": ("pooja", "puja", "satyanarayan", "katha", "bhandara", "jagran", "पूजा"),
    "baby_shower": ("godh bharai", "baby shower", "dohale", "डोहाळे"),
    "anniversary": ("anniversary", "saalgirah"),
    "other": (),
}
EVENT_LABEL = {"wedding": "Shaadi", "reception": "Reception", "engagement": "Sagai", "haldi_mehendi": "Haldi / Mehendi / Sangeet",
               "birthday": "Birthday", "corporate": "Corporate", "religious": "Pooja / dharmik", "baby_shower": "Godh bharai",
               "anniversary": "Anniversary", "other": "Function"}
DEFAULT_STAGES = [{"label": "Advance (booking pakki)", "pct": 25, "days_before": None},
                  {"label": "Doosri kisht", "pct": 50, "days_before": 15},
                  {"label": "Baaki (final count ke baad)", "pct": 25, "days_before": 1}]
# starter policy (hers to change): refund % of what was paid, by days before the event
DEFAULT_CANCEL = [{"days_before": 90, "refund_pct": 90}, {"days_before": 30, "refund_pct": 50}, {"days_before": 7, "refund_pct": 25},
                  {"days_before": 0, "refund_pct": 0}]
MONTHS = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6, "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12}


def digest(obj: Any) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()


def clean(text: Any, n: int = 500) -> str:
    """Client / her words: secrets never kept (OTP / PIN / password values, card-like and Aadhaar-like numbers)."""
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


def slot_of(text: Any) -> str:
    t = str(text or "").lower().strip()
    if t in SLOTS:
        return t
    if re.search(r"pura din|poora din|full ?day|din bhar|whole day|dono|both|पूरा दिन", t):
        return "full"
    if re.search(r"subah|morning|savere|lunch|din ka|dopahar|afternoon|सुबह|सकाळ", t):
        return "morning"
    if re.search(r"shaam|sham|evening|raat|night|dinner|शाम|रात|संध्याकाळ", t):
        return "evening"
    return ""


def slots_clash(a: str, b: str) -> bool:
    """full day takes the whole hall: it clashes with everything; morning / evening clash only with themselves."""
    return a == b or "full" in (a, b)


def diet_of(text: Any) -> str:
    t = str(text or "").lower()
    if "jain" in t or "जैन" in t:
        return "jain"
    if re.search(r"non[ -]?veg|nonveg|chicken|mutton|fish|egg|मांसाहार|मटन|चिकन", t):
        return "nonveg"
    if re.search(r"\bveg\b|shakahari|pure veg|शाकाहार", t):
        return "veg"
    return ""


def event_of(text: Any) -> str:
    t = str(text or "").lower()
    for k, words in EVENT_WORDS.items():
        if any(w in t for w in words):
            return k
    return ""


def date_of(text: Any, today: date) -> date | None:
    """A date in her / client's words; a day-month without a year = the next such day from today."""
    s = str(text or "").lower()
    m = re.search(r"\b(20\d\d)-(\d{1,2})-(\d{1,2})\b", s)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            return None
    m = re.search(r"\b(\d{1,2})[/.-](\d{1,2})(?:[/.-](\d{2,4}))?\b", s)
    if m:
        d, mo, y = int(m.group(1)), int(m.group(2)), m.group(3)
        return _mk(d, mo, y, today)
    m = re.search(r"\b(\d{1,2})\s*(?:st|nd|rd|th)?\s*(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?(?:\s*,?\s*(20\d\d))?", s)
    if m:
        return _mk(int(m.group(1)), MONTHS[m.group(2)], m.group(3), today)
    m = re.search(r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+(\d{1,2})(?:\s*,?\s*(20\d\d))?", s)
    if m:
        return _mk(int(m.group(2)), MONTHS[m.group(1)], m.group(3), today)
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


def guests_of(text: Any) -> int | None:
    s = str(text or "").lower()
    m = re.search(r"(\d{2,5})\s*(?:\+\s*)?(?:log|logon|logo|guests?|pax|people|persons?|mehmaan|mehman|plates?|thali|लोग|लोक|मेहमान)", s)
    if m:
        return int(m.group(1))
    m = re.search(r"(?:guests?|pax|mehmaan|log)\s*[:=-]?\s*(\d{2,5})", s)
    return int(m.group(1)) if m else None


def parse_enquiry(text: str, today: date) -> dict:
    """Facts from a pasted / forwarded enquiry (WhatsApp text, call note). Only what is written; the rest stays blank."""
    t = clean(text, 2000)
    out: dict[str, Any] = {}
    ph = ""
    for m in re.finditer(r"(?:\+?91[\s-]?)?[6-9]\d{4}[\s-]?\d{5}", t):
        ph = phone(m.group(0))
        if ph:
            break
    if ph:
        out["phone"] = ph
    d = date_of(t, today)
    if d:
        out["date"] = d.isoformat()
    g = guests_of(t)
    if g:
        out["guests"] = g
    for k, f in (("slot", slot_of), ("diet", diet_of), ("event_type", event_of)):
        v = f(t)
        if v:
            out[k] = v
    m = re.search(r"\b(?:naam|name|i am|main|mera naam)\s*[:\-]?\s*([A-Za-z][A-Za-z .]{1,40}?)(?:\s+(?:hai|hoon|hu|here)\b|[,.\n]|$)", t, re.I)
    if m:
        out["name"] = m.group(1).strip().title()
    m = re.search(r"budget\s*[:\-]?\s*(?:rs\.?|₹)?\s*([\d,.]+)\s*(lakh|lac|l|k|hazaar|thousand)?", t, re.I)
    if m:
        v = float(m.group(1).replace(",", "") or 0)
        mult = {"lakh": 1e5, "lac": 1e5, "l": 1e5, "k": 1e3, "hazaar": 1e3, "thousand": 1e3}.get((m.group(2) or "").lower(), 1)
        if v:
            out["budget"] = round(v * mult)
    return out


def hhmm(v: Any, default: str) -> str:
    s = str(v or "").strip()
    m = re.fullmatch(r"(\d{1,2})[:.](\d{2})", s)
    if not m or int(m.group(1)) > 23 or int(m.group(2)) > 59:
        return default
    return f"{int(m.group(1)):02d}:{m.group(2)}"


def food_gst(specified: bool, override: float | None = None) -> float:
    if override is not None:
        return float(override)
    return 18.0 if specified else 5.0


def room_gst(tariff: float) -> float:
    """Hotel accommodation (GST 2.0 from 22 Sep 2025): up to Rs 7,500 per unit per day 5%, above 18%."""
    return 5.0 if tariff <= 7500 else 18.0


def gst_split(base: float, pct: float) -> dict:
    """Function at her venue: place of supply = the venue (IGST Act s.12(3)(c)) -> CGST + SGST."""
    tax = round(base * pct / 100.0, 2)
    half = round(tax / 2.0, 2)
    return {"cgst": half, "sgst": round(tax - half, 2), "tax": tax}


def plates_billed(expected: int | None, guarantee: int | None, final: int | None = None, actual: int | None = None) -> int | None:
    """Plates charged = the higher of the minimum guarantee and the latest count (actual > final > expected)."""
    count = actual or final or expected
    vals = [v for v in (guarantee, count) if v]
    return max(vals) if vals else None


def split_amount(total: float, stages: list[dict]) -> list[float]:
    """Stage amounts that add up exactly to the total (last stage takes the rounding)."""
    out, run = [], 0.0
    for i, s in enumerate(stages):
        if i == len(stages) - 1:
            out.append(round(total - run, 2))
        else:
            a = round(total * float(s.get("pct") or 0) / 100.0, 0)
            out.append(a)
            run += a
    return out


def check_stages(stages: list[dict]) -> list[str]:
    probs = []
    if not stages:
        probs.append("Kam se kam ek kisht chahiye.")
    tot = sum(float(s.get("pct") or 0) for s in stages)
    if abs(tot - 100) > 0.01:
        probs.append(f"Kishton ka jod 100% hona chahiye (abhi {tot:g}%).")
    for s in stages:
        if not str(s.get("label") or "").strip():
            probs.append("Har kisht ka naam chahiye.")
            break
    return probs


def check_cancel(policy: list[dict]) -> tuple[list[str], list[str]]:
    """Problems (refuse) and notes (shown to her). Forfeiting everything months ahead can be an 'unfair contract' (CPA 2019
    s.2(46)); consumer commissions have ordered refunds where halls kept the whole advance."""
    probs, notes = [], []
    if not policy:
        probs.append("Cancellation policy khaali hai: likhiye kitne din pehle kitna wapas.")
    for p in policy:
        try:
            d, r = int(p.get("days_before")), float(p.get("refund_pct"))
        except (TypeError, ValueError):
            probs.append("Har line mein days_before aur refund_pct number chahiye.")
            continue
        if d < 0 or not 0 <= r <= 100:
            probs.append("days_before 0 ya zyada, refund_pct 0-100.")
    if not probs:
        far = [p for p in policy if int(p["days_before"]) >= 30 and float(p["refund_pct"]) == 0]
        if far:
            notes.append("30+ din pehle cancel par bhi poora advance rakhna 'unfair contract' gina ja sakta hai (CPA 2019 s.2(46)); "
                         "consumer commissions ne aise mamlon mein refund dilwaya hai. Apne kharche jitni katauti rakhiye.")
        tiers = sorted(policy, key=lambda p: -int(p["days_before"]))
        for a, b in zip(tiers, tiers[1:]):
            if float(b["refund_pct"]) > float(a["refund_pct"]):
                notes.append("Paas aane par refund zyada ho raha hai: policy ulti lagti hai, dekh lijiye.")
                break
    return probs, notes


def refund_for(policy: list[dict], days_before: int, paid: float) -> tuple[float, float]:
    """(refund %, refund amount) of what was paid, by HER policy; the tier with the largest days_before <= days left."""
    tiers = sorted(policy or [], key=lambda p: -int(p["days_before"]))
    pct = 0.0
    for p in tiers:
        if days_before >= int(p["days_before"]):
            pct = float(p["refund_pct"])
            break
    return pct, round(max(paid, 0) * pct / 100.0, 2)


def policy_lines(policy: list[dict]) -> list[str]:
    tiers = sorted(policy or [], key=lambda p: -int(p["days_before"]))
    out = []
    for i, p in enumerate(tiers):
        d = int(p["days_before"])
        upper = int(tiers[i - 1]["days_before"]) - 1 if i else None
        span = f"{d}+ din pehle" if upper is None else (f"{d}-{upper} din pehle" if d < upper else f"{d} din pehle")
        if d == 0 and upper is not None:
            span = f"{upper} din se kam" if upper > 0 else "usi din"
        out.append(f"{span}: jama rakam ka {float(p['refund_pct']):g}% wapas")
    return out


def noise_note(hall_kind: str, slot_to: str, music_end: str = "22:00") -> str:
    """Noise Pollution (Regulation and Control) Rules 2000, Rule 5: loudspeaker / public address only with written permission,
    not between 10 pm and 6 am except in closed premises (auditorium, conference room, community / banquet hall); a state may
    allow up to midnight on at most 15 festive days a year; at the boundary of a public place max 10 dB(A) above the area's
    ambient standard or 75 dB(A)."""
    late = slot_to > music_end
    if hall_kind in OPEN_AIR:
        if late:
            return (f"Khuli jagah ({hall_kind}): loudspeaker / DJ {music_end} tak hi (Noise Rules 2000 Rule 5); uske baad sirf state "
                    "ki tyohaar chhoot (saal mein 15 din tak, raat 12 tak) aur likhit permission ke saath. Client ko pehle bataiye.")
        return f"Khuli jagah: loudspeaker ke liye likhit permission; {music_end} ke baad band (Noise Rules 2000 Rule 5)."
    return ("Band hall: raat 10 ke baad ki rok mein band hall ki chhoot hai (Rule 5), par awaaz bahar na jaye; permission / "
            "police ke local niyam dekh lijiye.")


def lock_date(event: date, lock_days: int) -> date:
    return event - timedelta(days=max(0, int(lock_days)))


def stage_due(event: date, booked_on: date, days_before: Any) -> date:
    if days_before is None or days_before == "":
        return booked_on
    d = event - timedelta(days=int(days_before))
    return max(d, booked_on)
