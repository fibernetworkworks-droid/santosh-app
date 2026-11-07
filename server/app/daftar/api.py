"""HTTP routes of the Daftar Sahayak (/api/daftar/*), key-protected. HER tap lives ONLY here: POST /shares/{id}/decide
{yes, hash} (absence alerts / a report card for guardians)."""
from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException


def make_router(require_key, current_tenant) -> APIRouter:
    from . import rules as R
    from . import service as D

    r = APIRouter(prefix="/api/daftar", dependencies=[Depends(require_key)])

    async def run(fn, *a, **k):
        try:
            return await asyncio.to_thread(fn, *a, **k)
        except (D.DaftarError, ValueError) as e:
            raise HTTPException(400, str(e))

    def _b(body) -> dict[str, Any]:
        return dict(body or {})

    @r.get("")
    async def overview(tenant: str = Depends(current_tenant)):
        return await run(lambda: {**D.day(tenant), "never": R.NEVER, "grade_scale": R.GRADE_SCALE})

    @r.post("/attendance")
    async def post_att(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(D.mark_attendance, tenant, str(b.get("class") or ""), str(b.get("day") or ""), b.get("absent"),
                         b.get("late"), b.get("leave"))

    @r.get("/attendance")
    async def get_att(class_ref: str, month: str = "", tenant: str = Depends(current_tenant)):
        return await run(D.attendance, tenant, class_ref, month)

    @r.post("/attendance/alerts")
    async def post_alerts(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(D.absent_alerts, tenant, str(b.get("class") or ""), str(b.get("day") or ""))

    @r.post("/grade/sheet")
    async def post_sheet(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(D.grade_sheet, tenant, str(b.get("class") or ""), str(b.get("assessment") or ""),
                         str(b.get("subject") or ""), b.get("key"), str(b.get("paper") or ""), b.get("rows"), str(b.get("file_id") or ""))

    @r.post("/grade/omr")
    async def post_omr(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(D.omr_read, tenant, str(b.get("file_id") or ""), int(b.get("questions") or 0))

    @r.post("/grade/forms")
    async def post_forms(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(D.grade_forms, tenant, str(b.get("class") or ""), str(b.get("assessment") or ""),
                         str(b.get("form") or ""), str(b.get("paper") or ""))

    @r.get("/gradings")
    async def get_gradings(tenant: str = Depends(current_tenant)):
        return {"gradings": await run(D.gradings, tenant)}

    @r.get("/unsigned")
    async def get_unsigned(class_ref: str = "", assessment: str = "", tenant: str = Depends(current_tenant)):
        return await run(D.unsigned, tenant, class_ref, assessment)

    @r.get("/report/{ref}")
    async def get_report(ref: str, term: str = "", tenant: str = Depends(current_tenant)):
        return await run(D.report_card, tenant, ref, term)

    @r.post("/report/{ref}/file")
    async def post_report_file(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(D.report_card_file, tenant, ref, str(_b(body).get("term") or ""))

    @r.post("/report/{ref}/share")
    async def post_report_share(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(D.report_card_share, tenant, ref, str(_b(body).get("term") or ""))

    @r.post("/timetable")
    async def post_tt(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(D.timetable, tenant, b.get("needs") or [], int(b.get("periods") or 8), b.get("days"),
                         int(b.get("max_same") or 2))

    @r.get("/timetables")
    async def get_tts(tenant: str = Depends(current_tenant)):
        return {"timetables": await run(D.timetables, tenant)}

    @r.post("/shares/{share_id}/decide")
    async def decide(share_id: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(D.decide_share, tenant, share_id, bool(b.get("yes")), str(b.get("hash") or ""), True)

    return r
