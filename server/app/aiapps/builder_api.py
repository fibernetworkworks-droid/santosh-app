"""v0.772 HOOLA AI APPS - owner routes of part A (builder, templates, export / import).

main.py mounts this BEFORE the owner router (which has /api/aiapps/{id}), so /api/aiapps/plan, /templates and
/import are matched here first:  app.include_router(builder_api.make_router(require_key, current_tenant)).
"""
from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException


def make_router(require_key, current_tenant) -> APIRouter:
    from . import builder as B
    from . import dsl as D
    from . import templates as T
    from .store import AppError

    r = APIRouter(prefix="/api/aiapps", dependencies=[Depends(require_key)])

    async def run(fn, *a, **k):
        try:
            return await asyncio.to_thread(fn, *a, **k)
        except AppError as e:
            raise HTTPException(e.code, str(e))

    def _b(body: Any) -> dict[str, Any]:
        return dict(body) if isinstance(body, dict) else {}

    @r.post("/plan")
    async def plan(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(B.plan, tenant, _b(body).get("words", ""))

    @r.get("/templates")
    async def templates(q: str = ""):
        return await run(T.list, q)

    @r.post("/templates/{key}/trial")
    async def trial(key: str, body: dict = Body(default={})):
        b = _b(body)
        inputs = b.get("inputs") if isinstance(b.get("inputs"), dict) else None
        return await run(T.trial, key, str(b.get("text") or ""), inputs)

    @r.post("/templates/{key}/use")
    async def use(key: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(T.use, tenant, key, str(_b(body).get("name") or ""))

    @r.get("/{app_id}/export")
    async def export(app_id: str, tenant: str = Depends(current_tenant)):
        return await run(D.export, tenant, app_id)

    @r.post("/import")
    async def import_check(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(D.import_check, tenant, _b(body).get("file"))

    @r.post("/import/confirm")
    async def import_confirm(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(D.import_confirm, tenant, b.get("file"), str(b.get("name") or ""))

    return r
