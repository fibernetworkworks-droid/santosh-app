"""v0.877 HOOLA AGENT API - the endpoints.

  PUBLIC (a Hoola API key, `Authorization: Bearer hk_live_...`)   /api/hoola-api/v1/*
      GET  /tools                 the catalogue: schema + INR price per call
      POST /tools/{name}          run one tool as the key's company; body {"arguments": {...}}
      GET  /balance               wallet balance + this key's spend today
      GET  /usage                 the key's company usage (?days=7)
  PORTAL (the company's own Hoola login)                         /api/hoola-portal/*
      GET /me, /catalog, /wallet, /ledger, /usage     GET|POST /keys     DELETE /keys/{id}
  ADMIN (the operator tenant only)                               /api/hoola-admin/*
      GET /overview     POST /wallets/{tenant}/credit     POST /wallets/{tenant}/suspend

Errors on the public API use the OpenAI shape: {"error": {"message", "type", "code"}}.
"""
from __future__ import annotations

import asyncio
import uuid

from fastapi import APIRouter, Body, Depends, HTTPException, Request
from fastapi.responses import JSONResponse

from . import catalog as CAT
from . import service as SV

MAX_ADJUST_INR = 1_000_000


def _err(e: SV.ApiError) -> JSONResponse:
    h = {"Retry-After": str(e.retry_after)} if e.retry_after else {}
    return JSONResponse({"error": {"message": e.message, "type": "hoola_api_error", "code": e.code}},
                        status_code=e.status, headers=h)


def _bearer(request: Request) -> str:
    return request.headers.get("authorization", "").removeprefix("Bearer ").strip()


def _operator(tenant: str) -> bool:
    try:
        from ..config import get_settings
        return tenant == str(getattr(get_settings(), "hoola_operator_tenant", "default") or "default")
    except Exception:       # noqa: BLE001
        return False


def make_router(require_key, current_tenant):
    r = APIRouter()

    # ------------------------------------------------------------ public API (key auth)
    async def _auth(request: Request) -> SV.Key:
        if not SV.enabled():
            raise SV.ApiError(503, "api_disabled", "The Hoola API is not switched on yet.")
        return await asyncio.to_thread(SV.resolve, _bearer(request))

    @r.get("/api/hoola-api/v1/tools")
    async def v1_tools(request: Request):
        try:
            k = await _auth(request)
            rows = CAT.listing()
            if k.tools:
                rows = [x for x in rows if x["name"] in k.tools]
            return {"tools": rows}
        except SV.ApiError as e:
            return _err(e)

    @r.post("/api/hoola-api/v1/tools/{name}")
    async def v1_call(name: str, request: Request):
        try:
            k = await _auth(request)
            try:
                body = await request.json()
            except Exception:       # noqa: BLE001
                body = {}
            if body is not None and not isinstance(body, dict):
                raise SV.ApiError(400, "invalid_request", "The body must be a JSON object.")
            args = (body or {}).get("arguments", (body or {}).get("args"))
            out = await SV.call_tool(k, name, args)
            return JSONResponse(out, headers={"x-hoola-request-id": out["request_id"],
                                              "x-hoola-cost-inr": f"{out['charged_inr']:.6f}"})
        except SV.ApiError as e:
            return _err(e)

    @r.get("/api/hoola-api/v1/balance")
    async def v1_balance(request: Request):
        try:
            k = await _auth(request)
            b = await asyncio.to_thread(SV.balance, k.tenant_id)
            spent = await asyncio.to_thread(SV._spent_today, k.id)
            return {**b, "key_spent_today_micro_inr": spent, "key_daily_limit_micro_inr": k.daily_limit_micro}
        except SV.ApiError as e:
            return _err(e)

    @r.get("/api/hoola-api/v1/usage")
    async def v1_usage(request: Request, days: int = 7):
        try:
            k = await _auth(request)
            return await asyncio.to_thread(SV.usage, k.tenant_id, days)
        except SV.ApiError as e:
            return _err(e)

    # ------------------------------------------------------------ portal (company login)
    async def run(fn, *a, **kw):
        try:
            return await asyncio.to_thread(fn, *a, **kw)
        except SV.ApiError as e:
            raise HTTPException(e.status, e.message)

    @r.get("/api/hoola-portal/me", dependencies=[Depends(require_key)])
    async def p_me(tenant: str = Depends(current_tenant)):
        keys = await run(SV.list_keys, tenant)
        return {"enabled": SV.enabled(), "tenant": tenant, "wallet": await run(SV.balance, tenant),
                "keys": sum(1 for x in keys if not x["revoked"]), "base_url": "/api/hoola-api/v1",
                "topups": "Wallet top-up by UPI is not open yet: ask Hoola to credit your wallet."}

    @r.get("/api/hoola-portal/catalog", dependencies=[Depends(require_key)])
    async def p_catalog():
        return {"tools": CAT.listing()}

    @r.get("/api/hoola-portal/wallet", dependencies=[Depends(require_key)])
    async def p_wallet(tenant: str = Depends(current_tenant)):
        return {**await run(SV.balance, tenant), "invariant": await run(SV.check_invariant, tenant)}

    @r.get("/api/hoola-portal/ledger", dependencies=[Depends(require_key)])
    async def p_ledger(limit: int = 100, tenant: str = Depends(current_tenant)):
        return {"entries": await run(SV.ledger, tenant, limit)}

    @r.get("/api/hoola-portal/usage", dependencies=[Depends(require_key)])
    async def p_usage(days: int = 7, tenant: str = Depends(current_tenant)):
        return await run(SV.usage, tenant, days)

    @r.get("/api/hoola-portal/keys", dependencies=[Depends(require_key)])
    async def p_keys(tenant: str = Depends(current_tenant)):
        return {"keys": await run(SV.list_keys, tenant)}

    @r.post("/api/hoola-portal/keys", dependencies=[Depends(require_key)])
    async def p_key_new(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = dict(body or {})
        return await run(SV.create_key, tenant, str(b.get("name") or ""), b.get("tools"), b.get("rpm"), b.get("rph"),
                         b.get("concurrent"), b.get("daily_limit_inr"))

    @r.delete("/api/hoola-portal/keys/{kid}", dependencies=[Depends(require_key)])
    async def p_key_revoke(kid: str, tenant: str = Depends(current_tenant)):
        return await run(SV.revoke_key, tenant, kid)

    # ------------------------------------------------------------ admin (operator only)
    def _admin(tenant: str) -> None:
        if not _operator(tenant):
            raise HTTPException(403, "Only the Hoola operator can do this.")

    @r.get("/api/hoola-admin/overview", dependencies=[Depends(require_key)])
    async def a_overview(tenant: str = Depends(current_tenant)):
        _admin(tenant)

        def _go():
            from sqlalchemy import func, select

            from ..db import session
            from .models import HapiCall, HapiKey, HapiLedger, HapiWallet, ensure_tables
            ensure_tables()
            with session() as s:
                return {"wallets": s.scalar(select(func.count()).select_from(HapiWallet)) or 0,
                        "float_micro_inr": int(s.scalar(select(func.coalesce(func.sum(HapiWallet.balance_micro), 0))) or 0),
                        "keys": s.scalar(select(func.count()).select_from(HapiKey).where(HapiKey.revoked.is_(False))) or 0,
                        "calls": s.scalar(select(func.count()).select_from(HapiCall)) or 0,
                        "charged_micro_inr": int(s.scalar(select(func.coalesce(func.sum(HapiCall.charged_micro), 0))) or 0),
                        "ledger_rows": s.scalar(select(func.count()).select_from(HapiLedger)) or 0,
                        "enabled": SV.enabled()}
        return await run(_go)

    @r.post("/api/hoola-admin/wallets/{target}/credit", dependencies=[Depends(require_key)])
    async def a_credit(target: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        _admin(tenant)
        b = dict(body or {})
        reason = str(b.get("reason") or "").strip()
        if not reason:
            raise HTTPException(400, "A reason is required.")
        try:
            inr = float(b.get("amount_inr"))
        except (TypeError, ValueError):
            raise HTTPException(400, "amount_inr must be a number.")
        if inr <= 0 or inr > MAX_ADJUST_INR:
            raise HTTPException(400, f"amount_inr must be between 0 and {MAX_ADJUST_INR}.")
        ref = str(b.get("idempotency_key") or uuid.uuid4().hex)[:60]
        out = await run(SV.credit, target, int(round(inr * CAT.INR)), "adjustment", "admin", ref, f"{reason} (by {tenant})")
        return {**out, "invariant": await run(SV.check_invariant, target)}

    @r.post("/api/hoola-admin/wallets/{target}/suspend", dependencies=[Depends(require_key)])
    async def a_suspend(target: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        _admin(tenant)
        flag = bool((body or {}).get("suspended", True))

        def _go():
            from ..db import session
            from .models import HapiWallet, ensure_tables
            ensure_tables()
            with session() as s:
                w = s.get(HapiWallet, target)
                if w is None:
                    w = HapiWallet(tenant_id=target, balance_micro=0)
                    s.add(w)
                w.suspended = flag
            return {"tenant": target, "suspended": flag}
        return await run(_go)

    return r
