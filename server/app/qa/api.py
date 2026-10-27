"""HTTP routes of the QA Sahayak (/api/qa/*). main.py: app.include_router(make_router(require_key, current_tenant)).

Test accounts are typed only here (PUT /targets/{id}/accounts), never in chat. Filing a bug into her GitHub happens ONLY via
POST /api/qa/exports/{id}/push from her app (her tap, card hash must match)."""
from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException
from fastapi.responses import FileResponse


def make_router(require_key, current_tenant) -> APIRouter:
    from . import rules as R
    from . import service as S
    from .steps import GUIDE

    r = APIRouter(prefix="/api/qa", dependencies=[Depends(require_key)])

    async def run(fn, *a, **k):
        try:
            return await asyncio.to_thread(fn, *a, **k)
        except (S.QaError, ValueError) as e:
            raise HTTPException(400, str(e))

    def _b(body: dict | None) -> dict[str, Any]:
        return dict(body or {})

    @r.get("")
    async def overview(tenant: str = Depends(current_tenant)):
        return await run(S.overview, tenant)

    @r.get("/rules")
    async def rules():
        return {"types": R.TYPE_LABEL, "severities": R.SEV_LABEL, "statuses": R.BUG_LABEL, "standards": R.STANDARDS, "steps": GUIDE}

    @r.get("/settings")
    async def get_settings(tenant: str = Depends(current_tenant)):
        return await run(S.settings, tenant)

    @r.put("/settings")
    async def put_settings(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.save_settings, tenant, **{k: b[k] for k in ("team_name", "rules") if k in b})

    # ---- targets
    @r.get("/targets")
    async def list_targets(tenant: str = Depends(current_tenant)):
        return {"targets": await run(S.targets, tenant)}

    @r.post("/targets")
    async def add_target(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.add_target, tenant, str(b.get("kind") or ""), str(b.get("ref") or ""), str(b.get("url") or ""),
                         str(b.get("name") or ""), bool(b.get("govt_facing")), str(b.get("sector") or "general"), bool(b.get("allow_writes")))

    @r.get("/targets/{tid}")
    async def get_target(tid: str, tenant: str = Depends(current_tenant)):
        return await run(S.target, tenant, tid)

    @r.patch("/targets/{tid}")
    async def patch_target(tid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.update_target, tenant, tid, **{k: b[k] for k in ("name", "govt_facing", "sector", "allow_writes", "schedule") if k in b})

    @r.delete("/targets/{tid}")
    async def del_target(tid: str, tenant: str = Depends(current_tenant)):
        return await run(S.remove_target, tenant, tid)

    @r.post("/targets/{tid}/verify")
    async def verify(tid: str, tenant: str = Depends(current_tenant)):
        return await run(S.verify, tenant, tid)

    @r.post("/targets/{tid}/discover")
    async def discover(tid: str, tenant: str = Depends(current_tenant)):
        return await run(S.discover, tenant, tid)

    @r.post("/targets/{tid}/generate")
    async def generate(tid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.generate, tenant, tid, str(b.get("text") or ""), list(b.get("file_ids") or []), bool(b.get("rediscover")))

    @r.get("/targets/{tid}/readiness")
    async def ready(tid: str, tenant: str = Depends(current_tenant)):
        return await run(S.readiness, tenant, tid)

    @r.put("/targets/{tid}/accounts")
    async def set_account(tid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.set_account, tenant, tid, str(b.get("label") or "test"), str(b.get("username") or ""), str(b.get("password") or ""))

    @r.delete("/targets/{tid}/accounts/{label}")
    async def del_account(tid: str, label: str, tenant: str = Depends(current_tenant)):
        return await run(S.remove_account, tenant, tid, label)

    # ---- cases
    @r.get("/cases")
    async def list_cases(target: str = "", status: str = "active", type: str = "", result: str = "", tenant: str = Depends(current_tenant)):
        return {"cases": await run(S.cases, tenant, target, status, type, result)}

    @r.post("/cases")
    async def add_case(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.add_case, tenant, str(b.get("target") or ""), str(b.get("title") or ""), b.get("steps") or [],
                         b.get("steps_text") or None, str(b.get("expected") or ""), str(b.get("type") or "functional"),
                         str(b.get("priority") or "P3"), str(b.get("area") or ""), str(b.get("account") or ""), int(b.get("viewport") or 1280),
                         str(b.get("preconditions") or ""), b.get("tags") or None)

    @r.get("/cases/{cid}")
    async def get_case(cid: str, tenant: str = Depends(current_tenant)):
        return await run(S.case, tenant, cid)

    @r.patch("/cases/{cid}")
    async def patch_case(cid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        keys = ("title", "area", "expected", "preconditions", "account", "note", "requirement", "steps", "steps_text", "type", "priority",
                "viewport", "tags", "status")
        return await run(S.edit_case, tenant, cid, **{k: b[k] for k in keys if k in b})

    @r.post("/cases/{cid}/mark")
    async def mark(cid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.mark, tenant, cid, str(b.get("result") or ""), str(b.get("note") or ""))

    # ---- runs
    @r.post("/runs")
    async def start(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.start_run, tenant, str(b.get("target") or ""), str(b.get("which") or "all"), list(b.get("cases") or []) or None)

    @r.get("/runs")
    async def list_runs(target: str = "", tenant: str = Depends(current_tenant)):
        return {"runs": await run(S.runs, tenant, target)}

    @r.get("/runs/{rid}")
    async def get_run(rid: str, tenant: str = Depends(current_tenant)):
        return await run(S.run_view, tenant, rid)

    @r.get("/shots/{rid}/{name}")
    async def shot(rid: str, name: str, tenant: str = Depends(current_tenant)):
        p = await asyncio.to_thread(S.shot_path, tenant, rid, name)
        if not p:
            raise HTTPException(404, "screenshot nahi mila")
        return FileResponse(p, media_type="image/jpeg", headers={"Cache-Control": "private, max-age=86400"})

    # ---- bugs
    @r.get("/bugs")
    async def list_bugs(target: str = "", status: str = "", severity: str = "", tenant: str = Depends(current_tenant)):
        return {"bugs": await run(S.bugs, tenant, target, status, severity)}

    @r.get("/bugs/{bid}")
    async def get_bug(bid: str, tenant: str = Depends(current_tenant)):
        return await run(S.bug, tenant, bid)

    @r.post("/bugs/{bid}/status")
    async def bug_status(bid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.set_bug, tenant, bid, str(b.get("status") or ""), str(b.get("reason") or ""), str(b.get("duplicate_of") or ""),
                         str(b.get("severity") or ""))

    @r.post("/bugs/{bid}/retest")
    async def bug_retest(bid: str, tenant: str = Depends(current_tenant)):
        return await run(S.retest, tenant, bid, background=True)

    @r.post("/bugs/{bid}/github")
    async def bug_github(bid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.github_request, tenant, bid, str(_b(body).get("repo") or ""))

    # ---- her tap files it
    @r.post("/exports/{eid}/push")
    async def push(eid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.github_push, tenant, eid, str(_b(body).get("hash") or ""), by_tap=True)

    @r.post("/exports/{eid}/cancel")
    async def cancel(eid: str, tenant: str = Depends(current_tenant)):
        return await run(S.cancel_export, tenant, eid)

    @r.post("/register")
    async def register(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.register_file, tenant, str(_b(body).get("target") or ""))

    return r
