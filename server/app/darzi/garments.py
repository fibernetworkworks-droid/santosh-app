"""The garments an Indian tailor / boutique stitches, the measurements each one needs, and reading a measurement list
written the way tailors write it ("L 15, chest 34, kamar 30, bahi 11 1/2, gala aage 7 peeche 8").

Pure data + functions (no DB), easy to test."""
from __future__ import annotations

import re
from fractions import Fraction

# field id -> (Hinglish label, words people use for it)
FIELDS: dict[str, tuple[str, tuple[str, ...]]] = {
    "length": ("Lambai", ("length", "lambai", "lamba", "lmb", "l", "long", "full length", "kurta length", "top length")),
    "chest": ("Chhaati / bust", ("chest", "bust", "chhati", "chhaati", "chati", "seena", "sina", "c")),
    "upper_chest": ("Upar ki chhaati", ("upper chest", "upper bust", "upar chhati", "upar chest")),
    "waist": ("Kamar", ("waist", "kamar", "w", "kmr")),
    "hip": ("Hip / seat", ("hip", "hips", "seat", "sit", "kulha", "h")),
    "shoulder": ("Kandha", ("shoulder", "kandha", "kandhe", "sh", "sldr")),
    "sleeve_length": ("Baanh lambai", ("sleeve", "sleeve length", "bahi", "baahi", "baanh", "bah", "bazu", "aasteen", "asteen", "slv")),
    "sleeve_round": ("Baanh gheraa", ("sleeve round", "bicep", "baanh gola", "bahi gola", "mori", "sleeve mori", "arm round")),
    "armhole": ("Armhole / mudda", ("armhole", "arm hole", "mudda", "munda", "bagal", "ah")),
    "front_neck": ("Gala aage", ("front neck", "gala aage", "aage gala", "front gala", "fn", "neck front")),
    "back_neck": ("Gala peeche", ("back neck", "gala peeche", "peeche gala", "back gala", "bn", "neck back")),
    "neck": ("Gala / collar", ("neck", "collar", "gala", "kalar")),
    "point": ("Point / apex", ("point", "apex", "dart point", "bust point")),
    "cross_front": ("Cross front", ("cross front", "front cross")),
    "cross_back": ("Cross back", ("cross back", "back cross")),
    "bottom_length": ("Neeche ki lambai", ("bottom length", "salwar length", "pant length", "pajama length", "neeche lambai",
                                           "pyjama length", "trouser length", "lehenga length", "skirt length")),
    "thigh": ("Jaangh", ("thigh", "jangh", "jaangh", "jang")),
    "knee": ("Ghutna", ("knee", "ghutna", "ghutne")),
    "calf": ("Pindli", ("calf", "pindli")),
    "bottom": ("Mohri / paincha", ("bottom", "mohri", "mohari", "paincha", "pauncha", "ankle", "moori")),
    "inseam": ("Andar ki silai", ("inseam", "in seam", "inside length")),
    "crotch": ("Jhola / rise", ("crotch", "rise", "jhola", "seat depth", "lap")),
    "flare": ("Gher / flare", ("flare", "gher", "ghera", "ghera neeche")),
    "wrist": ("Kalai", ("wrist", "kalai", "cuff")),
}

# garment id -> label, words, the fields that matter (first ones = must have), usual minimum days
GARMENTS: dict[str, dict] = {
    "blouse": {"label": "Blouse", "words": ("blouse", "choli", "bluj", "blause", "saree blouse"),
               "fields": ["length", "chest", "waist", "shoulder", "sleeve_length", "sleeve_round", "upper_chest", "armhole",
                          "front_neck", "back_neck", "point"], "must": 6, "days": 4},
    "kurti": {"label": "Kurti / kurta (mahila)", "words": ("kurti", "ladies kurta", "suit top", "kameez", "top"),
              "fields": ["length", "chest", "waist", "hip", "shoulder", "sleeve_length", "sleeve_round", "armhole",
                         "front_neck", "back_neck"], "must": 6, "days": 4},
    "salwar_suit": {"label": "Salwar suit", "words": ("salwar suit", "suit", "punjabi suit", "salwar kameez", "dress"),
                    "fields": ["length", "chest", "waist", "hip", "shoulder", "sleeve_length", "bottom_length", "sleeve_round",
                               "armhole", "front_neck", "back_neck", "bottom"], "must": 7, "days": 5},
    "salwar": {"label": "Salwar / churidar / pyjami", "words": ("salwar", "churidar", "pyjami", "patiala", "leggings"),
               "fields": ["bottom_length", "waist", "hip", "thigh", "knee", "calf", "bottom"], "must": 3, "days": 3},
    "palazzo": {"label": "Palazzo / sharara", "words": ("palazzo", "plazo", "sharara", "garara", "gharara"),
                "fields": ["bottom_length", "waist", "hip", "bottom"], "must": 3, "days": 3},
    "lehenga": {"label": "Lehenga choli", "words": ("lehenga", "lehnga", "ghagra", "chaniya choli", "chaniya"),
                "fields": ["length", "chest", "waist", "shoulder", "sleeve_length", "bottom_length", "hip", "upper_chest",
                           "sleeve_round", "armhole", "front_neck", "back_neck", "flare"], "must": 7, "days": 10},
    "gown": {"label": "Gown / anarkali", "words": ("gown", "anarkali", "maxi", "long dress", "frock suit"),
             "fields": ["length", "chest", "waist", "hip", "shoulder", "sleeve_length", "armhole", "upper_chest",
                        "sleeve_round", "front_neck", "back_neck", "flare"], "must": 7, "days": 7},
    "petticoat": {"label": "Petticoat / saree shapewear", "words": ("petticoat", "peticot", "inskirt", "saya", "shapewear"),
                  "fields": ["bottom_length", "waist", "hip"], "must": 2, "days": 2},
    "saree_work": {"label": "Saree fall-pico / interlock", "words": ("fall pico", "fall", "pico", "saree fall", "interlock"),
                   "fields": [], "must": 0, "days": 2},
    "frock": {"label": "Bachchon ki frock", "words": ("frock", "baby frock", "kids dress", "bachche ki dress"),
              "fields": ["length", "chest", "waist", "shoulder", "sleeve_length", "armhole"], "must": 3, "days": 3},
    "shirt": {"label": "Shirt", "words": ("shirt", "kameez gents", "bushirt", "formal shirt"),
              "fields": ["length", "chest", "waist", "hip", "shoulder", "sleeve_length", "sleeve_round", "wrist", "neck"],
              "must": 6, "days": 4},
    "pant": {"label": "Pant / trouser", "words": ("pant", "pants", "trouser", "patloon", "patlun", "formal pant"),
             "fields": ["bottom_length", "waist", "hip", "thigh", "knee", "bottom", "crotch"], "must": 4, "days": 4},
    "kurta_pajama": {"label": "Kurta pajama (gents)", "words": ("kurta pajama", "kurta pyjama", "gents kurta", "kurta"),
                     "fields": ["length", "chest", "waist", "hip", "shoulder", "sleeve_length", "sleeve_round", "neck",
                                "bottom_length", "bottom"], "must": 6, "days": 5},
    "sherwani": {"label": "Sherwani / jodhpuri", "words": ("sherwani", "jodhpuri", "bandhgala", "achkan", "indo western"),
                 "fields": ["length", "chest", "waist", "hip", "shoulder", "sleeve_length", "sleeve_round", "neck", "wrist",
                            "bottom_length"], "must": 7, "days": 12},
    "safari": {"label": "Safari / suit / blazer", "words": ("safari", "blazer", "coat", "suit gents", "waistcoat", "jacket", "nehru jacket"),
               "fields": ["length", "chest", "waist", "hip", "shoulder", "sleeve_length", "sleeve_round", "neck"],
               "must": 6, "days": 7},
    "alteration": {"label": "Alteration / fitting theek", "words": ("alteration", "altration", "fitting", "loose", "tight",
                                                                   "chhota", "bada", "repair", "rafu", "zip"),
                   "fields": [], "must": 0, "days": 1},
    "other": {"label": "Kuch aur", "words": (), "fields": [], "must": 0, "days": 3},
}


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[_\-]+", " ", str(s or "").lower())).strip()


def garment_of(text: str) -> str:
    """'saree blouse' -> blouse, 'gents kurta' -> kurta_pajama. Longest matching word wins; unknown -> other."""
    t = _norm(text)
    if t in GARMENTS:
        return t
    best, size = "other", 0
    for gid, g in GARMENTS.items():
        for w in g["words"]:
            if re.search(r"(?<![a-z])" + re.escape(w) + r"(?![a-z])", t) and len(w) > size:
                best, size = gid, len(w)
    return best


def field_of(word: str) -> str:
    w = _norm(word)
    if w in FIELDS:
        return w
    for fid, (_label, words) in FIELDS.items():
        if w in words:
            return fid
    return ""


_NUM = r"\d+(?:\.\d+)?(?:\s+\d/\d|\s*½|\s*¼|\s*¾)?|\d/\d"


def to_number(raw: str) -> float | None:
    """'11 1/2' -> 11.5, '34½' -> 34.5, '7.25' -> 7.25."""
    s = str(raw or "").strip().replace("½", " 1/2").replace("¼", " 1/4").replace("¾", " 3/4")
    try:
        return float(sum(Fraction(p) for p in s.split()))
    except (ValueError, ZeroDivisionError):
        return None


def parse(text: str) -> dict[str, float]:
    """Read 'L 15 chest 34 kamar 30 bahi 11 1/2 gala aage 7 peeche 8' into {field: number}. Words it doesn't know are
    skipped (the caller shows what was understood, so nothing is guessed silently)."""
    t = _norm(text).replace("=", " ").replace(":", " ").replace(",", " ; ").replace("\n", " ; ")
    words = sorted({w for _f, (_l, ws) in FIELDS.items() for w in ws} | set(FIELDS), key=len, reverse=True)
    pat = re.compile(r"(?<![a-z])(" + "|".join(re.escape(w) for w in words) + r")(?![a-z])\s*(?:-|is|hai)?\s*(" + _NUM + r")")
    out: dict[str, float] = {}
    for m in pat.finditer(t):
        f = field_of(m.group(1))
        n = to_number(m.group(2))
        if f and n is not None:
            out[f] = n
    # "gala aage 7 peeche 8": 'peeche' alone right after a front neck means the back neck
    m = re.search(r"(?:aage|front)\s*(" + _NUM + r")\s*(?:;|\s)*(?:peeche|piche|back)\s*(" + _NUM + r")", t)
    if m:
        out["front_neck"], out["back_neck"] = to_number(m.group(1)), to_number(m.group(2))
    return out


def clean_values(values: dict | str | None) -> dict[str, float]:
    """Model / app input -> {field: number}: known names or synonyms only, numbers as numbers."""
    if isinstance(values, str):
        return parse(values)
    out: dict[str, float] = {}
    for k, v in (values or {}).items():
        f = field_of(k)
        n = v if isinstance(v, (int, float)) else to_number(str(v))
        if f and n is not None and 0 < float(n) < 400:
            out[f] = round(float(n), 2)
    return out


def missing(garment: str, values: dict[str, float]) -> list[str]:
    g = GARMENTS.get(garment) or GARMENTS["other"]
    return [f for f in g["fields"][: g["must"]] if f not in values]


def label(field: str) -> str:
    return FIELDS.get(field, (field,))[0]


def listing() -> list[dict]:
    return [{"id": gid, "label": g["label"], "fields": [{"id": f, "label": label(f)} for f in g["fields"]],
             "must": g["fields"][: g["must"]], "days": g["days"]} for gid, g in GARMENTS.items()]
