"""/api/bahi/* - the GST & Accounts desk (A0). Signed-in owner only (require_key + her tenant). No route returns a WhiteBooks key,
a password, a token or an OTP; none files or pays."""
from __future__ import annotations

from typing import Any


def make_router(require_key, current_tenant):
    from fastapi import APIRouter, Depends, HTTPException

    from . import connect as CN
    from . import einv as EV
    from . import gstr1 as G1
    from . import gstr3b as G3
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

    def _g1(fn, *a, **k):
        try:
            return fn(*a, **k)
        except G1.Gstr1Error as e:
            raise HTTPException(400, str(e))

    @r.post("/api/bahi/gstr1/prepare", dependencies=[Depends(require_key)])
    def _g1prep(body: dict, tenant: str = Depends(current_tenant)) -> dict[str, Any]:
        return _g1(G1.prepare, tenant, str(body.get("gstin") or ""), str(body.get("period") or ""))

    @r.post("/api/bahi/gstr1/save", dependencies=[Depends(require_key)])
    def _g1save(body: dict, tenant: str = Depends(current_tenant)) -> dict[str, Any]:
        return _g1(G1.save_draft, tenant, str(body.get("gstin") or ""), str(body.get("period") or ""), str(body.get("plan_hash") or ""),
                   body.get("confirm") is True)

    @r.post("/api/bahi/gstr1/evc-otp", dependencies=[Depends(require_key)])
    def _g1otp(body: dict, tenant: str = Depends(current_tenant)) -> dict[str, Any]:
        return _g1(G1.request_evc_otp, tenant, str(body.get("gstin") or ""), str(body.get("pan") or ""))

    @r.post("/api/bahi/gstr1/file", dependencies=[Depends(require_key)])
    def _g1file(body: dict, tenant: str = Depends(current_tenant)) -> dict[str, Any]:
        return _g1(G1.file_evc, tenant, str(body.get("gstin") or ""), str(body.get("period") or ""), str(body.get("pan") or ""),
                   str(body.get("otp") or ""), str(body.get("plan_hash") or ""), body.get("confirm") is True)

    def _g3(fn, *a, **k):
        try:
            return fn(*a, **k)
        except G3.Gstr3bError as e:
            raise HTTPException(400, str(e))

    def _gp3(body):
        return str(body.get("gstin") or ""), str(body.get("period") or "")

    @r.post("/api/bahi/gstr3b/prepare", dependencies=[Depends(require_key)])
    def _g3prep(body: dict, tenant: str = Depends(current_tenant)) -> dict[str, Any]:
        return _g3(G3.prepare, tenant, *_gp3(body))

    @r.post("/api/bahi/gstr3b/compare", dependencies=[Depends(require_key)])
    def _g3cmp(body: dict, tenant: str = Depends(current_tenant)) -> dict[str, Any]:
        return _g3(G3.compare_with_portal, tenant, *_gp3(body))

    @r.post("/api/bahi/gstr3b/save", dependencies=[Depends(require_key)])
    def _g3save(body: dict, tenant: str = Depends(current_tenant)) -> dict[str, Any]:
        return _g3(G3.save_draft, tenant, *_gp3(body), str(body.get("plan_hash") or ""), body.get("confirm") is True)

    @r.post("/api/bahi/gstr3b/setoff", dependencies=[Depends(require_key)])
    def _g3off(body: dict, tenant: str = Depends(current_tenant)) -> dict[str, Any]:
        return _g3(G3.apply_setoff, tenant, *_gp3(body), str(body.get("plan_hash") or ""), body.get("confirm") is True)

    @r.post("/api/bahi/gstr3b/payment", dependencies=[Depends(require_key)])
    def _g3pay(body: dict, tenant: str = Depends(current_tenant)) -> dict[str, Any]:
        return _g3(G3.payment_plan, tenant, *_gp3(body))

    @r.post("/api/bahi/gstr3b/evc-otp", dependencies=[Depends(require_key)])
    def _g3otp(body: dict, tenant: str = Depends(current_tenant)) -> dict[str, Any]:
        return _g3(G3.request_evc_otp, tenant, str(body.get("gstin") or ""), str(body.get("pan") or ""))

    @r.post("/api/bahi/gstr3b/file", dependencies=[Depends(require_key)])
    def _g3file(body: dict, tenant: str = Depends(current_tenant)) -> dict[str, Any]:
        return _g3(G3.file_evc, tenant, *_gp3(body), str(body.get("pan") or ""), str(body.get("otp") or ""),
                   str(body.get("plan_hash") or ""), body.get("confirm") is True)

    def _ev(fn, *a, **k):
        try:
            return fn(*a, **k)
        except EV.EinvError as e:
            raise HTTPException(400, str(e))

    @r.get("/api/bahi/einv/status", dependencies=[Depends(require_key)])
    def _evst(gstin: str, tenant: str = Depends(current_tenant)) -> dict[str, Any]:
        return _ev(EV.status, tenant, gstin)

    @r.post("/api/bahi/einv/connect", dependencies=[Depends(require_key)])
    def _evcon(body: dict, tenant: str = Depends(current_tenant)) -> dict[str, Any]:
        return _ev(EV.connect, tenant, str(body.get("gstin") or ""), str(body.get("username") or ""), str(body.get("password") or ""),
                   body.get("seller") if isinstance(body.get("seller"), dict) else {}, str(body.get("irp") or ""),
                   str(body.get("ewb_username") or ""), str(body.get("ewb_password") or ""))

    @r.get("/api/bahi/einv/list", dependencies=[Depends(require_key)])
    def _evlist(gstin: str, tenant: str = Depends(current_tenant)) -> dict[str, Any]:
        return _ev(EV.listing, tenant, gstin)

    @r.post("/api/bahi/einv/build", dependencies=[Depends(require_key)])
    def _evbuild(body: dict, tenant: str = Depends(current_tenant)) -> dict[str, Any]:
        return _ev(EV.build, tenant, str(body.get("gstin") or ""), str(body.get("doc_id") or ""), body.get("extra") if isinstance(body.get("extra"), dict) else {})

    @r.post("/api/bahi/einv/generate", dependencies=[Depends(require_key)])
    def _evgen(body: dict, tenant: str = Depends(current_tenant)) -> dict[str, Any]:
        return _ev(EV.generate, tenant, str(body.get("gstin") or ""), str(body.get("doc_id") or ""),
                   body.get("extra") if isinstance(body.get("extra"), dict) else {}, str(body.get("plan_hash") or ""), body.get("confirm") is True)

    @r.post("/api/bahi/einv/cancel", dependencies=[Depends(require_key)])
    def _evcan(body: dict, tenant: str = Depends(current_tenant)) -> dict[str, Any]:
        return _ev(EV.cancel, tenant, str(body.get("irn_id") or ""), str(body.get("reason") or ""), str(body.get("remark") or ""), body.get("confirm") is True)

    @r.post("/api/bahi/einv/ewb", dependencies=[Depends(require_key)])
    def _evewb(body: dict, tenant: str = Depends(current_tenant)) -> dict[str, Any]:
        return _ev(EV.ewb_from_irn, tenant, str(body.get("irn_id") or ""), body.get("transport") if isinstance(body.get("transport"), dict) else {},
                   body.get("confirm") is True)

    @r.post("/api/bahi/einv/ewb-cancel", dependencies=[Depends(require_key)])
    def _evewbc(body: dict, tenant: str = Depends(current_tenant)) -> dict[str, Any]:
        return _ev(EV.ewb_cancel, tenant, str(body.get("irn_id") or ""), str(body.get("reason_code") or "2"), str(body.get("remark") or ""),
                   body.get("confirm") is True)

    return r
