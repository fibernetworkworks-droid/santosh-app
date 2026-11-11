"""Paisa Sahayak LOAN reader and DEBT planner (register docs/research/banking_finance_industry #3 loan reader + comparator, #5 debt repayment planner).

Pure arithmetic: no database, no network, no model, nothing stored. The model never does these sums. What it will NOT do: tell anyone
which lender to pick, promise approval, or push a product. It shows the TOTAL COST so a person can decide. Every rate, fee and charge is
typed in by her from her own offer letter; the only default is the GST on a fee (18% on financial-service fees at the time of writing),
which is shown as ASSUMED and can be overwritten.
"""
from __future__ import annotations

from typing import Any

FEE_GST_DEFAULT = 18.0            # assumed; override with fee_gst_pct
FEE_FLAG_PCT = 2.0                # heuristic only: a processing fee above this share of the loan is worth asking to waive
MAX_MONTHS = 600


def _f(v: Any, name: str, lo: float | None = None) -> float:
    try:
        x = float(str(v).replace(",", "").strip())
    except (TypeError, ValueError):
        raise ValueError(f"{name}: give a number.") from None
    if lo is not None and x < lo:
        raise ValueError(f"{name} cannot be less than {lo}.")
    return x


def _r2(x: float) -> float:
    return round(x + 1e-9, 2)


def emi(principal: Any, annual_rate_pct: Any, months: Any) -> float:
    p, r, n = _f(principal, "loan amount", 0.01), _f(annual_rate_pct, "rate", 0), int(_f(months, "months", 1))
    if n > MAX_MONTHS:
        raise ValueError(f"Not more than {MAX_MONTHS} months.")
    i = r / 1200.0
    if i == 0:
        return _r2(p / n)
    return _r2(p * i * (1 + i) ** n / ((1 + i) ** n - 1))


def schedule(principal: Any, annual_rate_pct: Any, months: Any, lump: dict[str, Any] | None = None) -> dict[str, Any]:
    """Month-by-month reducing-balance schedule. `lump` = {month, amount, mode: reduce_tenure|reduce_emi} part-prepayment."""
    p, r, n = _f(principal, "loan amount", 0.01), _f(annual_rate_pct, "rate", 0), int(_f(months, "months", 1))
    i = r / 1200.0
    pay = emi(p, r, n)
    bal, rows, total_int = p, [], 0.0
    lm = int(lump["month"]) if lump and lump.get("month") else 0
    la = _f(lump["amount"], "prepayment", 0) if lump and lump.get("amount") else 0.0
    mode = (lump or {}).get("mode", "reduce_tenure")
    m = 0
    while bal > 0.005 and m < MAX_MONTHS:
        m += 1
        interest = _r2(bal * i)
        princ = min(bal, _r2(pay - interest)) if pay > interest else 0.0
        if pay <= interest and i > 0:
            raise ValueError("The EMI is less than the interest: the loan will never be paid off.")
        if bal - princ < 1.0 or m >= n and not (lm and m < lm):
            princ = bal                       # the last instalment absorbs the paise left by rounding
        extra = 0.0
        if lm and m == lm and la > 0 and bal - princ > 0:
            extra = min(la, _r2(bal - princ))
        paid = _r2(interest + princ + extra)
        bal = _r2(bal - princ - extra)
        total_int += interest
        rows.append({"month": m, "paid": paid, "interest": interest, "principal": _r2(princ + extra), "balance": max(bal, 0.0)})
        if extra and mode == "reduce_emi" and bal > 0:
            left = max(n - m, 1)
            pay = emi(bal, r, left)
    return {"emi": emi(p, r, n), "months": m, "total_interest": _r2(total_int), "total_paid": _r2(sum(x["paid"] for x in rows)), "rows": rows}


def _irr_monthly(flows: list[float]) -> float:
    """Monthly IRR of cash flows [t0, t1, ...] by bisection (+ at t0 = money received, - = paid)."""
    def npv(rate: float) -> float:
        return sum(f / (1 + rate) ** t for t, f in enumerate(flows))
    lo, hi = 0.0, 1.0
    if npv(lo) >= 0:
        return 0.0                      # nothing paid beyond what was received
    while npv(hi) < 0 and hi < 1e6:
        hi *= 2
    for _ in range(200):
        mid = (lo + hi) / 2
        if npv(mid) < 0:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def true_cost(principal: Any, annual_rate_pct: Any, months: Any, *, fee_pct: Any = 0, fee_fixed: Any = 0, fee_gst_pct: Any = None,
              insurance: Any = 0, other_upfront: Any = 0, fees_deducted: bool = True, balloon: Any = 0) -> dict[str, Any]:
    """What the loan REALLY costs: EMI, total paid, every fee, the money actually received, and the annualised rate on that money (APR)."""
    p, r, n = _f(principal, "loan amount", 0.01), _f(annual_rate_pct, "rate", 0), int(_f(months, "months", 1))
    gst = FEE_GST_DEFAULT if fee_gst_pct in (None, "") else _f(fee_gst_pct, "fee GST", 0)
    fee_base = p * _f(fee_pct, "processing fee %", 0) / 100.0 + _f(fee_fixed, "processing fee", 0)
    fee_gst = fee_base * gst / 100.0
    ins, oth = _f(insurance, "insurance", 0), _f(other_upfront, "other charges", 0)
    upfront = _r2(fee_base + fee_gst + ins + oth)
    pay = emi(p, r, n)
    bal = _f(balloon, "balloon", 0)
    received = p - upfront if fees_deducted else p
    sched = schedule(p, r, n)
    pays = [x["paid"] for x in sched["rows"]]
    flows = [received] + [0.0] * len(pays)
    for k, v in enumerate(pays):
        flows[k + 1] -= v
    if not fees_deducted:
        flows[1] -= upfront               # fees paid with the first instalment: still a cost
    if bal:
        flows[-1] -= bal
    im = _irr_monthly(flows)
    total_paid = sched["total_paid"] + bal
    flags = []
    if p and (fee_base / p) * 100 > FEE_FLAG_PCT:
        flags.append({"kind": "heuristic", "text": f"The processing fee is {round(fee_base / p * 100, 2)}% of the loan (>{FEE_FLAG_PCT}%): ask for it to be reduced or waived."})
    if ins:
        flags.append({"kind": "measured", "text": f"Insurance Rs {ins:,.2f} is bundled with the loan: ask whether it is required or whether you can buy your own insurance."})
    if bal:
        flags.append({"kind": "measured", "text": f"At the end, a balloon payment of Rs {bal:,.2f}: until then the EMIs do not fully pay off the loan."})
    if upfront and fees_deducted:
        flags.append({"kind": "measured", "text": f"Rs {upfront:,.2f} is deducted upfront: you receive Rs {received:,.2f} in hand, but interest runs on Rs {p:,.2f}."})
    return {"principal": _r2(p), "emi": pay, "months": n, "stated_rate_pct": r, "fee_before_gst": _r2(fee_base), "fee_gst": _r2(fee_gst),
            "fee_gst_pct": gst, "gst_note": "The GST rate is assumed (18%): match it with your offer letter." if fee_gst_pct in (None, "") else "",
            "insurance": _r2(ins), "other_upfront": _r2(oth), "upfront_total": upfront, "money_received": _r2(received),
            "total_interest": sched["total_interest"], "total_paid": _r2(total_paid),
            "total_cost": _r2(total_paid - p + upfront),
            "apr_nominal_pct": round(im * 1200.0, 2), "apr_effective_pct": round(((1 + im) ** 12 - 1) * 100.0, 2), "flags": flags,
            "note": "APR is the rate you pay on the money you ACTUALLY receive (after all fees). Calculation only: not advice from any lender."}


def flat_to_reducing(flat_rate_pct: Any, months: Any) -> dict[str, Any]:
    """A 'flat rate' quote charges interest on the full amount for the whole time; the true (reducing-balance) rate is much higher."""
    fr, n = _f(flat_rate_pct, "flat rate", 0), int(_f(months, "months", 1))
    p = 100000.0
    pay = p * (1 + fr / 100.0 * n / 12.0) / n
    flows = [p] + [-pay] * n
    im = _irr_monthly(flows)
    return {"flat_rate_pct": fr, "months": n, "emi_per_lakh": _r2(pay), "reducing_rate_pct": round(im * 1200.0, 2),
            "effective_rate_pct": round(((1 + im) ** 12 - 1) * 100.0, 2), "total_interest_per_lakh": _r2(pay * n - p),
            "note": "A flat rate means interest on the full amount for the full term. The real (reducing) rate is much higher than this."}


def compare(offers: list[dict[str, Any]]) -> dict[str, Any]:
    if not isinstance(offers, list) or len(offers) < 2:
        raise ValueError("Give at least two offers (name, amount, rate, months, fees).")
    rows = []
    for k, o in enumerate(offers[:8], 1):
        c = true_cost(o.get("amount"), o.get("rate"), o.get("months"), fee_pct=o.get("fee_pct", 0), fee_fixed=o.get("fee_fixed", 0),
                      fee_gst_pct=o.get("fee_gst_pct"), insurance=o.get("insurance", 0), other_upfront=o.get("other_upfront", 0),
                      fees_deducted=o.get("fees_deducted", True) is not False, balloon=o.get("balloon", 0))
        rows.append({"name": str(o.get("name") or f"Offer {k}")[:60], **{k2: c[k2] for k2 in (
            "principal", "months", "emi", "stated_rate_pct", "upfront_total", "money_received", "total_paid", "total_cost", "apr_effective_pct", "flags")}})
    like = len({(r["principal"], r["months"]) for r in rows}) == 1
    order = sorted(rows, key=lambda r: (r["apr_effective_pct"], r["total_cost"]))
    return {"offers": rows, "lowest_apr": order[0]["name"], "lowest_total_cost": min(rows, key=lambda r: r["total_cost"])["name"],
            "like_for_like": like, "note": ("The amounts / terms differ: only APR compares them on equal footing, not total cost." if not like else
                                          "The amount and term are the same: look at both the lower APR and the lower total cost.") +
            " This is only a calculation; which one to take is your decision (and the lender's approval)."}


def prepay(principal: Any, annual_rate_pct: Any, months: Any, lump_amount: Any, at_month: Any, mode: str = "reduce_tenure",
           charge_pct: Any = 0) -> dict[str, Any]:
    base = schedule(principal, annual_rate_pct, months)
    after = schedule(principal, annual_rate_pct, months, {"month": int(_f(at_month, "which month", 1)), "amount": lump_amount,
                                                           "mode": "reduce_emi" if mode == "reduce_emi" else "reduce_tenure"})
    charge = _r2(_f(lump_amount, "prepayment", 0) * _f(charge_pct, "prepayment charge %", 0) / 100.0)
    saved = _r2(base["total_interest"] - after["total_interest"])
    return {"before": {"months": base["months"], "total_interest": base["total_interest"], "emi": base["emi"]},
            "after": {"months": after["months"], "total_interest": after["total_interest"]}, "interest_saved": saved,
            "prepayment_charge": charge, "net_saving": _r2(saved - charge), "months_saved": base["months"] - after["months"],
            "worth_it": saved > charge,
            "note": "The charge is what you gave (from your loan agreement). It often does not apply to floating-rate loans: check the agreement."}


def debt_plan(debts: list[dict[str, Any]], extra_monthly: Any = 0, income_drop_pct: Any = 0) -> dict[str, Any]:
    """Snowball (smallest balance first) vs avalanche (highest rate first) vs minimums only. All numbers hers."""
    if not isinstance(debts, list) or not debts:
        raise ValueError("Give the list of debts: for each, the name, balance, rate and minimum payment.")
    base = []
    for k, d in enumerate(debts[:15], 1):
        bal = _f(d.get("balance"), "balance", 0.01)
        rate = _f(d.get("rate"), "rate", 0)
        mn = _f(d.get("min_payment"), "minimum payment", 0)
        base.append({"name": str(d.get("name") or f"Karz {k}")[:50], "balance": bal, "rate": rate, "min": mn})
    extra = _f(extra_monthly, "extra", 0)
    drop = _f(income_drop_pct, "income drop %", 0)
    budget = (sum(d["min"] for d in base) + extra) * (1 - drop / 100.0)
    shortfall = max(sum(d["min"] for d in base) - budget, 0.0)

    def run(order_key, use_budget: float):
        ds = [dict(d) for d in base]
        month, interest, paid_off = 0, 0.0, {}
        while any(d["balance"] > 0.005 for d in ds) and month < MAX_MONTHS:
            month += 1
            for d in ds:
                if d["balance"] > 0:
                    x = d["balance"] * d["rate"] / 1200.0
                    d["balance"] += x
                    interest += x
            pool = use_budget
            live = [d for d in ds if d["balance"] > 0.005]
            for d in live:
                pay = min(d["min"], d["balance"], pool)
                d["balance"] -= pay
                pool -= pay
            for d in sorted([d for d in ds if d["balance"] > 0.005], key=order_key):
                if pool <= 0:
                    break
                pay = min(pool, d["balance"])
                d["balance"] -= pay
                pool -= pay
            for d in ds:
                if d["balance"] <= 0.005 and d["name"] not in paid_off:
                    paid_off[d["name"]] = month
        done = all(d["balance"] <= 0.005 for d in ds)
        return {"months": month if done else None, "total_interest": _r2(interest) if done else None, "payoff_month": paid_off,
                "debt_free": done}
    mins_only = run(lambda d: d["balance"], sum(d["min"] for d in base))
    snow = run(lambda d: d["balance"], budget)
    aval = run(lambda d: -d["rate"], budget)
    flags = []
    for d in base:
        if d["rate"] and d["min"] < d["balance"] * d["rate"] / 1200.0:
            flags.append({"kind": "measured", "text": f"{d['name']}: the minimum payment is less than even the interest: the balance will keep growing."})
    if shortfall > 0:
        flags.append({"kind": "measured", "text": f"With this drop even the minimums are not covered: Rs {_r2(shortfall):,.2f} short every month. You need to talk to the lender / restructure, or get credit counselling."})
    return {"budget_monthly": _r2(budget), "debts": [{"name": d["name"], "balance": _r2(d["balance"]), "rate": d["rate"], "min": _r2(d["min"])} for d in base],
            "minimums_only": mins_only, "snowball": snow, "avalanche": aval,
            "interest_saved_avalanche_vs_snowball": (_r2(snow["total_interest"] - aval["total_interest"]) if snow["debt_free"] and aval["debt_free"] else None),
            "flags": flags,
            "note": "Avalanche usually costs less interest; snowball clears small debts quickly and keeps you motivated. Which one is up to you. This is a calculation, not advice; if you need credit counselling, go to an RBI-recognised agency (check)."}
