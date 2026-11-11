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

v0.420 Role packs (Phase 7: the Game Desk roles; each needs ITS employee hired for changes; reading is free):
GET    /api/gamedesk/worlds?studio=             Procedural World Engineer: worlds + kinds + defaults
POST   /api/gamedesk/worlds                     {words?, kind?, seed?, params?, studio?, key?}  generate + check (a draft)
GET    /api/gamedesk/world/{wid}                one world (checks, stats, files, demo)
POST   /api/gamedesk/world/{wid}/approve|reject|demo   her OK / no / build the walk-it demo (background)
POST   /api/gamedesk/worlds/apply               {studio}  approved worlds into the live game (HoolaWorld, no model)
GET    /api/gamedesk/world/{wid}/file/{name}?sig   preview.png | world.json | heightmap.png | world.glb (signed)
GET    /api/gamedesk/physics?studio=            Physics Engine Developer: setups (inputs, chosen settings, lab)
POST   /api/gamedesk/physics                    {words?, inputs?: {speed, wall, ticks, gravity, g3d}, studio?}  lab runs
GET    /api/gamedesk/physics/{pid}
POST   /api/gamedesk/physics/{pid}/approve|reject
POST   /api/gamedesk/physics/apply              {studio}  approved settings into the live game (HoolaPhysics)
GET    /api/gamedesk/audio?studio=              Spatial Audio Programmer: setups (zones, distances, measured report)
POST   /api/gamedesk/audio                      {words?, plan?: {zones: [{key, rt60, wet}], min_d, max_d, px_per_m}, studio?}
GET    /api/gamedesk/audio/{aid}                one setup
POST   /api/gamedesk/audio/{aid}/approve|reject
POST   /api/gamedesk/audio/apply                {studio}  approved setup into the live game (HoolaAudio)
GET    /api/gamedesk/audio/{aid}/file/{name}?sig   walkaround.wav | distance.wav | zones.wav (signed)
GET    /api/gamedesk/haptics?studio=            Haptics Engineer: pattern sets + checks + library + actuators
POST   /api/gamedesk/haptics                    {words?, patterns?: {name: [{t, d, a, s}]}, actuator?, studio?}
GET    /api/gamedesk/haptics/{hid}
POST   /api/gamedesk/haptics/{hid}/approve|reject
POST   /api/gamedesk/haptics/apply              {studio}  approved patterns into the live game (HoolaHaptics)
GET    /api/gamedesk/haptics/{hid}/file/{name}?sig   kit.zip | patterns.png (signed)
GET    /api/gamedesk/net?studio=                Multiplayer Programmer: setups (her numbers, the bot runs, verdict)
POST   /api/gamedesk/net                        {words?, inputs?: {players, tick, send, speed, size, interest}, studio?}
GET    /api/gamedesk/net/{nid}  POST /api/gamedesk/net/{nid}/approve|reject   GET .../file/kit.zip?sig
POST   /api/gamedesk/net/{nid}/server           {url}  HER game server (wss:// only; Hoola hosts nothing)
GET    /api/gamedesk/xr?studio=                 AR / VR Engineer: setups (comfort, gestures, demo play link)
POST   /api/gamedesk/xr                         {words?, settings?: {mode, locomotion, turn, snap_deg, seated, ui_m, text_deg, fps}, studio?}
GET    /api/gamedesk/xr/{xid}  POST /api/gamedesk/xr/{xid}/approve|reject  POST /api/gamedesk/xr/apply {studio}
GET    /api/gamedesk/sim?studio=    POST /api/gamedesk/sim {words?, kind?: orbit|flight|driving, params?, scenario?, studio?}
GET    /api/gamedesk/sim/{id}       POST /api/gamedesk/sim/{id}/approve|reject   POST /api/gamedesk/sim/apply {studio}
GET    /api/gamedesk/sim/{id}/file/log.csv|plot.png?sig
GET    /api/gamedesk/twin           POST /api/gamedesk/twin {words?, model?: {stations, data_map, shift_hours, days}, actual?: [per day]}
GET    /api/gamedesk/twin/{id}      POST /api/gamedesk/twin/{id}/approve|reject   GET .../file/layout.png?sig
GET    /api/gamedesk/vfx            POST /api/gamedesk/vfx {plan?: {show, seq, shots, sources, working, view, workers, fail_rate...}}
GET    /api/gamedesk/vfx/{id}       POST /api/gamedesk/vfx/{id}/approve|reject   GET .../file/kit.zip?sig

v0.425 Hoola Runtime + Ask Hoola in the editor (Game Engine plan Phase 8):
GET    /api/gamedesk/runtime/{sid}              settings (on, telemetry, kids), last replay tests
POST   /api/gamedesk/runtime/{sid}              {on?, telemetry?}  telemetry refused for a children's game
POST   /api/gamedesk/runtime/{sid}/replay       start a replay test (bot run, same seed again, the replay played back)
GET    /api/gamedesk/runtime/{sid}/replay/{rid} the recorded replay JSON
GET    /api/gamedesk/runtime/{sid}/telemetry    dashboard (installs, sessions, D1 / D7, funnel)   DELETE: wipe it
POST   /play/{token}/t                          telemetry from the game (same host as the play link; always 204)
GET    /api/gamedesk/liveops/{sid}[/dashboard|/crashes|/money]   v0.428 live ops view, D30 / DAU / balance, crash groups, money
POST   /api/gamedesk/liveops/{sid}/experiments[/{key}/start|stop]  A/B tests (start / stop = her tap); GET .../{key} = result
POST   /api/gamedesk/liveops/{sid}/events[/{key}/approve|cancel]   live events calendar (approve = her tap)
POST   /api/gamedesk/liveops/{sid}/crashes/{sig}/hotfix | /patch_check | /money (CSV)
GET    /play/{token}/live                       what the game reads: running tests + approved events (same host)
GET|POST /api/gamedesk/big[/{pid}/tasks[/{tno}[/reopen]]]   v0.433 big-studio projects in Unity / Unreal / Godot
GET    /api/gamedesk/big/plugin/{unity|unreal}.zip   the Hoola Crew editor plugin (MCP client; writes only on her Apply)
GET|POST /api/gamedesk/scenes/{sid}[/{name}/approve|reject]  v0.456 scenes as CHECKED DATA: the model writes a spec,
       Hoola generates the .tscn and loads it in the real engine; a scene may never carry script source
GET    /api/gamedesk/provenance/{sid}[/steam]   v0.455 where every shipped piece came from, the human record, and
       a DRAFT store answer she signs (generated / code-made / her own files kept apart)
GET|POST /api/gamedesk/arena[/briefs|/{rid}[/stop]|/compare/{a}/{b}|/duel]  v0.447 Game Arena (owner only): fixed briefs,
       runs judged by PLAYING, measured originality, run-vs-run compare, blind duels vs a rival's public game
GET    /api/gamedesk/editor/tokens  POST {label} (shown ONCE)  DELETE /api/gamedesk/editor/tokens/{id}
GET    /api/gamedesk/editor/plugin.zip          the Godot editor plugin (addons/hoola)
POST   /mcp/gamedesk                            MCP (JSON-RPC 2.0, Streamable HTTP) with 'Authorization: Bearer <editor token>'

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
GET    /api/gamestudio/{id}/library?q=&kind=model|texture&source=   v0.811 free CC0 library search (Kenney / Poly Haven / ambientCG)
POST   /api/gamestudio/{id}/library             {source, id, kind, key?}  one item as a draft asset (her OK still needed)
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
import json
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

    @r.get("/api/gamestudio/{sid}/library", dependencies=[Depends(require_key)])
    async def lib_search(sid: str, q: str = "", kind: str = "model", source: str = "", tenant: str = Depends(current_tenant)):
        """v0.811 the free library (Kenney on disk, Poly Haven, ambientCG - all CC0): search only, nothing is added."""
        from . import library as L
        await acall(A._studio, tenant, sid)                 # her project, or 404 like every other route here
        try:
            return await acall(L.search, q[:120], kind, source)
        except L.LibraryError as e:
            raise HTTPException(400, str(e)) from None

    @r.post("/api/gamestudio/{sid}/library", dependencies=[Depends(require_key)])
    async def lib_add(sid: str, body: Any = Body(default=None), tenant: str = Depends(current_tenant)):
        """One free library item as a DRAFT asset (checked by its bytes); it enters the game only after her OK."""
        from . import library as L
        b = _b(body)
        await acall(L.add, tenant, sid, str(b.get("source") or ""), str(b.get("id") or ""), str(b.get("kind") or "model"),
                    str(b.get("key") or ""))
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

    # ------------------------------------------------------------ v0.420 role packs: Procedural World + Physics
    from . import physics as PH
    from . import world as WD

    def _working(tenant: str, key: str, name: str) -> None:
        from ..employee import hire
        if not hire.is_working(tenant, key):
            raise HTTPException(400, f"{name} abhi hired nahi hai (ya paused hai). Employees mein hire kijiye.")

    @r.get("/api/gamedesk/worlds", dependencies=[Depends(require_key)])
    async def worlds_list(studio: str = "", tenant: str = Depends(current_tenant)):
        from ..employee import hire
        return {"worlds": await call(WD.worlds, tenant, studio), "kinds": list(WD.KINDS), "defaults": WD.DEFAULTS,
                "legend": {k: [n for n, _c, _w in v] for k, v in WD.LEGEND.items()},
                "hired": await asyncio.to_thread(hire.is_working, tenant, WD.KEY)}

    @r.post("/api/gamedesk/worlds", dependencies=[Depends(require_key)])
    async def worlds_make(body: Any = Body(default=None), tenant: str = Depends(current_tenant)):
        b = _b(body)
        _working(tenant, WD.KEY, "Procedural World Engineer")
        seed = b.get("seed")
        return await call(WD.make, tenant, str(b.get("words") or ""), str(b.get("kind") or ""),
                          int(seed) if str(seed or "").lstrip("-").isdigit() else None,
                          b.get("params") if isinstance(b.get("params"), dict) else None,
                          str(b.get("studio") or ""), str(b.get("key") or ""))

    @r.post("/api/gamedesk/worlds/apply", dependencies=[Depends(require_key)])
    async def worlds_apply(body: Any = Body(default=None), tenant: str = Depends(current_tenant)):
        _working(tenant, WD.KEY, "Procedural World Engineer")
        return await call(WD.apply, tenant, str(_b(body).get("studio") or ""))

    @r.get("/api/gamedesk/world/{wid}", dependencies=[Depends(require_key)])
    async def world_get(wid: str, tenant: str = Depends(current_tenant)):
        return await call(WD.get, tenant, wid)

    @r.post("/api/gamedesk/world/{wid}/{what}", dependencies=[Depends(require_key)])
    async def world_do(wid: str, what: str, tenant: str = Depends(current_tenant)):
        _working(tenant, WD.KEY, "Procedural World Engineer")
        fn = {"approve": WD.approve, "reject": WD.reject, "demo": WD.demo}.get(what)
        if fn is None:
            raise HTTPException(404, "approve | reject | demo")
        return await call(fn, tenant, wid)

    @r.get("/api/gamedesk/world/{wid}/file/{name}")
    def world_file(wid: str, name: str, sig: str = ""):
        p = WD.world_file(wid, name, sig)
        if p is None:
            raise HTTPException(404, "link purana / galat hai")
        media = {".png": "image/png", ".json": "application/json", ".glb": "model/gltf-binary"}.get(p.suffix, "application/octet-stream")
        return FileResponse(p, media_type=media, headers={"X-Content-Type-Options": "nosniff", "Cache-Control": "private, max-age=600"},
                            filename=None if p.suffix == ".png" else p.name)

    @r.get("/api/gamedesk/physics", dependencies=[Depends(require_key)])
    async def physics_list(studio: str = "", tenant: str = Depends(current_tenant)):
        from ..employee import hire
        return {"setups": await call(PH.setups, tenant, studio), "defaults": PH.DEFAULTS, "limits": PH.LIMITS,
                "hired": await asyncio.to_thread(hire.is_working, tenant, PH.KEY)}

    @r.post("/api/gamedesk/physics", dependencies=[Depends(require_key)])
    async def physics_make(body: Any = Body(default=None), tenant: str = Depends(current_tenant)):
        b = _b(body)
        _working(tenant, PH.KEY, "Physics Engine Developer")
        return await call(PH.setup, tenant, str(b.get("words") or ""),
                          b.get("inputs") if isinstance(b.get("inputs"), dict) else None, str(b.get("studio") or ""))

    @r.post("/api/gamedesk/physics/apply", dependencies=[Depends(require_key)])
    async def physics_apply(body: Any = Body(default=None), tenant: str = Depends(current_tenant)):
        _working(tenant, PH.KEY, "Physics Engine Developer")
        return await call(PH.apply, tenant, str(_b(body).get("studio") or ""))

    @r.get("/api/gamedesk/physics/{pid}", dependencies=[Depends(require_key)])
    async def physics_get(pid: str, tenant: str = Depends(current_tenant)):
        return await call(PH.get, tenant, pid)

    @r.post("/api/gamedesk/physics/{pid}/{what}", dependencies=[Depends(require_key)])
    async def physics_do(pid: str, what: str, tenant: str = Depends(current_tenant)):
        _working(tenant, PH.KEY, "Physics Engine Developer")
        fn = {"approve": PH.approve, "reject": PH.reject}.get(what)
        if fn is None:
            raise HTTPException(404, "approve | reject")
        return await call(fn, tenant, pid)

    # ------------------------------------------------------------ v0.421 role packs: Spatial Audio + Haptics
    from . import audio as AU
    from . import haptics as HP

    def _pack_routes(base: str, mod, key: str, name: str, lister: str, maker, files_fn, media: dict) -> None:
        @r.get(f"/api/gamedesk/{base}", dependencies=[Depends(require_key)])
        async def _list(studio: str = "", tenant: str = Depends(current_tenant)):
            from ..employee import hire
            extra = ({"library": sorted(HP.LIBRARY), "actuators": HP.ACTUATORS} if mod is HP else
                     {"zone_presets": AU.ZONE_PRESETS} if mod is AU else
                     {"networks": NC.NETWORKS, "defaults": NC.DEFAULTS} if mod is NC else
                     {"defaults": SM.DEFAULTS, "kinds": list(SM.KINDS)} if mod is SM else
                     {"example": TW.EXAMPLE} if mod is TW else {"example": VX.EXAMPLE} if mod is VX else {"defaults": XR.DEFAULTS})
            return {lister: await call(getattr(mod, lister), tenant, studio), "hired": await asyncio.to_thread(hire.is_working, tenant, key), **extra}

        @r.post(f"/api/gamedesk/{base}", dependencies=[Depends(require_key)])
        async def _make(body: Any = Body(default=None), tenant: str = Depends(current_tenant)):
            _working(tenant, key, name)
            return await call(maker, tenant, _b(body))

        @r.post(f"/api/gamedesk/{base}/apply", dependencies=[Depends(require_key)])
        async def _apply(body: Any = Body(default=None), tenant: str = Depends(current_tenant)):
            _working(tenant, key, name)
            return await call(mod.apply, tenant, str(_b(body).get("studio") or ""))

        @r.get(f"/api/gamedesk/{base}/{{xid}}", dependencies=[Depends(require_key)])
        async def _get(xid: str, tenant: str = Depends(current_tenant)):
            return await call(mod.get, tenant, xid)

        @r.post(f"/api/gamedesk/{base}/{{xid}}/{{what}}", dependencies=[Depends(require_key)])
        async def _do(xid: str, what: str, tenant: str = Depends(current_tenant)):
            _working(tenant, key, name)
            fn = {"approve": mod.approve, "reject": mod.reject}.get(what)
            if fn is None:
                raise HTTPException(404, "approve | reject")
            return await call(fn, tenant, xid)

        @r.get(f"/api/gamedesk/{base}/{{xid}}/file/{{fname}}")
        def _file(xid: str, fname: str, sig: str = ""):
            p = files_fn(xid, fname, sig)
            if p is None:
                raise HTTPException(404, "link purana / galat hai")
            return FileResponse(p, media_type=media.get(p.suffix, "application/octet-stream"),
                                headers={"X-Content-Type-Options": "nosniff", "Cache-Control": "private, max-age=600"},
                                filename=p.name if p.suffix == ".zip" else None)

    def _audio_make(tenant: str, b: dict):
        return AU.setup(tenant, str(b.get("words") or ""), b.get("plan") if isinstance(b.get("plan"), dict) else None,
                        str(b.get("studio") or ""))

    def _haptics_make(tenant: str, b: dict):
        return HP.make(tenant, str(b.get("words") or ""), b.get("patterns") if isinstance(b.get("patterns"), dict) else None,
                       str(b.get("actuator") or "phone_lra"), str(b.get("studio") or ""))

    from . import netcode as NC
    from . import xr as XR

    @r.post("/api/gamedesk/net/{nid}/server", dependencies=[Depends(require_key)])
    async def net_server(nid: str, body: Any = Body(default=None), tenant: str = Depends(current_tenant)):
        _working(tenant, NC.KEY, "Multiplayer Network Programmer")
        return await call(NC.set_server, tenant, nid, str(_b(body).get("url") or ""))

    def _net_make(tenant: str, b: dict):
        return NC.setup(tenant, str(b.get("words") or ""), b.get("inputs") if isinstance(b.get("inputs"), dict) else None,
                        str(b.get("studio") or ""))

    def _xr_make(tenant: str, b: dict):
        return XR.setup(tenant, str(b.get("words") or ""), b.get("settings") if isinstance(b.get("settings"), dict) else None,
                        str(b.get("studio") or ""))

    from . import sim as SM
    from . import twin as TW
    from . import vfx as VX

    def _sim_make(tenant: str, b: dict):
        return SM.setup(tenant, str(b.get("words") or ""), str(b.get("kind") or ""),
                        b.get("params") if isinstance(b.get("params"), dict) else None,
                        b.get("scenario") if isinstance(b.get("scenario"), dict) else None, str(b.get("studio") or ""))

    def _twin_make(tenant: str, b: dict):
        return TW.setup(tenant, str(b.get("words") or ""), b.get("model") if isinstance(b.get("model"), dict) else None,
                        b.get("actual") if isinstance(b.get("actual"), list) else None, str(b.get("name") or ""))

    def _vfx_make(tenant: str, b: dict):
        return VX.setup(tenant, str(b.get("words") or ""), b.get("plan") if isinstance(b.get("plan"), dict) else None)

    _pack_routes("sim", SM, SM.KEY, "Simulation Software Engineer", "setups", _sim_make, SM.sim_file,
                 {".csv": "text/csv", ".png": "image/png"})
    _pack_routes("twin", TW, TW.KEY, "Digital Twin Architect", "setups", _twin_make, TW.twin_file, {".png": "image/png"})
    _pack_routes("vfx", VX, VX.KEY, "VFX Pipeline Technical Director", "setups", _vfx_make, VX.vfx_file, {".zip": "application/zip"})
    _pack_routes("net", NC, NC.KEY, "Multiplayer Network Programmer", "setups", _net_make, NC.net_file, {".zip": "application/zip"})
    _pack_routes("xr", XR, XR.KEY, "AR / VR Interaction Engineer", "setups", _xr_make, lambda *a: None, {})
    _pack_routes("audio", AU, AU.KEY, "Spatial Audio Systems Programmer", "setups", _audio_make, AU.audio_file, {".wav": "audio/wav"})
    _pack_routes("haptics", HP, HP.KEY, "Haptic Feedback Systems Engineer", "sets", _haptics_make, HP.haptics_file,
                 {".zip": "application/zip", ".png": "image/png"})

    # ------------------------------------------------------------ v0.425 Hoola Runtime + Ask Hoola in the editor (MCP)
    from . import editor as ED
    from . import runtime as RT

    def _owner_game_dev(tenant: str) -> None:
        _working(tenant, "game_dev", "Game Developer")

    @r.get("/api/gamedesk/runtime/{sid}", dependencies=[Depends(require_key)])
    async def rt_get(sid: str, tenant: str = Depends(current_tenant)):
        return await call(RT.settings, tenant, sid)

    @r.post("/api/gamedesk/runtime/{sid}", dependencies=[Depends(require_key)])
    async def rt_set(sid: str, body: Any = Body(default=None), tenant: str = Depends(current_tenant)):
        _owner_game_dev(tenant)
        b = _b(body)
        return await call(RT.set_runtime, tenant, sid, b.get("on") if "on" in b else None,
                          b.get("telemetry") if "telemetry" in b else None)

    @r.post("/api/gamedesk/runtime/{sid}/replay", dependencies=[Depends(require_key)])
    async def rt_replay(sid: str, tenant: str = Depends(current_tenant)):
        _owner_game_dev(tenant)
        return await call(RT.start_replay_test, tenant, sid)

    @r.get("/api/gamedesk/runtime/{sid}/replay/{rid}", dependencies=[Depends(require_key)])
    async def rt_replay_file(sid: str, rid: str, tenant: str = Depends(current_tenant)):
        p = await call(RT.replay_file, tenant, sid, rid)
        if p is None:
            raise HTTPException(404, "replay nahi mila")
        return FileResponse(p, media_type="application/json", filename=p.name)

    @r.get("/api/gamedesk/runtime/{sid}/telemetry", dependencies=[Depends(require_key)])
    async def rt_tel(sid: str, tenant: str = Depends(current_tenant)):
        return await call(RT.dashboard, tenant, sid)

    @r.delete("/api/gamedesk/runtime/{sid}/telemetry", dependencies=[Depends(require_key)])
    async def rt_tel_del(sid: str, tenant: str = Depends(current_tenant)):
        _owner_game_dev(tenant)
        return await call(RT.delete_telemetry, tenant, sid)

    @r.post("/play/{token}/t")
    async def rt_ingest(token: str, request: Request):
        raw = await request.body()
        await asyncio.to_thread(RT.ingest, token, raw[: RT.MAX_BODY + 1])
        return Response(status_code=204, headers={"Cache-Control": "no-store"})

    # ------------------------------------------------------------ v0.428 Live ops (A/B, live events, crashes, patches, money)
    from . import liveops as LO

    @r.get("/api/gamedesk/liveops/{sid}", dependencies=[Depends(require_key)])
    async def lo_get(sid: str, tenant: str = Depends(current_tenant)):
        return await call(LO.view, tenant, sid)

    @r.get("/api/gamedesk/liveops/{sid}/dashboard", dependencies=[Depends(require_key)])
    async def lo_dash(sid: str, tenant: str = Depends(current_tenant)):
        return await call(LO.dashboard, tenant, sid)

    @r.post("/api/gamedesk/liveops/{sid}/experiments", dependencies=[Depends(require_key)])
    async def lo_exp_add(sid: str, body: Any = Body(default=None), tenant: str = Depends(current_tenant)):
        _owner_game_dev(tenant)
        b = _b(body)
        return await call(LO.add_experiment, tenant, sid, b.get("key"), b.get("title") or "", b.get("goal") or "win",
                          b.get("variants") if isinstance(b.get("variants"), list) else None, b.get("mde") or 0.05)

    @r.get("/api/gamedesk/liveops/{sid}/experiments/{key}", dependencies=[Depends(require_key)])
    async def lo_exp_res(sid: str, key: str, tenant: str = Depends(current_tenant)):
        return await call(LO.results, tenant, sid, key)

    @r.post("/api/gamedesk/liveops/{sid}/experiments/{key}/start", dependencies=[Depends(require_key)])
    async def lo_exp_start(sid: str, key: str, tenant: str = Depends(current_tenant)):
        _owner_game_dev(tenant)
        return await call(LO.start_experiment, tenant, sid, key)

    @r.post("/api/gamedesk/liveops/{sid}/experiments/{key}/stop", dependencies=[Depends(require_key)])
    async def lo_exp_stop(sid: str, key: str, body: Any = Body(default=None), tenant: str = Depends(current_tenant)):
        _owner_game_dev(tenant)
        return await call(LO.stop_experiment, tenant, sid, key, str(_b(body).get("ship") or ""))

    @r.post("/api/gamedesk/liveops/{sid}/events", dependencies=[Depends(require_key)])
    async def lo_ev_add(sid: str, body: Any = Body(default=None), tenant: str = Depends(current_tenant)):
        _owner_game_dev(tenant)
        b = _b(body)
        return await call(LO.add_event, tenant, sid, b.get("key"), b.get("title") or "", b.get("starts"), b.get("ends"), b.get("set"))

    @r.post("/api/gamedesk/liveops/{sid}/events/{key}/approve", dependencies=[Depends(require_key)])
    async def lo_ev_ok(sid: str, key: str, tenant: str = Depends(current_tenant)):
        _owner_game_dev(tenant)
        return await call(LO.approve_event, tenant, sid, key)

    @r.post("/api/gamedesk/liveops/{sid}/events/{key}/cancel", dependencies=[Depends(require_key)])
    async def lo_ev_cancel(sid: str, key: str, tenant: str = Depends(current_tenant)):
        _owner_game_dev(tenant)
        return await call(LO.cancel_event, tenant, sid, key)

    @r.get("/api/gamedesk/liveops/{sid}/crashes", dependencies=[Depends(require_key)])
    async def lo_crashes(sid: str, tenant: str = Depends(current_tenant)):
        return await call(LO.crashes, tenant, sid)

    @r.post("/api/gamedesk/liveops/{sid}/crashes/{sig}/hotfix", dependencies=[Depends(require_key)])
    async def lo_hotfix(sid: str, sig: str, tenant: str = Depends(current_tenant)):
        _owner_game_dev(tenant)
        return await call(LO.hotfix, tenant, sid, sig)

    @r.post("/api/gamedesk/liveops/{sid}/patch_check", dependencies=[Depends(require_key)])
    async def lo_patch(sid: str, tenant: str = Depends(current_tenant)):
        _owner_game_dev(tenant)
        return await call(LO.start_patch_check, tenant, sid)

    @r.get("/api/gamedesk/liveops/{sid}/money", dependencies=[Depends(require_key)])
    async def lo_money(sid: str, tenant: str = Depends(current_tenant)):
        return await call(LO.money, tenant, sid)

    @r.post("/api/gamedesk/liveops/{sid}/money", dependencies=[Depends(require_key)])
    async def lo_money_in(sid: str, body: Any = Body(default=None), tenant: str = Depends(current_tenant)):
        _owner_game_dev(tenant)
        b = _b(body)
        return await call(LO.import_revenue, tenant, sid, str(b.get("csv") or ""), str(b.get("source") or ""))

    # ------------------------------------------------------------ v0.456 Scenes as checked data (the ceiling)
    from . import scene as SC

    @r.get("/api/gamedesk/scenes/{sid}", dependencies=[Depends(require_key)])
    async def sc_view(sid: str, tenant: str = Depends(current_tenant)):
        return await call(SC.view, tenant, sid)

    @r.post("/api/gamedesk/scenes/{sid}", dependencies=[Depends(require_key)])
    async def sc_new(sid: str, body: Any = Body(default=None), tenant: str = Depends(current_tenant)):
        _owner_game_dev(tenant)
        b = _b(body)
        return await call(SC.propose, tenant, sid, str(b.get("words") or ""), str(b.get("name") or ""))

    @r.post("/api/gamedesk/scenes/{sid}/{name}/approve", dependencies=[Depends(require_key)])
    async def sc_ok(sid: str, name: str, tenant: str = Depends(current_tenant)):
        _owner_game_dev(tenant)
        return await call(SC.approve, tenant, sid, name)

    @r.post("/api/gamedesk/scenes/{sid}/{name}/reject", dependencies=[Depends(require_key)])
    async def sc_no(sid: str, name: str, tenant: str = Depends(current_tenant)):
        _owner_game_dev(tenant)
        return await call(SC.reject, tenant, sid, name)

    # ------------------------------------------------------------ v0.455 Provenance (what shipped, and what is hers)
    from . import provenance as PV

    @r.get("/api/gamedesk/provenance/{sid}", dependencies=[Depends(require_key)])
    async def pv_sheet(sid: str, tenant: str = Depends(current_tenant)):
        return await call(PV.sheet, tenant, sid)

    @r.get("/api/gamedesk/provenance/{sid}/steam", dependencies=[Depends(require_key)])
    async def pv_steam(sid: str, tenant: str = Depends(current_tenant)):
        return await call(PV.steam_survey, tenant, sid)

    # ------------------------------------------------------------ v0.447 Game Arena (is a Hoola game any good? as numbers)
    from . import arena as AR

    def _owner(tenant: str) -> None:
        if tenant != "default":
            raise HTTPException(403, "arena sirf owner ke liye hai")

    @r.get("/api/gamedesk/arena", dependencies=[Depends(require_key)])
    async def ar_runs(tenant: str = Depends(current_tenant)):
        _owner(tenant)
        return {"runs": await call(AR.runs, 20), "set": AR.SET_V, "total_briefs": len(AR.brief_set()),
                "genres": sorted(AR.GENRES), "duels": await call(AR.duel_table)}

    @r.get("/api/gamedesk/arena/briefs", dependencies=[Depends(require_key)])
    async def ar_briefs(genre: str = "", limit: int = 40, tenant: str = Depends(current_tenant)):
        _owner(tenant)
        return await call(AR.catalogue, genre, limit)

    @r.post("/api/gamedesk/arena", dependencies=[Depends(require_key)])
    async def ar_start(body: Any = Body(default=None), tenant: str = Depends(current_tenant)):
        _owner(tenant)
        b = _b(body)
        return await call(AR.start, int(b.get("n") or 8), int(b.get("seed") or 1), float(b.get("budget_inr") or 0),
                          str(b.get("note") or ""))

    @r.get("/api/gamedesk/arena/{rid}", dependencies=[Depends(require_key)])
    async def ar_view(rid: str, tenant: str = Depends(current_tenant)):
        _owner(tenant)
        return await call(AR.view, rid)

    @r.post("/api/gamedesk/arena/{rid}/stop", dependencies=[Depends(require_key)])
    async def ar_stop(rid: str, tenant: str = Depends(current_tenant)):
        _owner(tenant)
        return await call(AR.stop, rid)

    @r.get("/api/gamedesk/arena/compare/{a}/{b}", dependencies=[Depends(require_key)])
    async def ar_compare(a: str, b: str, tenant: str = Depends(current_tenant)):
        _owner(tenant)
        return await call(AR.compare, a, b)

    @r.post("/api/gamedesk/arena/duel", dependencies=[Depends(require_key)])
    async def ar_duel(body: Any = Body(default=None), tenant: str = Depends(current_tenant)):
        _owner(tenant)
        b = _b(body)
        return await call(AR.duel, str(b.get("brief") or ""), str(b.get("rival") or ""), str(b.get("url") or ""),
                          str(b.get("game") or ""))

    # ------------------------------------------------------------ v0.433 Big-studio mode (Unity / Unreal on her machines)
    from . import bigstudio as BS

    @r.get("/api/gamedesk/big", dependencies=[Depends(require_key)])
    async def bs_list(tenant: str = Depends(current_tenant)):
        return {"projects": await call(BS.projects, tenant), "mcp_url": service.base_url().rstrip("/") + "/mcp/gamedesk",
                "engines": BS.ENGINE_NAMES}

    @r.post("/api/gamedesk/big", dependencies=[Depends(require_key)])
    async def bs_new(body: Any = Body(default=None), tenant: str = Depends(current_tenant)):
        _owner_game_dev(tenant)
        b = _b(body)
        return await call(BS.new_project, tenant, b.get("engine"), b.get("title"), b.get("engine_version") or "",
                          b.get("about") or "", b.get("module") or "")

    @r.post("/api/gamedesk/big/{pid}/tasks", dependencies=[Depends(require_key)])
    async def bs_task_add(pid: str, body: Any = Body(default=None), tenant: str = Depends(current_tenant)):
        _owner_game_dev(tenant)
        b = _b(body)
        return await call(BS.add_task, tenant, pid, b.get("title"), b.get("detail") or "", b.get("priority") or 2)

    @r.get("/api/gamedesk/big/{pid}/tasks/{tno}", dependencies=[Depends(require_key)])
    async def bs_task_get(pid: str, tno: str, tenant: str = Depends(current_tenant)):
        return await call(BS.task, tenant, pid, tno)

    @r.post("/api/gamedesk/big/{pid}/tasks/{tno}/reopen", dependencies=[Depends(require_key)])
    async def bs_task_reopen(pid: str, tno: str, body: Any = Body(default=None), tenant: str = Depends(current_tenant)):
        _owner_game_dev(tenant)
        return await call(BS.reopen, tenant, pid, tno, str(_b(body).get("note") or ""))

    @r.get("/api/gamedesk/big/plugin/{engine}.zip", dependencies=[Depends(require_key)])
    async def bs_plugin(engine: str):
        if engine not in ("unity", "unreal"):
            raise HTTPException(404, "unity or unreal")
        name = "hoola_crew_unity.zip" if engine == "unity" else "hoola_crew_unreal.zip"
        return Response(content=BS.plugin_zip(engine, service.base_url()), media_type="application/zip",
                        headers={"Content-Disposition": f'attachment; filename="{name}"'})

    @r.get("/play/{token}/live")
    async def lo_live(token: str):
        d = await asyncio.to_thread(LO.live_config, token)
        return Response(content=json.dumps(d), media_type="application/json",
                        headers={"Cache-Control": "public, max-age=60", "X-Content-Type-Options": "nosniff"})

    @r.get("/api/gamedesk/editor/tokens", dependencies=[Depends(require_key)])
    async def ed_tokens(tenant: str = Depends(current_tenant)):
        return {"tokens": await call(ED.tokens, tenant), "mcp_url": service.base_url().rstrip("/") + "/mcp/gamedesk"}

    @r.post("/api/gamedesk/editor/tokens", dependencies=[Depends(require_key)])
    async def ed_token_new(body: Any = Body(default=None), tenant: str = Depends(current_tenant)):
        _owner_game_dev(tenant)
        return await call(ED.create_token, tenant, str(_b(body).get("label") or ""))

    @r.delete("/api/gamedesk/editor/tokens/{tid}", dependencies=[Depends(require_key)])
    async def ed_token_del(tid: str, tenant: str = Depends(current_tenant)):
        return await call(ED.revoke, tenant, tid)

    @r.get("/api/gamedesk/editor/plugin.zip", dependencies=[Depends(require_key)])
    async def ed_plugin(tenant: str = Depends(current_tenant)):
        data = ED.plugin_zip(service.base_url())
        return Response(content=data, media_type="application/zip",
                        headers={"Content-Disposition": 'attachment; filename="hoola_godot_plugin.zip"'})

    @r.post("/mcp/gamedesk")
    async def mcp(request: Request):
        who = await asyncio.to_thread(ED.auth, request.headers.get("authorization", ""))
        if who is None:
            return Response(status_code=401, headers={"WWW-Authenticate": 'Bearer realm="hoola-gamedesk"'},
                            content=b'{"error":"an editor token from Hoola (Game Desk > Editor) is needed"}', media_type="application/json")
        raw = await request.body()
        if len(raw) > 64 * 1024:
            raise HTTPException(413, "too big")
        try:
            body = json.loads(raw.decode("utf-8") or "null")
        except Exception:                               # noqa: BLE001
            return Response(content=json.dumps(ED._err(None, -32700, "Parse error")), media_type="application/json")
        hdr = request.headers.get("mcp-protocol-version", "")
        out = await asyncio.to_thread(ED.handle, who[0], who[1], body, hdr)
        if out is None:
            return Response(status_code=202, headers={"MCP-Protocol-Version": ED.MODERN[0]})
        return Response(content=json.dumps(out, ensure_ascii=False), media_type="application/json",
                        headers={"MCP-Protocol-Version": ED.MODERN[0]})

    @r.get("/mcp/gamedesk")
    async def mcp_get():
        return Response(status_code=405, headers={"Allow": "POST"})

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
