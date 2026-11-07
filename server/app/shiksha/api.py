"""HTTP routes of the Shiksha foundation (/api/shiksha/*): institution settings, classes, learners + guardian consent,
the shared question bank, gradebook, the frameworks library and the Python sandbox status. All key-protected."""
from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException


def make_router(require_key, current_tenant) -> APIRouter:
    from . import rules as R
    from . import service as S

    r = APIRouter(prefix="/api/shiksha", dependencies=[Depends(require_key)])

    async def run(fn, *a, **k):
        try:
            return await asyncio.to_thread(fn, *a, **k)
        except (S.ShikshaError, ValueError) as e:
            raise HTTPException(400, str(e))

    def _b(body) -> dict[str, Any]:
        return dict(body or {})

    @r.get("")
    async def overview(tenant: str = Depends(current_tenant)):
        return await run(lambda: {**S.day(tenant), "never": R.NEVER, "disclaimer": R.DISCLAIMER,
                                  "consent_methods": R.CONSENT_METHODS, "boards": R.BOARDS})

    @r.put("/settings")
    async def put_settings(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.save_settings, tenant, "owner", **{k: b[k] for k in S.SET_KEYS if k in b})

    @r.get("/classes")
    async def get_classes(status: str = "active", tenant: str = Depends(current_tenant)):
        return {"classes": await run(S.classes, tenant, status)}

    @r.post("/classes")
    async def post_class(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.add_class, tenant, b.get("name", ""), b.get("grade", ""), b.get("board", ""), b.get("subjects"),
                         b.get("section", ""), b.get("teacher", ""), b.get("year", ""))

    @r.patch("/classes/{ref}")
    async def patch_class(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.update_class, tenant, ref, "owner", **_b(body))

    @r.get("/learners")
    async def get_learners(class_ref: str = "", tenant: str = Depends(current_tenant)):
        return {"learners": await run(S.learners, tenant, class_ref)}

    @r.post("/learners")
    async def post_learner(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.add_learner, tenant, b.get("name", ""), b.get("class_ref", ""), b.get("roll", ""), b.get("birth_year"),
                         bool(b.get("adult")), b.get("guardian_name", ""), b.get("guardian_relation", ""),
                         b.get("guardian_phone", ""), b.get("guardian_email", ""), b.get("language", ""))

    @r.get("/learners/{ref}")
    async def get_learner(ref: str, tenant: str = Depends(current_tenant)):
        return await run(S.learner, tenant, ref)

    @r.post("/learners/{ref}/consent")
    async def post_consent(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.record_consent, tenant, ref, bool(b.get("given", True)), b.get("method", ""), b.get("note", ""))

    @r.delete("/learners/{ref}")
    async def del_learner(ref: str, tenant: str = Depends(current_tenant)):
        return await run(S.forget_learner, tenant, ref)

    @r.get("/learners/{ref}/marks")
    async def get_marks(ref: str, tenant: str = Depends(current_tenant)):
        return await run(S.marks, tenant, ref)

    @r.post("/marks/sign")
    async def sign(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.sign_off, tenant, list(_b(body).get("ids") or []))

    @r.get("/bank")
    async def get_bank(subject: str = "", grade: str = "", chapter: str = "", qtype: str = "", status: str = "", q: str = "",
                       limit: int = 50, tenant: str = Depends(current_tenant)):
        return await run(S.bank, tenant, subject, grade, chapter, qtype, status, q, limit)

    @r.get("/bank/{ref}")
    async def get_question(ref: str, tenant: str = Depends(current_tenant)):
        return await run(S.question, tenant, ref)

    @r.patch("/bank/{ref}")
    async def patch_question(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.edit_question, tenant, ref, _b(body))

    @r.post("/bank/status")
    async def bank_status(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.set_status, tenant, list(b.get("refs") or []), str(b.get("status") or ""))

    @r.get("/frameworks")
    async def get_frameworks(board: str = "CBSE", grade: str = "", subject: str = ""):
        from ..pathyakram import service as P
        return await run(P.frameworks_view, board, grade, subject)

    @r.get("/pylab")
    async def pylab_status():
        from ..pylab import service as PL
        return await run(PL.status)

    return r
