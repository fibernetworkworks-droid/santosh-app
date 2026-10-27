"""Santosh's own shopping executor: the same commerce service the MCP server exposes, with Santosh's confirm cards.

checkout is Tier 2 and never auto-approved: the card shows the seller's all-in quote (from the seller, not from chat
text) with the price breakup and the disclosures the E-Commerce Rules ask for (seller, delivery, returns, country of
origin, customer care, who is paid). Approving it places the order and opens UPI to pay with the user's own PIN.
Flipkart and Shopify brand stores are link-outs: the user finishes on the store's own app or checkout page.
"""
from __future__ import annotations

import copy
import re
from typing import Any

from ..commerce.service import CommerceService
from ..db import CommerceCart, CommerceOrder, CommerceQuote
from ..packs.registry import Pack
from .base import Ctx, NeedsApproval, ToolError, ToolSpec


def iso_duration(v: str) -> str:
    """'PT45M' -> '45 min', 'P3D' -> '3 days', 'PT2H' -> '2 hours' (ONDC durations)."""
    m = re.fullmatch(r"P(?:(\d+)D)?(?:T(?:(\d+)H)?(?:(\d+)M)?)?", (v or "").strip())
    if not m or not any(m.groups()):
        return v or ""
    d, h, mi = (int(x) if x else 0 for x in m.groups())
    parts = [f"{d} day{'s' if d != 1 else ''}" if d else "", f"{h} hour{'s' if h != 1 else ''}" if h else "",
             f"{mi} min" if mi else ""]
    return " ".join(p for p in parts if p)


def disclosure_rows(q: dict[str, Any], quote_ttl_seconds: int) -> list[dict[str, Any]]:
    """What the user must see before paying. Stored in Approval.items as kind=disclosure (shown, not priced)."""
    d = q.get("disclosures") or {}
    seller = q.get("seller") or d.get("seller", "")
    via = d.get("seller_app") or d.get("network") or ""
    rows = [("Seller", f"{seller}" + (f" (via {via})" if via and via != seller else "") + (f", {d['seller_city']}" if d.get("seller_city") else ""))]
    eta = d.get("delivery_eta") or d.get("delivery_slot") or ""
    if eta:
        rows.append(("Delivery", iso_duration(eta) if eta.startswith("P") else eta))
    if q.get("deliver_to"):
        rows.append(("Deliver to", q["deliver_to"]))
    rows.append(("Returns", d.get("returns") or "not stated by the seller"))
    if d.get("country_of_origin"):
        rows.append(("Country of origin", "India" if d["country_of_origin"] in ("IND", "IN") else d["country_of_origin"]))
    if d.get("customer_care"):
        rows.append(("Customer care", d["customer_care"]))
    if d.get("paid_to"):
        rows.append(("Paid to", d["paid_to"]))
    rows.append(("Price check", f"Total includes every charge. Valid {max(1, quote_ttl_seconds // 60)} min; after that I re-check with the seller."))
    return [{"name": k, "value": str(v)[:200], "kind": "disclosure"} for k, v in rows if v]


class CommerceExecutor:
    name = "commerce"

    def __init__(self, service_factory=None):
        self.make = service_factory or (lambda ctx: CommerceService(ctx.session, ctx.settings))

    def tool_specs(self, pack: Pack, ctx: Ctx) -> list[ToolSpec]:
        o = {"type": "object"}
        return [
            ToolSpec("search_products", "Search products across Santosh Bazar shops, ONDC, Shopify brand stores and Flipkart "
                     "(link only), cheapest first. Results are numbered; refer to them by number or offer_id.",
                     {**o, "properties": {"query": {"type": "string"}, "max_price_rupees": {"type": "number"},
                                          "sources": {"type": "array", "items": {"type": "string",
                                                                                 "enum": ["bazar", "ondc", "shopify", "flipkart"]}}},
                      "required": ["query"]}, 0),
            ToolSpec("add_to_cart", "Add a search result to the cart. pick = result number (1-based) from the last search, or offer_id. "
                     "Flipkart items give a link instead (bought in the Flipkart app).",
                     {**o, "properties": {"pick": {"type": "string"}, "quantity": {"type": "integer"}}, "required": ["pick"]}, 1),
            ToolSpec("view_cart", "Show open carts.", {**o, "properties": {}}, 0),
            ToolSpec("checkout", "Get the seller's all-in price for the latest (or given) cart and put a confirm card on the "
                     "user's screen. Nothing is ordered or paid until the user taps it.",
                     {**o, "properties": {"cart_id": {"type": "string"}}}, 2),
            ToolSpec("order_status", "Status of the latest (or given) order.", {**o, "properties": {"order_id": {"type": "string"}}}, 0),
            ToolSpec("list_orders", "Recent orders.", {**o, "properties": {}}, 0),
            ToolSpec("cancel_order", "Cancel the latest (or given) open order.",
                     {**o, "properties": {"order_id": {"type": "string"}, "reason": {"type": "string"}}}, 1),
            ToolSpec("request_return", "Return an item from a delivered order.",
                     {**o, "properties": {"order_id": {"type": "string"}, "item": {"type": "string"}, "reason": {"type": "string"}}}, 1),
            ToolSpec("get_buy_link", "Store link for Flipkart / brand-store items (the user buys there).",
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

    @staticmethod
    def _link(out: dict[str, Any]) -> dict[str, Any]:
        """Show an Open button for link-outs (Flipkart app, store checkout)."""
        url = out.get("url") or out.get("checkout_url") or ""
        if url:
            return {**out, "deep_link": url, "app": out.get("store") or out.get("seller") or "Store"}
        return out

    def call(self, pack: Pack, tool: str, args: dict[str, Any], ctx: Ctx) -> dict[str, Any] | NeedsApproval:
        s = self.make(ctx)
        u = ctx.user
        if tool == "search_products":
            srcs = args.get("sources")
            srcs = [x for x in srcs if isinstance(x, str)] if isinstance(srcs, list) else None
            r = s.search(u, str(args.get("query", "")), sources=srcs or None, max_price_rupees=args.get("max_price_rupees"), limit=6)
            self._remember(ctx, [x["offer_id"] for x in r["results"]])
            if not r["results"]:
                return {**r, "message": f"Nothing found for '{r['query']}'" + (f" near {r['pincode']}." if r["pincode"] else ".")}
            lines = [f"{i}. {x['name']}" + (f" ({x['pack']})" if x.get("pack", "").startswith("per ") else "")
                     + f" — {x['price']} · {x['seller']} ({x['seller_network']})"
                     + (" · on store app" if x["buy_mode"] == "handoff" else "") + (" · DEMO" if x.get("demo") else "")
                     for i, x in enumerate(r["results"], 1)]
            return {**r, "message": "Cheapest first:\n" + "\n".join(lines) + "\nSay e.g. '1 number 2 cart mein daalo'."}
        if tool == "add_to_cart":
            r = s.add_to_cart(u, self._pick(ctx, args.get("pick")), int(args.get("quantity") or 1))
            if r.get("added") is False:
                return self._link(r)
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
            if q.get("checkout_url") is not None and q.get("payment") == "On the store's own checkout page":
                return self._link({**q, "intent_url": ""})
            quote_row = s.db.get(CommerceQuote, q["quote_id"])
            items = [{"name": b["title"], "price_paise": b["amount_paise"], "kind": b.get("kind", "item")} for b in quote_row.breakup]
            demo = bool(q.get("demo"))
            return NeedsApproval(tier=2, title=("[DEMO] " if demo else "") + f"Order from {q['seller']}",
                                 payee=q["payment"].replace("UPI to ", ""), amount_paise=q["total_paise"],
                                 items=items + disclosure_rows(q, ctx.settings.commerce_quote_ttl_seconds),
                                 pay_method="Demo: no money moves" if demo else "UPI PIN in your UPI app",
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
            return self._link(s.buy_link(u, self._pick(ctx, args.get("pick"))))
        raise ToolError(f"Unknown tool {tool}")

    def execute(self, pack: Pack, action: str, args: dict[str, Any], ctx: Ctx) -> dict[str, Any]:
        if action != "place_order":
            raise ToolError(f"Unknown action {action}")
        s = self.make(ctx)
        o = s.confirm(ctx.user, args["quote_id"], "santosh_card", client_id="santosh-app",
                      idempotency_key=f"task-{ctx.task.id if ctx.task else ''}-{args['quote_id']}",
                      task_id=ctx.task.id if ctx.task else "")
        if o.get("demo"):
            return {"status": "demo_placed", "order_id": o["order_id"], "message": o.get("message", "[DEMO] Order placed.")}
        pay = o.get("pay") or {}
        return {"status": "open_app", "intent_url": pay.get("upi_link", ""), "txn_ref": pay.get("txn_ref", ""),
                "order_id": o["order_id"], "message": o.get("message", "Order saved.")}
