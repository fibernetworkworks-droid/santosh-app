"""Rules as DATA (plan law 2): every rate, date and limit lives in rules/*.json with WHERE it came from (`source`), HOW sure we are
(`basis`), WHEN it was last read (`checked_on`) and when it must be read again (`review_by`). This year alone changed the GST slabs,
three GSTR-3B locks, the whole Income-tax Act and the EPF ceiling - a number in code would already be wrong.

`basis`: primary (read on a government page) | primary-listing (the government page lists it, the text was not read) |
provider-spec (the GSP's own API spec) | secondary-confirmed (2+ independent secondary sources agree) | unverified (memory / one
weak source). An unverified row is SHOWN as a warning, never used to compute a tax or a penalty.
"""
from __future__ import annotations

import json
from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import Any

DIR = Path(__file__).resolve().parent / "rules"
NAMES = ("gst_rates", "due_dates", "limits", "forms_map")
BASES = ("primary", "primary-listing", "provider-spec", "secondary-confirmed", "unverified")
NEEDED = ("id", "basis", "source", "checked_on", "review_by")


class RulesError(Exception):
    pass


@lru_cache(maxsize=None)
def load(name: str) -> dict[str, Any]:
    if name not in NAMES:
        raise RulesError(f"No rule file '{name}'.")
    data = json.loads((DIR / f"{name}.json").read_text(encoding="utf-8"))
    for r in data.get("rows") or []:
        missing = [k for k in NEEDED if not r.get(k)]
        if missing:
            raise RulesError(f"{name}: row {r.get('id', '?')} has no {', '.join(missing)}")
        if r["basis"] not in BASES:
            raise RulesError(f"{name}: row {r['id']} basis '{r['basis']}' is not one of {', '.join(BASES)}")
    return data


def rows(name: str) -> list[dict[str, Any]]:
    return list(load(name).get("rows") or [])


def row(name: str, rid: str) -> dict[str, Any]:
    for r in rows(name):
        if r["id"] == rid:
            return r
    raise RulesError(f"{name}: no row '{rid}'")


def usable(r: dict[str, Any]) -> bool:
    """May this row feed a computed number? Only when it is not merely remembered."""
    return r.get("basis") != "unverified"


def stale(r: dict[str, Any], today: date | None = None) -> bool:
    try:
        return date.fromisoformat(str(r.get("review_by"))) < (today or date.today())
    except ValueError:
        return True


def freshness(today: date | None = None) -> dict[str, Any]:
    """How sure is the rule book right now - what the desk shows under 'Rules'."""
    out: dict[str, Any] = {"files": [], "by_basis": {b: 0 for b in BASES}, "stale": [], "unverified": []}
    for n in NAMES:
        d = load(n)
        rs = d.get("rows") or []
        out["files"].append({"name": n, "about": d.get("about", ""), "rows": len(rs)})
        for r in rs:
            out["by_basis"][r["basis"]] += 1
            item = {"file": n, "id": r["id"], "what": r.get("what") or r.get("note") or r["id"], "basis": r["basis"],
                    "source": r["source"], "checked_on": r["checked_on"], "review_by": r["review_by"]}
            if stale(r, today):
                out["stale"].append(item)
            if r["basis"] == "unverified":
                out["unverified"].append(item)
    out["total"] = sum(out["by_basis"].values())
    return out


def slabs_on(day: str) -> list[float]:
    """The GST slabs in force on a document date (YYYY-MM-DD)."""
    for r in rows("gst_rates"):
        if not r.get("slabs"):
            continue
        if r["from"] <= day and (not r.get("to") or day <= r["to"]):
            return list(r["slabs"])
    return []


def _shift(year: int, month: int, by: int) -> tuple[int, int]:
    m = month - 1 + by
    return year + m // 12, m % 12 + 1


def dues_for(period: str, scheme: str = "monthly", employer: bool = False, tds: bool = False,
             today: date | None = None) -> list[dict[str, Any]]:
    """The dated work for one tax period (YYYY-MM): each item with its date, days left and how sure the date is."""
    y, m = int(period[:4]), int(period[5:7])
    today = today or date.today()
    out = []
    for r in rows("due_dates"):
        ap = r.get("applies", "all")
        if ap == "monthly" and scheme != "monthly":
            continue
        if ap == "qrmp" and scheme != "qrmp":
            continue
        if ap == "employer" and not employer:
            continue
        if ap == "tds" and not tds:
            continue
        yy, mm = _shift(y, m, int(r.get("month_offset", 1)))
        day = int(r["day"])
        if r["id"] == "tds_deposit" and m == 3:
            yy, mm, day = y, 4, 30
        d = date(yy, mm, day)
        out.append({"id": r["id"], "what": r["what"], "date": d.isoformat(), "days_left": (d - today).days,
                    "if_missed": r.get("if_missed", ""), "basis": r["basis"], "source": r["source"], "checked_on": r["checked_on"]})
    return sorted(out, key=lambda x: x["date"])
