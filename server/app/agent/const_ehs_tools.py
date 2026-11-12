"""v0.586.0 const_ehs tools (Wave 4: #83 training & competency, #84 environmental monitoring,
#86 labour camp & welfare). Readings and limits are FED with sources; expiry/exceedance arithmetic;
"declare the site safe" stays with the EHS head (tier C via gates)."""
from __future__ import annotations

import asyncio
from typing import Any

from .tools import Ctx, ToolError

EHS_TOOLS = [
    {"name": "const_ehs", "description": (
        "EHS & welfare desk (#83/#84/#86). action=training_add: project, rows [name, trade, training, "
        "date, valid_till]. action=training_due: project (optional) -> expired / due-30-days / valid "
        "(the EHS head schedules the refresher). action=env_add: project, kind env_read|env_limit, rows "
        "- env_read [parameter, value, unit] (from your monitoring report), env_limit [parameter, "
        "limit, unit] + source (CPCB/SPCB norm) needed. action=env_check: project -> exceedance "
        "arithmetic on the fed limits. action=camp_add: project, rows [block, capacity, occupancy]. "
        "action=camp_check: project, rows [item, status], by (checker's name needed - clash_mark "
        "law; the welfare verdict is the officer's)."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["training_add", "training_due", "env_add", "env_check",
                                               "camp_add", "camp_check"]},
         "project": {"type": "string"}, "rows": {"type": "array", "items": {}},
         "kind": {"type": "string"}, "source": {"type": "string"}, "by": {"type": "string"}},
         "required": ["action"]}},
    {"name": "const_ehs_dekho", "description": (
        "Read the EHS desk (nothing changes). what=training | env | camp (project optional) - items "
        "by kind training|env_read|env_limit|camp|camp_check."),
     "input_schema": {"type": "object", "properties": {
         "what": {"type": "string", "enum": ["training", "env", "camp"]},
         "project": {"type": "string"}, "kind": {"type": "string"}},
         "required": ["what"]}},
]
EHS_LABELS = {"const_ehs": "Working on the safety and welfare desk",
              "const_ehs_dekho": "Viewing the safety desk"}


def _s(v: Any) -> str:
    return "" if v is None else str(v)


_EH = {"training": "training", "env_read": "env_read", "env_limit": "env_limit",
       "camp": "camp", "camp_check": "camp_check"}


def _act(ctx: Ctx, action: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..construction import ehs as E
    from ..construction.common import guard
    guard(f"{action} ehs")
    t, conv = ctx.tenant_id, ctx.conversation_id
    try:
        if action == "training_add":
            return E.training_add(t, _s(a.get("project")), a.get("rows") or [], conv)
        if action == "training_due":
            return E.training_due(t, _s(a.get("project")))
        if action == "env_add":
            return E.env_add(t, _s(a.get("project")), _s(a.get("kind")), a.get("rows") or [],
                             _s(a.get("source")), conv)
        if action == "env_check":
            return E.env_check(t, _s(a.get("project")))
        if action == "camp_add":
            return E.camp_add(t, _s(a.get("project")), a.get("rows") or [])
        if action == "camp_check":
            return E.camp_check(t, _s(a.get("project")), a.get("rows") or [], _s(a.get("by")))
    except (E.CstError, ValueError) as ex:
        raise ToolError(str(ex)) from None
    raise ToolError("Unknown action")


def _read(ctx: Ctx, what: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..construction import ehs as E
    from ..construction import models as M
    from ..construction.common import guard, _j
    from ..db import session
    from sqlalchemy import select
    guard(f"read ehs {what}")
    t, proj = ctx.tenant_id, _s(a.get("project"))
    kinds = {"training": ["training"], "env": ["env_read", "env_limit"], "camp": ["camp", "camp_check"]}
    if what not in kinds:
        raise ToolError("Unknown what")
    q = select(M.CEhsItem).where(M.CEhsItem.tenant_id == t, M.CEhsItem.kind.in_(kinds[what]))
    if proj:
        q = q.where(M.CEhsItem.project == proj)
    with session() as s:
        rows = s.scalars(q).all()
    return {what: [{"id": r.id, "project": r.project, "kind": r.kind, "name": r.name,
                    "data": _j(r.data, {}), "source": r.source, "by": r.by} for r in rows]}


async def const_ehs(ctx: Ctx, action, **a: Any):
    return await asyncio.to_thread(_act, ctx, str(action), a)


async def const_ehs_dekho(ctx: Ctx, what, **a: Any):
    return await asyncio.to_thread(_read, ctx, str(what), a)


EHS_HANDLERS = {"const_ehs": const_ehs, "const_ehs_dekho": const_ehs_dekho}
