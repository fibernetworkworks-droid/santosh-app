"""Flipkart Affiliate API (official): product search, prices and offers. Checkout happens in the Flipkart app/site
through the affiliate link — Flipkart does not allow third-party ordering."""
from __future__ import annotations

from typing import Any

import httpx
from sqlalchemy.orm import Session

from ...connectors.base import ToolError
from ...db import CommerceCart, User
from ..ondc.beckn import paise
from .base import PlaceResult, QuoteResult

API = "https://affiliate-api.flipkart.net/affiliate/1.0/search.json"


def _sandbox(req: httpx.Request) -> httpx.Response:
    q = req.url.params.get("query", "").lower()
    items = [
        ("BUDS1", "Wireless earbuds with ENC, 40 h playback", 1499, 3999, "Audio"),
        ("SPK1", "Portable Bluetooth speaker 16 W", 1799, 4499, "Audio"),
        ("KETTLE1", "Electric kettle 1.5 L stainless steel", 699, 1499, "Kitchen"),
    ]
    rows = [{"productBaseInfoV1": {"productId": pid, "title": t, "productUrl": f"https://dl.flipkart.com/dl/item/{pid}?affid=SANDBOX",
                                   "flipkartSellingPrice": {"amount": sp, "currency": "INR"},
                                   "maximumRetailPrice": {"amount": mrp, "currency": "INR"}, "inStock": True,
                                   "categoryPath": cat, "imageUrls": {}}}
            for pid, t, sp, mrp, cat in items if any(w in t.lower() for w in q.split() if len(w) > 2)]
    return httpx.Response(200, json={"products": rows})


class FlipkartProvider:
    source = "flipkart"
    label = "Flipkart (search + link)"

    def __init__(self, settings: Any, transport: httpx.BaseTransport | None = None):
        self.s = settings
        if transport is None and not settings.flipkart_affiliate_id and settings.commerce_sandbox_feeds:
            transport = httpx.MockTransport(_sandbox)
        self.enabled = bool(settings.flipkart_affiliate_id) or transport is not None
        self.http = httpx.Client(timeout=8.0, transport=transport)

    def available(self) -> bool:
        return self.enabled

    def search(self, db: Session, user: User, query: str, pincode: str, limit: int) -> list[dict[str, Any]]:
        r = self.http.get(API, params={"query": query, "resultCount": min(limit, 10)},
                          headers={"Fk-Affiliate-Id": self.s.flipkart_affiliate_id or "sandbox",
                                   "Fk-Affiliate-Token": self.s.flipkart_affiliate_token or "sandbox"})
        if r.status_code != 200:
            return []
        out = []
        for p in (r.json().get("products") or [])[:limit]:
            b = p.get("productBaseInfoV1") or {}
            out.append({
                "source": self.source, "ref": {"product_id": b.get("productId")},
                "name": b.get("title", ""), "brand": "", "description": b.get("categoryPath", ""), "image": "",
                "price_paise": paise((b.get("flipkartSpecialPrice") or b.get("flipkartSellingPrice") or {}).get("amount")),
                "mrp_paise": paise((b.get("maximumRetailPrice") or {}).get("amount")),
                "pack": "", "in_stock": bool(b.get("inStock", True)), "max_qty": 0,
                "seller": {"name": "Flipkart", "key": "flipkart", "city": "", "network": "Flipkart"},
                "delivery": {}, "returnable": None, "return_window": "see Flipkart", "cancellable": None, "cod": None,
                "country_of_origin": "", "customer_care": "Flipkart app", "url": b.get("productUrl", ""),
                "buy_mode": "handoff", "sponsored": False, "affiliate": True,
            })
        return out

    def quote(self, db: Session, user: User, cart: CommerceCart, address: dict[str, Any]) -> QuoteResult:
        raise ToolError("Flipkart orders are finished in the Flipkart app. Use the buy link.")

    def place(self, db, user, order, payment_ref) -> PlaceResult:
        raise ToolError("Flipkart orders are finished in the Flipkart app.")

    def status(self, db, user, order) -> dict[str, Any]:
        return {"status": order.status, "note": "Track this order in the Flipkart app."}

    def cancel(self, db, user, order, reason_id) -> dict[str, Any]:
        raise ToolError("Cancel Flipkart orders in the Flipkart app.")

    def return_item(self, db, user, order, item_ref, qty, reason_id, reason) -> dict[str, Any]:
        raise ToolError("Return Flipkart orders in the Flipkart app.")
