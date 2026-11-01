"""v0.357 Engineering Desk routes: her CAD projects (app key) and the signed file links (public, HMAC + expiry)."""
from __future__ import annotations

import asyncio
import mimetypes

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from . import service


class StartIn(BaseModel):
    brief: str
    conversation_id: str = ""


class ChangeIn(BaseModel):
    words: str


def make_router(require_key, current_tenant) -> APIRouter:
    r = APIRouter()

    def _do(fn, *a):
        try:
            return fn(*a)
        except service.EngError as e:
            raise HTTPException(400, str(e))

    @r.get("/api/eng/projects", dependencies=[Depends(require_key)])
    async def projects(tenant: str = Depends(current_tenant)):
        from ..employee import hire
        items = await asyncio.to_thread(_do, service.projects, tenant)
        return {"projects": items, "hired": hire.status(tenant, service.HIRE_KEY),
                "today": await asyncio.to_thread(service.runs_today, tenant)}

    @r.post("/api/eng/projects", dependencies=[Depends(require_key)])
    async def start(body: StartIn, tenant: str = Depends(current_tenant)):
        return await asyncio.to_thread(_do, service.start, tenant, body.conversation_id, body.brief)

    @r.get("/api/eng/projects/{pid}", dependencies=[Depends(require_key)])
    async def one(pid: str, tenant: str = Depends(current_tenant)):
        return await asyncio.to_thread(_do, service.get, tenant, pid)

    @r.post("/api/eng/projects/{pid}/change", dependencies=[Depends(require_key)])
    async def change(pid: str, body: ChangeIn, tenant: str = Depends(current_tenant)):
        return await asyncio.to_thread(_do, service.change, tenant, pid, body.words)

    @r.delete("/api/eng/projects/{pid}", dependencies=[Depends(require_key)])
    async def delete(pid: str, tenant: str = Depends(current_tenant)):
        await asyncio.to_thread(_do, service.delete, tenant, pid)
        return {"deleted": True}

    @r.get("/api/eng/files/{pid}/{v}/{name}")
    async def files(pid: str, v: str, name: str, exp: int = 0, sig: str = ""):
        p = await asyncio.to_thread(service.file_path, pid, f"{v}/{name}", exp, sig)
        if p is None:
            raise HTTPException(404, "not found")
        mt = {"step": "application/step", "stl": "model/stl", "py": "text/plain"}.get(name.rsplit(".", 1)[-1]) \
            or mimetypes.guess_type(name)[0] or "application/octet-stream"
        inline = name.endswith((".png", ".pdf", ".py"))
        return FileResponse(p, media_type=mt, filename=name, content_disposition_type="inline" if inline else "attachment")

    return r
