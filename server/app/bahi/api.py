"""/api/bahi/* - the GST & Accounts desk (A0). Signed-in owner only (require_key + her tenant). No route returns a WhiteBooks key,
a password, a token or an OTP; none files or pays."""
from __future__ import annotations

from typing import Any


def make_router(require_key, current_tenant):
    from fastapi import APIRouter, Depends, HTTPException

    from . import connect as CN
    from . import itc as IT
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

    @r.get("/api/bahi/connect", dependencies=[Depends(require_key)])
    def _conn(tenant: str = Depends(current_tenant)) -> dict[str, Any]:
        return {"connections": CN.status(tenant)}

    def _run(fn, *a, **k):
        try:
            return fn(*a, **k)
        except CN.ConnectError as e:
            raise HTTPException(400, str(e))

    @r.post("/api/bahi/connect/start", dependencies=[Depends(require_key)])
    def _cstart(body: dict, tenant: str = Depends(current_tenant)) -> dict[str, Any]:
        return _run(CN.start, tenant, str(body.get("gstin") or ""), str(body.get("gst_username") or ""))

    @r.post("/api/bahi/connect/verify", dependencies=[Depends(require_key)])
    def _cverify(body: dict, tenant: str = Depends(current_tenant)) -> dict[str, Any]:
        return _run(CN.verify, tenant, str(body.get("gstin") or ""), str(body.get("otp") or ""))

    @r.post("/api/bahi/connect/refresh", dependencies=[Depends(require_key)])
    def _crefresh(body: dict, tenant: str = Depends(current_tenant)) -> dict[str, Any]:
        return _run(CN.refresh, tenant, str(body.get("gstin") or ""))

    @r.post("/api/bahi/connect/disconnect", dependencies=[Depends(require_key)])
    def _cdisc(body: dict, tenant: str = Depends(current_tenant)) -> dict[str, Any]:
        return _run(CN.disconnect, tenant, str(body.get("gstin") or ""))

    @r.post("/api/bahi/supplier-check", dependencies=[Depends(require_key)])
    def _sup(body: dict, tenant: str = Depends(current_tenant)) -> dict[str, Any]:
        return _run(CN.supplier_check, tenant, str(body.get("gstin") or ""), filing=bool(body.get("filing", True)))

    def _it(fn, *a, **k):
        try:
            return fn(*a, **k)
        except IT.ItcError as e:
            raise HTTPException(400, str(e))

    @r.post("/api/bahi/itc/pull", dependencies=[Depends(require_key)])
    def _ipull(body: dict, tenant: str = Depends(current_tenant)) -> dict[str, Any]:
        return _it(IT.pull, tenant, str(body.get("gstin") or ""), str(body.get("period") or ""))

    @r.get("/api/bahi/itc/proposals", dependencies=[Depends(require_key)])
    def _iprop(gstin: str, period: str, tenant: str = Depends(current_tenant)) -> dict[str, Any]:
        return _it(IT.propose, tenant, gstin, period)

    @r.post("/api/bahi/itc/decide", dependencies=[Depends(require_key)])
    def _idec(body: dict, tenant: str = Depends(current_tenant)) -> dict[str, Any]:
        d = body.get("decisions") if isinstance(body.get("decisions"), dict) else {}
        return _it(IT.decide, tenant, str(body.get("gstin") or ""), str(body.get("period") or ""), d)

    @r.get("/api/bahi/itc/preview", dependencies=[Depends(require_key)])
    def _iprev(gstin: str, period: str, tenant: str = Depends(current_tenant)) -> dict[str, Any]:
        return _it(IT.preview, tenant, gstin, period)

    @r.post("/api/bahi/itc/apply", dependencies=[Depends(require_key)])
    def _iapply(body: dict, tenant: str = Depends(current_tenant)) -> dict[str, Any]:
        return _it(IT.apply, tenant, str(body.get("gstin") or ""), str(body.get("period") or ""), str(body.get("plan_hash") or ""),
                   body.get("confirm") is True)

    return r
