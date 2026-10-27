"""Hoola Notebook tools (NotebookLM / Gemini Notebook for India): sources -> cited chat with history, source guides,
Discover (fast web results / deep research), notes, and the Studio: audio + video overviews, slide decks, infographics,
mind maps, reports, flashcards, quizzes, data tables."""
from __future__ import annotations

import asyncio
from typing import Any

from ..bazar.connectors.base import ToolError as BazarError
from ..events import bus
from ..notebook import service as ns
from ..notebook import studio
from .tools import Ctx, ToolError

NB = {"type": "string", "description": "The notebook: its name or id"}
SOURCE = {"type": "object", "description": (
    "ONE source: {url} (web page, PDF link or YouTube), {text, title} (notes / pasted text), {file_id} (a file the user "
    "sent: PDF / Word / PPT / Excel / EPUB / photo / audio recording all work), {email_id} or {email_id, attachment_id}, "
    "{drive} (a Google Drive file name / link / id), {sheet} (a Google Sheet name / link)."),
    "properties": {"url": {"type": "string"}, "text": {"type": "string"}, "title": {"type": "string"},
                   "file_id": {"type": "string"}, "email_id": {"type": "string"}, "attachment_id": {"type": "string"},
                   "drive": {"type": "string"}, "sheet": {"type": "string"}, "tab": {"type": "string"}}}
LANG = {"type": "string", "description": "Output language code: hinglish, hi, en, mr, bn, ta, te, kn, ml, gu, pa, or, ur, "
                                         "as, ne, es, fr, de, ar, ja, zh ... (default: the sources' / user's language)"}

NOTEBOOK_TOOLS = [
    {"name": "notebook_create", "description": (
        "Create a Hoola Notebook (Hoola's NotebookLM) for a topic, optionally adding sources at once. Use when the user "
        "wants to study / research / understand a set of documents, links, videos, recordings or notes together."),
     "input_schema": {"type": "object", "properties": {
         "title": {"type": "string"}, "emoji": {"type": "string"}, "sources": {"type": "array", "items": SOURCE}},
         "required": ["title"]}},
    {"name": "notebook_list", "description": "The user's notebooks.",
     "input_schema": {"type": "object", "properties": {}}},
    {"name": "notebook_open", "description": "A notebook: its sources (numbered, on/off), notes, Studio items and chat settings.",
     "input_schema": {"type": "object", "properties": {"notebook": NB}, "required": ["notebook"]}},
    {"name": "notebook_add", "description": "Add sources to a notebook (up to 100 per notebook).",
     "input_schema": {"type": "object", "properties": {"notebook": NB, "sources": {"type": "array", "items": SOURCE}},
                      "required": ["notebook", "sources"]}},
    {"name": "notebook_discover", "description": (
        "Discover sources on the web for a notebook. mode=fast: web results the user can pick (add the chosen ones with "
        "notebook_add {url}); mode=deep: Deep research in the background (plans searches, reads pages, writes a cited "
        "report that is added as a source; a card arrives when done)."),
     "input_schema": {"type": "object", "properties": {"notebook": NB, "query": {"type": "string"},
                                                       "mode": {"type": "string", "enum": ["fast", "deep"]}, "language": LANG},
                      "required": ["notebook", "query"]}},
    {"name": "notebook_sources", "description": (
        "Manage sources: on / off (chat and Studio use only the ticked ones), only (just these), all_on, rename, refresh "
        "(read a web page / Drive file / Sheet again), guide (summary, key topics, questions of one source), remove."),
     "input_schema": {"type": "object", "properties": {
         "notebook": NB, "action": {"type": "string", "enum": ["on", "off", "only", "all_on", "rename", "refresh", "guide", "remove"]},
         "sources": {"type": "array", "items": {"type": "string"}, "description": "source numbers, ids or names"},
         "title": {"type": "string"}}, "required": ["notebook", "action"]}},
    {"name": "notebook_remove_source", "description": "Remove one source (number, id or name) from a notebook.",
     "input_schema": {"type": "object", "properties": {"notebook": NB, "source": {"type": "string"}},
                      "required": ["notebook", "source"]}},
    {"name": "notebook_ask", "description": (
        "Ask a question answered ONLY from the notebook's ticked sources, with [n] citations to exact passages; the "
        "notebook keeps its own chat history. Pass the answer to the user with the source names. save=true keeps it as a note."),
     "input_schema": {"type": "object", "properties": {"notebook": NB, "question": {"type": "string"},
                                                       "save": {"type": "boolean"}}, "required": ["notebook", "question"]}},
    {"name": "notebook_chat_config", "description": (
        "Configure the notebook's chat: goal default | learning (a tutor that teaches step by step) | custom (a role she "
        "describes in 'custom'), length default | shorter | longer, language (code or auto)."),
     "input_schema": {"type": "object", "properties": {
         "notebook": NB, "goal": {"type": "string", "enum": ["default", "learning", "custom"]}, "custom": {"type": "string"},
         "length": {"type": "string", "enum": ["default", "shorter", "longer"]}, "language": LANG}, "required": ["notebook"]}},
    {"name": "notebook_studio", "description": (
        "Make a Studio item from the notebook's sources, in the background (a live card arrives; the user is told when "
        "it's ready). kind: audio (format deep_dive|brief|critique|debate, length shorter|default|longer: a two-host "
        "podcast), video (format explainer|brief, style classic|whiteboard|watercolor|retro_print|heritage|paper_craft|"
        "kawaii|anime|custom + custom_style, voice female|male: a narrated video), slides (format detailed|presenter, "
        "length short|default|long, audience, style: PDF + PowerPoint), infographic (orientation landscape|portrait|square, "
        "detail concise|standard|detailed, style), mind_map, report (type briefing|study_guide|blog_post|summary|faq|"
        "timeline|action_items|custom; custom needs prompt), flashcards / quiz (count fewer|standard|more, difficulty "
        "easy|medium|hard, topic), table (columns). prompt = her extra instructions / focus. language for all."),
     "input_schema": {"type": "object", "properties": {
         "notebook": NB, "kind": {"type": "string", "enum": [k for k in studio.KIND_LABEL if k != "research"]},
         "format": {"type": "string"}, "length": {"type": "string"}, "style": {"type": "string"}, "custom_style": {"type": "string"},
         "voice": {"type": "string"}, "orientation": {"type": "string"}, "detail": {"type": "string"}, "type": {"type": "string"},
         "audience": {"type": "string"}, "count": {"type": "string"}, "difficulty": {"type": "string"}, "topic": {"type": "string"},
         "columns": {"type": "array", "items": {"type": "string"}}, "prompt": {"type": "string"}, "language": LANG},
         "required": ["notebook", "kind"]}},
    {"name": "notebook_output", "description": (
        "A Studio item: show (its content: report text, cards, quiz, table, slides, script), revise (slides: edits "
        "[{n, instruction}]), join (audio: ask the podcast hosts a question; they answer from the sources), file (make one "
        "of its files a normal file to send: name), rename, delete."),
     "input_schema": {"type": "object", "properties": {
         "notebook": NB, "output_id": {"type": "string"},
         "action": {"type": "string", "enum": ["show", "revise", "join", "file", "rename", "delete"]},
         "edits": {"type": "array", "items": {"type": "object", "properties": {"n": {"type": "integer"}, "instruction": {"type": "string"}}}},
         "question": {"type": "string"}, "name": {"type": "string"}, "title": {"type": "string"}},
         "required": ["notebook", "output_id", "action"]}},
    {"name": "notebook_note", "description": (
        "Notes in a notebook: read, create (her own note), update, delete, to_source (turn a note into a source)."),
     "input_schema": {"type": "object", "properties": {
         "notebook": NB, "action": {"type": "string", "enum": ["read", "create", "update", "delete", "to_source"]},
         "note_id": {"type": "string"}, "title": {"type": "string"}, "content": {"type": "string"}},
         "required": ["notebook"]}},
    {"name": "notebook_make", "description": (
        "Quick written item from the sources, returned at once: summary, study_guide, briefing, faq, timeline, mind_map, "
        "quiz, action_items, blog_post (prefer notebook_studio for visual / audio items)."),
     "input_schema": {"type": "object", "properties": {
         "notebook": NB, "kind": {"type": "string", "enum": list(ns.KINDS)}, "language": LANG, "focus": {"type": "string"}},
         "required": ["notebook", "kind"]}},
    {"name": "notebook_audio", "description": (
        "Audio Overview (same as notebook_studio kind=audio): two hosts talk through the sources. style deep_dive | brief | "
        "critique | debate; length shorter | default | longer."),
     "input_schema": {"type": "object", "properties": {
         "notebook": NB, "style": {"type": "string", "enum": list(ns.AUDIO_STYLES)}, "length": {"type": "string"},
         "language": LANG, "focus": {"type": "string"}}, "required": ["notebook"]}},
    {"name": "notebook_delete", "description": "Delete a notebook. Shows the user a confirm card first.",
     "input_schema": {"type": "object", "properties": {"notebook": NB}, "required": ["notebook"]}},
]

NOTEBOOK_LABELS = {"notebook_create": "Notebook bana raha hoon", "notebook_list": "Notebooks dekh raha hoon",
                   "notebook_open": "Notebook khol raha hoon", "notebook_add": "Sources jod raha hoon",
                   "notebook_discover": "Web par sources dhoondh raha hoon", "notebook_sources": "Sources sambhal raha hoon",
                   "notebook_remove_source": "Source hata raha hoon", "notebook_ask": "Sources mein jawab dhoondh raha hoon",
                   "notebook_chat_config": "Notebook chat set kar raha hoon", "notebook_studio": "Studio mein bana raha hoon",
                   "notebook_output": "Studio item dekh raha hoon", "notebook_note": "Note sambhal raha hoon",
                   "notebook_make": "Notebook se likh raha hoon", "notebook_audio": "Audio overview bana raha hoon",
                   "notebook_delete": "Delete ki manzoori le raha hoon"}


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
            "note": "Notebook is ready. Ask questions with notebook_ask, or offer Studio items (audio / video overview, "
                    "slides, mind map, flashcards, quiz, infographic, report, data table)."}


async def notebook_list(ctx: Ctx, **_):
    return {"notebooks": await _t(ns.list_notebooks, ctx.tenant_id)}


def _brief(d: dict) -> dict:
    """notebook_open for the model: no full note bodies / source texts."""
    return {"id": d["id"], "title": d["title"], "sources": d["sources"],
            "notes": [{k: n[k] for k in ("id", "kind", "title", "preview", "created")} for n in d["notes"]],
            "studio": [{k: o[k] for k in ("id", "kind", "title", "status", "stage", "error", "seconds", "count")} for o in d["outputs"]],
            "chat_config": d["chat_config"], "overview": (d.get("guide") or {}).get("overview", "")}


async def notebook_open(ctx: Ctx, notebook, **_):
    return _brief(await _t(ns.detail, ctx.tenant_id, str(notebook)))


async def notebook_add(ctx: Ctx, notebook, sources, **_):
    d = await _t(ns.detail, ctx.tenant_id, str(notebook))
    added, failed = await _add_all(ctx, d["id"], sources or [])
    if added:
        _card(ctx, d, "updated", {"sources": len(d["sources"]) + len(added)})
    return {"notebook": d["title"], "added": added, "failed": failed}


async def notebook_discover(ctx: Ctx, notebook, query, mode="fast", language="", **_):
    if mode == "deep":
        v = await _t(studio.start, ctx.tenant_id, ctx.conversation_id, str(notebook), "research",
                     {"query": str(query), "language": str(language or "")})
        studio.launch(v["id"])
        return {"status": "making", "output_id": v["id"], "note": "Deep research runs in the background (a few minutes); "
                                                                  "the report is added to the notebook as a source."}
    out = await _a(ns.discover(ctx.tenant_id, str(notebook), str(query)))
    return {**out, "note": "Show her these and add the ones she picks with notebook_add {url}."}


async def notebook_sources(ctx: Ctx, notebook, action, sources=None, title="", **_):
    nb = str(notebook)
    srcs = [str(s) for s in (sources or [])]
    d = await _t(ns.detail, ctx.tenant_id, nb)

    def ids() -> list[str]:
        out = []
        for s in srcs:
            out.append(ns._pick_source(ns._sources(d["id"]), s).id)
        return out
    if action in ("on", "off", "only"):
        if not srcs:
            raise ToolError("Kaunse sources? (number, id ya naam)")
        res = await _t(lambda: ns.set_enabled(ctx.tenant_id, nb, ids(), action != "off", only=action == "only"))
        return {"sources": res["sources"]}
    if action == "all_on":
        return {"sources": (await _t(ns.set_enabled, ctx.tenant_id, nb, None, True))["sources"]}
    if not srcs:
        raise ToolError("Kaunsa source?")
    if action == "rename":
        return {"sources": (await _t(ns.rename_source, ctx.tenant_id, nb, srcs[0], str(title)))["sources"]}
    if action == "refresh":
        res = await _t(ns.refresh_source, ctx.tenant_id, nb, srcs[0])
        return {"changed": res["changed"]}
    if action == "guide":
        return await _a(ns.source_guide(ctx.tenant_id, nb, srcs[0]))
    if action == "remove":
        return {"removed": await _t(ns.remove_source, ctx.tenant_id, nb, srcs[0])}
    raise ToolError("action: on, off, only, all_on, rename, refresh, guide, remove")


async def notebook_remove_source(ctx: Ctx, notebook, source, **_):
    return {"removed": await _t(ns.remove_source, ctx.tenant_id, str(notebook), str(source))}


async def notebook_ask(ctx: Ctx, notebook, question, save=False, **_):
    out = await _a(ns.ask(ctx.tenant_id, str(notebook), str(question), bool(save)))
    return {k: v for k, v in out.items() if k != "steps"}


async def notebook_chat_config(ctx: Ctx, notebook, goal="", custom="", length="", language="", **_):
    return {"chat_config": await _t(ns.set_config, ctx.tenant_id, str(notebook), str(goal or ""), str(custom or ""),
                                    str(length or ""), str(language or ""))}


async def notebook_studio(ctx: Ctx, notebook, kind, **opts):
    opts = {k: v for k, v in opts.items() if v not in (None, "", [])}
    if "prompt" in opts and "focus" not in opts:
        opts["focus"] = opts.pop("prompt")
    v = await _t(studio.start, ctx.tenant_id, ctx.conversation_id, str(notebook), str(kind), opts)
    studio.launch(v["id"])
    wait = {"audio": "3-8 min", "video": "4-10 min", "slides": "1-3 min", "infographic": "1-2 min"}.get(kind, "under a minute")
    return {"status": "making", "output_id": v["id"], "title": v["title"],
            "note": f"Being made in the background ({wait}); a live card shows progress and she is told when it's ready. "
                    "Don't poll."}


async def notebook_output(ctx: Ctx, notebook, output_id, action="show", edits=None, question="", name="", title="", **_):
    nb, oid = str(notebook), str(output_id)
    if action == "show":
        o = await _t(studio.get, ctx.tenant_id, nb, oid)
        data = dict(o.get("data") or {})
        for k in ("spec",):
            data.pop(k, None)
        return {**{k: o[k] for k in ("id", "kind", "title", "status", "stage", "error", "seconds")}, "data": data}
    if action == "revise":
        o = await _a(studio.revise_slides(ctx.tenant_id, nb, oid, list(edits or [])))
        return {"status": o["status"], "revised": (o.get("data") or {}).get("revised")}
    if action == "join":
        return await _a(studio.join_audio(ctx.tenant_id, nb, oid, str(question)))
    if action == "file":
        return await _t(studio.share_file, ctx.tenant_id, nb, oid, str(name), ctx.conversation_id)
    if action == "rename":
        return {"title": (await _t(studio.rename_output, ctx.tenant_id, nb, oid, str(title)))["title"]}
    if action == "delete":
        return {"deleted": await _t(studio.delete_output, ctx.tenant_id, nb, oid)}
    raise ToolError("action: show, revise, join, file, rename, delete")


async def notebook_note(ctx: Ctx, notebook, action="read", note_id="", title="", content="", **_):
    nb = str(notebook)
    if action == "read":
        return await _t(ns.get_note, ctx.tenant_id, nb, str(note_id))
    if action == "create":
        return await _t(ns.note_create, ctx.tenant_id, nb, str(title or ""), str(content or ""))
    if action == "update":
        return await _t(ns.note_update, ctx.tenant_id, nb, str(note_id), str(title or ""), str(content or ""))
    if action == "delete":
        return {"deleted": await _t(ns.note_delete, ctx.tenant_id, nb, str(note_id))}
    if action == "to_source":
        return {"sources": (await _t(ns.note_to_source, ctx.tenant_id, nb, str(note_id)))["sources"]}
    raise ToolError("action: read, create, update, delete, to_source")


async def notebook_make(ctx: Ctx, notebook, kind, language="", focus="", **_):
    out = await _a(ns.make(ctx.tenant_id, str(notebook), str(kind), str(language or ""), str(focus or ""), ctx.conversation_id))
    d = await _t(ns.detail, ctx.tenant_id, str(notebook))
    _card(ctx, d, "note", {"note_id": out["note_id"], "note_title": out["title"], "preview": out["content"][:400]})
    return out


async def notebook_audio(ctx: Ctx, notebook, style="deep_dive", language="hinglish", focus="", length="default", **_):
    v = await _t(studio.start, ctx.tenant_id, ctx.conversation_id, str(notebook), "audio",
                 {"format": str(style or "deep_dive"), "language": str(language or "hinglish"), "focus": str(focus or ""),
                  "length": str(length or "default")})
    studio.launch(v["id"])
    return {"audio_id": v["id"], "output_id": v["id"], "status": "making",
            "note": "Takes 3-8 minutes. The user gets a live card and is told when it's ready."}


async def notebook_delete(ctx: Ctx, notebook, **_):
    from ..bazar import service
    try:
        out = await asyncio.to_thread(service.run, ctx.tenant_id, ctx.conversation_id, "santosh-notebook",
                                      "confirm_delete", {"notebook": str(notebook)})
    except BazarError as e:
        raise ToolError(str(e))
    return {k: v for k, v in out.items() if k in ("needs_approval", "approval_id", "card", "say")} | {"status": "needs_approval"}


NOTEBOOK_HANDLERS = {"notebook_create": notebook_create, "notebook_list": notebook_list, "notebook_open": notebook_open,
                     "notebook_add": notebook_add, "notebook_discover": notebook_discover,
                     "notebook_sources": notebook_sources, "notebook_remove_source": notebook_remove_source,
                     "notebook_ask": notebook_ask, "notebook_chat_config": notebook_chat_config,
                     "notebook_studio": notebook_studio, "notebook_output": notebook_output, "notebook_note": notebook_note,
                     "notebook_make": notebook_make, "notebook_audio": notebook_audio, "notebook_delete": notebook_delete}

_ = Any
