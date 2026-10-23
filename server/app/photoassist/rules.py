"""Photo Sahayak rules: shoot kinds, starter shot lists and gear lists, time windows and the no-double-booking overlap, location /
drone / minor / monument checks, release texts, GST / TDS notes, payment schedule and refund tiers. Pure functions (no DB).

Everything here is a STARTER she can change; legal lines are plain-words notes, not legal advice (sources in WIRING.md)."""
from __future__ import annotations

import hashlib
import json
import re
from datetime import date, timedelta
from typing import Any

KINDS = ("wedding", "pre_wedding", "engagement", "event", "birthday", "corporate", "product", "food", "fashion", "portrait",
         "maternity", "newborn", "kids", "real_estate", "other")
KIND_LABEL = {"wedding": "Shaadi", "pre_wedding": "Pre-wedding", "engagement": "Sagai", "event": "Event", "birthday": "Birthday",
              "corporate": "Corporate", "product": "Product", "food": "Food", "fashion": "Fashion / model", "portrait": "Portrait",
              "maternity": "Maternity", "newborn": "Newborn", "kids": "Bachche", "real_estate": "Property / interior",
              "other": "Doosra"}
KIND_WORDS = [
    ("pre_wedding", r"pre[\s-]?wedding|prewed|pre wed|couple shoot"),
    ("engagement", r"engagement|sagai|sagaai|ring ceremony|roka"),
    ("wedding", r"shaadi|shadi|wedding|vivah|lagna|लग्न|शादी|haldi|mehendi|mehndi|sangeet|baraat|reception"),
    ("newborn", r"newborn|new born|naya bachcha|naamkaran|naming ceremony"),
    ("maternity", r"maternity|baby shower|godh bharai|dohale|गोद भराई"),
    ("birthday", r"birthday|janamdin|janmdin|bday"),
    ("kids", r"\bkids?\b|bachch?on|bachche"),
    ("product", r"product|ecommerce|e-commerce|catalog|catalogue|amazon listing|flipkart listing|packshot"),
    ("food", r"\bfood\b|menu shoot|restaurant shoot|dish"),
    ("fashion", r"fashion|model portfolio|lookbook|garment"),
    ("real_estate", r"real estate|property shoot|interior shoot|architecture|flat shoot"),
    ("corporate", r"corporate|office|conference|seminar|headshot|company|annual day"),
    ("portrait", r"portrait|profile photo|family photo|studio photo"),
    ("event", r"event|function|party|puja|pooja|launch|concert|show"),
]
MINOR_KINDS = ("newborn", "kids", "birthday")

SHOT_LISTS: dict[str, list[tuple[str, bool]]] = {
    "wedding": [("Dulhan taiyaar hote hue (details: lehenga, gehne, mehendi)", True), ("Dulha taiyaar / sehra", True),
                ("Baraat aagman", True), ("Jaimala / varmala", True), ("Pheras / mandap ki rasmein", True),
                ("Kanyadaan / sindoor / mangalsutra", True), ("Family group photos (list client se lijiye)", True),
                ("Couple portraits", True), ("Vidaai", False), ("Decor, stage, venue wide shots", False),
                ("Mehmaan candid", False)],
    "pre_wedding": [("Location ke wide shots", True), ("Couple close portraits", True), ("Walking / candid moments", True),
                    ("Outfit change ke baad set", False), ("Golden hour shots", False)],
    "engagement": [("Ring exchange", True), ("Couple portraits", True), ("Family group", True), ("Decor", False)],
    "event": [("Venue / setup wide", True), ("Mukhya mehmaan aagman", True), ("Stage / speech", True), ("Crowd candid", False),
              ("Branding / banners", False)],
    "birthday": [("Cake cutting", True), ("Birthday person portraits", True), ("Family group", True), ("Decor", False),
                 ("Games / candid", False)],
    "corporate": [("Headshots (list naamon ki)", True), ("Team group photo", True), ("Office / workspace", False),
                  ("Event stage / awards", False)],
    "product": [("Har product white background (front / back / side)", True), ("Detail / texture close-up", True),
                ("Lifestyle / in-use shot", False), ("Size / scale shot", False), ("Packaging", False)],
    "food": [("Hero dish top-angle", True), ("45 degree angle", True), ("Ingredients / process", False), ("Ambience", False)],
    "fashion": [("Full look front / back", True), ("Detail close-up", True), ("Movement shots", False), ("Portrait", False)],
    "portrait": [("Close-up", True), ("Half body", True), ("Full body", False), ("Alag background / outfit", False)],
    "maternity": [("Couple portraits", True), ("Bump silhouette", True), ("Family", False)],
    "newborn": [("Baby close-ups (soye hue, safe pose)", True), ("Parents ke saath", True), ("Details: haath, pair", False)],
    "kids": [("Candid khelte hue", True), ("Portrait", True), ("Family", False)],
    "real_estate": [("Har kamre ka wide (corner se)", True), ("Kitchen / bathroom", True), ("Building exterior", True),
                    ("Amenities", False), ("Twilight exterior", False)],
    "other": [("Mukhya shots (client se list lijiye)", True)],
}

GEAR_KINDS = ("camera", "lens", "flash", "light", "drone", "battery", "card", "stand", "gimbal", "mic", "laptop", "other")
GEAR_NEED: dict[str, list[str]] = {
    "_base": ["camera", "lens", "battery", "card"],
    "wedding": ["flash", "light", "stand"], "event": ["flash"], "birthday": ["flash"], "engagement": ["flash"],
    "corporate": ["flash", "light", "stand"], "product": ["light", "stand"], "food": ["light", "stand"],
    "fashion": ["light", "stand"], "portrait": ["light"], "newborn": ["light"], "maternity": ["light"], "real_estate": ["stand"],
}
GEAR_EXTRA_LINES = ["Spare batteries charged", "Memory cards khaali / format kiye (purani shoot ka backup pehle)", "Lens saaf",
                    "Second body ya backup camera", "Card reader / laptop backup"]

PLACE_KINDS = ("private", "venue", "public", "monument", "studio", "other")
MONUMENT_WORDS = r"\b(qila|quila|fort|mahal|maqbara|tomb|monument|asi|heritage|haveli|stepwell|baoli|vav|minar|taj mahal)\b|किला|महल"
VENUE_WORDS = r"\b(hotel|resort|banquet|lawn|hall|mall|cafe|restaurant|club|farmhouse|farm house|palace)\b"
PUBLIC_WORDS = r"\b(beach|road|market|bazaar|park|garden|ghat|station|metro|street|lake|bridge)\b"
RAIL_WORDS = r"\b(railway|station|metro|train)\b"
AIRPORT_WORDS = r"\b(airport|hawai adda|airbase|air force|cantonment|army|naval)\b"


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


def kind_of(text: Any) -> str:
    t = str(text or "").lower().strip()
    if t in KINDS:
        return t
    for k, rx in KIND_WORDS:
        if re.search(rx, t, re.I):
            return k
    return "other"


def hhmm(v: Any, default: str = "") -> str:
    """'16:00', '4 pm', 'shaam 4 baje', 'subah 7', '7:30' -> 'HH:MM' ('' when not a time)."""
    s = str(v or "").strip().lower()
    if not s:
        return default
    m = re.search(r"(\d{1,2})(?:[:.](\d{2}))?\s*(am|pm|baje|bje)?", s)
    if not m:
        return default
    h, mi, ap = int(m.group(1)), int(m.group(2) or 0), m.group(3) or ""
    pm = ap == "pm" or re.search(r"shaam|sham|raat|dopahar|evening|night|afternoon", s)
    am = ap == "am" or re.search(r"subah|morning|savere", s)
    if pm and h < 12 and not (re.search(r"raat", s) and h == 12):
        h += 12
    if am and h == 12:
        h = 0
    if not (pm or am) and ap in ("baje", "bje") and 1 <= h <= 6:
        h += 12                                                    # "4 baje" for a shoot = afternoon
    if h > 23 or mi > 59:
        return default
    return f"{h:02d}:{mi:02d}"


def minutes(t: str) -> int:
    h, m = t.split(":")
    return int(h) * 60 + int(m)


def windows(day: str, end_day: str, start: str, end: str) -> list[tuple[str, int, int]]:
    """Busy windows per date in minutes [from, to). No time = the whole day; a multi-day shoot = whole days."""
    try:
        d0 = date.fromisoformat(day)
    except (TypeError, ValueError):
        return []
    try:
        d1 = date.fromisoformat(end_day) if end_day else d0
    except ValueError:
        d1 = d0
    if d1 < d0:
        d1 = d0
    out = []
    multi = d1 > d0
    cur = d0
    while cur <= d1 and len(out) < 15:
        if multi or not start:
            out.append((cur.isoformat(), 0, 24 * 60))
        else:
            a = minutes(start)
            b = minutes(end) if end else min(a + 4 * 60, 24 * 60)
            if b <= a:                                             # past midnight: rest of the day + next morning
                out.append((cur.isoformat(), a, 24 * 60))
                out.append(((cur + timedelta(days=1)).isoformat(), 0, b))
            else:
                out.append((cur.isoformat(), a, b))
        cur += timedelta(days=1)
    return out


def overlap(w1: list[tuple[str, int, int]], w2: list[tuple[str, int, int]], buffer: int = 0) -> bool:
    """True when two shoots touch (with her travel buffer in minutes on both sides)."""
    for d1, a1, b1 in w1:
        for d2, a2, b2 in w2:
            if d1 == d2 and a1 < b2 + buffer and a2 < b1 + buffer:
                return True
    return False


def place_kind(location: str, given: str = "") -> str:
    g = str(given or "").lower()
    if g in PLACE_KINDS:
        return g
    t = str(location or "").lower()
    if re.search(MONUMENT_WORDS, t, re.I):
        return "monument"
    if re.search(r"\bstudio\b", t):
        return "studio"
    if re.search(VENUE_WORDS, t, re.I):
        return "venue"
    if re.search(PUBLIC_WORDS, t, re.I):
        return "public"
    return "private" if t else "other"


def shoot_checks(kind: str, location: str, place: str, drone: bool, commercial_use: bool, minors: bool,
                 drone_ok: dict | None = None) -> list[dict]:
    """Plain-words checks before a shoot (level: block | warn | note). Hoola never 'clears' a permission: she checks / applies."""
    out: list[dict] = []
    loc = str(location or "").lower()
    if place == "monument":
        out.append({"level": "warn", "key": "asi", "say": "ASI / state ki suraksheet monument par professional shoot (pre-wedding bhi) "
                    "ke liye pehle permission chahiye (ASI ka SAHMAT portal / us circle ka office; fee aur din unki list se)."})
    if place in ("venue", "private"):
        out.append({"level": "note", "key": "venue_ok", "say": "Venue / ghar ke maalik ki shoot permission (aur portfolio / commercial "
                    "use ho to property release) le lijiye."})
    if place == "public":
        out.append({"level": "note", "key": "public", "say": "Public jagah: tripod / bade setup ke liye local permission (nagar nigam / "
                    "police) lag sakti hai; bheed ke chehre commercial use mein ho to unki model release chahiye."})
    if re.search(RAIL_WORDS, loc, re.I):
        out.append({"level": "warn", "key": "rail", "say": "Railway / metro parisar mein shoot ke liye rail / metro prashasan ki permission chahiye."})
    if drone:
        d = drone_ok or {}
        if not d.get("uin"):
            out.append({"level": "warn", "key": "drone_uin", "say": "Drone (250 g se upar): Digital Sky par UIN registration chahiye; "
                        "gear mein drone ka UIN likh dijiye."})
        if not d.get("rpc"):
            out.append({"level": "warn", "key": "drone_rpc", "say": "Paise lekar (commercial) drone udane ke liye Remote Pilot Certificate "
                        "(DGCA-authorised RPTO se) chahiye; nano (250 g tak) ko chhod kar. Niyam mein RPC number aur tareekh daaliye."})
        if not d.get("insured"):
            out.append({"level": "warn", "key": "drone_ins", "say": "Drone ka third-party insurance (250 g se upar) zaroori hai: gear mein "
                        "insurance ki aakhri tareekh daaliye."})
        out.append({"level": "note", "key": "drone_zone", "say": "Udaan se pehle Digital Sky ke airspace map par zone dekhiye: green "
                    "(120 m / 400 ft tak) theek; yellow = permission; red = mana. Bheed ke upar mat udaiye."})
        if re.search(AIRPORT_WORDS, loc, re.I):
            out.append({"level": "warn", "key": "drone_airport", "say": "Jagah airport / defence ke paas lagti hai: yellow / red zone ho sakta "
                        "hai, permission ke bina drone nahi."})
        if place == "monument":
            out.append({"level": "warn", "key": "drone_asi", "say": "Monument par drone: aviation (Digital Sky) ke saath ASI ki alag permission."})
    if minors or kind in MINOR_KINDS:
        out.append({"level": "warn", "key": "minor", "say": "Bachchon ki photo: maa-baap / guardian ki likhit consent (DPDP Act s.9) aur "
                    "portfolio / social media par lagane ki alag haan zaroori; bina haan ke bachche ki photo public mat kijiye."})
    if commercial_use:
        out.append({"level": "warn", "key": "release", "say": "Photo ad / product / stock mein jayegi: har pehchaan-yogya vyakti ki model "
                    "release aur private jagah ki property release pehle."})
    if kind == "newborn":
        out.append({"level": "note", "key": "newborn_safe", "say": "Newborn: sirf surakshit pose, garam kamra, maa-baap paas; props par "
                    "bachche ko akela nahi."})
    return out


# ---- releases --------------------------------------------------------------------------------------------------------------
RELEASE_KINDS = ("model", "minor", "property")
USES = ("client_personal", "portfolio", "social_media", "advertising", "stock", "print_exhibition")
USE_LABEL = {"client_personal": "client ka niji upyog", "portfolio": "photographer ka portfolio / website",
             "social_media": "photographer ka social media", "advertising": "ad / brand promotion", "stock": "stock agency",
             "print_exhibition": "print / exhibition"}


def release_text(kind: str, studio: str, person: str, guardian: str, place: str, uses: list[str], shoot_line: str,
                 lang: str = "en") -> str:
    """Plain release / consent text she gets signed (paper or her phone). Not legal advice: her lawyer can change it."""
    use_txt = ", ".join(USE_LABEL.get(u, u) for u in uses) or "[upyog likhiye]"
    who = studio or "[photographer / studio]"
    if lang == "hi":
        if kind == "property":
            return (f"Main, {person or '[naam]'}, {place or '[pata]'} ka maalik / adhikrit vyakti, {who} ko {shoot_line} mein is jagah ki "
                    f"photo / video lene aur unhe in kaamon mein upyog karne ki anumati deta / deti hoon: {use_txt}. Main kabhi bhi "
                    "likh kar aage ke upyog ki anumati wapas le sakta / sakti hoon; jo pehle chhap chuka hai woh wapas nahi hoga.")
        sub = f"{person or '[bachche ka naam]'} (nabalig) ki taraf se main, {guardian or '[maa / pita / guardian]'}," if kind == "minor" \
            else f"Main, {person or '[naam]'},"
        return (f"{sub} {who} ko {shoot_line} mein li gayi meri / unki photo / video in kaamon mein upyog karne ki anumati deta / deti "
                f"hoon: {use_txt}. Mujhe bataya gaya hai ki photo kis kaam aayegi. Main kabhi bhi likh kar anumati wapas le sakta / sakti "
                "hoon (DPDP Act 2023 s.6); us ke baad naya upyog band hoga. Photo ka upyog apmaanjanak / galat sandarbh mein nahi hoga.")
    if kind == "property":
        return (f"I, {person or '[name]'}, owner / authorised person for {place or '[address]'}, allow {who} to photograph / film this "
                f"property during {shoot_line} and to use the images for: {use_txt}. I may withdraw permission for future uses in "
                "writing at any time; uses already published before that are not recalled.")
    sub = (f"I, {guardian or '[parent / guardian]'}, parent / lawful guardian of {person or '[child name]'} (a minor), give consent on "
           "their behalf and") if kind == "minor" else f"I, {person or '[name]'},"
    return (f"{sub} allow {who} to use photographs / video of me taken during {shoot_line} for: {use_txt}. I have been told what the "
            "images will be used for. I may withdraw this consent in writing at any time (DPDP Act 2023 s.6); new uses stop after "
            "that. The images will not be used in a defamatory or misleading context.")


# ---- money -------------------------------------------------------------------------------------------------------------------
DEFAULT_STAGES = [{"label": "Advance (booking par)", "pct": 30, "when": "booking"},
                  {"label": "Shoot se pehle", "pct": 40, "when": "before", "days_before": 7},
                  {"label": "Delivery par", "pct": 30, "when": "delivery"}]
DEFAULT_CANCEL = [{"days_before": 60, "refund_pct": 75}, {"days_before": 30, "refund_pct": 50}, {"days_before": 7, "refund_pct": 25},
                  {"days_before": 0, "refund_pct": 0}]
SAC = {"wedding": "998383", "pre_wedding": "998383", "engagement": "998383", "event": "998383", "birthday": "998383",
       "corporate": "998383", "product": "998382", "food": "998382", "fashion": "998382", "portrait": "998381", "maternity": "998381",
       "newborn": "998381", "kids": "998381", "real_estate": "998387", "other": "998387"}
COPYRIGHT_KEEP = ("Photos / videos ka copyright photographer ({studio}) ke paas rahega. Client ko apne niji upyog (print, family, apne "
                  "social media par credit ke saath) ka licence milta hai; commercial / ad upyog ke liye alag likhit anumati. "
                  "(Copyright Act 1957 s.17(b): likhit samjhaute ke bina, paise dekar khinchwai photo ka pehla maalik client hota hai, "
                  "isliye yeh line zaroori hai.)")
COPYRIGHT_CLIENT = ("Photos / videos ka copyright client ka hoga (Copyright Act 1957 s.17(b)). Photographer ({studio}) unhe apne portfolio "
                    "mein sirf client ki alag likhit haan se dikha sakta hai.")


def policy_lines(policy: list[dict]) -> list[str]:
    out = []
    for p in sorted(policy, key=lambda x: -int(x.get("days_before") or 0)):
        d, r = int(p.get("days_before") or 0), int(p.get("refund_pct") or 0)
        out.append(f"Shoot se {d}+ din pehle radd: jama ka {r}% wapas" if d else f"Shoot se kam din pehle: jama ka {r}% wapas")
    return out


def refund_pct(policy: list[dict], days_before: int) -> int:
    for p in sorted(policy, key=lambda x: -int(x.get("days_before") or 0)):
        if days_before >= int(p.get("days_before") or 0):
            return int(p.get("refund_pct") or 0)
    return 0


def unfair_policy(policy: list[dict]) -> str:
    for p in policy:
        if int(p.get("days_before") or 0) >= 30 and int(p.get("refund_pct") or 0) == 0:
            return ("Dhyaan: 30+ din pehle radd hone par bhi poora advance rakhna consumer commission mein 'unfair contract' (CPA 2019 "
                    "s.2(46)) mana ja sakta hai; kuch wapas dene ki line rakhiye.")
    return ""


def gst_split(base: float, pct: float, her_state: str, pos_state: str) -> dict:
    """CGST + SGST when the place of supply is her state, else IGST. pct 0 = no GST (not registered)."""
    tax = round(base * pct / 100.0, 2)
    if not pct:
        return {"pct": 0, "cgst": 0.0, "sgst": 0.0, "igst": 0.0, "tax": 0.0}
    if her_state and pos_state and her_state != pos_state:
        return {"pct": pct, "cgst": 0.0, "sgst": 0.0, "igst": tax, "tax": tax}
    half = round(tax / 2, 2)
    return {"pct": pct, "cgst": half, "sgst": round(tax - half, 2), "igst": 0.0, "tax": tax}


def tds_note(client_kind: str, kind: str, amount: float) -> str:
    """What the CLIENT may deduct (plain words; her CA decides). Personal shoots by individuals: none."""
    if client_kind != "business":
        return ""
    if kind in ("product", "food", "fashion"):
        return ("Business client ad / product shoot ke liye TDS kaat sakta hai: Income-tax Act 2025 s.393(1) - contract kaam (purana 194C) "
                "1% (individual / HUF) ya 2% (doosre), ek baar mein Rs 30,000 se upar ya saal mein Rs 1 lakh se upar; agar woh ise "
                "professional / advertising fee maane to 10% Rs 50,000 se upar. Form 16A / 26AS mein milan kijiye.")
    return ("Business client TDS kaat sakta hai: s.393(1) contract kaam (purana 194C) 1% / 2%, ek baar Rs 30,000 ya saal Rs 1 lakh se upar. "
            "Form 16A / 26AS mein milan kijiye; CA se pakka kijiye.")


def fy(d: date) -> str:
    y = d.year if d.month >= 4 else d.year - 1
    return f"{y % 100:02d}{(y + 1) % 100:02d}"


# ---- culling signals --------------------------------------------------------------------------------------------------------
def cull_hint(sig: dict) -> tuple[str, list[str]]:
    """Signals -> suggestion keep | maybe | reject with reasons (she decides; never a verdict)."""
    why: list[str] = []
    sharp = sig.get("sharpness")
    if sharp is not None and sharp < 25:
        why.append("dhundhli lag rahi (focus / hilna)")
    elif sharp is not None and sharp < 45:
        why.append("thodi soft")
    if sig.get("dark_pct", 0) > 55:
        why.append("bahut andheri")
    if sig.get("bright_pct", 0) > 30:
        why.append("highlights jal gaye")
    if sig.get("dup_of"):
        why.append(f"{sig['dup_of']} jaisi (duplicate)")
    if sig.get("eyes_closed"):
        why.append("aankhein band lag rahi")
    if sig.get("ai_note"):
        why.append(str(sig["ai_note"])[:80])
    bad = sum(1 for w in why if w.startswith(("dhundhli", "bahut andheri", "highlights jal", "aankhein band")))
    if bad >= 1 and (sharp is not None and sharp < 25 or len(why) >= 2):
        return "reject", why
    if why:
        return "maybe", why
    return "keep", ["saaf lag rahi"]


def https_link(url: str) -> str:
    u = str(url or "").strip()
    if not re.fullmatch(r"https://[A-Za-z0-9.-]+\.[A-Za-z]{2,}(/[^\s<>\"']*)?", u):
        return ""
    host = u.split("/")[2].lower()
    if re.fullmatch(r"[\d.]+", host) or host in ("localhost",):
        return ""
    return u
