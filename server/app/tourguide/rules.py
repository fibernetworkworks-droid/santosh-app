"""Tour Guide Sahayak rules: plain-words notes with dated sources, small parsers, safety briefs, script templates.

Nothing here invents a price, a monument timing, a ticket rate or a date: timings / tickets come only from what she typed (or the
official site she names as the source); everything else stays blank / "pata nahi". Tax lines are notes for her CA, not advice."""
from __future__ import annotations

import re
from datetime import date, datetime, timedelta

NEVER = (
    "Guest ko koi message / booking confirmation khud nahi bhejna: har message draft ya card, sirf aapke tap se jaata hai.",
    "Refund, discount ya koi bhi kharcha: sirf aapki haan (app ka card; paise wale card par fingerprint) se. Hoola paise nahi leta / deta.",
    "Daam, monument ke khulne ka samay, band ka din, ticket ka rate: sirf aapke bataye (ya official site jo aap batayein); warna 'pata nahi'.",
    "Ek tour slot mein group se zyada log, ya ek hi samay par aapke do tour: code mana kar deta hai (overbooking nahi).",
    "Guest ke ID / emergency number sirf Pehchaan Locker mein (masked reference); OTP / PIN / card kabhi nahi.",
    "Dukaan / emporium par guests ko zabardasti nahi le jaana; commission ho to guests ko saaf batana (aapka hisaab register mein).",
    "OTA / booking site / ASI portal mein Hoola login ya scraping nahi karta: aap khud book karti hain, Hoola steps aur yaad dilata hai.",
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
                 "iitg_adventure": "IITG Adventure (MoT)", "rlg": "Regional Level Guide (purana MoT licence)",
                 "state": "State tourism guide licence", "asi_site": "Monument / site guide permit", "first_aid": "First aid certificate",
                 "adventure": "Adventure / trek leader certificate", "other": "Doosra licence"}
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
GST_MODES = {"none": "GST registration nahi (CA se pakka: services par Rs 20 lakh / special states Rs 10 lakh se kam turnover)",
             "guide": "Tourist guide service: SAC 998556, 18% (ITC ke saath) - CA se pakka",
             "tour5": "Tour operator package: SAC 998555, 5% bina ITC - CA se pakka",
             "tour18": "Tour operator package: 18% ITC ke saath - CA se pakka"}


def scrub(text: str, n: int = 2000) -> str:
    """Free text: OTP / PIN / password values, card-like runs, Aadhaar-like 12 digits and PAN are never kept."""
    t = str(text or "")
    t = re.sub(r"\b(otp|pin|cvv|password|upi pin|mpin)\b\s*(?:is|hai|:|=)?\s*\S+", lambda m: f"{m.group(1)} [hataya]", t, flags=re.I)
    t = re.sub(r"\b(?:\d[ -]?){13,19}\b", "[hataya]", t)
    t = re.sub(r"\b\d{4}\s?\d{4}\s?\d{4}\b", "[ID hataya]", t)
    t = re.sub(r"\b[A-Z]{5}\d{4}[A-Z]\b", "[PAN hataya]", t)
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
        return None, "kitne log?"
    if price_group:
        return round(price_group, 2), "group ka daam"
    if price_pp:
        return round(price_pp * guests, 2), f"{guests} x per person"
    return None, "daam aapne nahi bataya"


def overlaps(a_start: int, a_len: int, b_start: int, b_len: int) -> bool:
    return a_start < b_start + b_len and b_start < a_start + a_len


SAFETY = {
    "common": ["Meeting point aur samay sabko saaf batayein; group ka WhatsApp / phone number sabke paas ho.",
               "Paani saath rakhein; bheed mein jeb / bag aage rakhein; group se alag ho jaayein to pichhle stop par rukein, phone karein.",
               "Emergency: 112. Guide ke paas first aid kit."],
    "city_walk": ["Sadak paar sirf zebra / signal par; ek line mein chalein; aaraam wale joote."],
    "heritage": ["Smarak par chadhna / likhna / chhoona mana; drone bina permission mana; photography ke niyam board par dekhein.",
                 "Ticket sabke paas (online ya counter); ID saath rakhein."],
    "temple": ["Joote bahar; kapde jagah ke niyam ke hisaab se; bheed mein bachchon ka haath pakdein; prasad / daan apni marzi se."],
    "trek": ["Trek leader aur last-man (sweep) tay; koi aage / peeche akela nahi.",
             "Medical fitness aur dawai guests khud batayein (declaration); first aid, torch, whistle, rain cover saath.",
             "Baarish / toofan / andhera ho to waapas mudne ka niyam pehle se tay; nadi / jharne ke paas ruk kar nahi nahana.",
             "Forest / ILP / trek permit (jagah ke hisaab se) pehle se; registered operator / insurance ki jaankari rakhein."],
    "food": ["Allergy (moongphali, gluten, doodh), jain / vegetarian pehle se poochh lein; paani band bottle ka."],
    "nature": ["Janwaron se doori, khana na daalein, shor nahi; forest ke niyam aur samay ka paalan."],
    "boat": ["Life jacket sabke liye; boat ki kshamta se zyada log nahi; baccho ko andar ki taraf."],
    "day_trip": ["Gaadi ka number aur driver ka phone sabke paas; har stop par ginti."],
}
NEED_NOTES = {
    "wheelchair": "Wheelchair: ramp / lift waale raaste aur toilet pehle check karein; seedhiyon wale stop chhodein ya vikalp batayein.",
    "senior": "Bade-buzurg: chhote stop, baithne ki jagah, dhoop / garmi se bachav.",
    "child": "Bachche: ginti har stop par, haath pakad kar bheed mein.",
    "pregnan": "Garbhvati guest: lambi chadhai / uneven raaste se bachein, doctor ki salah.",
    "diabet": "Diabetes: khane ka samay na tale; meetha / snack saath.",
    "asthma": "Asthma: inhaler saath; dhool / dhuan wale stop se bachein.",
    "allerg": "Allergy: khane ke stop par pehle bata dein.",
    "heart": "Dil ki bimari: chadhai / garmi se bachein; doctor ki salah.",
}


def safety_lines(kind: str, special_needs: str, guests: int, weather: dict | None) -> tuple[list[str], list[str]]:
    lines = list(SAFETY.get(kind, [])) + list(SAFETY["common"])
    low = str(special_needs or "").lower()
    for k, note in NEED_NOTES.items():
        if k in low:
            lines.append(note)
    warns: list[str] = []
    if guests and guests > 15:
        lines.append(f"{guests} log: ek co-guide / helper rakhein, har stop par ginti.")
    w = weather or {}
    rain = w.get("rain_chance_pct")
    tmax = w.get("max_c")
    if isinstance(rain, (int, float)) and rain >= 60:
        warns.append(f"Baarish ki sambhavna {int(rain)}%: chhata / rain cover; " + ("trek ko taalna / chhota karna sochiye." if kind in ("trek", "nature", "boat") else "chhat wale stop pehle."))
    if isinstance(tmax, (int, float)) and tmax >= 38:
        warns.append(f"Garmi {tmax:.0f}°C tak: subah jaldi shuru, paani / ORS, 12-3 baje chhaya mein.")
    if isinstance(tmax, (int, float)) and tmax <= 5:
        warns.append(f"Thand {tmax:.0f}°C: garam kapde, trek par andhera hone se pehle waapas.")
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
            "Guests ka medical fitness declaration + emergency contact (Pehchaan Locker / masked)",
            "Permit (forest / ILP / trek) - jagah ke hisaab se, aap khud official office / portal se",
            "Insurance / registered operator ki jaankari", "Mausam check (ek din pehle aur subah)",
            "Waapas mudne ka samay aur jagah tay", "First aid kit, torch, whistle, rassi, rain cover"]


def asi_steps(place: str) -> list[str]:
    return [f"{place}: ticket counter par ya online (ASI wale ONDC apps: Highway Delite, Pelocal WhatsApp 'Hi' +91 84228 89057, Abhee) - "
            "aap khud book karein, Hoola login nahi karta.",
            "Online ticket par chhoot (Rs 5 Indian / Rs 50 foreign) jaari hai (Jan 2026 khabar); asli rate official site / counter par.",
            "Khulne ka samay, band ka din, ticket ka rate: sirf monument ke board / official site se pakka karein."]
