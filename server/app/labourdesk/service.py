"""The Labour & Wages desk: the Today view, the registers, and the one door every action goes through (`run`).

Actions that decide something or record money - approving a day's muster, checking / approving / cancelling a wage run,
recording it paid, recording an advance given, recording a levy or tax deposit paid, recording a return filed, deciding to
hold or release a subcontractor's payment - are a person's tap on the desk (`TAP`): the chat and the tool can draft them,
never post them. Hoola pays nothing and files nothing."""
from __future__ import annotations

from datetime import timedelta
from typing import Any

from sqlalchemy import select

from ..db import session
from . import levies as LV, muster as MU, packs as P, subs as SB, wages as WG
from .core import FIELDS as CFIELDS
from .core import (LabourError, S, bring_legacy, employers, import_workers, papers, radar, rates, save_employer, save_paper, save_rate, save_settings,
                   save_site, save_worker, settings, sites, stamp, tables, today, workers)
from .models import LdMark

TAP = {"close_day", "check_run", "approve_run", "cancel_run", "mark_paid", "record_advance", "mark_levy_paid", "mark_deposited", "mark_filed",
       "decide_hold", "use_pack", "save_rule"}
READS = {"today", "settings", "sites", "employers", "workers", "worker", "papers", "radar", "rates", "day", "timesheet", "headcount", "runs", "run",
         "advances", "rules", "levies", "payments", "calendar", "period", "pack", "payslips", "registers", "close_out", "wages_due"}


def worker_detail(tenant: str, id: str) -> dict[str, Any]:
    from .core import resolve, worker_view
    tables()
    with session() as s:
        w = resolve(s, tenant, id)
        from .core import owners
        ow = owners(s, tenant)
        d = worker_view(w, ow, ow)
        marks = s.scalars(select(LdMark).where(LdMark.tenant_id == tenant, LdMark.worker_id == w.id).order_by(LdMark.seq.desc()).limit(60)).all()
        d["marks"] = [{"day": m.day, "site": ow.get(m.site_id, ""), "value": m.value, "hours": m.hours, "ot_hours": m.ot_hours, "source": m.source, "who": m.who,
                       "corrects": m.corrects, "reason": m.reason} for m in marks]
    d["papers"] = papers(tenant, "worker", d["id"])
    d["rates"] = [r for r in rates(tenant) if r["worker"] == d["name"] or (r["trade"] and r["trade"].lower() == (d["trade"] or "").lower())]
    d["advances"] = [a for a in WG.advances(tenant) if a["worker_id"] == d["id"]]
    return d


def today_view(tenant: str) -> dict[str, Any]:
    tables()
    st = settings(tenant)
    t0 = today(tenant)
    now_hm = stamp(tenant)[11:16]
    ss = sites(tenant)
    ws = workers(tenant)
    em = employers(tenant)
    dv = MU.day_view(tenant, t0.isoformat())
    yv = MU.day_view(tenant, (t0 - timedelta(days=1)).isoformat())
    rd = radar(tenant)
    rn = WG.runs(tenant)
    lv = LV.levies(tenant)
    cal = LV.calendar(tenant, 60)
    hc = MU.headcount(tenant, 30)
    due = WG.wages_due(tenant) if ws else {"estimate": 0, "people": 0, "ot_hours": 0, "start": t0.isoformat(), "end": t0.isoformat(), "ot": {}}
    week_start = t0 - timedelta(days=(t0.weekday() - int(st["week_start"])) % 7)
    last_start, last_end = week_start - timedelta(days=7), week_start - timedelta(days=1)
    sb = SB.period(tenant, last_start.isoformat(), last_end.isoformat()) if any(e["kind"] == "sub" for e in em) else {"rows": [], "missing": 0}
    needs: list[dict[str, Any]] = []
    marked_sites = {x["site_id"] for x in dv["sites"]}
    for si in ss:
        if si["id"] not in marked_sites and now_hm > st["cutoff"]:
            needs.append({"say": f"{si['name']}: today's muster is not in and the {st['cutoff']} cut-off has passed", "go": "muster", "bad": True})
    for f in dv["flags"]:
        needs.append({"say": "Today: " + f["text"], "go": "muster", "bad": f["sev"] == "bad"})
    for f in [f for f in yv["flags"] if f["sev"] == "bad"][:4]:
        needs.append({"say": "Yesterday: " + f["text"], "go": "muster/" + yv["day"], "bad": True})
    if dv["unknown"]:
        needs.append({"say": f"{len(dv['unknown'])} name(s) on today's muster I could not match - who are they?", "go": "muster"})
    for x in dv["sites"]:
        if not x["closed"] and x["total"] and now_hm > st["cutoff"]:
            needs.append({"say": f"{x['site']}: today's muster ({x['total']} people) waits for the site engineer's approval", "go": "muster"})
    for r in rn:
        if r["status"] == "draft" and r["people"]:
            needs.append({"say": f"Wage run {r['number']} ({r['employer']}, {r['start']} to {r['end']}) " +
                          (f"has {r['bad']} line check(s) to fix" if r["bad"] else "is ready for a person to check"), "go": "wages/" + r["id"], "bad": bool(r["bad"])})
        elif r["status"] == "checked":
            needs.append({"say": f"Wage run {r['number']} checked by {r['checked_by']}: waits for approval", "go": "wages/" + r["id"]})
        elif r["status"] == "approved":
            needs.append({"say": f"Wage run {r['number']} approved: make the payment file, upload it, then record it paid with the bank's reference", "go": "wages/" + r["id"]})
    for p in rd["rows"]:
        if p["lapsed"] or (p["whose"] != "worker" and p["days_left"] <= 30) or (p["whose"] == "worker" and p["days_left"] <= 14):
            needs.append({"say": f"{p['owner'] or 'Your company'}: {p['name']} " + ("lapsed on " + p["valid_to"] if p["lapsed"] else f"ends in {p['days_left']} days ({p['valid_to']})"),
                          "go": "workers", "bad": p["lapsed"]})
    for i in cal["items"]:
        if i.get("in_days") is not None and i["in_days"] <= 7 and not i.get("filed"):
            needs.append({"say": f"{i['what']} - due {i['due']}" + (f" ({i['amount']:,.2f})" if i.get("amount") else "") + (" - late" if i["late"] else ""),
                          "go": "levies", "bad": i["late"]})
    for r in sb["rows"]:
        if r["gaps"]:
            needs.append({"say": f"Last week, {r['say']}", "go": "subs"})
    if not ss:
        needs.append({"say": "Set your country, currency and pay period, then add your sites", "go": "settings"})
    elif not ws:
        needs.append({"say": "Add your workers - paste your sheet or the contractor's register", "go": "workers"})
    elif not st["set"]:
        needs.append({"say": "Set your country so the right overtime, levy and paper rules apply", "go": "settings"})
    if not rates(tenant, "floor") and ws:
        needs.append({"say": "No minimum (floor) rate rows yet: add each trade's floor with its source", "go": "settings"})
    tod = sum(x["total"] for x in dv["sites"])
    own_today = sum(g["present"] + g["half"] + g["count"] for x in dv["sites"] for g in x["gangs"] if g["own"])
    nxt = next((i for i in cal["items"] if not i.get("filed")), None)
    return {"settings": st, "sites": ss, "workers": len(ws), "employers": em, "today": t0.isoformat(),
            "tiles": {"on_site": tod, "own": own_today, "subs": tod - own_today, "planned": sum(x["planned"] for x in ss), "sites_in": len(dv["sites"]),
                      "sites_total": len(ss), "flags": len(dv["flags"]), "serious": dv["serious"], "papers_soon": rd["soon"], "papers_lapsed": rd["lapsed"],
                      "ot_hours": due["ot_hours"], "ot_rule": (due.get("ot") or {}).get("say", ""), "wages_due": due["estimate"], "wages_people": due["people"],
                      "wages_from": due["start"], "next_filing": ({"what": nxt["what"], "due": nxt["due"]} if nxt else None),
                      "levies_due": round(sum(x["amount"] for x in lv if x["status"] == "due"), 2)},
            "chart": hc, "needs": needs[:24], "coming": cal["items"][:10], "radar": rd["rows"][:10],
            "counts": {"muster": len(dv["flags"]) + len(dv["unknown"]), "workers": rd["lapsed"] + rd["soon"],
                       "wages": sum(1 for r in rn if r["status"] in ("draft", "checked", "approved") and r["people"]),
                       "levies": sum(1 for i in cal["items"] if i.get("in_days") is not None and i["in_days"] <= 7 and not i.get("filed")),
                       "subs": sb["missing"]},
            "serious": sum(1 for n in needs if n.get("bad")), "currency": st["currency"]}


def registers(tenant: str, start: str, end: str, site: str = "") -> dict[str, Any]:
    """The muster register and the wage register for a period, ready for an inspector or the client's auditor."""
    ts = MU.timesheet(tenant, start, end, site=site)
    rn = [r for r in WG.runs(tenant) if r["status"] in ("approved", "paid") and r["start"] <= ts["end"] and r["end"] >= ts["start"]]
    wage = []
    for r in rn:
        v = WG.run_view(tenant, r["id"])
        for ln in v["lines"]:
            wage.append({"run": v["number"], "employer": v["employer"], "name": ln["name"], "days": ln["days"], "ot_hours": ln["ot_hours"], "gross": ln["gross"],
                         "deductions": ln["deduction_total"], "advance": ln["advance"], "net": ln["net"], "status": v["status"],
                         "paid_ref": (v["paid"] or {}).get("ref", "")})
    return {"start": ts["start"], "end": ts["end"], "muster": ts["rows"], "wages": wage}


def close_out(tenant: str, site: str = "") -> dict[str, Any]:
    """What is left before a project closes: people still owed, open runs, levies, deposits, filings, papers to surrender, evidence gaps."""
    t0 = today(tenant)
    rn = WG.runs(tenant)
    lv = LV.levies(tenant)
    ad = [a for a in WG.advances(tenant) if a["left"] > 0]
    cal = LV.calendar(tenant, 365)
    st = settings(tenant)
    sb = SB.period(tenant, (t0 - timedelta(days=60)).isoformat(), t0.isoformat())
    lic = [p for p in papers(tenant) if p["whose"] in ("company", "employer") and p["kind"] in ("licence", "registration") and not p["lapsed"]]
    return {"open_runs": [r for r in rn if r["status"] in ("draft", "checked", "approved")], "levies_due": [x for x in lv if x["status"] == "due"],
            "advances_left": ad, "filings": [i for i in cal["items"] if not i.get("filed")][:20], "evidence_gaps": [r for r in sb["rows"] if r["gaps"]],
            "licences": lic, "retention": P.pack(st["country"])["retention"],
            "say": "Close the open runs, pay the levies and deposits, settle the advances, file the returns, collect the missing evidence and "
                   "surrender the work-specific licences; keep the records for your country's retention years."}


def run(tenant: str, part: str, a: dict[str, Any], actor: str = "desk") -> Any:
    """The one door. `actor` 'tool' (the chat) cannot take a TAP action: it drafts, a person posts."""
    a = {k: v for k, v in (a or {}).items() if not str(k).startswith("_")}
    if actor != "desk" and part in TAP:
        raise PermissionError(f"'{part}' is a person's decision on the desk (with their name). Hoola drafts it; it does not post it.")
    if actor != "desk" and part == "payment_file" and a.get("accounts"):
        raise PermissionError("Account numbers are typed on the desk for the one file, never in the chat.")
    g = lambda k: a.get(k)   # noqa: E731
    gs = lambda k: S(a.get(k), 300)   # noqa: E731
    if part == "today":
        bring_legacy(tenant)
    f = {
        "today": lambda: today_view(tenant),
        "settings": lambda: settings(tenant),
        "save_settings": lambda: save_settings(tenant, **{k: v for k, v in a.items() if k in CFIELDS}),
        "pack": lambda: P.pack(settings(tenant)["country"], settings(tenant)["region"]),
        "sites": lambda: {"sites": sites(tenant, True)},
        "save_site": lambda: save_site(tenant, gs("name"), gs("project"), gs("region"), g("planned"), gs("id"), g("active")),
        "employers": lambda: {"employers": employers(tenant)},
        "save_employer": lambda: save_employer(tenant, gs("name"), gs("kind") or "sub", gs("status"), gs("tax_id"), g("tax_id_ok"), gs("checked_on"),
                                               gs("checked_by"), gs("contact"), gs("id")),
        "workers": lambda: {"workers": workers(tenant, gs("q"), gs("employer"), gs("site"), bool(g("all")))},
        "worker": lambda: worker_detail(tenant, gs("id") or gs("name") or gs("worker")),
        "save_worker": lambda: save_worker(tenant, **a),
        "import_workers": lambda: import_workers(tenant, g("text") or "", gs("employer"), gs("site")),
        "papers": lambda: {"rows": papers(tenant, gs("whose"))},
        "save_paper": lambda: save_paper(tenant, gs("whose") or "worker", gs("kind"), gs("owner"), gs("name"), gs("number"), gs("issuer"), gs("valid_from"),
                                         gs("valid_to"), gs("file_id"), gs("note"), gs("id")),
        "radar": lambda: radar(tenant),
        "rates": lambda: {"rows": rates(tenant, gs("kind"))},
        "save_rate": lambda: save_rate(tenant, g("rate"), gs("kind") or "pay", gs("trade"), gs("skill"), gs("site"), gs("region"), gs("worker"),
                                       gs("basis") or "day", gs("unit"), gs("wef"), gs("source")),
        # muster
        "mark": lambda: MU.mark(tenant, g("marks") or [], gs("site"), gs("day"), gs("source") or "typed", gs("who"), gs("device"), gs("gang")),
        "correct": lambda: MU.correct(tenant, gs("id"), gs("who"), gs("reason"), g("status"), g("hours"), g("ot_hours"), g("count")),
        "resolve": lambda: MU.resolve_unknown(tenant, gs("id"), gs("worker"), gs("who"), bool(g("drop"))),
        "gate": lambda: MU.gate(tenant, g("count"), gs("site"), gs("day"), gs("source"), gs("who")),
        "close_day": lambda: MU.close_day(tenant, gs("site"), gs("day"), gs("who")),
        "import_device": lambda: MU.import_device(tenant, g("text") or "", gs("site"), gs("who"), gs("device")),
        "day": lambda: MU.day_view(tenant, gs("day"), gs("site")),
        "timesheet": lambda: MU.timesheet(tenant, gs("start"), gs("end"), gs("employer"), gs("site")),
        "headcount": lambda: MU.headcount(tenant, int(g("days") or 30)),
        # wages
        "draft_run": lambda: WG.draft_run(tenant, gs("start"), gs("end"), gs("employer"), gs("site"), gs("who"), g("allowances"), g("pieces")),
        "run": lambda: WG.run_view(tenant, gs("id")),
        "runs": lambda: {"rows": WG.runs(tenant, gs("status"))},
        "check_run": lambda: WG.check_run(tenant, gs("id"), gs("who")),
        "approve_run": lambda: WG.approve_run(tenant, gs("id"), gs("who"), gs("who2")),
        "cancel_run": lambda: WG.cancel_run(tenant, gs("id"), gs("who"), gs("reason")),
        "payment_file": lambda: WG.payment_file(tenant, gs("id"), gs("format"), g("accounts")),
        "mark_paid": lambda: WG.mark_paid(tenant, gs("id"), gs("who"), gs("ref"), gs("on"), g("failed")),
        "payslips": lambda: WG.payslips(tenant, gs("id")),
        "record_advance": lambda: WG.record_advance(tenant, gs("worker"), g("amount"), gs("who") or gs("given_by"), gs("day"), g("per_run"), gs("note")),
        "advances": lambda: {"rows": WG.advances(tenant)},
        "wages_due": lambda: WG.wages_due(tenant),
        # levies, withholding, filings
        "rules": lambda: {"rows": LV.rules(tenant, gs("kind"))},
        "use_pack": lambda: LV.use_pack(tenant, gs("pack_id"), gs("who"), gs("source"), g("rate_pct"), g("per_unit"), g("rates")),
        "save_rule": lambda: LV.save_rule(tenant, gs("kind"), gs("name"), gs("who"), gs("source"), gs("base") or "cost_of_work", g("rate_pct"), g("per_unit"),
                                          g("rates"), g("limits"), g("due"), gs("region")),
        "draft_levy": lambda: LV.draft_levy(tenant, g("base_amount") if g("base_amount") is not None else g("amount"), gs("ref"), gs("rule"), gs("base_source"),
                                            gs("day"), gs("site"), g("count"), gs("due")),
        "levies": lambda: {"rows": LV.levies(tenant)},
        "mark_levy_paid": lambda: LV.mark_levy_paid(tenant, gs("id"), gs("who"), gs("receipt"), gs("on")),
        "add_payment": lambda: LV.add_payment(tenant, gs("employer"), g("amount"), gs("day"), gs("ref"), g("materials"), gs("rule")),
        "payments": lambda: {"rows": LV.payments(tenant, gs("month"))},
        "mark_deposited": lambda: LV.mark_deposited(tenant, gs("month"), gs("who"), gs("receipt"), gs("on")),
        "calendar": lambda: LV.calendar(tenant, int(g("days") or 120)),
        "mark_filed": lambda: LV.mark_filed(tenant, gs("key"), gs("who"), gs("ref"), gs("on")),
        # subcontractors
        "add_evidence": lambda: SB.add_evidence(tenant, gs("employer"), gs("start"), gs("end"), gs("kind"), g("people"), g("names"), g("amount"), gs("file_id"),
                                                gs("ref"), gs("note")),
        "period": lambda: SB.period(tenant, gs("start"), gs("end"), gs("employer")),
        "draft_hold": lambda: SB.draft_hold(tenant, gs("employer"), gs("start"), gs("end")),
        "decide_hold": lambda: SB.decide(tenant, gs("id"), gs("decision"), gs("who"), gs("note")),
        # reports
        "registers": lambda: registers(tenant, gs("start"), gs("end"), gs("site")),
        "close_out": lambda: close_out(tenant, gs("site")),
    }.get(part)
    if f is None:
        raise LabourError(f"'{part}' is not a labour desk action.")
    return f()
