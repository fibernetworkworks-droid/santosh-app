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
POST   /api/gamestudio/{id}/github     {repo?, private?}  the GitHub card (her tap sends it)

v0.416 Game platforms (desktop on this server, Android in her builds repo; uploads only by her tap):
GET    /api/gamestudio/{id}/releases            releases + where each platform can be built + package + itch key set?
POST   /api/gamestudio/{id}/releases            {platforms: [linux, windows, macos, android], android_format: apk|aab}
GET    /api/gamestudio/release/{rid}/{platform}?exp&sig   a signed download (kit-<sid>/kit = the store kit ZIP)
GET    /api/gamestudio/{id}/store-kit?regen     store texts (limits checked), images, AI disclosure, rating draft, Steam scripts
GET    /api/gamestudio/{id}/rating              the age-rating draft (IARC-style answers)
POST   /api/gamestudio/itch-key                 {key}  her itch.io API key (app only, sealed)
POST   /api/gamestudio/{id}/releases/{rid}/itch {target: user/game}  the upload card
POST   /api/gamestudio/{id}/releases/{rid}/itch/push {hash}  HER TAP: butler push

v0.416 QA farm (bots play a DEBUG web build; no model, no money):
GET    /api/gamestudio/{id}/qa                  bugs + the last report (signed screenshot links) + history + running
POST   /api/gamestudio/{id}/qa/run              run the farm now (background, 2-4 minutes)
POST   /api/gamestudio/{id}/qa/golden           {rel?}  her OK: this start screen is the golden one
POST   /api/gamestudio/{id}/bugs                {title, detail?, severity?}  her own bug report
POST   /api/gamestudio/{id}/bugs/{B-0001}/fix|open|wontfix|duplicate   fix = a board task whose criterion is the bot
GET    /api/gamestudio/qa-shot/{sid}?rel&exp&sig  a signed QA screenshot

v0.416 Asset pipeline (her OK before anything enters the game; paid kinds only after her tap on the price card):
GET    /api/gamestudio/{id}/assets              assets + price card + spent
GET    /api/gamestudio/{id}/assets/suggest      what the game still needs, from the Bible (nothing priced)
POST   /api/gamestudio/{id}/assets              {kind, key, words, size?, quality?, palette_lock?, preset?, seed?, text?...}
POST   /api/gamestudio/{id}/assets/spend        {ids}  HER TAP: the priced assets start
POST   /api/gamestudio/{id}/assets/upload       {kind, key, data (base64), words?}  her own file, checked by its bytes
POST   /api/gamestudio/{id}/assets/{key}/approve|reject|remove   {v?}
POST   /api/gamestudio/{id}/assets-apply        approved assets into the live game (no model call)
GET    /api/gamestudio/asset/{aid}/{v}?exp&sig  a signed preview link

v0.406 Hoola Game Crew:
GET    /api/gamestudio/crew            the 49 roles (tiers, builds / writes) + the 9 team flows
POST   /api/gamestudio/{id}/plan       {words?, team?}  team = combat | narrative | ui | level | polish | audio | live_ops | qa | release
POST   /api/gamestudio/{id}/task/{t}   {action: review}  the role's lead reviews it (screenshots + the code change)
POST   /api/gamestudio/{id}/gate       {milestone?}  PASS / CONCERNS / FAIL / NOT ASSESSED (advice only)

v0.395 Game Bible (specs as data):
GET    /api/gamestudio/{id}/bible                   data + checks + templates + draft + history
POST   /api/gamestudio/{id}/bible/entity            {kind, entity}   her add / edit (validated, applies at once)
DELETE /api/gamestudio/{id}/bible/entity/{kind}/{eid}
POST   /api/gamestudio/{id}/bible/section           {section: meta|style|terms|player|curves|economy, value}
POST   /api/gamestudio/{id}/bible/generate          {kind, n, words}  a DRAFT (model words + curve numbers)
POST   /api/gamestudio/{id}/bible/seed              first Bible from the design doc (a draft)
POST   /api/gamestudio/{id}/bible/accept|reject     {ids?}  her OK on the draft
POST   /api/gamestudio/{id}/bible/simulate          {runs?}  seeded balance simulation
POST   /api/gamestudio/{id}/bible/apply             the Bible into the live game, no model call
POST   /api/gamestudio/{id}/bible/recurve           {kind}  numbers re-made from the curves"""
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
        from ..employee import hire   # v0.410 a game starts only while the Game Developer is hired (the tool checked, the route did not)
        if not hire.is_working(tenant, "game_dev"):
            raise HTTPException(400, "Game Developer abhi hired nahi hai (ya paused hai). Employees mein 'Hire Game Developer' dabaiye.")
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

    @r.get("/api/gamestudio/crew", dependencies=[Depends(require_key)])
    async def st_crew():
        from . import crew as C
        return C.roster()

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
        crit = b.get("criteria") if isinstance(b.get("criteria"), list) else None
        return await call(S.add_task, tenant, sid, str(b.get("title") or ""), str(b.get("detail") or ""),
                          str(b.get("milestone") or ""), str(b.get("kind") or "feature"), pr, "her",
                          str(b.get("role") or ""), crit)

    @r.post("/api/gamestudio/{sid}/plan", dependencies=[Depends(require_key)])
    async def st_plan(sid: str, body: Any = Body(default=None), tenant: str = Depends(current_tenant)):
        return await call(S.plan, tenant, sid, str(_b(body).get("words") or ""), str(_b(body).get("team") or ""))

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
        if a == "review":
            await call(S.review_task, tenant, sid, tid)
            return await call(S.get, tenant, sid)
        if a in ("drop", "todo"):
            await call(S.edit_task, tenant, sid, tid, status="dropped" if a == "drop" else "todo")
        elif a == "edit":
            await call(S.edit_task, tenant, sid, tid, title=b.get("title"), detail=b.get("detail"),
                       milestone=b.get("milestone"), priority=b.get("priority"))
        else:
            raise HTTPException(400, "action = ok | back | drop | todo | edit")
        return await call(S.get, tenant, sid)

    @r.post("/api/gamestudio/{sid}/gate", dependencies=[Depends(require_key)])
    async def st_gate(sid: str, body: Any = Body(default=None), tenant: str = Depends(current_tenant)):
        return await call(S.gate, tenant, sid, str(_b(body).get("milestone") or ""))

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

    # ------------------------------------------------------------ v0.395 Game Bible (specs as data)
    from . import bible as B

    async def bcall(fn, *a, **kw):
        try:
            return await asyncio.to_thread(fn, *a, **kw)
        except (B.BibleError, service.GameError) as e:
            raise HTTPException(400, str(e))

    @r.get("/api/gamestudio/{sid}/bible", dependencies=[Depends(require_key)])
    async def bi_get(sid: str, tenant: str = Depends(current_tenant)):
        return await bcall(B.view, tenant, sid)

    @r.post("/api/gamestudio/{sid}/bible/entity", dependencies=[Depends(require_key)])
    async def bi_set(sid: str, body: Any = Body(default=None), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await bcall(B.set_entity, tenant, sid, str(b.get("kind") or ""), b.get("entity") if isinstance(b.get("entity"), dict) else {})

    @r.delete("/api/gamestudio/{sid}/bible/entity/{kind}/{eid}", dependencies=[Depends(require_key)])
    async def bi_del(sid: str, kind: str, eid: str, tenant: str = Depends(current_tenant)):
        return await bcall(B.remove_entity, tenant, sid, kind, eid)

    @r.post("/api/gamestudio/{sid}/bible/section", dependencies=[Depends(require_key)])
    async def bi_sec(sid: str, body: Any = Body(default=None), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await bcall(B.set_section, tenant, sid, str(b.get("section") or ""), b.get("value"))

    @r.post("/api/gamestudio/{sid}/bible/{what}", dependencies=[Depends(require_key)])
    async def bi_do(sid: str, what: str, body: Any = Body(default=None), tenant: str = Depends(current_tenant)):
        b = _b(body)
        if what == "generate":
            try:
                n = int(b.get("n") or 3)
            except (TypeError, ValueError):
                n = 3
            return await bcall(B.generate, tenant, sid, str(b.get("kind") or ""), n, str(b.get("words") or ""))
        if what == "seed":
            return await bcall(B.seed, tenant, sid)
        if what == "accept":
            ids = [str(x) for x in b.get("ids") or []] if isinstance(b.get("ids"), list) else None
            return await bcall(B.accept, tenant, sid, ids)
        if what == "reject":
            return await bcall(B.reject, tenant, sid)
        if what == "simulate":
            try:
                runs = int(b.get("runs") or B.SIM_RUNS)
            except (TypeError, ValueError):
                runs = B.SIM_RUNS
            return await bcall(B.sim, tenant, sid, runs)
        if what == "apply":
            return await bcall(B.apply, tenant, sid)
        if what == "recurve":
            return await bcall(B.recurve, tenant, sid, str(b.get("kind") or ""))
        raise HTTPException(404, "generate | seed | accept | reject | simulate | apply | recurve")

    # ------------------------------------------------------------ v0.416 asset pipeline
    from . import assets as A

    async def acall(fn, *a, **kw):
        try:
            return await asyncio.to_thread(fn, *a, **kw)
        except (A.AssetError, service.GameError) as e:
            raise HTTPException(400, str(e))

    @r.get("/api/gamestudio/asset/{aid}/{v}")
    def asset_file(aid: str, v: int, exp: int = 0, sig: str = ""):
        p, media = A.file_for(aid, v, exp, sig)
        if p is None:
            raise HTTPException(404, "asset link purana / galat hai")
        return FileResponse(p, media_type=media, headers={"Cache-Control": "private, max-age=3600",
                                                          "X-Content-Type-Options": "nosniff"})

    @r.get("/api/gamestudio/{sid}/assets", dependencies=[Depends(require_key)])
    async def as_list(sid: str, tenant: str = Depends(current_tenant)):
        await acall(A.collect_models, tenant, sid)
        return await acall(A.assets, tenant, sid)

    @r.get("/api/gamestudio/{sid}/assets/suggest", dependencies=[Depends(require_key)])
    async def as_suggest(sid: str, tenant: str = Depends(current_tenant)):
        return {"suggest": await acall(A.suggest, tenant, sid)}

    @r.post("/api/gamestudio/{sid}/assets", dependencies=[Depends(require_key)])
    async def as_new(sid: str, body: Any = Body(default=None), tenant: str = Depends(current_tenant)):
        b = _b(body)
        spec = {k: b.get(k) for k in ("w", "h", "size", "quality", "palette_lock", "view", "preset", "seed", "mood", "bpm",
                                      "text", "voice", "language") if b.get(k) not in (None, "")}
        await acall(A.request, tenant, sid, str(b.get("kind") or ""), str(b.get("key") or ""), str(b.get("words") or ""), **spec)
        return await acall(A.assets, tenant, sid)

    @r.post("/api/gamestudio/{sid}/assets/spend", dependencies=[Depends(require_key)])
    async def as_spend(sid: str, body: Any = Body(default=None), tenant: str = Depends(current_tenant)):
        """HER TAP on the price card - the only way a paid asset starts."""
        ids = [str(x) for x in (_b(body).get("ids") or []) if isinstance(x, str)]
        return await acall(A.spend, tenant, sid, ids)

    @r.post("/api/gamestudio/{sid}/assets/upload", dependencies=[Depends(require_key)])
    async def as_upload(sid: str, body: Any = Body(default=None), tenant: str = Depends(current_tenant)):
        b = _b(body)
        await acall(A.upload, tenant, sid, str(b.get("kind") or ""), str(b.get("key") or ""), str(b.get("data") or ""),
                    str(b.get("words") or ""))
        return await acall(A.assets, tenant, sid)

    @r.post("/api/gamestudio/{sid}/assets/{key}/{what}", dependencies=[Depends(require_key)])
    async def as_do(sid: str, key: str, what: str, body: Any = Body(default=None), tenant: str = Depends(current_tenant)):
        b = _b(body)
        if what == "approve":
            try:
                v = int(b.get("v") or 0)
            except (TypeError, ValueError):
                v = 0
            await acall(A.approve, tenant, sid, key, v)
        elif what == "reject":
            await acall(A.reject, tenant, sid, key)
        elif what == "remove":
            await acall(A.remove, tenant, sid, key)
        else:
            raise HTTPException(404, "approve | reject | remove")
        return await acall(A.assets, tenant, sid)

    @r.post("/api/gamestudio/{sid}/assets-apply", dependencies=[Depends(require_key)])
    async def as_apply(sid: str, tenant: str = Depends(current_tenant)):
        return await acall(A.apply, tenant, sid)

    # ------------------------------------------------------------ v0.416 QA farm + bug tracker
    from . import qa as Q

    async def qcall(fn, *a, **kw):
        try:
            return await asyncio.to_thread(fn, *a, **kw)
        except (Q.QaError, service.GameError) as e:
            raise HTTPException(400, str(e))

    @r.get("/api/gamestudio/qa-shot/{sid}")
    def qa_shot(sid: str, rel: str = "", exp: int = 0, sig: str = ""):
        p = Q.shot_file(sid, rel, exp, sig)
        if p is None:
            raise HTTPException(404, "screenshot link purana / galat hai")
        return FileResponse(p, media_type="image/png", headers={"Cache-Control": "private, max-age=3600"})

    @r.get("/api/gamestudio/{sid}/qa", dependencies=[Depends(require_key)])
    async def qa_home(sid: str, tenant: str = Depends(current_tenant)):
        d = await qcall(Q.bugs, tenant, sid)
        st = await qcall(S.get, tenant, sid)
        d["last"] = Q.with_links(st["id"], d.get("last") or {})
        d["running"] = Q.running(st["id"])
        return d

    @r.post("/api/gamestudio/{sid}/qa/run", dependencies=[Depends(require_key)])
    async def qa_run(sid: str, tenant: str = Depends(current_tenant)):
        return await qcall(Q.start, tenant, sid)

    @r.post("/api/gamestudio/{sid}/qa/golden", dependencies=[Depends(require_key)])
    async def qa_golden(sid: str, body: Any = Body(default=None), tenant: str = Depends(current_tenant)):
        return await qcall(Q.approve_golden, tenant, sid, str(_b(body).get("rel") or ""))

    @r.post("/api/gamestudio/{sid}/bugs", dependencies=[Depends(require_key)])
    async def bug_new(sid: str, body: Any = Body(default=None), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await qcall(Q.report_bug, tenant, sid, str(b.get("title") or ""), str(b.get("detail") or ""),
                           str(b.get("severity") or "major"))

    @r.post("/api/gamestudio/{sid}/bugs/{number}/{what}", dependencies=[Depends(require_key)])
    async def bug_do(sid: str, number: str, what: str, tenant: str = Depends(current_tenant)):
        if what == "fix":
            return await qcall(Q.fix_bug, tenant, sid, number)
        if what in ("open", "wontfix", "duplicate", "fixed"):
            return await qcall(Q.set_bug, tenant, sid, number, what)
        raise HTTPException(404, "fix | open | wontfix | duplicate | fixed")

    # ------------------------------------------------------------ v0.416 game platforms
    from . import platforms as PF

    async def pcall(fn, *a, **kw):
        try:
            return await asyncio.to_thread(fn, *a, **kw)
        except (PF.PlatformError, service.GameError) as e:
            raise HTTPException(400, str(e))

    @r.get("/api/gamestudio/release/{rid}/{platform}")
    def rel_file(rid: str, platform: str, exp: int = 0, sig: str = ""):
        p = PF.kit_file(rid[4:], exp, sig) if rid.startswith("kit-") and platform == "kit" else PF.download_file(rid, platform, exp, sig)
        if p is None:
            raise HTTPException(404, "download link purana / galat hai")
        return FileResponse(p, filename=p.name, headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"})

    @r.get("/api/gamestudio/{sid}/releases", dependencies=[Depends(require_key)])
    async def rel_list(sid: str, tenant: str = Depends(current_tenant)):
        return await pcall(PF.releases, tenant, sid)

    @r.post("/api/gamestudio/{sid}/releases", dependencies=[Depends(require_key)])
    async def rel_new(sid: str, body: Any = Body(default=None), tenant: str = Depends(current_tenant)):
        b = _b(body)
        plats = [str(x) for x in (b.get("platforms") or []) if isinstance(x, str)]
        await pcall(PF.release, tenant, sid, plats, "aab" if b.get("android_format") == "aab" else "apk")
        return await pcall(PF.releases, tenant, sid)

    @r.get("/api/gamestudio/{sid}/store-kit", dependencies=[Depends(require_key)])
    async def rel_kit(sid: str, regen: bool = False, tenant: str = Depends(current_tenant)):
        return await pcall(PF.store_kit, tenant, sid, regen)

    @r.get("/api/gamestudio/{sid}/rating", dependencies=[Depends(require_key)])
    async def rel_rating(sid: str, tenant: str = Depends(current_tenant)):
        st = await pcall(S.get, tenant, sid)
        return await pcall(PF.rating_draft, tenant, st["id"])

    @r.post("/api/gamestudio/itch-key", dependencies=[Depends(require_key)])
    async def rel_itch_key(body: Any = Body(default=None), tenant: str = Depends(current_tenant)):
        """Her itch.io API key, typed in the app (never in chat); sealed."""
        return await pcall(PF.set_itch_key, tenant, str(_b(body).get("key") or ""))

    @r.post("/api/gamestudio/{sid}/releases/{rid}/itch", dependencies=[Depends(require_key)])
    async def rel_itch(sid: str, rid: str, body: Any = Body(default=None), tenant: str = Depends(current_tenant)):
        return await pcall(PF.itch_card, tenant, sid, rid, str(_b(body).get("target") or ""))

    @r.post("/api/gamestudio/{sid}/releases/{rid}/itch/push", dependencies=[Depends(require_key)])
    async def rel_itch_push(sid: str, rid: str, body: Any = Body(default=None), tenant: str = Depends(current_tenant)):
        """HER TAP on the itch.io card - the only way anything is uploaded."""
        return await pcall(PF.itch_push, tenant, sid, rid, str(_b(body).get("hash") or ""))

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
