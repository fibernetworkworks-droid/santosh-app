"""F12 of docs/FINANCE_GLOBAL_PLAN.md - Public sector (tool `public_finance`), for benefit offices, payment agencies, deposit insurers,
supervisors and development-finance teams, any country.

  benefits     a caseworker's check of one household against the scheme rules SHE gives (each with its source): which schemes the
               household meets, by how much it misses the others, the evidence still missing, the amount by HER rule. A caseworker
               decides; Hoola never awards, refuses or stops a benefit.
  overpayment  what was paid against what was due, period by period: overpaid, underpaid, the net, and the periods to look at.
  g2p          a government-to-person payment run reconciled: the approved beneficiary list against the payment file against the bank's
               return - paid, failed, never sent, paid twice, paid the wrong amount, paid to someone not on the list, one bank account
               shared by several beneficiaries. Account numbers masked.
  deposit_cover a failed bank's depositors: every account added up per depositor (joint accounts split by HER rule), set off against
               their loans if HER rule says so, covered up to HER limit -> the payout list, what is above cover, and the records a
               payout cannot go on (no ID, two IDs for one person).
  supervisor   banks' returns against HER thresholds: capital ratio, liquidity coverage, bad-loan ratio, large exposures - breaches,
               banks far from their peers, moves since the last period.
  inspection   an inspection's findings with owners and due dates: open, overdue, repeat findings.
  dev_finance  a development project: tranches released against the conditions met, spending against the budget lines, indicators
               against targets, spending outside the eligible categories.

Hoola never pays, awards, refuses, closes a bank or takes a supervisory action. Not legal advice."""
from __future__ import annotations

import re
import statistics
from collections import defaultdict
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from .. import laws as L


class PublicError(ValueError):
    pass


ZERO = Decimal(0)
NEVER = "Hoola never pays, awards, refuses or stops anything, and takes no supervisory action: a named official decides."
_OPS = {">=": lambda a, b: a >= b, "<=": lambda a, b: a <= b, ">": lambda a, b: a > b, "<": lambda a, b: a < b,
        "==": lambda a, b: a == b, "!=": lambda a, b: a != b}


def _n(v: Any, what: str, lo: float | None = None) -> Decimal:
    try:
        x = Decimal(str(v).replace(",", "").strip())
    except Exception:
        raise PublicError(f"{what}: a number.")
    if not x.is_finite():
        raise PublicError(f"{what}: a number.")
    if lo is not None and x < Decimal(str(lo)):
        raise PublicError(f"{what}: not below {lo}.")
    return x


def money(x: Decimal) -> float:
    return float(Decimal(x).quantize(Decimal("0.01"), ROUND_HALF_UP))


def mask(acct: Any) -> str:
    s = re.sub(r"\s", "", str(acct or ""))
    return ("*" * max(0, len(s) - 4) + s[-4:]) if s else ""


def _d(s: Any, what: str) -> date:
    try:
        return date.fromisoformat(str(s)[:10])
    except ValueError:
        raise PublicError(f"{what}: a date as YYYY-MM-DD.")


# ---- benefits ----------------------------------------------------------------------------------------------------------------

def benefits(a: dict[str, Any]) -> dict[str, Any]:
    hh = a.get("household") or {}
    schemes = a.get("schemes") or []
    if not schemes:
        raise PublicError("schemes: [{name, source, tests [{field, op, value}], amount {base, per_field, per_value}, evidence [..]}] - "
                          "the rules of your scheme, each with where it comes from.")
    out = []
    for k, sc in enumerate(schemes):
        name = sc.get("name") or f"scheme {k + 1}"
        if not str(sc.get("source") or "").strip():
            raise PublicError(f"{name}: source - the rule's legal or policy reference (no rule is used without one).")
        met, missed, unknown = [], [], []
        for t in sc.get("tests") or []:
            f, op = str(t.get("field")), str(t.get("op") or "")
            if op not in _OPS:
                raise PublicError(f"{name}: op is one of {', '.join(_OPS)}.")
            if hh.get(f) is None:
                unknown.append(f)
                continue
            v, lim = hh[f], t.get("value")
            try:
                v, lim = _n(v, f), _n(lim, f"{name}.{f}")
            except PublicError:
                v, lim = str(v).lower(), str(lim).lower()
            ok = _OPS[op](v, lim)
            row = {"field": f, "rule": f"{op} {t.get('value')}", "household": hh[f]}
            if ok:
                met.append(row)
            else:
                if isinstance(v, Decimal):
                    row["by"] = float(v - lim)
                missed.append(row)
        ev_need = [e for e in sc.get("evidence") or [] if e not in (a.get("evidence_held") or [])]
        amount = None
        am = sc.get("amount")
        if am and not missed and not unknown:
            amount = _n(am.get("base") or 0, f"{name}.amount.base")
            if am.get("per_field"):
                amount += _n(hh.get(am["per_field"]) or 0, am["per_field"]) * _n(am.get("per_value") or 0, f"{name}.amount.per_value")
            if am.get("max") is not None:
                amount = min(amount, _n(am["max"], f"{name}.amount.max"))
        state = "meets the rules" if not missed and not unknown else "does not meet" if missed else "cannot tell yet"
        out.append({"scheme": name, "source": sc["source"], "state": state, "met": met, "missed": missed, "unknown_fields": unknown,
                    "evidence_missing": ev_need, "amount": money(amount) if amount is not None else None})
    return {"schemes": out, "decider": "a caseworker", "never": NEVER,
            "says": "This is a check against the rules you gave, for the caseworker to decide on - not a decision."}


def overpayment(a: dict[str, Any]) -> dict[str, Any]:
    due = {str(r.get("period")): _n(r.get("amount"), "due.amount", 0) for r in a.get("due") or []}
    paid = defaultdict(lambda: ZERO)
    for r in a.get("paid") or []:
        paid[str(r.get("period"))] += _n(r.get("amount"), "paid.amount", 0)
    rows, over, under = [], ZERO, ZERO
    for p in sorted(set(due) | set(paid)):
        d = paid.get(p, ZERO) - due.get(p, ZERO)
        if d:
            rows.append({"period": p, "due": money(due.get(p, ZERO)), "paid": money(paid.get(p, ZERO)), "difference": money(d)})
            over += max(d, ZERO)
            under += max(-d, ZERO)
    return {"periods": rows, "overpaid": money(over), "underpaid": money(under), "net": money(over - under),
            "says": "Whether an overpayment is recovered, and how, is the official's decision under your rules."}


# ---- G2P reconciliation ------------------------------------------------------------------------------------------------------

def g2p(a: dict[str, Any]) -> dict[str, Any]:
    ben = {}
    for i, b in enumerate(a.get("beneficiaries") or []):
        bid = str(b.get("id") or "")
        if not bid:
            raise PublicError(f"beneficiaries[{i}].id: missing.")
        ben[bid] = {"amount": _n(b.get("amount"), f"beneficiaries[{i}].amount", 0), "account": str(b.get("account") or "")}
    sent = defaultdict(list)
    acct_ids = defaultdict(set)
    for i, p in enumerate(a.get("payments") or []):
        bid = str(p.get("id") or "")
        sent[bid].append({"ref": str(p.get("ref") or f"#{i}"), "amount": _n(p.get("amount"), f"payments[{i}].amount", 0),
                          "account": str(p.get("account") or "")})
        if p.get("account"):
            acct_ids[re.sub(r"\s", "", str(p["account"]))].add(bid)
    ret = {str(r.get("ref")): str(r.get("status") or "").lower() for r in a.get("bank_return") or []}
    paid, failed, not_sent, twice, wrong, unknown, no_return = [], [], [], [], [], [], []
    for bid, b in sorted(ben.items()):
        ps = sent.get(bid, [])
        if not ps:
            not_sent.append({"id": bid, "amount": money(b["amount"])})
            continue
        ok = [p for p in ps if ret.get(p["ref"]) in ("success", "paid", "credited")]
        bad = [p for p in ps if ret.get(p["ref"]) in ("failed", "rejected", "returned")]
        none = [p for p in ps if p["ref"] not in ret]
        if len(ok) > 1:
            twice.append({"id": bid, "refs": [p["ref"] for p in ok], "extra": money(sum((p["amount"] for p in ok[1:]), ZERO))})
        if ok:
            got = ok[0]["amount"]
            (wrong.append({"id": bid, "approved": money(b["amount"]), "paid": money(got), "difference": money(got - b["amount"])})
             if got != b["amount"] else paid.append(bid))
        elif bad:
            failed.append({"id": bid, "refs": [p["ref"] for p in bad], "reason": [ret[p["ref"]] for p in bad][0]})
        if none:
            no_return += [p["ref"] for p in none]
    for bid, ps in sent.items():
        if bid not in ben:
            unknown.append({"id": bid, "amount": money(sum((p["amount"] for p in ps), ZERO)), "account": mask(ps[0]["account"])})
    shared = [{"account": mask(k), "beneficiaries": sorted(v)} for k, v in acct_ids.items() if len(v) > 1]
    total = money(sum((b["amount"] for b in ben.values()), ZERO))
    return {"approved": len(ben), "approved_total": total, "paid": len(paid), "failed": failed, "never_sent": not_sent,
            "paid_twice": twice, "wrong_amount": wrong, "not_on_the_list": unknown, "shared_accounts": shared,
            "no_bank_return_for": no_return, "clean": not (failed or not_sent or twice or wrong or unknown or shared or no_return)}


# ---- deposit insurance -------------------------------------------------------------------------------------------------------

def deposit_cover(a: dict[str, Any]) -> dict[str, Any]:
    if a.get("limit") is None:
        raise PublicError("limit: the cover per depositor per bank under your scheme's law.")
    limit = _n(a["limit"], "limit", 0)
    setoff = bool(a.get("set_off_loans"))
    split = str(a.get("joint_rule") or "equal")
    if split != "equal":
        raise PublicError("joint_rule: equal (a joint account split equally between its holders) - the only rule built.")
    bal = defaultdict(lambda: ZERO)
    loans = defaultdict(lambda: ZERO)
    problems = []
    id_of_name = defaultdict(set)
    for i, acc in enumerate(a.get("accounts") or []):
        holders = [str(h) for h in acc.get("holders") or []]
        if not holders or any(not h.strip() for h in holders):
            problems.append({"account": mask(acc.get("number")), "problem": "an account with no depositor ID"})
            continue
        v = _n(acc.get("balance"), f"accounts[{i}].balance") + _n(acc.get("interest") or 0, f"accounts[{i}].interest", 0)
        if str(acc.get("type") or "").lower() == "excluded":
            continue
        for h in holders:
            bal[h] += v / len(holders)
    for i, ln in enumerate(a.get("loans") or []):
        loans[str(ln.get("depositor"))] += _n(ln.get("due"), f"loans[{i}].due", 0)
    for d in a.get("depositors") or []:
        id_of_name[(str(d.get("name") or "").strip().lower(), str(d.get("dob") or ""))].add(str(d.get("id")))
    for (nm, dob), ids in id_of_name.items():
        if len(ids) > 1 and nm:
            problems.append({"depositors": sorted(ids), "problem": "one person under two IDs: their accounts must be added together"})
    rows, covered, above = [], ZERO, ZERO
    for h in sorted(bal):
        gross = bal[h]
        net = gross - loans[h] if setoff else gross
        net = max(net, ZERO)
        cov = min(net, limit)
        covered += cov
        above += net - cov
        rows.append({"depositor": h, "deposits": money(gross), "loans_set_off": money(loans[h]) if setoff else 0.0,
                     "eligible": money(net), "covered": money(cov), "above_cover": money(net - cov)})
    return {"depositors": rows, "covered_total": money(covered), "above_cover_total": money(above), "records_to_fix": problems,
            "limit": float(limit), "set_off": setoff,
            "says": "Payouts wait for the records to fix; the insurer's officials approve the payout list. " + NEVER}


# ---- supervision -------------------------------------------------------------------------------------------------------------

def supervisor(a: dict[str, Any]) -> dict[str, Any]:
    th = a.get("thresholds") or {}
    if not th:
        raise PublicError("thresholds: {car_min, lcr_min, npl_max, large_exposure_max} - your rules, in percent.")
    rows, prev = [], {str(p.get("bank")): p for p in a.get("previous") or []}
    for i, b in enumerate(a.get("returns") or []):
        name = str(b.get("bank") or f"#{i}")
        r = {}
        cap, rwa = b.get("capital"), b.get("rwa")
        if cap is not None and rwa:
            r["car"] = _n(cap, "capital") / _n(rwa, "rwa") * 100
        if b.get("liquid_assets") is not None and b.get("net_outflows"):
            r["lcr"] = _n(b["liquid_assets"], "liquid_assets") / _n(b["net_outflows"], "net_outflows") * 100
        if b.get("npl") is not None and b.get("loans"):
            r["npl"] = _n(b["npl"], "npl") / _n(b["loans"], "loans") * 100
        if b.get("largest_exposure") is not None and cap:
            r["large_exposure"] = _n(b["largest_exposure"], "largest_exposure") / _n(cap, "capital") * 100
        breach = []
        for k, lim, low in (("car", th.get("car_min"), True), ("lcr", th.get("lcr_min"), True), ("npl", th.get("npl_max"), False),
                            ("large_exposure", th.get("large_exposure_max"), False)):
            if lim is None or k not in r:
                continue
            if (r[k] < _n(lim, k)) if low else (r[k] > _n(lim, k)):
                breach.append(f"{k} {money(r[k])}% against {lim}%")
        moves = {}
        if name in prev:
            p = prev[name]
            if p.get("capital") is not None and p.get("rwa") and "car" in r:
                moves["car_points"] = money(r["car"] - _n(p["capital"], "capital") / _n(p["rwa"], "rwa") * 100)
        rows.append({"bank": name, **{k: money(v) for k, v in r.items()}, "breaches": breach, "moves": moves})
    outl = []
    for k in ("car", "lcr", "npl"):
        vals = [x[k] for x in rows if k in x]
        if len(vals) >= 4:
            med = statistics.median(vals)
            mad = statistics.median([abs(v - med) for v in vals]) or 0
            for x in rows:
                if k in x and mad and abs(x[k] - med) / mad > float(a.get("outlier_mad") or 3):
                    outl.append({"bank": x["bank"], "measure": k, "value": x[k], "peer_median": round(med, 2)})
    return {"banks": rows, "in_breach": [x["bank"] for x in rows if x["breaches"]], "far_from_peers": outl, "never": NEVER}


def inspection(a: dict[str, Any]) -> dict[str, Any]:
    today = _d(a.get("today") or date.today().isoformat(), "today")
    seen = defaultdict(list)
    for f in a.get("earlier") or []:
        seen[str(f.get("area") or "").lower()].append(f.get("id"))
    rows = []
    for i, f in enumerate(a.get("findings") or []):
        due = _d(f.get("due"), f"findings[{i}].due") if f.get("due") else None
        st = str(f.get("status") or "open").lower()
        rows.append({"id": f.get("id"), "area": f.get("area"), "owner": f.get("owner"), "status": st,
                     "overdue_days": (today - due).days if due and st != "closed" and due < today else 0,
                     "repeat_of": seen.get(str(f.get("area") or "").lower(), []), "no_owner": not f.get("owner")})
    return {"findings": rows, "open": sum(1 for r in rows if r["status"] != "closed"),
            "overdue": [r["id"] for r in rows if r["overdue_days"] > 0], "repeat": [r["id"] for r in rows if r["repeat_of"]],
            "without_owner": [r["id"] for r in rows if r["no_owner"]]}


def dev_finance(a: dict[str, Any]) -> dict[str, Any]:
    met = {str(c) for c in a.get("conditions_met") or []}
    tr = []
    for t in a.get("tranches") or []:
        need = [str(c) for c in t.get("conditions") or []]
        miss = [c for c in need if c not in met]
        tr.append({"tranche": t.get("name"), "amount": money(_n(t.get("amount") or 0, "tranches.amount", 0)),
                   "released": bool(t.get("released")), "conditions_missing": miss,
                   "released_before_conditions": bool(t.get("released")) and bool(miss)})
    budget = {str(b.get("line")): _n(b.get("amount"), "budget.amount", 0) for b in a.get("budget") or []}
    spent = defaultdict(lambda: ZERO)
    ineligible = []
    elig = {str(x).lower() for x in a.get("eligible_categories") or []}
    for i, s in enumerate(a.get("spending") or []):
        v = _n(s.get("amount"), f"spending[{i}].amount", 0)
        spent[str(s.get("line"))] += v
        if elig and str(s.get("category") or "").lower() not in elig:
            ineligible.append({"item": s.get("id") or i, "category": s.get("category"), "amount": money(v)})
    lines = [{"line": k, "budget": money(budget.get(k, ZERO)), "spent": money(spent.get(k, ZERO)),
              "used_pct": money(spent.get(k, ZERO) / budget[k] * 100) if budget.get(k) else None,
              "over": spent.get(k, ZERO) > budget.get(k, ZERO)} for k in sorted(set(budget) | set(spent))]
    ind = []
    for x in a.get("indicators") or []:
        tgt, act = _n(x.get("target"), "indicators.target"), _n(x.get("actual") or 0, "indicators.actual")
        ind.append({"indicator": x.get("name"), "target": float(tgt), "actual": float(act),
                    "achieved_pct": money(act / tgt * 100) if tgt else None})
    return {"tranches": tr, "budget_lines": lines, "over_budget": [x["line"] for x in lines if x["over"]], "ineligible": ineligible,
            "indicators": ind, "released_before_conditions": [t["tranche"] for t in tr if t["released_before_conditions"]]}


ACTIONS = ("benefits", "overpayment", "g2p", "deposit_cover", "supervisor", "inspection", "dev_finance")
_ACTS = re.compile(r"pay|award|grant|refuse|deny|stop_benefit|disburse|release|transfer|close_bank|sanction|revoke|impose|fine_bank")


def run(tenant: str, action: str, a: dict[str, Any], actor: str = "owner") -> dict[str, Any]:
    a = dict(a)
    if action not in ACTIONS and _ACTS.search(str(action).lower()):
        raise L.Refused("approve_decision", NEVER)
    if action not in ACTIONS:
        raise PublicError("action: " + ", ".join(ACTIONS))
    out = globals()[action](a)
    out.setdefault("not_advice", L.NOT_ADVICE)
    return out
