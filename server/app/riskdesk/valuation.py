"""#112 valuation worksheet: DCF + sensitivity from the investor's / valuer's own inputs. A model of her assumptions, not a price opinion."""
from __future__ import annotations

from typing import Any


def _n(v: Any, name: str) -> float:
    try:
        return float(str(v).replace(",", ""))
    except (TypeError, ValueError):
        raise ValueError(f"{name} must be a number.")


def _value(cfs: list[float], r: float, g: float) -> tuple[float, float, float]:
    pv = sum(cf / (1 + r) ** (i + 1) for i, cf in enumerate(cfs))
    tv = cfs[-1] * (1 + g) / (r - g)
    pvtv = tv / (1 + r) ** len(cfs)
    return pv + pvtv, pv, pvtv


def dcf(cashflows: list, discount_pct: Any, terminal_growth_pct: Any, net_debt: Any = 0, shares: Any = None, step_pct: Any = 1) -> dict[str, Any]:
    cfs = [_n(c, "cashflow") for c in (cashflows or [])]
    if len(cfs) < 2:
        raise ValueError("cashflows: give free cash flow for at least 2 years.")
    r, g, st = _n(discount_pct, "discount_pct") / 100.0, _n(terminal_growth_pct, "terminal_growth_pct") / 100.0, _n(step_pct, "step_pct") / 100.0
    if r <= g:
        raise ValueError("The discount rate must be higher than the terminal growth.")
    ev, pv, pvtv = _value(cfs, r, g)
    nd = _n(net_debt, "net_debt")
    eq = ev - nd
    out: dict[str, Any] = {"enterprise_value": round(ev, 2), "pv_explicit": round(pv, 2), "pv_terminal": round(pvtv, 2),
                           "terminal_share_pct": round(100 * pvtv / ev, 1) if ev else None, "equity_value": round(eq, 2)}
    if shares:
        out["per_share"] = round(eq / _n(shares, "shares"), 2)
    grid = []
    for dr in (-2, -1, 0, 1, 2):
        row = {"discount_pct": round((r + dr * st) * 100, 2), "equity_value": []}
        for dg in (-1, 0, 1):
            rr, gg = r + dr * st, g + dg * st
            row["equity_value"].append({"growth_pct": round(gg * 100, 2), "value": round(_value(cfs, rr, gg)[0] - nd, 2) if rr > gg else None})
        grid.append(row)
    out["sensitivity"] = grid
    out["flags"] = ([f"The terminal value is {out['terminal_share_pct']}% of the total value: it depends heavily on assumptions."] if out["terminal_share_pct"] and out["terminal_share_pct"] > 75 else [])
    out["not_checked"] = "Whether the cash flow estimates are right, comparables, the share's liquidity / control discount, tax."
    out["decider"] = "A registered valuer gives the opinion and signs; this is an arithmetic worksheet of your assumptions, not an opinion on value."
    return out
