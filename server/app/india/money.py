"""v0.59 Indian money in words and numbers: ₹12,34,567.50, "baarah lakh chautees hazaar...", GSTIN check.

Hindi / Hinglish words are written here (num2words has no Hindi); English uses the Indian lakh / crore system.
"""
from __future__ import annotations

import re

_HI = ("एक दो तीन चार पाँच छह सात आठ नौ दस ग्यारह बारह तेरह चौदह पंद्रह सोलह सत्रह अठारह उन्नीस बीस इक्कीस बाईस तेईस "
       "चौबीस पच्चीस छब्बीस सत्ताईस अट्ठाईस उनतीस तीस इकतीस बत्तीस तैंतीस चौंतीस पैंतीस छत्तीस सैंतीस अड़तीस उनतालीस "
       "चालीस इकतालीस बयालीस तैंतालीस चवालीस पैंतालीस छियालीस सैंतालीस अड़तालीस उनचास पचास इक्यावन बावन तिरपन चौवन "
       "पचपन छप्पन सत्तावन अट्ठावन उनसठ साठ इकसठ बासठ तिरसठ चौंसठ पैंसठ छियासठ सड़सठ अड़सठ उनहत्तर सत्तर इकहत्तर "
       "बहत्तर तिहत्तर चौहत्तर पचहत्तर छिहत्तर सतहत्तर अठहत्तर उन्यासी अस्सी इक्यासी बयासी तिरासी चौरासी पचासी छियासी "
       "सत्तासी अट्ठासी नवासी नब्बे इक्यानबे बानबे तिरानबे चौरानबे पंचानबे छियानबे सत्तानबे अट्ठानबे निन्यानबे").split()
_HING = ("ek do teen chaar paanch chhah saat aath nau das gyaarah baarah terah chaudah pandrah solah satrah athaarah "
         "unnees bees ikkees baaees teyees chaubees pachchees chhabbees sattaaees atthaaees untees tees iktees battees "
         "taintees chauntees paintees chhattees saintees adtees untaalees chaalees iktaalees bayaalees taintaalees "
         "chavaalees paintaalees chhiyaalees saintaalees adtaalees unchaas pachaas ikyaavan baavan tirpan chauvan pachpan "
         "chhappan sattaavan atthaavan unsath saath iksath baasath tirsath chaunsath painsath chhiyaasath sadsath adsath "
         "unhattar sattar ikhattar bahattar tihattar chauhattar pachhattar chhihattar sathattar athhattar unyaasi assi "
         "ikyaasi bayaasi tiraasi chauraasi pachaasi chhiyaasi sattaasi atthaasi navaasi nabbe ikyaanve baanve tiraanve "
         "chauraanve pachaanve chhiyaanve sattaanve atthaanve ninyaanve").split()
assert len(_HI) == 99 and len(_HING) == 99
_SCALE = {"hi": ("सौ", "हज़ार", "लाख", "करोड़"), "hinglish": ("sau", "hazaar", "lakh", "crore")}
_EN1 = ("zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen "
        "seventeen eighteen nineteen").split()
_EN10 = "_ _ twenty thirty forty fifty sixty seventy eighty ninety".split()


def _en99(n: int) -> str:
    if n < 20:
        return _EN1[n]
    t, u = divmod(n, 10)
    return _EN10[t] + ("-" + _EN1[u] if u else "")


def _groups(n: int) -> list[tuple[int, int]]:
    """n -> [(value, scale index)] with 3=crore 2=lakh 1=hazaar 0=sau, plus (rest, -1). Above a crore people say
    '150 crore', so crore takes everything bigger."""
    out = []
    for idx, size in ((3, 10 ** 7), (2, 10 ** 5), (1, 1000), (0, 100)):
        q, n = divmod(n, size)
        if q:
            out.append((q, idx))
    if n:
        out.append((n, -1))
    return out


def words(n: int, lang: str = "hinglish") -> str:
    """Whole number in words: hinglish (default) | hi (Devanagari) | en (Indian English)."""
    n = int(n)
    if n < 0:
        return ("minus " if lang != "hi" else "ऋण ") + words(-n, lang)
    if n == 0:
        return {"hi": "शून्य", "en": "zero"}.get(lang, "shoonya")
    if lang == "en":
        parts = []
        for q, idx in _groups(n):
            name = ("hundred", "thousand", "lakh", "crore")[idx] if idx >= 0 else ""
            qs = words(q, "en") if q >= 100 else _en99(q)
            parts.append(qs + (" " + name if name else ""))
        return " ".join(parts)
    table = _HI if lang == "hi" else _HING
    scale = _SCALE["hi" if lang == "hi" else "hinglish"]
    parts = []
    for q, idx in _groups(n):
        qs = words(q, lang) if q >= 100 else table[q - 1]
        parts.append(qs + (" " + scale[idx] if idx >= 0 else ""))
    return " ".join(parts)


def rupees_words(amount: float, lang: str = "hinglish") -> str:
    """₹ amount in words with paise: 'do lakh pachchees hazaar rupaye aur pachaas paise'."""
    paise_total = round(float(amount) * 100)
    r, p = divmod(abs(paise_total), 100)
    sign = "minus " if paise_total < 0 else ""
    if lang == "en":
        s = f"Rupees {words(r, 'en')}" + (f" and {words(p, 'en')} paise" if p else "") + " only"
        return sign + s[0].upper() + s[1:]
    if lang == "hi":
        return sign + f"{words(r, 'hi')} रुपये" + (f" और {words(p, 'hi')} पैसे" if p else "")
    return sign + f"{words(r)} rupaye" + (f" aur {words(p)} paise" if p else "")


def inr(amount: float, paise: bool | None = None) -> str:
    """₹12,34,567.50 (lakh grouping). paise=None shows paise only when there are some."""
    neg = amount < 0
    a = abs(round(float(amount), 2))
    whole = int(a)
    frac = round((a - whole) * 100)
    s = str(whole)
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        head = re.sub(r"(\d)(?=(\d\d)+$)", r"\1,", head)
        s = head + "," + tail
    show = frac != 0 if paise is None else paise
    return ("-" if neg else "") + "₹" + s + (f".{frac:02d}" if show else "")


def short(amount: float) -> str:
    """₹2.25 lakh / ₹1.2 crore — how people say big amounts."""
    a = float(amount)
    for size, name in ((10 ** 7, "crore"), (10 ** 5, "lakh")):
        if abs(a) >= size:
            v = a / size
            return f"₹{v:.2f}".rstrip("0").rstrip(".") + f" {name}"
    return inr(a)


_GST_CHARS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
_GST_RE = re.compile(r"^[0-3][0-9][A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$")
STATE_CODES = {"01": "Jammu & Kashmir", "02": "Himachal Pradesh", "03": "Punjab", "04": "Chandigarh", "05": "Uttarakhand",
               "06": "Haryana", "07": "Delhi", "08": "Rajasthan", "09": "Uttar Pradesh", "10": "Bihar", "11": "Sikkim",
               "12": "Arunachal Pradesh", "13": "Nagaland", "14": "Manipur", "15": "Mizoram", "16": "Tripura",
               "17": "Meghalaya", "18": "Assam", "19": "West Bengal", "20": "Jharkhand", "21": "Odisha", "22": "Chhattisgarh",
               "23": "Madhya Pradesh", "24": "Gujarat", "26": "Dadra & Nagar Haveli and Daman & Diu", "27": "Maharashtra",
               "29": "Karnataka", "30": "Goa", "31": "Lakshadweep", "32": "Kerala", "33": "Tamil Nadu", "34": "Puducherry",
               "35": "Andaman & Nicobar", "36": "Telangana", "37": "Andhra Pradesh", "38": "Ladakh", "97": "Other Territory"}


def gstin_ok(g: str) -> bool:
    """Shape + state code + GSTN check digit (mod 36). A business number, public on every invoice."""
    g = (g or "").strip().upper()
    if not _GST_RE.match(g) or g[:2] not in STATE_CODES:
        return False
    total = 0
    for i, ch in enumerate(g[:14]):
        prod = _GST_CHARS.index(ch) * (1 if i % 2 == 0 else 2)
        total += prod // 36 + prod % 36
    return _GST_CHARS[(36 - total % 36) % 36] == g[14]


def gstin_info(g: str) -> dict:
    g = (g or "").strip().upper()
    ok = gstin_ok(g)
    out = {"gstin": g, "valid": ok}
    if ok:
        out |= {"state": STATE_CODES.get(g[:2]), "entity_no": g[12], "pan_based": True,
                "kind": {"P": "individual / proprietor", "C": "company", "F": "firm / LLP", "H": "HUF", "A": "AOP",
                         "T": "trust", "B": "BOI", "L": "local authority", "J": "artificial juridical person",
                         "G": "government"}.get(g[5], "other")}
    return out
