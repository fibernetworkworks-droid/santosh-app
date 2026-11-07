"""State rule packs: the law as DATA, never code (v0.512.0 - the state-pack law of the plan §6).

Every rule row carries its value, the clause it comes from, the source document, the date it was checked
and a `refresh_by` date. The loader refuses a stale pack (a stale pack makes the checker say so instead
of answering). Packs live beside this file as `<state>.json`; only what is DETERMINED and sourced goes
in - notified rates that move (minimum wages, cess notifications) are recorded with their notification
source or left out entirely, never guessed.

v0.512.0 ships `maharashtra.json` v0 (the plan's worked example) and the loader. Wave 2 checkers
(bye-law, RERA, approvals) consume these rows; Wave 1's `const_labour cess/TDS` reads the determined
tax rows through `tax_rows()`.

v0.550.0 adds `india.json` - the NATIONAL code rows for the Wave-3 desks (IS 875 unit weights and
imposed loads, IS 456 span/depth ratios, CPHEEO per-capita water). `rule_row(state, rule_id)` reads
the state pack FIRST, then the national pack, so a state row always wins; both refuse when stale.
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

_DIR = Path(__file__).parent

REQUIRED = ("state", "checked_on", "refresh_by", "rows")


class PackError(Exception):
    pass


def _validate(pack: dict) -> dict:
    for k in REQUIRED:
        if k not in pack:
            raise PackError(f"pack adhoora hai: '{k}' nahi mila")
    if not isinstance(pack.get("rows"), list) or not pack["rows"]:
        raise PackError("pack mein rows nahi")
    seen: set[str] = set()
    for r in pack["rows"]:
        for k in ("rule_id", "value", "clause", "source", "checked_on"):
            if k not in r:
                raise PackError(f"row mein '{k}' nahi: {r.get('rule_id', '?')}")
        if r["rule_id"] in seen:
            raise PackError(f"duplicate rule_id: {r['rule_id']}")
        seen.add(r["rule_id"])
    try:
        if date.fromisoformat(pack["refresh_by"]) < date.fromisoformat(pack["checked_on"]):
            raise PackError("refresh_by checked_on se pehle nahi ho sakta")
    except ValueError as ex:
        raise PackError(f"tareekh galat: {ex}") from None
    return pack


def load(state: str) -> dict:
    """Load + validate one state pack by name ('maharashtra'). Raises PackError with an honest message."""
    p = _DIR / f"{(state or '').strip().lower()}.json"
    if not p.exists():
        raise PackError(f"'{state}' ka rule pack abhi nahi hai. Jo states hain: "
                        + ", ".join(sorted(x.stem for x in _DIR.glob('*.json'))))
    try:
        pack = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as ex:
        raise PackError(f"pack padhne mein dikkat: {ex}") from None
    return _validate(pack)


def stale(pack: dict, on: date | None = None) -> bool:
    """True when the pack's refresh_by date has passed - the checker must say so, not answer."""
    try:
        return (on or date.today()) > date.fromisoformat(str(pack.get("refresh_by", "")))
    except ValueError:
        return True


def row(pack: dict, rule_id: str) -> dict | None:
    for r in pack.get("rows", []):
        if r.get("rule_id") == rule_id:
            return r
    return None


def value(pack: dict, rule_id: str, default=None):
    r = row(pack, rule_id)
    if r is None:
        return default
    return r.get("value", default)


def _fresh(state: str) -> dict:
    """load + the staleness refusal, shared by every reader - a stale pack makes the desk say so."""
    pack = load(state)
    if stale(pack):
        raise PackError(f"{pack.get('state')} ka rule pack purana hai (refresh_by {pack.get('refresh_by')}) - "
                        "pehle pack verify karke refresh karo, phir hisaab.")
    return pack


def national() -> dict:
    """The national code pack (`india`), refusing when stale."""
    return _fresh("india")


def rule_row(state: str, rule_id: str) -> dict | None:
    """One rule row, state pack first then the national pack - the state row always wins. Stale pack
    refuses (PackError); a rule that is in neither returns None and the caller refuses to guess."""
    _fresh(state)
    try:
        nat = national()
    except PackError:
        nat = {}
    r = row(load(state), rule_id)
    if r:
        return r
    return row(nat, rule_id)


def rule_value(state: str, rule_id: str, default=None):
    r = rule_row(state, rule_id)
    if r is None:
        return default
    return r.get("value", default)


def rule_cited(state: str, rule_id: str) -> dict:
    """The row with its citation, refusing when the rule is missing - the desk never carries a
    number without its clause."""
    r = rule_row(state, rule_id)
    if r is None:
        raise PackError(f"rule '{rule_id}' na state pack mein hai na national pack mein - bina clause ka "
                        "number nahi chalta. Rule ke clause + source ke saath add karo.")
    return {"rule_id": rule_id, "value": r.get("value"), "clause": r.get("clause"), "source": r.get("source"),
            "checked_on": r.get("checked_on")}


def tax_rows(state: str = "maharashtra") -> dict:
    """The determined tax / cess numbers Wave 1's calculators work from, each with its citation.
    Raises PackError (stale pack included) - the caller says the message, never a made-up rate."""
    pack = _fresh(state)
    out = {}
    for rid in ("gst_works_contract", "gst_tds", "it_tds_194c", "bocw_cess", "rera_escrow_pct"):
        r = row(pack, rid)
        if r:
            out[rid] = {"value": r.get("value"), "clause": r.get("clause"), "source": r.get("source"),
                        "checked_on": r.get("checked_on")}
    return out
