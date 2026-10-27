"""HTTP routes of the IT Helpdesk Sahayak (/api/helpdesk/*). main.py: app.include_router(make_router(require_key, current_tenant)).

The ONLY way a system-setting change is approved: POST /api/helpdesk/changes/{id}/decide from her app (her tap)."""
from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException


def make_router(require_key, current_tenant) -> APIRouter:
    from . import service as S

    r = APIRouter(prefix="/api/helpdesk", dependencies=[Depends(require_key)])

    async def run(fn, *a, **k):
        try:
            return await asyncio.to_thread(fn, *a, **k)
        except (S.HelpdeskError, ValueError) as e:
            raise HTTPException(400, str(e))

    def _b(body: dict | None) -> dict[str, Any]:
        return dict(body or {})

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
        keys = ("office_name", "entity", "contact_name", "contact_phone", "contact_email", "it_person", "morning_time", "rules", "sla")
        return await run(S.save_settings, tenant, **{k: b[k] for k in keys if k in b})

    @r.get("/playbooks")
    async def playbooks():
        return {"playbooks": S.playbook_list()}

    @r.get("/playbooks/{cat}")
    async def playbook(cat: str):
        return S.playbook_view(cat)

    # ---- tickets
    @r.get("/tickets")
    async def list_tickets(status: str = "", limit: int = 40, tenant: str = Depends(current_tenant)):
        return {"tickets": await run(S.tickets, tenant, status, limit)}

    @r.post("/tickets")
    async def new_ticket(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.new_ticket, tenant, str(b.get("text") or ""), person=str(b.get("person") or ""), asset=str(b.get("asset") or ""),
                         category=str(b.get("category") or ""), impact=str(b.get("impact") or ""), urgency=str(b.get("urgency") or ""),
                         error=str(b.get("error") or ""), since=str(b.get("since") or ""), location=str(b.get("location") or ""))

    @r.get("/tickets/{tid}")
    async def get_ticket(tid: str, tenant: str = Depends(current_tenant)):
        return await run(S.get_ticket, tenant, tid)

    @r.patch("/tickets/{tid}")
    async def patch_ticket(tid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        keys = ("error", "since", "location", "tried", "note", "person", "asset", "impact", "urgency")
        return await run(S.update_ticket, tenant, tid, **{k: b[k] for k in keys if k in b})

    @r.post("/tickets/{tid}/step")
    async def ticket_step(tid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.step, tenant, tid, str(b.get("result") or "not_fixed"), str(b.get("note") or ""), str(b.get("step_id") or ""))

    @r.post("/tickets/{tid}/escalate")
    async def ticket_escalate(tid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.escalate, tenant, tid, str(_b(body).get("vendor") or ""))

    @r.post("/tickets/{tid}/tech")
    async def ticket_tech(tid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.tech_update, tenant, tid, str(b.get("note") or ""), bool(b.get("fixed", True)), b.get("cost"))

    @r.post("/tickets/{tid}/resolve")
    async def ticket_resolve(tid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.resolve, tenant, tid, str(_b(body).get("note") or ""))

    @r.post("/tickets/{tid}/status")
    async def ticket_status(tid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.set_status, tenant, tid, str(_b(body).get("status") or ""))

    @r.post("/tickets/{tid}/change")
    async def ticket_change(tid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.request_change, tenant, tid, str(b.get("what") or ""), str(b.get("how") or ""), str(b.get("kind") or "setting"),
                         str(b.get("risk") or ""), str(b.get("undo") or ""), bool(b.get("careful")))

    # ---- system-setting changes: HER tap
    @r.get("/changes")
    async def list_changes(status: str = "", tenant: str = Depends(current_tenant)):
        return {"changes": await run(S.changes, tenant, status)}

    @r.post("/changes/{cid}/decide")
    async def decide(cid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        if "yes" not in b:
            raise HTTPException(400, "yes = true | false")
        return await run(S.decide_change, tenant, cid, bool(b.get("yes")), str(b.get("hash") or ""), str(b.get("reason") or ""), by_tap=True)

    @r.post("/changes/{cid}/done")
    async def change_done(cid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.change_done, tenant, cid, bool(b.get("ok", True)), str(b.get("note") or ""))

    # ---- assets / vendors
    @r.get("/assets")
    async def list_assets(kind: str = "", tenant: str = Depends(current_tenant)):
        return {"assets": await run(S.assets, tenant, kind)}

    @r.post("/assets")
    async def add_asset(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        keys = ("kind", "name", "brand", "model", "serial", "user", "location", "os", "bought", "warranty_until", "amc_until", "vendor", "notes")
        return await run(S.save_asset, tenant, "", **{k: b[k] for k in keys if k in b})

    @r.post("/assets/sync_pcs")
    async def sync_pcs(tenant: str = Depends(current_tenant)):
        return await run(S.sync_pcs, tenant)

    @r.get("/assets/{aid}")
    async def get_asset(aid: str, tenant: str = Depends(current_tenant)):
        return await run(S.asset_view, tenant, aid)

    @r.patch("/assets/{aid}")
    async def patch_asset(aid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        keys = ("kind", "name", "brand", "model", "serial", "user", "location", "os", "bought", "warranty_until", "amc_until", "vendor", "notes")
        return await run(S.save_asset, tenant, aid, **{k: b[k] for k in keys if k in b})

    @r.delete("/assets/{aid}")
    async def del_asset(aid: str, tenant: str = Depends(current_tenant)):
        return await run(S.remove_asset, tenant, aid)

    @r.get("/vendors")
    async def list_vendors(tenant: str = Depends(current_tenant)):
        return {"vendors": await run(S.vendors, tenant)}

    @r.post("/vendors")
    async def add_vendor(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        keys = ("kind", "phone", "email", "covers", "amc_until", "sla_hours", "notes")
        return await run(S.save_vendor, tenant, str(b.get("name") or ""), str(b.get("vendor") or ""), **{k: b[k] for k in keys if k in b})

    @r.delete("/vendors/{vid}")
    async def del_vendor(vid: str, tenant: str = Depends(current_tenant)):
        return await run(S.remove_vendor, tenant, vid)

    # ---- security
    @r.post("/phish")
    async def phish(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        did = {k: bool(b.get(k)) for k in ("clicked", "entered_password", "opened_attachment", "money", "gave_otp", "remote_access")}
        return await run(S.report_phish, tenant, str(b.get("text") or ""), str(b.get("sender") or ""), b.get("links") or [],
                         b.get("attachments") or [], str(b.get("kind") or "phishing"), str(b.get("person") or ""), str(b.get("asset") or ""),
                         bool(b.get("personal_data")), **did)

    @r.get("/incidents")
    async def list_incidents(tenant: str = Depends(current_tenant)):
        return {"incidents": await run(S.incidents, tenant)}

    @r.post("/incidents/{iid}/reported")
    async def reported(iid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.cert_in_reported, tenant, iid, str(_b(body).get("ref") or ""))

    @r.get("/known")
    async def known(category: str = "", tenant: str = Depends(current_tenant)):
        return {"known": await run(S.known, tenant, category)}

    @r.post("/register")
    async def register(tenant: str = Depends(current_tenant)):
        return await run(S.register_file, tenant)

    return r
