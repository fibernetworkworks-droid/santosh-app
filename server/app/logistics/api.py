"""HTTP routes of the Logistics Sahayak (/api/logistics/*). main.py: app.include_router(make_router(require_key, current_tenant)).

The ONLY ways things leave Hoola: POST /api/logistics/ewb/{id}/decide (her tap: e-way bill filing) and
POST /api/logistics/messages/{id}/send (her tap: business WhatsApp). Keys for her GSP are typed only here (PUT /ewb_keys)."""
from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, Body, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse


def make_router(require_key, current_tenant) -> APIRouter:
    from . import service as S

    r = APIRouter(prefix="/api/logistics", dependencies=[Depends(require_key)])

    async def run(fn, *a, **k):
        try:
            return await asyncio.to_thread(fn, *a, **k)
        except (S.LogiError, ValueError) as e:
            raise HTTPException(400, str(e))

    def _b(body: dict | None) -> dict[str, Any]:
        return dict(body or {})

    @r.get("")
    async def overview(tenant: str = Depends(current_tenant)):
        return await run(S.overview, tenant)

    @r.get("/board")
    async def board(tenant: str = Depends(current_tenant)):
        return await run(S.board, tenant)

    @r.get("/settings")
    async def get_settings(tenant: str = Depends(current_tenant)):
        return await run(S.settings, tenant)

    @r.put("/settings")
    async def put_settings(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.save_settings, tenant, **{k: b[k] for k in S.SETTING_KEYS if k in b})

    @r.put("/ewb_keys")
    async def ewb_keys(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.set_ewb_keys, tenant, str(b.get("provider") or "manual"), b.get("creds") or {})

    @r.get("/parties")
    async def get_parties(kind: str = "", q: str = "", tenant: str = Depends(current_tenant)):
        return {"parties": await run(S.parties, tenant, kind, q)}

    @r.post("/parties")
    async def post_party(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        keys = ("gstin", "address", "place", "pincode", "phone", "kind", "trans_id", "no_messages", "state")
        return await run(S.save_party, tenant, str(b.get("name") or ""), str(b.get("party") or ""), **{k: b[k] for k in keys if k in b})

    @r.get("/shipments")
    async def list_shipments(status: str = "", q: str = "", tenant: str = Depends(current_tenant)):
        return {"shipments": await run(S.shipments, tenant, status, q)}

    @r.post("/shipments")
    async def post_shipment(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        extra = {k: v for k, v in b.items() if k not in ("consignee", "goods", "goods_text", "thok_order")}
        return await run(S.new_shipment, tenant, str(b.get("consignee") or ""), b.get("goods"), str(b.get("goods_text") or ""),
                         str(b.get("thok_order") or ""), "", **extra)

    @r.get("/shipments/{ref}")
    async def get_shipment(ref: str, tenant: str = Depends(current_tenant)):
        return await run(S.get, tenant, ref)

    @r.patch("/shipments/{ref}")
    async def patch_shipment(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.update_shipment, tenant, ref, "", **_b(body))

    @r.post("/shipments/{ref}/update")
    async def post_update(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.update, tenant, ref, str(b.get("status") or ""), str(b.get("text") or ""), str(b.get("where") or ""),
                         str(b.get("eta") or ""), str(b.get("at") or ""), "owner", str(b.get("source") or "her"), "", str(b.get("reason") or ""))

    @r.post("/shipments/{ref}/location")
    async def post_location(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.location, tenant, ref, str(b.get("text") or ""), str(b.get("source") or "driver"))

    @r.post("/shipments/{ref}/track")
    async def post_track(ref: str, tenant: str = Depends(current_tenant)):
        return await run(S.track, tenant, ref)

    @r.post("/shipments/{ref}/draft")
    async def post_draft(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.draft, tenant, ref, str(b.get("kind") or "in_transit"), "", str(b.get("reason") or ""), str(b.get("where") or ""),
                         str(b.get("text") or ""))

    @r.post("/shipments/{ref}/docs")
    async def post_docs(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.documents, tenant, ref, _b(body).get("which") or None)

    @r.get("/shipments/{ref}/ewb")
    async def get_ewb(ref: str, tenant: str = Depends(current_tenant)):
        return await run(S.ewb_ready, tenant, ref)

    @r.post("/shipments/{ref}/ewb")
    async def post_ewb(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.ewb_request, tenant, ref, str(b.get("kind") or "generate"), str(b.get("vehicle_no") or ""), str(b.get("reason") or ""),
                         str(b.get("from_place") or ""), str(b.get("from_state") or ""), str(b.get("from_pincode") or ""), b.get("remaining_km"),
                         b.get("shipments"))

    @r.post("/shipments/{ref}/ewb_number")
    async def post_ewb_number(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.ewb_set, tenant, ref, str(b.get("ewb_no") or ""), str(b.get("valid_upto") or ""), str(b.get("generated") or ""))

    @r.post("/ewb/{ask_id}/decide")
    async def decide_ewb(ask_id: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.decide_ewb, tenant, ask_id, bool(b.get("yes")), str(b.get("hash") or ""), True)

    @r.post("/shipments/{ref}/photo")
    async def post_photo(ref: str, file: UploadFile = File(...), stage: str = Form("pod"), receiver: str = Form(""), remarks: str = Form(""),
                         short: str = Form(""), damaged: str = Form(""), tenant: str = Depends(current_tenant)):
        data = await file.read()
        return await run(S.add_photo, tenant, ref, data, stage, receiver, remarks, short or None, damaged.lower() in ("1", "true", "yes", "haan"))

    @r.get("/photos/{photo_id}")
    async def get_photo(photo_id: str, tenant: str = Depends(current_tenant)):
        p = await run(S.photo_file, tenant, photo_id)
        return FileResponse(str(p), media_type="image/jpeg")

    @r.post("/shipments/{ref}/cancel")
    async def post_cancel(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.cancel, tenant, ref, str(_b(body).get("reason") or ""))

    @r.put("/messages/{msg_id}")
    async def put_message(msg_id: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.edit_message, tenant, msg_id, str(_b(body).get("text") or ""))

    @r.post("/messages/{msg_id}/sent")
    async def post_sent(msg_id: str, tenant: str = Depends(current_tenant)):
        return await run(S.message_sent, tenant, msg_id)

    @r.post("/messages/{msg_id}/send")
    async def post_send(msg_id: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        try:
            return await S.send_business(tenant, msg_id, str(_b(body).get("hash") or ""), by_tap=True)
        except S.LogiError as e:
            raise HTTPException(400, str(e))

    @r.post("/register")
    async def post_register(tenant: str = Depends(current_tenant)):
        return await run(S.register_file, tenant)

    return r
