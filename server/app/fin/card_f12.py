"""The F12 card: the public sector (FINANCE_GLOBAL_PLAN phase F12).

G2P PAYMENT RUNS RECONCILED. A seeded beneficiary list, the payment file and the bank's return, with planted faults the card knows: a
beneficiary never sent, a payment the bank failed, one paid twice, one paid the wrong amount, a payment to someone not on the list, one
account shared by two beneficiaries, a payment the bank never answered. The card checks exactly those are found and nothing else, and a
clean run is called clean. Account numbers never leave unmasked.

DEPOSIT COVER. Hand cases (two accounts added for one depositor, a joint account split equally, loans set off only when her rule says,
an excluded account left out, an account with no ID and one person under two IDs named) and seeded failed banks checked on their laws:
covered + above cover = what is eligible, nobody covered above her limit, every balance counted once.

BENEFITS, SUPERVISION, DEVELOPMENT FINANCE. A household checked against scheme rules with their sources (met, missed by how much, cannot
tell yet, evidence missing, the amount by her rule); a rule with no source refused. Banks' ratios and breaches against hand-worked
numbers. A tranche released before its conditions named.

NO DECISION TAKEN. Paying, awarding, refusing, stopping, releasing, closing a bank or sanctioning is refused.

    python -m app.fin.card_f12        prints the card; exit 1 if anything fails
"""
from __future__ import annotations

import random
import sys
from decimal import Decimal
from typing import Any

from . import laws as L
from .desks import public as PB


def g2p_run(seed: int) -> dict[str, Any]:
    rnd = random.Random(seed)
    n = rnd.randint(400, 2000)
    ben = [{"id": f"B{k:05d}", "amount": rnd.choice([500, 1000, 1500, 2000]), "account": f"{rnd.randint(10 ** 11, 10 ** 12 - 1)}"}
           for k in range(n)]
    pay, ret = [], []
    picks = rnd.sample(range(n), 7)
    never, fail, twice, wrong, shared_a, shared_b, noret = picks
    for k, b in enumerate(ben):
        if k == never:
            continue
        amt = b["amount"] + (100 if k == wrong else 0)
        acct = ben[shared_a]["account"] if k == shared_b else b["account"]
        pay.append({"id": b["id"], "ref": f"R{k}", "amount": amt, "account": acct})
        if k != noret:
            ret.append({"ref": f"R{k}", "status": "failed" if k == fail else "success"})
        if k == twice:
            pay.append({"id": b["id"], "ref": f"R{k}b", "amount": amt, "account": acct})
            ret.append({"ref": f"R{k}b", "status": "success"})
    pay.append({"id": "X99999", "ref": "RX", "amount": 700, "account": "999988887777"})
    ret.append({"ref": "RX", "status": "success"})
    r = PB.g2p({"beneficiaries": ben, "payments": pay, "bank_return": ret})
    bad = []
    if [x["id"] for x in r["never_sent"]] != [ben[never]["id"]]:
        bad.append(f"never sent {r['never_sent']}")
    if [x["id"] for x in r["failed"]] != [ben[fail]["id"]]:
        bad.append(f"failed {r['failed']}")
    if [x["id"] for x in r["paid_twice"]] != [ben[twice]["id"]] or r["paid_twice"][0]["extra"] != float(ben[twice]["amount"]):
        bad.append(f"paid twice {r['paid_twice']}")
    if [(x["id"], x["difference"]) for x in r["wrong_amount"]] != [(ben[wrong]["id"], 100.0)]:
        bad.append(f"wrong amount {r['wrong_amount']}")
    if [x["id"] for x in r["not_on_the_list"]] != ["X99999"]:
        bad.append(f"not on the list {r['not_on_the_list']}")
    if [x["beneficiaries"] for x in r["shared_accounts"]] != [sorted([ben[shared_a]["id"], ben[shared_b]["id"]])]:
        bad.append(f"shared accounts {r['shared_accounts']}")
    if r["no_bank_return_for"] != [f"R{noret}"]:
        bad.append(f"no return {r['no_bank_return_for']}")
    if r["paid"] != n - 4 or r["clean"]:          # never sent, failed, wrong amount and no bank answer are not "paid"
        bad.append(f"paid {r['paid']} of {n}, clean {r['clean']}")
    if any(b["account"] in str(r) for b in ben):
        bad.append("an account number left unmasked")
    clean = PB.g2p({"beneficiaries": ben[:50], "payments": [{"id": b["id"], "ref": b["id"], "amount": b["amount"], "account": b["account"]}
                                                            for b in ben[:50]],
                    "bank_return": [{"ref": b["id"], "status": "success"} for b in ben[:50]]})
    if not clean["clean"] or clean["paid"] != 50:
        bad.append("a clean run was not called clean")
    return {"part": "G2P reconciliation", "beneficiaries": n, "ok": not bad, "problems": bad}


def deposits(seed: int) -> dict[str, Any]:
    bad = []
    r = PB.deposit_cover({"limit": 100000, "accounts": [
        {"number": "111122223333", "holders": ["A"], "balance": 60000},
        {"number": "111122224444", "holders": ["A"], "balance": 50000, "interest": 500},
        {"number": "555566667777", "holders": ["A", "B"], "balance": 80000},
        {"number": "999900001111", "holders": ["C"], "balance": 30000, "type": "excluded"},
        {"number": "222233334444", "holders": [""], "balance": 900},
        {"number": "333344445555", "holders": ["D"], "balance": 20000}],
        "loans": [{"depositor": "D", "due": 5000}],
        "depositors": [{"id": "D", "name": "Ravi K", "dob": "1980-01-01"}, {"id": "E", "name": "Ravi K", "dob": "1980-01-01"}]})
    got = {x["depositor"]: (x["deposits"], x["covered"], x["above_cover"]) for x in r["depositors"]}
    if got != {"A": (150500.0, 100000.0, 50500.0), "B": (40000.0, 40000.0, 0.0), "D": (20000.0, 20000.0, 0.0)}:
        bad.append(f"cover {got}")
    if len(r["records_to_fix"]) != 2:
        bad.append(f"records to fix {r['records_to_fix']}")
    s = PB.deposit_cover({"limit": 100000, "set_off_loans": True, "accounts": [{"number": "1", "holders": ["D"], "balance": 20000}],
                          "loans": [{"depositor": "D", "due": 5000}]})
    if s["depositors"][0]["covered"] != 15000.0:
        bad.append(f"set-off: covered {s['depositors'][0]['covered']}")
    rnd = random.Random(seed)
    lim = rnd.choice([50000, 100000, 250000])
    acc = []
    people = [f"P{k}" for k in range(300)]
    for k in range(1500):
        hs = rnd.sample(people, rnd.choice([1, 1, 1, 2, 3]))
        acc.append({"number": f"{k:012d}", "holders": hs, "balance": rnd.randint(0, 300000)})
    r = PB.deposit_cover({"limit": lim, "accounts": acc})
    tot_bal = sum(Decimal(a["balance"]) for a in acc)
    dep = sum(Decimal(str(x["deposits"])) for x in r["depositors"])
    if abs(dep - tot_bal) > Decimal("0.01") * len(r["depositors"]):
        bad.append(f"balances counted {dep}, the accounts hold {tot_bal}")
    for x in r["depositors"]:
        if x["covered"] > lim or abs(x["covered"] + x["above_cover"] - x["eligible"]) > 0.011:
            bad.append(f"{x['depositor']}: covered {x['covered']} + above {x['above_cover']} != {x['eligible']} or above the limit")
            break
    return {"part": "deposit cover", "accounts": len(acc), "ok": not bad, "problems": bad}


def checks() -> dict[str, Any]:
    bad = []
    sc = [{"name": "Child support", "source": "Act 12, s.4", "tests": [{"field": "income", "op": "<=", "value": 30000},
                                                                       {"field": "children", "op": ">=", "value": 1}],
           "amount": {"base": 0, "per_field": "children", "per_value": 1200, "max": 3000}, "evidence": ["birth certificate", "payslip"]},
          {"name": "Housing aid", "source": "Rule 7", "tests": [{"field": "income", "op": "<=", "value": 20000}]},
          {"name": "Disability aid", "source": "Act 3", "tests": [{"field": "disability_pct", "op": ">=", "value": 40}]}]
    r = PB.benefits({"household": {"income": 24000, "children": 3}, "schemes": sc, "evidence_held": ["payslip"]})
    st = {x["scheme"]: x for x in r["schemes"]}
    if (st["Child support"]["state"], st["Child support"]["amount"], st["Child support"]["evidence_missing"]) != \
            ("meets the rules", 3000.0, ["birth certificate"]):
        bad.append(f"child support {st['Child support']}")
    if st["Housing aid"]["state"] != "does not meet" or st["Housing aid"]["missed"][0]["by"] != 4000.0:
        bad.append(f"housing {st['Housing aid']}")
    if st["Disability aid"]["state"] != "cannot tell yet":
        bad.append("an unknown field was not 'cannot tell yet'")
    try:
        PB.benefits({"household": {}, "schemes": [{"name": "x", "tests": []}]})
        bad.append("a rule with no source was used")
    except PB.PublicError:
        pass
    s = PB.supervisor({"thresholds": {"car_min": 10.5, "lcr_min": 100, "npl_max": 5}, "returns": [
        {"bank": "A", "capital": 120, "rwa": 1000, "liquid_assets": 90, "net_outflows": 100, "npl": 30, "loans": 800},
        {"bank": "B", "capital": 100, "rwa": 1000, "liquid_assets": 150, "net_outflows": 100, "npl": 60, "loans": 1000}],
        "previous": [{"bank": "A", "capital": 130, "rwa": 1000}]})
    b = {x["bank"]: x for x in s["banks"]}
    if (b["A"]["car"], b["A"]["lcr"], b["A"]["npl"], len(b["A"]["breaches"]), b["A"]["moves"]) != (12.0, 90.0, 3.75, 1, {"car_points": -1.0}):
        bad.append(f"bank A {b['A']}")
    if [x.split()[0] for x in b["A"]["breaches"]] != ["lcr"] or [x.split()[0] for x in b["B"]["breaches"]] != ["car", "npl"] \
            or s["in_breach"] != ["A", "B"]:
        bad.append(f"bank B {b['B']}")
    d = PB.dev_finance({"conditions_met": ["audit"], "tranches": [{"name": "T1", "amount": 100, "conditions": ["audit"], "released": True},
                                                                   {"name": "T2", "amount": 200, "conditions": ["audit", "procurement plan"],
                                                                    "released": True}],
                        "budget": [{"line": "works", "amount": 1000}], "spending": [{"line": "works", "amount": 1100, "category": "works"},
                                                                                    {"line": "works", "amount": 50, "category": "gifts"}],
                        "eligible_categories": ["works"]})
    if d["released_before_conditions"] != ["T2"] or d["over_budget"] != ["works"] or len(d["ineligible"]) != 1:
        bad.append(f"development finance {d['released_before_conditions']} {d['over_budget']} {d['ineligible']}")
    for w in ("pay", "award_benefit", "refuse_claim", "stop_benefit", "release_tranche", "close_bank", "sanction_bank", "disburse"):
        try:
            PB.run("card_f12", w, {})
            bad.append(f"{w} was not refused")
        except L.Refused:
            pass
    return {"part": "benefits, supervision, development", "ok": not bad, "problems": bad}


def run(seeds: int = 3) -> dict[str, Any]:
    rows = []
    for fn, arg in [(checks, None)] + [(g2p_run, 700 + s) for s in range(seeds)] + [(deposits, 800 + s) for s in range(seeds)]:
        try:
            rows.append({**(fn() if arg is None else fn(arg)), "seed": arg})
        except Exception as e:      # a crash is a failed check, not a stopped card
            rows.append({"part": fn.__name__, "seed": arg, "ok": False, "problems": [f"{type(e).__name__}: {e}"]})
    return {"checks": len(rows), "passed": sum(r["ok"] for r in rows), "ok": all(r["ok"] for r in rows), "rows": rows}


if __name__ == "__main__":
    r = run(int(sys.argv[1]) if len(sys.argv) > 1 else 3)
    for x in r["rows"]:
        if not x["ok"]:
            print("FAIL", x["part"], x["seed"], "; ".join(x["problems"][:5]))
    print(f"F12 card: {r['passed']}/{r['checks']} ({sum(x.get('beneficiaries', 0) for x in r['rows'])} beneficiaries reconciled; "
          f"{sum(x.get('accounts', 0) for x in r['rows'])} deposit accounts covered)")
    sys.exit(0 if r["ok"] else 1)
