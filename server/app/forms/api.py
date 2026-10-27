"""HTTP routes for Profile > Google Forms, and the page shown after Google sign-in returns."""
from __future__ import annotations

import asyncio
import html as _h

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse

from ..config import get_settings


def make_router(require_key, current_tenant) -> APIRouter:
    r = APIRouter()

    @r.get("/api/forms/accounts", dependencies=[Depends(require_key)])
    def forms_accounts(tenant: str = Depends(current_tenant)):
        from . import accounts as fa
        from . import service as fs
        return {"accounts": fa.views(tenant), "can_link": fa.oauth_ready(), "recent": fs.recent(tenant),
                "watching": fs.watches(tenant)}

    @r.get("/api/forms/link", dependencies=[Depends(require_key)])
    def forms_link(login_hint: str = "", tenant: str = Depends(current_tenant)):
        from . import accounts as fa
        from .client import FormError
        try:
            return {"url": fa.start_link(tenant, login_hint)}
        except FormError as e:
            raise HTTPException(503, str(e))

    @r.delete("/api/forms/accounts/{key}", dependencies=[Depends(require_key)])
    def forms_remove(key: str, tenant: str = Depends(current_tenant)):
        from . import accounts as fa
        from . import service as fs
        if not fa.remove(tenant, key):
            raise HTTPException(404, "Account not found")
        return {"accounts": fa.views(tenant), "can_link": fa.oauth_ready(), "recent": fs.recent(tenant),
                "watching": fs.watches(tenant)}

    return r


def _page(address: str | None, error: str = "") -> HTMLResponse:
    scheme = get_settings().app_redirect_scheme
    deep = f"{scheme}://forms?ok={0 if error else 1}"
    msg = (f"<h2>Google Forms Santosh se jude! ✅</h2><p>{_h.escape(address or '')}</p>" if not error else
           f"<h3>Google Forms nahi jude</h3><p>{_h.escape(error)}</p>")
    return HTMLResponse(f"""<!doctype html><meta name=viewport content="width=device-width,initial-scale=1">
<body style="font-family:system-ui;text-align:center;padding:40px;background:#f3eefb">{msg}
<p><a href="{deep}" style="display:inline-block;background:#6d3fe0;color:#fff;padding:14px 22px;border-radius:14px;text-decoration:none;font-weight:700">App kholiye</a></p>
<script>setTimeout(function(){{location.href={deep!r}}},600);</script></body>""", status_code=400 if error else 200)


async def finish_page(request: Request) -> HTMLResponse:
    """Called from /auth/google/callback when the state starts with "gfm_"."""
    from . import accounts as fa
    from .client import FormError
    if request.query_params.get("error"):
        return _page(None, request.query_params["error"])
    try:
        view = await asyncio.to_thread(fa.finish_link, request.query_params.get("code", ""),
                                       request.query_params.get("state", ""))
    except FormError as e:
        return _page(None, str(e))
    return _page(view["address"])
