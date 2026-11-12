"""#60 goal planner + advance-tax calendar (#11 slice). SIP maths and date arithmetic only; rates are scenarios she can change, never promises."""
from __future__ import annotations

import datetime as dt
from typing import Any

SCENARIOS = {"low": 6.0, "mid": 9.0, "high": 12.0}  # ASSUMED annual returns, labelled in every output


def _n(v: Any, name: str, lo: float = 0.0) -> float:
    try:
        x = float(v)
    except (TypeError, ValueError):
        raise ValueError(f"{name} must be a number.")
    if x < lo:
        raise ValueError(f"{name} cannot be less than {lo:g}.")
    return x


def _fv_sip(sip: float, r_annual: float, months: int, current: float = 0.0) -> float:
    i = r_annual / 1200.0
    if i == 0:
        return current + sip * months
    g = (1 + i) ** months
    return current * g + sip * ((g - 1) / i) * (1 + i)  # SIP at start of month


def goal(target: Any, years: Any, current: Any = 0, inflation: Any = 6, rates: dict | None = None, today_value: Any = True) -> dict[str, Any]:
    t, y, cur, inf = _n(target, "target", 1), _n(years, "years", 0.25), _n(current, "current"), _n(inflation, "inflation")
    months = max(1, int(round(y * 12)))
    need = t * (1 + inf / 100.0) ** y if today_value is not False else t
    rs = dict(SCENARIOS)
    for k, v in (rates or {}).items():
        rs[str(k)] = _n(v, f"rate {k}")
    rows = []
    for name, r in rs.items():
        i = r / 1200.0
        grown = cur * (1 + i) ** months
        gap = max(0.0, need - grown)
        g = (1 + i) ** months
        sip = gap / (((g - 1) / i) * (1 + i)) if i else gap / months
        rows.append({"scenario": name, "annual_return_pct": r, "monthly_sip_needed": round(sip, 2), "current_grows_to": round(grown, 2),
                     "check_fv": round(_fv_sip(sip, r, months, cur), 2)})
    return {"goal_amount": t, "years": y, "inflation_pct": inf, "amount_needed_then": round(need, 2),
            "inflation_note": "The target was taken as today's value; the value on that date is given above." if today_value is not False else "The target was taken as the value on that date.",
            "scenarios": rows,
            "assumed": "Returns are ONLY scenarios (low/mid/high ASSUMED), not a promise; the real return can be higher or lower, and can fall.",
            "decider": "Choosing a product or portfolio is for you / a registered adviser; this is only a calculation, not advice."}


# advance tax: cumulative share due by date (individual non-presumptive). FROM MEMORY: verify on incometax.gov.in.
_ADV = [((6, 15), 15), ((9, 15), 45), ((12, 15), 75), ((3, 15), 100)]


def advance_tax(liability: Any, fy_start_year: Any, tds: Any = 0) -> dict[str, Any]:
    li, tdsv = _n(liability, "liability"), _n(tds, "tds")
    y = int(_n(fy_start_year, "fy_start_year", 2000))
    net = max(0.0, li - tdsv)
    out, prev = [], 0.0
    for (m, d), pct in _ADV:
        yr = y + 1 if m <= 3 else y
        cum = round(net * pct / 100.0, 2)
        out.append({"due": dt.date(yr, m, d).isoformat(), "cumulative_pct": pct, "cumulative_amount": cum, "this_instalment": round(cum - prev, 2)})
        prev = cum
    return {"fy": f"{y}-{str(y + 1)[2:]}", "tax_after_tds": round(net, 2), "instalments": out, "verify": True,
            "note": "Dates and % are from memory (verify: true): check on incometax.gov.in. Not for those who owe no advance tax at all (e.g. tax under Rs 10,000).",
            "decider": "The final tax and filing are done by your CA / you."}
