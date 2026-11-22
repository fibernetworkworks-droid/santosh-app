"""The F6 card: credit both sides (FINANCE_GLOBAL_PLAN phase F6).

APR for 10 countries' methods. For GB, DE, IE (EU / UK annual equivalent rate), US (actuarial), IN, AU, CA (nominal IRR) and SG, AE, SA
(effective IRR) the card makes loans from a seed - level payments with a fee taken from the loan, a fee paid separately, a balloon,
dated payments a month apart with real calendar days - and works each APR out itself by Newton's method from the same cash flows (a
different solver from the desk's), rounded by that method's rule; plus fixed textbook cases (1,000 repaid 12 x 88.85 = 12.00% US;
1,000 -> 1,200 in a year = 20.0% EU). The country -> method table is from memory; the card checks the arithmetic of each method.

MEMO FIGURES TRACED. A memo from figures with sources and from statement rows: every figure in the memo carries a source that exists,
every ratio recomputes from the two figures it names, the statement figures recompute from the rows they list, and a figure with no
source is refused.

CONTACT RULES. A sequence of planned collections contacts against Hoola's floor and her stricter rules: each is allowed or refused
exactly as the card expects - outside hours in the borrower's time zone, a second contact that day, a fourth that week, her no-contact
day, a third party, a threat, a legal word before the legal stage.

    python -m app.fin.card_f6        builds a scratch database, prints the card; exit 1 if anything fails
"""
from __future__ import annotations

import random
import re
import sys
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from . import profile as PR
from .desks import credit as CR

COUNTRIES = ["GB", "DE", "IE", "US", "IN", "AU", "CA", "SG", "AE", "SA"]
PPY = {"monthly": 12, "weekly": 52, "fortnightly": 26}


def _rd(x: float, places: int) -> float:
    return float(Decimal(str(x)).quantize(Decimal(1).scaleb(-places), ROUND_HALF_UP))


def _newton(f, df, x: float = 0.01) -> float:
    for _ in range(200):
        step = f(x) / df(x)
        x -= step
        if abs(step) < 1e-15:
            break
    return x


def hand_apr(received: float, pays: list[tuple[float, float]], ppy: int, method: str) -> float:
    if method == "eu_annual":
        f = lambda X: sum(p * (1 + X) ** (-t / ppy) for t, p in pays) - received                      # noqa: E731
        df = lambda X: sum(-t / ppy * p * (1 + X) ** (-t / ppy - 1) for t, p in pays)                  # noqa: E731
        return _rd(_newton(f, df, 0.1) * 100, 1)
    f = lambda r: sum(p * (1 + r) ** (-t) for t, p in pays) - received                                # noqa: E731
    df = lambda r: sum(-t * p * (1 + r) ** (-t - 1) for t, p in pays)                                 # noqa: E731
    i = _newton(f, df, 0.01)
    return _rd(i * ppy * 100, 2) if method in ("us_actuarial", "nominal_irr") else _rd(((1 + i) ** ppy - 1) * 100, 2)


def _level(amount: float, pct: float, n: int, ppy: int) -> float:
    i = Decimal(str(pct)) / 100 / ppy
    if i == 0:
        return float((Decimal(str(amount)) / n).quantize(Decimal("0.01"), ROUND_HALF_UP))
    v = Decimal(str(amount)) * i / (1 - (1 + i) ** -n)
    return float(v.quantize(Decimal("0.01"), ROUND_HALF_UP))


def apr_one(i: int, cc: str) -> dict[str, Any]:
    rnd = random.Random(6000 + i)
    m = CR.COUNTRY_METHOD[cc]
    bad: list[str] = []
    cases = 0
    for k in range(4):
        amt = round(rnd.uniform(1000, 60000), 2)
        rate = round(rnd.uniform(3, 39), 2)
        n = rnd.choice([6, 12, 24, 36, 60])
        freq = "weekly" if (cc == "AU" and k == 3) else "monthly"
        ppy = PPY[freq]
        fee = round(amt * rnd.uniform(0, 4) / 100, 2)
        a: dict[str, Any] = {"country": cc, "amount": amt, "rate": rate, "term": n, "frequency": freq, "fees_upfront": fee}
        pay = _level(amt, rate, n, ppy)
        pays = [(t + 1, pay) for t in range(n)]
        received = amt - fee
        if k == 1:                                   # the fee paid with the first payment, not taken from the loan
            a["fees_deducted"] = False
            received = amt
            pays = [(1, fee)] + pays
        if k == 2:                                   # a balloon at the end
            bal = round(amt * 0.2, 2)
            a["balloon"] = bal
            pays[-1] = (n, pay + bal)
        if k == 3 and freq == "monthly":             # dated payments: real calendar days / 365
            start = date(2026, 1, 31)
            a.pop("rate")
            a.pop("term")
            a["start"] = start.isoformat()
            pts = []
            for t in range(n):
                y, mo = 2026 + (t + 1) // 12, (t + 1) % 12 + 1
                last = (date(y + (mo == 12), mo % 12 + 1, 1) - timedelta(days=1)).day
                d = date(y, mo, min(31, last))
                pts.append({"date": d.isoformat(), "amount": pay})
            a["payments"] = pts
            pays = [((date.fromisoformat(p["date"]) - start).days / 365 * ppy, p["amount"]) for p in pts]
        got = CR.apr(a)
        want = hand_apr(received, pays, ppy, m)
        cases += 1
        if got["apr_pct"] != want or got["method"] != m:
            bad.append(f"{cc} case {k} ({m}) desk {got['apr_pct']} by hand {want}")
        if abs(got["total_paid"] - round(sum(p for _, p in pays), 2)) > 0.005:
            bad.append(f"{cc} case {k} total paid {got['total_paid']}")
        if "not confirmed" not in got["method_from"]:
            bad.append(f"{cc}: the country's method is not said to be unconfirmed")
    return {"part": "apr", "country": cc, "method": m, "cases": cases, "ok": not bad, "problems": bad}


def anchors() -> dict[str, Any]:
    bad = []
    if CR.apr({"method": "us_actuarial", "amount": 1000, "payment": 88.85, "term": 12})["apr_pct"] != 12.0:
        bad.append("US textbook 1,000 / 12 x 88.85 is not 12.00%")
    if CR.apr({"method": "eu_annual", "amount": 1000, "payments": [{"period": 12, "amount": 1200}]})["apr_pct"] != 20.0:
        bad.append("EU 1,000 -> 1,200 in a year is not 20.0%")
    if CR.apr({"method": "effective_irr", "amount": 1000, "payments": [{"period": 12, "amount": 1120}]})["apr_pct"] != 12.0:
        bad.append("effective: 1,000 -> 1,120 in a year is not 12.00%")
    try:
        CR.apr({"method": "nominal_irr", "amount": 1000, "payments": [{"period": 1, "amount": 900}]})
        bad.append("paying back less than received was given a rate")
    except CR.CreditError:
        pass
    return {"part": "apr anchors", "country": "-", "ok": not bad, "problems": bad}


# ---- memo ---------------------------------------------------------------------------------------------------------------------

def memo_one(i: int) -> dict[str, Any]:
    rnd = random.Random(8000 + i)
    bad: list[str] = []
    figs = {"revenue": rnd.uniform(5e5, 5e6), "ebitda": rnd.uniform(5e4, 8e5), "net_profit": rnd.uniform(1e4, 3e5),
            "interest": rnd.uniform(1e4, 9e4), "debt_service": rnd.uniform(5e4, 3e5), "current_assets": rnd.uniform(1e5, 9e5),
            "current_liabilities": rnd.uniform(5e4, 6e5), "total_debt": rnd.uniform(1e5, 2e6), "net_worth": rnd.uniform(1e5, 1e6)}
    figs = {k: round(v, 2) for k, v in figs.items()}
    srcs = ["audited accounts 2025 p.4", "audited accounts 2025 p.6", "management accounts Q2 2026"]
    given = {k: {"value": v, "source": srcs[j % 3]} for j, (k, v) in enumerate(figs.items())}
    rows = []
    for mo in range(1, 7):
        rows.append({"id": f"a{mo}", "date": f"2026-{mo:02d}-05", "narration": "SALARY ACME LTD", "amount": 4200.0})
        rows.append({"id": f"b{mo}", "date": f"2026-{mo:02d}-07", "narration": f"HOME LOAN EMI {mo}", "amount": -1100.0})
        rows.append({"id": f"c{mo}", "date": f"2026-{mo:02d}-15", "narration": "GROCERY", "amount": -round(rnd.uniform(200, 600), 2)})
    rows.append({"id": "x1", "date": "2026-04-09", "narration": "ECS RTN INSUFFICIENT FUNDS", "amount": -25.0})
    out = CR.memo("", "", {"borrower": "Test Co", "figures": given, "rows": rows, "opening": 1000, "policy": {"dscr": 1.25}})
    F, R, S = out["figures"], out["ratios"], out["sources"]
    for k, v in F.items():
        if v["source"] not in S:
            bad.append(f"figure {k} has source {v['source']} that is not listed")
        if k in figs and abs(v["value"] - figs[k]) > 1e-9:
            bad.append(f"figure {k} changed: {v['value']} vs {figs[k]}")
    for k, r in R.items():
        n, d = r["from"]
        unit = 100 if r["unit"] == "%" else 1
        want = float(Decimal(str(F[n]["value"] / F[d]["value"] * unit)).quantize(Decimal("0.1") if unit == 100 else Decimal("0.01"), ROUND_HALF_UP))
        if r["value"] != want:
            bad.append(f"ratio {k} {r['value']} by hand {want}")
        if sorted({F[n]["source"], F[d]["source"]}) != r["sources"]:
            bad.append(f"ratio {k} does not carry its figures' sources")
    by_id = {r["id"]: r for r in rows}
    for k, v in F.items():
        if "rows" in v:
            if any(x not in by_id for x in v["rows"]):
                bad.append(f"{k} points at rows that do not exist")
    if F["statement_regular_debt_payments_monthly"]["value"] != 1100.0 or sorted(F["statement_regular_debt_payments_monthly"]["rows"]) != [f"b{m}" for m in range(1, 7)]:
        bad.append(f"regular debt {F['statement_regular_debt_payments_monthly']}")
    if F["statement_bounced_items"]["value"] != 1 or F["statement_bounced_items"]["rows"] != ["x1"]:
        bad.append("the returned item is not traced")
    if F["statement_average_monthly_in"]["value"] != 4200.0:
        bad.append("average money in")
    section = ""
    for line in out["memo_markdown"].splitlines():          # every line in the Figures and Ratios sections is traced
        if line.startswith("## "):
            section = line[3:]
        if section in ("Figures", "Ratios") and line.startswith("- "):
            ref = re.findall(r"\[(S\d+(?:, S\d+)*)\]", line)
            if not ref or any(s.strip() not in S for s in ref[0].split(",")):
                bad.append(f"memo line without a valid source: {line}")
    try:
        CR.memo("", "", {"figures": {"revenue": {"value": 100}}})
        bad.append("a figure with no source was used")
    except CR.CreditError:
        pass
    dscr_bad = R["dscr"]["value"] < 1.25
    if dscr_bad != any("dscr" in f for f in out["policy_flags"]):
        bad.append("the DSCR policy flag is wrong")
    return {"part": "memo", "country": "-", "ok": not bad, "problems": bad}


# ---- contact rules ----------------------------------------------------------------------------------------------------------

def contact_one(i: int) -> dict[str, Any]:
    bad: list[str] = []
    t = f"card6-{i}"
    pv = PR.preview({"size": "business", "countries": ["GB"], "wants": [], "people": []})
    ans = {**pv["answers"], "currency": "GBP"}
    ws = PR.apply(t, ans, PR.preview(ans)["hash"])["id"]
    CR.run(t, "contact_rules", {"workspace": ws, "contact_rules": {"from_hour": 9, "to_hour": 23, "per_week": 5, "no_days": ["sun"],
                                                                   "source": "our collections policy"}})
    base = {"workspace": ws, "borrower": "Sam", "tz": "Asia/Kolkata", "channel": "call", "message": "A reminder that your payment is due."}
    # (when, changes, allowed?) - Monday 2026-09-07
    seq = [("2026-09-07T08:30", {}, False),            # before her 9:00 (stricter than the 8:00 floor)
           ("2026-09-07T21:30", {}, False),            # after the floor's 21:00 (her 23:00 is looser: the floor wins)
           ("2026-09-07T10:00", {}, True),
           ("2026-09-07T15:00", {}, False),            # a second that day
           ("2026-09-08T10:00", {"to": "employer"}, False),
           ("2026-09-08T10:00", {"message": "Pay today or we will tell your family."}, False),
           ("2026-09-08T10:00", {"message": "Pay or we take you to court."}, False),
           ("2026-09-08T10:00", {"message": "Pay or we take you to court.", "legal_stage": True}, True),
           ("2026-09-09T11:00", {"channel": "fax"}, False),
           ("2026-09-09T11:00", {}, True),
           ("2026-09-10T11:00", {}, False),            # the 4th this week: the floor allows 3
           ("2026-09-13T11:00", {}, False),            # Sunday, her no-contact day
           ("2026-09-14T11:00", {}, True),             # a new week
           ("2026-09-14T22:00", {"channel": "letter", "borrower": "Kim"}, True)]   # a letter is not held to calling hours
    for when, ch, ok in seq:
        try:
            CR.run(t, "collect", {**base, "when": when, **ch})
            got = True
        except CR.CreditError as e:
            got = False
            if "Refused" not in str(e):
                bad.append(f"{when} {ch}: refused without saying why: {e}")
        if got != ok:
            bad.append(f"{when} {ch}: {'allowed' if got else 'refused'}, expected {'allowed' if ok else 'refused'}")
    try:
        CR.run(t, "collect", {**base, "when": "2026-09-15T11:00", "tz": "Mars/Olympus"})
        bad.append("a contact with no real time zone was allowed")
    except CR.CreditError:
        pass
    return {"part": "contact rules", "country": "-", "cases": len(seq), "ok": not bad, "problems": bad}


def run(n: int = 10) -> dict[str, Any]:
    rows = []
    for i in range(n):
        cc = COUNTRIES[i % len(COUNTRIES)]
        try:
            rows.append(apr_one(i, cc))
        except Exception as e:    # a crash is a failed country, not a stopped card
            rows.append({"part": "apr", "country": cc, "ok": False, "problems": [f"{type(e).__name__}: {e}"]})
    for fn in (anchors, lambda: memo_one(0), lambda: memo_one(1), lambda: contact_one(0)):
        try:
            rows.append(fn())
        except Exception as e:
            rows.append({"part": "?", "country": "-", "ok": False, "problems": [f"{type(e).__name__}: {e}"]})
    apr_rows = [r for r in rows if r["part"] == "apr"]
    return {"checks": len(rows), "passed": sum(r["ok"] for r in rows), "ok": all(r["ok"] for r in rows),
            "countries": sorted({r["country"] for r in apr_rows}), "methods": sorted({r.get("method", "") for r in apr_rows}), "rows": rows}


def _scratch_db() -> None:
    import os
    import tempfile
    os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(tempfile.mkdtemp(prefix="card6_"), "card.db")
    os.environ["HOOLA_FIN_REVIEW_DIR"] = tempfile.mkdtemp(prefix="card6_review_")
    from ..config import get_settings
    get_settings.cache_clear()
    from .. import db
    db.init_db()


if __name__ == "__main__":
    _scratch_db()
    r = run(int(sys.argv[1]) if len(sys.argv) > 1 else 10)
    for x in r["rows"]:
        if not x["ok"]:
            print("FAIL", x["part"], x["country"], "; ".join(x["problems"][:6]))
    print(f"F6 card: {r['passed']}/{r['checks']} (APR in {len(r['countries'])} countries, methods {', '.join(r['methods'])})")
    sys.exit(0 if r["ok"] else 1)
