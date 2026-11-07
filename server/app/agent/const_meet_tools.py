"""v0.512.0 const_meet tools (#67 Meeting Secretary). `const_meet_dekho` only reads; `const_meet` does
the work. Tier A: OAC / site / coordination meetings, minutes as said, action items chased till closed
(closing is on the owner's / PM's word). Minutes PDF circulate karta hai - decisions Hoola nahi leta."""
from __future__ import annotations

import asyncio
from typing import Any

from .tools import Ctx, ToolError

MEET_TOOLS = [
    {"name": "const_meet", "description": (
        "Meeting secretary (OAC / site / coordination). action=meet: title, kind oac|site|coord|client|weekly, day, "
        "site, project, attendees, minutes [{text, by}], actions [{what, who, due}] -> baithak record + chase. "
        "action=minute: meet (id), text, by. action=action: meet (id), what, who, due. action=action_done: action (id) "
        "- OWNER ONLY, band karne ki haan. action=minutes_pdf: meet (id) -> the minutes PDF (file)."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["meet", "minute", "action", "action_done", "minutes_pdf"]},
         "title": {"type": "string"}, "kind": {"type": "string"}, "day": {"type": "string"}, "site": {"type": "string"},
         "project": {"type": "string"}, "attendees": {"type": "string"}, "minutes": {"type": "array", "items": {"type": "object"}},
         "actions": {"type": "array", "items": {"type": "object"}}, "meet": {"type": "string"}, "text": {"type": "string"},
         "by": {"type": "string"}, "what": {"type": "string"}, "who": {"type": "string"}, "due": {"type": "string"},
         "action_id": {"type": "string"}},
         "required": ["action"]}},
    {"name": "const_meet_dekho", "description": (
        "Read meetings (nothing changes). what=actions (open action items, late first) | meets (recent) | meet (id: "
        "minutes + actions)."),
     "input_schema": {"type": "object", "properties": {
         "what": {"type": "string", "enum": ["actions", "meets", "meet"]}, "meet": {"type": "string"}},
         "required": ["what"]}},
]
MEET_LABELS = {"const_meet": "Baithak ka record likh raha hoon", "const_meet_dekho": "Meetings dekh raha hoon"}


def _s(v: Any) -> str:
    return "" if v is None else str(v)


def _act(ctx: Ctx, action: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..construction import meetings as M
    from ..construction.common import guard
    guard(f"{action} meet")     # tier-C refusal rides every construction action
    t, conv = ctx.tenant_id, ctx.conversation_id
    try:
        if action == "meet":
            return M.meet(t, _s(a.get("title")), _s(a.get("kind")) or "site", _s(a.get("day")), _s(a.get("site")),
                          _s(a.get("project")), _s(a.get("attendees")), a.get("minutes"), a.get("actions"), conv)
        if action == "minute":
            return M.minute(t, _s(a.get("meet")), _s(a.get("text")), _s(a.get("by")))
        if action == "action":
            return M.action(t, _s(a.get("meet")), _s(a.get("what")), _s(a.get("who")), _s(a.get("due")))
        if action == "action_done":
            return M.action_done(t, _s(a.get("action_id")), ctx.actor)
        if action == "minutes_pdf":
            from .. import chatfiles
            mid = _s(a.get("meet"))
            pdf = M.minutes_pdf(t, mid)
            f = chatfiles.store(t, f"Minutes-{mid[:8]}.pdf", pdf, "application/pdf")
            return {"file": f, "say": "Minutes PDF ban gaya - circulate kijiye."}
    except (M.CstError, ValueError) as ex:
        raise ToolError(str(ex))
    raise ToolError("action galat")


def _read(ctx: Ctx, what: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..construction import meetings as M
    t = ctx.tenant_id
    try:
        if what == "actions":
            return M.open_actions(t)
        if what in ("meets", "meet"):
            from ..db import session
            from sqlalchemy import select
            from ..construction.common import _j
            from ..construction.models import CActionItem, CMeet
            with session() as s:
                if what == "meet":
                    x = s.get(CMeet, _s(a.get("meet")))
                    if not x or x.tenant_id != t:
                        raise M.CstError("Baithak nahi mili.")
                    acts = s.scalars(select(CActionItem).where(CActionItem.meet_id == x.id)).all()
                    return {"meet": {"title": x.title, "kind": x.kind, "day": x.day, "site": x.site, "project": x.project,
                                     "attendees": x.attendees, "minutes": _j(x.minutes, [])},
                            "actions": [{"what": r.what[:100], "who": r.who, "due": r.due, "status": r.status} for r in acts]}
                rows = s.scalars(select(CMeet).where(CMeet.tenant_id == t).order_by(CMeet.day.desc())).all()
            return {"meets": [{"id": r.id, "title": r.title, "kind": r.kind, "day": r.day, "status": r.status} for r in rows[:15]]}
    except (M.CstError, ValueError) as ex:
        raise ToolError(str(ex))
    raise ToolError("what galat")


async def const_meet(ctx: Ctx, action, **a: Any):
    return await asyncio.to_thread(_act, ctx, str(action), a)


async def const_meet_dekho(ctx: Ctx, what, **a: Any):
    return await asyncio.to_thread(_read, ctx, str(what), a)


MEET_HANDLERS = {"const_meet": const_meet, "const_meet_dekho": const_meet_dekho}
