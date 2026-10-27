"""HTTP routes of the PI Desk Sahayak (/api/pidesk/*). main.py: app.include_router(make_router(require_key, current_tenant)).

HER tap lives ONLY here (by_tap=True): POST /shares/{id}/decide (a report / evidence pack / complaint draft going to anyone).
Refusals (tracking / locating / profiling a person, CDR / bank records, pretexting...) come back as HTTP 403 with the reason."""
from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException


def make_router(require_key, current_tenant) -> APIRouter:
    from . import rules as R
    from . import service as S

    r = APIRouter(prefix="/api/pidesk", dependencies=[Depends(require_key)])

    async def run(fn, *a, **k):
        try:
            return await asyncio.to_thread(fn, *a, **k)
        except S.PiRefused as e:
            raise HTTPException(403, str(e))
        except S.PiError as e:
            raise HTTPException(400, str(e))
        except ValueError as e:
            raise HTTPException(400, str(e))

    def _b(body) -> dict[str, Any]:
        return dict(body or {})

    def _s(v) -> str:
        return "" if v is None else str(v)

    @r.get("")
    async def overview(tenant: str = Depends(current_tenant)):
        def go():
            return {"settings": S.settings(tenant), "cases": S.cases(tenant), "day": S.day(tenant), "kinds": S.KINDS,
                    "business_kinds": S.BUSINESS_KINDS, "never": R.NEVER, "checks": R.EMPLOY_CHECKS, "disclaimer": R.DISCLAIMER}
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
        return {"never": R.NEVER, "disclaimer": R.DISCLAIMER, "sources": R.SOURCES, "complaints": R.COMPLAINT_TO, "checks": R.EMPLOY_CHECKS}

    @r.post("/check")
    async def check(body: dict = Body(default={})):
        b = _b(body)
        return R.check_identifier(_s(b.get("kind")), _s(b.get("value")))

    # ---- cases
    @r.get("/cases")
    async def list_cases(status: str = "", tenant: str = Depends(current_tenant)):
        return {"cases": await run(S.cases, tenant, status)}

    @r.post("/cases")
    async def new_case(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.new_case, tenant, _s(b.get("kind") or "due_diligence"), _s(b.get("title")), _s(b.get("purpose")),
                         _s(b.get("subject_name")), _s(b.get("subject_kind")), b.get("identifiers") or [], _s(b.get("website")),
                         _s(b.get("role")))

    @r.get("/cases/{ref}")
    async def get_case(ref: str, tenant: str = Depends(current_tenant)):
        return await run(S.case_view, tenant, ref)

    @r.post("/cases/{ref}/ids")
    async def ids(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.check_ids, tenant, ref, _b(body).get("identifiers") or [])

    @r.post("/cases/{ref}/page")
    async def page(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.read_page, tenant, ref, _s(_b(body).get("url")))

    @r.post("/cases/{ref}/paste")
    async def paste(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.paste, tenant, ref, _s(b.get("text")), _s(b.get("source_url")), _s(b.get("where")))

    @r.post("/cases/{ref}/news")
    async def news(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.news, tenant, ref, _s(_b(body).get("query")))

    @r.post("/cases/{ref}/note")
    async def note(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.note, tenant, ref, _s(b.get("fact")), _s(b.get("source_url")), _s(b.get("section") or "note"))

    @r.post("/cases/{ref}/evidence")
    async def evidence(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.add_evidence, tenant, ref, _s(b.get("file_id")), _s(b.get("kind") or "other"), _s(b.get("note")),
                         _s(b.get("happened_at")))

    @r.post("/cases/{ref}/doc_check")
    async def doc_check(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.doc_check, tenant, ref, _s(b.get("file_id")), _s(b.get("claimed_date")), b.get("expect") or {},
                         _s(b.get("note")), "", "owner", _s(b.get("evidence_id")))

    @r.post("/cases/{ref}/event")
    async def event(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.add_event, tenant, ref, _s(b.get("at")), _s(b.get("what")), b.get("amount"), _s(b.get("ref")))

    @r.get("/cases/{ref}/timeline")
    async def timeline(ref: str, all: bool = False, tenant: str = Depends(current_tenant)):
        return await run(S.timeline, tenant, ref, not all)

    @r.post("/cases/{ref}/money")
    async def money(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.set_money, tenant, ref, b.get("lost"), _s(b.get("mode")), b.get("refs") or [], _s(b.get("suspect")))

    @r.post("/cases/{ref}/reported")
    async def reported(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.mark_reported, tenant, ref, _s(b.get("where")), _s(b.get("ref")), _s(b.get("on")))

    @r.post("/cases/{ref}/complaint")
    async def complaint(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.complaint, tenant, ref, _s(_b(body).get("to") or "cyber"))

    @r.post("/cases/{ref}/pack")
    async def pack(ref: str, tenant: str = Depends(current_tenant)):
        return await run(S.pack, tenant, ref)

    @r.post("/cases/{ref}/report")
    async def report(ref: str, tenant: str = Depends(current_tenant)):
        return await run(S.report, tenant, ref)

    @r.get("/cases/{ref}/custody")
    async def custody(ref: str, tenant: str = Depends(current_tenant)):
        return {"custody": await run(S.custody, tenant, ref), "check": await run(S.verify_chain, tenant, ref)}

    @r.get("/cases/{ref}/consent_text")
    async def consent_text(ref: str, tenant: str = Depends(current_tenant)):
        return await run(S.consent_text, tenant, ref)

    @r.post("/cases/{ref}/consent")
    async def consent(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.consent, tenant, ref, _s(b.get("file_id")), _s(b.get("signed_on")), b.get("checks") or [], int(b.get("days") or 180))

    @r.post("/cases/{ref}/reference")
    async def reference(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.reference_request, tenant, ref, _s(b.get("about")), _s(b.get("to_name")), _s(b.get("to_contact")))

    @r.post("/cases/{ref}/close")
    async def close(ref: str, tenant: str = Depends(current_tenant)):
        return await run(S.close, tenant, ref)

    @r.post("/cases/{ref}/forget")
    async def forget(ref: str, tenant: str = Depends(current_tenant)):
        return await run(S.forget, tenant, ref)

    # ---- sharing: card -> her tap
    @r.post("/cases/{ref}/share")
    async def share(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.share_request, tenant, ref, _s(b.get("what") or "report"), _s(b.get("to_name")), _s(b.get("to_contact")),
                         _s(b.get("note")))

    @r.get("/shares")
    async def list_shares(status: str = "", tenant: str = Depends(current_tenant)):
        return {"shares": await run(S.shares, tenant, status)}

    @r.post("/shares/{sid}/decide")
    async def decide_share(sid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        if "yes" not in b:
            raise HTTPException(400, "yes = true | false")
        return await run(S.decide_share, tenant, sid, bool(b["yes"]), _s(b.get("hash")), by_tap=True)

    return r
