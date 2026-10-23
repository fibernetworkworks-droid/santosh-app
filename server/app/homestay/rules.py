"""Homestay Sahayak rules: money / dates, OTA e-mail and iCal reading (her own pasted mail / exported file, never a login),
nights + rates from HER rate card, cancellation from HER written policy, GST notes, state registration starters, Form C fields,
message templates. Pure functions (no database) so they are easy to test."""
from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from typing import Any

NEVER = (
    "Kisi OTA (Airbnb / Booking.com / MakeMyTrip / Agoda / Goibibo) mein login ya scraping nahi: sirf aapka paste kiya mail ya export ki hui iCal file.",
    "Ek kamra ek raat do baar nahi: double booking code mein mana (OTA mail se aaye tab bhi).",
    "Mehmaan ko koi message / confirmation aapke tap ke bina nahi; refund / cancel / kharcha sirf aapke tap (aur fingerprint) se.",
    "Paisa kabhi khud nahi: advance / balance sirf aapke UPI ID ka link; 'paise mile' sirf aap kahein.",
    "Mehmaan ka Aadhaar / passport / visa number sirf Pehchaan Locker mein ({id:...}); Hoola Form C khud portal par nahi bharta.",
    "Daam, taarikh, mehmaan ka naam ya review kabhi gadhna nahi: jo nahi pata woh [khaali?] rehta hai.",
    "Review maangne ka message sabko ek jaisa (achha-bura dekh kar alag nahi: review gating mana); review ke badle chhoot nahi.",
)

SOURCES = (
    ("Immigration and Foreigners Act 2025 in force 1 Sep 2025; Form-III (earlier Form C) by accommodation providers incl. homestays, "
     "within 24 h of arrival; departure recorded; records kept electronically >= 1 year; Rs 50,000 per case (s.8, Rule 17)",
     "https://nicobartimes.com/?p=22158", "2025-10-14"),
    ("Hotels / homestays risk Rs 50,000 per unreported foreign guest; homestay owners can activate the reporting account by OTP",
     "https://www.heraldgoa.in/?p=457029", "2025-12"),
    ("Form C online filing guide (Goa Govt, FRRO portal indianfrro.gov.in)", "https://www.goa.gov.in/wp-content/uploads/2025/12/ONLINE-FILLING-OF.pdf",
     "2025-12"),
    ("GST 2.0: accommodation up to Rs 7,500 per unit per day 5% without ITC from 22 Sep 2025 (was 12%), ITC reversal",
     "https://taxguru.in/goods-and-service-tax/gst-implication-hotel-industry-due-rate-rationalization-gst-2-0-regime.html", "2025-09-25"),
    ("Above Rs 7,500 per unit per day 18% with ITC; value = per unit per day, not the whole stay; registration above Rs 20 lakh "
     "(Rs 10 lakh special category states)", "https://www.kanakkupillai.com/learn/gst-on-hotel-rooms/", "2026-10-14"),
    ("State homestay rules compared (Kerala, Karnataka, Goa 1-6 rooms; HP Home Stay Rules 2025; Uttarakhand 2026; Rajasthan 2026; "
     "TN, WB, Sikkim) - indicative, state portal decides", "https://www.studiomatrx.org/guides/homestay-registration-and-licensing-india", "2026-10-06"),
    ("Himachal Pradesh Home Stay Rules 2025 (notified 25 Jun 2025: up to 6 rooms / 12 beds, Silver / Gold / Diamond fees Rs 3,000-18,000, "
     "guest register, fire safety)", "https://teamleaseregtech.com/updates/article/43970/himachal-pradesh-home-stay-rules-2025/", "2025-06-26"),
    ("Maharashtra Tourism Bed & Breakfast scheme (registration 5 years, renew 3 months before, police character certificate, "
     "society NOC)", "https://www.professionalutilities.com/bed-and-breakfast-registration/maharashtra.php", "2026"),
    ("Bombay HC (Harmesh Singh Chadha v MCGM, 14 Jun 2022): MTDC B&B registration does not replace the BMC lodging licence (s.394 MMC Act)",
     "https://barandbench.com/news/bed-and-breakfast-facility-registered-with-mtdc-requires-bmc-licence-bombay-high-court", "2022-06-17"),
    ("Goa Homestay and Bed & Breakfast Scheme launched 7 Aug 2025 (hinterland talukas, Rs 2 lakh grant, 5 years)",
     "https://www.theweek.in/wire-updates/national/2025/08/07/bes29-ga-homestay-scheme.html", "2025-08-07"),
)

OTA_WORDS = {
    "airbnb": ("airbnb",),
    "booking": ("booking.com",),
    "mmt": ("makemytrip", "make my trip", "mmt"),
    "goibibo": ("goibibo",),
    "agoda": ("agoda",),
    "expedia": ("expedia",),
    "vrbo": ("vrbo",),
}
SOURCE_LABEL = {"direct": "Seedha", "airbnb": "Airbnb", "booking": "Booking.com", "mmt": "MakeMyTrip", "goibibo": "Goibibo",
                "agoda": "Agoda", "expedia": "Expedia", "vrbo": "Vrbo", "ical": "Calendar file", "block": "Band (khud)", "other": "Doosra"}

MONTHS = {m: i for i, m in enumerate(("jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"), 1)}
MONTHS.update({"january": 1, "february": 2, "march": 3, "april": 4, "june": 6, "july": 7, "august": 8, "september": 9, "sept": 9,
               "october": 10, "november": 11, "december": 12})


# ---------------------------------------------------------------- small helpers
def money(v) -> float:
    if v is None or v == "":
        return 0.0
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).lower().replace(",", "").replace("₹", "").replace("rs.", "").replace("rs", "").replace("inr", "").strip()
    mult = 1.0
    m = re.search(r"(lakh|lac|\bl\b|k\b|hazar|hazaar|thousand)", s)
    if m:
        mult = 100000.0 if m.group(1) in ("lakh", "lac", "l") else 1000.0
    n = re.search(r"-?\d+(?:\.\d+)?", s)
    return round(float(n.group()) * mult, 2) if n else 0.0


def phone10(v) -> str:
    d = re.sub(r"\D", "", str(v or ""))
    if len(d) == 12 and d.startswith("91"):
        d = d[2:]
    if len(d) == 11 and d.startswith("0"):
        d = d[1:]
    return d if len(d) == 10 and d[0] in "6789" else ""


def phone_any(v) -> str:
    """Indian 10 digits, else an international number with + (foreign guests), else ''."""
    p = phone10(v)
    if p:
        return p
    s = str(v or "").strip()
    d = re.sub(r"\D", "", s)
    return "+" + d if s.startswith("+") and 8 <= len(d) <= 15 else ""


def parse_date(v, today: date | None = None) -> date | None:
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    if not v:
        return None
    s = str(v).strip()
    for f in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%d.%m.%Y", "%d-%m-%y", "%d/%m/%y", "%Y%m%d"):
        try:
            return datetime.strptime(s[:10] if f != "%Y%m%d" else s[:8], f).date()
        except ValueError:
            pass
    found = find_dates(s, today)
    return found[0][1] if found else None


def scrub(text: str, n: int = 2000) -> str:
    """Free text: OTP / PIN / password values, card-like runs, Aadhaar-like 12 digits, PAN, passport-like numbers are never kept."""
    t = str(text or "")
    t = re.sub(r"\b(otp|pin|cvv|password|upi pin|mpin)\b\s*(?:is|hai|:|=)?\s*\S+", lambda m: f"{m.group(1)} [hataya]", t, flags=re.I)
    t = re.sub(r"\b(?:\d[ -]?){13,19}\b", "[hataya]", t)
    t = re.sub(r"\b\d{4}\s?\d{4}\s?\d{4}\b", "[ID hataya]", t)
    t = re.sub(r"\b[A-Z]{5}\d{4}[A-Z]\b", "[PAN hataya]", t)
    t = re.sub(r"(passport|visa)\s*(?:no\.?|number|#)?\s*[:\-]?\s*[A-Z0-9]{6,12}\b", lambda m: f"{m.group(1)} [locker mein]", t, flags=re.I)
    return t.strip()[:n]


BLANK = re.compile(r"\[[^\]\n]{1,40}\?\]")


def blanks(text: str) -> list[str]:
    return BLANK.findall(text or "")


def guess_source(text: str) -> str:
    t = (text or "").lower()
    for k, words in OTA_WORDS.items():
        if any(w in t for w in words):
            return k
    return ""


# ---------------------------------------------------------------- dates inside free text (OTA mails)
_DATE_PATTERNS = (
    re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b"),                                                          # 2026-11-14
    re.compile(r"\b(\d{1,2})[/.-](\d{1,2})[/.-](\d{2,4})\b"),                                              # 14/11/2026
    re.compile(r"\b(\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-z]{3,9})\.?,?\s+(\d{4})\b"),                        # 14 Nov 2026
    re.compile(r"\b([A-Za-z]{3,9})\.?\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(\d{4})\b"),                        # Nov 14, 2026
    re.compile(r"\b(\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-z]{3,9})\b(?!\s*\d)"),                               # 14 Nov (no year)
)


def find_dates(text: str, today: date | None = None) -> list[tuple[int, date]]:
    """(position, date) of every date written in the text, in order."""
    out: list[tuple[int, date]] = []
    taken: list[tuple[int, int]] = []
    t = text or ""
    for i, pat in enumerate(_DATE_PATTERNS):
        for m in pat.finditer(t):
            if any(a <= m.start() < b for a, b in taken):
                continue
            d = None
            try:
                g = m.groups()
                if i == 0:
                    d = date(int(g[0]), int(g[1]), int(g[2]))
                elif i == 1:
                    y = int(g[2]) + (2000 if len(g[2]) == 2 else 0)
                    d = date(y, int(g[1]), int(g[0]))
                elif i == 2:
                    mo = MONTHS.get(g[1].lower())
                    d = date(int(g[2]), mo, int(g[0])) if mo else None
                elif i == 3:
                    mo = MONTHS.get(g[0].lower())
                    d = date(int(g[2]), mo, int(g[1])) if mo else None
                else:
                    mo = MONTHS.get(g[1].lower())
                    if mo and today:
                        d = date(today.year, mo, int(g[0]))
                        if d < today - timedelta(days=60):
                            d = date(today.year + 1, mo, int(g[0]))
            except ValueError:
                d = None
            if d:
                out.append((m.start(), d))
                taken.append((m.start(), m.end()))
    return sorted(out)


def _labelled(text: str, labels: tuple[str, ...], dates: list[tuple[int, date]]) -> date | None:
    low = (text or "").lower()
    best = None
    for lab in labels:
        for m in re.finditer(lab, low):
            after = [d for p, d in dates if 0 <= p - m.end() <= 80]
            if after:
                cand = after[0]
                if best is None:
                    best = cand
                break
        if best:
            return best
    return best


def parse_ota_email(text: str, today: date | None = None) -> dict[str, Any]:
    """Read HER pasted OTA mail (data, never instructions). Returns what was found + what is missing; nothing is guessed."""
    t = str(text or "")[:20000]
    low = t.lower()
    src = guess_source(t)
    dates = find_dates(t, today)
    ci = _labelled(t, (r"check[\s-]*in", r"arrival", r"arriving", r"from\b"), dates)
    co = _labelled(t, (r"check[\s-]*out", r"departure", r"departing", r"until\b", r"\bto\b"), dates)
    if not (ci and co and co > ci):
        seq = [d for _, d in dates]
        pair = next(((a, b) for a, b in zip(seq, seq[1:]) if 0 < (b - a).days <= 60), None)
        if pair:
            ci, co = pair
    ref = ""
    for pat in (r"\b(HM[A-Z0-9]{8})\b", r"(?:booking|reservation|confirmation)\s*(?:id|no\.?|number|code|#)\s*[:#]?\s*([A-Z0-9][A-Z0-9-]{4,24})",
                r"\b(NH\d{6,})\b"):
        m = re.search(pat, t, re.I)
        if m:
            ref = m.group(1).strip().upper()
            break
    if not src and re.fullmatch(r"HM[A-Z0-9]{8}", ref):
        src = "airbnb"                                   # Airbnb confirmation codes start with HM
    adults = 0
    m = (re.search(r"(?<!\d)(\d{1,2})[ \t]*(?:adults?|bade)\b", low)
         or re.search(r"(?<!\d)(\d{1,2})[ \t]*(?:guests?|mehmaan|log|persons?|people)\b", low))
    if m:
        adults = int(m.group(1))
    children = 0
    m = re.search(r"(?<!\d)(\d{1,2})[ \t]*(?:child|children|kids?|bachche)\b", low)
    if m:
        children = int(m.group(1))
        if "guest" in low[max(0, m.start() - 40):m.start()] and adults >= children:
            pass
    name = ""
    for pat, fl in ((r"(?:guest name|booked by|booker|name of guest|lead guest|guest)[ \t]*[:\-][ \t]*([A-Za-z][A-Za-z .'-]{1,60})", re.I),
                    (r"\b([A-Z][a-z]+(?: [A-Z][a-z]+)?)'s (?:reservation|booking|trip)", 0),
                    (r"(?i:new (?:booking|reservation) (?:from|by)) ([A-Z][a-z]+(?: [A-Z][a-z]+){0,2})", 0),
                    (r"(?i:confirmed)\s*[-–:]\s*([A-Z][a-z]+(?: [A-Z][a-z]+){0,2}) (?i:arrives)", 0)):
        m = re.search(pat, t, fl)
        if m:
            name = re.split(r"\s{2,}|\n", m.group(1).strip())[0].strip(" .-")[:60]
            break
    amount = 0.0
    m = re.search(r"(?:total payout|you(?:'ll)? earn|payout|net amount|amount payable|total price|total amount|total)\D{0,25}"
                  r"(?:₹|rs\.?|inr)\s*([\d,]+(?:\.\d+)?)", t, re.I)
    if m:
        amount = money(m.group(1))
    phone = ""
    m = re.search(r"(?:\+91[\s-]?)?\b[6-9]\d{4}[\s-]?\d{5}\b", t)
    if m:
        phone = phone10(m.group())
    cancelled = bool(re.search(r"\b(cancell?ed|cancel ho gay[ia])\b", low)) and not re.search(r"\bnot cancell?ed\b", low)
    missing = [k for k, v in (("check_in", ci), ("check_out", co)) if not v]
    return {"source": src or "other", "ref": ref, "check_in": ci.isoformat() if ci else "", "check_out": co.isoformat() if co else "",
            "adults": adults, "children": children, "guest_name": name, "amount": amount, "phone": phone, "cancelled": cancelled,
            "missing": missing}


# ---------------------------------------------------------------- iCal (.ics) export she gives
def _ics_date(v: str) -> date | None:
    v = (v or "").strip()
    m = re.match(r"(\d{4})(\d{2})(\d{2})", v)
    if not m:
        return None
    try:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
        return None


def parse_ics(text: str) -> dict[str, Any]:
    """Events of an exported calendar (Airbnb / Booking.com / MMT / Google iCal). DTEND of an all-day event is the check-out day."""
    raw = str(text or "")[:2_000_000].replace("\r\n", "\n").replace("\r", "\n")
    lines: list[str] = []
    for ln in raw.split("\n"):
        if ln[:1] in (" ", "\t") and lines:
            lines[-1] += ln[1:]
        else:
            lines.append(ln)
    prodid = next((ln.split(":", 1)[1] for ln in lines if ln.upper().startswith("PRODID")), "")
    events, cur = [], None
    for ln in lines:
        u = ln.upper()
        if u.startswith("BEGIN:VEVENT"):
            cur = {}
        elif u.startswith("END:VEVENT"):
            if cur is not None:
                events.append(cur)
            cur = None
        elif cur is not None and ":" in ln:
            k, v = ln.split(":", 1)
            key = k.split(";", 1)[0].upper()
            if key in ("DTSTART", "DTEND", "SUMMARY", "UID", "DESCRIPTION", "STATUS"):
                cur[key] = v.replace("\\n", "\n").replace("\\,", ",").strip()
    out = []
    for e in events[:2000]:
        ci, co = _ics_date(e.get("DTSTART", "")), _ics_date(e.get("DTEND", ""))
        if not ci:
            continue
        if not co or co <= ci:
            co = ci + timedelta(days=1)
        if (e.get("STATUS") or "").upper() == "CANCELLED":
            continue
        summ = scrub(e.get("SUMMARY", ""), 120)
        desc = e.get("DESCRIPTION", "")
        ref = ""
        m = re.search(r"\b(HM[A-Z0-9]{8})\b", desc + " " + summ)
        if m:
            ref = m.group(1)
        out.append({"uid": (e.get("UID") or f"{ci}-{co}-{summ}")[:200], "check_in": ci.isoformat(), "check_out": co.isoformat(),
                    "summary": summ, "ref": ref,
                    "reserved": bool(re.search(r"reserv|booked|booking|guest", summ, re.I)) or bool(ref)})
    return {"source": guess_source(prodid + " " + " ".join(e.get("summary", "") for e in out[:5])) or "", "events": out,
            "prodid": prodid[:120]}


# ---------------------------------------------------------------- nights, rates, money
def nights(ci: date, co: date) -> list[date]:
    return [ci + timedelta(days=i) for i in range((co - ci).days)]


def overlaps(a_in: date, a_out: date, b_in: date, b_out: date) -> bool:
    return a_in < b_out and b_in < a_out


def night_rate(room: dict, d: date) -> float:
    """HER rate for this room on this night (Fri / Sat night = weekend rate when she gave one; her special dates win)."""
    special = (room.get("special") or {}).get(d.isoformat())
    if special:
        return float(special)
    if d.weekday() in (4, 5) and float(room.get("weekend_rate") or 0) > 0:
        return float(room["weekend_rate"])
    return float(room.get("base_rate") or 0)


def gst_rate(per_unit_day: float) -> int:
    """GST 2.0 (22 Sep 2025): accommodation <= Rs 7,500 per unit per day 5% (no ITC), above 18%."""
    return 5 if per_unit_day <= 7500 else 18


def quote(rooms: list[dict], ci: date, co: date, adults: int, children: int, addons: list[dict], menu: dict[str, Any],
          gstin: str = "", count_children: bool = False) -> dict[str, Any]:
    """Lines from HER rate card + menu only. Anything she hasn't priced = missing (never guessed)."""
    lines, missing, warns = [], [], []
    ns = nights(ci, co)
    if not ns:
        return {"lines": [], "missing": ["taarikh"], "total": 0.0, "nights": 0, "gst": [], "warnings": []}
    cap = sum(int(r.get("max_guests") or 0) for r in rooms)
    people = int(adults or 0) + int(children or 0)
    if cap and people > cap:
        warns.append(f"{people} log, kamron mein {cap} tak ki jagah.")
    base = sum(int(r.get("base_guests") or 2) for r in rooms)
    extra = max(0, int(adults or 0) + (int(children or 0) if count_children else 0) - base)
    tax_lines = []
    for r in rooms:
        for d in ns:
            rate = night_rate(r, d)
            if rate <= 0:
                missing.append(f"{r.get('name') or r.get('number')} ka {d.isoformat()} ka daam")
                continue
            lines.append({"kind": "room", "item": f"{r.get('name') or r.get('number')} · {d.strftime('%d %b')}", "qty": 1, "rate": rate,
                          "amount": rate, "room": r.get("number"), "night": d.isoformat()})
            if gstin:
                g = gst_rate(rate)
                tax_lines.append({"base": rate, "pct": g, "tax": round(rate * g / 100, 2), "what": "room"})
    if extra:
        xr = max(float(r.get("extra_person") or 0) for r in rooms) if rooms else 0.0
        if xr <= 0:
            missing.append("extra bed / extra mehmaan ka daam")
        else:
            amt = round(xr * extra * len(ns), 2)
            lines.append({"kind": "extra", "item": f"Extra mehmaan x{extra} x {len(ns)} raat", "qty": extra * len(ns), "rate": xr,
                          "amount": amt})
            if gstin:
                g = gst_rate((sum(night_rate(r, ns[0]) for r in rooms) / max(1, len(rooms))) + xr)
                tax_lines.append({"base": amt, "pct": g, "tax": round(amt * g / 100, 2), "what": "extra"})
    for a in addons or []:
        item = str(a.get("item") or "").strip().lower()
        if not item:
            continue
        price = (menu or {}).get(item)
        qty = float(a.get("qty") or 0)
        if qty <= 0:
            per = str(a.get("per") or (menu or {}).get(f"{item}__per") or "person_day")
            qty = float(people * len(ns)) if per == "person_day" else (float(len(ns)) if per == "day" else 1.0)
        if price is None or float(price) <= 0:
            missing.append(f"{item} ka daam (menu mein nahi)")
            continue
        amt = round(float(price) * qty, 2)
        lines.append({"kind": "addon", "item": item, "qty": qty, "rate": float(price), "amount": amt})
        if gstin:
            tax_lines.append({"base": amt, "pct": 5, "tax": round(amt * 0.05, 2), "what": "food / add-on (5% maana; CA se pakka)"})
    sub = round(sum(x["amount"] for x in lines), 2)
    tax = round(sum(x["tax"] for x in tax_lines), 2)
    return {"lines": lines, "subtotal": sub, "gst": tax_lines, "tax": tax, "total": round(sub + tax, 2), "nights": len(ns),
            "missing": missing, "warnings": warns}


def gst_note(gstin: str, max_rate: float, ota: bool) -> str:
    if not gstin:
        s = ("GST registration nahi: bill par GST nahi lagaya. Saal ka turnover Rs 20 lakh (special category states Rs 10 lakh) "
             "paar ho to registration chahiye.")
        if ota:
            s += " OTA se aayi booking par GST aam taur par OTA (e-commerce operator, s.9(5)) bharta hai jab aap registration ke layak nahi - CA se pakka."
        return s
    r = gst_rate(max_rate) if max_rate else 5
    return (f"Kamra {r}% GST (har kamra har raat {'Rs 7,500 tak 5%, bina ITC' if r == 5 else 'Rs 7,500 se upar 18%, ITC ke saath'}; "
            "GST 2.0, 22 Sep 2025). Khaana / add-on 5% maana - CA se pakka.")


def refund_for(policy: list[dict], paid: float, ci: date, on: date) -> dict[str, Any]:
    """HER written policy: tiers [{days: 7, pct: 100}, {days: 2, pct: 50}, {days: 0, pct: 0}] = cancel at least N days before
    check-in -> pct of what was paid comes back. No policy = she decides the amount."""
    tiers = sorted([t for t in (policy or []) if isinstance(t, dict)], key=lambda t: -int(t.get("days") or 0))
    days = (ci - on).days
    if not tiers:
        return {"days_before": days, "pct": None, "refund": None, "why": "Aapki cancellation policy likhi nahi: wapas kitna, aap batayiye."}
    for t in tiers:
        if days >= int(t.get("days") or 0):
            pct = max(0.0, min(100.0, float(t.get("pct") or 0)))
            return {"days_before": days, "pct": pct, "refund": round(paid * pct / 100, 2),
                    "why": f"Check-in se {days} din pehle: aapki policy {pct:g}% wapas."}
    return {"days_before": days, "pct": 0.0, "refund": 0.0, "why": f"Check-in se {days} din pehle: policy mein wapsi nahi."}


def policy_text(policy: list[dict]) -> str:
    tiers = sorted([t for t in (policy or []) if isinstance(t, dict)], key=lambda t: -int(t.get("days") or 0))
    if not tiers:
        return ""
    parts = [f"{int(t.get('days') or 0)}+ din pehle cancel: {float(t.get('pct') or 0):g}% wapas" for t in tiers]
    return "Cancellation: " + "; ".join(parts) + "."


def parse_policy(text: str) -> list[dict]:
    """'7 din pehle 100%, 2 din pehle 50%, uske baad kuch nahi' -> tiers."""
    out = []
    for m in re.finditer(r"(\d{1,3})\s*(?:din|days?)[^\d%]{0,25}?(\d{1,3})\s*%", str(text or ""), re.I):
        out.append({"days": int(m.group(1)), "pct": min(100, int(m.group(2)))})
    if re.search(r"(baad|after|uske baad|within)[^.]{0,30}(kuch nahi|no refund|non.?refundable|0\s*%)", str(text or ""), re.I):
        out.append({"days": 0, "pct": 0})
    seen, res = set(), []
    for t in sorted(out, key=lambda t: -t["days"]):
        if t["days"] not in seen:
            seen.add(t["days"])
            res.append(t)
    return res


def upi_link(vpa: str, name: str, amount: float, note: str) -> str:
    from urllib.parse import quote as q
    if not vpa or amount <= 0:
        return ""
    return f"upi://pay?pa={q(vpa)}&pn={q(name or '')}&am={amount:.2f}&cu=INR&tn={q(note[:60])}"


# ---------------------------------------------------------------- Form C (Form-III) for foreign guests
FORM_C_FIELDS = (
    ("name", "Poora naam (passport jaisa)"), ("nationality", "Nationality"), ("gender", "Gender"), ("dob", "Janam taarikh"),
    ("passport_ref", "Passport number (Pehchaan Locker)"), ("passport_place", "Passport kahan bana"), ("passport_issue", "Passport issue date"),
    ("passport_expiry", "Passport expiry"), ("visa_ref", "Visa / e-Visa number (Locker)"), ("visa_type", "Visa type"),
    ("visa_expiry", "Visa expiry"), ("india_arrival", "Bharat mein aane ki taarikh"), ("arrived_from", "Kahan se aaye (city / desh)"),
    ("next_destination", "Aage kahan jayenge"), ("purpose", "Aane ka maksad"), ("address_abroad", "Videsh ka pata"),
    ("contact_india", "Bharat mein phone"),
)


def form_c_missing(g: dict) -> list[str]:
    return [label for k, label in FORM_C_FIELDS if not str(g.get(k) or "").strip()]


# ---------------------------------------------------------------- state registration starters (her state portal decides)
COMMON_ITEMS = (
    ("tourism", "Rajya tourism vibhag mein homestay / B&B registration", True),
    ("local", "Gram panchayat / nagar palika / municipal lodging ya trade licence (Mumbai: BMC licence alag, Bombay HC 2022)", True),
    ("fire", "Fire safety: extinguisher + bahar nikalne ka raasta; kuch rajyon mein fire NOC (Goa mein hamesha)", True),
    ("police", "Police station: guest register / jaankari (rajya / thane ka niyam)", True),
    ("frro", "Videshi mehmaan aate hain to indianfrro.gov.in par Form C (Form-III) account", False),
    ("fssai", "Khaana dete hain to FSSAI basic registration (1 Apr 2026 se Rs 1.5 crore turnover tak registration)", False),
    ("gst", "GST registration jab turnover Rs 20 lakh (special category Rs 10 lakh) se upar", False),
    ("society", "Society / padosi NOC (flat ya society mein ho to)", False),
    ("insurance", "Ghar / mehmaan ka insurance (sujhav)", False),
)

STATES: dict[str, dict[str, Any]] = {
    "MH": {"scheme": "Maharashtra Tourism Bed & Breakfast scheme (Dept of Tourism)", "rooms": "4-10 beds (starter)", "validity_years": 5,
           "renew_before_days": 90, "notes": ["Police station se character certificate", "Society NOC", "Mumbai: BMC lodging licence alag"]},
    "GA": {"scheme": "Goa Homestay & Bed and Breakfast Scheme 2025 + Goa tourist trade registration", "rooms": "1-6 kamre (starter)",
           "validity_years": 5, "renew_before_days": 60, "notes": ["Fire NOC aur society NOC zaroori (starter)"]},
    "KL": {"scheme": "Kerala Tourism homestay classification (Diamond / Gold / Silver)", "rooms": "1-6 kamre, malik ghar mein",
           "validity_years": 3, "renew_before_days": 60, "notes": []},
    "KA": {"scheme": "Karnataka homestay registration", "rooms": "1-6 kamre, malik ghar mein", "validity_years": 0, "renew_before_days": 60,
           "notes": ["Fees / validity apne district tourism office se pakka kijiye"]},
    "HP": {"scheme": "Himachal Pradesh Home Stay Rules 2025", "rooms": "6 kamre / 12 bed tak", "validity_years": 0, "renew_before_days": 60,
           "notes": ["Silver / Gold / Diamond, fees area ke hisaab se Rs 3,000-18,000", "Guest register", "Fire safety + emergency exit"]},
    "UK": {"scheme": "Uttarakhand homestay registration rules 2026", "rooms": "8 kamre / 24 bed tak (starter)", "validity_years": 5,
           "renew_before_days": 60, "notes": ["Malik wahi rehta ho (permanent resident)"]},
    "RJ": {"scheme": "Rajasthan Homestay / PG House scheme 2026 (single window)", "rooms": "8 kamre / 24 bed tak (starter)",
           "validity_years": 2, "renew_before_days": 60, "notes": []},
    "TN": {"scheme": "Tamil Nadu homestay (Silver / Gold)", "rooms": "1-3 kamre / 6 bed (starter)", "validity_years": 0,
           "renew_before_days": 60, "notes": []},
    "WB": {"scheme": "West Bengal Homestay Policy 2026", "rooms": "1-8 kamre / 16 bed (starter)", "validity_years": 0,
           "renew_before_days": 60, "notes": []},
    "SK": {"scheme": "Sikkim homestay registration", "rooms": "5 kamre tak (starter)", "validity_years": 3, "renew_before_days": 60, "notes": []},
}


def registration_items(state: str, foreign: bool, food: bool, flat: bool) -> list[dict[str, Any]]:
    st = STATES.get((state or "").upper(), {})
    items = []
    for key, text, always in COMMON_ITEMS:
        if key == "frro" and not foreign:
            continue
        if key == "fssai" and not food:
            continue
        if key == "society" and not flat:
            continue
        if key == "tourism" and st:
            text = f"{st['scheme']} ({st['rooms']})"
        items.append({"id": key, "text": text, "must": bool(always or key in ("frro", "fssai"))})
    return items


def state_info(state: str) -> dict[str, Any]:
    st = STATES.get((state or "").upper())
    if not st:
        return {"state": state, "scheme": "", "note": "Is rajya ka starter nahi: apne rajya ke tourism portal se scheme / fees / validity pakki kijiye."}
    return {"state": state.upper(), **st, "note": "Starter jaankari (Oct 2026): rajya ka portal hi aakhri sach."}


# ---------------------------------------------------------------- message templates (facts only, blanks stay as [..?])
def _f(facts: dict, k: str, blank: str) -> str:
    v = str(facts.get(k) or "").strip()
    return v or f"[{blank}?]"


def message_text(kind: str, f: dict[str, Any]) -> str:
    g = _f(f, "guest", "naam")
    biz = _f(f, "business", "homestay ka naam")
    dates = f"{_f(f, 'check_in', 'check-in')} se {_f(f, 'check_out', 'check-out')}"
    if kind == "confirmation":
        lines = [f"Namaste {g} ji,", f"{biz} mein aapki booking {f.get('number', '')} pakki: {dates} ({f.get('nights', '')} raat), "
                 f"{f.get('rooms_text', '')}, {f.get('people', '')} log.",
                 f"Kul: {_f(f, 'total_text', 'kul daam')}. Advance: {f.get('advance_text') or 'koi nahi'}; baaki aate waqt.",
                 f"Check-in {_f(f, 'checkin_time', 'check-in samay')}, check-out {_f(f, 'checkout_time', 'check-out samay')}."]
        if f.get("policy"):
            lines.append(f["policy"])
        if f.get("pay_link"):
            lines.append(f"Advance UPI se: {f['pay_link']}")
        lines.append("Hum kabhi OTP / PIN nahi maangte. Dhanyavaad!")
        return "\n".join(lines)
    if kind == "checkin_info":
        lines = [f"Namaste {g} ji, {biz} mein aapka swagat {_f(f, 'check_in', 'check-in')} ko.",
                 f"Pata: {_f(f, 'address', 'pata')}" + (f" (map: {f['map']})" if f.get("map") else ""),
                 f"Check-in {_f(f, 'checkin_time', 'check-in samay')} ke baad. Phone: {_f(f, 'host_phone', 'aapka phone')}."]
        if f.get("instructions"):
            lines.append(str(f["instructions"]))
        lines.append("Aate waqt sabka photo ID saath laaiye (videshi mehmaan: passport aur visa).")
        return "\n".join(lines)
    if kind == "house_rules":
        return f"Namaste {g} ji, {biz} ke ghar ke niyam:\n{_f(f, 'house_rules', 'ghar ke niyam')}\nDhanyavaad!"
    if kind == "payment":
        return (f"Namaste {g} ji, booking {f.get('number', '')} ({dates}) ke liye {_f(f, 'amount_text', 'raqam')} baaki. "
                f"UPI: {_f(f, 'pay_link', 'UPI link')}\nHum kabhi OTP / PIN nahi maangte.")
    if kind == "review":
        lines = [f"Namaste {g} ji, {biz} mein rukne ke liye dhanyavaad!"]
        if f.get("review_link"):
            lines.append(f"Aapka anubhav jaisa bhi raha, ek imaandaar review likhenge to bahut madad hogi: {f['review_link']}")
        elif f.get("ota"):
            lines.append(f"Aapka anubhav jaisa bhi raha, {f['ota']} par ek imaandaar review likhenge to bahut madad hogi.")
        else:
            lines.append("Aapka anubhav jaisa bhi raha, [review link?] par ek imaandaar review likhenge to bahut madad hogi.")
        return "\n".join(lines)
    if kind == "cancellation":
        s = f"Namaste {g} ji, booking {f.get('number', '')} ({dates}) radd ho gayi."
        if f.get("refund_text"):
            s += f" Wapas: {f['refund_text']} (aapke account mein bheja jaayega)."
        return s
    return f"Namaste {g} ji,\n{_f(f, 'text', 'message')}"
