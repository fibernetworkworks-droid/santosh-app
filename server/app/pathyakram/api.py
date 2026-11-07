"""HTTP routes of the Pathyakram Sahayak (/api/pathyakram/*). main.py: app.include_router(make_router(require_key,
current_tenant)).

HER tap lives ONLY here (by_tap=True): POST /shares/{id}/decide {yes, hash} (a paper / plan going outside: file, Google
Forms quiz, WhatsApp / email draft)."""
from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException


def make_router(require_key, current_tenant) -> APIRouter:
    from ..shiksha import rules as R
    from . import service as P

    r = APIRouter(prefix="/api/pathyakram", dependencies=[Depends(require_key)])

    async def run(fn, *a, **k):
        try:
            return await asyncio.to_thread(fn, *a, **k)
        except (P.PathyakramError, ValueError) as e:
            raise HTTPException(400, str(e))
        except Exception as e:                       # shiksha errors surface the same way
            if type(e).__name__ == "ShikshaError":
                raise HTTPException(400, str(e))
            raise

    def _b(body) -> dict[str, Any]:
        return dict(body or {})

    @r.get("")
    async def overview(tenant: str = Depends(current_tenant)):
        return await run(lambda: {**P.day(tenant), "never": R.NEVER, "disclaimer": R.DISCLAIMER})

    @r.post("/generate")
    async def gen(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(P.generate, tenant, b.get("subject", ""), b.get("grade", ""), b.get("board", ""), b.get("chapter", ""),
                         b.get("topic", ""), b.get("counts"), b.get("marks"), b.get("difficulty", ""), b.get("competency_pct"),
                         b.get("language", ""), b.get("notes", ""))

    @r.post("/blueprint")
    async def bp(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(P.blueprint, tenant, b.get("subject", ""), b.get("grade", ""), b.get("board", ""), b.get("sections"),
                         b.get("max_marks"), b.get("duration_min"))

    @r.get("/papers")
    async def get_papers(status: str = "", tenant: str = Depends(current_tenant)):
        return {"papers": await run(P.papers, tenant, status)}

    @r.post("/papers")
    async def post_paper(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(P.make_paper, tenant, b.get("subject", ""), b.get("grade", ""), b.get("board", ""), b.get("title", ""),
                         b.get("chapters"), b.get("sections"), b.get("max_marks"), b.get("duration_min"),
                         b.get("approved_only", True) is not False, bool(b.get("fill_missing")), b.get("language", ""))

    @r.get("/papers/{ref}")
    async def get_paper(ref: str, key: bool = False, tenant: str = Depends(current_tenant)):
        return await run(P.paper, tenant, ref, key)

    @r.post("/papers/{ref}/swap")
    async def post_swap(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(P.swap, tenant, ref, int(b.get("n") or 0), b.get("question", ""))

    @r.post("/papers/{ref}/approve")
    async def post_approve(ref: str, tenant: str = Depends(current_tenant)):
        return await run(P.approve_paper, tenant, ref)

    @r.post("/papers/{ref}/file")
    async def post_paper_file(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(P.paper_file, tenant, ref, bool(_b(body).get("key")))

    @r.get("/plans")
    async def get_plans(kind: str = "", tenant: str = Depends(current_tenant)):
        return {"plans": await run(P.plans, tenant, kind)}

    @r.post("/plans/year")
    async def post_year(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(P.year_plan, tenant, b.get("subject", ""), b.get("grade", ""), b.get("board", ""), b.get("chapters"),
                         b.get("weights"), b.get("start_month", "April"), int(b.get("months") or 10),
                         int(b.get("revision_months") if b.get("revision_months") is not None else 1), int(b.get("periods_per_week") or 6))

    @r.post("/plans/lesson")
    async def post_lesson(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(P.lesson_plan, tenant, b.get("subject", ""), b.get("grade", ""), b.get("topic", ""), b.get("board", ""),
                         int(b.get("minutes") or 40), int(b.get("periods") or 1), b.get("language", ""), b.get("notes", ""))

    @r.post("/plans/rubric")
    async def post_rubric(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(P.rubric, tenant, b.get("task", ""), b.get("subject", ""), b.get("grade", ""), b.get("board", ""),
                         b.get("criteria"), int(b.get("levels") or 4), float(b.get("total_points") or 20))

    @r.get("/plans/{ref}")
    async def get_plan(ref: str, tenant: str = Depends(current_tenant)):
        return await run(P.plan, tenant, ref)

    @r.post("/plans/{ref}/approve")
    async def post_plan_approve(ref: str, tenant: str = Depends(current_tenant)):
        return await run(P.approve_plan, tenant, ref)

    @r.post("/plans/{ref}/file")
    async def post_plan_file(ref: str, tenant: str = Depends(current_tenant)):
        return await run(P.plan_file, tenant, ref)

    @r.get("/shares")
    async def get_shares(status: str = "", tenant: str = Depends(current_tenant)):
        return {"shares": await run(P.shares, tenant, status)}

    @r.post("/shares")
    async def post_share(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(P.share_request, tenant, b.get("what", "paper"), b.get("ref", ""), b.get("via", "file"),
                         b.get("to_name", ""), b.get("to_contact", ""), bool(b.get("with_key")), b.get("note", ""))

    @r.post("/shares/{share_id}/decide")
    async def decide(share_id: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(P.decide_share, tenant, share_id, bool(b.get("yes")), str(b.get("hash") or ""), True)

    return r
