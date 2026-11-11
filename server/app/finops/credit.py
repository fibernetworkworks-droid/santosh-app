"""#34 credit memo drafter: ratios from the financials she gives, a memo with blanks. The committee approves; nothing here scores a borrower or says approve / decline."""
from __future__ import annotations

from typing import Any


def _f(v: Any) -> float:
    try:
        return float(str(v).replace(",", ""))
    except (TypeError, ValueError):
        return 0.0


def _div(a: float, b: float):
    return round(a / b, 2) if b else None


def ratios(fin: dict) -> dict[str, Any]:
    if not isinstance(fin, dict) or not fin:
        raise ValueError("financials do: revenue, ebitda, net_profit, interest, debt_service (instalments due), current_assets, current_liabilities, total_debt, net_worth.")
    ebitda, ds = _f(fin.get("ebitda")), _f(fin.get("debt_service"))
    r = {"current_ratio": _div(_f(fin.get("current_assets")), _f(fin.get("current_liabilities"))),
         "debt_to_equity": _div(_f(fin.get("total_debt")), _f(fin.get("net_worth"))),
         "interest_cover": _div(ebitda, _f(fin.get("interest"))),
         "dscr": _div(ebitda, ds) if ds else _div(_f(fin.get("net_profit")) + _f(fin.get("depreciation")) + _f(fin.get("interest")), _f(fin.get("interest")) + _f(fin.get("repayment"))),
         "ebitda_margin_pct": round(100 * ebitda / _f(fin.get("revenue")), 1) if _f(fin.get("revenue")) else None,
         "net_margin_pct": round(100 * _f(fin.get("net_profit")) / _f(fin.get("revenue")), 1) if _f(fin.get("revenue")) else None}
    return r


def memo(borrower: str, fin: dict, purpose: str = "", amount: Any = None, years: list[dict] | None = None, policy: dict | None = None) -> dict[str, Any]:
    rt = ratios(fin)
    flags = []
    pol = policy or {}  # HER policy floors, never ours
    for k, op in (("current_ratio", "min"), ("dscr", "min"), ("interest_cover", "min"), ("debt_to_equity", "max")):
        lim = pol.get(k)
        v = rt.get(k)
        if lim is None or v is None:
            continue
        if (op == "min" and v < _f(lim)) or (op == "max" and v > _f(lim)):
            flags.append(f"{k} {v} is outside your policy ({op} {lim}).")
    trend = []
    if years and len(years) >= 2:
        a, b = years[-2], years[-1]
        for k in ("revenue", "ebitda", "net_profit"):
            if _f(a.get(k)):
                trend.append(f"{k}: {100 * (_f(b.get(k)) - _f(a.get(k))) / _f(a.get(k)):+.1f}% (from the previous year)")
    md = ["# Credit memo (DRAFT)", f"**Borrower:** {borrower or '[name]'}", f"**Purpose / amount:** {purpose or '[purpose]'} / {amount if amount else '[amount]'}",
          "## Numbers (from the financials you gave)"] + [f"- {k}: {v if v is not None else 'denominator not found'}" for k, v in rt.items()]
    md += ["## Trend"] + ([f"- {t}" for t in trend] or ["- [give year-on-year numbers]"])
    md += ["## Policy check"] + ([f"- {f}" for f in flags] or ["- " + ("no policy floors were given" if not pol else "within the floors given")])
    md += ["## Still to be filled in here (analyst)", "- Management / promoter background: [ ]", "- Industry and competition: [ ]", "- Security / collateral and value: [ ]",
           "- Proposed covenants / conditions: [ ]", "- Main risks and mitigants: [ ]", "- Sanction recommendation: [credit officer]"]
    return {"memo_markdown": "\n".join(md), "ratios": rt, "policy_flags": flags, "trend": trend,
            "not_checked": "Whether the financials are true (audited?), CIBIL / bureau, GST-to-bank flow matching, collateral value: these were not checked.",
            "decider": "Sanction / decline belongs to the credit committee. This draft gives no score and no 'approve'."}
