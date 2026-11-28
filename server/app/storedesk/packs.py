"""Country packs for the Material Store: what the papers are called, which documents a receipt must carry for which kind of item,
and the storage rules - each row with its source. A row nobody has checked against the primary text says `check: True` and is shown
as "check this", never applied as a rule. A country with no pack gets the general rows only.

Sources read for these rows (Nov 2026): IS 4082:1996 (Bureau of Indian Standards, scanned copy at law.resource.org); the European
Commission's page on CE marking and the Declaration of Performance (and Conformity) under the Construction Products Regulation;
Iowa DOT Instructional Memorandum 451 (mill test reports and heat numbers for reinforcing steel - one US state's rule, not a national
one). Bar mass tolerances in IS 1786 / BS 4449 / ASTM A615 were NOT read from the standards: they are her number per item."""
from __future__ import annotations

from typing import Any

# what a delivery paper is called (labels only)
DELIVERY = {"IN": "challan", "GB": "delivery note", "IE": "delivery note", "US": "delivery ticket", "CA": "delivery ticket",
            "AE": "delivery note", "SA": "delivery note", "AU": "delivery docket", "NZ": "delivery docket", "SG": "delivery order",
            "MY": "delivery order", "ZA": "delivery note", "KE": "delivery note", "NG": "waybill"}
EU = {"AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR", "DE", "GR", "HU", "IE", "IT", "LV", "LT", "LU", "MT", "NL", "PL", "PT",
      "RO", "SK", "SI", "ES", "SE", "IS", "LI", "NO"}   # EU + EEA

SRC_EC = "European Commission - CE marking and declaration of performance and conformity (Construction Products Regulation)"
SRC_IS4082 = "IS 4082:1996 Stacking and storage of construction materials and components at site - recommendations (BIS)"
SRC_IADOT = "Iowa DOT Instructional Memorandum 451 (reinforcing steel: mill test reports per heat) - a US state rule"

# document rows: id, applies to (item categories / trace kinds), the paper, source, checked against the source?
DOCS: list[dict[str, Any]] = [
    {"id": "gen-delivery", "where": "*", "for": "*", "need": "The supplier's delivery paper with its number", "source": "General practice", "check": False},
    {"id": "gen-heat", "where": "*", "for": "heat", "need": "A mill test certificate for every heat number delivered",
     "source": "General practice for traceable steel; " + SRC_IADOT, "check": False},
    {"id": "eu-ce", "where": "EU", "for": "bulk", "need": "CE marking and the Declaration of Performance (and Conformity) for products a harmonised standard covers",
     "source": SRC_EC, "check": False},
    {"id": "gb-ukca", "where": "GB", "for": "bulk", "need": "UKCA or CE marking and the declaration of performance", "source": "Not read here", "check": True},
    {"id": "us-mtr", "where": "US", "for": "heat", "need": "Mill test report certified by the mill (federal-aid / state DOT work)", "source": SRC_IADOT, "check": True},
    {"id": "in-bis", "where": "IN", "for": "bulk", "need": "BIS mark (ISI) and the manufacturer's test certificate where the product is under compulsory certification",
     "source": "Not read here", "check": True},
]

# storage rows: id, where, what kind of item (by words in its name), the rule, source, checked?
STORAGE: list[dict[str, Any]] = [
    {"id": "gen-fifo", "where": "*", "words": ("cement", "adhesive", "mortar", "grout", "admixture", "paint", "sealant", "plaster"),
     "rule": "Label each stack with the day it came in; issue the oldest first.", "source": "General practice", "check": False},
    {"id": "gen-steel", "where": "*", "words": ("rebar", "steel", "bar", "tmt"),
     "rule": "Keep off the ground on supports, by diameter and by heat number, under cover where the site allows.", "source": "General practice", "check": False},
    {"id": "in-cement", "where": "IN", "words": ("cement",),
     "rule": "Stacks at most 10 bags high, on planks or a raised floor, clear of walls, bag types not mixed, first in first out.",
     "source": SRC_IS4082, "check": False},
]

UNITS = {   # common conversions to a base unit (used to offer a conversion; her item's own `conv` always wins)
    "kg": {"t": 1000, "tonne": 1000, "g": 0.001, "lb": 0.45359237, "short ton": 907.18474},
    "t": {"kg": 0.001, "lb": 0.00045359237},
    "m": {"ft": 0.3048, "mm": 0.001, "cm": 0.01},
    "m3": {"yd3": 0.764554857984, "cft": 0.028316846592, "l": 0.001},
    "m2": {"ft2": 0.09290304, "sqft": 0.09290304},
}


def _applies(row: dict[str, Any], country: str) -> bool:
    w = row["where"]
    return w == "*" or w == country or (w == "EU" and country in EU)


def docs_for(country: str, category: str, trace: str, off: list[str] | None = None) -> list[dict[str, Any]]:
    off = set(off or [])
    out = []
    for r in DOCS:
        if r["id"] in off or not _applies(r, country):
            continue
        if r["for"] in ("*", category, trace):
            out.append(r)
    return out


def storage_for(country: str, name: str, off: list[str] | None = None) -> list[dict[str, Any]]:
    off = set(off or [])
    n = (name or "").lower()
    return [r for r in STORAGE if r["id"] not in off and _applies(r, country) and any(w in n for w in r["words"])]


def pack(country: str) -> dict[str, Any]:
    c = (country or "").upper()
    return {"country": c or "-", "delivery_word": DELIVERY.get(c, "delivery note"),
            "docs": [r for r in DOCS if _applies(r, c)], "storage": [r for r in STORAGE if _applies(r, c)],
            "note": ("Rows marked 'check this' were not read from the primary text; they are shown, never applied as a rule. "
                     "A country with no rows of its own gets the general rows only.")}
