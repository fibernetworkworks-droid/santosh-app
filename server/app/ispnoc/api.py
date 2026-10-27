"""HTTP routes of the NOC Sahayak (/api/ispnoc/*). main.py: app.include_router(make_router(require_key, current_tenant)).

Key-protected: everything for her app. The ONLY way a change on live equipment is approved:
POST /api/ispnoc/changes/{id}/decide {yes, hash} (her tap).
Public but signed: /api/ispnoc/collector/{push|jobs|jobs/{id}/result} - HMAC-SHA256 with the collector's own secret
(headers X-Hoola-Collector, X-Hoola-Ts, X-Hoola-Nonce, X-Hoola-Sig over method, path, time, nonce, sha256(body)); ±5 min, no replays.
"""
from __future__ import annotations

import asyncio
import base64
import json
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Request
from fastapi.responses import PlainTextResponse


def make_router(require_key, current_tenant) -> APIRouter:
    from . import service as S

    outer = APIRouter()
    r = APIRouter(prefix="/api/ispnoc", dependencies=[Depends(require_key)])
    pub = APIRouter(prefix="/api/ispnoc/collector")

    async def run(fn, *a, **k):
        try:
            return await asyncio.to_thread(fn, *a, **k)
        except (S.NocError, ValueError) as e:
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
        keys = ("isp_name", "model", "upstream", "optics", "teams", "sla", "bsnl_sla_hours", "bsnl_penalty_note", "window_min",
                "morning_time", "rules")
        await run(S._no_secret_keys, {k: v for k, v in b.items() if k != "teams"})
        return await run(S.save_settings, tenant, **{k: b[k] for k in keys if k in b})

    # ---- network inventory
    @r.get("/network")
    async def network(tenant: str = Depends(current_tenant)):
        return await run(S.network, tenant)

    @r.post("/sites")
    async def site(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.save_site, tenant, str(b.pop("name", "") or ""), str(b.pop("site", "") or ""), **b)

    @r.post("/olts")
    async def olt(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.save_olt, tenant, str(b.pop("name", "") or ""), str(b.pop("olt", "") or ""), **b)

    @r.post("/onts")
    async def ont(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.save_ont, tenant, str(b.pop("ont", "") or ""), **b)

    @r.get("/onts")
    async def onts(q: str = "", olt: str = "", pon: str = "", tenant: str = Depends(current_tenant)):
        return {"onts": await run(S.find_onts, tenant, q, olt, pon)}

    @r.post("/splitters")
    async def splitter(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.save_splitter, tenant, str(b.pop("name", "") or ""), **b)

    @r.delete("/{what}/{ref}")
    async def remove(what: str, ref: str, tenant: str = Depends(current_tenant)):
        w = {"sites": "site", "olts": "olt", "onts": "ont", "splitters": "splitter"}.get(what)
        if not w:
            raise HTTPException(404, "not found")
        return await run(S.remove, tenant, w, ref)

    @r.post("/import")
    async def import_inv(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        if b.get("file_id"):
            return await run(S.import_inventory, tenant, None, kind=str(b.get("kind") or "auto"), file_id=str(b["file_id"]))
        try:
            data = base64.b64decode(str(b.get("data_b64") or ""), validate=False)
        except (ValueError, TypeError):
            raise HTTPException(400, "File padh nahi paaye.")
        return await run(S.import_inventory, tenant, data, str(b.get("name") or "network.csv"), str(b.get("kind") or "auto"))

    # ---- alarms + faults
    @r.post("/alarms")
    async def alarms(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        text = str(b.get("text") or "")
        if not text and b.get("data_b64"):
            try:
                text = base64.b64decode(str(b["data_b64"])).decode("utf-8", errors="replace")
            except (ValueError, TypeError):
                raise HTTPException(400, "File padh nahi paaye.")
        return await run(S.ingest, tenant, text, str(b.get("olt") or ""), str(b.get("source") or "paste"))

    @r.post("/analyse")
    async def analyse(tenant: str = Depends(current_tenant)):
        return await run(S.analyse, tenant)

    @r.get("/faults")
    async def faults(status: str = "open", limit: int = 40, tenant: str = Depends(current_tenant)):
        return {"faults": await run(S.faults, tenant, status, limit)}

    @r.get("/faults/{fid}")
    async def fault(fid: str, tenant: str = Depends(current_tenant)):
        return await run(S.fault_view, tenant, fid, True)

    @r.post("/faults/{fid}/ticket")
    async def ticket(fid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.open_ticket, tenant, fid, str(b.get("team") or ""), str(b.get("assignee") or ""), str(b.get("phone") or ""),
                         str(b.get("eta") or ""), str(b.get("note") or ""), str(b.get("ext_ref") or ""))

    @r.get("/faults/{fid}/message")
    async def message(fid: str, restored: bool = False, tenant: str = Depends(current_tenant)):
        return await run(S.customer_message, tenant, fid, restored)

    @r.post("/faults/{fid}/resolve")
    async def resolve(fid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.resolve, tenant, fid, str(_b(body).get("note") or ""))

    @r.post("/faults/{fid}/dismiss")
    async def dismiss(fid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.dismiss, tenant, fid, str(_b(body).get("reason") or ""))

    @r.post("/faults/{fid}/note")
    async def note(fid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.fault_note, tenant, fid, str(_b(body).get("text") or ""))

    # ---- tickets
    @r.get("/tickets")
    async def tickets(status: str = "open", tenant: str = Depends(current_tenant)):
        return {"tickets": await run(S.tickets, tenant, status)}

    @r.patch("/tickets/{tid}")
    async def patch_ticket(tid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.update_ticket, tenant, tid, str(b.get("status") or ""), str(b.get("eta") or ""), str(b.get("note") or ""),
                         str(b.get("assignee") or ""), str(b.get("phone") or ""), str(b.get("ext_ref") or ""))

    # ---- changes on live equipment
    @r.get("/changes")
    async def list_changes(status: str = "", tenant: str = Depends(current_tenant)):
        return {"changes": await run(S.changes, tenant, status)}

    @r.post("/changes")
    async def new_change(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.request_change, tenant, str(b.get("action") or ""), str(b.get("olt") or ""), str(b.get("pon") or ""),
                         str(b.get("onu") or ""), str(b.get("port") or ""), b.get("commands") or None, b.get("rollback") or None,
                         str(b.get("reason") or ""), str(b.get("fault") or ""))

    @r.put("/changes/{cid}")
    async def edit_change(cid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        if not isinstance(b.get("commands"), list):
            raise HTTPException(400, "commands = list of lines")
        return await run(S.edit_change, tenant, cid, b["commands"], b.get("rollback") if isinstance(b.get("rollback"), list) else None)

    @r.post("/changes/{cid}/decide")
    async def decide(cid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        if "yes" not in b or not b.get("hash"):
            raise HTTPException(400, "yes + hash chahiye (card se)")
        return await run(S.decide_change, tenant, cid, bool(b["yes"]), str(b["hash"]), str(b.get("reason") or ""), by_tap=True)

    @r.post("/changes/{cid}/done")
    async def change_done(cid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.change_done, tenant, cid, bool(b.get("ok", True)), str(b.get("output") or ""))

    @r.post("/changes/{cid}/cancel")
    async def cancel_change(cid: str, tenant: str = Depends(current_tenant)):
        return await run(S.cancel_change, tenant, cid)

    @r.post("/optics")
    async def optics(body: dict = Body(default={})):
        b = _b(body)
        try:
            splits = [int(x) for x in (b.get("splits") or [])]
        except (TypeError, ValueError):
            raise HTTPException(400, "splits = [8, 4] jaisa")
        return await run(S.optics_check, str(b.get("class") or ""), float(b.get("km") or 0), splits, int(b.get("connectors") or 4),
                         int(b.get("splices") or 4), S._num(b.get("rx")))

    @r.get("/report")
    async def report(days: int = 30, tenant: str = Depends(current_tenant)):
        return await run(S.report, tenant, days)

    # ---- collectors (her app)
    @r.get("/collectors")
    async def list_collectors(tenant: str = Depends(current_tenant)):
        return {"collectors": await run(S.collectors, tenant)}

    @r.post("/collectors")
    async def new_collector(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.create_collector, tenant, str(b.get("name") or ""), str(b.get("site") or ""), bool(b.get("changes_ok")))

    @r.patch("/collectors/{cid}")
    async def patch_collector(cid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.update_collector, tenant, cid, b.get("changes_ok") if "changes_ok" in b else None,
                         b.get("olts") if isinstance(b.get("olts"), list) else None, b.get("active") if "active" in b else None)

    @r.get("/collector-script", response_class=PlainTextResponse)
    async def script():
        return PlainTextResponse(S.collector_script(), media_type="text/x-python")

    # ---- the collector itself (public, HMAC-signed)
    async def _auth(request: Request) -> tuple[Any, bytes]:
        body = await request.body()
        if len(body) > 8_000_000:
            raise HTTPException(413, "too big")
        h = request.headers
        try:
            c = await asyncio.to_thread(S.verify_collector, h.get("x-hoola-collector", ""), request.method, request.url.path,
                                        h.get("x-hoola-ts", ""), h.get("x-hoola-sig", ""), body, h.get("x-hoola-nonce", ""))
        except S.NocError as e:
            raise HTTPException(401, str(e))
        return c, body

    def _json(body: bytes) -> dict:
        try:
            v = json.loads(body or b"{}")
        except ValueError:
            raise HTTPException(400, "bad json")
        if not isinstance(v, dict):
            raise HTTPException(400, "bad json")
        return v

    @pub.post("/push")
    async def c_push(request: Request):
        c, body = await _auth(request)
        return await run(S.collector_push, c, _json(body))

    @pub.get("/jobs")
    async def c_jobs(request: Request):
        c, _ = await _auth(request)
        return await run(S.collector_jobs, c)

    @pub.post("/jobs/{jid}/result")
    async def c_result(jid: str, request: Request):
        c, body = await _auth(request)
        b = _json(body)
        return await run(S.collector_result, c, jid, bool(b.get("ok")), str(b.get("output") or ""))

    outer.include_router(pub)
    outer.include_router(r)
    return outer
