"""Santosh Commerce MCP server.

One MCP endpoint that lets Santosh — or any MCP client the user connects (Claude, ChatGPT, Gemini, their own
agent) — shop across MVP Bazar shops, the ONDC open network, Shopify brand stores and Flipkart search, then pay by
UPI and track orders.

Run:  python -m app.commerce.mcp_server            (streamable HTTP on :8100/mcp)
Auth: per-user bearer tokens from POST /v1/users/{id}/mcp-tokens (stored hashed).

Money safety: place_order needs an unexpired quote and the user's confirmation (MCP elicitation when the client
supports it, otherwise user_confirmed=true after showing the quote). It returns a UPI intent: the user pays in their
own UPI app with their own PIN. Santosh never sees a PIN, card number or OTP.
"""
from __future__ import annotations

import hashlib
import secrets
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

import anyio.to_thread
from mcp.server.auth.settings import AuthSettings
from mcp.server.mcpserver import Context, MCPServer
from mcp.types import ToolAnnotations
from pydantic import BaseModel, Field
from sqlalchemy import select

from ..config import get_settings
from ..connectors.base import ToolError
from ..db import McpToken, User, session_factory
from .service import CommerceService

INSTRUCTIONS = """Santosh Commerce: shop for an Indian user across local MVP Bazar shops, the ONDC open network,
Shopify brand stores and Flipkart (search + link only).
Flow: search_products -> add_to_cart -> get_quote (shows the all-in price, seller, returns, delivery) -> show the quote
to the user and get a clear yes -> place_order -> give the user the UPI link to pay with their own PIN ->
order_status. Never place an order the user has not seen and approved. One seller per cart. Prices are in rupees.
Flipkart and Shopify items finish on the store's own checkout (use get_buy_link / the checkout_url)."""


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def issue_token(db, user_id: str, label: str = "") -> str:
    token = "snt_mcp_" + secrets.token_urlsafe(32)
    db.add(McpToken(user_id=user_id, token_hash=hash_token(token), label=label[:80]))
    db.commit()
    return token


class DbTokenVerifier:
    async def verify_token(self, token: str):
        from mcp.server.auth.provider import AccessToken

        def lookup():
            with session_factory() as db:
                row = db.scalars(select(McpToken).where(McpToken.token_hash == hash_token(token), McpToken.revoked.is_(False))).first()
                return (row.user_id, list(row.scopes), row.label) if row else None
        found = await anyio.to_thread.run_sync(lookup)
        if not found:
            return None
        uid, scopes, label = found
        return AccessToken(token=token, client_id=label or "mcp-client", scopes=scopes, subject=uid,
                           resource=get_settings().public_base_url.rstrip("/") + "/mcp")


class OrderConfirmation(BaseModel):
    confirm: bool = Field(description="Yes, place this order and open UPI to pay")


def _current_user_id() -> str:
    from mcp.server.auth.middleware.auth_context import get_access_token
    tok = get_access_token()
    if tok is None or not tok.subject:
        raise ToolError("Not signed in to Santosh.")
    return tok.subject


def _client_id() -> str:
    from mcp.server.auth.middleware.auth_context import get_access_token
    tok = get_access_token()
    return tok.client_id if tok else ""


def build_server(user_resolver=None, service_factory=None):
    """user_resolver / service_factory are injectable for tests."""
    st = get_settings()
    resolve = user_resolver or _current_user_id
    make = service_factory or (lambda db: CommerceService(db, get_settings()))
    base = st.public_base_url.rstrip("/")
    kwargs: dict[str, Any] = {}
    if user_resolver is None:
        kwargs = {"token_verifier": DbTokenVerifier(),
                  "auth": AuthSettings(issuer_url=base, resource_server_url=base + "/mcp", validate_token_resource=False)}
    srv = MCPServer("santosh-commerce", title="Santosh Commerce", instructions=INSTRUCTIONS, version="0.4.0",
                    website_url="https://www.ainewtika.com", **kwargs)

    @contextmanager
    def svc() -> Iterator[tuple[CommerceService, User]]:
        db = session_factory()
        try:
            user = db.get(User, resolve())
            if user is None:
                raise ToolError("Santosh account not found.")
            yield make(db), user
        finally:
            db.close()

    ro = ToolAnnotations(readOnlyHint=True, openWorldHint=True)
    write = ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=True, openWorldHint=True)
    money = ToolAnnotations(readOnlyHint=False, destructiveHint=True, idempotentHint=True, openWorldHint=True)

    @srv.tool(annotations=ro)
    def list_sources() -> dict[str, Any]:
        """Where Santosh can shop for this user and how each source finishes the purchase."""
        with svc() as (s, _):
            return {"sources": s.sources()}

    @srv.tool(annotations=ro)
    def search_products(query: str, pincode: str = "", sources: list[str] | None = None,
                        max_price_rupees: float | None = None, limit: int = 8) -> dict[str, Any]:
        """Search products across sources (bazar, ondc, shopify, flipkart), cheapest first, for delivery to a PIN code.
        Each result has an offer_id to use with add_to_cart / get_product / get_buy_link."""
        with svc() as (s, u):
            return s.search(u, query, pincode, sources, max_price_rupees, max(1, min(limit, 20)))

    @srv.tool(annotations=ro)
    def get_product(offer_id: str) -> dict[str, Any]:
        """Full details of a search result: seller, returns, delivery, country of origin, customer care."""
        with svc() as (s, u):
            return s.get_offer(u, offer_id)

    @srv.tool(annotations=ro)
    def get_buy_link(offer_id: str) -> dict[str, Any]:
        """Store link for items bought on the store's own app/checkout (Flipkart, brand stores)."""
        with svc() as (s, u):
            return s.buy_link(u, offer_id)

    @srv.tool(annotations=write)
    def add_to_cart(offer_id: str, quantity: int = 1, cart_id: str = "") -> dict[str, Any]:
        """Add a product to the cart for its seller (one seller per cart). Returns the cart."""
        with svc() as (s, u):
            return s.add_to_cart(u, offer_id, quantity, cart_id or None)

    @srv.tool(annotations=write)
    def update_cart(cart_id: str, offer_id: str, quantity: int) -> dict[str, Any]:
        """Change a quantity; 0 removes the item."""
        with svc() as (s, u):
            return s.update_cart(u, cart_id, offer_id, quantity)

    @srv.tool(annotations=ro)
    def view_cart(cart_id: str) -> dict[str, Any]:
        """Show a cart."""
        with svc() as (s, u):
            return s.view_cart(u, cart_id)

    @srv.tool(annotations=ro)
    def list_carts() -> dict[str, Any]:
        """Open carts."""
        with svc() as (s, u):
            return {"carts": s.list_carts(u)}

    @srv.tool(annotations=write)
    def get_quote(cart_id: str, delivery_pincode: str = "", delivery_address_line: str = "") -> dict[str, Any]:
        """Re-check price and stock with the seller and return the all-in price (items, delivery, packing, taxes),
        seller, returns and delivery time. Valid for 10 minutes. Show it to the user before place_order."""
        addr = {k: v for k, v in {"pincode": delivery_pincode, "line1": delivery_address_line}.items() if v}
        with svc() as (s, u):
            return s.quote(u, cart_id, addr)

    @srv.tool(annotations=money)
    async def place_order(quote_id: str, idempotency_key: str, ctx: Context, user_confirmed: bool = False) -> dict[str, Any]:
        """Place the order for an approved quote and get the UPI payment link. The user pays in their own UPI app.
        Set user_confirmed=true only after the user explicitly said yes to the exact quote shown."""
        def load():
            with svc() as (s, u):
                from ..db import CommerceCart, CommerceQuote
                q = s.db.get(CommerceQuote, quote_id)
                if q is None or q.user_id != u.id:
                    raise ToolError("Quote not found.")
                return s.quote_view(q, s.db.get(CommerceCart, q.cart_id))
        view = await anyio.to_thread.run_sync(load)
        surface = ""
        try:
            res = await ctx.elicit(view.get("confirm_text", "Place this order?"), OrderConfirmation)
            if res.action != "accept" or not res.data.confirm:
                return {"placed": False, "message": "Not ordered. The user did not confirm."}
            surface = "mcp_elicitation"
        except Exception:  # client without elicitation support
            if not user_confirmed:
                return {"placed": False, "needs_user_confirmation": True, "quote": view,
                        "message": "Show this quote to the user and call place_order again with user_confirmed=true only "
                                   "after they clearly agree."}
            surface = "mcp_user_confirmed"

        def go():
            with svc() as (s, u):
                return s.confirm(u, quote_id, surface, client_id=_client_id_safe(), idempotency_key=idempotency_key)
        return {"placed": True, **(await anyio.to_thread.run_sync(go))}

    @srv.tool(annotations=ro)
    def order_status(order_id: str) -> dict[str, Any]:
        """Latest status from the seller (payment, packed, shipped, out for delivery, delivered)."""
        with svc() as (s, u):
            return s.status(u, order_id)

    @srv.tool(annotations=ro)
    def list_orders(open_only: bool = False) -> dict[str, Any]:
        """Recent orders."""
        with svc() as (s, u):
            return {"orders": s.list_orders(u, open_only)}

    @srv.tool(annotations=money)
    def cancel_order(order_id: str, reason: str = "") -> dict[str, Any]:
        """Cancel an order (before shipping). Refunds go back to the user's UPI account."""
        with svc() as (s, u):
            return s.cancel(u, order_id, reason)

    @srv.tool(annotations=write)
    def request_return(order_id: str, item: str, quantity: int = 1, reason: str = "") -> dict[str, Any]:
        """Ask the seller to take back a delivered item (if it is returnable)."""
        with svc() as (s, u):
            return s.return_item(u, order_id, item, quantity, reason)

    def _client_id_safe() -> str:
        try:
            return _client_id()
        except Exception:
            return ""

    return srv


def main() -> None:  # pragma: no cover - entry point
    import uvicorn

    from ..db import init_engine
    init_engine()
    srv = build_server()
    uvicorn.run(srv.streamable_http_app(host="0.0.0.0"), host="0.0.0.0", port=8100)


if __name__ == "__main__":  # pragma: no cover
    main()
