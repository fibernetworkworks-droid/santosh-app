"""HTTP routes of the Legalres Sahayak (/api/legalres/*). main.py: app.include_router(make_router(require_key, current_tenant)).

HER tap lives ONLY here (by_tap=True): POST /shares/{id}/decide {yes, hash} (a memo going outside). The Indian Kanoon token is typed
ONLY here (PUT /key) and never returned."""
from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException


def make_router(require_key, current_tenant) -> APIRouter:
    from . import rules as R
    from . import service as S

    r = APIRouter(prefix="/api/legalres", dependencies=[Depends(require_key)])

    async def run(fn, *a, **k):
        try:
            return await asyncio.to_thread(fn, *a, **k)
        except S.LegalresError as e:
            raise HTTPException(400, str(e))
        except ValueError as e:
            raise HTTPException(400, str(e))

    async def arun(coro):
        try:
            return await coro
        except S.LegalresError as e:
            raise HTTPException(400, str(e))

    def _b(body) -> dict[str, Any]:
        return dict(body or {})

    def _s(v) -> str:
        return "" if v is None else str(v)

    @r.get("")
    async def overview(tenant: str = Depends(current_tenant)):
        def go():
            return {**S.day(tenant), "matters": S.matters(tenant), "never": R.NEVER, "disclaimer": R.DISCLAIMER}
        return await run(go)

    @r.get("/settings")
    async def get_settings(tenant: str = Depends(current_tenant)):
        return await run(S.settings, tenant)

    @r.put("/settings")
    async def put_settings(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.save_settings, tenant, "owner", **{k: b[k] for k in S._SET_KEYS if k in b})

    @r.put("/key")
    async def put_key(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.set_ik_key, tenant, _s(_b(body).get("token")))

    @r.delete("/key")
    async def del_key(tenant: str = Depends(current_tenant)):
        return await run(S.forget_ik_key, tenant)

    @r.get("/mapping")
    async def get_mapping(text: str = "", act: str = ""):
        return S.mapping(text, act)

    @r.get("/matters")
    async def list_matters(status: str = "", tenant: str = Depends(current_tenant)):
        return {"matters": await run(S.matters, tenant, status)}

    @r.post("/matters")
    async def new_matter(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.new_matter, tenant, _s(b.get("title")), _s(b.get("client")), _s(b.get("court")))

    @r.get("/matters/{ref}")
    async def get_matter(ref: str, tenant: str = Depends(current_tenant)):
        return await run(S.matter_view, tenant, ref)

    @r.patch("/matters/{ref}")
    async def patch_matter(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.update_matter, tenant, ref, "owner", **{k: b.get(k) for k in ("title", "client", "court", "status")})

    @r.post("/matters/{ref}/forget")
    async def forget(ref: str, tenant: str = Depends(current_tenant)):
        return await run(S.forget_matter, tenant, ref, "owner")

    @r.post("/research")
    async def research(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        urls = [u for u in (b.get("urls") or []) if isinstance(u, str)]
        return await arun(S.research(tenant, _s(b.get("question")), _s(b.get("matter")), urls, b.get("use_ik"), b.get("use_web"),
                                     b.get("use_files"), _s(b.get("client"))))

    @r.post("/matters/{ref}/link")
    async def add_link(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await arun(S.add_link(tenant, ref, _s(_b(body).get("url"))))

    @r.post("/matters/{ref}/note")
    async def add_note(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.note, tenant, ref, _s(_b(body).get("text")))

    @r.get("/matters/{ref}/memo")
    async def get_memo(ref: str, v: int = 0, tenant: str = Depends(current_tenant)):
        return await run(S.memo, tenant, ref, v or None)

    @r.post("/matters/{ref}/memo/file")
    async def memo_file(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        v = _b(body).get("v")
        return await run(S.memo_file, tenant, ref, int(v) if v else None)

    @r.get("/matters/{ref}/sources/{n}")
    async def get_source(ref: str, n: int, tenant: str = Depends(current_tenant)):
        return await run(S.source_text, tenant, ref, n)

    @r.post("/matters/{ref}/sources/{n}/save")
    async def save_source(ref: str, n: int, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.save_authority, tenant, ref, n, _s(b.get("note")), bool(b.get("saved", True)))

    @r.get("/authorities")
    async def get_authorities(q: str = "", matter: str = "", tenant: str = Depends(current_tenant)):
        return {"authorities": await run(S.authorities, tenant, q, matter)}

    @r.post("/matters/{ref}/share")
    async def share(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.share_request, tenant, ref, _s(b.get("to_name")), _s(b.get("to_contact")), _s(b.get("via")) or "whatsapp",
                         _s(b.get("note")), "owner")

    @r.get("/shares")
    async def list_shares(status: str = "", tenant: str = Depends(current_tenant)):
        return {"shares": await run(S.shares, tenant, status)}

    @r.post("/shares/{share_id}/decide")
    async def decide(share_id: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.decide_share, tenant, share_id, bool(b.get("yes")), _s(b.get("hash")), True)

    return r
