"""/api/dod/* - the Hoola DOD page's API. Tenant-scoped by the console sign-in. Her taps only: give a task, tell it
something, answer its question, stop it. Mounted with app.include_router(make_router(require_key, current_tenant))."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException
from fastapi.responses import FileResponse

from . import gateway as GW
from . import service as S
from .looks import all_looks, file_of


def make_router(require_key, current_tenant) -> APIRouter:
    r = APIRouter(prefix="/api/dod")
    auth = [Depends(require_key)]

    @r.get("/look/{name}")
    def look(name: str):
        """The 200 looks are pre-rendered pictures with nothing private in them, so an <img> can load them."""
        p = file_of(name)
        if p is None:
            raise HTTPException(404, "No such face.")
        return FileResponse(p, media_type="image/webp", headers={"Cache-Control": "public, max-age=604800"})

    @r.get("/looks", dependencies=auth)
    def looks() -> dict[str, Any]:
        return {"looks": all_looks(), "voices": list(S.VOICES)}

    @r.get("/status", dependencies=auth)
    async def status(tenant: str = Depends(current_tenant)) -> dict[str, Any]:
        ready = GW.readiness()
        out: dict[str, Any] = {"profile": S.profile(tenant), "summary": S.summary(tenant),
                               "engine": {"ok": ready["ok"], "why": ready["why"]}}
        sp = await GW.spent(tenant)
        if sp is not None:
            out["spent"] = sp
        return out

    @r.put("/profile", dependencies=auth)
    def put_profile(body: dict = Body(...), tenant: str = Depends(current_tenant)) -> dict[str, Any]:
        try:
            return {"profile": S.save_profile(tenant, str(body.get("name") or ""), str(body.get("look") or ""),
                                              str(body.get("voice") or "warm"))}
        except ValueError as e:
            raise HTTPException(400, str(e)) from e

    @r.get("/tasks", dependencies=auth)
    def tasks(state: str = "", limit: int = 60, tenant: str = Depends(current_tenant)) -> dict[str, Any]:
        return {"tasks": S.list_tasks(tenant, state, limit)}

    @r.post("/tasks", dependencies=auth)
    async def new_task(body: dict = Body(...), tenant: str = Depends(current_tenant)) -> dict[str, Any]:
        try:
            return {"task": S.create(tenant, str(body.get("ask") or ""), str(body.get("kind") or "task"))}
        except ValueError as e:
            raise HTTPException(400, str(e)) from e

    def _guard(fn, *a):
        try:
            return fn(*a)
        except KeyError as e:
            raise HTTPException(404, "No such task.") from e
        except ValueError as e:
            raise HTTPException(409, str(e)) from e

    @r.get("/tasks/{task_id}", dependencies=auth)
    def one(task_id: str, tenant: str = Depends(current_tenant)) -> dict[str, Any]:
        return {"task": _guard(lambda: S.view(S._get(tenant, task_id)))}

    @r.post("/tasks/{task_id}/note", dependencies=auth)
    async def task_note(task_id: str, body: dict = Body(...), tenant: str = Depends(current_tenant)) -> dict[str, Any]:
        return {"task": _guard(S.note, tenant, task_id, str(body.get("text") or ""))}

    @r.post("/tasks/{task_id}/answer", dependencies=auth)
    async def task_answer(task_id: str, body: dict = Body(...), tenant: str = Depends(current_tenant)) -> dict[str, Any]:
        return {"task": _guard(S.answer, tenant, task_id, str(body.get("id") or ""), str(body.get("choice") or ""),
                               str(body.get("hash") or ""))}

    @r.post("/tasks/{task_id}/stop", dependencies=auth)
    async def task_stop(task_id: str, tenant: str = Depends(current_tenant)) -> dict[str, Any]:
        return {"task": _guard(S.stop, tenant, task_id)}

    _SHOTS: dict[str, tuple[float, bytes]] = {}

    @r.get("/tasks/{task_id}/screen", dependencies=auth)
    async def task_screen(task_id: str, tenant: str = Depends(current_tenant)):
        """What her coworker's browser shows right now (a picture; at most one fresh one every 3 s per task)."""
        import time as _t
        from fastapi.responses import Response
        t = _guard(S._get, tenant, task_id)
        if t.status not in S.OPEN:
            raise HTTPException(404, "The task has finished.")
        hit = _SHOTS.get(task_id)
        fresh = 1 if t.status == "needs_you" and '"kind": "browser"' in (t.question or "") else 3   # live while she drives
        if hit and _t.time() - hit[0] < fresh:
            img = hit[1]
        else:
            img = await GW.screenshot(tenant, f"hoola-dod-{task_id}")
            if img:
                _SHOTS[task_id] = (_t.time(), img)
        if not img:
            raise HTTPException(404, "No page open right now.")
        return Response(img, media_type="image/jpeg", headers={"Cache-Control": "no-store"})

    @r.post("/tasks/{task_id}/control", dependencies=auth)
    async def task_control(task_id: str, body: dict = Body(...), tenant: str = Depends(current_tenant)) -> dict[str, Any]:
        """v0.999.332 HER hands on the coworker's browser while it waits for her there: clicks on the live picture,
        keys and typing go to that task's page. Nothing she types is kept."""
        try:
            out = await S.control(tenant, task_id, body.get("inputs") if isinstance(body, dict) else None)
        except LookupError as e:
            raise HTTPException(404, str(e)) from None
        except ValueError as e:
            raise HTTPException(409, str(e)) from None
        _SHOTS.pop(task_id, None)   # the next look shows what her input did
        return out

    @r.get("/tasks/{task_id}/files/{name}", dependencies=auth)
    def task_file(task_id: str, name: str, tenant: str = Depends(current_tenant)):
        p = _guard(S.file_path, tenant, task_id, name)
        if p is None:
            raise HTTPException(404, "That file is no longer here.")
        return FileResponse(p, filename=p.name)

    return r
