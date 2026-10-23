"""HTTP routes of the Interior Sahayak (/api/interior/*). main.py: app.include_router(make_router(require_key, current_tenant)).

HER taps live ONLY here (by_tap=True): quotation to the client (/quotes/{id}/decide), vendor order (/orders/{id}/decide, with her
fingerprint once a phone key is active: 428 -> /orders/{id}/challenge -> sign -> resend with `proof`), change order that changes the
price (/changes/{id}/decide), payment request (/stages/{id}/decide). All routes are key-protected; no public routes."""
from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, Body, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response

MAX_UPLOAD = 15 * 1024 * 1024


def make_router(require_key, current_tenant) -> APIRouter:
    from . import service as S

    r = APIRouter(prefix="/api/interior", dependencies=[Depends(require_key)])

    async def run(fn, *a, **k):
        try:
            return await asyncio.to_thread(fn, *a, **k)
        except S.InteriorError as e:
            code = str(e)
            if code in ("fingerprint_needed", "fingerprint_invalid"):
                raise HTTPException(428, code)
            raise HTTPException(400, code)
        except ValueError as e:
            raise HTTPException(400, str(e))

    def _b(body: dict | None) -> dict[str, Any]:
        return dict(body or {})

    async def _read(file: UploadFile) -> bytes:
        data = await file.read()
        if len(data) > MAX_UPLOAD:
            raise HTTPException(413, "File 15 MB se badi.")
        return data

    @r.get("")
    async def overview(tenant: str = Depends(current_tenant)):
        return await run(S.overview, tenant)

    @r.get("/day")
    async def day(tenant: str = Depends(current_tenant)):
        return await run(S.day, tenant)

    @r.get("/waiting")
    async def waiting(tenant: str = Depends(current_tenant)):
        return await run(S.waiting, tenant)

    @r.get("/settings")
    async def get_settings(tenant: str = Depends(current_tenant)):
        return await run(S.settings, tenant)

    @r.put("/settings")
    async def put_settings(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.save_settings, tenant, **{k: b[k] for k in S._SET_KEYS if k in b})

    # ---- rate card + vendors
    @r.get("/rates")
    async def list_rates(q: str = "", tenant: str = Depends(current_tenant)):
        return {"rates": await run(S.rates, tenant, q)}

    @r.post("/rates")
    async def save_rate(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.rate_save, tenant, str(b.get("name") or ""), b.get("rate"), str(b.get("unit") or ""), str(b.get("kind") or ""),
                         str(b.get("code") or ""), str(b.get("spec") or ""), str(b.get("hsn_sac") or ""), b.get("gst_pct"), str(b.get("id") or ""))

    @r.delete("/rates/{rid}")
    async def del_rate(rid: str, tenant: str = Depends(current_tenant)):
        return await run(S.rate_remove, tenant, rid)

    @r.post("/rates/import")
    async def import_rates(file: UploadFile = File(...), tenant: str = Depends(current_tenant)):
        data = await _read(file)
        return await run(S.import_rates, tenant, "", data, file.filename or "rates.csv")

    @r.get("/vendors")
    async def list_vendors(tenant: str = Depends(current_tenant)):
        return {"vendors": await run(S.vendors, tenant)}

    @r.post("/vendors")
    async def save_vendor(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.vendor_save, tenant, str(b.get("name") or ""), str(b.get("trade") or ""), str(b.get("phone") or ""),
                         str(b.get("gstin") or ""), str(b.get("notes") or ""), str(b.get("id") or ""))

    # ---- projects
    @r.get("/projects")
    async def list_projects(status: str = "", tenant: str = Depends(current_tenant)):
        return {"projects": await run(S.projects, tenant, status)}

    @r.post("/projects")
    async def new_project(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.project_save, tenant, str(b.get("name") or ""), "", "owner", "", **{k: b[k] for k in S._PROJ_KEYS if k in b})

    @r.get("/projects/{pid}")
    async def get_project(pid: str, tenant: str = Depends(current_tenant)):
        return await run(S.project_view, tenant, pid)

    @r.patch("/projects/{pid}")
    async def patch_project(pid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.project_save, tenant, str(b.get("name") or ""), pid, "owner", "", **{k: b[k] for k in S._PROJ_KEYS if k in b})

    @r.post("/projects/{pid}/brief")
    async def brief(pid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.brief, tenant, pid, str(b.get("room") or ""), str(b.get("style") or ""), b.get("budget"), b.get("must"),
                         b.get("avoid"), str(b.get("notes") or ""), str(b.get("room_type") or ""))

    @r.post("/projects/{pid}/measure")
    async def measure(pid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.measure, tenant, pid, str(b.get("room") or ""), b.get("l"), b.get("w"), b.get("h"), str(b.get("unit") or ""),
                         b.get("openings"), str(b.get("notes") or ""), str(b.get("by") or ""))

    @r.post("/projects/{pid}/measure_sheet")
    async def measure_sheet(pid: str, tenant: str = Depends(current_tenant)):
        return await run(S.measure_sheet, tenant, pid)

    @r.post("/projects/{pid}/concept")
    async def concept(pid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.concept, tenant, pid, str(b.get("room") or ""), str(b.get("style") or ""), str(b.get("words") or ""),
                         int(b.get("pictures") or 0), b.get("file_ids"), bool(b.get("brand_colors")))

    @r.post("/projects/{pid}/render3d")
    async def render3d(pid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.render3d, tenant, pid, str(b.get("room") or ""), str(b.get("words") or ""))

    @r.get("/projects/{pid}/boq")
    async def get_boq(pid: str, tenant: str = Depends(current_tenant)):
        return await run(S.boq, tenant, pid)

    @r.post("/projects/{pid}/boq")
    async def set_boq(pid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.boq_set, tenant, pid, b.get("lines"), bool(b.get("replace")))

    @r.delete("/projects/{pid}/boq/{line}")
    async def del_boq(pid: str, line: str, tenant: str = Depends(current_tenant)):
        return await run(S.boq_remove, tenant, pid, line)

    @r.post("/projects/{pid}/boq_file")
    async def boq_file(pid: str, tenant: str = Depends(current_tenant)):
        return await run(S.boq_file, tenant, pid)

    @r.post("/projects/{pid}/quote")
    async def make_quote(pid: str, tenant: str = Depends(current_tenant)):
        return await run(S.quote_make, tenant, pid)

    @r.get("/projects/{pid}/stages")
    async def get_stages(pid: str, tenant: str = Depends(current_tenant)):
        return await run(S.stages, tenant, pid)

    @r.get("/projects/{pid}/schedule")
    async def get_schedule(pid: str, tenant: str = Depends(current_tenant)):
        return await run(S.schedule, tenant, pid)

    @r.post("/projects/{pid}/tasks")
    async def add_task(pid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.task_add, tenant, pid, str(b.get("what") or ""), str(b.get("kind") or ""), str(b.get("room") or ""),
                         str(b.get("vendor") or ""), str(b.get("start") or ""), str(b.get("end") or ""), str(b.get("note") or ""))

    @r.patch("/tasks/{tid}")
    async def patch_task(tid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.task_update, tenant, tid, str(b.get("status") or ""), str(b.get("start") or ""), str(b.get("end") or ""),
                         str(b.get("note") or ""))

    @r.post("/projects/{pid}/orders")
    async def new_order(pid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.order_request, tenant, pid, str(b.get("vendor") or ""), b.get("lines"), b.get("amount"), str(b.get("start") or ""),
                         str(b.get("finish") or ""), str(b.get("notes") or ""))

    @r.post("/projects/{pid}/changes")
    async def new_change(pid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.change_request, tenant, pid, str(b.get("what") or ""), b.get("add"), b.get("remove"))

    @r.post("/projects/{pid}/snags")
    async def new_snag(pid: str, what: str = Form(""), room: str = Form(""), vendor: str = Form(""),
                       file: UploadFile | None = File(None), tenant: str = Depends(current_tenant)):
        data = await _read(file) if file is not None else None
        return await run(S.snag_add, tenant, pid, what, room, vendor, "", data)

    @r.post("/projects/{pid}/handover")
    async def do_handover(pid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.handover, tenant, pid, bool(b.get("force")), str(b.get("reason") or ""))

    @r.post("/projects/{pid}/forget")
    async def do_forget(pid: str, tenant: str = Depends(current_tenant)):
        return await run(S.forget, tenant, pid)

    # ---- quotes (her tap)
    @r.get("/quotes/{qid}")
    async def get_quote(qid: str, tenant: str = Depends(current_tenant)):
        return await run(S.quote_view, tenant, qid)

    @r.get("/quotes/{qid}/pdf")
    async def quote_pdf(qid: str, tenant: str = Depends(current_tenant)):
        q = await run(S.quote_view, tenant, qid)
        final = q["status"] in ("approved", "sent", "accepted")
        data = await run(S.quote_pdf, tenant, qid, final)
        return Response(data, media_type="application/pdf",
                        headers={"Content-Disposition": f'inline; filename="{q["number"].replace("/", "-")}.pdf"'})

    @r.post("/quotes/{qid}/request")
    async def quote_request(qid: str, tenant: str = Depends(current_tenant)):
        return await run(S.quote_request, tenant, qid)

    @r.post("/quotes/{qid}/decide")
    async def quote_decide(qid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.decide_quote, tenant, qid, bool(b.get("yes")), str(b.get("hash") or ""), str(b.get("reason") or ""), True)

    @r.post("/quotes/{qid}/mark")
    async def quote_mark(qid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.quote_mark, tenant, qid, str(_b(body).get("what") or ""), "owner")

    # ---- payment stages (her tap)
    @r.post("/stages/{sid}/due")
    async def stage_due(sid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.stage_due, tenant, sid, str(_b(body).get("due_on") or ""))

    @r.post("/stages/{sid}/request")
    async def stage_request(sid: str, tenant: str = Depends(current_tenant)):
        return await run(S.pay_request, tenant, sid)

    @r.post("/stages/{sid}/decide")
    async def stage_decide(sid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.decide_payment, tenant, sid, bool(b.get("yes")), str(b.get("hash") or ""), True)

    @r.post("/stages/{sid}/paid")
    async def stage_paid(sid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.stage_paid, tenant, sid, b.get("amount"), str(b.get("ref") or ""), str(b.get("day") or ""), "owner")

    # ---- vendor orders (her tap + fingerprint)
    @r.get("/orders")
    async def list_orders(status: str = "", tenant: str = Depends(current_tenant)):
        return {"orders": await run(S.orders, tenant, "", status)}

    @r.post("/orders/{oid}/challenge")
    async def order_challenge(oid: str, tenant: str = Depends(current_tenant)):
        return await run(S.order_challenge, tenant, oid)

    @r.post("/orders/{oid}/decide")
    async def order_decide(oid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        proof = b.get("proof") if isinstance(b.get("proof"), dict) else None
        return await run(S.decide_order, tenant, oid, bool(b.get("yes")), str(b.get("hash") or ""), str(b.get("reason") or ""), proof, True)

    @r.post("/orders/{oid}/done")
    async def order_done(oid: str, tenant: str = Depends(current_tenant)):
        return await run(S.order_done, tenant, oid)

    # ---- change orders (her tap)
    @r.post("/changes/{cid}/decide")
    async def change_decide(cid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.decide_change, tenant, cid, bool(b.get("yes")), str(b.get("hash") or ""), str(b.get("reason") or ""), True)

    # ---- snags
    @r.post("/snags/{sid}/photo")
    async def snag_photo(sid: str, stage: str = Form("fixed"), file: UploadFile = File(...), tenant: str = Depends(current_tenant)):
        data = await _read(file)
        return await run(S.snag_photo, tenant, sid, data, "", stage)

    @r.patch("/snags/{sid}")
    async def snag_status(sid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.snag_status, tenant, sid, str(_b(body).get("status") or ""), "owner")

    @r.get("/snags/{sid}/photos/{phid}")
    async def snag_photo_get(sid: str, phid: str, tenant: str = Depends(current_tenant)):
        path = await run(S.snag_file, tenant, sid, phid)
        return FileResponse(path, media_type="image/jpeg")

    return r
