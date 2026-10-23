"""HTTP routes of the Product Sahayak (/api/product/*). main.py: app.include_router(make_router(require_key, current_tenant)).

The ONLY way anything goes outside (GitHub release, public page): POST /api/product/publish/{id}/decide (her app tap, card hash).
The GitHub token is typed only here (PUT /api/product/github), sealed, never returned.
Public route: GET /api/product/page/{token} (random token, read-only HTML, CSP default-src 'none')."""
from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException
from fastapi.responses import HTMLResponse


def make_router(require_key, current_tenant) -> APIRouter:
    from . import service as S

    root = APIRouter()
    r = APIRouter(prefix="/api/product", dependencies=[Depends(require_key)])

    async def run(fn, *a, **k):
        try:
            return await asyncio.to_thread(fn, *a, **k)
        except (S.ProductError, ValueError) as e:
            raise HTTPException(400, str(e))

    def _b(body: dict | None) -> dict[str, Any]:
        return dict(body or {})

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
        keys = ("product", "who", "language", "app_ref", "site_ref", "rules", "morning_time", "repo", "scoring", "cycle_weeks",
                "harvest_days", "capacity", "north_star")
        return await run(S.save_settings, tenant, **{k: b[k] for k in keys if k in b})

    @r.post("/kpis")
    async def kpi(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.set_kpi, tenant, str(b.get("name") or ""), str(b.get("definition") or ""), str(b.get("unit") or ""),
                         b.get("target"), str(b.get("better") or "up"), str(b.get("kpi") or ""), bool(b.get("remove")))

    @r.put("/github")
    async def github(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.save_github, tenant, str(b.get("token") or ""), str(b.get("repo") or ""))

    @r.delete("/github")
    async def github_off(tenant: str = Depends(current_tenant)):
        return await run(S.forget_github, tenant)

    # ---- backlog
    @r.post("/harvest")
    async def harvest(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.harvest, tenant, _b(body).get("days"))

    @r.get("/opportunities")
    async def opps(status: str = "", q: str = "", tenant: str = Depends(current_tenant)):
        return await run(S.backlog, tenant, status, q)

    @r.post("/opportunities")
    async def opp_new(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.add_opportunity, tenant, str(b.get("title") or ""), str(b.get("problem") or ""), str(b.get("who") or ""),
                         str(b.get("source") or "her"), str(b.get("quote") or ""), str(b.get("note") or ""))

    @r.post("/ideas")
    async def ideas(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.add_ideas, tenant, str(b.get("text") or ""), str(b.get("file_id") or ""), str(b.get("source") or "idea"),
                         str(b.get("competitor") or ""))

    @r.get("/duplicates")
    async def dups(tenant: str = Depends(current_tenant)):
        return {"pairs": await run(S.duplicates, tenant)}

    @r.get("/opportunities/{ref}")
    async def opp_get(ref: str, tenant: str = Depends(current_tenant)):
        return await run(S.opportunity, tenant, ref)

    @r.patch("/opportunities/{ref}")
    async def opp_patch(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        keys = ("title", "problem", "who", "theme", "note", "goal", "status")
        return await run(S.update_opportunity, tenant, ref, **{k: b[k] for k in keys if k in b})

    @r.post("/opportunities/{ref}/{action}")
    async def opp_act(ref: str, action: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        if action == "score":
            return await run(S.score, tenant, ref, b.get("reach"), b.get("impact"), b.get("confidence"), b.get("effort"), b.get("ease"),
                             b.get("ice_impact"), b.get("ice_confidence"), bool(b.get("use_seen")))
        if action == "kano":
            return await run(S.kano_set, tenant, ref, b.get("answers"), str(b.get("category") or ""))
        if action == "merge":
            return await run(S.merge, tenant, ref, str(b.get("into") or ""))
        if action == "drop":
            return await run(S.drop, tenant, ref, str(b.get("reason") or ""))
        if action == "place":
            return await run(S.place, tenant, ref, str(b.get("bucket") or ""), str(b.get("theme") or ""))
        if action == "depends":
            return await run(S.set_depends, tenant, ref, b.get("on") or [], bool(b.get("remove")))
        if action == "solution":
            return await run(S.add_solution, tenant, ref, str(b.get("text") or ""), str(b.get("assumption") or ""), bool(b.get("chosen")))
        if action == "ship":
            return await run(S.ship, tenant, ref, str(b.get("day") or ""))
        if action == "result":
            return await run(S.before_after, tenant, ref, int(b.get("window") or 30))
        if action == "spec":
            return await run(S.write_spec, tenant, ref, str(b.get("note") or ""))
        raise HTTPException(404, "action")

    # ---- roadmap
    @r.get("/roadmap")
    async def roadmap(tenant: str = Depends(current_tenant)):
        return await run(S.roadmap, tenant)

    @r.post("/roadmap/plan")
    async def plan(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.plan, tenant, bool(_b(body).get("apply")))

    @r.post("/roadmap/files")
    async def roadmap_files(tenant: str = Depends(current_tenant)):
        return await run(S.roadmap_files, tenant)

    # ---- specs
    @r.get("/specs")
    async def specs(tenant: str = Depends(current_tenant)):
        return {"specs": await run(S.specs, tenant)}

    @r.get("/specs/{ref}")
    async def spec_get(ref: str, tenant: str = Depends(current_tenant)):
        return await run(S.spec, tenant, ref)

    @r.put("/specs/{ref}")
    async def spec_put(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.edit_spec, tenant, ref, _b(body).get("fields") or _b(body))

    @r.post("/specs/{ref}/revise")
    async def spec_revise(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.revise_spec, tenant, ref, str(_b(body).get("instruction") or ""))

    @r.get("/specs/{ref}/tasks")
    async def spec_tasks(ref: str, tenant: str = Depends(current_tenant)):
        return await run(S.tasks, tenant, ref)

    @r.post("/specs/{ref}/files")
    async def spec_files(ref: str, tenant: str = Depends(current_tenant)):
        return await run(S.spec_files, tenant, ref)

    # ---- releases
    @r.get("/releases")
    async def rels(tenant: str = Depends(current_tenant)):
        return {"releases": await run(S.releases, tenant)}

    @r.post("/releases")
    async def rel_new(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        gh = b.get("github")
        return await run(S.release_new, tenant, str(b.get("version") or ""), str(b.get("text") or ""), b.get("opps") or None,
                         str(b.get("since") or ""), None if gh is None else bool(gh), str(b.get("day") or ""))

    @r.get("/releases/{ref}")
    async def rel_get(ref: str, tenant: str = Depends(current_tenant)):
        return await run(S.release, tenant, ref)

    @r.put("/releases/{ref}")
    async def rel_put(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.release_edit, tenant, ref, b.get("hinglish"), b.get("english"), str(b.get("title") or ""))

    @r.post("/releases/{ref}/files")
    async def rel_files(ref: str, tenant: str = Depends(current_tenant)):
        return await run(S.release_files, tenant, ref)

    @r.get("/prs")
    async def prs(since: str = "", tenant: str = Depends(current_tenant)):
        return {"prs": await run(S.merged_prs, tenant, since)}

    # ---- publishing (her tap)
    @r.post("/publish")
    async def pub(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.publish_request, tenant, str(b.get("what") or "release"), str(b.get("ref") or ""), str(b.get("dest") or "copy"),
                         str(b.get("lang") or "both"))

    @r.get("/publish")
    async def pubs(status: str = "", tenant: str = Depends(current_tenant)):
        return {"cards": await run(S.publishes, tenant, status)}

    @r.post("/publish/{pid}/decide")
    async def decide(pid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.decide_publish, tenant, pid, bool(b.get("yes")), str(b.get("hash") or ""), True, str(b.get("reason") or ""))

    @r.post("/publish/{pid}/unpage")
    async def unpage(pid: str, tenant: str = Depends(current_tenant)):
        return await run(S.unpage, tenant, pid)

    # ---- metrics
    @r.get("/metrics")
    async def metrics(tenant: str = Depends(current_tenant)):
        return await run(S.metrics, tenant)

    @r.post("/metrics")
    async def metric_add(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.metric_add, tenant, str(b.get("kpi") or ""), b.get("value"), str(b.get("day") or ""), str(b.get("note") or ""))

    @root.get("/api/product/page/{token}")
    async def page(token: str):
        code, body = await asyncio.to_thread(S.public_page, token)
        return HTMLResponse(body, status_code=code, headers={
            "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'",
            "X-Robots-Tag": "noindex", "Referrer-Policy": "no-referrer", "Cache-Control": "no-store"})

    root.include_router(r)
    return root
