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
        raise ValueError("applicant details do.")
    if not rules:
        raise ValueError("rules do: [{field, op, value, code, severity}]. Apni policy ke niyam; hamare paas koi built-in niyam nahi.")
    a = dict(applicant)
    inc, obl, emi = _n(a.get("income_monthly")), _n(a.get("obligations_monthly")), _n(a.get("requested_emi"))
    if inc:
        a["foir_pct"] = round(100 * (obl + emi) / inc, 1)
    hits, exceptions, missing = [], [], []
    for r in rules[:200]:
        f = str(r.get("field") or "").strip().lower()
        if f in PROTECTED or any(p in f for p in PROTECTED):
            raise ValueError(f"Niyam '{f}' par nahi ban sakta: yeh bhedbhaav ka aadhaar (ya uska pratinidhi) hai.")
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
            "note": "Har hit ek kaaran-code hai jo graahak ko samjhaaya ja sake. 'hit' = aapka diya niyam poora nahi hua.",
            "not_checked": "Bureau ki report ki sachchai, documents ki asliyat, collateral, fraud, KYC.",
            "decider": "Loan manzoor / namanzoor credit officer / committee ka hai. Yahan koi faisla, score ya 'approve' nahi."}


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
          f"| Grievance officer | {grievance or '[naam, phone, email]'} |", "| Recovery agent / LSP details | [bharein] |", "| Penal charges | [bharein] |",
          "", "Sanction aur dastakhat adhikrit vyakti ka kaam hai. [ ] = jo yahan nahi mila."]
    return {"kfs_markdown": "\n".join(md), "computed": tc,
            "not_checked": "Regulator ke tay kiye hue har khaane ka format aur lender ki apni policy: yeh aapko jaanchna hai.",
            "decider": "Sanction letter / KFS jaari karna adhikrit vyakti ka hai; yeh sirf draft hai."}


def dpd(accounts: list[dict], as_of: Any = None, npa_days: Any = 90) -> dict[str, Any]:
    if not accounts:
        raise ValueError("accounts rows do: id, outstanding, oldest_due_date.")
    today = dt.date.fromisoformat(str(as_of)[:10]) if as_of else dt.date.today()
    npa = int(_n(npa_days))
    buckets = {"standard(0)": 0.0, "SMA-0(1-30)": 0.0, "SMA-1(31-60)": 0.0, "SMA-2(61-90)": 0.0, "NPA-suggested": 0.0}
    rows = []
    for ac in accounts[:5000]:
        out = _n(ac.get("outstanding"))
        try:
            days = max(0, (today - dt.date.fromisoformat(str(ac.get("oldest_due_date"))[:10])).days)
        except (TypeError, ValueError):
            raise ValueError(f"Tareekh samajh nahi aayi: {ac.get('oldest_due_date')}")
        b = ("standard(0)" if days == 0 else "SMA-0(1-30)" if days <= 30 else "SMA-1(31-60)" if days <= 60 else "SMA-2(61-90)" if days <= npa else "NPA-suggested")
        buckets[b] += out
        rows.append({"id": ac.get("id"), "outstanding": out, "dpd": days, "bucket": b})
    return {"as_of": today.isoformat(), "buckets": {k: round(v, 2) for k, v in buckets.items()}, "accounts": sorted(rows, key=lambda r: -r["dpd"]), "npa_days_used": npa,
            "verify": True, "note": "SMA bands aur 90-din ka NPA niyam yaad se hain; apne regulator ke taaza circular se milaiye. Yeh suggestion hai, classification nahi.",
            "not_checked": "Restructuring, moratorium, partial payment ka asar, borrower-wise (account nahi) ginti.",
            "decider": "NPA ghoshit karna aur notice / SARFAESI / IBC ke kadam recovery aur legal team ke hain; yahan kuch nahi bheja gaya."}


def ecl(exposures: list[dict], stage2_dpd: Any = 30, stage3_dpd: Any = 90) -> dict[str, Any]:
    if not exposures:
        raise ValueError("exposures rows do: ead, pd (0-1), lgd (0-1), dpd (ya stage).")
    by = {1: 0.0, 2: 0.0, 3: 0.0}
    rows, flags = [], []
    for e in exposures[:20000]:
        ead, pd_, lgd = _n(e.get("ead")), _n(e.get("pd")), _n(e.get("lgd"))
        if not (0 <= pd_ <= 1 and 0 <= lgd <= 1):
            raise ValueError("pd aur lgd 0 se 1 ke beech (jaise 0.02) hone chahiye.")
        st = int(e["stage"]) if e.get("stage") else (3 if _n(e.get("dpd")) > _n(stage3_dpd) else 2 if _n(e.get("dpd")) > _n(stage2_dpd) else 1)
        use = pd_
        if st == 2:
            if e.get("pd_lifetime") is None:
                flags.append(f"{e.get('id', '?')}: stage 2 par lifetime PD nahi mila; 12-mahine wala PD liya (ECL kam aanka ja sakta hai).")
            else:
                use = _n(e.get("pd_lifetime"))
        elif st == 3:
            use = 1.0
        v = round(ead * use * lgd, 2)
        by[st] += v
        rows.append({"id": e.get("id"), "stage": st, "ead": ead, "pd_used": use, "lgd": lgd, "ecl": v})
    return {"total_ecl": round(sum(by.values()), 2), "by_stage": {f"stage{k}": round(v, 2) for k, v in by.items()}, "rows": rows, "flags": flags,
            "method": "ECL = EAD x PD x LGD (stage 1: 12-month PD; stage 2: lifetime PD jahan diya; stage 3: PD = 1). Discounting aur macro adjustment shaamil nahi.",
            "verify": True, "not_checked": "PD / LGD model ki sahi hona, forward-looking adjustment, discounting.",
            "decider": "Provision ka aankda risk committee manzoor karta hai aur auditor jaanchta hai; yeh working paper hai."}
