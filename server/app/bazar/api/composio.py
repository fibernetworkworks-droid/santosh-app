"""v0.276 COMPOSIO routes: her app list / connect / disconnect (app key), the sign-in callback and Composio's signed
"connection expired" webhook (both public; the callback trusts only its own signed state, the webhook only a valid
HMAC signature)."""
from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse

from .. import service
from ..connectors.base import ToolError


def make_router(require_key, current_tenant) -> APIRouter:
    r = APIRouter()

    def _do(fn, *a):
        try:
            return fn(*a)
        except ToolError as e:
            raise HTTPException(400, str(e))

    @r.get("/api/composio/apps", dependencies=[Depends(require_key)])
    async def apps(q: str = "", category: str = "", offset: int = 0, limit: int = 40,
                   tenant: str = Depends(current_tenant)):
        return await asyncio.to_thread(_do, service.composio_apps, tenant, q, category, offset, limit)

    @r.post("/api/composio/apps/{toolkit}/connect", dependencies=[Depends(require_key)])
    async def connect(toolkit: str, tenant: str = Depends(current_tenant)):
        return await asyncio.to_thread(_do, service.composio_connect, tenant, toolkit, "")

    @r.post("/api/composio/apps/{toolkit}/key", dependencies=[Depends(require_key)])
    async def key(toolkit: str, body: dict, tenant: str = Depends(current_tenant)):
        # her own key for that app goes straight to Composio; never logged, never stored in Hoola
        values = body.get("values") if isinstance(body, dict) else None
        return await asyncio.to_thread(_do, service.composio_key, tenant, toolkit, values or {})

    @r.delete("/api/composio/apps/{toolkit}", dependencies=[Depends(require_key)])
    async def remove(toolkit: str, tenant: str = Depends(current_tenant)):
        return {"removed": await asyncio.to_thread(_do, service.composio_remove, tenant, toolkit)}

    @r.get("/bazar/composio/callback")
    async def callback(st: str = ""):
        # v0.774 one done page for the phone AND the web console (bazar/donepage.py)
        from ...config import get_settings
        from .. import donepage
        name = ""
        try:
            name, ok = await asyncio.to_thread(service.composio_callback, st)
            title = f"{name} is connected" if ok else f"{name} sign-in did not finish"
            detail = (f"Hoola can now work in {name} for you. Reads run straight away; sending, deleting and payments "
                      f"always wait for your tap." if ok else "Nothing was linked. Please try again from Connectors.")
        except ToolError as e:
            ok, title, detail = False, "Not connected", str(e)
        link = f"{get_settings().app_redirect_scheme}://bazar?linked={'1' if ok else '0'}"
        return HTMLResponse(donepage.render(ok, title, detail, link, name))

    @r.post("/bazar/composio/webhook")
    async def webhook(request: Request):
        from .. import composio
        raw = await request.body()
        h = request.headers
        if not composio.verify_webhook(raw, h.get("webhook-id", ""), h.get("webhook-timestamp", ""),
                                       h.get("webhook-signature", "")):
            raise HTTPException(401, "bad signature")
        try:
            ev = json.loads(raw)
        except ValueError:
            raise HTTPException(400, "bad json")
        if ev.get("type") == "composio.connected_account.expired":
            ca = str((ev.get("data") or {}).get("id") or "")
            if ca:
                await asyncio.to_thread(service.composio_expired, ca)
        return {"ok": True}

    return r
