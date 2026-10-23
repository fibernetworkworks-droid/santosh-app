"""Feedback Sahayak rules: language, sentiment and aspects (English / Hinglish / Hindi / Marathi), NPS / CSAT maths,
theme trend and spike tests, impact weights, suspicious-review signals and reply checks. Pure functions, no database.

Research (23 Oct 2026):
- IS 19000:2022 "Online Consumer Reviews - Principles and Requirements for their Collection, Moderation and Publication"
  (BIS + Department of Consumer Affairs, in force 25 Nov 2022, voluntary with a BIS conformity scheme): covers platforms AND
  sellers / brands that collect reviews from their own customers; reviewer traceability (email / phone / link check), paid or
  reward-based reviews must be marked, no purchased reviews, a published code of practice, a review once live is not edited
  by the business. mondaq.com/Article/1259220, inc42.com (Nov 2022).
- CCPA Guidelines for Prevention and Regulation of Dark Patterns, 2023 (13 patterns incl. disguised advertisement, false
  urgency) + CCPA advisory 5 Jun 2025: e-commerce platforms to self-audit within 3 months and self-declare (storyboard18.com,
  barandbench.com). Misleading ads: penalty up to Rs 10 lakh, Rs 50 lakh for repeats (Consumer Protection Act 2019 s.21).
- Google review policy (Maps user-generated content / fake engagement): no incentives for reviews, no review gating
  (asking only happy customers), no reviews by owners / staff, no asking to change or remove a review; a business may flag
  a review through Business Profile > Reviews > Report (brightlocal.com review platform guidelines; applausehq.com).
- Google Business Profile API: accounts.locations.reviews list / get / updateReply (v4, scope business.manage, API access
  needs Google's approval); 2026 additions ReviewReplyState (1 Apr), ReviewMediaItem (20 Apr), PolicyViolation on replies
  (1 Jul), reviewReplyUrl (24 Jul) (developers.google.com/my-business/content/latest-updates). Reply comment <= 4096 bytes.
- NPS (Bain / Reichheld): promoters 9-10, passives 7-8, detractors 0-6, NPS = %P - %D; CSAT = share of 4-5 on a 1-5 scale.
"""
from __future__ import annotations

import math
import re
import unicodedata
from typing import Any

NEVER = (
    "Kisi review ko hatana, chhupana ya sirf achhe reviews dikhana (IS 19000:2022, Google policy).",
    "Sirf khush graahakon se review maangna (review gating) - survey ke baad review ka link sabko ek jaisa.",
    "Review badalne / hatane ke badle discount, cashback ya gift.",
    "Apne ya staff ke naam se review likhna / likhwana, paise de kar review.",
    "Public review ka jawab owner ki haan ke bina daalna.",
    "Graahak ka phone, address, order number public jawab mein likhna.",
)

LANGS = {"hi": "Hindi", "mr": "Marathi", "en": "English", "hinglish": "Hinglish"}

# ---------------------------------------------------------------- words
POS = {
    # English
    "good": 1, "great": 1.4, "excellent": 1.6, "awesome": 1.5, "nice": 1, "best": 1.4, "love": 1.4, "loved": 1.4, "amazing": 1.5,
    "tasty": 1.2, "delicious": 1.4, "fresh": 1, "clean": 1, "friendly": 1.2, "polite": 1.2, "fast": 1, "quick": 1, "helpful": 1.2,
    "recommend": 1.2, "recommended": 1.2, "perfect": 1.5, "superb": 1.5, "happy": 1.1, "satisfied": 1.1, "worth": 1, "fantastic": 1.5,
    "wonderful": 1.4, "courteous": 1.2, "professional": 1, "reasonable": 0.8, "affordable": 0.8, "on time": 1, "thank you": 0.6,
    "thanks": 0.5, "beautiful": 1.1, "comfortable": 1, "smooth": 0.9, "genuine": 0.9, "hygienic": 1.1,
    # Hinglish (Latin)
    "accha": 1, "achha": 1, "acha": 1, "achchha": 1, "badhiya": 1.3, "badiya": 1.3, "mast": 1.3, "zabardast": 1.5,
    "jabardast": 1.5, "shandaar": 1.5, "shandar": 1.5, "khush": 1.1, "swadisht": 1.3, "saaf": 1, "saf suthra": 1.1, "jaldi": 0.7,
    "paisa vasool": 1.4, "paisa wasool": 1.4, "maza aaya": 1.3, "maja aaya": 1.3, "behtareen": 1.5, "behtrin": 1.5, "sahi hai": 0.8,
    "lajawab": 1.5, "first class": 1.3, "ekdum sahi": 1.2,
    # Marathi (Latin)
    "chhan": 1.2, "chan": 1.2, "chaan": 1.2, "uttam": 1.4, "avadla": 1.2, "aavadla": 1.2, "avadle": 1.2, "chavishta": 1.3,
    "bhari": 1.2, "lay bhari": 1.5, "swachh": 1,
    # Hindi (Devanagari)
    "अच्छा": 1, "अच्छी": 1, "बढ़िया": 1.3, "बढिया": 1.3, "शानदार": 1.5, "स्वादिष्ट": 1.3, "खुश": 1.1, "साफ": 1, "बेहतरीन": 1.5,
    "लाजवाब": 1.5, "धन्यवाद": 0.6, "मज़ा": 1.1, "मजा": 1.1,
    # Marathi (Devanagari)
    "छान": 1.2, "उत्तम": 1.4, "आवडले": 1.2, "आवडलं": 1.2, "मस्त": 1.3, "चविष्ट": 1.3, "स्वच्छ": 1, "भारी": 1.2,
}
NEG = {
    # English
    "bad": 1, "worst": 1.6, "poor": 1.2, "terrible": 1.5, "horrible": 1.5, "rude": 1.4, "late": 1, "delay": 1, "delayed": 1.1,
    "slow": 0.9, "dirty": 1.3, "stale": 1.3, "expensive": 0.8, "overpriced": 1.1, "broken": 1.2, "damaged": 1.2, "defective": 1.3,
    "wrong": 1, "missing": 1.1, "refund": 0.6, "fraud": 1.8, "cheat": 1.6, "cheated": 1.6, "waste": 1.2, "disappointed": 1.3,
    "disappointing": 1.3, "unhygienic": 1.5, "smell": 0.9, "rotten": 1.6, "insect": 1.6, "cockroach": 1.8, "problem": 0.7,
    "issue": 0.6, "complaint": 0.8, "not working": 1.2, "never again": 1.5, "pathetic": 1.6, "useless": 1.4, "cold": 0.5,
    "unprofessional": 1.3, "careless": 1.1, "overcharged": 1.3, "no response": 1.2, "not responding": 1.2, "bland": 0.9,
    "awful": 1.5, "scam": 1.8, "fake": 1.2, "hate": 1.4, "spoiled": 1.4, "leak": 1, "leaking": 1, "torn": 1, "unsafe": 1.4,
    # Hinglish (Latin)
    "bekar": 1.3, "bekaar": 1.3, "bakwas": 1.5, "bakwaas": 1.5, "ghatiya": 1.6, "kharab": 1.2, "ganda": 1.3, "gandi": 1.3,
    "der": 0.8, "thanda": 0.6, "mehenga": 0.8, "mehnga": 0.8, "mahanga": 0.8, "toota": 1.1, "tuta": 1.1, "galat": 1,
    "nahi aaya": 1.1, "nahi mila": 1.1, "dhokha": 1.7, "barbaad": 1.4, "badtameez": 1.5, "baasi": 1.3, "sada hua": 1.5,
    "keeda": 1.7, "kida": 1.7, "faltu": 1.2, "bura": 1.1, "ghatia": 1.6, "chuna lagaya": 1.6, "thagi": 1.6, "pareshan": 1,
    "pareshani": 1, "intezaar": 0.7, "intezar": 0.7,
    # Marathi (Latin)
    "vait": 1.2, "waeet": 1.2, "ghan": 1.2, "ushir": 0.9, "mahag": 0.8, "tutla": 1.1, "chukicha": 1, "fasavnuk": 1.7,
    # Hindi (Devanagari)
    "खराब": 1.2, "बेकार": 1.3, "घटिया": 1.6, "गंदा": 1.3, "गंदी": 1.3, "देर": 0.8, "महंगा": 0.8, "टूटा": 1.1, "गलत": 1,
    "धोखा": 1.7, "बासी": 1.3, "बदतमीज": 1.5, "बदतमीज़": 1.5, "बकवास": 1.5, "कीड़ा": 1.7, "बुरा": 1.1, "परेशान": 1,
    # Marathi (Devanagari)
    "वाईट": 1.2, "घाण": 1.2, "उशीर": 0.9, "महाग": 0.8, "तुटलेले": 1.1, "चुकीचे": 1, "फसवणूक": 1.7, "बेकार ": 1.3,
}
NEGATORS = {"not", "no", "never", "nahi", "nahin", "nai", "na", "mat", "didnt", "didn't", "dont", "don't", "wasnt", "wasn't",
            "isnt", "isn't", "nahi tha", "नहीं", "नही", "नाही", "नको", "ना"}
INTENS = {"very": 1.5, "bahut": 1.5, "bohot": 1.5, "bahot": 1.5, "khup": 1.5, "ekdum": 1.4, "really": 1.3, "too": 1.3,
          "extremely": 1.7, "so": 1.2, "bilkul": 1.3, "बहुत": 1.5, "खूप": 1.5, "एकदम": 1.4, "अत्यंत": 1.6}
BUT = r"(?:\bbut\b|\blekin\b|\blekhin\b|\bmagar\b|\bhowever\b|\bthough\b|\balthough\b|\bpar\b|\bpan\b|\bparantu\b|लेकिन|मगर|परंतु|पण|पर\b)"

# aspect id -> (label, words, fixability 0..1, urgent)
ASPECTS: dict[str, tuple[str, tuple[str, ...], float, bool]] = {
    "food_safety": ("Khane mein baal / keeda / bimari", ("hair in", "baal tha", "baal mila", "insect", "cockroach", "keeda", "kida", "worm",
                    "food poisoning", "vomit", "ulti", "stomach upset", "pet kharab", "expired", "fungus", "rotten", "sada hua", "बाल",
                    "कीड़ा", "उल्टी", "एक्सपायर", "allergy", "hospital"), 1.0, True),
    "safety": ("Suraksha / badsalooki", ("harass", "harassment", "misbehave", "misbehaved", "threat", "unsafe", "abuse", "abused",
               "chhed", "gaali", "injury", "chot lagi", "current laga", "shock laga", "fire", "धमकी", "गाली"), 1.0, True),
    "fraud": ("Dhokha / nakli maal", ("fraud", "cheat", "cheated", "scam", "dhokha", "thagi", "fake product", "duplicate product",
              "nakli", "chuna lagaya", "fasavnuk", "धोखा", "नकली", "फसवणूक"), 1.0, True),
    "taste": ("Swaad / khana", ("khana", "khaana", "food", "jevan", "jevan", "खाना", "जेवण", "taste", "tasty", "tasteless", "swad", "swaad", "flavour", "flavor", "bland", "spicy", "teekha", "tikha",
              "namak", "salty", "oily", "delicious", "swadisht", "chav", "chavishta", "स्वाद", "चव", "स्वादिष्ट", "चविष्ट"), 0.8, False),
    "freshness": ("Taazgi", ("fresh", "stale", "baasi", "basi", "shila", "not fresh", "thanda khana", "food was cold", "बासी", "शिळे"), 0.9, False),
    "quantity": ("Matra / quantity", ("quantity", "portion", "matra", "small portion", "kam diya", "less quantity", "too less",
                 "मात्रा"), 0.8, False),
    "price": ("Daam", ("price", "pricing", "expensive", "costly", "overpriced", "mehenga", "mehnga", "mahanga", "rate", "cheap",
              "sasta", "value for money", "paisa vasool", "paisa wasool", "affordable", "reasonable", "mahag", "महंगा", "महाग",
              "किंमत", "दाम"), 0.5, False),
    "billing": ("Bill / zyada paise", ("bill", "billing", "overcharged", "overcharge", "extra charge", "charged extra", "charged twice",
                "double charge", "receipt", "invoice", "zyada paise", "jyada paise", "mrp se zyada", "बिल"), 0.9, False),
    "staff": ("Staff / seva", ("staff", "service", "waiter", "rude", "behaviour", "behavior", "attitude", "polite", "friendly", "courteous",
              "badtameez", "tameez", "manager", "employee", "receptionist", "owner was", "vagnuk", "वागणूक", "व्यवहार", "स्टाफ",
              "बदतमीज"), 1.0, False),
    "wait": ("Intezaar / der", ("wait", "waiting", "waited", "slow service", "late", "der", "delay", "queue", "line mein",
             "intezaar", "intezar", "time laga", "ghanta", "hour", "ushir", "उशीर", "देर", "इंतजार"), 0.9, False),
    "delivery": ("Delivery", ("delivery", "delivered", "courier", "rider", "delivery boy", "shipping", "dispatch", "parcel",
                 "not delivered", "deliver", "पार्सल", "डिलीवरी"), 0.8, False),
    "packaging": ("Packing", ("packing", "packaging", "packed", "spill", "spilled", "leak", "leaking", "seal", "dabba", "box was",
                  "पैकिंग"), 1.0, False),
    "quality": ("Quality", ("quality", "material", "durable", "fabric", "kapda", "build quality", "finishing", "stitching",
                "गुणवत्ता", "क्वालिटी"), 0.6, False),
    "defect": ("Kharab / toota maal", ("broken", "damaged", "defective", "not working", "kaam nahi karta", "chalu nahi", "toota",
               "tuta", "crack", "faulty", "dead on arrival", "tutla", "टूटा", "तुटलेले"), 0.6, False),
    "wrong_item": ("Galat / kam saamaan", ("wrong item", "wrong product", "wrong order", "galat item", "galat saman", "galat saamaan",
                   "missing", "item missing", "nahi mila", "not received", "different product", "chukicha", "गलत"), 0.9, False),
    "fit": ("Size / fitting", ("size", "fitting", "fit", "tight", "loose", "chhota", "bada size", "साइज"), 0.6, False),
    "refund": ("Refund / return", ("refund", "return", "replacement", "exchange", "paisa wapas", "paise wapas", "money back",
               "cancel", "cancelled", "रिफंड", "वापस"), 0.8, False),
    "clean": ("Safai", ("clean", "cleanliness", "dirty", "hygiene", "hygienic", "unhygienic", "ganda", "gandi", "saaf", "safai",
              "washroom", "toilet", "smell", "badbu", "ghan", "swachh", "साफ", "सफाई", "गंदा", "घाण", "स्वच्छ"), 1.0, False),
    "ambience": ("Mahaul / baithne ki jagah", ("ambience", "ambiance", "music", "seating", "decor", "crowd", "noise", "noisy",
                 "mahaul", "atmosphere", "a/c", "ac", "garmi", "pankha", "fan", "माहौल"), 0.6, False),
    "location": ("Jagah / parking", ("parking", "location", "address", "hard to find", "road", "jagah", "dhundhna", "पार्किंग"),
                 0.2, False),
    "app": ("App / website / payment", ("app", "website", "online order", "payment", "upi", "login", "crash", "crashes", "otp",
            "ऐप"), 0.5, False),
    "response": ("Jawab / sampark", ("no response", "not responding", "no reply", "call nahi uthaya", "phone nahi uthaya",
                 "koi jawab nahi", "customer care", "support", "whatsapp", "callback", "contact", "जवाब"), 1.0, False),
    "knowledge": ("Jaankari / salah", ("explained", "knowledge", "knowledgeable", "expert", "samjhaya", "advice", "treatment",
                  "diagnosis", "doctor", "teacher", "समझाया"), 0.7, False),
    "hours": ("Samay / band tha", ("closed", "timing", "timings", "dukaan band", "shop band", "band milta", "band mila", "open late", "hours", "time pe nahi",
              "बंद"), 0.9, False),
    "availability": ("Stock / mil nahi raha", ("out of stock", "not available", "stock", "available", "khatam", "nahi tha",
                     "उपलब्ध"), 0.7, False),
    "booking": ("Booking / appointment", ("appointment", "booking", "booked", "slot", "reservation", "अपॉइंटमेंट"), 0.8, False),
}
URGENT_WORDS = tuple(w for a in ASPECTS.values() if a[3] for w in a[1])

INCENTIVE = ("review ke liye discount", "review ke badle", "discount for review", "free for review", "review ke liye free",
             "cashback for review", "paid review", "got it free for review", "review dene par", "5 star dene par",
             "in exchange for a review", "for an honest review")
GENERIC = {"good", "nice", "best", "great", "ok", "okay", "accha", "achha", "acha", "mast", "superb", "excellent", "bad", "worst",
           "very good", "nice service", "good service", "best service", "badhiya", "chhan", "छान", "अच्छा"}
STOP = set("""a an the is was were are be been it this that to of in on for and or with at by from as i we you they he she my our your
their me us them very so too also just not no yes but if then than there here have has had do did does will would can could
hai hain tha thi the ho hua hui ka ki ke ko se me mein par aur bhi to toh ye yeh wo woh is us kya kuch bahut bohot ek
koi sab hi na nahi nahin mat ji sir madam please pls also hota hoti karna kiya kiye diya liya wala wali wale aap hum mai main
mera meri mere hamara humne maine diya gaya gayi raha rahi rahe tha lekin magar pan par aaya aayi aaye mila mili zala hota hoti
hote all got get one time place really just will also our very much bhi hua hui tar ani ahe aahe hoti hota
था थी थे है हैं का की के को में और नहीं भी तो पर एक हुआ आहे होते होता आणि पण""".split())
SOURCE_PUBLIC = {"google", "play", "amazon", "flipkart", "zomato", "swiggy", "justdial", "facebook", "practo", "tripadvisor", "meesho"}
SOURCE_LABEL = {"google": "Google review", "play": "Play Store", "amazon": "Amazon", "flipkart": "Flipkart", "zomato": "Zomato",
                "swiggy": "Swiggy", "meesho": "Meesho", "survey": "Hoola survey", "gforms": "Google Form", "typeform": "Typeform",
                "surveymonkey": "SurveyMonkey", "whatsapp": "WhatsApp", "call": "Call note", "text": "Likha / chipkaya",
                "csv": "Sheet", "justdial": "Justdial", "practo": "Practo", "facebook": "Facebook"}


def norm(text: str) -> str:
    t = unicodedata.normalize("NFC", text or "").replace("​", "").replace("‌", "").replace("‍", "")
    return re.sub(r"\s+", " ", t).strip()


def _latin(p: str) -> bool:
    return all(ord(c) < 128 for c in p)


def has(text_l: str, phrase: str) -> bool:
    if _latin(phrase):
        return re.search(r"(?<![a-z0-9])" + re.escape(phrase) + r"(?![a-z0-9])", text_l) is not None
    return phrase.strip() in text_l


def lang_of(text: str) -> str:
    """hi | mr | en | hinglish (Hindi / Marathi in Latin letters count by their words; Latin Marathi -> 'mr')."""
    t = text or ""
    deva = sum(1 for c in t if "ऀ" <= c <= "ॿ")
    latin = sum(1 for c in t if c.isascii() and c.isalpha())
    try:
        from ..voicelang import detect
        d = detect(t)
        code = (d.get("lang") or "")[:2]
    except Exception:
        code = ""
    if deva and deva >= latin:
        return "mr" if code == "mr" else "hi"
    if code == "mr":
        return "mr"
    if code == "hi":
        return "hinglish"
    return "en" if latin else (code or "en")


def clauses(text: str) -> list[str]:
    t = (text or "").lower()
    parts = re.split(r"[.!?;\n।]+|,\s*|" + BUT, t)
    return [p.strip() for p in parts if p and p.strip()]


def _tokens(cl: str) -> list[str]:
    return re.findall(r"[a-z0-9']+|[ऀ-ॿ]+", cl)


def clause_score(cl: str) -> float:
    """Signed sentiment of one clause from the word lists: intensifiers multiply, a negator within 2 words flips."""
    toks = _tokens(cl)
    score = 0.0
    used: set[tuple[int, int]] = set()
    # phrases first (multi-word) so 'not working' / 'nahi aaya' count once
    for lex, sign in ((NEG, -1), (POS, 1)):
        for ph, w in lex.items():
            ph = ph.strip()
            if " " not in ph:
                continue
            if has(cl, ph):
                score += sign * w
                used.add((-1, hash(ph)))
    phrase_neg = any(has(cl, p) for p in NEG if " " in p.strip() and (p.startswith("not ") or p.startswith("no ")
                                                                        or "nahi" in p))
    for i, tok in enumerate(toks):
        w, sign = 0.0, 0
        if tok in POS:
            w, sign = POS[tok], 1
        elif tok in NEG:
            w, sign = NEG[tok], -1
        if not sign:
            continue
        mult = 1.0
        for j in range(max(0, i - 2), i):
            mult *= INTENS.get(toks[j], 1.0)
        window = toks[max(0, i - 2): i] + toks[i + 1: i + 3]
        if not phrase_neg and any(x in NEGATORS for x in window):
            sign = -sign
            w *= 0.8
        score += sign * w * mult
    return score


def aspects_in(cl: str) -> list[str]:
    found = []
    for aid, (_l, words, _f, _u) in ASPECTS.items():
        if any(has(cl, w) for w in words):
            found.append(aid)
    if "delivery" in found and "wait" in found:          # "delivery late" is one delivery complaint
        found.remove("wait")
    if "food_safety" in found and "taste" in found:
        found.remove("taste")
    if "wait" in found and "staff" in found and "slow service" in cl:
        found.remove("staff")
    return found


def stars_of(v: Any) -> float | None:
    """'5', '4.0', '★★★★☆', 'FIVE', '4/5', '4 out of 5' -> 1..5."""
    if v is None:
        return None
    if isinstance(v, (int, float)):
        f = float(v)
        return f if 0 < f <= 5 else None
    s = str(v).strip()
    if not s:
        return None
    if "★" in s or "⭐" in s:
        n = s.count("★") + s.count("⭐")
        return float(n) if 0 < n <= 5 else None
    words = {"ONE": 1, "TWO": 2, "THREE": 3, "FOUR": 4, "FIVE": 5}
    if s.upper() in words:
        return float(words[s.upper()])
    m = re.match(r"^\s*(\d+(?:\.\d+)?)\s*(?:/\s*5|out of 5|stars?|\*)?\s*$", s, re.I)
    if m:
        f = float(m.group(1))
        return f if 0 < f <= 5 else None
    return None


def score_of(v: Any) -> int | None:
    try:
        f = float(str(v).strip().split("/")[0])
    except (TypeError, ValueError):
        return None
    return int(round(f)) if 0 <= f <= 10 else None


def analyse(text: str, stars: float | None = None, score: int | None = None) -> dict[str, Any]:
    """One piece of feedback -> {lang, sentiment -1..1, label pos|neg|neu|mixed, aspects [{aspect, pol}], urgent, words}."""
    t = norm(text)
    tl = t.lower()
    cls = clauses(t) or ([tl] if tl else [])
    asp: dict[str, float] = {}
    total, pos_c, neg_c = 0.0, 0, 0
    for cl in cls:
        sc = clause_score(cl)
        total += sc
        if sc > 0.3:
            pos_c += 1
        elif sc < -0.3:
            neg_c += 1
        for a in aspects_in(cl):
            asp[a] = asp.get(a, 0.0) + sc
    text_s = math.tanh(total / 2.0) if cls else 0.0
    base = None
    if stars is not None:
        base = (float(stars) - 3) / 2
    elif score is not None:
        base = max(-1.0, min(1.0, (int(score) - 7) / 3))
    if base is not None and cls:
        s = 0.6 * base + 0.4 * text_s
    elif base is not None:
        s = base
    else:
        s = text_s
    urgent = any(has(tl, w) for w in URGENT_WORDS)
    out_asp = []
    for a, v in asp.items():
        pol = "pos" if v > 0.3 else ("neg" if v < -0.3 else ("neg" if ASPECTS[a][3] else ("neg" if s < -0.25 else ("pos" if s > 0.25 else "neu"))))
        if ASPECTS[a][3]:
            pol = "neg"
        out_asp.append({"aspect": a, "pol": pol})
    if urgent and not any(x["aspect"] in ("food_safety", "safety", "fraud") for x in out_asp):
        for a in ("food_safety", "safety", "fraud"):
            if any(has(tl, w) for w in ASPECTS[a][1]):
                out_asp.append({"aspect": a, "pol": "neg"})
    if urgent:
        s = min(s, -0.5)
    label = "neu"
    if pos_c and neg_c:
        label = "mixed"
    elif s > 0.25:
        label = "pos"
    elif s < -0.25:
        label = "neg"
    if label == "mixed" and (stars is not None and stars <= 2 or urgent):
        label = "neg"
    return {"lang": lang_of(t) if t else "", "sentiment": round(s, 3), "label": label, "aspects": out_asp, "urgent": urgent,
            "words": content_words(t)}


def content_words(text: str) -> list[str]:
    out = []
    for w in re.findall(r"[a-z][a-z']{2,}|[ऀ-ॿ]{2,}", (text or "").lower()):
        if w in STOP or w in POS or w in NEG or w in NEGATORS or w in INTENS:
            continue
        out.append(w)
    return out


def theme_key(aspect: str, pol: str) -> str:
    return f"{aspect}:{'pos' if pol == 'pos' else 'neg'}"


def theme_label(key: str, custom: str = "") -> str:
    if custom:
        return custom
    a, _, p = key.partition(":")
    if a.startswith("other_"):
        base = "Doosri baat: " + a[6:].replace("_", " ")
    else:
        base = ASPECTS.get(a, (a.replace("_", " ").title(),))[0]
    return base + (" - tareef" if p == "pos" else " - shikayat")


def fixability(aspect: str) -> float:
    return ASPECTS.get(aspect, ("", (), 0.6, False))[2]


def is_urgent_aspect(aspect: str) -> bool:
    return ASPECTS.get(aspect, ("", (), 0.6, False))[3]


# ---------------------------------------------------------------- scores
def nps(scores: list[int]) -> dict[str, Any]:
    n = len(scores)
    if not n:
        return {"n": 0, "nps": None}
    p = sum(1 for x in scores if x >= 9) / n
    d = sum(1 for x in scores if x <= 6) / n
    val = round((p - d) * 100)
    moe = 1.96 * math.sqrt(max(0.0, (p + d - (p - d) ** 2)) / n) * 100
    return {"n": n, "nps": val, "promoters_pct": round(p * 100), "passives_pct": round((1 - p - d) * 100), "detractors_pct": round(d * 100),
            "margin": round(moe), "low_n": n < 30,
            "say": f"NPS {val:+d} ({n} jawab" + (f", +/-{round(moe)} ka farak ho sakta hai" if n < 100 else "") + ")"}


def csat(stars: list[float]) -> dict[str, Any]:
    n = len(stars)
    if not n:
        return {"n": 0, "csat": None}
    good = sum(1 for x in stars if x >= 4) / n
    return {"n": n, "csat": round(good * 100), "avg": round(sum(stars) / n, 2), "low_n": n < 30,
            "dist": {str(k): sum(1 for x in stars if round(x) == k) for k in range(1, 6)},
            "say": f"CSAT {round(good * 100)}% (4-5 taare), ausat {sum(stars) / n:.1f}* ({n})"}


def trend(cur: int, prev: int) -> dict[str, Any]:
    if prev == 0:
        return {"pct": None, "new": cur >= 2, "say": "naya" if cur >= 2 else ""}
    pct = round((cur - prev) / prev * 100)
    return {"pct": pct, "new": False, "say": (f"+{pct}%" if pct > 0 else f"{pct}%")}


def poisson_sf(k: int, lam: float) -> float:
    """P(X >= k) for X ~ Poisson(lam)."""
    if k <= 0:
        return 1.0
    lam = max(lam, 1e-9)
    term, cdf = math.exp(-lam), 0.0
    for i in range(k):
        if i:
            term *= lam / i
        cdf += term
    return max(0.0, 1.0 - cdf)


def spike(last7: int, prev28: int) -> dict[str, Any] | None:
    lam = prev28 / 4.0
    if last7 < 3 or last7 < 2 * lam + 1:
        return None
    p = poisson_sf(last7, lam + 0.5)
    if p >= 0.02:
        return None
    return {"last7": last7, "usual": round(lam, 1), "p": round(p, 4)}


def severity(stars: float | None, score: int | None, sentiment: float) -> float:
    if stars is not None:
        return {1: 1.0, 2: 0.8, 3: 0.4}.get(int(round(stars)), 0.15)
    if score is not None:
        return 1.0 if score <= 3 else (0.7 if score <= 6 else 0.2)
    return 0.7 if sentiment < -0.5 else (0.5 if sentiment < -0.25 else 0.3)


def source_weight(source: str) -> float:
    return 1.3 if source in SOURCE_PUBLIC else 1.0


def recency(days_old: float, half_life: float = 30.0) -> float:
    return 0.5 ** (max(0.0, days_old) / half_life)


def fix_score(impact: float, aspect: str, trend_pct: float | None, new: bool, urgent: bool) -> float:
    g = 1.0 + min(1.0, max(0.0, (trend_pct or 0) / 100.0)) + (0.5 if new else 0)
    return round(impact * (0.4 + fixability(aspect)) * g * (4.0 if urgent else 1.0), 3)


# ---------------------------------------------------------------- suspicious signals (never remove; she may report via the platform)
def norm_text(text: str) -> str:
    return re.sub(r"[^a-z0-9ऀ-ॿ ]+", "", (text or "").lower()).strip()


def shingles(text: str) -> set[str]:
    w = norm_text(text).split()
    return {" ".join(w[i:i + 3]) for i in range(max(0, len(w) - 2))} or set(w)


def jaccard(a: set[str], b: set[str]) -> float:
    return len(a & b) / len(a | b) if a and b else 0.0


def incentive_words(text: str) -> bool:
    tl = (text or "").lower()
    return any(p in tl for p in INCENTIVE)


def generic(text: str) -> bool:
    t = norm_text(text)
    return not t or t in GENERIC or len(t.split()) <= 2


# ---------------------------------------------------------------- reply checks
REPLY_MAX = 4096
_PHONE = re.compile(r"(?<!\d)(?:\+?91[\s-]?)?[6-9]\d{4}[\s-]?\d{5}(?!\d)")
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
_BRIBE = re.compile(r"(discount|cashback|gift|free|offer|coupon|refund).{0,40}(review|rating|star|hata|remove|delete|change|badal)"
                    r"|(review|rating|star).{0,40}(hata|remove|delete|change|badal).{0,40}(discount|cashback|gift|free|offer|coupon)",
                    re.I)


def digits(s: str) -> str:
    return re.sub(r"\D", "", s or "")[-10:]


def reply_problems(text: str, business_phone: str = "", business_email: str = "") -> list[str]:
    """Things that must not go into a public reply."""
    out = []
    t = text or ""
    if not t.strip():
        out.append("Jawab khaali hai.")
    if len(t.encode("utf-8")) > REPLY_MAX:
        out.append("Jawab bahut lamba (Google 4096 bytes tak leta hai).")
    for m in _PHONE.finditer(t):
        if digits(m.group(0)) != digits(business_phone):
            out.append("Jawab mein kisi ka phone number hai (sirf business ka number chalega).")
            break
    for m in _EMAIL.finditer(t):
        if m.group(0).lower() != (business_email or "").lower():
            out.append("Jawab mein kisi ka email hai.")
            break
    try:
        from .. import pii
        kinds = pii.find(t)
        if kinds:
            out.append("Jawab mein niji jaankari: " + pii.describe(kinds) + ".")
    except Exception:
        pass
    if _BRIBE.search(t):
        out.append("Review badalne / hatane ke badle kuch dena mana hai (Google policy, IS 19000).")
    if re.search(r"\[[^\]]{1,40}\]", t):
        out.append("Jawab mein [khaali jagah] bachi hai.")
    return out


def mask(text: str) -> str:
    """Quotes shown in reports: phone numbers and emails hidden."""
    t = _PHONE.sub("[phone]", text or "")
    return _EMAIL.sub("[email]", t)
