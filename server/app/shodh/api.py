"""HTTP routes of the Shodh Sahayak (/api/shodh/*), key-protected. The optional Semantic Scholar key is typed ONLY here
(PUT /key) and never returned."""
from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException


def make_router(require_key, current_tenant) -> APIRouter:
    from . import service as SH

    r = APIRouter(prefix="/api/shodh", dependencies=[Depends(require_key)])

    async def run(fn, *a, **k):
        try:
            return await asyncio.to_thread(fn, *a, **k)
        except (SH.ShodhError, ValueError) as e:
            raise HTTPException(400, str(e))

    def _b(body) -> dict[str, Any]:
        return dict(body or {})

    @r.get("")
    async def overview(tenant: str = Depends(current_tenant)):
        return await run(lambda: {**SH.day(tenant), "never": SH.NEVER, "ai_note": SH.AI_NOTE})

    @r.put("/settings")
    async def put_settings(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(SH.save_settings, tenant, "owner", b.get("email"), b.get("style"))

    @r.put("/key")
    async def put_key(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(SH.set_s2_key, tenant, str(_b(body).get("key") or ""))

    @r.post("/projects")
    async def post_project(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(SH.new_project, tenant, str(b.get("title") or ""), str(b.get("question") or ""), str(b.get("field") or ""))

    @r.get("/projects/{ref}/papers")
    async def get_papers(ref: str, status: str = "", q: str = "", tenant: str = Depends(current_tenant)):
        return await run(SH.papers, tenant, ref, status, q)

    @r.post("/projects/{ref}/search")
    async def post_search(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(SH.search, tenant, ref, str(b.get("query") or ""), b.get("sources"), int(b.get("year_from") or 0),
                         int(b.get("limit") or 20))

    @r.post("/projects/{ref}/doi")
    async def post_doi(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(SH.add_doi, tenant, ref, str(_b(body).get("doi") or ""))

    @r.post("/projects/{ref}/screen")
    async def post_screen(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(SH.screen, tenant, ref, list(b.get("refs") or []), bool(b.get("include", True)), str(b.get("reason") or ""))

    @r.post("/projects/{ref}/summarize")
    async def post_sum(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(SH.summarize, tenant, ref, list(_b(body).get("refs") or []))

    @r.get("/projects/{ref}/matrix")
    async def get_matrix(ref: str, tenant: str = Depends(current_tenant)):
        return await run(SH.matrix, tenant, ref)

    @r.post("/projects/{ref}/gaps")
    async def post_gaps(ref: str, tenant: str = Depends(current_tenant)):
        return await run(SH.gaps, tenant, ref)

    @r.post("/projects/{ref}/references")
    async def post_refs(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(SH.references, tenant, ref, str(b.get("style") or ""), str(b.get("format") or "text"))

    return r
