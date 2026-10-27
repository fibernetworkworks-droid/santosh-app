"""In-process stand-in for the ONDC network: registry, gateway and two seller apps (Akola grocery, electronics).

Used when BAZAR_ONDC_MODE=sandbox. Every request from Santosh is signature-checked with Santosh's public key, and
every callback is signed with the seller app's own key and delivered to OndcBuyer.receive — so the real signing,
verification, message building and parsing code all run.
"""
from __future__ import annotations

import copy
import json
from collections.abc import Callable
from typing import Any

import httpx

from . import beckn
from .crypto import generate_keys, load_signing_key, parse_auth_header, sign_body, verify_body

GATEWAY = "gateway.sandbox.ondc"
_KEYS = {GATEWAY: generate_keys(), "bpp.akolafresh.sandbox": generate_keys(), "bpp.vidarbhatech.sandbox": generate_keys()}

_SELLERS: dict[str, dict[str, Any]] = {
    "bpp.akolafresh.sandbox": {
        "domain": "ONDC:RET10", "app": "Akola Fresh (sandbox seller app)",
        "provider": {"id": "P-AF-1", "name": "Akola Fresh Mart", "city": "Akola", "location": "L-AF-1",
                     "serves_prefix": "444", "delivery": 3000, "free_above": 49900, "packing": 1000},
        "items": [
            ("AF-ATTA5", "Whole wheat atta 5 kg", 26500, 28000, "5", "kilogram", "Vidarbha Mills", True),
            ("AF-RICE1", "Basmati rice 1 kg", 12900, 15000, "1", "kilogram", "Vidarbha Mills", True),
            ("AF-TOOR1", "Toor dal 1 kg", 15800, 17000, "1", "kilogram", "Akola Pulses", True),
            ("AF-OIL1", "Groundnut oil 1 L", 19500, 21000, "1", "litre", "Shegaon Oils", True),
            ("AF-SUGAR1", "Sugar 1 kg", 4600, 5000, "1", "kilogram", "Paras Sugar", False),
            ("AF-TEA250", "Tea powder 250 g", 13000, 14500, "250", "gram", "Pune Tea Co", True),
            ("AF-MILK1", "Toned milk 1 L", 5800, 5800, "1", "litre", "Akola Dairy", False),
        ],
    },
    "bpp.vidarbhatech.sandbox": {
        "domain": "ONDC:RET14", "app": "Vidarbha Tech (sandbox seller app)",
        "provider": {"id": "P-VT-1", "name": "Vidarbha Electronics", "city": "Nagpur", "location": "L-VT-1",
                     "serves_prefix": "", "delivery": 4900, "free_above": 99900, "packing": 0},
        "items": [
            ("VT-BUDS", "Wireless earbuds (Bluetooth 5.3)", 119900, 249900, "1", "unit", "SoundLeaf Audio", True),
            ("VT-SPK10", "Bluetooth speaker 10 W", 149900, 299900, "1", "unit", "SoundLeaf Audio", True),
            ("VT-CHG25", "USB-C fast charger 25 W", 69900, 129900, "1", "unit", "VoltKart", True),
            ("VT-LED4", "LED bulb 9 W, pack of 4", 39900, 59900, "4", "unit", "Prakash Lighting", False),
        ],
    },
}
STATE: dict[str, Any] = {"orders": {}}


def reset() -> None:
    STATE["orders"] = {}


def _sign(sub: str, payload: dict[str, Any]) -> tuple[str, bytes]:
    body = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode()
    return sign_body(body, sub, f"{sub}-k1", _KEYS[sub].signing_private), body


def registry_rows(settings: Any) -> list[dict[str, Any]]:
    rows = [{"subscriber_id": s, "ukId": f"{s}-k1", "signing_public_key": k.signing_public,
             "type": "BG" if s == GATEWAY else "BPP"} for s, k in _KEYS.items()]
    pub = settings.ondc_signing_public_key or _derive_public(settings.ondc_signing_private_key)
    rows.append({"subscriber_id": settings.ondc_subscriber_id, "ukId": settings.ondc_unique_key_id,
                 "signing_public_key": pub, "type": "BAP"})
    return rows


def _derive_public(private_b64: str) -> str:
    from cryptography.hazmat.primitives import serialization

    from .crypto import b64e
    return b64e(load_signing_key(private_b64).public_key().public_bytes(serialization.Encoding.Raw,
                                                                        serialization.PublicFormat.Raw))


def _catalog(bpp: str, query: str) -> dict[str, Any]:
    s = _SELLERS[bpp]
    p = s["provider"]
    words = [w for w in query.lower().split() if len(w) > 2]
    items = []
    for iid, name, price, mrp, mval, unit, maker, ret in s["items"]:
        if words and not any(w in name.lower() for w in words):
            continue
        items.append({
            "id": iid, "location_id": p["location"], "category_id": "Foodgrains" if s["domain"] == "ONDC:RET10" else "Audio",
            "descriptor": {"name": name, "short_desc": name, "images": [f"https://{bpp}/img/{iid}.png"]},
            "price": {"currency": "INR", "value": beckn.rupee_str(price), "maximum_value": beckn.rupee_str(mrp)},
            "quantity": {"available": {"count": "99"}, "maximum": {"count": "10"},
                         "unitized": {"measure": {"unit": unit, "value": mval}}},
            "fulfillment_id": "F1", "@ondc/org/returnable": ret, "@ondc/org/cancellable": True,
            "@ondc/org/return_window": "P7D" if ret else "PT0S", "@ondc/org/seller_pickup_return": ret,
            "@ondc/org/time_to_ship": "PT45M" if s["domain"] == "ONDC:RET10" else "P2D",
            "@ondc/org/available_on_cod": False,
            "@ondc/org/contact_details_consumer_care": f"{p['name']}, care@{bpp}, 1800000000",
            "@ondc/org/statutory_reqs_packaged_commodities": {
                "manufacturer_or_packer_name": maker, "manufacturer_or_packer_address": p["city"],
                "common_or_generic_name_of_commodity": name, "net_quantity_or_measure_of_commodity_in_pkg": f"{mval} {unit}",
                "month_year_of_manufacture_packing_import": "09/2026", "imported_product_country_of_origin": "IND"},
        })
    return {"bpp/descriptor": {"name": s["app"]}, "bpp/fulfillments": [{"id": "F1", "type": "Delivery"}],
            "bpp/providers": [{"id": p["id"], "descriptor": {"name": p["name"]},
                               "locations": [{"id": p["location"], "address": {"city": p["city"]}}],
                               "fulfillments": [{"id": "F1", "type": "Delivery"}], "items": items}]}


def _quote(bpp: str, req_items: list[dict[str, Any]], pincode: str) -> tuple[dict[str, Any], bool]:
    s = _SELLERS[bpp]
    p = s["provider"]
    by = {i[0]: i for i in s["items"]}
    breakup, subtotal = [], 0
    for it in req_items:
        row = by.get(it["id"])
        if not row:
            continue
        n = int((it.get("quantity") or {}).get("count", 1))
        line = row[2] * n
        subtotal += line
        breakup.append({"@ondc/org/item_id": row[0], "@ondc/org/item_quantity": {"count": n}, "title": row[1],
                        "@ondc/org/title_type": "item", "price": {"currency": "INR", "value": beckn.rupee_str(line)},
                        "item": {"price": {"currency": "INR", "value": beckn.rupee_str(row[2])}}})
    delivery = 0 if subtotal >= p["free_above"] else p["delivery"]
    breakup.append({"@ondc/org/item_id": "F1", "title": "Delivery charges", "@ondc/org/title_type": "delivery",
                    "price": {"currency": "INR", "value": beckn.rupee_str(delivery)}})
    if p["packing"]:
        breakup.append({"@ondc/org/item_id": "F1", "title": "Packing charges", "@ondc/org/title_type": "packing",
                        "price": {"currency": "INR", "value": beckn.rupee_str(p["packing"])}})
    total = subtotal + delivery + p["packing"]
    serviceable = not p["serves_prefix"] or str(pincode).startswith(p["serves_prefix"])
    return {"price": {"currency": "INR", "value": beckn.rupee_str(total)}, "breakup": breakup, "ttl": "PT15M"}, serviceable


def handler_factory(settings: Any, deliver: Callable[[str, str, bytes], dict[str, Any]]) -> Callable[[httpx.Request], httpx.Response]:
    def bap_public() -> str:
        return settings.ondc_signing_public_key or _derive_public(settings.ondc_signing_private_key)

    def respond(bpp: str, action: str, ctx: dict[str, Any], message: dict[str, Any], error: dict[str, Any] | None = None) -> None:
        c = dict(ctx, action=action, bpp_id=bpp, bpp_uri=f"https://{bpp}", timestamp=beckn.now_iso())
        payload: dict[str, Any] = {"context": c, "message": message}
        if error:
            payload["error"] = error
        header, body = _sign(bpp, payload)
        deliver(action, header, body)

    def handler(req: httpx.Request) -> httpx.Response:
        host, path = req.url.host, req.url.path
        if path.endswith("/lookup"):
            q = json.loads(req.content or b"{}")
            rows = [r for r in registry_rows(settings) if r["subscriber_id"] == q.get("subscriber_id")]
            return httpx.Response(200, json=rows)
        auth = req.headers.get("authorization", "")
        p = parse_auth_header(auth)
        if p.get("subscriber_id") != settings.ondc_subscriber_id or not verify_body(auth, req.content, bap_public()):
            return httpx.Response(401, json={"message": {"ack": {"status": "NACK"}},
                                             "error": {"type": "POLICY-ERROR", "code": "10001", "message": "Invalid signature"}})
        payload = json.loads(req.content)
        ctx, msg = payload["context"], payload["message"]
        action = ctx["action"]
        if host == GATEWAY and action == "search":
            q = ((msg.get("intent") or {}).get("item") or {}).get("descriptor", {}).get("name", "")
            for bpp, s in _SELLERS.items():
                if s["domain"] == ctx["domain"]:
                    cat = _catalog(bpp, q)
                    if cat["bpp/providers"][0]["items"]:
                        respond(bpp, "on_search", ctx, {"catalog": cat})
            return httpx.Response(200, json={"message": {"ack": {"status": "ACK"}}})
        bpp = host
        if bpp not in _SELLERS:
            return httpx.Response(404, json={"error": {"message": "unknown seller app"}})
        s = _SELLERS[bpp]
        order = msg.get("order") or {}
        if action in ("select", "init"):
            pin = ""
            for f in order.get("fulfillments", []):
                pin = (((f.get("end") or {}).get("location") or {}).get("address") or {}).get("area_code", pin)
            quote, ok = _quote(bpp, order.get("items", []), pin)
            out = {"provider": order.get("provider"), "items": [{"id": i["id"], "fulfillment_id": "F1"} for i in order.get("items", [])],
                   "fulfillments": [{"id": "F1", "@ondc/org/provider_name": s["provider"]["name"], "tracking": False,
                                     "@ondc/org/category": "Immediate Delivery" if s["domain"] == "ONDC:RET10" else "Standard Delivery",
                                     "@ondc/org/TAT": "PT60M" if s["domain"] == "ONDC:RET10" else "P3D",
                                     "state": {"descriptor": {"code": "Serviceable" if ok else "Non-serviceable"}}}],
                   "quote": quote}
            if action == "init":
                out["billing"] = order.get("billing")
                out["payment"] = {"type": "ON-ORDER", "collected_by": "BAP", "@ondc/org/buyer_app_finder_fee_type": "percent",
                                  "@ondc/org/buyer_app_finder_fee_amount": "3", "@ondc/org/settlement_basis": "delivery",
                                  "@ondc/org/settlement_window": "P1D", "@ondc/org/withholding_amount": "0.00",
                                  "@ondc/org/settlement_details": [{"settlement_counterparty": "seller-app",
                                                                    "settlement_phase": "sale-amount", "settlement_type": "upi",
                                                                    "upi_address": f"{bpp.split('.')[1]}@oksbi",
                                                                    "beneficiary_name": s["provider"]["name"]}]}
            err = None if ok else {"type": "DOMAIN-ERROR", "code": "30009", "message": "Location not serviceable"}
            respond(bpp, "on_" + action, ctx, {"order": out}, err)
        elif action == "confirm":
            o = copy.deepcopy(order)
            o["state"] = "Accepted"
            for f in o.get("fulfillments", []):
                f["state"] = {"descriptor": {"code": "Pending"}}
                f["tracking"] = False
            STATE["orders"][o["id"]] = {"order": o, "step": 0, "bpp": bpp}
            respond(bpp, "on_confirm", ctx, {"order": o})
        elif action == "status":
            rec = STATE["orders"].get(msg.get("order_id"))
            if rec is None:
                respond(bpp, "on_status", ctx, {}, {"type": "DOMAIN-ERROR", "code": "30004", "message": "Order not found"})
            else:
                flow = ["Pending", "Packed", "Order-picked-up", "Out-for-delivery", "Order-delivered"]
                o = rec["order"]
                if o["state"] not in ("Cancelled",) and not any(
                        ((f.get("state") or {}).get("descriptor") or {}).get("code", "").startswith("Return") for f in o["fulfillments"]):
                    rec["step"] = min(rec["step"] + 1, len(flow) - 1)
                    code = flow[rec["step"]]
                    o["state"] = "Completed" if code == "Order-delivered" else "In-progress"
                    for f in o["fulfillments"]:
                        f["state"] = {"descriptor": {"code": code}}
                        if code == "Out-for-delivery":
                            f["agent"] = {"name": "Sandeep (delivery)", "phone": "9800000099"}
                respond(bpp, "on_status", ctx, {"order": o})
        elif action == "cancel":
            rec = STATE["orders"].get(msg.get("order_id"))
            if rec is None:
                respond(bpp, "on_cancel", ctx, {}, {"type": "DOMAIN-ERROR", "code": "30004", "message": "Order not found"})
            elif rec["step"] >= 2:
                respond(bpp, "on_cancel", ctx, {"order": rec["order"]},
                        {"type": "DOMAIN-ERROR", "code": "30010", "message": "Order already shipped; cancellation not allowed"})
            else:
                rec["order"]["state"] = "Cancelled"
                for f in rec["order"]["fulfillments"]:
                    f["state"] = {"descriptor": {"code": "Cancelled"}}
                respond(bpp, "on_cancel", ctx, {"order": rec["order"]})
        elif action == "update":
            oid = (msg.get("order") or {}).get("id")
            rec = STATE["orders"].get(oid)
            if rec is None:
                respond(bpp, "on_update", ctx, {}, {"type": "DOMAIN-ERROR", "code": "30004", "message": "Order not found"})
            else:
                rec["order"]["fulfillments"].append({"id": "R1", "type": "Return",
                                                     "state": {"descriptor": {"code": "Return_Initiated"}}})
                respond(bpp, "on_update", ctx, {"order": rec["order"]})
        else:
            return httpx.Response(400, json={"error": {"message": f"unsupported {action}"}})
        return httpx.Response(200, json={"message": {"ack": {"status": "ACK"}}})

    return handler


def transport(settings: Any, deliver: Callable[[str, str, bytes], dict[str, Any]]) -> httpx.MockTransport:
    return httpx.MockTransport(handler_factory(settings, deliver))


def sandbox_settings_patch(settings: Any) -> None:
    """Point the client at the sandbox gateway/registry and create a dev key pair if none is set."""
    settings.ondc_gateway_url = f"https://{GATEWAY}/search"
    settings.ondc_registry_url = "https://registry.sandbox.ondc/v2.0/lookup"
    if not settings.ondc_signing_private_key:
        k = generate_keys()
        settings.ondc_signing_private_key, settings.ondc_signing_public_key = k.signing_private, k.signing_public
