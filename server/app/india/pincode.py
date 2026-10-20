"""v0.59 Is this a real Indian PIN code? (captn3m0/india-pincode-regex, MIT: one regex built from India Post's list.)"""
from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

ZONES = {"1": "Delhi, Haryana, Punjab, HP, J&K, Chandigarh", "2": "UP, Uttarakhand", "3": "Rajasthan, Gujarat, Daman & Diu",
         "4": "Maharashtra, Goa, MP, Chhattisgarh", "5": "Telangana, AP, Karnataka", "6": "Tamil Nadu, Kerala, Puducherry, Lakshadweep",
         "7": "West Bengal, Odisha, North East, A&N", "8": "Bihar, Jharkhand", "9": "Army Post Office (APO / FPO)"}


@lru_cache(maxsize=1)
def _re() -> re.Pattern:
    return re.compile("^(?:" + (Path(__file__).parent / "pincode_regex.txt").read_text().strip() + ")$")


def valid(pin: str) -> bool:
    p = re.sub(r"\s", "", str(pin or ""))
    return bool(re.fullmatch(r"[1-9]\d{5}", p)) and bool(_re().match(p))


def info(pin: str) -> dict:
    p = re.sub(r"\s", "", str(pin or ""))
    ok = valid(p)
    return {"pin": p, "valid": ok, **({"zone": ZONES.get(p[0], "")} if ok else
                                      {"say": "Yeh PIN code India Post ki list mein nahi hai."})}


def find_in(text: str) -> list[str]:
    """Real PIN codes inside an address ('Akot 444 101' -> ['444101'])."""
    out = []
    for m in re.finditer(r"(?<!\d)([1-9]\d{2})\s?(\d{3})(?!\d)", text or ""):
        p = m.group(1) + m.group(2)
        if valid(p) and p not in out:
            out.append(p)
    return out
