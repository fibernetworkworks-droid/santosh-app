"""F6 of docs/FINANCE_GLOBAL_PLAN.md - Credit & Lending, both sides (employee `credit`, tool `credit_lending`), any country.

Borrower (people, sole traders, businesses):
  apr          the APR of a loan by a country's method: the EU / UK annual equivalent rate (actual days, one decimal), the US actuarial
               method (unit-period rate x periods), a nominal IRR (rate x periods: India's KFS, Australia's comparison rate shape, Canada) or
               an effective IRR (Singapore's EIR shape). Which method a country uses is from memory (not confirmed) unless she names it.
  shop         loan offers side by side: APR by her country's method, total cost, money in hand; cheapest by total cost.
  invoice_finance  an invoice advance or factoring offer: money now, fee, days -> what it really costs a year.
  readiness    the business-loan readiness pack from her own statements and books: 12 months in / out, the lowest balance, regular
               debts, bounced items, profit from her books, the papers a lender will ask for.

Lender (businesses, firms, institutions; the decision is always a named person's):
  analyse      a borrower's statement: income by month, regular debts, bounced / returned items, every figure traced to the rows.
  memo         a credit memo where every figure carries its source (the borrower's document and page, or the statement rows);
               ratios worked out from those figures; a figure with no source is refused.
  rules        hits against HER credit policy rules (rules on protected grounds refused).
  kfs          a key-facts / disclosure draft with the APR by the country's method.
  conditions   documents and conditions-precedent checklist: received / missing / waived (by whom).
  servicing    a loan's schedule against what was paid: arrears, days past due, the next due.
  collect      a collections contact checked BEFORE it is made, against Hoola's floor and her (stricter) contact rules: hours in the
               borrower's time zone, contacts a day / week, no third parties, the words in the message. A breach is refused; an allowed
               contact is logged as planned - Hoola never sends it.
  ews          early-warning signals from repayments and statements.
  ecl          ECL working paper (EAD x PD x LGD by stage).

Not credit advice; no loan is approved, declined or paid out here."""
from __future__ import annotations

import json
import re
from collections import defaultdict
from datetime import date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from .. import laws as L
from .. import pack as P


class CreditError(ValueError):
    pass


DECIDER = "The decision belongs to the named credit officer or committee; Hoola gives no score and no approve / decline."
NOT_CONFIRMED = " (not confirmed - check this)"
PPY = {"monthly": 12, "fortnightly": 26, "weekly": 52, "quarterly": 4, "yearly": 1}

# which APR method a country uses - from memory, status verify
COUNTRY_METHOD = {"GB": "eu_annual", "DE": "eu_annual", "IE": "eu_annual", "US": "us_actuarial", "IN": "nominal_irr",
                  "AU": "nominal_irr", "CA": "nominal_irr", "SG": "effective_irr", "AE": "effective_irr", "SA": "effective_irr"}
METHODS = {
    "eu_annual": "annual equivalent rate: every payment discounted at (1 + X) to the power of its time in years from the drawdown "
                 "(actual days / 365, or months / 12); one decimal",
    "us_actuarial": "actuarial method: the rate per payment period x the periods in a year; two decimals",
    "nominal_irr": "the rate per period on the money actually received x the periods in a year; two decimals",
    "effective_irr": "the rate per period on the money actually received compounded over a year; two decimals",
}


def _f(v: Any, what: str, lo: float | None = None) -> float:
    try:
        x = float(str(v).replace(",", ""))
    except (TypeError, ValueError):
        raise CreditError(f"{what}: a number.")
    if lo is not None and x < lo:
        raise CreditError(f"{what}: not below {lo}.")
    return x


def _d(s: Any, what: str) -> date:
    try:
        return date.fromisoformat(str(s)[:10])
    except ValueError:
        raise CreditError(f"{what}: a date as YYYY-MM-DD.")


def _r(x: float, places: int) -> float:
    return float(Decimal(str(x)).quantize(Decimal(1).scaleb(-places), ROUND_HALF_UP))


def _add_months(d: date, n: int) -> date:
    y, m = d.year + (d.month - 1 + n) // 12, (d.month - 1 + n) % 12 + 1
    last = (date(y + (m == 12), m % 12 + 1, 1) - timedelta(days=1)).day
    return d.replace(year=y, month=m, day=min(d.day, last))


# ---- APR -----------------------------------------------------------------------------------------------------------------------

def _solve(f, lo: float = -0.99, hi: float = 10.0) -> float:
    """f decreasing in the rate; bisection to well past the rounding the methods need."""
    if f(lo) < 0:
        raise CreditError("The payments are less than the money received: there is no positive rate.")
    while f(hi) > 0 and hi < 1e6:
        hi *= 2
    for _ in range(300):
        mid = (lo + hi) / 2
        if f(mid) > 0:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def level_payment(amount: float, annual_pct: float, n: int, ppy: int) -> float:
    i = annual_pct / 100 / ppy
    if i == 0:
        return round(amount / n, 2)
    return round(amount * i / (1 - (1 + i) ** -n), 2)


def _flows(a: dict[str, Any]) -> tuple[float, list[tuple[float, float]], int, str, list[str]]:
    """-> money received at time 0, [(time in periods, payment)], periods a year, schedule note, lines explaining."""
    amount = _f(a.get("amount"), "amount", 0.01)
    freq = a.get("frequency") or "monthly"
    if freq not in PPY:
        raise CreditError("frequency: " + " | ".join(PPY))
    ppy = PPY[freq]
    fees = sum(_f(x, "fees") for x in (a.get("fees_upfront"), a.get("fee_fixed")) if x not in (None, ""))
    if a.get("fee_pct"):
        fees += amount * _f(a["fee_pct"], "fee_pct", 0) / 100
    received = amount - fees if a.get("fees_deducted", True) else amount
    how = [f"loan {amount:,.2f}", f"upfront charges {fees:,.2f}" + (" taken from the loan" if a.get("fees_deducted", True) else "")]
    pays: list[tuple[float, float]] = []
    start = _d(a["start"], "start") if a.get("start") else None
    if a.get("payments"):
        for k, p in enumerate(a["payments"]):
            if p.get("date"):
                if not start:
                    raise CreditError("start: the drawdown date, when payments carry dates.")
                t = (_d(p["date"], f"payments[{k}].date") - start).days / 365 * ppy
            else:
                t = _f(p.get("period", k + 1), f"payments[{k}].period", 0)
            pays.append((t, _f(p.get("amount"), f"payments[{k}].amount", 0)))
        how.append(f"{len(pays)} payments you gave, total {sum(x for _, x in pays):,.2f}")
    else:
        n = int(_f(a.get("term"), "term (number of payments)", 1))
        pay = _f(a["payment"], "payment") if a.get("payment") else level_payment(amount, _f(a.get("rate"), "rate (annual %)", 0), n, ppy)
        pays = [(k + 1, pay) for k in range(n)]
        if a.get("balloon"):
            pays[-1] = (n, pay + _f(a["balloon"], "balloon", 0))
        how.append(f"{n} {freq} payments of {pay:,.2f}" + (f" + balloon {_f(a['balloon'], 'balloon'):,.2f}" if a.get("balloon") else ""))
    if not a.get("fees_deducted", True) and fees:
        pays.insert(0, (pays[0][0], fees))
    return received, pays, ppy, freq, how


def apr_of(received: float, pays: list[tuple[float, float]], ppy: int, method: str) -> float:
    if method not in METHODS:
        raise CreditError("method: " + " | ".join(METHODS))
    if sum(p for _, p in pays) <= received:
        raise CreditError("The payments are not more than the money received: there is no positive rate.")
    if method == "eu_annual":
        x = _solve(lambda X: sum(p / (1 + X) ** (t / ppy) for t, p in pays) - received)
        return _r(x * 100, 1)
    i = _solve(lambda r: sum(p / (1 + r) ** t for t, p in pays) - received)
    if method in ("us_actuarial", "nominal_irr"):
        return _r(i * ppy * 100, 2)
    return _r(((1 + i) ** ppy - 1) * 100, 2)


def _method(a: dict[str, Any]) -> tuple[str, str]:
    if a.get("method"):
        if a["method"] not in METHODS:
            raise CreditError("method: " + " | ".join(METHODS))
        return a["method"], "the method you chose"
    cc = str(a.get("country") or "").upper()
    if cc not in COUNTRY_METHOD:
        raise CreditError("country (ISO code) or method " + " | ".join(METHODS) + ": which APR method to use.")
    law = P.peek(cc, "consumer_credit.apr_method")
    return COUNTRY_METHOD[cc], f"{cc}: {law or 'its usual method'}" + NOT_CONFIRMED


def apr(a: dict[str, Any]) -> dict[str, Any]:
    m, why = _method(a)
    received, pays, ppy, freq, how = _flows(a)
    total = sum(p for _, p in pays)
    return {"apr_pct": apr_of(received, pays, ppy, m), "method": m, "method_is": METHODS[m], "method_from": why,
            "money_received": round(received, 2), "total_paid": round(total, 2), "cost_of_credit": round(total - received, 2),
            "how": how, "says": "Worked out from the payments; the lender's own figure on the offer must match it."}


def shop(a: dict[str, Any]) -> dict[str, Any]:
    offers = a.get("offers") or []
    if len(offers) < 1:
        raise CreditError("offers: [{name, amount, rate, term, fee_pct, fees_upfront, payment, frequency}].")
    rows = []
    for k, o in enumerate(offers[:12]):
        r = apr({**{x: a[x] for x in ("country", "method") if a.get(x)}, **o})
        rows.append({"name": str(o.get("name") or f"offer {k + 1}")[:60], "apr_pct": r["apr_pct"], "total_paid": r["total_paid"],
                     "money_received": r["money_received"], "cost_of_credit": r["cost_of_credit"]})
    rows.sort(key=lambda x: x["cost_of_credit"])
    return {"offers": rows, "cheapest_by_total_cost": rows[0]["name"], "method_from": _method(a)[1],
            "says": "Compared on what you would really pay. Not advice: also read each offer's terms (early repayment, late fees)."}


def invoice_finance(a: dict[str, Any]) -> dict[str, Any]:
    face = _f(a.get("invoice"), "invoice (amount)", 0.01)
    adv = face * _f(a.get("advance_pct", 80), "advance_pct", 0) / 100
    fee = _f(a.get("fee", 0), "fee") + face * _f(a.get("fee_pct", 0), "fee_pct", 0) / 100
    days = _f(a.get("days"), "days (until your customer pays)", 1)
    disc = adv * _f(a.get("discount_rate_pct", 0), "discount_rate_pct", 0) / 100 * days / 365
    cost = fee + disc
    received = adv - fee
    year = ((1 + cost / received) ** (365 / days) - 1) * 100 if received > 0 else None
    return {"advance": round(adv, 2), "money_now": round(received, 2), "cost": round(cost, 2),
            "cost_a_year_pct": _r(year, 2) if year is not None else None,
            "simple_a_year_pct": _r(cost / received * 365 / days * 100, 2) if received > 0 else None,
            "how": f"{cost:,.2f} for {received:,.2f} over {days:g} days, compounded to a year",
            "says": "Compare it with an overdraft or a loan's APR; ask whether the customer pays the financier or you (recourse)."}


# ---- borrower readiness + statement analysis -----------------------------------------------------------------------------------

_BOUNCE = re.compile(r"return|bounce|insufficient|dishono|unpaid|reversal|nsf|chq rtn|ecs rtn", re.I)
_DEBT = re.compile(r"\bemi\b|loan|repayment|mortgage|finance|credit card|\bcc\b|lease", re.I)
_SALARY = re.compile(r"salary|payroll|wages|stipend", re.I)


def _rows(tenant: str, ws: str, a: dict[str, Any]) -> list[dict[str, Any]]:
    if a.get("rows"):
        out = []
        for k, r in enumerate(a["rows"][:5000]):
            amt = _f(r.get("amount"), f"rows[{k}].amount")
            out.append({"id": str(r.get("id") or f"r{k + 1}"), "day": str(_d(r.get("date"), f"rows[{k}].date")), "amount": amt,
                        "narration": str(r.get("narration") or "")[:200]})
        return out
    if not ws:
        raise CreditError("rows [{date, narration, amount}] or a workspace with her statements.")
    from .. import spine as SP
    return [{"id": r["id"], "day": r["day"], "amount": float(r["amount"]), "narration": r["narration"]}
            for r in SP.txns(tenant, ws, since=str(a.get("since") or ""), until=str(a.get("upto") or ""), limit=5000)]


def analyse(tenant: str, ws: str, a: dict[str, Any]) -> dict[str, Any]:
    rows = sorted(_rows(tenant, ws, a), key=lambda r: (r["day"], r["id"]))
    if not rows:
        raise CreditError("No statement rows.")
    months: dict[str, dict[str, Any]] = defaultdict(lambda: {"in": 0.0, "out": 0.0, "in_rows": [], "out_rows": []})
    bounces, debts, salary = [], defaultdict(lambda: {"total": 0.0, "rows": [], "months": set()}), []
    bal = _f(a.get("opening", 0), "opening")
    low = (bal, "opening")
    for r in rows:
        m = months[r["day"][:7]]
        side = "in" if r["amount"] > 0 else "out"
        m[side] += abs(r["amount"])
        m[side + "_rows"].append(r["id"])
        bal += r["amount"]
        if bal < low[0]:
            low = (round(bal, 2), r["id"])
        if _BOUNCE.search(r["narration"]):
            bounces.append({"row": r["id"], "day": r["day"], "narration": r["narration"], "amount": r["amount"]})
        elif r["amount"] < 0 and _DEBT.search(r["narration"]):
            key = " ".join(re.sub(r"[\d/#:.-]+", " ", r["narration"].lower()).split()[:3])
            d = debts[key]
            d["total"] += -r["amount"]
            d["rows"].append(r["id"])
            d["months"].add(r["day"][:7])
        elif r["amount"] > 0 and _SALARY.search(r["narration"]):
            salary.append({"row": r["id"], "day": r["day"], "amount": r["amount"]})
    n = len(months)
    fig: dict[str, dict[str, Any]] = {}
    fig["months_read"] = {"value": n, "rows": [], "how": "months with at least one row"}
    tin = sum(m["in"] for m in months.values())
    tout = sum(m["out"] for m in months.values())
    fig["average_monthly_in"] = {"value": round(tin / n, 2), "rows": [x for m in months.values() for x in m["in_rows"]],
                                 "how": f"{tin:,.2f} money in / {n} months"}
    fig["average_monthly_out"] = {"value": round(tout / n, 2), "rows": [x for m in months.values() for x in m["out_rows"]],
                                  "how": f"{tout:,.2f} money out / {n} months"}
    reg = {k: v for k, v in debts.items() if len(v["months"]) >= 2}
    obl = sum(v["total"] / n for v in reg.values())
    fig["regular_debt_payments_monthly"] = {"value": round(obl, 2), "rows": [x for v in reg.values() for x in v["rows"]],
                                            "how": "debt-like payments seen in 2 or more months, averaged over the months read"}
    fig["bounced_items"] = {"value": len(bounces), "rows": [b["row"] for b in bounces], "how": "returned / unpaid items by their words"}
    fig["lowest_balance"] = {"value": low[0], "rows": [low[1]] if low[1] != "opening" else [], "how": "running balance from the opening you gave"}
    if salary:
        fig["salary_monthly"] = {"value": round(sum(s["amount"] for s in salary) / n, 2), "rows": [s["row"] for s in salary],
                                 "how": "salary-like credits averaged over the months read"}
    return {"by_month": {k: {"in": round(v["in"], 2), "out": round(v["out"], 2)} for k, v in sorted(months.items())},
            "figures": fig, "bounced": bounces, "regular_debts": [{"what": k, "monthly": round(v["total"] / n, 2), "months": len(v["months"])}
                                                               for k, v in reg.items()],
            "says": "Every figure lists the statement rows it came from. The words used to sort rows can miss or catch the wrong line."}


def readiness(tenant: str, ws: str, a: dict[str, Any]) -> dict[str, Any]:
    if not ws:
        raise CreditError("workspace: her finance workspace.")
    since = str(a.get("since") or (date.today() - timedelta(days=365)).isoformat())
    an = analyse(tenant, ws, {**a, "since": since})
    out: dict[str, Any] = {"statements": an}
    from ..calc import from_minor
    from ..profile import get as _get
    from . import books as B
    bal = B.balances(tenant, ws, upto=str(a.get("upto") or date.today().isoformat()), since=since)
    kind = {c["code"]: c["type"] for c in B.coa(tenant, ws)}
    income = -sum(v for k, v in bal.items() if kind.get(k) == "income")
    cost = sum(v for k, v in bal.items() if kind.get(k) == "expense")
    out["books"] = None
    if income or cost:
        cur = str(_get(tenant, ws).get("currency") or "USD")
        out["books"] = {"income": float(from_minor(income, cur)), "costs": float(from_minor(cost, cur)),
                        "profit": float(from_minor(income - cost, cur)), "from": "your Books & Accounts for the same months"}
    f = an["figures"]
    gaps = []
    if f["months_read"]["value"] < 12:
        gaps.append(f"only {f['months_read']['value']} months of statements - lenders usually ask for 6 to 12")
    if f["bounced_items"]["value"]:
        gaps.append(f"{f['bounced_items']['value']} returned items - be ready to explain each")
    if not out.get("books"):
        gaps.append("no profit and loss from your books - add your invoices and bills in Books & Accounts")
    out.update({"papers_a_lender_asks_for": ["bank statements (6-12 months)", "profit and loss and balance sheet (2 years if you have them)",
                                             "tax returns", "identity and business registration", "list of existing loans and what you pay",
                                             "what the loan is for and how it will be repaid"],
                "gaps": gaps, "says": "Your own figures, ready to show a lender. Hoola does not apply for the loan."})
    return out


# ---- the memo ----------------------------------------------------------------------------------------------------------------

_RATIOS = {"current_ratio": ("current_assets", "current_liabilities", "x"), "debt_to_equity": ("total_debt", "net_worth", "x"),
           "interest_cover": ("ebitda", "interest", "x"), "dscr": ("ebitda", "debt_service", "x"),
           "ebitda_margin_pct": ("ebitda", "revenue", "%"), "net_margin_pct": ("net_profit", "revenue", "%"),
           "debt_to_income": ("obligations_monthly", "income_monthly", "%")}


def memo(tenant: str, ws: str, a: dict[str, Any]) -> dict[str, Any]:
    """figures: {name: {value, source}} - each figure needs where it came from (document + page, or 'statement'). Statement rows
    given with analyse=true add the statement figures, traced to row ids."""
    src: list[str] = []
    figs: dict[str, dict[str, Any]] = {}
    for k, v in (a.get("figures") or {}).items():
        if not isinstance(v, dict) or v.get("value") in (None, "") or not str(v.get("source") or "").strip():
            raise CreditError(f"figures.{k}: {{value, source}} - a figure with no source is not used in a memo.")
        s = str(v["source"])[:120]
        if s not in src:
            src.append(s)
        figs[str(k)] = {"value": _f(v["value"], f"figures.{k}"), "source": f"S{src.index(s) + 1}"}
    if a.get("rows") or a.get("analyse"):
        an = analyse(tenant, ws, a)
        src.append("bank statement rows " + (f"{an['by_month'] and min(an['by_month'])} to {max(an['by_month'])}"))
        sid = f"S{len(src)}"
        for k, v in an["figures"].items():
            figs.setdefault("statement_" + k, {"value": v["value"], "source": sid, "rows": v["rows"]})
        if "income_monthly" not in figs and "statement_average_monthly_in" in figs:
            figs["income_monthly"] = dict(figs["statement_average_monthly_in"])
        if "obligations_monthly" not in figs:
            figs["obligations_monthly"] = dict(figs["statement_regular_debt_payments_monthly"])
    if not figs:
        raise CreditError("figures {name: {value, source}} and / or statement rows.")
    ratios = {}
    for name, (n, d, unit) in _RATIOS.items():
        if n in figs and d in figs and figs[d]["value"]:
            v = figs[n]["value"] / figs[d]["value"] * (100 if unit == "%" else 1)
            ratios[name] = {"value": _r(v, 1 if unit == "%" else 2), "unit": unit, "from": [n, d],
                            "sources": sorted({figs[n]["source"], figs[d]["source"]})}
    pol = a.get("policy") or {}
    flags = []
    for k, lim in pol.items():
        if k in ratios:
            low_is_bad = k not in ("debt_to_equity", "debt_to_income")
            v = ratios[k]["value"]
            if (low_is_bad and v < _f(lim, f"policy.{k}")) or (not low_is_bad and v > _f(lim, f"policy.{k}")):
                flags.append(f"{k} {v} is outside your policy ({'min' if low_is_bad else 'max'} {lim})")
    md = ["# Credit memo (DRAFT)", f"**Borrower:** {a.get('borrower') or '[name]'}   **Asked for:** {a.get('amount') or '[amount]'} "
          f"for {a.get('purpose') or '[purpose]'}", "", "## Figures"]
    for k, v in figs.items():
        md.append(f"- {k}: {v['value']:,.2f} [{v['source']}]")
    md += ["", "## Ratios"]
    for k, v in ratios.items():
        md.append(f"- {k}: {v['value']}{'%' if v['unit'] == '%' else 'x'} = {v['from'][0]} / {v['from'][1]} [{', '.join(v['sources'])}]")
    md += ["", "## Against your policy"] + ([f"- {x}" for x in flags] or ["- " + ("no policy limits given" if not pol else "within your limits")])
    md += ["", "## For the analyst to write", "- Who the borrower is and the business: [ ]", "- Security and its value: [ ]",
           "- Risks and how they are covered: [ ]", "- Conditions / covenants proposed: [ ]", "", "## Sources"]
    md += [f"- S{i + 1}: {s}" for i, s in enumerate(src)]
    md += ["", DECIDER]
    return {"memo_markdown": "\n".join(md), "figures": figs, "ratios": ratios, "sources": {f"S{i + 1}": s for i, s in enumerate(src)},
            "policy_flags": flags, "decider": DECIDER}


def rules(a: dict[str, Any]) -> dict[str, Any]:
    from ...riskdesk import credit as RC
    try:
        return RC.underwrite(a.get("applicant") or {}, a.get("rules") or [])
    except ValueError as e:
        raise CreditError(str(e))


def kfs(a: dict[str, Any]) -> dict[str, Any]:
    from ...riskdesk import credit as RC
    r = apr(a)
    try:
        k = RC.kfs(a.get("lender", ""), a.get("borrower", ""), a.get("product", ""), a.get("amount"), a.get("rate", 0), a.get("term"),
                   a.get("fee_pct", 0), a.get("fees_upfront", 0) or 0, 0, 0, a.get("cooling_off_days"), a.get("grievance", ""))
    except ValueError as e:
        raise CreditError(str(e))
    k["kfs_markdown"] += f"\n\nAPR by {r['method']} ({r['method_from']}): {r['apr_pct']}%"
    k["apr"] = r
    return k


def conditions(a: dict[str, Any]) -> dict[str, Any]:
    items = a.get("items") or []
    if not items:
        raise CreditError("items: [{name, status received|missing|waived, waived_by, due}].")
    out, today = [], _d(a.get("today") or date.today().isoformat(), "today")
    for k, x in enumerate(items[:200]):
        st = x.get("status") or "missing"
        if st not in ("received", "missing", "waived"):
            raise CreditError(f"items[{k}].status: received | missing | waived.")
        if st == "waived" and not x.get("waived_by"):
            raise CreditError(f"items[{k}]: a waived condition needs who waived it (waived_by).")
        row = {"name": str(x.get("name") or "")[:120], "status": st}
        if x.get("waived_by"):
            row["waived_by"] = str(x["waived_by"])[:80]
        if x.get("due"):
            row["due"] = str(_d(x["due"], f"items[{k}].due"))
            row["late"] = st == "missing" and _d(x["due"], "due") < today
        out.append(row)
    missing = [x["name"] for x in out if x["status"] == "missing"]
    return {"items": out, "missing": missing, "ready_to_draw": not missing,
            "says": ("All conditions received or waived. " if not missing else f"{len(missing)} still missing. ") + DECIDER}


def servicing(a: dict[str, Any]) -> dict[str, Any]:
    amount, n = _f(a.get("amount"), "amount", 0.01), int(_f(a.get("term"), "term", 1))
    start = _d(a.get("start"), "start (first due date)")
    pay = _f(a["payment"], "payment") if a.get("payment") else level_payment(amount, _f(a.get("rate"), "rate"), n, 12)
    today = _d(a.get("today") or date.today().isoformat(), "today")
    paid = sum(_f(p.get("amount"), "paid.amount") for p in a.get("paid") or [] if _d(p.get("date"), "paid.date") <= today)
    due_dates = [_add_months(start, k) for k in range(n)]
    due_now = [d for d in due_dates if d <= today]
    owed = round(pay * len(due_now), 2)
    arrears = round(max(0.0, owed - paid), 2)
    covered = int((Decimal(str(paid)) / Decimal(str(pay))).to_integral_value(rounding="ROUND_FLOOR")) if pay else 0
    oldest = due_dates[covered] if arrears > 0 and covered < len(due_dates) else None
    return {"payment": pay, "due_so_far": owed, "paid_so_far": round(paid, 2), "arrears": arrears,
            "days_past_due": (today - oldest).days if oldest else 0, "oldest_unpaid_due": oldest.isoformat() if oldest else None,
            "next_due": next((d.isoformat() for d in due_dates if d > today), None), "instalments_left": n - len(due_now)}


# ---- collections contact rules ------------------------------------------------------------------------------------------------

FLOOR = {"from_hour": 8, "to_hour": 21, "per_day": 1, "per_week": 3, "no_days": [], "channels": ["call", "sms", "email", "letter", "whatsapp"]}
_THREATS = re.compile(r"\b(police|arrest|jail|prison|criminal|warrant|shame|humiliat|your family|your employer|your boss|your neighbou?rs|"
                      r"we will tell|seize|confiscat|ruin you|blacklist(ed)? for life|kill|hurt|beat)\w*", re.I)
_LEGAL = re.compile(r"\b(court|legal action|lawsuit|sue|summons)\b", re.I)
DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


def _settings(tenant: str, ws: str) -> dict[str, Any]:
    from ..profile import ProfileError, get
    try:
        return dict(((get(tenant, ws).get("settings") or {}).get("credit")) or {})
    except ProfileError as e:
        raise CreditError(str(e))


def _save(tenant: str, ws: str, change) -> Any:
    from ... import db
    from ..models import FinWorkspace, ensure
    ensure()
    with db.session() as s:
        row = s.get(FinWorkspace, ws)
        if not row or row.tenant_id != tenant:
            raise CreditError("No such workspace.")
        st = json.loads(row.settings or "{}")
        out = change(st.setdefault("credit", {}))
        row.settings = json.dumps(st)
        s.commit()
    return out


def contact_rules(tenant: str, ws: str, a: dict[str, Any]) -> dict[str, Any]:
    r = dict(a.get("contact_rules") or {})
    mine: dict[str, Any] = {}
    for k in ("from_hour", "to_hour", "per_day", "per_week"):
        if r.get(k) is not None:
            mine[k] = int(_f(r[k], f"contact_rules.{k}", 0))
    if r.get("no_days"):
        bad = [d for d in r["no_days"] if str(d).lower()[:3] not in DAYS]
        if bad:
            raise CreditError("no_days: mon tue wed thu fri sat sun.")
        mine["no_days"] = [str(d).lower()[:3] for d in r["no_days"]]
    if r.get("channels"):
        mine["channels"] = [c for c in r["channels"] if c in FLOOR["channels"]]
    if r.get("source"):
        mine["source"] = str(r["source"])[:160]
    if not mine:
        raise CreditError("contact_rules: from_hour, to_hour, per_day, per_week, no_days, channels, source.")
    _save(tenant, ws, lambda c: c.__setitem__("contact_rules", mine))
    return {"contact_rules": mine, "effective": _effective(mine),
            "says": "Your rules can only be stricter than Hoola's floor; where a rule is looser, the floor wins."}


def _effective(mine: dict[str, Any]) -> dict[str, Any]:
    return {"from_hour": max(FLOOR["from_hour"], mine.get("from_hour", 0)), "to_hour": min(FLOOR["to_hour"], mine.get("to_hour", 24)),
            "per_day": min(FLOOR["per_day"], mine.get("per_day", 99)), "per_week": min(FLOOR["per_week"], mine.get("per_week", 99)),
            "no_days": sorted(set(FLOOR["no_days"]) | set(mine.get("no_days") or [])),
            "channels": [c for c in FLOOR["channels"] if c in (mine.get("channels") or FLOOR["channels"])]}


def collect(tenant: str, ws: str, a: dict[str, Any]) -> dict[str, Any]:
    if not ws:
        raise CreditError("workspace: the lender's finance workspace (her contact log lives there).")
    from zoneinfo import ZoneInfo
    cfg = _settings(tenant, ws)
    eff = _effective(cfg.get("contact_rules") or {})
    who = str(a.get("borrower") or "").strip()
    if not who:
        raise CreditError("borrower: who is being contacted.")
    try:
        tz = ZoneInfo(str(a.get("tz") or ""))
    except Exception:
        raise CreditError("tz: the borrower's time zone (e.g. Asia/Kolkata, Europe/London) - hours are checked where they live.")
    try:
        when = datetime.fromisoformat(str(a.get("when"))).replace(tzinfo=None)
    except ValueError:
        raise CreditError("when: the borrower's local time YYYY-MM-DDTHH:MM.")
    ch = str(a.get("channel") or "")
    to = str(a.get("to") or "borrower")
    msg = str(a.get("message") or "")
    no: list[str] = []
    if to != "borrower":
        no.append("only the borrower may be contacted about the debt - never family, employer, neighbours or friends")
    if ch not in eff["channels"]:
        no.append(f"channel {ch or '(none)'} is not allowed: {', '.join(eff['channels'])}")
    if ch in ("call", "sms", "whatsapp") and not (eff["from_hour"] <= when.hour < eff["to_hour"]):
        no.append(f"{when:%H:%M} is outside {eff['from_hour']:02d}:00-{eff['to_hour']:02d}:00 in {tz.key}")
    if DAYS[when.weekday()] in eff["no_days"]:
        no.append(f"no contact on {DAYS[when.weekday()]}")
    log = [x for x in cfg.get("contacts") or [] if x["borrower"].lower() == who.lower()]
    day = when.date().isoformat()
    wk0 = (when.date() - timedelta(days=when.weekday())).isoformat()
    wk1 = (when.date() - timedelta(days=when.weekday()) + timedelta(days=6)).isoformat()
    if sum(1 for x in log if x["when"][:10] == day) >= eff["per_day"]:
        no.append(f"already {eff['per_day']} contact(s) that day")
    if sum(1 for x in log if wk0 <= x["when"][:10] <= wk1) >= eff["per_week"]:
        no.append(f"already {eff['per_week']} contacts that week")
    t = _THREATS.search(msg)
    if t:
        no.append(f"the message threatens or shames ('{t.group(0)}') - never allowed")
    if _LEGAL.search(msg) and not a.get("legal_stage"):
        no.append("the message mentions court or legal action, but the account is not at the legal stage (legal_stage)")
    if no:
        raise CreditError("Refused - this contact would break the contact rules: " + "; ".join(no) + ".")
    rec = {"borrower": who, "when": when.isoformat(timespec="minutes"), "tz": tz.key, "channel": ch, "planned": True}
    _save(tenant, ws, lambda c: c.setdefault("contacts", []).append(rec) or c.__setitem__("contacts", c["contacts"][-5000:]))
    return {"contact": rec, "rules_used": eff,
            "says": "Allowed and logged as planned. Hoola does not send it: the person collecting sends it, in your name."}


def ews(a: dict[str, Any]) -> dict[str, Any]:
    sig = []
    hist = [int(_f(x, "dpd_history")) for x in a.get("dpd_history") or []]
    if len(hist) >= 2 and hist[-1] > hist[-2]:
        sig.append({"signal": "days past due rising", "detail": f"{hist[-2]} -> {hist[-1]}"})
    if a.get("rows"):
        an = analyse("", "", a)
        bm = list(an["by_month"].values())
        if len(bm) >= 4:
            prev = sum(m["in"] for m in bm[-4:-1]) / 3
            if prev and bm[-1]["in"] < prev * (1 - _f(a.get("inflow_drop_pct", 30), "inflow_drop_pct") / 100):
                sig.append({"signal": "money in dropped", "detail": f"{bm[-1]['in']:,.2f} vs {prev:,.2f} average of the 3 months before"})
        if an["figures"]["bounced_items"]["value"]:
            sig.append({"signal": "returned items", "detail": f"{an['figures']['bounced_items']['value']} in the statement"})
    for c in a.get("covenants_breached") or []:
        sig.append({"signal": "covenant breached", "detail": str(c)[:80]})
    return {"signals": sig, "watch": bool(sig), "says": "Signals to look at, not a classification. " + DECIDER}


def ecl(a: dict[str, Any]) -> dict[str, Any]:
    from ...riskdesk import credit as RC
    try:
        return RC.ecl(a.get("exposures") or [], a.get("stage2_dpd", 30), a.get("stage3_dpd", 90))
    except ValueError as e:
        raise CreditError(str(e))


ACTIONS = ("apr", "shop", "invoice_finance", "readiness", "analyse", "memo", "rules", "kfs", "conditions", "servicing",
           "contact_rules", "collect", "ews", "ecl", "methods")


def run(tenant: str, action: str, a: dict[str, Any], actor: str = "owner") -> dict[str, Any]:
    a = dict(a)
    ws = str(a.get("workspace") or "")
    if re.search(r"approve|decline|disburse", action):
        raise L.Refused("approve_decision", DECIDER)
    f = {"apr": lambda: apr(a), "shop": lambda: shop(a), "invoice_finance": lambda: invoice_finance(a),
         "readiness": lambda: readiness(tenant, ws, a), "analyse": lambda: analyse(tenant, ws, a), "memo": lambda: memo(tenant, ws, a),
         "rules": lambda: rules(a), "kfs": lambda: kfs(a), "conditions": lambda: conditions(a), "servicing": lambda: servicing(a),
         "contact_rules": lambda: contact_rules(tenant, ws, a), "collect": lambda: collect(tenant, ws, a), "ews": lambda: ews(a),
         "ecl": lambda: ecl(a), "methods": lambda: {"methods": METHODS, "countries": {k: v + NOT_CONFIRMED for k, v in COUNTRY_METHOD.items()}}}
    if action not in f:
        raise CreditError("action: " + ", ".join(ACTIONS))
    if action in ("contact_rules",) and not ws:
        raise CreditError("workspace: the finance workspace.")
    out = f[action]()
    out.setdefault("not_advice", L.NOT_ADVICE)
    return out
