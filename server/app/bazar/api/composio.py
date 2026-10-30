"""v0.276 COMPOSIO routes: her app list / connect / disconnect (app key), the sign-in callback and Composio's signed
"connection expired" webhook (both public; the callback trusts only its own signed state, the webhook only a valid
HMAC signature)."""
from __future__ import annotations

import asyncio
import json
from html import escape

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
    async def apps(tenant: str = Depends(current_tenant)):
        return await asyncio.to_thread(_do, service.composio_apps, tenant)

    @r.post("/api/composio/apps/{toolkit}/connect", dependencies=[Depends(require_key)])
    async def connect(toolkit: str, tenant: str = Depends(current_tenant)):
        return await asyncio.to_thread(_do, service.composio_connect, tenant, toolkit, "")

    @r.delete("/api/composio/apps/{toolkit}", dependencies=[Depends(require_key)])
    async def remove(toolkit: str, tenant: str = Depends(current_tenant)):
        return {"removed": await asyncio.to_thread(_do, service.composio_remove, tenant, toolkit)}

    @r.get("/bazar/composio/callback")
    async def callback(st: str = ""):
        from ...config import get_settings
        try:
            name, ok = await asyncio.to_thread(service.composio_callback, st)
            msg = f"{escape(name)} jud gaya." if ok else f"{escape(name)} ka sign-in abhi poora nahi hua. Dobara try kijiye."
        except ToolError as e:
            msg, ok = escape(str(e)), False
        link = f"{get_settings().app_redirect_scheme}://bazar?linked={'1' if ok else '0'}"
        return HTMLResponse(f"""<!doctype html><meta name=viewport content="width=device-width,initial-scale=1">
<body style="font-family:sans-serif;padding:32px;text-align:center"><h2>{'✅' if ok else '⚠️'} {msg}</h2>
<p><a href="{link}" style="font-size:18px">Hoola par wapas jaiye</a></p><script>setTimeout(()=>location.href="{link}",800)</script>""")

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
