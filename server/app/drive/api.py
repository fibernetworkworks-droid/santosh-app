"""HTTP routes for Google Drive (Profile > Google Drive in the app).

main.py: `app.include_router(drive_api.make_router(require_key, current_tenant))`, and in /auth/google/callback
send states starting with "gdr_" to `await drive_api.finish_page(request)`.
"""
from __future__ import annotations

import asyncio
import html as _h

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse

from ..config import get_settings


def _page(address: str | None, error: str = "") -> HTMLResponse:
    scheme = get_settings().app_redirect_scheme
    deep = f"{scheme}://drive?ok={0 if error else 1}"
    msg = (f"<h2>Google Drive Santosh se juda! ✅</h2><p>{_h.escape(address or '')}</p>" if not error else
           f"<h3>Drive nahi juda</h3><p>{_h.escape(error)}</p>")
    return HTMLResponse(f"""<!doctype html><meta name=viewport content="width=device-width,initial-scale=1">
<body style="font-family:system-ui;text-align:center;padding:40px;background:#f3eefb">{msg}
<p><a href="{deep}" style="display:inline-block;background:#6d3fe0;color:#fff;padding:14px 22px;border-radius:14px;text-decoration:none;font-weight:700">App kholiye</a></p>
<script>setTimeout(function(){{location.href={deep!r}}},600);</script></body>""", status_code=400 if error else 200)


async def finish_page(request: Request) -> HTMLResponse:
    from . import accounts as da
    from .client import DriveError
    if request.query_params.get("error"):
        return _page(None, request.query_params["error"])
    try:
        view = await asyncio.to_thread(da.finish_link, request.query_params.get("code", ""),
                                       request.query_params.get("state", ""))
    except DriveError as e:
        return _page(None, str(e))
    return _page(view["address"])


def state_for(tenant: str) -> dict:
    from . import accounts as da
    from . import service as ds
    out = {"accounts": da.views(tenant), "can_link": da.oauth_ready(), "storage": [], "recent": ds.recent(tenant, 10)}
    if out["accounts"]:
        try:
            out["storage"] = ds.storage(tenant)["storage"]
        except Exception as e:
            out["error"] = str(e)
    return out


def make_router(require_key, current_tenant) -> APIRouter:
    r = APIRouter()

    @r.get("/api/drive/accounts", dependencies=[Depends(require_key)])
    def drive_accounts(tenant: str = Depends(current_tenant)):
        return state_for(tenant)

    @r.get("/api/drive/link", dependencies=[Depends(require_key)])
    def drive_link(login_hint: str = "", tenant: str = Depends(current_tenant)):
        from . import accounts as da
        from .client import DriveError
        try:
            return {"url": da.start_link(tenant, login_hint)}
        except DriveError as e:
            raise HTTPException(503, str(e))

    @r.delete("/api/drive/accounts/{key}", dependencies=[Depends(require_key)])
    def drive_remove(key: str, tenant: str = Depends(current_tenant)):
        from . import accounts as da
        if not da.remove(tenant, key):
            raise HTTPException(404, "Drive account not found")
        return state_for(tenant)

    return r
