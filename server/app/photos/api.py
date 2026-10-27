"""HTTP routes for Google Photos (Profile > Google Photos in the app).

main.py: `app.include_router(photos_api.make_router(require_key, current_tenant))`, and in /auth/google/callback
send states starting with "gph_" to `await photos_api.finish_page(request)`.
"""
from __future__ import annotations

import asyncio
import html as _h

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse

from ..config import get_settings


def _page(address: str | None, error: str = "") -> HTMLResponse:
    deep = f"{get_settings().app_redirect_scheme}://photos?ok={0 if error else 1}"
    msg = (f"<h2>Google Photos Santosh se juda! ✅</h2><p>{_h.escape(address or '')}</p>" if not error else
           f"<h3>Google Photos nahi juda</h3><p>{_h.escape(error)}</p>")
    return HTMLResponse(f"""<!doctype html><meta name=viewport content="width=device-width,initial-scale=1">
<body style="font-family:system-ui;text-align:center;padding:40px;background:#f3eefb">{msg}
<p><a href="{deep}" style="display:inline-block;background:#6d3fe0;color:#fff;padding:14px 22px;border-radius:14px;text-decoration:none;font-weight:700">App kholiye</a></p>
<script>setTimeout(function(){{location.href={deep!r}}},600);</script></body>""", status_code=400 if error else 200)


async def finish_page(request: Request) -> HTMLResponse:
    from . import accounts as pa
    from .client import PhotosError
    if request.query_params.get("error"):
        return _page(None, request.query_params["error"])
    try:
        view = await asyncio.to_thread(pa.finish_link, request.query_params.get("code", ""),
                                       request.query_params.get("state", ""))
    except PhotosError as e:
        return _page(None, str(e))
    return _page(view["address"])


def state_for(tenant: str) -> dict:
    from . import accounts as pa
    from .service import LIMITS
    return {"accounts": pa.views(tenant), "can_link": pa.oauth_ready(), "limits": LIMITS}


def make_router(require_key, current_tenant) -> APIRouter:
    r = APIRouter()

    @r.get("/api/photos/accounts", dependencies=[Depends(require_key)])
    def photos_accounts(tenant: str = Depends(current_tenant)):
        return state_for(tenant)

    @r.get("/api/photos/link", dependencies=[Depends(require_key)])
    def photos_link(login_hint: str = "", tenant: str = Depends(current_tenant)):
        from . import accounts as pa
        from .client import PhotosError
        try:
            return {"url": pa.start_link(tenant, login_hint)}
        except PhotosError as e:
            raise HTTPException(503, str(e))

    @r.delete("/api/photos/accounts/{key}", dependencies=[Depends(require_key)])
    def photos_remove(key: str, tenant: str = Depends(current_tenant)):
        from . import accounts as pa
        if not pa.remove(tenant, key):
            raise HTTPException(404, "Photos account not found")
        return state_for(tenant)

    @r.get("/api/photos/picks/{pick_id}", dependencies=[Depends(require_key)])
    async def photos_pick_status(pick_id: str, tenant: str = Depends(current_tenant)):
        from . import service as ps
        from .client import PhotosError
        try:
            return await asyncio.to_thread(ps.refresh_pick, tenant, pick_id)
        except PhotosError as e:
            raise HTTPException(404, str(e))

    return r
