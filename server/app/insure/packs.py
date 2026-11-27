"""Insurance country packs (INSURANCE AGENT DESK, owner: "now insurance agent assistant - make it very powerful and advanced like
the other employees"; every AI employee is GLOBAL).

A pack holds the servicing rules an agent works to in one country: free-look / cooling-off days, premium grace days, how long a lapsed
policy can be revived, the claim timelines, the regulator, the ombudsman and the complaint ladder, and whether individual premiums carry
a tax. India's numbers were read from the IRDAI 2024 master circulars (22 Oct 2026, see rules.py) and are CHECKED. Every other country
is a starting list from memory: each value is shown as 'check this' and NEVER used in a calculation until she confirms it (one tap,
"Use this value") or types her own from the policy / regulator. Her value always wins.
"""
from __future__ import annotations

import json
import re
from typing import Any

RULE_KEYS = ("free_look_days", "grace_monthly_days", "grace_other_days", "revival_years", "revival_years_ulip", "death_claim_days",
             "death_investigated_days", "reimbursement_days", "cashless_hours")
RULE_SAY = {"free_look_days": "Free-look / cooling-off (days)", "grace_monthly_days": "Grace period, monthly premiums (days)",
            "grace_other_days": "Grace period, other premiums (days)", "revival_years": "Revival of a lapsed traditional policy (years)",
            "revival_years_ulip": "Revival of a lapsed unit-linked policy (years)", "death_claim_days": "Death claim settled within (days)",
            "death_investigated_days": "Death claim with an investigation (days)", "reimbursement_days": "Health reimbursement settled within (days)",
            "cashless_hours": "Cashless approval within (hours)"}

PACKS: dict[str, dict[str, Any]] = {
    "IN": {"name": "India", "currency": "INR", "checked": True, "source": "IRDAI master circulars 2024 (read 22 Oct 2026)",
           "regulator": "IRDAI", "ombudsman": "Insurance Ombudsman",
           "ladder": ["The insurer's grievance officer", "Bima Bharosa (IRDAI's complaint portal)", "The Insurance Ombudsman"],
           "rules": {"free_look_days": 30, "grace_monthly_days": 15, "grace_other_days": 30, "revival_years": 5, "revival_years_ulip": 3,
                     "death_claim_days": 15, "death_investigated_days": 45, "reimbursement_days": 15, "cashless_hours": 1},
           "tax": "No GST on individual life and health premiums since 22 Sep 2025 (group policies still taxed). The health premium "
                  "deduction (Sec 126, old 80D) applies only in the old tax regime.", "premium_tax_exempt": True, "lakh": True},
    "GB": {"name": "United Kingdom", "currency": "GBP", "checked": False, "regulator": "FCA (conduct) and PRA",
           "ombudsman": "Financial Ombudsman Service",
           "ladder": ["The insurer's complaints team (8 weeks to answer)", "The Financial Ombudsman Service"],
           "rules": {"free_look_days": 30, "grace_monthly_days": 30, "grace_other_days": 30, "death_claim_days": None},
           "tax": "Insurance Premium Tax applies to general insurance; long-term life insurance is exempt."},
    "US": {"name": "United States", "currency": "USD", "checked": False, "regulator": "Your state insurance department (NAIC model laws)",
           "ombudsman": "State insurance department consumer services",
           "ladder": ["The insurer's complaints / appeals process", "Your state insurance department"],
           "rules": {"free_look_days": 10, "grace_monthly_days": 31, "grace_other_days": 31, "revival_years": 3},
           "tax": "Premium taxes are paid by insurers and differ by state; rules differ by state - check the state that issued the policy."},
    "AE": {"name": "United Arab Emirates", "currency": "AED", "checked": False, "regulator": "Central Bank of the UAE",
           "ombudsman": "Sanadak (UAE financial ombudsman)",
           "ladder": ["The insurer's complaints unit", "Sanadak"],
           "rules": {"free_look_days": 30, "grace_monthly_days": 30, "grace_other_days": 30},
           "tax": "VAT may apply to some general insurance; life insurance is generally exempt - check."},
    "SG": {"name": "Singapore", "currency": "SGD", "checked": False, "regulator": "MAS", "ombudsman": "FIDReC",
           "ladder": ["The insurer's complaints team", "FIDReC"],
           "rules": {"free_look_days": 14, "grace_monthly_days": 30, "grace_other_days": 30},
           "tax": "GST applies to general insurance; life policies are exempt."},
    "AU": {"name": "Australia", "currency": "AUD", "checked": False, "regulator": "ASIC and APRA", "ombudsman": "AFCA",
           "ladder": ["The insurer's internal dispute resolution (30 days)", "AFCA"],
           "rules": {"free_look_days": 14, "grace_monthly_days": 30, "grace_other_days": 30},
           "tax": "GST and stamp duty apply to general insurance; life insurance is input-taxed."},
    "CA": {"name": "Canada", "currency": "CAD", "checked": False, "regulator": "Your provincial insurance regulator",
           "ombudsman": "OLHI (life and health) / GIO (general)",
           "ladder": ["The insurer's ombudsman", "OLHI or GIO", "Your provincial regulator"],
           "rules": {"free_look_days": 10, "grace_monthly_days": 30, "grace_other_days": 30},
           "tax": "Provincial premium taxes apply; rules differ by province."},
    "ZA": {"name": "South Africa", "currency": "ZAR", "checked": False, "regulator": "FSCA and the Prudential Authority",
           "ombudsman": "National Financial Ombud Scheme",
           "ladder": ["The insurer's complaints team", "The National Financial Ombud Scheme"],
           "rules": {"free_look_days": 30, "grace_monthly_days": 30, "grace_other_days": 30},
           "tax": "Check how VAT applies to the cover."},
    "KE": {"name": "Kenya", "currency": "KES", "checked": False, "regulator": "Insurance Regulatory Authority",
           "ombudsman": "IRA consumer complaints", "ladder": ["The insurer's complaints desk", "The IRA"],
           "rules": {"free_look_days": 30, "grace_monthly_days": 30, "grace_other_days": 30}, "tax": "Check the levies on premiums."},
}
GENERIC = {"name": "Your country", "currency": "", "checked": False, "regulator": "Your insurance regulator", "ombudsman": "",
           "ladder": ["The insurer's complaints team", "Your insurance regulator or ombudsman"], "rules": {},
           "tax": "Check how premiums are taxed in your country."}


def pack(country: str) -> dict[str, Any]:
    return PACKS.get((country or "IN").upper(), GENERIC)


def is_india(country: str) -> bool:
    return (country or "IN").upper() == "IN"


def effective(country: str, mine: dict | str | None) -> dict[str, dict[str, Any]]:
    """{key: {value, source: yours | checked | check this | not set, suggested}}. Only 'yours' and 'checked' are usable."""
    if isinstance(mine, str):
        try:
            mine = json.loads(mine or "{}")
        except ValueError:
            mine = {}
    mine = mine if isinstance(mine, dict) else {}
    p = pack(country)
    out = {}
    for k in RULE_KEYS:
        sug = p["rules"].get(k)
        if mine.get(k) not in (None, ""):
            out[k] = {"value": mine[k], "source": "yours", "suggested": sug, "label": RULE_SAY[k]}
        elif sug is not None and p.get("checked"):
            out[k] = {"value": sug, "source": "checked", "suggested": sug, "label": RULE_SAY[k]}
        elif sug is not None:
            out[k] = {"value": None, "source": "check this", "suggested": sug, "label": RULE_SAY[k]}
        else:
            out[k] = {"value": None, "source": "not set", "suggested": None, "label": RULE_SAY[k]}
    return out


def usable(country: str, mine, key: str) -> float | None:
    v = effective(country, mine)[key]["value"]
    return None if v is None else float(v)


def clean_rules(a: dict[str, Any]) -> dict[str, Any]:
    out = {}
    for k in RULE_KEYS:
        if k not in a:
            continue
        v = a[k]
        if v in (None, ""):
            out[k] = None
            continue
        try:
            f = float(v)
        except (TypeError, ValueError):
            raise ValueError(f"{RULE_SAY[k]}: a number, please")
        if f < 0 or f > 3650:
            raise ValueError(f"{RULE_SAY[k]}: between 0 and 3650")
        out[k] = int(f) if f == int(f) else f
    return out


# ---------------------------------------------------------------- money words for a non-India desk
_LAKH = re.compile(r"₹\s?(-?[\d,]*\.?\d+)\s?(lakh|cr)\b")
_RS = re.compile(r"₹\s?(-?[\d,]*\.?\d+)")


def money(v: float, cur: str) -> str:
    v = float(v or 0)
    return f"{cur} {v:,.0f}" if cur else f"{v:,.0f}"


def localise(obj: Any, cur: str) -> Any:
    """The engine writes Indian money words (₹1,23,456 / ₹5 lakh). On another country's desk they become '<CUR> 123,456'."""
    if isinstance(obj, str):
        if "₹" not in obj:
            return obj
        s = _LAKH.sub(lambda m: money(float(m.group(1).replace(",", "")) * (1e5 if m.group(2) == "lakh" else 1e7), cur), obj)
        s = _RS.sub(lambda m: money(float(m.group(1).replace(",", "")), cur), s)
        return s.replace(" / lakh", " per 100,000")
    if isinstance(obj, dict):
        return {k: localise(v, cur) for k, v in obj.items()}
    if isinstance(obj, list):
        return [localise(v, cur) for v in obj]
    return obj
