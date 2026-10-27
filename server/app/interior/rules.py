"""Pure rules of the Interior Sahayak: measurement maths, line kinds, styles + palettes, GST split, payment-stage template,
installation order, the 'architect' title rule. No database, no network.

Nothing here is a price, a rate, a size or a brand price: those come ONLY from her rate card / her words / her site measurement.
Palettes and style words are design suggestions (her taste decides), clearly not facts."""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any

# ---------------------------------------------------------------- line kinds (BOQ heads)
# unit = usual unit for her rate card; trade = who does it; order = installation sequence (lower first);
# area = which measured quantity can feed it when she says "naap se lo"; sac = usual code (her CA confirms).
KINDS: dict[str, dict[str, Any]] = {
    "civil":         {"label": "Civil / tod-phod", "unit": "sqft", "trade": "mason", "order": 10, "area": "", "sac": "9954",
                      "words": ["civil", "tod", "todna", "demolition", "plaster", "brick", "wall banana", "diwar"]},
    "plumbing":      {"label": "Plumbing", "unit": "point", "trade": "plumber", "order": 15, "area": "", "sac": "9954",
                      "words": ["plumbing", "nal", "tap", "pipe", "sink point", "drain", "geyser point"]},
    "electrical":    {"label": "Electrical", "unit": "point", "trade": "electrician", "order": 20, "area": "", "sac": "9954",
                      "words": ["electrical", "wiring", "switch", "socket", "light point", "bijli", "fan point", "mcb", "db"]},
    "false_ceiling": {"label": "False ceiling", "unit": "sqft", "trade": "ceiling", "order": 30, "area": "ceiling", "sac": "9954",
                      "words": ["false ceiling", "pop", "gypsum", "ceiling", "cove", "jhoota ceiling", "seeling"]},
    "painting":      {"label": "Painting", "unit": "sqft", "trade": "painter", "order": 40, "area": "wall", "sac": "9954",
                      "words": ["paint", "painting", "putty", "rang", "texture", "wallpaper", "polish"]},
    "flooring":      {"label": "Flooring", "unit": "sqft", "trade": "flooring", "order": 50, "area": "floor", "sac": "9954",
                      "words": ["floor", "flooring", "tile", "tiles", "marble", "granite", "wooden floor", "laminate floor", "vinyl"]},
    "kitchen":       {"label": "Modular kitchen", "unit": "rft", "trade": "modular", "order": 60, "area": "", "sac": "9954",
                      "words": ["kitchen", "modular kitchen", "rasoi", "shutter", "tandem", "basket", "loft", "platform"]},
    "wardrobe":      {"label": "Wardrobe", "unit": "sqft", "trade": "carpenter", "order": 62, "area": "", "sac": "9954",
                      "words": ["wardrobe", "almirah", "almari", "cupboard", "closet", "sliding wardrobe"]},
    "tv_unit":       {"label": "TV unit / storage", "unit": "sqft", "trade": "carpenter", "order": 64, "area": "", "sac": "9954",
                      "words": ["tv unit", "tv panel", "crockery", "shoe rack", "storage", "study table", "vanity", "mandir", "puja unit"]},
    "glass":         {"label": "Glass / aluminium", "unit": "sqft", "trade": "fabricator", "order": 66, "area": "", "sac": "9954",
                      "words": ["glass", "partition", "aluminium", "mirror", "shower", "window"]},
    "furniture":     {"label": "Furniture (loose)", "unit": "nos", "trade": "supplier", "order": 70, "area": "", "sac": "9403",
                      "words": ["sofa", "bed", "chair", "dining", "table", "furniture", "mattress", "recliner", "ottoman"]},
    "decor":         {"label": "Decor / furnishing", "unit": "nos", "trade": "supplier", "order": 80, "area": "", "sac": "",
                      "words": ["curtain", "parda", "blind", "rug", "carpet", "lamp", "decor", "art", "wallpaper art", "cushion"]},
    "cleaning":      {"label": "Deep cleaning", "unit": "lumpsum", "trade": "cleaner", "order": 95, "area": "", "sac": "9985",
                      "words": ["cleaning", "safai", "deep clean"]},
    "other":         {"label": "Doosra", "unit": "nos", "trade": "other", "order": 90, "area": "", "sac": "", "words": []},
}

UNITS = {"sqft": "sq ft", "rft": "running ft", "sqm": "sq m", "rmt": "running m", "nos": "nos", "point": "point",
         "set": "set", "lumpsum": "lump sum", "kg": "kg", "litre": "litre"}
_UNIT_WORDS = {"sqft": ["sqft", "sq ft", "sft", "square feet", "sq.ft", "sq. ft"], "rft": ["rft", "running ft", "running feet", "r ft"],
               "sqm": ["sqm", "sq m", "square metre", "square meter"], "rmt": ["rmt", "running m", "running metre"],
               "nos": ["nos", "no", "pcs", "piece", "number", "nag"], "point": ["point", "points", "pt"], "set": ["set"],
               "lumpsum": ["lumpsum", "lump sum", "ls", "job"], "kg": ["kg"], "litre": ["litre", "liter", "ltr", "l"]}


def kind_of(text: str) -> str:
    t = " " + re.sub(r"\s+", " ", str(text or "").lower()) + " "
    best, score = "other", 0
    for k, v in KINDS.items():
        for w in v["words"]:
            if f" {w} " in t or (len(w) > 4 and w in t):
                if len(w) > score:
                    best, score = k, len(w)
    return best


def unit_of(text: str, default: str = "") -> str:
    t = str(text or "").strip().lower()
    if t in UNITS:
        return t
    for u, ws in _UNIT_WORDS.items():
        if t in ws:
            return u
    return default


# ---------------------------------------------------------------- measurement
_FT_IN = re.compile(r"(\d+(?:\.\d+)?)\s*(?:'|ft|feet|foot)\s*(?:(\d+(?:\.\d+)?)\s*(?:\"|in|inch|inches))?", re.I)


def length(value: Any, unit: str = "ft") -> float | None:
    """One length in FEET from her words: 12, 12.5, "12'6\"", "12 ft 6 in", "3.6 m", "3600 mm". None = not given / unreadable."""
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        v = float(value)
        return round(v * {"ft": 1, "m": 3.28084, "mm": 0.00328084, "cm": 0.0328084, "in": 1 / 12}.get(unit, 1), 4) if v > 0 else None
    s = str(value).strip().lower()
    m = _FT_IN.fullmatch(s) or _FT_IN.match(s)
    if m and ("'" in s or "ft" in s or "feet" in s or "foot" in s):
        v = float(m.group(1)) + (float(m.group(2)) / 12 if m.group(2) else 0)
        return round(v, 4) if v > 0 else None
    m = re.fullmatch(r"(\d+(?:\.\d+)?)\s*(mm|cm|m|in|inch|\"|ft)?", s)
    if not m:
        return None
    u = m.group(2) or unit
    u = {"inch": "in", '"': "in"}.get(u, u)
    return length(float(m.group(1)), u)


def room_areas(l: float | None, w: float | None, h: float | None, openings: list[dict] | None = None) -> dict[str, Any]:
    """Areas from HER measured numbers only (feet). Missing number = that area stays None (never guessed).
    openings: [{kind door|window|other, w, h, count}] in feet."""
    out: dict[str, Any] = {"floor_sqft": None, "ceiling_sqft": None, "perimeter_rft": None, "wall_sqft": None,
                           "openings_sqft": 0.0, "skirting_rft": None, "missing": []}
    if not l:
        out["missing"].append("lambai")
    if not w:
        out["missing"].append("chaudai")
    if not h:
        out["missing"].append("unchai")
    op_area, door_w = 0.0, 0.0
    for o in openings or []:
        ow, oh, n = float(o.get("w") or 0), float(o.get("h") or 0), max(1, int(o.get("count") or 1))
        if ow > 0 and oh > 0:
            op_area += ow * oh * n
        if (o.get("kind") or "") == "door" and ow > 0:
            door_w += ow * n
    out["openings_sqft"] = round(op_area, 2)
    if l and w:
        out["floor_sqft"] = round(l * w, 2)
        out["ceiling_sqft"] = round(l * w, 2)
        out["perimeter_rft"] = round(2 * (l + w), 2)
        out["skirting_rft"] = round(max(0.0, 2 * (l + w) - door_w), 2)
        if h:
            out["wall_sqft"] = round(max(0.0, 2 * (l + w) * h - op_area), 2)
    return out


def qty_from_area(area_key: str, areas: dict[str, Any], unit: str) -> tuple[float | None, str]:
    """Quantity for a line from the room's measured areas. Returns (qty or None, note)."""
    key = {"floor": "floor_sqft", "ceiling": "ceiling_sqft", "wall": "wall_sqft", "skirting": "skirting_rft",
           "perimeter": "perimeter_rft", "wall_ceiling": "wall_sqft"}.get(area_key, "")
    if not key or not areas:
        return None, ""
    v = areas.get(key)
    if v is None:
        return None, "naap adhoora (" + ", ".join(areas.get("missing") or []) + ")"
    if area_key == "wall_ceiling" and areas.get("ceiling_sqft") is not None:
        v = v + areas["ceiling_sqft"]
    want_rft = key.endswith("_rft")
    if unit == "sqm" and not want_rft:
        return round(v / 10.7639, 2), "sq ft se sq m"
    if unit in ("sqft", "") and not want_rft:
        return round(v, 2), ""
    if unit in ("rft", "") and want_rft:
        return round(v, 2), ""
    if unit == "rmt" and want_rft:
        return round(v / 3.28084, 2), "ft se m"
    return None, f"naap ki ikai ({'rft' if want_rft else 'sqft'}) aur rate ki ikai ({unit}) alag"


# ---------------------------------------------------------------- styles (suggestions, her taste decides)
STYLES: dict[str, dict[str, Any]] = {
    "modern":        {"label": "Modern", "words": ["modern", "sleek", "aadhunik"],
                      "palette": ["#F5F5F2", "#2E2E2E", "#9A8F84", "#C9A66B", "#5B6B73"],
                      "materials": ["matte laminate", "handle-less shutters", "profile lights", "quartz top"]},
    "minimal":       {"label": "Minimal", "words": ["minimal", "minimalist", "simple", "saada", "clean"],
                      "palette": ["#FFFFFF", "#EDEBE6", "#BDB6AA", "#3B3B3B", "#8C9A8B"],
                      "materials": ["flat shutters", "hidden storage", "warm white light"]},
    "contemporary":  {"label": "Contemporary", "words": ["contemporary"],
                      "palette": ["#F2EFEA", "#1F2A36", "#B08D57", "#7D8C8C", "#D9CBB5"],
                      "materials": ["fluted panels", "brass trims", "veneer", "cove lights"]},
    "scandinavian":  {"label": "Scandinavian", "words": ["scandinavian", "scandi", "nordic"],
                      "palette": ["#FAF8F5", "#E3DCD2", "#A9B4A2", "#6E5D4E", "#2F3437"],
                      "materials": ["light oak", "linen", "rounded edges"]},
    "japandi":       {"label": "Japandi", "words": ["japandi", "japanese", "zen"],
                      "palette": ["#EFE9E1", "#C8B8A6", "#8A7968", "#3C3A36", "#7E8C74"],
                      "materials": ["ash wood", "cane", "low furniture", "paper-like light"]},
    "industrial":    {"label": "Industrial", "words": ["industrial", "loft", "exposed"],
                      "palette": ["#3A3A3A", "#8B8B8B", "#B5651D", "#D8D2C8", "#1E1E1E"],
                      "materials": ["concrete finish", "black metal", "exposed brick", "edison bulbs"]},
    "traditional_indian": {"label": "Traditional Indian", "words": ["traditional", "indian", "desi", "ethnic", "paramparik", "jaali", "rajasthani", "kerala", "chettinad"],
                      "palette": ["#7B2D26", "#D9A441", "#F3E6D0", "#2F4F4F", "#A0522D"],
                      "materials": ["sheesham wood", "jaali", "brass", "handloom fabric"]},
    "boho":          {"label": "Boho", "words": ["boho", "bohemian"],
                      "palette": ["#E9D8C4", "#C7774F", "#7A8B5C", "#F4EDE4", "#5A3E2B"],
                      "materials": ["cane", "jute", "macrame", "plants"]},
    "luxury":        {"label": "Luxury", "words": ["luxury", "premium", "shahi", "royal", "lavish"],
                      "palette": ["#1C1C1C", "#C9A227", "#F4F1EA", "#5E4B3C", "#2D3E50"],
                      "materials": ["italian marble look", "veneer", "gold PVD trims", "velvet"]},
    "coastal":       {"label": "Coastal", "words": ["coastal", "beach", "goan"],
                      "palette": ["#FFFFFF", "#A7C7E7", "#E6D5B8", "#2E5E7E", "#9FB8AD"],
                      "materials": ["whitewash wood", "rattan", "blue accents"]},
    "classic":       {"label": "Classic", "words": ["classic", "colonial", "victorian", "french"],
                      "palette": ["#F6F1E7", "#8C6B4F", "#2E3B4E", "#C2B280", "#5C4033"],
                      "materials": ["mouldings", "panelled doors", "warm wood"]},
}


def style_of(text: str) -> str:
    t = str(text or "").lower()
    best, n = "", 0
    for k, v in STYLES.items():
        for w in v["words"]:
            if re.search(rf"\b{re.escape(w)}\b", t) and len(w) > n:
                best, n = k, len(w)
    return best


# ---------------------------------------------------------------- money
def r2(v: float) -> float:
    return round(float(v) + 1e-9, 2)


def gst_split(taxable: float, pct: float, intra: bool) -> dict[str, float]:
    tax = r2(taxable * pct / 100)
    if intra:
        half = r2(tax / 2)
        return {"cgst": half, "sgst": r2(tax - half), "igst": 0.0, "tax": tax}
    return {"cgst": 0.0, "sgst": 0.0, "igst": tax, "tax": tax}


DEFAULT_STAGES = [
    {"label": "Booking / design advance", "pct": 10},
    {"label": "Design pakka, production shuru", "pct": 50},
    {"label": "Material site par / installation shuru", "pct": 35},
    {"label": "Handover", "pct": 5},
]


def check_stages(stages: list[dict]) -> list[str]:
    errs = []
    if not stages:
        return ["Koi stage nahi."]
    tot = 0.0
    for s in stages:
        if not str(s.get("label") or "").strip():
            errs.append("Stage ka naam khaali.")
        p = float(s.get("pct") or 0)
        if p <= 0 or p > 100:
            errs.append(f"'{s.get('label')}' ka % 1-100 hona chahiye.")
        tot += p
    if abs(tot - 100) > 0.01:
        errs.append(f"Saare stages milkar 100% hone chahiye (abhi {tot:g}%).")
    return errs


def split_amount(total: float, stages: list[dict]) -> list[float]:
    """Stage amounts that add up EXACTLY to the total (the last one takes the rounding)."""
    out, used = [], 0.0
    for i, s in enumerate(stages):
        if i == len(stages) - 1:
            out.append(r2(total - used))
        else:
            a = float(round(total * float(s["pct"]) / 100))
            out.append(a)
            used += a
    return out


# ---------------------------------------------------------------- titles: Architects Act 1972 s.37
_ARCH = re.compile(r"\b(architect|architects|architectural firm|आर्किटेक्ट|वास्तुविद)\b", re.I)


def title_problem(title: str, coa_reg: str = "") -> str:
    """Only a person registered with the Council of Architecture may use the title 'architect' (Architects Act 1972 s.37)."""
    if _ARCH.search(title or "") and not re.fullmatch(r"(?i)CA/\d{4}/\d{3,6}", (coa_reg or "").strip()):
        return ("'Architect' shabd sirf Council of Architecture mein registered vyakti use kar sakte hain (Architects Act 1972 "
                "s.37). Apna CoA number (CA/YYYY/NNNNN) daaliye, ya 'Interior Designer' likhiye.")
    return ""


# ---------------------------------------------------------------- sequence
def sequence_problems(tasks: list[dict]) -> list[str]:
    """Same room: a later trade starting before an earlier one is finished (e.g. flooring before ceiling)."""
    out = []
    by_room: dict[str, list[dict]] = {}
    for t in tasks:
        if t.get("status") == "cancelled":
            continue
        by_room.setdefault(t.get("room") or "", []).append(t)
    for room, ts in by_room.items():
        for a in ts:
            for b in ts:
                oa, ob = KINDS.get(a.get("kind") or "other", KINDS["other"])["order"], KINDS.get(b.get("kind") or "other", KINDS["other"])["order"]
                if oa < ob and a.get("end") and b.get("start") and b["start"] < a["end"] and not (oa >= 60 and ob >= 60):
                    out.append(f"{room or 'Ghar'}: {KINDS.get(b['kind'], KINDS['other'])['label']} ({b['start']}) "
                               f"{KINDS.get(a['kind'], KINDS['other'])['label']} khatam hone ({a['end']}) se pehle shuru.")
    return out


# ---------------------------------------------------------------- hashing / cleaning
def digest(obj: Any) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()


def clean(text: Any, n: int = 500) -> str:
    """Her / client words: secrets never kept (OTP / PIN / password values, card-like numbers, Aadhaar-like 12 digits)."""
    t = str(text or "")
    t = re.sub(r"\b(otp|pin|cvv|password|upi pin)\b\s*(?:is|hai|:|=)?\s*\S+", lambda m: f"{m.group(1)} [hataya]", t, flags=re.I)
    t = re.sub(r"\b(?:\d[ -]?){12,19}\b", "[hataya]", t)
    return t.strip()[:n]


def phone(text: Any) -> str:
    d = re.sub(r"\D", "", str(text or ""))
    if len(d) == 12 and d.startswith("91"):
        d = d[2:]
    return d if re.fullmatch(r"[6-9]\d{9}", d) else ""
