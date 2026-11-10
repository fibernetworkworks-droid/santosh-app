"""v0.586.0 const_land tools (Wave 4: #1 Land Scout, #2 Title Due-Diligence, #3 Land Records,
#4 DM Assistant, #5 Project Finance, #6 JV Tracker). The record says what was FED and who said it;
the title opinion is the title advocate's, the funding structure the CFO's (tier C via gates)."""
from __future__ import annotations

import asyncio
from typing import Any

from .tools import Ctx, ToolError

LAND_TOOLS = [
    {"name": "const_land", "description": (
        "Land & feasibility desk (#1-#6) - parcel register, title checklist, land-record "
        "reconciliation, FSI worksheet, cost/funding totals, JV entitlement. action=parcel_add: "
        "project, survey_no, village, area, area_unit, area_source (7/12/mutation/agreement - "
        "no area without a source). action=item_add: project, kind title|record|criterion|worksheet|"
        "finance|funding|jv, rows, by (a name is required with title marks), source (worksheet/"
        "finance/jv ka source zaroori). title rows [doc, status]; record rows [doc_no, area, date]; "
        "criterion rows [criterion, weight, score] (weights/scores are YOURS); worksheet rows [use, "
        "builtup]; finance rows [head, amount]; funding rows [source, amount]; jv rows [party, "
        "share_pct] (deed se). action=recon: project, parcel -> records total vs claimed. "
        "action=feasibility: project, plot_area, fsi, fsi_source -> permissible vs programme. "
        "action=jv_calc: project, developable_area -> party-wise share (on the deed's %). "
        "action=finance_sum: project, interest_rate_pct, rate_source, years -> totals + equity:debt "
        "+ simple interest. Title opinion, funding structure, JV signing - ALL are for a human "
        "(tier C)."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["parcel_add", "item_add", "recon", "feasibility",
                                               "jv_calc", "finance_sum"]},
         "project": {"type": "string"}, "survey_no": {"type": "string"}, "village": {"type": "string"},
         "area": {"type": "number"}, "area_unit": {"type": "string"}, "area_source": {"type": "string"},
         "kind": {"type": "string"}, "rows": {"type": "array", "items": {}}, "by": {"type": "string"},
         "source": {"type": "string"}, "note": {"type": "string"}, "parcel": {"type": "string"},
         "plot_area": {"type": "number"}, "fsi": {"type": "number"}, "fsi_source": {"type": "string"},
         "developable_area": {"type": "number"}, "interest_rate_pct": {"type": "number"},
         "rate_source": {"type": "string"}, "years": {"type": "number"}},
         "required": ["action"]}},
    {"name": "const_land_dekho", "description": (
        "Read the land desk (nothing changes). what=parcels (project optional) | items (project/kind "
        "optional)."),
     "input_schema": {"type": "object", "properties": {
         "what": {"type": "string", "enum": ["parcels", "items"]},
         "project": {"type": "string"}, "kind": {"type": "string"}, "parcel": {"type": "string"}},
         "required": ["what"]}},
]
LAND_LABELS = {"const_land": "Zameen desk par kaam kar raha hoon",
               "const_land_dekho": "Zameen desk dekh raha hoon"}


def _s(v: Any) -> str:
    return "" if v is None else str(v)


def _act(ctx: Ctx, action: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..construction import land as L
    from ..construction.common import guard
    guard(f"{action} land")
    t, conv = ctx.tenant_id, ctx.conversation_id
    try:
        if action == "parcel_add":
            return L.parcel_add(t, _s(a.get("project")), _s(a.get("survey_no")), _s(a.get("village")),
                                float(a.get("area") or 0), _s(a.get("area_source")),
                                _s(a.get("area_unit")) or "sqm", _s(a.get("note")), conv)
        if action == "item_add":
            return L.item_add(t, _s(a.get("project")), _s(a.get("kind")), a.get("rows") or [],
                              _s(a.get("by")), _s(a.get("source")), _s(a.get("note")), conv)
        if action == "recon":
            return L.records_recon(t, _s(a.get("project")), _s(a.get("parcel")))
        if action == "feasibility":
            return L.feasibility(t, _s(a.get("project")), float(a.get("plot_area") or 0),
                                 float(a.get("fsi") or 0), _s(a.get("fsi_source")), _s(a.get("note")))
        if action == "jv_calc":
            return L.jv_entitlement(t, _s(a.get("project")), float(a.get("developable_area") or 0))
        if action == "finance_sum":
            return L.finance_sum(t, _s(a.get("project")), float(a.get("interest_rate_pct") or 0),
                                 _s(a.get("rate_source")), float(a.get("years") or 0))
    except (L.CstError, ValueError) as ex:
        raise ToolError(str(ex)) from None
    raise ToolError("action galat")


async def const_land(ctx: Ctx, action, **a: Any):
    return await asyncio.to_thread(_act, ctx, str(action), a)


async def const_land_dekho(ctx: Ctx, what, **a: Any):
    return await asyncio.to_thread(_read, ctx, str(what), a)


def _read(ctx: Ctx, what: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..construction import land as L
    from ..construction.common import guard
    guard(f"read land {what}")
    try:
        return L.dekho(ctx.tenant_id, what, _s(a.get("project")), _s(a.get("kind")), _s(a.get("parcel")))
    except (L.CstError, ValueError) as ex:
        raise ToolError(str(ex)) from None
    raise ToolError("what galat")


LAND_HANDLERS = {"const_land": const_land, "const_land_dekho": const_land_dekho}
