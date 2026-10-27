"""HTTP routes of the Propagent Sahayak (/api/propagent/*). main.py: app.include_router(make_router(require_key, current_tenant)).

Everything that waits for her is decided ONLY at POST /api/propagent/cards/{id}/decide (her app tap with the card's hash; a paper
that names money needs her phone's fingerprint once a phone key is set up: 428 -> POST /cards/{id}/challenge, sign, resend with
`proof`). The public listing page /api/propagent/page/{token} is the only route without the key: it checks its own random token
and shows only what she approved."""
from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, Body, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse

_CSP = "default-src 'none'; img-src 'self'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'"


def make_router(require_key, current_tenant) -> APIRouter:
    from . import service as S

    r = APIRouter(prefix="/api/propagent")
    p = APIRouter(prefix="/api/propagent", dependencies=[Depends(require_key)])

    async def run(fn, *a, **k):
        try:
            return await asyncio.to_thread(fn, *a, **k)
        except S.PropError as e:
            code = str(e)
            if code in ("fingerprint_needed", "fingerprint_invalid"):
                raise HTTPException(428, code)
            raise HTTPException(400, code)
        except ValueError as e:
            raise HTTPException(400, str(e))

    def _b(body: dict | None) -> dict[str, Any]:
        return dict(body or {})

    # ---- public page (own token check)
    @r.get("/page/{token}", response_class=HTMLResponse)
    async def page(token: str):
        code, text = await asyncio.to_thread(S.page_html, token)
        return HTMLResponse(text, status_code=code, headers={"Content-Security-Policy": _CSP, "X-Robots-Tag": "noindex",
                                                             "Referrer-Policy": "no-referrer", "Cache-Control": "no-store"})

    @r.get("/page/{token}/photo/{n}")
    async def page_photo(token: str, n: int):
        path = await asyncio.to_thread(S.page_photo, token, n)
        if path is None:
            raise HTTPException(404, "nahi mila")
        return FileResponse(path, media_type="image/jpeg", headers={"Cache-Control": "no-store"})

    # ---- all-in-one + settings
    @p.get("")
    async def overview(tenant: str = Depends(current_tenant)):
        return await run(S.overview, tenant)

    @p.get("/day")
    async def day(tenant: str = Depends(current_tenant)):
        return await run(S.day, tenant)

    @p.get("/settings")
    async def get_settings(tenant: str = Depends(current_tenant)):
        return await run(S.settings, tenant)

    @p.put("/settings")
    async def put_settings(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.save_settings, tenant, **{k: b[k] for k in S._SET_KEYS if k in b})

    @p.get("/steps/{what}")
    async def steps(what: str):
        return S.official_steps(what)

    # ---- listings
    @p.get("/listings")
    async def get_listings(status: str = "", purpose: str = "", q: str = "", tenant: str = Depends(current_tenant)):
        return {"listings": await run(S.listings, tenant, status, purpose, q)}

    @p.post("/listings")
    async def new_listing(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.save_listing, tenant, "", str(b.pop("words", "") or ""), **{k: b[k] for k in S._LISTING_KEYS if k in b})

    @p.get("/listings/{lid}")
    async def get_listing(lid: str, tenant: str = Depends(current_tenant)):
        return await run(S.listing_view, tenant, lid)

    @p.patch("/listings/{lid}")
    async def patch_listing(lid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.save_listing, tenant, lid, str(b.pop("words", "") or ""), **{k: b[k] for k in S._LISTING_KEYS if k in b})

    @p.post("/listings/{lid}/photo")
    async def photo(lid: str, file: UploadFile = File(...), kind: str = Form("photo"), note: str = Form(""),
                    tenant: str = Depends(current_tenant)):
        data = await file.read()
        if len(data) > 15 * 1024 * 1024:
            raise HTTPException(413, "Photo 15 MB se badi.")
        return await run(S.add_photo, tenant, lid, data, kind, note)

    @p.get("/photos/{pid}")
    async def photo_get(pid: str, tenant: str = Depends(current_tenant)):
        path = await run(S.photo_path, tenant, pid)
        return FileResponse(path, media_type="image/jpeg")

    @p.post("/listings/{lid}/describe")
    async def describe(lid: str, tenant: str = Depends(current_tenant)):
        return await run(S.describe, tenant, lid)

    @p.post("/listings/{lid}/publish")
    async def publish(lid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.publish_request, tenant, lid, str(_b(body).get("where") or "page"))

    @p.post("/listings/{lid}/unpublish")
    async def unpublish(lid: str, tenant: str = Depends(current_tenant)):
        return await run(S.unpublish, tenant, lid)

    @p.post("/listings/{lid}/poster")
    async def poster(lid: str, tenant: str = Depends(current_tenant)):
        return await run(S.poster, tenant, lid)

    @p.get("/listings/{lid}/buyers")
    async def buyers(lid: str, tenant: str = Depends(current_tenant)):
        return await run(S.buyers_for, tenant, lid)

    @p.post("/listings/{lid}/forget_owner")
    async def forget_owner(lid: str, tenant: str = Depends(current_tenant)):
        return await run(S.forget_owner, tenant, lid)

    @p.post("/sheet")
    async def sheet(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        ids = _b(body).get("listings")
        return await run(S.portal_sheet, tenant, ids if isinstance(ids, list) else None)

    # ---- leads
    @p.get("/leads")
    async def get_leads(stage: str = "", q: str = "", tenant: str = Depends(current_tenant)):
        return {"leads": await run(S.leads, tenant, stage, q)}

    @p.post("/leads")
    async def new_lead(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.save_lead, tenant, "", str(b.get("name") or ""), str(b.get("phone") or ""), str(b.get("role") or ""),
                         str(b.get("words") or ""), str(b.get("source") or ""), b.get("consent"), b.get("need"),
                         str(b.get("next_when") or ""), str(b.get("next_what") or ""), str(b.get("notes") or ""))

    @p.get("/leads/{lid}")
    async def get_lead(lid: str, tenant: str = Depends(current_tenant)):
        out = await run(S.lead_view, tenant, lid)
        out["matches"] = (await run(S.matches, tenant, lid))["matches"]
        return out

    @p.patch("/leads/{lid}")
    async def patch_lead(lid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.save_lead, tenant, lid, str(b.get("name") or ""), str(b.get("phone") or ""), str(b.get("role") or ""),
                         str(b.get("words") or ""), str(b.get("source") or ""), b.get("consent"), b.get("need"),
                         str(b.get("next_when") or ""), str(b.get("next_what") or ""), str(b.get("notes") or ""),
                         str(b.get("stage") or ""), b.get("no_messages"))

    @p.post("/leads/{lid}/share")
    async def share(lid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        ids = b.get("listings")
        return await run(S.share_request, tenant, lid, ids if isinstance(ids, list) else None, str(b.get("text") or ""))

    @p.post("/leads/{lid}/forget")
    async def forget_lead(lid: str, tenant: str = Depends(current_tenant)):
        return await run(S.forget_lead, tenant, lid)

    @p.post("/messages")
    async def message(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.message_request, tenant, str(b.get("to") or "lead"), str(b.get("ref") or ""), str(b.get("text") or ""))

    # ---- visits
    @p.get("/visits")
    async def get_visits(day: str = "", status: str = "", tenant: str = Depends(current_tenant)):
        return {"visits": await run(S.visits, tenant, day, status)}

    @p.post("/visits")
    async def new_visit(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.plan_visit, tenant, str(b.get("lead") or ""), list(b.get("listings") or []), str(b.get("day") or ""),
                         str(b.get("start") or "10:00"))

    @p.post("/visits/{vid}/done")
    async def visit_done(vid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        fb = b.get("feedback")
        return await run(S.visit_done, tenant, vid, fb if isinstance(fb, dict) else None, str(b.get("status") or "done"),
                         str(b.get("notes") or ""))

    # ---- deals + papers + commission
    @p.get("/deals")
    async def get_deals(status: str = "", tenant: str = Depends(current_tenant)):
        return {"deals": await run(S.deals, tenant, status)}

    @p.post("/deals")
    async def new_deal(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        lid, lead = str(b.pop("listing", "") or ""), str(b.pop("lead", "") or "")
        return await run(S.deal_new, tenant, lid, lead, **_deal_kw(b, S))

    @p.get("/deals/{did}")
    async def get_deal(did: str, tenant: str = Depends(current_tenant)):
        return await run(S.deal_view, tenant, did)

    @p.patch("/deals/{did}")
    async def patch_deal(did: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.deal_update, tenant, did, str(b.get("ids_text") or ""), str(b.get("ids_side") or "buyer"),
                         str(b.get("ids_person") or ""), **_deal_kw(b, S))

    @p.post("/deals/{did}/status")
    async def deal_status(did: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.deal_status, tenant, did, str(b.get("status") or ""), "owner", str(b.get("note") or ""))

    @p.post("/deals/{did}/check")
    async def check(did: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.check_item, tenant, did, str(b.get("key") or ""), bool(b.get("done", True)))

    @p.post("/deals/{did}/document")
    async def document(did: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.document_request, tenant, did, str(_b(body).get("kind") or ""))

    @p.post("/deals/{did}/commission")
    async def commission(did: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.commission_received, tenant, did, str(b.get("side") or ""), b.get("amount"), str(b.get("mode") or ""),
                         str(b.get("ref") or ""), str(b.get("day") or ""))

    @p.get("/commission")
    async def commission_report(tenant: str = Depends(current_tenant)):
        return await run(S.commission_report, tenant)

    # ---- cards: HER tap
    @p.get("/cards")
    async def get_cards(status: str = "", kind: str = "", tenant: str = Depends(current_tenant)):
        return {"cards": await run(S.cards, tenant, status, kind)}

    @p.post("/cards/{cid}/challenge")
    async def challenge(cid: str, tenant: str = Depends(current_tenant)):
        return await run(S.card_challenge, tenant, cid)

    @p.post("/cards/{cid}/decide")
    async def decide(cid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        if "yes" not in b:
            raise HTTPException(400, "yes = true | false")
        proof = b.get("proof") if isinstance(b.get("proof"), dict) else None
        return await run(S.decide_card, tenant, cid, bool(b.get("yes")), str(b.get("hash") or ""), str(b.get("reason") or ""), proof,
                         by_tap=True)

    @p.post("/cards/{cid}/sent")
    async def sent(cid: str, tenant: str = Depends(current_tenant)):
        return await run(S.card_sent, tenant, cid)

    @p.post("/register")
    async def register(tenant: str = Depends(current_tenant)):
        return await run(S.register_file, tenant)

    outer = APIRouter()
    outer.include_router(r)
    outer.include_router(p)
    return outer


def _deal_kw(b: dict, S) -> dict:
    out = {k: b[k] for k in S._DEAL_KEYS if k in b}
    for side in ("buyer", "seller"):
        if isinstance(b.get(f"{side}_commission"), dict):
            out[f"{side}_commission"] = b[f"{side}_commission"]
    return out
