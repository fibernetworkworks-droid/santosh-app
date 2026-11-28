"""HOOLA DIAGRAM (docs/DIAGRAM_TOOL_PLAN.md): ONE `diagram` tool, the same for Hoola chat and (D4) Hoola Code.

The model writes only a DESCRIPTION; a vendored engine draws it and checks it (app/diagram/service.py):
archify (10 system / code types - its own code places boxes and lines) or diagram-design (the other types, a designer
look). The checked diagram opens in her workspace as a page with versions; the model sees a picture of it first."""
from __future__ import annotations

from .tools import Ctx, ToolError

DIAGRAM_TOOLS = [
    {"name": "diagram", "description": (
        "Draw a DIAGRAM for her - architecture, workflow / process, sequence, data flow, status / lifecycle, database "
        "tables (ERD), class, tree / hierarchy, timeline, time waterfall, flowchart, org chart, funnel / pyramid, "
        "quadrant, venn, user journey, swimlane, Gantt, sankey, fishbone, Wardley, kanban, charts (bar, line, scatter, "
        "heatmap, treemap) and more (action=types lists every one) - whenever she asks for one, or a picture would "
        "explain better than text, also in the middle of other work. NOT for a plain list (write a table) and NOT for "
        "an interactive page / calculator (that is `artifact`). Two engines draw: archify for systems, flows and "
        "anything about code (its code places every box and line - you write NO coordinates) and diagram-design for "
        "the rest; code picks the engine from the type. STEPS: (1) tell her the plan in ONE line (type, what is in it, "
        "what you leave out); (2) action=guide with the type - read what to write; (3) action=draw with type, title "
        "and content (archify: its JSON; diagram-design: the whole HTML page); (4) a failing check comes back with the "
        "exact problems - fix them and draw again with the SAME diagram_id (3 rounds); (5) a passing diagram comes "
        "back WITH A PICTURE - look at it; fix anything wrong with action=update; then tell her in one or two sentences "
        "what it shows (she opens the card). Labels in HER language; only facts she gave or you read - an unknown is a "
        "[blank]. EDITABLE: when she wants to change it by hand (or says draw.io / editable), draw type drawio - she can "
        "drag, rename and restyle it herself; to change one later, action=read first (you get the shapes she has "
        "SELECTED), then action=change with ops id by id - never redraw her hand work; action=editable turns an archify / "
        "diagram-design diagram into a draw.io one. action=list shows her diagrams."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["types", "guide", "draw", "update", "read", "change", "editable", "list"]},
         "type": {"type": "string", "description": "guide / draw: the diagram type, e.g. architecture, sequence, "
                                                   "workflow, flowchart, org-chart, pyramid, journey, gantt"},
         "engine": {"type": "string", "enum": ["archify", "diagram-design", "drawio"],
                    "description": "optional: only if she asked for one; code checks it draws the type"},
         "title": {"type": "string", "description": "draw: a short name she will recognise"},
         "content": {"description": "draw / update: the WHOLE description - archify: its JSON (object or string); "
                                    "diagram-design: the complete HTML page"},
         "diagram_id": {"type": "string", "description": "draw (a fix round) / update / read / change / editable: the "
                                                         "diagram's id"},
         "from_id": {"type": "string", "description": "draw type drawio: the archify / diagram-design diagram this "
                                                      "editable one redraws (action=editable gives it)"},
         "ops": {"type": "array", "description": "change (editable diagrams): [{op: update|add|delete, id, value, style, "
                                                 "x, y, width, height, source, target, edge, parent}] - ids from action=read",
                 "items": {"type": "object"}},
         "edits": {"type": "array", "description": "update: exact replacements in the current description",
                   "items": {"type": "object", "properties": {"old_str": {"type": "string"},
                                                               "new_str": {"type": "string"}},
                             "required": ["old_str", "new_str"]}}},
         "required": ["action"]}},
]

DIAGRAM_LABELS = {"diagram": "Drawing the diagram"}


async def diagram(ctx: Ctx, action: str = "", **args):
    import asyncio

    from ..diagram import service as S
    act = str(action or "").strip().lower()
    tenant, conv = ctx.tenant_id, ctx.conversation_id or ""
    if act == "types":
        return {"ok": True, "types": [f"{t['type']} ({t['engine']}): {t['use']}" for t in S.catalogue()]}
    if act == "guide":
        if not args.get("type"):
            raise ToolError("guide needs type (action=types lists them).")
        return S.guide(str(args["type"]), str(args.get("engine") or ""))
    if act == "list":
        return {"ok": True, "diagrams": S.listing(tenant)}
    if act == "draw":
        if args.get("content") in (None, ""):
            raise ToolError("draw needs content: the whole description (read action=guide for the type first).")
        if not args.get("type") and not args.get("diagram_id"):
            raise ToolError("draw needs type (or diagram_id for a fix round).")
        return await asyncio.to_thread(S.draw, tenant, conv, str(args.get("type") or ""), str(args.get("title") or ""),
                                       args.get("content"), str(args.get("engine") or ""),
                                       str(args.get("diagram_id") or ""), str(args.get("from_id") or ""))
    if act == "read":
        if not args.get("diagram_id"):
            raise ToolError("read needs diagram_id (action=list shows them).")
        return await asyncio.to_thread(S.read, tenant, str(args["diagram_id"]))
    if act == "change":
        if not args.get("diagram_id") or not isinstance(args.get("ops"), list):
            raise ToolError("change needs diagram_id and ops (a list) - call action=read first.")
        return await asyncio.to_thread(S.change, tenant, conv, str(args["diagram_id"]), args["ops"])
    if act == "editable":
        if not args.get("diagram_id"):
            raise ToolError("editable needs diagram_id.")
        return await asyncio.to_thread(S.editable, tenant, str(args["diagram_id"]))
    if act == "update":
        if not args.get("diagram_id"):
            raise ToolError("update needs diagram_id (action=list shows them).")
        return await asyncio.to_thread(S.update, tenant, conv, str(args["diagram_id"]), args.get("edits"),
                                       args.get("content"), str(args.get("title") or ""))
    raise ToolError("action must be types, guide, draw, update, read, change, editable or list.")


DIAGRAM_HANDLERS = {"diagram": diagram}
