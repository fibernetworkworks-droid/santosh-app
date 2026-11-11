"""v0.531.0 const_drawqa tools (C10: #9 bye-law checker + #16 Drawing QA Reviewer glue; BBS #73
rides const_qs action=bbs). Document-level, PDF/DWG-first. Rules are DATA with clause + source (a
rule without its clause refuses); the check verdict is ARITHMETIC and the outcome is the project
architect's (tier B) - the review pack carries the sign line EMPTY."""
from __future__ import annotations

import asyncio
from typing import Any

from .tools import Ctx, ToolError

DRAWQA_TOOLS = [
    {"name": "const_drawqa", "description": (
        "Drawing QA & bye-law check (document-level, PDF/DWG-first; a PDF was never a model). action=dwg: project, "
        "dwg_no, rev, kind (plan/section/structural/services), scale_as_noted, source -> register. action=rule_add: "
        "rule_id, text, limit_value, unit, clause (e.g. 'UDCPR 6.1'), source (which DCPR / ULB letter), direction "
        "min|max (setback is MIN, FAR is MAX) - a rule without a clause is not kept. action=check: drawing, rule_id, "
        "declared -> within/breach (ARITHMETIC; the project architect decides). action=review_pack: drawing -> checks + "
        "PDF with an empty sign line (for the architect). "
        "action=dwg_mark: drawing, status received|under_check|returned|ok_drafted."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["dwg", "rule_add", "check", "review_pack", "dwg_mark"]},
         "project": {"type": "string"}, "dwg_no": {"type": "string"}, "rev": {"type": "string"},
         "kind": {"type": "string"}, "scale_as_noted": {"type": "string"}, "source": {"type": "string"},
         "drawing": {"type": "string"}, "rule_id": {"type": "string"}, "text": {"type": "string"},
         "limit_value": {"type": "number"}, "unit": {"type": "string"}, "clause": {"type": "string"},
         "checked_on": {"type": "string"}, "declared": {"type": "number"}, "note": {"type": "string"},
         "direction": {"type": "string"}, "status": {"type": "string"}},
         "required": ["action"]}},
    {"name": "const_drawqa_dekho", "description": (
        "Read drawing QA (nothing changes). what=day | drawings (project optional) | rules | checks (drawing optional)."),
     "input_schema": {"type": "object", "properties": {
         "what": {"type": "string", "enum": ["day", "drawings", "rules", "checks"]},
         "project": {"type": "string"}, "drawing": {"type": "string"}}, "required": ["what"]}},
]
DRAWQA_LABELS = {"const_drawqa": "Checking the drawing register", "const_drawqa_dekho": "Viewing drawing QA"}


def _s(v: Any) -> str:
    return "" if v is None else str(v)


def _act(ctx: Ctx, action: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..construction import drawqa as D
    from ..construction.common import guard
    guard(f"{action} drawqa")     # tier-C refusal rides every construction action
    t = ctx.tenant_id
    try:
        if action == "dwg":
            return D.dwg_add(t, _s(a.get("project")), _s(a.get("dwg_no")), _s(a.get("rev")), _s(a.get("kind")),
                             _s(a.get("scale_as_noted")), _s(a.get("source")), ctx.conversation_id)
        if action == "rule_add":
            return D.rule_add(t, _s(a.get("rule_id")), _s(a.get("text")), a.get("limit_value"), _s(a.get("unit")),
                              _s(a.get("clause")), _s(a.get("source")), _s(a.get("checked_on")),
                              _s(a.get("direction")) or "max")
        if action == "check":
            return D.check(t, _s(a.get("drawing")), _s(a.get("rule_id")), a.get("declared"), _s(a.get("note")))
        if action == "review_pack":
            return D.review_pack(t, _s(a.get("drawing")))
        if action == "dwg_mark":
            return D.dwg_mark(t, _s(a.get("drawing")), _s(a.get("status")), _s(a.get("note")))
    except (D.CstError, ValueError) as ex:
        raise ToolError(str(ex))
    raise ToolError("action galat")


def _read(ctx: Ctx, what: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..construction import drawqa as D
    from ..construction.common import guard
    from ..db import session
    from sqlalchemy import select
    from ..construction.models import CDraw, CDrawCheck, CDrawRule
    t = ctx.tenant_id
    guard(f"read drawqa {what}")
    try:
        if what == "day":
            return D.day(t)
        if what == "drawings":
            with session() as s:
                rows = s.scalars(select(CDraw).where(CDraw.tenant_id == t)).all()
            p = _s(a.get("project"))
            if p:
                rows = [r for r in rows if r.project == p]
            return {"drawings": [{"id": r.id, "project": r.project, "dwg_no": r.dwg_no, "rev": r.rev,
                                  "kind": r.kind, "status": r.status} for r in rows]}
        if what == "rules":
            with session() as s:
                rows = s.scalars(select(CDrawRule).where(CDrawRule.tenant_id == t)).all()
            return {"rules": [{"id": r.id, "rule_id": r.rule_id, "text": r.text[:80], "limit": r.limit_value,
                               "direction": r.direction, "unit": r.unit, "clause": r.clause, "source": r.source[:60]}
                              for r in rows]}
        if what == "checks":
            with session() as s:
                rows = s.scalars(select(CDrawCheck).where(CDrawCheck.tenant_id == t)).all()
            d = _s(a.get("drawing"))
            if d:
                rows = [r for r in rows if r.drawing_id == d]
            return {"checks": [{"id": r.id, "drawing_id": r.drawing_id, "rule_id": r.rule_id, "declared": r.declared,
                                "limit": r.limit_value, "verdict": r.verdict, "checked_on": r.checked_on}
                               for r in rows]}
    except (D.CstError, ValueError) as ex:
        raise ToolError(str(ex))
    raise ToolError("what galat")


async def const_drawqa(ctx: Ctx, action, **a: Any):
    return await asyncio.to_thread(_act, ctx, str(action), a)


async def const_drawqa_dekho(ctx: Ctx, what, **a: Any):
    return await asyncio.to_thread(_read, ctx, str(what), a)


DRAWQA_HANDLERS = {"const_drawqa": const_drawqa, "const_drawqa_dekho": const_drawqa_dekho}
