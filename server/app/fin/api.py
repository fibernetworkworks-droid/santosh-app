"""/api/fin/* - the finance core (F0). Signed-in owner only (require_key + her tenant). No route moves money, files or signs."""
from __future__ import annotations

from typing import Any


def make_router(require_key, current_tenant):
    from fastapi import APIRouter, Depends, HTTPException

    from . import evidence as EV
    from . import laws as L
    from . import pack as P
    from . import profile as PR
    from . import spine as SP

    r = APIRouter()
    dep = [Depends(require_key)]

    def _err(e: Exception):
        raise HTTPException(400, str(e))

    @r.get("/api/fin/setup", dependencies=dep)
    def _questions() -> dict[str, Any]:
        return {"questions": PR.questions(), "sizes": PR.SIZES, "employees": PR.EMPLOYEES, "serves": PR.SERVES,
                "not_advice": L.NOT_ADVICE}

    @r.post("/api/fin/setup/preview", dependencies=dep)
    def _preview(body: dict | None = None) -> dict[str, Any]:
        try:
            return PR.preview((body or {}).get("answers") or body)
        except PR.ProfileError as e:
            _err(e)

    @r.post("/api/fin/setup/apply", dependencies=dep)
    def _apply(body: dict | None = None, tenant: str = Depends(current_tenant)) -> dict[str, Any]:
        b = body or {}
        try:
            return PR.apply(tenant, b.get("answers"), str(b.get("hash") or ""), str(b.get("workspace_id") or ""),
                            str(b.get("parent_id") or ""))
        except PR.ProfileError as e:
            _err(e)

    @r.get("/api/fin/workspaces", dependencies=dep)
    def _workspaces(tenant: str = Depends(current_tenant)) -> dict[str, Any]:
        return {"workspaces": PR.workspaces(tenant)}

    @r.get("/api/fin/packs", dependencies=dep)
    def _packs() -> dict[str, Any]:
        return P.check_all()

    @r.get("/api/fin/packs/{cc}", dependencies=dep)
    def _pack(cc: str) -> dict[str, Any]:
        try:
            return P.view(cc)
        except P.PackError as e:
            _err(e)

    @r.get("/api/fin/laws", dependencies=dep)
    def _laws() -> dict[str, Any]:
        return {"tier_c": [L.tier_c(k) for k in L.TIER_C], "not_advice": L.NOT_ADVICE}

    @r.post("/api/fin/{ws}/import", dependencies=dep)
    def _import(ws: str, body: dict | None = None, tenant: str = Depends(current_tenant)) -> dict[str, Any]:
        b = body or {}
        try:
            return SP.import_statement(tenant, ws, str(b.get("text") or ""), str(b.get("account") or "Main account"),
                                       str(b.get("currency") or ""), str(b.get("format") or ""))
        except (SP.SpineError, PR.ProfileError) as e:
            _err(e)

    @r.get("/api/fin/{ws}/accounts", dependencies=dep)
    def _accounts(ws: str, tenant: str = Depends(current_tenant)) -> dict[str, Any]:
        try:
            return {"accounts": SP.accounts(tenant, ws)}
        except PR.ProfileError as e:
            _err(e)

    @r.get("/api/fin/{ws}/txns", dependencies=dep)
    def _txns(ws: str, account: str = "", since: str = "", until: str = "", limit: int = 500,
              tenant: str = Depends(current_tenant)) -> dict[str, Any]:
        try:
            return {"txns": SP.txns(tenant, ws, account, since, until, limit)}
        except PR.ProfileError as e:
            _err(e)

    @r.get("/api/fin/events", dependencies=dep)
    def _events(ws: str = "", tenant: str = Depends(current_tenant)) -> dict[str, Any]:
        return {"events": EV.events(tenant, ws), "chain": EV.verify(tenant)}

    return r
