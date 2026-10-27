"""HTTP routes of the Artist Sahayak (/api/artistmgr/*). main.py: app.include_router(make_router(require_key, current_tenant)).

HER taps live ONLY here (by_tap=True): POST /cards/{id}/decide {yes, hash, reason, proof} for a reply / contract / invoice /
payment request / message going out, hold -> confirmed gig, release metadata final and the payout statement. The payout card
needs her fingerprint once a phone key is active: 428 -> POST /cards/{id}/challenge -> sign -> resend with `proof`.
All routes key-protected; no public routes."""
from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException
from fastapi.responses import Response


def make_router(require_key, current_tenant) -> APIRouter:
    from . import service as S

    r = APIRouter(prefix="/api/artistmgr", dependencies=[Depends(require_key)])

    async def run(fn, *a, **k):
        try:
            return await asyncio.to_thread(fn, *a, **k)
        except S.ArtistError as e:
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

    # ---- roster
    @r.get("/artists")
    async def list_artists(all: bool = False, tenant: str = Depends(current_tenant)):
        return {"artists": await run(S.artists, tenant, all)}

    @r.post("/artists")
    async def save_artist(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.artist_save, tenant, _s(b.get("name")), _s(b.get("kind")), _s(b.get("genre")), _s(b.get("phone")),
                         _s(b.get("email")), _s(b.get("city")), b.get("members"), b.get("min_fee"), _s(b.get("fee_note")),
                         b.get("commission_pct"), b.get("rider"), _s(b.get("gstin")), _s(b.get("upi_id")), _s(b.get("art_form")),
                         _s(b.get("notes")), _s(b.get("id")), b.get("active"))

    @r.get("/artists/{aid}")
    async def get_artist(aid: str, tenant: str = Depends(current_tenant)):
        return await run(S.artist_view, tenant, aid)

    @r.post("/artists/{aid}/regs")
    async def set_reg(aid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.reg_set, tenant, aid, _s(b.get("key")), _s(b.get("status")), _s(b.get("ref")), _s(b.get("note")))

    @r.post("/artists/{aid}/block")
    async def block(aid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.block_days, tenant, aid, _s(b.get("from")), _s(b.get("to")), _s(b.get("note")))

    @r.delete("/blocks/{bid}")
    async def unblock(bid: str, tenant: str = Depends(current_tenant)):
        return await run(S.unblock, tenant, bid)

    @r.post("/artists/{aid}/payout")
    async def payout(aid: str, tenant: str = Depends(current_tenant)):
        return await run(S.payout_request, tenant, aid)

    @r.post("/artists/{aid}/message")
    async def artist_message(aid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.message_request, tenant, _s(b.get("text")), "", aid, _s(b.get("to")))

    @r.post("/artists/{aid}/forget")
    async def forget_artist(aid: str, tenant: str = Depends(current_tenant)):
        return await run(S.forget_artist, tenant, aid)

    # ---- gigs
    @r.get("/check")
    async def check(artist: str, day: str, start: str = "", end: str = "", city: str = "", tenant: str = Depends(current_tenant)):
        return await run(S.check, tenant, artist, day, start, end, city)

    @r.get("/calendar")
    async def calendar(month: str = "", artist: str = "", tenant: str = Depends(current_tenant)):
        return await run(S.calendar, tenant, month, artist)

    @r.get("/gigs")
    async def list_gigs(status: str = "", artist: str = "", day_from: str = "", tenant: str = Depends(current_tenant)):
        return {"gigs": await run(S.gigs, tenant, status, artist, day_from)}

    @r.post("/gigs")
    async def new_gig(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        kw = {k: b[k] for k in S._GIG_KEYS if k in b and k != "artist"}
        return await run(S.offer, tenant, _s(b.get("text")), _s(b.get("artist")), "owner", "", **kw)

    @r.get("/gigs/{gid}")
    async def get_gig(gid: str, tenant: str = Depends(current_tenant)):
        return await run(S.gig_view, tenant, gid)

    @r.patch("/gigs/{gid}")
    async def patch_gig(gid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        kw = {k: b[k] for k in S._GIG_KEYS if k in b and k != "artist"}
        return await run(S.gig_save, tenant, gid, _s(b.get("artist")), "", "owner", "", **kw)

    @r.get("/gigs/{gid}/contract.pdf")
    async def contract_pdf(gid: str, tenant: str = Depends(current_tenant)):
        data = await run(S.contract_pdf, tenant, gid, False)
        return Response(data, media_type="application/pdf", headers={"Content-Disposition": f'inline; filename="{gid}_agreement_draft.pdf"'})

    @r.post("/gigs/{gid}/{what}")
    async def gig_action(gid: str, what: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        """Card requests (never decide): reply | contract | confirm | invoice | pay | message; and her records: hold | release |
        paid | tds | expense | done | cancel | travel | forget."""
        b = _b(body)
        if what == "reply":
            return await run(S.reply_request, tenant, gid, _s(b.get("text")))
        if what == "contract":
            return await run(S.contract_request, tenant, gid)
        if what == "confirm":
            return await run(S.confirm_request, tenant, gid)
        if what == "invoice":
            return await run(S.invoice_request, tenant, gid)
        if what == "pay":
            return await run(S.pay_request, tenant, gid, _s(b.get("stage")), b.get("amount"))
        if what == "message":
            return await run(S.message_request, tenant, _s(b.get("text")), gid, "", _s(b.get("to")))
        if what == "hold":
            return await run(S.hold, tenant, gid, b.get("hours"))
        if what == "release":
            return await run(S.release, tenant, gid)
        if what == "paid":
            return await run(S.paid, tenant, gid, b.get("amount"), _s(b.get("mode")) or "upi", _s(b.get("ref")), _s(b.get("day")))
        if what == "tds":
            return await run(S.set_tds, tenant, gid, b.get("amount"))
        if what == "expense":
            return await run(S.expense, tenant, gid, _s(b.get("what")), b.get("amount"), _s(b.get("paid_by")) or "manager")
        if what == "done":
            return await run(S.done, tenant, gid)
        if what == "cancel":
            return await run(S.cancel, tenant, gid, _s(b.get("reason")), _s(b.get("by")) or "promoter")
        if what == "travel":
            return await run(S.travel_link, tenant, gid, _s(b.get("origin")))
        if what == "forget":
            return await run(S.forget, tenant, gid)
        raise HTTPException(404, "Nahi pehchana.")

    # ---- releases + royalties + payouts
    @r.get("/releases")
    async def list_releases(artist: str = "", tenant: str = Depends(current_tenant)):
        return {"releases": await run(S.releases, tenant, artist)}

    @r.post("/releases")
    async def save_release(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.release_save, tenant, _s(b.get("artist")), _s(b.get("title")), _s(b.get("kind")), _s(b.get("day")),
                         _s(b.get("distributor")), _s(b.get("upc")), b.get("tracks"), b.get("artwork"), _s(b.get("label")),
                         _s(b.get("notes")), _s(b.get("id")))

    @r.get("/releases/{rid}")
    async def get_release(rid: str, tenant: str = Depends(current_tenant)):
        return await run(S.release_view, tenant, rid)

    @r.post("/releases/{rid}/final")
    async def release_final(rid: str, tenant: str = Depends(current_tenant)):
        return await run(S.release_final_request, tenant, rid)

    @r.post("/releases/{rid}/step")
    async def release_step(rid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.release_step, tenant, rid, _s(_b(body).get("step")))

    @r.post("/royalties")
    async def add_royalty(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.royalty_add, tenant, _s(b.get("artist")), _s(b.get("source")), b.get("amount"), _s(b.get("period")),
                         _s(b.get("release")), _s(b.get("ref")))

    @r.get("/payouts")
    async def list_payouts(artist: str = "", tenant: str = Depends(current_tenant)):
        return {"payouts": await run(S.payouts, tenant, artist)}

    @r.post("/payouts/{pid}/paid")
    async def payout_paid(pid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.payout_paid, tenant, pid, _s(_b(body).get("ref")))

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
