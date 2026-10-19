"""ONDC (buyer app): search across seller apps on the open network, quote, confirm after UPI payment, track."""
from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from ...connectors.base import ToolError
from ...db import CommerceCart, CommerceOrder, User
from ..ondc import beckn
from ..ondc.client import OndcBuyer
from .base import PlaceResult, QuoteResult

GROCERY_WORDS = {"atta", "rice", "chawal", "dal", "oil", "tel", "sugar", "sakhar", "tea", "chai", "milk", "doodh", "masala",
                 "salt", "namak", "ghee", "besan", "poha", "biscuit", "soap", "detergent", "basmati", "toor", "wheat"}


def make_buyer(db: Session, settings: Any) -> OndcBuyer:
    if settings.ondc_mode == "sandbox":
        from ..ondc import sandbox
        sandbox.sandbox_settings_patch(settings)
        buyer = OndcBuyer(db, settings)
        buyer.http = __import__("httpx").Client(transport=sandbox.transport(settings, buyer.receive))
        buyer.registry.http = buyer.http
        return buyer
    return OndcBuyer(db, settings)


class OndcProvider:
    source = "ondc"
    label = "ONDC open network"

    def __init__(self, settings: Any):
        self.s = settings

    def available(self) -> bool:
        return self.s.ondc_mode == "sandbox" or bool(self.s.ondc_signing_private_key)

    def _domains(self, query: str) -> list[str]:
        q = set(query.lower().split())
        if q & GROCERY_WORDS:
            return ["ONDC:RET10"]
        return ["ONDC:RET10", "ONDC:RET14"]

    def search(self, db: Session, user: User, query: str, pincode: str, limit: int) -> list[dict[str, Any]]:
        loc = (user.profile or {}).get("home_location") or {}
        gps = f"{loc.get('lat', 20.7002)},{loc.get('lng', 77.0082)}"
        offers = make_buyer(db, self.s).search(query, pincode or user.pincode or "", gps, self._domains(query))
        if self.s.ondc_mode == "sandbox":
            for o in offers:
                o["demo"] = True
        return offers[:limit]

    def quote(self, db: Session, user: User, cart: CommerceCart, address: dict[str, Any]) -> QuoteResult:
        ref0 = cart.lines[0]["ref"]
        buyer = make_buyer(db, self.s)
        txn = ref0.get("transaction_id") or beckn.new_id()
        sel = beckn.parse_quote(buyer.call("select", ref0["domain"], txn, ref0["bpp_id"], ref0["bpp_uri"],
                                           beckn.select_message(ref0["provider_id"], ref0["location_id"], cart.lines, address)))
        if sel["error"] or not sel["serviceable"]:
            msg = (sel["error"] or {}).get("message") or "This seller doesn't deliver to your PIN code."
            raise ToolError(f"{cart.seller_name}: {msg}")
        fid = sel["fulfillment"]["id"] or "F1"
        init_msg = beckn.init_message(ref0["provider_id"], ref0["location_id"], cart.lines, address, fid, address.get("name", user.name))
        on_init = buyer.call("init", ref0["domain"], txn, ref0["bpp_id"], ref0["bpp_uri"], init_msg)
        q = beckn.parse_quote(on_init)
        if q["error"]:
            raise ToolError(f"{cart.seller_name}: {q['error'].get('message', 'could not prepare the order')}")
        prices = {b["item_id"]: b for b in q["breakup"] if b["kind"] == "item"}
        lines = []
        for ln in cart.lines:
            b = prices.get(ln["ref"]["item_id"])
            if b is None:
                raise ToolError(f"{ln['name']} is no longer available from {cart.seller_name}.")
            lines.append({**ln, "unit_price_paise": b["amount_paise"] // max(1, int(b["qty"] or ln["qty"]))})
        breakup = [{"title": b["title"], "kind": b["kind"], "amount_paise": b["amount_paise"]} for b in q["breakup"]]
        returns = "; ".join(f"{ln['name']}: {'returnable within ' + ln.get('return_window', '').replace('P', '').replace('D', ' days') if ln.get('returnable') else 'not returnable'}"
                            for ln in cart.lines)
        disclosures = {"seller": cart.seller_name, "seller_app": cart.meta.get("seller_app", ""), "network": "ONDC",
                       "delivery_eta": q["fulfillment"]["eta"] or sel["fulfillment"]["eta"], "returns": returns,
                       "country_of_origin": ", ".join(sorted({ln.get("country_of_origin") or "not stated" for ln in cart.lines})),
                       "customer_care": cart.meta.get("customer_care", ""), "paid_to": "Newtika (ONDC buyer app) — settled to the seller"}
        raw_quote = ((on_init.get("message") or {}).get("order") or {}).get("quote") or {}
        settlement = (q["payment"].get("@ondc/org/settlement_details") or [])
        demo = self.s.ondc_mode == "sandbox"
        if demo:
            disclosures["paid_to"] = "Nobody: sandbox network, no money moves"
        return QuoteResult(q["total_paise"], breakup, lines, disclosures,
                           payee_name="Sandbox (no money)" if demo else self.s.collection_name,
                           payee_vpa="" if demo else self.s.collection_vpa,
                           meta={"demo": demo, "txn": txn, "init_order": init_msg["order"], "quote_raw": raw_quote, "settlement": settlement,
                                 "domain": ref0["domain"], "bpp_id": ref0["bpp_id"], "bpp_uri": ref0["bpp_uri"]})

    def place(self, db: Session, user: User, order: CommerceOrder, payment_ref: str) -> PlaceResult:
        m = order.meta
        oid = f"SNT-{order.id}"
        msg = beckn.confirm_message(oid, m["init_order"], m["quote_raw"], order.total_paise, payment_ref, m["settlement"])
        res = beckn.parse_order(make_buyer(db, self.s).call("confirm", m["domain"], m["txn"], m["bpp_id"], m["bpp_uri"], msg))
        if res["error"]:
            raise ToolError(f"The seller couldn't accept the order: {res['error'].get('message', '')}. Your refund will be started.")
        return PlaceResult(res["external_id"] or oid, res["status"])

    def _call(self, db: Session, order: CommerceOrder, action: str, message: dict[str, Any]) -> dict[str, Any]:
        m = order.meta
        return beckn.parse_order(make_buyer(db, self.s).call(action, m["domain"], m["txn"], m["bpp_id"], m["bpp_uri"], message))

    def status(self, db: Session, user: User, order: CommerceOrder) -> dict[str, Any]:
        r = self._call(db, order, "status", {"order_id": order.external_id})
        if r["error"]:
            return {"status": order.status, "note": r["error"].get("message", "")}
        note = f"Seller status: {r['fulfillment_state'] or r['order_state']}"
        if r["agent"]:
            note += f". Delivery partner {r['agent'].get('name', '')} {r['agent'].get('phone', '')}"
        return {"status": r["status"], "note": note}

    def cancel(self, db: Session, user: User, order: CommerceOrder, reason_id: str) -> dict[str, Any]:
        r = self._call(db, order, "cancel", beckn.cancel_message(order.external_id, reason_id))
        if r["error"]:
            raise ToolError(f"{order.seller_name}: {r['error'].get('message', 'cannot cancel now')}")
        return {"status": "cancelled", "note": "Cancelled on ONDC. Refund goes back to your UPI account."}

    def return_item(self, db: Session, user: User, order: CommerceOrder, item_ref: str, qty: int, reason_id: str,
                    reason: str) -> dict[str, Any]:
        line = next((ln for ln in order.lines if ln["ref"].get("item_id") == item_ref or ln["name"].lower() == item_ref.lower()), None)
        if line is None:
            raise ToolError("Which item do you want to return?")
        if not line.get("returnable"):
            raise ToolError(f"{line['name']} is marked not returnable by the seller.")
        r = self._call(db, order, "update", beckn.return_message(order.external_id, line["ref"]["item_id"], qty, reason_id, reason))
        if r["error"]:
            raise ToolError(f"{order.seller_name}: {r['error'].get('message', 'return not accepted')}")
        return {"status": "return_requested", "note": "Return requested. The seller will arrange pickup; refund after the check."}
