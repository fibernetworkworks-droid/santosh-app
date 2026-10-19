"""Santosh's own shopping executor: the same commerce service the MCP server exposes, with Santosh's confirm cards.

checkout is Tier 2: the card shows the seller's all-in quote (from the seller, not from chat text); approving it
places the order and opens UPI to pay with the user's own PIN.
"""
from __future__ import annotations

import copy
from typing import Any

from ..commerce.service import CommerceService
from ..db import CommerceCart, CommerceOrder, CommerceQuote
from ..packs.registry import Pack
from .base import Ctx, NeedsApproval, ToolError, ToolSpec


class CommerceExecutor:
    name = "commerce"

    def __init__(self, service_factory=None):
        self.make = service_factory or (lambda ctx: CommerceService(ctx.session, ctx.settings))

    def tool_specs(self, pack: Pack, ctx: Ctx) -> list[ToolSpec]:
        o = {"type": "object"}
        return [
            ToolSpec("search_products", "Search products across MVP Bazar shops, ONDC, brand stores and Flipkart, cheapest first. "
                     "Results are numbered; refer to them by number or offer_id.",
                     {**o, "properties": {"query": {"type": "string"}, "max_price_rupees": {"type": "number"},
                                          "sources": {"type": "array", "items": {"type": "string"}}}, "required": ["query"]}, 0),
            ToolSpec("add_to_cart", "Add a search result to the cart. pick = result number (1-based) from the last search, or offer_id.",
                     {**o, "properties": {"pick": {"type": "string"}, "quantity": {"type": "integer"}}, "required": ["pick"]}, 1),
            ToolSpec("view_cart", "Show open carts.", {**o, "properties": {}}, 0),
            ToolSpec("checkout", "Get the seller's all-in price for the latest (or given) cart and ask the user to approve.",
                     {**o, "properties": {"cart_id": {"type": "string"}}}, 2),
            ToolSpec("order_status", "Status of the latest (or given) order.", {**o, "properties": {"order_id": {"type": "string"}}}, 0),
            ToolSpec("list_orders", "Recent orders.", {**o, "properties": {}}, 0),
            ToolSpec("cancel_order", "Cancel the latest (or given) open order.",
                     {**o, "properties": {"order_id": {"type": "string"}, "reason": {"type": "string"}}}, 1),
            ToolSpec("request_return", "Return an item from a delivered order.",
                     {**o, "properties": {"order_id": {"type": "string"}, "item": {"type": "string"}, "reason": {"type": "string"}}}, 1),
            ToolSpec("get_buy_link", "Store link for Flipkart / brand-store items.",
                     {**o, "properties": {"pick": {"type": "string"}}, "required": ["pick"]}, 0),
        ]

    # ------------------------------------------------------------------
    def _remember(self, ctx: Ctx, ids: list[str]) -> None:
        prof = copy.deepcopy(ctx.user.profile or {})
        prof["last_search"] = ids
        ctx.user.profile = prof

    def _pick(self, ctx: Ctx, pick: Any) -> str:
        p = str(pick).strip()
        last = (ctx.user.profile or {}).get("last_search") or []
        if p.isdigit() and 1 <= int(p) <= len(last):
            return last[int(p) - 1]
        if p.isdigit():
            raise ToolError(f"There are only {len(last)} results in the last search.")
        return p

    def _latest_cart(self, ctx: Ctx) -> str:
        from sqlalchemy import select
        c = ctx.session.scalars(select(CommerceCart).where(CommerceCart.user_id == ctx.user.id, CommerceCart.status.in_(["open", "quoted"]))
                                .order_by(CommerceCart.created_at.desc())).first()
        if c is None or not c.lines:
            raise ToolError("Your cart is empty. Search for something first.")
        return c.id

    def _latest_order(self, ctx: Ctx, open_only: bool = True) -> str:
        from sqlalchemy import select

        from ..commerce.service import OPEN
        q = select(CommerceOrder).where(CommerceOrder.user_id == ctx.user.id)
        if open_only:
            q = q.where(CommerceOrder.status.in_(OPEN))
        o = ctx.session.scalars(q.order_by(CommerceOrder.created_at.desc())).first()
        if o is None:
            raise ToolError("No open orders.")
        return o.id

    def call(self, pack: Pack, tool: str, args: dict[str, Any], ctx: Ctx) -> dict[str, Any] | NeedsApproval:
        s = self.make(ctx)
        u = ctx.user
        if tool == "search_products":
            r = s.search(u, str(args.get("query", "")), sources=args.get("sources"), max_price_rupees=args.get("max_price_rupees"), limit=6)
            self._remember(ctx, [x["offer_id"] for x in r["results"]])
            if not r["results"]:
                return {**r, "message": f"Nothing found for '{r['query']}' near {r['pincode']}."}
            lines = [f"{i}. {x['name']}" + (f" ({x['pack']})" if x.get("pack", "").startswith("per ") else "")
                     + f" — {x['price']} · {x['seller']} ({x['seller_network']})"
                     + (" · on store app" if x["buy_mode"] == "handoff" else "") for i, x in enumerate(r["results"], 1)]
            return {**r, "message": "Cheapest first:\n" + "\n".join(lines) + "\nSay e.g. '1 number 2 cart mein daalo'."}
        if tool == "add_to_cart":
            r = s.add_to_cart(u, self._pick(ctx, args.get("pick")), int(args.get("quantity") or 1))
            if r.get("added") is False:
                return r
            return {**r, "message": f"Cart at {r['seller']}: " + ", ".join(f"{i['name']} × {i['qty']}" for i in r["items"])
                    + f" ({r['items_total']} before delivery). Say 'order karo' to see the final price."}
        if tool == "view_cart":
            carts = s.list_carts(u)
            if not carts:
                return {"carts": [], "message": "Your cart is empty."}
            return {"carts": carts, "message": " | ".join(f"{c['seller']}: " + ", ".join(f"{i['name']} × {i['qty']}" for i in c["items"])
                                                          for c in carts)}
        if tool == "checkout":
            q = s.quote(u, args.get("cart_id") or self._latest_cart(ctx))
            if q.get("payment") == "On the store's own checkout page":
                return {**q, "intent_url": "", "checkout_url": q["checkout_url"]}
            d = q["disclosures"]
            quote_row = s.db.get(CommerceQuote, q["quote_id"])
            items = [{"name": b["title"], "price_paise": b["amount_paise"]} for b in quote_row.breakup]
            extra = [x for x in (f"Delivery {d['delivery_eta'].replace('PT', '').replace('M', ' min').replace('P', '').replace('D', ' days')}"
                                 if d.get("delivery_eta") else "", d.get("returns", "")) if x]
            return NeedsApproval(tier=2, title=f"Order from {q['seller']}", payee=q["payment"].replace("UPI to ", ""),
                                 amount_paise=q["total_paise"], items=items + [{"name": e, "price_paise": 0} for e in extra],
                                 pay_method="UPI PIN in your UPI app",
                                 action={"executor": "commerce", "pack_id": pack.id, "name": "place_order",
                                         "args": {"quote_id": q["quote_id"]}},
                                 preview=q)
        if tool == "order_status":
            r = s.status(u, args.get("order_id") or self._latest_order(ctx, open_only=False))
            return {**r, "message": f"{r['seller']} order {r['order_id'][:6]}: {r['status'].replace('_', ' ')}. {r.get('note', '')}".strip()}
        if tool == "list_orders":
            rows = s.list_orders(u)
            return {"orders": rows, "message": "; ".join(f"{o['order_id'][:6]} {o['seller']} {o['total']} {o['status']}" for o in rows) or "No orders yet."}
        if tool == "cancel_order":
            return s.cancel(u, args.get("order_id") or self._latest_order(ctx), str(args.get("reason", "")))
        if tool == "request_return":
            oid = args.get("order_id") or self._latest_order(ctx, open_only=False)
            o = s._order(u, oid)
            item = args.get("item") or (o.lines[0]["name"] if o.lines else "")
            return s.return_item(u, oid, item, 1, str(args.get("reason", "")))
        if tool == "get_buy_link":
            return s.buy_link(u, self._pick(ctx, args.get("pick")))
        raise ToolError(f"Unknown tool {tool}")

    def execute(self, pack: Pack, action: str, args: dict[str, Any], ctx: Ctx) -> dict[str, Any]:
        if action != "place_order":
            raise ToolError(f"Unknown action {action}")
        s = self.make(ctx)
        o = s.confirm(ctx.user, args["quote_id"], "santosh_card", client_id="santosh-app",
                      idempotency_key=f"task-{ctx.task.id if ctx.task else ''}-{args['quote_id']}",
                      task_id=ctx.task.id if ctx.task else "")
        pay = o.get("pay") or {}
        return {"status": "open_app", "intent_url": pay.get("upi_link", ""), "txn_ref": pay.get("txn_ref", ""),
                "order_id": o["order_id"], "message": o.get("message", "Order saved.")}
