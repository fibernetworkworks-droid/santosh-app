"""HTTP routes for the 3D Studio (Profile > "<name> · 3D Studio" in the app).

GET    /api/blender3d                    health (Blender installed? network locked?) + her projects
POST   /api/blender3d                    {brief, photos?, exports?, views?, quality?, aspect?, turntable?, print?, style?}
GET    /api/blender3d/{id}               one project (versions, objects, the script)
POST   /api/blender3d/{id}/change        {words?, exports?, views?, quality?, turntable?, aspect?}  (no words = same model, new
                                         renders / files)
POST   /api/blender3d/{id}/cancel
DELETE /api/blender3d/{id}
GET    /api/blender3d/files/{id}/{v}/{name}?exp&sig   (public, signed: renders / turntable / exports for the app)"""
from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException
from fastapi.responses import FileResponse


def make_router(require_key, current_tenant) -> APIRouter:
    from . import guard, service

    r = APIRouter()

    async def call(fn, *a, **kw):
        try:
            return await asyncio.to_thread(fn, *a, **kw)
        except guard.GuardError as e:
            raise HTTPException(400, "Script mein dikkat: " + "; ".join(e.problems[:6]))
        except service.B3Error as e:
            raise HTTPException(400, str(e))

    def _b(body: Any) -> dict:
        return body if isinstance(body, dict) else {}

    @r.get("/api/blender3d", dependencies=[Depends(require_key)])
    async def home(tenant: str = Depends(current_tenant)):
        return {"health": service.health(), "projects": await call(service.projects, tenant),
                "formats": list(service.FORMATS), "views": list(service.VIEWS), "aspects": list(service.ASPECTS)}

    @r.post("/api/blender3d", dependencies=[Depends(require_key)])
    async def make(body: Any = Body(default=None), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await call(service.start, tenant, str(b.get("conversation_id") or ""), str(b.get("brief") or ""), b)

    @r.get("/api/blender3d/files/{pid}/{v}/{name}")
    def files(pid: str, v: str, name: str, exp: int = 0, sig: str = ""):
        p = service.file_path(pid, f"{v}/{name}", exp, sig)
        if p is None:
            raise HTTPException(404, "link purana / galat hai")
        media = {"png": "image/png", "mp4": "video/mp4", "glb": "model/gltf-binary", "stl": "model/stl",
                 "obj": "text/plain", "fbx": "application/octet-stream", "usdz": "model/vnd.usdz+zip",
                 "blend": "application/octet-stream"}.get(p.suffix.lstrip(".").lower(), "application/octet-stream")
        return FileResponse(p, media_type=media, filename=p.name,
                            headers={"Cache-Control": "private, max-age=86400", "X-Content-Type-Options": "nosniff"})

    @r.get("/api/blender3d/{pid}", dependencies=[Depends(require_key)])
    async def one(pid: str, tenant: str = Depends(current_tenant)):
        return await call(service.get, tenant, pid)

    @r.post("/api/blender3d/{pid}/change", dependencies=[Depends(require_key)])
    async def change(pid: str, body: Any = Body(default=None), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await call(service.change, tenant, pid, str(b.get("words") or ""), b)

    @r.post("/api/blender3d/{pid}/cancel", dependencies=[Depends(require_key)])
    async def cancel(pid: str, tenant: str = Depends(current_tenant)):
        return await call(service.cancel, tenant, pid)

    @r.delete("/api/blender3d/{pid}", dependencies=[Depends(require_key)])
    async def delete(pid: str, tenant: str = Depends(current_tenant)):
        await call(service.delete, tenant, pid)
        return {"ok": True}

    return r
