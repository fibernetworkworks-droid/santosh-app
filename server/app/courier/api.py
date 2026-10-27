"""HTTP routes for Courier Sahayak (Profile > Courier sahayak). All under /api/courier, all need the key.

POST /api/courier/cards/{id}/decide is the ONLY way a booking / return label / NDR action / cancel goes to a carrier: her tap
sends the hash of the card she saw (and, once a phone key is active, the fingerprint proof for approvekey kind "courier" on
cards that may charge her wallet). The agent tools can only make cards."""
from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field


class SettingsBody(BaseModel):
    business: str | None = None
    gstin: str | None = None
    warehouse: dict | None = None
    default_carrier: str | None = None
    divisor: float | None = None
    remit_days: int | None = None
    manifest_time: str | None = None
    morning_time: str | None = None


class RulesBody(BaseModel):
    text: str = ""
    rules: dict | None = None


class KeyBody(BaseModel):
    creds: dict = Field(default_factory=dict)


class ParcelBody(BaseModel):
    order_ref: str = ""
    customer: dict = Field(default_factory=dict)
    items: list | str = Field(default_factory=list)
    value: float | None = None
    payment: str = "prepaid"
    cod_amount: float | None = None
    weight_kg: float | None = None
    dims: dict = Field(default_factory=dict)
    eway_no: str = ""
    note: str = ""
    conversation_id: str = ""


class UpdateBody(BaseModel):
    order_ref: str | None = None
    customer: dict | None = None
    items: list | str | None = None
    value: float | None = None
    payment: str | None = None
    cod_amount: float | None = None
    weight_kg: float | None = None
    dims: dict | None = None
    eway_no: str | None = None
    note: str | None = None


class BookBody(BaseModel):
    courier: str = ""
    provider: str = ""


class AwbBody(BaseModel):
    awb: str
    carrier: str = ""


class NdrBody(BaseModel):
    action: str = "reattempt"
    phone: str = ""
    address: str = ""
    when: str = ""
    note: str = ""


class ReturnBody(BaseModel):
    wapsi_ref: str = ""
    ref: str = ""
    customer: dict = Field(default_factory=dict)
    items: list | str = Field(default_factory=list)
    weight_kg: float | None = None
    dims: dict = Field(default_factory=dict)
    reason: str = ""


class DecideBody(BaseModel):
    yes: bool
    hash: str = ""
    reason: str = ""
    proof: dict | None = None


def _fingerprint(tenant: str, card_id: str, proof: dict | None) -> None:
    """A card that may charge her courier wallet needs her phone's fingerprint once a phone key is active (428 = ask the phone)."""
    from .. import approvekey as ak
    try:
        if ak.active_on(tenant):
            ak.verify(tenant, "courier", card_id, proof)
    except ak.ApproveError as e:
        code = str(e)
        if code in ("fingerprint_needed", "fingerprint_invalid"):
            raise HTTPException(428, code)
        raise HTTPException(400, code)


def make_router(require_key, current_tenant) -> APIRouter:
    from . import carriers as K
    from . import service as S
    r = APIRouter(prefix="/api/courier", dependencies=[Depends(require_key)])

    async def run(fn, *a, **kw):
        try:
            return await asyncio.to_thread(fn, *a, **kw)
        except (S.CourierError, K.CarrierError) as e:
            raise HTTPException(400, str(e))

    @r.get("")
    async def courier_home(tenant: str = Depends(current_tenant)):
        return await run(S.home, tenant)

    @r.get("/settings")
    async def courier_settings(tenant: str = Depends(current_tenant)):
        return await run(S.settings, tenant)

    @r.put("/settings")
    async def courier_settings_put(body: SettingsBody, tenant: str = Depends(current_tenant)):
        return await run(S.save_settings, tenant, **body.model_dump(exclude_none=True))

    @r.post("/rules")
    async def courier_rules(body: RulesBody, tenant: str = Depends(current_tenant)):
        return await run(S.set_rules, tenant, body.text, body.rules)

    @r.put("/keys/{provider}")
    async def courier_keys(provider: str, body: KeyBody, tenant: str = Depends(current_tenant)):
        return await run(S.set_keys, tenant, provider, body.creds)

    @r.delete("/keys/{provider}")
    async def courier_keys_off(provider: str, tenant: str = Depends(current_tenant)):
        return await run(S.forget_keys, tenant, provider)

    @r.get("/parcels")
    async def courier_parcels(status: str = "", q: str = "", tenant: str = Depends(current_tenant)):
        return {"parcels": await run(S.parcels, tenant, status, q)}

    @r.post("/parcels")
    async def courier_new(body: ParcelBody, tenant: str = Depends(current_tenant)):
        d = body.model_dump()
        conv = d.pop("conversation_id", "")
        return await run(S.new_parcel, tenant, conv=conv, **d)

    @r.get("/parcels/{ref}")
    async def courier_one(ref: str, tenant: str = Depends(current_tenant)):
        return await run(S.parcel_view, tenant, ref)

    @r.patch("/parcels/{ref}")
    async def courier_update(ref: str, body: UpdateBody, tenant: str = Depends(current_tenant)):
        return await run(S.update_parcel, tenant, ref, **body.model_dump(exclude_none=True))

    @r.post("/parcels/{ref}/check")
    async def courier_check(ref: str, tenant: str = Depends(current_tenant)):
        return await run(S.check, tenant, ref)

    @r.post("/parcels/{ref}/book")
    async def courier_book(ref: str, body: BookBody, tenant: str = Depends(current_tenant)):
        return await run(S.book_request, tenant, ref, body.courier, body.provider)

    @r.post("/parcels/{ref}/awb")
    async def courier_awb(ref: str, body: AwbBody, tenant: str = Depends(current_tenant)):
        return await run(S.set_awb, tenant, ref, body.awb, body.carrier)

    @r.post("/parcels/{ref}/track")
    async def courier_track(ref: str, tenant: str = Depends(current_tenant)):
        return await run(S.track, tenant, ref)

    @r.get("/parcels/{ref}/message")
    async def courier_message(ref: str, kind: str = "shipped", tenant: str = Depends(current_tenant)):
        return await run(S.message, tenant, ref, kind)

    @r.post("/parcels/{ref}/ndr")
    async def courier_ndr(ref: str, body: NdrBody, tenant: str = Depends(current_tenant)):
        return await run(S.ndr_request, tenant, ref, body.action, body.phone, body.address, body.when, body.note)

    @r.post("/parcels/{ref}/cancel")
    async def courier_cancel(ref: str, tenant: str = Depends(current_tenant)):
        return await run(S.cancel_request, tenant, ref)

    @r.post("/parcels/{ref}/forget")
    async def courier_forget(ref: str, tenant: str = Depends(current_tenant)):
        return await run(S.forget, tenant, ref)

    @r.get("/parcels/{ref}/label")
    async def courier_label(ref: str, tenant: str = Depends(current_tenant)):
        v = await run(S.parcel_view, tenant, ref)
        path = (v.get("label") or {}).get("path", "")
        from pathlib import Path
        p = Path(path) if path else None
        if not p or not p.is_file() or p.parent.resolve() != S._dir(tenant).resolve():
            raise HTTPException(404, "Label abhi nahi hai.")
        return FileResponse(str(p), media_type="application/pdf", filename=f"Label-{v['number']}.pdf")

    @r.post("/returns")
    async def courier_return(body: ReturnBody, tenant: str = Depends(current_tenant)):
        return await run(S.return_request, tenant, body.wapsi_ref, body.ref, body.customer, body.items, body.weight_kg, body.dims, body.reason)

    @r.get("/cards")
    async def courier_cards(status: str = "waiting", tenant: str = Depends(current_tenant)):
        return {"cards": await run(S.cards, tenant, status)}

    @r.post("/cards/{card_id}/decide")
    async def courier_decide(card_id: str, body: DecideBody, tenant: str = Depends(current_tenant)):
        if body.yes:
            cards = await run(S.cards, tenant, "waiting")
            c = next((x for x in cards if x["id"] == card_id), None)
            if c and c["money"]:
                await asyncio.to_thread(_fingerprint, tenant, card_id, body.proof)
        return await run(S.decide, tenant, card_id, body.yes, body.hash, True, body.reason)

    @r.get("/where")
    async def courier_where(q: str = "", tenant: str = Depends(current_tenant)):
        return await run(S.where, tenant, q)

    @r.post("/remit")
    async def courier_remit(file: UploadFile = File(...), tenant: str = Depends(current_tenant)):
        data = await file.read()
        if len(data) > 15 * 1024 * 1024:
            raise HTTPException(413, "Sheet 15 MB se badi.")
        return await run(S.remit_import, tenant, data, file.filename or "remittance.csv")

    @r.get("/cod")
    async def courier_cod(tenant: str = Depends(current_tenant)):
        return await run(S.cod_report, tenant)

    @r.get("/manifest")
    async def courier_manifest(on: str = "", tenant: str = Depends(current_tenant)):
        return await run(S.manifest, tenant, on)

    @r.post("/manifest/file")
    async def courier_manifest_file(on: str = "", tenant: str = Depends(current_tenant)):
        return await run(S.manifest_file, tenant, on)

    return r
