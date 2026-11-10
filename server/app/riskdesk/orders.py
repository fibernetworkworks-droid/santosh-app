"""#66 order ticket, #65 mandate drift, #75 exposure monitor. A ticket is a PREPARED paper: nothing is placed here. An order can only go through
the broker's own official API on the investor's explicit tap. No view on what to buy or sell is ever given; limits are the investor's own."""
from __future__ import annotations

from typing import Any


def _f(v: Any, name: str = "value", required: bool = False) -> float:
    if v is None or v == "":
        if required:
            raise ValueError(f"{name} do.")
        return 0.0
    try:
        return float(str(v).replace(",", ""))
    except ValueError:
        raise ValueError(f"{name} number chahiye.")


def ticket(symbol: str, side: str, qty: Any, order_type: str = "limit", price: Any = None, ltp: Any = None, product: str = "delivery",
           portfolio_value: Any = None, holding_qty: Any = None, rates: dict | None = None, max_pct_of_portfolio: Any = 10,
           max_price_deviation_pct: Any = 5) -> dict[str, Any]:
    sym, sd, ot, pr = str(symbol or "").strip().upper(), str(side or "").lower(), str(order_type or "").lower(), str(product or "").lower()
    if not sym:
        raise ValueError("symbol do.")
    if sd not in ("buy", "sell"):
        raise ValueError("side buy ya sell likhiye.")
    if ot not in ("market", "limit", "stoploss"):
        raise ValueError("order_type: market / limit / stoploss.")
    q = int(_f(qty, "qty", True))
    if q <= 0:
        raise ValueError("qty 1 ya zyada.")
    p, l = _f(price, "price"), _f(ltp, "ltp")
    if ot != "market" and p <= 0:
        raise ValueError("limit / stoploss ke liye price do.")
    px = p if ot != "market" else l
    flags = []
    value = round(q * px, 2) if px > 0 else None
    if value is None:
        flags.append({"level": "info", "text": "Market order ka andaaza ke liye ltp chahiye; value nahi nikali."})
    if ot == "market":
        flags.append({"level": "caution", "text": "Market order jis bhaav par mile wahi lagta hai; patle (kam volume) share mein bhaav bahut hil sakta hai."})
    if ot == "limit" and l > 0:
        dev = 100 * (p - l) / l
        lim = _f(max_price_deviation_pct)
        if (sd == "buy" and dev > lim) or (sd == "sell" and dev < -lim):
            flags.append({"level": "check", "text": f"Aapka limit bhaav ltp se {dev:+.1f}% par hai, aapki seema {lim:g}%: kya galat likha gaya?"})
    pv = _f(portfolio_value)
    if value and pv > 0:
        pct = 100 * value / pv
        if sd == "buy" and pct > _f(max_pct_of_portfolio):
            flags.append({"level": "check", "text": f"Yeh order portfolio ka {pct:.1f}% hai, aapki apni seema {max_pct_of_portfolio}%."})
    if sd == "sell" and holding_qty is not None and q > _f(holding_qty):
        flags.append({"level": "stop", "text": f"Bechne ki qty {q} aapke paas ki {holding_qty} se zyada hai (short sale ban jaayegi)."})
    if pr in ("intraday", "margin", "mis", "mtf"):
        flags.append({"level": "caution", "text": "Udhaar / intraday product: nuksaan lagayi hui rakam se zyada ho sakta hai aur din ke ant mein position band ho sakti hai."})
    ch = None
    r = rates or {}
    if value and r:
        b = value * _f(r.get("brokerage_pct")) / 100.0
        if r.get("brokerage_cap") is not None:
            b = min(b, _f(r.get("brokerage_cap")))
        other = value * _f(r.get("other_pct")) / 100.0
        ch = {"brokerage": round(b, 2), "other": round(other, 2), "total": round(b + other, 2),
              "basis": "Sirf aapke diye hue dar se; GST / STT / stamp ke dar maine nahi bhare."}
    t = {"symbol": sym, "side": sd, "qty": q, "order_type": ot, "price": p or None, "ltp": l or None, "product": pr, "est_value": value, "est_charges": ch}
    return {"ticket": t, "flags": flags, "placed": False,
            "confirm_text": f"{sd.upper()} {q} x {sym} {ot.upper()}" + (f" @ {p:g}" if p else "") + (f" (~Rs {value:,.0f})" if value else ""),
            "charges_note": None if ch else "Charges: dar diye nahi gaye, isliye nahi nikaale.",
            "not_checked": "Bhaav ki sachchai, circuit limit, margin / funds, market ke ghante: broker ka system jaanchta hai.",
            "decider": "Yeh sirf order ki taiyaar parchi hai. Bhejna aapke confirm tap par, broker ke official API se hi; yahan kuch nahi bheja gaya. Kharidne-bechne ki salah yeh nahi deta."}


def drift(holdings: list[dict], targets: dict | None = None, tolerance_pct: Any = 5, max_single_pct: Any = None, max_group_pct: Any = None,
          margin: dict | None = None, margin_alert_pct: Any = 80) -> dict[str, Any]:
    if not holdings:
        raise ValueError("holdings rows do: symbol, qty, price (aur chaahein to group).")
    rows, total = [], 0.0
    for h in holdings[:2000]:
        v = _f(h.get("qty"), "qty") * _f(h.get("price"), "price")
        rows.append({"symbol": str(h.get("symbol") or "?").upper(), "group": str(h.get("group") or h.get("sector") or ""), "value": round(v, 2)})
        total += v
    if total <= 0:
        raise ValueError("Portfolio ki kul keemat 0 hai.")
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
            alerts.append(f"{r['symbol']} {r['weight_pct']}% hai, mandate ki seema {ms:g}%.")
    for g, w in groups.items():
        if mg is not None and w > mg:
            alerts.append(f"Group '{g}' {w:.1f}% hai, mandate ki seema {mg:g}%.")
    drifts, prop = [], []
    tol = _f(tolerance_pct)
    for k, tgt in (targets or {}).items():
        cur = next((r["weight_pct"] for r in rows if r["symbol"] == k.upper()), groups.get(k, 0.0))
        d = round(cur - _f(tgt), 2)
        drifts.append({"name": k, "current_pct": round(cur, 2), "target_pct": _f(tgt), "drift_pct": d, "outside_tolerance": abs(d) > tol})
        if abs(d) > tol:
            prop.append({"name": k, "move_value": round(-d * total / 100.0, 2), "note": "Prastaav hai, order nahi: portfolio manager tay karega."})
    mg_out = None
    if margin:
        used, avail = _f(margin.get("used")), _f(margin.get("available"))
        util = round(100 * used / (used + avail), 1) if used + avail else None
        mg_out = {"utilisation_pct": util, "alert": util is not None and util >= _f(margin_alert_pct)}
        if mg_out["alert"]:
            alerts.append(f"Margin istemal {util}%, aapka alert {margin_alert_pct}% par tha.")
    return {"total_value": round(total, 2), "weights": sorted(rows, key=lambda r: -r["weight_pct"]), "groups": {k: round(v, 2) for k, v in groups.items()},
            "drift": drifts, "alerts": alerts, "proposals": prop, "margin": mg_out,
            "not_checked": "Live bhaav, liquidity, tax asar, mandate ke baaki niyam.",
            "decider": "Rebalance ka faisla portfolio manager / niveshak ka hai; compliance pehle jaanchta hai. Yahan koi trade nahi hua."}
