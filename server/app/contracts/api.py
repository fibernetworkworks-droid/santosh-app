"""HTTP routes of the Contracts Sahayak (/api/contracts/*). main.py: app.include_router(make_router(require_key, current_tenant)).

HER taps live ONLY here (by_tap=True): POST /cards/{id}/decide (send a draft / redline to the other side, e-sign steps, e-stamp
steps (428 fingerprint_needed -> POST /cards/{id}/challenge, sign, resend with `proof`), notice letters)."""
from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException


def make_router(require_key, current_tenant) -> APIRouter:
    from . import rules as R
    from . import service as S

    r = APIRouter(prefix="/api/contracts", dependencies=[Depends(require_key)])

    async def run(fn, *a, **k):
        try:
            return await asyncio.to_thread(fn, *a, **k)
        except S.ContractError as e:
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
            return {"settings": S.settings(tenant), "contracts": S.contracts(tenant), "day": S.day(tenant),
                    "renewals": S.renewals(tenant), "cards": S.cards(tenant, "waiting"), "never": R.NEVER, "draft": R.DRAFT_LINE}
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
        out = await run(S.save_settings, tenant, **{k: b[k] for k in S._SET_KEYS if k in b})
        if isinstance(b.get("stamp_rates"), list):
            await run(S.set_rates, tenant, b["stamp_rates"])
            out = await run(S.settings, tenant)
        return out

    @r.get("/playbook")
    async def get_playbook(tenant: str = Depends(current_tenant)):
        return await run(S.playbook_view, tenant)

    @r.put("/playbook/{key}")
    async def put_playbook(key: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.save_playbook, tenant, key, b.get("position"), b.get("level"), b.get("value"), b.get("standard_text"),
                         b.get("off"), bool(b.get("reset")))

    @r.get("/contracts")
    async def list_contracts(q: str = "", status: str = "", tenant: str = Depends(current_tenant)):
        return {"contracts": await run(S.contracts, tenant, q, status)}

    @r.post("/contracts")
    async def add(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.add, tenant, _s(b.get("title")), _s(b.get("file_id")), _s(b.get("text")), _s(b.get("kind")),
                         _s(b.get("counterparty")), _s(b.get("our_role")), _s(b.get("our_label")), _s(b.get("their_label")),
                         _s(b.get("their_contact")), _s(b.get("status")))

    @r.get("/contracts/{ref}")
    async def get_contract(ref: str, tenant: str = Depends(current_tenant)):
        return await run(S.contract_view, tenant, ref)

    @r.patch("/contracts/{ref}")
    async def patch_contract(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.update, tenant, ref, **_b(body))

    @r.post("/contracts/{ref}/review")
    async def review(ref: str, tenant: str = Depends(current_tenant)):
        return await run(S.review_again, tenant, ref)

    @r.post("/contracts/{ref}/version")
    async def version(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.add_version, tenant, ref, _s(b.get("file_id")), _s(b.get("text")), _s(b.get("note")))

    @r.post("/contracts/{ref}/redline")
    async def redline(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.redline, tenant, ref, b.get("keys") or [], b.get("edits") or [], _s(b.get("note")), "", bool(b.get("use_model")))

    @r.post("/contracts/{ref}/share")
    async def share(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.share_version, tenant, ref, int(_b(body).get("version") or 0))

    @r.post("/contracts/{ref}/obligations")
    async def oblig(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.oblig_add, tenant, ref, _s(b.get("what")), _s(b.get("due")), _s(b.get("who") or "us"), _s(b.get("kind") or "other"),
                         b.get("every_months"))

    @r.get("/obligations")
    async def list_obligations(status: str = "open", days: int | None = None, tenant: str = Depends(current_tenant)):
        return {"obligations": await run(S.obligations, tenant, status, days)}

    @r.post("/obligations/{oid}/done")
    async def oblig_done(oid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.oblig_done, tenant, oid, _s(b.get("note")), bool(b.get("waive")))

    @r.post("/contracts/{ref}/cards")
    async def card(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        kind = _s(b.pop("kind", ""))
        b.pop("conv", None)
        return await run(S.card_request, tenant, ref, kind, "", **b)

    @r.get("/cards")
    async def list_cards(status: str = "", tenant: str = Depends(current_tenant)):
        return {"cards": await run(S.cards, tenant, status)}

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
    async def card_done(cid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.card_done, tenant, cid, _s(_b(body).get("note")))

    @r.post("/contracts/{ref}/signed")
    async def signed(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.signed, tenant, ref, _s(b.get("on")), _s(b.get("file_id")), _s(b.get("note")))

    @r.post("/contracts/{ref}/stamped")
    async def stamped(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.stamped, tenant, ref, _s(b.get("cert_no")), _s(b.get("on")), b.get("amount"), bool(b.get("not_needed")))

    @r.post("/contracts/{ref}/status")
    async def status(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.set_status, tenant, ref, _s(_b(body).get("status")))

    @r.post("/contracts/{ref}/forget")
    async def forget(ref: str, tenant: str = Depends(current_tenant)):
        return await run(S.forget, tenant, ref)

    @r.get("/register")
    async def register(tenant: str = Depends(current_tenant)):
        return await run(S.register_file, tenant)

    @r.get("/rules")
    async def rules():
        return {"kinds": R.KINDS, "roles": list(R.ROLES), "clauses": {k: v["label"] for k, v in R.CLAUSES.items()},
                "first_schedule": R.FIRST_SCHEDULE, "never": R.NEVER, "draft": R.DRAFT_LINE, "sources": R.SOURCES,
                "notice_kinds": S.NOTICE_KINDS, "card_kinds": S.CARD_KINDS}

    return r
