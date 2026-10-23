"""Gyaan text helpers: Indian numbers, identifiers, masking before indexing, and a light Devanagari -> Roman transliteration
so a Hinglish question ("bijli bill kitna tha") finds a Devanagari document ("बिजली बिल") and the other way round.

Everything here is plain Python (no model, no network) so it runs at ingest time on the VPS CPU in microseconds."""
from __future__ import annotations

import re
import unicodedata

# ---------------------------------------------------------------- digits and amounts
def ascii_digits(text: str) -> str:
    """Devanagari / Gujarati / Bengali / Gurmukhi / Tamil ... digits -> 0-9 (models and FTS both read ASCII digits best)."""
    if not text:
        return ""
    out = []
    for ch in text:
        if ch.isdigit() and not ("0" <= ch <= "9"):
            try:
                out.append(str(unicodedata.digit(ch)))
                continue
            except (TypeError, ValueError):
                pass
        out.append(ch)
    return "".join(out)


_GROUPED = re.compile(r"(?<![\d,])\d{1,3}(?:,\d{2})*,\d{3}(?:\.\d+)?(?![\d,])")       # 9,22,436.38 or 1,250
_LAKH = re.compile(r"(?<![\w.])(\d+(?:\.\d+)?)\s*(lakh|lakhs|lac|lacs|l|लाख|crore|crores|cr|करोड़|करोड|k|हज़ार|हजार|hazar|hazaar|thousand)\b",
                   re.I)
_MULT = {"lakh": 100000, "lakhs": 100000, "lac": 100000, "lacs": 100000, "l": 100000, "लाख": 100000,
         "crore": 10000000, "crores": 10000000, "cr": 10000000, "करोड़": 10000000, "करोड": 10000000,
         "k": 1000, "thousand": 1000, "hazar": 1000, "hazaar": 1000, "हज़ार": 1000, "हजार": 1000}


def _plain(n: float) -> str:
    return str(int(n)) if float(n).is_integer() else f"{n:.2f}".rstrip("0").rstrip(".")


def numbers(text: str) -> list[str]:
    """Canonical numbers in a text: "₹9,22,436" -> 922436, "1.5 lakh" -> 150000, "१२५०" -> 1250. Used both as extra
    index tokens and to check that an answer's numbers really are in its cited source."""
    t = ascii_digits(text or "")
    out: list[str] = []
    for m in _GROUPED.finditer(t):
        out.append(_plain(float(m.group(0).replace(",", ""))))
    for m in _LAKH.finditer(t):
        try:
            out.append(_plain(float(m.group(1)) * _MULT[m.group(2).lower()]))
        except (KeyError, ValueError):
            pass
    for m in re.finditer(r"(?<![\d.,])\d+(?:\.\d+)?(?![\d,])", t):
        out.append(_plain(float(m.group(0))) if len(m.group(0)) < 16 else m.group(0))
    seen: set[str] = set()
    return [x for x in out if not (x in seen or seen.add(x))]


# ---------------------------------------------------------------- identifiers (exact lookup, never by embedding)
GSTIN = re.compile(r"\b\d{2}[A-Z]{5}\d{4}[A-Z][1-9A-Z]Z[0-9A-Z]\b")
PHONE = re.compile(r"(?<![\d])(?:\+?91[\s-]?|0)?([6-9]\d{4})[\s-]?(\d{5})(?![\d])")
LONGNUM = re.compile(r"(?<![\d])\d{8,18}(?![\d])")
CODE = re.compile(r"\b(?=[A-Z0-9/-]{5,24}\b)(?=[A-Z0-9/-]*\d)(?=[A-Z0-9/-]*[A-Z])[A-Z][A-Z0-9]*(?:[/-][A-Z0-9]+)+\b|\b[A-Z]{2,6}\d{3,14}\b")
IFSC = re.compile(r"\b[A-Z]{4}0[A-Z0-9]{6}\b")


def compact(v: str) -> str:
    return re.sub(r"[^0-9A-Za-z]", "", v or "").upper()


def ids(text: str) -> list[tuple[str, str]]:
    """(kind, compact value) for every identifier: GSTIN, phone, IFSC, invoice / order / ticket codes, long numbers
    (consumer, account, policy numbers). Aadhaar / PAN / card numbers are already masked before this runs."""
    t = ascii_digits(text or "")
    up = t.upper()
    out: list[tuple[str, str]] = []
    for m in GSTIN.finditer(up):
        out.append(("gstin", m.group(0)))
    for m in IFSC.finditer(up):
        out.append(("ifsc", m.group(0)))
    for m in PHONE.finditer(t):
        out.append(("phone", m.group(1) + m.group(2)))
    for m in CODE.finditer(up):
        v = compact(m.group(0))
        if len(v) >= 5 and not GSTIN.fullmatch(v) and not IFSC.fullmatch(v):
            out.append(("code", v))
    for m in LONGNUM.finditer(t):
        v = m.group(0)
        if not any(v.endswith(p) and k == "phone" for k, p in out):
            out.append(("number", v))
    seen: set[tuple[str, str]] = set()
    return [x for x in out if not (x in seen or seen.add(x))]


# ---------------------------------------------------------------- masking before anything is stored
def _luhn(num: str) -> bool:
    s, alt = 0, False
    for ch in reversed(num):
        d = int(ch)
        if alt:
            d *= 2
            if d > 9:
                d -= 9
        s += d
        alt = not alt
    return s % 10 == 0


_SECRET = re.compile(r"\b(otp|o\.t\.p|one[- ]time password|pin|m-?pin|upi pin|cvv|password|passcode|पासवर्ड|ओटीपी)\b"
                     r"(\W{0,12}(is|hai|:|=|-)?\W{0,6})([A-Za-z0-9@#$%^&*!]{3,12})", re.I)


def mask(text: str) -> tuple[str, list[str]]:
    """Aadhaar (Verhoeff), PAN, card numbers (Luhn), bank account numbers with context and OTP / PIN / password values are
    masked BEFORE indexing: the knowledge base never holds them, so no answer, cache or log can leak them."""
    from .. import pii
    t = text or ""
    found: list[str] = []

    def _aad(m: re.Match) -> str:
        d = re.sub(r"\D", "", m.group(0))
        if pii.verhoeff_ok(d):
            found.append("aadhaar")
            return "XXXX XXXX " + d[-4:]
        return m.group(0)
    t = pii.AADHAAR_ANY.sub(_aad, t)

    def _pan(m: re.Match) -> str:
        found.append("pan")
        return "XXXXX" + m.group(0)[5:9] + "X"
    t = pii.PAN.sub(_pan, t)

    def _card(m: re.Match) -> str:
        d = re.sub(r"\D", "", m.group(0))
        if 13 <= len(d) <= 19 and _luhn(d):
            found.append("card")
            return "XXXX XXXX XXXX " + d[-4:]
        return m.group(0)
    t = re.sub(r"(?<!\d)(?:\d[ -]?){12,18}\d(?!\d)", _card, t)

    def _bank(m: re.Match) -> str:
        found.append("bank_account")
        g = m.group(0)
        digits = re.findall(r"\d{9,18}", g)
        for d in digits:
            g = g.replace(d, "X" * (len(d) - 4) + d[-4:])
        return g
    t = pii.BANK.sub(_bank, t)

    def _sec(m: re.Match) -> str:
        found.append("secret")
        return m.group(1) + m.group(2) + "••••"
    t = _SECRET.sub(_sec, t)
    return t, sorted(set(found))


# ---------------------------------------------------------------- Devanagari -> Roman (for Hinglish search)
_V = {"अ": "a", "आ": "aa", "इ": "i", "ई": "ii", "उ": "u", "ऊ": "uu", "ऋ": "ri", "ए": "e", "ऐ": "ai", "ओ": "o", "औ": "au",
      "ऍ": "e", "ऑ": "o", "ऎ": "e", "ऒ": "o", "ळ": "l"}
_M = {"ा": "aa", "ि": "i", "ी": "ii", "ु": "u", "ू": "uu", "ृ": "ri", "े": "e", "ै": "ai", "ो": "o", "ौ": "au", "ॅ": "e", "ॉ": "o",
      "ॆ": "e", "ॊ": "o"}
_C = {"क": "k", "ख": "kh", "ग": "g", "घ": "gh", "ङ": "n", "च": "ch", "छ": "chh", "ज": "j", "झ": "jh", "ञ": "n", "ट": "t",
      "ठ": "th", "ड": "d", "ढ": "dh", "ण": "n", "त": "t", "थ": "th", "द": "d", "ध": "dh", "न": "n", "प": "p", "फ": "ph",
      "ब": "b", "भ": "bh", "म": "m", "य": "y", "र": "r", "ल": "l", "व": "v", "श": "sh", "ष": "sh", "स": "s", "ह": "h",
      "ळ": "l", "क़": "q", "ख़": "kh", "ग़": "g", "ज़": "z", "ड़": "d", "ढ़": "dh", "फ़": "f", "य़": "y"}
_NUKTA = {"क": "q", "ख": "kh", "ग": "g", "ज": "z", "ड": "r", "ढ": "rh", "फ": "f"}
VIRAMA, NUKTA, ANUSVARA, CHANDRA, VISARGA = "्", "़", "ं", "ँ", "ः"


def _word(w: str) -> str:
    # units: (roman consonant or vowel, has_inherent_a)
    units: list[list] = []
    i = 0
    while i < len(w):
        ch = w[i]
        if ch in _C:
            r = _C[ch]
            if i + 1 < len(w) and w[i + 1] == NUKTA:
                r = _NUKTA.get(ch, r)
                i += 1
            units.append([r, True, "c"])
        elif ch in _V:
            units.append([_V[ch], False, "v"])
        elif ch in _M and units:
            units[-1][0] += _M[ch]
            units[-1][1] = False
            units[-1][2] = "cv"
        elif ch == VIRAMA and units:
            units[-1][1] = False
            units[-1][2] = "half"
        elif ch in (ANUSVARA, CHANDRA) and units:
            if units[-1][1]:
                units[-1][0] += "a"
                units[-1][1] = False
            units[-1][0] += "n"
        elif ch == VISARGA and units:
            units[-1][0] += "h"
        elif ch.isascii():
            units.append([ch, False, "x"])
        i += 1
    # Hindi schwa deletion (simple, good enough for search): drop a word-final inherent 'a', and a medial one between a
    # vowel and a consonant that carries its own vowel (बिजली -> bijli, कमरा -> kamra, but कमल -> kamal)
    n = len(units)
    keep = [u[1] for u in units]
    if n > 1 and keep[-1] and units[-1][2] == "c":
        keep[-1] = False
    for k in range(1, n - 1):
        if not (keep[k] and units[k][2] == "c"):
            continue
        prev_vowel = units[k - 1][2] in ("v", "cv") or keep[k - 1]
        nxt = units[k + 1]
        if prev_vowel and nxt[2] == "cv":
            keep[k] = False
    return "".join(u[0] + ("a" if keep[j] else "") for j, u in enumerate(units))


_DEVA_WORD = re.compile(r"[ऀ-ॿ]+")


def has_devanagari(text: str) -> bool:
    return bool(_DEVA_WORD.search(text or ""))


def translit(text: str) -> str:
    """Devanagari words -> rough Roman (Latin text passes through)."""
    if not has_devanagari(text):
        return text or ""
    return _DEVA_WORD.sub(lambda m: _word(m.group(0)), text)


def phon(text: str) -> str:
    """A spelling-forgiving key for Roman text (kyaa / kya, nahin / nahi, bijlee / bijli): used on BOTH the index and the
    query of the trigram table, so Hinglish spelling variants and transliterated Devanagari meet."""
    t = (translit(text) or "").lower()
    t = ascii_digits(t)
    for a, b in (("aa", "a"), ("ee", "i"), ("ii", "i"), ("oo", "u"), ("uu", "u"), ("ph", "f"), ("sh", "s"), ("chh", "ch"),
                 ("w", "v"), ("z", "j"), ("q", "k"), ("ck", "k"), ("nh", "n"), ("y ", "i ")):
        t = t.replace(a, b)
    t = re.sub(r"(.)\1+", r"\1", t)              # double letters
    return re.sub(r"\s+", " ", t).strip()


STOP = {"kya", "hai", "tha", "thi", "the", "and", "aur", "wala", "wali", "wale", "ka", "ki", "ke", "ko", "se", "me", "mein",
        "par", "pe", "kitna", "kitni", "kitne", "kab", "kaun", "kahan", "kaise", "batao", "bataiye", "bata", "do", "dijiye",
        "mera", "meri", "mere", "humara", "hamara", "is", "us", "yeh", "ye", "woh", "vo", "the", "a", "an", "of", "to", "in",
        "on", "for", "what", "when", "where", "who", "how", "which", "my", "our", "please", "pls", "tell", "me", "about",
        "hain", "ho", "hua", "hui", "kar", "karo", "karna", "le", "lo", "ek", "koi", "sab", "sabhi", "apna", "apni",
        "है", "था", "थी", "क्या", "का", "की", "के", "को", "से", "में", "पर", "और", "मेरा", "मेरी", "कितना", "कब", "कौन", "कहाँ",
        "आहे", "होता", "होती", "काय", "किती", "कधी", "माझा", "माझी", "आणि", "ला", "ची", "चा", "चे", "मध्ये", "ने"}


STOP |= {"kiti", "aahe", "ahe", "kay", "kadhi", "majha", "majhi", "hota", "hoti", "ani", "madhye", "cha", "chi", "che",
         "liye"}
_STOP_KEYS: set[str] = set()


def _stop_keys() -> set[str]:
    if not _STOP_KEYS:
        _STOP_KEYS.update(phon(w) for w in STOP)
    return _STOP_KEYS


def words(text: str) -> list[str]:
    """Content words of a question / sentence (no stop words in any script or spelling, >= 3 letters or a number)."""
    t = ascii_digits(text or "").lower()
    ws = re.findall(r"[\wऀ-ॿ]+", t)
    keys = _stop_keys()
    return [w for w in ws if w not in STOP and phon(w) not in keys and (len(w) >= 3 or w.isdigit())]
