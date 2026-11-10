"""v0.49 Indian personal / financial details that Hoola must never keep in memory or pass on (Presidio-style
recognizers, built in: Microsoft Presidio's own Indian recognizers need a 500 MB spaCy model we don't want on the VPS).

find(text) -> list of kinds found: otp_pin, password, card, aadhaar, pan, bank_account, cvv
Aadhaar numbers are confirmed with the Verhoeff checksum UIDAI uses (fewer false alarms on random 12-digit numbers);
cards with Luhn. The Hoola Network keeps its own (stricter, no checksum) rule in net.policy.secret_found.
"""
from __future__ import annotations

import re

from .net import policy

_D = ((0, 1, 2, 3, 4, 5, 6, 7, 8, 9), (1, 2, 3, 4, 0, 6, 7, 8, 9, 5), (2, 3, 4, 0, 1, 7, 8, 9, 5, 6),
      (3, 4, 0, 1, 2, 8, 9, 5, 6, 7), (4, 0, 1, 2, 3, 9, 5, 6, 7, 8), (5, 9, 8, 7, 6, 0, 4, 3, 2, 1),
      (6, 5, 9, 8, 7, 1, 0, 4, 3, 2), (7, 6, 5, 9, 8, 2, 1, 0, 4, 3), (8, 7, 6, 5, 9, 3, 2, 1, 0, 4),
      (9, 8, 7, 6, 5, 4, 3, 2, 1, 0))
_P = ((0, 1, 2, 3, 4, 5, 6, 7, 8, 9), (1, 5, 7, 6, 2, 8, 3, 0, 9, 4), (5, 8, 0, 3, 7, 9, 6, 1, 4, 2),
      (8, 9, 1, 6, 0, 4, 3, 5, 2, 7), (9, 4, 5, 3, 1, 2, 6, 8, 7, 0), (4, 2, 8, 6, 5, 7, 3, 9, 0, 1),
      (2, 7, 9, 3, 8, 0, 6, 4, 1, 5), (7, 0, 4, 6, 9, 1, 3, 2, 5, 8))

AADHAAR_ANY = re.compile(r"(?<!\d)[2-9]\d{3}[ -]?\d{4}[ -]?\d{4}(?!\d)")
PAN = re.compile(r"\b[A-Z]{3}[ABCFGHLJPT][A-Z]\d{4}[A-Z]\b")
BANK = re.compile(r"\b(a/?c|acc(ount)?|khata|bank)\W{0,3}(no|number|num|sankhya)?\W{0,6}(is|hai|:|=|-)?\W{0,4}\d{9,18}\b", re.I)
CVV = re.compile(r"\bcvv2?\b\W{0,10}\d{3,4}\b", re.I)


def verhoeff_ok(num: str) -> bool:
    c = 0
    for i, ch in enumerate(reversed(num)):
        c = _D[c][_P[i % 8][int(ch)]]
    return c == 0


def find(text: str) -> list[str]:
    t = text or ""
    out: list[str] = []
    s = policy.secret_found(t)
    if s:
        out.append({"OTP / PIN": "otp_pin", "password": "password", "card number": "card",
                    "Aadhaar number": "aadhaar"}.get(s, s))
    if "aadhaar" not in out:
        for m in AADHAAR_ANY.finditer(t):
            if verhoeff_ok(re.sub(r"\D", "", m.group(0))):
                out.append("aadhaar")
                break
    if PAN.search(t):
        out.append("pan")
    if BANK.search(t):
        out.append("bank_account")
    if CVV.search(t) and "otp_pin" not in out:
        out.append("cvv")
    return out


_CARDLIKE = re.compile(r"(?<!\d)(?:\d[ -]?){12,18}\d(?!\d)")


def _luhn(num: str) -> bool:
    tot, alt = 0, False
    for ch in reversed(num):
        d = int(ch)
        if alt:
            d = d * 2 - 9 if d > 4 else d * 2
        tot += d
        alt = not alt
    return tot % 10 == 0


def mask_sensitive(text: str, mark: str = "######") -> str:
    """v0.661 the numbers that must never sit in memory - a card (Luhn), an Aadhaar (Verhoeff), a bank account next to
    its word, a PAN, a CVV - masked; every OTHER number stays. Before, memory masked ANY 9+ digit run, so her
    customers' phone numbers and order numbers became ###### and Hoola could not call or message the right person."""
    t = text or ""
    t = CVV.sub(lambda m: re.sub(r"\d{3,4}\b", "***", m.group(0)), t)
    t = BANK.sub(lambda m: re.sub(r"\d{9,18}", mark, m.group(0)), t)
    t = PAN.sub(mark, t)

    def _card(m):
        d = re.sub(r"\D", "", m.group(0))
        return mark if 13 <= len(d) <= 19 and _luhn(d) else m.group(0)
    t = _CARDLIKE.sub(_card, t)

    def _aad(m):
        return mark if verhoeff_ok(re.sub(r"\D", "", m.group(0))) else m.group(0)
    return AADHAAR_ANY.sub(_aad, t)


SAY = {"otp_pin": "OTP / PIN", "password": "password", "card": "card number", "aadhaar": "Aadhaar number",
       "pan": "PAN number", "bank_account": "bank account number", "cvv": "CVV"}


def describe(kinds: list[str]) -> str:
    return ", ".join(SAY.get(k, k) for k in kinds)
