"""Pure rules of the Event Sahayak: event kinds, budget heads, the permissions checklist worked out from the event's facts,
the task plan counted back from the event date, run-of-show parsing and checks, RSVP words, GST split, hashing / cleaning.
No database, no network.

Nothing here is a price, a vendor rate, a date or a licence fee: those come ONLY from her / her vendors' quotes. Lead times and
licence lists are STARTERS (her city / police station / venue decides) and are always said as such."""
from __future__ import annotations

import hashlib
import json
import re
from datetime import date, timedelta
from typing import Any

# ---------------------------------------------------------------- event kinds
KINDS: dict[str, dict[str, Any]] = {
    "corporate":   {"label": "Corporate event / offsite", "words": ["corporate", "offsite", "annual day", "town hall", "office party",
                                                                   "team outing", "rnr", "award night", "dealer meet", "agm"]},
    "conference":  {"label": "Conference / seminar", "words": ["conference", "seminar", "summit", "convention", "symposium", "workshop",
                                                              "sammelan", "conclave"]},
    "launch":      {"label": "Product launch", "words": ["launch", "unveil", "opening", "inauguration", "udghatan", "showroom opening"]},
    "birthday":    {"label": "Birthday / anniversary", "words": ["birthday", "janamdin", "bday", "anniversary", "salgirah", "naming",
                                                                "namkaran", "baby shower", "godh bharai", "kitty", "party"]},
    "college_fest": {"label": "College fest", "words": ["college fest", "fest", "techfest", "cultural fest", "annual function",
                                                       "farewell", "freshers", "convocation", "youth festival"]},
    "exhibition":  {"label": "Exhibition / expo", "words": ["exhibition", "expo", "trade show", "mela", "stall", "fair", "pradarshani"]},
    "other":       {"label": "Doosra event", "words": []},
}


def kind_of(text: str) -> str:
    t = " " + re.sub(r"\s+", " ", str(text or "").lower()) + " "
    best, n = "other", 0
    for k, v in KINDS.items():
        for w in v["words"]:
            if (f" {w} " in t or (len(w) > 5 and w in t)) and len(w) > n:
                best, n = k, len(w)
    return best


# ---------------------------------------------------------------- budget heads
# sac = usual code for the line when billed by her as part of the event (her CA confirms); pure = usually passed through at actual
HEADS: dict[str, dict[str, Any]] = {
    "venue":        {"label": "Venue / hall", "words": ["venue", "hall", "banquet", "lawn", "auditorium", "ground", "resort", "hotel"]},
    "catering":     {"label": "Catering / khana", "words": ["catering", "caterer", "khana", "food", "buffet", "lunch", "dinner", "snacks",
                                                           "high tea", "plate", "menu", "cake", "mocktail"]},
    "decor":        {"label": "Decor / stage", "words": ["decor", "decoration", "stage", "backdrop", "flower", "phool", "balloon",
                                                        "theme", "entry gate", "photobooth", "centerpiece"]},
    "sound_light":  {"label": "Sound / light", "words": ["sound", "dj", "light", "lighting", "speaker", "truss", "par can", "mic",
                                                        "mike", "audio"]},
    "av":           {"label": "AV / LED / screen", "words": ["led", "screen", "projector", "av ", "led wall", "laptop", "live stream",
                                                            "streaming", "camera switcher", "teleprompter"]},
    "photo_video":  {"label": "Photo / video", "words": ["photo", "photographer", "video", "videographer", "drone", "reel", "camera"]},
    "entertainment": {"label": "Artist / entertainment", "words": ["artist", "anchor", "emcee", "host", "band", "singer", "dancer",
                                                                  "comedian", "magician", "performance", "celebrity", "speaker fee"]},
    "printing":     {"label": "Printing / branding", "words": ["print", "printing", "standee", "banner", "flex", "invite card",
                                                              "badge", "lanyard", "brochure", "branding", "signage"]},
    "gifting":      {"label": "Gifts / kits", "words": ["gift", "return gift", "kit", "hamper", "memento", "trophy", "award"]},
    "transport":    {"label": "Transport", "words": ["transport", "bus", "cab", "car", "tempo", "pickup", "drop", "travel"]},
    "stay":         {"label": "Stay / rooms", "words": ["room", "rooms", "stay", "accommodation", "hotel room"]},
    "permissions":  {"label": "Permission / licence fees", "words": ["permission", "licence", "license", "noc", "ppl", "iprs", "fee"]},
    "staff":        {"label": "Staff / volunteers / security", "words": ["staff", "bouncer", "security", "volunteer", "hostess",
                                                                         "usher", "manpower", "helper"]},
    "misc":         {"label": "Doosra kharcha", "words": []},
}


def head_of(text: str) -> str:
    t = " " + re.sub(r"\s+", " ", str(text or "").lower()) + " "
    best, n = "misc", 0
    for k, v in HEADS.items():
        for w in v["words"]:
            if (f" {w.strip()} " in t or (len(w) > 4 and w in t)) and len(w) > n:
                best, n = k, len(w)
    return best


# ---------------------------------------------------------------- permissions (starters; her city decides)
# lead = days before the event to apply by (starter). why = plain words. who = usual office.
PERMITS: dict[str, dict[str, Any]] = {
    "venue_noc":   {"label": "Venue ka booking letter / NOC", "lead": 30, "who": "venue",
                    "why": "Police / fire / loudspeaker sab venue ki chitthi maangte hain."},
    "police":      {"label": "Police permission (public event / bheed)", "lead": 15, "who": "local police station / commissioner office",
                    "why": "Khuli jagah, public / ticketed event ya badi bheed par police ki likhit anumati."},
    "loudspeaker": {"label": "Loudspeaker / sound permission", "lead": 15, "who": "police / district authority",
                    "why": "Noise Pollution (Regulation and Control) Rules 2000: loudspeaker likhit anumati se; raat 10 se subah 6 band "
                           "(state saal mein 15 din tak raat 12 baje tak chhoot de sakta hai)."},
    "fire":        {"label": "Fire NOC (pandal / temporary structure)", "lead": 15, "who": "fire brigade / municipal fire dept",
                    "why": "Pandal, temporary structure ya badi bheed par fire safety ki NOC aur extinguishers."},
    "structure":   {"label": "Stage / truss stability certificate", "lead": 7, "who": "structural engineer / vendor",
                    "why": "Bada stage, truss ya LED wall: vendor se stability / load certificate lijiye."},
    "fssai":       {"label": "Caterer ka FSSAI registration / licence", "lead": 10, "who": "caterer (FSSAI)",
                    "why": "Khana dene wale caterer ka FSSAI number contract aur bill par ho."},
    "music":       {"label": "Music licence (PPL / IPRS)", "lead": 10, "who": "PPL (recordings) + IPRS (songs ke shabd / dhun)",
                    "why": "Recorded gaane bajane par recordings aur gaane dono ke rights; venue ka licence pehle se hai to uski copy lijiye."},
    "liquor":      {"label": "Sharab ka one-day / occasional licence", "lead": 10, "who": "state excise department",
                    "why": "Event mein sharab: state excise ka occasional licence (rajya ke niyam alag)."},
    "fireworks":   {"label": "Aatishbaazi / pyro permission", "lead": 15, "who": "police / district magistrate",
                    "why": "Aatishbaazi ya cold pyro par likhit anumati aur samay ki pabandi."},
    "drone":       {"label": "Drone (DigitalSky / zone check)", "lead": 7, "who": "DGCA DigitalSky",
                    "why": "Drone shoot: registered drone, remote pilot certificate, zone green / yellow check."},
    "traffic":     {"label": "Traffic / parking permission", "lead": 10, "who": "traffic police",
                    "why": "Sadak par gaadiyan / rally / badi parking ke liye traffic police."},
    "tickets":     {"label": "Ticketed event: GST + local entertainment rules", "lead": 15, "who": "CA / municipal body",
                    "why": "Ticket bechne par GST aur kuch shaharon mein local entertainment / amusement niyam: CA se poochhiye."},
}


def permits_for(ev: dict) -> list[str]:
    """Which checklist items apply, from the event's facts. Starters; she can add / mark not needed."""
    out = ["venue_noc"]
    venue = str(ev.get("venue_kind") or "")
    head = int(ev.get("headcount") or 0)
    if venue in ("open", "public") or ev.get("ticketed") or head >= 500:
        out.append("police")
    if ev.get("sound"):
        out.append("loudspeaker")
    if ev.get("pandal") or venue == "open" or head >= 1000:
        out.append("fire")
    if ev.get("stage"):
        out.append("structure")
    if ev.get("food"):
        out.append("fssai")
    if ev.get("music"):
        out.append("music")
    if ev.get("alcohol"):
        out.append("liquor")
    if ev.get("fireworks"):
        out.append("fireworks")
    if ev.get("drone"):
        out.append("drone")
    if ev.get("road"):
        out.append("traffic")
    if ev.get("ticketed"):
        out.append("tickets")
    return out


# ---------------------------------------------------------------- task plan counted back from the event day
# (days before the event, task, head / area). Negative = after the event.
TASKS: list[tuple[int, str, str]] = [
    (60, "Venue pakka (date block + booking letter)", "venue"),
    (45, "Vendors ke quote lo (catering, decor, sound, photo)", "vendors"),
    (40, "Client ko quotation", "client"),
    (30, "Invite / save-the-date bhejo", "guests"),
    (30, "Vendors book karo (advance aapki haan se)", "vendors"),
    (21, "Permissions ki arzi (police / sound / fire / music)", "permits"),
    (14, "RSVP follow-up", "guests"),
    (10, "Run-of-show ka pehla draft", "show"),
    (7, "Final headcount caterer ko", "vendors"),
    (5, "Printing / branding final", "vendors"),
    (3, "Run-of-show sab vendors ko", "show"),
    (2, "Vendor arrival + setup time pakka", "vendors"),
    (1, "Setup + rehearsal / sound check", "show"),
    (0, "Event day: cue sheet + emergency numbers", "show"),
    (-1, "Venue khaali / saaman wapas", "venue"),
    (-2, "Post-event report", "report"),
    (-3, "Client ko invoice (aapki haan se)", "client"),
]

# conferences / exhibitions need more time; birthdays less
_SCALE = {"conference": 1.5, "exhibition": 1.5, "launch": 1.2, "corporate": 1.0, "college_fest": 1.2, "birthday": 0.5, "other": 1.0}


def task_plan(kind: str, event_day: date, today: date) -> list[dict]:
    sc = _SCALE.get(kind, 1.0)
    out = []
    for days, what, area in TASKS:
        d = int(round(days * sc)) if days > 0 else days
        due = event_day - timedelta(days=d)
        if days > 0 and due < today:
            due = today                                   # already late in the plan: due now
        out.append({"what": what, "area": area, "due": due.isoformat(), "days_before": d})
    return out


# ---------------------------------------------------------------- run of show
_TIME = re.compile(r"^\s*(\d{1,2})[:.](\d{2})\s*(am|pm|baje)?\b", re.I)
_DUR = re.compile(r"\((\d{1,3})\s*(?:min|m|minute|minutes)\)", re.I)
_WHO = re.compile(r"\s[-–—]\s*([^|]+?)\s*(?:\||$)")


def hhmm(text: str) -> str:
    m = _TIME.match(str(text or ""))
    if not m:
        return ""
    h, mi = int(m.group(1)), int(m.group(2))
    ap = (m.group(3) or "").lower()
    if ap == "pm" and h < 12:
        h += 12
    if ap == "am" and h == 12:
        h = 0
    if h > 23 or mi > 59:
        return ""
    return f"{h:02d}:{mi:02d}"


def minutes(t: str) -> int:
    h, m = (int(x) for x in t.split(":"))
    return h * 60 + m


_AV_WORDS = {"mic": ["mic", "mike", "speech", "address", "welcome", "anchor"], "music": ["music", "dj", "song", "dance", "band", "gaana"],
             "video": ["video", "av", "film", "presentation", "ppt", "screen"], "light": ["light", "spot", "blackout", "laser"]}
SOUND = ("mic", "music")


def parse_cues(text: str) -> tuple[list[dict], list[str]]:
    """Lines like '18:30 Welcome by anchor (10 min) - Riya | stage' -> cues. Lines without a time are refused (listed)."""
    cues, bad = [], []
    for raw in str(text or "").splitlines():
        line = raw.strip(" •-\t")
        if not line:
            continue
        t = hhmm(line)
        if not t:
            bad.append(line[:80])
            continue
        rest = _TIME.sub("", line, count=1).strip(" -:")
        dur = _DUR.search(rest)
        rest2 = _DUR.sub("", rest).strip()
        who, where = "", ""
        if "|" in rest2:
            rest2, where = rest2.split("|", 1)
        w = _WHO.search(" " + rest2)
        if w:
            who = w.group(1).strip()
            rest2 = (" " + rest2)[:w.start()].strip()
        low = rest2.lower()
        av = [k for k, ws in _AV_WORDS.items() if any(x in low for x in ws)]
        cues.append({"time": t, "mins": int(dur.group(1)) if dur else None, "what": clean(rest2, 160), "who": clean(who, 60),
                     "where": clean(where, 60), "av": av})
    cues.sort(key=lambda c: c["time"])
    return cues, bad


def cue_problems(cues: list[dict], sound_till: str = "22:00") -> list[str]:
    """Overlaps, missing owners, sound after her allowed time (Noise Rules: 10 pm unless the state relaxed it to midnight)."""
    out = []
    lim = minutes(sound_till or "22:00")
    for i, c in enumerate(cues):
        start = minutes(c["time"])
        end = start + int(c.get("mins") or 0)
        if not c.get("who"):
            out.append(f"{c['time']} '{c['what']}': kaun karega likha nahi.")
        if set(c.get("av") or []) & set(SOUND):
            if (start >= lim or end > lim) and start >= 6 * 60 - 1:
                out.append(f"{c['time']} '{c['what']}': sound {sound_till} ke baad (Noise Rules 2000) - anumati / chhoot ke bina nahi.")
            elif start < 6 * 60:
                out.append(f"{c['time']} '{c['what']}': sound raat 10 se subah 6 ke beech (Noise Rules 2000).")
        if i + 1 < len(cues) and c.get("mins"):
            nxt = minutes(cues[i + 1]["time"])
            if end > nxt:
                out.append(f"{c['time']} '{c['what']}' {c['mins']} min ka hai par agla cue {cues[i + 1]['time']} par: takraav.")
    return out


# ---------------------------------------------------------------- RSVP words
_YES = ["haan", "yes", "aa rahe", "aa raha", "aa rahi", "aayenge", "aaenge", "coming", "confirm", "pakka", "ho", "हाँ", "हो"]
_NO = ["nahi", "nahin", "no", "na ", "nahi aa", "not coming", "busy", "नहीं", "नाही"]
_MAYBE = ["shayad", "maybe", "dekhte", "pata nahi", "sochenge", "may be", "शायद"]


def rsvp_of(text: str) -> tuple[str, int | None]:
    """(status yes|no|maybe|'', plus_ones or None) from a guest's / her words. '+2' or 'do log aur' style counts are read."""
    t = " " + str(text or "").lower() + " "
    st = ""
    if any(w in t for w in _MAYBE):
        st = "maybe"
    elif any(f" {w.strip()} " in t or w in t for w in _NO if len(w.strip()) > 2) or " na " in t:
        st = "no"
    elif any(f" {w} " in t for w in _YES) or any(w in t for w in ("aa rahe", "aa raha", "aa rahi", "aayenge", "coming")):
        st = "yes"
    m = re.search(r"\+\s*(\d{1,2})", t)
    plus = int(m.group(1)) if m else None
    return st, plus


# ---------------------------------------------------------------- money
def r2(v: float) -> float:
    return round(float(v) + 1e-9, 2)


def gst_split(taxable: float, pct: float, intra: bool) -> dict[str, float]:
    tax = r2(taxable * pct / 100)
    if intra:
        half = r2(tax / 2)
        return {"cgst": half, "sgst": r2(tax - half), "igst": 0.0, "tax": tax}
    return {"cgst": 0.0, "sgst": 0.0, "igst": tax, "tax": tax}


def num(v) -> float | None:
    """A number from her words ('1.5 lakh', '25k', '₹40,000'); None when not given."""
    if v is None or v == "" or isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).lower().replace(",", "").replace("₹", "").replace("rs.", "").replace("rs", "").strip()
    m = re.match(r"^(-?\d+(?:\.\d+)?)\s*(lakh|lac|l|k|thousand|hazar|hazaar|cr|crore)?\b", s)
    if not m:
        return None
    n = float(m.group(1))
    u = m.group(2) or ""
    if u in ("lakh", "lac", "l"):
        n *= 100000
    elif u in ("k", "thousand", "hazar", "hazaar"):
        n *= 1000
    elif u in ("cr", "crore"):
        n *= 10000000
    return n


# ---------------------------------------------------------------- hashing / cleaning
def digest(obj: Any) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()


def clean(text: Any, n: int = 500) -> str:
    """Her / client / vendor words: secrets never kept (OTP / PIN / password values, card-like and Aadhaar-like numbers)."""
    t = str(text or "")
    t = re.sub(r"\b(otp|pin|cvv|password|upi pin)\b\s*(?:is|hai|:|=)?\s*\S+", lambda m: f"{m.group(1)} [hataya]", t, flags=re.I)
    t = re.sub(r"\b(?:\d[ -]?){12,19}\b", "[hataya]", t)
    return t.strip()[:n]


def phone(text: Any) -> str:
    d = re.sub(r"\D", "", str(text or ""))
    if len(d) == 12 and d.startswith("91"):
        d = d[2:]
    return d if re.fullmatch(r"[6-9]\d{9}", d) else ""


def blanks_in(text: str) -> list[str]:
    return re.findall(r"\[[^\]]{1,40}\?\]|\[____\]", str(text or ""))
