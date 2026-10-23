"""HTTP routes of the Vakil Sahayak (/api/vakil/*). main.py: app.include_router(make_router(require_key, current_tenant)).

HER taps live ONLY here (by_tap=True): POST /cards/{id}/decide (filing / message / fee; a fee card needs her fingerprint once a phone
key is active: 428 fingerprint_needed -> POST /cards/{id}/challenge, sign, resend with `proof`)."""
from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException


def make_router(require_key, current_tenant) -> APIRouter:
    from . import rules as R
    from . import service as S

    r = APIRouter(prefix="/api/vakil", dependencies=[Depends(require_key)])

    async def run(fn, *a, **k):
        try:
            return await asyncio.to_thread(fn, *a, **k)
        except S.VakilError as e:
            code = str(e)
            if code in ("fingerprint_needed", "fingerprint_invalid"):
                raise HTTPException(428, code)
            raise HTTPException(400, code)
        except ValueError as e:
            raise HTTPException(400, str(e))

    def _b(body) -> dict[str, Any]:
        return dict(body or {})

    def _s(v) -> str:
        return "" if v is None else str(v)

    @r.get("")
    async def overview(tenant: str = Depends(current_tenant)):
        def go():
            return {"settings": S.settings(tenant), "day": S.day(tenant), "matters": S.matters(tenant),
                    "deadlines": S.deadlines(tenant), "cards": S.cards(tenant), "never": R.NEVER}
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
        return {"limits": {k: {kk: v[kk] for kk in ("label", "n", "unit", "from", "src", "kind")} for k, v in R.LIMITS.items()},
                "ask_only": R.ASK_ONLY, "kinds": R.MATTER_KINDS, "sides": R.SIDES, "drafts": S.DRAFT_KINDS, "official": R.OFFICIAL,
                "sources": R.SOURCES, "never": R.NEVER, "check": R.CHECK}

    # ---- clients
    @r.get("/clients")
    async def list_clients(q: str = "", tenant: str = Depends(current_tenant)):
        return {"clients": await run(S.clients, tenant, q)}

    @r.post("/clients")
    async def new_client(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        name, ref = _s(b.pop("name", "")), _s(b.pop("ref", ""))
        return await run(S.save_client, tenant, name, ref, **b)

    @r.post("/clients/{ref}/forget")
    async def forget(ref: str, tenant: str = Depends(current_tenant)):
        return await run(S.forget, tenant, ref)

    # ---- matters
    @r.get("/matters")
    async def list_matters(status: str = "", q: str = "", tenant: str = Depends(current_tenant)):
        return {"matters": await run(S.matters, tenant, status, q)}

    @r.post("/matters")
    async def new_matter(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        title = _s(b.pop("title", ""))
        b.pop("ref", None)
        return await run(S.save_matter, tenant, title, "", **{k: b[k] for k in S._MATTER_KEYS if k in b})

    @r.get("/matters/{ref}")
    async def get_matter(ref: str, tenant: str = Depends(current_tenant)):
        return await run(S.matter_view, tenant, ref)

    @r.patch("/matters/{ref}")
    async def patch_matter(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        title = _s(b.pop("title", ""))
        return await run(S.save_matter, tenant, title, ref, **{k: b[k] for k in S._MATTER_KEYS if k in b})

    @r.post("/matters/{ref}/hearing")
    async def hearing(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.hearing, tenant, ref, _s(b.get("on")), _s(b.get("purpose")), _s(b.get("result")), _s(b.get("next_date")),
                         _s(b.get("next_purpose")), _s(b.get("stage")), "her")

    @r.post("/matters/{ref}/event")
    async def event(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.event, tenant, ref, _s(b.get("on")), _s(b.get("what")))

    @r.post("/matters/{ref}/docs")
    async def doc(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.doc_set, tenant, ref, _s(b.get("key")), _s(b.get("state") or "have"), _s(b.get("file_id")),
                         _s(b.get("note")), _s(b.get("label")))

    @r.post("/matters/{ref}/draft")
    async def draft(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.draft, tenant, ref, _s(b.get("kind")), _s(b.get("words")), _s(b.get("reason")), _s(b.get("to")))

    @r.post("/matters/{ref}/limitation")
    async def limitation(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.limitation, tenant, _s(b.get("kind")), _s(b.get("start")), ref, b.get("n"), _s(b.get("unit")),
                         _s(b.get("cc_applied")), _s(b.get("cc_ready")), _s(b.get("label")), True)

    @r.post("/limitation")
    async def limitation_try(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.limitation, tenant, _s(b.get("kind")), _s(b.get("start")), "", b.get("n"), _s(b.get("unit")),
                         _s(b.get("cc_applied")), _s(b.get("cc_ready")), _s(b.get("label")), False)

    @r.get("/deadlines")
    async def list_deadlines(status: str = "open", tenant: str = Depends(current_tenant)):
        return {"deadlines": await run(S.deadlines, tenant, status)}

    @r.post("/deadlines/{did}")
    async def deadline_set(did: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.deadline_done, tenant, did, _s(_b(body).get("status") or "done"))

    # ---- what she pasted from eCourts
    @r.post("/paste/status")
    async def paste_status(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.status_paste, tenant, _s(b.get("text")), _s(b.get("matter")))

    @r.post("/paste/cause_list")
    async def paste_cause(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.cause_list, tenant, _s(b.get("text")), _s(b.get("on")))

    # ---- cards (her tap)
    @r.get("/cards")
    async def list_cards(status: str = "waiting", tenant: str = Depends(current_tenant)):
        return {"cards": await run(S.cards, tenant, status)}

    @r.post("/matters/{ref}/message")
    async def message(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.message_request, tenant, ref, _s(b.get("to") or "client"), _s(b.get("text")), _s(b.get("purpose") or "update"),
                         _s(b.get("phone")), _s(b.get("email")))

    @r.post("/matters/{ref}/filing")
    async def filing(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.filing_request, tenant, ref, _s(b.get("what")), b.get("file_ids") or [], bool(b.get("use_operator")),
                         _s(b.get("note")))

    @r.post("/matters/{ref}/fee_request")
    async def fee_request(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.fee_request, tenant, ref, b.get("amount"), _s(b.get("for")))

    @r.post("/cards/{cid}/challenge")
    async def challenge(cid: str, tenant: str = Depends(current_tenant)):
        return await run(S.card_challenge, tenant, cid)

    @r.post("/cards/{cid}/decide")
    async def decide(cid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        if "yes" not in b:
            raise HTTPException(400, "yes = true | false")
        proof = b.get("proof") if isinstance(b.get("proof"), dict) else None
        return await run(S.decide, tenant, cid, bool(b["yes"]), _s(b.get("hash")), _s(b.get("reason")), proof, by_tap=True)

    @r.post("/cards/{cid}/done")
    async def done(cid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.card_done, tenant, cid, _s(b.get("ref_no")), _s(b.get("on")))

    # ---- fees
    @r.get("/fees")
    async def fees(matter: str = "", tenant: str = Depends(current_tenant)):
        return await run(S.ledger, tenant, matter)

    @r.post("/matters/{ref}/fee")
    async def fee(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.fee_add, tenant, ref, _s(b.get("kind")), b.get("amount"), _s(b.get("note")), _s(b.get("on")), _s(b.get("ref_no")))

    @r.get("/register")
    async def register(tenant: str = Depends(current_tenant)):
        return await run(S.register_file, tenant)

    return r
