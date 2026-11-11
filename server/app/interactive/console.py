"""v0.747 HOOLA INTERACTIVE - the console page's own doors (/api/interactive/studio/*). Thin: the work is studio.py
(projects, scenes, the make job) over frames.do_avatar_film (voice -> words -> HyperFrames)."""
from __future__ import annotations

from pathlib import Path
from typing import Callable

from fastapi import APIRouter, Body, Depends, HTTPException
from fastapi.responses import FileResponse

from . import hub as H
from . import studio as S


def make_router(require_key: Callable, current_tenant: Callable) -> APIRouter:
    r = APIRouter(prefix="/api/interactive/studio", dependencies=[Depends(require_key)])

    def on() -> None:
        from ..config import get_settings
        if not get_settings().interactive_page:
            raise HTTPException(403, "Hoola Interactive is switched off on this server.")

    def wrap(fn, *a, code: int = 422, **kw):
        try:
            return fn(*a, **kw)
        except S.StudioError as e:
            raise HTTPException(404 if "not found" in str(e) else code, str(e))

    @r.get("/status")
    async def status(tenant: str = Depends(current_tenant)):
        from ..config import get_settings
        return {"enabled": bool(get_settings().interactive_page), **S.readiness(), "running": S.running_for(tenant)}

    @r.get("/list")
    async def listing(tenant: str = Depends(current_tenant)):
        on()
        return S.listing(tenant)

    @r.post("/draft")
    def draft(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        """Her one line -> the film as scenes (one brain call). Runs in the thread pool: it can take a little while."""
        on()
        b = dict(body or {})
        if not b.get("brand"):                              # v0.772: her Brand page is the default for every new video
            b["brand"] = (S._load(tenant).get("brand") or {}).get("name", "")
        return wrap(S.draft, tenant, str(b.get("ask") or ""), shape=str(b.get("shape") or "talking_head"),
                    lang=str(b.get("lang") or "hi"), aspect=str(b.get("aspect") or ""),
                    seconds=int(b.get("seconds") or 30), avatar_id=str(b.get("avatar_id") or ""),
                    brand=str(b.get("brand") or ""), code=502)

    @r.get("/project")
    async def get_project(id: str = "", tenant: str = Depends(current_tenant)):
        on()
        p = wrap(S.project, tenant, id)
        return {**p, "problems": S.problems(p)}

    @r.put("/project")
    async def put_project(id: str = "", body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        on()
        p = wrap(S.save, tenant, id, dict(body or {}))
        return {**p, "problems": S.problems(p)}

    @r.delete("/project")
    async def del_project(id: str = "", tenant: str = Depends(current_tenant)):
        on()
        return {"ok": wrap(S.remove, tenant, id, code=409)}

    @r.post("/make")
    async def make(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        on()
        b = dict(body or {})
        return wrap(S.make, tenant, str(b.get("id") or ""), silent=bool(b.get("silent")), code=409)

    @r.get("/progress")
    async def progress(id: str = "", tenant: str = Depends(current_tenant)):
        on()
        return wrap(S.job_view, tenant, id)

    @r.post("/stop")
    async def stop(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        on()
        return {"ok": wrap(S.stop, tenant, str((body or {}).get("id") or ""), code=409)}

    @r.get("/video")
    async def video(id: str = "", download: int = 0, tenant: str = Depends(current_tenant)):
        on()
        p = wrap(S.project, tenant, id)
        f = S.video_path(tenant, id)
        if p["status"] != "ready" or not f.is_file():
            raise HTTPException(404, "This video is not ready.")
        name = "".join(c if c.isalnum() or c in " ._-" else "_" for c in p["title"])[:60].strip() or "hoola-video"
        return FileResponse(str(f), media_type="video/mp4", filename=f"{name}.mp4" if download else None)

    @r.get("/photo")
    async def photo(id: str = "", tenant: str = Depends(current_tenant)):
        on()
        f = S.photo_path(tenant, id)
        if f is None:
            raise HTTPException(404, "This avatar was not found.")
        return FileResponse(str(f))

    @r.post("/avatar")
    async def avatar(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        """A photo avatar from a file she just uploaded through the chat file lane (owner-checked here)."""
        on()
        from ..mailbox import service as ms
        b = dict(body or {})
        try:
            row = ms._file_row(tenant, str(b.get("file_id") or ""))
        except Exception:
            raise HTTPException(404, "That photo was not found - upload it again.")
        if not Path(row.stored_path).is_file():
            raise HTTPException(404, "That photo was not found - upload it again.")
        return wrap(S.add_avatar, tenant, str(b.get("name") or ""), row.stored_path, lang=str(b.get("lang") or "hi"),
                    consent=bool(b.get("consent")), filename=row.name)

    @r.delete("/avatar")
    async def del_avatar(id: str = "", tenant: str = Depends(current_tenant)):
        on()
        return {"ok": wrap(S.remove_avatar, tenant, id)}

    return r


def make_hub_router(require_key: Callable, current_tenant: Callable) -> APIRouter:
    """v0.772 the twelve pages' doors (/api/interactive/hub/*). Thin: the work and the rules are hub.py."""
    r = APIRouter(prefix="/api/interactive/hub", dependencies=[Depends(require_key)])

    def on() -> None:
        from ..config import get_settings
        if not get_settings().interactive_page:
            raise HTTPException(403, "Hoola Interactive is switched off on this server.")

    def wrap(fn, *a, code: int = 422, **kw):
        try:
            return fn(*a, **kw)
        except S.StudioError as e:
            raise HTTPException(404 if "not found" in str(e) else code, str(e))

    def view(p: dict) -> dict:
        return {**p, "problems": S.problems(p)}

    @r.get("/overview")
    async def overview(tenant: str = Depends(current_tenant)):
        on()
        return H.overview(tenant)

    @r.put("/brand")
    async def brand(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        on()
        return wrap(H.brand_set, tenant, dict(body or {}))

    @r.post("/glossary")
    async def glossary_add(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        on()
        b = dict(body or {})
        return wrap(H.glossary_add, tenant, str(b.get("term") or ""), mode=str(b.get("mode") or "keep"),
                    to=str(b.get("to") or ""), lang=str(b.get("lang") or ""))

    @r.delete("/glossary")
    async def glossary_del(id: str = "", tenant: str = Depends(current_tenant)):
        on()
        return H.glossary_remove(tenant, id)

    @r.post("/template")
    async def template_save(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        on()
        b = dict(body or {})
        return wrap(H.template_save, tenant, str(b.get("project") or ""), str(b.get("name") or ""))

    @r.delete("/template")
    async def template_del(id: str = "", tenant: str = Depends(current_tenant)):
        on()
        return {"ok": wrap(H.template_remove, tenant, id)}

    @r.post("/template/use")
    async def template_use(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        on()
        b = dict(body or {})
        return view(wrap(H.template_use, tenant, str(b.get("id") or ""), dict(b.get("values") or {}),
                         lang=str(b.get("lang") or "hi"), avatar_id=str(b.get("avatar_id") or ""), title=str(b.get("title") or "")))

    @r.post("/batch")
    async def batch(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        on()
        b = dict(body or {})
        return {"made": wrap(H.batch, tenant, list(b.get("scripts") or []), shape=str(b.get("shape") or "talking_head"),
                             lang=str(b.get("lang") or "hi"), avatar_id=str(b.get("avatar_id") or ""))}

    @r.post("/personalise")
    async def personalise(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        on()
        b = dict(body or {})
        return {"made": wrap(H.personalise, tenant, str(b.get("project") or ""), list(b.get("names") or []))}

    @r.post("/duplicate")
    async def duplicate(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        on()
        return view(wrap(H.duplicate, tenant, str((body or {}).get("id") or "")))

    @r.post("/trash")
    async def trash(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        on()
        return {"ok": wrap(H.trash, tenant, str((body or {}).get("id") or ""), code=409)}

    @r.post("/restore")
    async def restore(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        on()
        return view(wrap(H.restore, tenant, str((body or {}).get("id") or "")))

    @r.post("/trash/empty")
    async def empty(tenant: str = Depends(current_tenant)):
        on()
        return {"removed": H.empty_trash(tenant)}

    @r.post("/translate")
    def translate(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        """One model call for the words, then the number + glossary checks. Thread pool: it can take a little while."""
        on()
        b = dict(body or {})
        return view(wrap(H.translate, tenant, str(b.get("id") or ""), str(b.get("lang") or ""), code=502))

    @r.post("/brain")
    async def brain(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        on()
        return wrap(H.brain_save, tenant, dict(body or {}))

    @r.delete("/brain")
    async def brain_del(id: str = "", tenant: str = Depends(current_tenant)):
        on()
        return {"ok": H.brain_remove(tenant, id)}

    @r.get("/voice")
    def voice(lang: str = "hi", tenant: str = Depends(current_tenant)):
        """A short line in the Hoola voice. Says plainly when the voice engine is not connected."""
        on()
        from fastapi.responses import Response
        from . import lab
        try:
            return Response(H.voice_sample(lang), media_type="audio/wav")
        except lab.LabError as e:
            raise HTTPException(503, str(e))

    return r
