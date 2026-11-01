"""v0.357 ENGINEERING DESK chat tool: the hired CAD Engineer designs a part from her words (CadQuery in Hoola's locked
box) and changes it on her words. Files (STEP / STL / drawing PDF / views) land on the CAD Desk; the chat gets one line."""
from __future__ import annotations

import asyncio

from .tools import Ctx, ToolError

ENG_TOOLS = [
    {"name": "cad_part", "description": (
        "The CAD Engineer (an employee she hires in Employees). Designs a mechanical part from her words and sizes in mm "
        "as parametric CadQuery code, builds it in Hoola's locked box (no network), checks it (valid solid, one body, "
        "the size asked) and gives STEP (CAD / CNC), STL (3D printing), 4 views and a dimensioned drawing PDF on the CAD "
        "Desk. action=new brief=<what the part is, every size she gave in mm, holes, fillets, material> starts a part "
        "(runs in the background, about a minute; the chat gets a line when ready). action=change project_id=... "
        "words=<her change> makes the next version. action=list / get project_id=... show parts and files. "
        "If she has not hired the CAD Engineer, tell her to hire it from Employees (one tap). Never call a design "
        "certified, approved or safe without a qualified engineer; refuse weapons and export-controlled parts."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["new", "change", "list", "get"]},
         "brief": {"type": "string"}, "project_id": {"type": "string"}, "words": {"type": "string"}},
         "required": ["action"]}},
]
ENG_LABELS = {"cad_part": "CAD part bana raha hoon"}


async def cad_part(ctx: Ctx, action, brief="", project_id="", words="", **_):
    from ..engineering import service as eng

    def go():
        try:
            if action == "new":
                p = eng.start(ctx.tenant_id, ctx.conversation_id, str(brief or ""))
                return {"project_id": p["id"], "status": p["status"],
                        "say": "Part ban raha hai (lagbhag ek minute). Taiyaar hote hi chat mein line aayegi; files CAD Desk par."}
            if action == "change":
                p = eng.change(ctx.tenant_id, str(project_id or ""), str(words or ""), ctx.conversation_id)
                return {"project_id": p["id"], "status": p["status"], "say": "Naya version ban raha hai."}
            if action == "get":
                return eng.get(ctx.tenant_id, str(project_id or ""))
            if action == "list":
                return {"projects": [{k: p[k] for k in ("id", "title", "status", "stage")} for p in eng.projects(ctx.tenant_id, 15)]}
        except eng.EngError as e:
            raise ToolError(str(e))
        raise ToolError("action must be new, change, list or get")
    return await asyncio.to_thread(go)


ENG_HANDLERS = {"cad_part": cad_part}
