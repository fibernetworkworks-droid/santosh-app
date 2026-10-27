"""HTTP routes of the Influencer Sahayak (/api/influencer/*). main.py: app.include_router(make_router(require_key, current_tenant)).

HER taps live ONLY here (by_tap=True): POST /cards/{id}/decide {yes, hash, reason, proof} for pitch / contract / content to the
brand / go-live note to the creator / invoice / creator payout / campaign report / message. The payout card needs her fingerprint
once a phone key is active: 428 -> POST /cards/{id}/challenge -> sign -> resend with `proof`. All routes key-protected."""
from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, Body, Depends, File, HTTPException, UploadFile
from fastapi.responses import Response


def make_router(require_key, current_tenant) -> APIRouter:
    from . import service as S

    r = APIRouter(prefix="/api/influencer", dependencies=[Depends(require_key)])

    async def run(fn, *a, **k):
        try:
            return await asyncio.to_thread(fn, *a, **k)
        except S.InfluencerError as e:
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

    def _pdf(data: bytes, name: str) -> Response:
        return Response(data, media_type="application/pdf", headers={"Content-Disposition": f'inline; filename="{name}"'})

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
        return await run(S.save_settings, tenant, **{k: b[k] for k in S._SET_KEYS if k in b})

    # ---- creators + rate card
    @r.get("/creators")
    async def list_creators(status: str = "", tenant: str = Depends(current_tenant)):
        return {"creators": await run(S.creators, tenant, status)}

    @r.post("/creators")
    async def save_creator(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        ref = _s(b.pop("id", "") or b.pop("ref", ""))
        return await run(S.creator_save, tenant, ref, "owner", **b)

    @r.get("/creators/{ref}")
    async def get_creator(ref: str, tenant: str = Depends(current_tenant)):
        return await run(S.creator_view, tenant, ref)

    @r.post("/creators/{ref}/rates")
    async def save_rate(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.rate_save, tenant, ref, _s(b.get("platform")), _s(b.get("fmt")), b.get("price"), b.get("usage_days"),
                         b.get("usage_price"), _s(b.get("notes")))

    @r.get("/creators/{ref}/ratecard")
    async def get_ratecard(ref: str, tenant: str = Depends(current_tenant)):
        return await run(S.rate_card, tenant, ref)

    @r.get("/creators/{ref}/ratecard.pdf")
    async def ratecard_pdf(ref: str, tenant: str = Depends(current_tenant)):
        return _pdf(await run(S.rate_card_pdf, tenant, ref), "ratecard.pdf")

    @r.post("/creators/{ref}/forget")
    async def forget_creator(ref: str, tenant: str = Depends(current_tenant)):
        return await run(S.forget, tenant, ref, "")

    # ---- deals
    @r.get("/deals")
    async def list_deals(stage: str = "", creator: str = "", tenant: str = Depends(current_tenant)):
        return {"deals": await run(S.deals, tenant, stage, creator)}

    @r.post("/deals")
    async def new_deal(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.deal_save, tenant, "", "owner", "", bool(b.get("force")), _s(b.get("reason")),
                         **{k: b[k] for k in S._DEAL_KEYS if k in b})

    @r.get("/deals/{ref}")
    async def get_deal(ref: str, tenant: str = Depends(current_tenant)):
        return await run(S.deal_view, tenant, ref)

    @r.patch("/deals/{ref}")
    async def patch_deal(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.deal_save, tenant, ref, "owner", "", bool(b.get("force")), _s(b.get("reason")),
                         **{k: b[k] for k in S._DEAL_KEYS if k in b})

    @r.get("/deals/{ref}/contract.pdf")
    async def contract_pdf(ref: str, tenant: str = Depends(current_tenant)):
        return _pdf(await run(S.contract_pdf, tenant, ref, False), f"{ref}_contract_draft.pdf")

    @r.get("/deals/{ref}/invoice.pdf")
    async def invoice_pdf(ref: str, tenant: str = Depends(current_tenant)):
        return _pdf(await run(S.invoice_pdf, tenant, ref), f"{ref}_invoice.pdf")

    @r.get("/deals/{ref}/report")
    async def get_report(ref: str, tenant: str = Depends(current_tenant)):
        return await run(S.report, tenant, ref)

    @r.post("/deals/{ref}/metrics")
    async def upload_metrics(ref: str, file: UploadFile = File(...), tenant: str = Depends(current_tenant)):
        data = await file.read()
        if len(data) > 5 * 1024 * 1024:
            raise HTTPException(413, "Sheet 5 MB se badi.")
        return await run(S.import_metrics, tenant, ref, data)

    @r.post("/deals/{ref}/{what}")
    async def deal_action(ref: str, what: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        """Card requests (never decide): pitch | contract | invoice | payout | report | message; owner records: stage | paid |
        payout_sent | forget."""
        b = _b(body)
        if what == "pitch":
            return await run(S.pitch_request, tenant, ref)
        if what == "contract":
            return await run(S.contract_request, tenant, ref)
        if what == "invoice":
            return await run(S.invoice_request, tenant, ref)
        if what == "payout":
            return await run(S.payout_request, tenant, ref)
        if what == "report":
            return await run(S.report_request, tenant, ref, _s(b.get("note")))
        if what == "message":
            return await run(S.message_request, tenant, ref, _s(b.get("text")), _s(b.get("to")) or "brand")
        if what == "stage":
            return await run(S.stage, tenant, ref, _s(b.get("stage")), _s(b.get("reason")))
        if what == "paid":
            return await run(S.received, tenant, ref, b.get("amount"), b.get("tds"), _s(b.get("ref")), _s(b.get("on")))
        if what == "payout_sent":
            return await run(S.payout_sent, tenant, ref, _s(b.get("ref")))
        if what == "forget":
            return await run(S.forget, tenant, "", ref)
        if what == "metrics_text":
            t = _s(b.get("csv"))
            if len(t) > 2_000_000:
                raise HTTPException(413, "Sheet bahut badi.")
            return await run(S.import_metrics, tenant, ref, t)
        raise HTTPException(404, "Nahi pehchana.")

    # ---- posts / calendar / checks
    @r.get("/posts")
    async def list_posts(deal: str = "", day_from: str = "", status: str = "", tenant: str = Depends(current_tenant)):
        return {"posts": await run(S.posts, tenant, deal, day_from, status)}

    @r.get("/calendar")
    async def get_calendar(month: str = "", tenant: str = Depends(current_tenant)):
        return await run(S.calendar, tenant, month)

    @r.patch("/posts/{ref}")
    async def patch_post(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        keys = ("caption", "script", "duration_s", "ai_media", "due", "ticks", "brand_notes", "brand_ok", "live_url", "posted_on", "status")
        return await run(S.post_save, tenant, ref, "owner", **{k: b[k] for k in keys if k in b})

    @r.post("/posts/{ref}/metrics")
    async def post_metrics(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.metrics, tenant, ref, "owner", **_b(body))

    @r.post("/posts/{ref}/{what}")
    async def post_card(ref: str, what: str, tenant: str = Depends(current_tenant)):
        if what == "content":
            return await run(S.content_request, tenant, ref)
        if what == "golive":
            return await run(S.golive_request, tenant, ref)
        raise HTTPException(404, "Nahi pehchana.")

    @r.post("/check")
    async def check(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.check_text, tenant, _s(b.get("caption")), _s(b.get("platform")) or "instagram", _s(b.get("fmt")) or "reel",
                         _s(b.get("kind")) or "paid", _s(b.get("creator")), bool(b.get("ai_media")), b.get("duration_s"))

    # ---- cards (HER tap)
    @r.get("/cards")
    async def list_cards(status: str = "waiting", tenant: str = Depends(current_tenant)):
        return {"cards": await run(S.cards, tenant, status)}

    @r.get("/cards/{cid}")
    async def get_card(cid: str, tenant: str = Depends(current_tenant)):
        return await run(S.card_view, tenant, cid)

    @r.post("/cards/{cid}/challenge")
    async def card_challenge(cid: str, tenant: str = Depends(current_tenant)):
        return await run(S.card_challenge, tenant, cid)

    @r.post("/cards/{cid}/decide")
    async def card_decide(cid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        proof = b.get("proof") if isinstance(b.get("proof"), dict) else None
        return await run(S.decide, tenant, cid, bool(b.get("yes")), _s(b.get("hash")), _s(b.get("reason")), proof, True)

    return r
