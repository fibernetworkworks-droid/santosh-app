"""The wage working paper: per person units x rate (the rate row named), overtime by HER country's rule (her contract may only go
higher), allowances, statutory deductions from HER rows with a source, advances recovered (never above her cap), net. Every
line is checked against the minimum (floor) row for the trade; nobody is paid twice for the same day.

Prepared (Hoola or a person) -> checked by one person -> approved by another (two above her limit). The approval is bound to
the run's hash: if a mark, a rate or an advance changes the paper afterwards, the run goes back to draft. The payment file is
made for her bank; she uploads it. Paid is recorded only from her tap with the bank's reference. Hoola moves no money."""
from __future__ import annotations

import csv
import hashlib
import io
import json
import re
from collections import defaultdict
from datetime import date, timedelta
from typing import Any

from sqlalchemy import select

from ..db import session
from .core import (LOCK, LabourError, S, day_of, employer_id, find_rate, need_who, num, own_employer, paper_state, resolve, settings, site_id,
                   site_names, span, stamp, tables, today)
from .models import LdAdvance, LdEmployer, LdRate, LdRun, LdSite, LdWorker
from .muster import effective

NEVER_KEPT = "Account numbers are used for this one file and never kept."


def _week_key(d: str, start: int) -> str:
    x = date.fromisoformat(d)
    return (x - timedelta(days=(x.weekday() - start) % 7)).isoformat()


def _ot_rule(st: dict[str, Any]) -> dict[str, Any]:
    o = st["ot"]
    her = float(st.get("ot_x") or 0)
    if o["basis"] == "contract":
        return {"basis": "day", "after": st["day_hours"], "x": her, "set": her > 0, "checked": True,
                "say": (f"your contract: {her:g}x beyond {st['day_hours']:g} hours a day" if her else "not set - write your contract's overtime multiplier in Settings"),
                "source": o["source"]}
    if o["check"]:
        return {"basis": o["basis"], "after": o["after"] or st["day_hours"], "x": her, "set": her > 0, "checked": False,
                "say": (f"your contract: {her:g}x (the country rule is not checked here: {o['source']})" if her else
                        f"check this: the overtime rule for {st['country'] or 'your country'} is not checked - write your contract's multiplier"),
                "source": o["source"]}
    x = max(float(o["x"]), her)
    after = o["after"] if o["basis"] == "week" else (o["after"] or st["day_hours"])
    return {"basis": o["basis"], "after": after, "x": x, "set": True, "checked": True,
            "say": f"{x:g}x beyond {after:g} hours a {o['basis']}" + (" (your contract, above the country rule)" if her > float(o["x"]) else ""), "source": o["source"]}


def _compute(s, tenant: str, run: LdRun, st: dict[str, Any]) -> dict[str, Any]:
    days = span(run.start, run.end)
    per, _heads = effective(s, tenant, days[0], days[-1], run.site_id)
    wk = {r.id: r for r in s.scalars(select(LdWorker).where(LdWorker.tenant_id == tenant)).all()}
    sites_ = {r.id: r for r in s.scalars(select(LdSite).where(LdSite.tenant_id == tenant)).all()}
    all_rates = s.scalars(select(LdRate).where(LdRate.tenant_id == tenant).order_by(LdRate.created_at, LdRate.id)).all()
    rule = _ot_rule(st)
    dh = float(st["day_hours"])
    inputs = run.inputs or {}
    allow = inputs.get("allowances") or {}
    by_w: dict[str, list] = defaultdict(list)
    for (d, si, w), m in per.items():
        if m.employer_id == run.employer_id and w in wk:
            by_w[w].append((d, si, m))
    others = [r for r in s.scalars(select(LdRun).where(LdRun.tenant_id == tenant, LdRun.employer_id == run.employer_id,
                                                        LdRun.status != "cancelled")).all() if r.id != run.id and r.start <= run.end and r.end >= run.start]
    advances = defaultdict(list)
    for a in s.scalars(select(LdAdvance).where(LdAdvance.tenant_id == tenant)).all():
        if a.amount - a.recovered > 1e-9:
            advances[a.worker_id].append(a)
    required = st["required"]
    pbad = paper_state(s, tenant, list(by_w), run.end, required)
    lines, bad_n = [], 0
    for w, marks in sorted(by_w.items(), key=lambda kv: wk[kv[0]].name):
        wr = wk[w]
        marks.sort()
        checks: list[dict[str, str]] = []
        dsum = sum(m.value for d, si, m in marks)
        if dsum <= 0:
            continue
        site_for = max({si for d, si, m in marks}, key=lambda x: sum(1 for d, si, m in marks if si == x))
        region = (sites_[site_for].region if site_for in sites_ else "") or st["region"]
        rate = find_rate(all_rates, "pay", wr, site_for, region, run.end)
        floor = find_rate(all_rates, "floor", wr, site_for, region, run.end)
        # hours and overtime
        norm_h, ot_h, pieces = 0.0, 0.0, 0.0
        if rule["basis"] == "week":
            weeks: dict[str, float] = defaultdict(float)
            for d, si, m in marks:
                weeks[_week_key(d, int(st["week_start"]))] += (m.hours or dh * m.value) + (m.ot_hours if not m.hours else 0)
                pieces += m.pieces
            for k, h in weeks.items():
                o = max(0.0, h - float(rule["after"]))
                ot_h += o
                norm_h += h - o
        else:
            for d, si, m in marks:
                pieces += m.pieces
                if m.ot_hours:
                    o = m.ot_hours
                    n = (m.hours - o) if m.hours else dh * m.value
                elif m.hours:
                    o = max(0.0, m.hours - float(rule["after"]))
                    n = m.hours - o
                else:
                    o, n = 0.0, dh * m.value
                ot_h += o
                norm_h += max(n, 0.0)
        basic, hourly, day_eq = 0.0, 0.0, 0.0
        if rate is None:
            checks.append({"sev": "bad", "text": f"No pay rate on file for {wr.trade or 'this worker'} - add one in Settings."})
        else:
            if rate.basis == "day":
                basic, hourly, day_eq = dsum * rate.rate, rate.rate / dh, rate.rate
            elif rate.basis == "hour":
                basic, hourly, day_eq = norm_h * rate.rate, rate.rate, rate.rate * dh
            else:
                pq = pieces or float((inputs.get("pieces") or {}).get(w) or 0)
                basic = pq * rate.rate
                hourly = basic / norm_h if norm_h else 0.0
                day_eq = basic / dsum if dsum else 0.0
                if not pq:
                    checks.append({"sev": "warn", "text": "Paid by the piece but no pieces are recorded for this period."})
        ot_pay = 0.0
        if ot_h > 1e-9:
            if not rule["set"]:
                checks.append({"sev": "bad", "text": f"{ot_h:g} overtime hours, but {rule['say']}."})
            else:
                ot_pay = ot_h * hourly * float(rule["x"])
        al = float(allow.get(w) or allow.get(wr.name) or 0)
        gross = basic + ot_pay + al
        deds, emp_c = [], 0.0
        for row in st.get("deductions") or []:
            b = basic if row["base"] == "basic" else gross
            if row.get("cap"):
                b = min(b, float(row["cap"]))
            amt = round(b * float(row["pct"]) / 100, 2)
            deds.append({"name": row["name"], "amount": amt, "source": row["source"]})
            emp_c += round(b * float(row.get("employer_pct") or 0) / 100, 2)
        dtot = round(sum(x["amount"] for x in deds), 2)
        owed = sum(a.amount - a.recovered for a in advances.get(w, []))
        sched = sum((a.per_run or (a.amount - a.recovered)) for a in advances.get(w, []))
        capv = max(0.0, (gross - dtot)) * float(st["advance_cap"]) / 100
        adv = round(min(owed, sched, capv), 2) if owed > 1e-9 else 0.0
        if owed > 1e-9 and adv + 1e-9 < min(owed, sched):
            checks.append({"sev": "info", "text": f"Advance recovery held to {adv:g} by your {st['advance_cap']:g}% cap ({owed - adv:g} still owed)."})
        net = round(gross - dtot - adv, 2)
        # checks
        if rate is not None and floor is None:
            checks.append({"sev": "warn", "text": f"No minimum rate on file for {wr.trade or wr.skill or 'this trade'} - add the floor row with its source."})
        elif rate is not None and floor is not None:
            f_eq = floor.rate if floor.basis == "day" else floor.rate * dh if floor.basis == "hour" else 0.0
            if f_eq and day_eq + 1e-9 < f_eq:
                checks.append({"sev": "bad", "text": f"Pays {day_eq:,.2f} a day, below the minimum {f_eq:,.2f} a day ({floor.source or 'no source written on the floor row'})."})
            elif not floor.source:
                checks.append({"sev": "warn", "text": "The minimum rate row has no source written."})
            else:
                checks.append({"sev": "ok", "text": f"At or above the minimum {f_eq:,.2f} a day ({floor.source})."})
        if w in pbad:
            checks.append({"sev": "warn", "text": "Papers: " + "; ".join(pbad[w]) + "."})
        for o in others:
            if any(ln.get("worker_id") == w for ln in (o.lines or [])):
                checks.append({"sev": "bad", "text": f"Already in {o.number} ({o.start} to {o.end}) for days in this period - paid twice?"})
        bad_n += sum(1 for c in checks if c["sev"] == "bad")
        lines.append({"worker_id": w, "name": wr.name, "code": wr.code, "trade": wr.trade, "bank_last4": wr.bank_last4, "language": wr.language,
                      "days": round(dsum, 2), "normal_hours": round(norm_h, 2), "ot_hours": round(ot_h, 2), "pieces": round(pieces, 3),
                      "rate": rate.rate if rate else None, "basis": rate.basis if rate else "", "rate_source": (rate.source if rate else ""),
                      "basic": round(basic, 2), "ot_x": rule["x"] if ot_h > 1e-9 else 0, "ot_pay": round(ot_pay, 2), "allowances": round(al, 2),
                      "gross": round(gross, 2), "deductions": deds, "deduction_total": dtot, "employer_contrib": round(emp_c, 2), "advance": adv,
                      "net": net, "checks": checks})
    total = round(sum(ln["net"] for ln in lines), 2)
    h = hashlib.sha256(json.dumps({"p": [run.employer_id, run.site_id, run.start, run.end],
                                   "l": [[ln["worker_id"], ln["days"], ln["normal_hours"], ln["ot_hours"], ln["rate"], ln["gross"], ln["deduction_total"],
                                          ln["advance"], ln["net"]] for ln in lines]}, sort_keys=True).encode()).hexdigest()
    return {"lines": lines, "total": total, "hash": h, "bad": bad_n, "ot": rule,
            "totals": {k: round(sum(ln[k] for ln in lines), 2) for k in ("basic", "ot_pay", "allowances", "gross", "deduction_total", "advance", "net",
                                                                          "employer_contrib", "days", "ot_hours")}}


def _number(s, tenant: str) -> str:
    n = len(s.scalars(select(LdRun.id).where(LdRun.tenant_id == tenant)).all()) + 1
    return f"LR-{n:04d}"


def _changes(s, tenant: str, run: LdRun, lines: list[dict[str, Any]]) -> list[str]:
    prev = [r for r in s.scalars(select(LdRun).where(LdRun.tenant_id == tenant, LdRun.employer_id == run.employer_id, LdRun.site_id == run.site_id,
                                                     LdRun.status.in_(("approved", "paid", "checked")))).all() if r.end < run.start]
    if not prev:
        return []
    p = max(prev, key=lambda r: r.end)
    old = {ln["worker_id"]: ln for ln in (p.lines or [])}
    new = {ln["worker_id"]: ln for ln in lines}
    out = []
    for w, ln in new.items():
        o = old.get(w)
        if o is None:
            out.append(f"{ln['name']}: new this period ({ln['days']:g} days).")
        elif o["net"] and abs(ln["net"] - o["net"]) / max(o["net"], 1) > 0.1:
            why = "more days" if ln["days"] > o["days"] else "fewer days" if ln["days"] < o["days"] else \
                  "a new rate" if ln["rate"] != o["rate"] else "overtime" if ln["ot_hours"] != o["ot_hours"] else "deductions or advances"
            out.append(f"{ln['name']}: {o['net']:,.2f} -> {ln['net']:,.2f} ({why}).")
    for w, o in old.items():
        if w not in new:
            out.append(f"{o['name']}: in {p.number}, not in this period.")
    return out[:30]


def _log(run: LdRun, tenant: str, text: str) -> None:
    run.log = list(run.log or []) + [{"at": stamp(tenant), "text": S(text, 300)}]


def draft_run(tenant: str, start: str, end: str, employer: str = "", site: str = "", who: str = "", allowances: Any = None,
              pieces: Any = None) -> dict[str, Any]:
    tables()
    st = settings(tenant)
    a, b = day_of(start, tenant, "From"), day_of(end, tenant, "To")
    span(a, b)
    with LOCK, session() as s:
        eid = employer_id(s, tenant, employer)
        sid = site_id(s, tenant, site) if site else ""
        dup = s.scalars(select(LdRun).where(LdRun.tenant_id == tenant, LdRun.employer_id == eid, LdRun.site_id == sid, LdRun.start == a,
                                            LdRun.end == b, LdRun.status.in_(("draft", "checked")))).first()
        r = dup or LdRun(tenant_id=tenant, number=_number(s, tenant), employer_id=eid, site_id=sid, start=a, end=b, inputs={}, log=[], lines=[], paid={})
        if dup is None:
            s.add(r)
        inp = dict(r.inputs or {})
        if isinstance(allowances, dict):
            inp["allowances"] = {S(k, 120): num(v, "Allowance") for k, v in allowances.items()}
        if isinstance(pieces, dict):
            inp["pieces"] = {S(k, 120): num(v, "Pieces") for k, v in pieces.items()}
        r.inputs = inp
        r.status = "draft"
        r.checked_by = r.approved_by = r.approved_by2 = ""
        r.prepared_by = S(who, 80) or "Hoola"
        c = _compute(s, tenant, r, st)
        r.lines, r.total, r.hash = c["lines"], c["total"], c["hash"]
        _log(r, tenant, f"Prepared by {r.prepared_by}")
        s.flush()
        rid = r.id
    out = run_view(tenant, rid)
    out["say"] = f"Run {out['number']} prepared: {len(out['lines'])} people, net {out['total']:,.2f} {st['currency']}" + \
                 (f"; {out['bad']} line check(s) must be fixed before it can be checked" if out["bad"] else "; ready for a person to check") + "."
    return out


def run_view(tenant: str, id: str) -> dict[str, Any]:
    tables()
    st = settings(tenant)
    with LOCK, session() as s:
        r = s.get(LdRun, id)
        if r is None or r.tenant_id != tenant:
            raise LabourError("No such wage run.")
        stale = False
        if r.status in ("draft", "checked", "approved"):
            c = _compute(s, tenant, r, st)
            if r.status == "draft":
                r.lines, r.total, r.hash = c["lines"], c["total"], c["hash"]
            elif c["hash"] != r.hash:
                stale = True
                _log(r, tenant, f"Changed after it was {r.status} (a mark, rate or advance moved): back to draft")
                r.status, r.checked_by, r.approved_by, r.approved_by2 = "draft", "", "", ""
                r.lines, r.total, r.hash = c["lines"], c["total"], c["hash"]
            ot, bad = c["ot"], c["bad"]
            totals = c["totals"]
        else:
            ot = _ot_rule(st)
            bad = sum(1 for ln in r.lines or [] for x in ln.get("checks") or [] if x["sev"] == "bad")
            totals = {k: round(sum(ln.get(k, 0) for ln in r.lines or []), 2) for k in ("basic", "ot_pay", "allowances", "gross", "deduction_total", "advance",
                                                                                       "net", "employer_contrib", "days", "ot_hours")}
        emp = s.get(LdEmployer, r.employer_id)
        sn = site_names(s, tenant)
        changes = _changes(s, tenant, r, r.lines or [])
        need2 = bool(st["second_limit"]) and r.total > float(st["second_limit"])
        return {"id": r.id, "number": r.number, "employer_id": r.employer_id, "employer": emp.name if emp else "", "own": bool(emp and emp.kind == "own"),
                "site_id": r.site_id, "site": sn.get(r.site_id, "Every site"), "start": r.start, "end": r.end, "status": r.status, "stale": stale,
                "lines": r.lines or [], "total": r.total, "totals": totals, "hash": r.hash, "bad": bad, "ot": ot, "prepared_by": r.prepared_by,
                "checked_by": r.checked_by, "approved_by": r.approved_by, "approved_by2": r.approved_by2, "second_needed": need2, "log": r.log or [],
                "paid": r.paid or {}, "changes": changes, "currency": st["currency"], "rail": st["pack"]["rail"]}


def runs(tenant: str, status: str = "") -> list[dict[str, Any]]:
    tables()
    with session() as s:
        emp = {r.id: r.name for r in s.scalars(select(LdEmployer).where(LdEmployer.tenant_id == tenant)).all()}
        sn = site_names(s, tenant)
        q = select(LdRun).where(LdRun.tenant_id == tenant)
        if status:
            q = q.where(LdRun.status == status)
        return [{"id": r.id, "number": r.number, "employer": emp.get(r.employer_id, ""), "site": sn.get(r.site_id, "Every site"), "start": r.start, "end": r.end,
                 "status": r.status, "total": r.total, "people": len(r.lines or []), "checked_by": r.checked_by, "approved_by": r.approved_by,
                 "bad": sum(1 for ln in r.lines or [] for x in ln.get("checks") or [] if x["sev"] == "bad")}
                for r in sorted(s.scalars(q).all(), key=lambda r: (r.end, r.number), reverse=True)]


def check_run(tenant: str, id: str, who: str) -> dict[str, Any]:
    who = need_who(who, "the check")
    v = run_view(tenant, id)
    if v["status"] != "draft":
        raise LabourError(f"{v['number']} is {v['status']}: only a draft is checked.")
    if v["bad"]:
        raise LabourError(f"{v['bad']} line check(s) must be fixed first (rates, the minimum rate, overtime rule, paid twice).")
    if not v["lines"]:
        raise LabourError("The run has nobody in it.")
    if who.lower() == (v["prepared_by"] or "").lower():
        raise LabourError("The person who prepared the run cannot also check it.")
    with LOCK, session() as s:
        r = s.get(LdRun, id)
        r.status, r.checked_by = "checked", who
        _log(r, tenant, f"Checked by {who}")
    out = run_view(tenant, id)
    out["say"] = f"{v['number']} checked by {who}. A second person approves it."
    return out


def approve_run(tenant: str, id: str, who: str, who2: str = "") -> dict[str, Any]:
    who = need_who(who, "the approval")
    v = run_view(tenant, id)
    if v["status"] != "checked":
        raise LabourError(f"{v['number']} is {v['status']}" + (" - it changed after it was checked, so it is a draft again" if v["stale"] else "") + ": it must be checked first.")
    if who.lower() in ((v["checked_by"] or "").lower(), (v["prepared_by"] or "").lower()):
        raise LabourError("The approver must be a different person from whoever prepared and checked the run.")
    w2 = S(who2, 80)
    if v["second_needed"]:
        if not w2:
            raise LabourError(f"Above your limit of {settings(tenant)['second_limit']:,.2f}: a second approver's name is needed.")
        if w2.lower() in (who.lower(), (v["checked_by"] or "").lower(), (v["prepared_by"] or "").lower()):
            raise LabourError("The second approver must be another person.")
    with LOCK, session() as s:
        r = s.get(LdRun, id)
        r.status, r.approved_by, r.approved_by2 = "approved", who, w2
        _log(r, tenant, f"Approved by {who}" + (f" and {w2}" if w2 else "") + f" (paper {r.hash[:12]})")
    out = run_view(tenant, id)
    out["say"] = f"{v['number']} approved by {who}" + (f" and {w2}" if w2 else "") + ". Make the payment file and upload it to your bank yourself."
    return out


def cancel_run(tenant: str, id: str, who: str, reason: str = "") -> dict[str, Any]:
    who = need_who(who, "cancelling the run")
    with LOCK, session() as s:
        r = s.get(LdRun, id)
        if r is None or r.tenant_id != tenant:
            raise LabourError("No such wage run.")
        if r.status == "paid":
            raise LabourError("A paid run stays on the record.")
        r.status = "cancelled"
        _log(r, tenant, f"Cancelled by {who}: {S(reason, 200) or 'no reason given'}")
        return {"say": f"{r.number} cancelled."}


def _ready(tenant: str, id: str) -> dict[str, Any]:
    v = run_view(tenant, id)
    if v["status"] not in ("approved", "paid"):
        raise LabourError(f"{v['number']} is {v['status']}" + (" (it changed after approval)" if v["stale"] else "") + ": only an approved run has a payment file.")
    return v


def payment_file(tenant: str, id: str, fmt: str = "", accounts: Any = None, from_account: str = "") -> dict[str, Any]:
    v = _ready(tenant, id)
    fmt = fmt or v["rail"]["format"]
    lines = [ln for ln in v["lines"] if ln["net"] > 0]
    buf = io.StringIO()
    w = csv.writer(buf)
    note = ""
    if fmt == "csv":
        w.writerow(["payee", "your reference", "bank (last 4)", "amount", "currency", "reference"])
        for ln in lines:
            w.writerow([ln["name"], ln["code"] or ln["worker_id"][-6:], ln["bank_last4"], f"{ln['net']:.2f}", v["currency"], f"{v['number']} {v['end']}"])
        note = "Your bank matches the payees by your reference; the accounts are in your bank's payee list, not here."
    elif fmt == "in_bulk":
        acc = accounts if isinstance(accounts, dict) else {}
        bad = []
        w.writerow(["beneficiary name", "account number", "ifsc", "amount", "narration"])
        for ln in lines:
            x = acc.get(ln["worker_id"]) or acc.get(ln["name"]) or {}
            no, ifsc = re.sub(r"\s", "", S(x.get("account"), 30)), S(x.get("ifsc"), 11).upper()
            if not re.fullmatch(r"\d{9,18}", no) or not re.fullmatch(r"[A-Z]{4}0[A-Z0-9]{6}", ifsc):
                bad.append(ln["name"])
                continue
            if ln["bank_last4"] and not no.endswith(ln["bank_last4"]):
                bad.append(ln["name"] + " (does not end in " + ln["bank_last4"] + ")")
                continue
            w.writerow([ln["name"], no, ifsc, f"{ln['net']:.2f}", f"Wages {v['start']} to {v['end']}"])
        if bad:
            raise LabourError("Type an account number (9-18 digits) and IFSC for " + ", ".join(bad[:8]) + ". " + NEVER_KEPT)
        note = NEVER_KEPT
    elif fmt == "ae_wps":
        w.writerow(["employee code", "name", "days", "fixed pay", "variable pay", "deductions", "net", "period from", "period to"])
        for ln in lines:
            w.writerow([ln["code"] or ln["worker_id"][-6:], ln["name"], ln["days"], f"{ln['basic']:.2f}", f"{ln['ot_pay'] + ln['allowances']:.2f}",
                        f"{ln['deduction_total'] + ln['advance']:.2f}", f"{ln['net']:.2f}", v["start"], v["end"]])
        note = "Your agent bank turns this into the salary information file; its exact layout is the bank's - check this before you upload."
    else:
        raise LabourError("Format: csv, in_bulk (India, accounts typed for this file) or ae_wps (UAE).")
    return {"file": buf.getvalue(), "name": f"{v['number']}-{fmt}.csv", "format": fmt, "count": len(lines),
            "total": round(sum(ln["net"] for ln in lines), 2), "note": note, "say": f"Payment file for {v['number']} ready ({len(lines)} people). Upload it to your bank yourself."}


def mark_paid(tenant: str, id: str, who: str, ref: str, on: str = "", failed: Any = None) -> dict[str, Any]:
    """Her tap with the bank's reference. Failures go back to 'to pay' with the reason; advances count as recovered only when paid."""
    who = need_who(who, "recording the payment")
    ref = S(ref, 80)
    if not ref:
        raise LabourError("The bank's reference (or the WPS report number) for this payment.")
    v = _ready(tenant, id)
    if v["status"] == "paid":
        raise LabourError(f"{v['number']} is already recorded as paid ({v['paid'].get('ref')}).")
    fl = {S(k, 60): S(x, 200) for k, x in (failed or {}).items()} if isinstance(failed, dict) else {}
    names = {ln["name"]: ln["worker_id"] for ln in v["lines"]}
    fl = {names.get(k, k): x for k, x in fl.items()}
    with LOCK, session() as s:
        r = s.get(LdRun, id)
        for ln in r.lines or []:
            if ln["worker_id"] in fl or ln["advance"] <= 0:
                continue
            left = ln["advance"]
            for a in sorted(s.scalars(select(LdAdvance).where(LdAdvance.tenant_id == tenant, LdAdvance.worker_id == ln["worker_id"])).all(), key=lambda a: a.day):
                take = min(left, a.amount - a.recovered)
                if take > 1e-9:
                    a.recovered = round(a.recovered + take, 2)
                    a.history = list(a.history or []) + [{"run": r.number, "amount": round(take, 2), "on": day_of(on, tenant)}]
                    left -= take
        r.status = "paid"
        r.paid = {"ref": ref, "on": day_of(on, tenant, "Paid on"), "by": who, "failed": fl}
        _log(r, tenant, f"Paid recorded by {who}, bank reference {ref}" + (f"; {len(fl)} failed" if fl else ""))
    out = run_view(tenant, id)
    out["say"] = f"{v['number']} recorded as paid (ref {ref})" + (f"; {len(fl)} payment(s) failed and are still to pay" if fl else "") + "."
    return out


def payslips(tenant: str, id: str) -> dict[str, Any]:
    v = _ready(tenant, id)
    st = settings(tenant)
    out = []
    for ln in v["lines"]:
        rows = [("Days", f"{ln['days']:g}"), ("Normal hours", f"{ln['normal_hours']:g}"), ("Rate", f"{ln['rate'] or 0:,.2f} a {ln['basis']}"),
                ("Basic", f"{ln['basic']:,.2f}")]
        if ln["ot_hours"]:
            rows.append((f"Overtime {ln['ot_hours']:g} h at {ln['ot_x']:g}x", f"{ln['ot_pay']:,.2f}"))
        if ln["allowances"]:
            rows.append(("Allowances", f"{ln['allowances']:,.2f}"))
        rows.append(("Gross", f"{ln['gross']:,.2f}"))
        for d in ln["deductions"]:
            rows.append((d["name"], f"-{d['amount']:,.2f}"))
        if ln["advance"]:
            rows.append(("Advance recovered", f"-{ln['advance']:,.2f}"))
        rows.append(("Net pay", f"{ln['net']:,.2f} {v['currency']}"))
        out.append({"worker_id": ln["worker_id"], "name": ln["name"], "language": ln["language"] or st["language"], "rows": rows,
                    "head": f"{st['company'] or 'Your employer'} - {v['site']} - {v['start']} to {v['end']} - {v['number']}"})
    return {"slips": out, "say": f"{len(out)} payslip(s) for {v['number']}. Hoola can put any of them in the worker's language in the chat."}


# ---------------------------------------------------------------- advances
def record_advance(tenant: str, worker: str, amount: Any, given_by: str, day: str = "", per_run: Any = None, note: str = "") -> dict[str, Any]:
    """Records an advance she GAVE (a person's tap); Hoola never pays one."""
    given_by = need_who(given_by, "the advance")
    x = num(amount, "Advance", allow_zero=False)
    with LOCK, session() as s:
        w = resolve(s, tenant, worker)
        a = LdAdvance(tenant_id=tenant, worker_id=w.id, amount=x, per_run=num(per_run or 0, "Per run"), day=day_of(day, tenant), given_by=given_by,
                      note=S(note, 200), history=[])
        s.add(a)
        s.flush()
        return {"id": a.id, "say": f"Advance of {x:,.2f} to {w.name} recorded. It is recovered from wages, never above your cap."}


def advances(tenant: str) -> list[dict[str, Any]]:
    tables()
    with session() as s:
        wn = {r.id: r.name for r in s.scalars(select(LdWorker).where(LdWorker.tenant_id == tenant)).all()}
        return [{"id": a.id, "worker_id": a.worker_id, "worker": wn.get(a.worker_id, ""), "amount": a.amount, "recovered": a.recovered,
                 "left": round(a.amount - a.recovered, 2), "per_run": a.per_run, "day": a.day, "given_by": a.given_by, "note": a.note, "history": a.history or []}
                for a in sorted(s.scalars(select(LdAdvance).where(LdAdvance.tenant_id == tenant)).all(), key=lambda a: a.day, reverse=True)]


def wages_due(tenant: str) -> dict[str, Any]:
    """This period's estimate for her own people from the muster so far, and what waits in runs."""
    st = settings(tenant)
    t0 = today(tenant)
    if st["pay_cycle"] == "monthly":
        start = t0.replace(day=1)
    else:
        start = t0 - timedelta(days=(t0.weekday() - int(st["week_start"])) % 7)
        if st["pay_cycle"] == "fortnightly":
            start = start - timedelta(days=7) if (start.isocalendar()[1] % 2) else start
    with session() as s:
        own = own_employer(s, tenant).id
        tmp = LdRun(tenant_id=tenant, employer_id=own, site_id="", start=start.isoformat(), end=t0.isoformat(), inputs={}, lines=[], id="__estimate__")
        c = _compute(s, tenant, tmp, st)
    return {"start": start.isoformat(), "end": t0.isoformat(), "estimate": c["total"], "people": len(c["lines"]), "ot_hours": c["totals"]["ot_hours"],
            "ot": c["ot"]}
