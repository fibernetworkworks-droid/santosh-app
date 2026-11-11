"""Santosh Artifacts tools: build or revise an interactive page for the user (see app/artifacts.py).

parity Phase 6 (`artifact`): the chat model writes the page ITSELF in the tool call - create / update (exact
old_str -> new_str) / rewrite - like Claude's artifacts. Every change is a new version; the current version's text
stays in the conversation as the tool call, so an edit is small. `artifact_make` (the separate 16k builder that
rebuilds the whole page) stays as the 'polish / studio quality' path."""
from __future__ import annotations

from .. import artifacts
from ..config import get_settings
from .tools import Ctx, ToolError

ARTIFACT_TOOLS = [
    {"name": "artifact", "description": (
        "Write a page, dashboard, chart, calculator, tracker, document or diagram YOURSELF, right in this call - it "
        "opens beside the chat as you write it (like Claude's artifacts). action=create: give title, type "
        "(html | markdown | svg | mermaid) and the COMPLETE content (html: one self-contained document, inline CSS/JS, "
        "mobile first, light + dark, data embedded, libraries only from cdnjs / jsdelivr / unpkg, no fetch(); saving "
        "via await santosh.storage.get/set(key) in try/catch - localStorage is not available). action=update: change "
        "an existing page with old_str (EXACT text from its current version, occurring once) -> new_str; several "
        "changes = edits [{old_str, new_str}]. Use update for every small change (a colour, a label, a number, one "
        "section) - never rewrite the page for it. action=rewrite: the whole new content, only for big changes. "
        "Every change is a new version (the user can go back). A card with an Open button appears in the chat. "
        "Use this for pages you write in the chat; use artifact_make only when the user asks for a polished / "
        "studio-quality page."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["create", "update", "rewrite"]},
         "title": {"type": "string", "description": "Short name (create; optional on update / rewrite)"},
         "type": {"type": "string", "enum": ["html", "markdown", "svg", "mermaid"],
                  "description": "create: what content is (default html)"},
         "content": {"type": "string", "description": "create / rewrite: the complete content"},
         "artifact_id": {"type": "string", "description": "update / rewrite: the page's id"},
         "old_str": {"type": "string", "description": "update: exact text in the current version, occurring once"},
         "new_str": {"type": "string", "description": "update: the replacement text"},
         "edits": {"type": "array", "description": "update: several replacements, applied in order (all or none)",
                   "items": {"type": "object", "properties": {"old_str": {"type": "string"},
                                                               "new_str": {"type": "string"}},
                             "required": ["old_str", "new_str"]}}},
         "required": ["action"]}},
    {"name": "artifact_make", "description": (
        "POLISH path - a separate builder writes a studio-quality page (takes 20-90 seconds, rebuilds the whole page "
        "every change). Use it only when the user asks for a polished / studio-quality / professional page; for "
        "everything you can write yourself use `artifact`. Build an interactive page the user opens full screen in the Santosh app and can share: a calculator (EMI, GST, "
        "profit, loan), a tracker or account book (milk, credit, expenses, attendance, habits, study), a checklist or "
        "planner, a chart or mini dashboard from their numbers, a quiz or flashcards, a poster/menu/price list/visiting "
        "card, a mini landing page, a simple game, a formatted document or plan. Use it whenever the user wants "
        "something to USE, KEEP, SEE or SHARE rather than just an answer ('make me a calculator', 'show a chart', "
        "'I need a tracker', 'make a poster'). Write `request` as a full brief: purpose, every detail and number the "
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

ARTIFACT_LABELS = {"artifact": "Writing the page", "artifact_make": "Building the page",
                   "artifact_list": "Looking at your pages"}


async def artifact_make(ctx: Ctx, request, artifact_id=None, data=None, _wait=None, **_):
    try:
        r = await artifacts.make(ctx.tenant_id, ctx.conversation_id, str(request or ""), artifact_id=str(artifact_id or ""),
                                 data=str(data or "")[:60000], wait=get_settings().artifact_wait_seconds if _wait is None else float(_wait))
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


async def artifact(ctx: Ctx, action=None, title=None, type=None, content=None, artifact_id=None, old_str=None,
                   new_str=None, edits=None, **_):
    """parity Phase 6: store what the chat model wrote as a new version (no builder call)."""
    if not get_settings().chat_artifact_direct:
        raise ToolError("Direct pages are switched off here; use artifact_make with a full brief instead.")
    act = str(action or "").strip().lower()
    if act == "edit":
        act = "update"
    if act == "update" and not edits and old_str is not None:
        edits = [{"old_str": old_str, "new_str": "" if new_str is None else new_str}]
    if edits is not None and not isinstance(edits, list):
        raise ToolError("edits must be a list of {old_str, new_str}.")
    try:
        r = artifacts.write(ctx.tenant_id, ctx.conversation_id, act, artifact_id=str(artifact_id or ""),
                            title=str(title or ""), kind=str(type or ""),
                            content=None if content is None else str(content), edits=edits,
                            note={"create": "Written in the chat", "update": "Edited in the chat",
                                  "rewrite": "Rewritten in the chat"}.get(act, act))
    except artifacts.EditError as e:
        raise ToolError(str(e))
    r["say"] = (f"Version {r['version']} is ready; the card in the chat has an Open button. Tell the user in one or two "
                "lines what it does (or what changed). For the next change use action=update with old_str from "
                "this version.")
    return r


async def artifact_list(ctx: Ctx, **_):
    return {"artifacts": artifacts.list_for(ctx.tenant_id, limit=20)}


ARTIFACT_HANDLERS = {"artifact": artifact, "artifact_make": artifact_make, "artifact_list": artifact_list}
