"""The F5 card: payroll for 6 countries checked against answers worked out by hand, and the cash forecast back-tested on months that
really happened (FINANCE_GLOBAL_PLAN phase F5).

PAYROLL. For GB, DE, AU, SG, IN and US the card gives a payroll rule set of the shape a payroll adviser would type into settings
(income tax by annual bands or none, contributions with thresholds and ceilings on both sides, a fixed-by-slab tax, a before-tax
pension, weekly / fortnightly / monthly pay). These numbers are the card's TEST rules, shaped like each country's - not a claim about
the law. Then 4-6 people from a seed (salary, hourly, overtime, bonus, unpaid days, one who left before the period, one who starts after)
are paid by the desk, and the card works every line out itself (plain Decimal, half-up to the cent, each tax band rounded on its own)
and compares to the cent: gross, before-tax, taxable, income tax, each contribution both sides, net pay, employer cost, the totals and
what goes to each authority. Also: a closed period is never recalculated, a run with no rules is refused (never a guessed rate), the
filings tracker's due dates, contractor totals over her threshold.

CASH. Nine months of statements with repeating items (rent, software, loan, salaries in, utilities varying) and one-offs are made from a
seed. The backtest predicts each of the last 3 months only from the 3 months before it; the card works the same model out by hand, checks
the desk learned only from earlier months, and that on a business with steady habits the error stays under 10% of spending. The 13-week
forecast's weekly closing balances are checked by hand against the open invoices, bills, payroll and repeating items put in.

    python -m app.fin.card_f5        builds a scratch database, prints the card; exit 1 if anything fails
"""
from __future__ import annotations

import random
import sys
from collections import defaultdict
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from . import profile as PR
from .desks import books as B
from .desks import cash as CS
from .desks import payroll as PY

D = Decimal
PPY = {"monthly": 12, "fortnightly": 26, "weekly": 52}

RULES: dict[str, dict[str, Any]] = {
    "GB": {"cur": "GBP", "frequency": "monthly", "period": "2026-08",
           "income_tax": {"method": "annualised", "allowance": 12570, "bands": [{"upto": 37700, "pct": 20}, {"upto": 125140, "pct": 40},
                                                                             {"upto": None, "pct": 45}]},
           "contributions": [{"name": "NI main", "employee_pct": 8, "from": 1048, "upto": 4189},
                             {"name": "NI upper", "employee_pct": 2, "from": 4189},
                             {"name": "NI employer", "employer_pct": 15, "from": 417}], "pension": 5},
    "DE": {"cur": "EUR", "frequency": "monthly", "period": "2026-08",
           "income_tax": {"method": "period", "allowance": 0, "bands": [{"upto": 1000, "pct": 0}, {"upto": 5000, "pct": 22},
                                                                         {"upto": None, "pct": 42}]},
           "contributions": [{"name": "pension", "employee_pct": 9.3, "employer_pct": 9.3, "upto": 8050},
                             {"name": "health", "employee_pct": 8.55, "employer_pct": 7.3, "upto": 5512.5},
                             {"name": "unemployment", "employee_pct": 1.3, "employer_pct": 1.3, "upto": 8050},
                             {"name": "care", "employee_pct": 1.8, "employer_pct": 1.8, "upto": 5512.5}], "pension": 0},
    "AU": {"cur": "AUD", "frequency": "fortnightly", "period": "2026-08-03",
           "income_tax": {"method": "annualised", "allowance": 0, "bands": [{"upto": 18200, "pct": 0}, {"upto": 45000, "pct": 16},
                                                                         {"upto": 135000, "pct": 30}, {"upto": 190000, "pct": 37},
                                                                         {"upto": None, "pct": 45}]},
           "contributions": [{"name": "super", "employer_pct": 12}], "pension": 0},
    "SG": {"cur": "SGD", "frequency": "monthly", "period": "2026-08", "income_tax": {"method": "none"},
           "contributions": [{"name": "CPF", "employee_pct": 20, "employer_pct": 17, "upto": 8000}], "pension": 0},
    "IN": {"cur": "INR", "frequency": "monthly", "period": "2026-08",
           "income_tax": {"method": "annualised", "allowance": 75000,
                          "bands": [{"upto": 400000, "pct": 0}, {"upto": 800000, "pct": 5}, {"upto": 1200000, "pct": 10},
                                    {"upto": 1600000, "pct": 15}, {"upto": 2000000, "pct": 20}, {"upto": 2400000, "pct": 25},
                                    {"upto": None, "pct": 30}]},
           "contributions": [{"name": "PF", "employee_pct": 12, "employer_pct": 12, "upto": 15000},
                             {"name": "professional tax", "slabs": [{"upto": 7500, "employee": 0, "employer": 0},
                                                                    {"upto": 10000, "employee": 175, "employer": 0},
                                                                    {"upto": None, "employee": 200, "employer": 0}]}], "pension": 0},
    "US": {"cur": "USD", "frequency": "weekly", "period": "2026-08-03",
           "income_tax": {"method": "annualised", "allowance": 15000, "bands": [{"upto": 11925, "pct": 10}, {"upto": 48475, "pct": 12},
                                                                             {"upto": 103350, "pct": 22}, {"upto": None, "pct": 24}]},
           "contributions": [{"name": "social security", "employee_pct": 6.2, "employer_pct": 6.2, "upto": 3386.54},
                             {"name": "medicare", "employee_pct": 1.45, "employer_pct": 1.45}], "pension": 4},
}


def _c(x: Any) -> int:          # units -> cents, half-up
    return int((D(str(x)) * 100).quantize(D(1), ROUND_HALF_UP))


def _r(x: Decimal) -> int:
    return int(x.quantize(D(1), ROUND_HALF_UP))


def _pc(minor: int, pct: Any) -> int:
    return _r(D(minor) * D(str(pct)) / 100)


def _hand_bands(amount: int, bands: list[dict[str, Any]]) -> int:
    tax, lo = 0, 0
    for b in bands:
        hi = None if b["upto"] is None else _c(b["upto"])
        top = amount if hi is None else min(amount, hi)
        if top > lo:
            tax += _pc(top - lo, b["pct"])
        if hi is None or amount <= hi:
            break
        lo = hi
    return tax


def hand_pay(rule: dict[str, Any], p: dict[str, Any], x: dict[str, Any]) -> dict[str, int]:
    """One person's pay worked out from the rules, independently of the desk."""
    ppy = PPY[rule["frequency"]]
    if p["kind"] == "annual":
        g = _r(D(_c(p["pay"])) / ppy)
    elif p["kind"] == "per_period":
        g = _c(p["pay"])
    else:
        g = _r(D(_c(p["pay"])) * D(str(x.get("hours", p.get("hours", 0)))))
    if x.get("unpaid_days"):
        per = x.get("working_days", 21 if ppy == 12 else 5 * 52 // ppy)
        g -= _r(D(g) * D(str(x["unpaid_days"])) / D(str(per)))
    g += sum(_c(x[k]) for k in ("overtime", "bonus") if x.get(k))
    pre = _pc(g, p["pre_tax_pct"]) if p.get("pre_tax_pct") else 0
    tx = g - pre
    t = rule["income_tax"]
    if t["method"] == "annualised":
        tax = _r(D(_hand_bands(max(0, tx * ppy - _c(t["allowance"])), t["bands"])) / ppy)
    elif t["method"] == "period":
        tax = _hand_bands(max(0, tx - _r(D(_c(t["allowance"])) / ppy)), t["bands"])
    else:
        tax = 0
    ee = er = 0
    per_con = {}
    for c in rule["contributions"]:
        if c.get("slabs"):
            s = next(s for s in c["slabs"] if s["upto"] is None or D(g) / 100 <= D(str(s["upto"])))
            a, b = _c(s["employee"]), _c(s["employer"])
        else:
            base = g
            lo = _c(c.get("from", 0))
            top = min(base, _c(c["upto"])) if c.get("upto") is not None else base
            part = max(0, top - lo)
            a, b = _pc(part, c.get("employee_pct", 0)), _pc(part, c.get("employer_pct", 0))
        ee += a
        er += b
        per_con[c["name"]] = (a, b)
    return {"gross": g, "pre_tax": pre, "taxable": tx, "tax": tax, "ee": ee, "er": er, "net": g - pre - tax - ee, "cost": g + er,
            "per": per_con}


def _ws(t: str, cc: str, cur: str) -> str:
    pv = PR.preview({"size": "business", "countries": [cc], "wants": [], "people": []})
    ans = {**pv["answers"], "currency": cur}
    return PR.apply(t, ans, PR.preview(ans)["hash"])["id"]


def payroll_one(i: int, cc: str) -> dict[str, Any]:
    rnd = random.Random(5000 + i)
    rule = RULES[cc]
    cur = rule["cur"]
    t = f"card5-{i}-{cc}"
    ws = _ws(t, cc, cur)
    run = lambda a, **x: PY.run(t, a, {"workspace": ws, **x}, "card")   # noqa: E731
    bad: list[str] = []
    run("employee", name="Early Bird", annual=30000)
    try:                                                                       # no rules: refused, never guessed
        run("run", period=rule["period"])
        bad.append("a payroll with no rules was not refused")
    except PY.PayrollError as e:
        if "settings" not in str(e):
            bad.append(f"refusal did not say how to go on: {e}")
    run("settings", country=cc, frequency=rule["frequency"], source="card test rules", contributions=rule["contributions"],
        income_tax=rule["income_tax"], pay_day=25,
        filings=[{"name": "monthly return", "every": "monthly", "due_day": 19}, {"name": "year end", "every": "yearly", "month": 3,
                                                                                  "due_offset_days": 60}])
    scale = {"INR": 80, "SGD": 1.3, "AUD": 1.5, "EUR": 0.9, "GBP": 0.8, "USD": 1}[cur]
    people: dict[str, dict[str, Any]] = {}
    extras: dict[str, dict[str, Any]] = {}
    n = 4 + i % 3
    for k in range(n):
        name = f"Person {k + 1}"
        pre = rule["pension"] if k % 2 == 0 else 0
        if k == 1 and rule["frequency"] != "monthly":
            p = {"kind": "hourly", "pay": round(rnd.uniform(18, 60) * scale, 2), "hours": rnd.choice([38, 40, 76, 80])}
            run("employee", name=name, hourly=p["pay"], hours=p["hours"], pre_tax_pct=pre or None)
        else:
            p = {"kind": "annual", "pay": round(rnd.uniform(12000, 160000) * scale, 2)}
            run("employee", name=name, annual=p["pay"], pre_tax_pct=pre or None)
        p["pre_tax_pct"] = pre
        people[name.lower().replace(" ", "-")] = p
        x: dict[str, Any] = {}
        if k == 2:
            x = {"overtime": round(rnd.uniform(50, 900) * scale, 2), "bonus": round(rnd.uniform(0, 3000) * scale, 2)}
        if k == 3:
            x = {"unpaid_days": rnd.choice([1, 2, 3])}
        if x:
            extras[name.lower().replace(" ", "-")] = x
    run("employee", name="Early Bird", leave=True, left_on="2026-01-31")     # left before the period: not paid
    run("employee", name="Late Start", annual=50000 * scale, start="2027-01-01")   # starts after: not paid
    out = run("run", period=rule["period"], extras=extras)
    got = {p["id"]: p for p in out["people"]}
    if set(got) != set(people):
        bad.append(f"paid {sorted(got)}, expected {sorted(people)}")
    tot = defaultdict(int)
    auth = defaultdict(int)
    for pid, p in people.items():
        h = hand_pay(rule, p, extras.get(pid, {}))
        g = got.get(pid)
        if not g:
            continue
        for k in ("gross", "pre_tax", "tax", "ee", "er", "net", "cost"):
            if _c(g[k]) != h[k]:
                bad.append(f"{pid} {k} {g[k]} by hand {h[k] / 100:.2f}")
            tot[k] += h[k]
        for c in g["contributions"]:
            a, b = h["per"][c["name"]]
            if (_c(c["employee"]), _c(c["employer"])) != (a, b):
                bad.append(f"{pid} {c['name']} {c['employee']}/{c['employer']} by hand {a / 100:.2f}/{b / 100:.2f}")
            auth[c["name"]] += a + b
        auth["income tax"] += h["tax"]
    for k, v in tot.items():
        if _c(out["totals"][k]) != v:
            bad.append(f"total {k} {out['totals'][k]} by hand {v / 100:.2f}")
    for k, v in auth.items():
        if _c(out["to_authorities"].get(k, 0)) != v:
            bad.append(f"to {k} {out['to_authorities'].get(k)} by hand {v / 100:.2f}")
    slip = run("payslip", period=rule["period"], employee="Person 1")
    if "DRAFT" not in slip["payslip"] or "card test rules" not in slip["payslip"]:
        bad.append("payslip does not show draft / its rules")
    run("close", period=rule["period"])
    try:
        run("run", period=rule["period"])
        bad.append("a closed payroll was recalculated")
    except PY.PayrollError:
        pass
    f = run("filings", year=2026, today="2026-10-01")
    sept = next((x for x in f["items"] if x["filing"] == "monthly return" and x["for"] == "2026-08"), None)
    if not sept or sept["due"] != "2026-09-19" or sept["status"] != "overdue":
        bad.append(f"filing for 2026-08 due {sept}")
    ye = next((x for x in f["items"] if x["filing"] == "year end"), None)
    if not ye or ye["due"] != (date(2026, 3, 31) + timedelta(days=60)).isoformat():
        bad.append(f"year-end filing due {ye}")
    pays = [{"payee": rnd.choice(["Ann", "Bo", "Cy"]), "amount": round(rnd.uniform(10, 900), 2), "date": f"2026-0{rnd.randint(1, 9)}-10"}
            for _ in range(12)]
    want = defaultdict(int)
    for p in pays:
        want[p["payee"]] += _c(p["amount"])
    con = run("contractors", year=2026, rows=pays, threshold=600, tax_ids={"Ann": "123456789"})
    for p in con["payees"]:
        if _c(p["total"]) != want[p["payee"]] or p["report"] != (want[p["payee"]] >= 60000):
            bad.append(f"contractor {p['payee']} {p['total']} by hand {want[p['payee']] / 100:.2f}")
    return {"part": "payroll", "country": cc, "people": len(people), "ok": not bad, "problems": bad[:12]}


# ---- cash ---------------------------------------------------------------------------------------------------------------------

def _history(rnd: random.Random, months: list[str], cur_scale: float = 1.0) -> list[dict[str, Any]]:
    rows = []
    for m in months:
        def add(day, amt, narr):
            rows.append({"day": f"{m}-{day:02d}", "amount_minor": _c(round(amt, 2)), "narration": narr, "currency": "GBP"})
        add(1, -2000, f"RENT UNIT 4 REF {rnd.randint(1000, 9999)}")
        add(5, -49.99, "SOFTWARE SUB")
        add(10, -650, f"LOAN REPAYMENT {m}")
        add(15, -(180 + rnd.uniform(-25, 25)), "ENERGY CO")
        add(28, 9000 + rnd.uniform(-300, 300), f"CLIENT RETAINER INV {rnd.randint(100, 999)}")
        add(rnd.randint(2, 27), -(rnd.uniform(5, 40)), "BANK CHARGE")
        if rnd.random() < 0.3:
            add(rnd.randint(2, 27), -rnd.uniform(100, 600), f"ONE OFF {rnd.randint(1, 99)}")
    return rows


def hand_predict(rows: list[dict[str, Any]], month: str, window: int = 3) -> int:
    """The repeating-items model, worked out by hand: items (narration without numbers, first 4 words, sign) in 2+ of the window
    months count at their monthly average; everything else at its average over the window."""
    before = [CS._add_months(month, -k) for k in range(window, 0, -1)]
    groups: dict[tuple[str, bool], dict[str, Any]] = defaultdict(lambda: {"m": set(), "s": 0})
    rest = 0
    for r in rows:
        if r["day"][:7] in before:
            g = groups[(CS._key(r["narration"]), r["amount_minor"] > 0)]
            g["m"].add(r["day"][:7])
            g["s"] += r["amount_minor"]
    rep = 0
    for g in groups.values():
        if len(g["m"]) >= 2:
            rep += _r(D(g["s"]) / len(g["m"]))
        else:
            rest += g["s"]
    return rep + _r(D(rest) / window)


def cash_one(i: int) -> dict[str, Any]:
    rnd = random.Random(9000 + i)
    bad: list[str] = []
    t = f"card5-cash-{i}"
    ws = _ws(t, "GB", "GBP")
    months = [f"2026-{m:02d}" for m in range(1, 10)]
    rows = _history(rnd, months)
    bt = CS.backtest(t, ws, {"_rows": rows, "window": 3, "hold_out": 3})
    errs = []
    for mo in bt["months"]:
        want = hand_predict(rows, mo["month"])
        if _c(mo["predicted"]) != want:
            bad.append(f"backtest {mo['month']} predicted {mo['predicted']} by hand {want / 100:.2f}")
        if mo["month"] in mo["learned_from"] or any(x >= mo["month"] for x in mo["learned_from"]):
            bad.append(f"backtest {mo['month']} learned from itself or later: {mo['learned_from']}")
        actual = sum(r["amount_minor"] for r in rows if r["day"][:7] == mo["month"])
        if _c(mo["actual"]) != actual:
            bad.append(f"actual {mo['month']}")
        errs.append(mo["error_pct_of_spending"])
    if bt["mean_error_pct_of_spending"] is None or bt["mean_error_pct_of_spending"] >= 10:
        bad.append(f"steady habits but mean error {bt['mean_error_pct_of_spending']}% of spending")

    # the 13-week forecast on real records
    from . import spine as SP
    def _line(r):
        v = r["amount_minor"] / 100
        return f"{r['day']},{r['narration']},{'' if v > 0 else f'{-v:.2f}'},{f'{v:.2f}' if v > 0 else ''}\n"
    csv_ = "Date,Narration,Debit,Credit\n" + "".join(_line(r) for r in rows if r["day"] >= "2026-06-01")
    SP.import_statement(t, ws, csv_, "Current", "GBP")
    opening = sum(r["amount_minor"] for r in rows if r["day"] >= "2026-06-01")
    B.run(t, "invoice", {"workspace": ws, "party": "Acme", "issue": "2026-09-20", "due": "2026-10-17", "issue_now": True,
                         "lines": [{"price": 1200}]}, "card")
    B.run(t, "invoice", {"workspace": ws, "party": "Late Ltd", "issue": "2026-08-01", "due": "2026-09-01", "issue_now": True,
                         "lines": [{"price": 300}]}, "card")
    B.run(t, "bill", {"workspace": ws, "party": "Printer", "issue": "2026-09-25", "due": "2026-10-09", "issue_now": True,
                      "lines": [{"price": 450}]}, "card")
    CS.save_settings(t, ws, {"min_cash": 20000, "lag_days": 5})
    f = CS.forecast(t, ws, {"start": "2026-10-05", "weeks": 13, "items": [{"date": "2026-11-16", "amount": -5000, "label": "new van"}]})
    # by hand: the same items, week by week
    start = date(2026, 10, 5)
    hist = [r for r in rows if "2026-06-22" <= r["day"] <= "2026-10-04"]   # within 100 days before start, as the desk reads
    ms = sorted({r["day"][:7] for r in hist})[-3:]
    rec = CS.recurring(hist, ms)
    items = [(date(2026, 10, 22), 120000), (start, 30000), (date(2026, 10, 9), -45000), (date(2026, 11, 16), -500000)]
    for r in rec:
        for m in ("2026-10", "2026-11", "2026-12", "2027-01"):
            d = date(int(m[:4]), int(m[5:]), 1)
            last = ((d + timedelta(days=32)).replace(day=1) - timedelta(days=1)).day
            d = d.replace(day=min(r["day"], last))
            if d >= start:
                items.append((d, r["monthly_minor"]))
    bal = opening
    for k, wk in enumerate(f["weeks"]):
        a0 = start + timedelta(days=7 * k)
        bal += sum(v for d, v in items if a0 <= d <= a0 + timedelta(days=6))
        if _c(wk["closing"]) != bal:
            bad.append(f"week {k + 1} closing {wk['closing']} by hand {bal / 100:.2f}")
            break
    if "invoice " not in " ".join(f["overdue_invoices"]) or not any("Late Ltd" in x for x in f["overdue_invoices"]):
        bad.append("the overdue invoice was not put in week 1 and named")
    if f["under_minimum_weeks"] != [w["week"] for w in f["weeks"] if _c(w["closing"]) < 2000000]:
        bad.append("weeks under her minimum wrong")
    if _c(f["opening"]) != opening:
        bad.append(f"opening {f['opening']} by hand {opening / 100:.2f}")
    fee = CS.fees(t, ws, {})
    want_fee = -sum(r["amount_minor"] for r in rows if r["day"] >= "2026-06-01" and r["narration"] == "BANK CHARGE")
    if _c(fee["total"]) != want_fee:
        bad.append(f"bank fees {fee['total']} by hand {want_fee / 100:.2f}")
    return {"part": "cash", "country": "GB", "ok": not bad, "problems": bad[:12], "mean_error_pct": bt["mean_error_pct_of_spending"]}


def run(n: int = 12) -> dict[str, Any]:
    rows = []
    for i in range(n):
        cc = list(RULES)[i % 6]
        try:
            rows.append(payroll_one(i, cc))
        except Exception as e:     # a crash is a failed country, not a stopped card
            rows.append({"part": "payroll", "country": cc, "ok": False, "problems": [f"{type(e).__name__}: {e}"]})
    for i in range(max(1, n // 4)):
        try:
            rows.append(cash_one(i))
        except Exception as e:
            rows.append({"part": "cash", "country": "GB", "ok": False, "problems": [f"{type(e).__name__}: {e}"]})
    pay = [r for r in rows if r["part"] == "payroll"]
    return {"payrolls": len(pay), "countries": sorted({r["country"] for r in pay}), "passed": sum(r["ok"] for r in rows),
            "checks": len(rows), "ok": all(r["ok"] for r in rows), "rows": rows,
            "backtest_error_pct": [r.get("mean_error_pct") for r in rows if r["part"] == "cash"]}


def _scratch_db() -> None:
    import os
    import tempfile
    os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(tempfile.mkdtemp(prefix="card5_"), "card.db")
    os.environ["HOOLA_FIN_REVIEW_DIR"] = tempfile.mkdtemp(prefix="card5_review_")
    from ..config import get_settings
    get_settings.cache_clear()
    from .. import db
    db.init_db()


if __name__ == "__main__":
    _scratch_db()
    r = run(int(sys.argv[1]) if len(sys.argv) > 1 else 12)
    for x in r["rows"]:
        if not x["ok"]:
            print("FAIL", x["part"], x["country"], "; ".join(x["problems"]))
    print(f"F5 card: {r['passed']}/{r['checks']} ({r['payrolls']} payrolls in {len(r['countries'])} countries; backtest error "
          f"{r['backtest_error_pct']}% of spending)")
    sys.exit(0 if r["ok"] else 1)
