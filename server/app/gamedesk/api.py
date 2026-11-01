"""HTTP routes for the Game Desk (Employees > Game Developer > desk, console + app).

GET    /api/game                       health (Godot, Web templates, network lock) + her games
POST   /api/game                       {brief, orientation?, conversation_id?}  -> a design doc first
GET    /api/game/{id}                  one game (design, versions, checks, files)
POST   /api/game/{id}/approve          {feedback?}  no feedback = build it; feedback = change the design first
POST   /api/game/{id}/change           {words}      a new version from the current code
POST   /api/game/{id}/cancel
DELETE /api/game/{id}
GET    /api/game/{id}/source           her whole Godot project as a zip (opens in the Godot editor)
GET    /play/{token}/{path}            public but secret: the playable build + screenshots (strict CSP, gzip)"""
from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Request
from fastapi.responses import FileResponse, RedirectResponse, Response

# 'unsafe-eval' is for Hoola's own probe (Godot's JavaScriptBridge.eval reports fps / readiness); the game's code can
# never reach the page (guard.py refuses JavaScriptBridge), and connect-src 'self' keeps every game off the network.
CSP = ("default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval' 'wasm-unsafe-eval'; style-src 'self' 'unsafe-inline'; "
       "img-src 'self' data: blob:; media-src 'self' blob:; connect-src 'self'; worker-src 'self' blob:; "
       "font-src 'self' data:; frame-ancestors 'self'; base-uri 'none'; form-action 'none'")


def make_router(require_key, current_tenant) -> APIRouter:
    from . import service

    r = APIRouter()

    async def call(fn, *a, **kw):
        try:
            return await asyncio.to_thread(fn, *a, **kw)
        except service.GameError as e:
            raise HTTPException(400, str(e))

    def _b(body: Any) -> dict:
        return body if isinstance(body, dict) else {}

    @r.get("/api/game", dependencies=[Depends(require_key)])
    async def home(tenant: str = Depends(current_tenant)):
        return {"health": service.health(), "games": await call(service.projects, tenant),
                "orientations": list(service.ORIENTATIONS)}

    @r.post("/api/game", dependencies=[Depends(require_key)])
    async def make(body: Any = Body(default=None), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await call(service.start, tenant, str(b.get("conversation_id") or ""), str(b.get("brief") or ""),
                          str(b.get("orientation") or "portrait"))

    @r.get("/api/game/{pid}", dependencies=[Depends(require_key)])
    async def one(pid: str, tenant: str = Depends(current_tenant)):
        return await call(service.get, tenant, pid)

    @r.post("/api/game/{pid}/approve", dependencies=[Depends(require_key)])
    async def ok(pid: str, body: Any = Body(default=None), tenant: str = Depends(current_tenant)):
        return await call(service.approve, tenant, pid, str(_b(body).get("feedback") or ""))

    @r.post("/api/game/{pid}/change", dependencies=[Depends(require_key)])
    async def chg(pid: str, body: Any = Body(default=None), tenant: str = Depends(current_tenant)):
        return await call(service.change, tenant, pid, str(_b(body).get("words") or ""))

    @r.post("/api/game/{pid}/cancel", dependencies=[Depends(require_key)])
    async def stop(pid: str, tenant: str = Depends(current_tenant)):
        return await call(service.cancel, tenant, pid)

    @r.delete("/api/game/{pid}", dependencies=[Depends(require_key)])
    async def drop(pid: str, tenant: str = Depends(current_tenant)):
        await call(service.delete, tenant, pid)
        return {"ok": True}

    @r.get("/api/game/{pid}/source", dependencies=[Depends(require_key)])
    async def source(pid: str, tenant: str = Depends(current_tenant)):
        data, name = await call(service.source_zip, tenant, pid)
        return Response(data, media_type="application/zip",
                        headers={"Content-Disposition": f'attachment; filename="{name}"', "Cache-Control": "private, no-store"})

    @r.get("/play/{token}")
    def play_root(token: str):
        return RedirectResponse(f"/play/{token}/", status_code=307)

    @r.get("/play/{token}/{path:path}")
    def play(token: str, request: Request, path: str = ""):
        p, media = service.play_file(token, path)
        if p is None:
            raise HTTPException(404, "game link purana / galat hai")
        headers = {"Content-Security-Policy": CSP, "X-Content-Type-Options": "nosniff", "Referrer-Policy": "no-referrer",
                   "Cache-Control": "no-cache" if p.suffix == ".html" else "public, max-age=3600",
                   "X-Robots-Tag": "noindex",
                   # the console shows the game in a sandboxed frame (opaque origin, no access to Hoola's login), so the
                   # engine's own fetches of .wasm / .pck need CORS; the files are public behind the secret token anyway
                   "Access-Control-Allow-Origin": "*", "Cross-Origin-Resource-Policy": "cross-origin"}
        gz = p.with_name(p.name + ".gz")
        if p.suffix in (".wasm", ".pck", ".js") and gz.is_file() and "gzip" in request.headers.get("accept-encoding", ""):
            headers.update({"Content-Encoding": "gzip", "Vary": "Accept-Encoding"})
            return FileResponse(gz, media_type=media, headers=headers)
        return FileResponse(p, media_type=media, headers=headers)

    return r
