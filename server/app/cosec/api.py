"""HTTP routes of the Cosec Sahayak (/api/cosec/*). main.py: app.include_router(make_router(require_key, current_tenant)).

HER taps live ONLY here (by_tap=True): POST /meetings/{id}/notice/decide (notice goes out), /meetings/{id}/minutes/decide (minutes
signed off), /filings/{id}/decide ("file karo"; 428 fingerprint_needed -> POST /filings/{id}/challenge, sign, resend with `proof`).
No public routes."""
from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException


def make_router(require_key, current_tenant) -> APIRouter:
    from . import rules as R
    from . import service as S

    r = APIRouter(prefix="/api/cosec", dependencies=[Depends(require_key)])

    async def run(fn, *a, **k):
        try:
            return await asyncio.to_thread(fn, *a, **k)
        except S.CosecError as e:
            code = str(e)
            if code in ("fingerprint_needed", "fingerprint_invalid"):
                raise HTTPException(428, code)
            raise HTTPException(400, code)
        except ValueError as e:
            raise HTTPException(400, str(e))

    def _b(body) -> dict[str, Any]:
        return dict(body or {})

    def _s(v) -> str:
        return "" if v is None else str(v)

    def _yes(b: dict) -> bool:
        if "yes" not in b:
            raise HTTPException(400, "yes = true | false")
        return bool(b["yes"])

    @r.get("")
    async def overview(tenant: str = Depends(current_tenant)):
        def go():
            S.ensure(tenant)
            return {"settings": S.settings(tenant), "entities": S.entities(tenant), "day": S.day(tenant),
                    "filings": S.filings(tenant, within_days=60), "never": R.NEVER, "draft_line": R.DRAFT_LINE}
        return await run(go)

    @r.get("/day")
    async def day(tenant: str = Depends(current_tenant)):
        return await run(S.day, tenant)

    @r.get("/settings")
    async def get_settings(tenant: str = Depends(current_tenant)):
        return await run(S.settings, tenant)

    @r.put("/settings")
    async def put_settings(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.save_settings, tenant, **{k: b[k] for k in S._SET_KEYS if k in b})

    @r.get("/rules")
    async def rules():
        return {"forms": R.FORMS, "events": {k: v["label"] for k, v in R.EVENTS.items()}, "kinds": R.KINDS, "never": R.NEVER,
                "draft_line": R.DRAFT_LINE, "agenda": R.AGENDA}

    # ---- entities + people
    @r.get("/entities")
    async def list_entities(status: str = "", tenant: str = Depends(current_tenant)):
        return {"entities": await run(S.entities, tenant, status)}

    @r.post("/entities")
    async def new_entity(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        name = _s(b.pop("name", ""))
        b.pop("ref", None)
        return await run(S.save_entity, tenant, name, "", **{k: b[k] for k in S._ENT_KEYS if k in b})

    @r.get("/entities/{ref}")
    async def get_entity(ref: str, tenant: str = Depends(current_tenant)):
        return await run(S.entity_view, tenant, ref)

    @r.patch("/entities/{ref}")
    async def patch_entity(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.save_entity, tenant, _s(b.get("name")), ref, **{k: b[k] for k in S._ENT_KEYS if k in b})

    @r.post("/entities/{ref}/people")
    async def people(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        keys = ("din", "designation", "address", "share_class", "folio", "appointed_on", "ceased_on", "din_on", "kyc_on", "member_since",
                "email", "phone", "id_ref", "shares", "nominal")
        return await run(S.person, tenant, ref, _s(b.get("name")), _s(b.get("role") or "director"), _s(b.get("person")),
                         **{k: b[k] for k in keys if k in b})

    @r.post("/entities/{ref}/calendar")
    async def cal(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.calendar, tenant, ref, _s(_b(body).get("fy")))

    @r.post("/entities/{ref}/events")
    async def ev(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        det = b.get("details") if isinstance(b.get("details"), dict) else {}
        return await run(S.event, tenant, ref, _s(b.get("kind")), _s(b.get("on")), _s(b.get("words")), det)

    @r.get("/entities/{ref}/registers")
    async def registers(ref: str, tenant: str = Depends(current_tenant)):
        return await run(S.registers_file, tenant, ref)

    @r.post("/entities/{ref}/forget")
    async def forget(ref: str, tenant: str = Depends(current_tenant)):
        return await run(S.forget, tenant, ref)

    # ---- filings
    @r.get("/filings")
    async def list_filings(entity: str = "", status: str = "", within_days: int | None = None, tenant: str = Depends(current_tenant)):
        return {"filings": await run(S.filings, tenant, entity, status, within_days)}

    @r.post("/filings/{fid}/request")
    async def filing_request(fid: str, tenant: str = Depends(current_tenant)):
        return await run(S.filing_request, tenant, fid)

    @r.post("/filings/{fid}/challenge")
    async def filing_challenge(fid: str, tenant: str = Depends(current_tenant)):
        return await run(S.filing_challenge, tenant, fid)

    @r.post("/filings/{fid}/decide")
    async def decide_filing(fid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        proof = b.get("proof") if isinstance(b.get("proof"), dict) else None
        return await run(S.decide_filing, tenant, fid, _yes(b), _s(b.get("hash")), _s(b.get("reason")), proof, by_tap=True)

    @r.post("/filings/{fid}/done")
    async def filing_done(fid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.filing_done, tenant, fid, _s(b.get("srn")), _s(b.get("filed_on")), b.get("fee"))

    @r.post("/filings/{fid}/skip")
    async def filing_skip(fid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.filing_skip, tenant, fid, _s(_b(body).get("reason")))

    # ---- meetings
    @r.get("/meetings")
    async def list_meetings(entity: str = "", status: str = "", tenant: str = Depends(current_tenant)):
        return {"meetings": await run(S.meetings, tenant, entity, status)}

    @r.post("/entities/{ref}/meetings")
    async def new_meeting(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.meeting_new, tenant, ref, _s(b.get("kind") or "board"), _s(b.get("on")), _s(b.get("time")), _s(b.get("place")),
                         _s(b.get("mode") or "physical"), b.get("agenda") or [], _s(b.get("fy")), _s(b.get("chair")))

    @r.patch("/meetings/{mid}")
    async def patch_meeting(mid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.meeting_update, tenant, mid, **{k: b[k] for k in ("on", "time", "place", "chair", "mode", "agenda") if k in b})

    @r.post("/meetings/{mid}/notice")
    async def notice(mid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        sc = b.get("shorter_consent")
        return await run(S.notice_request, tenant, mid, _s(b.get("send_on")), _s(b.get("mode")), None if sc is None else bool(sc))

    @r.post("/meetings/{mid}/notice/decide")
    async def decide_notice(mid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.decide_notice, tenant, mid, _yes(b), _s(b.get("hash")), _s(b.get("send_on")), by_tap=True)

    @r.post("/meetings/{mid}/attendance")
    async def attend(mid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        mc = b.get("members_count")
        return await run(S.attendance, tenant, mid, b.get("present") or [], b.get("interested") or [], _s(b.get("chair")),
                         int(mc) if mc not in (None, "") else None)

    @r.post("/meetings/{mid}/resolutions")
    async def res(mid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.resolution, tenant, mid, "", _s(b.get("kind") or "board"), _s(b.get("text")), _s(b.get("passed_on")),
                         b.get("votes_for"), b.get("votes_against"), bool(b.get("mgt14")))

    @r.post("/entities/{ref}/resolutions")
    async def circular(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.resolution, tenant, "", ref, "circular", _s(b.get("text")), _s(b.get("passed_on")), b.get("votes_for"),
                         b.get("votes_against"), bool(b.get("mgt14")))

    @r.post("/meetings/{mid}/minutes/draft")
    async def minutes_draft(mid: str, tenant: str = Depends(current_tenant)):
        return await run(S.minutes_draft, tenant, mid)

    @r.put("/meetings/{mid}/minutes")
    async def minutes_edit(mid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.minutes_edit, tenant, mid, _s(_b(body).get("text")))

    @r.post("/meetings/{mid}/minutes")
    async def minutes_request(mid: str, tenant: str = Depends(current_tenant)):
        return await run(S.minutes_request, tenant, mid)

    @r.post("/meetings/{mid}/minutes/decide")
    async def decide_minutes(mid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.decide_minutes, tenant, mid, _yes(b), _s(b.get("hash")), _s(b.get("signed_on")), by_tap=True)

    return r
