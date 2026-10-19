"""Shopify brand stores (many Indian D2C brands) via each store's official Storefront MCP endpoint
(https://{store}/api/mcp): catalog search and cart. Payment happens on the store's own checkout page
(handoff), so Santosh never takes card or UPI details for these stores.
"""
from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from ...connectors.base import ToolError
from ...connectors.mcp_remote import McpHttpRemote, RemoteTools
from ...db import CommerceCart, CommerceOrder, User
from ..ondc.beckn import paise
from .base import PlaceResult, QuoteResult


def _data(res: dict[str, Any]) -> Any:
    if res.get("is_error"):
        raise ToolError(res.get("text") or "The store returned an error.")
    if res.get("data") is not None:
        return res["data"]
    try:
        return json.loads(res.get("text") or "{}")
    except ValueError:
        return {}


class FakeStorefront:
    """Sandbox stand-in with the same tool names as Shopify's Storefront MCP."""

    PRODUCTS = [
        {"product_id": "gid://shopify/Product/101", "title": "Cotton kurta — indigo", "url": "https://demo-kurta.example/products/indigo",
         "image_url": "", "description": "Handloom cotton, made in India",
         "price_range": {"min": "1299.00", "max": "1299.00", "currency": "INR"},
         "variants": [{"variant_id": "gid://shopify/ProductVariant/1011", "title": "M", "price": "1299.00", "currency": "INR", "available": True},
                      {"variant_id": "gid://shopify/ProductVariant/1012", "title": "L", "price": "1299.00", "currency": "INR", "available": True}]},
        {"product_id": "gid://shopify/Product/102", "title": "Cold-pressed coconut oil 500 ml", "url": "https://demo-kurta.example/products/coconut-oil",
         "image_url": "", "description": "Kerala, glass bottle",
         "price_range": {"min": "349.00", "max": "349.00", "currency": "INR"},
         "variants": [{"variant_id": "gid://shopify/ProductVariant/1021", "title": "500 ml", "price": "349.00", "currency": "INR", "available": True}]},
    ]

    def __init__(self) -> None:
        self.carts: dict[str, list[dict[str, Any]]] = {}

    def list_tools(self) -> list[dict[str, Any]]:
        return [{"name": n, "description": "", "input_schema": {"type": "object"}}
                for n in ("search_shop_catalog", "get_product_details", "update_cart", "get_cart", "search_shop_policies_and_faqs")]

    def _cart(self, cid: str) -> dict[str, Any]:
        lines = self.carts[cid]
        by = {v["variant_id"]: (p, v) for p in self.PRODUCTS for v in p["variants"]}
        sub = sum(float(by[ln["merchandise_id"]][1]["price"]) * ln["quantity"] for ln in lines)
        ship = 0.0 if sub >= 999 else 79.0
        return {"cart": {"id": cid, "checkout_url": f"https://demo-kurta.example/checkouts/{cid}",
                         "lines": [{"merchandise_id": ln["merchandise_id"], "quantity": ln["quantity"],
                                    "title": by[ln["merchandise_id"]][0]["title"],
                                    "cost": {"total_amount": {"amount": f"{float(by[ln['merchandise_id']][1]['price']) * ln['quantity']:.2f}",
                                                              "currency": "INR"}}} for ln in lines],
                         "cost": {"subtotal_amount": {"amount": f"{sub:.2f}", "currency": "INR"},
                                  "total_amount": {"amount": f"{sub + ship:.2f}", "currency": "INR"},
                                  "shipping_amount": {"amount": f"{ship:.2f}", "currency": "INR"}}}}

    def call_tool(self, name: str, args: dict[str, Any]) -> dict[str, Any]:
        if name == "search_shop_catalog":
            q = str(args.get("query", "")).lower().split()
            hits = [p for p in self.PRODUCTS if not q or any(w in p["title"].lower() for w in q)]
            return {"is_error": False, "data": {"products": hits}}
        if name == "update_cart":
            cid = args.get("cart_id") or f"c{len(self.carts) + 1}"
            self.carts.setdefault(cid, [])
            for ln in args.get("lines", []):
                self.carts[cid] = [x for x in self.carts[cid] if x["merchandise_id"] != ln["merchandise_id"]] + \
                    ([ln] if ln.get("quantity", 0) > 0 else [])
            return {"is_error": False, "data": self._cart(cid)}
        if name == "get_cart":
            return {"is_error": False, "data": self._cart(args["cart_id"])}
        return {"is_error": True, "text": f"unknown tool {name}"}


_FAKE = FakeStorefront()


class ShopifyProvider:
    source = "shopify"
    label = "Brand stores (Shopify)"

    def __init__(self, settings: Any, remotes: dict[str, RemoteTools] | None = None):
        self.s = settings
        stores = [x.strip() for x in (settings.shopify_stores or "").split(",") if x.strip()]
        if remotes is not None:
            self.remotes = remotes
        elif stores:
            self.remotes = {st: McpHttpRemote(f"https://{st}/api/mcp", "") for st in stores}
        elif settings.commerce_sandbox_feeds:
            self.remotes = {"demo-kurta.example": _FAKE}
        else:
            self.remotes = {}

    def available(self) -> bool:
        return bool(self.remotes)

    def search(self, db: Session, user: User, query: str, pincode: str, limit: int) -> list[dict[str, Any]]:
        out = []
        for store, r in self.remotes.items():
            try:
                data = _data(r.call_tool("search_shop_catalog", {"query": query, "context": f"Shopper in India, PIN {pincode}"}))
            except Exception:
                continue
            for p in (data.get("products") or [])[:limit]:
                for v in (p.get("variants") or [])[:3]:
                    title = p.get("title", "") + ("" if v.get("title") in (None, "", "Default Title") else f" ({v['title']})")
                    out.append({
                        "source": self.source, "ref": {"store": store, "product_id": p.get("product_id"), "variant_id": v.get("variant_id")},
                        "name": title, "brand": store, "description": p.get("description", ""), "image": p.get("image_url", ""),
                        "price_paise": paise(v.get("price") or (p.get("price_range") or {}).get("min")),
                        "mrp_paise": paise(v.get("compare_at_price") or v.get("price") or 0),
                        "pack": "", "in_stock": bool(v.get("available", True)), "max_qty": 10,
                        "seller": {"name": store, "key": f"shopify::{store}", "city": "", "network": "Shopify store"},
                        "delivery": {}, "returnable": None, "return_window": "see store policy", "cancellable": None,
                        "cod": None, "country_of_origin": "", "customer_care": f"https://{store}/policies", "url": p.get("url", ""),
                        "buy_mode": "handoff", "sponsored": False,
                    })
        return out[:limit]

    def quote(self, db: Session, user: User, cart: CommerceCart, address: dict[str, Any]) -> QuoteResult:
        store = cart.seller_key.split("::", 1)[1]
        r = self.remotes.get(store)
        if r is None:
            raise ToolError("This store is no longer connected.")
        lines_in = [{"merchandise_id": ln["ref"]["variant_id"], "quantity": int(ln["qty"])} for ln in cart.lines]
        data = _data(r.call_tool("update_cart", {"cart_id": cart.meta.get("store_cart_id"), "lines": lines_in}))
        c = data.get("cart") or data
        cart.meta = {**cart.meta, "store_cart_id": c.get("id")}
        cost = c.get("cost") or {}
        total = paise((cost.get("total_amount") or {}).get("amount"))
        breakup = [{"title": ln.get("title", "item") + f" × {ln.get('quantity', 1)}", "kind": "item",
                    "amount_paise": paise(((ln.get("cost") or {}).get("total_amount") or {}).get("amount"))} for ln in c.get("lines", [])]
        ship = paise((cost.get("shipping_amount") or {}).get("amount"))
        if ship:
            breakup.append({"title": "Shipping (store estimate)", "kind": "delivery", "amount_paise": ship})
        return QuoteResult(total, breakup, cart.lines, {"seller": store, "network": "Shopify store",
                                                        "returns": "Store's own policy", "paid_to": f"{store} on its own checkout page"},
                           payee_name=store, payment_mode="handoff", handoff_url=c.get("checkout_url", ""))

    def place(self, db: Session, user: User, order: CommerceOrder, payment_ref: str) -> PlaceResult:
        return PlaceResult(order.meta.get("store_cart_id", ""), "handed_off")

    def status(self, db: Session, user: User, order: CommerceOrder) -> dict[str, Any]:
        return {"status": order.status, "note": "Finish payment on the store's checkout page; the store emails the order status."}

    def cancel(self, db: Session, user: User, order: CommerceOrder, reason_id: str) -> dict[str, Any]:
        return {"status": "cancelled", "note": "Removed from Santosh. If you already paid, cancel from the store's order email."}

    def return_item(self, db, user, order, item_ref, qty, reason_id, reason) -> dict[str, Any]:
        return {"status": order.status, "note": "Returns for brand stores go through the store's returns page."}
