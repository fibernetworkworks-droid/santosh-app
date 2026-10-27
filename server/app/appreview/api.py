"""HTTP routes of the App Review Sahayak (/api/appreview/*). main.py: app.include_router(make_router(require_key, current_tenant)).

The ONLY way the fix list goes to the Developer Sahayak / her developer: POST /api/appreview/handoffs/{id}/decide (her tap).
The GitHub token is typed only in the app (PUT /api/appreview/github), sealed, never returned."""
from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, Body, Depends, File, HTTPException, UploadFile


def make_router(require_key, current_tenant) -> APIRouter:
    from . import service as S

    r = APIRouter(prefix="/api/appreview", dependencies=[Depends(require_key)])

    async def run(fn, *a, **k):
        try:
            return await asyncio.to_thread(fn, *a, **k)
        except (S.ReviewError, ValueError) as e:
            raise HTTPException(400, str(e))

    def _b(body: dict | None) -> dict[str, Any]:
        return dict(body or {})

    @r.get("")
    async def overview(tenant: str = Depends(current_tenant)):
        return await run(S.summary, tenant)

    @r.get("/settings")
    async def get_settings(tenant: str = Depends(current_tenant)):
        return await run(S.settings, tenant)

    @r.put("/settings")
    async def put_settings(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.save_settings, tenant, **{k: b[k] for k in ("stack", "kids", "ios", "developer") if k in b})

    @r.post("/upload")
    async def upload(file: UploadFile = File(...), tenant: str = Depends(current_tenant)):
        from ..config import get_settings as gs
        cap = int(gs().appcheck_max_mb) * 1024 * 1024
        data = await file.read(cap + 1)
        return await run(S.upload, tenant, file.filename or "app.zip", data)

    @r.post("/reviews")
    async def new_review(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        conv = str(b.get("conv") or "")
        if b.get("file"):
            return await run(S.review_file, tenant, str(b["file"]), conv)
        if b.get("repo"):
            return await run(S.review_repo, tenant, str(b["repo"]), str(b.get("ref") or ""), conv)
        if b.get("url"):
            return await run(S.review_web, tenant, str(b["url"]), conv)
        raise HTTPException(400, "file (upload id / file_id), repo ya url dijiye")

    @r.get("/reviews")
    async def list_reviews(limit: int = 30, tenant: str = Depends(current_tenant)):
        return {"reviews": await run(S.reviews, tenant, limit)}

    @r.get("/reviews/{ref}")
    async def get_review(ref: str, tenant: str = Depends(current_tenant)):
        return await run(S.get, tenant, ref)

    @r.post("/reviews/{ref}/mark")
    async def mark(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.mark, tenant, ref, str(b.get("key") or ""), str(b.get("status") or ""), str(b.get("note") or ""))

    @r.post("/reviews/{ref}/files")
    async def files(ref: str, tenant: str = Depends(current_tenant)):
        return await run(S.report_files, tenant, ref)

    @r.get("/reviews/{ref}/fixlist")
    async def fixlist(ref: str, tenant: str = Depends(current_tenant)):
        def go():
            v = S.get(tenant, ref)
            return {"tasks": S.fix_list(v), "markdown": S.fix_list_md(v, S.settings(tenant)["developer"])}
        return await run(go)

    @r.post("/reviews/{ref}/handoff")
    async def handoff(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.handoff_request, tenant, ref, list(b.get("keys") or []), str(b.get("to") or "devsahayak"))

    @r.post("/handoffs/{hid}/decide")
    async def decide(hid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        if "yes" not in b:
            raise HTTPException(400, "yes = true | false")
        return await run(S.handoff_decide, tenant, hid, bool(b.get("yes")), str(b.get("hash") or ""), by_tap=True)

    # ---- website domains
    @r.get("/domains")
    async def list_domains(tenant: str = Depends(current_tenant)):
        return {"domains": await run(S.domains, tenant)}

    @r.post("/domains")
    async def add_domain(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.domain_add, tenant, str(_b(body).get("url") or ""))

    @r.post("/domains/verify")
    async def verify_domain(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.domain_verify, tenant, str(_b(body).get("url") or ""))

    # ---- GitHub read-only token (typed only in the app)
    @r.put("/github")
    async def put_github(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.set_github, tenant, str(_b(body).get("token") or ""))

    @r.delete("/github")
    async def del_github(tenant: str = Depends(current_tenant)):
        return await run(S.clear_github, tenant)

    return r
