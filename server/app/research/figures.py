"""v0.474 R3 - reading figures, links and the Sources section of a report. Shared by the engine's claim check and the R0 card,
so the card and the live check can never disagree about what counts as a key figure."""
from __future__ import annotations

import re

NUM_TOL = 0.015              # relative tolerance when matching a report figure to a page figure (rounding)
MIN_KEY = 13                 # whole numbers below this are counts and months, not key figures

URL = re.compile(r"https?://[^\s)\]>\"'*]+")
REF = re.compile(r"\[(\d{1,3})\]")
YEAR = re.compile(r"\b(?:19|20)\d{2}\b")
SRC_HEAD = re.compile(r"^\s*(?:#{1,4}\s*)?\**\s*(sources?|references?|bibliography|strot|sandarbh|स्रोत|संदर्भ)\b[^\n]*$",
                      re.I | re.M)
NUM = re.compile(r"(?<![\w.])-?\d[\d,]*(?:\.\d+)?(?:\s*(?:lakh|lac|crore|cr\b|k\b))?", re.I)
UNSURE = ("could not confirm", "couldn't confirm", "not confirmed", "unconfirmed", "unable to confirm",
          "not able to confirm", "could not verify", "could not find", "couldn't find", "not found", "uncertain",
          "limitation", "not final", "disagree", "conflict", "confirm nahi", "pata nahi", "nahi mil", "nahi mila",
          "verify nahi", "pushti nahi", "pakka nahi", "anishchit", "abhi final nahi", "alag alag", "ek jaisa nahi")


def numbers(text: str) -> list[float]:
    """Every number in a text the Indian way: 17,994.52 / Rs 17,994 / 23.18 lakh / 1.5 crore / -12."""
    out = []
    for m in NUM.finditer(str(text or "").replace("₹", " ").replace("−", "-")):
        raw = m.group(0).lower()
        mult = 1.0
        if "lakh" in raw or "lac" in raw:
            mult = 1e5
        elif "crore" in raw or re.search(r"cr\b", raw):
            mult = 1e7
        elif raw.endswith("k"):
            mult = 1e3
        digits = re.sub(r"[^\d.\-]", "", raw.split()[0] if " " in raw else re.sub(r"[a-z]+$", "", raw))
        try:
            out.append(float(digits) * mult)
        except ValueError:
            continue
    return out


def norm_url(u: str) -> str:
    return re.sub(r"^https?://(www\.)?", "", u.rstrip(".,;:)")).split("#")[0].rstrip("/").lower()


def host_of(u: str) -> str:
    return norm_url(u).split("/")[0].split("?")[0]


def split_report(report: str) -> tuple[str, list[str]]:
    """(body, source lines). The Sources section starts at the LAST heading called Sources / References."""
    text = str(report or "")
    heads = list(SRC_HEAD.finditer(text))
    if not heads:
        return text, []
    h = heads[-1]
    body, tail = text[:h.start()], text[h.end():]
    return body, [ln.strip() for ln in tail.splitlines() if ln.strip() and not ln.strip().startswith(("---", "==="))]


def clean_for_numbers(body: str) -> str:
    t = URL.sub(" ", body)
    t = REF.sub(" ", t)
    t = re.sub(r"\b\d{1,2}[-/ ](?:\d{1,2}|[A-Za-z]{3,9})[-/ ,]+(?:19|20)\d{2}\b", " ", t)       # 12 March 2025, 3/4/2025
    t = re.sub(r"\b(?:19|20)\d{2}\s*[-–]\s*(?:\d{2}|(?:19|20)\d{2})\b", " ", t)                   # 2024-25, FY 2023-2024
    t = re.sub(r"(?m)^\s*\d{1,2}[.)]\s", " ", t)                                                  # list numerals
    t = re.sub(r"\b(?:19|20)\d{2}\b", " ", t)                                                     # a bare year
    return re.sub(r"\bQ[1-4]\b|\bFY\s?\d{2,4}\b", " ", t)


def key_figures(body: str, asked: str = "") -> list[float]:
    """The numbers that make a claim: not a year, a date, a [n], a list numeral, a small count, or a number the ask
    itself already contained."""
    asked_set = {round(v, 4) for v in numbers(asked)}
    out, seen = [], set()
    for v in numbers(clean_for_numbers(body)):
        a = abs(v)
        if round(v, 4) in asked_set or round(v, 4) in seen:
            continue
        if a < MIN_KEY and float(a).is_integer():
            continue
        seen.add(round(v, 4))
        out.append(v)
    return out


def near(v: float, pool: list[float]) -> bool:
    tol = max(abs(v) * NUM_TOL, 1e-9)
    return any(abs(p - v) <= tol for p in pool)
