"""v0.787 HOOLA VOCAL -> v0.999.89 GLOBAL - the page's doors (/api/vocal/*). Thin: the work and the rules are service.py.
The contract is docs/HOOLA_VOCAL_GLOBAL.md."""
from __future__ import annotations

from pathlib import Path
from typing import Callable

from fastapi import APIRouter, Body, Depends, HTTPException, Response
from fastapi.responses import FileResponse

from . import engines as EN
from . import service as V

MIME = {"wav": "audio/wav", "mp3": "audio/mpeg", "flac": "audio/flac", "m4b": "audio/mp4", "mp4": "video/mp4",
        "srt": "application/x-subrip"}


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

    def maybe(tenant: str, file_id) -> str:
        return upload(tenant, file_id) if file_id else ""

    # ---------------------------------------------------------------- overview, prices
    @r.get("/overview")
    async def overview(tenant: str = Depends(current_tenant)):
        return run(V.overview, tenant)

    @r.post("/quote")
    def quote(b: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        on()
        job = str(b.get("job") or "tts")
        eng = str(b.get("engine") or "")
        if not eng or eng == "auto":
            eng = "eleven" if job in ("change", "isolate", "sfx", "dub_own") else "gemini"
            if job in ("tts", "dialogue") and b.get("voice"):
                try:
                    eng = V._engine_of(V._voice(V._load(tenant), str(b["voice"])))
                except V.VocalError:
                    pass
        try:
            return EN.quote(job, chars=int(b.get("chars") or 0), seconds=float(b.get("seconds") or 0),
                            takes=int(b.get("takes") or 1), engine=eng)
        except (TypeError, ValueError):
            raise HTTPException(422, "The numbers in that question could not be read.")

    # ---------------------------------------------------------------- speech
    @r.post("/tts")
    async def tts(b: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await arun(V.tts, tenant, b.get("text"), voice=str(b.get("voice") or ""), lang=str(b.get("lang") or "auto"),
                          style=str(b.get("style") or "friendly"), speed=b.get("speed"), rules=b.get("rules") is not False,
                          takes=b.get("takes") or 1, engine=str(b.get("engine") or "auto"), expressive=b.get("expressive"),
                          chat=str(b.get("chat") or ""), fmt=str(b.get("format") or "wav"))

    @r.post("/dialogue")
    async def dialogue(b: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await arun(V.dialogue, tenant, b.get("lines"), b.get("cast"), lang=str(b.get("lang") or "auto"),
                          style=str(b.get("style") or "friendly"), chat=str(b.get("chat") or ""))

    @r.post("/podcast")
    async def podcast(b: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        on()
        try:
            title, text = V.source_text(tenant, maybe(tenant, b.get("file_id")), str(b.get("url") or ""), str(b.get("text") or ""))
            out = await V.podcast(tenant, text, minutes=b.get("minutes") or 3, hosts=b.get("hosts"), lang=str(b.get("lang") or "auto"))
        except V.VocalError as e:
            raise fail(e)
        if title and out.get("title") == "Podcast":
            out["title"] = title
        return out

    @r.get("/voice/preview")
    async def preview(id: str, lang: str = "en", tenant: str = Depends(current_tenant)):
        return Response(await arun(V.preview, tenant, id, lang), media_type="audio/wav",
                        headers={"Cache-Control": "private, max-age=86400"})

    # ---------------------------------------------------------------- her voices
    @r.get("/consent-line")
    def consent_line(lang: str = "en", tenant: str = Depends(current_tenant)):
        return run(V.consent_line, lang)

    @r.post("/voice/clone")
    def clone(b: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        on()
        return run(V.voice_clone, tenant, b.get("name"), upload(tenant, b.get("file_id")), b.get("consent"),
                   lang=str(b.get("lang") or "en"), consent_path=maybe(tenant, b.get("consent_file_id")))

    @r.post("/voice/design")
    def design(b: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        if b.get("name") and not b.get("preview"):          # the old one-step design (kept for the old page / tests)
            return run(V.voice_design, tenant, b.get("name"), b.get("description"), gender=str(b.get("gender") or ""))
        return run(V.design_preview, tenant, b.get("description"), gender=str(b.get("gender") or ""), lang=str(b.get("lang") or ""))

    @r.post("/voice/design/save")
    def design_save(b: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return run(V.design_save, tenant, str(b.get("pid") or ""), b.get("name"))

    @r.post("/voice/remix")
    def remix(b: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return run(V.voice_remix, tenant, str(b.get("base") or ""), b.get("change"), b.get("name"))

    @r.delete("/voice")
    def voice_remove(id: str, tenant: str = Depends(current_tenant)):
        return run(V.voice_remove, tenant, id)

    # ---------------------------------------------------------------- dictionary
    @r.post("/rule")
    def rule(b: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return run(V.rule_add, tenant, b.get("word"), b.get("say"), lang=str(b.get("lang") or ""))

    @r.delete("/rule")
    def rule_remove(id: str, tenant: str = Depends(current_tenant)):
        return run(V.rule_remove, tenant, id)

    # ---------------------------------------------------------------- sound tools
    @r.post("/sfx")
    def sfx(b: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        if b.get("prompt"):
            return run(V.sfx_text, tenant, b.get("prompt"), seconds=b.get("seconds") or 0, loop=bool(b.get("loop")),
                       takes=b.get("takes") or 4, chat=str(b.get("chat") or ""))
        return run(V.sfx, tenant, str(b.get("preset") or ""), b.get("seed"))

    @r.post("/cleanup")
    def cleanup(b: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        on()
        return run(V.cleanup, tenant, upload(tenant, b.get("file_id")), name=str(b.get("name") or ""),
                   denoise=b.get("denoise") is not False, voice=b.get("voice") is not False,
                   silence=bool(b.get("silence")), level=b.get("level") is not False,
                   people=bool(b.get("people")), music=bool(b.get("music")))

    @r.post("/change")
    def change(b: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        on()
        return run(V.change, tenant, upload(tenant, b.get("file_id")), str(b.get("voice") or ""),
                   denoise=b.get("denoise") is not False, name=str(b.get("name") or ""))

    @r.post("/music")
    async def music(b: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await arun(V.music, tenant, b.get("brief"), genre=str(b.get("genre") or ""), lang=str(b.get("lang") or "en"),
                          vocals=str(b.get("vocals") or "instrumental"), mood=str(b.get("mood") or ""))

    # ---------------------------------------------------------------- dubbing
    @r.post("/dub")
    def dub(b: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        on()
        return run(V.dub_start, tenant, upload(tenant, b.get("file_id")), b.get("langs"), mode=str(b.get("mode") or "matched"),
                   keep_sound=b.get("keep_sound") is not False, name=str(b.get("name") or ""))

    @r.get("/dub/{did}")
    def dub_get(did: str, tenant: str = Depends(current_tenant)):
        return run(V.dub_get, tenant, did)

    @r.get("/dubs")
    def dub_list(tenant: str = Depends(current_tenant)):
        return {"dubs": run(V.dubs, tenant)}

    # ---------------------------------------------------------------- studio
    @r.post("/project")
    def project(b: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return run(V.project_save, tenant, pid=str(b.get("id") or ""), title=b.get("title"), voice=str(b.get("voice") or ""),
                   lang=str(b.get("lang") or "en"), chapters=b.get("chapters"), cast=b.get("cast"))

    @r.post("/project/import")
    def project_import(b: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        on()
        return run(V.project_import, tenant, file_path=maybe(tenant, b.get("file_id")), url=str(b.get("url") or ""),
                   text=str(b.get("text") or ""), title=str(b.get("title") or ""))

    @r.post("/project/cast")
    async def project_cast(b: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await arun(V.project_cast, tenant, str(b.get("id") or ""), b.get("n") or 0)

    @r.delete("/project")
    def project_remove(id: str, tenant: str = Depends(current_tenant)):
        return run(V.project_remove, tenant, id)

    @r.post("/project/chapter")
    async def chapter(b: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await arun(V.chapter_make, tenant, str(b.get("id") or ""), b.get("n"))

    @r.post("/project/export")
    def export(b: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return run(V.project_export, tenant, str(b.get("id") or ""), str(b.get("format") or "wav"))

    # ---------------------------------------------------------------- history, files
    @r.delete("/history")
    def history_remove(id: str, tenant: str = Depends(current_tenant)):
        return run(V.history_remove, tenant, id)

    @r.get("/audio")
    def audio(id: str, format: str = "", tenant: str = Depends(current_tenant)):
        f, h = run(V.audio_file, tenant, id, format)
        name = "".join(c if c.isalnum() or c in " -_" else "_" for c in (h.get("title") or "hoola-vocal"))[:60].strip() or "hoola-vocal"
        return FileResponse(f, media_type=MIME.get(h.get("ext", "wav"), "application/octet-stream"),
                            headers={"Cache-Control": "private, no-store",
                                     "Content-Disposition": f'inline; filename="{name}.{h.get("ext", "wav")}"'})

    return r
