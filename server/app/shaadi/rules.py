"""Shaadi Sahayak rules: communities and their functions (editable starters), checklist counted back from the date, vendor kinds,
budget heads, wedding registration checklist by law (checklist only, never legal advice), noise-hour check, money / text helpers.

Nothing here invents a muhurat, a price or a date: dates come from her, panchang facts from app.india.days, prices from her
vendors' quotes."""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any

# ---------------------------------------------------------------- communities -> functions (starter list, she edits)
F = {
    "roka": "Roka", "sagai": "Sagai / Engagement", "sakharpuda": "Sakharpuda", "chunni": "Chunni", "kurmai": "Kurmai",
    "gol_dhana": "Gol Dhana", "nichayathartham": "Nichayathartham", "mangni": "Mangni", "aashirbaad": "Aashirbaad",
    "engagement": "Engagement", "adarni": "Adarni", "pellichoopulu": "Pellichoopulu",
    "kelvan": "Kelvan", "mandvo": "Mandvo Mahurat", "haldi": "Haldi", "pithi": "Pithi", "gaye_holud": "Gaye Holud",
    "nalangu": "Nalangu", "mangala_snanam": "Mangala Snanam", "manjha": "Manjha", "madhavsaro": "Madhavsaro",
    "mehendi": "Mehendi", "sangeet": "Sangeet", "garba": "Garba / Dandiya", "chooda": "Chooda", "jaggo": "Jaggo",
    "bridal_shower": "Bridal shower", "tilak": "Tilak",
    "shaadi": "Shaadi (phere)", "lagna": "Lagna", "anand_karaj": "Anand Karaj", "biye": "Biye", "muhurtham": "Muhurtham",
    "pelli": "Pelli", "kalyanam": "Kalyanam", "nikah": "Nikah", "church_wedding": "Church wedding", "lagan": "Lagan",
    "court_marriage": "Court marriage (SMA)",
    "vidaai": "Vidaai", "reception": "Reception", "walima": "Walima", "bou_bhaat": "Bou Bhaat", "griha_pravesh": "Griha pravesh",
}
COMMUNITIES: dict[str, dict[str, Any]] = {
    "hindu_north": {"label": "Hindu (Uttar Bharat)", "law": "hma",
                    "fns": ["roka", "sagai", "haldi", "mehendi", "sangeet", "shaadi", "vidaai", "reception"]},
    "marathi": {"label": "Marathi", "law": "hma", "fns": ["sakharpuda", "kelvan", "haldi", "mehendi", "lagna", "reception"]},
    "gujarati": {"label": "Gujarati", "law": "hma", "fns": ["gol_dhana", "mandvo", "pithi", "garba", "lagna", "reception"]},
    "punjabi": {"label": "Punjabi", "law": "hma",
                "fns": ["roka", "chunni", "mehendi", "sangeet", "chooda", "jaggo", "shaadi", "reception"]},
    "sikh": {"label": "Sikh", "law": "hma", "fns": ["roka", "kurmai", "mehendi", "sangeet", "anand_karaj", "reception"]},
    "marwari": {"label": "Marwari / Rajasthani", "law": "hma", "fns": ["sagai", "tilak", "pithi", "mehendi", "sangeet", "shaadi", "reception"]},
    "bengali": {"label": "Bengali", "law": "hma", "fns": ["aashirbaad", "gaye_holud", "biye", "bou_bhaat"]},
    "tamil": {"label": "Tamil", "law": "hma", "fns": ["nichayathartham", "nalangu", "muhurtham", "reception"]},
    "telugu": {"label": "Telugu", "law": "hma", "fns": ["pellichoopulu", "mangala_snanam", "pelli", "reception"]},
    "malayali": {"label": "Malayali", "law": "hma", "fns": ["engagement", "haldi", "kalyanam", "reception"]},
    "kannada": {"label": "Kannada", "law": "hma", "fns": ["engagement", "haldi", "shaadi", "reception"]},
    "jain": {"label": "Jain", "law": "hma", "fns": ["sagai", "mehendi", "lagna", "reception"]},
    "muslim": {"label": "Muslim", "law": "muslim", "fns": ["mangni", "manjha", "mehendi", "nikah", "walima"]},
    "christian": {"label": "Christian", "law": "christian", "fns": ["engagement", "bridal_shower", "church_wedding", "reception"]},
    "parsi": {"label": "Parsi", "law": "parsi", "fns": ["adarni", "madhavsaro", "lagan", "reception"]},
    "interfaith": {"label": "Different religions / court marriage", "law": "sma", "fns": ["engagement", "mehendi", "court_marriage", "reception"]},
    "other": {"label": "Other", "law": "", "fns": ["engagement", "mehendi", "sangeet", "shaadi", "reception"]},
}
_COMM_WORDS = {
    "marathi": ["marathi", "maharashtrian", "मराठी"], "gujarati": ["gujarati", "gujju", "ગુજરાતી"], "punjabi": ["punjabi", "पंजाबी"],
    "sikh": ["sikh", "anand karaj", "gurdwara"], "marwari": ["marwari", "rajasthani", "baniya"], "bengali": ["bengali", "bangali"],
    "tamil": ["tamil", "iyer", "iyengar"], "telugu": ["telugu", "andhra", "telangana"], "malayali": ["malayali", "kerala"],
    "kannada": ["kannada", "kannadiga"], "jain": ["jain"], "muslim": ["muslim", "nikah", "walima"], "christian": ["christian", "church"],
    "parsi": ["parsi", "zoroastrian"], "interfaith": ["interfaith", "court marriage", "special marriage", "inter caste", "alag dharm"],
    "hindu_north": ["hindu", "north indian", "uttar", "punjabi hindu", "up ", "bihari"],
}

# a ceremony she should not get from us: muhurat, ritual timing — pandit / qazi / priest decides
RITUAL_FNS = {"shaadi", "lagna", "anand_karaj", "biye", "muhurtham", "pelli", "kalyanam", "nikah", "church_wedding", "lagan",
              "sakharpuda", "sagai", "roka", "gol_dhana", "mandvo", "tilak", "kurmai", "nichayathartham", "haldi", "pithi"}

VENDOR_KINDS = {
    "venue": "Venue / hall / lawn", "decor": "Decor / tent", "caterer": "Caterer", "photographer": "Photo / video",
    "mehendi": "Mehendi artist", "dj": "DJ / sound", "band": "Band / drums (dhol)", "pandit": "Pandit / qazi / priest",
    "makeup": "Makeup / hair", "transport": "Cars / bus", "invites": "Card / invites", "choreographer": "Choreographer",
    "anchor": "Anchor / emcee", "lights": "Lights / generator", "florist": "Flowers", "hotel": "Hotel / rooms", "gifts": "Gift / return gifts",
    "attire": "Clothes / designer", "jeweller": "Jewellery", "security": "Security", "other": "Other",
}
_VENDOR_WORDS = {
    "venue": ["venue", "hall", "lawn", "banquet", "mandap", "farmhouse", "resort"], "decor": ["decor", "tent", "mandap decor", "sajawat"],
    "caterer": ["cater", "khana", "food", "halwai", "bhojan"], "photographer": ["photo", "video", "drone", "camera", "cinema"],
    "mehendi": ["mehendi", "mehndi", "henna"], "dj": ["dj", "sound", "speaker"], "band": ["band", "dhol", "shehnai", "baaja"],
    "pandit": ["pandit", "purohit", "qazi", "kazi", "priest", "granthi", "guruji", "panditji"],
    "makeup": ["makeup", "make up", "parlour", "hair"], "transport": ["bus", "car", "gaadi", "tempo", "traveller", "ghodi", "baggi"],
    "invites": ["card", "invite", "patrika", "kankotri"], "choreographer": ["choreo", "dance"], "anchor": ["anchor", "emcee", "host"],
    "lights": ["light", "generator", "genset"], "florist": ["flower", "phool", "florist", "gajra"], "hotel": ["hotel", "room", "stay"],
    "gifts": ["return gift", "gift hamper"], "attire": ["lehenga", "sherwani", "saree", "designer", "kapde"],
    "jeweller": ["jewel", "gehne", "sona"], "security": ["security", "bouncer", "guard"],
}
HEADS = ["venue", "decor", "caterer", "photographer", "mehendi", "dj", "band", "pandit", "makeup", "transport", "invites",
         "hotel", "attire", "jeweller", "gifts", "travel", "lights", "florist", "other"]

# checklist: (days before the FIRST function; negative = after the wedding day), what, kind
CHECKLIST = [
    (240, "Fix the budget and guest count (both sides)", "plan"),
    (210, "Visit and book the venue / hall (block the date)", "venue"),
    (180, "Confirm the auspicious time and date with the pandit / qazi / priest (Hoola does not give muhurat)", "ritual"),
    (165, "Get quotes from the caterer, photographer, decorator", "vendors"),
    (150, "Book the caterer, photographer, decorator (advance only with your approval)", "vendors"),
    (120, "Book clothes / jewellery, makeup artist, mehendi artist", "vendors"),
    (100, "Finalise the guest list from both sides (with phone numbers)", "guests"),
    (90, "Card / e-invite design (Brand Assistant) and text", "invites"),
    (75, "Block rooms for guests coming from outside", "rooms"),
    (60, "Send the invites (with your tap) and start RSVPs", "invites"),
    (60, "Trains / flights for guests coming from outside (IRCTC opens 60 days ahead)", "travel"),
    (45, "Book DJ / band, transport, return gifts", "vendors"),
    (30, "Makeup / mehendi trial, menu tasting", "vendors"),
    (30, "Loudspeaker / police permission (no noise after 10 pm) and check the venue's fire NOC", "permits"),
    (21, "RSVP follow-up, confirm room allocation", "guests"),
    (14, "Give the caterer the final headcount and plate count", "vendors"),
    (10, "Give vendors the timeline for each function", "timeline"),
    (7, "Confirm with all vendors, schedule the remaining payments", "vendors"),
    (3, "Arrival / room / vehicle list for guests", "rooms"),
    (1, "Emergency kit, cash envelopes, contact list", "plan"),
    (-7, "Complete the shagun / gift register; groom and bride sign the no-dowry list", "gifts"),
    (-14, "Settle remaining vendor accounts, photos / video delivery date", "vendors"),
    (-30, "Wedding registration (Maharashtra: within 90 days)", "registration"),
]
EXTRA_CHECKLIST = {
    "christian": [(35, "Banns / notice at the church (parish rules)", "ritual")],
    "muslim": [(30, "Fix the qazi, the nikahnama and the witnesses", "ritual")],
    "sikh": [(60, "Book the Anand Karaj date at the gurdwara", "ritual")],
    "interfaith": [(45, "Special Marriage Act notice to the Marriage Officer (30-day notice period)", "registration")],
    "punjabi": [(20, "Chooda preparation (maternal uncle's side)", "ritual")],
    "parsi": [(45, "Agiary / priest booking", "ritual")],
}

# starter timeline per function (offsets in minutes from her start time); ritual rows only as "pandit ke samay par"
TIMELINE = {
    "default": [(-180, "Decor / sound set-up begins", "decor"), (-60, "Vendors arrive, sound check", "dj"),
                (0, "Guests start arriving", ""), (60, "Main event", ""), (120, "Food", "caterer"), (240, "End / farewell (vidaai)", "")],
    "mehendi": [(-120, "Seating arrangement, mattresses / cushions", "decor"), (0, "Mehendi artist starts (bride first)", "mehendi"),
                (90, "Guests' mehendi, music", "dj"), (150, "Food", "caterer")],
    "sangeet": [(-240, "Stage, lights, sound", "decor"), (-60, "Rehearsal / sound check", "dj"), (0, "Guests arrive", ""),
                (45, "Performances", "choreographer"), (150, "Food", "caterer"), (210, "DJ (until 10 pm)", "dj")],
    "haldi": [(-90, "Flower / marigold decor", "decor"), (0, "Haldi ritual (as per family custom)", ""), (60, "Bath, breakfast", "caterer")],
    "reception": [(-240, "Stage decor, lights", "decor"), (-30, "Photographer ready", "photographer"), (0, "Guests arrive", ""),
                  (30, "Groom and bride on stage", ""), (60, "Food service starts", "caterer"), (210, "End", "")],
}

# registration checklist by law (CHECKLIST ONLY: registrar / vakil decides)
REGISTRATION = {
    "hma": {"law": "Hindu Marriage Act 1955 s.8 + state rules (Hindu, Sikh, Jain, Buddhist)",
            "items": ["Proof of age of both (groom 21+, bride 18+)", "Address proof of both", "Photos of both",
                      "The wedding card / invite", "A photo of the wedding (the ceremony)", "Name and address of the pandit / purohit (a certificate in some places)",
                      "Three witnesses with their IDs", "Divorce decree / death certificate of a spouse (if applicable)"]},
    "muslim": {"law": "Nikahnama + state ki registration (e.g. Maharashtra 1998 Act)",
               "items": ["Nikahnama (a translation if it is in Urdu)", "Proof of age", "Address proof", "Photos", "Witnesses with their IDs"]},
    "christian": {"law": "Indian Christian Marriage Act 1872 (church register / Marriage Registrar)",
                  "items": ["The church's marriage certificate / register entry", "Proof of age", "Photos", "Gawah"]},
    "parsi": {"law": "Parsi Marriage and Divorce Act 1936", "items": ["Priest's certificate", "Proof of age", "Two witnesses", "Photos"]},
    "sma": {"law": "Special Marriage Act 1954 (alag dharm / court marriage)",
            "items": ["Notice to the Marriage Officer (in the district where one party has lived for 30 days)", "30-day notice period (time for objections)",
                      "Proof that the groom is 21+ and the bride 18+", "Address proof", "Three witnesses with their IDs", "Photos",
                      "Divorce / death certificate (if applicable)"]},
}
STATE_NOTES = {"MH": "Maharashtra: Maharashtra Regulation of Marriage Bureaus and Registration of Marriages Act 1998 - registration within 90 days;"
                     "online igrmaharashtra.gov.in; both parties and three witnesses with originals."}

NOISE_START = 22 * 60      # 10 pm (Noise Pollution (Regulation and Control) Rules 2000, rule 5)
NOISE_END = 6 * 60

GUEST_SIDES = ("bride", "groom", "common")
RSVP = ("yes", "no", "maybe", "pending")
CASH_LIMIT = 200000        # Rs 2 lakh cash from one person in a day (Income-tax: old s.269ST)


def community_of(text: str) -> str:
    t = f" {(text or '').lower()} "
    if t.strip() in COMMUNITIES:
        return t.strip()
    for k, words in _COMM_WORDS.items():
        if any(w in t for w in words):
            return k
    return ""


def vendor_kind(text: str) -> str:
    t = (text or "").lower().strip()
    if t in VENDOR_KINDS:
        return t
    for k, words in _VENDOR_WORDS.items():
        if any(w in t for w in words):
            return k
    return "other"


def fn_key(text: str) -> str:
    t = (text or "").lower().strip().replace(" ", "_")
    if t in F:
        return t
    for k, label in F.items():
        if t and (t in k or t.replace("_", " ") in label.lower()):
            return k
    return ""


def digest(obj: Any) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()


def clean(text: Any, n: int = 500) -> str:
    """Her / client / guest words: secrets never kept (OTP / PIN / password values, card-like / Aadhaar-like numbers)."""
    t = str(text or "")
    t = re.sub(r"\b(otp|pin|cvv|password|upi pin)\b\s*(?:is|hai|:|=)?\s*\S+", lambda m: f"{m.group(1)} [hataya]", t, flags=re.I)
    t = re.sub(r"\b(?:\d[ -]?){12,19}\b", "[hataya]", t)
    return t.strip()[:n]


def phone(text: Any) -> str:
    d = re.sub(r"\D", "", str(text or ""))
    if len(d) == 12 and d.startswith("91"):
        d = d[2:]
    return d if re.fullmatch(r"[6-9]\d{9}", d) else ""


def mask_name(name: str) -> str:
    """'Sunita Mehra' -> 'Sunita M.' (gift register outside her own screen)."""
    parts = (name or "").split()
    if not parts:
        return ""
    return parts[0] if len(parts) == 1 else f"{parts[0]} {parts[-1][0]}."


def hhmm(v: Any) -> int | None:
    """'7 pm' / '19:30' / '7:30 shaam' -> minutes from midnight; None if not understood."""
    s = str(v or "").strip().lower()
    if not s:
        return None
    m = re.match(r"^(\d{1,2})(?::|\.)?(\d{2})?\s*(am|pm|subah|dopahar|shaam|sham|raat)?$", s)
    if not m:
        return None
    h, mi, ap = int(m.group(1)), int(m.group(2) or 0), m.group(3)
    if ap in ("pm", "shaam", "sham", "raat", "dopahar") and h < 12:
        h += 12
    if ap == "raat" and h == 24:
        h = 0
    if ap in ("am", "subah") and h == 12:
        h = 0
    if h > 23 or mi > 59:
        return None
    return h * 60 + mi


def fmt(mins: int | None) -> str:
    if mins is None:
        return ""
    mins %= 24 * 60
    return f"{mins // 60:02d}:{mins % 60:02d}"


def noise_problem(start: int | None, end: int | None, loud: bool) -> str:
    """Loudspeaker / DJ / band running into 10 pm - 6 am (Noise Rules 2000 rule 5; states may allow up to midnight on a few days)."""
    if not loud or start is None:
        return ""
    e = end if end is not None else start + 180
    if e <= start:
        e += 24 * 60
    if e > NOISE_START or start < NOISE_END:
        return ("No DJ / band / loudspeaker between 10 pm and 6 am (Noise Pollution Rules 2000). "
                "A closed hall has different rules; check police / district permission.")
    return ""


def age_problem(age_bride: Any, age_groom: Any) -> str:
    """Prohibition of Child Marriage Act 2006: bride 18+, groom 21+. Hoola never plans a child marriage."""
    try:
        if age_bride not in (None, "") and int(age_bride) < 18:
            return "The bride is under 18: this is a child marriage (Prohibition of Child Marriage Act 2006). Hoola will not plan this wedding."
        if age_groom not in (None, "") and int(age_groom) < 21:
            return "The groom is under 21: this is a child marriage (Prohibition of Child Marriage Act 2006). Hoola will not plan this wedding."
    except (TypeError, ValueError):
        return ""
    return ""


DOWRY_WORDS = re.compile(r"\b(dahej|dowry|daheja|tilak ki rakam|var dakshina)\b", re.I)


def dowry_problem(text: str) -> str:
    if DOWRY_WORDS.search(text or ""):
        return ("Asking for or giving dowry is an offence (Dowry Prohibition Act 1961). Hoola will not keep accounts or write messages for it. "
                "Shagun / gifts can be written in the register.")
    return ""
