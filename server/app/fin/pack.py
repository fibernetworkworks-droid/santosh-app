"""Country packs (plan section 4.3 and decision D3). Every country rule is DATA in packs/<CC>.json; every leaf is

    {"value": ..., "status": "verify" | "source_read" | "checked", "source": "https://...", "checked_on": "YYYY-MM-DD",
     "review_by": "YYYY-MM-DD", "checked_by": "name (checked only)", "quote": "the official sentence (source_read)"}

verify       from research or memory - NEVER used in a calculation or a deadline; Hoola says "check this for <country>"
source_read  Hoola read the official page (an allowed host of that pack) and quoted it - explanations, guides, reminders, estimates
checked      a qualified person confirmed it - required to file, pay, compute a tax due, a payroll deduction, a legal deadline, a refund right

A value past review_by drops one level (checked -> source_read, source_read -> verify) until it is read again.
A country with no file gets the FLOOR pack: explanations, budgets, documents and maths on her own numbers; no country rule.

    python -m app.fin.pack check      schema + freshness of every pack (exit 1 on a schema error)
"""
from __future__ import annotations

import json
import os
import re
import sys
from contextlib import contextmanager
from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import Any

DIR = Path(__file__).resolve().parent / "packs"
STATUSES = ("verify", "source_read", "checked")
LEVEL = {"verify": 0, "source_read": 1, "checked": 2}
TOP = ("cc", "name", "currency", "minor_unit", "languages", "version", "official_hosts", "sections")
SECTIONS = ("rails", "regulators", "ombudsman", "fraud_report", "scam_refund", "deposit_insurance", "credit_bureaus",
            "open_banking", "tax", "payroll", "consumer_credit", "free_advice", "data_law", "entity_types", "id_checks", "ai_rules",
            "card_dispute", "identity_theft")
# ISO 4217 minor units that are not 2 (from the ISO list; checked by the money tests)
MINOR = {"JPY": 0, "KRW": 0, "VND": 0, "CLP": 0, "ISK": 0, "UGX": 0, "XAF": 0, "XOF": 0, "PYG": 0, "RWF": 0, "KMF": 0, "GNF": 0,
         "DJF": 0, "VUV": 0, "XPF": 0, "BIF": 0, "KWD": 3, "BHD": 3, "OMR": 3, "JOD": 3, "TND": 3, "IQD": 3, "LYD": 3}


_AS_CHECKED = [False]   # the F1 card's "as if a person had checked it" mode - never set by a live path


def review_dir() -> Path:
    """Where Hoola's reads of official pages and a person's checks are kept (fin/review.py writes it). One file per country."""
    return Path(os.environ.get("HOOLA_FIN_REVIEW_DIR") or (Path("data") / "fin" / "pack_review"))


@contextmanager
def as_checked():
    """Card only: read every rule as if a qualified person had checked it, to test what Hoola WOULD say. Never used for her."""
    _AS_CHECKED[0] = True
    try:
        yield
    finally:
        _AS_CHECKED[0] = False


class PackError(ValueError):
    pass


class Unchecked(Exception):
    """A rule was needed at a level it does not have. Its message is what Hoola says to her."""
    def __init__(self, cc: str, path: str, have: str, need: str):
        self.cc, self.path, self.have, self.need = cc, path, have, need
        what = path.replace(".", " / ").replace("_", " ")
        if have == "missing":
            msg = f"Hoola has no rule for {what} in {cc} yet - check this with the official source."
        else:
            msg = f"Check this for {cc}: {what} is not confirmed yet ({have.replace('_', ' ')}), so Hoola will not use it here."
        super().__init__(msg)


def _leaf(v: Any) -> bool:
    return isinstance(v, dict) and "status" in v and "value" in v


def _walk(node: Any, path: str = ""):
    if _leaf(node):
        yield path, node
    elif isinstance(node, dict):
        for k, v in node.items():
            yield from _walk(v, f"{path}.{k}" if path else k)


def _day(s: Any) -> date | None:
    try:
        return date.fromisoformat(str(s))
    except ValueError:
        return None


def validate(p: dict[str, Any]) -> list[str]:
    errs = []
    for k in TOP:
        if k not in p:
            errs.append(f"missing {k}")
    if errs:
        return errs
    if not re.fullmatch(r"[A-Z]{2}", str(p["cc"])):
        errs.append("cc must be ISO alpha-2")
    if not re.fullmatch(r"[A-Z]{3}", str(p["currency"])):
        errs.append("currency must be ISO 4217")
    if int(p["minor_unit"]) != MINOR.get(p["currency"], 2):
        errs.append(f"minor_unit {p['minor_unit']} does not match ISO 4217 for {p['currency']}")
    for s in p["sections"]:
        if s not in SECTIONS:
            errs.append(f"unknown section {s}")
    hosts = [h.lower() for h in p.get("official_hosts") or []]
    for path, v in _walk(p["sections"]):
        st = v.get("status")
        if st not in STATUSES:
            errs.append(f"{path}: status {st!r}")
            continue
        if st in ("source_read", "checked"):
            src = str(v.get("source") or "")
            host = re.sub(r"^https?://([^/]+).*$", r"\1", src).lower()
            if not src.startswith("https://"):
                errs.append(f"{path}: {st} needs an https source")
            elif not any(host == h or host.endswith("." + h) for h in hosts):
                errs.append(f"{path}: {st} source {host} is not an official host of this pack")
            if not _day(v.get("checked_on")):
                errs.append(f"{path}: {st} needs checked_on")
            if not _day(v.get("review_by")):
                errs.append(f"{path}: {st} needs review_by")
        if st == "source_read" and not str(v.get("quote") or "").strip():
            errs.append(f"{path}: source_read needs the quoted official text")
        if st == "checked" and not str(v.get("checked_by") or "").strip():
            errs.append(f"{path}: checked needs checked_by")
    return errs


@lru_cache(maxsize=None)
def load(cc: str) -> dict[str, Any] | None:
    cc = str(cc or "").upper()
    f = DIR / f"{cc}.json"
    if not re.fullmatch(r"[A-Z]{2}", cc) or not f.exists():
        return None
    p = json.loads(f.read_text(encoding="utf-8"))
    p = _with_review(p)
    errs = validate(p)
    if errs:
        raise PackError(f"{cc}: " + "; ".join(errs[:6]))
    if cc == "IN":
        p = _with_india_rules(p)
    return p


def _with_review(p: dict[str, Any]) -> dict[str, Any]:
    """Lay the review file over the pack: each entry replaces one leaf's status / source / quote / dates (and value, when a person
    corrected it). The merged pack is validated like any other, so a review can never point at an unofficial site."""
    f = review_dir() / f"{p.get('cc', '')}.json"
    if not f.exists():
        return p
    try:
        rv = json.loads(f.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return p
    for path, e in (rv.get("rules") or {}).items():
        node = p["sections"]
        keys = path.split(".")
        for k in keys[:-1]:
            node = node.setdefault(k, {})
        leaf = dict(node.get(keys[-1]) or {"value": None, "status": "verify"})
        for k in ("status", "source", "quote", "checked_on", "review_by", "checked_by", "value"):
            if k in e:
                leaf[k] = e[k]
        node[keys[-1]] = leaf
    return p


def _with_india_rules(p: dict[str, Any]) -> dict[str, Any]:
    """India's tax rates and dates already live as rules-as-data in bahi/rules (v0.807). The pack reads them there - one copy, never
    two. bahi's basis maps honestly: primary -> source_read (a government page was read); anything else -> verify."""
    try:
        from ..bahi import rules as BR
    except Exception:
        return p
    tax = p["sections"].setdefault("tax", {})
    for name in ("gst_rates", "due_dates", "tds"):
        try:
            for r in BR.rows(name):
                st = "source_read" if r.get("basis") == "primary" else "verify"
                leaf = {"value": {k: v for k, v in r.items() if k not in ("basis", "source", "checked_on", "review_by", "id", "note")},
                        "status": st, "source": r.get("source", ""), "checked_on": r.get("checked_on", ""),
                        "review_by": r.get("review_by", ""), "quote": r.get("note", "") or r.get("id", ""), "from": f"bahi/rules/{name}.json"}
                tax.setdefault(name, {})[r["id"]] = leaf
        except Exception:
            continue
    return p


def codes() -> list[str]:
    return sorted(f.stem for f in DIR.glob("*.json") if re.fullmatch(r"[A-Z]{2}", f.stem))


def _effective(v: dict[str, Any], today: date | None = None) -> str:
    if _AS_CHECKED[0]:
        return "checked"
    st = v.get("status", "verify")
    rb = _day(v.get("review_by"))
    if st != "verify" and rb and rb < (today or date.today()):
        return "source_read" if st == "checked" else "verify"
    return st


def _get(p: dict[str, Any], path: str) -> Any:
    node: Any = p["sections"]
    for k in path.split("."):
        if not isinstance(node, dict) or k not in node:
            return None
        node = node[k]
    return node


def value_of(cc: str, path: str, need: str = "checked", today: date | None = None) -> dict[str, Any]:
    """The rule at `path` if it is at least at level `need`; else Unchecked (her words say what to check)."""
    if need not in STATUSES:
        raise ValueError(need)
    p = load(cc)
    if p is None:
        raise Unchecked(str(cc).upper(), path, "missing", need)
    v = _get(p, path)
    if not _leaf(v):
        raise Unchecked(p["cc"], path, "missing", need)
    eff = _effective(v, today)
    if LEVEL[eff] < LEVEL[need]:
        raise Unchecked(p["cc"], path, eff, need)
    return {"cc": p["cc"], "path": path, "value": v["value"], "status": eff, "source": v.get("source", ""),
            "checked_on": v.get("checked_on", ""), "review_by": v.get("review_by", "")}


def peek(cc: str, path: str) -> Any:
    """The raw value whatever its status - for display and defaults only (shown with its status), never for a calculation."""
    p = load(cc)
    v = _get(p, path) if p else None
    return v.get("value") if _leaf(v) else None


def currency_of(cc: str) -> str:
    p = load(cc)
    return p["currency"] if p else ""


def minor_unit(currency: str) -> int:
    return MINOR.get(str(currency or "").upper(), 2)


def freshness(cc: str, today: date | None = None) -> dict[str, Any]:
    p = load(cc)
    if p is None:
        return {"cc": str(cc).upper(), "floor": True, "checked": 0, "source_read": 0, "verify": 0, "expired": 0, "total": 0}
    c = {"checked": 0, "source_read": 0, "verify": 0, "expired": 0}
    for _, v in _walk(p["sections"]):
        eff = _effective(v, today)
        c[eff] += 1
        if eff != v.get("status"):
            c["expired"] += 1
    return {"cc": p["cc"], "name": p["name"], "floor": False, "version": p["version"], **c, "total": sum(c[s] for s in STATUSES)}


def view(cc: str) -> dict[str, Any]:
    p = load(cc)
    if p is None:
        return {"cc": str(cc).upper(), "floor": True,
                "says": "No country pack yet: explanations, budgets, document reading and maths on her own numbers; no country rule is used."}
    rows = [{"path": path, "value": v["value"], "status": _effective(v), "source": v.get("source", ""),
             "checked_on": v.get("checked_on", ""), "review_by": v.get("review_by", "")} for path, v in _walk(p["sections"])]
    return {"cc": p["cc"], "name": p["name"], "currency": p["currency"], "floor": False, "version": p["version"],
            "freshness": freshness(p["cc"]), "rows": rows}


def check_all(today: date | None = None) -> dict[str, Any]:
    out, bad = [], []
    for cc in codes():
        load.cache_clear()
        try:
            out.append(freshness(cc, today))
        except PackError as e:
            bad.append(str(e))
    return {"packs": out, "errors": bad}


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "check":
        r = check_all()
        for f in r["packs"]:
            print(f"{f['cc']} {f.get('name', '')}: {f['total']} rules - checked {f['checked']}, source read {f['source_read']}, "
                  f"verify {f['verify']}, expired {f['expired']}")
        for e in r["errors"]:
            print("ERROR", e)
        sys.exit(1 if r["errors"] else 0)
    print(__doc__)
