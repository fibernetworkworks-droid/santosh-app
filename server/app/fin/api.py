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

    def _owner(tenant: str) -> None:
        from ..config import get_settings
        if tenant != get_settings().tenant_id:
            raise HTTPException(403, "Country rules are the same for every user, so only the Hoola owner can change them.")

    @r.get("/api/fin/packs/{cc}/todo", dependencies=dep)
    def _todo(cc: str) -> dict[str, Any]:
        from . import review as RV
        return {"cc": cc.upper(), "rules": RV.todo(cc)}

    @r.post("/api/fin/packs/{cc}/read", dependencies=dep)
    def _read(cc: str, body: dict | None = None, tenant: str = Depends(current_tenant)) -> dict[str, Any]:
        from . import review as RV
        _owner(tenant)
        b = body or {}
        try:
            return RV.read(cc, str(b.get("path") or ""), str(b.get("url") or ""), str(b.get("quote") or ""))
        except (RV.ReviewError, P.PackError) as e:
            _err(e)
        except Exception as e:   # the page could not be fetched
            raise HTTPException(502, f"Could not read the page: {type(e).__name__}")

    @r.post("/api/fin/packs/{cc}/confirm", dependencies=dep)
    def _confirm(cc: str, body: dict | None = None, tenant: str = Depends(current_tenant)) -> dict[str, Any]:
        from . import review as RV
        _owner(tenant)
        b = body or {}
        try:
            return RV.confirm(cc, str(b.get("path") or ""), str(b.get("checked_by") or ""), str(b.get("source") or ""),
                              b.get("value"), str(b.get("quote") or ""))
        except (RV.ReviewError, P.PackError) as e:
            _err(e)

    @r.get("/api/fin/safety/cases", dependencies=dep)
    def _safety_cases(tenant: str = Depends(current_tenant)) -> dict[str, Any]:
        from .desks import safety as SF
        return {"cases": SF.cases(tenant)}

    @r.post("/api/fin/safety/{part}", dependencies=dep)
    def _safety(part: str, body: dict | None = None, tenant: str = Depends(current_tenant)) -> dict[str, Any]:
        from . import core
        from .desks import safety as SF
        a = dict(body or {})
        try:
            return core.run_tool(tenant, "owner", "paisa_sahayak", part, a, lambda: SF.run(tenant, part, a))
        except L.Refused as e:
            raise HTTPException(403, str(e))
        except (SF.SafetyError, PR.ProfileError) as e:
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
