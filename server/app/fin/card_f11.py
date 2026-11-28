"""The F11 card: community & inclusive finance, Islamic finance, digital assets (FINANCE_GLOBAL_PLAN phase F11).

SAVINGS-GROUP BOOKS IN 4 COUNTRIES BALANCE. A full cycle of meetings for a group in Kenya (VSLA, shares), Uganda (VSLA, shares, a
currency with no cents), India (SHG, amounts) and Mexico (caja de ahorro, amounts): savings, fines, the social fund, loans only from what
the box holds, repayments with interest first, expenses; the group's own count of the box at some meetings, with planted wrong counts.
The card keeps its own books meeting by meeting and checks: the cash in the box, every member's savings and what each still owes match;
the books balance (cash + loans out = opening + savings + interest + fines - expenses); exactly the planted wrong counts are found; the
share-out adds up to the cash to the cent and gives each member their share of the savings within one cent; a meeting that lends more
than the box holds, and a repayment of more than is owed, are refused.

ZAKAT ON A FIXED SET. Twelve cases worked out by hand on the usual method: nisab on gold and on silver, gold by purity, jewellery counted
or not by the school she names, debts due taken off, trade stock and money owed to her, long-term shares at the part her scholar counts,
a lunar year not yet passed, debts above the assets, exactly at the nisab. The set is written to be given to a scholar for review; until
a scholar has reviewed it the card says so.

CRYPTO GAINS MATCH. Buys, sells, swaps (a sale and a buy at the day's value), coins received as income and transfers between her own
wallets, matched in 6 countries' methods: the same history gives the same disposals, India does not set losses off, Germany exempts coins
held more than a year, the UK matches a buy-back within 30 days, Canada denies the superficial loss, the US has no wash-sale rule for
crypto. Then random histories checked on the cost and gain laws, and Bitcoin / Tron address checksums on real and changed addresses.

    python -m app.fin.card_f11        prints the card; exit 1 if anything fails
"""
from __future__ import annotations

import random
import sys
from collections import defaultdict
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from .desks import community as CM
from .desks import digital as DG

SCHOLAR_REVIEWED = False      # set True only once a named scholar has signed off the ZAKAT set below

GROUPS = {"KE": {"share": 100, "rate": (5, 10), "cents": True}, "UG": {"share": 2000, "rate": (5, 10), "cents": False},
          "IN": {"share": None, "rate": (1, 2), "cents": True}, "MX": {"share": None, "rate": (2, 4), "cents": True}}


def savings_groups(seed: int) -> dict[str, Any]:
    rnd = random.Random(seed)
    bad, meetings_n = [], 0
    for country, g in GROUPS.items():
        members = [f"{country}{k}" for k in range(rnd.randint(8, 25))]
        unit = Decimal(g["share"]) if g["share"] else None
        cash = Decimal(rnd.choice([0, 500, 1000])) * (100 if not g["cents"] else 1)
        opening = cash
        saved = {m: Decimal(0) for m in members}
        owed_p = defaultdict(Decimal)
        owed_i = defaultdict(Decimal)
        interest = fines = expenses = Decimal(0)
        meetings, planted = [], []
        n = rnd.randint(10, 24)
        for k in range(n):
            mt: dict[str, Any] = {"date": (date(2026, 1, 5) + timedelta(days=14 * k)).isoformat()}
            sv = {}
            for m in members:
                x = rnd.randint(0, 5) if unit else (Decimal(rnd.randint(0, 40)) * 25 if g["cents"] else Decimal(rnd.randint(0, 40)) * 1000)
                if x:
                    sv[m] = x
                    amt = Decimal(x) * unit if unit else Decimal(x)
                    saved[m] += amt
                    cash += amt
            mt["savings"] = {m: (int(v) if unit else float(v)) for m, v in sv.items()}
            fn = {m: (10 if g["cents"] else 1000) for m in rnd.sample(members, rnd.randint(0, 2))}
            mt["fines"] = fn
            for v in fn.values():
                cash += Decimal(v)
                fines += Decimal(v)
            rep = []
            last = k >= n - 2
            for m in [m for m in members if owed_p[m] + owed_i[m] > 0]:
                due = owed_p[m] + owed_i[m]
                if last or rnd.random() < 0.5:
                    pay = due if (last or rnd.random() < 0.5) else (due / 2).quantize(Decimal("0.01") if g["cents"] else Decimal(1))
                    rep.append({"member": m, "amount": float(pay)})
                    to_i = min(pay, owed_i[m])
                    owed_i[m] -= to_i
                    owed_p[m] -= pay - to_i
                    interest += to_i
                    cash += pay
            mt["repayments"] = rep
            if rnd.random() < 0.2:
                e = Decimal(rnd.choice([50, 120])) * (1 if g["cents"] else 100)
                if e <= cash:
                    mt["expenses"] = [{"what": "stationery", "amount": float(e)}]
                    cash -= e
                    expenses += e
            loans = []
            if not last:
                for m in rnd.sample(members, rnd.randint(0, 3)):
                    if owed_p[m] > 0:
                        continue
                    amt = (cash * Decimal(rnd.uniform(0.05, 0.3))).quantize(Decimal("1"))
                    if amt <= 0:
                        continue
                    rate, months = rnd.randint(*g["rate"]), rnd.randint(1, 3)
                    loans.append({"member": m, "amount": float(amt), "rate_pct": rate, "months": months})
                    owed_p[m] += amt
                    owed_i[m] += amt * rate / 100 * months
                    cash -= amt
            mt["loans"] = loans
            if rnd.random() < 0.4:
                wrong = rnd.random() < 0.3
                mt["counted"] = float(cash + (Decimal(rnd.choice([-50, 20, 5])) if wrong else 0))
                if wrong:
                    planted.append(mt["date"])
            meetings.append(mt)
        meetings_n += n
        r = CM.group({"country": country, "members": members, "share_value": g["share"], "opening_cash": float(opening),
                      "meetings": meetings, "share_out": True})
        q = lambda x: float(Decimal(x).quantize(Decimal("0.01"), ROUND_HALF_UP))  # noqa: E731
        if r["cash_box"] != q(cash):
            bad.append(f"{country}: cash {r['cash_box']}, by hand {q(cash)}")
        if r["savings"] != {m: q(v) for m, v in saved.items()}:
            bad.append(f"{country}: savings differ from the hand books")
        if r["owes"]:
            bad.append(f"{country}: loans left at the end {r['owes']}")
        if not r["balanced"]:
            bad.append(f"{country}: the books do not balance")
        if [x["meeting"] for x in r["count_mismatches"]] != planted:
            bad.append(f"{country}: wrong counts found {[x['meeting'] for x in r['count_mismatches']]}, planted {planted}")
        if r["totals"].get("interest", 0.0) != q(interest) or r["totals"].get("fines", 0.0) != q(fines):
            bad.append(f"{country}: interest / fines differ from the hand books")
        so = r.get("share_out") or {}
        if not so.get("possible"):
            bad.append(f"{country}: no share-out though every loan was repaid")
        else:
            cents = sum(round(v * 100) for v in so["per_member"].values())
            if cents != round(q(cash) * 100):
                bad.append(f"{country}: share-out adds to {cents / 100}, the box holds {q(cash)}")
            tot = sum(saved.values())
            for m in members:
                exact = cash * saved[m] / tot
                if abs(Decimal(str(so["per_member"][m])) - exact) > Decimal("0.0101"):
                    bad.append(f"{country}: {m} gets {so['per_member'][m]}, their share is {q(exact)}")
                    break
        for wrong, why, says in (({"loans": [{"member": members[0], "amount": float(cash) + 10 ** 9, "rate_pct": 1}]},
                                  "lends more than the box", "cannot lend"),
                                 ({"repayments": [{"member": members[0], "amount": 10 ** 9}]}, "repays more than owed", "but owes")):
            try:
                CM.group({"members": members, "share_value": g["share"], "opening_cash": float(opening), "meetings": meetings + [wrong]})
                bad.append(f"{country}: a meeting that {why} was accepted")
            except CM.CommunityError as e:
                if says not in str(e):
                    bad.append(f"{country}: a meeting that {why} was refused for another reason: {e}")
    # a part repayment pays the interest first: 1,000 lent at 10% for a month, 300 back -> 100 interest, 800 still lent
    p = CM.group({"members": ["A", "B"], "meetings": [{"savings": {"A": 1000, "B": 500}, "loans": [{"member": "B", "amount": 1000,
                  "rate_pct": 10, "months": 1}]}, {"repayments": [{"member": "B", "amount": 300}]}]})
    if (p["loans_outstanding"], p["interest_due"], p["totals"]["interest"], p["owes"]) != (800.0, 0.0, 100.0, {"B": 800.0}):
        bad.append(f"a part repayment: lent {p['loans_outstanding']}, interest due {p['interest_due']}, interest {p['totals']['interest']}")
    return {"part": "savings groups", "countries": sorted(GROUPS), "meetings": meetings_n, "ok": not bad, "problems": bad[:10]}


P = {"gold_price_per_gram": 80, "silver_price_per_gram": 1}
ZAKAT = [
    ({"nisab_basis": "silver", "cash": 1000}, 25.0),
    ({"nisab_basis": "gold", "cash": 1000}, 0.0),
    ({"nisab_basis": "gold", "cash": 5000, "gold": [{"grams": 30, "karat": 24}]}, 185.0),
    ({"nisab_basis": "silver", "cash": 500, "gold": [{"grams": 20, "karat": 18, "jewellery": True}], "school": "hanafi"}, 42.5),
    ({"nisab_basis": "silver", "cash": 500, "gold": [{"grams": 20, "karat": 18, "jewellery": True}], "school": "shafii"}, 0.0),
    ({"nisab_basis": "silver", "cash": 3000, "business_stock": 2000, "receivables": 500, "debts_due": 1500}, 100.0),
    ({"nisab_basis": "silver", "shares_longterm": 10000, "shares_longterm_pct": 25}, 62.5),
    ({"nisab_basis": "silver", "cash": 10000, "lunar_year_passed": False}, 0.0),
    ({"nisab_basis": "silver", "cash": 1000, "debts_due": 2000}, 0.0),
    ({"nisab_basis": "silver", "silver_grams": 700}, 17.5),
    ({"nisab_basis": "gold", "shares_trading": 4000, "bank": 6000}, 250.0),
    ({"nisab_basis": "silver", "cash": 595}, 14.88),
    ({"nisab_basis": "gold", "cash": 6900}, 172.5),          # above 85 g of gold at 80 a gram (6,800)
]


def zakat_set() -> dict[str, Any]:
    bad = []
    for k, (case, want) in enumerate(ZAKAT):
        r = CM.zakat({**P, "lunar_year_passed": True, **case})
        if r["zakat"] != want:
            bad.append(f"case {k + 1}: zakat {r['zakat']}, by hand {want}")
    try:
        CM.zakat({**P, "nisab_basis": "silver", "gold": [{"grams": 10, "jewellery": True}]})
        bad.append("jewellery with no school named was counted without asking")
    except CM.CommunityError:
        pass
    return {"part": "zakat set", "cases": len(ZAKAT), "ok": not bad, "problems": bad, "scholar_reviewed": SCHOLAR_REVIEWED}


def _ev(d, t, asset, qty, value, **x):
    return {"date": d, "type": t, "asset": asset, "qty": qty, "value": value, **x}


HISTORY = [_ev("2024-01-10", "buy", "BTC", 1, 40000), _ev("2024-06-01", "swap", "BTC", 0.5, 35000, get_asset="ETH", get_qty=10),
           _ev("2024-07-01", "income", "ETH", 1, 3000, kind="staking"), _ev("2024-08-01", "sell", "ETH", 11, 22000),
           _ev("2024-08-02", "transfer", "ETH", 1, 0), _ev("2025-02-01", "sell", "BTC", 0.5, 50000)]
BUYBACK = [_ev("2025-01-01", "buy", "ETH", 1, 2000), _ev("2025-02-01", "sell", "ETH", 1, 1500), _ev("2025-02-10", "buy", "ETH", 1, 1600)]
CRYPTO_HAND = [
    (c, HISTORY, {"gains": [15000.0, -16000.0, 30000.0], "net": n}) for c, n in
    (("US", 29000.0), ("GB", 29000.0), ("CA", 29000.0), ("AU", 29000.0), ("IN", 45000.0), ("DE", -1000.0))
] + [("GB", BUYBACK, {"gains": [-100.0]}), ("US", BUYBACK, {"gains": [-500.0], "net": -500.0}),
     ("CA", BUYBACK, {"gains": [0.0], "left": 2100.0}), ("IN", BUYBACK, {"gains": [-500.0], "net": 0.0}),
     ("DE", [_ev("2024-01-10", "buy", "BTC", 1, 40000), _ev("2025-01-10", "sell", "BTC", 0.5, 30000), _ev("2025-01-11", "sell", "BTC", 0.5, 30000)],
      {"gains": [10000.0, 10000.0], "net": 10000.0, "exempt": 10000.0}),
     ("AU", [_ev("2024-01-10", "buy", "BTC", 1, 40000), _ev("2025-01-10", "sell", "BTC", 0.5, 30000), _ev("2025-01-11", "sell", "BTC", 0.5, 30000)],
      {"terms": [["short"], ["long"]]})]


def crypto(seed: int) -> dict[str, Any]:
    bad = []
    for c, hist, want in CRYPTO_HAND:
        r = DG.gains({"country": c, "events": hist})
        if "gains" in want and [d["gain"] for d in r["disposals"]] != want["gains"]:
            bad.append(f"{c}: gains {[d['gain'] for d in r['disposals']]}, by hand {want['gains']}")
        if "net" in want and r["net"] != want["net"]:
            bad.append(f"{c}: net {r['net']}, by hand {want['net']}")
        if "exempt" in want and r.get("exempt_gain") != want["exempt"]:
            bad.append(f"{c}: exempt {r.get('exempt_gain')}, by hand {want['exempt']}")
        if "left" in want and r["holdings"][0]["cost"] != want["left"]:
            bad.append(f"{c}: cost left {r['holdings'][0]['cost']}, by hand {want['left']}")
        if "terms" in want and [[p.get("term") for p in d["parts"]] for d in r["disposals"]] != want["terms"]:
            bad.append(f"{c}: terms {[[p.get('term') for p in d['parts']] for d in r['disposals']]}")
        if hist is HISTORY and (r["own_transfers_ignored"] != 1 or r["income_total"] != 3000.0):
            bad.append(f"{c}: transfers / income not kept apart")
    rnd = random.Random(seed)
    runs = 0
    for c in DG.CRYPTO:
        for k in range(5):
            runs += 1
            held = defaultdict(Decimal)
            ev, d, paid = [], date(2023, 1, 1), Decimal(0)
            for _ in range(rnd.randint(6, 25)):
                d += timedelta(days=rnd.choice([0, 2, 9, 31, 60, 200]))
                a = rnd.choice(["BTC", "ETH", "SOL"])
                val = Decimal(rnd.randint(100, 9000))
                q = Decimal(rnd.randint(1, 400)) / 100
                t = rnd.random()
                if held[a] > 0 and t < 0.35:
                    q = min(q, held[a])
                    held[a] -= q
                    ev.append(_ev(d.isoformat(), "sell", a, float(q), float(val)))
                elif held[a] > 0 and t < 0.55:
                    q = min(q, held[a])
                    b = rnd.choice([x for x in ("BTC", "ETH", "SOL") if x != a])
                    gq = Decimal(rnd.randint(1, 400)) / 100
                    held[a] -= q
                    held[b] += gq
                    paid += val
                    ev.append(_ev(d.isoformat(), "swap", a, float(q), float(val), get_asset=b, get_qty=float(gq)))
                else:
                    kind = "income" if t > 0.9 else "buy"
                    held[a] += q
                    paid += val
                    ev.append(_ev(d.isoformat(), kind, a, float(q), float(val)))
            if not any(e["type"] in ("sell", "swap") for e in ev):
                continue
            r = DG.gains({"country": c, "events": ev})
            used = sum(Decimal(str(x["cost"])) for x in r["disposals"])
            left = sum(Decimal(str(h["cost"])) for h in r["holdings"])
            moved = sum(Decimal(str(x["disallowed"])) for x in r["disposals"])
            if abs(used + left - paid - moved) > Decimal("0.011") * (len(r["disposals"]) + 3):
                bad.append(f"{c} {seed}/{k}: cost used {used} + left {left} != paid {paid} + moved {moved}")
            got = {h["symbol"]: Decimal(str(h["qty"])) for h in r["holdings"]}
            if any(abs(got.get(x, Decimal(0)) - held[x]) > Decimal("0.0000001") for x in held):
                bad.append(f"{c} {seed}/{k}: coins left differ from the history")
    for addr, chain, ok in (("bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4", "bitcoin", True),
                            ("bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t5", "bitcoin", False),
                            ("bc1p5d7rjq7g6rdk2yhzks9smlaqtedr4dekq08ge8ztwac72sfr9rusxg3297", "bitcoin", True),
                            ("1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa", "bitcoin", True), ("1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNb", "bitcoin", False),
                            ("TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t", "tron", True), ("TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6u", "tron", False)):
        if DG.wallet({"address": addr, "chain": chain})["address"]["valid_shape"] != ok:
            bad.append(f"address {addr[:10]}... checked {not ok}, should be {ok}")
    p = DG.wallet({"address": "0x1234aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5678", "chain": "ethereum",
                   "known": ["0x1234bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb5678"]})
    if not p["looks_like_yours_but_is_not"]:
        bad.append("a poisoning address was not named")
    return {"part": "crypto gains", "runs": runs, "ok": not bad, "problems": bad[:10]}


def run(seeds: int = 3) -> dict[str, Any]:
    rows = []
    for fn, arg in [(zakat_set, None)] + [(savings_groups, 500 + s) for s in range(seeds)] + [(crypto, 600 + s) for s in range(seeds)]:
        try:
            rows.append({**(fn() if arg is None else fn(arg)), "seed": arg})
        except Exception as e:      # a crash is a failed check, not a stopped card
            rows.append({"part": fn.__name__, "seed": arg, "ok": False, "problems": [f"{type(e).__name__}: {e}"]})
    return {"checks": len(rows), "passed": sum(r["ok"] for r in rows), "ok": all(r["ok"] for r in rows), "rows": rows,
            "scholar_reviewed": SCHOLAR_REVIEWED}


if __name__ == "__main__":
    r = run(int(sys.argv[1]) if len(sys.argv) > 1 else 3)
    for x in r["rows"]:
        if not x["ok"]:
            print("FAIL", x["part"], x["seed"], "; ".join(x["problems"][:5]))
    print(f"F11 card: {r['passed']}/{r['checks']} ({sum(x.get('meetings', 0) for x in r['rows'])} group meetings in "
          f"{', '.join(GROUPS)}; {len(ZAKAT)} zakat cases, {'reviewed' if SCHOLAR_REVIEWED else 'NOT yet reviewed'} by a scholar; "
          f"{sum(x.get('runs', 0) for x in r['rows'])} crypto histories)")
    sys.exit(0 if r["ok"] else 1)
