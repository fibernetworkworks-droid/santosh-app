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
    "interfaith": {"label": "Alag dharm / court marriage", "law": "sma", "fns": ["engagement", "mehendi", "court_marriage", "reception"]},
    "other": {"label": "Doosra", "law": "", "fns": ["engagement", "mehendi", "sangeet", "shaadi", "reception"]},
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
    "mehendi": "Mehendi artist", "dj": "DJ / sound", "band": "Band / dhol", "pandit": "Pandit / qazi / priest",
    "makeup": "Makeup / hair", "transport": "Gaadi / bus", "invites": "Card / invites", "choreographer": "Choreographer",
    "anchor": "Anchor / emcee", "lights": "Lights / generator", "florist": "Phool", "hotel": "Hotel / rooms", "gifts": "Gift / return gifts",
    "attire": "Kapde / designer", "jeweller": "Gehne", "security": "Security", "other": "Doosra",
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
    (240, "Budget aur mehmaan ki ginti tay (dono taraf)", "plan"),
    (210, "Venue / hall dekhna aur book karna (date block)", "venue"),
    (180, "Pandit / qazi / priest se muhurat aur date pakki karwana (Hoola muhurat nahi batata)", "ritual"),
    (165, "Caterer, photographer, decor ke quote lena", "vendors"),
    (150, "Caterer, photographer, decor book (advance aapki haan se)", "vendors"),
    (120, "Kapde / gehne, makeup artist, mehendi artist book", "vendors"),
    (100, "Mehmaan list dono taraf se pakki (phone ke saath)", "guests"),
    (90, "Card / e-invite design (Brand Sahayak) aur text", "invites"),
    (75, "Bahar se aane walon ke rooms block karna", "rooms"),
    (60, "Invite bhejna (aapke tap se) aur RSVP shuru", "invites"),
    (60, "Bahar se aane walon ki train / flight (IRCTC 60 din pehle khulta hai)", "travel"),
    (45, "DJ / band, transport, return gifts book", "vendors"),
    (30, "Makeup / mehendi trial, menu tasting", "vendors"),
    (30, "Loudspeaker / police permission (raat 10 baje ke baad shor nahi) aur venue ka fire NOC dekhna", "permits"),
    (21, "RSVP follow-up, room allocation pakka", "guests"),
    (14, "Caterer ko final headcount, plate count", "vendors"),
    (10, "Function-wise timeline vendors ko dena", "timeline"),
    (7, "Saare vendors se confirm, baaki payment schedule", "vendors"),
    (3, "Mehmaan ke liye arrival / room / gaadi list", "rooms"),
    (1, "Emergency kit, nakad lifafe, contact list", "plan"),
    (-7, "Shagun / gift register poora karna; dahej rules ki list par dulha-dulhan ke sign", "gifts"),
    (-14, "Vendors ka baaki hisaab, photos / video delivery date", "vendors"),
    (-30, "Shaadi registration (Maharashtra: 90 din ke andar)", "registration"),
]
EXTRA_CHECKLIST = {
    "christian": [(35, "Church mein banns / notice (parish ke niyam)", "ritual")],
    "muslim": [(30, "Qazi aur nikahnama, gawah (witnesses) tay", "ritual")],
    "sikh": [(60, "Gurdwara mein Anand Karaj ki date book", "ritual")],
    "interfaith": [(45, "Special Marriage Act notice Marriage Officer ko (30 din ka notice period)", "registration")],
    "punjabi": [(20, "Chooda ki taiyaari (mama ki taraf)", "ritual")],
    "parsi": [(45, "Agiary / priest ki booking", "ritual")],
}

# starter timeline per function (offsets in minutes from her start time); ritual rows only as "pandit ke samay par"
TIMELINE = {
    "default": [(-180, "Decor / sound set-up shuru", "decor"), (-60, "Vendors pahunche, sound check", "dj"),
                (0, "Mehmaan aana shuru", ""), (60, "Mukhya karyakram", ""), (120, "Khana", "caterer"), (240, "Samaapt / vidaai", "")],
    "mehendi": [(-120, "Baithne ki vyavastha, gaddi / cushions", "decor"), (0, "Mehendi artist shuru (dulhan pehle)", "mehendi"),
                (90, "Mehmaan ki mehendi, music", "dj"), (150, "Khana", "caterer")],
    "sangeet": [(-240, "Stage, lights, sound", "decor"), (-60, "Rehearsal / sound check", "dj"), (0, "Mehmaan aana", ""),
                (45, "Performances", "choreographer"), (150, "Khana", "caterer"), (210, "DJ (raat 10 baje tak)", "dj")],
    "haldi": [(-90, "Phool / genda decor", "decor"), (0, "Haldi ki rasm (ghar ke rivaaj)", ""), (60, "Snaan, nashta", "caterer")],
    "reception": [(-240, "Stage decor, lights", "decor"), (-30, "Photographer taiyaar", "photographer"), (0, "Mehmaan aana", ""),
                  (30, "Dulha-dulhan stage par", ""), (60, "Khana shuru", "caterer"), (210, "Samaapt", "")],
}

# registration checklist by law (CHECKLIST ONLY: registrar / vakil decides)
REGISTRATION = {
    "hma": {"law": "Hindu Marriage Act 1955 s.8 + state rules (Hindu, Sikh, Jain, Buddhist)",
            "items": ["Dono ki umr ka saboot (dulha 21+, dulhan 18+)", "Dono ka pata saboot", "Dono ki photos",
                      "Shaadi ki card / invite", "Shaadi ki photo (rasm ki)", "Pandit / purohit ka naam-pata (kahin kahin certificate)",
                      "Teen gawah unke ID ke saath", "Talaq ka decree / pati-patni ki death certificate (agar lagu)"]},
    "muslim": {"law": "Nikahnama + state ki registration (e.g. Maharashtra 1998 Act)",
               "items": ["Nikahnama (Urdu ho to anuvaad)", "Umr ka saboot", "Pata saboot", "Photos", "Gawah unke ID ke saath"]},
    "christian": {"law": "Indian Christian Marriage Act 1872 (church register / Marriage Registrar)",
                  "items": ["Church ka marriage certificate / register entry", "Umr ka saboot", "Photos", "Gawah"]},
    "parsi": {"law": "Parsi Marriage and Divorce Act 1936", "items": ["Priest ka certificate", "Umr ka saboot", "Do gawah", "Photos"]},
    "sma": {"law": "Special Marriage Act 1954 (alag dharm / court marriage)",
            "items": ["Marriage Officer ko notice (ek ke 30 din se rehne ki jagah wale district mein)", "30 din ka notice period (aapatti ka samay)",
                      "Dulha 21+, dulhan 18+ ka saboot", "Pata saboot", "Teen gawah unke ID ke saath", "Photos",
                      "Talaq / death certificate (agar lagu)"]},
}
STATE_NOTES = {"MH": "Maharashtra: Maharashtra Regulation of Marriage Bureaus and Registration of Marriages Act 1998 - 90 din ke andar "
                     "registration; online igrmaharashtra.gov.in; dono aur teen gawah originals ke saath."}

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
        return ("DJ / band / loudspeaker raat 10 se subah 6 baje ke beech nahi (Noise Pollution Rules 2000). "
                "Band hall ho to alag niyam; police / district permission dekhiye.")
    return ""


def age_problem(age_bride: Any, age_groom: Any) -> str:
    """Prohibition of Child Marriage Act 2006: bride 18+, groom 21+. Hoola never plans a child marriage."""
    try:
        if age_bride not in (None, "") and int(age_bride) < 18:
            return "Dulhan 18 saal se kam hai: yeh baal vivah hai (Prohibition of Child Marriage Act 2006). Hoola yeh shaadi plan nahi karega."
        if age_groom not in (None, "") and int(age_groom) < 21:
            return "Dulha 21 saal se kam hai: yeh baal vivah hai (Prohibition of Child Marriage Act 2006). Hoola yeh shaadi plan nahi karega."
    except (TypeError, ValueError):
        return ""
    return ""


DOWRY_WORDS = re.compile(r"\b(dahej|dowry|daheja|tilak ki rakam|var dakshina)\b", re.I)


def dowry_problem(text: str) -> str:
    if DOWRY_WORDS.search(text or ""):
        return ("Dahej maangna / dena apradh hai (Dowry Prohibition Act 1961). Hoola iska hisaab ya message nahi banayega. "
                "Shagun / tohfe register mein likhe ja sakte hain.")
    return ""
