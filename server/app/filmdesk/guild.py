"""Film Desk ROYALTY / GUILD terms: royalty and residual statements from HER contract terms, all in CODE.

Register: docs/research/film_industry/00_INDEX.md  (#21/#23 royalty and residual maths, guild agreements). Pure functions: no
database, no network, no model.

THE RULE: this module ships NO guild rate table. Guild and society agreements (writers, directors, musicians, performers, music
rights societies) are negotiated, change, and differ by territory and by contract, so any table baked in here would be stale or wrong
the day it was read. Every term is typed in by her from the actual contract, and each one MUST carry a `source` (the clause or the
document it came from). A term with no source is refused. The output is a calculation for the producer and her accountant to check
against the contract. It is not a statement of what anyone is owed, it files nothing, and it pays nothing.
"""
from __future__ import annotations

import re
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

BASES = ("flat_inr", "percent_of_gross", "percent_of_net", "per_unit")
ROLES = ("writer", "director", "actor", "composer", "lyricist", "singer", "musician", "editor", "cinematographer", "other")
TERM_MAX, RECEIPT_MAX = 120, 400
MEDIA = ("theatrical", "festival", "svod", "avod", "tvod", "tv", "home_video", "airline", "educational", "music", "other")
_Q = Decimal("0.01")


def _clean(v: Any, n: int) -> str:
    return re.sub(r"\s+", " ", str(v or "")).strip()[:n]


def _day(v: Any) -> str:
    try:
        return date.fromisoformat(str(v or "").strip()[:10]).isoformat()
    except ValueError:
        return ""


def _dec(v: Any) -> Decimal | None:
    try:
        d = Decimal(str(v).replace(",", "").strip())
    except Exception:
        return None
    return d if d >= 0 else None


def _media(v: Any) -> list[str]:
    items = v if isinstance(v, list) else re.split(r"[,/ ]+", str(v or ""))
    out = []
    for x in items:
        k = str(x).strip().lower()
        if k == "all":
            return ["all"]
        if k in MEDIA and k not in out:
            out.append(k)
    return out or ["all"]


def norm_term(raw: dict[str, Any], seq: int) -> dict[str, Any]:
    party = _clean(raw.get("party"), 80)
    if not party:
        raise ValueError("Say who gets it (party).")
    basis = _clean(raw.get("basis"), 20).lower()
    if basis not in BASES:
        raise ValueError(f"basis must be one of: {', '.join(BASES)}")
    rate = _dec(raw.get("rate"))
    if rate is None:
        raise ValueError("Give the rate (a number): from the contract.")
    if basis.startswith("percent") and rate > 100:
        raise ValueError("percent cannot be more than 100.")
    source = _clean(raw.get("source"), 160)
    if not source:
        raise ValueError("Write the source (the contract clause / document): no rate is counted without a source.")
    role = _clean(raw.get("role"), 20).lower()
    return {"id": f"gt{seq}", "party": party, "role": role if role in ROLES else "other", "guild": _clean(raw.get("guild"), 60),
            "basis": basis, "rate": float(rate), "threshold_inr": float(_dec(raw.get("threshold_inr")) or 0),
            "cap_inr": (float(_dec(raw.get("cap_inr"))) if _dec(raw.get("cap_inr")) is not None else None),
            "floor_inr": float(_dec(raw.get("floor_inr")) or 0), "applies_to": _media(raw.get("applies_to")),
            "start": _day(raw.get("start")), "end": _day(raw.get("end")), "source": source, "notes": _clean(raw.get("notes"), 300)}


def norm_receipt(raw: dict[str, Any], seq: int) -> dict[str, Any]:
    medium = _clean(raw.get("medium"), 20).lower()
    if medium not in MEDIA:
        raise ValueError(f"medium must be one of: {', '.join(MEDIA)}")
    amt = _dec(raw.get("amount_inr"))
    if amt is None:
        raise ValueError("Give amount_inr (total income, rupees).")
    net = _dec(raw.get("net_inr"))
    units = _dec(raw.get("units"))
    return {"id": f"rc{seq}", "medium": medium, "amount_inr": float(amt), "net_inr": float(net) if net is not None else None,
            "units": float(units) if units is not None else None, "period": _day(raw.get("period")),
            "payer": _clean(raw.get("payer"), 80), "notes": _clean(raw.get("notes"), 200)}


def _r(x: Decimal) -> float:
    return float(x.quantize(_Q, rounding=ROUND_HALF_UP))


def statement(terms: list[dict[str, Any]], receipts: list[dict[str, Any]]) -> dict[str, Any]:
    """For each term: the receipts it applies to (by medium and date window) -> base -> amount (threshold, floor, cap) in exact paise.
    Totals per party add up the lines exactly. A line that cannot be computed says why instead of showing 0."""
    lines, parties, notes = [], {}, []
    for t in terms:
        mine = [r for r in receipts if ("all" in t["applies_to"] or r["medium"] in t["applies_to"])
                and (not t["start"] or not r["period"] or r["period"] >= t["start"])
                and (not t["end"] or not r["period"] or r["period"] <= t["end"])]
        base_g = sum((Decimal(str(r["amount_inr"])) for r in mine), Decimal("0"))
        why, amt = "", Decimal("0")
        if not mine:
            why = "no income falls under this rate (by medium / date)."
        elif t["basis"] == "flat_inr":
            amt = Decimal(str(t["rate"]))
        elif t["basis"] == "percent_of_gross":
            over = max(base_g - Decimal(str(t["threshold_inr"])), Decimal("0"))
            amt = over * Decimal(str(t["rate"])) / Decimal(100)
        elif t["basis"] == "percent_of_net":
            if any(r["net_inr"] is None for r in mine):
                why = "net_inr is missing in some income lines: a rate on net cannot be counted then."
            else:
                base_n = sum((Decimal(str(r["net_inr"])) for r in mine), Decimal("0"))
                over = max(base_n - Decimal(str(t["threshold_inr"])), Decimal("0"))
                amt = over * Decimal(str(t["rate"])) / Decimal(100)
        elif t["basis"] == "per_unit":
            if any(r["units"] is None for r in mine):
                why = "units (count) is missing in some income lines."
            else:
                units = sum((Decimal(str(r["units"])) for r in mine), Decimal("0"))
                amt = units * Decimal(str(t["rate"]))
        capped = False
        if not why:
            if amt < Decimal(str(t["floor_inr"])):
                amt = Decimal(str(t["floor_inr"]))
            if t["cap_inr"] is not None and amt > Decimal(str(t["cap_inr"])):
                amt, capped = Decimal(str(t["cap_inr"])), True
        amt = amt.quantize(_Q, rounding=ROUND_HALF_UP)
        lines.append({"term": t["id"], "party": t["party"], "role": t["role"], "guild": t["guild"], "basis": t["basis"], "rate": t["rate"],
                      "receipts_n": len(mine), "gross_base_inr": _r(base_g), "amount_inr": 0.0 if why else _r(amt), "capped": capped,
                      "problem": why, "source": t["source"]})
        if why:
            notes.append(f"{t['party']} ({t['id']}): {why}")
        else:
            parties[t["party"]] = parties.get(t["party"], Decimal("0")) + amt
    total = sum(parties.values(), Decimal("0"))
    return {"lines": lines, "by_party": [{"party": k, "amount_inr": _r(v)} for k, v in sorted(parties.items(), key=lambda x: -x[1])],
            "total_inr": _r(total), "gross_receipts_inr": _r(sum((Decimal(str(r["amount_inr"])) for r in receipts), Decimal("0"))),
            "problems": notes,
            "note": "This is a calculation from the contract rates you wrote, not any guild's or society's rate list. Check it with the contract and your accountant; "
                    "Hoola sends, files or pays nothing. You can put this total into the waterfall as a deduction."}
