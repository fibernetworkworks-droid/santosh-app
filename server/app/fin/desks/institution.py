"""F9 of docs/FINANCE_GLOBAL_PLAN.md - Institution mode and the five institution employees (tool `institution_desk`): Financial
Crime, Compliance, Risk, Audit & Controls, Governance. For a small regulated firm up to a bank. Every draft goes through maker-checker
(fin/makerchecker.py). Hoola prepares, screens and counts; the institution's named people decide, sign and file.

FINANCIAL CRIME
  aml_triage    transactions (her own, up to millions) against HER rule settings: structuring just under her cash threshold, money
                passed straight through, high-risk countries she lists, a month far above the customer's own average (up to 6 months before), a dormant account
                waking up, many senders into one account; each alert lists the transactions behind it.
  sar_draft     a suspicious-activity narrative from an alert and the customer profile she gives: who, what, when, where, why it is
                unusual, what was done - every amount and date taken from the transactions; no accusation words; the analyst's parts
                left blank; machine checks; then into maker-checker. Hoola never files it.
  sar_score     a named MLRO / compliance person scores the draft (1-5 on each criterion) - the human review the card asks for.
  kyc_review    a customer file: documents present / expired, risk rating from HER factor weights, next review date.
  sanctions     names against HER watch list (finops screen).
COMPLIANCE
  obligations   her obligation register (owner, control, how often, evidence) and what is due / overdue.
  policy_check  a policy text against the sections she requires.
  promotion_check a financial promotion checked for a risk warning, balance, past-performance wording, guarantees.
  complaints_mi complaints by category, response times against her deadline, upheld rate.
RISK
  incident      an incident and its reporting clocks from HER list of hours (e.g. 4, 24, 72) - when each report is due.
  rcsa          risks scored likelihood x impact into a heat map against her appetite.
  third_party   her third-party register checked for the fields she must keep; critical ones without an exit plan named.
  models        model / AI inventory: validation overdue, owner missing.
  ecl           ECL working paper.
AUDIT
  pbc           the prepared-by-client list: received / outstanding / late.
  sample        a reproducible random sample (the seed is recorded) of the size she sets.
  control_test  a control's sample results -> effective, or a deficiency with the failures listed.
  je_test       journal entries tested: weekends, round amounts, near period end, unusual users, no description.
GOVERNANCE
  board_pack    agenda items with their papers present / missing, open actions from last minutes.
  cap_table     shareholdings and a new round: pre / post money, new shares, everyone's percentage after.
  related_party transactions with her related parties named.
  whistle       a whistleblowing case logged with a case number only - no name kept.
PLUMBING
  person_add, limits, submit, revise, check, drafts (maker-checker), api_key (scoped keys, only the hash kept), retention (her keep
  periods), export (her registers and drafts as one file).

Not legal advice; nothing is filed, frozen or reported to a regulator here."""
from __future__ import annotations

import hashlib
import json
import random
import re
import secrets
import statistics
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from .. import evidence as EV
from .. import laws as L
from .. import makerchecker as MC


class InstError(ValueError):
    pass


NOT_CONFIRMED = " (not confirmed - check this)"
DECIDER = "The decision is the named officer's; nothing is filed, frozen or reported here."
ACCUSE = re.compile(r"\b(launder\w*|criminal\w*|guilty|fraudster\w*|terroris\w*|crook|thief|stole|illegal\w*|money mule)\b", re.I)


def _f(v: Any, what: str, lo: float | None = None) -> float:
    try:
        x = float(str(v).replace(",", ""))
    except (TypeError, ValueError):
        raise InstError(f"{what}: a number.")
    if lo is not None and x < lo:
        raise InstError(f"{what}: not below {lo}.")
    return x


def _d(s: Any, what: str) -> date:
    try:
        return date.fromisoformat(str(s)[:10])
    except ValueError:
        raise InstError(f"{what}: a date as YYYY-MM-DD.")


# ---- AML triage ------------------------------------------------------------------------------------------------------------------

DEFAULT_RULES = {"cash_threshold": 10000, "structuring_band_pct": 10, "structuring_count": 3, "structuring_days": 7,
                 "pass_through_pct": 90, "pass_through_days": 2, "pass_through_min": 5000, "high_risk_countries": [],
                 "high_risk_min": 1000, "spike_multiple": 5, "spike_min": 5000, "dormant_days": 180, "dormant_min": 2000,
                 "fan_in_senders": 10, "fan_in_days": 7}


_DAYS: dict[str, date] = {}


def _day(s: str) -> date:
    d = _DAYS.get(s)
    if d is None:
        d = _DAYS[s] = date.fromisoformat(s)
    return d


def aml_triage(a: dict[str, Any]) -> dict[str, Any]:
    """transactions: [{id, customer, date, amount, direction in|out, channel cash|wire|card|transfer, country, counterparty}]."""
    r = {**DEFAULT_RULES, **{k: v for k, v in (a.get("rules") or {}).items() if k in DEFAULT_RULES}}
    given = sorted(k for k in (a.get("rules") or {}) if k in DEFAULT_RULES)
    tx = a.get("transactions") or []
    if not tx:
        raise InstError("transactions: [{id, customer, date, amount, direction, channel, country, counterparty}] (or rows in that order).")
    by: dict[str, list[tuple]] = defaultdict(list)
    for t in tx:
        if isinstance(t, (tuple, list)):   # compact rows: (id, customer, date, amount, direction, channel, country, counterparty)
            by[t[1]].append((t[2], float(t[3]), t[4], t[5], t[6], t[7], t[0]))
            continue
        by[str(t["customer"])].append((str(t["date"])[:10], float(t["amount"]), t.get("direction", "in"), t.get("channel", ""),
                                       str(t.get("country") or "").upper(), str(t.get("counterparty") or ""), str(t["id"])))
    thr = float(r["cash_threshold"])
    low = thr * (1 - float(r["structuring_band_pct"]) / 100)
    hr = {c.upper() for c in r["high_risk_countries"]}
    alerts = []

    def alert(cust, rule, ids, why):
        alerts.append({"customer": cust, "rule": rule, "transactions": ids[:50], "count": len(ids), "why": why})
    for cust, ts in by.items():
        ts.sort()
        days = [_day(x[0]) for x in ts]
        near = [(days[i], ts[i]) for i in range(len(ts)) if ts[i][3] == "cash" and ts[i][2] == "in" and low <= ts[i][1] < thr]
        j = 0
        for i in range(len(near)):
            while near[i][0] - near[j][0] > timedelta(days=int(r["structuring_days"])):
                j += 1
            if i - j + 1 >= int(r["structuring_count"]):
                e = i
                while e + 1 < len(near) and near[e + 1][0] - near[j][0] <= timedelta(days=int(r["structuring_days"])):
                    e += 1                    # every deposit in the same window, not just the first ones that reached the count
                win = near[j:e + 1]
                alert(cust, "structuring", [x[1][6] for x in win],
                      f"{len(win)} cash deposits between {low:,.0f} and {thr:,.0f} within {r['structuring_days']} days")
                break
        ins = [(days[i], ts[i]) for i in range(len(ts)) if ts[i][2] == "in"]
        outs = [(days[i], ts[i]) for i in range(len(ts)) if ts[i][2] == "out"]
        for d0, t0 in ins:
            if t0[1] < float(r["pass_through_min"]):
                continue
            went = [o for o in outs if d0 <= o[0] <= d0 + timedelta(days=int(r["pass_through_days"]))]
            tot = sum(o[1][1] for o in went)
            if tot >= t0[1] * float(r["pass_through_pct"]) / 100:
                alert(cust, "pass_through", [t0[6]] + [o[1][6] for o in went],
                      f"{t0[1]:,.2f} in on {d0}, {tot:,.2f} out within {r['pass_through_days']} days")
                break
        if hr:
            risky = [t for t in ts if t[4] in hr]
            if sum(t[1] for t in risky) >= float(r["high_risk_min"]):
                alert(cust, "high_risk_country", [t[6] for t in risky],
                      f"{sum(t[1] for t in risky):,.2f} with {', '.join(sorted({t[4] for t in risky}))}")
        months: dict[str, float] = defaultdict(float)
        mids: dict[str, list[str]] = defaultdict(list)
        for t in ts:
            months[t[0][:7]] += t[1]
            mids[t[0][:7]].append(t[6])
        ks = sorted(months)
        for k in range(3, len(ks)):
            prev = ks[max(0, k - 6):k]
            base = sum(months[m] for m in prev) / len(prev)
            if months[ks[k]] >= float(r["spike_min"]) and base > 0 and months[ks[k]] >= base * float(r["spike_multiple"]):
                alert(cust, "spike", mids[ks[k]],
                      f"{months[ks[k]]:,.2f} in {ks[k]} vs an average of {base:,.2f} in the {len(prev)} months before")
                break
        for i in range(1, len(ts)):
            if (days[i] - days[i - 1]).days >= int(r["dormant_days"]):
                after = [t for t in ts[i:] if _day(t[0]) <= days[i] + timedelta(days=30)]
                if sum(t[1] for t in after) >= float(r["dormant_min"]):
                    alert(cust, "dormant_reactivated", [t[6] for t in after],
                          f"no activity for {(days[i] - days[i - 1]).days} days, then {sum(t[1] for t in after):,.2f} within 30 days")
                    break
        j = 0
        for i in range(len(ins)):
            while ins[i][0] - ins[j][0] > timedelta(days=int(r["fan_in_days"])):
                j += 1
            senders = {x[1][5] for x in ins[j:i + 1] if x[1][5]}
            if len(senders) >= int(r["fan_in_senders"]):
                alert(cust, "fan_in", [x[1][6] for x in ins[j:i + 1]], f"{len(senders)} different senders within {r['fan_in_days']} days")
                break
    per = defaultdict(list)
    for x in alerts:
        per[x["customer"]].append(x["rule"])
    for x in alerts:
        x["rules_on_customer"] = len(per[x["customer"]])
    alerts.sort(key=lambda x: (-x["rules_on_customer"], x["customer"], x["rule"]))
    return {"transactions": len(tx), "customers": len(by), "alerts": alerts, "customers_alerted": len(per),
            "rules_used": r, "rules_yours": given,
            "rules_hoola_default": sorted(k for k in DEFAULT_RULES if k not in given),
            "says": "Signals for an analyst, not findings; Hoola's starting values are marked - set your own. " + DECIDER}


# ---- SAR draft, checks, human score ----------------------------------------------------------------------------------------

SAR_PARTS = ("Subject", "Activity", "When", "Where", "Why it is unusual", "What was done", "Analyst assessment")


def sar_draft(tenant: str, ws: str, a: dict[str, Any]) -> dict[str, Any]:
    al = a.get("alert") or {}
    ids = set(map(str, al.get("transactions") or []))
    tx = [t for t in a.get("transactions") or [] if str(t.get("id")) in ids]
    if not al or not tx:
        raise InstError("alert (from aml_triage) and the transactions behind it.")
    cust = a.get("customer") or {}
    tx.sort(key=lambda t: (str(t["date"]), str(t["id"])))
    total = sum(Decimal(str(t["amount"])) for t in tx)
    lines = [f"- {t['date']}: {Decimal(str(t['amount'])):,.2f} {t.get('direction', '')} by {t.get('channel', '')}"
             f"{' (' + str(t['country']) + ')' if t.get('country') else ''}, ref {t['id']}" for t in tx]
    body = "\n".join([
        "# Suspicious activity report (DRAFT)", "", "## Subject",
        f"Customer {al['customer']}" + (f", {cust.get('name')}" if cust.get("name") else "") +
        (f", {cust.get('occupation')}" if cust.get("occupation") else "") +
        (f"; declared income {cust.get('declared_income')}" if cust.get("declared_income") else ""),
        "", "## Activity", f"{len(tx)} transactions totalling {total:,.2f}:", *lines,
        "", "## When", f"From {tx[0]['date']} to {tx[-1]['date']}.",
        "", "## Where", "Countries: " + (", ".join(sorted({str(t['country']) for t in tx if t.get('country')})) or "[ ]") +
        "; channels: " + ", ".join(sorted({str(t.get('channel')) for t in tx if t.get('channel')})),
        "", "## Why it is unusual", f"Rule '{al['rule']}': {al.get('why', '')}." +
        (f" Expected activity on file: {cust['expected_activity']}." if cust.get("expected_activity") else " Expected activity on file: [ ]"),
        "", "## What was done", str(a.get("actions_taken") or "[ the steps taken: contact, review, restrictions ]"),
        "", "## Analyst assessment", "[ the analyst's own assessment ]"])
    chk = sar_checks(body, tx)
    out = {"body": body, "checks": chk}
    if a.get("person"):
        out["draft"] = MC.submit(tenant, ws, {"person": a["person"], "kind": "sar", "title": f"SAR {al['customer']} {al['rule']}",
                                              "body": body})["draft"]
    return {**out, "says": "A draft for the MLRO. " + DECIDER}


def sar_checks(body: str, tx: list[dict[str, Any]]) -> dict[str, Any]:
    amounts = {f"{Decimal(str(t['amount'])):,.2f}" for t in tx}
    amounts.add(f"{sum(Decimal(str(t['amount'])) for t in tx):,.2f}")
    dates = {str(t["date"])[:10] for t in tx}
    act = body.split("## Activity", 1)[-1].split("## Why it is unusual", 1)[0]
    seen_amt = set(re.findall(r"\d{1,3}(?:,\d{3})*\.\d{2}", act))
    seen_dates = set(re.findall(r"\d{4}-\d{2}-\d{2}", act))
    problems = []
    if seen_amt - amounts:
        problems.append(f"amounts not in the transactions: {sorted(seen_amt - amounts)}")
    if seen_dates - dates:
        problems.append(f"dates not in the transactions: {sorted(seen_dates - dates)}")
    missing = [p for p in SAR_PARTS if f"## {p}" not in body]
    if missing:
        problems.append("parts missing: " + ", ".join(missing))
    acc = ACCUSE.findall(body)
    if acc:
        problems.append(f"accusing words: {sorted(set(w.lower() for w in acc))} - a report describes, it does not accuse")
    return {"ok": not problems, "problems": problems, "parts": list(SAR_PARTS)}


SCORE_ON = ("facts_complete", "clear_and_ordered", "why_suspicious", "no_accusation", "ready_to_file")


def sar_score(tenant: str, ws: str, a: dict[str, Any]) -> dict[str, Any]:
    p = MC.person(tenant, ws, a.get("person"))
    if not ({"mlro", "compliance"} & set(p["roles"])):
        raise InstError("Only an MLRO or compliance person scores a SAR draft.")
    sc = {}
    for k in SCORE_ON:
        v = int(_f((a.get("scores") or {}).get(k), f"scores.{k}", 1))
        if not 1 <= v <= 5:
            raise InstError(f"scores.{k}: 1 to 5.")
        sc[k] = v
    did = str(a.get("draft") or "")

    def ch(s):
        s.setdefault("sar_scores", []).append({"draft": did, "by": p["id"], "scores": sc, "comment": str(a.get("comment") or "")[:1000],
                                               "on": date.today().isoformat()})
        return len(s["sar_scores"])
    MC.save(tenant, ws, ch)
    EV.record(tenant, ws, p["id"], "sar", f"SAR draft scored {sum(sc.values())}/25")
    return {"draft": did, "scores": sc, "total": sum(sc.values()), "out_of": 25, "scored_by": p["name"]}


def kyc_review(a: dict[str, Any]) -> dict[str, Any]:
    today = _d(a.get("today") or date.today().isoformat(), "today")
    docs = a.get("documents") or []
    need = [str(x).lower() for x in a.get("required") or ["identity", "address", "source of funds"]]
    have = {str(d.get("kind")).lower(): d for d in docs}
    missing = [n for n in need if n not in have]
    expired = [k for k, d in have.items() if d.get("expires") and _d(d["expires"], "expires") < today]
    w = a.get("weights") or {}
    score = sum(_f(w.get(k, 0), f"weights.{k}") for k, v in (a.get("factors") or {}).items() if v)
    bands = a.get("bands") or {"low": 0, "medium": 3, "high": 6}
    rating = max((b for b, lo in bands.items() if score >= _f(lo, "bands")), key=lambda b: _f(bands[b], "bands"))
    months = {"low": 36, "medium": 24, "high": 12, **(a.get("review_months") or {})}
    nxt = date(today.year + (today.month - 1 + int(months.get(rating, 12))) // 12, (today.month - 1 + int(months.get(rating, 12))) % 12 + 1, 1)
    return {"missing": missing, "expired": expired, "risk_score": score, "rating": rating, "next_review": nxt.isoformat(),
            "weights_from": "yours" if w else "no weights given: score 0", "says": "The rating comes from YOUR factor weights. " + DECIDER}


def sanctions(a: dict[str, Any]) -> dict[str, Any]:
    from ...finops import aml as A
    try:
        return A.screen(a.get("names") or [], a.get("watch") or [], a.get("threshold", 0.7))
    except ValueError as e:
        raise InstError(str(e))


# ---- compliance ----------------------------------------------------------------------------------------------------------------

def obligations(tenant: str, ws: str, a: dict[str, Any]) -> dict[str, Any]:
    today = _d(a.get("today") or date.today().isoformat(), "today")
    if a.get("add"):
        MC.person(tenant, ws, a.get("person"), "compliance")
        rows = []
        for k, o in enumerate(a["add"]):
            if not o.get("source"):
                raise InstError(f"add[{k}].source: the rule this obligation comes from (her register is only as good as its sources).")
            rows.append({"name": str(o.get("name"))[:120], "source": str(o["source"])[:160], "owner": str(o.get("owner") or "")[:80],
                         "control": str(o.get("control") or "")[:160], "every_days": int(_f(o.get("every_days", 365), "every_days", 1)),
                         "last_done": str(o.get("last_done") or "")[:10]})
        MC.save(tenant, ws, lambda s: s.setdefault("obligations", []).extend(rows))
    reg = MC.inst(MC.workspace(tenant, ws)).get("obligations") or []
    out = []
    for o in reg:
        due = (_d(o["last_done"], "last_done") + timedelta(days=o["every_days"])) if o["last_done"] else today
        out.append({**o, "due": due.isoformat(), "overdue": due < today, "no_owner": not o["owner"], "no_control": not o["control"]})
    return {"obligations": out, "overdue": [o["name"] for o in out if o["overdue"]], "gaps": [o["name"] for o in out if o["no_owner"] or o["no_control"]]}


def policy_check(a: dict[str, Any]) -> dict[str, Any]:
    text = str(a.get("text") or "")
    need = [str(x) for x in a.get("required_sections") or ["purpose", "scope", "roles", "procedure", "review", "approval"]]
    heads = {h.strip().lower() for h in re.findall(r"^#+\s*(.+)$", text, re.M)}
    missing = [s for s in need if not any(s.lower() in h for h in heads)]
    owner = re.search(r"\bowner\s*:\s*\S", text, re.I)
    rv = re.search(r"\b(next review|review date)\s*:\s*(\d{4}-\d{2}-\d{2})", text, re.I)
    return {"missing_sections": missing, "owner_named": bool(owner), "review_date": rv.group(2) if rv else None,
            "ok": not missing and bool(owner) and bool(rv)}


_GUARANTEE = re.compile(r"\b(guarantee[ds]?|risk[- ]free|no risk|can'?t lose|sure (?:thing|profit)|safe as)\b", re.I)


def promotion_check(a: dict[str, Any]) -> dict[str, Any]:
    t = str(a.get("text") or "")
    probs = []
    if _GUARANTEE.search(t):
        probs.append(f"a promise of safety or return ('{_GUARANTEE.search(t).group(0)}')")
    if not re.search(r"(capital|money|investment).{0,40}(at risk|can (?:go down|fall)|may (?:lose|get back less))|value .{0,30}(go down|fall)", t, re.I):
        probs.append("no clear risk warning")
    if re.search(r"\b(returned|grew|performance|up \d+%)\b", t, re.I) and not re.search(r"past performance", t, re.I):
        probs.append("talks about returns without saying past performance is not a guide")
    if re.search(r"\b(\d+(?:\.\d+)?)\s*%", t) and not re.search(r"\b(fees?|charges?)\b", t, re.I):
        probs.append("shows a percentage return but no fees or charges")
    for w in a.get("banned_words") or []:
        if re.search(rf"\b{re.escape(str(w))}\b", t, re.I):
            probs.append(f"uses '{w}', on your banned list")
    return {"problems": probs, "ok": not probs, "rules_from": "Hoola's general checks" + NOT_CONFIRMED + "; your rulebook decides"}


def complaints_mi(a: dict[str, Any]) -> dict[str, Any]:
    dl = int(_f(a.get("deadline_days", 56), "deadline_days", 1))
    cats: dict[str, dict[str, int]] = defaultdict(lambda: {"count": 0, "upheld": 0, "late": 0})
    days = []
    for c in a.get("complaints") or []:
        k = cats[str(c.get("category") or "other")]
        k["count"] += 1
        k["upheld"] += 1 if c.get("upheld") else 0
        if c.get("closed"):
            n = (_d(c["closed"], "closed") - _d(c.get("received"), "received")).days
            days.append(n)
            k["late"] += 1 if n > dl else 0
    tot = sum(v["count"] for v in cats.values())
    return {"by_category": dict(cats), "total": tot, "upheld_pct": round(sum(v["upheld"] for v in cats.values()) * 100 / tot, 1) if tot else None,
            "median_days": statistics.median(days) if days else None, "late": sum(v["late"] for v in cats.values()),
            "deadline_days": f"{dl} (yours)" if a.get("deadline_days") else f"{dl}" + NOT_CONFIRMED}


# ---- risk ---------------------------------------------------------------------------------------------------------------------

def incident(tenant: str, ws: str, a: dict[str, Any]) -> dict[str, Any]:
    try:
        found = datetime.fromisoformat(str(a.get("detected"))).replace(tzinfo=None)
    except ValueError:
        raise InstError("detected: when it was found, YYYY-MM-DDTHH:MM.")
    clocks = a.get("clocks") or []
    if not clocks:
        raise InstError("clocks: [{report, hours}] from your regulator's rules (e.g. initial 4, intermediate 72) - Hoola has no clock of its own.")
    due = [{"report": str(c.get("report")), "due": (found + timedelta(hours=_f(c.get("hours"), "hours", 0))).isoformat(timespec="minutes")}
           for c in clocks]
    rec = {"title": str(a.get("title") or "")[:160], "detected": found.isoformat(timespec="minutes"), "severity": a.get("severity"), "due": due}
    if ws:
        MC.save(tenant, ws, lambda s: s.setdefault("incidents", []).append(rec))
    return {**rec, "says": "Report clocks from the hours you gave. " + DECIDER}


def rcsa(a: dict[str, Any]) -> dict[str, Any]:
    app = _f(a.get("appetite", 12), "appetite", 0)
    rows = []
    for r in a.get("risks") or []:
        li, im = int(_f(r.get("likelihood"), "likelihood", 1)), int(_f(r.get("impact"), "impact", 1))
        if not (1 <= li <= 5 and 1 <= im <= 5):
            raise InstError("likelihood and impact: 1 to 5.")
        ctl = r.get("control_effect", 0)
        res = max(1, li * im - int(_f(ctl, "control_effect", 0)))
        rows.append({"risk": r.get("name"), "inherent": li * im, "residual": res, "over_appetite": res > app})
    heat = [[0] * 5 for _ in range(5)]
    for r in a.get("risks") or []:
        heat[int(r["impact"]) - 1][int(r["likelihood"]) - 1] += 1
    return {"risks": rows, "heat_map_impact_by_likelihood": heat, "over_appetite": [r["risk"] for r in rows if r["over_appetite"]]}


TP_FIELDS = ("name", "service", "critical", "contract_end", "data_location", "subcontractors", "exit_plan", "last_assessed")


def third_party(a: dict[str, Any]) -> dict[str, Any]:
    need = list(a.get("required_fields") or TP_FIELDS)
    out = []
    for v in a.get("vendors") or []:
        miss = [f for f in need if v.get(f) in (None, "", [])]
        out.append({"vendor": v.get("name"), "missing": miss, "critical_without_exit_plan": bool(v.get("critical")) and not v.get("exit_plan")})
    return {"vendors": out, "incomplete": [x["vendor"] for x in out if x["missing"]],
            "critical_without_exit_plan": [x["vendor"] for x in out if x["critical_without_exit_plan"]],
            "fields_from": "yours" if a.get("required_fields") else "Hoola's starting list" + NOT_CONFIRMED}


def models(a: dict[str, Any]) -> dict[str, Any]:
    today = _d(a.get("today") or date.today().isoformat(), "today")
    out = []
    for m in a.get("models") or []:
        v = m.get("validated")
        due = (_d(v, "validated") + timedelta(days=int(_f(m.get("validate_every_days", 365), "validate_every_days", 1)))) if v else None
        out.append({"model": m.get("name"), "owner": m.get("owner") or None, "ai": bool(m.get("ai")),
                    "validation_due": due.isoformat() if due else None, "overdue": due is None or due < today})
    return {"models": out, "overdue": [m["model"] for m in out if m["overdue"]], "no_owner": [m["model"] for m in out if not m["owner"]]}


def ecl(a: dict[str, Any]) -> dict[str, Any]:
    from ...riskdesk import credit as RC
    try:
        return RC.ecl(a.get("exposures") or [], a.get("stage2_dpd", 30), a.get("stage3_dpd", 90))
    except ValueError as e:
        raise InstError(str(e))


# ---- audit --------------------------------------------------------------------------------------------------------------------

def pbc(a: dict[str, Any]) -> dict[str, Any]:
    today = _d(a.get("today") or date.today().isoformat(), "today")
    out = []
    for x in a.get("items") or []:
        late = not x.get("received") and x.get("due") and _d(x["due"], "due") < today
        out.append({"item": x.get("item"), "owner": x.get("owner"), "received": bool(x.get("received")), "late": bool(late)})
    return {"items": out, "outstanding": [x["item"] for x in out if not x["received"]], "late": [x["item"] for x in out if x["late"]]}


def sample(a: dict[str, Any]) -> dict[str, Any]:
    pop = [str(x) for x in a.get("population") or []]
    n = int(_f(a.get("size"), "size", 1))
    if n > len(pop):
        raise InstError(f"size {n} is more than the population ({len(pop)}).")
    seed = int(a["seed"]) if a.get("seed") is not None else secrets.randbelow(10**9)
    pick = sorted(random.Random(seed).sample(range(len(pop)), n))
    return {"sample": [pop[i] for i in pick], "seed": seed, "population": len(pop),
            "says": "The seed is recorded: the same seed and population give the same sample."}


def control_test(a: dict[str, Any]) -> dict[str, Any]:
    res = a.get("results") or []
    if not res:
        raise InstError("results: [{item, passed, note}] - what each sampled item showed.")
    fails = [r for r in res if not r.get("passed")]
    tol = int(_f(a.get("tolerated_failures", 0), "tolerated_failures", 0))
    return {"tested": len(res), "failures": [{"item": r.get("item"), "note": r.get("note")} for r in fails],
            "conclusion": "effective" if len(fails) <= tol else "deficiency", "tolerated_failures": tol,
            "says": "The conclusion follows your tolerance; whether a deficiency is significant is the auditor's judgement."}


def je_test(a: dict[str, Any]) -> dict[str, Any]:
    pe = _d(a["period_end"], "period_end") if a.get("period_end") else None
    users = {str(u) for u in a.get("usual_users") or []}
    out = []
    for j in a.get("journals") or []:
        d = _d(j.get("date"), "journals.date")
        amt = _f(j.get("amount"), "amount")
        flags = []
        if d.weekday() >= 5:
            flags.append("weekend")
        if amt >= 1000 and amt % 1000 == 0:
            flags.append("round amount")
        if pe and abs((pe - d).days) <= int(_f(a.get("near_days", 3), "near_days", 0)):
            flags.append("near period end")
        if users and str(j.get("user")) not in users:
            flags.append("unusual user")
        if not str(j.get("description") or "").strip():
            flags.append("no description")
        if flags:
            out.append({"id": j.get("id"), "flags": flags})
    return {"flagged": sorted(out, key=lambda x: -len(x["flags"])), "tested": len(a.get("journals") or [])}


# ---- governance ----------------------------------------------------------------------------------------------------------------

def board_pack(a: dict[str, Any]) -> dict[str, Any]:
    items = a.get("agenda") or []
    papers = {str(p).lower() for p in a.get("papers") or []}
    out = [{"item": i.get("item"), "paper": i.get("paper"), "paper_present": not i.get("paper") or str(i["paper"]).lower() in papers}
           for i in items]
    acts = [x for x in a.get("actions") or [] if not x.get("done")]
    return {"agenda": out, "papers_missing": [x["paper"] for x in out if not x["paper_present"]], "open_actions": acts}


def cap_table(a: dict[str, Any]) -> dict[str, Any]:
    holders = {str(h["name"]): int(_f(h.get("shares"), "shares", 0)) for h in a.get("holders") or []}
    total = sum(holders.values())
    if not total:
        raise InstError("holders: [{name, shares}].")
    out = {"before": {k: {"shares": v, "pct": round(v * 100 / total, 4)} for k, v in holders.items()}, "shares_before": total}
    if a.get("raise") is not None:
        pre = Decimal(str(_f(a.get("pre_money"), "pre_money", 0.01)))
        new_money = Decimal(str(_f(a["raise"], "raise", 0)))
        price = pre / total
        new = int((new_money / price).to_integral_value(rounding="ROUND_FLOOR"))
        post = total + new
        inv = str(a.get("investor") or "new investor")
        after = {**holders, inv: holders.get(inv, 0) + new}
        out.update({"price_per_share": float(price.quantize(Decimal("0.0001"), ROUND_HALF_UP)), "new_shares": new,
                    "post_money": float(pre + new_money), "shares_after": post,
                    "after": {k: {"shares": v, "pct": round(v * 100 / post, 4)} for k, v in after.items()}})
    return out


def related_party(a: dict[str, Any]) -> dict[str, Any]:
    rp = {str(x).lower(): str(x) for x in a.get("related") or []}
    hits = [t for t in a.get("transactions") or [] if str(t.get("counterparty") or "").lower() in rp]
    return {"related_transactions": hits, "total": round(sum(_f(t.get("amount"), "amount") for t in hits), 2),
            "says": "These need the approval and disclosure your rules require."}


def whistle(tenant: str, ws: str, a: dict[str, Any]) -> dict[str, Any]:
    if any(k in a for k in ("reporter", "reporter_name", "name", "email", "phone")):
        raise InstError("A whistleblowing case keeps no name or contact of the person reporting: leave them out.")
    case = "WB-" + hashlib.sha256(f"{tenant}{ws}{datetime.now(timezone.utc).isoformat()}{secrets.token_hex(4)}".encode()).hexdigest()[:8].upper()
    rec = {"case": case, "what": str(a.get("what") or "")[:2000], "area": str(a.get("area") or "")[:80], "on": date.today().isoformat()}
    MC.save(tenant, ws, lambda s: s.setdefault("whistle", []).append(rec))
    EV.record(tenant, ws, "whistle", "whistle", f"case {case} logged")
    return {"case": case, "says": "Logged with a case number only. Give the reporter the number so they can follow it."}


# ---- plumbing: keys, retention, export ---------------------------------------------------------------------------------------

SCOPES = ("read", "draft", "check", "admin")


def api_key(tenant: str, ws: str, a: dict[str, Any]) -> dict[str, Any]:
    MC.person(tenant, ws, a.get("person"), "admin")
    if a.get("revoke"):
        MC.save(tenant, ws, lambda s: [k.__setitem__("revoked", True) for k in s.get("keys", []) if k["id"] == a["revoke"]])
        return {"revoked": a["revoke"]}
    scopes = [x for x in a.get("scopes") or [] if x in SCOPES]
    if not scopes:
        raise InstError("scopes: " + ", ".join(SCOPES))
    raw = "hik_" + secrets.token_urlsafe(24)
    kid = "k" + secrets.token_hex(4)
    MC.save(tenant, ws, lambda s: s.setdefault("keys", []).append({"id": kid, "hash": hashlib.sha256(raw.encode()).hexdigest(),
                                                                   "scopes": scopes, "made": date.today().isoformat()}))
    EV.record(tenant, ws, str(a.get("person")), "inst", f"API key {kid} made {scopes}")
    return {"id": kid, "key": raw, "scopes": scopes, "says": "Shown once; only its hash is kept. A key can never check a draft it did not see."}


def key_allows(tenant: str, ws: str, raw: str, scope: str) -> bool:
    h = hashlib.sha256(str(raw).encode()).hexdigest()
    for k in MC.inst(MC.workspace(tenant, ws)).get("keys") or []:
        if k["hash"] == h and not k.get("revoked"):
            return scope in k["scopes"] or "admin" in k["scopes"]
    return False


def retention(tenant: str, ws: str, a: dict[str, Any]) -> dict[str, Any]:
    MC.person(tenant, ws, a.get("person"), "admin")
    keep = {str(k): int(_f(v, f"keep.{k}", 1)) for k, v in (a.get("keep_years") or {}).items()}
    if not keep:
        raise InstError("keep_years: {sar: 5, kyc: 5, ...} - your record-keeping periods.")
    MC.save(tenant, ws, lambda s: s.__setitem__("retention", keep))
    return {"keep_years": keep, "says": "Kept as your periods; nothing is deleted before them, and deleting after them is your tap."}


def export(tenant: str, ws: str, a: dict[str, Any]) -> dict[str, Any]:
    MC.person(tenant, ws, a.get("person"), "admin")
    st = MC.inst(MC.workspace(tenant, ws))
    st = {k: v for k, v in st.items() if k != "keys"}
    dr = MC.drafts(tenant, ws, {"person": a.get("person")})["drafts"]
    blob = json.dumps({"workspace": ws, "registers": st, "drafts": dr, "events": EV.events(tenant, ws, 2000)}, default=str)
    return {"file": blob, "bytes": len(blob), "sha256": hashlib.sha256(blob.encode()).hexdigest()}


# ---- door ----------------------------------------------------------------------------------------------------------------------

_WS = {"sar_draft", "sar_score", "obligations", "incident", "whistle", "api_key", "retention", "export"}
_MC = {"person_add": MC.person_add, "limits": MC.limits, "submit": MC.submit, "revise": MC.revise, "check": MC.check, "drafts": MC.drafts}
ACTIONS = tuple(_MC) + ("aml_triage", "sar_draft", "sar_score", "kyc_review", "sanctions", "obligations", "policy_check", "promotion_check",
                        "complaints_mi", "incident", "rcsa", "third_party", "models", "ecl", "pbc", "sample", "control_test", "je_test",
                        "board_pack", "cap_table", "related_party", "whistle", "api_key", "retention", "export")


def run(tenant: str, action: str, a: dict[str, Any], actor: str = "owner") -> dict[str, Any]:
    a = {k: v for k, v in dict(a).items() if k not in ("state", "approved_by", "checks")}      # no state is ever set from outside
    ws = str(a.get("workspace") or "")
    if re.search(r"file|submit_to|freeze|report_to|approve_draft|set_state|force", action):
        raise L.Refused("file_as_institution", DECIDER)
    try:
        if action in _MC:
            if not ws:
                raise InstError("workspace: the institution's workspace.")
            out = _MC[action](tenant, ws, a)
        elif action in _WS:
            if not ws and action != "incident":
                raise InstError("workspace: the institution's workspace.")
            out = globals()[action](tenant, ws, a)
        elif action in ACTIONS:
            out = globals()[action](a)
        else:
            raise InstError("action: " + ", ".join(ACTIONS))
    except MC.MCError as e:
        raise InstError(str(e))
    out.setdefault("not_advice", L.NOT_ADVICE)
    return out
