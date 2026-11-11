"""#110 payables / receivables: ageing and 3-way match. Nothing is paid or sent; a payment run is the approver's tap elsewhere."""
from __future__ import annotations

import datetime as dt
from typing import Any


def _d(v: Any) -> dt.date:
    if isinstance(v, dt.date):
        return v
    s = str(v or "").strip()[:10]
    for f in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y"):
        try:
            return dt.datetime.strptime(s, f).date()
        except ValueError:
            pass
    raise ValueError(f"Could not read the date: '{v}' (write YYYY-MM-DD).")


def _f(v: Any) -> float:
    try:
        return float(str(v).replace(",", ""))
    except (TypeError, ValueError):
        return 0.0


BUCKETS = [("not_due", None), ("1-30", 30), ("31-60", 60), ("61-90", 90), ("90+", 10**9)]


def ageing(items: list[dict], as_of: Any = None) -> dict[str, Any]:
    if not items:
        raise ValueError("invoices rows do: party, invoice_no, due_date, amount, paid.")
    today = _d(as_of) if as_of else dt.date.today()
    tot = {b: 0.0 for b, _ in BUCKETS}
    parties: dict[str, dict] = {}
    rows = []
    for it in items[:5000]:
        out = round(_f(it.get("amount")) - _f(it.get("paid")), 2)
        if out <= 0:
            continue
        late = (today - _d(it.get("due_date") or it.get("date"))).days
        b = "not_due" if late <= 0 else next(n for n, hi in BUCKETS[1:] if late <= hi)
        tot[b] += out
        p = parties.setdefault(str(it.get("party") or "?"), {"outstanding": 0.0, "oldest_days_late": 0})
        p["outstanding"] = round(p["outstanding"] + out, 2)
        p["oldest_days_late"] = max(p["oldest_days_late"], late)
        rows.append({"party": it.get("party"), "invoice_no": it.get("invoice_no"), "outstanding": out, "days_late": max(0, late), "bucket": b})
    return {"as_of": today.isoformat(), "buckets": {k: round(v, 2) for k, v in tot.items()}, "total_outstanding": round(sum(tot.values()), 2),
            "by_party": dict(sorted(parties.items(), key=lambda kv: -kv[1]["outstanding"])), "rows": rows,
            "decider": "Sending a reminder or running a payment run is the approver's tap; nothing was sent or paid here."}


def three_way(pos: list[dict], grns: list[dict], invoices: list[dict], qty_tol_pct: Any = 0, price_tol_pct: Any = 0) -> dict[str, Any]:
    qt, pt = _f(qty_tol_pct), _f(price_tol_pct)
    po = {str(r.get("po")): r for r in pos or []}
    gr: dict[str, float] = {}
    for r in grns or []:
        gr[str(r.get("po"))] = gr.get(str(r.get("po")), 0.0) + _f(r.get("qty"))
    out = []
    for inv in invoices or []:
        k = str(inv.get("po"))
        p = po.get(k)
        issues = []
        if not p:
            issues.append("PO not found")
        else:
            iq, rq, oq = _f(inv.get("qty")), gr.get(k, 0.0), _f(p.get("qty"))
            if rq == 0:
                issues.append("goods not received (no GRN)")
            elif abs(iq - rq) > rq * qt / 100.0:
                issues.append(f"invoice qty {iq:g} != received {rq:g}")
            if iq > oq * (1 + qt / 100.0):
                issues.append(f"invoice qty {iq:g} is more than PO qty {oq:g}")
            op, ip = _f(p.get("price")), _f(inv.get("price"))
            if op and abs(ip - op) > op * pt / 100.0:
                issues.append(f"rate {ip:g} != PO rate {op:g}")
        out.append({"invoice": inv.get("invoice_no"), "po": k, "status": "match" if not issues else "hold", "issues": issues})
    return {"results": out, "match": sum(r["status"] == "match" for r in out), "hold": sum(r["status"] == "hold" for r in out),
            "not_checked": "Tax, discount, freight, partial-delivery schedules and duplicate invoice numbers: these were not checked.",
            "decider": "Hold or release is decided by the approver; payment happens only on their tap."}
