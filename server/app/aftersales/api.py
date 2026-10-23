"""HTTP routes for After-sales Sahayak (Profile > After-sales Sahayak in the app).

main.py: `app.include_router(aftersales_api.make_router(require_key, current_tenant))`.
Her taps that the tools can never make: POST /api/aftersales/visits/{id}/charge (charge the customer),
POST /api/aftersales/messages/{id}/send (business WhatsApp), POST /api/aftersales/templates/{name}/submit (to Meta).
"""
from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, Response


def _err(e: Exception):
    raise HTTPException(400, str(e))


def make_router(require_key, current_tenant) -> APIRouter:
    from . import service as S

    r = APIRouter(dependencies=[Depends(require_key)])

    def run(fn, *a, **kw):
        try:
            return fn(*a, **kw)
        except S.AsError as e:
            _err(e)

    async def arun(fn, *a, **kw):
        try:
            return await asyncio.to_thread(fn, *a, **kw)
        except S.AsError as e:
            _err(e)

    @r.get("/api/aftersales")
    async def overview(tenant: str = Depends(current_tenant)):
        return await arun(S.overview, tenant)

    @r.get("/api/aftersales/day")
    async def day(tenant: str = Depends(current_tenant)):
        return await arun(S.day, tenant)

    @r.get("/api/aftersales/settings")
    def get_settings(tenant: str = Depends(current_tenant)):
        return S.settings(tenant)

    @r.post("/api/aftersales/settings")
    def post_settings(body: dict, tenant: str = Depends(current_tenant)):
        keys = ("business", "phone", "address", "gstin", "gst_on", "gst_pct", "sac", "prices", "day_start", "day_end", "work_days",
                "travel_minutes", "lead_minutes", "remind_days", "terms", "rule", "morning_time")
        return run(S.save_settings, tenant, **{k: body[k] for k in keys if k in body})

    @r.get("/api/aftersales/schedules")
    def get_schedules(tenant: str = Depends(current_tenant)):
        return {"schedules": S.schedules(tenant)}

    @r.post("/api/aftersales/schedules")
    def post_schedule(body: dict, tenant: str = Depends(current_tenant)):
        return run(S.set_schedule, tenant, str(body.get("ptype") or ""), body.get("months"), body.get("usage"))

    @r.get("/api/aftersales/due")
    async def get_due(within: int = 15, tenant: str = Depends(current_tenant)):
        return await arun(S.due, tenant, within)

    @r.post("/api/aftersales/customers")
    def post_customer(body: dict, tenant: str = Depends(current_tenant)):
        keys = ("name", "phone", "area", "pincode", "address", "customer", "no_messages", "marketing_ok", "notes")
        return run(S.save_customer, tenant, **{k: body[k] for k in keys if k in body})

    @r.get("/api/aftersales/units")
    async def get_units(q: str = "", tenant: str = Depends(current_tenant)):
        return {"units": await arun(S.units, tenant, q)}

    @r.post("/api/aftersales/units")
    def post_unit(body: dict, tenant: str = Depends(current_tenant)):
        keys = ("unit", "ptype", "brand", "model", "serial", "installed_on", "purchased_on", "warranty_months", "warranty_until", "last_service",
                "reading", "notes", "name", "phone", "area", "pincode", "address", "customer", "status")
        return run(S.save_unit, tenant, **{k: body[k] for k in keys if k in body})

    @r.get("/api/aftersales/units/{uid}")
    def get_unit(uid: str, tenant: str = Depends(current_tenant)):
        return run(S.get_unit, tenant, uid)

    @r.post("/api/aftersales/units/{uid}/amc")
    def post_amc(uid: str, body: dict, tenant: str = Depends(current_tenant)):
        return run(S.set_amc, tenant, uid, str(body.get("plan") or "non_comprehensive"), str(body.get("start") or ""), body.get("months", 12),
                   body.get("visits"), body.get("price"))

    @r.post("/api/aftersales/import")
    async def post_import(body: dict, tenant: str = Depends(current_tenant)):
        """JSON {file_id} or {name, data_b64} (the app's generic call can't do multipart)."""
        if body.get("file_id"):
            return await arun(S.import_units, tenant, file_id=str(body["file_id"]))
        return await arun(S.import_units, tenant, run(S.decode_b64, body.get("data_b64")), str(body.get("name") or "units.csv"))

    @r.post("/api/aftersales/import_file")
    async def post_import_file(file: UploadFile = File(...), tenant: str = Depends(current_tenant)):
        data = await file.read()
        return await arun(S.import_units, tenant, data, file.filename or "units.csv")

    @r.get("/api/aftersales/techs")
    def get_techs(tenant: str = Depends(current_tenant)):
        return {"techs": S.techs(tenant)}

    @r.post("/api/aftersales/techs")
    def post_tech(body: dict, tenant: str = Depends(current_tenant)):
        keys = ("name", "tech", "phone", "skills", "areas", "per_day", "off_days", "active")
        return run(S.save_tech, tenant, **{k: body[k] for k in keys if k in body})

    @r.get("/api/aftersales/slots")
    async def get_slots(unit: str, days: int = 5, tech: str = "", day: str = "", tenant: str = Depends(current_tenant)):
        return await arun(S.slots, tenant, unit, days, tech, day)

    @r.get("/api/aftersales/visits")
    async def get_visits(day: str = "", status: str = "", tech: str = "", tenant: str = Depends(current_tenant)):
        return {"visits": await arun(S.visits, tenant, day, status, tech)}

    @r.post("/api/aftersales/visits")
    async def post_visit(body: dict, tenant: str = Depends(current_tenant)):
        return await arun(S.book, tenant, str(body.get("unit") or ""), str(body.get("start") or ""), str(body.get("tech") or ""),
                          str(body.get("kind") or "service"), str(body.get("problem") or ""), body.get("minutes"), bool(body.get("force")))

    @r.get("/api/aftersales/visits/{vid}")
    def get_visit(vid: str, tenant: str = Depends(current_tenant)):
        return run(S.get_visit, tenant, vid)

    @r.get("/api/aftersales/visits/{vid}/report.pdf")
    def get_report_pdf(vid: str, tenant: str = Depends(current_tenant)):
        data = run(S.report_pdf, tenant, vid)
        return Response(data, media_type="application/pdf", headers={"Content-Disposition": f'inline; filename="service-report-{vid}.pdf"'})

    @r.get("/api/aftersales/visits/{vid}/photos/{pid}")
    def get_photo(vid: str, pid: str, tenant: str = Depends(current_tenant)):
        path, mime = run(S.photo_file, tenant, vid, pid)
        return FileResponse(path, media_type=mime, headers={"Cache-Control": "private, max-age=3600"})

    @r.post("/api/aftersales/visits/{vid}/photo")
    async def post_photo(vid: str, body: dict, tenant: str = Depends(current_tenant)):
        kind = str(body.get("kind") or "work")
        if body.get("file_id"):
            return await arun(S.attach_file, tenant, vid, str(body["file_id"]), kind)
        return await arun(S.add_photo, tenant, vid, run(S.decode_b64, body.get("data_b64")), kind)

    @r.post("/api/aftersales/visits/{vid}/charge")
    def post_charge(vid: str, body: dict, tenant: str = Depends(current_tenant)):
        """HER tap on the charge card: {yes, total?, hash?}. The only way a customer charge is approved."""
        return run(S.decide_charge, tenant, vid, bool(body.get("yes")), body.get("total"), True, str(body.get("hash") or ""))

    @r.post("/api/aftersales/visits/{vid}/{action}")
    async def visit_action(vid: str, action: str, body: dict, tenant: str = Depends(current_tenant)):
        if action == "reschedule":
            return await arun(S.reschedule, tenant, vid, str(body.get("start") or ""), str(body.get("tech") or ""), bool(body.get("force")))
        if action in ("on_way", "cancel", "no_show"):
            return await arun(S.set_status, tenant, vid, {"cancel": "cancelled"}.get(action, action), str(body.get("note") or ""))
        if action == "done":
            return await arun(S.complete, tenant, vid, body.get("checklist"), body.get("readings"), body.get("parts"), body.get("labour"),
                              str(body.get("notes") or ""), str(body.get("signed_by") or ""), str(body.get("done_at") or ""))
        if action == "job_card":
            return await arun(S.job_card, tenant, vid)
        if action == "report":
            return await arun(S.report, tenant, vid)
        if action == "paid":
            return await arun(S.mark_paid, tenant, vid, body.get("amount"), str(body.get("how") or ""))
        if action == "claim":
            return await arun(S.claim, tenant, "", vid, str(body.get("part") or ""), str(body.get("fault") or ""), str(body.get("brand_ref") or ""),
                              body.get("amount"))
        raise HTTPException(404, "action nahi")

    @r.post("/api/aftersales/remind")
    async def post_remind(body: dict, tenant: str = Depends(current_tenant)):
        return await arun(S.remind, tenant, body.get("within"), str(body.get("kind") or "due"), str(body.get("unit") or ""))

    @r.get("/api/aftersales/messages")
    def get_messages(status: str = "draft", kind: str = "", tenant: str = Depends(current_tenant)):
        return {"messages": S.messages(tenant, status, kind)}

    @r.post("/api/aftersales/messages/{mid}/send")
    async def post_send(mid: str, body: dict, tenant: str = Depends(current_tenant)):
        """HER tap: business WhatsApp (via template | business)."""
        try:
            return await S.send_message(tenant, mid, str(body.get("via") or "template"), by_tap=True)
        except S.AsError as e:
            _err(e)

    @r.post("/api/aftersales/messages/{mid}/{status}")
    def post_mark(mid: str, status: str, tenant: str = Depends(current_tenant)):
        if status not in ("sent", "skipped", "draft"):
            raise HTTPException(404, "status nahi")
        return run(S.message_mark, tenant, mid, status)

    @r.get("/api/aftersales/templates")
    def get_templates(tenant: str = Depends(current_tenant)):
        return {"templates": S.templates(tenant)}

    @r.post("/api/aftersales/templates/{name}/submit")
    async def post_template(name: str, tenant: str = Depends(current_tenant)):
        try:
            return await S.submit_template(tenant, name, by_tap=True)
        except S.AsError as e:
            _err(e)

    @r.get("/api/aftersales/amc")
    async def get_amc(tenant: str = Depends(current_tenant)):
        return await arun(S.amc_view, tenant)

    @r.get("/api/aftersales/claims")
    def get_claims(status: str = Query(""), tenant: str = Depends(current_tenant)):
        return S.claims(tenant, status)

    @r.post("/api/aftersales/claims")
    def post_claim(body: dict, tenant: str = Depends(current_tenant)):
        return run(S.claim, tenant, str(body.get("unit") or ""), str(body.get("visit") or ""), str(body.get("part") or ""),
                   str(body.get("fault") or ""), str(body.get("brand_ref") or ""), body.get("amount"))

    @r.post("/api/aftersales/claims/{cid}")
    def post_claim_update(cid: str, body: dict, tenant: str = Depends(current_tenant)):
        return run(S.claim_update, tenant, cid, str(body.get("status") or ""), str(body.get("brand_ref") or ""), body.get("settled"),
                   str(body.get("note") or ""))

    return r
