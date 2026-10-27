"""v0.83 An OTP as people really say it: "4 5 6 7 8 9", "चार पांच छह सात आठ नौ", "four five double six",
"४५६७८९", "456-789". Used for the chat / call answer to a waiting OTP box (never anywhere else).

find_otp(text, expected) -> the digits or None. Only a run of 4-8 digits counts; Hinglish words that are also ordinary
words ("do" = give, "ek" = a) count only inside a run and are dropped from its ends when the run is too long."""
from __future__ import annotations

import re
import unicodedata

WORDS = {
    # English
    "zero": "0", "oh": "0", "o": "0", "one": "1", "two": "2", "three": "3", "four": "4", "five": "5", "six": "6",
    "seven": "7", "eight": "8", "nine": "9",
    # Hindi / Hinglish in Latin letters
    "shunya": "0", "shoonya": "0", "sunya": "0", "sifar": "0", "ek": "1", "do": "2", "teen": "3", "tin": "3",
    "char": "4", "chaar": "4", "paanch": "5", "panch": "5", "paach": "5", "chhe": "6", "chhah": "6", "chhah.": "6",
    "che": "6", "chah": "6", "chhey": "6", "saat": "7", "sat": "7", "aath": "8", "aat": "8", "nau": "9", "naw": "9",
    # Devanagari (Hindi / Marathi) + English said in Devanagari
    "शून्य": "0", "शुन्य": "0", "सुन्न": "0", "ज़ीरो": "0", "जीरो": "0", "एक": "1", "दो": "2", "दोन": "2", "तीन": "3",
    "चार": "4", "पांच": "5", "पाँच": "5", "पाच": "5", "छह": "6", "छः": "6", "छे": "6", "छै": "6", "सहा": "6", "सात": "7",
    "आठ": "8", "नौ": "9", "नऊ": "9", "वन": "1", "टू": "2", "थ्री": "3", "फोर": "4", "फ़ोर": "4", "फाइव": "5",
    "फ़ाइव": "5", "सिक्स": "6", "सेवन": "7", "एट": "8", "एइट": "8", "नाइन": "9", "ज़ेरो": "0",
}
AMBIGUOUS = {"do", "ek", "oh", "o", "tin", "sat", "che", "aat", "एक", "दो"}
REPEAT = {"double": 2, "dabal": 2, "डबल": 2, "triple": 3, "tripal": 3, "ट्रिपल": 3}
_SPLIT = re.compile(r"[\s,.;:!?()\[\]'\"/|-]+")


def _digits(tok: str) -> str:
    """'४५६' / '456' / '٤٥٦' -> '456'; '' when the token is not all digits."""
    if not tok:
        return ""
    out = []
    for ch in tok:
        try:
            out.append(str(unicodedata.decimal(ch)))
        except (TypeError, ValueError):
            return ""
    return "".join(out)


def _tokens(text: str) -> list[tuple[str, bool] | None]:
    """Each piece -> (digits, ambiguous) or None (a non-digit word breaks a run)."""
    out: list[tuple[str, bool] | None] = []
    rep = 1
    for raw in _SPLIT.split(str(text or "").lower()):
        if not raw:
            continue
        if raw in REPEAT:
            rep = REPEAT[raw]
            continue
        d = _digits(raw)
        amb = False
        if not d and raw in WORDS:
            d, amb = WORDS[raw], raw in AMBIGUOUS
        if not d:
            # "OTP:456789" / "otp456789" -> the digit tail
            m = re.search(r"(\d{4,8})$", raw)
            if m and not out:
                out.append((m.group(1), False))
                rep = 1
                continue
            out.append(None)
            rep = 1
            continue
        if rep > 1 and len(d) == 1:
            d = d * rep
        rep = 1
        out.append((d, amb))
    return out


def _runs(toks):
    run: list[tuple[str, bool]] = []
    for t in toks + [None]:
        if t is None:
            if run:
                yield run
            run = []
        else:
            run.append(t)


def _trim(run: list[tuple[str, bool]], want: int) -> str:
    run = list(run)
    while run and len("".join(d for d, _ in run)) > want:
        if run[-1][1]:
            run.pop()
        elif run[0][1]:
            run.pop(0)
        else:
            break
    return "".join(d for d, _ in run)


def find_otp(text: str, expected: int = 0) -> str | None:
    """The OTP in what she said / typed, or None. expected = digits the page's box takes (0 = unknown)."""
    want = expected if 4 <= (expected or 0) <= 8 else 0
    best = None
    for run in _runs(_tokens(text)):
        val = _trim(run, want or 6) if len("".join(d for d, _ in run)) > (want or 8) else "".join(d for d, _ in run)
        if not 4 <= len(val) <= 8:
            # an ambiguous word in front/behind ("ek OTP 456789 hai") may have made it too long; else not an OTP
            continue
        if want and len(val) == want:
            return val
        if best is None or len(val) > len(best):
            best = val
    return best


def mask(text: str, otp: str) -> str:
    """Hide every way this OTP appears in a line (numerals with gaps, or as spoken words)."""
    if not otp or not text:
        return text
    out = re.sub(r"\d(?:[\s,.-]*\d){3,}", lambda m: "•" * len(otp) if re.sub(r"\D", "", m.group()) == otp else m.group(), text)
    if find_otp(out) == otp:              # said as words: hide the whole line, it was only the OTP
        return "OTP " + "•" * len(otp)
    return out
