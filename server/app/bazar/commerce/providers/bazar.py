"""Santosh Bazar shops (Newtika's own rails): local shops in the user's PIN code, UPI straight to the shop."""
from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ...connectors.base import ToolError
from ...db import CommerceCart, CommerceOrder, Shop, ShopItem, ShopOrder, User
from .base import PlaceResult, QuoteResult, words

STATUS = {"placed": "placed", "accepted": "accepted", "ready": "packed", "delivered": "delivered", "cancelled": "cancelled"}


class BazarProvider:
    source = "bazar"
    label = "Santosh Bazar (local shops)"

    def available(self) -> bool:
        return True

    def _shops(self, db: Session, user: User) -> list[Shop]:
        shops = db.scalars(select(Shop).where(Shop.active.is_(True))).all()
        pin = user.pincode or ""
        return [s for s in shops if (pin and pin in (s.pincodes or [])) or (user.city and s.city.lower() == (user.city or "").lower())]

    def search(self, db: Session, user: User, query: str, pincode: str, limit: int) -> list[dict[str, Any]]:
        q = words(query)
        out = []
        for shop in self._shops(db, user):
            for it in shop.items:
                if it.kind != "product":
                    continue
                hay = " ".join([it.name.lower(), *[a.lower() for a in it.aliases or []]])
                if q and not any(w in hay for w in q):
                    continue
                out.append({
                    "source": self.source, "ref": {"shop_id": shop.id, "item_id": it.id},
                    "name": it.name, "brand": "", "description": "", "image": "",
                    "price_paise": it.price_paise, "mrp_paise": it.price_paise,
                    "pack": f"per {it.unit}", "in_stock": bool(it.in_stock), "max_qty": 50,
                    "seller": {"name": shop.name, "key": f"bazar::{shop.id}", "city": shop.city, "network": "Santosh Bazar"},
                    "delivery": {"slots": shop.slots[:2], "fee_paise": shop.delivery_fee_paise},
                    "returnable": False, "return_window": "", "cancellable": True, "cod": False,
                    "country_of_origin": "", "customer_care": f"{shop.name}, +{shop.owner_phone}", "url": "",
                    "buy_mode": "order", "sponsored": False,
                })
        return out[:limit]

    def quote(self, db: Session, user: User, cart: CommerceCart, address: dict[str, Any]) -> QuoteResult:
        shop = db.get(Shop, cart.seller_key.split("::", 1)[1])
        if shop is None or not shop.active:
            raise ToolError("This shop is not taking orders right now.")
        lines, breakup, sub = [], [], 0
        for ln in cart.lines:
            it = db.get(ShopItem, ln["ref"]["item_id"])
            if it is None or not it.in_stock:
                raise ToolError(f"{ln['name']} is out of stock at {shop.name}.")
            amt = it.price_paise * int(ln["qty"])
            sub += amt
            lines.append({**ln, "unit_price_paise": it.price_paise})
            breakup.append({"title": f"{it.name} × {ln['qty']}", "kind": "item", "amount_paise": amt})
        if sub < shop.min_order_paise:
            raise ToolError(f"{shop.name} needs a minimum order of ₹{shop.min_order_paise / 100:.0f}.")
        if shop.delivery_fee_paise:
            breakup.append({"title": "Delivery", "kind": "delivery", "amount_paise": shop.delivery_fee_paise})
        total = sub + shop.delivery_fee_paise
        return QuoteResult(total, breakup, lines, payee_name=shop.name, payee_vpa=shop.upi_id,
                           disclosures={"seller": shop.name, "seller_city": shop.city, "delivery_slot": (shop.slots or ["-"])[0],
                                        "returns": "Talk to the shop for returns", "customer_care": f"+{shop.owner_phone}"},
                           meta={"slot": (shop.slots or [""])[0]})

    def place(self, db: Session, user: User, order: CommerceOrder, payment_ref: str) -> PlaceResult:
        so = db.get(ShopOrder, order.meta.get("shop_order_id", ""))
        if so is None:
            raise ToolError("Shop order missing")
        so.payment_status = "paid"
        return PlaceResult(so.id, "accepted" if so.status == "accepted" else "placed")

    def create_shop_order(self, db: Session, user: User, cart: CommerceCart, total: int, slot: str, txn_ref: str) -> ShopOrder:
        so = ShopOrder(shop_id=cart.seller_key.split("::", 1)[1], user_id=user.id, kind="order",
                       lines=[{"label": f"{ln['name']} × {ln['qty']}", "price_paise": ln["unit_price_paise"] * ln["qty"]}
                              for ln in cart.lines],
                       total_paise=total, slot=slot, address=(user.profile or {}).get("address", ""), status="placed",
                       payment_status="unpaid", txn_ref=txn_ref)
        db.add(so)
        db.flush()
        return so

    def status(self, db: Session, user: User, order: CommerceOrder) -> dict[str, Any]:
        so = db.get(ShopOrder, order.meta.get("shop_order_id", ""))
        if so is None:
            return {"status": order.status}
        return {"status": STATUS.get(so.status, order.status), "note": f"Shop status: {so.status}, slot {so.slot or '-'}"}

    def cancel(self, db: Session, user: User, order: CommerceOrder, reason_id: str) -> dict[str, Any]:
        so = db.get(ShopOrder, order.meta.get("shop_order_id", ""))
        if so and so.status in ("ready", "delivered"):
            raise ToolError("The shop has already packed or delivered this order. Call the shop to cancel.")
        if so:
            so.status = "cancelled"
        return {"status": "cancelled", "note": "Cancelled. If you already paid, the shop refunds you by UPI."}

    def return_item(self, db: Session, user: User, order: CommerceOrder, item_ref: str, qty: int, reason_id: str,
                    reason: str) -> dict[str, Any]:
        return {"status": order.status, "note": "Returns at Bazar shops are handled by the shop; I've noted your request."}
