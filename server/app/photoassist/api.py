"""HTTP routes of the Photo Sahayak (/api/photoassist/*). main.py: app.include_router(make_router(require_key, current_tenant)).

HER taps live ONLY here (by_tap=True): POST /cards/{id}/decide {yes, hash, reason, proof} for quotation / booking terms /
hold -> confirmed / payment request / gallery delivery / invoice / message / discount / refund. Money cards (discount, refund)
need her fingerprint once a phone key is active: 428 -> POST /cards/{id}/challenge -> sign -> resend with `proof`.
All routes key-protected (no public routes)."""
from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, Body, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response


def make_router(require_key, current_tenant) -> APIRouter:
    from . import service as S

    r = APIRouter(prefix="/api/photoassist", dependencies=[Depends(require_key)])

    async def run(fn, *a, **k):
        try:
            return await asyncio.to_thread(fn, *a, **k)
        except S.PhotoError as e:
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

    @r.get("/settings")
    async def get_settings(tenant: str = Depends(current_tenant)):
        return await run(S.settings, tenant)

    @r.put("/settings")
    async def put_settings(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.save_settings, tenant, "owner", **{k: b[k] for k in S._SET_KEYS if k in b})

    @r.get("/packages")
    async def list_packages(tenant: str = Depends(current_tenant)):
        return {"packages": await run(S.packages, tenant)}

    @r.post("/packages")
    async def save_package(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.package_save, tenant, _s(b.get("name")), b.get("price"), _s(b.get("unit")), b.get("includes"),
                         b.get("edits"), _s(b.get("id")), b.get("active"))

    @r.get("/gear")
    async def list_gear(tenant: str = Depends(current_tenant)):
        return {"gear": await run(S.gear, tenant)}

    @r.post("/gear")
    async def save_gear(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.gear_save, tenant, _s(b.get("name")), _s(b.get("kind")), _s(b.get("serial")), _s(b.get("uin")),
                         b.get("weight_g"), _s(b.get("insured_until")), _s(b.get("notes")), _s(b.get("id")), b.get("active"))

    @r.get("/free")
    async def free(day: str, start: str = "", end: str = "", shooter: str = "main", end_day: str = "",
                   tenant: str = Depends(current_tenant)):
        return await run(S.free, tenant, day, start, end, shooter, end_day)

    @r.get("/calendar")
    async def calendar(month: str = "", tenant: str = Depends(current_tenant)):
        return await run(S.calendar, tenant, month)

    @r.get("/shoots")
    async def list_shoots(status: str = "", day_from: str = "", tenant: str = Depends(current_tenant)):
        return {"shoots": await run(S.shoots, tenant, status, day_from)}

    @r.post("/shoots")
    async def new_shoot(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.shoot_save, tenant, "", "owner", "", **{k: b[k] for k in S._SH_KEYS if k in b})

    @r.get("/shoots/{sid}")
    async def get_shoot(sid: str, tenant: str = Depends(current_tenant)):
        return await run(S.shoot_view, tenant, sid)

    @r.patch("/shoots/{sid}")
    async def patch_shoot(sid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.shoot_save, tenant, sid, "owner", "", **{k: b[k] for k in S._SH_KEYS if k in b})

    @r.get("/shoots/{sid}/quote.pdf")
    async def quote_pdf(sid: str, tenant: str = Depends(current_tenant)):
        data = await run(S.quote_pdf, tenant, sid, False)
        return Response(data, media_type="application/pdf", headers={"Content-Disposition": f'inline; filename="{sid}_quote_draft.pdf"'})

    @r.get("/shoots/{sid}/receipt/{rc:path}")
    async def receipt(sid: str, rc: str, tenant: str = Depends(current_tenant)):
        data = await run(S.receipt_pdf, tenant, sid, rc)
        return Response(data, media_type="application/pdf", headers={"Content-Disposition": 'inline; filename="receipt.pdf"'})

    @r.post("/shoots/{sid}/cull")
    async def cull(sid: str, file: UploadFile = File(...), look: str = Form("true"), tenant: str = Depends(current_tenant)):
        data = await file.read()
        if len(data) > 25 * 1024 * 1024:
            raise HTTPException(413, "Photo 25 MB se badi.")
        return await run(S.cull, tenant, sid, [(file.filename or "photo.jpg", data)], None, look != "false")

    @r.post("/releases/{rid}/proof")
    async def release_proof_up(rid: str, file: UploadFile = File(...), tenant: str = Depends(current_tenant)):
        data = await file.read()
        if len(data) > 25 * 1024 * 1024:
            raise HTTPException(413, "Photo 25 MB se badi.")
        return await run(S.release_signed, tenant, rid, data)

    @r.get("/releases/{rid}/proof")
    async def release_proof(rid: str, tenant: str = Depends(current_tenant)):
        p, mime = await run(S.release_proof, tenant, rid)
        return FileResponse(p, media_type=mime)

    @r.get("/releases/{rid}/pdf")
    async def release_pdf(rid: str, tenant: str = Depends(current_tenant)):
        data = await run(S.release_pdf, tenant, rid)
        return Response(data, media_type="application/pdf", headers={"Content-Disposition": 'inline; filename="release.pdf"'})

    @r.post("/releases/{rid}/withdraw")
    async def release_withdraw(rid: str, tenant: str = Depends(current_tenant)):
        return await run(S.release_withdraw, tenant, rid)

    @r.get("/photos/{pid}")
    async def photo(pid: str, tenant: str = Depends(current_tenant)):
        p, mime = await run(S.photo_file, tenant, pid)
        return FileResponse(p, media_type=mime)

    @r.post("/photos/pick")
    async def photo_pick(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.pick, tenant, b.get("ids") or [], _s(b.get("choice")))

    @r.post("/shoots/{sid}/{what}")
    async def act(sid: str, what: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        """Card requests (never decide): quote | contract | confirm | pay | delivery | invoice | message | discount; and work:
        hold | release | shot | done | paid | cancel | refund_sent | forget | shots | gear | check | edit | release_new."""
        b = _b(body)
        if what == "quote":
            return await run(S.quote_request, tenant, sid)
        if what == "contract":
            return await run(S.contract_request, tenant, sid)
        if what == "confirm":
            return await run(S.confirm_request, tenant, sid)
        if what == "pay":
            return await run(S.pay_request, tenant, sid, _s(b.get("stage")), b.get("amount"))
        if what == "delivery":
            return await run(S.delivery_request, tenant, sid, _s(b.get("link")), _s(b.get("what")), _s(b.get("expires")))
        if what == "invoice":
            return await run(S.invoice_request, tenant, sid)
        if what == "message":
            return await run(S.message_request, tenant, sid, _s(b.get("text")))
        if what == "discount":
            return await run(S.discount_request, tenant, sid, b.get("amount"), b.get("pct"), _s(b.get("reason")))
        if what == "hold":
            return await run(S.hold, tenant, sid, b.get("hours"))
        if what == "release":
            return await run(S.release_hold, tenant, sid)
        if what == "shot":
            return await run(S.mark_shot, tenant, sid)
        if what == "done":
            return await run(S.done, tenant, sid)
        if what == "paid":
            return await run(S.paid, tenant, sid, b.get("amount"), _s(b.get("mode")) or "upi", _s(b.get("ref")), _s(b.get("day")))
        if what == "cancel":
            return await run(S.cancel, tenant, sid, _s(b.get("reason")), _s(b.get("by")) or "client")
        if what == "refund_sent":
            return await run(S.refund_sent, tenant, sid, _s(b.get("ref")))
        if what == "forget":
            return await run(S.forget, tenant, sid)
        if what == "shots":
            return await run(S.shots, tenant, sid, b.get("add"), b.get("tick"), b.get("untick"), bool(b.get("must")))
        if what == "gear":
            return await run(S.gear_check, tenant, sid, b.get("tick"), bool(b.get("rebuild")))
        if what == "check":
            return await run(S.checks_tick, tenant, sid, _s(b.get("key")), b.get("done", True) is not False)
        if what == "edit":
            return await run(S.edit, tenant, sid, _s(b.get("photo")), _s(b.get("ask")), _s(b.get("status")), b.get("index"))
        if what == "release_new":
            return await run(S.release_new, tenant, sid, _s(b.get("kind")) or "model", _s(b.get("person")), _s(b.get("guardian")),
                             _s(b.get("place")), b.get("uses"), _s(b.get("lang")) or "en")
        raise HTTPException(404, "Nahi pehchana.")

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
