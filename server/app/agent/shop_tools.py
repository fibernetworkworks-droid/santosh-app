"""v0.80 Tool `order_karo`: order / book from shopping, grocery, food, pharmacy and travel sites end to end; the final
payment is always hers."""
from __future__ import annotations

import asyncio
from typing import Any

from .tools import Ctx, ToolError

SHOP_TOOLS = [
    {"name": "order_karo", "description": (
        "ORDER or BOOK for her on Amazon, Flipkart, Meesho, Myntra, AJIO, Nykaa, Croma, Tata CLiQ, Blinkit, Zepto, "
        "Swiggy Instamart, BigBasket, JioMart, DMart Ready, Swiggy / Zomato food, 1mg, PharmEasy, IRCTC, redBus, "
        "MakeMyTrip, BookMyShow: Hoola does EVERYTHING (search, compare, choose the right item / size / quantity, cart, "
        "her saved address, slot, coupon) up to the payment; SHE makes the final payment herself (a card on her phone / "
        "live view, or her UPI app). Uses the company's official MCP when she has linked it, else Hoola's own Chrome "
        "with her saved logins (OTP from her phone). "
        "action=order: what (items with quantity, brand / size / veg etc. in her words), site (if she named one; else "
        "the best site for the kind of thing), budget, when (delivery date / slot / travel date), address ('ghar', "
        "'office'...), notes, compare (other site ids to check the price on first, when she wants the cheapest). "
        "Runs in the background with a live card; don't poll. action=orders: her recent orders and their status. "
        "action=sites: what's supported. action=mark (order_id, status placed|failed|cancelled, order_ref, total): "
        "record the result of an order you did through an official MCP."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["order", "orders", "sites", "mark"]},
         "what": {"type": "string"}, "site": {"type": "string"}, "budget": {"type": "string"},
         "when": {"type": "string"}, "address": {"type": "string"}, "notes": {"type": "string"},
         "compare": {"type": "array", "items": {"type": "string"}},
         "order_id": {"type": "string"}, "status": {"type": "string"}, "order_ref": {"type": "string"},
         "total": {"type": "string"}},
         "required": ["action"]}},
]
SHOP_LABELS = {"order_karo": "Order taiyaar kar raha hoon"}


def _run(ctx: Ctx, action: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..shop import service as shop, sites
    try:
        if action == "sites":
            return {"sites": sites.listing()}
        if action == "orders":
            return {"orders": shop.orders(ctx.tenant_id, 15)}
        if action == "mark":
            return shop.mark(ctx.tenant_id, str(a.get("order_id", "")), str(a.get("status", "")),
                             str(a.get("order_ref", "")), str(a.get("total", "")))
        if action == "order":
            return shop.order(ctx.tenant_id, str(a.get("what", "")), ctx.conversation_id, str(a.get("site", "")),
                              str(a.get("budget", "")), str(a.get("when", "")), str(a.get("address", "")),
                              str(a.get("notes", "")), [str(x).lower() for x in (a.get("compare") or [])],
                              created_by=getattr(ctx, "actor", "owner") or "owner")
    except shop.ShopError as e:
        raise ToolError(str(e))
    raise ToolError("action = order | orders | sites | mark")


async def order_karo(ctx: Ctx, action, **a: Any):
    return await asyncio.to_thread(_run, ctx, str(action), a)


SHOP_HANDLERS = {"order_karo": order_karo}
