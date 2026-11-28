"""The F8 card: payments (FINANCE_GLOBAL_PLAN phase F8).

REPRESENTMENT PACKS FOR 3 SCHEMES' REASON CODES. For every reason code Hoola knows on Visa, Mastercard and Amex, a seed gives a mix of
evidence. The card checks: the evidence needed is that code's list; what she has and what is missing split it exactly; the verdict
follows the code's minimum (and an already-refunded processing error says so); the response deadline is received + her processor's
window; the letter and the evidence index name exactly the evidence present, and nothing she does not have. For Visa 10.4 the card
builds earlier transactions it knows the answer for (inside / outside 120-365 days, disputed, sharing too little, sharing two without
IP or device) and checks the compelling-evidence test counts exactly the right ones.

RECONCILIATION OF FIXED MULTI-GATEWAY MONTHS. Three months, three gateways: orders, sales, refunds, chargebacks and fees in weekly
payouts, bank deposits 1-3 days later. Planted: an order the gateway never settled, a sale at the wrong amount, a gateway sale with no
order, a payout that never reached the bank, a deposit from nowhere, two payouts of the same amount on the same day from two gateways
(the deposit narration must decide). The card knows every answer it planted and checks the reconciliation finds exactly those, and
that each gateway's sales, refunds, chargebacks, fees, net and effective fee rate match its own arithmetic to the cent.

    python -m app.fin.card_f8        prints the card; exit 1 if anything fails
"""
from __future__ import annotations

import random
import sys
from datetime import date, timedelta
from typing import Any

from .desks import payments as PM


def representment(seed: int) -> dict[str, Any]:
    rnd = random.Random(seed)
    bad: list[str] = []
    n = 0
    for net, codes in PM.REASONS.items():
        for code, rc in codes.items():
            for k in range(3):
                n += 1
                pool = list(PM.EVIDENCE)
                have = set(rnd.sample(pool, rnd.randint(0, 6)))
                if k == 2:
                    have |= set(rc["need"][: rc["min"]])           # at least once a full set
                r = PM.dispute({"network": net, "reason_code": code, "evidence": {x: True for x in have}, "amount": 120.5,
                                "transaction_id": f"T{n}", "received": "2026-09-01", "window_days": 20})
                got = [x for x in rc["need"] if x in have]
                miss = [x for x in rc["need"] if x not in have]
                if r["evidence_needed"] != rc["need"] or r["evidence_you_have"] != got or r["evidence_missing"] != miss:
                    bad.append(f"{net} {code}: evidence split {r['evidence_you_have']} / {r['evidence_missing']}, by hand {got} / {miss}")
                if rc["kind"] == "processing" and "refund_issued" in have:
                    want = "already refunded"
                elif len(got) >= rc["min"]:
                    want = "the evidence answers"
                else:
                    want = "too little evidence"
                if not r["verdict"].startswith(want):
                    bad.append(f"{net} {code}: verdict '{r['verdict']}', by hand '{want}'")
                if r["respond_by"] != "2026-09-21":
                    bad.append(f"{net} {code}: respond by {r['respond_by']}")
                for x in PM.EVIDENCE:
                    if (PM.EVIDENCE[x] in r["letter"]) != (x in got):
                        bad.append(f"{net} {code}: the letter {'names' if x not in got else 'leaves out'} {x}")
                        break
    # Visa 10.4 compelling evidence, with earlier payments whose answer the card knows
    disputed = {"ip": "1.2.3.4", "device": "dev-9", "shipping": "1 high st", "account": "sam@x"}
    priors = [({"date": "2026-04-01", "ip": "1.2.3.4", "device": "dev-9"}, True),          # 153 days, ip + device
              ({"date": "2025-11-10", "ip": "1.2.3.4", "shipping": "1 High St"}, True),     # 295 days, ip + shipping (case kept loose)
              ({"date": "2026-07-01", "ip": "1.2.3.4", "device": "dev-9"}, False),          # 62 days: too recent
              ({"date": "2025-06-01", "ip": "1.2.3.4", "device": "dev-9"}, False),          # 457 days: too old
              ({"date": "2026-03-01", "ip": "1.2.3.4", "device": "dev-9", "disputed": True}, False),
              ({"date": "2026-03-02", "shipping": "1 high st", "account": "sam@x"}, False),  # two shared, neither ip nor device
              ({"date": "2026-03-03", "device": "dev-9"}, False)]                            # one shared
    for cut in (len(priors), 1):
        ps = priors[:cut]
        r = PM.dispute({"network": "visa", "reason_code": "10.4", "dispute_date": "2026-09-01", "disputed": disputed,
                        "prior": [p for p, _ in ps], "evidence": {}})
        want = [i + 1 for i, (_, ok) in enumerate(ps) if ok]
        got = [g["prior"] for g in r["compelling_evidence"]["qualifying"]]
        if got != want or r["compelling_evidence"]["qualifies"] != (len(want) >= 2):
            bad.append(f"compelling evidence counted {got}, by hand {want}")
        if (("prior_transactions" in r["evidence_you_have"]) != (len(want) >= 2)):
            bad.append("compelling evidence not carried into the evidence")
    for wrong in ({"network": "discover", "reason_code": "1"}, {"network": "visa", "reason_code": "99.9"}):
        try:
            PM.dispute(wrong)
            bad.append(f"an unknown code was answered: {wrong}")
        except PM.PaymentsError:
            pass
    return {"part": "representment", "packs": n, "ok": not bad, "problems": bad[:12]}


def reconciliation(seed: int) -> dict[str, Any]:
    rnd = random.Random(seed)
    bad: list[str] = []
    gws = ["northpay", "eastcard", "westwallet"]
    orders, settlements, deposits = [], [], []
    hand = {g: {"sale": 0, "refund": 0, "chargeback": 0, "fee": 0} for g in gws}
    plant = {"missing_at_gateway": [], "amount_differs": [], "gateway_sale_without_order": [], "no_deposit": [], "stray": []}
    oid = 0
    day0 = date(2026, 6, 1)
    for week in range(13):
        for g in gws:
            pd_ = day0 + timedelta(days=7 * week + gws.index(g))
            lines = []
            for _ in range(rnd.randint(3, 9)):
                oid += 1
                amt = rnd.randint(500, 90000)
                o = {"id": f"O{oid}", "gateway": g, "amount": amt / 100}
                orders.append(o)
                if oid % 47 == 0:                                     # never settled
                    plant["missing_at_gateway"].append(o["id"])
                    continue
                settle = amt + (100 if oid % 53 == 0 else 0)          # settled at the wrong amount
                if settle != amt:
                    plant["amount_differs"].append(o["id"])
                lines.append({"order_id": o["id"], "type": "sale", "amount": settle / 100})
                hand[g]["sale"] += settle
                fee = round(settle * 0.029) + 30
                lines.append({"order_id": o["id"], "type": "fee", "amount": fee / 100})
                hand[g]["fee"] += fee
                if rnd.random() < 0.08:
                    r = rnd.randint(100, settle)
                    lines.append({"order_id": o["id"], "type": "refund", "amount": r / 100})
                    hand[g]["refund"] += r
                if rnd.random() < 0.03:
                    lines.append({"order_id": o["id"], "type": "chargeback", "amount": settle / 100})
                    hand[g]["chargeback"] += settle
            if week == 5 and g == "eastcard":                          # a sale with no order behind it
                lines.append({"order_id": "GHOST1", "type": "sale", "amount": 12.34})
                hand[g]["sale"] += 1234
                plant["gateway_sale_without_order"].append("GHOST1")
            net = sum(round(ln["amount"] * 100) * (1 if ln["type"] == "sale" else -1) for ln in lines)
            pid = f"{g[:2].upper()}{week:02d}"
            settlements.append({"gateway": g, "payout_id": pid, "payout_date": pd_.isoformat(), "lines": lines})
            if week == 8 and g == "westwallet":
                plant["no_deposit"].append(pid)
                continue
            deposits.append({"id": f"D-{pid}", "date": (pd_ + timedelta(days=rnd.randint(1, 3))).isoformat(), "amount": net / 100,
                             "narration": f"{g.upper()} PAYOUT {pid}"})
    # two payouts with the same amount on the same day from two gateways: the narration decides
    same = 4321.00
    for g, pid in (("northpay", "NO-TWIN"), ("eastcard", "EA-TWIN"), ("westwallet", "WE-TWIN")):
        settlements.append({"gateway": g, "payout_id": pid, "payout_date": "2026-09-20", "lines": [{"order_id": f"TW-{g}", "type": "sale", "amount": same}]})
        orders.append({"id": f"TW-{g}", "gateway": g, "amount": same})
        hand[g]["sale"] += 432100
    deposits.append({"id": "D-EA-TWIN", "date": "2026-09-22", "amount": same, "narration": "EASTCARD PAYOUT"})   # the later one
    deposits.append({"id": "D-NO-TWIN", "date": "2026-09-21", "amount": same, "narration": "NORTHPAY PAYOUT"})
    plant["no_deposit"].append("WE-TWIN")                     # a third payout of the same amount never arrived: no deposit is reused
    deposits.append({"id": "D-STRAY", "date": "2026-07-15", "amount": 999.99, "narration": "UNKNOWN CREDIT"})
    plant["stray"].append("D-STRAY")
    rnd.shuffle(deposits)
    r = PM.reconcile({"orders": orders, "settlements": settlements, "deposits": deposits, "window_days": 5})
    if sorted(x["order"] for x in r["orders"]["missing_at_gateway"]) != sorted(plant["missing_at_gateway"]):
        bad.append(f"missing at gateway {[x['order'] for x in r['orders']['missing_at_gateway']]} vs {plant['missing_at_gateway']}")
    if sorted(x["order"] for x in r["orders"]["amount_differs"]) != sorted(plant["amount_differs"]):
        bad.append("amount differences wrong")
    if r["orders"]["gateway_sale_without_order"] != plant["gateway_sale_without_order"]:
        bad.append("gateway sale without order wrong")
    if sorted(r["payouts_without_deposit"]) != sorted(plant["no_deposit"]):
        bad.append(f"payouts without deposit {r['payouts_without_deposit']} vs {plant['no_deposit']}")
    if r["deposits_without_payout"] != plant["stray"]:
        bad.append(f"deposits without payout {r['deposits_without_payout']}")
    twin = {x["payout"]: x["deposit"] for x in r["payouts"] if x["payout"].endswith("TWIN")}
    if twin != {"NO-TWIN": "D-NO-TWIN", "EA-TWIN": "D-EA-TWIN", "WE-TWIN": None}:
        bad.append(f"same-amount payouts matched to the wrong deposits: {twin}")
    for p in r["payouts"]:
        if p["deposit"] and not p["payout"].endswith("TWIN") and p["deposit"] != f"D-{p['payout']}":
            bad.append(f"payout {p['payout']} matched to {p['deposit']}")
            break
    for g in gws:
        h, got = hand[g], r["by_gateway"][g]
        want = {"sales": h["sale"] / 100, "refunds": h["refund"] / 100, "chargebacks": h["chargeback"] / 100, "fees": h["fee"] / 100,
                "net": (h["sale"] - h["refund"] - h["chargeback"] - h["fee"]) / 100,
                "effective_fee_pct": round(h["fee"] * 100 / h["sale"], 3)}
        for k, v in want.items():
            if abs(got[k] - v) > 1e-9:
                bad.append(f"{g} {k} {got[k]} by hand {v}")
    if r["balanced"]:
        bad.append("planted problems but the month says balanced")
    clean = PM.reconcile({"orders": [{"id": "A", "gateway": "x", "amount": 10}],
                          "settlements": [{"gateway": "x", "payout_id": "P", "payout_date": "2026-01-01",
                                           "lines": [{"order_id": "A", "type": "sale", "amount": 10}, {"order_id": "A", "type": "fee", "amount": 0.5}]}],
                          "deposits": [{"id": "B", "date": "2026-01-02", "amount": 9.5, "narration": "X"}]})
    if not clean["balanced"]:
        bad.append("a clean month is not balanced")
    return {"part": "reconciliation", "orders": len(orders), "payouts": len(settlements), "ok": not bad, "problems": bad[:12]}


def run(seeds: int = 3) -> dict[str, Any]:
    rows = []
    for s in range(seeds):
        for fn in (representment, reconciliation):
            try:
                rows.append({**fn(100 + s), "seed": 100 + s})
            except Exception as e:      # a crash is a failed check, not a stopped card
                rows.append({"part": fn.__name__, "seed": 100 + s, "ok": False, "problems": [f"{type(e).__name__}: {e}"]})
    return {"checks": len(rows), "passed": sum(r["ok"] for r in rows), "ok": all(r["ok"] for r in rows), "rows": rows,
            "schemes": sorted(PM.REASONS), "reason_codes": sum(len(v) for v in PM.REASONS.values())}


if __name__ == "__main__":
    r = run(int(sys.argv[1]) if len(sys.argv) > 1 else 3)
    for x in r["rows"]:
        if not x["ok"]:
            print("FAIL", x["part"], x["seed"], "; ".join(x["problems"][:5]))
    print(f"F8 card: {r['passed']}/{r['checks']} ({r['reason_codes']} reason codes in {', '.join(r['schemes'])}; "
          f"{sum(x.get('payouts', 0) for x in r['rows'])} payouts reconciled)")
    sys.exit(0 if r["ok"] else 1)
