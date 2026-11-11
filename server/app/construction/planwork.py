"""Wave 4 (v0.586.0) const_plan: the planning & project-controls desk (register #42, #43, #63, #65,
#66, #68, #69, #79, #80).

The delay desk's law holds here too: dates, progress and criticality are WORDS before they are
numbers - baseline dates, % complete and P/I marks are FED/HER, variance and scores are arithmetic,
and the critical path / extension of time is NEVER computed (gates.py: "declare the critical path").
Cash-flow and EVM ride HER baseline and HER bills: PV from the plan, EV on HER % complete."""
from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy import select

from ..db import session
from . import models as M
from .common import CstError, _date, _dump, _j, _num, publish, today


def _w(x: Any) -> dict:
    return x if isinstance(x, dict) else {}


# ---------------------------------------------------------------- schedule (#63)
def activity_add(tenant: str, project: str, rows: list, note: str = "", conv: str = "") -> dict:
    """rows [code, name, base_start, base_finish] - the baseline AS FED (HER plan)."""
    if not rows:
        raise CstError("Activity rows are needed [code, name, base_start, base_finish].")
    made = 0
    with session() as s:
        for r in rows:
            if not isinstance(r, (list, tuple)) or len(r) < 4:
                continue
            if not _date(r[2]) or not _date(r[3]):
                raise CstError(f"Activity '{r[0]}': baseline dates are needed as yyyy-mm-dd.")
            s.add(M.CplanActivity(tenant_id=tenant, project=project, code=str(r[0])[:40],
                                  name=str(r[1])[:160], base_start=str(r[2])[:10],
                                  base_finish=str(r[3])[:10]))
            made += 1
    publish(tenant, "const_plan", {"kind": "activities", "project": project, "rows": made}, conv)
    return {"ok": True, "rows": made, "said": f"{made} activities written to the baseline ({project}) - the dates are from your plan."}


def activity_update(tenant: str, project: str, code: str, act_start: str = "", act_finish: str = "",
                    pct: float | None = None) -> dict:
    """Actual dates and % complete - HER word, recorded as said."""
    with session() as s:
        a = s.scalars(select(M.CplanActivity).where(M.CplanActivity.tenant_id == tenant,
                                                    M.CplanActivity.project == project,
                                                    M.CplanActivity.code == code)).first()
        if not a:
            raise CstError(f"Activity '{code}' not found ({project}).")
        if act_start:
            if not _date(act_start):
                raise CstError("act_start yyyy-mm-dd do.")
            a.act_start = act_start
        if act_finish:
            if not _date(act_finish):
                raise CstError("act_finish yyyy-mm-dd do.")
            a.act_finish = act_finish
        if pct is not None:
            a.pct = max(0.0, min(100.0, float(pct)))
    return {"ok": True, "code": code, "act_start": a.act_start, "act_finish": a.act_finish,
            "pct": a.pct, "said": f"{code} update: {a.pct:.0f}% (your word, recorded)."}


def variance(tenant: str, project: str, name: str = "") -> dict:
    """#63: planned-vs-actual date arithmetic per activity. Criticality NOT computed."""
    with session() as s:
        acts = s.scalars(select(M.CplanActivity).where(M.CplanActivity.tenant_id == tenant,
                                                       M.CplanActivity.project == project)).all()
    if not acts:
        raise CstError("No activities found - run action=activity_add first.")
    t0 = today(tenant)
    rows, slip_total = [], 0
    for a in acts:
        bf, af = _date(a.base_finish), _date(a.act_finish)
        slip = (af - bf).days if (bf and af) else None
        state = ("as planned" if slip is None or slip == 0 else
                 ("LATE" if slip > 0 else "early"))
        if slip and slip > 0:
            slip_total += slip
        running = bool(bf and bf < t0 and not a.act_start)
        rows.append({"code": a.code, "name": a.name, "base_finish": a.base_finish,
                     "act_finish": a.act_finish or "", "slip_days": slip, "state": state,
                     "pct": a.pct, "not_started_past_base": running})
    res = {"project": project, "activities": rows,
           "late_count": sum(1 for r in rows if r["state"] == "LATE"),
           "total_slip_days_late_activities": slip_total,
           "said": ("Date variance arithmetic - which activity is critical is the planner's mark "
                    "(Hoola does NOT compute criticality).")}
    with session() as s:
        s.add(M.CplanCalc(tenant_id=tenant, project=project, kind="variance", name=name or "variance",
                          result=_dump(res)))
    return {"ok": True, "kind": "variance", **res}


# ---------------------------------------------------------------- resources & productivity (#65)
def resource_add(tenant: str, project: str, rows: list, note: str = "") -> dict:
    """rows [activity_code, trade, crew, output_planned_per_day] - HER resource plan."""
    made = 0
    with session() as s:
        for r in rows:
            if not isinstance(r, (list, tuple)) or len(r) < 3:
                continue
            s.add(M.CplanItem(tenant_id=tenant, project=project, kind="resource",
                              name=str(r[1])[:160],
                              data=_dump({"activity": str(r[0])[:40], "trade": str(r[1])[:80],
                                          "crew": _num(r[2]) if len(r) > 2 else 0.0,
                                          "output_planned": _num(r[3]) if len(r) > 3 else 0.0}),
                              note=note))
            made += 1
    return {"ok": True, "rows": made, "said": f"{made} resource row(s) likhi."}


def productivity(tenant: str, project: str, activity: str, output_actual: float) -> dict:
    """#65: planned vs actual output for one activity - the planned number is HER row's."""
    with session() as s:
        row = s.scalars(select(M.CplanItem).where(M.CplanItem.tenant_id == tenant,
                                                  M.CplanItem.project == project,
                                                  M.CplanItem.kind == "resource",
                                                  M.CplanItem.name == activity)).first()
    if not row:
        raise CstError(f"Activity '{activity}' has no resource row - run action=resource_add first.")
    d = _j(row.data, {})
    planned = float(d.get("output_planned") or 0)
    ratio = round(output_actual / planned, 3) if planned else None
    return {"ok": True, "activity": activity, "planned_per_day": planned,
            "actual_per_day": output_actual, "achievement": ratio,
            "verdict": ("below plan" if ratio is not None and ratio < 1 else "at/above plan"),
            "said": "Achievement is arithmetic - the supervisor gives the reason for the productivity."}


# ---------------------------------------------------------------- risks (#66)
def risk_add(tenant: str, project: str, rows: list, note: str = "", conv: str = "") -> dict:
    """rows [risk, p(1-5 HER), i(1-5 HER), owner, due] - P and I are HER marks; score = P x I."""
    made = 0
    with session() as s:
        for r in rows:
            if not isinstance(r, (list, tuple)) or len(r) < 3:
                continue
            p, i = _num(r[1]), _num(r[2])
            if not (1 <= p <= 5) or not (1 <= i <= 5):
                raise CstError(f"Risk '{r[0]}': P and I are YOUR marks, 1-5 (you give them).")
            s.add(M.CplanItem(tenant_id=tenant, project=project, kind="risk", name=str(r[0])[:160],
                              data=_dump({"p": p, "i": i, "score": p * i,
                                          "owner": str(r[3])[:120] if len(r) > 3 else "",
                                          "due": str(r[4])[:10] if len(r) > 4 else ""}),
                              note=note))
            made += 1
    publish(tenant, "const_plan", {"kind": "risks", "project": project, "rows": made}, conv)
    return {"ok": True, "rows": made, "said": f"{made} risks written - score = P x I (your marks)."}


def risk_board(tenant: str, project: str) -> dict:
    with session() as s:
        rows = s.scalars(select(M.CplanItem).where(M.CplanItem.tenant_id == tenant,
                                                   M.CplanItem.project == project,
                                                   M.CplanItem.kind == "risk")).all()
    risks = sorted(({"risk": r.name, **_j(r.data, {})} for r in rows),
                   key=lambda x: -float(x.get("score") or 0))
    return {"ok": True, "risks": risks, "top": risks[0] if risks else None,
            "said": "Board sorted by P x I - the mitigation decision is the owner's."}


# ---------------------------------------------------------------- site instructions & PMC log (#69)
def si_add(tenant: str, project: str, rows: list, note: str = "") -> dict:
    """rows [no, date, from, to, subject] - the site-instruction register."""
    made = 0
    with session() as s:
        for r in rows:
            if not isinstance(r, (list, tuple)) or len(r) < 5:
                continue
            s.add(M.CplanItem(tenant_id=tenant, project=project, kind="si", name=str(r[0])[:40],
                              data=_dump({"date": str(r[1])[:10], "frm": str(r[2])[:120],
                                          "to": str(r[3])[:120], "subject": str(r[4])[:200]}),
                              note=note))
            made += 1
    return {"ok": True, "rows": made, "said": f"{made} site instruction(s) in the register."}


def pmc_log(tenant: str, project: str, date_s: str, what: str, note: str = "") -> dict:
    if not _date(date_s):
        raise CstError("Visit date yyyy-mm-dd do.")
    with session() as s:
        s.add(M.CplanItem(tenant_id=tenant, project=project, kind="pmclog", name=what[:160],
                          data=_dump({"date": date_s, "note": note})))
    return {"ok": True, "said": "PMC visit written to the log."}


# ---------------------------------------------------------------- cash-flow (#42) & EVM (#43)
def cashflow(tenant: str, project: str, pv_rows: list, ac_rows: list, name: str = "") -> dict:
    """#42: planned value per period (HER baseline) vs actual (HER bills) -> variance table."""
    if not pv_rows:
        raise CstError("pv_rows are needed [period, planned_value] - from your baseline.")
    pv = {str(r[0])[:20]: _num(r[1]) for r in pv_rows if isinstance(r, (list, tuple)) and r}
    ac = {str(r[0])[:20]: _num(r[1]) for r in ac_rows if isinstance(r, (list, tuple)) and r}
    per, tp, ta = [], 0.0, 0.0
    for k in dict.fromkeys(list(pv) + list(ac)):
        p, a = pv.get(k, 0.0), ac.get(k, 0.0)
        tp, ta = tp + p, ta + a
        per.append({"period": k, "planned": p, "actual": a, "var": round(a - p, 2)})
    res = {"periods": per, "total_planned": round(tp, 2), "total_actual": round(ta, 2),
           "total_var": round(ta - tp, 2),
           "said": "Both sides of the S-curve are from YOUR numbers (baseline + bills)."}
    with session() as s:
        s.add(M.CplanCalc(tenant_id=tenant, project=project, kind="cashflow", name=name or "cashflow",
                          result=_dump(res)))
    return {"ok": True, "kind": "cashflow", **res}


def evm(tenant: str, project: str, bac: float, rows: list, name: str = "") -> dict:
    """#43: [period, pv, ev, ac] - EV is HER % complete x HER BAC, fed as the EV number; SPI = EV/PV,
    CPI = EV/AC. No forecast beyond the arithmetic (the EAC is the PM's call)."""
    if bac <= 0:
        raise CstError("BAC (budget at completion) is needed - from your budget.")
    if not rows:
        raise CstError("rows are needed [period, pv, ev, ac].")
    per, cpv, cev, cac = [], 0.0, 0.0, 0.0
    for r in rows:
        if not isinstance(r, (list, tuple)) or len(r) < 4:
            continue
        pv, ev, ac = _num(r[1]), _num(r[2]), _num(r[3])
        cpv, cev, cac = cpv + pv, cev + ev, cac + ac
        per.append({"period": str(r[0])[:20], "pv": pv, "ev": ev, "ac": ac,
                    "spi": round(ev / pv, 3) if pv else None,
                    "cpi": round(ev / ac, 3) if ac else None})
    res = {"bac": bac, "periods": per,
           "cum": {"pv": round(cpv, 2), "ev": round(cev, 2), "ac": round(cac, 2),
                   "spi": round(cev / cpv, 3) if cpv else None,
                   "cpi": round(cev / cac, 3) if cac else None,
                   "cv": round(cev - cac, 2), "sv": round(cev - cpv, 2)},
           "pct_complete": round(cev / bac * 100, 1),
           "said": ("EV is your % complete x your BAC; SPI/CPI are arithmetic on them. The EAC "
                    "estimate is the PM's - not Hoola's.")}
    with session() as s:
        s.add(M.CplanCalc(tenant_id=tenant, project=project, kind="evm", name=name or "evm",
                          result=_dump(res)))
    return {"ok": True, "kind": "evm", **res}


# ---------------------------------------------------------------- dashboard (#68)
def dashboard(tenant: str, project: str) -> dict:
    """#68: the director's rollup - ONLY what the other rows already said, as fed."""
    with session() as s:
        acts = s.scalars(select(M.CplanActivity).where(M.CplanActivity.tenant_id == tenant,
                                                       M.CplanActivity.project == project)).all()
        risks = s.scalars(select(M.CplanItem).where(M.CplanItem.tenant_id == tenant,
                                                    M.CplanItem.project == project,
                                                    M.CplanItem.kind == "risk")).all()
        calcs = s.scalars(select(M.CplanCalc).where(M.CplanCalc.tenant_id == tenant,
                                                    M.CplanCalc.project == project)).all()
    t0 = today(tenant)
    late = [a.code for a in acts if _date(a.base_finish) and _date(a.base_finish) < t0 and a.pct < 100]
    top_risks = sorted(({"risk": r.name, **_j(r.data, {})} for r in risks),
                       key=lambda x: -float(x.get("score") or 0))[:3]
    evm_last = None
    for c in calcs:
        if c.kind == "evm":
            evm_last = _j(c.result, {}).get("cum")
    return {"ok": True, "kind": "dashboard", "project": project,
            "activities": len(acts), "not_complete_past_base_finish": late,
            "top_risks": top_risks, "evm_cum": evm_last,
            "said": ("The dashboard shows only what is written in the registers - no new number comes "
                     "from code.")}


# ---------------------------------------------------------------- specialist agencies (#79)
def agency_add(tenant: str, project: str, rows: list, note: str = "") -> dict:
    """rows [agency, scope, sample_or_mockup_status, start, finish]."""
    made = 0
    with session() as s:
        for r in rows:
            if not isinstance(r, (list, tuple)) or len(r) < 2:
                continue
            s.add(M.CplanItem(tenant_id=tenant, project=project, kind="agency", name=str(r[0])[:160],
                              data=_dump({"scope": str(r[1])[:200],
                                          "sample_status": str(r[2])[:80] if len(r) > 2 else "",
                                          "start": str(r[3])[:10] if len(r) > 3 else "",
                                          "finish": str(r[4])[:10] if len(r) > 4 else ""}),
                              note=note))
            made += 1
    return {"ok": True, "rows": made, "said": f"{made} specialist agency row(s) - work goes ahead only once their samples/mockups are approved."}


# ---------------------------------------------------------------- plant & bookings (#80)
def plant_add(tenant: str, project: str, rows: list, note: str = "") -> dict:
    """rows [plant, type, owned_or_hired]."""
    made = 0
    with session() as s:
        for r in rows:
            if not isinstance(r, (list, tuple)) or len(r) < 2:
                continue
            s.add(M.CplanItem(tenant_id=tenant, project=project, kind="plant", name=str(r[0])[:120],
                              data=_dump({"type": str(r[1])[:80],
                                          "owned_hired": str(r[2])[:12] if len(r) > 2 else ""}),
                              note=note))
            made += 1
    return {"ok": True, "rows": made, "said": f"{made} plant in the register."}


def plant_book(tenant: str, project: str, plant: str, frm: str, to: str, site: str) -> dict:
    """One booking - overlapping bookings on the SAME plant are named, not resolved."""
    if not _date(frm) or not _date(to):
        raise CstError("Booking dates yyyy-mm-dd do.")
    if _date(to) < _date(frm):
        raise CstError("The booking's end date cannot be before its start.")
    with session() as s:
        s.add(M.CplanItem(tenant_id=tenant, project=project, kind="booking", name=plant[:120],
                          data=_dump({"from": frm, "to": to, "site": site[:160]})))
        books = s.scalars(select(M.CplanItem).where(M.CplanItem.tenant_id == tenant,
                                                    M.CplanItem.project == project,
                                                    M.CplanItem.kind == "booking",
                                                    M.CplanItem.name == plant)).all()
    f1, t1 = _date(frm), _date(to)
    clash = []
    for b in books:
        d = _j(b.data, {})
        f2, t2 = _date(d.get("from")), _date(d.get("to"))
        if not (f2 and t2 and (f2, t2) != (f1, t1)):
            continue
        if f1 <= t2 and f2 <= t1:
            clash.append({"site": d.get("site"), "from": d.get("from"), "to": d.get("to")})
    return {"ok": True, "plant": plant, "from": frm, "to": to, "site": site,
            "double_booked_with": clash,
            "said": (f"CAUTION: this plant has {len(clash)} other booking(s) in the same window."
                     if clash else "Booking written - no clash.")}


def plant_util(tenant: str, project: str, plant: str, working_days: int) -> dict:
    """Utilisation = booked days / working days, arithmetic on HER bookings."""
    if working_days <= 0:
        raise CstError("working_days 0 se bada do.")
    with session() as s:
        books = s.scalars(select(M.CplanItem).where(M.CplanItem.tenant_id == tenant,
                                                    M.CplanItem.project == project,
                                                    M.CplanItem.kind == "booking",
                                                    M.CplanItem.name == plant)).all()
    days = 0
    for b in books:
        d = _j(b.data, {})
        f, t = _date(d.get("from")), _date(d.get("to"))
        if f and t:
            days += max(0, (t - f).days + 1)
    util = round(days / working_days * 100, 1)
    return {"ok": True, "plant": plant, "booked_days": days, "working_days": working_days,
            "utilisation_pct": util,
            "said": "Utilisation = booked / working days (on your bookings)."}
