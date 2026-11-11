"""v0.787 HOOLA VOCAL - the page's doors (/api/vocal/*). Thin: the work and the rules are service.py."""
from __future__ import annotations

from pathlib import Path
from typing import Callable

from fastapi import APIRouter, Body, Depends, HTTPException, Response
from fastapi.responses import FileResponse

from . import service as V

MIME = {"wav": "audio/wav", "mp3": "audio/mpeg"}


def make_router(require_key: Callable, current_tenant: Callable) -> APIRouter:
    r = APIRouter(prefix="/api/vocal", dependencies=[Depends(require_key)])

    def on() -> None:
        from ..config import get_settings
        if not get_settings().vocal_page:
            raise HTTPException(403, "Hoola Vocal is switched off on this server.")

    def fail(e: Exception) -> HTTPException:
        return HTTPException(404 if "not found" in str(e) else 422, str(e))

    def run(fn, *a, **kw):
        on()
        try:
            return fn(*a, **kw)
        except V.VocalError as e:
            raise fail(e)

    async def arun(fn, *a, **kw):
        on()
        try:
            return await fn(*a, **kw)
        except V.VocalError as e:
            raise fail(e)

    def upload(tenant: str, file_id: str) -> str:
        """A file she just uploaded through the chat file lane (owner-checked there)."""
        from ..mailbox import service as ms
        try:
            row = ms._file_row(tenant, str(file_id or ""))
            if not Path(row.stored_path).is_file():
                raise FileNotFoundError
        except Exception:
            raise HTTPException(404, "That file was not found - upload it again.")
        return row.stored_path

    @r.get("/overview")
    async def overview(tenant: str = Depends(current_tenant)):
        return run(V.overview, tenant)

    @r.post("/tts")
    async def tts(b: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await arun(V.tts, tenant, b.get("text"), voice=str(b.get("voice") or ""), lang=str(b.get("lang") or "hi"),
                          style=str(b.get("style") or "friendly"), speed=b.get("speed"), rules=b.get("rules") is not False)

    @r.post("/dialogue")
    async def dialogue(b: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await arun(V.dialogue, tenant, b.get("lines"), b.get("cast"), lang=str(b.get("lang") or "hi"),
                          style=str(b.get("style") or "friendly"))

    @r.get("/voice/preview")
    async def preview(id: str, lang: str = "hi", tenant: str = Depends(current_tenant)):
        return Response(await arun(V.preview, tenant, id, lang), media_type="audio/wav", headers={"Cache-Control": "no-store"})

    @r.post("/voice/clone")
    def clone(b: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        on()
        return run(V.voice_clone, tenant, b.get("name"), upload(tenant, b.get("file_id")), b.get("consent"), lang=str(b.get("lang") or "hi"))

    @r.post("/voice/design")
    def design(b: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return run(V.voice_design, tenant, b.get("name"), b.get("description"), gender=str(b.get("gender") or ""))

    @r.delete("/voice")
    def voice_remove(id: str, tenant: str = Depends(current_tenant)):
        return run(V.voice_remove, tenant, id)

    @r.post("/rule")
    def rule(b: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return run(V.rule_add, tenant, b.get("word"), b.get("say"), lang=str(b.get("lang") or ""))

    @r.delete("/rule")
    def rule_remove(id: str, tenant: str = Depends(current_tenant)):
        return run(V.rule_remove, tenant, id)

    @r.post("/sfx")
    def sfx(b: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return run(V.sfx, tenant, str(b.get("preset") or ""), b.get("seed"))

    @r.post("/cleanup")
    def cleanup(b: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        on()
        return run(V.cleanup, tenant, upload(tenant, b.get("file_id")), name=str(b.get("name") or ""),
                   denoise=b.get("denoise") is not False, voice=b.get("voice") is not False,
                   silence=bool(b.get("silence")), level=b.get("level") is not False)

    @r.post("/music")
    async def music(b: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await arun(V.music, tenant, b.get("brief"), genre=str(b.get("genre") or ""), lang=str(b.get("lang") or "hi"),
                          vocals=str(b.get("vocals") or "instrumental"), mood=str(b.get("mood") or ""))

    @r.post("/project")
    def project(b: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return run(V.project_save, tenant, pid=str(b.get("id") or ""), title=b.get("title"), voice=str(b.get("voice") or ""),
                   lang=str(b.get("lang") or "hi"), chapters=b.get("chapters"))

    @r.delete("/project")
    def project_remove(id: str, tenant: str = Depends(current_tenant)):
        return run(V.project_remove, tenant, id)

    @r.post("/project/chapter")
    async def chapter(b: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await arun(V.chapter_make, tenant, str(b.get("id") or ""), b.get("n"))

    @r.post("/project/export")
    def export(b: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return run(V.project_export, tenant, str(b.get("id") or ""))

    @r.delete("/history")
    def history_remove(id: str, tenant: str = Depends(current_tenant)):
        return run(V.history_remove, tenant, id)

    @r.get("/audio")
    def audio(id: str, tenant: str = Depends(current_tenant)):
        f, h = run(V.audio_file, tenant, id)
        return FileResponse(f, media_type=MIME.get(h.get("ext", "wav"), "application/octet-stream"),
                            headers={"Cache-Control": "private, no-store"})

    return r
