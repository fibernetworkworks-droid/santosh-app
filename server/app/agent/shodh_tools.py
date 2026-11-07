"""Shodh Sahayak tools (research assistant, Shiksha suite Phase 4). `shodh_dekho` only reads; `shodh` works.

Papers come ONLY from official open scholarly APIs (a DOI is checked against Crossref); references are built in code from
that metadata; a [P-xxx] cite that is not a project paper is removed; analysis numbers come from code run in the locked
sandbox; drafts carry an AI-assistance note; no thesis / assignment ghost-writing."""
from __future__ import annotations

import asyncio
from typing import Any

from .tools import Ctx, ToolError

SHODH_TOOLS = [
    {"name": "shodh", "description": (
        "Research assistant for a Master's / PhD researcher (Shodh Sahayak). action=project: title, question, field -> SP-001. "
        "action=search: project, query, sources [openalex, crossref, arxiv, pubmed, semantic_scholar] (default first three), "
        "year_from, limit -> real papers P-001 (official APIs only). action=doi: project, doi (checked against Crossref; a "
        "made-up DOI is refused). action=screen: project, refs [P-001], include true|false, reason. action=summarize: "
        "project, refs -> problem / method / data / findings / limitations from the abstract. action=gaps: project -> "
        "research gaps each citing its papers. action=references: project, style apa|ieee|harvard, format text|bibtex|ris -> "
        "a file (Zotero / Mendeley import). action=analyse: project, question, datasets [ds_...], file_ids [], clean -> the "
        "model writes Python, the sandbox runs it: numbers, charts, cleaned.csv and the code. action=draft: project, section "
        "literature_review|methods|results|discussion|introduction, analysis_output (results: the numbers' only source), notes, "
        "language -> a draft the researcher edits (cites only project papers; AI-assistance note). action=settings: email "
        "(contact the open APIs ask for), style. Never write a thesis / assignment for submission as the student's own work."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["project", "search", "doi", "screen", "summarize", "gaps", "references", "analyse",
                                               "draft", "settings"]},
         "project": {"type": "string"}, "title": {"type": "string"}, "question": {"type": "string"}, "field": {"type": "string"},
         "query": {"type": "string"}, "sources": {"type": "array", "items": {"type": "string"}}, "year_from": {"type": "integer"},
         "limit": {"type": "integer"}, "doi": {"type": "string"}, "refs": {"type": "array", "items": {"type": "string"}},
         "include": {"type": "boolean"}, "reason": {"type": "string"}, "style": {"type": "string"}, "format": {"type": "string"},
         "datasets": {"type": "array", "items": {"type": "string"}}, "file_ids": {"type": "array", "items": {"type": "string"}},
         "clean": {"type": "boolean"}, "section": {"type": "string"}, "analysis_output": {"type": "string"},
         "notes": {"type": "string"}, "language": {"type": "string"}, "email": {"type": "string"}},
         "required": ["action"]}},
    {"name": "shodh_dekho", "description": (
        "Read research work (nothing changes). what=day | projects | papers (project, status found|included|excluded, q) | "
        "paper (project, ref: abstract, ids, summary) | matrix (project: literature-review matrix of included papers) | rules."),
     "input_schema": {"type": "object", "properties": {
         "what": {"type": "string", "enum": ["day", "projects", "papers", "paper", "matrix", "rules"]},
         "project": {"type": "string"}, "status": {"type": "string"}, "q": {"type": "string"}, "ref": {"type": "string"}},
         "required": ["what"]}},
]
SHODH_LABELS = {"shodh": "Research mein madad kar raha hoon", "shodh_dekho": "Research project dekh raha hoon"}


def _s(v: Any) -> str:
    return "" if v is None else str(v)


def _actor(ctx: Ctx) -> str:
    a = getattr(ctx, "actor", "owner") or "owner"
    if a.startswith("customer:"):
        raise ToolError("Research assistant sirf owner / team ke liye.")
    return a


async def shodh(ctx: Ctx, action, **a: Any):
    from ..shodh import service as SH
    t, actor, conv, action, p = ctx.tenant_id, _actor(ctx), ctx.conversation_id, str(action), _s(a.get("project"))
    refs = [str(x) for x in a.get("refs") or []]
    try:
        if action == "project":
            return await asyncio.to_thread(SH.new_project, t, _s(a.get("title")), _s(a.get("question")), _s(a.get("field")), actor)
        if action == "search":
            return await asyncio.to_thread(SH.search, t, p, _s(a.get("query")), a.get("sources"), int(a.get("year_from") or 0),
                                           int(a.get("limit") or 20), actor)
        if action == "doi":
            return await asyncio.to_thread(SH.add_doi, t, p, _s(a.get("doi")), actor)
        if action == "screen":
            return await asyncio.to_thread(SH.screen, t, p, refs, a.get("include", True) is not False, _s(a.get("reason")), actor)
        if action == "summarize":
            return await asyncio.to_thread(SH.summarize, t, p, refs, actor)
        if action == "gaps":
            return await asyncio.to_thread(SH.gaps, t, p, actor)
        if action == "references":
            return await asyncio.to_thread(SH.references, t, p, _s(a.get("style")), _s(a.get("format")) or "text", conv)
        if action == "analyse":
            return await asyncio.to_thread(SH.analyse, t, p, _s(a.get("question")), a.get("datasets"), a.get("file_ids"),
                                           bool(a.get("clean")), actor, conv)
        if action == "draft":
            return await asyncio.to_thread(SH.draft, t, p, _s(a.get("section")), _s(a.get("analysis_output")), _s(a.get("notes")),
                                           _s(a.get("language")) or "English", actor)
        if action == "settings":
            return await asyncio.to_thread(SH.save_settings, t, actor, a.get("email"), a.get("style"))
    except (SH.ShodhError, ValueError) as e:
        raise ToolError(str(e))
    raise ToolError("action galat")


async def shodh_dekho(ctx: Ctx, what, **a: Any):
    from ..shodh import service as SH
    _actor(ctx)
    t, what, p = ctx.tenant_id, str(what), _s(a.get("project"))

    def go():
        if what == "day":
            return SH.day(t)
        if what == "projects":
            return {"projects": SH.projects(t)}
        if what == "papers":
            return SH.papers(t, p, _s(a.get("status")), _s(a.get("q")))
        if what == "paper":
            return SH.paper(t, p, _s(a.get("ref")))
        if what == "matrix":
            return SH.matrix(t, p)
        if what == "rules":
            return {"never": SH.NEVER, "ai_note": SH.AI_NOTE}
        raise ToolError("what galat")
    try:
        return await asyncio.to_thread(go)
    except (SH.ShodhError, ValueError) as e:
        raise ToolError(str(e))


SHODH_HANDLERS = {"shodh": shodh, "shodh_dekho": shodh_dekho}
