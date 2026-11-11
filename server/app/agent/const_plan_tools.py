"""v0.586.0 const_plan tools (Wave 4: #42 cash-flow, #43 EVM, #63 scheduler, #65 resources, #66
risks, #68 dashboard, #69 PMC, #79 agencies, #80 plant). Baselines, % complete and P/I are FED/HER;
variance and scores are arithmetic; criticality is NEVER computed (tier C via gates)."""
from __future__ import annotations

import asyncio
from typing import Any

from .tools import Ctx, ToolError

PLAN_TOOLS = [
    {"name": "const_plan", "description": (
        "Planning & controls desk (#42/#43/#63/#65/#66/#68/#69/#79/#80). action=activity_add: project, "
        "rows [code, name, base_start, base_finish] (the baseline is YOURS). action=activity_update: project, "
        "code, act_start, act_finish, pct. action=variance: project -> planned vs actual dates "
        "(NOT criticality). action=resource_add: project, rows [activity, trade, crew, output_planned]. "
        "action=productivity: project, activity, output_actual. action=risk_add: project, rows [risk, "
        "p(1-5 YOURS), i(1-5 YOURS), owner, due] -> score = p x i. action=risk_board: project. "
        "action=si_add: project, rows [no, date, from, to, subject]. action=pmc_log: project, date, "
        "what, note. action=cashflow: project, pv_rows [period, planned], ac_rows [period, actual] -> "
        "S-curve variance. action=evm: project, bac, rows [period, pv, ev, ac] -> SPI/CPI (not EAC). "
        "action=dashboard: project -> only what the registers have already said. action=agency_add: rows [agency, "
        "scope, sample_status, start, finish]. action=plant_add: rows [plant, type, owned_hired]. "
        "action=plant_book: project, plant, from, to, site -> double-booking NAMED. action=plant_util: "
        "project, plant, working_days -> utilisation %."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["activity_add", "activity_update", "variance",
                                               "resource_add", "productivity", "risk_add",
                                               "risk_board", "si_add", "pmc_log", "cashflow", "evm",
                                               "dashboard", "agency_add", "plant_add", "plant_book",
                                               "plant_util"]},
         "project": {"type": "string"}, "rows": {"type": "array", "items": {}},
         "note": {"type": "string"}, "code": {"type": "string"}, "act_start": {"type": "string"},
         "act_finish": {"type": "string"}, "pct": {"type": "number"}, "activity": {"type": "string"},
         "output_actual": {"type": "number"}, "date": {"type": "string"}, "what": {"type": "string"},
         "pv_rows": {"type": "array", "items": {}}, "ac_rows": {"type": "array", "items": {}},
         "bac": {"type": "number"}, "plant": {"type": "string"}, "from": {"type": "string"},
         "to": {"type": "string"}, "site": {"type": "string"}, "working_days": {"type": "number"}},
         "required": ["action"]}},
    {"name": "const_plan_dekho", "description": (
        "Read the planning desk (nothing changes). what=activities (project) | items (project, kind "
        "risk|resource|productivity|si|pmclog|agency|plant|booking) | calcs (project, kind variance|"
        "cashflow|evm|dashboard optional)."),
     "input_schema": {"type": "object", "properties": {
         "what": {"type": "string", "enum": ["activities", "items", "calcs"]},
         "project": {"type": "string"}, "kind": {"type": "string"}},
         "required": ["what"]}},
]
PLAN_LABELS = {"const_plan": "Working on the planning desk",
               "const_plan_dekho": "Viewing the planning desk"}


def _s(v: Any) -> str:
    return "" if v is None else str(v)


def _n(v: Any) -> float | None:
    return None if v is None else float(v)


def _act(ctx: Ctx, action: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..construction import planwork as P
    from ..construction.common import guard
    guard(f"{action} plan controls")
    t, conv = ctx.tenant_id, ctx.conversation_id
    try:
        if action == "activity_add":
            return P.activity_add(t, _s(a.get("project")), a.get("rows") or [], _s(a.get("note")), conv)
        if action == "activity_update":
            return P.activity_update(t, _s(a.get("project")), _s(a.get("code")), _s(a.get("act_start")),
                                     _s(a.get("act_finish")), _n(a.get("pct")))
        if action == "variance":
            return P.variance(t, _s(a.get("project")), _s(a.get("note")))
        if action == "resource_add":
            return P.resource_add(t, _s(a.get("project")), a.get("rows") or [], _s(a.get("note")))
        if action == "productivity":
            return P.productivity(t, _s(a.get("project")), _s(a.get("activity")),
                                  float(a.get("output_actual") or 0))
        if action == "risk_add":
            return P.risk_add(t, _s(a.get("project")), a.get("rows") or [], _s(a.get("note")), conv)
        if action == "risk_board":
            return P.risk_board(t, _s(a.get("project")))
        if action == "si_add":
            return P.si_add(t, _s(a.get("project")), a.get("rows") or [], _s(a.get("note")))
        if action == "pmc_log":
            return P.pmc_log(t, _s(a.get("project")), _s(a.get("date")), _s(a.get("what")),
                             _s(a.get("note")))
        if action == "cashflow":
            return P.cashflow(t, _s(a.get("project")), a.get("pv_rows") or [], a.get("ac_rows") or [],
                              _s(a.get("note")))
        if action == "evm":
            return P.evm(t, _s(a.get("project")), float(a.get("bac") or 0), a.get("rows") or [],
                         _s(a.get("note")))
        if action == "dashboard":
            return P.dashboard(t, _s(a.get("project")))
        if action == "agency_add":
            return P.agency_add(t, _s(a.get("project")), a.get("rows") or [], _s(a.get("note")))
        if action == "plant_add":
            return P.plant_add(t, _s(a.get("project")), a.get("rows") or [], _s(a.get("note")))
        if action == "plant_book":
            return P.plant_book(t, _s(a.get("project")), _s(a.get("plant")), _s(a.get("from")),
                                _s(a.get("to")), _s(a.get("site")))
        if action == "plant_util":
            return P.plant_util(t, _s(a.get("project")), _s(a.get("plant")),
                                int(float(a.get("working_days") or 0)))
    except (P.CstError, ValueError) as ex:
        raise ToolError(str(ex)) from None
    raise ToolError("unknown action")


def _read(ctx: Ctx, what: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..construction import planwork as P
    from ..construction import models as M
    from ..construction.common import guard, _j
    from ..db import session
    from sqlalchemy import select
    guard(f"read plan {what}")
    t, proj = ctx.tenant_id, _s(a.get("project"))
    try:
        if what == "activities":
            q = select(M.CplanActivity).where(M.CplanActivity.tenant_id == t)
            if proj:
                q = q.where(M.CplanActivity.project == proj)
            with session() as s:
                rows = s.scalars(q).all()
            return {"activities": [{"id": r.id, "project": r.project, "code": r.code, "name": r.name,
                                    "base": [r.base_start, r.base_finish],
                                    "actual": [r.act_start, r.act_finish], "pct": r.pct} for r in rows]}
        if what == "items":
            q = select(M.CplanItem).where(M.CplanItem.tenant_id == t)
            if proj:
                q = q.where(M.CplanItem.project == proj)
            if _s(a.get("kind")):
                q = q.where(M.CplanItem.kind == _s(a.get("kind")))
            with session() as s:
                rows = s.scalars(q).all()
            return {"items": [{"id": r.id, "project": r.project, "kind": r.kind, "name": r.name,
                               "data": _j(r.data, {})} for r in rows]}
        if what == "calcs":
            q = select(M.CplanCalc).where(M.CplanCalc.tenant_id == t)
            if proj:
                q = q.where(M.CplanCalc.project == proj)
            if _s(a.get("kind")):
                q = q.where(M.CplanCalc.kind == _s(a.get("kind")))
            with session() as s:
                rows = s.scalars(q).all()
            return {"calcs": [{"id": r.id, "project": r.project, "kind": r.kind, "name": r.name,
                               "result": _j(r.result, {})} for r in rows]}
    except (P.CstError, ValueError) as ex:
        raise ToolError(str(ex)) from None
    raise ToolError("unknown what")


async def const_plan(ctx: Ctx, action, **a: Any):
    return await asyncio.to_thread(_act, ctx, str(action), a)


async def const_plan_dekho(ctx: Ctx, what, **a: Any):
    return await asyncio.to_thread(_read, ctx, str(what), a)


PLAN_HANDLERS = {"const_plan": const_plan, "const_plan_dekho": const_plan_dekho}
