"""HTTP routes of the DPO Sahayak (/api/dpo/*). main.py: app.include_router(make_router(require_key, current_tenant)).

Publishing a privacy notice, replying to a person, erasing data and every breach notice are decided ONLY here:
POST /api/dpo/cards/{id}/decide {yes, hash, reason, proof} from her app (her tap, the card's hash; an erasure also needs her
phone's fingerprint once a phone key is set up: 428 -> POST /api/dpo/cards/{id}/challenge, sign, resend with `proof`)."""
from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException


def make_router(require_key, current_tenant) -> APIRouter:
    from . import service as S

    r = APIRouter(prefix="/api/dpo", dependencies=[Depends(require_key)])

    async def run(fn, *a, **k):
        try:
            return await asyncio.to_thread(fn, *a, **k)
        except S.DpoError as e:
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

    @r.get("/law")
    async def law():
        return S.law()

    @r.get("/settings")
    async def get_settings(tenant: str = Depends(current_tenant)):
        return await run(S.settings, tenant)

    @r.put("/settings")
    async def put_settings(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.save_settings, tenant, "owner", **{k: b[k] for k in S._SET_KEYS if k in b})

    # ---- records of processing
    @r.post("/scan")
    async def scan(tenant: str = Depends(current_tenant)):
        return await run(S.scan, tenant)

    @r.get("/activities")
    async def acts(tenant: str = Depends(current_tenant)):
        return {"activities": await run(S.activities, tenant)}

    @r.post("/activities")
    async def add_act(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.activity_save, tenant, "", "owner", **{k: b[k] for k in S._ACT_KEYS if k in b})

    @r.patch("/activities/{aid}")
    async def edit_act(aid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.activity_save, tenant, aid, "owner", **{k: b[k] for k in S._ACT_KEYS if k in b})

    @r.post("/activities/{aid}/dpia")
    async def dpia(aid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.dpia, tenant, aid, _b(body).get("answers") or {})

    @r.get("/retention")
    async def retention(tenant: str = Depends(current_tenant)):
        return {"retention": await run(S.retention, tenant)}

    @r.post("/register")
    async def register(tenant: str = Depends(current_tenant)):
        return await run(S.register_file, tenant)

    # ---- notices
    @r.get("/notices")
    async def list_notices(tenant: str = Depends(current_tenant)):
        return {"notices": await run(S.notices, tenant)}

    @r.post("/notices")
    async def new_notice(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.notice_draft, tenant, _s(b.get("lang") or "hi"), b.get("activities"))

    @r.patch("/notices/{nid}")
    async def edit_notice(nid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.notice_edit, tenant, nid, _s(_b(body).get("text")))

    @r.post("/notices/{nid}/publish")
    async def publish(nid: str, tenant: str = Depends(current_tenant)):
        return await run(S.notice_request, tenant, nid)

    # ---- consents
    @r.get("/consents")
    async def list_consents(q: str = "", tenant: str = Depends(current_tenant)):
        return {"consents": await run(S.consents, tenant, q)}

    @r.post("/consents")
    async def add_consent(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.consent_add, tenant, _s(b.get("name")), _s(b.get("phone")), b.get("activities"), _s(b.get("how")),
                         _s(b.get("proof")), bool(b.get("child")), _s(b.get("parent_name")), _s(b.get("parent_check")),
                         b.get("notice_version"))

    @r.post("/consents/withdraw")
    async def withdraw(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.consent_withdraw, tenant, _s(b.get("consent")), _s(b.get("phone")), _s(b.get("how")))

    # ---- rights requests
    @r.get("/requests")
    async def list_requests(status: str = "", tenant: str = Depends(current_tenant)):
        return {"requests": await run(S.requests, tenant, status)}

    @r.post("/requests")
    async def new_request(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.request_new, tenant, _s(b.get("text")), _s(b.get("name")), _s(b.get("phone")), _s(b.get("email")),
                         _s(b.get("via")), _s(b.get("kind")), _s(b.get("received")))

    @r.get("/requests/{rid}")
    async def get_request(rid: str, tenant: str = Depends(current_tenant)):
        return await run(S.request_view, tenant, rid)

    @r.post("/requests/{rid}/verify")
    async def verify(rid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.request_verify, tenant, rid, bool(b.get("ok", True)), _s(b.get("how")))

    @r.post("/requests/{rid}/reply")
    async def reply(rid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.request_reply, tenant, rid, _s(_b(body).get("body")))

    @r.post("/requests/{rid}/erase")
    async def erase(rid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.erase_request, tenant, rid, _b(body).get("modules"))

    @r.post("/requests/{rid}/sent")
    async def sent(rid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.request_sent, tenant, rid, _s(_b(body).get("how")))

    @r.post("/requests/{rid}/close")
    async def close(rid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.request_close, tenant, rid, _s(b.get("status") or "closed"), _s(b.get("note")))

    @r.get("/find")
    async def find(phone: str = "", tenant: str = Depends(current_tenant)):
        return {"found": await run(S.find, tenant, phone)}

    # ---- breaches
    @r.get("/breaches")
    async def list_breaches(status: str = "", tenant: str = Depends(current_tenant)):
        return {"breaches": await run(S.breaches, tenant, status)}

    @r.post("/breaches")
    async def new_breach(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        facts = {k: b[k] for k in S.R.BREACH_FIELDS if k in b}
        return await run(S.breach_new, tenant, _s(b.get("title")), _s(b.get("aware")), bool(b.get("cert_in", True)),
                         b.get("activities"), b.get("affected"), **facts)

    @r.get("/breaches/{bid}")
    async def get_breach(bid: str, tenant: str = Depends(current_tenant)):
        return await run(S.breach_view, tenant, bid)

    @r.patch("/breaches/{bid}")
    async def upd_breach(bid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        facts = {k: b[k] for k in S.R.BREACH_FIELDS if k in b}
        return await run(S.breach_update, tenant, bid, b.get("affected"), **facts)

    @r.post("/breaches/{bid}/send")
    async def send_breach(bid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.breach_send, tenant, bid, _s(_b(body).get("which") or "initial"))

    @r.post("/breaches/{bid}/sent")
    async def breach_sent(bid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.breach_sent, tenant, bid, _s(b.get("which") or "initial"), _s(b.get("ref")))

    @r.post("/breaches/{bid}/close")
    async def close_breach(bid: str, tenant: str = Depends(current_tenant)):
        return await run(S.breach_close, tenant, bid)

    # ---- vendors
    @r.get("/vendors")
    async def list_vendors(tenant: str = Depends(current_tenant)):
        return {"vendors": await run(S.vendors, tenant), "clauses": [{"key": k, "text": t} for k, t in S.R.DPA_CLAUSES]}

    @r.post("/vendors")
    async def save_vendor(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        ref = _s(b.pop("vendor", ""))
        return await run(S.vendor_save, tenant, ref, "owner", **b)

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
                         by_tap=True)

    return r
