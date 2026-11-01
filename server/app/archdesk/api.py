"""v0.410 Architecture Desk routes (Principal Software Architect): designs, approve / change, PR reviews against the
approved design (her tap posts), signed file links (diagram SVG / PNG, design PDF / Markdown)."""
from __future__ import annotations

import asyncio
import mimetypes

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from . import service


class StartIn(BaseModel):
    brief: str = Field(max_length=service.MAX_BRIEF)
    repo: str = ""
    conversation_id: str = ""
    scale: dict = {}


class ChangeIn(BaseModel):
    words: str = Field(max_length=service.MAX_CHANGE)


class ApproveIn(BaseModel):
    watch_prs: bool | None = None


class WatchIn(BaseModel):
    watch_prs: bool


class ReviewIn(BaseModel):
    pr: int


def make_router(require_key, current_tenant) -> APIRouter:
    r = APIRouter()

    def _do(fn, *a, **kw):
        try:
            return fn(*a, **kw)
        except service.ArchError as e:
            raise HTTPException(400, str(e))

    async def call(fn, *a, **kw):
        return await asyncio.to_thread(_do, fn, *a, **kw)

    @r.get("/api/arch/projects", dependencies=[Depends(require_key)])
    async def projects(tenant: str = Depends(current_tenant)):
        from ..employee import hire
        return {"projects": await call(service.projects, tenant), "hired": hire.status(tenant, service.HIRE_KEY),
                "health": service.health()}

    @r.post("/api/arch/projects", dependencies=[Depends(require_key)])
    async def start(body: StartIn, tenant: str = Depends(current_tenant)):
        return await call(service.start, tenant, body.conversation_id, body.brief, body.repo, body.scale)

    @r.get("/api/arch/projects/{pid}", dependencies=[Depends(require_key)])
    async def one(pid: str, tenant: str = Depends(current_tenant)):
        return await call(service.get, tenant, pid)

    @r.post("/api/arch/projects/{pid}/change", dependencies=[Depends(require_key)])
    async def change(pid: str, body: ChangeIn, tenant: str = Depends(current_tenant)):
        return await call(service.change, tenant, pid, body.words)

    @r.post("/api/arch/projects/{pid}/approve", dependencies=[Depends(require_key)])
    async def approve(pid: str, body: ApproveIn | None = None, tenant: str = Depends(current_tenant)):
        return await call(service.approve, tenant, pid, body.watch_prs if body else None)

    @r.put("/api/arch/projects/{pid}/watch", dependencies=[Depends(require_key)])
    async def watch(pid: str, body: WatchIn, tenant: str = Depends(current_tenant)):
        return await call(service.settings, tenant, pid, body.watch_prs)

    @r.post("/api/arch/projects/{pid}/cancel", dependencies=[Depends(require_key)])
    async def cancel(pid: str, tenant: str = Depends(current_tenant)):
        return await call(service.cancel, tenant, pid)

    @r.delete("/api/arch/projects/{pid}", dependencies=[Depends(require_key)])
    async def delete(pid: str, tenant: str = Depends(current_tenant)):
        await call(service.delete, tenant, pid)
        return {"deleted": True}

    @r.post("/api/arch/projects/{pid}/review", dependencies=[Depends(require_key)])
    async def review(pid: str, body: ReviewIn, tenant: str = Depends(current_tenant)):
        return await call(service.review_pr, tenant, pid, body.pr)

    @r.post("/api/arch/reviews/{rid}/post", dependencies=[Depends(require_key)])
    async def post(rid: str, tenant: str = Depends(current_tenant)):
        return await call(service.post_review, tenant, rid, by_tap=True)

    @r.post("/api/arch/reviews/{rid}/discard", dependencies=[Depends(require_key)])
    async def discard(rid: str, tenant: str = Depends(current_tenant)):
        return await call(service.discard_review, tenant, rid)

    @r.get("/api/arch/files/{pid}/{v}/{name}")
    async def files(pid: str, v: str, name: str, exp: int = 0, sig: str = ""):
        p = await asyncio.to_thread(service.file_path, pid, f"{v}/{name}", exp, sig)
        if p is None:
            raise HTTPException(404, "not found")
        mt = {"svg": "image/svg+xml", "md": "text/markdown; charset=utf-8"}.get(name.rsplit(".", 1)[-1]) \
            or mimetypes.guess_type(name)[0] or "application/octet-stream"
        headers = {"Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'"} if name.endswith(".svg") else None
        return FileResponse(p, media_type=mt, filename=name, content_disposition_type="inline", headers=headers)

    return r
