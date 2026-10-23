"""Kruti Dev 010 (legacy Hindi / Marathi typing font) -> Unicode Devanagari.

Many Indian offices, courts and typing shops still keep text in Kruti Dev: the letters are plain ASCII that only look
Hindi in that font ("Hkkjr" = भारत). This turns such text into real Unicode so it can be searched, translated, fixed,
and printed in any font. Longest-match over the Kruti Dev key table, then the two reorderings every converter needs:
'f' (ि is typed BEFORE its consonant) and 'Z' (reph र् is typed AFTER its syllable). Best effort: names and rare
conjuncts should be checked by eye.
"""
from __future__ import annotations

import re

_MAP = {
    # independent vowels
    "v‚": "ऑ", "vks": "ओ", "vkS": "औ", "vk": "आ", "v": "अ", "b±": "ईं", "Ã": "ई", "bZ": "ई", "b": "इ", "m": "उ",
    "Å": "ऊ", ",s": "ऐ", ",": "ए", "_": "ऋ",
    # conjuncts / special shapes
    "Ùk": "त्त", "Ù": "त्त्", "Dr": "क्त", "–": "दृ", "—": "कृ", "é": "न्न", "™": "न्न्", "à": "ह्न", "á": "ह्य",
    "â": "हृ", "ã": "ह्म", "ºz": "ह्र", "º": "ह्", "í": "द्द", "{k": "क्ष", "{": "क्ष्", "=": "त्र",
    "«": "त्र्", "Nî": "छ्य", "Vî": "ट्य", "Bî": "ठ्य", "Mî": "ड्य", "<î": "ढ्य", "|": "द्य", "K": "ज्ञ", "}": "द्व",
    "J": "श्र", "Vª": "ट्र", "Mª": "ड्र", "<ª": "ढ्र", "Nª": "छ्र", "Ø": "क्र", "Ý": "फ्र", "æ": "द्र", "ç": "प्र",
    "Á": "प्र", "xz": "ग्र", "#": "रु", ":": "रू", "ô": "क्क", "ê": "ट्ट", "ë": "ट्ठ", "ì": "ड्ड", "ï": "ड्ढ", ")": "द्ध",
    # nukta letters
    "d+": "क़", "[+k": "ख़", "[+": "ख़्", "x+": "ग़", "t+": "ज़", "T+": "ज़्", "M+": "ड़", "<+": "ढ़", "Q+": "फ़",
    "¶+": "फ़्", ";+": "य़", "j+": "ऱ", "u+": "ऩ",
    # consonants (with their half forms + 'k' = full)
    "d": "क", "Dk": "क", "D": "क्", "[k": "ख", "[": "ख्", "x": "ग", "Xk": "ग", "X": "ग्", "Ä": "घ", "?k": "घ", "?": "घ्",
    "³": "ङ", "p": "च", "Pk": "च", "P": "च्", "N": "छ", "t": "ज", "Tk": "ज", "T": "ज्", ">": "झ", "÷": "झ्", "¥": "ञ",
    "V": "ट", "B": "ठ", "M": "ड", "<": "ढ", ".k": "ण", ".": "ण्", "r": "त", "Rk": "त", "R": "त्", "Fk": "थ", "F": "थ्",
    "n": "द", "/k": "ध", "/": "ध्", "Ë": "ध्", "è": "ध", "u": "न", "Uk": "न", "U": "न्", "i": "प", "Ik": "प", "I": "प्",
    "Q": "फ", "¶": "फ्", "c": "ब", "Ck": "ब", "C": "ब्", "Hk": "भ", "H": "भ्", "e": "म", "Ek": "म", "E": "म्", ";": "य",
    "¸": "य्", "j": "र", "y": "ल", "Yk": "ल", "Y": "ल्", "G": "ळ", "o": "व", "Ok": "व", "O": "व्", "'k": "श", "'": "श्",
    "\"k": "ष", "\"": "ष्", "l": "स", "Lk": "स", "L": "स्", "g": "ह",
    # vowel signs and marks
    "‚": "ॉ", "ks": "ो", "kS": "ौ", "k": "ा", "h": "ी", "È": "ीं", "q": "ु", "w": "ू", "`": "ृ", "s": "े", "S": "ै",
    "a": "ं", "¡": "ँ", "%": "ः", "W": "ॅ", "z": "्र", "~": "्", "+": "़", "•": "ऽ", "·": "ऽ",
    # digits and punctuation
    "å": "०", "ƒ": "१", "„": "२", "…": "३", "†": "४", "‡": "५", "ˆ": "६", "‰": "७", "Š": "८", "‹": "९",
    "AA": "॥", "A": "।", "]": ",", "-": ".", "&": "-", "¼": "(", "½": ")", "@": "/", "\\": "?", "¾": "=", "ñ": "॰",
    "^": "‘", "*": "’", "Þ": "“", "ß": "”",
}
_KEYS = sorted(_MAP, key=len, reverse=True)
_MAXLEN = max(len(k) for k in _KEYS)
_MATRA = set("ािीुूृेैोौंँःॅॉ़")
_CONS = re.compile(r"[\u0915-\u0939\u0958-\u095F]")
# words that are English / numbers inside a Kruti Dev line stay as they are only when the whole token is clearly not KD
_KD_HINT = re.compile(r"(?:k|h|s|S|ks|kS|q|w|a|Z)")


def looks_krutidev(text: str) -> bool:
    """Heuristic: mostly ASCII letters forming KD patterns, no Devanagari, few real English words."""
    t = text or ""
    if re.search(r"[ऀ-ॿ]", t) or len(t.strip()) < 6:
        return False
    words = re.findall(r"[A-Za-z;'\"\[\]{}/<>.,=]+", t)
    if not words:
        return False
    common = {"the", "and", "is", "to", "of", "in", "for", "on", "with", "a", "this", "that", "dear", "sir", "madam", "date"}
    eng = sum(1 for w in words if w.lower() in common)
    # v0.134: Roman Hinglish ("dukan subah 10 se raat 9 tak khuli rehti hai") is NOT Kruti Dev - its everyday words veto it
    hinglish = {"hai", "hain", "tha", "thi", "ka", "ki", "ke", "ko", "se", "me", "mein", "tak", "aur", "nahi", "nahin", "kya",
                "ye", "yeh", "woh", "vo", "par", "pe", "bhi", "hi", "ho", "kar", "karo", "raha", "rahi", "rehti", "rehta",
                "subah", "raat", "din", "aaj", "kal", "band", "khuli", "wala", "wali", "liye", "kitna", "kab", "kaise", "ek"}
    hing = sum(1 for w in words if w.lower() in hinglish)
    if hing >= max(2, len(words) // 10):
        return False
    kd = sum(1 for w in words if re.search(r"(?:[a-zA-Z](?:k|h|s|ks|q|w)\b|k[a-z]|gS|esa|ugh|dk|ds)", w))
    return kd >= max(2, len(words) // 3) and eng <= len(words) // 5


def to_unicode(text: str) -> str:
    out: list[str] = []
    i, n = 0, len(text)
    while i < n:
        ch = text[i]
        if ch in "fZ\n\r\t ":
            out.append(ch)
            i += 1
            continue
        for L in range(min(_MAXLEN, n - i), 0, -1):
            piece = text[i:i + L]
            if piece in _MAP:
                out.append(_MAP[piece])
                i += L
                break
        else:
            out.append(ch)
            i += 1
    s = "".join(out)
    # ि typed before its consonant (or conjunct): move it after the whole cluster
    while "f" in s:
        k = s.index("f")
        j = k + 1
        if j >= len(s) or not _CONS.match(s[j]):
            s = s[:k] + "ि" + s[k + 1:]           # nothing to attach to: keep the sign where it was
            continue
        j += 1
        while j < len(s) and s[j] == "़":
            j += 1
        while j + 1 < len(s) and s[j] == "्" and _CONS.match(s[j + 1]):
            j += 2
        s = s[:k] + s[k + 1:j] + "ि" + s[j:]
    # reph typed after its syllable: put र् before the syllable's first consonant
    while "Z" in s:
        k = s.index("Z")
        j = k - 1
        while j >= 0 and s[j] in _MATRA:
            j -= 1
        while j - 2 >= 0 and s[j - 1] == "्" and _CONS.match(s[j - 2]):
            j -= 2
        if j < 0:
            s = s[:k] + s[k + 1:]
            continue
        s = s[:j] + "र्" + s[j:k] + s[k + 1:]
    return s


# ---------------------------------------------------------------- Unicode -> Kruti Dev 010 (for forms that still ask for it)
def _reverse() -> dict[str, str]:
    rev: dict[str, str] = {}
    for k, v in _MAP.items():
        if v in ("॥",) or k in ("bZ", "AA"):
            continue
        if v not in rev or len(k) < len(rev[v]):
            rev[v] = k
    rev["ई"] = "bZ"
    rev["॥"] = "AA"
    rev["ध"] = "/k"          # the keys typists use most (the others render the same in the font)
    rev["प्र"] = "iz"
    rev.pop("ीं", None)
    return rev


_REV = _reverse()
_RKEYS = sorted(_REV, key=len, reverse=True)
_RMAX = max(len(k) for k in _RKEYS)


def _cluster_end(s: str, j: int) -> int:
    """From a consonant at j, the end of its conjunct cluster (C(़)(्C(़))*)."""
    j += 1
    while j < len(s) and s[j] == "़":
        j += 1
    while j + 1 < len(s) and s[j] == "्" and _CONS.match(s[j + 1]):
        j += 2
        while j < len(s) and s[j] == "़":
            j += 1
    return j


def from_unicode(text: str) -> str:
    import unicodedata
    s = unicodedata.normalize("NFC", text or "")
    out: list[str] = []
    i, n = 0, len(s)
    while i < n:
        # reph: र् before a consonant cluster -> the cluster (+ its signs) then Z
        if s.startswith("र्", i) and i + 2 < n and _CONS.match(s[i + 2]):
            j = _cluster_end(s, i + 2)
            k = j
            while k < n and s[k] in _MATRA:
                k += 1
            out.append(from_unicode(s[i + 2:k]) + "Z")
            i = k
            continue
        # ि after a cluster -> f before it
        if _CONS.match(s[i]):
            j = _cluster_end(s, i)
            if j < n and s[j] == "ि":
                out.append("f" + _plain(s[i:j]))
                i = j + 1
                continue
        piece = _plain_step(s, i)
        out.append(piece[0])
        i = piece[1]
    return "".join(out)


def _plain_step(s: str, i: int) -> tuple[str, int]:
    for L in range(min(_RMAX, len(s) - i), 0, -1):
        if s[i:i + L] in _REV:
            return _REV[s[i:i + L]], i + L
    return s[i], i + 1


def _plain(s: str) -> str:
    out, i = [], 0
    while i < len(s):
        p, i = _plain_step(s, i)
        out.append(p)
    return "".join(out)
