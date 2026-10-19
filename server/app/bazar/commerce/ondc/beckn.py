"""ONDC retail (Beckn) message builders and parsers — retail API contract 1.2.x.

Field names follow the ONDC retail spec; validate every flow with ONDC's Pramaan log-verification utility before
going live (domain codes, enums and tag lists change between minor versions).
"""
from __future__ import annotations

import datetime as dt
import uuid
from typing import Any

# Retail domains (ONDC retail API contract)
DOMAINS = {
    "ONDC:RET10": "Grocery", "ONDC:RET11": "Food & beverage", "ONDC:RET12": "Fashion", "ONDC:RET13": "Beauty & personal care",
    "ONDC:RET14": "Electronics", "ONDC:RET15": "Appliances", "ONDC:RET16": "Home & kitchen", "ONDC:RET18": "Health & wellness",
}
CANCEL_REASONS = {"001": "Price of one or more items have changed", "002": "Product available at lower price",
                  "003": "Order in pending shipment / delivery state for too long", "005": "Ordered by mistake",
                  "006": "Delivery address changed"}
RETURN_REASONS = {"001": "Buyer does not need it anymore", "002": "Item does not match the description",
                  "003": "Item is damaged", "004": "Wrong item delivered", "005": "Item is missing / short quantity"}
# fulfillment state codes -> Santosh order status
FULFILLMENT_STATE = {"Pending": "accepted", "Packed": "packed", "Agent-assigned": "packed", "Order-picked-up": "shipped",
                     "Out-for-delivery": "out_for_delivery", "Order-delivered": "delivered", "Cancelled": "cancelled",
                     "Return_Initiated": "return_requested", "Return_Approved": "return_requested",
                     "Return_Picked": "return_requested", "Return_Delivered": "returned", "Liquidated": "returned"}
ORDER_STATE = {"Created": "placed", "Accepted": "accepted", "In-progress": "packed", "Completed": "delivered",
               "Cancelled": "cancelled"}


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def new_id() -> str:
    return str(uuid.uuid4())


def context(action: str, *, domain: str, bap_id: str, bap_uri: str, city: str, core_version: str, transaction_id: str,
            bpp_id: str = "", bpp_uri: str = "", message_id: str | None = None, ttl: str = "PT30S") -> dict[str, Any]:
    c = {"domain": domain, "action": action, "country": "IND", "city": city, "core_version": core_version,
         "bap_id": bap_id, "bap_uri": bap_uri, "transaction_id": transaction_id,
         "message_id": message_id or new_id(), "timestamp": now_iso(), "ttl": ttl}
    if bpp_id:
        c["bpp_id"], c["bpp_uri"] = bpp_id, bpp_uri
    return c


def paise(value: Any) -> int:
    try:
        return int(round(float(value) * 100))
    except (TypeError, ValueError):
        return 0


def rupee_str(p: int) -> str:
    return f"{p / 100:.2f}"


# ------------------------------------------------------------------ search
def search_message(query: str, pincode: str, gps: str, finder_fee_percent: str) -> dict[str, Any]:
    return {"intent": {
        "item": {"descriptor": {"name": query}},
        "fulfillment": {"type": "Delivery", "end": {"location": {"gps": gps, "address": {"area_code": pincode}}}},
        "payment": {"@ondc/org/buyer_app_finder_fee_type": "percent", "@ondc/org/buyer_app_finder_fee_amount": finder_fee_percent},
        "tags": [{"code": "bap_terms", "list": [{"code": "static_terms", "value": ""},
                                                 {"code": "static_terms_new", "value": "https://santosh.ainewtika.com/terms"}]}],
    }}


def parse_catalog(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """on_search -> normalised offers."""
    ctx = payload.get("context", {})
    catalog = (payload.get("message") or {}).get("catalog") or {}
    bpp_name = ((catalog.get("bpp/descriptor") or {}).get("name")) or ctx.get("bpp_id", "")
    out = []
    for prov in catalog.get("bpp/providers", []) or []:
        pname = (prov.get("descriptor") or {}).get("name") or bpp_name
        loc = (prov.get("locations") or [{}])[0]
        city = ((loc.get("address") or {}).get("city")) or ""
        tts = {}
        for f in prov.get("fulfillments", []) or []:
            tts[f.get("id")] = f
        for it in prov.get("items", []) or []:
            price = it.get("price") or {}
            qty = it.get("quantity") or {}
            avail = int(((qty.get("available") or {}).get("count")) or 0)
            maxq = int(((qty.get("maximum") or {}).get("count")) or 0)
            measure = ((qty.get("unitized") or {}).get("measure")) or {}
            stat = it.get("@ondc/org/statutory_reqs_packaged_commodities") or {}
            desc = it.get("descriptor") or {}
            out.append({
                "source": "ondc",
                "ref": {"bpp_id": ctx.get("bpp_id", ""), "bpp_uri": ctx.get("bpp_uri", ""), "domain": ctx.get("domain", ""),
                        "provider_id": prov.get("id", ""), "location_id": it.get("location_id") or loc.get("id", ""),
                        "item_id": it.get("id", "")},
                "name": desc.get("name", ""), "brand": stat.get("manufacturer_or_packer_name", ""),
                "description": desc.get("short_desc", ""),
                "image": (desc.get("images") or [""])[0],
                "price_paise": paise(price.get("value")), "mrp_paise": paise(price.get("maximum_value") or price.get("value")),
                "pack": f"{measure.get('value', '')} {measure.get('unit', '')}".strip(),
                "in_stock": avail > 0, "max_qty": maxq or 10,
                "seller": {"name": pname, "key": f"{ctx.get('bpp_id', '')}::{prov.get('id', '')}", "city": city,
                           "network": "ONDC", "seller_app": bpp_name},
                "delivery": {"time_to_ship": it.get("@ondc/org/time_to_ship", "")},
                "returnable": bool(it.get("@ondc/org/returnable", False)),
                "return_window": it.get("@ondc/org/return_window", ""),
                "cancellable": bool(it.get("@ondc/org/cancellable", False)),
                "cod": bool(it.get("@ondc/org/available_on_cod", False)),
                "country_of_origin": stat.get("imported_product_country_of_origin", ""),
                "customer_care": it.get("@ondc/org/contact_details_consumer_care", ""),
                "buy_mode": "order", "sponsored": False,
            })
    return out


# ------------------------------------------------------------------ select / init / confirm
def _end(address: dict[str, Any]) -> dict[str, Any]:
    return {"location": {"gps": address.get("gps", ""), "address": {
        "name": address.get("name", ""), "building": address.get("line1", ""), "locality": address.get("locality", ""),
        "city": address.get("city", ""), "state": address.get("state", ""), "country": "IND",
        "area_code": address.get("pincode", "")}},
        "contact": {"phone": address.get("phone", ""), "email": address.get("email", "")}}


def select_message(provider_id: str, location_id: str, lines: list[dict[str, Any]], address: dict[str, Any]) -> dict[str, Any]:
    return {"order": {
        "provider": {"id": provider_id, "locations": [{"id": location_id}]},
        "items": [{"id": ln["ref"]["item_id"], "location_id": location_id, "quantity": {"count": ln["qty"]}} for ln in lines],
        "fulfillments": [{"end": {"location": {"gps": address.get("gps", ""), "address": {"area_code": address.get("pincode", "")}}}}],
    }}


def parse_quote(payload: dict[str, Any]) -> dict[str, Any]:
    """on_select / on_init -> {total_paise, breakup, fulfillment, serviceable, items, payment}"""
    msg = (payload.get("message") or {}).get("order") or {}
    q = msg.get("quote") or {}
    breakup = []
    for b in q.get("breakup", []) or []:
        kind = b.get("@ondc/org/title_type", "item")
        breakup.append({"title": b.get("title", kind), "kind": kind, "item_id": b.get("@ondc/org/item_id", ""),
                        "qty": ((b.get("@ondc/org/item_quantity") or {}).get("count")),
                        "amount_paise": paise((b.get("price") or {}).get("value"))})
    fl = (msg.get("fulfillments") or [{}])[0]
    state = ((fl.get("state") or {}).get("descriptor") or {}).get("code", "Serviceable")
    return {"total_paise": paise((q.get("price") or {}).get("value")), "breakup": breakup,
            "fulfillment": {"id": fl.get("id", ""), "eta": fl.get("@ondc/org/TAT", ""), "type": fl.get("@ondc/org/category", ""),
                            "provider_name": fl.get("@ondc/org/provider_name", "")},
            "serviceable": state != "Non-serviceable", "items": msg.get("items", []), "payment": msg.get("payment") or {},
            "quote_ttl": q.get("ttl", ""), "error": payload.get("error")}


def init_message(provider_id: str, location_id: str, lines: list[dict[str, Any]], address: dict[str, Any],
                 fulfillment_id: str, billing_name: str) -> dict[str, Any]:
    ts = now_iso()
    return {"order": {
        "provider": {"id": provider_id, "locations": [{"id": location_id}]},
        "items": [{"id": ln["ref"]["item_id"], "fulfillment_id": fulfillment_id, "quantity": {"count": ln["qty"]}} for ln in lines],
        "billing": {"name": billing_name, "address": {"name": billing_name, "building": address.get("line1", ""),
                                                      "locality": address.get("locality", ""), "city": address.get("city", ""),
                                                      "state": address.get("state", ""), "country": "IND",
                                                      "area_code": address.get("pincode", "")},
                    "phone": address.get("phone", ""), "email": address.get("email", ""), "created_at": ts, "updated_at": ts},
        "fulfillments": [{"id": fulfillment_id, "type": "Delivery", "end": _end(address)}],
    }}


def confirm_message(order_id: str, init_order: dict[str, Any], quote_raw: dict[str, Any], amount_paise: int,
                    payment_ref: str, settlement: list[dict[str, Any]]) -> dict[str, Any]:
    ts = now_iso()
    order = dict(init_order)
    order.update({
        "id": order_id, "state": "Created", "quote": quote_raw,
        "payment": {"uri": "", "tl_method": "http/get", "status": "PAID", "type": "ON-ORDER", "collected_by": "BAP",
                    "params": {"amount": rupee_str(amount_paise), "currency": "INR", "transaction_id": payment_ref},
                    "@ondc/org/buyer_app_finder_fee_type": "percent", "@ondc/org/buyer_app_finder_fee_amount": "3",
                    "@ondc/org/settlement_basis": "delivery", "@ondc/org/settlement_window": "P1D",
                    "@ondc/org/withholding_amount": "0.00", "@ondc/org/settlement_details": settlement},
        "created_at": ts, "updated_at": ts,
    })
    return {"order": order}


def parse_order(payload: dict[str, Any]) -> dict[str, Any]:
    """on_confirm / on_status / on_cancel / on_update -> {external_id, status, tracking, raw_state}"""
    o = (payload.get("message") or {}).get("order") or {}
    fl = (o.get("fulfillments") or [{}])
    fstate = ""
    for f in fl:
        code = ((f.get("state") or {}).get("descriptor") or {}).get("code", "")
        if code:
            fstate = code
    status = FULFILLMENT_STATE.get(fstate) or ORDER_STATE.get(o.get("state", ""), "placed")
    if o.get("state") == "Cancelled":
        status = "cancelled"
    agent = {}
    for f in fl:
        if f.get("agent"):
            agent = f["agent"]
    return {"external_id": o.get("id", ""), "status": status, "order_state": o.get("state", ""), "fulfillment_state": fstate,
            "agent": agent, "tracking": any(f.get("tracking") for f in fl), "error": payload.get("error")}


def cancel_message(order_id: str, reason_id: str) -> dict[str, Any]:
    return {"order_id": order_id, "cancellation_reason_id": reason_id}


def return_message(order_id: str, item_id: str, qty: int, reason_id: str, reason_desc: str) -> dict[str, Any]:
    return {"update_target": "item", "order": {"id": order_id, "state": "Completed", "items": [], "fulfillments": [{
        "type": "Return",
        "tags": [{"code": "return_request", "list": [
            {"code": "id", "value": new_id()[:8]}, {"code": "item_id", "value": item_id},
            {"code": "item_quantity", "value": str(qty)}, {"code": "reason_id", "value": reason_id},
            {"code": "reason_desc", "value": reason_desc}, {"code": "ttl_approval", "value": "PT24H"},
            {"code": "ttl_reverseqc", "value": "P3D"}, {"code": "images", "value": ""}]}]}]}}
