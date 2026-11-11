"""Tour Guide Sahayak rules: plain-words notes with dated sources, small parsers, safety briefs, script templates.

Nothing here invents a price, a monument timing, a ticket rate or a date: timings / tickets come only from what she typed (or the
official site she names as the source); everything else stays blank / "pata nahi". Tax lines are notes for her CA, not advice."""
from __future__ import annotations

import re
from datetime import date, datetime, timedelta

NEVER = (
    "Never send a guest a message / booking confirmation by itself: every message is a draft or a card and goes only on your tap.",
    "Refund, discount or any expense: only with your approval (the card in the app; fingerprint on money cards). Hoola does not take / pay money.",
    "Price, monument opening hours, closed day, ticket rate: only what you tell (or the official site you name); otherwise 'not known'.",
    "More people than the group size in one tour slot, or two of your tours at the same time: the code refuses (no overbooking).",
    "A guest's ID / emergency number only in the ID Locker (masked reference); never OTP / PIN / card.",
    "Never force guests into a shop / emporium; if there is a commission, tell guests clearly (your accounts stay in the register).",
    "Hoola never logs in to or scrapes an OTA / booking site / ASI portal: you book yourself, Hoola gives the steps and reminds you.",
)

# (what, url, date published / checked)
SOURCES = (
    ("Incredible India Tourist Facilitator (IITF) / Tourist Guide (IITG Heritage, IITG Adventure) certification: portal iitf.gov.in, "
     "certificate + badge valid 5 years, renewal after a 2-week online IITTM refresher (register well before 4 months of expiry), "
     "registration valid 3 years (+2 years at 50% fee), fee Rs 2,000 + exam Rs 500",
     "https://tourism.gov.in/sites/default/files/2024-02/IITFC%20modified%20guideline%2011012021.pdf", "guideline 11 Jan 2021, checked 23 Oct 2026"),
    ("MoT stopped issuing Regional Level Guide (RLG) licences from 2 Mar 2020 (AMASR Act 1958 delegated power); old RLG holders moved "
     "to IITG via the refresher", "https://tourism.gov.in/sites/default/files/2020-04/usq%202713%20for%2017032020.pdf", "17 Mar 2020"),
    ("State guide licences (state tourism departments, renewal per state rules: e.g. Punjab guidelines)",
     "https://punjabtourism.punjab.gov.in/tenders/guidelines_for_grant_of_guide_license_by_deptt.pdf", "checked 23 Oct 2026"),
    ("ASI: online tickets for 170+ centrally protected monuments / museums on ONDC apps (Highway Delite, Pelocal WhatsApp, Abhee); "
     "online discount Rs 5 Indian / Rs 50 foreign continues", "https://www.theweek.in/wire-updates/national/2026/01/06/tourists-visiting-asi-monuments-can-now-book-tickets-online-through-various-digital-platforms.html",
     "6 Jan 2026"),
    ("ASI online ticket booking launched for over 170 monuments (All India Radio)",
     "https://www.newsonair.gov.in/online-ticket-booking-launched-for-over-170-archaeological-monuments", "Jan 2026"),
    ("GST after 22 Sep 2025 (GST 2.0): tourist guide services SAC 998556 18% with ITC",
     "https://busy.in/sac-code-998556", "checked 23 Oct 2026"),
    ("GST: tour operator packages SAC 998555 5% without ITC (or 18% with ITC); pure-agent costs only when conditions are met",
     "https://busy.in/sac-code-998555", "checked 23 Oct 2026"),
    ("Tour operators 5% / 18% options, TCS only on overseas packages (5% up to Rs 10 lakh, 20% above), not on domestic tours",
     "https://www.taxaj.com/learn/?p=496", "2026"),
    ("Trekking rules (registered operator, trained guide, first aid, permits) - example: Ladakh trekking regulations",
     "https://tourism.ladakh.gov.in/assets/pdf/Trekking.pdf", "checked 23 Oct 2026"),
    ("Consumer Protection Act 2019 + E-Commerce Rules 2020: cancellation / refund terms shown upfront before the booking",
     "https://consumeraffairs.nic.in/acts-and-rules/consumer-protection", "checked 23 Oct 2026"),
    ("DPDP Act 2023 + Rules 2025 (notified Nov 2025; most duties from 13 May 2027): purpose limit, erase guest data after use",
     "https://www.meity.gov.in/data-protection-framework", "checked 23 Oct 2026"),
)

KINDS = {"city_walk": "City walk", "heritage": "Heritage / monument", "temple": "Temple / pilgrimage", "trek": "Trek / hike",
         "food": "Food walk", "nature": "Nature / wildlife", "boat": "Boat / water", "day_trip": "Day trip", "other": "Tour"}
LICENCE_KINDS = {"iitf": "IITF (Incredible India Tourist Facilitator)", "iitg_heritage": "IITG Heritage (MoT)",
                 "iitg_adventure": "IITG Adventure (MoT)", "rlg": "Regional Level Guide (old MoT licence)",
                 "state": "State tourism guide licence", "asi_site": "Monument / site guide permit", "first_aid": "First aid certificate",
                 "adventure": "Adventure / trek leader certificate", "other": "Other licence"}
MOT_KINDS = ("iitf", "iitg_heritage", "iitg_adventure")
WINDOWS = (90, 60, 30, 7, 0)
REFRESHER_DAYS = 120          # IITF / IITG: register for the refresher well before 4 months of expiry
LANGS = {"hinglish": "Hinglish", "hi": "Hindi", "en": "English", "mr": "Marathi", "gu": "Gujarati", "ta": "Tamil", "te": "Telugu",
         "kn": "Kannada", "ml": "Malayalam", "bn": "Bengali", "pa": "Punjabi", "fr": "French", "de": "German", "es": "Spanish",
         "it": "Italian", "ru": "Russian", "ja": "Japanese", "zh": "Chinese", "ko": "Korean", "ar": "Arabic", "pt": "Portuguese"}
LANG_WORDS = {"hindi": "hi", "हिंदी": "hi", "english": "en", "angrezi": "en", "marathi": "mr", "मराठी": "mr", "gujarati": "gu",
              "tamil": "ta", "telugu": "te", "kannada": "kn", "malayalam": "ml", "bengali": "bn", "bangla": "bn", "punjabi": "pa",
              "french": "fr", "german": "de", "spanish": "es", "italian": "it", "russian": "ru", "japanese": "ja",
              "chinese": "zh", "mandarin": "zh", "korean": "ko", "arabic": "ar", "portuguese": "pt", "hinglish": "hinglish"}
DAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
DAY_WORDS = {"monday": "mon", "somvar": "mon", "tuesday": "tue", "mangalvar": "tue", "wednesday": "wed", "budhvar": "wed",
             "thursday": "thu", "guruvar": "thu", "friday": "fri", "shukravar": "fri", "jumma": "fri", "saturday": "sat",
             "shanivar": "sat", "sunday": "sun", "ravivar": "sun", "itvaar": "sun"}
GST_MODES = {"none": "No GST registration (confirm with your CA: turnover below Rs 20 lakh on services / Rs 10 lakh in special states)",
             "guide": "Tourist guide service: SAC 998556, 18% (with ITC) - confirm with your CA",
             "tour5": "Tour operator package: SAC 998555, 5% without ITC - confirm with your CA",
             "tour18": "Tour operator package: 18% with ITC - confirm with your CA"}


def scrub(text: str, n: int = 2000) -> str:
    """Free text: OTP / PIN / password values, card-like runs, Aadhaar-like 12 digits and PAN are never kept."""
    t = str(text or "")
    t = re.sub(r"\b(otp|pin|cvv|password|upi pin|mpin)\b\s*(?:is|hai|:|=)?\s*\S+", lambda m: f"{m.group(1)} [removed]", t, flags=re.I)
    t = re.sub(r"\b(?:\d[ -]?){13,19}\b", "[removed]", t)
    t = re.sub(r"\b\d{4}\s?\d{4}\s?\d{4}\b", "[ID removed]", t)
    t = re.sub(r"\b[A-Z]{5}\d{4}[A-Z]\b", "[PAN removed]", t)
    return t.strip()[:n]


def money(v) -> float | None:
    if v is None or v == "":
        return None
    if isinstance(v, (int, float)):
        return float(v) if v >= 0 else None
    t = str(v).lower().replace(",", "").replace("₹", "").replace("rs.", "").replace("rs", "").strip()
    m = re.search(r"(\d+(?:\.\d+)?)\s*(k|hazaar|hazar|thousand|lakh|lac)?", t)
    if not m:
        return None
    x = float(m.group(1))
    mul = {"k": 1e3, "hazaar": 1e3, "hazar": 1e3, "thousand": 1e3, "lakh": 1e5, "lac": 1e5}.get(m.group(2) or "", 1)
    return round(x * mul, 2)


def phone10(v) -> str:
    d = re.sub(r"\D", "", str(v or ""))
    if len(d) == 12 and d.startswith("91"):
        d = d[2:]
    if len(d) == 11 and d.startswith("0"):
        d = d[1:]
    return d if re.fullmatch(r"[6-9]\d{9}", d) else ""


def mask_phone(p: str) -> str:
    return f"{p[:2]}XXXXXX{p[-2:]}" if len(p) == 10 else ""


def parse_date(v, today: date | None = None) -> date | None:
    if v is None or v == "":
        return None
    if isinstance(v, date) and not isinstance(v, datetime):
        return v
    if isinstance(v, datetime):
        return v.date()
    t = str(v).strip().lower()
    base = today or date.today()
    if t in ("aaj", "today"):
        return base
    if t in ("kal", "tomorrow"):
        return base + timedelta(days=1)
    if t in ("parso", "parson"):
        return base + timedelta(days=2)
    m = re.fullmatch(r"(\d{4})-(\d{1,2})-(\d{1,2})", t)
    try:
        if m:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        m = re.fullmatch(r"(\d{1,2})[-/.](\d{1,2})(?:[-/.](\d{2,4}))?", t)
        if m:
            y = int(m.group(3)) if m.group(3) else base.year
            y = y + 2000 if y < 100 else y
            d = date(y, int(m.group(2)), int(m.group(1)))
            if not m.group(3) and d < base:
                d = date(y + 1, d.month, d.day)
            return d
    except ValueError:
        return None
    return None


def parse_time(v) -> str:
    """'7', '7:30', '07:30', 'subah 7', 'shaam 5', '5 pm' -> HH:MM; '' when not a clear time."""
    t = str(v or "").strip().lower()
    if not t:
        return ""
    m = re.search(r"(\d{1,2})(?::|\.)?(\d{2})?\s*(am|pm|baje)?", t)
    if not m:
        return ""
    h, mi = int(m.group(1)), int(m.group(2) or 0)
    pm = m.group(3) == "pm" or any(w in t for w in ("shaam", "sham", "raat", "dopahar", "evening", "night"))
    am = m.group(3) == "am" or any(w in t for w in ("subah", "savere", "morning"))
    if pm and h < 12 and not (any(w in t for w in ("dopahar",)) and h >= 11):
        h += 12
    if am and h == 12:
        h = 0
    if h > 23 or mi > 59:
        return ""
    return f"{h:02d}:{mi:02d}"


def minutes(hhmm: str) -> int | None:
    m = re.fullmatch(r"(\d{2}):(\d{2})", hhmm or "")
    return int(m.group(1)) * 60 + int(m.group(2)) if m else None


def hhmm(mins: int) -> str:
    mins = max(0, int(mins)) % (24 * 60)
    return f"{mins // 60:02d}:{mins % 60:02d}"


def days_list(v) -> list[str]:
    out = []
    items = v if isinstance(v, list) else re.split(r"[,/ ]+", str(v or ""))
    for x in items:
        k = str(x).strip().lower()
        if k[:3] in DAYS:
            k = k[:3]
        k = DAY_WORDS.get(k, k)
        if k in DAYS and k not in out:
            out.append(k)
    return out


def lang_of(text: str) -> str:
    t = str(text or "").lower()
    for w, code in LANG_WORDS.items():
        if re.search(rf"(?<!\w){re.escape(w)}(?!\w)", t):
            return code
    return ""


def parse_enquiry(text: str, today: date) -> dict:
    """Only what is written: date, time, guests, phone, email, language. Nothing guessed."""
    t = str(text or "")
    low = t.lower()
    out: dict = {}
    m = re.search(r"\b(\d{1,2}[-/.]\d{1,2}(?:[-/.]\d{2,4})?|\d{4}-\d{1,2}-\d{1,2})\b", t)
    d = parse_date(m.group(1), today) if m else None
    if not d:
        for w in ("parso", "kal", "aaj", "tomorrow", "today"):
            if re.search(rf"\b{w}\b", low):
                d = parse_date(w, today)
                break
    if d:
        out["date"] = d.isoformat()
    m = re.search(r"(\d{1,3})\s*(log|logon|people|persons?|pax|guests?|adults?|members?|jan)\b", low) or \
        re.search(r"group of (\d{1,3})", low)
    if m:
        out["guests"] = int(m.group(1))
    m = re.search(r"((?:subah|savere|shaam|sham|dopahar|morning|evening)\s*\d{1,2}(?::\d{2})?(?:\s*baje)?|\d{1,2}(?::\d{2})?\s*(?:am|pm)|\d{1,2}:\d{2})", low)
    if m:
        tm = parse_time(m.group(1))
        if tm:
            out["start_time"] = tm
    for cand in re.findall(r"(?:\+?91[\s-]?)?[6-9]\d{4}[\s-]?\d{5}", t):
        p = phone10(cand)
        if p:
            out["phone"] = p
            break
    m = re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", t)
    if m:
        out["email"] = m.group(0)[:160]
    lg = lang_of(t)
    if lg:
        out["language"] = lg
    return out


def price_for(price_pp: float | None, price_group: float | None, group_max: int, guests: int) -> tuple[float | None, str]:
    """Her price only. Group price when she gave one (covers up to group_max), else per person x guests; None = blank."""
    if guests <= 0:
        return None, "how many people?"
    if price_group:
        return round(price_group, 2), "group price"
    if price_pp:
        return round(price_pp * guests, 2), f"{guests} x per person"
    return None, "you have not given a price"


def overlaps(a_start: int, a_len: int, b_start: int, b_len: int) -> bool:
    return a_start < b_start + b_len and b_start < a_start + a_len


SAFETY = {
    "common": ["Tell everyone the meeting point and time clearly; everyone should have the group's WhatsApp / phone number.",
               "Carry water; in crowds keep pockets / bags in front; if you get separated from the group, wait at the last stop and call.",
               "Emergency: 112. The guide carries a first aid kit."],
    "city_walk": ["Cross roads only at a zebra crossing / signal; walk in single file; wear comfortable shoes."],
    "heritage": ["No climbing on / writing on / touching the monument; no drones without permission; check the photography rules on the board.",
                 "Everyone carries a ticket (online or counter); carry your ID."],
    "temple": ["Shoes outside; dress by the rules of the place; hold children's hands in crowds; prasad / donations are your own choice."],
    "trek": ["A trek leader and a last-man (sweep) are fixed; no one walks alone ahead / behind.",
             "Guests declare their own medical fitness and medicines (declaration); carry first aid, torch, whistle, rain cover.",
             "The turn-back rule for rain / storm / darkness is fixed in advance; no stopping to bathe near rivers / waterfalls.",
             "Forest / ILP / trek permit (as the place requires) in advance; keep the registered operator / insurance details."],
    "food": ["Ask in advance about allergies (peanut, gluten, milk) and Jain / vegetarian food; sealed bottled water only."],
    "nature": ["Keep your distance from animals, do not feed them, no noise; follow the forest's rules and timings."],
    "boat": ["Life jackets for everyone; no more people than the boat's capacity; children sit on the inner side."],
    "day_trip": ["Everyone has the vehicle number and the driver's phone; head count at every stop."],
}
NEED_NOTES = {
    "wheelchair": "Wheelchair: check ramp / lift routes and toilets beforehand; skip stops with stairs or offer an alternative.",
    "senior": "Seniors: short stops, places to sit, protection from sun / heat.",
    "child": "Children: head count at every stop, hold hands in crowds.",
    "pregnan": "Pregnant guest: avoid long climbs / uneven paths, follow the doctor's advice.",
    "diabet": "Diabetes: do not delay meal times; carry sweets / snacks.",
    "asthma": "Asthma: carry the inhaler; avoid dusty / smoky stops.",
    "allerg": "Allergy: tell the food stop in advance.",
    "heart": "Heart condition: avoid climbs / heat; follow the doctor's advice.",
}


def safety_lines(kind: str, special_needs: str, guests: int, weather: dict | None) -> tuple[list[str], list[str]]:
    lines = list(SAFETY.get(kind, [])) + list(SAFETY["common"])
    low = str(special_needs or "").lower()
    for k, note in NEED_NOTES.items():
        if k in low:
            lines.append(note)
    warns: list[str] = []
    if guests and guests > 15:
        lines.append(f"{guests} people: keep a co-guide / helper, head count at every stop.")
    w = weather or {}
    rain = w.get("rain_chance_pct")
    tmax = w.get("max_c")
    if isinstance(rain, (int, float)) and rain >= 60:
        warns.append(f"Chance of rain {int(rain)}%: umbrella / rain cover; " + ("consider postponing / shortening the trek." if kind in ("trek", "nature", "boat") else "covered stops first."))
    if isinstance(tmax, (int, float)) and tmax >= 38:
        warns.append(f"Heat up to {tmax:.0f}°C: start early in the morning, water / ORS, stay in shade from 12 to 3.")
    if isinstance(tmax, (int, float)) and tmax <= 5:
        warns.append(f"Cold {tmax:.0f}°C: warm clothes, be back from the trek before dark.")
    return lines, warns


INTRO = {
    "hinglish": ("Namaste sabhi ko! Main {guide}, aaj aapki {tour} ki guide hoon. Hum lagbhag {duration} saath rahenge. "
                 "Pehla stop: {first}. Kuch zaroori baatein: {safety} Kisi ko bhi dikkat ho to turant mujhe batayein. "
                 "Mera number: {phone}. Chaliye shuru karte hain!"),
    "hi": ("नमस्ते! मैं {guide}, आज आपकी {tour} की गाइड हूँ। हम लगभग {duration} साथ रहेंगे। पहला पड़ाव: {first}। "
           "ज़रूरी बातें: {safety} कोई भी दिक्कत हो तो तुरंत बताइए। मेरा नंबर: {phone}। चलिए शुरू करते हैं!"),
    "mr": ("नमस्कार! मी {guide}, आज तुमच्या {tour} ची गाइड आहे. आपण साधारण {duration} सोबत असू. पहिला थांबा: {first}. "
           "महत्त्वाचे: {safety} काहीही अडचण असेल तर लगेच सांगा. माझा नंबर: {phone}. चला सुरू करूया!"),
    "en": ("Hello everyone! I'm {guide}, your guide for today's {tour}. We'll be together for about {duration}. First stop: {first}. "
           "A few important things: {safety} If anything bothers you, tell me right away. My number: {phone}. Let's begin!"),
}


def gst_note(mode: str) -> str:
    return GST_MODES.get(mode or "none", GST_MODES["none"])


def trek_checklist() -> list[str]:
    return ["Trek leader trained (IITG Adventure / adventure course) + first aid certificate valid",
            "Guests' medical fitness declaration + emergency contact (ID Locker / masked)",
            "Permit (forest / ILP / trek) - as the place requires, you get it yourself from the official office / portal",
            "Insurance / registered operator details", "Weather check (a day before and in the morning)",
            "Turn-back time and point fixed", "First aid kit, torch, whistle, rope, rain cover"]


def asi_steps(place: str) -> list[str]:
    return [f"{place}: at the ticket counter or online (ASI's ONDC apps: Highway Delite, Pelocal WhatsApp 'Hi' +91 84228 89057, Abhee) - "
            "you book yourself, Hoola does not log in.",
            "The online ticket discount (Rs 5 Indian / Rs 50 foreign) continues (news of Jan 2026); the real rate is on the official site / at the counter.",
            "Opening hours, closed day, ticket rate: confirm only from the monument's board / official site."]
