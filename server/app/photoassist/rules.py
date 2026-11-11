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
    "wedding": [("Bride getting ready (details: lehenga, jewellery, mehendi)", True), ("Groom getting ready / sehra", True),
                ("Baraat arrival", True), ("Jaimala / varmala", True), ("Pheras / mandap rituals", True),
                ("Kanyadaan / sindoor / mangalsutra", True), ("Family group photos (get the list from the client)", True),
                ("Couple portraits", True), ("Vidaai", False), ("Decor, stage, venue wide shots", False),
                ("Guest candids", False)],
    "pre_wedding": [("Wide shots of the location", True), ("Couple close portraits", True), ("Walking / candid moments", True),
                    ("Set after the outfit change", False), ("Golden hour shots", False)],
    "engagement": [("Ring exchange", True), ("Couple portraits", True), ("Family group", True), ("Decor", False)],
    "event": [("Venue / setup wide", True), ("Chief guest arrival", True), ("Stage / speech", True), ("Crowd candid", False),
              ("Branding / banners", False)],
    "birthday": [("Cake cutting", True), ("Birthday person portraits", True), ("Family group", True), ("Decor", False),
                 ("Games / candid", False)],
    "corporate": [("Headshots (list of names)", True), ("Team group photo", True), ("Office / workspace", False),
                  ("Event stage / awards", False)],
    "product": [("Every product on a white background (front / back / side)", True), ("Detail / texture close-up", True),
                ("Lifestyle / in-use shot", False), ("Size / scale shot", False), ("Packaging", False)],
    "food": [("Hero dish top-angle", True), ("45 degree angle", True), ("Ingredients / process", False), ("Ambience", False)],
    "fashion": [("Full look front / back", True), ("Detail close-up", True), ("Movement shots", False), ("Portrait", False)],
    "portrait": [("Close-up", True), ("Half body", True), ("Full body", False), ("Different background / outfit", False)],
    "maternity": [("Couple portraits", True), ("Bump silhouette", True), ("Family", False)],
    "newborn": [("Baby close-ups (asleep, safe pose)", True), ("With the parents", True), ("Details: hands, feet", False)],
    "kids": [("Candid at play", True), ("Portrait", True), ("Family", False)],
    "real_estate": [("Wide of every room (from the corner)", True), ("Kitchen / bathroom", True), ("Building exterior", True),
                    ("Amenities", False), ("Twilight exterior", False)],
    "other": [("Main shots (get the list from the client)", True)],
}

GEAR_KINDS = ("camera", "lens", "flash", "light", "drone", "battery", "card", "stand", "gimbal", "mic", "laptop", "other")
GEAR_NEED: dict[str, list[str]] = {
    "_base": ["camera", "lens", "battery", "card"],
    "wedding": ["flash", "light", "stand"], "event": ["flash"], "birthday": ["flash"], "engagement": ["flash"],
    "corporate": ["flash", "light", "stand"], "product": ["light", "stand"], "food": ["light", "stand"],
    "fashion": ["light", "stand"], "portrait": ["light"], "newborn": ["light"], "maternity": ["light"], "real_estate": ["stand"],
}
GEAR_EXTRA_LINES = ["Spare batteries charged", "Memory cards empty / formatted (back up the last shoot first)", "Lens cleaned",
                    "Second body or backup camera", "Card reader / laptop backup"]

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
    t = re.sub(r"\b(otp|pin|cvv|password|upi pin)\b\s*(?:is|hai|:|=)?\s*\S+", lambda m: f"{m.group(1)} [removed]", t, flags=re.I)
    t = re.sub(r"\b(?:\d[ -]?){12,19}\b", "[removed]", t)
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
        out.append({"level": "warn", "key": "asi", "say": "A professional shoot (pre-wedding too) at an ASI / state protected monument "
                    "needs permission first (ASI's SAHMAT portal / that circle's office; fee and days as per their list)."})
    if place in ("venue", "private"):
        out.append({"level": "note", "key": "venue_ok", "say": "Get shoot permission from the venue / house owner (and a property release "
                    "if there is portfolio / commercial use)."})
    if place == "public":
        out.append({"level": "note", "key": "public", "say": "Public place: a tripod / large setup may need local permission (municipal corporation / "
                    "police); if faces in the crowd are used commercially, their model release is needed."})
    if re.search(RAIL_WORDS, loc, re.I):
        out.append({"level": "warn", "key": "rail", "say": "A shoot on railway / metro premises needs permission from the railway / metro administration."})
    if drone:
        d = drone_ok or {}
        if not d.get("uin"):
            out.append({"level": "warn", "key": "drone_uin", "say": "Drone (over 250 g): UIN registration on Digital Sky is needed; "
                        "add the drone's UIN in gear."})
        if not d.get("rpc"):
            out.append({"level": "warn", "key": "drone_rpc", "say": "Flying a drone for money (commercial) needs a Remote Pilot Certificate "
                        "(from a DGCA-authorised RPTO), except nano (up to 250 g). Add the RPC number and date in the rules."})
        if not d.get("insured"):
            out.append({"level": "warn", "key": "drone_ins", "say": "Third-party insurance for the drone (over 250 g) is required: add the "
                        "insurance end date in gear."})
        out.append({"level": "note", "key": "drone_zone", "say": "Before flying, check the zone on the Digital Sky airspace map: green "
                    "(up to 120 m / 400 ft) is fine; yellow = permission; red = not allowed. Do not fly over crowds."})
        if re.search(AIRPORT_WORDS, loc, re.I):
            out.append({"level": "warn", "key": "drone_airport", "say": "The place looks close to an airport / defence area: it may be a yellow / red zone, "
                        "no drone without permission."})
        if place == "monument":
            out.append({"level": "warn", "key": "drone_asi", "say": "Drone at a monument: a separate ASI permission along with aviation (Digital Sky)."})
    if minors or kind in MINOR_KINDS:
        out.append({"level": "warn", "key": "minor", "say": "Photos of children: written consent of the parents / guardian (DPDP Act s.9) and "
                    "a separate approval for portfolio / social media use are required; do not make a child's photo public without that approval."})
    if commercial_use:
        out.append({"level": "warn", "key": "release", "say": "The photo will go into an ad / product / stock: get a model release from every identifiable person "
                    "and a property release for a private place first."})
    if kind == "newborn":
        out.append({"level": "note", "key": "newborn_safe", "say": "Newborn: only safe poses, a warm room, parents close by; never leave the baby "
                    "alone on props."})
    return out


# ---- releases --------------------------------------------------------------------------------------------------------------
RELEASE_KINDS = ("model", "minor", "property")
USES = ("client_personal", "portfolio", "social_media", "advertising", "stock", "print_exhibition")
USE_LABEL = {"client_personal": "client's personal use", "portfolio": "photographer's portfolio / website",
             "social_media": "photographer's social media", "advertising": "ad / brand promotion", "stock": "stock agency",
             "print_exhibition": "print / exhibition"}
USE_LABEL_HI = {"client_personal": "client ka niji upyog", "portfolio": "photographer ka portfolio / website",
                "social_media": "photographer ka social media"}      # the Hindi release keeps its own words


def release_text(kind: str, studio: str, person: str, guardian: str, place: str, uses: list[str], shoot_line: str,
                 lang: str = "en") -> str:
    """Plain release / consent text she gets signed (paper or her phone). Not legal advice: her lawyer can change it."""
    use_txt = ", ".join(USE_LABEL.get(u, u) for u in uses) or "[write the uses]"
    who = studio or "[photographer / studio]"
    if lang == "hi":
        use_txt = ", ".join(USE_LABEL_HI.get(u, USE_LABEL.get(u, u)) for u in uses) or "[upyog likhiye]"
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
DEFAULT_STAGES = [{"label": "Advance (on booking)", "pct": 30, "when": "booking"},
                  {"label": "Before the shoot", "pct": 40, "when": "before", "days_before": 7},
                  {"label": "On delivery", "pct": 30, "when": "delivery"}]
DEFAULT_CANCEL = [{"days_before": 60, "refund_pct": 75}, {"days_before": 30, "refund_pct": 50}, {"days_before": 7, "refund_pct": 25},
                  {"days_before": 0, "refund_pct": 0}]
SAC = {"wedding": "998383", "pre_wedding": "998383", "engagement": "998383", "event": "998383", "birthday": "998383",
       "corporate": "998383", "product": "998382", "food": "998382", "fashion": "998382", "portrait": "998381", "maternity": "998381",
       "newborn": "998381", "kids": "998381", "real_estate": "998387", "other": "998387"}
COPYRIGHT_KEEP = ("Copyright in the photos / videos stays with the photographer ({studio}). The client gets a licence for personal use (print, family, own "
                  "social media with credit); commercial / ad use needs separate written permission. "
                  "(Copyright Act 1957 s.17(b): without a written agreement, the first owner of a photo taken for payment is the client, "
                  "so this line is needed.)")
COPYRIGHT_CLIENT = ("Copyright in the photos / videos belongs to the client (Copyright Act 1957 s.17(b)). The photographer ({studio}) may show them in their portfolio "
                    "only with the client's separate written approval.")


def policy_lines(policy: list[dict]) -> list[str]:
    out = []
    for p in sorted(policy, key=lambda x: -int(x.get("days_before") or 0)):
        d, r = int(p.get("days_before") or 0), int(p.get("refund_pct") or 0)
        out.append(f"Cancelled {d}+ days before the shoot: {r}% of the amount paid is refunded" if d else f"Fewer days before the shoot: {r}% of the amount paid is refunded")
    return out


def refund_pct(policy: list[dict], days_before: int) -> int:
    for p in sorted(policy, key=lambda x: -int(x.get("days_before") or 0)):
        if days_before >= int(p.get("days_before") or 0):
            return int(p.get("refund_pct") or 0)
    return 0


def unfair_policy(policy: list[dict]) -> str:
    for p in policy:
        if int(p.get("days_before") or 0) >= 30 and int(p.get("refund_pct") or 0) == 0:
            return ("Note: keeping the whole advance even on a cancellation 30+ days ahead can be held an 'unfair contract' by a consumer commission (CPA 2019 "
                    "s.2(46)); keep a line that refunds some of it.")
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
        return ("A business client may deduct TDS for an ad / product shoot: Income-tax Act 2025 s.393(1) - contract work (earlier 194C) "
                "1% (individual / HUF) or 2% (others), above Rs 30,000 at one time or above Rs 1 lakh in a year; if they treat it as a "
                "professional / advertising fee, 10% above Rs 50,000. Match it against Form 16A / 26AS.")
    return ("A business client may deduct TDS: s.393(1) contract work (earlier 194C) 1% / 2%, above Rs 30,000 at one time or Rs 1 lakh in a year. "
            "Match it against Form 16A / 26AS; confirm with your CA.")


def fy(d: date) -> str:
    y = d.year if d.month >= 4 else d.year - 1
    return f"{y % 100:02d}{(y + 1) % 100:02d}"


# ---- culling signals --------------------------------------------------------------------------------------------------------
def cull_hint(sig: dict) -> tuple[str, list[str]]:
    """Signals -> suggestion keep | maybe | reject with reasons (she decides; never a verdict)."""
    why: list[str] = []
    sharp = sig.get("sharpness")
    if sharp is not None and sharp < 25:
        why.append("blurry (focus / shake)")
    elif sharp is not None and sharp < 45:
        why.append("slightly soft")
    if sig.get("dark_pct", 0) > 55:
        why.append("very dark")
    if sig.get("bright_pct", 0) > 30:
        why.append("highlights blown out")
    if sig.get("dup_of"):
        why.append(f"same as {sig['dup_of']} (duplicate)")
    if sig.get("eyes_closed"):
        why.append("eyes look closed")
    if sig.get("ai_note"):
        why.append(str(sig["ai_note"])[:80])
    bad = sum(1 for w in why if w.startswith(("blurry", "very dark", "highlights blown", "eyes look closed")))
    if bad >= 1 and (sharp is not None and sharp < 25 or len(why) >= 2):
        return "reject", why
    if why:
        return "maybe", why
    return "keep", ["looks sharp"]


def https_link(url: str) -> str:
    u = str(url or "").strip()
    if not re.fullmatch(r"https://[A-Za-z0-9.-]+\.[A-Za-z]{2,}(/[^\s<>\"']*)?", u):
        return ""
    host = u.split("/")[2].lower()
    if re.fullmatch(r"[\d.]+", host) or host in ("localhost",):
        return ""
    return u
