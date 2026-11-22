"""F10 of docs/FINANCE_GLOBAL_PLAN.md - Investments & Wealth (employee 9, the parts F7 did not build; tool `investments_desk`), for a
person up to a fund administrator, any country.

  lots         capital gains from her buys and sells, matched by HER country's method:
                 GB  same day, then the next 30 days, then the Section 104 pool (average cost)
                 US  first in, first out; a loss with the same shares bought 30 days before or after is a wash sale: the loss is
                     not allowed now, it is added to the cost of the replacement shares and their holding period carries over;
                     long term = held more than one year
                 IN  first in, first out; long term = held more than 12 months (listed shares)
                 CA  average cost (adjusted cost base); a superficial loss (the same shares bought 30 days before or after and still
                     held 30 days after) is denied in the share of the shares still held and added to the cost base
                 AU  first in, first out; held at least 12 months = the discount may apply
                 DE  first in, first out
               Every method and holding period is Hoola's from memory (not confirmed - check this); she can name her own method.
               The gains are worked out; the TAX on them is not (it needs her rate and allowances - D3 of the plan).
  statement    holdings read into value, weights, allocation by class, unrealised gain, positions over HER concentration limit.
  fees         what yearly charges cost over the years, at the return SHE assumes (Hoola never assumes a return).
  harvest      unrealised losses she could realise, each with the wash / superficial window warning from her recent buys.
  derivatives  the reality check on an option or future: the most she can lose, the most she can gain, the break-even, and what a
               1% move does to a future or to her margin. No view on the market.
  scam         an offer read for the signs of investment fraud, and the firm checked against the register entries SHE pastes.
  retirement   a pot drawn down year by year at her withdrawal, return and inflation assumptions: the year it runs out.
  nav_check    a fund's NAV per unit worked out from its assets, liabilities and units, against the NAV reported.
  methods      the country table.

Hoola never places, changes or cancels an order and never says what to buy or sell. Not investment advice."""
from __future__ import annotations

import re
from collections import defaultdict
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from .. import laws as L


class InvestError(ValueError):
    pass


NOT_CONFIRMED = " (from memory - not confirmed, check this)"
NEVER = "Hoola never places, changes or cancels an order: you do, with your broker."
ZERO = Decimal(0)

METHODS: dict[str, dict[str, Any]] = {
    "GB": {"method": "uk_share_id", "name": "same day, then the next 30 days, then the Section 104 pool", "term": None},
    "US": {"method": "fifo", "name": "first in, first out, with the 30-day wash-sale rule", "wash_days": 30, "term": "more than 1 year"},
    "IN": {"method": "fifo", "name": "first in, first out", "term": "more than 12 months"},
    "CA": {"method": "average", "name": "average cost (adjusted cost base), with the 30-day superficial-loss rule", "superficial_days": 30,
           "term": None},
    "AU": {"method": "fifo", "name": "first in, first out; the discount may apply when held at least 12 months", "term": "at least 12 months"},
    "DE": {"method": "fifo", "name": "first in, first out", "term": None},
}
TERM_MONTHS = {"more than 1 year": 12, "more than 12 months": 12, "at least 12 months": 12}


def _n(v: Any, what: str, lo: float | None = None) -> Decimal:
    try:
        x = Decimal(str(v).replace(",", "").strip())
    except Exception:
        raise InvestError(f"{what}: a number.")
    if not x.is_finite():
        raise InvestError(f"{what}: a number.")
    if lo is not None and x < Decimal(str(lo)):
        raise InvestError(f"{what}: not below {lo}.")
    return x


def _d(s: Any, what: str) -> date:
    try:
        return date.fromisoformat(str(s)[:10])
    except ValueError:
        raise InvestError(f"{what}: a date as YYYY-MM-DD.")


def money(x: Decimal) -> float:
    return float(x.quantize(Decimal("0.01"), ROUND_HALF_UP))


def _months_after(d: date, m: int) -> date:
    y, mo = divmod(d.month - 1 + m, 12)
    y, mo = d.year + y, mo + 1
    for day in (d.day, 30, 29, 28):
        try:
            return date(y, mo, day)
        except ValueError:
            continue
    raise InvestError("date")


def _term(country: str, bought: date, sold: date) -> str | None:
    t = METHODS.get(country, {}).get("term")
    if not t:
        return None
    return "long" if sold > _months_after(bought, TERM_MONTHS[t]) else "short"


# ---- tax lots ----------------------------------------------------------------------------------------------------------------

def _trades(a: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    rows = a.get("trades") or []
    if not isinstance(rows, list) or not rows:
        raise InvestError("trades: [{date, side buy|sell, qty, price, fees, symbol}].")
    by: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for i, t in enumerate(rows):
        side = str(t.get("side") or "").lower()
        if side not in ("buy", "sell"):
            raise InvestError(f"trades[{i}].side: buy | sell.")
        qty = _n(t.get("qty"), f"trades[{i}].qty")
        if qty <= 0:
            raise InvestError(f"trades[{i}].qty: more than 0.")
        by[str(t.get("symbol") or "-").upper()].append({
            "i": i, "date": _d(t.get("date"), f"trades[{i}].date"), "side": side, "qty": qty,
            "price": _n(t.get("price"), f"trades[{i}].price", 0), "fees": _n(t.get("fees") or 0, f"trades[{i}].fees", 0)})
    for s in by.values():
        s.sort(key=lambda t: (t["date"], 0 if t["side"] == "buy" else 1, t["i"]))
    return by


def _cost(t: dict[str, Any]) -> Decimal:
    return t["qty"] * t["price"] + t["fees"]


def _proceeds(t: dict[str, Any]) -> Decimal:
    return t["qty"] * t["price"] - t["fees"]


def _fifo(sym: str, ts: list[dict[str, Any]], country: str, wash_days: int) -> dict[str, Any]:
    lots: list[dict[str, Any]] = []          # open lots: qty, cost, date (holding-period date), bought (real date), washable
    pending: dict[int, list[tuple[Decimal, Decimal, int]]] = defaultdict(list)   # future buy -> (qty, extra cost, days carried)
    future_free = {t["i"]: t["qty"] for t in ts if t["side"] == "buy"}           # replacement capacity left on each buy
    disposals, disallowed_total = [], ZERO
    for j, t in enumerate(ts):
        if t["side"] == "buy":
            per = _cost(t) / t["qty"]
            left = t["qty"]
            for q, extra, carry in pending.pop(t["i"], []):
                lots.append({"qty": q, "cost": per * q + extra, "date": t["date"] - timedelta(days=carry), "bought": t["date"],
                             "free": ZERO, "buy": t["i"]})
                left -= q
            if left > 0:
                lots.append({"qty": left, "cost": _cost(t) if left == t["qty"] else per * left, "date": t["date"], "bought": t["date"], "free": left, "buy": t["i"]})
            continue
        need, take = t["qty"], []
        while need > 0:
            if not lots:
                raise InvestError(f"{sym}: sold {money(t['qty'])} on {t['date']} but held fewer.")
            lot = lots[0]
            q = min(need, lot["qty"])
            c = lot["cost"] * q / lot["qty"]
            take.append({"qty": q, "cost": c, "date": lot["date"]})
            free_used = min(lot["free"], q)       # sold shares are never their own replacement
            lot["free"] -= free_used
            lot["qty"] -= q
            lot["cost"] -= c
            need -= q
            if lot["qty"] <= 0:
                lots.pop(0)
        per_proceeds = _proceeds(t) / t["qty"]
        parts, dis_sum = [], ZERO
        for p in take:
            gain = per_proceeds * p["qty"] - p["cost"]
            part = {"qty": float(p["qty"]), "acquired": p["date"].isoformat(), "cost": money(p["cost"]),
                    "proceeds": money(per_proceeds * p["qty"]), "gain": money(gain), "days_held": (t["date"] - p["date"]).days,
                    "term": _term(country, p["date"], t["date"]), "disallowed": 0.0}
            if gain < 0 and wash_days:
                lo, hi = t["date"] - timedelta(days=wash_days), t["date"] + timedelta(days=wash_days)
                loss_per = -gain / p["qty"]
                want, carry = p["qty"], (t["date"] - p["date"]).days
                dis = ZERO
                for lot in list(lots):                  # replacement shares already held, bought inside the window
                    if want <= 0:
                        break
                    if lot["free"] > 0 and lo <= lot["bought"] <= hi:
                        q = min(want, lot["free"])
                        share = lot["cost"] * q / lot["qty"]
                        k = lots.index(lot)
                        rest = {**lot, "qty": lot["qty"] - q, "cost": lot["cost"] - share, "free": lot["free"] - q}
                        new = {**lot, "qty": q, "cost": share + loss_per * q, "date": lot["date"] - timedelta(days=carry), "free": ZERO}
                        lots[k:k + 1] = [x for x in (new, rest) if x["qty"] > 0]
                        future_free[lot["buy"]] = future_free.get(lot["buy"], ZERO) - q
                        dis += loss_per * q
                        want -= q
                for f in ts[j + 1:]:                    # replacement shares bought after the sale, inside the window
                    if want <= 0 or f["date"] > hi:
                        break
                    if f["side"] == "buy" and future_free.get(f["i"], ZERO) > 0:
                        q = min(want, future_free[f["i"]])
                        pending[f["i"]].append((q, loss_per * q, carry))
                        future_free[f["i"]] -= q
                        dis += loss_per * q
                        want -= q
                if dis > 0:
                    part["disallowed"] = money(dis)
                    part["gain"] = money(gain + dis)
                    disallowed_total += dis
                    dis_sum += dis
            parts.append(part)
        disposals.append({"symbol": sym, "date": t["date"].isoformat(), "qty": float(t["qty"]), "proceeds": money(_proceeds(t)),
                          "cost": money(sum((p["cost"] for p in take), ZERO)),
                          "gain": money(_proceeds(t) - sum((p["cost"] for p in take), ZERO) + dis_sum), "disallowed": money(dis_sum),
                          "parts": parts})
    left_q = sum((x["qty"] for x in lots), ZERO)
    return {"disposals": disposals, "holding": {"symbol": sym, "qty": float(left_q), "cost": money(sum((x["cost"] for x in lots), ZERO)),
                                                "lots": [{"qty": float(x["qty"]), "cost": money(x["cost"]), "held_from": x["date"].isoformat()}
                                                         for x in lots]},
            "disallowed": disallowed_total}


def _held_on(ts: list[dict[str, Any]], d: date) -> Decimal:
    return sum((t["qty"] if t["side"] == "buy" else -t["qty"] for t in ts if t["date"] <= d), ZERO)


def _average(sym: str, ts: list[dict[str, Any]], country: str, sup_days: int) -> dict[str, Any]:
    qty, cost, pending_add = ZERO, ZERO, ZERO
    disposals, disallowed_total = [], ZERO
    for t in ts:
        if t["side"] == "buy":
            qty += t["qty"]
            cost += _cost(t) + pending_add
            pending_add = ZERO
            continue
        if t["qty"] > qty:
            raise InvestError(f"{sym}: sold {money(t['qty'])} on {t['date']} but held fewer.")
        c = cost * t["qty"] / qty
        qty -= t["qty"]
        cost -= c
        gain = _proceeds(t) - c
        dis = ZERO
        if gain < 0 and sup_days:
            lo, hi = t["date"] - timedelta(days=sup_days), t["date"] + timedelta(days=sup_days)
            bought = sum((b["qty"] for b in ts if b["side"] == "buy" and lo <= b["date"] <= hi), ZERO)
            held = _held_on(ts, hi)
            q = min(t["qty"], bought, max(held, ZERO))
            if q > 0:
                dis = -gain * q / t["qty"]
                if qty > 0:
                    cost += dis
                else:
                    pending_add += dis
                disallowed_total += dis
        disposals.append({"symbol": sym, "date": t["date"].isoformat(), "qty": float(t["qty"]), "proceeds": money(_proceeds(t)),
                          "cost": money(c), "gain": money(gain + dis), "disallowed": money(dis),
                          "average_cost": money(c / t["qty"]) if t["qty"] else 0.0})
    return {"disposals": disposals, "holding": {"symbol": sym, "qty": float(qty), "cost": money(cost)}, "disallowed": disallowed_total}


def _uk(sym: str, ts: list[dict[str, Any]]) -> dict[str, Any]:
    buys = [dict(t, left=t["qty"]) for t in ts if t["side"] == "buy"]
    sells = [dict(t, left=t["qty"], parts=[]) for t in ts if t["side"] == "sell"]
    per = {b["i"]: _cost(b) / b["qty"] for b in buys}
    for s in sells:                                     # 1 the same day
        for b in buys:
            if s["left"] > 0 and b["left"] > 0 and b["date"] == s["date"]:
                q = min(s["left"], b["left"])
                s["parts"].append({"rule": "same day", "qty": q, "cost": per[b["i"]] * q, "acquired": b["date"]})
                s["left"] -= q
                b["left"] -= q
    for s in sells:                                     # 2 the next 30 days, earlier disposals first, earlier buys first
        for b in buys:
            if s["left"] > 0 and b["left"] > 0 and s["date"] < b["date"] <= s["date"] + timedelta(days=30):
                q = min(s["left"], b["left"])
                s["parts"].append({"rule": "30 days", "qty": q, "cost": per[b["i"]] * q, "acquired": b["date"]})
                s["left"] -= q
                b["left"] -= q
    pool_q, pool_c = ZERO, ZERO                          # 3 the Section 104 pool, in date order
    events = sorted([("b", b) for b in buys] + [("s", s) for s in sells], key=lambda e: (e[1]["date"], 0 if e[0] == "b" else 1, e[1]["i"]))
    for kind, e in events:
        if kind == "b":
            pool_q += e["left"]
            pool_c += per[e["i"]] * e["left"]
        elif e["left"] > 0:
            if e["left"] > pool_q:
                raise InvestError(f"{sym}: sold {money(e['qty'])} on {e['date']} but held fewer.")
            c = pool_c * e["left"] / pool_q
            e["parts"].append({"rule": "Section 104 pool", "qty": e["left"], "cost": c, "acquired": None})
            pool_q -= e["left"]
            pool_c -= c
            e["left"] = ZERO
    disposals = []
    for s in sells:
        pp = _proceeds(s) / s["qty"]
        parts = [{"rule": p["rule"], "qty": float(p["qty"]), "cost": money(p["cost"]), "proceeds": money(pp * p["qty"]),
                  "gain": money(pp * p["qty"] - p["cost"]), "acquired": p["acquired"].isoformat() if p["acquired"] else None}
                 for p in s["parts"]]
        cost = sum((p["cost"] for p in s["parts"]), ZERO)
        disposals.append({"symbol": sym, "date": s["date"].isoformat(), "qty": float(s["qty"]), "proceeds": money(_proceeds(s)),
                          "cost": money(cost), "gain": money(_proceeds(s) - cost), "disallowed": 0.0, "parts": parts})
    return {"disposals": disposals, "holding": {"symbol": sym, "qty": float(pool_q), "cost": money(pool_c)}, "disallowed": ZERO}


def lots(a: dict[str, Any]) -> dict[str, Any]:
    country = str(a.get("country") or "").upper()
    m = dict(METHODS.get(country) or {})
    method = str(a.get("method") or m.get("method") or "")
    if method not in ("fifo", "average", "uk_share_id"):
        raise InvestError("country: " + ", ".join(METHODS) + " - or method: fifo | average | uk_share_id (yours).")
    rule_days = a.get("rule_days")
    wash = int(rule_days) if rule_days is not None else int(m.get("wash_days") or 0)
    sup = int(rule_days) if rule_days is not None else int(m.get("superficial_days") or 0)
    out_d, holds, dis_total = [], [], ZERO
    for sym, ts in sorted(_trades(a).items()):
        if method == "uk_share_id":
            r = _uk(sym, ts)
        elif method == "average":
            r = _average(sym, ts, country, sup)
        else:
            r = _fifo(sym, ts, country, wash)
        out_d += r["disposals"]
        holds.append(r["holding"])
        dis_total += r["disallowed"]
    out_d.sort(key=lambda x: (x["date"], x["symbol"]))
    gains = sum((Decimal(str(d["gain"])) for d in out_d if d["gain"] > 0), ZERO)
    losses = sum((Decimal(str(d["gain"])) for d in out_d if d["gain"] < 0), ZERO)
    by_term: dict[str, Decimal] = defaultdict(lambda: ZERO)
    for d in out_d:
        for p in d.get("parts") or []:
            if p.get("term"):
                by_term[p["term"]] += Decimal(str(p["gain"]))
    src = "your method" if a.get("method") else (m.get("name", "") + NOT_CONFIRMED)
    return {"country": country or None, "method": method, "method_from": src, "disposals": out_d, "holdings": holds,
            "gains": money(gains), "losses": money(losses), "net": money(gains + losses), "disallowed_losses": money(dis_total),
            "by_term": {k: money(v) for k, v in by_term.items()},
            "tax": "The tax on these gains is not worked out here: it needs your rate and allowances."}


# ---- the rest ----------------------------------------------------------------------------------------------------------------

def statement(a: dict[str, Any]) -> dict[str, Any]:
    rows = a.get("holdings") or []
    if not rows:
        raise InvestError("holdings: [{symbol, qty, price, cost, asset_class}].")
    hs, total = [], ZERO
    for i, h in enumerate(rows):
        v = _n(h.get("qty"), f"holdings[{i}].qty") * _n(h.get("price"), f"holdings[{i}].price", 0)
        c = _n(h["cost"], f"holdings[{i}].cost", 0) if h.get("cost") is not None else None
        hs.append({"symbol": str(h.get("symbol") or f"#{i}"), "class": str(h.get("asset_class") or "unknown"), "value": v, "cost": c})
        total += v
    if total <= 0:
        raise InvestError("holdings: the total value is 0.")
    lim = _n(a["max_pct"], "max_pct", 0) if a.get("max_pct") is not None else None
    by_class: dict[str, Decimal] = defaultdict(lambda: ZERO)
    out = []
    for h in sorted(hs, key=lambda h: -h["value"]):
        w = h["value"] / total * 100
        by_class[h["class"]] += h["value"]
        out.append({"symbol": h["symbol"], "class": h["class"], "value": money(h["value"]), "weight_pct": money(w),
                    "unrealised": money(h["value"] - h["cost"]) if h["cost"] is not None else None,
                    "over_limit": bool(lim is not None and w > lim)})
    return {"total": money(total), "holdings": out, "allocation": {k: money(v / total * 100) for k, v in sorted(by_class.items())},
            "over_your_limit": [h["symbol"] for h in out if h["over_limit"]],
            "limit": float(lim) if lim is not None else "set max_pct (your concentration limit) to flag positions",
            "unrealised": money(sum((h["value"] - h["cost"] for h in hs if h["cost"] is not None), ZERO))}


def fees(a: dict[str, Any]) -> dict[str, Any]:
    if a.get("return_pct") is None:
        raise InvestError("return_pct: the yearly return YOU assume (Hoola never assumes one).")
    amt = _n(a.get("amount"), "amount", 0)
    years = int(_n(a.get("years"), "years", 1))
    r = _n(a.get("return_pct"), "return_pct") / 100
    fee = sum((_n(a.get(k) or 0, k, 0) for k in ("fee_pct", "platform_pct")), ZERO) / 100
    entry = _n(a.get("entry_pct") or 0, "entry_pct", 0) / 100
    gross, net, rows = amt, amt * (1 - entry), []
    for y in range(1, years + 1):
        gross *= 1 + r
        net *= (1 + r) * (1 - fee)
        rows.append({"year": y, "without_fees": money(gross), "with_fees": money(net)})
    return {"end_without_fees": money(gross), "end_with_fees": money(net), "fees_cost": money(gross - net),
            "share_lost_pct": money((gross - net) / gross * 100) if gross else 0.0, "years": rows,
            "assumed": f"{float(r * 100)}% a year, your assumption"}


def harvest(a: dict[str, Any]) -> dict[str, Any]:
    country = str(a.get("country") or "").upper()
    days = int(METHODS.get(country, {}).get("wash_days") or METHODS.get(country, {}).get("superficial_days") or a.get("rule_days") or 0)
    today = _d(a.get("today") or date.today().isoformat(), "today")
    recent: dict[str, list[date]] = defaultdict(list)
    for b in a.get("recent_buys") or []:
        recent[str(b.get("symbol") or "").upper()].append(_d(b.get("date"), "recent_buys.date"))
    out = []
    for i, h in enumerate(a.get("holdings") or []):
        sym = str(h.get("symbol") or f"#{i}").upper()
        v = _n(h.get("qty"), f"holdings[{i}].qty") * _n(h.get("price"), f"holdings[{i}].price", 0)
        loss = v - _n(h.get("cost"), f"holdings[{i}].cost", 0)
        if loss >= 0:
            continue
        near = [d.isoformat() for d in recent[sym] if days and abs((today - d).days) <= days]
        out.append({"symbol": sym, "unrealised_loss": money(loss),
                    "warning": (f"you bought {sym} on {', '.join(near)}: inside the {days}-day rule, the loss may not count"
                                + NOT_CONFIRMED) if near else (
                        f"buying {sym} again within {days} days (before or after) may make the loss not count" + NOT_CONFIRMED if days else "")})
    out.sort(key=lambda x: x["unrealised_loss"])
    return {"losses": out, "total": money(sum((Decimal(str(x["unrealised_loss"])) for x in out), ZERO)), "never": NEVER,
            "says": "This is a list to look at, not a plan to sell."}


def derivatives(a: dict[str, Any]) -> dict[str, Any]:
    out = []
    for i, p in enumerate(a.get("positions") or []):
        kind = str(p.get("type") or "").lower()
        side = str(p.get("side") or "long").lower()
        mult = _n(p.get("multiplier") or 1, f"positions[{i}].multiplier", 0)
        qty = _n(p.get("qty") or 1, f"positions[{i}].qty", 0) * mult
        if kind in ("call", "put"):
            k = _n(p.get("strike"), f"positions[{i}].strike", 0)
            prem = _n(p.get("premium"), f"positions[{i}].premium", 0)
            be = k + prem if kind == "call" else k - prem
            if side == "long":
                worst, best = -prem * qty, ("unlimited" if kind == "call" else money((k - prem) * qty))
            else:
                worst, best = ("unlimited" if kind == "call" else -(k - prem) * qty), money(prem * qty)
            out.append({"position": i, "type": kind, "side": side, "break_even": money(be),
                        "most_you_can_lose": worst if isinstance(worst, str) else money(worst), "most_you_can_gain": best,
                        "says": "A short option can lose far more than the premium it brings in." if side == "short" else
                        "If the price is not past the break-even at expiry, the whole premium is lost."})
        elif kind == "future":
            px = _n(p.get("price"), f"positions[{i}].price", 0)
            notional = px * qty
            margin = _n(p["margin"], f"positions[{i}].margin", 0) if p.get("margin") is not None else None
            one = notional / 100
            out.append({"position": i, "type": kind, "side": side, "notional": money(notional), "per_1pct_move": money(one),
                        "leverage": money(notional / margin) if margin else None,
                        "move_that_wipes_the_margin_pct": money(margin / notional * 100) if margin and notional else None,
                        "most_you_can_lose": "more than your margin" if side == "short" or margin else "the whole notional"})
        else:
            raise InvestError(f"positions[{i}].type: call | put | future.")
    trades = a.get("results") or []
    stats = None
    if trades:
        pnl = [_n(x, "results") for x in trades]
        stats = {"trades": len(pnl), "losing": sum(1 for x in pnl if x < 0), "losing_pct": money(Decimal(sum(1 for x in pnl if x < 0)) / len(pnl) * 100),
                 "net": money(sum(pnl, ZERO))}
    return {"positions": out, "your_results": stats, "never": NEVER}


_SCAM = [
    (r"\bguarantee[ds]?\b", "a guaranteed return: real investments can fall"),
    (r"\b(\d{2,3})\s?%\s*(a|per|every)\s*(month|week|day)\b", "a very high return per month / week / day"),
    (r"\b(risk[- ]free|no risk|zero risk)\b", "\"no risk\" claims"),
    (r"\b(today only|act now|limited (slots|time)|last chance|hurry)\b", "pressure to decide now"),
    (r"\b(recruit|refer|bring) (\w+ )?(friends|members|people)\b", "pays for bringing in others"),
    (r"\b(crypto|forex|bitcoin|binary option)s?\b", "crypto / forex / binary options, common in these frauds"),
    (r"\b(whatsapp|telegram) group\b", "an invitation through a chat group"),
    (r"\b(send|transfer) (money|funds) to (my|a personal|this) (account|wallet|upi)\b", "money to a personal account or wallet"),
    (r"\b(secret|insider|exclusive) (tip|strategy|information)\b", "secret / insider tips"),
    (r"\b(withdrawal|unlock) fee\b", "a fee to take your own money out"),
]
REGISTERS = {"GB": "the FCA Financial Services Register", "US": "SEC IAPD / FINRA BrokerCheck", "IN": "the SEBI intermediary list",
             "AU": "ASIC Professional Registers", "CA": "the CSA National Registration Search", "DE": "the BaFin company database",
             "SG": "the MAS Financial Institutions Directory", "AE": "the SCA / DFSA public register", "IE": "the Central Bank register"}


def scam(a: dict[str, Any]) -> dict[str, Any]:
    text = str(a.get("text") or "")
    firm = str(a.get("firm") or "").strip()
    if not text and not firm:
        raise InvestError("text: the offer; firm: who is offering it.")
    flags = [why for rx, why in _SCAM if re.search(rx, text, re.I)]
    reg = a.get("register")
    found = None
    if firm and isinstance(reg, list):
        key = re.sub(r"[^a-z0-9]", "", firm.lower())
        found = any(re.sub(r"[^a-z0-9]", "", str(r.get("name") if isinstance(r, dict) else r).lower()) == key for r in reg)
        if not found:
            flags.append(f"{firm} is not in the register entries you pasted")
    country = str(a.get("country") or "").upper()
    return {"flags": flags, "level": "high" if len(flags) >= 3 else "some" if flags else "none found",
            "on_your_register": found, "check_on": (REGISTERS.get(country, "your regulator's public register") + NOT_CONFIRMED),
            "says": "None found is not a clean bill: check the firm on the regulator's own register before paying anything."}


def retirement(a: dict[str, Any]) -> dict[str, Any]:
    for k in ("return_pct", "inflation_pct"):
        if a.get(k) is None:
            raise InvestError(f"{k}: your assumption (Hoola never assumes one).")
    pot = _n(a.get("pot"), "pot", 0)
    draw = _n(a.get("withdraw"), "withdraw", 0)
    r, inf = _n(a["return_pct"], "return_pct") / 100, _n(a["inflation_pct"], "inflation_pct") / 100
    years = int(_n(a.get("years") or 40, "years", 1))
    rows, runs_out = [], None
    for y in range(1, years + 1):
        take = min(draw, pot)
        pot = (pot - take) * (1 + r)
        rows.append({"year": y, "withdrawn": money(take), "left": money(pot)})
        if pot <= 0 and runs_out is None:
            runs_out = y
            break
        draw *= 1 + inf
    return {"runs_out_in_year": runs_out, "years": rows, "left_at_end": money(pot),
            "assumed": f"{float(r * 100)}% return, {float(inf * 100)}% inflation, your assumptions; real returns vary year to year"}


def nav_check(a: dict[str, Any]) -> dict[str, Any]:
    assets = sum((_n(x.get("value"), "assets.value") for x in a.get("assets") or []), ZERO)
    liab = sum((_n(x.get("value"), "liabilities.value", 0) for x in a.get("liabilities") or []), ZERO)
    units = _n(a.get("units"), "units", 0)
    if units <= 0:
        raise InvestError("units: the units in issue.")
    nav = (assets - liab) / units
    out = {"assets": money(assets), "liabilities": money(liab), "net_assets": money(assets - liab), "nav_per_unit": float(nav.quantize(Decimal("0.0001"), ROUND_HALF_UP))}
    if a.get("reported_nav") is not None:
        rep = _n(a["reported_nav"], "reported_nav")
        diff = (rep - nav) / nav * 10000 if nav else ZERO
        tol = _n(a.get("tolerance_bp") or 1, "tolerance_bp", 0)
        out.update({"reported": float(rep), "difference_bp": float(diff.quantize(Decimal("0.01"))), "break": abs(diff) > tol,
                    "tolerance_bp": float(tol)})
    return out


ACTIONS = ("lots", "statement", "fees", "harvest", "derivatives", "scam", "retirement", "nav_check", "methods")
_ORDERISH = re.compile(r"order|execute|place|buy|sell|cancel|allocat|affirm|route|trade_now|submit|send|transfer|pay|switch|invest_now")


def run(tenant: str, action: str, a: dict[str, Any], actor: str = "owner") -> dict[str, Any]:
    a = dict(a)
    if _ORDERISH.search(str(action).lower()):
        raise L.Refused("place_order", NEVER)
    if action == "methods":
        out = {"methods": METHODS, "from": "Hoola's table" + NOT_CONFIRMED}
    elif action in ACTIONS:
        out = globals()[action](a)
    else:
        raise InvestError("action: " + ", ".join(ACTIONS))
    out.setdefault("not_advice", L.NOT_ADVICE)
    return out
