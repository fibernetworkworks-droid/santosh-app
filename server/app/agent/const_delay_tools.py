"""v0.550.0 const_delay tools (C13b, Wave 3: #47 Delay Analyst's Working-paper Builder). The
programmes are DATA (criticality = HER marks, no CPM computed), the windows are HER choice, the
notice-compliance is the contract's own arithmetic, and the working paper goes to the forensic
planner with the sign line EMPTY - the entitlement conclusion is counsel's (tier C refusal rides)."""
from __future__ import annotations

import asyncio
from typing import Any

from .tools import Ctx, ToolError

DELAY_TOOLS = [
    {"name": "const_delay", "description": (
        "Delay analysis working papers (#47) - as-planned vs as-built, windows, notice compliance. "
        "CRITICALITY IS NOT COMPUTED (YOUR critical marks on the baseline rows); the entitlement "
        "conclusion is not derived by code (forensic planner + counsel). action=prog_add: project, kind "
        "baseline|asbuilt, rows [{activity, start, finish, critical?}] (YYYY-MM-DD). action=window_add: "
        "project, label, start, finish -> analysis window. action=impact: project -> per-activity slip "
        "days + windows touched + HER criticality beside it. action=notice_check: project, event, "
        "event_date, notice_date, notice_days, contract_ref -> in-window/late (arithmetic, cited). "
        "action=pack: project, prepared_for (forensic planner ka naam) -> working paper PDF, sign lines "
        "khaali."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["prog_add", "window_add", "impact", "notice_check", "pack"]},
         "project": {"type": "string"}, "kind": {"type": "string"}, "note": {"type": "string"},
         "rows": {"type": "array", "items": {"type": "object"}},
         "label": {"type": "string"}, "start": {"type": "string"}, "finish": {"type": "string"},
         "event": {"type": "string"}, "event_date": {"type": "string"}, "notice_date": {"type": "string"},
         "notice_days": {"type": "number"}, "contract_ref": {"type": "string"},
         "prepared_for": {"type": "string"}},
         "required": ["action"]}},
    {"name": "const_delay_dekho", "description": (
        "Read the delay desk (nothing changes). what=programmes (project optional) | windows (project) | "
        "notices (project) | impact (project) - same comparison, read-only."),
     "input_schema": {"type": "object", "properties": {
         "what": {"type": "string", "enum": ["programmes", "windows", "notices", "impact"]},
         "project": {"type": "string"}},
         "required": ["what"]}},
]
DELAY_LABELS = {"const_delay": "Delay working paper bana raha hoon", "const_delay_dekho": "Delay desk dekh raha hoon"}


def _s(v: Any) -> str:
    return "" if v is None else str(v)


def _act(ctx: Ctx, action: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..construction import delay as D
    from ..construction.common import guard
    guard(f"{action} delay")
    t, conv = ctx.tenant_id, ctx.conversation_id
    try:
        if action == "prog_add":
            return D.prog_add(t, _s(a.get("project")), _s(a.get("kind")), a.get("rows") or [],
                              _s(a.get("note")), conv)
        if action == "window_add":
            return D.window_add(t, _s(a.get("project")), _s(a.get("label")), _s(a.get("start")),
                                _s(a.get("finish")), _s(a.get("note")))
        if action == "impact":
            return D.impact(t, _s(a.get("project")))
        if action == "notice_check":
            return D.notice_check(t, _s(a.get("project")), _s(a.get("event")), _s(a.get("event_date")),
                                  _s(a.get("notice_date")), a.get("notice_days") or 0,
                                  _s(a.get("contract_ref")))
        if action == "pack":
            return D.pack(t, _s(a.get("project")), _s(a.get("prepared_for")))
    except (D.CstError, ValueError) as ex:
        raise ToolError(str(ex)) from None
    raise ToolError("action galat")


def _read(ctx: Ctx, what: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..construction import delay as D
    from ..construction.common import guard
    from ..db import session
    from sqlalchemy import select
    from ..construction.models import CdelNotice, CdelProg, CdelWindow
    guard(f"read delay {what}")
    t = ctx.tenant_id
    try:
        p = _s(a.get("project"))
        if what == "programmes":
            q = select(CdelProg).where(CdelProg.tenant_id == t)
            if p:
                q = q.where(CdelProg.project == p)
            with session() as s:
                rows = s.scalars(q).all()
            return {"programmes": [{"id": r.id, "project": r.project, "kind": r.kind,
                                    "rows": len(D._j(r.rows, [])), "note": r.note[:60]} for r in rows]}
        if what == "windows":
            q = select(CdelWindow).where(CdelWindow.tenant_id == t)
            if p:
                q = q.where(CdelWindow.project == p)
            with session() as s:
                rows = s.scalars(q).all()
            return {"windows": [{"id": r.id, "label": r.label, "start": r.start, "finish": r.finish}
                                for r in rows]}
        if what == "notices":
            q = select(CdelNotice).where(CdelNotice.tenant_id == t)
            if p:
                q = q.where(CdelNotice.project == p)
            with session() as s:
                rows = s.scalars(q).all()
            return {"notices": [{"id": r.id, "event": r.event[:60], "event_date": r.event_date,
                                 "notice_date": r.notice_date, "taken": r.taken_days,
                                 "window": r.notice_days, "verdict": r.verdict,
                                 "contract_ref": r.contract_ref[:60]} for r in rows]}
        if what == "impact":
            return D.impact(t, p)
    except (D.CstError, ValueError) as ex:
        raise ToolError(str(ex)) from None
    raise ToolError("what galat")


async def const_delay(ctx: Ctx, action, **a: Any):
    return await asyncio.to_thread(_act, ctx, str(action), a)


async def const_delay_dekho(ctx: Ctx, what, **a: Any):
    return await asyncio.to_thread(_read, ctx, str(what), a)


DELAY_HANDLERS = {"const_delay": const_delay, "const_delay_dekho": const_delay_dekho}
