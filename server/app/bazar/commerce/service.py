"""Santosh commerce service — one shopping flow over every legal source.

search -> add_to_cart -> quote (all-in price, disclosures, 10-minute validity) -> user confirms -> UPI intent
(the user enters their own UPI PIN) -> payment confirmed -> order placed with the seller -> status / cancel / return.

Rules built in (Consumer Protection (E-Commerce) Rules + CCPA dark-pattern guidelines + Santosh guard tiers):
- The price the user approves is the full price: items, delivery, packing, taxes, fees. No pre-ticked add-ons.
- Nothing is ordered without an explicit confirmation of an unexpired quote, and no money moves without the user's
  own UPI PIN. Every confirmation is stored as a consent record (who, what, amount, payee, quote hash, surface).
- Prices and stock are re-checked when quoting; a changed cart invalidates the quote.
- Results are sorted by price; sponsored results (none today) would be labelled. MRP is shown as MRP, not as a
  "discount" claim.
- Per-order cap (SANTOSH_COMMERCE_MAX_ORDER_PAISE); one seller per cart; idempotency keys on order placement.
- Seller name, returns, delivery time, country of origin and customer care are shown before payment.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..connectors.base import ToolError, rupees
from ..connectors.upi import build_upi_intent
from ..db import CommerceCart, CommerceOffer, CommerceOrder, CommerceQuote, ConsentRecord, ShopOrder, Transaction, User
from .providers.base import Provider
from .providers.bazar import BazarProvider
from .providers.flipkart import FlipkartProvider
from .providers.ondc import OndcProvider
from .providers.shopify import ShopifyProvider

CANCEL_REASON = {"mistake": "005", "galti": "005", "address": "006", "late": "003", "der": "003", "price": "001",
                 "sasta": "002", "cheaper": "002"}
RETURN_REASON = {"damaged": "003", "toota": "003", "kharab": "003", "wrong": "004", "galat": "004", "missing": "005",
                 "kam": "005", "not needed": "001", "nahi chahiye": "001", "different": "002", "alag": "002"}
OPEN = ("payment_pending", "placed", "accepted", "packed", "shipped", "out_for_delivery")


def _now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)


def _reason(text: str, table: dict[str, str], default: str) -> str:
    t = (text or "").lower()
    return next((code for word, code in table.items() if word in t), default)


class CommerceService:
    def __init__(self, db: Session, settings: Any, providers: dict[str, Provider] | None = None):
        self.db, self.s = db, settings
        if providers is None:
            providers = {"bazar": BazarProvider(), "ondc": OndcProvider(settings), "shopify": ShopifyProvider(settings),
                         "flipkart": FlipkartProvider(settings)}
        self.providers = {k: v for k, v in providers.items() if v.available()}

    # ------------------------------------------------------------------ search
    def sources(self) -> list[dict[str, Any]]:
        modes = {"bazar": "order + UPI to shop", "ondc": "order + UPI, open network", "shopify": "cart, pay on store checkout",
                 "flipkart": "search + link to Flipkart"}
        return [{"source": k, "name": p.label, "how": modes.get(k, "")} for k, p in self.providers.items()]

    def search(self, user: User, query: str, pincode: str = "", sources: list[str] | None = None,
               max_price_rupees: float | None = None, limit: int = 8) -> dict[str, Any]:
        query = (query or "").strip()
        if len(query) < 2:
            raise ToolError("What should I search for?")
        pin = pincode or user.pincode or ""
        offers: list[dict[str, Any]] = []
        errors = []
        for key, prov in self.providers.items():
            if sources and key not in sources:
                continue
            try:
                offers += prov.search(self.db, user, query, pin, max(limit, 10))
            except ToolError as e:
                errors.append(f"{prov.label}: {e}")
            except Exception as e:  # one source down must not break search
                errors.append(f"{prov.label}: unavailable ({type(e).__name__})")
        if max_price_rupees:
            offers = [o for o in offers if o["price_paise"] <= max_price_rupees * 100]
        offers = [o for o in offers if o["in_stock"]]
        offers.sort(key=lambda o: (o["sponsored"], o["price_paise"]))
        offers = offers[:limit]
        out = []
        for o in offers:
            row = CommerceOffer(user_id=user.id, source=o["source"], data=o)
            self.db.add(row)
            self.db.flush()
            out.append(self.offer_view(row))
        self.db.commit()
        return {"query": query, "pincode": pin, "results": out, "sources_searched": [k for k in self.providers if not sources or k in sources],
                "errors": errors, "note": "Sorted by price. MRP is the printed maximum price, not a discount claim."}

    @staticmethod
    def offer_view(row: CommerceOffer) -> dict[str, Any]:
        o = row.data
        v = {"offer_id": row.id, "source": o["source"], "name": o["name"], "price": rupees(o["price_paise"]),
             "price_paise": o["price_paise"], "seller": o["seller"]["name"], "seller_network": o["seller"].get("network", ""),
             "pack": o.get("pack", ""), "buy_mode": o["buy_mode"],
             "returnable": o.get("returnable"), "return_window": o.get("return_window", ""),
             "delivery": o.get("delivery", {}), "country_of_origin": o.get("country_of_origin", "")}
        if o.get("mrp_paise") and o["mrp_paise"] > o["price_paise"]:
            v["mrp"] = rupees(o["mrp_paise"])
        if o.get("sponsored"):
            v["label"] = "Sponsored"
        if o["buy_mode"] == "handoff":
            v["how_to_buy"] = "Finish on the store's own app/checkout (link)"
        return v

    def _offer(self, user: User, offer_id: str) -> CommerceOffer:
        row = self.db.get(CommerceOffer, offer_id)
        if row is None or row.user_id != user.id:
            raise ToolError("I can't find that product any more. Please search again.")
        return row

    def get_offer(self, user: User, offer_id: str) -> dict[str, Any]:
        row = self._offer(user, offer_id)
        o = row.data
        return {**self.offer_view(row), "brand": o.get("brand", ""), "description": o.get("description", ""),
                "seller_city": o["seller"].get("city", ""), "cancellable": o.get("cancellable"), "cod": o.get("cod"),
                "customer_care": o.get("customer_care", ""), "url": o.get("url", "")}

    def buy_link(self, user: User, offer_id: str) -> dict[str, Any]:
        o = self._offer(user, offer_id).data
        if not o.get("url"):
            raise ToolError("This product has no store link; add it to a cart instead.")
        return {"name": o["name"], "price": rupees(o["price_paise"]), "url": o["url"], "store": o["seller"]["name"],
                "affiliate_link": bool(o.get("affiliate")),
                "message": f"Open {o['seller']['name']} to buy {o['name']} ({rupees(o['price_paise'])}). Final price is shown there."
                           + (" Santosh may earn a referral fee from this link." if o.get("affiliate") else "")}

    # ------------------------------------------------------------------ cart
    def _cart(self, user: User, cart_id: str) -> CommerceCart:
        c = self.db.get(CommerceCart, cart_id)
        if c is None or c.user_id != user.id:
            raise ToolError("Cart not found")
        return c

    def add_to_cart(self, user: User, offer_id: str, qty: int = 1, cart_id: str | None = None) -> dict[str, Any]:
        row = self._offer(user, offer_id)
        o = row.data
        if o["buy_mode"] == "handoff" and o["source"] == "flipkart":
            return {**self.buy_link(user, offer_id), "added": False}
        qty = int(qty)
        if qty < 1 or (o.get("max_qty") and qty > o["max_qty"]):
            raise ToolError(f"Quantity must be between 1 and {o.get('max_qty') or 10}.")
        if cart_id:
            cart = self._cart(user, cart_id)
            if cart.seller_key != o["seller"]["key"]:
                raise ToolError(f"This cart is for {cart.seller_name}. One seller per order — I'll start a new cart if you want.")
        else:
            cart = self.db.scalars(select(CommerceCart).where(CommerceCart.user_id == user.id, CommerceCart.status == "open",
                                                              CommerceCart.seller_key == o["seller"]["key"])).first()
            if cart is None:
                cart = CommerceCart(user_id=user.id, source=o["source"], seller_key=o["seller"]["key"], seller_name=o["seller"]["name"],
                                    meta={"seller_app": o["seller"].get("seller_app", ""), "customer_care": o.get("customer_care", "")})
                self.db.add(cart)
                self.db.flush()
        lines = [ln for ln in cart.lines if ln["offer_id"] != offer_id]
        lines.append({"offer_id": offer_id, "ref": o["ref"], "name": o["name"], "qty": qty, "unit_price_paise": o["price_paise"],
                      "returnable": o.get("returnable"), "return_window": o.get("return_window", ""),
                      "country_of_origin": o.get("country_of_origin", "")})
        cart.lines = lines
        cart.status = "open"
        self._supersede(cart.id)
        self.db.commit()
        return self.view_cart(user, cart.id)

    def update_cart(self, user: User, cart_id: str, offer_id: str, qty: int) -> dict[str, Any]:
        cart = self._cart(user, cart_id)
        if qty <= 0:
            cart.lines = [ln for ln in cart.lines if ln["offer_id"] != offer_id]
        else:
            cart.lines = [{**ln, "qty": int(qty)} if ln["offer_id"] == offer_id else ln for ln in cart.lines]
        cart.status = "open"
        self._supersede(cart.id)
        self.db.commit()
        return self.view_cart(user, cart_id)

    def view_cart(self, user: User, cart_id: str) -> dict[str, Any]:
        c = self._cart(user, cart_id)
        sub = sum(ln["unit_price_paise"] * ln["qty"] for ln in c.lines)
        return {"cart_id": c.id, "seller": c.seller_name, "source": c.source, "status": c.status,
                "items": [{"offer_id": ln["offer_id"], "name": ln["name"], "qty": ln["qty"],
                           "price": rupees(ln["unit_price_paise"] * ln["qty"])} for ln in c.lines],
                "items_total": rupees(sub), "note": "Delivery, packing and taxes are added in the quote."}

    def list_carts(self, user: User) -> list[dict[str, Any]]:
        rows = self.db.scalars(select(CommerceCart).where(CommerceCart.user_id == user.id, CommerceCart.status.in_(["open", "quoted"]))).all()
        return [self.view_cart(user, c.id) for c in rows if c.lines]

    def _supersede(self, cart_id: str) -> None:
        for q in self.db.scalars(select(CommerceQuote).where(CommerceQuote.cart_id == cart_id, CommerceQuote.status == "open")).all():
            q.status = "superseded"

    # ------------------------------------------------------------------ quote
    @staticmethod
    def _hash(user_id: str, lines: list[dict[str, Any]], total: int, payee: str) -> str:
        key = json.dumps({"u": user_id, "l": [[ln["ref"], ln["qty"], ln["unit_price_paise"]] for ln in lines], "t": total, "p": payee},
                         sort_keys=True, default=str)
        return hashlib.sha256(key.encode()).hexdigest()

    def default_address(self, user: User) -> dict[str, Any]:
        prof = user.profile or {}
        loc = prof.get("home_location") or {}
        addr = prof.get("delivery_address") or {}
        return {"name": addr.get("name") or user.name or "Customer", "line1": addr.get("line1") or prof.get("address", ""),
                "locality": addr.get("locality", ""), "city": addr.get("city") or user.city or "", "state": addr.get("state", "Maharashtra"),
                "pincode": addr.get("pincode") or user.pincode or "", "phone": addr.get("phone") or user.phone,
                "email": addr.get("email", ""), "gps": f"{loc.get('lat', '')},{loc.get('lng', '')}" if loc else ""}

    def quote(self, user: User, cart_id: str, address: dict[str, Any] | None = None) -> dict[str, Any]:
        cart = self._cart(user, cart_id)
        if not cart.lines:
            raise ToolError("The cart is empty.")
        if cart.status == "ordered":
            raise ToolError("This cart was already ordered.")
        addr = {**self.default_address(user), **(address or {})}
        if not addr.get("pincode"):
            raise ToolError("I need your delivery PIN code first.")
        prov = self.providers.get(cart.source)
        if prov is None:
            raise ToolError(f"{cart.source} is not available right now.")
        r = prov.quote(self.db, user, cart, addr)
        if r.payment_mode != "handoff" and r.total_paise > self.s.commerce_max_order_paise:
            raise ToolError(f"This order is {rupees(r.total_paise)}, above Santosh's per-order limit of "
                            f"{rupees(self.s.commerce_max_order_paise)}.")
        changed = [ln["name"] for ln, new in zip(cart.lines, r.lines, strict=False) if ln["unit_price_paise"] != new["unit_price_paise"]]
        cart.lines = r.lines
        self._supersede(cart.id)
        q = CommerceQuote(user_id=user.id, cart_id=cart.id, total_paise=r.total_paise, breakup=r.breakup, disclosures=r.disclosures,
                          address=addr, payment_mode=r.payment_mode,
                          quote_hash=self._hash(user.id, r.lines, r.total_paise, r.payee_vpa or r.handoff_url),
                          expires_at=_now() + dt.timedelta(seconds=self.s.commerce_quote_ttl_seconds),
                          meta={**r.meta, "payee_name": r.payee_name, "payee_vpa": r.payee_vpa, "handoff_url": r.handoff_url})
        self.db.add(q)
        cart.status = "quoted"
        self.db.flush()
        out = self.quote_view(q, cart)
        if changed:
            out["price_changed"] = changed
            out["message"] = "Prices changed since search for: " + ", ".join(changed) + ". " + out["message"]
        self.db.commit()
        return out

    def quote_view(self, q: CommerceQuote, cart: CommerceCart) -> dict[str, Any]:
        items = ", ".join(f"{ln['name']} × {ln['qty']}" for ln in cart.lines)
        base = {"quote_id": q.id, "cart_id": cart.id, "seller": cart.seller_name, "source": cart.source,
                "total": rupees(q.total_paise), "total_paise": q.total_paise,
                "breakup": [{"title": b["title"], "amount": rupees(b["amount_paise"])} for b in q.breakup],
                "disclosures": q.disclosures, "deliver_to": f"{q.address.get('line1', '')}, {q.address.get('city', '')} {q.address.get('pincode', '')}".strip(", "),
                "valid_for_minutes": max(0, int((q.expires_at - _now()).total_seconds() // 60))}
        if q.payment_mode == "handoff":
            return {**base, "payment": "On the store's own checkout page", "checkout_url": q.meta.get("handoff_url", ""),
                    "message": f"Your cart at {cart.seller_name} is ready: {items}. Total about {rupees(q.total_paise)}. "
                               f"Open the store checkout to pay; the store confirms the final amount."}
        return {**base, "payment": f"UPI to {q.meta.get('payee_name')}", "needs_confirmation": True,
                "confirm_text": f"Order {items} from {cart.seller_name} for {rupees(q.total_paise)} (all-in), pay by UPI to {q.meta.get('payee_name')}?",
                "message": f"{items} from {cart.seller_name}: {rupees(q.total_paise)} all-in. Confirm to pay by UPI."}

    # ------------------------------------------------------------------ confirm + pay
    def confirm(self, user: User, quote_id: str, surface: str, client_id: str = "", idempotency_key: str = "",
                task_id: str = "") -> dict[str, Any]:
        if idempotency_key:
            prev = self.db.scalars(select(CommerceOrder).where(CommerceOrder.user_id == user.id,
                                                               CommerceOrder.idempotency_key == idempotency_key)).first()
            if prev is not None:
                return self.order_view(prev, include_payment=True)
        q = self.db.get(CommerceQuote, quote_id)
        if q is None or q.user_id != user.id:
            raise ToolError("Quote not found.")
        if q.status != "open":
            raise ToolError("This price quote is no longer valid (the cart changed or it was used). Please get a fresh quote.")
        if _now() > q.expires_at:
            q.status = "expired"
            self.db.commit()
            raise ToolError("The price quote expired. Please get a fresh quote so the price and stock are current.")
        cart = self._cart(user, q.cart_id)
        if self._hash(user.id, cart.lines, q.total_paise, q.meta.get("payee_vpa") or q.meta.get("handoff_url", "")) != q.quote_hash:
            q.status = "superseded"
            self.db.commit()
            raise ToolError("The cart changed after the quote. Please get a fresh quote.")
        if q.payment_mode == "handoff":
            raise ToolError("This store takes payment on its own checkout page: open the checkout link.")
        if q.total_paise > self.s.commerce_max_order_paise:
            raise ToolError("Above the per-order limit.")
        q.status = "confirmed"
        cart.status = "ordered"
        order = CommerceOrder(user_id=user.id, source=cart.source, seller_name=cart.seller_name, cart_id=cart.id, quote_id=q.id,
                              lines=cart.lines, total_paise=q.total_paise, idempotency_key=idempotency_key,
                              meta=dict(q.meta), history=[{"at": _now().isoformat(), "status": "payment_pending", "note": f"confirmed via {surface}"}])
        self.db.add(order)
        self.db.flush()
        txn = Transaction(user_id=user.id, task_id=task_id, kind="commerce", provider=cart.source, amount_paise=q.total_paise,
                          status="awaiting_payment", meta={"commerce_order_id": order.id, "payee": q.meta.get("payee_vpa")})
        self.db.add(txn)
        self.db.flush()
        order.txn_ref = txn.txn_ref
        if cart.source == "bazar":
            so = self.providers["bazar"].create_shop_order(self.db, user, cart, q.total_paise,  # type: ignore[attr-defined]
                                                           q.meta.get("slot", ""), txn.txn_ref)
            order.meta = {**order.meta, "shop_order_id": so.id}
            order.external_id = so.id
        self.db.add(ConsentRecord(user_id=user.id, quote_id=q.id, order_id=order.id, surface=surface, client_id=client_id,
                                  statement=self.quote_view(q, cart).get("confirm_text", ""), amount_paise=q.total_paise,
                                  payee=f"{q.meta.get('payee_name')} ({q.meta.get('payee_vpa')})", quote_hash=q.quote_hash))
        self.db.commit()
        return self.order_view(order, include_payment=True)

    def payment_link(self, order: CommerceOrder) -> str:
        return build_upi_intent(order.meta.get("payee_vpa", ""), order.meta.get("payee_name", ""), order.total_paise,
                                note=f"Santosh order {order.id[:6]}", tr=order.txn_ref, max_paise=self.s.upi_max_amount_paise)

    def on_paid(self, txn: Transaction) -> str:
        order = self.db.get(CommerceOrder, txn.meta.get("commerce_order_id", ""))
        if order is None:
            return f"Payment of {rupees(txn.amount_paise)} done."
        user = self.db.get(User, order.user_id)
        order.payment_status = "paid"
        prov = self.providers.get(order.source)
        try:
            r = prov.place(self.db, user, order, txn.txn_ref) if prov else None  # type: ignore[arg-type]
        except ToolError as e:
            self._move(order, "failed", str(e))
            txn.status = "refund_due"
            return f"Paid {rupees(order.total_paise)}, but {e}"
        if r:
            order.external_id = r.external_id or order.external_id
            self._move(order, r.status if r.status != "handed_off" else "placed", "seller accepted the order")
        txn.status = "completed"
        return f"Paid {rupees(order.total_paise)}. {order.seller_name} has your order (Santosh order {order.id[:6]})."

    def on_failed(self, txn: Transaction) -> None:
        order = self.db.get(CommerceOrder, txn.meta.get("commerce_order_id", ""))
        if order is not None:
            self._move(order, "failed", "payment failed")
            if order.meta.get("shop_order_id"):
                so = self.db.get(ShopOrder, order.meta["shop_order_id"])
                if so:
                    so.status = "cancelled"

    def _move(self, order: CommerceOrder, status: str, note: str = "") -> None:
        if status != order.status:
            order.status = status
            order.history = [*order.history, {"at": _now().isoformat(), "status": status, "note": note}]

    # ------------------------------------------------------------------ after the order
    def _order(self, user: User, order_id: str) -> CommerceOrder:
        o = self.db.get(CommerceOrder, order_id)
        if o is None or o.user_id != user.id:
            o = self.db.scalars(select(CommerceOrder).where(CommerceOrder.user_id == user.id,
                                                            CommerceOrder.id.startswith(order_id))).first() if len(order_id) >= 4 else None
        if o is None:
            raise ToolError("Order not found.")
        return o

    def order_view(self, o: CommerceOrder, include_payment: bool = False) -> dict[str, Any]:
        v = {"order_id": o.id, "source": o.source, "seller": o.seller_name, "status": o.status, "payment": o.payment_status,
             "total": rupees(o.total_paise), "items": [f"{ln['name']} × {ln['qty']}" for ln in o.lines],
             "placed_at": o.created_at.isoformat(timespec="minutes") if o.created_at else "",
             "history": o.history[-4:]}
        if include_payment and o.payment_status != "paid" and o.status == "payment_pending":
            v["pay"] = {"upi_link": self.payment_link(o), "amount": rupees(o.total_paise), "payee": o.meta.get("payee_name"),
                        "txn_ref": o.txn_ref}
            v["message"] = (f"Order saved. Pay {rupees(o.total_paise)} to {o.meta.get('payee_name')} in your UPI app "
                            f"(enter your PIN there). I'll confirm with {o.seller_name} as soon as it's paid.")
        return v

    def list_orders(self, user: User, open_only: bool = False, limit: int = 10) -> list[dict[str, Any]]:
        q = select(CommerceOrder).where(CommerceOrder.user_id == user.id)
        if open_only:
            q = q.where(CommerceOrder.status.in_(OPEN))
        return [self.order_view(o) for o in self.db.scalars(q.order_by(CommerceOrder.created_at.desc()).limit(limit)).all()]

    def status(self, user: User, order_id: str) -> dict[str, Any]:
        o = self._order(user, order_id)
        note = ""
        if o.payment_status == "paid" and o.status in OPEN:
            r = self.providers[o.source].status(self.db, user, o) if o.source in self.providers else {"status": o.status}
            self._move(o, r["status"], r.get("note", ""))
            note = r.get("note", "")
        self.db.commit()
        v = self.order_view(o, include_payment=True)
        v["note"] = note or ("Waiting for your UPI payment." if o.status == "payment_pending" else "")
        return v

    def cancel(self, user: User, order_id: str, reason: str = "") -> dict[str, Any]:
        o = self._order(user, order_id)
        if o.status not in OPEN:
            raise ToolError(f"This order is {o.status.replace('_', ' ')}; it can't be cancelled.")
        if o.payment_status != "paid":
            self._move(o, "cancelled", "cancelled before payment")
            if o.meta.get("shop_order_id"):
                so = self.db.get(ShopOrder, o.meta["shop_order_id"])
                if so:
                    so.status = "cancelled"
            self.db.commit()
            return {**self.order_view(o), "message": "Cancelled. Nothing was paid."}
        r = self.providers[o.source].cancel(self.db, user, o, _reason(reason, CANCEL_REASON, "005"))
        self._move(o, r["status"], reason or "cancelled by user")
        self.db.commit()
        return {**self.order_view(o), "message": r.get("note", "Cancelled.")}

    def return_item(self, user: User, order_id: str, item: str, qty: int = 1, reason: str = "") -> dict[str, Any]:
        o = self._order(user, order_id)
        if o.status != "delivered":
            raise ToolError("Returns open after delivery.")
        r = self.providers[o.source].return_item(self.db, user, o, item, qty, _reason(reason, RETURN_REASON, "001"), reason or "Not needed")
        self._move(o, r["status"], reason)
        self.db.commit()
        return {**self.order_view(o), "message": r.get("note", "")}
