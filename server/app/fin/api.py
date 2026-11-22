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

    @r.post("/api/fin/household/{part}", dependencies=dep)
    def _household(part: str, body: dict | None = None, tenant: str = Depends(current_tenant)) -> dict[str, Any]:
        from . import core
        from .desks import household as HH
        from .desks.safety import SafetyError
        a = dict(body or {})
        try:
            return core.run_tool(tenant, "owner", "household_money", part, a, lambda: HH.run(tenant, part, a))
        except L.Refused as e:
            raise HTTPException(403, str(e))
        except (SafetyError, PR.ProfileError) as e:
            _err(e)

    @r.post("/api/fin/books/{part}", dependencies=dep)
    def _books(part: str, body: dict | None = None, tenant: str = Depends(current_tenant)) -> dict[str, Any]:
        from . import core
        from .desks import books as BK
        a = dict(body or {})
        try:
            return core.run_tool(tenant, "owner", "books_accounts", part, a, lambda: BK.run(tenant, part, a, "owner"))
        except L.Refused as e:
            raise HTTPException(403, str(e))
        except (BK.BooksError, PR.ProfileError) as e:
            _err(e)

    @r.post("/api/fin/tax/{part}", dependencies=dep)
    def _tax(part: str, body: dict | None = None, tenant: str = Depends(current_tenant)) -> dict[str, Any]:
        from . import core
        from .desks import tax as TX
        a = dict(body or {})
        try:
            return core.run_tool(tenant, "owner", "tax_worldwide", part, a, lambda: TX.run(tenant, part, a, "owner"))
        except L.Refused as e:
            raise HTTPException(403, str(e))
        except (TX.TaxError, PR.ProfileError) as e:
            _err(e)

    @r.post("/api/fin/payroll/{part}", dependencies=dep)
    def _payroll(part: str, body: dict | None = None, tenant: str = Depends(current_tenant)) -> dict[str, Any]:
        from . import core
        from .desks import payroll as PY
        a = dict(body or {})
        try:
            return core.run_tool(tenant, "owner", "payroll_worldwide", part, a, lambda: PY.run(tenant, part, a, "owner"))
        except L.Refused as e:
            raise HTTPException(403, str(e))
        except (PY.PayrollError, PR.ProfileError) as e:
            _err(e)

    @r.post("/api/fin/cash/{part}", dependencies=dep)
    def _cash(part: str, body: dict | None = None, tenant: str = Depends(current_tenant)) -> dict[str, Any]:
        from . import core
        from .desks import cash as CS
        a = dict(body or {})
        try:
            return core.run_tool(tenant, "owner", "cash_treasury", part, a, lambda: CS.run(tenant, part, a, "owner"))
        except L.Refused as e:
            raise HTTPException(403, str(e))
        except (CS.CashError, PR.ProfileError) as e:
            _err(e)

    @r.post("/api/fin/credit/{part}", dependencies=dep)
    def _credit(part: str, body: dict | None = None, tenant: str = Depends(current_tenant)) -> dict[str, Any]:
        from . import core
        from .desks import credit as CR
        a = dict(body or {})
        try:
            return core.run_tool(tenant, "owner", "credit_lending", part, a, lambda: CR.run(tenant, part, a, "owner"))
        except L.Refused as e:
            raise HTTPException(403, str(e))
        except (CR.CreditError, PR.ProfileError) as e:
            _err(e)

    @r.post("/api/fin/firm/{part}", dependencies=dep)
    def _firm(part: str, body: dict | None = None, tenant: str = Depends(current_tenant)) -> dict[str, Any]:
        from . import core
        from .desks import firm as FM
        a = dict(body or {})
        try:
            return core.run_tool(tenant, "owner", "firm_practice", part, a, lambda: FM.run(tenant, part, a, "owner"))
        except L.Refused as e:
            raise HTTPException(403, str(e))
        except (FM.FirmError, PR.ProfileError) as e:
            _err(e)

    @r.post("/api/fin/payments/{part}", dependencies=dep)
    def _paydesk(part: str, body: dict | None = None, tenant: str = Depends(current_tenant)) -> dict[str, Any]:
        from . import core
        from .desks import payments as PM
        a = dict(body or {})
        try:
            return core.run_tool(tenant, "owner", "payments_desk", part, a, lambda: PM.run(tenant, part, a, "owner"))
        except L.Refused as e:
            raise HTTPException(403, str(e))
        except (PM.PaymentsError, PR.ProfileError) as e:
            _err(e)

    @r.post("/api/fin/institution/{part}", dependencies=dep)
    def _institution(part: str, body: dict | None = None, tenant: str = Depends(current_tenant)) -> dict[str, Any]:
        from . import core
        from .desks import institution as IN
        a = dict(body or {})
        try:
            return core.run_tool(tenant, "owner", "institution_desk", part, a, lambda: IN.run(tenant, part, a, "owner"))
        except L.Refused as e:
            raise HTTPException(403, str(e))
        except (IN.InstError, PR.ProfileError) as e:
            _err(e)

    @r.post("/api/fin/investments/{part}", dependencies=dep)
    def _investdesk(part: str, body: dict | None = None, tenant: str = Depends(current_tenant)) -> dict[str, Any]:
        from . import core
        from .desks import investments as IV
        a = dict(body or {})
        try:
            return core.run_tool(tenant, "owner", "investments_desk", part, a, lambda: IV.run(tenant, part, a, "owner"))
        except L.Refused as e:
            raise HTTPException(403, str(e))
        except IV.InvestError as e:
            _err(e)

    @r.post("/api/fin/markets/{part}", dependencies=dep)
    def _mktdesk(part: str, body: dict | None = None, tenant: str = Depends(current_tenant)) -> dict[str, Any]:
        from . import core
        from .desks import markets as MK
        a = dict(body or {})
        try:
            return core.run_tool(tenant, "owner", "markets_desk", part, a, lambda: MK.run(tenant, part, a, "owner"))
        except L.Refused as e:
            raise HTTPException(403, str(e))
        except MK.MarketsError as e:
            _err(e)

    @r.post("/api/fin/community/{part}", dependencies=dep)
    def _commfin(part: str, body: dict | None = None, tenant: str = Depends(current_tenant)) -> dict[str, Any]:
        from . import core
        from .desks import community as CM
        a = dict(body or {})
        try:
            return core.run_tool(tenant, "owner", "community_finance", part, a, lambda: CM.run(tenant, part, a, "owner"))
        except L.Refused as e:
            raise HTTPException(403, str(e))
        except CM.CommunityError as e:
            _err(e)

    @r.post("/api/fin/digital/{part}", dependencies=dep)
    def _digiasset(part: str, body: dict | None = None, tenant: str = Depends(current_tenant)) -> dict[str, Any]:
        from . import core
        from .desks import digital as DG
        a = dict(body or {})
        try:
            return core.run_tool(tenant, "owner", "digital_assets", part, a, lambda: DG.run(tenant, part, a, "owner"))
        except L.Refused as e:
            raise HTTPException(403, str(e))
        except DG.DigitalError as e:
            _err(e)

    @r.post("/api/fin/public/{part}", dependencies=dep)
    def _pubfin(part: str, body: dict | None = None, tenant: str = Depends(current_tenant)) -> dict[str, Any]:
        from . import core
        from .desks import public as PB
        a = dict(body or {})
        try:
            return core.run_tool(tenant, "owner", "public_finance", part, a, lambda: PB.run(tenant, part, a, "owner"))
        except L.Refused as e:
            raise HTTPException(403, str(e))
        except PB.PublicError as e:
            _err(e)

    @r.get("/api/fin/proof", dependencies=dep)
    def _proof() -> dict[str, Any]:
        """The proof without running the cards (that takes minutes: python -m app.fin.proof, or vps-ops fin_proof)."""
        from . import proof as PF
        u, p = PF.users(), PF.packs()
        return {"users": u, "packs": p, "cards": "run python -m app.fin.proof on the server (vps-ops fin_proof)"}

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
