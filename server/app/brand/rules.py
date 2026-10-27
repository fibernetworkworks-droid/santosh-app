"""v0.118 Brand Sahayak: platform sizes, colour maths, festival themes and the design rules (pure functions).

Sources (22 Oct 2026):
- Instagram 2026: feed 4:5 1080x1350 default, 3:4 1080x1440 fills the new taller profile grid, 1:1 1080x1080; Stories /
  Reels 1080x1920 with ~150 px top and ~250 px bottom kept free of text (inro.social, skedsocial.com 2026 guides).
- Sprout Social size guide (May 2026): Facebook feed 1080x1350, Facebook cover 851x315, LinkedIn 1200x627, X 1600x900,
  YouTube thumbnail 16:9 (1280x720 minimum), Pinterest 1000x1500, Google Business Profile photo 720x720+ (posts 4:3).
- WCAG 2.2 contrast: 4.5:1 for normal text, 3:1 for large text (>= 24 px, or 18.66 px bold).
- Print: 300 dpi for paper (150 dpi is the floor for photos), 3 mm bleed on each side; flex banners print fine at
  ~100 dpi. Hoola's PDF is RGB: the printer converts to CMYK (ask him for a proof).
- Emblems and Names (Prevention of Improper Use) Act 1950, Schedule (industries.delhi.gov.in): the Indian National
  Flag, the Government of India / State emblems and seals, the Ashoka Chakra / Dharma Chakra, names or pictures of
  Mahatma Gandhi, Nehru, Indira Gandhi, Chhatrapati Shivaji Maharaj, the Prime Minister, Rashtrapati Bhavan, Parliament,
  courts, UN / WHO / Olympic rings, Red-Cross-type bodies may not be used for trade or advertising without permission.
- ASCI / CCPA claim rules: same checks as the content writer (kalam.service.RISK).
"""
from __future__ import annotations

import colorsys
import re
from typing import Any

# ---------------------------------------------------------------- sizes (px for screens, mm for paper)
SIZES: dict[str, dict[str, Any]] = {
    "insta_post": {"label": "Instagram post 4:5", "w": 1080, "h": 1350, "safe": (60, 60)},
    "insta_square": {"label": "Instagram / WhatsApp square", "w": 1080, "h": 1080, "safe": (60, 60)},
    "insta_grid": {"label": "Instagram 3:4 (grid)", "w": 1080, "h": 1440, "safe": (70, 70)},
    "story": {"label": "Story / Reel cover / WhatsApp status", "w": 1080, "h": 1920, "safe": (160, 260)},
    "fb_post": {"label": "Facebook post", "w": 1080, "h": 1350, "safe": (60, 60)},
    "fb_cover": {"label": "Facebook cover", "w": 1702, "h": 630, "safe": (40, 40)},
    "linkedin": {"label": "LinkedIn post", "w": 1200, "h": 627, "safe": (40, 40)},
    "x_post": {"label": "X post", "w": 1600, "h": 900, "safe": (40, 40)},
    "yt_thumb": {"label": "YouTube thumbnail", "w": 1280, "h": 720, "safe": (40, 40)},
    "gbp": {"label": "Google Business post 4:3", "w": 1200, "h": 900, "safe": (40, 40)},
    "pinterest": {"label": "Pinterest pin", "w": 1000, "h": 1500, "safe": (60, 60)},
    "a4": {"label": "A4 poster / flyer (print)", "mm": (210, 297), "w": 1240, "h": 1754, "print": True, "bleed": 3},
    "a3": {"label": "A3 poster (print)", "mm": (297, 420), "w": 1240, "h": 1754, "print": True, "bleed": 3},
    "a5": {"label": "A5 handbill (print)", "mm": (148, 210), "w": 1240, "h": 1760, "print": True, "bleed": 3},
    "flex_6x3": {"label": "Flex banner 6x3 ft (print)", "mm": (1829, 914), "w": 2000, "h": 1000, "print": True, "bleed": 0,
                 "dpi": 100},
}
SETS = {
    "social": ["insta_post", "story", "fb_post", "insta_square"],
    "whatsapp": ["insta_square", "story"],
    "all_social": ["insta_post", "insta_square", "insta_grid", "story", "fb_post", "linkedin", "x_post", "gbp",
                   "pinterest", "yt_thumb"],
    "print": ["a4"],
    "festival": ["insta_post", "story", "insta_square"],
}
ALIASES = {"instagram": "insta_post", "insta": "insta_post", "post": "insta_post", "square": "insta_square",
           "whatsapp": "insta_square", "status": "story", "whatsapp_status": "story", "reel": "story", "stories": "story",
           "facebook": "fb_post", "fb": "fb_post", "cover": "fb_cover", "youtube": "yt_thumb", "thumbnail": "yt_thumb",
           "google": "gbp", "gmb": "gbp", "twitter": "x_post", "x": "x_post", "flyer": "a4", "pamphlet": "a5",
           "handbill": "a5", "banner": "flex_6x3", "flex": "flex_6x3", "poster": "a4"}

KINDS = {
    "poster": "Poster / post (offer, launch, news)",
    "festival": "Tyohar ki badhai",
    "offer": "Offer / sale / daam",
    "event": "Event / workshop / camp",
    "hiring": "Naukri / hiring",
    "product": "Product photo post",
    "quote": "Vichar / tip / review card",
    "announcement": "Suchna (band / naya time / naya pata)",
}
LAYOUTS = ("hero", "photo", "split", "minimal", "festival", "offer")
KIND_LAYOUT = {"poster": "hero", "festival": "festival", "offer": "offer", "event": "hero", "hiring": "minimal",
               "product": "photo", "quote": "minimal", "announcement": "minimal"}

FONTS = {   # bundled OFL fonts (app/motion/assets/fonts) - nothing is downloaded at render time
    "poppins": {"label": "Poppins (modern)", "family": "Poppins"},
    "mukta": {"label": "Mukta (Hindi / Marathi)", "family": "Mukta"},
}

LIMITS = {"headline": 48, "sub": 110, "offer": 26, "cta": 28, "body": 220, "date": 60}

# ---------------------------------------------------------------- festivals (original motifs drawn in SVG by Hoola)
FESTIVALS = [
    # (words in the holiday name, theme)
    (("diwali", "deepavali", "dipawali", "दिवाली"), {"key": "diwali", "motif": "diya", "colors": ["#7A1F3D", "#F5A623", "#FFD36E"],
     "greet": {"hi": "शुभ दीपावली", "mr": "दिवाळीच्या हार्दिक शुभेच्छा", "en": "Happy Diwali"}}),
    (("dussehra", "dasara", "vijayadashami", "दशहरा"), {"key": "dussehra", "motif": "toran", "colors": ["#8B1E1E", "#F28C28", "#FFE08A"],
     "greet": {"hi": "विजयादशमी की शुभकामनाएँ", "mr": "दसऱ्याच्या हार्दिक शुभेच्छा", "en": "Happy Dussehra"}}),
    (("navratri", "durga", "नवरात्रि"), {"key": "navratri", "motif": "rangoli", "colors": ["#B0124F", "#F7B32B", "#2D936C"],
     "greet": {"hi": "शुभ नवरात्रि", "mr": "नवरात्रीच्या शुभेच्छा", "en": "Happy Navratri"}}),
    (("holi", "होली"), {"key": "holi", "motif": "splash", "colors": ["#E83F6F", "#2274A5", "#FFBF00"],
     "greet": {"hi": "होली की शुभकामनाएँ", "mr": "होळीच्या शुभेच्छा", "en": "Happy Holi"}}),
    (("ganesh", "ganesha", "vinayaka", "गणेश"), {"key": "ganesh", "motif": "toran", "colors": ["#C2410C", "#FBBF24", "#7C2D12"],
     "greet": {"hi": "गणेश चतुर्थी की शुभकामनाएँ", "mr": "गणेशोत्सवाच्या हार्दिक शुभेच्छा", "en": "Happy Ganesh Chaturthi"}}),
    (("sankranti", "pongal", "lohri", "uttarayan", "bihu"), {"key": "sankranti", "motif": "kite", "colors": ["#0E7490", "#F59E0B", "#FDE68A"],
     "greet": {"hi": "मकर संक्रांति की शुभकामनाएँ", "mr": "तिळगूळ घ्या, गोड गोड बोला", "en": "Happy Makar Sankranti"}}),
    (("eid", "ramzan", "bakrid", "id-ul", "id ul", "muharram", "milad"), {"key": "eid", "motif": "moon", "colors": ["#064E3B", "#D4AF37", "#F5F0E1"],
     "greet": {"hi": "ईद मुबारक", "mr": "ईद मुबारक", "en": "Eid Mubarak"}}),
    (("christmas",), {"key": "christmas", "motif": "tree", "colors": ["#14532D", "#B91C1C", "#FDE68A"],
     "greet": {"hi": "मेरी क्रिसमस", "mr": "नाताळच्या शुभेच्छा", "en": "Merry Christmas"}}),
    (("new year",), {"key": "newyear", "motif": "sparkle", "colors": ["#1E1B4B", "#F59E0B", "#E0E7FF"],
     "greet": {"hi": "नववर्ष की शुभकामनाएँ", "mr": "नववर्षाच्या शुभेच्छा", "en": "Happy New Year"}}),
    (("gudi padwa", "ugadi", "gudi"), {"key": "padwa", "motif": "toran", "colors": ["#9A3412", "#FACC15", "#15803D"],
     "greet": {"hi": "गुड़ी पड़वा की शुभकामनाएँ", "mr": "गुढीपाडव्याच्या हार्दिक शुभेच्छा", "en": "Happy Gudi Padwa"}}),
    (("raksha", "rakhi"), {"key": "rakhi", "motif": "rangoli", "colors": ["#9D174D", "#F59E0B", "#FCE7F3"],
     "greet": {"hi": "रक्षाबंधन की शुभकामनाएँ", "mr": "रक्षाबंधनाच्या शुभेच्छा", "en": "Happy Raksha Bandhan"}}),
    (("janmashtami", "krishna"), {"key": "janmashtami", "motif": "sparkle", "colors": ["#1E3A8A", "#FACC15", "#DBEAFE"],
     "greet": {"hi": "जन्माष्टमी की शुभकामनाएँ", "mr": "गोकुळाष्टमीच्या शुभेच्छा", "en": "Happy Janmashtami"}}),
    (("independence", "republic"), {"key": "national", "motif": "waves", "colors": ["#EA580C", "#FFFFFF", "#15803D"],
     "greet": {"hi": "हार्दिक शुभकामनाएँ", "mr": "हार्दिक शुभेच्छा", "en": "Warm wishes"},
     "note": "Rashtriya Dhwaj / Ashoka Chakra / Rajya chinh vyapar ke poster mein nahi (Emblems Act 1950): sirf rang ki lehrein."}),
    (("guru nanak", "gurpurab"), {"key": "gurpurab", "motif": "sparkle", "colors": ["#1E3A8A", "#F59E0B", "#FEF3C7"],
     "greet": {"hi": "गुरु पर्व की लख-लख बधाइयाँ", "mr": "गुरुपर्वाच्या शुभेच्छा", "en": "Happy Gurpurab"}}),
    (("chhath",), {"key": "chhath", "motif": "diya", "colors": ["#9A3412", "#F59E0B", "#FDE68A"],
     "greet": {"hi": "छठ पूजा की शुभकामनाएँ", "mr": "छठ पूजेच्या शुभेच्छा", "en": "Happy Chhath Puja"}}),
    (("bhai duj", "bhaidooj", "bhau beej"), {"key": "bhaiduj", "motif": "diya", "colors": ["#7C2D12", "#F59E0B", "#FFEDD5"],
     "greet": {"hi": "भाई दूज की शुभकामनाएँ", "mr": "भाऊबीजेच्या शुभेच्छा", "en": "Happy Bhai Dooj"}}),
    (("karwa", "karaka"), {"key": "karwa", "motif": "moon", "colors": ["#831843", "#F59E0B", "#FCE7F3"],
     "greet": {"hi": "करवा चौथ की शुभकामनाएँ", "mr": "करवा चौथच्या शुभेच्छा", "en": "Happy Karwa Chauth"}}),
    (("onam",), {"key": "onam", "motif": "rangoli", "colors": ["#166534", "#EAB308", "#FEF9C3"],
     "greet": {"hi": "ओणम की शुभकामनाएँ", "mr": "ओणमच्या शुभेच्छा", "en": "Happy Onam"}}),
]
DEFAULT_FEST = {"key": "festival", "motif": "sparkle", "colors": ["#3F1D5C", "#F5A623", "#FFF4D6"],
                "greet": {"hi": "हार्दिक शुभकामनाएँ", "mr": "हार्दिक शुभेच्छा", "en": "Warm wishes"}}


def festival_theme(name: str) -> dict[str, Any]:
    t = (name or "").lower()
    for words, theme in FESTIVALS:
        if any(w in t for w in words):
            return dict(theme)
    return dict(DEFAULT_FEST)


# ---------------------------------------------------------------- things a business poster may not carry
PROTECTED = [
    (r"\b(national flag|tiranga|tricolou?r flag|rashtriya dhwaj|तिरंगा|राष्ट्रीय ध्वज)\b", "Rashtriya Dhwaj"),
    (r"\b(ashoka chakra|dharma chakra|ashok chakra|ashoka emblem|lion capital|state emblem|satyamev jayate|अशोक चक्र|सत्यमेव जयते)\b",
     "Ashoka Chakra / Rajya chinh"),
    (r"\b(mahatma gandhi|gandhi ?ji|bapu|nehru|indira gandhi|shivaji maharaj|chhatrapati shivaji|prime minister|pradhan ?mantri|"
     r"modi ?ji|narendra modi|rashtrapati|president of india|राष्ट्रपति|प्रधानमंत्री|महात्मा गांधी)\b",
     "Gandhi / Nehru / Indira Gandhi / Shivaji Maharaj / Pradhan Mantri / Rashtrapati ka naam ya photo"),
    (r"\b(government of india|bharat sarkar|govt\.? of india|bharat sarkar ki|bhaarat sarkaar|bhaarat sarkar|"
     r"maharashtra shasan|sarkari yojana ka logo|भारत सरकार)\b", "Sarkar ka naam / chinh (sarkari jud-ne ka bhram)"),
    (r"\b(olympic|olympics|unesco|united nations|who approved|red cross|interpol)\b", "UN / WHO / Olympic / Red Cross jaisa naam"),
]
LOGO_WORDS = r"\b(logo|chinh|nishan)\b"


def protected(text: str) -> list[str]:
    t = (text or "").lower()
    return [label for pat, label in PROTECTED if re.search(pat, t, re.I)]


# ---------------------------------------------------------------- colour maths
def hex_ok(v: str) -> bool:
    return bool(re.fullmatch(r"#[0-9a-fA-F]{6}", (v or "").strip()))


def norm_hex(v: str) -> str:
    v = (v or "").strip()
    if re.fullmatch(r"#?[0-9a-fA-F]{3}", v):
        v = v.lstrip("#")
        v = "#" + "".join(c * 2 for c in v)
    if re.fullmatch(r"[0-9a-fA-F]{6}", v):
        v = "#" + v
    return v.upper() if hex_ok(v) else ""


NAMED = {"red": "#D32F2F", "laal": "#D32F2F", "lal": "#D32F2F", "maroon": "#7A1F3D", "orange": "#F57C00", "kesari": "#F57C00",
         "saffron": "#F57C00", "yellow": "#F9C80E", "peela": "#F9C80E", "pila": "#F9C80E", "gold": "#C9A227", "sunehra": "#C9A227",
         "green": "#2E7D32", "hara": "#2E7D32", "blue": "#1565C0", "neela": "#1565C0", "nila": "#1565C0", "navy": "#0B2545",
         "sky": "#4FC3F7", "aasmani": "#4FC3F7", "purple": "#6A1B9A", "baingani": "#6A1B9A", "pink": "#E91E63", "gulabi": "#E91E63",
         "black": "#111111", "kaala": "#111111", "kala": "#111111", "white": "#FFFFFF", "safed": "#FFFFFF", "grey": "#616161",
         "brown": "#6D4C41", "teal": "#00897B", "cream": "#FFF8E1"}


def parse_color(v: str) -> str:
    h = norm_hex(v)
    if h:
        return h
    return NAMED.get((v or "").strip().lower(), "")


def rgb(h: str) -> tuple[int, int, int]:
    h = norm_hex(h) or "#000000"
    return int(h[1:3], 16), int(h[3:5], 16), int(h[5:7], 16)


def to_hex(r: float, g: float, b: float) -> str:
    return "#%02X%02X%02X" % tuple(max(0, min(255, int(round(x)))) for x in (r, g, b))


def luminance(h: str) -> float:
    def ch(c: int) -> float:
        c = c / 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = rgb(h)
    return 0.2126 * ch(r) + 0.7152 * ch(g) + 0.0722 * ch(b)


def contrast(a: str, b: str) -> float:
    la, lb = luminance(a), luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return round((hi + 0.05) / (lo + 0.05), 2)


def mix(a: str, b: str, t: float) -> str:
    ra, ga, ba = rgb(a)
    rb, gb, bb = rgb(b)
    return to_hex(ra + (rb - ra) * t, ga + (gb - ga) * t, ba + (bb - ba) * t)


def best_text(bg: str, candidates: list[str] | None = None) -> str:
    """The text colour that reads best on bg (her dark / light first, then pure black / white)."""
    cands = [c for c in (candidates or []) if hex_ok(c)] + ["#111111", "#FFFFFF"]
    return max(cands, key=lambda c: contrast(bg, c))


def readable(bg: str, fg: str, large: bool = False) -> bool:
    return contrast(bg, fg) >= (3.0 if large else 4.5)


def saturation(h: str) -> float:
    r, g, b = (x / 255 for x in rgb(h))
    return colorsys.rgb_to_hls(r, g, b)[2]


def palette_from_image(data: bytes, n: int = 5) -> list[str]:
    """Main colours of her logo: transparent / near-white / near-black pixels skipped, most used + most colourful first."""
    import io

    from PIL import Image
    im = Image.open(io.BytesIO(data)).convert("RGBA")
    im.thumbnail((160, 160))
    data = im.get_flattened_data() if hasattr(im, "get_flattened_data") else im.getdata()
    px = [p for p in data if p[3] > 128]
    keep = [p[:3] for p in px if not (min(p[:3]) > 235) and not (max(p[:3]) < 22)]
    if len(keep) < 20:
        keep = [p[:3] for p in px] or [(17, 17, 17)]
    small = Image.new("RGB", (len(keep), 1))
    small.putdata(keep)
    q = small.quantize(colors=min(8, max(2, len(set(keep)))), method=Image.Quantize.MEDIANCUT)
    pal = q.getpalette() or []
    counts = sorted(q.getcolors() or [], reverse=True)
    out: list[str] = []
    for cnt, idx in counts:
        c = to_hex(*pal[idx * 3: idx * 3 + 3])
        if all(_dist(c, o) > 48 for o in out):
            out.append(c)
    out.sort(key=lambda c: -(saturation(c) * 0.6 + 0.4))   # stable: colourful before grey, frequency kept within ties
    return out[:n]


def _dist(a: str, b: str) -> float:
    ra, ga, ba = rgb(a)
    rb, gb, bb = rgb(b)
    return ((ra - rb) ** 2 + (ga - gb) ** 2 + (ba - bb) ** 2) ** 0.5


def kit_colors(palette: list[str]) -> dict[str, str]:
    """primary / secondary / accent / dark / light from a palette, so text always has a readable partner."""
    p = [c for c in palette if hex_ok(c)] or ["#1565C0"]
    usable = [c for c in p if 0.02 < luminance(c) < 0.85] or p      # the brand colours, not her black / white
    primary = usable[0]
    others = [c for c in usable[1:] if _dist(c, primary) > 90]
    accent = others[0] if others else ("#F5A623" if _dist(primary, "#F5A623") > 120 else "#1E88E5")
    secondary = others[1] if len(others) > 1 else mix(primary, "#FFFFFF", 0.35)
    darks = [c for c in p if luminance(c) < 0.03 and c not in (primary, accent)]
    lights = [c for c in p if luminance(c) > 0.8 and c not in (primary, accent)]
    dark = darks[0] if darks else mix(primary, "#000000", 0.75)
    light = lights[0] if lights else mix(primary, "#FFFFFF", 0.92)
    return {"primary": primary, "secondary": secondary, "accent": accent, "dark": dark, "light": light}


# ---------------------------------------------------------------- picking sizes
def sizes_of(v: Any, kind: str = "poster") -> list[str]:
    if isinstance(v, str):
        v = [x for x in re.split(r"[,\s/]+", v) if x]
    out: list[str] = []
    for x in v or []:
        x = str(x).strip().lower().replace("-", "_")
        if x in SETS:
            out += SETS[x]
        elif x in SIZES:
            out.append(x)
        elif x in ALIASES:
            out.append(ALIASES[x])
    if not out:
        out = list(SETS["festival" if kind == "festival" else "social"])
    seen: list[str] = []
    for x in out:
        if x not in seen:
            seen.append(x)
    return seen[:14]


def aspect(size: str) -> str:
    s = SIZES[size]
    r = s["w"] / s["h"]
    return "tall" if r < 0.7 else "portrait" if r < 0.95 else "square" if r < 1.15 else "wide" if r < 2.2 else "banner"


def needed_px(size: str, box_frac: float = 1.0) -> int:
    """Pixels a photo needs across its box: screen formats = the box width; print = 150 dpi at its real width."""
    s = SIZES[size]
    if s.get("print"):
        mm = s["mm"][0] * box_frac
        return int(mm / 25.4 * 150)
    return int(s["w"] * box_frac)


def phone_ok(p: str) -> bool:
    d = re.sub(r"\D", "", p or "")
    return len(d) in (10, 11, 12) and (len(d) != 10 or d[0] in "6789")
