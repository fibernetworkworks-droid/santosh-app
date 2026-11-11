"""/api/bahi/* - the GST & Accounts desk (A0). Signed-in owner only (require_key + her tenant). No route returns a WhiteBooks key,
a password, a token or an OTP; none files or pays."""
from __future__ import annotations

from typing import Any


def make_router(require_key, current_tenant):
    from fastapi import APIRouter, Depends, HTTPException

    from . import register as REG
    from . import rules as RU
    from . import service as SV

    r = APIRouter()

    @r.get("/api/bahi/overview", dependencies=[Depends(require_key)])
    def _overview(tenant: str = Depends(current_tenant)) -> dict[str, Any]:
        return SV.overview(tenant)

    @r.post("/api/bahi/sync", dependencies=[Depends(require_key)])
    def _sync(body: dict | None = None, tenant: str = Depends(current_tenant)) -> dict[str, Any]:
        b = body or {}
        months = b.get("months") if isinstance(b.get("months"), list) else None
        sources = b.get("sources") if isinstance(b.get("sources"), list) else None
        try:
            return REG.sync(tenant, months=months, sources=sources)
        except REG.RegisterError as e:
            raise HTTPException(400, str(e))

    @r.get("/api/bahi/register", dependencies=[Depends(require_key)])
    def _register(period: str = "", direction: str = "", source: str = "", q: str = "", limit: int = 200,
                  tenant: str = Depends(current_tenant)) -> dict[str, Any]:
        return {"rows": REG.listing(tenant, period=period, direction=direction, source=source, q=q, limit=limit)}

    @r.get("/api/bahi/rules", dependencies=[Depends(require_key)])
    def _rules() -> dict[str, Any]:
        return {"freshness": RU.freshness(), "files": {n: RU.load(n) for n in RU.NAMES}}

    @r.post("/api/bahi/periods/{period}/lock", dependencies=[Depends(require_key)])
    def _lock(period: str, body: dict | None = None, tenant: str = Depends(current_tenant)) -> dict[str, Any]:
        b = body or {}
        try:
            return REG.set_lock(tenant, period, bool(b.get("on", True)), gstin=str(b.get("gstin") or "")[:15],
                                by="owner", note=str(b.get("note") or ""))
        except REG.RegisterError as e:
            raise HTTPException(400, str(e))

    return r
