"""#11 loyalty lists, #21 markdown steps, #46 unit economics, #15 ABC/range, #28/#35 price rule check, #70 scheme accrual, #71 retailer credit exposure,
#69 beat route, #80 working capital, #6 delivery batches. Proposals only."""
from __future__ import annotations

import datetime as dt
import math
from collections import defaultdict
from typing import Any


def _f(v: Any) -> float:
    try:
        return float(str(v).replace(",", ""))
    except (TypeError, ValueError):
        return 0.0


def _d(v: Any) -> dt.date:
    s = str(v or "").strip()[:10]
    for f in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y"):
        try:
            return dt.datetime.strptime(s, f).date()
        except ValueError:
            pass
    raise ValueError(f"Could not understand the date: '{v}' (write YYYY-MM-DD).")


def loyalty(customers: list[dict], today: Any = None, lapsed_days: Any = 60) -> dict[str, Any]:
    if not customers:
        raise ValueError("Give customers rows: id, last_visit, visits, spend, birthday (MM-DD), opted_in.")
    t = _d(today) if today else dt.date.today()
    ld = _f(lapsed_days)
    ok = [c for c in customers if c.get("opted_in") in (True, "true", "yes", "1", 1)]
    skipped = len(customers) - len(ok)
    lapsed, birthdays, best = [], [], []
    for c in ok:
        idle = (t - _d(c.get("last_visit"))).days if c.get("last_visit") else None
        if idle is not None and idle >= ld:
            lapsed.append({"id": c.get("id"), "idle_days": idle, "spend": _f(c.get("spend"))})
        b = str(c.get("birthday") or "")
        if len(b) >= 5:
            try:
                bd = dt.date(t.year, int(b[-5:-3]), int(b[-2:]))
                if 0 <= (bd - t).days <= 7:
                    birthdays.append({"id": c.get("id"), "on": bd.isoformat()})
            except ValueError:
                pass
        best.append((c.get("id"), _f(c.get("spend"))))
    return {"opted_in": len(ok), "left_out_no_consent": skipped, "lapsed": sorted(lapsed, key=lambda r: -r["spend"])[:50], "birthdays_this_week": birthdays,
            "top_spenders": [{"id": i, "spend": s} for i, s in sorted(best, key=lambda x: -x[1])[:10]],
            "rule": "Only customers who said yes; the list is never sold to anyone; every message carries a way to stop.",
            "decider": "Sending a message is your tap; nothing was sent here."}


def markdown(items: list[dict], today: Any = None, steps: list | None = None) -> dict[str, Any]:
    if not items:
        raise ValueError("Give items rows: name, stock, cost, price, mrp, expiry, floor_margin_pct.")
    t = _d(today) if today else dt.date.today()
    sched = steps or [(14, 10), (7, 25), (3, 40)]     # (days left <=, discount % off current price) - HER schedule overrides
    out, at_risk = [], 0.0
    for it in items[:3000]:
        price, cost, stock = _f(it.get("price")), _f(it.get("cost")), _f(it.get("stock"))
        left = (_d(it.get("expiry")) - t).days
        disc = 0.0
        for days, pct in sorted(sched, key=lambda s: s[0], reverse=True):
            if left <= days:
                disc = _f(pct)
        new = price * (1 - disc / 100.0)
        floor = cost * (1 + _f(it.get("floor_margin_pct")) / 100.0)
        note = ""
        if new < floor:
            note = "Below the floor: the floor price was used to stay inside your limit."
            new = floor
        if _f(it.get("mrp")) and new > _f(it.get("mrp")):
            new = _f(it.get("mrp"))
        waste = round(stock * cost, 2) if left <= 3 else 0.0
        at_risk += waste
        out.append({"name": it.get("name"), "days_left": left, "discount_pct": round(100 * (1 - new / price), 1) if price else 0, "proposed_price": round(new, 2),
                    "below_cost": new < cost, "waste_risk_at_cost": waste, "note": note,
                    "route": "expired" if left < 0 else ("charity / staff / bulk offer" if left <= 2 else "")})
    return {"items": sorted(out, key=lambda r: r["days_left"]), "waste_risk_total": round(at_risk, 2),
            "assumed": "Discount steps come from your schedule (if not given, 10/25/40% at 14/7/3 days is assumed); selling expired goods is against the law.",
            "decider": "Setting the new price is your job; this is only a proposal."}


def unit_economics(cac: Any, orders: Any, aov: Any, cogs_pct: Any, ship_cost: Any = 0, return_rate_pct: Any = 0, return_cost: Any = 0, repeat_orders: Any = 1) -> dict[str, Any]:
    a, n, c = _f(aov), _f(orders), _f(cac)
    if a <= 0:
        raise ValueError("Give aov (average order value).")
    rr = _f(return_rate_pct) / 100.0
    contrib = a * (1 - _f(cogs_pct) / 100.0) - _f(ship_cost) - rr * _f(return_cost) - rr * a * 0  # revenue kept even if refunded? treated via return_cost
    ltv = contrib * max(1.0, _f(repeat_orders))
    return {"contribution_per_order": round(contrib, 2), "ltv_contribution": round(ltv, 2), "ltv_to_cac": round(ltv / c, 2) if c else None,
            "orders_to_recover_cac": round(c / contrib, 1) if contrib > 0 else None,
            "loss_per_order": contrib < 0, "note": "The effect of returns comes only from the return_cost you gave; add the refund amount into return_cost yourself." ,
            "decider": "The ad budget and the price are your decision; this is only a calculation."}


def abc(items: list[dict], a_pct: Any = 70, b_pct: Any = 90, tail_margin_pct: Any = 5) -> dict[str, Any]:
    if not items:
        raise ValueError("Give items rows: sku, sales, margin.")
    rows = sorted(items, key=lambda i: -_f(i.get("sales")))
    total = sum(_f(i.get("sales")) for i in rows) or 1.0
    run, out, tail = 0.0, [], []
    for i in rows:
        run += _f(i.get("sales"))
        share = 100 * run / total
        cls = "A" if share - 100 * _f(i.get("sales")) / total < _f(a_pct) else ("B" if share - 100 * _f(i.get("sales")) / total < _f(b_pct) else "C")
        out.append({"sku": i.get("sku"), "sales": _f(i.get("sales")), "class": cls, "cum_share_pct": round(share, 1)})
        if cls == "C" and _f(i.get("margin")) < _f(tail_margin_pct):
            tail.append(i.get("sku"))
    return {"skus": out, "counts": {k: sum(r["class"] == k for r in out) for k in "ABC"}, "range_review_candidates": tail,
            "note": "C class + low margin SKUs are only for consideration; keeping one can be right for local demand, a festival or a new product.",
            "decider": "Removing from the range is the category head's / owner's decision."}


def price_rule(items: list[dict], max_change_pct: Any = 10) -> dict[str, Any]:
    if not items:
        raise ValueError("Give items rows: name, cost, price, mrp, competitor_prices [..], floor_margin_pct, target (match_lowest|median|keep).")
    cap = _f(max_change_pct)
    out = []
    for it in items[:2000]:
        cost, price, mrp = _f(it.get("cost")), _f(it.get("price")), _f(it.get("mrp"))
        comps = sorted(_f(c) for c in it.get("competitor_prices") or [] if _f(c) > 0)
        floor = cost * (1 + _f(it.get("floor_margin_pct")) / 100.0)
        tgt = str(it.get("target") or "keep")
        want = price
        if comps and tgt == "match_lowest":
            want = comps[0]
        elif comps and tgt == "median":
            want = comps[len(comps) // 2]
        why = []
        if want < floor:
            want = floor
            why.append("not below the floor margin")
        if mrp and want > mrp:
            want = mrp
            why.append("not above MRP")
        ch = 100 * (want - price) / price if price else 0.0
        review = abs(ch) > cap
        if review:
            why.append(f"change {ch:+.1f}% is bigger than your {cap:g}% limit: check again")
        out.append({"name": it.get("name"), "current": price, "proposed": round(want, 2), "change_pct": round(ch, 1), "needs_second_look": review, "why": why,
                    "competitors_seen": len(comps)})
    return {"items": out, "rule": "Competitor prices are only the ones you gave (lawful / seller API / your own notes); no scraping.", "decider": "A price changes only with your approval."}


def scheme(scheme_def: dict, sales: list[dict], claims: list[dict] | None = None) -> dict[str, Any]:
    if not scheme_def or not sales:
        raise ValueError("Give scheme {min_qty, per_unit | percent, cap} and sales [{retailer, qty, value}].")
    minq, per, pct, cap = _f(scheme_def.get("min_qty")), _f(scheme_def.get("per_unit")), _f(scheme_def.get("percent")), scheme_def.get("cap")
    by = defaultdict(lambda: [0.0, 0.0])
    for s in sales:
        by[str(s.get("retailer"))][0] += _f(s.get("qty"))
        by[str(s.get("retailer"))][1] += _f(s.get("value"))
    rows = []
    for r, (q, v) in by.items():
        ok = q >= minq
        amt = (q * per + v * pct / 100.0) if ok else 0.0
        if cap is not None:
            amt = min(amt, _f(cap))
        rows.append({"retailer": r, "qty": q, "eligible": ok, "accrual": round(amt, 2)})
    cl = {str(c.get("retailer")): _f(c.get("amount")) for c in claims or []}
    for r in rows:
        if r["retailer"] in cl:
            r["claimed"] = cl[r["retailer"]]
            r["difference"] = round(cl[r["retailer"]] - r["accrual"], 2)
            r["status"] = "match" if abs(r["difference"]) < 0.5 else "dispute"
    return {"retailers": rows, "total_accrual": round(sum(r["accrual"] for r in rows), 2), "decider": "Finance approves the settlement; no payment or credit note was made here."}


def credit_exposure(retailers: list[dict], limit_multiple: Any = 1.5, overdue_days: Any = 30) -> dict[str, Any]:
    if not retailers:
        raise ValueError("Give retailers rows: retailer, outstanding, oldest_days, limit, avg_monthly_purchase.")
    m, od = _f(limit_multiple), _f(overdue_days)
    out = []
    for r in retailers[:3000]:
        out_, lim, avg = _f(r.get("outstanding")), _f(r.get("limit")), _f(r.get("avg_monthly_purchase"))
        sug = round(avg * m, 2)
        flags = []
        if lim and out_ > lim:
            flags.append("over the limit")
        if _f(r.get("oldest_days")) > od:
            flags.append(f"{_f(r.get('oldest_days')):g} days old and still unpaid")
        out.append({"retailer": r.get("retailer"), "outstanding": out_, "limit": lim, "utilisation_pct": round(100 * out_ / lim, 1) if lim else None,
                    "suggested_limit": sug, "flags": flags})
    return {"retailers": out, "basis": f"Suggested limit = average monthly purchase x {m:g} (your multiplier). Only the record of dealings; no basis like caste / religion / locality.",
            "decider": "The credit head decides the credit limit; no limit was changed here."}


def beat_route(start: dict, stops: list[dict]) -> dict[str, Any]:
    if not stops or not start:
        raise ValueError("Give start {lat, lng} and stops [{name, lat, lng}].")
    def hav(a, b):
        r = 6371.0
        p1, p2 = math.radians(_f(a["lat"])), math.radians(_f(b["lat"]))
        dp, dl = p2 - p1, math.radians(_f(b["lng"]) - _f(a["lng"]))
        h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
        return 2 * r * math.asin(math.sqrt(h))
    cur, left, order, total = start, list(stops), [], 0.0
    while left:
        nxt = min(left, key=lambda s: hav(cur, s))
        d = hav(cur, nxt)
        total += d
        order.append({"name": nxt.get("name"), "leg_km": round(d, 2)})
        cur = nxt
        left.remove(nxt)
    return {"order": order, "straight_line_km": round(total, 2), "method": "nearest-neighbour, straight-line distance (not by road)",
            "note": "For real road distance / time use maps_nearest or maps_route_plan.", "decider": "The sales manager decides the day's route."}


def working_capital(inventory: Any, cogs_annual: Any, receivables: Any, sales_annual: Any, payables: Any) -> dict[str, Any]:
    cogs, sales = _f(cogs_annual), _f(sales_annual)
    if cogs <= 0 or sales <= 0:
        raise ValueError("Give cogs_annual and sales_annual.")
    dio, dso, dpo = 365 * _f(inventory) / cogs, 365 * _f(receivables) / sales, 365 * _f(payables) / cogs
    ccc = dio + dso - dpo
    return {"inventory_days": round(dio, 1), "receivable_days": round(dso, 1), "payable_days": round(dpo, 1), "cash_cycle_days": round(ccc, 1),
            "cash_tied_up_estimate": round(ccc / 365 * sales, 2),
            "reading": "The shorter the cash cycle, the less money is tied up." , "decider": "Taking credit / a loan is decided by the lender and you; this is only a calculation."}


def delivery_batches(orders: list[dict], free_above: Any = 0, flat_fee: Any = 0) -> dict[str, Any]:
    if not orders:
        raise ValueError("Give orders rows: id, area, amount.")
    by = defaultdict(list)
    for o in orders[:3000]:
        by[str(o.get("area") or "?")].append(o)
    out = []
    for area, os_ in sorted(by.items(), key=lambda kv: -len(kv[1])):
        total = sum(_f(o.get("amount")) for o in os_)
        fee = 0.0 if (_f(free_above) and total >= _f(free_above)) else _f(flat_fee)
        out.append({"area": area, "orders": [o.get("id") for o in os_], "count": len(os_), "value": round(total, 2), "fee_if_one_trip": fee})
    return {"batches": out, "rule": "Charges come only from your rule (free_above / flat_fee).", "decider": "You decide the rider and the delivery charge."}
