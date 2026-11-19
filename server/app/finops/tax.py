"""#11/#103 slice: reconcile TDS in her books against the 26AS / AIS rows she pastes. Matching only; no rates, no sections invented."""
from __future__ import annotations

from collections import defaultdict
from typing import Any


def _f(v: Any) -> float:
    try:
        return float(str(v).replace(",", ""))
    except (TypeError, ValueError):
        return 0.0


def _key(r: dict) -> tuple[str, str]:
    return (str(r.get("party") or r.get("deductor") or "").strip().lower(), str(r.get("section") or "").strip().upper())


def tds_reconcile(books: list[dict], portal: list[dict], tolerance: Any = 1.0) -> dict[str, Any]:
    if not books and not portal:
        raise ValueError("Give the books and portal (26AS / AIS) rows.")
    tol = _f(tolerance)
    b, p = defaultdict(float), defaultdict(float)
    for r in books or []:
        b[_key(r)] += _f(r.get("tds"))
    for r in portal or []:
        p[_key(r)] += _f(r.get("tds"))
    rows = []
    for k in sorted(set(b) | set(p)):
        bv, pv = round(b.get(k, 0.0), 2), round(p.get(k, 0.0), 2)
        diff = round(bv - pv, 2)
        status = "match" if abs(diff) <= tol else ("not_in_portal" if k not in p else ("not_in_books" if k not in b else "difference"))
        rows.append({"party": k[0], "section": k[1], "books_tds": bv, "portal_tds": pv, "difference": diff, "status": status})
    bad = [r for r in rows if r["status"] != "match"]
    asks = {"not_in_portal": "Ask the party: was the TDS deposited / is the PAN right? If it does not show on the portal, there is no credit.",
            "not_in_books": "No entry in the books: was this income/receipt missed?",
            "difference": "The amounts differ: ask for the certificate (Form 16A)."}
    return {"rows": rows, "matched": len(rows) - len(bad), "to_check": len(bad), "what_to_ask": {r["party"] + "/" + r["section"]: asks[r["status"]] for r in bad},
            "not_checked": "The section's rate, the threshold, or whether the PAN/TAN is right: these were not checked.",
            "decider": "The claim and the reply are decided by your CA."}
