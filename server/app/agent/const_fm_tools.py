"""v0.586.0 const_fm tools (Wave 4: #102-#108, riding the EXISTING property/society seats per plan
§12 - the duty `fm_work` in roles.py admits these tools, no new hire key). Due dates and gaps are
arithmetic on FED rows; the compliance certificate is the agency's, the structural-audit
certificate the registered engineer's (tier C via gates)."""
from __future__ import annotations

import asyncio
from typing import Any

from .tools import Ctx, ToolError

FM_TOOLS = [
    {"name": "const_fm", "description": (
        "Facility & property FM desk (#102-#108, property/society seats ke tools). action=wo_add: "
        "project, location, issue, priority -> work order. action=wo_update: wo (id), status "
        "open|in_progress|done|cancelled, by (naam zaroori). action=ppm_add: project, rows [asset, "
        "task, freq_days, last_done]. action=ppm_due: project (optional) -> next-due arithmetic. "
        "action=comp_add: project, rows [system(lift|fire|stp|wtp|other), cert_no, agency, last, due]. "
        "action=comp_due: project -> overdue list (certificate agency ki). action=roster_add: rows "
        "[post, weekday, shift, person]. action=roster_gap: project -> khali posts. action=audit_add: "
        "rows [building, audit_type, last, cycle_yrs(aapke municipal circular se), agency]. "
        "action=audit_due: project -> next-due (certificate registered engineer ki, tier C). "
        "action=asset_add: rows [asset, space, dept, warranty_till]."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["wo_add", "wo_update", "ppm_add", "ppm_due",
                                               "comp_add", "comp_due", "roster_add", "roster_gap",
                                               "audit_add", "audit_due", "asset_add"]},
         "project": {"type": "string"}, "location": {"type": "string"}, "issue": {"type": "string"},
         "priority": {"type": "string"}, "wo": {"type": "string"}, "status": {"type": "string"},
         "by": {"type": "string"}, "rows": {"type": "array", "items": {}}},
         "required": ["action"]}},
    {"name": "const_fm_dekho", "description": (
        "Read the FM desk (nothing changes). what=wo | ppm | comp | roster | audit | asset (project "
        "optional)."),
     "input_schema": {"type": "object", "properties": {
         "what": {"type": "string", "enum": ["wo", "ppm", "comp", "roster", "audit", "asset"]},
         "project": {"type": "string"}},
         "required": ["what"]}},
]
FM_LABELS = {"const_fm": "FM desk par kaam kar raha hoon",
             "const_fm_dekho": "FM desk dekh raha hoon"}


def _s(v: Any) -> str:
    return "" if v is None else str(v)


def _act(ctx: Ctx, action: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..construction import fm as F
    from ..construction.common import guard
    guard(f"{action} fm")
    t, conv = ctx.tenant_id, ctx.conversation_id
    try:
        if action == "wo_add":
            return F.wo_add(t, _s(a.get("project")), _s(a.get("location")), _s(a.get("issue")),
                            _s(a.get("priority")) or "normal", conv)
        if action == "wo_update":
            return F.wo_update(t, _s(a.get("wo")), _s(a.get("status")), _s(a.get("by")))
        if action == "ppm_add":
            return F.ppm_add(t, _s(a.get("project")), a.get("rows") or [], conv)
        if action == "ppm_due":
            return F.ppm_due(t, _s(a.get("project")))
        if action == "comp_add":
            return F.comp_add(t, _s(a.get("project")), a.get("rows") or [], conv)
        if action == "comp_due":
            return F.comp_due(t, _s(a.get("project")))
        if action == "roster_add":
            return F.roster_add(t, _s(a.get("project")), a.get("rows") or [])
        if action == "roster_gap":
            return F.roster_gap(t, _s(a.get("project")))
        if action == "audit_add":
            return F.audit_add(t, _s(a.get("project")), a.get("rows") or [])
        if action == "audit_due":
            return F.audit_due(t, _s(a.get("project")))
        if action == "asset_add":
            return F.asset_add(t, _s(a.get("project")), a.get("rows") or [])
    except (F.CstError, ValueError) as ex:
        raise ToolError(str(ex)) from None
    raise ToolError("action galat")


async def const_fm(ctx: Ctx, action, **a: Any):
    return await asyncio.to_thread(_act, ctx, str(action), a)


async def const_fm_dekho(ctx: Ctx, what, **a: Any):
    return await asyncio.to_thread(_read, ctx, str(what), a)


def _read(ctx: Ctx, what: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..construction import fm as F
    from ..construction.common import guard
    guard(f"read fm {what}")
    try:
        return F.dekho(ctx.tenant_id, what, _s(a.get("project")))
    except (F.CstError, ValueError) as ex:
        raise ToolError(str(ex)) from None
    raise ToolError("what galat")


FM_HANDLERS = {"const_fm": const_fm, "const_fm_dekho": const_fm_dekho}
