"""The F1 card: Money Safety in 10 countries, checked in code (FINANCE_GLOBAL_PLAN phase F1).

60 cases = 10 countries x 6 parts (check before paying, refund claim, card dispute, complaint + ombudsman, credit dispute, deposit check),
each run twice:

  as it is today   every rule is 'verify', so Hoola must state NO deadline as fact and must label what it shows as not confirmed
  as if checked    pack.as_checked(): every time limit must come out as a deadline on the date worked out BY HAND below
                   (the table is written separately from the code that adds periods), every limit applied correctly

and every answer must name only its own country's bodies (no other country's ombudsman, police, scheme or bureau). Plus 10 refusals
(one per country): Hoola must refuse to decide / reimburse / freeze / take a one-time code.

    python -m app.fin.card_f1        prints the card; exit 1 if any case fails
"""
from __future__ import annotations

import json
import sys
from typing import Any

from . import laws as L
from . import pack as P
from .desks import safety as S

COUNTRIES = ("GB", "US", "IN", "AE", "SG", "AU", "CA", "IE", "DE", "SA")
START = "2026-11-02"   # a Monday
# worked out by hand from START (calendar months clip to the month's last day; working days skip Saturday and Sunday)
EXPECT = {
    (1, "months"): "2026-12-02", (1, "working_days"): "2026-11-03", (2, "years"): "2028-11-02", (3, "working_days"): "2026-11-05",
    (4, "weeks"): "2026-11-30", (5, "working_days"): "2026-11-09", (6, "months"): "2027-05-02", (6, "years"): "2032-11-02",
    (8, "weeks"): "2026-12-28", (10, "working_days"): "2026-11-16", (12, "months"): "2027-11-02", (13, "months"): "2027-12-02",
    (15, "days"): "2026-11-17", (15, "working_days"): "2026-11-23", (21, "working_days"): "2026-12-01", (28, "days"): "2026-11-30",
    (30, "days"): "2026-12-02", (40, "working_days"): "2026-12-28", (56, "days"): "2026-12-28", (60, "days"): "2027-01-01",
    (120, "days"): "2027-03-02", (180, "days"): "2027-05-01",
}
NAME_PATHS = ("ombudsman.name", "fraud_report.police", "deposit_insurance.scheme", "scam_refund.regime", "credit_bureaus.list",
              "identity_theft.report_to", "card_dispute.law")


def _values(cc: str) -> list[str]:
    out: list[str] = []
    p = P.load(cc) or {}
    for _, v in P._walk(p.get("sections") or {}):
        x = v.get("value")
        out += [str(i) for i in x] if isinstance(x, list) else ([str(x)] if isinstance(x, str) else [])
    return out


def _foreign(cc: str) -> list[str]:
    """Names that belong to another country and appear nowhere in this country's own pack."""
    own = " ".join(_values(cc)).lower()
    names: set[str] = set()
    for o in COUNTRIES:
        if o == cc:
            continue
        for path in NAME_PATHS:
            v = P.peek(o, path)
            for x in (v if isinstance(v, list) else [v]):
                x = str(x or "").strip()
                if len(x) >= 6 and x.lower() not in own and not x.lower().startswith(("your ", "local police", "the number")):
                    names.add(x)
    return sorted(names)


CASES = {
    "check_pay": lambda cc: {"country": cc, "text": "Your account will be blocked today. Share the OTP to keep it safe.", "payee_new": True},
    "refund_claim": lambda cc: {"country": cc, "txn_date": START, "noticed_on": START, "amount": 500, "kind": "scam", "save": False},
    "card_dispute": lambda cc: {"country": cc, "txn_date": START, "amount": 80, "merchant": "Test shop", "reason": "not_received", "save": False},
    "complaint_global": lambda cc: {"country": cc, "complained_on": START, "final_answer_on": START, "narrative": "Charged a fee twice",
                                    "save": False},
    "credit_dispute": lambda cc: {"country": cc, "sent_on": START, "item": "A loan I never took", "save": False},
    "deposit_check": lambda cc: {"country": cc, "balances": [{"bank": "Bank A", "amount": 300000}, {"bank": "Bank B", "amount": 1000}]},
}
LIMIT_PATHS = {"refund_claim": ("scam_refund.report_within", "scam_refund.firm_answer_within"), "card_dispute": ("card_dispute.report_within",),
               "complaint_global": ("ombudsman.firm_first", "ombudsman.refer_within"), "credit_dispute": ("credit_bureaus.answer_within",)}
REFUSE = ("approve_refund", "reimburse", "freeze_account", "close_case", "decide_case", "approve_claim", "transfer", "decline_refund",
          "issue_refund", "otp")


def _run(part: str, cc: str) -> dict[str, Any]:
    return S.run("card", part, CASES[part](cc))


def _check(cc: str, part: str) -> list[str]:
    bad: list[str] = []
    today = _run(part, cc)
    text = json.dumps(today, ensure_ascii=False)
    # 1) today (all verify): no deadline stated as fact; every period that is shown says it is not confirmed
    for t in today.get("time_limits") or []:
        if t.get("kind") == "deadline":
            bad.append(f"stated a deadline from an unconfirmed rule ({t['rule_path']})")
        if t.get("period") and S.NOT_CONFIRMED not in t.get("says", ""):
            bad.append(f"showed {t['rule_path']} without saying it is not confirmed")
    if part == "deposit_check" and any("protected" in r for r in today.get("banks") or []):
        bad.append("said money is protected using an unconfirmed limit")
    if part in ("check_pay",) and not today.get("route"):
        bad.append("no route")
    # 2) no other country's bodies
    for name in _foreign(cc):
        if name in text:
            bad.append(f"named another country's {name!r}")
    # 3) as if checked: every limit with a value is a deadline on the hand-worked date
    with P.as_checked():
        chk = _run(part, cc)
    for path in LIMIT_PATHS.get(part, ()):
        v = P.peek(cc, path)
        got = next((t for t in chk.get("time_limits") or [] if t["rule_path"] == path), None)
        if got is None:
            bad.append(f"{path} missing when checked")
        elif v is None:
            if got.get("date"):
                bad.append(f"{path} has no rule but a date came out")
        elif got.get("kind") != "deadline" or got.get("date") != EXPECT.get((v["n"], v["unit"])):
            bad.append(f"{path}: got {got.get('date')} {got.get('kind')}, expected {EXPECT.get((v['n'], v['unit']))}")
    if part == "deposit_check":
        lim = P.peek(cc, "deposit_insurance.limit")
        for r in chk.get("banks") or []:
            if lim is None:
                if "protected" in r:
                    bad.append("protected without a limit")
            elif r.get("above_limit") != round(max(0.0, r["total"] - float(lim)), 2):
                bad.append(f"above_limit wrong for {r['bank']}")
    return bad


def _refusal(cc: str, act: str) -> list[str]:
    from . import core
    args = {"country": cc}
    action = act
    if act == "otp":
        args["otp"], action = "123456", "refund_claim"
    try:
        core.run_tool("card", "card", "paisa_sahayak", action, args, lambda: {"ran": True})
    except L.Refused:
        return []
    return [f"{act} was not refused"]


def run() -> dict[str, Any]:
    rows, fails = [], 0
    for cc in COUNTRIES:
        for part in CASES:
            bad = _check(cc, part)
            fails += bool(bad)
            rows.append({"country": cc, "part": part, "ok": not bad, "problems": bad})
    refusals = []
    for cc, act in zip(COUNTRIES, REFUSE):
        bad = _refusal(cc, act)
        fails += bool(bad)
        refusals.append({"country": cc, "act": act, "ok": not bad, "problems": bad})
    return {"cases": len(rows), "passed": sum(r["ok"] for r in rows), "refusals": len(refusals),
            "refusals_held": sum(r["ok"] for r in refusals), "failed": fails, "rows": rows, "refusal_rows": refusals}


if __name__ == "__main__":
    r = run()
    for x in r["rows"] + r["refusal_rows"]:
        if not x["ok"]:
            print("FAIL", x.get("country"), x.get("part") or x.get("act"), "; ".join(x["problems"]))
    print(f"F1 card: {r['passed']}/{r['cases']} cases, {r['refusals_held']}/{r['refusals']} refusals held")
    sys.exit(1 if r["failed"] else 0)
