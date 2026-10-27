"""Pure rules of the Yatra Sahayak: Indian Railways booking windows (ARP, Tatkal, chart), ID proofs, flight check-in, passport /
visa notes, documents checklist, packing list, pasted-quote parsing and the comparison table. No I/O here.

Nothing here invents a fare, a time or a visa type: unknowns stay blank ("pata nahi") and every rule carries where it comes
from. Railway rules change often: each line says "IRCTC / RailOne par pakka karein"."""
from __future__ import annotations

import re
import urllib.parse
from datetime import date, datetime, time, timedelta
from typing import Any

# ----------------------------------------------------------------------------- sources (checked 23 Oct 2026)
SOURCES = [
    {"what": "Advance reservation period 60 days (journey day not counted), from 1 Nov 2024",
     "url": "https://www.outlooktraveller.com/News/indian-railways-new-rule-aadhaar-verification-compulsory-for-early-reservations",
     "date": "2025-09"},
    {"what": "First 15 minutes of general reservation opening only for Aadhaar-authenticated IRCTC users (from 1 Oct 2025); "
             "agents barred first 10 minutes; PRS counters unchanged",
     "url": "https://www.outlooktraveller.com/News/indian-railways-new-rule-aadhaar-verification-compulsory-for-early-reservations",
     "date": "2025-09"},
    {"what": "Tatkal online only for Aadhaar-authenticated users (1 Jul 2025), Aadhaar OTP mandatory (15 Jul 2025), authorised agents "
             "barred 10:00-10:30 (AC) and 11:00-11:30 (non-AC)",
     "url": "https://www.theweek.in/wire-updates/national/2025/07/16/des69-jk-tatkal-otp.html", "date": "2025-07-16"},
    {"what": "Chart: trains after 2 pm first chart 8 h before; 5 am-2 pm departures at 9 pm previous night; midnight-5 am at 8 pm "
             "previous evening; final chart 30 min before (secondary source)",
     "url": "https://savedelete.com/article/irctc-train-chart-preparation-time-for-indian-railways/", "date": "2026"},
    {"what": "DigiYatra (face-based paperless entry) at 38 airports, voluntary for domestic flyers",
     "url": "https://superkalam.com/current-affairs/15-06-2026/digital-transformation-digiyatra-facilitating-contactless-travel-at-38-airports-with-over-10-crore-seamless-journeys-pg7-6960e7dc-a808-4815-afe2-eef3e375dbe9",
     "date": "2026-06-15"},
    {"what": "DigiYatra required for international transit passengers at Delhi, Mumbai, Bengaluru, Hyderabad from 1 Jun 2026 "
             "(press report; check with the airport)",
     "url": "https://www.outlooktraveller.com/amp/story/destinations/india/News/digiyatra-now-mandatory-for-international-transit-at-four-major-indian-airports",
     "date": "2026"},
    {"what": "Indian passport services (renewal, Tatkaal passport)", "url": "https://www.passportindia.gov.in", "date": "2026-10"},
]

DISCLAIM = "Niyam badalte rehte hain: IRCTC / airline / embassy ki official site par ek baar pakka kar lijiye."

# ----------------------------------------------------------------------------- railways
CLASSES = {
    "1A": "First AC", "2A": "AC 2 tier", "3A": "AC 3 tier", "3E": "AC 3 economy", "EC": "Executive chair car", "EA": "Anubhuti",
    "CC": "AC chair car", "SL": "Sleeper", "2S": "Second sitting", "FC": "First class",
}
AC_CLASSES = {"1A", "2A", "3A", "3E", "EC", "EA", "CC"}
QUOTAS = {
    "GN": "General", "TQ": "Tatkal", "PT": "Premium Tatkal", "LD": "Ladies", "SS": "Lower berth / senior citizen",
    "HP": "Divyangjan (handicapped)", "DF": "Defence", "FT": "Foreign tourist", "YU": "Yuva",
}
ARP_DAYS = 60
BOOKING_OPENS = time(8, 0)

CLASS_WORDS = {
    "1a": "1A", "first ac": "1A", "2a": "2A", "2ac": "2A", "ac 2": "2A", "second ac": "2A", "3a": "3A", "3ac": "3A",
    "ac 3": "3A", "third ac": "3A", "3e": "3E", "economy": "3E", "cc": "CC", "chair car": "CC", "ec": "EC",
    "executive": "EC", "sl": "SL", "sleeper": "SL", "2s": "2S", "second sitting": "2S", "general seating": "2S",
}


def norm_class(v: str) -> str:
    v = (v or "").strip()
    if v.upper() in CLASSES:
        return v.upper()
    return CLASS_WORDS.get(v.lower(), "")


def norm_quota(v: str) -> str:
    v = (v or "").strip()
    if v.upper() in QUOTAS:
        return v.upper()
    low = v.lower()
    if "premium" in low:
        return "PT"
    if "tatkal" in low or "tatkaal" in low:
        return "TQ"
    if "ladies" in low or "mahila" in low:
        return "LD"
    if "senior" in low or "lower" in low:
        return "SS"
    return "GN" if low in ("", "gn", "general") else ""


def arp_open(journey: date) -> datetime:
    """When general booking opens for this journey date (local time)."""
    return datetime.combine(journey - timedelta(days=ARP_DAYS), BOOKING_OPENS)


def tatkal_open(journey: date, cls: str) -> dict[str, Any]:
    """Tatkal opens one day before the journey (journey day not counted): AC 10:00, non-AC 11:00."""
    cls = norm_class(cls) or "SL"
    t = time(10, 0) if cls in AC_CLASSES else time(11, 0)
    at = datetime.combine(journey - timedelta(days=1), t)
    return {"at": at.isoformat(timespec="minutes"), "class": cls, "ac": cls in AC_CLASSES,
            "agents_from": (at + timedelta(minutes=30)).isoformat(timespec="minutes"),
            "say": (f"Tatkal ({CLASSES.get(cls, cls)}) {at:%d %b} ko {at:%H:%M} baje khulega. IRCTC account Aadhaar se "
                    "verified hona chahiye aur Aadhaar wale mobile par OTP aayega; agent pehle 30 minute book nahi kar sakte. "
                    "Tatkal ticket cancel karne par aam taur par paisa wapas nahi milta.")}


def chart_time(depart: datetime) -> datetime:
    """First reservation chart (secondary source, see SOURCES)."""
    t = depart.time()
    if t >= time(14, 0):
        return depart - timedelta(hours=8)
    prev = depart.date() - timedelta(days=1)
    if t >= time(5, 0):
        return datetime.combine(prev, time(21, 0))
    return datetime.combine(prev, time(20, 0))


TRAIN_ID = ["Aadhaar (mAadhaar / DigiLocker copy bhi)", "Voter ID", "Passport", "PAN card", "Driving licence",
            "Sarkari photo ID card", "School / college photo ID (students)", "Bank passbook with photo"]
FLIGHT_ID = ["Aadhaar", "Passport", "Voter ID", "Driving licence", "PAN card", "Sarkari / PSU employee photo ID"]


# ----------------------------------------------------------------------------- flights
def web_checkin(depart: datetime, international: bool = False) -> dict[str, Any]:
    """Usual window (airline rules differ: always shown as 'aam taur par')."""
    opens = depart - timedelta(hours=48)
    closes = depart - timedelta(minutes=75 if international else 60)
    return {"opens": opens.isoformat(timespec="minutes"), "closes": closes.isoformat(timespec="minutes"),
            "say": (f"Web check-in aam taur par {opens:%d %b %H:%M} se {closes:%d %b %H:%M} tak (airline ki site par pakka "
                    "karein). Airport " + ("3 ghante" if international else "2 ghante") + " pehle pahunchiye.")}


# ----------------------------------------------------------------------------- countries / visa (only what is certain)
CITY_COUNTRY = {
    "dubai": "uae", "abu dhabi": "uae", "sharjah": "uae", "bangkok": "thailand", "phuket": "thailand", "pattaya": "thailand",
    "krabi": "thailand", "singapore": "singapore", "bali": "indonesia", "jakarta": "indonesia", "kathmandu": "nepal",
    "pokhara": "nepal", "thimphu": "bhutan", "paro": "bhutan", "colombo": "sri_lanka", "kandy": "sri_lanka", "male": "maldives",
    "london": "uk", "paris": "france", "rome": "italy", "zurich": "switzerland", "amsterdam": "netherlands", "berlin": "germany",
    "barcelona": "spain", "madrid": "spain", "vienna": "austria", "prague": "czechia", "new york": "usa", "san francisco": "usa",
    "chicago": "usa", "tokyo": "japan", "osaka": "japan", "kuala lumpur": "malaysia", "langkawi": "malaysia", "hanoi": "vietnam",
    "ho chi minh": "vietnam", "da nang": "vietnam", "sydney": "australia", "melbourne": "australia", "toronto": "canada",
    "vancouver": "canada", "baku": "azerbaijan", "istanbul": "turkey", "mauritius": "mauritius",
}
SCHENGEN = {"france", "italy", "switzerland", "netherlands", "germany", "spain", "austria", "czechia", "greece", "portugal",
            "belgium", "sweden", "norway", "denmark", "finland", "poland", "hungary", "croatia"}
VISA = {
    "nepal": {"name": "Nepal", "need": False, "note": "Bharatiya nagrikon ko visa nahi chahiye; valid passport ya Voter ID saath rakhiye.",
              "official": "https://www.immigration.gov.np"},
    "bhutan": {"name": "Bhutan", "need": False, "note": "Visa nahi, par entry permit aur Sustainable Development Fee lagti hai; "
                                                        "passport ya Voter ID chahiye.", "official": "https://www.visitbhutan.com"},
    "uae": {"name": "UAE", "need": None, "official": "https://icp.gov.ae"},
    "thailand": {"name": "Thailand", "need": None, "official": "https://www.thaievisa.go.th"},
    "singapore": {"name": "Singapore", "need": None, "official": "https://www.ica.gov.sg"},
    "indonesia": {"name": "Indonesia", "need": None, "official": "https://evisa.imigrasi.go.id"},
    "sri_lanka": {"name": "Sri Lanka", "need": None, "official": "https://www.eta.gov.lk"},
    "maldives": {"name": "Maldives", "need": None, "official": "https://immigration.gov.mv"},
    "malaysia": {"name": "Malaysia", "need": None, "official": "https://malaysiavisa.imi.gov.my"},
    "vietnam": {"name": "Vietnam", "need": None, "official": "https://evisa.gov.vn"},
    "uk": {"name": "UK", "need": True, "official": "https://www.gov.uk/check-uk-visa"},
    "usa": {"name": "USA", "need": True, "official": "https://travel.state.gov"},
    "japan": {"name": "Japan", "need": None, "official": "https://www.mofa.go.jp/j_info/visit/visa/"},
    "australia": {"name": "Australia", "need": True, "official": "https://immi.homeaffairs.gov.au"},
    "canada": {"name": "Canada", "need": True, "official": "https://www.canada.ca/en/immigration-refugees-citizenship.html"},
    "turkey": {"name": "Turkey", "need": None, "official": "https://www.evisa.gov.tr"},
    "azerbaijan": {"name": "Azerbaijan", "need": None, "official": "https://evisa.gov.az"},
    "mauritius": {"name": "Mauritius", "need": None, "official": "https://passport.govmu.org"},
    "schengen": {"name": "Schengen (Europe)", "need": True, "official": "https://home-affairs.ec.europa.eu/policies/schengen-borders-and-visa/visa-policy_en",
                 "note": "Schengen visa ke liye kam se kam EUR 30,000 ka medical travel insurance zaroori hai."},
}


def country_of(text: str) -> str:
    low = (text or "").lower()
    for k, v in VISA.items():
        if re.search(rf"\b{re.escape(v['name'].split(' ')[0].lower())}\b", low) or re.search(rf"\b{k.replace('_', ' ')}\b", low):
            return k
    for city, c in CITY_COUNTRY.items():
        if re.search(rf"\b{re.escape(city)}\b", low):
            return c
    return ""


def visa_info(country: str) -> dict[str, Any]:
    if not country:
        return {}
    key = "schengen" if country in SCHENGEN else country
    v = dict(VISA.get(key) or {"name": country.replace("_", " ").title(), "need": None, "official": ""})
    v["country"] = country
    if v.get("need") is None:
        v["say"] = (f"{v['name']}: visa / e-visa / visa-on-arrival ka niyam Bharatiya passport ke liye badalta rehta hai; "
                    f"pakka type official site par dekhiye{(': ' + v['official']) if v.get('official') else ''}.")
    elif v["need"]:
        v["say"] = f"{v['name']}: visa pehle se lena hoga. Official: {v['official']}. " + v.get("note", "")
    else:
        v["say"] = f"{v['name']}: " + v.get("note", "")
    return v


def passport_check(expiry: str, return_date: str, country: str = "") -> dict[str, Any]:
    """Safe rule: valid 6 months beyond the return date (many countries ask this; Schengen: 3 months after leaving)."""
    try:
        exp, ret = date.fromisoformat(expiry), date.fromisoformat(return_date)
    except (TypeError, ValueError):
        return {"ok": None, "say": "Passport ki expiry date bataiye (DD-MM-YYYY), tab check karunga."}
    months = (exp.year - ret.year) * 12 + (exp.month - ret.month) - (1 if exp.day < ret.day else 0)
    need = 3 if country in SCHENGEN else 6
    ok = months >= need
    say = (f"Passport wapsi ke baad {months} mahine valid hai" + (" - theek hai." if ok else
           f" - kam se kam {need} mahine chahiye. Jaldi renew karaiye (passportindia.gov.in; jaldi ho to Tatkaal)."))
    if country in SCHENGEN:
        say += " Schengen: passport pichhle 10 saal mein bana ho aur 2 khaali page."
    return {"ok": ok, "months_after_return": months, "need_months": need, "say": say}


# ----------------------------------------------------------------------------- documents checklist
def doc_checklist(info: dict[str, Any]) -> list[dict[str, Any]]:
    """info: modes (set of train / flight / bus / hotel), international, country, travellers [{name, age, kind}], tatkal."""
    modes = set(info.get("modes") or [])
    intl = bool(info.get("international"))
    country = info.get("country") or ""
    out: list[dict[str, Any]] = []

    def add(i, title, why="", who="sab", must=True, src=""):
        out.append({"id": i, "title": title, "why": why, "who": who, "must": must, "src": src})

    trav = info.get("travellers") or []
    if "train" in modes:
        add("train_id", "Har yatri ka original photo ID (train)", "TTE maang sakta hai: " + ", ".join(TRAIN_ID[:5]) + "...")
        add("train_ticket", "E-ticket / SMS (PNR wala)", "Print zaroori nahi, SMS / app mein ticket kaafi hai.")
        if info.get("tatkal"):
            add("tatkal_aadhaar", "IRCTC account Aadhaar se verified + Aadhaar wala mobile saath",
                "Tatkal ke liye Aadhaar OTP zaroori (15 Jul 2025 se).", src=SOURCES[2]["url"])
    if "flight" in modes:
        add("flight_id", "Photo ID (flight)", "Airport entry ke liye: " + ", ".join(FLIGHT_ID[:4]) + "...")
        add("boarding", "Boarding pass (web check-in ke baad)")
        add("digiyatra", "DigiYatra app (marzi se)", "38 airports par bina kaagaz entry; domestic mein marzi.", must=False,
            src=SOURCES[4]["url"])
    if "bus" in modes:
        add("bus_ticket", "Bus ticket / SMS + photo ID")
    if "hotel" in modes or intl:
        add("hotel_voucher", "Hotel booking voucher / confirmation", "Check-in par photo ID bhi maangte hain.")
    if intl:
        add("passport", "Passport (wapsi ke baad 6 mahine valid, 2 khaali page)", src=SOURCES[6]["url"])
        v = visa_info(country)
        if v.get("need") is not False:
            add("visa", f"Visa / e-visa ({v.get('name') or 'desh'})", v.get("say", "Official site par type check karein."),
                must=True, src=v.get("official", ""))
        add("return_ticket", "Wapsi ka ticket + hotel booking ki copy", "Immigration maang sakta hai.")
        add("insurance", "Travel insurance", (VISA["schengen"]["note"] if country in SCHENGEN else
                                             "Medical emergency ke liye accha; kuch desh ke visa mein zaroori."),
            must=country in SCHENGEN)
        add("forex", "Forex card / thoda cash (desh ki currency)", must=False)
        add("photos", "Passport size photos (2-4)", must=False)
    for t in trav:
        try:
            age = int(t.get("age") or -1)
        except (TypeError, ValueError):
            age = -1
        if 0 <= age < 18:
            add(f"minor_{t.get('name', '')[:20]}", f"{t.get('name') or 'Bachche'}: birth certificate / school ID",
                "Bachchon ki age proof ke liye.", who=t.get("name") or "bachcha")
        if age >= 60 and "train" in modes:
            add(f"senior_{t.get('name', '')[:20]}", f"{t.get('name')}: age proof saath (lower berth quota ke liye)",
                who=t.get("name") or "", must=False)
    add("emergency", "Emergency contact + zaroori dawaiyan", must=False)
    return out


# ----------------------------------------------------------------------------- packing
def packing(days: int, month: int, kind: str = "", international: bool = False, kids: bool = False) -> list[str]:
    days = max(1, min(int(days or 1), 30))
    k = (kind or "").lower()
    out = [f"Kapde {days} din ke (+1 extra)", "Phone charger + power bank", "Zaroori dawaiyan + first-aid", "Photo ID (original)",
           "Toothbrush / toiletries", "Paani ki bottle", "Thoda cash + UPI wala phone"]
    if month in (11, 12, 1, 2) or any(w in k for w in ("hill", "pahad", "manali", "shimla", "kashmir", "ladakh", "snow")):
        out += ["Garam kapde / jacket", "Topi, muffler, gloves"]
    if month in (6, 7, 8, 9):
        out += ["Chhata / raincoat", "Jaldi sookhne wale kapde"]
    if month in (3, 4, 5) or any(w in k for w in ("beach", "goa", "samudra")):
        out += ["Sunscreen, topi, chashma", "Halke cotton kapde"]
    if any(w in k for w in ("beach", "goa", "samudra", "andaman")):
        out += ["Swimwear", "Chappal"]
    if any(w in k for w in ("mandir", "temple", "tirth", "yatra", "pilgrim", "darshan")):
        out += ["Darshan ke liye saade kapde", "Mandir ke niyam (dress code) check karein"]
    if any(w in k for w in ("business", "meeting", "office", "conference")):
        out += ["Formal kapde", "Laptop + charger", "Visiting card"]
    if international:
        out += ["Passport + visa copy (phone mein bhi)", "Travel adapter (plug)", "Forex card"]
    if kids:
        out += ["Bachchon ke snacks, khilone", "Bachchon ki dawai"]
    return list(dict.fromkeys(out))


# ----------------------------------------------------------------------------- links (official / search pages only)
def maps_link(place: str, near: str = "") -> str:
    q = f"{place}, {near}" if near and near.lower() not in place.lower() else place
    return "https://www.google.com/maps/search/?api=1&query=" + urllib.parse.quote(q.strip())


def search_links(mode: str, origin: str = "", dest: str = "", day: str = "") -> list[dict[str, str]]:
    m = (mode or "").lower()
    q = urllib.parse.quote
    if m == "train":
        return [{"name": "IRCTC (official)", "url": "https://www.irctc.co.in/nget/train-search"},
                {"name": "RailOne app (Indian Railways)", "url": "https://play.google.com/store/search?q=RailOne&c=apps"}]
    if m == "bus":
        return [{"name": "redBus", "url": "https://www.redbus.in"},
                {"name": "State transport (MSRTC)", "url": "https://npublic.msrtcors.com"}]
    if m == "flight":
        return [{"name": "Google Flights", "url": "https://www.google.com/travel/flights?q=" + q(f"flights from {origin} to {dest} on {day}".strip())},
                {"name": "MakeMyTrip", "url": "https://www.makemytrip.com/flights/"}]
    if m == "hotel":
        return [{"name": "Google Hotels", "url": "https://www.google.com/travel/hotels?q=" + q(f"hotels in {dest}".strip())},
                {"name": "Google Maps", "url": maps_link(f"hotels in {dest}")}]
    return []


SITE_FOR = {"train": "irctc", "bus": "redbus", "flight": "makemytrip", "hotel": "makemytrip"}

# ----------------------------------------------------------------------------- pasted quotes -> options
_PRICE = re.compile(r"(?:₹|rs\.?|inr)\s*(\d[\d,]*(?:\.\d{1,2})?)|(\d[\d,]{2,}(?:\.\d{1,2})?)\s*(?:rs|rupaye|rupees|/-)", re.I)
_TIME = re.compile(r"\b([01]?\d|2[0-3])[:.]([0-5]\d)\b")
_RATING = re.compile(r"(?:rating|⭐|★)\s*[:=]?\s*(\d(?:\.\d)?)|(\d\.\d)\s*/\s*5|(\d(?:\.\d)?)\s*(?:⭐|★)", re.I)
_STARS = re.compile(r"\b([1-5])\s*(?:\*|star)", re.I)
_DUR = re.compile(r"(\d{1,2})\s*h(?:rs?|ours?)?\s*(?:(\d{1,2})\s*m(?:in)?)?|(\d{1,3})\s*min", re.I)
_TRAIN_NO = re.compile(r"\b(\d{5})\b")
_FLIGHT_NO = re.compile(r"\b(6E|AI|UK|SG|QP|IX|I5|G8|EK|QR|SQ|TG)[\s-]?(\d{2,4})\b", re.I)

MODE_WORDS = {
    "flight": ("flight", "indigo", "air india", "akasa", "spicejet", "vistara", "6e", "airline", "udaan"),
    "train": ("train", "express", "rajdhani", "shatabdi", "vande", "duronto", "mail", "superfast", "irctc", "gadi"),
    "bus": ("bus", "volvo", "sleeper bus", "seater", "travels", "msrtc", "ksrtc"),
    "hotel": ("hotel", "resort", "homestay", "stay", "lodge", "inn", "night", "raat", "room"),
    "cab": ("cab", "taxi", "innova", "dzire", "ertiga", "car"),
}


def guess_mode(text: str) -> str:
    low = (text or "").lower()
    if _FLIGHT_NO.search(text or ""):
        return "flight"
    for m, ws in MODE_WORDS.items():
        if any(re.search(rf"\b{re.escape(w)}\b", low) for w in ws):
            return m
    if _TRAIN_NO.search(text or ""):
        return "train"
    return "other"


def paise_of(text: str) -> int | None:
    m = _PRICE.search(text or "")
    if not m:
        return None
    v = (m.group(1) or m.group(2) or "").replace(",", "")
    try:
        return int(round(float(v) * 100))
    except ValueError:
        return None


def minutes_of(text: str) -> int | None:
    m = _DUR.search(text or "")
    if m:
        if m.group(3):
            return int(m.group(3))
        return int(m.group(1)) * 60 + int(m.group(2) or 0)
    iso = re.fullmatch(r"PT(?:(\d+)H)?(?:(\d+)M)?", (text or "").strip())
    if iso and (iso.group(1) or iso.group(2)):
        return int(iso.group(1) or 0) * 60 + int(iso.group(2) or 0)
    return None


def parse_quotes(text: str, mode: str = "") -> list[dict[str, Any]]:
    """One option per line (or per blank-line block). Only what is written; nothing filled in."""
    blocks = [b.strip() for b in re.split(r"\n\s*\n|\n(?=\s*(?:\d+[.)]|[-•*])\s)", text or "") if b.strip()]
    if len(blocks) <= 1:
        blocks = [ln.strip() for ln in (text or "").splitlines() if ln.strip()]
    out = []
    for b in blocks[:30]:
        line = re.sub(r"^\s*(?:\d+[.)]|[-•*])\s*", "", b).strip()
        if len(line) < 4:
            continue
        md = mode or guess_mode(line)
        price = paise_of(line)
        times = [f"{int(h):02d}:{mm}" for h, mm in _TIME.findall(line)]
        rating = None
        r = _RATING.search(line)
        if r:
            try:
                rating = float(r.group(1) or r.group(2) or r.group(3))
            except (TypeError, ValueError):
                rating = None
            if rating is not None and rating > 5:
                rating = None
        stars = None
        s = _STARS.search(line)
        if s:
            stars = int(s.group(1))
        dur = minutes_of(line)
        if dur is None and len(times) >= 2:
            h1, m1 = map(int, times[0].split(":"))
            h2, m2 = map(int, times[1].split(":"))
            d = (h2 * 60 + m2) - (h1 * 60 + m1)
            dur = d if d > 0 else d + 24 * 60
        name = re.split(r"(?:₹|rs\.?\s*\d|inr|\b\d{1,2}[:.]\d{2}\b|rating|⭐|★|\|)", line, maxsplit=1, flags=re.I)[0]
        name = re.sub(r"[,;:\-–|]+\s*$", "", name).strip() or line[:60]
        fl = _FLIGHT_NO.search(line)
        tn = _TRAIN_NO.search(line) if md == "train" else None
        if md == "other" and price is None and not times and rating is None and not fl:
            continue                       # not an option (no price / time / rating / known kind)
        out.append({"mode": md, "name": name[:120], "code": (fl.group(1).upper() + " " + fl.group(2)) if fl else (tn.group(1) if tn else ""),
                    "depart": times[0] if times else "", "arrive": times[1] if len(times) > 1 else "",
                    "duration_min": dur, "price_paise": price, "rating": rating, "stars": stars,
                    "per_night": bool(re.search(r"/\s*night|per night|prati raat|/raat", line, re.I)),
                    "refundable": (True if re.search(r"\brefundable\b|free cancel", line, re.I) and not re.search(r"non[- ]?refundable", line, re.I)
                                   else (False if re.search(r"non[- ]?refundable", line, re.I) else None)),
                    "cls": norm_class(next((w for w in re.findall(r"\b(1A|2A|3A|3E|SL|CC|EC|2S)\b", line, re.I)), "")),
                    "raw": line[:300]})
    return out


def compare(options: list[dict[str, Any]], nights: int = 1) -> dict[str, Any]:
    """Comparison per mode by what she gave: total price (hotels x nights), time, rating. Missing = pata nahi."""
    by: dict[str, list[dict[str, Any]]] = {}
    for o in options:
        by.setdefault(o.get("mode") or "other", []).append(o)
    out: dict[str, Any] = {}
    for mode, rows in by.items():
        table = []
        for o in rows:
            p = o.get("price_paise")
            total = (p * max(1, nights) if (p is not None and o.get("per_night") and mode == "hotel") else p)
            table.append({**o, "total_paise": total})
        priced = [r for r in table if r["total_paise"] is not None]
        timed = [r for r in table if r.get("duration_min")]
        rated = [r for r in table if r.get("rating") is not None]
        cheapest = min(priced, key=lambda r: r["total_paise"])["id"] if priced else None
        fastest = min(timed, key=lambda r: r["duration_min"])["id"] if timed and mode != "hotel" else None
        best = max(rated, key=lambda r: r["rating"])["id"] if rated else None
        for r in table:
            tags = []
            if r["id"] == cheapest and len(priced) > 1:
                tags.append("sabse sasta")
            if r["id"] == fastest and len(timed) > 1:
                tags.append("sabse tez")
            if r["id"] == best and len(rated) > 1:
                tags.append("sabse achhi rating")
            if r["total_paise"] is None:
                tags.append("daam pata nahi")
            r["tags"] = tags
        table.sort(key=lambda r: (r["total_paise"] is None, r["total_paise"] or 0))
        notes = []
        if priced and len(priced) < len(table):
            notes.append("Kuch options ka daam nahi diya: unhe tulna mein peeche rakha.")
        out[mode] = {"rows": table, "cheapest": cheapest, "fastest": fastest, "best_rated": best, "notes": notes}
    return out


def holiday_note(hols: list[dict[str, Any]], start: date, end: date) -> list[dict[str, Any]]:
    """Public holidays within 3 days of the trip = rush / higher fares likely."""
    out = []
    for h in hols:
        try:
            d = date.fromisoformat(h["date"])
        except (KeyError, ValueError):
            continue
        if start - timedelta(days=3) <= d <= end + timedelta(days=3):
            long_wk = d.weekday() in (0, 4) or (d.weekday() in (5, 6))
            out.append({"date": h["date"], "name": h.get("name", ""), "kind": h.get("kind", ""),
                        "say": f"{d:%d %b} {h.get('name', '')}: bheed aur kiraya zyada ho sakta hai"
                               + (" (lamba weekend)" if long_wk else "") + "; jaldi book karein."})
    return out
