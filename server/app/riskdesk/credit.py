"""#32 underwriter's assistant, #36 key fact statement, #39 past-due ageing, #92 ECL working paper. HER rules and HER inputs; the decision is a person's."""
from __future__ import annotations

import datetime as dt
import operator
from typing import Any

from ..finguard import loans as LN

# Fair lending: a rule may not be written on these (or on proxies). Refused, not ignored.
PROTECTED = {"religion", "caste", "gender", "sex", "community", "race", "marital_status", "pincode", "locality", "area", "surname", "tribe", "disability"}
_OPS = {">": operator.gt, ">=": operator.ge, "<": operator.lt, "<=": operator.le, "==": operator.eq, "!=": operator.ne}


def underwrite(applicant: dict, rules: list[dict]) -> dict[str, Any]:
    if not isinstance(applicant, dict) or not applicant:
        raise ValueError("Give applicant details.")
    if not rules:
        raise ValueError("Give rules: [{field, op, value, code, severity}]. They are your policy's rules; we have no built-in rules.")
    a = dict(applicant)
    inc, obl, emi = _n(a.get("income_monthly")), _n(a.get("obligations_monthly")), _n(a.get("requested_emi"))
    if inc:
        a["foir_pct"] = round(100 * (obl + emi) / inc, 1)
    hits, exceptions, missing = [], [], []
    for r in rules[:200]:
        f = str(r.get("field") or "").strip().lower()
        if f in PROTECTED or any(p in f for p in PROTECTED):
            raise ValueError(f"A rule cannot be built on '{f}': it is a ground for discrimination (or a proxy for one).")
        op = _OPS.get(str(r.get("op")))
        if not op:
            raise ValueError(f"op: {', '.join(_OPS)}")
        if f not in a or a[f] in (None, ""):
            missing.append({"field": f, "code": r.get("code")})
            continue
        try:
            left, right = (float(a[f]), float(r.get("value")))
        except (TypeError, ValueError):
            left, right = a[f], r.get("value")
        if not op(left, right):                           # the rule is the REQUIREMENT; a miss is a hit
            h = {"code": r.get("code") or f, "field": f, "required": f"{r.get('op')} {r.get('value')}", "actual": a[f], "severity": r.get("severity", "refer")}
            hits.append(h)
            if h["severity"] != "info":
                exceptions.append(h["code"])
    return {"applicant_fields_used": sorted({str(r.get("field")).lower() for r in rules}), "foir_pct": a.get("foir_pct"), "rule_hits": hits,
            "exceptions": exceptions, "missing_inputs": missing, "rules_run": len(rules) - len(missing),
            "reason_codes": [h["code"] for h in hits],
            "note": "Every hit is a reason code that can be explained to the customer. 'hit' = a rule you gave was not met.",
            "not_checked": "Whether the bureau report is true, whether documents are genuine, collateral, fraud, KYC.",
            "decider": "Approving / rejecting the loan is the credit officer's / committee's. There is no decision, score or 'approve' here."}


def _n(v: Any) -> float:
    try:
        return float(str(v).replace(",", ""))
    except (TypeError, ValueError):
        return 0.0


def kfs(lender: str, borrower: str, product: str, amount: Any, rate: Any, months: Any, fee_pct: Any = 0, fee_fixed: Any = 0, insurance: Any = 0,
        other_upfront: Any = 0, cooling_off_days: Any = None, grievance: str = "") -> dict[str, Any]:
    tc = LN.true_cost(amount, rate, months, fee_pct=fee_pct, fee_fixed=fee_fixed, insurance=insurance, other_upfront=other_upfront)
    md = ["# Key Fact Statement (DRAFT)", f"**Lender:** {lender or '[lender]'}  **Borrower:** {borrower or '[borrower]'}  **Product:** {product or '[product]'}",
          "| Item | Value |", "|---|---|", f"| Loan amount | {_n(amount):,.2f} |", f"| Interest rate (annual, reducing) | {_n(rate)}% |",
          f"| Tenure | {int(_n(months))} months |", f"| EMI | {tc.get('emi')} |", f"| Total interest | {tc.get('total_interest')} |",
          f"| Upfront charges | {tc.get('upfront_total', tc.get('upfront'))} |", f"| Money actually received | {tc.get('money_received')} |",
          f"| APR (on money received) | {tc.get('apr_nominal_pct')}% |", f"| Total paid | {tc.get('total_paid')} |",
          f"| Cooling-off / look-up period | {cooling_off_days if cooling_off_days else '[days: lender policy]'} |",
          f"| Grievance officer | {grievance or '[name, phone, email]'} |", "| Recovery agent / LSP details | [fill in] |", "| Penal charges | [fill in] |",
          "", "Sanction and signature are the authorised person's job. [ ] = what was not found here."]
    return {"kfs_markdown": "\n".join(md), "computed": tc,
            "not_checked": "The format of every field set by the regulator and the lender's own policy: you must check these.",
            "decider": "Issuing the sanction letter / KFS is the authorised person's; this is only a draft."}


def dpd(accounts: list[dict], as_of: Any = None, npa_days: Any = 90) -> dict[str, Any]:
    if not accounts:
        raise ValueError("Give accounts rows: id, outstanding, oldest_due_date.")
    today = dt.date.fromisoformat(str(as_of)[:10]) if as_of else dt.date.today()
    npa = int(_n(npa_days))
    buckets = {"standard(0)": 0.0, "SMA-0(1-30)": 0.0, "SMA-1(31-60)": 0.0, "SMA-2(61-90)": 0.0, "NPA-suggested": 0.0}
    rows = []
    for ac in accounts[:5000]:
        out = _n(ac.get("outstanding"))
        try:
            days = max(0, (today - dt.date.fromisoformat(str(ac.get("oldest_due_date"))[:10])).days)
        except (TypeError, ValueError):
            raise ValueError(f"Could not read the date: {ac.get('oldest_due_date')}")
        b = ("standard(0)" if days == 0 else "SMA-0(1-30)" if days <= 30 else "SMA-1(31-60)" if days <= 60 else "SMA-2(61-90)" if days <= npa else "NPA-suggested")
        buckets[b] += out
        rows.append({"id": ac.get("id"), "outstanding": out, "dpd": days, "bucket": b})
    return {"as_of": today.isoformat(), "buckets": {k: round(v, 2) for k, v in buckets.items()}, "accounts": sorted(rows, key=lambda r: -r["dpd"]), "npa_days_used": npa,
            "verify": True, "note": "The SMA bands and the 90-day NPA rule are from memory; match them with your regulator's latest circular. This is a suggestion, not a classification.",
            "not_checked": "Restructuring, moratorium, the effect of part payments, borrower-wise (not account-wise) counting.",
            "decider": "Declaring an NPA and the notice / SARFAESI / IBC steps are the recovery and legal teams'; nothing was sent here."}


def ecl(exposures: list[dict], stage2_dpd: Any = 30, stage3_dpd: Any = 90) -> dict[str, Any]:
    if not exposures:
        raise ValueError("Give exposures rows: ead, pd (0-1), lgd (0-1), dpd (or stage).")
    by = {1: 0.0, 2: 0.0, 3: 0.0}
    rows, flags = [], []
    for e in exposures[:20000]:
        ead, pd_, lgd = _n(e.get("ead")), _n(e.get("pd")), _n(e.get("lgd"))
        if not (0 <= pd_ <= 1 and 0 <= lgd <= 1):
            raise ValueError("pd and lgd must be between 0 and 1 (for example 0.02).")
        st = int(e["stage"]) if e.get("stage") else (3 if _n(e.get("dpd")) > _n(stage3_dpd) else 2 if _n(e.get("dpd")) > _n(stage2_dpd) else 1)
        use = pd_
        if st == 2:
            if e.get("pd_lifetime") is None:
                flags.append(f"{e.get('id', '?')}: no lifetime PD found at stage 2; the 12-month PD was used (ECL may be understated).")
            else:
                use = _n(e.get("pd_lifetime"))
        elif st == 3:
            use = 1.0
        v = round(ead * use * lgd, 2)
        by[st] += v
        rows.append({"id": e.get("id"), "stage": st, "ead": ead, "pd_used": use, "lgd": lgd, "ecl": v})
    return {"total_ecl": round(sum(by.values()), 2), "by_stage": {f"stage{k}": round(v, 2) for k, v in by.items()}, "rows": rows, "flags": flags,
            "method": "ECL = EAD x PD x LGD (stage 1: 12-month PD; stage 2: lifetime PD where given; stage 3: PD = 1). Discounting and macro adjustment are not included.",
            "verify": True, "not_checked": "Whether the PD / LGD model is right, forward-looking adjustment, discounting.",
            "decider": "The provision figure is approved by the risk committee and checked by the auditor; this is a working paper."}
