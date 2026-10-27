"""HTTP routes of the Archassist Sahayak (/api/archassist/*). main.py: app.include_router(make_router(require_key, current_tenant)).

HER taps live ONLY here (by_tap=True): POST /transmittals/{id}/decide (drawings issued), /submissions/{id}/decide ("submit karo"),
/invoices/{id}/decide (invoice numbered; 428 fingerprint_needed -> POST /invoices/{id}/challenge, sign, resend with `proof`)."""
from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException


def make_router(require_key, current_tenant) -> APIRouter:
    from . import rules as R
    from . import service as S

    r = APIRouter(prefix="/api/archassist", dependencies=[Depends(require_key)])

    async def run(fn, *a, **k):
        try:
            return await asyncio.to_thread(fn, *a, **k)
        except S.ArchError as e:
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

    @r.get("")
    async def overview(tenant: str = Depends(current_tenant)):
        def go():
            return {"settings": S.settings(tenant), "projects": S.projects(tenant), "day": S.day(tenant), "consultants": S.consultants(tenant),
                    "never": R.NEVER}
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
        return {"rulesets": {k: {"label": v["label"], "fsi": v["fsi"], "front": v["front"], "notes": v["notes"]} for k, v in R.RULESETS.items()},
                "authorities": R.AUTHORITIES, "docs": R.PLOT_DOCS, "fee_stages": R.FEE_STAGES, "never": R.NEVER, "check": R.CHECK_LINE}

    # ---- projects
    @r.get("/projects")
    async def list_projects(status: str = "", tenant: str = Depends(current_tenant)):
        return {"projects": await run(S.projects, tenant, status)}

    @r.post("/projects")
    async def new_project(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        name = _s(b.pop("name", ""))
        b.pop("ref", None)
        return await run(S.save_project, tenant, name, "", **b)

    @r.get("/projects/{ref}")
    async def get_project(ref: str, tenant: str = Depends(current_tenant)):
        return await run(S.project_view, tenant, ref)

    @r.patch("/projects/{ref}")
    async def patch_project(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        name = _s(b.pop("name", ""))
        b.pop("ref", None)
        return await run(S.save_project, tenant, name, ref, **b)

    @r.post("/projects/{ref}/docs")
    async def doc(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.doc, tenant, ref, _s(b.get("key")), _s(b.get("state") or "have"), _s(b.get("file_id")), _s(b.get("note")),
                         _s(b.get("label")))

    @r.post("/projects/{ref}/area")
    async def area(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.area_check, tenant, ref, b.get("proposal") or {}, b.get("overrides") or {})

    @r.post("/projects/{ref}/forget")
    async def forget(ref: str, tenant: str = Depends(current_tenant)):
        return await run(S.forget, tenant, ref)

    @r.get("/projects/{ref}/register")
    async def register(ref: str, tenant: str = Depends(current_tenant)):
        return await run(S.register_file, tenant, ref)

    # ---- approvals + submissions
    @r.get("/projects/{ref}/approvals")
    async def approvals(ref: str, tenant: str = Depends(current_tenant)):
        return await run(S.approvals, tenant, ref)

    @r.post("/projects/{ref}/approvals")
    async def approval_set(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.approval_set, tenant, ref, _s(b.get("key")), _s(b.get("status")), _s(b.get("ref_no")), _s(b.get("on")),
                         _s(b.get("valid_to")), _s(b.get("file_id")), _s(b.get("note")))

    @r.post("/projects/{ref}/submissions")
    async def submission_request(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.submission_request, tenant, ref, _s(b.get("stage") or "building_permission"), "", _s(b.get("note")))

    @r.post("/submissions/{sid}/decide")
    async def decide_submission(sid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        if "yes" not in b:
            raise HTTPException(400, "yes = true | false")
        return await run(S.decide_submission, tenant, sid, bool(b["yes"]), _s(b.get("hash")), _s(b.get("reason")), by_tap=True)

    @r.post("/submissions/{sid}/update")
    async def submission_update(sid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.submission_update, tenant, sid, _s(b.get("status")), _s(b.get("ref_no")), _s(b.get("on")), _s(b.get("valid_to")),
                         _s(b.get("note")))

    # ---- drawings + transmittals
    @r.get("/projects/{ref}/drawings")
    async def list_drawings(ref: str, tenant: str = Depends(current_tenant)):
        return {"drawings": await run(S.drawings, tenant, ref)}

    @r.post("/projects/{ref}/drawings")
    async def drawing(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.drawing, tenant, ref, _s(b.get("sheet")), _s(b.get("title")), _s(b.get("discipline")), _s(b.get("scale")),
                         _s(b.get("status")), _s(b.get("rev")), _s(b.get("file_id")), _s(b.get("note")), "Owner", bool(b.get("revise")))

    @r.post("/projects/{ref}/transmittals")
    async def transmittal(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.transmittal_request, tenant, ref, _s(b.get("to_kind") or "client"), _s(b.get("to_name")), b.get("sheets") or [],
                         _s(b.get("purpose") or "for_approval"), _s(b.get("to_contact")), _s(b.get("note")), int(b.get("copies") or 1))

    @r.post("/transmittals/{tid}/decide")
    async def decide_transmittal(tid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        if "yes" not in b:
            raise HTTPException(400, "yes = true | false")
        return await run(S.decide_transmittal, tenant, tid, bool(b["yes"]), _s(b.get("hash")), _s(b.get("reason")), by_tap=True)

    @r.post("/projects/{ref}/rera_certificate")
    async def rera(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.rera_certificate, tenant, ref, _s(b.get("building")), b.get("pct_done"), _s(b.get("as_on")), b.get("stages") or {})

    # ---- consultants, RFIs, meetings
    @r.get("/consultants")
    async def list_consultants(tenant: str = Depends(current_tenant)):
        return {"consultants": await run(S.consultants, tenant)}

    @r.post("/consultants")
    async def consultant(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.consultant, tenant, _s(b.get("name")), _s(b.get("kind") or "structural"), _s(b.get("phone")), _s(b.get("email")),
                         _s(b.get("firm")), _s(b.get("licence")))

    @r.get("/rfis")
    async def list_rfis(project: str = "", status: str = "", tenant: str = Depends(current_tenant)):
        return {"rfis": await run(S.rfis, tenant, project, status)}

    @r.post("/projects/{ref}/rfis")
    async def rfi(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.rfi, tenant, ref, _s(b.get("subject")), _s(b.get("question")), _s(b.get("party")), b.get("sheets") or [],
                         _s(b.get("due")), _s(b.get("direction") or "out"))

    @r.post("/rfis/{rid}/answer")
    async def rfi_answer(rid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.rfi_answer, tenant, rid, _s(b.get("answer")), bool(b.get("close")))

    @r.post("/projects/{ref}/meetings")
    async def meeting(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.meeting, tenant, ref, b.get("points") or [], b.get("attendees") or [], _s(b.get("on")), _s(b.get("place")))

    @r.post("/meetings/{mid}/done")
    async def point_done(mid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.point_done, tenant, mid, int(_b(body).get("n") or 0))

    # ---- fees + invoices
    @r.post("/projects/{ref}/fee")
    async def fee(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.fee_set, tenant, ref, _s(b.get("basis")), b.get("percent"), b.get("project_cost"), b.get("lump"), b.get("stages"))

    @r.get("/invoices")
    async def list_invoices(project: str = "", status: str = "", tenant: str = Depends(current_tenant)):
        return {"invoices": await run(S.invoices, tenant, project, status)}

    @r.post("/projects/{ref}/invoices")
    async def invoice(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.invoice_request, tenant, ref, _s(b.get("stage")), b.get("amount"), _s(b.get("label")))

    @r.post("/invoices/{iid}/challenge")
    async def invoice_challenge(iid: str, tenant: str = Depends(current_tenant)):
        return await run(S.invoice_challenge, tenant, iid)

    @r.post("/invoices/{iid}/decide")
    async def decide_invoice(iid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        if "yes" not in b:
            raise HTTPException(400, "yes = true | false")
        proof = b.get("proof") if isinstance(b.get("proof"), dict) else None
        return await run(S.decide_invoice, tenant, iid, bool(b["yes"]), _s(b.get("hash")), _s(b.get("reason")), proof, by_tap=True)

    @r.post("/invoices/{iid}/paid")
    async def invoice_paid(iid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.invoice_paid, tenant, iid, b.get("amount"), b.get("tds"), _s(b.get("on")), _s(b.get("ref")))

    return r
