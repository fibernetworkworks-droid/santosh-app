"""Santosh Artifacts tools: build or revise an interactive page for the user (see app/artifacts.py)."""
from __future__ import annotations

from .. import artifacts
from .tools import Ctx, ToolError

ARTIFACT_TOOLS = [
    {"name": "artifact_make", "description": (
        "Build an interactive page the user opens full screen in the Santosh app and can share: a calculator (EMI, GST, "
        "profit, loan), a tracker or hisaab book (milk, udhar, expenses, attendance, habits, study), a checklist or "
        "planner, a chart or mini dashboard from their numbers, a quiz or flashcards, a poster/menu/price list/visiting "
        "card, a mini landing page, a simple game, a formatted document or plan. Use it whenever the user wants "
        "something to USE, KEEP, SEE or SHARE rather than just an answer ('ek calculator bana do', 'chart dikhao', "
        "'tracker chahiye', 'poster banao'). Write `request` as a full brief: purpose, every detail and number the "
        "user gave, language (Hindi/Hinglish/English/Marathi...), style wishes. Put any table/list data in `data`. "
        "To change an existing page pass its artifact_id with the change request (a new version is made; saved data "
        "is kept). Pages can save entries and ask Santosh questions. A card with an Open button appears in the chat; "
        "building takes about 20-90 seconds."),
     "input_schema": {"type": "object", "properties": {
         "request": {"type": "string", "description": "Full brief of what to build or what to change"},
         "artifact_id": {"type": "string", "description": "Only to revise an existing page"},
         "data": {"type": "string", "description": "Optional data to embed: CSV, JSON or a plain list"}},
         "required": ["request"]}},
    {"name": "artifact_list", "description": "The user's recent Santosh pages (artifacts) with ids, titles and versions; "
                                             "use to find the id before revising one.",
     "input_schema": {"type": "object", "properties": {}}},
]

ARTIFACT_LABELS = {"artifact_make": "Page bana raha hoon", "artifact_list": "Aapke pages dekh raha hoon"}


async def artifact_make(ctx: Ctx, request, artifact_id=None, data=None, _wait=None, **_):
    try:
        r = await artifacts.make(ctx.tenant_id, ctx.conversation_id, str(request or ""), artifact_id=str(artifact_id or ""),
                                 data=str(data or "")[:60000], wait=150 if _wait is None else float(_wait))
    except (ValueError, RuntimeError) as e:
        raise ToolError(str(e))
    if r["status"] == "building":
        r["say"] = ("It's being built; the card in the chat turns into an Open button when ready. Tell the user in one "
                    "line what you're making.")
    elif r["status"] == "ready":
        r["say"] = "Ready: an Open button is on the card in the chat. Tell the user what it does in one or two lines."
    else:
        r["say"] = "It could not be built this time; offer to try again."
    return r


async def artifact_list(ctx: Ctx, **_):
    return {"artifacts": artifacts.list_for(ctx.tenant_id, limit=20)}


ARTIFACT_HANDLERS = {"artifact_make": artifact_make, "artifact_list": artifact_list}
