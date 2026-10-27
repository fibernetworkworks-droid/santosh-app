"""HTTP routes of the Podcast Sahayak (/api/podcast/*). main.py: app.include_router(make_router(require_key, current_tenant)).

HER taps live ONLY here (by_tap=True): POST /cards/{id}/decide {yes, hash, reason} for publishing an episode, any message to a
guest / sponsor (invite, release request, script) and any sponsor invoice.
Public (no key; each checks its own random feed token, only PUBLISHED in-feed episodes are served):
  GET /api/podcast/feed/{token}.xml           - her RSS 2.0 + itunes + Podcasting 2.0 feed
  GET /api/podcast/pub/{token}/{ep}/{name}    - audio / transcript.vtt|srt|json / chapters.json ; show/art.jpg"""
from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, Body, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response


def make_router(require_key, current_tenant) -> APIRouter:
    from . import service as S

    outer = APIRouter()
    r = APIRouter(prefix="/api/podcast", dependencies=[Depends(require_key)])

    async def run(fn, *a, **k):
        try:
            return await asyncio.to_thread(fn, *a, **k)
        except S.PodcastError as e:
            raise HTTPException(400, str(e))
        except ValueError as e:
            raise HTTPException(400, str(e))

    def _b(body: dict | None) -> dict[str, Any]:
        return dict(body or {})

    def _s(v) -> str:
        return "" if v is None else str(v)

    async def _read(file: UploadFile, limit: int) -> bytes:
        data = await file.read(limit + 1)
        if len(data) > limit:
            raise HTTPException(413, "File bahut badi hai.")
        return data

    @r.get("")
    async def overview(tenant: str = Depends(current_tenant)):
        return await run(S.overview, tenant)

    @r.get("/day")
    async def day(tenant: str = Depends(current_tenant)):
        return await run(S.day, tenant)

    @r.get("/settings")
    async def get_settings(tenant: str = Depends(current_tenant)):
        return await run(S.settings, tenant)

    @r.put("/settings")
    async def put_settings(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.save_settings, tenant, **{k: b[k] for k in S._SET_KEYS if k in b})

    @r.post("/artwork")
    async def artwork(file: UploadFile = File(...), tenant: str = Depends(current_tenant)):
        data = await _read(file, 20 * 1024 * 1024)
        return await run(S.set_artwork, tenant, "", data, file.filename or "art.jpg")

    @r.post("/feed")
    async def feed(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.feed_set, tenant, bool(b.get("on")), bool(b.get("new_token")))

    # ---- guests
    @r.get("/guests")
    async def list_guests(tenant: str = Depends(current_tenant)):
        return {"guests": await run(S.guests, tenant)}

    @r.post("/guests")
    async def save_guest(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.guest_save, tenant, _s(b.get("name")), _s(b.get("phone")), _s(b.get("email")), _s(b.get("bio")),
                         b.get("topics"), b.get("links"), _s(b.get("status")), _s(b.get("notes")), _s(b.get("guest")),
                         b.get("no_messages"))

    @r.get("/guests/{gid}")
    async def get_guest(gid: str, tenant: str = Depends(current_tenant)):
        return await run(S.guest_view, tenant, gid)

    @r.get("/guests/{gid}/release_text")
    async def rel_text(gid: str, episode: str = "", fee: str = "", tenant: str = Depends(current_tenant)):
        return await run(S.release_text, tenant, gid, episode, fee)

    @r.post("/guests/{gid}/invite")
    async def invite(gid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.invite_request, tenant, gid, _s(b.get("episode")), _s(b.get("text")))

    @r.post("/guests/{gid}/release_request")
    async def rel_req(gid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.release_request, tenant, gid, _s(b.get("episode")), _s(b.get("fee")))

    @r.post("/guests/{gid}/release")
    async def rel_got(gid: str, how: str = Form(...), text: str = Form(""), episode: str = Form(""), at: str = Form(""),
                      file: UploadFile | None = File(None), tenant: str = Depends(current_tenant)):
        if how == "file":
            if file is None:
                raise HTTPException(400, "Signed release ki file chahiye.")
            data = await _read(file, 20 * 1024 * 1024)
            from .. import chatfiles
            f = await asyncio.to_thread(chatfiles.store, tenant, file.filename or "release.pdf", data, file.content_type or "")
            return await run(S.release_got, tenant, gid, "file", f["file_id"], "", episode, at)
        return await run(S.release_got, tenant, gid, how, "", text, episode, at)

    @r.post("/guests/{gid}/revoke")
    async def revoke(gid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.release_revoke, tenant, gid, _s(_b(body).get("note")))

    @r.post("/guests/{gid}/forget")
    async def forget(gid: str, tenant: str = Depends(current_tenant)):
        return await run(S.forget_guest, tenant, gid)

    # ---- episodes
    @r.get("/episodes")
    async def list_eps(status: str = "", tenant: str = Depends(current_tenant)):
        return {"episodes": await run(S.episodes, tenant, status)}

    @r.post("/episodes")
    async def save_ep(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.episode_save, tenant, _s(b.get("episode")), _s(b.get("title")), b.get("season"), b.get("episode_no"),
                         _s(b.get("kind")), b.get("topics"), b.get("guests"), b.get("record_at"), b.get("record_minutes"),
                         _s(b.get("record_place")), _s(b.get("publish_on")), b.get("explicit"), b.get("news"), b.get("ai_parts"))

    @r.get("/episodes/{eid}")
    async def get_ep(eid: str, tenant: str = Depends(current_tenant)):
        return await run(S.episode_view, tenant, eid)

    @r.get("/episodes/{eid}/checks")
    async def ep_checks(eid: str, tenant: str = Depends(current_tenant)):
        return await run(S.checks, tenant, eid)

    @r.post("/episodes/{eid}/run_sheet")
    async def ep_run(eid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.run_sheet, tenant, eid, _b(body).get("minutes"))

    @r.post("/episodes/{eid}/audio")
    async def ep_audio(eid: str, file: UploadFile = File(...), tenant: str = Depends(current_tenant)):
        data = await _read(file, S.AUDIO_MAX)
        return await run(S.attach_audio, tenant, eid, "", data, file.filename or "episode.mp3")

    @r.post("/episodes/{eid}/loudness")
    async def ep_loud(eid: str, tenant: str = Depends(current_tenant)):
        return await run(S.measure_loudness, tenant, eid)

    @r.post("/episodes/{eid}/normalize")
    async def ep_norm(eid: str, tenant: str = Depends(current_tenant)):
        return await run(S.normalize, tenant, eid)

    @r.post("/episodes/{eid}/transcribe")
    async def ep_tr(eid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.transcribe, tenant, eid, _s(b.get("file_id")), _s(b.get("text")))

    @r.post("/episodes/{eid}/captions")
    async def ep_caps(eid: str, file: UploadFile = File(...), tenant: str = Depends(current_tenant)):
        data = await _read(file, 10 * 1024 * 1024)
        return await run(S.transcribe, tenant, eid, "", data.decode("utf-8-sig", "replace"))

    @r.post("/episodes/{eid}/speakers")
    async def ep_spk(eid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.set_speakers, tenant, eid, _b(body).get("names") or {})

    @r.get("/episodes/{eid}/transcript.{fmt}")
    async def ep_tfile(eid: str, fmt: str, tenant: str = Depends(current_tenant)):
        data, mime, name = await run(S.transcript_file, tenant, eid, fmt)
        return Response(data, media_type=mime, headers={"Content-Disposition": f'attachment; filename="{name}"'})

    @r.post("/episodes/{eid}/notes")
    async def ep_notes(eid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.make_notes, tenant, eid, _b(body).get("links"))

    @r.put("/episodes/{eid}/notes")
    async def ep_edit(eid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.edit_notes, tenant, eid, b.get("summary"), b.get("points"), b.get("chapters"), b.get("links"), b.get("quotes"))

    @r.get("/episodes/{eid}/crosspost")
    async def ep_cross(eid: str, url: str = "", tenant: str = Depends(current_tenant)):
        return await run(S.crosspost, tenant, eid, url)

    @r.post("/episodes/{eid}/music")
    async def ep_music(eid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.music_use, tenant, eid, _s(b.get("music")), bool(b.get("remove")))

    @r.post("/episodes/{eid}/reads")
    async def ep_read(eid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.read_save, tenant, eid, _s(b.get("sponsor")), _s(b.get("script")), _s(b.get("slot")) or "mid",
                         b.get("fix", True) is not False, b.get("brand_ok"))

    @r.post("/episodes/{eid}/publish_request")
    async def ep_pub(eid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.publish_request, tenant, eid, _s(_b(body).get("where")) or "feed")

    @r.post("/episodes/{eid}/posted")
    async def ep_posted(eid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.posted, tenant, eid, _s(b.get("platform")), _s(b.get("url")))

    @r.post("/episodes/{eid}/unpublish")
    async def ep_unpub(eid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.unpublish, tenant, eid, _s(_b(body).get("reason")))

    # ---- music register
    @r.get("/music")
    async def list_music(tenant: str = Depends(current_tenant)):
        return {"music": await run(S.music_list, tenant)}

    @r.post("/music")
    async def save_music(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.music_save, tenant, _s(b.get("title")), _s(b.get("licence")) or "unknown", _s(b.get("artist")),
                         _s(b.get("source")), _s(b.get("proof")), _s(b.get("attribution")), _s(b.get("valid_until")),
                         b.get("commercial_ok"), _s(b.get("music")))

    # ---- sponsors
    @r.get("/sponsors")
    async def list_sp(tenant: str = Depends(current_tenant)):
        return {"sponsors": await run(S.sponsors, tenant)}

    @r.post("/sponsors")
    async def save_sp(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.sponsor_save, tenant, _s(b.get("brand")), _s(b.get("contact")), _s(b.get("phone")), _s(b.get("email")),
                         _s(b.get("gstin")), b.get("amount"), _s(b.get("deliverables")), _s(b.get("status")), _s(b.get("notes")),
                         _s(b.get("sponsor")))

    @r.post("/sponsors/{sid}/message")
    async def sp_msg(sid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.sponsor_request, tenant, sid, _s(b.get("episode")), _s(b.get("text")))

    @r.post("/sponsors/{sid}/invoice")
    async def sp_inv(sid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.invoice_request, tenant, sid, b.get("amount"), _s(b.get("note")))

    @r.post("/sponsors/{sid}/paid")
    async def sp_paid(sid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.paid, tenant, sid, b.get("amount"), _s(b.get("ref")), b.get("tds"))

    # ---- analytics she gives
    @r.post("/stats")
    async def stats_text(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.stats_import, tenant, _s(b.get("text")), _s(b.get("file_id")), _s(b.get("platform")))

    @r.post("/stats/file")
    async def stats_file(file: UploadFile = File(...), platform: str = Form(""), tenant: str = Depends(current_tenant)):
        data = await _read(file, 10 * 1024 * 1024)
        from .. import chatfiles
        f = await asyncio.to_thread(chatfiles.store, tenant, file.filename or "stats.csv", data, file.content_type or "")
        return await run(S.stats_import, tenant, "", f["file_id"], platform)

    @r.get("/stats")
    async def stats(tenant: str = Depends(current_tenant)):
        return await run(S.stats_report, tenant)

    # ---- cards (HER tap)
    @r.get("/cards")
    async def list_cards(status: str = "waiting", tenant: str = Depends(current_tenant)):
        return {"cards": await run(S.cards, tenant, status)}

    @r.get("/cards/{cid}")
    async def get_card(cid: str, tenant: str = Depends(current_tenant)):
        return await run(S.card_view, tenant, cid)

    @r.post("/cards/{cid}/decide")
    async def decide(cid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.decide, tenant, cid, bool(b.get("yes")), _s(b.get("hash")), _s(b.get("reason")), by_tap=True)

    @r.post("/messages")
    async def message(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.message_request, tenant, _s(b.get("to")), _s(b.get("text")))

    # ---- public feed (token-checked, no key)
    pub = APIRouter(prefix="/api/podcast")

    @pub.get("/feed/{token}.xml")
    async def feed_xml(token: str):
        x = await asyncio.to_thread(S.feed_xml, token)
        if x is None:
            raise HTTPException(404, "Not found")
        return Response(x, media_type="application/rss+xml; charset=utf-8",
                        headers={"Cache-Control": "public, max-age=300", "X-Content-Type-Options": "nosniff"})

    @pub.get("/pub/{token}/{ep}/{name}")
    async def pub_file(token: str, ep: str, name: str):
        f = await asyncio.to_thread(S.pub_file, token, ep, name)
        if f is None:
            raise HTTPException(404, "Not found")
        kind, val, mime = f
        hdr = {"Cache-Control": "public, max-age=3600", "X-Content-Type-Options": "nosniff"}
        if kind == "path":
            return FileResponse(val, media_type=mime, headers=hdr)
        return Response(val, media_type=mime, headers=hdr)

    outer.include_router(r)
    outer.include_router(pub)
    return outer
