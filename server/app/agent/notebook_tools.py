"""Santosh Notebook tools: NotebookLM-style research notebooks (sources -> cited answers, study guides, audio)."""
from __future__ import annotations

import asyncio
from typing import Any

from ..bazar.connectors.base import ToolError as BazarError
from ..events import bus
from ..notebook import service as ns
from .tools import Ctx, ToolError

NB = {"type": "string", "description": "The notebook: its name or id"}
SOURCE = {"type": "object", "description": (
    "ONE source: {url} (web page, PDF link or YouTube), {text, title} (notes / pasted text), {file_id} (a file from "
    "the PC via pc_send_to_phone or one the user added), {email_id} (an email) or {email_id, attachment_id} (its "
    "attachment), {drive} (a Google Drive file name / link / id), {sheet} (a Google Sheet name / link)."),
    "properties": {"url": {"type": "string"}, "text": {"type": "string"}, "title": {"type": "string"},
                   "file_id": {"type": "string"}, "email_id": {"type": "string"}, "attachment_id": {"type": "string"},
                   "drive": {"type": "string"}, "sheet": {"type": "string"}, "tab": {"type": "string"}}}

NOTEBOOK_TOOLS = [
    {"name": "notebook_create", "description": (
        "Create a Santosh Notebook (like NotebookLM) for a topic, optionally adding sources at once. Use when the user "
        "wants to study / research / understand a set of documents, links or notes together."),
     "input_schema": {"type": "object", "properties": {
         "title": {"type": "string"}, "emoji": {"type": "string"}, "sources": {"type": "array", "items": SOURCE}},
         "required": ["title"]}},
    {"name": "notebook_list", "description": "The user's notebooks.",
     "input_schema": {"type": "object", "properties": {}}},
    {"name": "notebook_open", "description": "A notebook's sources (numbered), saved notes and audio overviews.",
     "input_schema": {"type": "object", "properties": {"notebook": NB}, "required": ["notebook"]}},
    {"name": "notebook_add", "description": "Add sources to a notebook (up to 50 per notebook).",
     "input_schema": {"type": "object", "properties": {"notebook": NB, "sources": {"type": "array", "items": SOURCE}},
                      "required": ["notebook", "sources"]}},
    {"name": "notebook_remove_source", "description": "Remove one source (number, id or name) from a notebook.",
     "input_schema": {"type": "object", "properties": {"notebook": NB, "source": {"type": "string"}},
                      "required": ["notebook", "source"]}},
    {"name": "notebook_ask", "description": (
        "Ask a question answered ONLY from the notebook's sources, with [n] citations to exact passages. Pass the "
        "answer to the user with its citations (source names). save=true keeps it as a note."),
     "input_schema": {"type": "object", "properties": {"notebook": NB, "question": {"type": "string"},
                                                       "save": {"type": "boolean"}}, "required": ["notebook", "question"]}},
    {"name": "notebook_make", "description": (
        "Make something from all the sources and save it in the notebook: summary, study_guide, briefing, faq, "
        "timeline, mind_map, quiz, action_items. language: hi, hinglish, en, mr. focus = optional angle."),
     "input_schema": {"type": "object", "properties": {
         "notebook": NB, "kind": {"type": "string", "enum": list(ns.KINDS)},
         "language": {"type": "string", "enum": list(ns.LANGS)}, "focus": {"type": "string"}},
         "required": ["notebook", "kind"]}},
    {"name": "notebook_note", "description": "Read a saved note in full (note id from notebook_open).",
     "input_schema": {"type": "object", "properties": {"notebook": NB, "note_id": {"type": "string"}},
                      "required": ["notebook", "note_id"]}},
    {"name": "notebook_audio", "description": (
        "Make an audio overview: two hosts (Ravi and Priya) talk through the sources like a podcast. style: brief "
        "(~3 min), deep_dive (~8 min), debate. language: hinglish (default), hi, en, mr. Takes a few minutes; the user "
        "gets a notification and a play card in the chat when it's ready."),
     "input_schema": {"type": "object", "properties": {
         "notebook": NB, "style": {"type": "string", "enum": list(ns.AUDIO_STYLES)},
         "language": {"type": "string", "enum": list(ns.LANGS)}, "focus": {"type": "string"}},
         "required": ["notebook"]}},
    {"name": "notebook_delete", "description": "Delete a notebook. Shows the user a confirm card first.",
     "input_schema": {"type": "object", "properties": {"notebook": NB}, "required": ["notebook"]}},
]

NOTEBOOK_LABELS = {"notebook_create": "Notebook bana raha hoon", "notebook_list": "Notebooks dekh raha hoon",
                   "notebook_open": "Notebook khol raha hoon", "notebook_add": "Sources jod raha hoon",
                   "notebook_remove_source": "Source hata raha hoon", "notebook_ask": "Sources mein jawab dhoondh raha hoon",
                   "notebook_make": "Notebook se likh raha hoon", "notebook_note": "Note padh raha hoon",
                   "notebook_audio": "Audio overview bana raha hoon", "notebook_delete": "Delete ki manzoori le raha hoon"}


async def _t(fn, *a, **kw):
    try:
        return await asyncio.to_thread(fn, *a, **kw)
    except ns.NotebookError as e:
        raise ToolError(str(e))


async def _a(coro):
    try:
        return await coro
    except ns.NotebookError as e:
        raise ToolError(str(e))


def _card(ctx: Ctx, nb: dict, status: str, extra: dict | None = None) -> None:
    bus.publish(ctx.conversation_id, "notebook", {"id": nb["id"], "title": nb["title"], "emoji": nb.get("emoji", "📒"),
                                                  "status": status, **(extra or {})})


async def _add_all(ctx: Ctx, nb: str, sources: list) -> tuple[list, list]:
    added, failed = [], []
    for src in sources or []:
        try:
            added.append(await asyncio.to_thread(ns.add_source, ctx.tenant_id, nb, dict(src or {})))
        except ns.NotebookError as e:
            failed.append({"source": {k: v for k, v in (src or {}).items() if k != "text"}, "error": str(e)})
    return added, failed


async def notebook_create(ctx: Ctx, title, emoji="", sources=None, **_):
    nb = await _t(ns.create, ctx.tenant_id, ctx.conversation_id, str(title), str(emoji or ""))
    added, failed = await _add_all(ctx, nb["id"], sources or [])
    _card(ctx, nb, "created", {"sources": len(added)})
    return {**nb, "added": added, "failed": failed,
            "note": "Notebook is ready. Ask questions with notebook_ask, or offer a study guide / audio overview."}


async def notebook_list(ctx: Ctx, **_):
    return {"notebooks": await _t(ns.list_notebooks, ctx.tenant_id)}


async def notebook_open(ctx: Ctx, notebook, **_):
    return await _t(ns.detail, ctx.tenant_id, str(notebook))


async def notebook_add(ctx: Ctx, notebook, sources, **_):
    d = await _t(ns.detail, ctx.tenant_id, str(notebook))
    added, failed = await _add_all(ctx, d["id"], sources or [])
    if added:
        _card(ctx, d, "updated", {"sources": len(d["sources"]) + len(added)})
    return {"notebook": d["title"], "added": added, "failed": failed}


async def notebook_remove_source(ctx: Ctx, notebook, source, **_):
    return {"removed": await _t(ns.remove_source, ctx.tenant_id, str(notebook), str(source))}


async def notebook_ask(ctx: Ctx, notebook, question, save=False, **_):
    return await _a(ns.ask(ctx.tenant_id, str(notebook), str(question), bool(save)))


async def notebook_make(ctx: Ctx, notebook, kind, language="", focus="", **_):
    out = await _a(ns.make(ctx.tenant_id, str(notebook), str(kind), str(language or ""), str(focus or "")))
    d = await _t(ns.detail, ctx.tenant_id, str(notebook))
    _card(ctx, d, "note", {"note_id": out["note_id"], "note_title": out["title"], "preview": out["content"][:400]})
    return out


async def notebook_note(ctx: Ctx, notebook, note_id, **_):
    return await _t(ns.get_note, ctx.tenant_id, str(notebook), str(note_id))


async def notebook_audio(ctx: Ctx, notebook, style="deep_dive", language="hinglish", focus="", **_):
    out = await _t(ns.start_audio, ctx.tenant_id, ctx.conversation_id, str(notebook), str(language or "hinglish"),
                   str(style or "deep_dive"), str(focus or ""))
    ns.launch_audio(out["audio_id"])
    return {**out, "status": "making", "note": "Takes 2-5 minutes. The user is notified with a play card when ready."}


async def notebook_delete(ctx: Ctx, notebook, **_):
    from ..bazar import service
    try:
        out = await asyncio.to_thread(service.run, ctx.tenant_id, ctx.conversation_id, "santosh-notebook",
                                      "confirm_delete", {"notebook": str(notebook)})
    except BazarError as e:
        raise ToolError(str(e))
    return {k: v for k, v in out.items() if k in ("needs_approval", "approval_id", "card", "say")} | {"status": "needs_approval"}


NOTEBOOK_HANDLERS = {"notebook_create": notebook_create, "notebook_list": notebook_list, "notebook_open": notebook_open,
                     "notebook_add": notebook_add, "notebook_remove_source": notebook_remove_source,
                     "notebook_ask": notebook_ask, "notebook_make": notebook_make, "notebook_note": notebook_note,
                     "notebook_audio": notebook_audio, "notebook_delete": notebook_delete}
