"""HTTP routes of the Site Sahayak (/api/sitesup/*). main.py: app.include_router(make_router(require_key, current_tenant)).

Her taps live ONLY here: POST /api/sitesup/indents/{id}/decide (material indent / purchase; fingerprint once a phone key is set up and
the amount is known: 428 -> POST /api/sitesup/indents/{id}/challenge, sign, resend with `proof`), POST /api/sitesup/reports/{id}/decide
(DPR / message to the client), POST /api/sitesup/stops/{id}/decide and /lift (stop-work order and lifting it)."""
from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, Body, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response


def make_router(require_key, current_tenant) -> APIRouter:
    from . import service as S

    r = APIRouter(prefix="/api/sitesup", dependencies=[Depends(require_key)])

    async def run(fn, *a, **k):
        try:
            return await asyncio.to_thread(fn, *a, **k)
        except S.SiteError as e:
            code = str(e)
            if code in ("fingerprint_needed", "fingerprint_invalid"):
                raise HTTPException(428, code)
            raise HTTPException(400, code)
        except ValueError as e:
            raise HTTPException(400, str(e))

    def b_(body: dict | None) -> dict[str, Any]:
        return dict(body or {})

    def s_(v) -> str:
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
        b = b_(body)
        return await run(S.save_settings, tenant, **{k: b[k] for k in S._SET_KEYS if k in b})

    # ---- sites + plan + progress
    @r.get("/sites")
    async def list_sites(status: str = "", tenant: str = Depends(current_tenant)):
        return {"sites": await run(S.sites, tenant, status)}

    @r.post("/sites")
    async def add_site(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = b_(body)
        name, site = s_(b.pop("name", "")), s_(b.pop("site", ""))
        return await run(S.save_site, tenant, name, site, **b)

    @r.get("/sites/{sid}")
    async def get_site(sid: str, tenant: str = Depends(current_tenant)):
        v = await run(S.site_view, tenant, sid)
        v["activities"] = await run(S.activities, tenant, sid)
        v["material"] = await run(S.material_balance, tenant, sid)
        v["labour_today"] = await run(S.labour_day, tenant, sid, "")
        v["snags"] = await run(S.snags, tenant, sid, "")
        v["pours"] = await run(S.pours, tenant, sid)
        v["safety"] = await run(S.safety_log, tenant, sid, "", 30)
        v["reports"] = await run(S.reports, tenant, sid, "")
        return v

    @r.patch("/sites/{sid}")
    async def patch_site(sid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = b_(body)
        b.pop("site", None)
        name = s_(b.pop("name", ""))
        return await run(S.save_site, tenant, name, sid, **b)

    @r.post("/sites/{sid}/plan")
    async def plan(sid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = b_(body)
        return await run(S.plan, tenant, sid, b.get("items"), bool(b.get("from_boq")))

    @r.post("/sites/{sid}/progress")
    async def progress(sid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = b_(body)
        return await run(S.progress, tenant, sid, s_(b.get("activity")), b.get("qty"), s_(b.get("day")), s_(b.get("note")), s_(b.get("delay")),
                         b.get("lost_hours"), b.get("by_client"), "owner")

    @r.get("/sites/{sid}/lookahead")
    async def lookahead(sid: str, days: int = 0, tenant: str = Depends(current_tenant)):
        return await run(S.lookahead, tenant, sid, days or None)

    # ---- labour
    @r.post("/sites/{sid}/attendance")
    async def attendance(sid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = b_(body)
        rows = b.pop("rows", None)
        d = s_(b.pop("day", ""))
        return await run(S.attendance, tenant, sid, rows, d, "owner", **b)

    @r.get("/sites/{sid}/register")
    async def register(sid: str, start: str = "", end: str = "", tenant: str = Depends(current_tenant)):
        return await run(S.register, tenant, sid, start, end)

    @r.post("/sites/{sid}/register_file")
    async def register_file(sid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = b_(body)
        return await run(S.register_file, tenant, sid, s_(b.get("start")), s_(b.get("end")))

    # ---- material + indents
    @r.post("/sites/{sid}/material")
    async def material(sid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = b_(body)
        return await run(S.material, tenant, sid, s_(b.get("item")), b.get("qty"), s_(b.get("kind") or "in"), s_(b.get("unit")),
                         s_(b.get("supplier")), s_(b.get("challan")), s_(b.get("vehicle")), b.get("ok", True) is not False, s_(b.get("note")),
                         s_(b.get("day")), s_(b.get("indent")), "owner")

    @r.post("/sites/{sid}/indents")
    async def indent_new(sid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = b_(body)
        return await run(S.indent_request, tenant, sid, b.get("items"), s_(b.get("need_by")), s_(b.get("reason")), s_(b.get("supplier")),
                         s_(b.get("supplier_phone")), b.get("amount"), "owner")

    @r.get("/indents")
    async def indent_list(status: str = "", tenant: str = Depends(current_tenant)):
        return {"indents": await run(S.indents, tenant, status)}

    @r.post("/indents/{iid}/challenge")
    async def indent_challenge(iid: str, tenant: str = Depends(current_tenant)):
        return await run(S.indent_challenge, tenant, iid)

    @r.post("/indents/{iid}/decide")
    async def indent_decide(iid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = b_(body)
        return await run(S.decide_indent, tenant, iid, bool(b.get("yes")), s_(b.get("hash")), s_(b.get("reason")), b.get("proof"), by_tap=True)

    @r.post("/indents/{iid}/ordered")
    async def indent_ordered(iid: str, tenant: str = Depends(current_tenant)):
        return await run(S.indent_ordered, tenant, iid)

    # ---- safety + stop work
    @r.post("/sites/{sid}/toolbox")
    async def toolbox(sid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = b_(body)
        return await run(S.toolbox, tenant, sid, s_(b.get("topic")), b.get("people"), s_(b.get("by")), s_(b.get("note")), s_(b.get("day")), "owner")

    @r.post("/sites/{sid}/checklist")
    async def checklist(sid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = b_(body)
        return await run(S.checklist, tenant, sid, s_(b.get("kind")), b.get("answers") or {}, s_(b.get("area")), s_(b.get("day")), "owner")

    @r.post("/sites/{sid}/incident")
    async def incident(sid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = b_(body)
        return await run(S.incident, tenant, sid, s_(b.get("text")), s_(b.get("kind")), s_(b.get("at")), b.get("people"), s_(b.get("names")),
                         s_(b.get("action")), s_(b.get("injury_off_since")), "owner")

    @r.get("/incidents/{iid}/form")
    async def form_xi(iid: str, tenant: str = Depends(current_tenant)):
        return {"text": await run(S.form_xi_text, tenant, iid)}

    @r.post("/incidents/{iid}/reported")
    async def reported(iid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.incident_reported, tenant, iid, s_(b_(body).get("ref")))

    @r.get("/stops")
    async def stop_list(status: str = "", tenant: str = Depends(current_tenant)):
        return {"stops": await run(S.stops, tenant, status)}

    @r.post("/sites/{sid}/stops")
    async def stop_new(sid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = b_(body)
        return await run(S.stop_request, tenant, sid, s_(b.get("area")), s_(b.get("reason")), "", s_(b.get("contractor")), "owner")

    @r.post("/stops/{wid}/decide")
    async def stop_decide(wid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = b_(body)
        return await run(S.decide_stop, tenant, wid, bool(b.get("yes")), s_(b.get("hash")), by_tap=True)

    @r.post("/stops/{wid}/lift")
    async def stop_lift(wid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.lift_stop, tenant, wid, s_(b_(body).get("note")), by_tap=True)

    # ---- quality
    @r.post("/sites/{sid}/pours")
    async def pour(sid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = b_(body)
        return await run(S.pour, tenant, sid, s_(b.get("element")), s_(b.get("grade")), b.get("volume"), s_(b.get("cement")), s_(b.get("day")),
                         s_(b.get("source")), s_(b.get("slump")), b.get("checks"), bool(b.get("hot_dry")), b.get("ages"), "owner")

    @r.post("/pours/{pid}/cubes")
    async def cubes(pid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = b_(body)
        return await run(S.cube_result, tenant, pid, b.get("age"), b.get("results"), int(b.get("sample") or 1), s_(b.get("lab")), s_(b.get("tested_on")))

    @r.get("/cubes_due")
    async def cubes_due(within: int = 3, tenant: str = Depends(current_tenant)):
        return {"cubes": await run(S.cubes_due, tenant, within)}

    @r.post("/sites/{sid}/snags")
    async def snag(sid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = b_(body)
        return await run(S.snag, tenant, sid, s_(b.get("text")), s_(b.get("location")), s_(b.get("trade")), s_(b.get("contractor")),
                         s_(b.get("due")), "owner")

    @r.post("/snags/{nid}/status")
    async def snag_status(nid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.snag_status, tenant, nid, s_(b_(body).get("status")), "owner")

    @r.post("/sites/{sid}/photo")
    async def photo(sid: str, file: UploadFile = File(...), ref: str = Form(""), stage: str = Form("site"), note: str = Form(""),
                    tenant: str = Depends(current_tenant)):
        data = await file.read()
        if len(data) > 20 * 1024 * 1024:
            raise HTTPException(413, "Photo 20 MB se badi.")
        return await run(S.add_photo, tenant, data, sid, ref, stage, note)

    @r.get("/photos/{pid}")
    async def photo_get(pid: str, tenant: str = Depends(current_tenant)):
        data = await run(S.photo_bytes, tenant, pid)
        return Response(data, media_type="image/jpeg", headers={"Cache-Control": "private, max-age=86400"})

    # ---- DPR + client messages
    @r.post("/sites/{sid}/dpr")
    async def dpr(sid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = b_(body)
        return await run(S.dpr_request, tenant, sid, s_(b.get("day")), s_(b.get("weather")), s_(b.get("tomorrow")), s_(b.get("remarks")),
                         s_(b.get("to_phone")), "owner")

    @r.post("/sites/{sid}/message")
    async def message(sid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = b_(body)
        return await run(S.message_request, tenant, sid, s_(b.get("text")), s_(b.get("to_phone")))

    @r.get("/reports")
    async def report_list(status: str = "", tenant: str = Depends(current_tenant)):
        return {"reports": await run(S.reports, tenant, "", status)}

    @r.post("/reports/{rid}/decide")
    async def report_decide(rid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = b_(body)
        try:
            return await S.decide_report(tenant, rid, bool(b.get("yes")), s_(b.get("hash")), s_(b.get("via") or "self"), by_tap=True)
        except S.SiteError as e:
            raise HTTPException(400, str(e))

    @r.post("/reports/{rid}/sent")
    async def report_sent(rid: str, tenant: str = Depends(current_tenant)):
        return await run(S.report_sent, tenant, rid)

    @r.post("/sites/{sid}/forget")
    async def forget(sid: str, tenant: str = Depends(current_tenant)):
        return await run(S.forget, tenant, sid)

    return r
