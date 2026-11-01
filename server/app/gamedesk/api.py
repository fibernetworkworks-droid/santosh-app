"""HTTP routes for the Game Desk (Employees > Game Developer > desk, console + app).

GET    /api/game                       health (Godot, Web templates, network lock) + her games
POST   /api/game                       {brief, orientation?, conversation_id?}  -> a design doc first
GET    /api/game/{id}                  one game (design, versions, checks, files)
POST   /api/game/{id}/approve          {feedback?}  no feedback = build it; feedback = change the design first
POST   /api/game/{id}/change           {words}      a new version from the current code
POST   /api/game/{id}/cancel
DELETE /api/game/{id}
GET    /api/game/{id}/source           her whole Godot project as a zip (opens in the Godot editor)
GET    /play/{token}/{path}            public but secret: the playable build + screenshots (strict CSP, gzip)

v0.386 Studio Project (long game projects):
GET    /api/gamestudio                 her projects (board counts, milestones, next tasks, last night)
POST   /api/gamestudio                 {title?, goal?, game? (G-0001) | brief?, orientation?, conversation_id?}
GET    /api/gamestudio/{id}            the whole project: tasks, milestones, decisions, nightly, versions
POST   /api/gamestudio/{id}/settings   {title, goal, auto, nightly_on, summary_on, summary_hour, status, milestones}
POST   /api/gamestudio/{id}/tasks      {title, detail?, milestone?, kind?, priority?}
POST   /api/gamestudio/{id}/plan       {words?}  Hoola proposes the next small tasks into To do
POST   /api/gamestudio/{id}/start      {task?}   build one task (the next one if none given)
POST   /api/gamestudio/{id}/task/{t}   {action: ok|back|drop|todo|edit, note?, title?, detail?, milestone?, priority?}
POST   /api/gamestudio/{id}/decide     {text, why?}
GET    /api/gamestudio/{id}/why?q=     decisions + finished tasks about q
GET    /api/gamestudio/{id}/summary    the morning summary now
POST   /api/gamestudio/{id}/nightly    build + play the live version again now
POST   /api/gamestudio/{id}/restore    {n}  an old version's code back as a new version
POST   /api/gamestudio/{id}/github     {repo?, private?}  the GitHub card (her tap sends it)"""
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

    # ------------------------------------------------------------ v0.386 Studio Project
    from . import studio as S

    @r.get("/api/gamestudio", dependencies=[Depends(require_key)])
    async def st_home(tenant: str = Depends(current_tenant)):
        return {"projects": await call(S.studios, tenant), "health": service.health(),
                "milestones": S.MILESTONES, "kinds": list(S.KINDS)}

    @r.post("/api/gamestudio", dependencies=[Depends(require_key)])
    async def st_new(body: Any = Body(default=None), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await call(S.create, tenant, str(b.get("conversation_id") or ""), str(b.get("title") or ""),
                          str(b.get("goal") or ""), str(b.get("game") or ""), str(b.get("brief") or ""),
                          str(b.get("orientation") or "portrait"))

    @r.get("/api/gamestudio/{sid}", dependencies=[Depends(require_key)])
    async def st_one(sid: str, tenant: str = Depends(current_tenant)):
        return await call(S.get, tenant, sid)

    @r.post("/api/gamestudio/{sid}/settings", dependencies=[Depends(require_key)])
    async def st_set(sid: str, body: Any = Body(default=None), tenant: str = Depends(current_tenant)):
        b = _b(body)
        keep = ("title", "goal", "auto", "nightly_on", "summary_on", "summary_hour", "status", "milestones")
        return await call(S.settings, tenant, sid, **{k: b.get(k) for k in keep if k in b})

    @r.post("/api/gamestudio/{sid}/tasks", dependencies=[Depends(require_key)])
    async def st_add(sid: str, body: Any = Body(default=None), tenant: str = Depends(current_tenant)):
        b = _b(body)
        try:
            pr = int(b.get("priority") or 2)
        except (TypeError, ValueError):
            pr = 2
        return await call(S.add_task, tenant, sid, str(b.get("title") or ""), str(b.get("detail") or ""),
                          str(b.get("milestone") or ""), str(b.get("kind") or "feature"), pr)

    @r.post("/api/gamestudio/{sid}/plan", dependencies=[Depends(require_key)])
    async def st_plan(sid: str, body: Any = Body(default=None), tenant: str = Depends(current_tenant)):
        return await call(S.plan, tenant, sid, str(_b(body).get("words") or ""))

    @r.post("/api/gamestudio/{sid}/start", dependencies=[Depends(require_key)])
    async def st_start(sid: str, body: Any = Body(default=None), tenant: str = Depends(current_tenant)):
        await call(S.start_task, tenant, sid, str(_b(body).get("task") or ""))
        return await call(S.get, tenant, sid)

    @r.post("/api/gamestudio/{sid}/task/{tid}", dependencies=[Depends(require_key)])
    async def st_task(sid: str, tid: str, body: Any = Body(default=None), tenant: str = Depends(current_tenant)):
        b = _b(body)
        a = str(b.get("action") or "")
        note = str(b.get("note") or "")
        if a == "ok":
            return (await call(S.approve_task, tenant, sid, tid, note))["studio"]
        if a == "back":
            return await call(S.reject_task, tenant, sid, tid, note)
        if a in ("drop", "todo"):
            await call(S.edit_task, tenant, sid, tid, status="dropped" if a == "drop" else "todo")
        elif a == "edit":
            await call(S.edit_task, tenant, sid, tid, title=b.get("title"), detail=b.get("detail"),
                       milestone=b.get("milestone"), priority=b.get("priority"))
        else:
            raise HTTPException(400, "action = ok | back | drop | todo | edit")
        return await call(S.get, tenant, sid)

    @r.post("/api/gamestudio/{sid}/decide", dependencies=[Depends(require_key)])
    async def st_decide(sid: str, body: Any = Body(default=None), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await call(S.decide, tenant, sid, str(b.get("text") or ""), str(b.get("why") or ""))

    @r.get("/api/gamestudio/{sid}/why", dependencies=[Depends(require_key)])
    async def st_why(sid: str, q: str = "", tenant: str = Depends(current_tenant)):
        return await call(S.why, tenant, sid, q)

    @r.get("/api/gamestudio/{sid}/summary", dependencies=[Depends(require_key)])
    async def st_summary(sid: str, tenant: str = Depends(current_tenant)):
        return {"text": await call(S.summary, tenant, sid)}

    @r.post("/api/gamestudio/{sid}/nightly", dependencies=[Depends(require_key)])
    async def st_night(sid: str, tenant: str = Depends(current_tenant)):
        return await call(S.nightly, tenant, sid)

    @r.post("/api/gamestudio/{sid}/restore", dependencies=[Depends(require_key)])
    async def st_restore(sid: str, body: Any = Body(default=None), tenant: str = Depends(current_tenant)):
        try:
            n = int(_b(body).get("n") or 0)
        except (TypeError, ValueError):
            n = 0
        return await call(S.restore, tenant, sid, n)

    @r.post("/api/gamestudio/{sid}/github", dependencies=[Depends(require_key)])
    async def st_github(sid: str, body: Any = Body(default=None), tenant: str = Depends(current_tenant)):
        from ..site.github import GithubError
        from . import github as GGH
        b = _b(body)
        try:
            return await call(GGH.request, tenant, sid, str(b.get("repo") or ""), b.get("private") is not False,
                              str(b.get("conversation_id") or ""))
        except GithubError as e:
            raise HTTPException(400, str(e))

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
