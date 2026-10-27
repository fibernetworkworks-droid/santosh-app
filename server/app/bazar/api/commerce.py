"""Santosh Shopping routes: orders and Commerce MCP tokens (signed-in app), ONDC network callbacks (public, every
callback signature-checked against the sender's registry key) and the Commerce MCP server at /mcp/commerce.

Mounted from app/main.py with ``mount(app, require_key, current_tenant)``.
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import select

from ..commerce.mcp_server import MOUNT_PATH, RateLimit, issue_token
from ..commerce.ondc import crypto
from ..commerce.service import CommerceService
from ..config import get_settings
from ..connectors.base import ToolError
from ..db import McpToken, session_factory

log = logging.getLogger("santosh.bazar.commerce")

ON_ACTIONS = {"on_search", "on_select", "on_init", "on_confirm", "on_status", "on_track", "on_cancel", "on_update",
              "on_rating", "on_support"}


class TokenIn(BaseModel):
    label: str = Field(default="My AI assistant", max_length=80)


def _db():
    s = session_factory()
    try:
        yield s
        s.commit()
    except Exception:
        s.rollback()
        raise
    finally:
        s.close()


def _user(s, tenant: str):
    from ..service import ensure_user
    return ensure_user(s, tenant)


def app_router(require_key, current_tenant) -> APIRouter:
    r = APIRouter(prefix="/api/bazar/commerce", tags=["commerce"], dependencies=[Depends(require_key)])

    @r.get("/orders")
    def orders(open_only: bool = False, tenant: str = Depends(current_tenant), s=Depends(_db)):
        return {"orders": CommerceService(s, get_settings()).list_orders(_user(s, tenant), open_only, 30)}

    @r.get("/orders/{order_id}")
    def order_status(order_id: str, tenant: str = Depends(current_tenant), s=Depends(_db)):
        try:
            return CommerceService(s, get_settings()).status(_user(s, tenant), order_id)
        except ToolError as e:
            raise HTTPException(404, str(e))

    @r.post("/mcp-tokens")
    def create_mcp_token(body: TokenIn, tenant: str = Depends(current_tenant), s=Depends(_db)):
        """Token for connecting Claude / ChatGPT / any MCP client to Santosh Shopping. Shown once, stored hashed."""
        _user(s, tenant)
        s.flush()
        tok = issue_token(s, tenant, body.label)
        return {"token": tok, "mcp_url": get_settings().public_base_url.rstrip("/") + MOUNT_PATH, "label": body.label,
                "header": "Authorization: Bearer <token>",
                "note": "Shown only once. Anyone with this token can search and build carts as you; every order still "
                        "needs your yes on the exact price and your own UPI PIN."}

    @r.get("/mcp-tokens")
    def list_mcp_tokens(tenant: str = Depends(current_tenant), s=Depends(_db)):
        rows = s.scalars(select(McpToken).where(McpToken.user_id == tenant).order_by(McpToken.created_at.desc())).all()
        return {"tokens": [{"id": t.id, "label": t.label, "created_at": t.created_at.isoformat(timespec="minutes"),
                            "revoked": t.revoked} for t in rows],
                "mcp_url": get_settings().public_base_url.rstrip("/") + MOUNT_PATH}

    @r.delete("/mcp-tokens/{tid}")
    def revoke_mcp_token(tid: str, tenant: str = Depends(current_tenant), s=Depends(_db)):
        t = s.get(McpToken, tid)
        if not t or t.user_id != tenant:
            raise HTTPException(404, "Token not found")
        t.revoked = True
        return {"revoked": tid}

    return r


# ------------------------------------------------------------------ ONDC network (public)
public = APIRouter(tags=["ondc"])


@public.get("/ondc-site-verification.html", response_class=HTMLResponse)
def ondc_site_verification():
    st = get_settings()
    if not (st.ondc_request_id and st.ondc_signing_private_key):
        raise HTTPException(404, "Not configured")
    return HTMLResponse(crypto.site_verification_html(st.ondc_request_id, st.ondc_signing_private_key))


class ChallengeIn(BaseModel):
    subscriber_id: str
    challenge: str


@public.post("/ondc/on_subscribe")
def ondc_on_subscribe(body: ChallengeIn):
    st = get_settings()
    if body.subscriber_id != st.ondc_subscriber_id:
        raise HTTPException(400, "Unknown subscriber")
    try:
        answer = crypto.decrypt_challenge(body.challenge, st.ondc_encryption_private_key, st.ondc_registry_public_key)
    except Exception as e:
        raise HTTPException(400, "Could not decrypt the challenge") from e
    return {"answer": answer}


@public.post("/ondc/{action}")
async def ondc_callback(action: str, request: Request):
    if action not in ON_ACTIONS:
        return JSONResponse({"message": {"ack": {"status": "NACK"}}, "error": {"code": "10002", "message": "Unsupported action"}},
                            status_code=400)
    body = await request.body()
    auth = request.headers.get("authorization", "")

    def handle() -> dict[str, Any]:
        from ..commerce.providers.ondc import make_buyer
        with session_factory() as s:
            return make_buyer(s, get_settings()).receive(action, auth, body)
    import asyncio
    try:
        res = await asyncio.to_thread(handle)
    except ToolError as e:  # keys not configured
        res = {"message": {"ack": {"status": "NACK"}}, "error": {"code": "10001", "message": str(e)}}
    ok = ((res.get("message") or {}).get("ack") or {}).get("status") == "ACK"
    return JSONResponse(res, status_code=200 if ok else 401)


# ------------------------------------------------------------------ Commerce MCP server
class McpMount:
    """ASGI app at /mcp: the per-token rate limit, then the MCP server built fresh at each app start (the SDK's
    session manager runs once per instance). Before startup it answers 503."""

    def __init__(self, per_minute: int):
        self.inner = None
        self.limited = RateLimit(self._call, per_minute)

    async def _call(self, scope, receive, send):
        if self.inner is None:
            await send({"type": "http.response.start", "status": 503, "headers": [(b"content-type", b"text/plain")]})
            await send({"type": "http.response.body", "body": b"Santosh Commerce MCP is starting"})
            return
        await self.inner(scope, receive, send)

    async def __call__(self, scope, receive, send):
        await self.limited(scope, receive, send)

    @asynccontextmanager
    async def running(self):
        from ..commerce.mcp_server import build_server
        inner = build_server().streamable_http_app(streamable_http_path=MOUNT_PATH.removeprefix("/mcp"), host="0.0.0.0")
        async with inner.router.lifespan_context(inner):
            self.inner = inner
            try:
                yield
            finally:
                self.inner = None


def mount(app: FastAPI, require_key, current_tenant) -> McpMount | None:
    app.include_router(public)
    app.include_router(app_router(require_key, current_tenant))
    try:
        import mcp.server.mcpserver  # noqa: F401  (mcp>=2)
    except ImportError:
        log.warning("Commerce MCP not mounted: needs mcp>=2 (pip install -U 'mcp>=2.2')")
        return None
    m = McpMount(get_settings().commerce_mcp_rate_per_minute)
    app.mount("/mcp", m)
    outer = app.router.lifespan_context

    @asynccontextmanager
    async def lifespan(a):
        async with m.running():
            async with outer(a) as state:
                yield state
    app.router.lifespan_context = lifespan
    app.state.commerce_mcp = m
    return m
