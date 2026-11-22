"""The F10 card: investments and markets (FINANCE_GLOBAL_PLAN phase F10).

TAX LOTS FOR 6 COUNTRIES' METHODS. For GB, US, IN, CA, AU and DE a fixed set of buys and sells whose answers were worked out by hand:
the UK same-day, 30-day and Section 104 matches; a US wash sale (the loss moved into the replacement shares, the holding period carried
over) and the one-year line; India's 12-month line; Canada's average cost and a superficial loss in the share still held; Australia's
12-month line; Germany's first in, first out. Then, for every country and every seed, random buys and sells checked on two laws that
hold whatever the method: each disposal's gain = proceeds - cost + any loss not allowed, and the cost used + the cost left = everything
paid + the losses moved into new shares. With the 30-day rules off, first-in-first-out and average cost are checked against a second,
separate implementation in this file.

RECONCILIATION BREAKS FOUND ON FIXED FILES. Her books and a custodian's file as CSV text: planted, a position the custodian does not
hold, one only the custodian holds, quantity breaks, a cash break and a currency only one side has; and traps that must NOT break - a
custodian position split over two lines, a zero line on our side with nothing on theirs. Trade confirmations with planted missing /
orphan / quantity / price / side breaks and a price inside the tolerance that must match. Settlement fails aged, the penalty worked out
by hand.

NO ORDER EVER PLACED. Every order-like action (place, buy, sell, execute, cancel, allocate, affirm, submit, send, route, transfer) is
refused by both desks and by the laws screen; neither desk can reach the network; nothing either desk returns says an order was placed.

    python -m app.fin.card_f10        prints the card; exit 1 if anything fails
"""
from __future__ import annotations

import inspect
import random
import sys
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from . import core, laws as L
from .desks import investments as IV
from .desks import markets as MK


def _t(d, side, qty, price, sym="X", fees=0):
    return {"date": d, "side": side, "qty": qty, "price": price, "fees": fees, "symbol": sym}


def _close(a: float, b: float, tol: float = 0.011) -> bool:
    return abs(float(a) - float(b)) <= tol


HAND: list[tuple[str, list[dict], dict[str, Any]]] = [
    ("GB", [_t("2025-01-01", "buy", 1000, 2), _t("2025-05-01", "buy", 500, 3), _t("2025-06-01", "sell", 700, 4),
            _t("2025-06-01", "buy", 200, 3.5), _t("2025-06-20", "buy", 100, 3.8)],
     {"gains": [786.67], "rules": [[("same day", 200, 700.0), ("30 days", 100, 380.0), ("Section 104 pool", 400, 933.33)]],
      "left": (1100, 2566.67)}),
    ("GB", [_t("2025-01-01", "buy", 100, 10), _t("2025-02-01", "sell", 100, 8), _t("2025-02-15", "buy", 100, 9),
            _t("2025-03-01", "sell", 100, 11)],      # bed and breakfasting: the first sale is matched with the buy 14 days later
     {"gains": [-100.0, 100.0], "left": (0, 0.0)}),
    ("US", [_t("2026-01-02", "buy", 100, 10), _t("2026-02-01", "sell", 100, 8), _t("2026-02-10", "buy", 100, 9),
            _t("2026-06-01", "sell", 100, 12)],
     {"gains": [0.0, 100.0], "disallowed": [200.0, 0.0], "days": [[30], [141]], "terms": [["short"], ["short"]], "left": (0, 0.0)}),
    ("US", [_t("2025-01-02", "buy", 10, 100), _t("2026-01-02", "sell", 5, 120), _t("2026-01-03", "sell", 5, 120)],
     {"gains": [100.0, 100.0], "terms": [["short"], ["long"]]}),
    ("US", [_t("2026-01-02", "buy", 100, 10), _t("2026-01-20", "buy", 40, 9), _t("2026-02-01", "sell", 100, 8),
            _t("2026-03-01", "sell", 40, 12)],     # 40 replacement shares bought before: 40 x 2 moved into them, 30 days carried
     {"gains": [-120.0, 40.0], "disallowed": [80.0, 0.0], "days": [[30], [70]], "left": (0, 0.0)}),
    ("IN", [_t("2025-03-01", "buy", 100, 50), _t("2025-09-01", "buy", 100, 60), _t("2026-03-02", "sell", 150, 70, fees=15)],
     {"gains": [2485.0], "parts": [[1990.0, 495.0]], "terms": [["long", "short"]], "by_term": {"long": 1990.0, "short": 495.0},
      "left": (50, 3000.0)}),
    ("CA", [_t("2026-01-02", "buy", 100, 10), _t("2026-02-01", "sell", 100, 8), _t("2026-02-10", "buy", 50, 9)],
     {"gains": [-100.0], "disallowed": [100.0], "left": (50, 550.0)}),
    ("CA", [_t("2025-01-02", "buy", 100, 10), _t("2025-03-01", "buy", 100, 20), _t("2025-06-01", "sell", 50, 18)],
     {"gains": [150.0], "left": (150, 2250.0)}),
    ("AU", [_t("2025-01-10", "buy", 200, 5), _t("2026-01-10", "sell", 100, 6), _t("2026-01-11", "sell", 100, 6)],
     {"gains": [100.0, 100.0], "terms": [["short"], ["long"]]}),
    ("DE", [_t("2025-01-02", "buy", 10, 100), _t("2025-02-02", "buy", 10, 200), _t("2025-03-02", "sell", 15, 150)],
     {"gains": [250.0], "left": (5, 1000.0)}),
]


def hand() -> dict[str, Any]:
    bad = []
    for n, (country, trades, want) in enumerate(HAND):
        try:
            r = IV.lots({"country": country, "trades": trades})
        except Exception as e:
            bad.append(f"{country} #{n}: {type(e).__name__}: {e}")
            continue
        ds = r["disposals"]
        if [d["gain"] for d in ds] != want["gains"]:
            bad.append(f"{country} #{n}: gains {[d['gain'] for d in ds]}, by hand {want['gains']}")
        if "disallowed" in want and [d["disallowed"] for d in ds] != want["disallowed"]:
            bad.append(f"{country} #{n}: losses not allowed {[d['disallowed'] for d in ds]}, by hand {want['disallowed']}")
        if "days" in want and [[p["days_held"] for p in d["parts"]] for d in ds] != want["days"]:
            bad.append(f"{country} #{n}: days held {[[p['days_held'] for p in d['parts']] for d in ds]}, by hand {want['days']}")
        if "terms" in want and [[p["term"] for p in d["parts"]] for d in ds] != want["terms"]:
            bad.append(f"{country} #{n}: terms {[[p['term'] for p in d['parts']] for d in ds]}, by hand {want['terms']}")
        if "parts" in want and [[p["gain"] for p in d["parts"]] for d in ds] != want["parts"]:
            bad.append(f"{country} #{n}: part gains differ from the hand answer")
        if "rules" in want and [[(p["rule"], p["qty"], p["cost"]) for p in d["parts"]] for d in ds] != want["rules"]:
            bad.append(f"{country} #{n}: UK matching {[[(p['rule'], p['qty'], p['cost']) for p in d['parts']] for d in ds]}")
        if "by_term" in want and r["by_term"] != want["by_term"]:
            bad.append(f"{country} #{n}: by term {r['by_term']}")
        if "left" in want:
            h = r["holdings"][0]
            if (h["qty"], h["cost"]) != want["left"]:
                bad.append(f"{country} #{n}: left {(h['qty'], h['cost'])}, by hand {want['left']}")
    return {"part": "tax lots by hand", "cases": len(HAND), "countries": sorted({c for c, _, _ in HAND}), "ok": not bad, "problems": bad}


def _ref_fifo(trades):
    lots, gains = [], []
    for t in sorted(trades, key=lambda t: (t["date"], 0 if t["side"] == "buy" else 1)):
        q, p, f = Decimal(str(t["qty"])), Decimal(str(t["price"])), Decimal(str(t["fees"]))
        if t["side"] == "buy":
            lots.append([q, q * p + f])
            continue
        cost, need = Decimal(0), q
        while need > 0:
            take = min(need, lots[0][0])
            c = lots[0][1] * take / lots[0][0]
            cost += c
            lots[0][0] -= take
            lots[0][1] -= c
            need -= take
            if lots[0][0] == 0:
                lots.pop(0)
        gains.append(float((q * p - f - cost).quantize(Decimal("0.01"), ROUND_HALF_UP)))
    return gains


def _ref_average(trades):
    q0, c0, gains = Decimal(0), Decimal(0), []
    for t in sorted(trades, key=lambda t: (t["date"], 0 if t["side"] == "buy" else 1)):
        q, p, f = Decimal(str(t["qty"])), Decimal(str(t["price"])), Decimal(str(t["fees"]))
        if t["side"] == "buy":
            q0, c0 = q0 + q, c0 + q * p + f
            continue
        c = c0 * q / q0
        q0, c0 = q0 - q, c0 - c
        gains.append(float((q * p - f - c).quantize(Decimal("0.01"), ROUND_HALF_UP)))
    return gains


def _random_trades(rnd: random.Random, n: int) -> list[dict]:
    d, held, out = date(2024, 1, 2), 0, []
    for _ in range(n):
        d += timedelta(days=rnd.choice([0, 1, 3, 7, 12, 20, 33, 45, 90, 200]))
        price = round(rnd.uniform(5, 50), 2)
        if held > 0 and rnd.random() < 0.45:
            q = rnd.randint(1, held)
            held -= q
            out.append(_t(d.isoformat(), "sell", q, price, fees=round(rnd.uniform(0, 5), 2)))
        else:
            q = rnd.randint(1, 120)
            held += q
            out.append(_t(d.isoformat(), "buy", q, price, fees=round(rnd.uniform(0, 5), 2)))
    return out


def laws_hold(seed: int) -> dict[str, Any]:
    rnd = random.Random(seed)
    bad, runs = [], 0
    for country in IV.METHODS:
        for k in range(6):
            trades = _random_trades(rnd, rnd.randint(6, 30))
            runs += 1
            r = IV.lots({"country": country, "trades": trades})
            paid = sum(Decimal(str(t["qty"])) * Decimal(str(t["price"])) + Decimal(str(t["fees"])) for t in trades if t["side"] == "buy")
            used = sum(Decimal(str(d["cost"])) for d in r["disposals"])
            left = Decimal(str(r["holdings"][0]["cost"]))
            moved = Decimal(str(r["disallowed_losses"]))
            n = len(r["disposals"]) + 1
            if abs((used + left) - (paid + moved)) > Decimal("0.011") * n:
                bad.append(f"{country} seed {seed}/{k}: cost used {used} + left {left} != paid {paid} + moved {moved}")
            for d in r["disposals"]:
                if not _close(d["gain"], d["proceeds"] - d["cost"] + d["disallowed"], 0.021):
                    bad.append(f"{country} seed {seed}/{k}: a disposal's gain is not proceeds - cost + not allowed")
                    break
            want_q = sum(t["qty"] if t["side"] == "buy" else -t["qty"] for t in trades)
            if r["holdings"][0]["qty"] != want_q:
                bad.append(f"{country} seed {seed}/{k}: {r['holdings'][0]['qty']} left, the trades leave {want_q}")
            m = IV.METHODS[country]["method"]
            if m in ("fifo", "average"):
                plain = IV.lots({"method": m, "trades": trades, "rule_days": 0})
                ref = _ref_fifo(trades) if m == "fifo" else _ref_average(trades)
                if [d["gain"] for d in plain["disposals"]] != ref:
                    bad.append(f"{country} seed {seed}/{k}: {m} gains differ from the second implementation")
    return {"part": "tax lots, laws on random trades", "runs": runs, "ok": not bad, "problems": bad[:10]}


# ---- reconciliation on fixed files ---------------------------------------------------------------------------------------------

def _csv(rows: list[tuple]) -> str:
    return "account,symbol,qty\n" + "\n".join(",".join(str(x) for x in r) for r in rows)


def reconciliation(seed: int) -> dict[str, Any]:
    rnd = random.Random(seed)
    accts = [f"A{k:03d}" for k in range(40)]
    syms = [f"S{k:02d}" for k in range(25)]
    book = {}
    for a in accts:
        for s in rnd.sample(syms, rnd.randint(3, 9)):
            book[(a, s)] = rnd.randint(1, 5000)
    keys = sorted(book)
    picks = rnd.sample(keys, 8)
    gone, qty_breaks, split = picks[0], picks[1:4], picks[4]
    extra = ("A999", "S77")
    cust = []
    for k in keys:
        if k == gone:
            continue
        q = book[k] + (rnd.choice([-1, 1]) * rnd.randint(1, 50) if k in qty_breaks else 0)
        if k == split:
            cust += [(k[0], k[1], q - 1), (k[0], k[1], 1)]        # a trap: two lines, the same total
        else:
            cust.append((k[0], k[1], q))
    cust.append((*extra, 300))
    ours = [(k[0], k[1], book[k]) for k in keys] + [("A998", "S88", 0)]   # a trap: a zero line on our side only
    want = {(gone[0], gone[1]): ("missing at the custodian", book[gone])}
    for k in qty_breaks:
        theirs = sum(q for a, s, q in cust if (a, s) == k)
        want[k] = ("quantity", book[k] - theirs)
    want[extra] = ("missing in our books", -300)
    cash_o = [{"account": "A000", "currency": "USD", "amount": 1000.00}, {"account": "A001", "currency": "EUR", "amount": 250.50}]
    cash_t = [{"account": "A000", "currency": "USD", "amount": 990.00}, {"account": "A001", "currency": "EUR", "amount": 250.50},
              {"account": "A001", "currency": "GBP", "amount": 12.00}]
    r = MK.recon({"internal_csv": _csv(ours), "custodian_csv": _csv(cust), "internal_cash": cash_o, "custodian_cash": cash_t})
    got = {(b["account"], b["symbol"]): (b["break"], b["difference"]) for b in r["breaks"]}
    bad = []
    if got != want:
        bad.append(f"breaks found {sorted(set(got) ^ set(want))} differ, or the differences do: {[(k, got.get(k), want.get(k)) for k in want if got.get(k) != want[k]][:3]}")
    cash = {(c["account"], c["currency"]): c["difference"] for c in r["cash_breaks"]}
    if cash != {("A000", "USD"): 10.0, ("A001", "GBP"): -12.0}:
        bad.append(f"cash breaks {cash}")
    if r["balanced"]:
        bad.append("an unbalanced file was called balanced")
    clean = MK.recon({"internal_csv": _csv([(k[0], k[1], book[k]) for k in keys]),
                      "custodian_csv": _csv([(k[0], k[1], book[k]) for k in reversed(keys)])})
    if not clean["balanced"]:
        bad.append("an identical file was not balanced")
    # confirmations
    trades, confs = [], []
    for k in range(30):
        t = {"id": f"T{k}", "side": rnd.choice(["buy", "sell"]), "symbol": rnd.choice(syms), "account": rnd.choice(accts),
             "qty": rnd.randint(1, 900), "price": round(rnd.uniform(10, 300), 4), "trade_date": "2026-09-01", "settle_date": "2026-09-03"}
        trades.append(t)
        confs.append(dict(t))
    confs[3]["qty"] += 5
    confs[7]["price"] = round(confs[7]["price"] + 0.05, 4)
    confs[9]["price"] = round(confs[9]["price"] + 0.004, 4)        # inside the tolerance: must match
    confs[12]["side"] = "sell" if confs[12]["side"] == "buy" else "buy"
    del confs[20]
    confs.append({**trades[0], "id": "X1"})
    c = MK.confirm({"trades": trades, "confirms": confs, "price_tolerance": 0.01})
    br = {b["id"]: sorted(x["field"] for x in b["differences"]) for b in c["breaks"]}
    if br != {"T3": ["qty"], "T7": ["price"], "T12": ["side"]}:
        bad.append(f"confirmation breaks {br}")
    if c["unconfirmed"] != ["T20"] or c["confirms_with_no_trade"] != ["X1"] or "T9" not in c["matched"] or c["affirmed"] is not False:
        bad.append("confirmations: unconfirmed / orphan / tolerance wrong")
    f = MK.fails({"today": "2026-09-15", "penalty_bp_per_day": 1, "settlements": [
        {"id": "F1", "value": 100000, "intended": "2026-09-14"}, {"id": "F2", "value": 50000, "intended": "2026-09-01"},
        {"id": "F3", "value": 70000, "intended": "2026-09-10", "settled": "yes"}, {"id": "F4", "value": 9000, "intended": "2026-09-15"}]})
    if [(x["id"], x["days_late"], x["penalty"]) for x in f["fails"]] != [("F2", 14, 70.0), ("F1", 1, 10.0)] or f["penalty"] != 80.0:
        bad.append(f"fails {[(x['id'], x['days_late'], x['penalty']) for x in f['fails']]}")
    return {"part": "reconciliation breaks", "positions": len(keys), "ok": not bad, "problems": bad}


# ---- no order ----------------------------------------------------------------------------------------------------------------

ORDER_WORDS = ("place_order", "buy", "sell", "execute_trade", "cancel_order", "allocate", "affirm", "submit_order", "send_order",
               "route_order", "transfer", "buy_order", "sell_order")


def no_order() -> dict[str, Any]:
    bad = []
    for desk, tool in ((IV, "investments_desk"), (MK, "markets_desk")):
        for w in ORDER_WORDS:
            try:
                core.run_tool("card_f10", "owner", tool, w, {}, lambda: desk.run("card_f10", w, {}))
                bad.append(f"{tool}.{w} was not refused")
            except L.Refused:
                pass
            except Exception as e:
                bad.append(f"{tool}.{w}: {type(e).__name__} instead of a refusal")
        src = inspect.getsource(desk)
        for lib in ("httpx", "requests", "urllib", "socket", "smtplib", "aiohttp"):
            if f"import {lib}" in src or f"from {lib}" in src:
                bad.append(f"{tool} can reach the network ({lib})")
    outs = [IV.run("card_f10", "lots", {"country": "US", "trades": HAND[2][1]}),
            MK.run("card_f10", "confirm", {"trades": [], "confirms": []})]
    for o in outs:
        if any(k in o and o[k] for k in ("placed", "order_id", "executed")):
            bad.append("a desk answer says an order was placed")
    return {"part": "no order placed", "tried": len(ORDER_WORDS) * 2, "ok": not bad, "problems": bad}


def run(seeds: int = 3) -> dict[str, Any]:
    rows = []
    for fn, arg in [(hand, None), (no_order, None)] + [(laws_hold, 300 + s) for s in range(seeds)] + \
                   [(reconciliation, 400 + s) for s in range(seeds)]:
        try:
            rows.append({**(fn() if arg is None else fn(arg)), "seed": arg})
        except Exception as e:      # a crash is a failed check, not a stopped card
            rows.append({"part": fn.__name__, "seed": arg, "ok": False, "problems": [f"{type(e).__name__}: {e}"]})
    return {"checks": len(rows), "passed": sum(r["ok"] for r in rows), "ok": all(r["ok"] for r in rows), "rows": rows,
            "countries": sorted(IV.METHODS)}


if __name__ == "__main__":
    r = run(int(sys.argv[1]) if len(sys.argv) > 1 else 3)
    for x in r["rows"]:
        if not x["ok"]:
            print("FAIL", x["part"], x["seed"], "; ".join(x["problems"][:5]))
    print(f"F10 card: {r['passed']}/{r['checks']} (tax lots for {', '.join(r['countries'])}; "
          f"{sum(x.get('runs', 0) for x in r['rows'])} random trade lists; "
          f"{sum(x.get('positions', 0) for x in r['rows'])} positions reconciled)")
    sys.exit(0 if r["ok"] else 1)
