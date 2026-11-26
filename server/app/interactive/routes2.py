"""v0.999.170 HOOLA INTERACTIVE REBUILD - the new doors of the rebuilt page (contract docs/HOOLA_INTERACTIVE_REBUILD.md).

    /api/interactive/x/*      the console page (her key): engines, defaults, voices, languages, the price card,
                              B-roll shots, live agents (session pass, ask, publish), app keys + webhooks
    /api/interactive/v1/*     her own apps (an hi_live_ app key)
    /api/interactive/pub/*    a live agent she published on her website (a public agent pass; minute cap a day)

Thin: the rules live in studio.py / engines.py / voice.py / live.py / apps.py.
"""
from __future__ import annotations

import asyncio
from typing import Any, Callable

from fastapi import APIRouter, Body, Depends, Header, HTTPException, Request
from fastapi.responses import FileResponse, Response

from . import apps as AP
from . import engines as EN
from . import live as LV
from . import studio as S
from . import voice as VO


def _on() -> None:
    from ..config import get_settings
    if not get_settings().interactive_page:
        raise HTTPException(403, "Hoola Interactive is switched off on this server.")


def _wrap(fn, *a, code: int = 422, **kw):
    try:
        return fn(*a, **kw)
    except S.StudioError as e:
        raise HTTPException(404 if "not found" in str(e) else code, str(e))
    except EN.EngineError as e:
        raise HTTPException(e.status, str(e))
    except VO.VoiceError as e:
        raise HTTPException(503, str(e))
    except LV.LiveError as e:
        raise HTTPException(e.status, str(e))


def make_router(require_key: Callable, current_tenant: Callable) -> APIRouter:
    r = APIRouter(prefix="/api/interactive/x", dependencies=[Depends(require_key)])

    @r.get("/home")
    async def home(tenant: str = Depends(current_tenant)):
        """Everything the page needs on first paint, in one call."""
        _on()
        from . import hub as H
        ov = await asyncio.to_thread(H.overview, tenant)
        return {**ov, "engines": EN.view(tenant), "live": LV.agents(tenant), "apps": AP.view(tenant)}

    @r.get("/engines")
    async def engines(tenant: str = Depends(current_tenant)):
        _on()
        return EN.view(tenant)

    @r.put("/engines/default")
    async def engine_default(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        _on()
        return {"defaults": _wrap(EN.set_default, tenant, str((body or {}).get("id") or ""), code=409)}

    @r.get("/engines/prices")
    def engine_prices(job: str = "video", seconds: int = 30, voice: str = "", tenant: str = Depends(current_tenant)):
        """v0.999.208 every engine of one job priced for one length (the Engines page cards). Nothing is spent."""
        _on()
        vc = int(VO.credits_for(tenant, voice, int(seconds * 14)).get("credits") or 0) if job == "video" else 0
        return _wrap(EN.prices, job, float(seconds), vc)

    @r.get("/engines/one")
    def engine_one(id: str = "", voice: str = "", tenant: str = Depends(current_tenant)):
        """v0.999.208 one engine for the side panel: its row, its price at each usual length, her videos on it."""
        _on()
        row = next((e for e in EN.view(tenant)["engines"] if e["id"] == id), None)
        if row is None:
            raise HTTPException(404, "That engine is not on the list.")
        vf = lambda s: int(VO.credits_for(tenant, voice, int(s * 14)).get("credits") or 0)   # noqa: E731
        vids = []
        if row["job"] == "video":
            for p in S.listing(tenant)["projects"]:
                if (p.get("engine") or "hoola") == id:
                    vids.append({"id": p.get("id"), "title": p.get("title") or "Untitled", "status": p.get("status") or "",
                                 "seconds": round(float(((p.get("video") or {}).get("duration")) or 0)),
                                 "updated": p.get("updated") or p.get("created") or ""})
        return {"engine": row, "prices": _wrap(EN.ladder, id, vf), "videos": vids[:12]}

    @r.get("/estimate")
    def estimate(engine: str = "", seconds: int = 30, voice: str = "", tenant: str = Depends(current_tenant)):
        """v0.999.172 the price shown under the home box BEFORE anything is planned: her engine x the length she picked,
        plus the voice for about that many spoken characters. Nothing is spent."""
        _on()
        secs = max(10, min(90, int(seconds or 30)))
        eid = engine or EN.defaults_of(tenant)["video"]
        vc = int(VO.credits_for(tenant, voice, int(secs * 14)).get("credits") or 0)
        return _wrap(EN.quote, eid, float(secs), vc)

    @r.get("/compare")
    def compare(id: str = "", tenant: str = Depends(current_tenant)):
        """v0.999.172 every video engine priced for THIS draft (same length, same voice), for the Compare engines menu."""
        _on()
        p = _wrap(S.project, tenant, id)
        base = _wrap(S.quote_for, tenant, p)
        out = []
        for e in EN.view(tenant)["engines"]:
            if e["job"] != "video":
                continue
            try:
                q = EN.quote(e["id"], base["seconds"], base["voice_credits"])
            except EN.EngineError:
                continue
            out.append({"id": e["id"], "label": e["label"], "ready": e["ready"], "status": e.get("status"),
                        "what": e["what"], "quality": e["quality"], "credits": q["credits"],
                        "face_credits": q["face_credits"], "face": e["face"]})
        return {"engines": out, "seconds": base["seconds"], "chosen": p.get("engine") or "hoola"}

    @r.get("/voices")
    def voices(tenant: str = Depends(current_tenant)):
        _on()
        return VO.voices(tenant)

    @r.post("/voices/apply")
    def voices_apply(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        """v0.999.201 one voice into several of her videos (free; only the voice changes)."""
        _on()
        b = dict(body or {})
        try:
            return VO.apply_voice(tenant, str(b.get("voice") or ""), list(b.get("ids") or []))
        except VO.VoiceError as e:
            raise HTTPException(404 if "not found" in str(e).lower() else 422, str(e))

    @r.get("/langs")
    async def langs():
        _on()
        return {"langs": VO.langs()}

    @r.get("/quote")
    async def quote(id: str = "", silent: int = 0, tenant: str = Depends(current_tenant)):
        _on()
        p = _wrap(S.project, tenant, id)
        return {"quote": _wrap(S.quote_for, tenant, p, bool(silent)),
                "problems": S.problems(p) + S.engine_problems(tenant, p)}

    @r.post("/make")
    async def make(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        """Her tap on the price card: the make starts only with that exact quote."""
        _on()
        b = dict(body or {})
        return _wrap(S.make, tenant, str(b.get("id") or ""), silent=bool(b.get("silent")),
                     quote_key=str(b.get("quote_key") or ""), code=409)

    @r.post("/broll")
    def broll(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        _on()
        b = dict(body or {})
        return _wrap(LV.broll_make, tenant, str(b.get("prompt") or ""), int(b.get("seconds") or 6),
                     str(b.get("aspect") or "16:9"), str(b.get("engine") or "gemini_broll"),
                     quote_key=str(b.get("quote_key") or ""), code=409)

    @r.get("/broll/quote")
    async def broll_quote(seconds: int = 6, engine: str = "gemini_broll"):
        _on()
        return _wrap(EN.quote, engine, float(seconds))

    @r.get("/broll/file")
    async def broll_file(id: str = "", tenant: str = Depends(current_tenant)):
        _on()
        f = LV.broll_path(tenant, id)
        if f is None:
            raise HTTPException(404, "That shot was not found.")
        return FileResponse(str(f), media_type="video/mp4")

    # ---- live agents
    @r.get("/live")
    async def live_list(tenant: str = Depends(current_tenant)):
        _on()
        return LV.agents(tenant)

    @r.post("/live")
    async def live_save(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        _on()
        return _wrap(LV.agent_save, tenant, dict(body or {}))

    @r.delete("/live")
    async def live_del(id: str = "", tenant: str = Depends(current_tenant)):
        _on()
        return {"ok": _wrap(LV.agent_remove, tenant, id)}

    @r.post("/live/session")
    async def live_session(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        _on()
        return await asyncio.to_thread(_wrap, LV.session, tenant, str((body or {}).get("id") or ""), code=409)

    @r.post("/live/ask")
    def live_ask(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        _on()
        b = dict(body or {})
        return _wrap(LV.ask, tenant, str(b.get("id") or ""), str(b.get("text") or ""), code=409)

    @r.get("/live/questions")
    async def live_questions(id: str = "", tenant: str = Depends(current_tenant)):
        _on()
        return _wrap(LV.questions, tenant, id)

    @r.post("/live/learn")
    async def live_learn(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        """v0.999.202 her answer to a question it could not answer, added to its facts."""
        _on()
        b = dict(body or {})
        return _wrap(LV.learn, tenant, str(b.get("id") or ""), str(b.get("qid") or ""), str(b.get("answer") or ""))

    @r.post("/live/dismiss")
    async def live_dismiss(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        _on()
        b = dict(body or {})
        return _wrap(LV.dismiss, tenant, str(b.get("id") or ""), str(b.get("qid") or ""))

    @r.post("/live/publish")
    async def live_publish(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        _on()
        b = dict(body or {})
        return _wrap(LV.publish, tenant, str(b.get("id") or ""), bool(b.get("on", True)), list(b.get("sites") or []))

    # ---- app keys + webhooks
    @r.get("/apps")
    async def apps(request: Request, tenant: str = Depends(current_tenant)):
        _on()
        return AP.view(tenant, str(request.base_url))

    @r.patch("/apps/keys")
    async def key_rename(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        _on()
        b = dict(body or {})
        return _wrap(AP.key_rename, tenant, str(b.get("id") or ""), b.get("name"))

    @r.post("/apps/keys")
    async def key_new(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        _on()
        return _wrap(AP.key_new, tenant, (body or {}).get("name"))

    @r.delete("/apps/keys")
    async def key_del(id: str = "", tenant: str = Depends(current_tenant)):
        _on()
        return _wrap(AP.key_remove, tenant, id)

    @r.post("/apps/hooks")
    def hook_new(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        _on()
        b = dict(body or {})
        return _wrap(AP.hook_add, tenant, b.get("url"), b.get("events"))

    @r.delete("/apps/hooks")
    async def hook_del(id: str = "", tenant: str = Depends(current_tenant)):
        _on()
        return _wrap(AP.hook_remove, tenant, id)

    @r.post("/apps/hooks/test")
    def hook_test(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        _on()
        return _wrap(AP.hook_test, tenant, str((body or {}).get("id") or ""))

    return r


def make_public_router() -> APIRouter:
    """Her own apps (an app key) and her published live agents (a public agent pass). No console key here."""
    r = APIRouter(prefix="/api/interactive")

    def tenant_of(auth: str) -> str:
        _on()
        try:
            return AP.who(auth)[0]
        except PermissionError as e:
            raise HTTPException(401, str(e))
        except OverflowError as e:
            raise HTTPException(429, str(e))

    def public_project(p: dict[str, Any], tenant: str) -> dict[str, Any]:
        from ..config import get_settings
        base = (getattr(get_settings(), "public_base_url", "") or "").rstrip("/")
        out = {k: p.get(k) for k in ("id", "title", "status", "lang", "shape", "aspect", "engine", "voice", "error",
                                     "created", "updated")}
        out["scenes"] = [{"say": s["say"], "look": s["look"], "needs": s.get("needs", "")} for s in p["scenes"]]
        out["video"] = p.get("video")
        out["problems"] = S.problems(p) + S.engine_problems(tenant, p)
        out["download"] = f"{base}/api/interactive/v1/videos/{p['id']}/file" if p["status"] == "ready" else ""
        return out

    @r.get("/v1/engines")
    async def v1_engines(authorization: str = Header(default="")):
        tenant = tenant_of(authorization)
        return EN.view(tenant)

    @r.get("/v1/avatars")
    async def v1_avatars(authorization: str = Header(default="")):
        tenant = tenant_of(authorization)
        return {"avatars": [{k: a.get(k) for k in ("id", "name", "kind", "lang", "consent_at")}
                            for a in S._load(tenant).get("avatars") or []]}

    @r.post("/v1/videos")
    def v1_new(body: dict = Body(default={}), authorization: str = Header(default="")):
        tenant = tenant_of(authorization)
        b = dict(body or {})
        p = _wrap(S.draft, tenant, str(b.get("brief") or b.get("ask") or ""), shape=str(b.get("shape") or "talking_head"),
                  lang=str(b.get("lang") or "en"), seconds=int(b.get("seconds") or 30),
                  avatar_id=str(b.get("avatar_id") or ""), voice=str(b.get("voice") or ""),
                  engine=str(b.get("engine") or ""), code=502)
        if isinstance(b.get("scenes"), list) and b["scenes"]:
            p = _wrap(S.save, tenant, p["id"], {"scenes": b["scenes"]})
        return {**public_project(p, tenant), "quote": _wrap(S.quote_for, tenant, p)}

    @r.post("/v1/videos/{pid}/make")
    def v1_make(pid: str, body: dict = Body(default={}), authorization: str = Header(default="")):
        tenant = tenant_of(authorization)
        out = _wrap(S.make, tenant, pid, quote_key=str((body or {}).get("quote_key") or ""), code=409)
        AP.count_video(tenant)
        return out

    @r.get("/v1/videos/{pid}")
    async def v1_get(pid: str, authorization: str = Header(default="")):
        tenant = tenant_of(authorization)
        p = _wrap(S.project, tenant, pid)
        return {**public_project(p, tenant), "progress": S.job_view(tenant, pid)}

    @r.get("/v1/videos/{pid}/file")
    async def v1_file(pid: str, authorization: str = Header(default="")):
        tenant = tenant_of(authorization)
        p = _wrap(S.project, tenant, pid)
        f = S.video_path(tenant, pid)
        if p["status"] != "ready" or not f.is_file():
            raise HTTPException(404, "This video is not ready.")
        return FileResponse(str(f), media_type="video/mp4", filename=f"{pid}.mp4")

    # ---- a live agent on her website (called from her site's page: answers carry CORS headers, errors too)
    CORS = {"Access-Control-Allow-Origin": "*", "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type", "Access-Control-Max-Age": "600"}

    def cors(fn, *a):
        from fastapi.responses import JSONResponse
        try:
            return JSONResponse(fn(*a), headers=CORS)
        except HTTPException as e:
            return JSONResponse({"detail": e.detail}, status_code=e.status_code, headers=CORS)
        except (LV.LiveError, EN.EngineError) as e:
            return JSONResponse({"detail": str(e)}, status_code=getattr(e, "status", 422), headers=CORS)

    @r.options("/pub/{token}")
    @r.options("/pub/{token}/ask")
    @r.options("/pub/{token}/session")
    async def pub_pre(token: str):
        return Response(status_code=204, headers=CORS)

    @r.get("/pub/{token}")
    async def pub_info(token: str, request: Request):
        return cors(lambda: (_on(), LV.public_info(token, request.headers.get("origin") or ""))[1])

    @r.post("/pub/{token}/ask")
    def pub_ask(token: str, request: Request, body: dict = Body(default={})):
        ip = request.client.host if request.client else ""
        return cors(lambda: (_on(), LV.public_ask(token, str((body or {}).get("text") or ""),
                                                  request.headers.get("origin") or "", ip))[1])

    @r.post("/pub/{token}/session")
    def pub_session(token: str, request: Request):
        ip = request.client.host if request.client else ""
        return cors(lambda: (_on(), LV.public_session(token, request.headers.get("origin") or "", ip))[1])

    return r


def voice_preview_response(data: bytes) -> Response:
    return Response(data, media_type="audio/wav")
