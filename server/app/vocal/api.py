"""v0.787 HOOLA VOCAL -> v0.999.90 GLOBAL - the page's doors (/api/vocal/*). Thin: the work and the rules are service.py.
The contract is docs/HOOLA_VOCAL_GLOBAL.md."""
from __future__ import annotations

from pathlib import Path
from typing import Callable

from fastapi import APIRouter, Body, Depends, HTTPException, Response
from fastapi.responses import FileResponse, JSONResponse

from . import book as BK
from . import dubbing as DB
from . import engines as EN
from . import service as V

MIME = {"wav": "audio/wav", "mp3": "audio/mpeg", "flac": "audio/flac", "m4b": "audio/mp4", "m4a": "audio/mp4",
        "ogg": "audio/ogg", "mp4": "video/mp4", "srt": "application/x-subrip", "vtt": "text/vtt",
        "zip": "application/zip"}


def _attach(name: str) -> dict[str, str]:
    safe = "".join(c if c.isalnum() or c in " -_." else "_" for c in name)[:90] or "file"
    return {"Cache-Control": "private, no-store", "Content-Disposition": f'attachment; filename="{safe}"'}


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
                          mode=str(b.get("mode") or "lines"), reactions=bool(b.get("reactions")), music=b.get("music") or "")

    @r.post("/dialogue/{hid}/line")
    async def dialogue_line(hid: str, b: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        from . import talk as TK
        return await arun(TK.remake_line, tenant, hid, b.get("n"), b.get("text"), b.get("speaker"), chat=str(b.get("chat") or ""))

    @r.get("/dialogue/{hid}/voices")
    def dialogue_voices(hid: str, tenant: str = Depends(current_tenant)):
        from . import talk as TK
        data, name = run(TK.stems, tenant, hid)
        return Response(data, media_type="application/zip", headers=_attach(name))

    @r.get("/dialogue/{hid}/subtitles")
    def dialogue_subs(hid: str, fmt: str = "srt", tenant: str = Depends(current_tenant)):
        from . import talk as TK
        data, name = run(TK.subtitles, tenant, hid, fmt)
        return Response(data, media_type="text/vtt" if name.endswith(".vtt") else "application/x-subrip", headers=_attach(name))

    @r.post("/take/{hid}/dub")
    async def take_dub(hid: str, b: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        from . import more as M
        return await arun(M.take_dub, tenant, hid, b.get("langs"), chat=str(b.get("chat") or ""))

    @r.post("/tts/stream")
    def tts_stream(b: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        from . import more as M
        return run(M.stream_start, tenant, b.get("text"), voice=str(b.get("voice") or ""), lang=str(b.get("lang") or "auto"),
                   style=str(b.get("style") or "friendly"), speed=b.get("speed"), expressive=b.get("expressive"),
                   chat=str(b.get("chat") or ""), rules=b.get("rules") is not False)

    # ---------------------------------------------------------------- for her own apps (Settings)
    @r.get("/apps")
    def apps_view(tenant: str = Depends(current_tenant)):
        from . import apps as AP
        return run(AP.view, tenant)

    @r.post("/apps/keys")
    def apps_key_new(b: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        from . import apps as AP
        return run(AP.key_new, tenant, b.get("name"))

    @r.delete("/apps/keys/{kid}")
    def apps_key_remove(kid: str, tenant: str = Depends(current_tenant)):
        from . import apps as AP
        return run(AP.key_remove, tenant, kid)

    @r.post("/apps/hooks")
    def apps_hook_new(b: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        from . import apps as AP
        return run(AP.hook_add, tenant, b.get("url"), b.get("events"))

    @r.delete("/apps/hooks/{hid}")
    def apps_hook_remove(hid: str, tenant: str = Depends(current_tenant)):
        from . import apps as AP
        return run(AP.hook_remove, tenant, hid)

    @r.post("/apps/hooks/{hid}/test")
    def apps_hook_test(hid: str, tenant: str = Depends(current_tenant)):
        from . import apps as AP
        return run(AP.hook_test, tenant, hid)

    @r.post("/sweep")
    def sweep_now(tenant: str = Depends(current_tenant)):
        from . import more as M
        return run(M.sweep, tenant)

    @r.post("/podcast")
    async def podcast(b: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        on()
        try:
            title, text = V.source_text(tenant, maybe(tenant, b.get("file_id")), str(b.get("url") or ""), str(b.get("text") or ""),
                                        pages=True)
            out = await V.podcast(tenant, text, minutes=b.get("minutes") or 3, hosts=b.get("hosts"), lang=str(b.get("lang") or "auto"),
                                  kind=str(b.get("kind") or "podcast"), must=b.get("must") or "")
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
                   speakers=b.get("speakers") or 0, voices=b.get("voices"), keep=b.get("keep"), check=bool(b.get("check")))

    @r.get("/dub/{did}")
    def dub_get(did: str, tenant: str = Depends(current_tenant)):
        return run(DB.view, tenant, did)

    @r.delete("/dub/{did}")
    def dub_remove(did: str, tenant: str = Depends(current_tenant)):
        return run(DB.remove, tenant, did)

    @r.post("/dub/{did}/ok")
    def dub_ok(did: str, b: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return run(DB.ok, tenant, did, str(b.get("lang") or ""))

    @r.post("/dub/{did}/remake")
    def dub_remake(did: str, b: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return run(DB.remake, tenant, did, str(b.get("lang") or ""))

    @r.post("/dub/{did}/stop")
    def dub_stop(did: str, tenant: str = Depends(current_tenant)):
        return run(DB.stop, tenant, did)

    @r.put("/dub/{did}/speakers")
    def dub_speakers(did: str, b: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return run(DB.speakers_set, tenant, did, b.get("names"), b.get("voices"))

    @r.put("/dub/{did}/keep")
    def dub_keep(did: str, b: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return run(DB.keep_set, tenant, did, b.get("words"))

    @r.get("/dub/{did}/speaker")
    def dub_speaker(did: str, sp: str = "", tenant: str = Depends(current_tenant)):
        f = run(DB.speaker_sample, tenant, did, sp)
        return FileResponse(f, media_type="audio/mpeg", headers={"Cache-Control": "private, no-store"})

    @r.get("/dub/{did}/poster")
    def dub_poster(did: str, tenant: str = Depends(current_tenant)):
        f = run(DB.poster, tenant, did)
        return FileResponse(f, media_type="image/jpeg", headers={"Cache-Control": "private, max-age=3600"})

    @r.get("/dub/{did}/source")
    def dub_source(did: str, tenant: str = Depends(current_tenant)):
        f = run(DB.source, tenant, did)
        return FileResponse(f, media_type="video/mp4", headers={"Cache-Control": "private, no-store"})

    @r.get("/dub/{did}/export")
    def dub_export(did: str, what: str = "video", langs: str = "", tenant: str = Depends(current_tenant)):
        on()
        data, name, mime = run(DB.export, tenant, did, what, [x for x in langs.split(",") if x.strip()])
        return Response(data, media_type=mime, headers=_attach(name))

    @r.post("/dub/{did}/langs")
    def dub_langs(did: str, b: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        on()
        return run(V.dub_more, tenant, did, b.get("langs"))

    @r.get("/settings")
    def settings_get(tenant: str = Depends(current_tenant)):
        return run(V.settings_get, tenant)

    @r.put("/voices/fav")
    def voice_fav(b: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return run(V.voice_fav, tenant, b.get("id"), b.get("on", True))

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
        return run(V.dub_line_save, tenant, did, n, str(b.get("lang") or ""), b.get("text"), b.get("pace"), b.get("speaker"))

    @r.post("/dub/{did}/lines/{n}/shorten")
    def dub_line_shorten(did: str, n: int, b: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return run(DB.shorten, tenant, did, n, str(b.get("lang") or ""))

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
                   lang=str(b.get("lang") or "en"), chapters=b.get("chapters"), cast=b.get("cast"), author=b.get("author"),
                   pace=b.get("pace"), gap=b.get("gap"))

    @r.post("/project/import/preview")
    def project_preview(b: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        on()
        return run(BK.preview, tenant, file_path=maybe(tenant, b.get("file_id")), url=str(b.get("url") or ""),
                   text=str(b.get("text") or ""), title=str(b.get("title") or ""))

    @r.post("/project/import")
    def project_import(b: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        on()
        return run(V.project_import, tenant, file_path=maybe(tenant, b.get("file_id")), url=str(b.get("url") or ""),
                   text=str(b.get("text") or ""), title=str(b.get("title") or ""), keep=b.get("keep"),
                   author=b.get("author"), cover=str(b.get("cover") or ""))

    @r.get("/project/cover")
    def project_cover(id: str = "", token: str = "", tenant: str = Depends(current_tenant)):
        f = run(BK.cover_file, tenant, id, token)
        return FileResponse(f, media_type="image/png" if f.suffix == ".png" else "image/jpeg",
                            headers={"Cache-Control": "private, no-store"})

    @r.post("/project/cover")
    def project_cover_set(b: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        on()
        return run(BK.set_cover, tenant, str(b.get("id") or ""), upload(tenant, b.get("file_id")))

    @r.get("/project/people")
    def project_people(id: str, tenant: str = Depends(current_tenant)):
        return run(BK.people, tenant, id)

    @r.post("/project/people/find")
    async def project_people_find(b: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await arun(BK.find_people, tenant, str(b.get("id") or ""))

    @r.post("/project/people/merge")
    def project_people_merge(b: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return run(BK.merge, tenant, str(b.get("id") or ""), b.get("keep"), b.get("drop"))

    @r.post("/project/people/apart")
    def project_people_apart(b: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return run(BK.apart, tenant, str(b.get("id") or ""), b.get("a"), b.get("b"))

    @r.put("/project/people")
    def project_people_set(b: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return run(BK.set_people, tenant, str(b.get("id") or ""), b.get("voices"), b.get("small"))

    @r.get("/project/para")
    def project_para(id: str, n: int = 0, k: int = 0, tenant: str = Depends(current_tenant)):
        f = run(BK.para_file, tenant, id, n, k)
        return FileResponse(f, media_type="audio/wav", headers={"Cache-Control": "private, no-store"})

    @r.put("/project/para")
    def project_para_who(b: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return run(BK.set_who, tenant, str(b.get("id") or ""), b.get("n"), b.get("k"), b.get("who"))

    @r.get("/project/check")
    def project_check(id: str, tenant: str = Depends(current_tenant)):
        return run(BK.check, tenant, id)

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
    async def export(b: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await arun(V.project_export_full, tenant, str(b.get("id") or ""), str(b.get("format") or "wav"),
                          bool(b.get("even", False)), bool(b.get("intro", False)))

    # ---------------------------------------------------------------- history, files
    @r.post("/join")
    def join(b: dict = Body(...), tenant: str = Depends(current_tenant)):
        return run(V.join_takes, tenant, b.get("ids"), b.get("title"), b.get("format") or "wav", b.get("gap"))

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


def make_public_router() -> APIRouter:
    """Doors with no console sign-in: the one-time stream link (the token IS the permission, 2 minutes, once) and her
    own apps' doors (her app key in Authorization: Bearer)."""
    from fastapi import Header
    from fastapi.responses import StreamingResponse
    from . import apps as AP
    from . import more as M
    r = APIRouter(prefix="/api/vocal")

    def on() -> None:
        from ..config import get_settings
        if not get_settings().vocal_page:
            raise HTTPException(403, "Hoola Vocal is switched off on this server.")

    @r.get("/stream/{token}")
    def stream(token: str):
        on()
        job = M.stream_take(token)
        if not job:
            raise HTTPException(404, "This play link was used already or is older than 2 minutes. Tap play again.")
        return StreamingResponse(M.stream_run(job), media_type="audio/mpeg",
                                 headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"})

    def app_tenant(auth: str) -> str:
        on()
        try:
            return AP.who(auth)[0]
        except PermissionError as e:
            raise HTTPException(401, str(e))
        except OverflowError as e:
            raise HTTPException(429, str(e))

    @r.get("/v1/voices")
    def v1_voices(authorization: str = Header(default="")):
        t = app_tenant(authorization)
        out = V.overview(t)["voices"]
        return {"voices": [{"id": v["id"], "name": v["name"], "engine": v.get("engine"), "tier": v.get("tier"),
                            "langs": v.get("langs") or [], "any_language": bool(v.get("any")), "ready": bool(v.get("ready"))}
                           for v in out]}

    @r.post("/v1/speech")
    async def v1_speech(b: dict = Body(default={}), authorization: str = Header(default="")):
        from .. import usage
        t = app_tenant(authorization)
        try:
            with usage.scope(t, "create"):
                row = await V.tts(t, b.get("text"), voice=str(b.get("voice") or ""), lang=str(b.get("lang") or "auto"),
                                  style=str(b.get("style") or "friendly"), speed=b.get("speed"), takes=1,
                                  engine=str(b.get("engine") or "auto"), fmt=str(b.get("format") or "mp3"),
                                  extra={"via": "app"})
        except V.VocalNoCredits as e:
            return no_credits(e)
        except V.VocalError as e:
            raise HTTPException(422, str(e))
        f, h = V.audio_file(t, row["id"])
        return Response(f.read_bytes(), media_type=MIME.get(h.get("ext", "mp3"), "application/octet-stream"),
                        headers={"Cache-Control": "no-store", "X-Hoola-Id": row["id"], "X-Hoola-Credits": str(row.get("credits") or 0),
                                 "X-Hoola-Seconds": str(row.get("seconds") or 0)})

    @r.get("/v1/sounds/{hid}")
    def v1_sound(hid: str, format: str = "", authorization: str = Header(default="")):
        t = app_tenant(authorization)
        try:
            f, h = V.audio_file(t, hid, format)
        except V.VocalError as e:
            raise HTTPException(404, str(e))
        return FileResponse(f, media_type=MIME.get(h.get("ext", "wav"), "application/octet-stream"),
                            headers={"Cache-Control": "no-store"})

    return r
