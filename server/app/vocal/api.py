"""v0.787 HOOLA VOCAL -> v0.999.90 GLOBAL - the page's doors (/api/vocal/*). Thin: the work and the rules are service.py.
The contract is docs/HOOLA_VOCAL_GLOBAL.md."""
from __future__ import annotations

from pathlib import Path
from typing import Callable

from fastapi import APIRouter, Body, Depends, HTTPException, Response
from fastapi.responses import FileResponse, JSONResponse

from . import engines as EN
from . import service as V

MIME = {"wav": "audio/wav", "mp3": "audio/mpeg", "flac": "audio/flac", "m4b": "audio/mp4", "m4a": "audio/mp4",
        "ogg": "audio/ogg", "mp4": "video/mp4", "srt": "application/x-subrip", "vtt": "text/vtt"}


def no_credits(e: Exception) -> JSONResponse:
    """0 credits: a plain line + where the page links to (the job was refused before any engine call)."""
    return JSONResponse({"detail": str(e), "credits": V.CREDITS_PAGE, "need": "credits"}, status_code=402)


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
        except V.VocalNoCredits as e:
            return no_credits(e)
        except V.VocalError as e:
            raise fail(e)

    async def arun(fn, *a, **kw):
        on()
        try:
            return await fn(*a, **kw)
        except V.VocalNoCredits as e:
            return no_credits(e)
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
        if job not in EN.JOBS:                          # a price follows the job's id, never a label
            raise HTTPException(422, "Unknown job. Ask for a price by the job's id.")
        eng = str(b.get("engine") or "")
        if not eng or eng == "auto":
            eng = "eleven" if job in ("change", "isolate", "sfx", "dub_own") else "server" if job == "cleanup" else "gemini"
            if job in ("tts", "dialogue") and b.get("voice"):
                try:
                    eng = V._engine_of(V._voice(V._load(tenant), str(b["voice"])))
                except V.VocalError:
                    pass
        try:
            q = EN.quote(job, chars=int(b.get("chars") or 0), seconds=float(b.get("seconds") or 0),
                         takes=int(b.get("takes") or 1), engine=eng)
            ln = b.get("langs")
            n = (len(ln) if isinstance(ln, list) else int(ln or 0)) if job.startswith("dub") else 0
            if n > 1:                                   # a dub is priced per language
                q.update(credits=q["credits"] * n, usd=round(q["usd"] * n, 4),
                         line=q["line"].replace(f"about {q['credits']} credit{'' if q['credits'] == 1 else 's'}",
                                                       f"about {q['credits'] * n} credits for {n} languages"))
            return q
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
                          style=str(b.get("style") or "friendly"), chat=str(b.get("chat") or ""),
                          mode=str(b.get("mode") or "lines"))

    @r.post("/podcast")
    async def podcast(b: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        on()
        try:
            title, text = V.source_text(tenant, maybe(tenant, b.get("file_id")), str(b.get("url") or ""), str(b.get("text") or ""))
            out = await V.podcast(tenant, text, minutes=b.get("minutes") or 3, hosts=b.get("hosts"), lang=str(b.get("lang") or "auto"))
        except V.VocalNoCredits as e:
            return no_credits(e)
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
        return run(V.rule_add, tenant, b.get("word"), b.get("say"), lang=str(b.get("lang") or ""), ipa=b.get("ipa") or "")

    @r.post("/rules/import")
    def rules_import(b: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return run(V.rules_import, tenant, b.get("text"))

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

    # ---------------------------------------------------------------- dubbing
    @r.post("/dub")
    def dub(b: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        on()
        return run(V.dub_start, tenant, upload(tenant, b.get("file_id")), b.get("langs"), mode=str(b.get("mode") or "matched"),
                   keep_sound=b.get("keep_sound") is not False, name=str(b.get("name") or ""),
                   speakers=b.get("speakers") or 0, voices=b.get("voices"))

    @r.get("/dub/{did}")
    def dub_get(did: str, tenant: str = Depends(current_tenant)):
        return run(V.dub_get, tenant, did)

    @r.post("/dub/{did}/langs")
    def dub_langs(did: str, b: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        on()
        return run(V.dub_more, tenant, did, b.get("langs"))

    @r.get("/settings")
    def settings_get(tenant: str = Depends(current_tenant)):
        return run(V.settings_get, tenant)

    @r.put("/settings")
    def settings_put(b: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return run(V.settings_save, tenant, b)

    @r.get("/dubs")
    def dub_list(tenant: str = Depends(current_tenant)):
        return {"dubs": run(V.dubs, tenant)}

    @r.get("/dub/{did}/subtitles")
    def dub_subtitles(did: str, lang: str = "", format: str = "srt", tenant: str = Depends(current_tenant)):
        data, name = run(V.dub_subtitles, tenant, did, lang, format)
        ext = "vtt" if name.endswith(".vtt") else "srt"
        safe = "".join(c if c.isalnum() or c in " -_." else "_" for c in name)[:90] or f"subtitles.{ext}"
        return Response(data, media_type=f"{MIME[ext]}; charset=utf-8",
                        headers={"Cache-Control": "private, no-store", "Content-Disposition": f'attachment; filename="{safe}"'})

    @r.get("/dub/{did}/lines")
    def dub_lines(did: str, lang: str = "", tenant: str = Depends(current_tenant)):
        return run(V.dub_lines, tenant, did, lang)

    @r.put("/dub/{did}/lines/{n}")
    def dub_line_save(did: str, n: int, b: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return run(V.dub_line_save, tenant, did, n, str(b.get("lang") or ""), b.get("text"))

    @r.post("/dub/{did}/lines/{n}/redo")
    def dub_line_redo(did: str, n: int, b: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return run(V.dub_line_redo, tenant, did, n, str(b.get("lang") or ""))

    # ---------------------------------------------------------------- the shared voice library
    @r.get("/library")
    def shared_library(q: str = "", lang: str = "", gender: str = "", age: str = "", accent: str = "", use: str = "",
                       sort: str = "", page: int = 0, tenant: str = Depends(current_tenant)):
        return run(V.shared_library, q=q, lang=lang, gender=gender, age=age, accent=accent, use=use, sort=sort, page=page)

    @r.post("/library/add")
    def library_add(b: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return run(V.library_add, tenant, b.get("id"), b.get("owner"), b.get("name"))

    @r.get("/library/preview")
    def library_preview(url: str = "", tenant: str = Depends(current_tenant)):
        data = run(V.library_preview, url)
        return Response(data, media_type="audio/mpeg", headers={"Cache-Control": "private, max-age=86400"})

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
