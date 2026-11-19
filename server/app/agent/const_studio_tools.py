"""v0.586.0 const_studio + const_learn tools (Wave 4: #119/#120 studio, #121/#122/#123 learning).

Studio keeps the shot-brief register and checklists - Hoola renders nothing. Learning keeps the
registers, quizzes and arithmetic - the certificate is the training centre's, tax/investment advice
stays the CA's (tier C via gates)."""
from __future__ import annotations

import asyncio
from typing import Any

from .tools import Ctx, ToolError

STUDIO_TOOLS = [
    {"name": "const_studio", "description": (
        "Visualisation & presentation desk (#119/#120) - registers and checklists, NOT render/design. "
        "action=shot_add: project, rows [shot, view, time_of_day, purpose] -> brief register. "
        "action=shot_asset: project, shot, rows [asset, needed(yes/no), status]. action=report_add: "
        "project, name, rows [section, kind, status] -> outline register (deck approval is YOURS). "
        "action=status: project, ref (optional) -> pending vs ready."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["shot_add", "shot_asset", "report_add", "status"]},
         "project": {"type": "string"}, "rows": {"type": "array", "items": {}},
         "shot": {"type": "string"}, "name": {"type": "string"}, "ref": {"type": "string"}},
         "required": ["action"]}},
    {"name": "const_studio_dekho", "description": (
        "Read the studio desk (nothing changes). what=shots | reports | items (project optional)."),
     "input_schema": {"type": "object", "properties": {
         "what": {"type": "string", "enum": ["shots", "reports", "items"]},
         "project": {"type": "string"}},
         "required": ["what"]}},
]
STUDIO_LABELS = {"const_studio": "Working on the studio desk",
                 "const_studio_dekho": "Viewing the studio desk"}

LEARN_TOOLS = [
    {"name": "const_learn", "description": (
        "Training & coaching desk (#121/#122/#123). action=trainee_add: project, rows [name, trade, "
        "batch]. action=module_add: rows [module, hours, status]. action=assess_add: rows [trainee, "
        "module, marks, max] (marks from YOUR sheets). action=assess_sum: project, pass_pct (YOUR "
        "policy) -> pass/re-test. action=topic_add: rows [topic, syllabus_ref, status]. action=quiz_add: "
        "project, topic, rows [question, correct_answer, option_b, option_c, option_d]. action=quiz_score: "
        "topic, rows [trainee, answers...] -> score arithmetic. action=coach_check: rows [item, status, "
        "note] (contractor records discipline). action=coach_note: text. Certificate training centre "
        "gives; tax/investment advice is tier C."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["trainee_add", "module_add", "assess_add", "assess_sum",
                                               "topic_add", "quiz_add", "quiz_score", "coach_check",
                                               "coach_note"]},
         "project": {"type": "string"}, "rows": {"type": "array", "items": {}},
         "pass_pct": {"type": "number"}, "topic": {"type": "string"}, "text": {"type": "string"}},
         "required": ["action"]}},
    {"name": "const_learn_dekho", "description": (
        "Read the learning desk (nothing changes). what=trainees | modules | assessments | topics | "
        "quizzes | coach (project optional)."),
     "input_schema": {"type": "object", "properties": {
         "what": {"type": "string", "enum": ["trainees", "modules", "assessments", "topics",
                                             "quizzes", "coach"]},
         "project": {"type": "string"}},
         "required": ["what"]}},
]
LEARN_LABELS = {"const_learn": "Working on the training desk",
                "const_learn_dekho": "Viewing the training desk"}


def _s(v: Any) -> str:
    return "" if v is None else str(v)


def _studio_act(ctx: Ctx, action: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..construction import studio as ST
    from ..construction.common import guard
    guard(f"{action} studio")
    t, conv = ctx.tenant_id, ctx.conversation_id
    try:
        if action == "shot_add":
            return ST.shot_add(t, _s(a.get("project")), a.get("rows") or [], conv)
        if action == "shot_asset":
            return ST.shot_asset(t, _s(a.get("project")), _s(a.get("shot")), a.get("rows") or [])
        if action == "report_add":
            return ST.report_add(t, _s(a.get("project")), _s(a.get("name")), a.get("rows") or [], conv)
        if action == "status":
            return ST.studio_status(t, _s(a.get("project")), _s(a.get("ref")))
    except (ST.CstError, ValueError) as ex:
        raise ToolError(str(ex)) from None
    raise ToolError("unknown action")


def _learn_act(ctx: Ctx, action: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..construction import learn as LE
    from ..construction.common import guard
    guard(f"{action} learning")
    t, conv = ctx.tenant_id, ctx.conversation_id
    try:
        if action == "trainee_add":
            return LE.trainee_add(t, _s(a.get("project")), a.get("rows") or [], conv)
        if action == "module_add":
            return LE.module_add(t, _s(a.get("project")), a.get("rows") or [])
        if action == "assess_add":
            return LE.assess_add(t, _s(a.get("project")), a.get("rows") or [])
        if action == "assess_sum":
            return LE.assess_sum(t, _s(a.get("project")), float(a.get("pass_pct") or 0))
        if action == "topic_add":
            return LE.topic_add(t, _s(a.get("project")), a.get("rows") or [])
        if action == "quiz_add":
            return LE.quiz_add(t, _s(a.get("project")), _s(a.get("topic")), a.get("rows") or [])
        if action == "quiz_score":
            return LE.quiz_score(t, _s(a.get("project")), _s(a.get("topic")), a.get("rows") or [])
        if action == "coach_check":
            return LE.coach_check(t, _s(a.get("project")), a.get("rows") or [])
        if action == "coach_note":
            return LE.coach_note(t, _s(a.get("project")), _s(a.get("text")), conv)
    except (LE.CstError, ValueError) as ex:
        raise ToolError(str(ex)) from None
    raise ToolError("unknown action")


async def const_studio(ctx: Ctx, action, **a: Any):
    return await asyncio.to_thread(_studio_act, ctx, str(action), a)


async def const_studio_dekho(ctx: Ctx, what, **a: Any):
    return await asyncio.to_thread(_studio_read, ctx, str(what), a)


def _studio_read(ctx: Ctx, what: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..construction import studio as ST
    from ..construction import models as M
    from ..construction.common import guard, _j
    from ..db import session
    from sqlalchemy import select
    guard(f"read studio {what}")
    q = select(M.CstudioItem).where(M.CstudioItem.tenant_id == ctx.tenant_id)
    if _s(a.get("project")):
        q = q.where(M.CstudioItem.project == _s(a.get("project")))
    if what == "shots":
        q = q.where(M.CstudioItem.kind == "shot")
    elif what == "reports":
        q = q.where(M.CstudioItem.kind == "report")
    elif what != "items":
        raise ToolError("unknown what")
    with session() as s:
        rows = s.scalars(q).all()
    return {what: [{"id": r.id, "project": r.project, "kind": r.kind, "ref": r.ref,
                    "name": r.name, "data": _j(r.data, {})} for r in rows]}


async def const_learn(ctx: Ctx, action, **a: Any):
    return await asyncio.to_thread(_learn_act, ctx, str(action), a)


async def const_learn_dekho(ctx: Ctx, what, **a: Any):
    return await asyncio.to_thread(_learn_read, ctx, str(what), a)


def _learn_read(ctx: Ctx, what: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..construction import learn as LE
    from ..construction import models as M
    from ..construction.common import guard, _j
    from ..db import session
    from sqlalchemy import select
    guard(f"read learning {what}")
    kinds = {"trainees": ["trainee"], "modules": ["module"], "assessments": ["assess"],
             "topics": ["topic"], "quizzes": ["quiz", "attempt"], "coach": ["coach", "coach_note"]}
    if what not in kinds:
        raise ToolError("unknown what")
    q = select(M.ClearnItem).where(M.ClearnItem.tenant_id == ctx.tenant_id,
                                   M.ClearnItem.kind.in_(kinds[what]))
    if _s(a.get("project")):
        q = q.where(M.ClearnItem.project == _s(a.get("project")))
    with session() as s:
        rows = s.scalars(q).all()
    return {what: [{"id": r.id, "project": r.project, "kind": r.kind, "name": r.name,
                    "data": _j(r.data, {}), "note": r.note} for r in rows]}


STUDIO_HANDLERS = {"const_studio": const_studio, "const_studio_dekho": const_studio_dekho}
LEARN_HANDLERS = {"const_learn": const_learn, "const_learn_dekho": const_learn_dekho}
