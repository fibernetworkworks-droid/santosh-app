"""v0.550.0 const_green tools (C15, Wave 3: #104 Energy Manager/Auditor Assistant, #110 Green Building
Consultant's Assistant, #111 ECBC Compliance Checker, #112 Energy Modelling Assistant, #113 Daylight
& Thermal-comfort Analyst, #114 Embodied Carbon / LCA Assistant, #115 Water / Rainwater & Waste
Planner, #116 Commissioning Authority's Assistant, #117 T&C Records Keeper, #118 M&V Analyst).
Records + arithmetic; every certification refused (audit / rating / Cx sign-off / energy audit -
tier C refusals ride the gate); EnergyPlus not run here; EPD factors need their source."""
from __future__ import annotations

import asyncio
from typing import Any

from .tools import Ctx, ToolError

GREEN_TOOLS = [
    {"name": "const_green", "description": (
        "Green & performance desk - energy, ECBC, daylight, carbon, water, credits, commissioning, T&C, "
        "M&V. Every certification is REFUSED (audit/rating/sign-off is a person's). action=meter_add: site, meter, "
        "kwh, day, note. action=tariff_add: name, rows [{from_kwh, to_kwh, rate, fixed_rs}], source (YOUR "
        "bill). action=bill: name, kwh_month -> slab-by-slab maths. action=benchmark: site, builtup_m2, "
        "benchmark_kwh_m2_mo, benchmark_source -> EPI kWh/m2/month. action=rule_add: family ecbc|daylight|"
        "benchmark|other, rule_id, text, value, unit, direction, clause, source - a rule without a clause is not "
        "kept. action=check: project, rule_id, declared -> within/breach (the ECBC assessor decides). "
        "action=daylight: project, room, glazing_m2, floor_m2, rule_id (optional) -> WFR % (explained, not "
        "certified). action=model_inputs: project, rows [{param, value, unit, source}] -> the modeller's INPUT "
        "register (EnergyPlus is not run here). action=carbon_add: project, material, qty, unit, "
        "factor_kgco2e, factor_source (EPD/LCA named) -> kgCO2e. action=carbon_hotspots: project -> ranked "
        "list (assessor decides). action=water_demand: project, name, occupants -> KLD (CPHEEO row). "
        "action=rwh: project, name, roof_m2, runoff_coeff, rainfall_mm, rain_source (IMD station) -> m3/yr. "
        "action=credit_add: project, rating IGBC|GRIHA|LEED, credit, points_available, points_claimed, "
        "evidence_ref, status planned|claimed|denied. action=credits_score: project -> claimed vs available "
        "(sum of YOUR rows; the rating is the assessor's). action=cx_add: project, system, test, steps [..], season "
        "first|seasonal -> Cx script. action=cx_issue: cx (id), severity minor|major|critical, note. "
        "action=cx_status: cx (id), status planned|done|failed. action=tc_add: project, system, cert_no, "
        "agency, tested_on, as_installed, design, tolerance_pct, unit -> ok/exceeds (acceptance is the T&C "
        "engineer's). action=mv_add: project, option A|B|C|D, baseline rows [{driver, kwh}], report rows "
        "-> M&V job. action=mv_savings: mv (id) -> baseline model (a, b, r2 printed) + savings (IPMVP "
        "routine, YOUR option). action=day: desk summary."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["meter_add", "tariff_add", "bill", "benchmark", "rule_add",
                                               "check", "daylight", "model_inputs", "carbon_add",
                                               "carbon_hotspots", "water_demand", "rwh", "credit_add",
                                               "credits_score", "cx_add", "cx_issue", "cx_status", "tc_add",
                                               "mv_add", "mv_savings", "day"]},
         "site": {"type": "string"}, "meter": {"type": "string"}, "kwh": {"type": "number"},
         "day": {"type": "string"}, "note": {"type": "string"}, "name": {"type": "string"},
         "rows": {"type": "array", "items": {"type": "object"}}, "source": {"type": "string"},
         "kwh_month": {"type": "number"}, "builtup_m2": {"type": "number"},
         "benchmark_kwh_m2_mo": {"type": "number"}, "benchmark_source": {"type": "string"},
         "family": {"type": "string"}, "rule_id": {"type": "string"}, "text": {"type": "string"},
         "value": {"type": "number"}, "unit": {"type": "string"}, "direction": {"type": "string"},
         "clause": {"type": "string"}, "checked_on": {"type": "string"}, "project": {"type": "string"},
         "declared": {"type": "number"}, "room": {"type": "string"}, "glazing_m2": {"type": "number"},
         "floor_m2": {"type": "number"}, "material": {"type": "string"}, "qty": {"type": "number"},
         "factor_kgco2e": {"type": "number"}, "factor_source": {"type": "string"},
         "occupants": {"type": "number"}, "roof_m2": {"type": "number"}, "runoff_coeff": {"type": "number"},
         "rainfall_mm": {"type": "number"}, "rain_source": {"type": "string"}, "rating": {"type": "string"},
         "credit": {"type": "string"}, "points_available": {"type": "number"},
         "points_claimed": {"type": "number"}, "evidence_ref": {"type": "string"}, "status": {"type": "string"},
         "system": {"type": "string"}, "test": {"type": "string"}, "steps": {"type": "array", "items": {"type": "string"}},
         "season": {"type": "string"}, "cx": {"type": "string"}, "severity": {"type": "string"},
         "cert_no": {"type": "string"}, "agency": {"type": "string"}, "tested_on": {"type": "string"},
         "as_installed": {"type": "number"}, "design": {"type": "number"}, "tolerance_pct": {"type": "number"},
         "option": {"type": "string"}, "baseline": {"type": "array", "items": {"type": "object"}},
         "report": {"type": "array", "items": {"type": "object"}}, "mv": {"type": "string"}},
         "required": ["action"]}},
    {"name": "const_green_dekho", "description": (
        "Read the performance desk (nothing changes). what=day | meters (site optional) | tariffs | rules "
        "(family optional) | checks (project optional) | carbon (project) | credits (project) | cx "
        "(project optional) | tc (project optional) | mv (project optional)."),
     "input_schema": {"type": "object", "properties": {
         "what": {"type": "string", "enum": ["day", "meters", "tariffs", "rules", "checks", "carbon",
                                             "credits", "cx", "tc", "mv"]},
         "site": {"type": "string"}, "family": {"type": "string"}, "project": {"type": "string"}},
         "required": ["what"]}},
]
GREEN_LABELS = {"const_green": "Performance desk par kaam kar raha hoon",
                "const_green_dekho": "Performance desk dekh raha hoon"}


def _s(v: Any) -> str:
    return "" if v is None else str(v)


def _act(ctx: Ctx, action: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..construction import green as G
    from ..construction.common import guard
    guard(f"{action} green")
    t = ctx.tenant_id
    try:
        if action == "meter_add":
            return G.meter_add(t, _s(a.get("site")), _s(a.get("meter")), a.get("kwh"), _s(a.get("day")),
                               _s(a.get("note")))
        if action == "tariff_add":
            return G.tariff_add(t, _s(a.get("name")), a.get("rows") or [], _s(a.get("source")))
        if action == "bill":
            return G.bill(t, _s(a.get("name")), a.get("kwh_month"))
        if action == "benchmark":
            return G.benchmark(t, _s(a.get("site")), a.get("builtup_m2"), a.get("benchmark_kwh_m2_mo") or 0.0,
                               _s(a.get("benchmark_source")))
        if action == "rule_add":
            return G.rule_add(t, _s(a.get("family")), _s(a.get("rule_id")), _s(a.get("text")),
                              a.get("value"), _s(a.get("unit")), _s(a.get("direction")) or "max",
                              _s(a.get("clause")), _s(a.get("source")), _s(a.get("checked_on")))
        if action == "check":
            return G.check(t, _s(a.get("project")), _s(a.get("rule_id")), a.get("declared"), _s(a.get("note")))
        if action == "daylight":
            return G.daylight(t, _s(a.get("project")), _s(a.get("room")), a.get("glazing_m2"), a.get("floor_m2"),
                              _s(a.get("rule_id")))
        if action == "model_inputs":
            return G.model_inputs(t, _s(a.get("project")), a.get("rows") or [])
        if action == "carbon_add":
            return G.carbon_add(t, _s(a.get("project")), _s(a.get("material")), a.get("qty"),
                                _s(a.get("unit")), a.get("factor_kgco2e"), _s(a.get("factor_source")))
        if action == "carbon_hotspots":
            return G.carbon_hotspots(t, _s(a.get("project")))
        if action == "water_demand":
            return G.water_demand(t, _s(a.get("project")), _s(a.get("name")), a.get("occupants"))
        if action == "rwh":
            return G.rwh(t, _s(a.get("project")), _s(a.get("name")), a.get("roof_m2"), a.get("runoff_coeff"),
                         a.get("rainfall_mm"), _s(a.get("rain_source")))
        if action == "credit_add":
            return G.credit_add(t, _s(a.get("project")), _s(a.get("rating")), _s(a.get("credit")),
                                a.get("points_available"), a.get("points_claimed"), _s(a.get("evidence_ref")),
                                _s(a.get("status")) or "claimed")
        if action == "credits_score":
            return G.credits_score(t, _s(a.get("project")))
        if action == "cx_add":
            return G.cx_add(t, _s(a.get("project")), _s(a.get("system")), _s(a.get("test")),
                            a.get("steps") or [], _s(a.get("season")) or "first")
        if action == "cx_issue":
            return G.cx_issue(t, _s(a.get("cx")), _s(a.get("severity")) or "minor", _s(a.get("note")))
        if action == "cx_status":
            return G.cx_status(t, _s(a.get("cx")), _s(a.get("status")))
        if action == "tc_add":
            return G.tc_add(t, _s(a.get("project")), _s(a.get("system")), _s(a.get("cert_no")),
                            _s(a.get("agency")), _s(a.get("tested_on")), a.get("as_installed"), a.get("design"),
                            a.get("tolerance_pct"), _s(a.get("unit")))
        if action == "mv_add":
            return G.mv_add(t, _s(a.get("project")), _s(a.get("option")), a.get("baseline") or [],
                            a.get("report") or [], _s(a.get("note")))
        if action == "mv_savings":
            return G.mv_savings(t, _s(a.get("mv")))
        if action == "day":
            return G.day(t)
    except (G.CstError, ValueError) as ex:
        raise ToolError(str(ex)) from None
    raise ToolError("Unknown action")


def _read(ctx: Ctx, what: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..construction import green as G
    from ..construction.common import guard
    from ..db import session
    from sqlalchemy import select
    from ..construction.models import (CgrCarbon, CgrCheck, CgrCredit, CgrCx, CgrCxIssue, CgrEcbcRule,
                                       CgrMeter, CgrMv, CgrTariff, CgrTc)
    guard(f"read green {what}")
    t = ctx.tenant_id
    try:
        if what == "day":
            return G.day(t)
        if what == "meters":
            q = select(CgrMeter).where(CgrMeter.tenant_id == t)
            if _s(a.get("site")):
                q = q.where(CgrMeter.site == _s(a.get("site")))
            with session() as s:
                rows = s.scalars(q).all()
            return {"meters": [{"id": r.id, "site": r.site, "meter": r.meter, "day": r.day, "kwh": r.kwh}
                               for r in rows]}
        if what == "tariffs":
            with session() as s:
                rows = s.scalars(select(CgrTariff).where(CgrTariff.tenant_id == t)).all()
            return {"tariffs": [{"id": r.id, "name": r.name, "slabs": len(G._j(r.rows, [])),
                                 "source": r.source[:60]} for r in rows]}
        if what == "rules":
            q = select(CgrEcbcRule).where(CgrEcbcRule.tenant_id == t)
            if _s(a.get("family")):
                q = q.where(CgrEcbcRule.family == _s(a.get("family")))
            with session() as s:
                rows = s.scalars(q).all()
            return {"rules": [{"id": r.id, "family": r.family, "rule_id": r.rule_id, "text": r.text[:80],
                               "value": r.value, "direction": r.direction, "unit": r.unit, "clause": r.clause,
                               "source": r.source[:60]} for r in rows]}
        if what == "checks":
            q = select(CgrCheck).where(CgrCheck.tenant_id == t)
            if _s(a.get("project")):
                q = q.where(CgrCheck.project == _s(a.get("project")))
            with session() as s:
                rows = s.scalars(q).all()
            return {"checks": [{"id": r.id, "project": r.project, "rule_id": r.rule_id, "declared": r.declared,
                                "limit": r.limit_value, "verdict": r.verdict, "checked_on": r.checked_on}
                               for r in rows]}
        if what == "carbon":
            with session() as s:
                rows = s.scalars(select(CgrCarbon).where(CgrCarbon.tenant_id == t,
                                                         CgrCarbon.project == _s(a.get("project")))).all()
            return {"carbon": [{"id": r.id, "material": r.material, "qty": r.qty, "unit": r.unit,
                                "factor": r.factor_kgco2e, "kgco2e": r.kgco2e, "source": r.factor_source[:60]}
                               for r in rows]}
        if what == "credits":
            with session() as s:
                rows = s.scalars(select(CgrCredit).where(CgrCredit.tenant_id == t,
                                                         CgrCredit.project == _s(a.get("project")))).all()
            return {"credits": [{"id": r.id, "rating": r.rating, "credit": r.credit,
                                 "claimed": r.points_claimed, "available": r.points_available,
                                 "status": r.status, "evidence": r.evidence_ref[:50]} for r in rows]}
        if what == "cx":
            q = select(CgrCx).where(CgrCx.tenant_id == t)
            if _s(a.get("project")):
                q = q.where(CgrCx.project == _s(a.get("project")))
            with session() as s:
                rows = s.scalars(q).all()
                iss = s.scalars(select(CgrCxIssue).where(CgrCxIssue.tenant_id == t)).all()
            return {"cx": [{"id": r.id, "project": r.project, "system": r.system, "test": r.test[:60],
                            "season": r.season, "status": r.status,
                            "issues": sum(1 for i in iss if i.cx_id == r.id and i.status == "open")}
                           for r in rows]}
        if what == "tc":
            q = select(CgrTc).where(CgrTc.tenant_id == t)
            if _s(a.get("project")):
                q = q.where(CgrTc.project == _s(a.get("project")))
            with session() as s:
                rows = s.scalars(q).all()
            return {"tc": [{"id": r.id, "system": r.system, "cert_no": r.cert_no, "as_installed": r.as_installed,
                            "design": r.design, "dev_pct": r.dev_pct, "tolerance_pct": r.tolerance_pct,
                            "verdict": r.verdict} for r in rows]}
        if what == "mv":
            with session() as s:
                rows = s.scalars(select(CgrMv).where(CgrMv.tenant_id == t,
                                                     CgrMv.project == _s(a.get("project")))).all()
            return {"mv": [{"id": r.id, "option": r.option, "baseline_rows": len(G._j(r.baseline, [])),
                            "report_rows": len(G._j(r.report, [])), "result": G._j(r.result, {})}
                           for r in rows]}
    except (G.CstError, ValueError) as ex:
        raise ToolError(str(ex)) from None
    raise ToolError("Unknown what")


async def const_green(ctx: Ctx, action, **a: Any):
    return await asyncio.to_thread(_act, ctx, str(action), a)


async def const_green_dekho(ctx: Ctx, what, **a: Any):
    return await asyncio.to_thread(_read, ctx, str(what), a)


GREEN_HANDLERS = {"const_green": const_green, "const_green_dekho": const_green_dekho}
