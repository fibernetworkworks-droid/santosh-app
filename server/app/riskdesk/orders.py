"""#66 order ticket, #65 mandate drift, #75 exposure monitor. A ticket is a PREPARED paper: nothing is placed here. An order can only go through
the broker's own official API on the investor's explicit tap. No view on what to buy or sell is ever given; limits are the investor's own."""
from __future__ import annotations

from typing import Any


def _f(v: Any, name: str = "value", required: bool = False) -> float:
    if v is None or v == "":
        if required:
            raise ValueError(f"{name} is required.")
        return 0.0
    try:
        return float(str(v).replace(",", ""))
    except ValueError:
        raise ValueError(f"{name} must be a number.")


def ticket(symbol: str, side: str, qty: Any, order_type: str = "limit", price: Any = None, ltp: Any = None, product: str = "delivery",
           portfolio_value: Any = None, holding_qty: Any = None, rates: dict | None = None, max_pct_of_portfolio: Any = 10,
           max_price_deviation_pct: Any = 5) -> dict[str, Any]:
    sym, sd, ot, pr = str(symbol or "").strip().upper(), str(side or "").lower(), str(order_type or "").lower(), str(product or "").lower()
    if not sym:
        raise ValueError("symbol is required.")
    if sd not in ("buy", "sell"):
        raise ValueError("Give side as buy or sell.")
    if ot not in ("market", "limit", "stoploss"):
        raise ValueError("order_type: market / limit / stoploss.")
    q = int(_f(qty, "qty", True))
    if q <= 0:
        raise ValueError("qty must be 1 or more.")
    p, l = _f(price, "price"), _f(ltp, "ltp")
    if ot != "market" and p <= 0:
        raise ValueError("Give a price for a limit / stoploss order.")
    px = p if ot != "market" else l
    flags = []
    value = round(q * px, 2) if px > 0 else None
    if value is None:
        flags.append({"level": "info", "text": "An estimate for a market order needs the ltp; no value was worked out."})
    if ot == "market":
        flags.append({"level": "caution", "text": "A market order fills at whatever price is available; in a thinly traded (low volume) share the price can move a lot."})
    if ot == "limit" and l > 0:
        dev = 100 * (p - l) / l
        lim = _f(max_price_deviation_pct)
        if (sd == "buy" and dev > lim) or (sd == "sell" and dev < -lim):
            flags.append({"level": "check", "text": f"Your limit price is {dev:+.1f}% from the ltp, your limit is {lim:g}%: was it typed wrongly?"})
    pv = _f(portfolio_value)
    if value and pv > 0:
        pct = 100 * value / pv
        if sd == "buy" and pct > _f(max_pct_of_portfolio):
            flags.append({"level": "check", "text": f"This order is {pct:.1f}% of the portfolio, your own limit is {max_pct_of_portfolio}%."})
    if sd == "sell" and holding_qty is not None and q > _f(holding_qty):
        flags.append({"level": "stop", "text": f"Sell qty {q} is more than the {holding_qty} you hold (it would become a short sale)."})
    if pr in ("intraday", "margin", "mis", "mtf"):
        flags.append({"level": "caution", "text": "Margin / intraday product: the loss can be more than the money put in, and the position can be closed at the end of the day."})
    ch = None
    r = rates or {}
    if value and r:
        b = value * _f(r.get("brokerage_pct")) / 100.0
        if r.get("brokerage_cap") is not None:
            b = min(b, _f(r.get("brokerage_cap")))
        other = value * _f(r.get("other_pct")) / 100.0
        ch = {"brokerage": round(b, 2), "other": round(other, 2), "total": round(b + other, 2),
              "basis": "Only from the rates you gave; I did not fill in GST / STT / stamp rates."}
    t = {"symbol": sym, "side": sd, "qty": q, "order_type": ot, "price": p or None, "ltp": l or None, "product": pr, "est_value": value, "est_charges": ch}
    return {"ticket": t, "flags": flags, "placed": False,
            "confirm_text": f"{sd.upper()} {q} x {sym} {ot.upper()}" + (f" @ {p:g}" if p else "") + (f" (~Rs {value:,.0f})" if value else ""),
            "charges_note": None if ch else "Charges: no rates were given, so they were not worked out.",
            "not_checked": "Whether the price is true, circuit limits, margin / funds, market hours: the broker's system checks these.",
            "decider": "This is only a prepared order ticket. It is sent on your confirm tap, only through the broker's official API; nothing was sent here. This does not give buy / sell advice."}


def drift(holdings: list[dict], targets: dict | None = None, tolerance_pct: Any = 5, max_single_pct: Any = None, max_group_pct: Any = None,
          margin: dict | None = None, margin_alert_pct: Any = 80) -> dict[str, Any]:
    if not holdings:
        raise ValueError("Give holdings rows: symbol, qty, price (and group if you like).")
    rows, total = [], 0.0
    for h in holdings[:2000]:
        v = _f(h.get("qty"), "qty") * _f(h.get("price"), "price")
        rows.append({"symbol": str(h.get("symbol") or "?").upper(), "group": str(h.get("group") or h.get("sector") or ""), "value": round(v, 2)})
        total += v
    if total <= 0:
        raise ValueError("The portfolio's total value is 0.")
    for r in rows:
        r["weight_pct"] = round(100 * r["value"] / total, 2)
    groups: dict[str, float] = {}
    for r in rows:
        if r["group"]:
            groups[r["group"]] = groups.get(r["group"], 0.0) + r["weight_pct"]
    alerts = []
    ms = _f(max_single_pct) if max_single_pct is not None else None
    mg = _f(max_group_pct) if max_group_pct is not None else None
    for r in rows:
        if ms is not None and r["weight_pct"] > ms:
            alerts.append(f"{r['symbol']} {r['weight_pct']}%, the mandate limit is {ms:g}%.")
    for g, w in groups.items():
        if mg is not None and w > mg:
            alerts.append(f"Group '{g}' {w:.1f}%, the mandate limit is {mg:g}%.")
    drifts, prop = [], []
    tol = _f(tolerance_pct)
    for k, tgt in (targets or {}).items():
        cur = next((r["weight_pct"] for r in rows if r["symbol"] == k.upper()), groups.get(k, 0.0))
        d = round(cur - _f(tgt), 2)
        drifts.append({"name": k, "current_pct": round(cur, 2), "target_pct": _f(tgt), "drift_pct": d, "outside_tolerance": abs(d) > tol})
        if abs(d) > tol:
            prop.append({"name": k, "move_value": round(-d * total / 100.0, 2), "note": "This is a proposal, not an order: the portfolio manager decides."})
    mg_out = None
    if margin:
        used, avail = _f(margin.get("used")), _f(margin.get("available"))
        util = round(100 * used / (used + avail), 1) if used + avail else None
        mg_out = {"utilisation_pct": util, "alert": util is not None and util >= _f(margin_alert_pct)}
        if mg_out["alert"]:
            alerts.append(f"Margin used {util}%, your alert was at {margin_alert_pct}%.")
    return {"total_value": round(total, 2), "weights": sorted(rows, key=lambda r: -r["weight_pct"]), "groups": {k: round(v, 2) for k, v in groups.items()},
            "drift": drifts, "alerts": alerts, "proposals": prop, "margin": mg_out,
            "not_checked": "Live prices, liquidity, tax impact, the mandate's other rules.",
            "decider": "The rebalance decision is the portfolio manager's / investor's; compliance checks first. No trade was made here."}
