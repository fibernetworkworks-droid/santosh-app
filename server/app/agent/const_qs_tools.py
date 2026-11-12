"""v0.531.0 const_qs tools (C8: #37 take-off + #38 rate analyst + #39 BOQ/abstract + #41 cost
controller + #49 retention/PV). Every quantity carries its IS 1200 trail; a recompute is runnable
on demand (the trail law). NEVER a certificate of measurement - certification is the billing
engineer's act (tier C, gates.py)."""
from __future__ import annotations

import asyncio
from typing import Any

from .tools import Ctx, ToolError

QS_TOOLS = [
    {"name": "const_qs", "description": (
        "QS desk: take-off with the IS 1200 formula trail, rate build-up, BOQ + abstract, cost control, retention / "
        "price-variation. action=takeoff: project, item, kind earthwork|concrete|brickwork|plaster|formwork|steel, "
        "params {length, breadth/height, depth/thickness, openings_m2 | length_m, dia_mm, nos}, dwg_ref -> qty + trail. "
        "action=bbs: bars [{shape, dia, length, nos}] -> steel weight DRAFT. action=recompute: takeoff (id) -> bit-for-bit "
        "check. action=rate: item, unit, components [{head, qty, unit, rate, source}], overhead_pct, profit_pct, source "
        "(SOR/quote) -> built-up rate. action=boq: project, item, unit, qty, rate, head. action=abstract: project. "
        "action=budget: project, head, budget, committed, actual (cost controller). action=retention: amount, pct "
        "(% of the contract). action=pv: amount, workable_pct, base_index, current_index. A working paper is never a certificate. "
        "Wave 4 #40: action=cost_plan: project, rows [head, planned, estimate] -> variance; action=ve_option: "
        "project, rows [option, saving(FED), risk_note]. #89: action=gst_row: project, ref (bill/RA), rows "
        "[taxable, rate_pct, rcm], source (or india pack row) -> tax arithmetic; action=gst_sum: ref, itc, "
        "itc_source -> net. Only the CA files the return (tier C)."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["takeoff", "bbs", "recompute", "rate", "boq", "abstract", "budget",
                                               "retention", "pv", "cost_plan", "ve_option",
                                               "gst_row", "gst_sum"]},
         "project": {"type": "string"}, "item": {"type": "string"}, "kind": {"type": "string"},
         "params": {"type": "object"}, "bars": {"type": "array", "items": {"type": "object"}},
         "takeoff": {"type": "string"}, "unit": {"type": "string"},
         "components": {"type": "array", "items": {"type": "object"}}, "overhead_pct": {"type": "number"},
         "profit_pct": {"type": "number"}, "source": {"type": "string"}, "qty": {"type": "number"},
         "rate": {"type": "number"}, "head": {"type": "string"}, "budget": {"type": "number"},
         "committed": {"type": "number"}, "actual": {"type": "number"}, "amount": {"type": "number"},
         "pct": {"type": "number"}, "workable_pct": {"type": "number"}, "base_index": {"type": "number"},
         "current_index": {"type": "number"}, "dwg_ref": {"type": "string"}, "rows": {"type": "array", "items": {}},
         "ref": {"type": "string"}, "itc": {"type": "number"}, "itc_source": {"type": "string"}},
         "required": ["action"]}},
    {"name": "const_qs_dekho", "description": (
        "Read QS desk (nothing changes). what=day | takeoffs (project optional) | rates | boq (project) | "
        "abstract (project) | budget (project)."),
     "input_schema": {"type": "object", "properties": {
         "what": {"type": "string", "enum": ["day", "takeoffs", "rates", "boq", "abstract", "budget"]},
         "project": {"type": "string"}}, "required": ["what"]}},
]
QS_LABELS = {"const_qs": "Calculating measurements and rates", "const_qs_dekho": "Viewing the QS desk"}


def _s(v: Any) -> str:
    return "" if v is None else str(v)


def _act(ctx: Ctx, action: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..construction import qs as Q
    from ..construction.common import guard
    guard(f"{action} qs")     # tier-C refusal rides every construction action
    t, conv = ctx.tenant_id, ctx.conversation_id
    try:
        if action == "takeoff":
            return Q.takeoff(t, _s(a.get("project")), _s(a.get("item")), _s(a.get("kind")), a.get("params") or {},
                             _s(a.get("dwg_ref")))
        if action == "bbs":
            from ..construction import is1200 as M
            out = M.bbs(a.get("bars") or [])
            return out
        if action == "recompute":
            return Q.recompute(t, _s(a.get("takeoff")))
        if action == "rate":
            return Q.rate_buildup(t, _s(a.get("item")), _s(a.get("unit")), a.get("components") or [],
                                  a.get("overhead_pct"), a.get("profit_pct"), _s(a.get("source")))
        if action == "boq":
            return Q.boq_add(t, _s(a.get("project")), _s(a.get("item")), _s(a.get("unit")), a.get("qty"),
                             a.get("rate"), _s(a.get("head")), _s(a.get("takeoff")), _s(a.get("rate_id")))
        if action == "abstract":
            return Q.abstract(t, _s(a.get("project")))
        if action == "budget":
            return Q.budget(t, _s(a.get("project")), _s(a.get("head")), a.get("budget"), a.get("committed"),
                            a.get("actual"), _s(a.get("note")))
        if action == "retention":
            return Q.retention(a.get("amount"), a.get("pct"))
        if action == "pv":
            return Q.price_variation(a.get("amount"), a.get("workable_pct"), a.get("base_index"),
                                     a.get("current_index"))

        if action == "cost_plan":
            return Q.cost_plan(t, _s(a.get("project")), a.get("rows") or [], _s(a.get("note")))
        if action == "ve_option":
            return Q.ve_option(t, _s(a.get("project")), a.get("rows") or [])
        if action == "gst_row":
            return Q.gst_row(t, _s(a.get("project")), _s(a.get("ref")), a.get("rows") or [],
                             _s(a.get("source")))
        if action == "gst_sum":
            return Q.gst_sum(t, _s(a.get("project")), _s(a.get("ref")), a.get("itc") or 0.0,
                             _s(a.get("itc_source")))
    except (Q.CstError, ValueError) as ex:
        raise ToolError(str(ex))
    raise ToolError("Unknown action")


def _read(ctx: Ctx, what: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..construction import qs as Q
    from ..construction.common import guard
    from ..db import session
    from sqlalchemy import select
    from ..construction.models import CqsBoq, CqsBudget, CqsRate, CqsTakeoff
    t = ctx.tenant_id
    guard(f"read qs {what}")
    try:
        if what == "day":
            return Q.day(t, _s(a.get("project")))
        if what == "takeoffs":
            with session() as s:
                rows = s.scalars(select(CqsTakeoff).where(CqsTakeoff.tenant_id == t)).all()
            p = _s(a.get("project"))
            if p:
                rows = [r for r in rows if r.project == p]
            return {"takeoffs": [{"id": r.id, "project": r.project, "item": r.item, "kind": r.kind,
                                  "qty": r.qty, "unit": r.unit, "formula": r.formula, "is_ref": r.is_ref}
                                 for r in rows]}
        if what == "rates":
            with session() as s:
                rows = s.scalars(select(CqsRate).where(CqsRate.tenant_id == t)).all()
            return {"rates": [{"id": r.id, "item": r.item, "unit": r.unit, "rate": r.rate, "source": r.source}
                              for r in rows]}
        if what == "boq":
            with session() as s:
                rows = s.scalars(select(CqsBoq).where(CqsBoq.tenant_id == t,
                                                      CqsBoq.project == _s(a.get("project")))).all()
            return {"boq": [{"id": r.id, "item": r.item, "unit": r.unit, "qty": r.qty, "rate": r.rate,
                             "amount": r.amount, "head": r.head} for r in rows]}
        if what == "abstract":
            return Q.abstract(t, _s(a.get("project")))
        if what == "budget":
            with session() as s:
                rows = s.scalars(select(CqsBudget).where(CqsBudget.tenant_id == t,
                                                         CqsBudget.project == _s(a.get("project")))).all()
            return {"budget": [{"id": r.id, "head": r.head, "budget": r.budget, "committed": r.committed,
                                "actual": r.actual} for r in rows]}
    except (Q.CstError, ValueError) as ex:
        raise ToolError(str(ex))
    raise ToolError("Unknown what")


async def const_qs(ctx: Ctx, action, **a: Any):
    return await asyncio.to_thread(_act, ctx, str(action), a)


async def const_qs_dekho(ctx: Ctx, what, **a: Any):
    return await asyncio.to_thread(_read, ctx, str(what), a)


QS_HANDLERS = {"const_qs": const_qs, "const_qs_dekho": const_qs_dekho}
