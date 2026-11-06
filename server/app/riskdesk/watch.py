"""#51 payment-velocity rule hits, #76 round-trip (wash-like) pattern flags. Rules and thresholds are HERS; every hit is evidence for an analyst, never a block or an accusation."""
from __future__ import annotations

import datetime as dt
from collections import defaultdict
from typing import Any


def _t(v: Any) -> dt.datetime:
    try:
        return dt.datetime.fromisoformat(str(v).replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        raise ValueError(f"Samay samajh nahi aaya: '{v}' (2026-11-05T14:30:00 jaisa likhiye).")


def _f(v: Any) -> float:
    try:
        return float(str(v).replace(",", ""))
    except (TypeError, ValueError):
        return 0.0


def velocity(txns: list[dict], window_minutes: Any = 10, max_count: Any = 5, max_amount: Any = None, shared_device_accounts: Any = 3) -> dict[str, Any]:
    if not txns:
        raise ValueError("txns rows do: account, ts, amount, device.")
    w = dt.timedelta(minutes=_f(window_minutes))
    by = defaultdict(list)
    dev = defaultdict(set)
    for x in txns[:50000]:
        by[str(x.get("account"))].append((_t(x.get("ts")), _f(x.get("amount"))))
        if x.get("device"):
            dev[str(x["device"])].add(str(x.get("account")))
    hits = []
    for acc, ev in by.items():
        ev.sort()
        i = 0
        best = None
        for j in range(len(ev)):
            while ev[j][0] - ev[i][0] > w:
                i += 1
            n, amt = j - i + 1, sum(a for _, a in ev[i:j + 1])
            over = n > _f(max_count) or (max_amount is not None and amt > _f(max_amount))
            if over and (best is None or n > best["count"]):
                best = {"account": acc, "rule": "velocity", "count": n, "amount": round(amt, 2), "from": ev[i][0].isoformat(), "to": ev[j][0].isoformat()}
        if best:
            hits.append(best)
    for d, accs in dev.items():
        if len(accs) >= int(_f(shared_device_accounts)):
            hits.append({"rule": "shared_device", "device": d, "accounts": sorted(accs), "count": len(accs)})
    return {"rule_hits": hits, "kind": "rule hit, not a verdict", "accounts_seen": len(by),
            "not_checked": "Customer ka asli vyavhaar, geo / device ki sachchai, pichhla itihaas.",
            "decider": "Block ya release fraud analyst karta hai; yahan koi transaction roka ya chhoda nahi gaya."}


def wash(trades: list[dict], qty_tolerance_pct: Any = 5, window_minutes: Any = 60) -> dict[str, Any]:
    if not trades:
        raise ValueError("trades rows do: client, symbol, side, qty, price, ts.")
    tol, w = _f(qty_tolerance_pct) / 100.0, dt.timedelta(minutes=_f(window_minutes))
    by = defaultdict(list)
    for x in trades[:50000]:
        by[(str(x.get("client")), str(x.get("symbol")).upper())].append((_t(x.get("ts")), str(x.get("side")).lower(), _f(x.get("qty")), _f(x.get("price"))))
    out = []
    for (cl, sym), ev in by.items():
        ev.sort()
        buys = [e for e in ev if e[1] == "buy"]
        sells = [e for e in ev if e[1] == "sell"]
        used = set()
        for b in buys:
            for k, s in enumerate(sells):
                if k in used or abs(s[0] - b[0]) > w or not b[2]:
                    continue
                if abs(s[2] - b[2]) <= tol * b[2]:
                    used.add(k)
                    out.append({"client": cl, "symbol": sym, "buy": {"ts": b[0].isoformat(), "qty": b[2], "price": b[3]}, "sell": {"ts": s[0].isoformat(), "qty": s[2], "price": s[3]},
                                "why": "Usi client ne usi share mein lagbhag barabar qty kharidi aur bechi, kam samay mein."})
                    break
    return {"round_trips": out, "kind": "pattern flag, not an accusation", "note": "Aksar yeh asli (hedge / arbitrage / square-off) hota hai; evidence ke liye hai.",
            "not_checked": "Counterparty, order book, intent: sirf trade rows dekhi gayi.",
            "decider": "Jaanch aur nirnay surveillance / compliance officer ka hai."}
