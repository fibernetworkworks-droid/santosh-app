"""v0.357 Engineering Desk routes: her CAD projects (app key) and the signed file links (public, HMAC + expiry)."""
from __future__ import annotations

import asyncio
import mimetypes

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from . import service


class FileIn(BaseModel):
    name: str
    data: str            # base64


class StartIn(BaseModel):
    brief: str
    conversation_id: str = ""
    images: list[str] = []           # v0.362 base64 sketch / photo (max 3)
    files: list[FileIn] = []         # v0.362 her STEP / STL to modify or fit to (max 2)


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
        import base64
        import binascii
        try:
            imgs = [base64.b64decode(x.split(",", 1)[-1], validate=False) for x in body.images[:3]]
            files = [(f.name, base64.b64decode(f.data.split(",", 1)[-1], validate=False)) for f in body.files[:2]]
        except (binascii.Error, ValueError):
            raise HTTPException(400, "file sahi nahi padhi gayi")
        return await asyncio.to_thread(_do, service.start, tenant, body.conversation_id, body.brief, imgs, files)

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
        mt = {"step": "application/step", "stl": "model/stl", "py": "text/plain", "3mf": "model/3mf",
              "glb": "model/gltf-binary", "dxf": "image/vnd.dxf"}.get(name.rsplit(".", 1)[-1]) \
            or mimetypes.guess_type(name)[0] or "application/octet-stream"
        inline = name.endswith((".png", ".pdf", ".py"))
        return FileResponse(p, media_type=mt, filename=name, content_disposition_type="inline" if inline else "attachment")

    return r
