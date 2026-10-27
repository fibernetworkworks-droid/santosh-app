"""Pure rules of the Front Office Sahayak (hotel / lodge / guest house front desk). No database here.

GST slabs, night-wise rates, availability arithmetic, OTA confirmation-mail / sheet parsing, cancellation policy, Form C (Form III)
deadlines, occupancy / ADR / RevPAR, scrub. Every number about money is HER number; nothing here invents a price or a date."""
from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from typing import Any

# ---------------------------------------------------------------- sources (checked 23 Oct 2026)
SOURCES = [
    ("GST on hotel rooms: up to Rs 7,500 per unit per day 5% without ITC, above 18% with ITC, from 22 Sep 2025; SAC 996311; "
     "value per room per day after discount", "https://themunim.com/blog/gst-on-hotel-rooms/", "Aug 2026"),
    ("GST 2.0 hotel FAQs (56th Council: 12% -> 5% for rooms <= Rs 7,500, no ITC)",
     "https://hnallp.com/assets/articles/d8cae-gst2.0_faqs_hospitlaityindustry_ss_rm_21.09.2025_final-1.pdf", "21 Sep 2025"),
    ("Restaurant in 'specified premises' (any room > Rs 7,500 a day in the previous FY) 18% with ITC from 1 Apr 2025, else 5% no ITC",
     "https://busy.in/gst-rates/hotel-industry/", "2026"),
    ("Immigration and Foreigners Act 2025 in force 1 Sep 2025: s.8 accommodation keeper reports foreign guests; Rules 2025 r.17: "
     "Form III (C-Form) on e-FRRO within 24 h of arrival and of departure, records 1 year, s.23(b) penalty",
     "https://nriinformation.com/visa-oci/c-form-hosting-foreign-guest-india", "2026"),
    ("e-FRRO Form C online filling steps for hotels (Goa)", "https://www.goa.gov.in/wp-content/uploads/2025/12/ONLINE-FILLING-OF.pdf",
     "Dec 2025"),
    ("Accommodation providers directed to report foreign arrivals within 24 hours (district police directive)",
     "https://nenow.in/north-east-news/nagaland/nagaland-accommodation-providers-directed-to-report-foreign-arrivals-within-24-hours.html",
     "2026"),
    ("Consumer Protection (E-Commerce) Rules 2020 + CCPA dark-pattern guidelines 2023: cancellation / refund terms shown upfront, no "
     "hidden charges", "https://www.indialaw.in/blog/civil/consumer-protection-e-commerce-rules-2020/", "2020 / 2023"),
    ("DPDP Act 2023 + Rules 2025 (notified 13-14 Nov 2025, phased to May 2027): guest data only for the stay, erase when no longer "
     "needed unless a law asks to keep it", "https://www.dpdpa.com/", "Nov 2025"),
]

NEVER = (
    "Kisi raat ka room do logon ko dena (overbooking code mein mana hai)",
    "Guest ka Aadhaar / passport number seedha rakhna (sirf Pehchaan Locker ka {id:...})",
    "Guest ko confirmation / koi message aapke tap ke bina bhejna",
    "Refund, discount, complimentary, cancellation charge ya bill final aapki haan ke bina",
    "Paise lena / dena (UPI link sirf aapke UPI ID ka; guest apne app se deta hai)",
    "OTA extranet / channel manager mein login karna ya scrape karna (sirf aapka paste kiya mail / sheet)",
    "Form C khud submit karna (indianfrro.gov.in par aap submit karti hain; Hoola data taiyaar karta hai)",
    "Rate, availability, review ya tareekh apne aap gadhna",
)

ROOM_STATUS = ("dirty", "clean", "inspected", "out_of_order")
ROOM_STATUS_LABEL = {"dirty": "Ganda", "clean": "Saaf", "inspected": "Jaancha hua", "out_of_order": "Kharab / band"}
SOURCES_OTA = ("makemytrip", "goibibo", "booking", "agoda", "airbnb", "expedia", "cleartrip", "easemytrip", "yatra")
SOURCE_LABEL = {"walk_in": "Walk-in", "phone": "Phone", "whatsapp": "WhatsApp", "direct": "Direct", "agent": "Agent",
                "makemytrip": "MakeMyTrip", "goibibo": "Goibibo", "booking": "Booking.com", "agoda": "Agoda", "airbnb": "Airbnb",
                "expedia": "Expedia", "cleartrip": "Cleartrip", "easemytrip": "EaseMyTrip", "yatra": "Yatra", "other": "Other"}
EXTRA_KINDS = ("food", "restaurant", "room_service", "laundry", "extra_bed", "minibar", "transport", "late_checkout", "early_checkin",
               "other")
MEAL_PLANS = ("EP", "CP", "MAP", "AP")
ROOM_GST_LIMIT = 7500.0


# ---------------------------------------------------------------- small helpers
def money(v: Any) -> float:
    if v is None:
        return 0.0
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).lower().replace(",", "").replace("₹", "").replace("rs.", "").replace("rs", "").replace("inr", "").strip()
    m = re.search(r"(-?\d+(?:\.\d+)?)\s*(k|lakh|lac|l|cr|crore)?\b", s)
    if not m:
        return 0.0
    n = float(m.group(1))
    u = m.group(2) or ""
    return n * {"k": 1e3, "lakh": 1e5, "lac": 1e5, "l": 1e5, "cr": 1e7, "crore": 1e7}.get(u, 1)


def phone10(v: Any) -> str:
    d = re.sub(r"\D", "", str(v or ""))
    if len(d) == 12 and d.startswith("91"):
        d = d[2:]
    if len(d) == 11 and d.startswith("0"):
        d = d[1:]
    return d if re.fullmatch(r"[6-9]\d{9}", d) else ""


_SECRETS = [
    (re.compile(r"(?i)\b(otp|pin|cvv|mpin|password|passcode)\b\s*[:=-]?\s*\S+"), r"\1 [hataya]"),
    (re.compile(r"(?<!\d)(?:\d[ -]?){13,19}(?!\d)"), "[card hataya]"),
    (re.compile(r"(?<!\d)[2-9]\d{3}[ -]?\d{4}[ -]?\d{4}(?!\d)"), "[ID hataya]"),
    (re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b"), "[PAN hataya]"),
    (re.compile(r"\b[A-PR-WY][1-9]\d\s?\d{4}[1-9]\b"), "[passport hataya]"),
]


def scrub(text: Any, n: int = 500) -> str:
    """Free text kept by the front desk: OTP / PIN / card / Aadhaar / PAN / passport numbers removed."""
    t = str(text or "")
    for rx, rep in _SECRETS:
        t = rx.sub(rep, t)
    return re.sub(r"[ \t]+", " ", t).strip()[:n]


_MON = {m: i + 1 for i, m in enumerate(("jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"))}


def parse_date(v: Any, today: date | None = None) -> date | None:
    """2026-10-24 / 24-10-2026 / 24/10/26 / 24 Oct 2026 / Fri, 24 Oct 2026 / Oct 24, 2026 / aaj / kal / parso."""
    if v is None or v == "":
        return None
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    s = str(v).strip().lower()
    td = today or date.today()
    if s in ("aaj", "today", "aj"):
        return td
    if s in ("kal", "tomorrow"):
        return td + timedelta(days=1)
    if s in ("parso", "parson"):
        return td + timedelta(days=2)
    m = re.search(r"(\d{4})-(\d{1,2})-(\d{1,2})", s)
    try:
        if m:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        m = re.search(r"(\d{1,2})[/.-](\d{1,2})[/.-](\d{2,4})", s)
        if m:
            y = int(m.group(3))
            y = y + 2000 if y < 100 else y
            return date(y, int(m.group(2)), int(m.group(1)))
        m = re.search(r"(\d{1,2})(?:st|nd|rd|th)?\s+([a-z]{3})[a-z]*[,]?\s+(\d{4})", s)
        if m and m.group(2) in _MON:
            return date(int(m.group(3)), _MON[m.group(2)], int(m.group(1)))
        m = re.search(r"([a-z]{3})[a-z]*\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(\d{4})", s)
        if m and m.group(1) in _MON:
            return date(int(m.group(3)), _MON[m.group(1)], int(m.group(2)))
    except ValueError:
        return None
    return None


def nights(arrive: date, depart: date) -> list[date]:
    return [arrive + timedelta(days=i) for i in range((depart - arrive).days)]


def fy_of(d: date) -> str:
    y = d.year if d.month >= 4 else d.year - 1
    return f"{y % 100:02d}{(y + 1) % 100:02d}"


# ---------------------------------------------------------------- rates
def _mmdd(s: str) -> str:
    s = str(s or "").strip()
    m = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", s)
    if m:
        return s
    m = re.fullmatch(r"(\d{1,2})[-/](\d{1,2})", s)
    return f"{int(m.group(2)):02d}-{int(m.group(1)):02d}" if m else ""


def season_hit(seasons: list[dict], d: date) -> dict | None:
    """Seasons: [{name, from, to, rate}] where from/to are YYYY-MM-DD (one year) or DD-MM (every year; may cross new year)."""
    for se in seasons or []:
        f, t = str(se.get("from") or ""), str(se.get("to") or "")
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", f) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", t):
            if f <= d.isoformat() <= t:
                return se
            continue
        a, b = _mmdd(f), _mmdd(t)
        if not a or not b:
            continue
        x = d.strftime("%m-%d")
        if (a <= b and a <= x <= b) or (a > b and (x >= a or x <= b)):
            return se
    return None


def night_rate(plan: dict, d: date, weekend_days: list[int]) -> tuple[float | None, str]:
    """Her rate for one night: season > weekend > base. None = she never gave a rate (a blank, never a guess)."""
    se = season_hit(plan.get("seasons") or [], d)
    if se and money(se.get("rate")) > 0:
        return money(se.get("rate")), f"season {se.get('name') or ''}".strip()
    if d.weekday() in (weekend_days or []) and money(plan.get("weekend")) > 0:
        return money(plan.get("weekend")), "weekend"
    if money(plan.get("base")) > 0:
        return money(plan.get("base")), "base"
    return None, "rate nahi"


def room_gst_pct(per_night_value: float) -> int:
    """GST 2.0 (from 22 Sep 2025): value per unit per day <= 7,500 -> 5% (no ITC), above -> 18%."""
    return 5 if per_night_value <= ROOM_GST_LIMIT else 18


def extra_gst_pct(kind: str, specified_premises: bool, her_pct: dict | None = None) -> int:
    her = her_pct or {}
    if kind in her and str(her[kind]).strip() != "":
        try:
            return int(float(her[kind]))
        except (TypeError, ValueError):
            pass
    if kind in ("food", "restaurant", "room_service", "minibar"):
        return 18 if specified_premises else 5
    if kind in ("extra_bed", "late_checkout", "early_checkin"):
        return -1          # part of the room's value per day (room slab)
    if kind == "transport":
        return 5
    return 18


def split_tax(taxable: float, pct: float, inter_state: bool) -> dict:
    tax = round(taxable * pct / 100.0, 2)
    if inter_state:
        return {"igst": tax, "cgst": 0.0, "sgst": 0.0, "tax": tax}
    half = round(tax / 2.0, 2)
    return {"igst": 0.0, "cgst": half, "sgst": round(tax - half, 2), "tax": tax}


# ---------------------------------------------------------------- cancellation policy
def cancel_fee(policy: dict, arrive: date, cancel_on: date, first_night: float, total: float) -> tuple[float, str]:
    """HER policy: {free_days: n, fee: 'first_night' | 'pct', pct: x, no_show: 'first_night' | 'full' | 'pct'}.
    Returns (fee, why). Policy missing = 0 with a note (never invent a charge)."""
    if not policy:
        return 0.0, "Aapki cancellation policy set nahi; koi charge nahi lagaya."
    days = (arrive - cancel_on).days
    free = int(money(policy.get("free_days")))
    if days >= free:
        return 0.0, f"Aagman se {days} din pehle cancel: {free} din tak free (aapki policy)."
    kind = str(policy.get("fee") or "first_night")
    if kind == "pct":
        p = money(policy.get("pct"))
        return round(total * p / 100.0, 2), f"{free} din se kam: {p:g}% (aapki policy)."
    if kind == "full":
        return round(total, 2), f"{free} din se kam: poora (aapki policy)."
    return round(first_night, 2), f"{free} din se kam: pehli raat ka kiraya (aapki policy)."


def policy_text(policy: dict) -> str:
    if not policy:
        return ""
    free = int(money(policy.get("free_days")))
    kind = str(policy.get("fee") or "first_night")
    fee = {"pct": f"{money(policy.get('pct')):g}% kiraya", "full": "poora kiraya"}.get(kind, "pehli raat ka kiraya")
    return f"Aagman se {free} din pehle tak free cancellation; uske baad {fee}."


# ---------------------------------------------------------------- availability
def overlaps(a1: date, d1: date, a2: date, d2: date) -> bool:
    return a1 < d2 and a2 < d1


# ---------------------------------------------------------------- Form C (Form III)
def formc_due(at: datetime) -> datetime:
    """Immigration and Foreigners Rules 2025 r.17(5)/(6): within 24 hours of arrival / departure."""
    return at + timedelta(hours=24)


def is_foreign(nationality: str) -> bool:
    n = (nationality or "").strip().lower()
    return bool(n) and n not in ("india", "indian", "in", "ind", "bharat", "bharatiya", "भारत", "भारतीय")


# ---------------------------------------------------------------- reports
def kpis(rooms_available: int, rooms_sold: int, room_revenue: float) -> dict:
    occ = round(100.0 * rooms_sold / rooms_available, 1) if rooms_available else 0.0
    adr = round(room_revenue / rooms_sold, 2) if rooms_sold else 0.0
    revpar = round(room_revenue / rooms_available, 2) if rooms_available else 0.0
    return {"rooms_available": rooms_available, "rooms_sold": rooms_sold, "room_revenue": round(room_revenue, 2),
            "occupancy_pct": occ, "adr": adr, "revpar": revpar}


# ---------------------------------------------------------------- OTA mails / sheets (HER paste; data, never instructions)
_OTA_WORDS = [
    ("makemytrip", r"make\s*my\s*trip|\bmmt\b|makemytrip"), ("goibibo", r"goibibo"), ("booking", r"booking\.com"),
    ("agoda", r"agoda"), ("airbnb", r"airbnb"), ("expedia", r"expedia"), ("cleartrip", r"cleartrip"),
    ("easemytrip", r"easemytrip|ease\s*my\s*trip"), ("yatra", r"yatra\.com|\byatra\b"),
]
_REF = [
    r"(?:booking|reservation|confirmation|itinerary|order)\s*(?:id|no\.?|number|#|code)\s*[:#-]?\s*([A-Z0-9][A-Z0-9-]{4,24})",
    r"\b(NH\d{6,14})\b", r"\b(HM[A-Z0-9]{8,16})\b", r"\b(GOIBIBO[A-Z0-9]{4,})\b", r"\b(HM[0-9A-Z]{6,})\b",
]


def ota_source(text: str) -> str:
    t = text.lower()
    for k, rx in _OTA_WORDS:
        if re.search(rx, t):
            return k
    return ""


def _after(label: str, text: str) -> str:
    m = re.search(rf"(?im)^\s*[^\n]*?\b{label}\b[^\n:]*[:\-]\s*(.+)$", text)
    return m.group(1).strip() if m else ""


def _int_after(label: str, text: str) -> int:
    m = re.search(rf"(?i)(?<![\d,])(\d{{1,3}})[ \t]*{label}", text) or re.search(rf"(?i){label}[ \t]*[:\-]?[ \t]*(\d{{1,3}})\b", text)
    return int(m.group(1)) if m else 0


def _amount_after(labels: list[str], text: str) -> float | None:
    for lab in labels:
        m = re.search(rf"(?i){lab}[^\n\d₹]{{0,40}}(?:₹|rs\.?|inr)?\s*([\d,]+(?:\.\d{{1,2}})?)", text)
        if m:
            return money(m.group(1))
    return None


def parse_ota(text: str, today: date | None = None) -> dict:
    """One booking from a pasted OTA mail (MakeMyTrip, Goibibo, Booking.com, Agoda, Airbnb ...). Missing = '' / None, never guessed.
    Returns {source, ref, cancelled, guest, phone, email, arrive, depart, rooms, room_type, adults, children, amount, paid_online,
    pay_at_hotel, commission, meal_plan, missing[]}."""
    raw = str(text or "")[:20000]
    t = raw.replace("\r", "")
    src = ota_source(t)
    ref = ""
    for rx in _REF:
        m = re.search(rx, t, re.I)
        if m:
            ref = m.group(1).strip().upper().rstrip(".")
            break
    cancelled = bool(re.search(r"(?i)\b(cancell?ed|cancellation (?:confirmed|notification)|booking has been cancel)", t))
    guest = ""
    for lab in ("guest name", "primary guest", "lead guest", "guest", "booked by", "name"):
        v = _after(lab, t)
        if v and not re.search(r"\d{3}", v):
            guest = re.sub(r"\s{2,}", " ", v)[:80]
            break
    arrive = depart = None
    for lab in ("check-in", "check in", "checkin", "arrival", "arriving"):
        v = _after(lab, t)
        if v:
            arrive = parse_date(v, today)
            if arrive:
                break
    for lab in ("check-out", "check out", "checkout", "departure", "departing"):
        v = _after(lab, t)
        if v:
            depart = parse_date(v, today)
            if depart:
                break
    if arrive and not depart:
        n = _int_after(r"nights?", t)
        if n:
            depart = arrive + timedelta(days=n)
    rooms = _int_after(r"rooms?\b", t) or 1
    room_type = ""
    for lab in ("room type", "room category", "room name", "room"):
        v = _after(lab, t)
        if v and not re.fullmatch(r"\d+", v.strip()):
            room_type = re.sub(r"\s{2,}", " ", v)[:60]
            break
    adults = _int_after(r"adults?", t)
    children = _int_after(r"(?:child|children|kids?)", t)
    amount = _amount_after(["total amount", "booking amount", "total price", "grand total", "total payable", "amount payable",
                            "total charge", "total"], t)
    pay_at_hotel = _amount_after(["pay at hotel", "payable at hotel", "to be collected", "collect from guest", "balance"], t)
    paid_online = bool(re.search(r"(?i)\b(prepaid|paid online|payment received|already paid|pre-paid)\b", t))
    commission = _amount_after(["commission"], t)
    meal = ""
    m = re.search(r"\b(EP|CP|MAP|AP)\b", t)
    if m:
        meal = m.group(1)
    elif re.search(r"(?i)breakfast included|with breakfast", t):
        meal = "CP"
    ph = ""
    m = re.search(r"(?i)(?:mobile|phone|contact|tel)[^\n\d+]{0,20}((?:\+?91[\s-]?)?[6-9]\d{4}[\s-]?\d{5})", t) or \
        re.search(r"(?<![\w])((?:\+91[\s-]?)?[6-9]\d{4}[\s-]?\d{5})(?![\w])", t)
    if m:
        ph = phone10(m.group(1))
    em = ""
    m = re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", t)
    if m and not re.search(r"(?i)noreply|no-reply|makemytrip|goibibo|booking\.com|agoda|airbnb|expedia", m.group(0)):
        em = m.group(0)
    missing = [k for k, v in (("source", src), ("ref", ref), ("guest", guest), ("arrive", arrive), ("depart", depart)) if not v]
    return {"source": src or "other", "ref": ref, "cancelled": cancelled, "guest": guest, "phone": ph, "email": em,
            "arrive": arrive.isoformat() if arrive else "", "depart": depart.isoformat() if depart else "", "rooms": max(1, rooms),
            "room_type": room_type, "adults": adults, "children": children, "amount": amount, "paid_online": paid_online,
            "pay_at_hotel": pay_at_hotel, "commission": commission, "meal_plan": meal, "missing": missing}


_COLS = {
    "ref": ("booking id", "booking no", "reservation id", "confirmation", "booking reference", "booking number", "order id", "ref"),
    "guest": ("guest name", "guest", "booker name", "name", "customer"),
    "arrive": ("check-in", "check in", "checkin", "arrival", "start date"),
    "depart": ("check-out", "check out", "checkout", "departure", "end date"),
    "room_type": ("room type", "room name", "unit type", "room category", "listing", "room"),
    "rooms": ("rooms", "no of rooms", "room nights qty", "units"),
    "adults": ("adults", "persons", "guests", "pax"),
    "amount": ("total amount", "price", "amount", "total", "payout", "booking amount", "net amount"),
    "status": ("status", "booking status"),
    "phone": ("phone", "mobile", "contact"),
    "source": ("source", "channel", "ota"),
}


def map_columns(header: list[str]) -> dict[str, int]:
    h = [str(x or "").strip().lower() for x in header]
    out: dict[str, int] = {}
    for key, names in _COLS.items():
        for nm in names:
            for i, col in enumerate(h):
                if i in out.values():
                    continue
                if col == nm or (len(nm) > 3 and col.startswith(nm)):
                    out[key] = i
                    break
            if key in out:
                break
    return out


def row_booking(row: list[Any], cols: dict[str, int], source: str, today: date | None = None) -> dict:
    g = lambda k: (row[cols[k]] if k in cols and cols[k] < len(row) else None)  # noqa: E731
    st = str(g("status") or "").lower()
    src = str(g("source") or "").strip().lower()
    src = next((k for k, rx in _OTA_WORDS if re.search(rx, src)), "") or source or "other"
    amt = g("amount")
    return {"source": src, "ref": str(g("ref") or "").strip().upper()[:30], "cancelled": "cancel" in st,
            "guest": str(g("guest") or "").strip()[:80], "phone": phone10(g("phone")),
            "arrive": (parse_date(g("arrive"), today) or "") and parse_date(g("arrive"), today).isoformat(),
            "depart": (parse_date(g("depart"), today) or "") and parse_date(g("depart"), today).isoformat(),
            "room_type": str(g("room_type") or "").strip()[:60], "rooms": int(money(g("rooms")) or 1),
            "adults": int(money(g("adults"))), "children": 0, "amount": money(amt) if amt not in (None, "") else None,
            "paid_online": False, "pay_at_hotel": None, "commission": None, "meal_plan": "", "email": ""}


def match_room_type(name: str, types: list[dict]) -> dict | None:
    """Her room type by name / code / alias words (OTA names differ: 'Deluxe Double Room' -> Deluxe)."""
    n = re.sub(r"[^a-z0-9 ]", " ", (name or "").lower())
    if not n.strip():
        return types[0] if len(types) == 1 else None
    best, score = None, 0
    for t in types:
        words = {w for w in re.sub(r"[^a-z0-9 ]", " ", f"{t.get('name', '')} {t.get('code', '')} {t.get('aliases', '')}".lower()).split()
                 if len(w) > 2 and w not in ("room", "rooms", "with", "and", "the")}
        hit = sum(1 for w in words if re.search(rf"\b{re.escape(w)}\b", n))
        if hit > score:
            best, score = t, hit
    return best if score else None
