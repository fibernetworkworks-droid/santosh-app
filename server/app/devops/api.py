"""HTTP routes of the DevOps Sahayak (/api/devops/*). main.py: app.include_router(make_router(require_key, current_tenant)).

Her taps (the ONLY ways these happen): POST /api/devops/deploys/{id}/decide (production deploy / rollback / environment approval),
POST /api/devops/runs/{key}/rerun (re-run failed CI jobs), PUT /api/devops/github (her token, typed in the app).
Public: POST /api/devops/collect/{collector_id} - the read-only collector on HER server, HMAC-signed (checked in service.collect)."""
from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, Body, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import PlainTextResponse


def make_router(require_key, current_tenant) -> APIRouter:
    from . import service as S

    outer = APIRouter()
    r = APIRouter(prefix="/api/devops", dependencies=[Depends(require_key)])

    async def run(fn, *a, **k):
        try:
            return await asyncio.to_thread(fn, *a, **k)
        except (S.DevopsError, ValueError) as e:
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
        return await run(S.save_settings, tenant, **{k: b[k] for k in ("team", "morning_time", "rules") if k in b})

    @r.put("/github")
    async def put_github(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.connect_github, tenant, str(_b(body).get("token") or ""))

    @r.delete("/github")
    async def del_github(tenant: str = Depends(current_tenant)):
        return await run(S.forget_github, tenant)

    # ---- repos / builds
    @r.get("/repos")
    async def get_repos(tenant: str = Depends(current_tenant)):
        return {"repos": await run(S.repos, tenant)}

    @r.post("/repos")
    async def add_repo(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.add_repo, tenant, str(b.get("repo") or b.get("full_name") or ""), str(b.get("deploy_workflow") or ""),
                         str(b.get("environment") or ""), str(b.get("rollback_workflow") or ""), bool(b.get("watch", True)))

    @r.delete("/repos/{ref:path}")
    async def del_repo(ref: str, tenant: str = Depends(current_tenant)):
        return await run(S.remove_repo, tenant, ref)

    @r.post("/sync")
    async def sync(tenant: str = Depends(current_tenant)):
        return await run(S.sync, tenant)

    @r.get("/runs")
    async def get_runs(repo: str = "", status: str = "", limit: int = 40, tenant: str = Depends(current_tenant)):
        return {"runs": await run(S.runs, tenant, repo, status, limit)}

    @r.get("/runs/{key}")
    async def get_run(key: str, tenant: str = Depends(current_tenant)):
        return await run(S.run_view, tenant, key)

    @r.post("/runs/{key}/diagnose")
    async def diagnose(key: str, tenant: str = Depends(current_tenant)):
        return await run(S.diagnose, tenant, key, None, "", False)

    @r.post("/runs/{key}/rerun")
    async def rerun(key: str, tenant: str = Depends(current_tenant)):
        return await run(S.rerun, tenant, key, by_tap=True)

    @r.get("/health")
    async def health(repo: str = "", tenant: str = Depends(current_tenant)):
        return await run(S.build_health, tenant, repo)

    @r.get("/dora")
    async def dora(days: int = 30, repo: str = "", tenant: str = Depends(current_tenant)):
        return await run(S.dora, tenant, days, repo)

    @r.post("/ci-log")
    async def ci_log(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.explain_ci_log, tenant, str(_b(body).get("text") or ""))

    # ---- server logs
    @r.post("/logs")
    async def logs(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.ingest_logs, tenant, str(b.get("text") or ""), str(b.get("source") or ""))

    @r.post("/logs/upload")
    async def logs_upload(file: UploadFile = File(...), source: str = Form(""), tenant: str = Depends(current_tenant)):
        data = await file.read(S.MAX_LOG_TEXT + 1)
        return await run(S.ingest_logs, tenant, data[-S.MAX_LOG_TEXT:].decode("utf-8", "replace"), source or (file.filename or "upload"))

    @r.delete("/logs")
    async def forget_logs(older_days: int = 0, tenant: str = Depends(current_tenant)):
        return await run(S.forget_logs, tenant, older_days)

    @r.get("/clusters")
    async def get_clusters(status: str = "", source: str = "", tenant: str = Depends(current_tenant)):
        return {"clusters": await run(S.clusters, tenant, status, source)}

    @r.patch("/clusters/{cid}")
    async def patch_cluster(cid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.set_cluster, tenant, cid, str(_b(body).get("status") or ""))

    @r.get("/runbooks/{rid}")
    async def get_runbook(rid: str):
        return await run(S.runbook, rid)

    @r.get("/collectors")
    async def get_collectors(tenant: str = Depends(current_tenant)):
        return {"collectors": await run(S.collectors, tenant)}

    @r.post("/collectors")
    async def new_collector(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.create_collector, tenant, str(_b(body).get("name") or ""))

    @r.delete("/collectors/{cid}")
    async def del_collector(cid: str, tenant: str = Depends(current_tenant)):
        return await run(S.revoke_collector, tenant, cid)

    @r.get("/collectors/{cid}/script", response_class=PlainTextResponse)
    async def collector_script(cid: str, tenant: str = Depends(current_tenant)):
        cols = await run(S.collectors, tenant)
        if not any(c["id"] == cid for c in cols):
            raise HTTPException(404, "collector nahi mila")
        return PlainTextResponse(S.collector_script(), headers={"Content-Disposition": 'attachment; filename="hoola_log_agent.py"'})

    # ---- scripts / checklists
    @r.get("/templates")
    async def templates():
        from . import templates as T
        return {"templates": [{"kind": k, **v} for k, v in T.KINDS.items()]}

    @r.get("/scripts")
    async def get_scripts(tenant: str = Depends(current_tenant)):
        return {"scripts": await run(S.scripts, tenant)}

    @r.post("/scripts")
    async def make_script(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.make_script, tenant, str(b.get("kind") or ""), b.get("params") if isinstance(b.get("params"), dict) else {},
                         str(b.get("ask") or ""))

    @r.post("/scripts/check")
    async def check_script(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.check_script, tenant, str(b.get("content") or ""), str(b.get("name") or ""))

    @r.get("/scripts/{sid}")
    async def get_script(sid: str, tenant: str = Depends(current_tenant)):
        return await run(S.script_view, tenant, sid)

    @r.post("/scripts/{sid}/reviewed")
    async def reviewed(sid: str, tenant: str = Depends(current_tenant)):
        return await run(S.mark_script, tenant, sid)

    @r.get("/checklists")
    async def get_checklists(tenant: str = Depends(current_tenant)):
        return {"checklists": await run(S.checklists, tenant)}

    @r.post("/checklists")
    async def new_checklist(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.make_checklist, tenant, str(b.get("kind") or "deploy"), str(b.get("deploy") or ""))

    @r.post("/checklists/{cid}/items/{item}")
    async def tick_item(cid: str, item: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.tick_item, tenant, cid, item, bool(_b(body).get("done", True)), "owner")

    # ---- endpoints
    @r.get("/endpoints")
    async def get_endpoints(tenant: str = Depends(current_tenant)):
        return {"endpoints": await run(S.endpoints, tenant)}

    @r.post("/endpoints")
    async def add_endpoint(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.add_endpoint, tenant, str(b.get("url") or ""), str(b.get("name") or ""), int(b.get("expect_status") or 200),
                         str(b.get("keyword") or ""))

    @r.delete("/endpoints/{eid}")
    async def del_endpoint(eid: str, tenant: str = Depends(current_tenant)):
        return await run(S.remove_endpoint, tenant, eid)

    @r.post("/watch")
    async def watch(tenant: str = Depends(current_tenant)):
        return await run(S.watch, tenant)

    # ---- deploys
    @r.get("/deploys")
    async def get_deploys(status: str = "", tenant: str = Depends(current_tenant)):
        return {"deploys": await run(S.deploys, tenant, status)}

    @r.post("/deploys")
    async def request_deploy(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.request_deploy, tenant, str(b.get("repo") or ""), str(b.get("ref") or ""), str(b.get("environment") or ""),
                         str(b.get("note") or ""))

    @r.post("/deploys/rollback")
    async def request_rollback(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.request_rollback, tenant, str(b.get("repo") or ""), str(b.get("to") or ""), str(b.get("note") or ""))

    @r.get("/deploys/{did}")
    async def get_deploy(did: str, tenant: str = Depends(current_tenant)):
        return await run(S.deploy_view, tenant, did)

    @r.post("/deploys/{did}/decide")
    async def decide(did: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.decide_deploy, tenant, did, bool(b.get("yes")), str(b.get("hash") or ""), str(b.get("reason") or ""), by_tap=True)

    @r.post("/deploys/{did}/reject_github")
    async def reject_github(did: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.reject_review_on_github, tenant, did, str(b.get("hash") or ""), str(b.get("reason") or ""), by_tap=True)

    @r.post("/deploys/{did}/cancel")
    async def cancel(did: str, tenant: str = Depends(current_tenant)):
        return await run(S.cancel_card, tenant, did)

    outer.include_router(r)

    # ---- public: her collector (signature checked inside)
    @outer.post("/api/devops/collect/{cid}")
    async def collect(cid: str, request: Request):
        raw = await request.body()
        try:
            return await asyncio.to_thread(S.collect, cid, request.headers.get("x-hoola-time", ""), request.headers.get("x-hoola-sign", ""), raw)
        except PermissionError:
            raise HTTPException(403, "signature / collector galat")
        except (S.DevopsError, ValueError) as e:
            raise HTTPException(400, str(e))

    return outer
