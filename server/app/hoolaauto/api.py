"""HOOLA AUTO routes. Owner routes /api/auto/* (her sign-in). Public: /api/auto/c/{token}/* = the client's intake page,
the random token in the address is the whole key (only its sha256 is kept; 30 days; one project; answers only)."""
from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException

from . import service as S


async def _run(fn, *a, **kw):
    try:
        return await asyncio.to_thread(fn, *a, **kw)
    except S.AutoError as e:
        raise HTTPException(e.status, str(e))


def _b(body: Any) -> dict[str, Any]:
    return body if isinstance(body, dict) else {}


def make_router(require_key, current_tenant) -> APIRouter:
    r = APIRouter(prefix="/api/auto", dependencies=[Depends(require_key)])

    @r.get("/projects")
    async def projects(archived: bool = False, tenant: str = Depends(current_tenant)):
        return await _run(S.list_projects, tenant, archived)

    @r.post("/projects")
    async def create(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await _run(S.create_project, tenant, _b(body))

    @r.get("/projects/{pid}")
    async def one(pid: str, tenant: str = Depends(current_tenant)):
        return await _run(S.project_view, tenant, pid)

    @r.patch("/projects/{pid}")
    async def update(pid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await _run(S.update_project, tenant, pid, _b(body))

    @r.post("/projects/{pid}/archive")
    async def archive(pid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await _run(S.archive_project, tenant, pid, bool(_b(body).get("on", True)))

    @r.get("/projects/{pid}/env")
    async def env(pid: str, tenant: str = Depends(current_tenant)):
        return await _run(S.env_view, tenant, pid)

    @r.get("/projects/{pid}/intake")
    async def intake(pid: str, tenant: str = Depends(current_tenant)):
        return await _run(S.intake_view, tenant, pid)

    @r.put("/projects/{pid}/intake/{key}")
    async def answer(pid: str, key: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await _run(S.answer, tenant, pid, key, str(_b(body).get("value") or ""))

    @r.post("/projects/{pid}/intake/{key}/confirm")
    async def confirm(pid: str, key: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await _run(S.confirm, tenant, pid, key, str(_b(body).get("pick") or ""))

    @r.get("/projects/{pid}/sources")
    async def sources(pid: str, tenant: str = Depends(current_tenant)):
        return await _run(S.sources_view, tenant, pid)

    @r.post("/projects/{pid}/sources")
    async def add_source(pid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await _run(S.add_source, tenant, pid, _b(body))

    @r.post("/projects/{pid}/client-link")
    async def client_link(pid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await _run(S.client_link, tenant, pid, bool(_b(body).get("on", True)))

    @r.post("/projects/{pid}/review")
    async def review(pid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await _run(S.send_for_review, tenant, pid, str(_b(body).get("note") or ""))

    @r.get("/projects/{pid}/mission")
    async def mission(pid: str, tenant: str = Depends(current_tenant)):
        return await _run(S.mission, tenant, pid)

    @r.get("/projects/{pid}/gates")
    async def gates(pid: str, tenant: str = Depends(current_tenant)):
        return await _run(S.gates, tenant, pid)

    @r.get("/projects/{pid}/gates/{gid}")
    async def gate(pid: str, gid: str, tenant: str = Depends(current_tenant)):
        return await _run(S.gate, tenant, pid, gid)

    @r.post("/projects/{pid}/gates/{gid}/decide")
    async def decide(pid: str, gid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await _run(S.decide, tenant, pid, gid, bool(b.get("yes")), str(b.get("hash") or ""), str(b.get("note") or ""))

    @r.post("/projects/{pid}/golive/{index}/merge")
    async def golive_merge(pid: str, index: int, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await _run(S.golive_merge, tenant, pid, index, str(b.get("sha") or ""), str(b.get("reason") or ""))

    @r.get("/projects/{pid}/agents/{role}")
    async def agent(pid: str, role: str, tenant: str = Depends(current_tenant)):
        return await _run(S.agent_view, tenant, pid, role)

    @r.post("/projects/{pid}/agents/{role}/message")
    async def message(pid: str, role: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await _run(S.message, tenant, pid, role, str(_b(body).get("text") or ""))

    @r.post("/projects/{pid}/tasks/{tid}/{what}")
    async def task_act(pid: str, tid: str, what: str, tenant: str = Depends(current_tenant)):
        if what == "skip":
            return await _run(S.skip_task, tenant, pid, tid)
        if what == "retry":
            return await _run(S.retry_task, tenant, pid, tid)
        raise HTTPException(404, "what = skip | retry")

    return r


def make_public_router() -> APIRouter:
    p = APIRouter(prefix="/api/auto/c")

    @p.get("/{token}")
    async def view(token: str):
        return await _run(S.client_view, token)

    @p.post("/{token}/answer")
    async def answer(token: str, body: dict = Body(default={})):
        b = _b(body)
        return await _run(S.client_answer, token, str(b.get("key") or ""), str(b.get("value") or ""))

    @p.post("/{token}/confirm")
    async def confirm(token: str, body: dict = Body(default={})):
        b = _b(body)
        return await _run(S.client_confirm, token, str(b.get("key") or ""), str(b.get("pick") or ""))

    @p.post("/{token}/signoff")
    async def signoff(token: str):
        return await _run(S.client_signoff, token)

    return p
