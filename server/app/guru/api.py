"""HTTP routes of the Guru Sahayak (/api/guru/*), key-protected. HER tap lives ONLY here: POST /shares/{id}/decide
{yes, hash} (a weekly report going to the guardian)."""
from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException


def make_router(require_key, current_tenant) -> APIRouter:
    from . import rules as R
    from . import service as G

    r = APIRouter(prefix="/api/guru", dependencies=[Depends(require_key)])

    async def run(fn, *a, **k):
        try:
            return await asyncio.to_thread(fn, *a, **k)
        except (G.GuruError, ValueError) as e:
            raise HTTPException(400, str(e))

    def _b(body) -> dict[str, Any]:
        return dict(body or {})

    @r.get("")
    async def overview(tenant: str = Depends(current_tenant)):
        return await run(lambda: {**G.day(tenant), "never": R.NEVER, "disclaimer": R.DISCLAIMER, "levels": R.LEVEL_SAY})

    @r.put("/settings")
    async def put_settings(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(G.save_settings, tenant, "owner", **{k: b.get(k) for k in ("day_minutes", "exam_mode", "report_weekday", "language")})

    @r.post("/sessions")
    async def post_session(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(G.start, tenant, str(b.get("learner") or ""), str(b.get("mode") or "doubt"), str(b.get("subject") or ""),
                         str(b.get("grade") or ""), str(b.get("topic") or ""), str(b.get("language") or ""))

    @r.post("/sessions/{ref}/doubt")
    async def post_doubt(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(G.doubt, tenant, ref, str(b.get("text") or ""), str(b.get("file_id") or ""))

    @r.post("/sessions/{ref}/hint")
    async def post_hint(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(G.hint, tenant, ref, str(_b(body).get("attempt") or ""))

    @r.post("/sessions/{ref}/practice")
    async def post_practice(ref: str, tenant: str = Depends(current_tenant)):
        return await run(G.next_question, tenant, ref)

    @r.post("/sessions/{ref}/answer")
    async def post_answer(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(G.answer, tenant, ref, str(b.get("given") or ""), int(b.get("hints") or 0))

    @r.post("/sessions/{ref}/language")
    async def post_lang(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(G.language_turn, tenant, ref, str(_b(body).get("text") or ""))

    @r.post("/sessions/{ref}/end")
    async def post_end(ref: str, tenant: str = Depends(current_tenant)):
        return await run(G.end, tenant, ref)

    @r.get("/learners/{ref}/progress")
    async def get_progress(ref: str, tenant: str = Depends(current_tenant)):
        return await run(G.progress, tenant, ref)

    @r.post("/learners/{ref}/report")
    async def post_report(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(G.share_request, tenant, ref, str(_b(body).get("via") or "whatsapp"))

    @r.post("/shares/{share_id}/decide")
    async def decide(share_id: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(G.decide_share, tenant, share_id, bool(b.get("yes")), str(b.get("hash") or ""), True)

    return r
