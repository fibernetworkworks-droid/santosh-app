"""HTTP routes of the Society Sahayak (/api/society/*). main.py: app.include_router(make_router(require_key, current_tenant)).

Bills to members, notices / circulars, messages to members, spends and penalties are decided ONLY here:
POST /api/society/cards/{id}/decide {yes, hash, via, proof} from her app (her tap, the card's hash; a spend also needs her
phone's fingerprint once a phone key is set up: 428 -> POST /api/society/cards/{id}/challenge, sign, resend with `proof`)."""
from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, Body, Depends, File, HTTPException, UploadFile


def make_router(require_key, current_tenant) -> APIRouter:
    from . import service as S

    r = APIRouter(prefix="/api/society", dependencies=[Depends(require_key)])

    async def run(fn, *a, **k):
        try:
            return await asyncio.to_thread(fn, *a, **k)
        except S.SocietyError as e:
            code = str(e)
            if code in ("fingerprint_needed", "fingerprint_invalid"):
                raise HTTPException(428, code)
            raise HTTPException(400, code)
        except ValueError as e:
            raise HTTPException(400, str(e))

    def _b(body: dict | None) -> dict[str, Any]:
        return dict(body or {})

    def _s(v) -> str:
        return "" if v is None else str(v)

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
        return await run(S.save_settings, tenant, "owner", **{k: b[k] for k in S._SET_KEYS if k in b})

    @r.post("/heads")
    async def head(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.set_head, tenant, _s(b.get("key")), b.get("rate"), _s(b.get("label")), _s(b.get("basis")), _s(b.get("fund")),
                         bool(b.get("remove")))

    # ---- flats
    @r.get("/flats")
    async def list_flats(q: str = "", tenant: str = Depends(current_tenant)):
        return {"flats": await run(S.flats, tenant, q)}

    @r.post("/flats")
    async def add_flat(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        unit = _s(b.pop("unit", ""))
        b.pop("flat", None)
        return await run(S.save_flat, tenant, unit, "", "owner", **{k: b[k] for k in S._FLAT_KEYS if k in b})

    @r.get("/flats/{fid}")
    async def get_flat(fid: str, tenant: str = Depends(current_tenant)):
        return await run(S.flat_view, tenant, fid)

    @r.patch("/flats/{fid}")
    async def patch_flat(fid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.save_flat, tenant, "", fid, "owner", **{k: b[k] for k in S._FLAT_KEYS if k in b})

    @r.post("/flats/import")
    async def import_flats(file: UploadFile = File(...), tenant: str = Depends(current_tenant)):
        data = await file.read()
        if len(data) > 10 * 1024 * 1024:
            raise HTTPException(413, "File 10 MB se badi.")
        return await run(S.import_flats, tenant, data, file.filename or "flats.csv")

    @r.post("/flats/{fid}/nominate")
    async def nominate(fid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.nominate, tenant, fid, _s(b.get("name")), _s(b.get("relation")), b.get("share_pct"), bool(b.get("revoke")))

    @r.post("/flats/{fid}/transfer")
    async def transfer(fid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.transfer, tenant, fid, _s(b.get("new_owner")), _s(b.get("phone")), b.get("premium"), _s(b.get("on")),
                         _s(b.get("share_cert")))

    @r.post("/flats/{fid}/parking")
    async def parking(fid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.parking, tenant, fid, _s(b.get("slot")), _s(b.get("kind") or "car"), _s(b.get("resolution")), bool(b.get("remove")))

    @r.post("/flats/{fid}/forget")
    async def forget(fid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.forget, tenant, fid, _s(_b(body).get("who") or "tenant"))

    @r.post("/flats/{fid}/receipt")
    async def receipt(fid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.receive, tenant, fid, b.get("amount"), _s(b.get("mode") or "upi"), _s(b.get("ref")), _s(b.get("day")))

    @r.get("/parking")
    async def parking_register(tenant: str = Depends(current_tenant)):
        return {"parking": await run(S.parking_register, tenant)}

    # ---- bills / dues
    @r.post("/bills")
    async def make_bills(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.make_bills, tenant, _s(b.get("period")), b.get("flats"))

    @r.get("/bills")
    async def list_bills(period: str = "", status: str = "", flat: str = "", tenant: str = Depends(current_tenant)):
        return {"bills": await run(S.bills, tenant, period, status, flat)}

    @r.get("/dues")
    async def dues(tenant: str = Depends(current_tenant)):
        return await run(S.dues, tenant)

    @r.post("/remind")
    async def remind(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.remind, tenant, b.get("flats"), _s(b.get("text")), _s(b.get("via") or "self"), int(b.get("min_days") or 0))

    @r.post("/messages")
    async def message(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.message, tenant, b.get("flats") or [], _s(b.get("text")), _s(b.get("via") or "self"))

    @r.post("/penalties")
    async def penalty(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.penalty_request, tenant, _s(b.get("flat")), _s(b.get("what")), b.get("amount"), _s(b.get("rule")))

    # ---- cards (HER tap)
    @r.get("/cards")
    async def list_cards(status: str = "waiting", tenant: str = Depends(current_tenant)):
        return {"cards": await run(S.cards, tenant, status)}

    @r.post("/cards/{cid}/challenge")
    async def challenge(cid: str, tenant: str = Depends(current_tenant)):
        return await run(S.challenge, tenant, cid)

    @r.post("/cards/{cid}/decide")
    async def decide(cid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        if "yes" not in b:
            raise HTTPException(400, "yes chahiye (Haan / Mana).")
        return await run(S.decide_card, tenant, cid, bool(b.get("yes")), _s(b.get("hash")), _s(b.get("reason")), b.get("proof"),
                         _s(b.get("via")), by_tap=True)

    # ---- complaints
    @r.get("/complaints")
    async def list_complaints(status: str = "open", tenant: str = Depends(current_tenant)):
        return {"complaints": await run(S.complaints, tenant, status)}

    @r.post("/complaints")
    async def new_complaint(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.complaint_new, tenant, _s(b.get("text")), _s(b.get("flat")), _s(b.get("kind") or "complaint"))

    @r.patch("/complaints/{cid}")
    async def upd_complaint(cid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.complaint_update, tenant, cid, _s(b.get("status")), _s(b.get("note")), _s(b.get("contract")))

    # ---- notices / meetings
    @r.get("/notices")
    async def list_notices(status: str = "", tenant: str = Depends(current_tenant)):
        return {"notices": await run(S.notices, tenant, status)}

    @r.post("/notices")
    async def new_notice(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.notice_draft, tenant, _s(b.get("kind") or "notice"), _s(b.get("title")), _s(b.get("body")),
                         _s(b.get("meeting")), _s(b.get("audience") or "all"), b.get("flats"))

    @r.patch("/notices/{nid}")
    async def edit_notice(nid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.notice_edit, tenant, nid, _s(b.get("body")), _s(b.get("title")))

    @r.post("/notices/{nid}/send")
    async def send_notice(nid: str, tenant: str = Depends(current_tenant)):
        return await run(S.notice_send, tenant, nid)

    @r.get("/meetings")
    async def list_meetings(status: str = "", tenant: str = Depends(current_tenant)):
        return {"meetings": await run(S.meetings, tenant, status)}

    @r.post("/meetings")
    async def plan(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.meeting_plan, tenant, _s(b.get("kind") or "agm"), _s(b.get("day")), _s(b.get("time")), _s(b.get("place")),
                         b.get("agenda"))

    @r.get("/meetings/{mid}")
    async def get_meeting(mid: str, tenant: str = Depends(current_tenant)):
        return await run(S.meeting_view, tenant, mid)

    @r.post("/meetings/{mid}/held")
    async def held(mid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.meeting_held, tenant, mid, b.get("present"), b.get("present_count"), _s(b.get("chair")), _s(b.get("notes")))

    @r.post("/meetings/{mid}/resolution")
    async def resolution(mid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.resolution, tenant, mid, _s(b.get("text")), _s(b.get("proposer")), _s(b.get("seconder")), b.get("for"),
                         b.get("against"))

    @r.post("/meetings/{mid}/minutes")
    async def minutes(mid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.minutes_final, tenant, mid, _s(_b(body).get("text")))

    # ---- vendors / spends
    @r.get("/contracts")
    async def list_contracts(tenant: str = Depends(current_tenant)):
        return {"contracts": await run(S.contracts, tenant)}

    @r.post("/contracts")
    async def save_contract(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.contract_save, tenant, _s(b.get("vendor")), _s(b.get("kind") or "other"), _s(b.get("phone")), b.get("amount"),
                         _s(b.get("per") or "year"), _s(b.get("start")), _s(b.get("end")), _s(b.get("visits")), b.get("individual"),
                         _s(b.get("contract") or b.get("id")), _s(b.get("status")), _s(b.get("notes")))

    @r.get("/spends")
    async def list_spends(status: str = "", tenant: str = Depends(current_tenant)):
        return {"spends": await run(S.spends, tenant, status)}

    @r.post("/spends")
    async def spend(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.spend_request, tenant, _s(b.get("kind") or "other"), _s(b.get("what")), b.get("amount"), _s(b.get("vendor")),
                         _s(b.get("contract")), _s(b.get("fund") or "general"), _s(b.get("resolution")))

    @r.post("/spends/{sid}/done")
    async def spend_done(sid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.spend_done, tenant, sid, b.get("amount"), _s(b.get("ref")), _s(b.get("day")))

    # ---- staff / visitors
    @r.get("/staff")
    async def list_staff(tenant: str = Depends(current_tenant)):
        return {"staff": await run(S.staff_list, tenant)}

    @r.post("/staff")
    async def save_staff(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.staff_save, tenant, _s(b.get("name")), _s(b.get("role") or "other"), _s(b.get("agency")), b.get("flats"),
                         _s(b.get("phone")), _s(b.get("verified_on")), _s(b.get("status")), _s(b.get("id")))

    @r.get("/visits")
    async def list_visits(inside: bool = False, days: int = 1, tenant: str = Depends(current_tenant)):
        return {"visits": await run(S.visits, tenant, inside, days)}

    @r.post("/visits")
    async def visit_in(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.visit_in, tenant, _s(b.get("name")), _s(b.get("flat")), _s(b.get("purpose")), _s(b.get("phone")),
                         _s(b.get("vehicle")), _s(b.get("kind") or "visitor"))

    @r.post("/visits/{vid}/out")
    async def visit_out(vid: str, tenant: str = Depends(current_tenant)):
        return await run(S.visit_out, tenant, vid)

    # ---- accounts
    @r.get("/accounts")
    async def accounts(fy: str = "", tenant: str = Depends(current_tenant)):
        return await run(S.accounts, tenant, fy)

    @r.post("/audit")
    async def audit(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.mark_audit, tenant, _s(b.get("fy")), _s(b.get("on")), _s(b.get("auditor")))

    @r.get("/calendar")
    async def calendar(tenant: str = Depends(current_tenant)):
        return {"calendar": await run(S.calendar, tenant)}

    @r.post("/register")
    async def register(tenant: str = Depends(current_tenant)):
        return await run(S.register_file, tenant)

    return r
