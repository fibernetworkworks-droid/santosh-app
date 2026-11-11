"""#1 daily summary, #81 cash-flow forecast, #2 reorder + dead stock + expiry, #7 margin/MRP check, #10 compliance calendar, #36 oversell check."""
from __future__ import annotations

import datetime as dt
from collections import defaultdict
from typing import Any


def _f(v: Any) -> float:
    try:
        return float(str(v).replace(",", ""))
    except (TypeError, ValueError):
        return 0.0


def _d(v: Any) -> dt.date:
    if isinstance(v, dt.date):
        return v
    s = str(v or "").strip()[:10]
    for f in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y"):
        try:
            return dt.datetime.strptime(s, f).date()
        except ValueError:
            pass
    raise ValueError(f"Could not read the date: '{v}' (write it as YYYY-MM-DD).")


def day_summary(sales: list[dict]) -> dict[str, Any]:
    if not sales:
        raise ValueError("sales rows do: time (ya date), amount, mode (cash/upi/credit), item.")
    mode, hour, item = defaultdict(float), defaultdict(float), defaultdict(float)
    for s in sales[:20000]:
        a = _f(s.get("amount"))
        mode[str(s.get("mode") or "other").lower()] += a
        t = str(s.get("time") or "")
        if len(t) >= 13 and t[10] in "T " and t[11:13].isdigit():
            hour[int(t[11:13])] += a
        elif len(t) >= 2 and t[:2].isdigit() and ":" in t:
            hour[int(t[:2])] += a
        if s.get("item"):
            item[str(s["item"])] += a
    total = sum(mode.values())
    best = max(hour.items(), key=lambda kv: kv[1]) if hour else None
    return {"total": round(total, 2), "bills": len(sales), "by_mode": {k: round(v, 2) for k, v in mode.items()},
            "credit_given": round(mode.get("credit", 0.0), 2), "best_hour": best[0] if best else None,
            "best_hour_amount": round(best[1], 2) if best else None,
            "top_items": [{"item": k, "amount": round(v, 2)} for k, v in sorted(item.items(), key=lambda kv: -kv[1])[:5]],
            "decider": "This is only a summary of the bills you gave; giving credit or not is your decision."}


def forecast(weekly_sales: list[Any], weeks: int = 4, festival_boost: dict | None = None) -> dict[str, Any]:
    ws = [_f(x) for x in weekly_sales or []]
    if len(ws) < 4:
        raise ValueError("Give at least 4 weeks of sales (weekly_sales: [..]).")
    recent = ws[-4:]
    base = sum(recent) / 4.0
    trend = (recent[-1] - recent[0]) / 3.0
    out = []
    boost = {int(k): _f(v) for k, v in (festival_boost or {}).items()}
    for i in range(1, int(weeks) + 1):
        v = max(0.0, base + trend * i * 0.5) * boost.get(i, 1.0)
        out.append({"week_ahead": i, "estimate": round(v, 2), "festival_multiplier": boost.get(i, 1.0)})
    spread = max(recent) - min(recent)
    return {"base_avg_last4": round(base, 2), "weekly_trend": round(trend, 2), "forecast": out,
            "range_note": f"The last 4 weeks varied by {round(spread, 2)} up and down, so each estimate can be off by about that much.",
            "assumed": "Simple averaging + half the trend; the festival effect only from the multiplier you gave.",
            "decider": "Ordering stock / taking credit is your decision; this is an estimate, not a promise."}


def reorder(items: list[dict], today: Any = None, cover_days: Any = 7, expiry_days: Any = 30, dead_days: Any = 45) -> dict[str, Any]:
    if not items:
        raise ValueError("items rows do: name, stock, daily_sales, lead_days, cost, last_sold, expiry.")
    t = _d(today) if today else dt.date.today()
    cd, ed, dd = _f(cover_days), _f(expiry_days), _f(dead_days)
    rows, expiring, dead, tied = [], [], [], 0.0
    for it in items[:5000]:
        stock, ds, lead = _f(it.get("stock")), _f(it.get("daily_sales")), _f(it.get("lead_days"))
        need = ds * (lead + cd)
        order = max(0.0, need - stock)
        days_left = round(stock / ds, 1) if ds else None
        r = {"name": it.get("name"), "stock": stock, "days_of_stock": days_left, "order_qty": round(order, 1) if order else 0,
             "mover": "fast" if ds and stock / ds <= lead else ("slow" if ds and ds < 0.2 else "normal") if ds else "no sales"}
        rows.append(r)
        if it.get("expiry"):
            left = (_d(it["expiry"]) - t).days
            if left <= ed:
                expiring.append({"name": it.get("name"), "days_left": left, "stock": stock, "value_at_cost": round(stock * _f(it.get("cost")), 2)})
        if it.get("last_sold"):
            idle = (t - _d(it["last_sold"])).days
            if idle >= dd and stock > 0:
                val = round(stock * _f(it.get("cost")), 2)
                dead.append({"name": it.get("name"), "idle_days": idle, "cash_stuck": val})
                tied += val
    return {"reorder": [r for r in rows if r["order_qty"]], "all": rows, "expiring": sorted(expiring, key=lambda e: e["days_left"]),
            "dead_stock": sorted(dead, key=lambda d: -d["cash_stuck"]), "cash_stuck_in_dead_stock": round(tied, 2),
            "formula": f"order = daily_sales x (lead_days + {cd:g} days cover) - stock",
            "decider": "Placing the order is your tap; nothing was sent to the supplier here."}


def margin(items: list[dict]) -> dict[str, Any]:
    if not items:
        raise ValueError("items rows do: name, cost, selling, mrp.")
    out, flags = [], []
    for it in items[:5000]:
        c, s, m = _f(it.get("cost")), _f(it.get("selling")), _f(it.get("mrp"))
        r = {"name": it.get("name"), "margin_pct_on_selling": round(100 * (s - c) / s, 1) if s else None, "markup_pct_on_cost": round(100 * (s - c) / c, 1) if c else None}
        if m and s > m:
            flags.append({"name": it.get("name"), "issue": f"Selling price {s:g} is above the MRP {m:g}: selling above MRP is against the law."})
        if c and s < c:
            flags.append({"name": it.get("name"), "issue": f"Selling price {s:g} is below the cost {c:g}: a loss on every sale."})
        out.append(r)
    return {"items": out, "flags": flags, "decider": "Setting prices is your job; this changes nothing."}


_CAL = [("GSTR-1", 11, "the 11th of the month (monthly filer)"), ("GSTR-3B", 20, "the 20th of the month (monthly filer; different under QRMP)")]


def licences(items: list[dict], today: Any = None, warn_days: Any = 45) -> dict[str, Any]:
    t = _d(today) if today else dt.date.today()
    w = _f(warn_days)
    rows = []
    for it in items or []:
        left = (_d(it.get("expiry")) - t).days
        rows.append({"name": it.get("name"), "expiry": str(_d(it.get("expiry"))), "days_left": left,
                     "status": "expired" if left < 0 else ("renew soon" if left <= w else "ok")})
    gst = []
    for name, day, note in _CAL:
        nxt = dt.date(t.year, t.month, day)
        if nxt < t:
            nxt = dt.date(t.year + (t.month == 12), (t.month % 12) + 1, day)
        gst.append({"name": name, "next_due": nxt.isoformat(), "note": note})
    return {"licences": sorted(rows, key=lambda r: r["days_left"]), "gst_dates": gst, "verify": True,
            "note": "The GST dates are from memory (verify): check your filing frequency and the latest notification. The licence list is from the entries you gave; we have no record of your licences.",
            "decider": "Renewal and filing are done by you / your CA."}


def oversell(channels: list[dict], safety_stock: Any = 0) -> dict[str, Any]:
    if not channels:
        raise ValueError("channels rows do: channel, stock, open_orders.")
    ss = _f(safety_stock)
    total = sum(_f(c.get("stock")) for c in channels)
    committed = sum(_f(c.get("open_orders")) for c in channels)
    free = total - committed - ss
    rows = [{"channel": c.get("channel"), "stock": _f(c.get("stock")), "open_orders": _f(c.get("open_orders")),
             "oversold": _f(c.get("open_orders")) > _f(c.get("stock"))} for c in channels]
    return {"total_stock": total, "open_orders": committed, "safety_stock": ss, "sellable_now": max(0.0, free), "short_by": max(0.0, -free),
            "channels": rows, "risk": "OVERSELL" if free < 0 else ("tight" if free < ss else "ok"),
            "suggest": "Stop this item on all channels at once, or correct the stock." if free < 0 else "",
            "decider": "Stopping a listing / changing stock is your tap; nothing was changed here."}
