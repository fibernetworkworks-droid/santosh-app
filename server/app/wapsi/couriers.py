"""Reverse pickup through official courier-aggregator APIs, behind one small interface.

- Shiprocket (API user made by her in Shiprocket > Settings > API; docs https://apidocs.shiprocket.in, base
  https://apiv2.shiprocket.in): POST /v1/external/auth/login {email, password} -> token; POST
  /v1/external/orders/create/return (pickup_* = the customer, shipping_* = her warehouse, order_items with optional QC
  fields qc_enable / qc_product_name / qc_brand / qc_color / qc_size, payment_method PREPAID) -> order_id + shipment_id;
  POST /v1/external/courier/assign/awb {shipment_id, is_return: 1} -> awb; GET /v1/external/courier/track/shipment/{id}.
- Delhivery (her own Delhivery One account token): POST /api/cmu/create.json with format=json&data={shipments:
  [{..., payment_mode: "Pickup"}], pickup_location: {name: her registered warehouse}} -> waybill; GET
  /api/v1/packages/json/?waybill=. (Field names from Delhivery's B2C docs; check on her account before going live.)
- manual: no keys -> a pickup checklist + the customer message draft; she books it in her courier's app.

Booking a pickup may charge HER courier wallet; it only happens after she approved the return. Base URLs can be pointed
at fakes with WAPSI_SHIPROCKET_BASE / WAPSI_DELHIVERY_BASE; tests plug an httpx MockTransport with set_transport."""
from __future__ import annotations

import json
import os
import time
from typing import Any

import httpx


class CourierError(Exception):
    pass


_TRANSPORT: httpx.BaseTransport | None = None
_TOKENS: dict[str, tuple[str, float]] = {}


def set_transport(t: httpx.BaseTransport | None) -> None:
    global _TRANSPORT
    _TRANSPORT = t
    _TOKENS.clear()


def _http(method: str, url: str, **kw) -> httpx.Response:
    try:
        with httpx.Client(timeout=30, transport=_TRANSPORT) as c:
            return c.request(method, url, **kw)
    except httpx.HTTPError as e:
        raise CourierError(f"Courier tak nahi pahunch paya ({e.__class__.__name__}).")


def norm_status(text: str) -> str:
    t = (text or "").lower()
    if any(w in t for w in ("cancel", "rto")):
        return "cancelled"
    if any(w in t for w in ("fail", "not picked", "pickup exception", "unsuccessful", "rejected")):
        return "failed"
    if "deliver" in t and "out for" not in t and "undeliver" not in t:
        return "delivered"
    if any(w in t for w in ("picked", "in transit", "transit", "shipped", "reached", "out for delivery", "dispatched")):
        return "in_transit"
    return "booked"


class Courier:
    name = "manual"
    needs = ()

    def __init__(self, creds: dict[str, Any] | None = None):
        self.creds = creds or {}

    def book(self, ref: str, customer: dict, warehouse: dict, items: list[dict], parcel: dict, qc: bool) -> dict:
        raise NotImplementedError

    def track(self, pickup: dict) -> dict:
        return {"status": pickup.get("status", "booked"), "events": []}


class Manual(Courier):
    name = "manual"

    def book(self, ref, customer, warehouse, items, parcel, qc):
        return {"provider": "manual", "status": "manual", "awb": "",
                "steps": ["Apne courier app (Shiprocket / Delhivery / India Post / local) mein 'reverse pickup' banaiye",
                          f"Pickup: {customer.get('name', '')}, {customer.get('address', '')} {customer.get('pincode', '')}".strip(),
                          f"Pahunchana: {warehouse.get('name', '')}, {warehouse.get('address', '')} {warehouse.get('pincode', '')}".strip(),
                          "AWB / tracking number Hoola ko bataiye (tracking yahin dikhegi)",
                          "Graahak ko bolein: saamaan wapas usi packing mein, label ke saath; dabba band karte waqt video banayein"]}


class Shiprocket(Courier):
    name = "shiprocket"
    needs = ("email", "password")

    def base(self) -> str:
        return (os.environ.get("WAPSI_SHIPROCKET_BASE") or "https://apiv2.shiprocket.in/v1/external").rstrip("/")

    def token(self) -> str:
        key = self.creds.get("email", "")
        hit = _TOKENS.get("sr:" + key)
        if hit and hit[1] > time.time():
            return hit[0]
        if not (self.creds.get("email") and self.creds.get("password")):
            raise CourierError("Shiprocket API user (email + password) app mein jodiye.")
        r = _http("POST", self.base() + "/auth/login", json={"email": self.creds["email"], "password": self.creds["password"]})
        if r.status_code >= 400:
            raise CourierError("Shiprocket ne login mana kiya: API user ka email / password dekhiye.")
        tok = (r.json() or {}).get("token", "")
        if not tok:
            raise CourierError("Shiprocket se token nahi mila.")
        _TOKENS["sr:" + key] = (tok, time.time() + 8 * 86400)         # tokens live ~10 days
        return tok

    def _call(self, method: str, path: str, body: Any = None) -> dict:
        r = _http(method, self.base() + path, json=body, headers={"Authorization": f"Bearer {self.token()}"})
        try:
            data = r.json()
        except ValueError:
            data = {}
        if r.status_code >= 400:
            msg = (data or {}).get("message") or json.dumps((data or {}).get("errors") or {})[:200] or str(r.status_code)
            raise CourierError(f"Shiprocket: {msg}")
        return data or {}

    def book(self, ref, customer, warehouse, items, parcel, qc):
        first, _, last = (customer.get("name") or "Customer").partition(" ")
        body = {
            "order_id": ref, "order_date": parcel.get("order_date") or time.strftime("%Y-%m-%d"),
            "pickup_customer_name": first, "pickup_last_name": last, "pickup_address": customer.get("address", ""),
            "pickup_city": customer.get("city", ""), "pickup_state": customer.get("state", ""), "pickup_country": "India",
            "pickup_pincode": customer.get("pincode", ""), "pickup_email": customer.get("email", ""),
            "pickup_phone": customer.get("phone", ""),
            "shipping_customer_name": warehouse.get("name", ""), "shipping_address": warehouse.get("address", ""),
            "shipping_city": warehouse.get("city", ""), "shipping_state": warehouse.get("state", ""), "shipping_country": "India",
            "shipping_pincode": warehouse.get("pincode", ""), "shipping_email": warehouse.get("email", ""),
            "shipping_phone": warehouse.get("phone", ""),
            "order_items": [dict({"name": i.get("name", "")[:100], "sku": i.get("sku") or i.get("name", "")[:40],
                                  "units": int(i.get("qty") or 1), "selling_price": float(i.get("price") or 0)},
                                 **({"qc_enable": True, "qc_product_name": i.get("name", "")[:100]} if qc else {})) for i in items],
            "payment_method": "PREPAID", "sub_total": float(sum(float(i.get("price") or 0) * float(i.get("qty") or 1) for i in items)),
            "length": float(parcel.get("length") or 20), "breadth": float(parcel.get("breadth") or 15),
            "height": float(parcel.get("height") or 10), "weight": float(parcel.get("weight") or 0.5)}
        missing = [k for k in ("pickup_address", "pickup_pincode", "pickup_phone", "shipping_address", "shipping_pincode", "shipping_phone")
                   if not str(body.get(k) or "").strip()]
        if missing:
            raise CourierError("Pickup ke liye yeh chahiye: " + ", ".join(m.replace("_", " ") for m in missing))
        made = self._call("POST", "/orders/create/return", body)
        sid = made.get("shipment_id")
        if not sid:
            raise CourierError("Shiprocket ne return order nahi banaya: " + str(made.get("message") or made)[:200])
        out = {"provider": "shiprocket", "order_id": made.get("order_id"), "shipment_id": sid, "status": "booked", "awb": ""}
        try:
            a = self._call("POST", "/courier/assign/awb", {"shipment_id": sid, "is_return": 1})
            d = ((a.get("response") or {}).get("data") or {})
            out["awb"], out["courier"] = str(d.get("awb_code") or ""), str(d.get("courier_name") or "")
        except CourierError as e:
            out["note"] = f"Return order bana, AWB abhi nahi: {e}"
        return out

    def track(self, pickup):
        if not pickup.get("shipment_id"):
            return {"status": pickup.get("status", "booked"), "events": []}
        d = self._call("GET", f"/courier/track/shipment/{pickup['shipment_id']}")
        td = d.get("tracking_data") or (next(iter(d.values()), {}) if isinstance(d, dict) and d else {})
        td = td.get("tracking_data", td) if isinstance(td, dict) else {}
        acts = td.get("shipment_track_activities") or []
        cur = ""
        st = td.get("shipment_track") or []
        if st:
            cur = str(st[0].get("current_status") or "")
        if not cur and acts:
            cur = str(acts[0].get("activity") or "")
        return {"status": norm_status(cur) if cur else pickup.get("status", "booked"), "raw": cur[:80],
                "events": [{"at": str(a.get("date", ""))[:19], "what": str(a.get("activity", ""))[:120], "where": str(a.get("location", ""))[:60]}
                           for a in acts[:10]]}


class Delhivery(Courier):
    name = "delhivery"
    needs = ("token", "pickup_location")

    def base(self) -> str:
        return (os.environ.get("WAPSI_DELHIVERY_BASE") or "https://track.delhivery.com").rstrip("/")

    def book(self, ref, customer, warehouse, items, parcel, qc):
        if not (self.creds.get("token") and self.creds.get("pickup_location")):
            raise CourierError("Delhivery token aur registered warehouse ka naam app mein jodiye.")
        ship = {"name": customer.get("name", ""), "add": customer.get("address", ""), "pin": customer.get("pincode", ""),
                "city": customer.get("city", ""), "state": customer.get("state", ""), "country": "India", "phone": customer.get("phone", ""),
                "order": ref, "payment_mode": "Pickup", "products_desc": ", ".join(i.get("name", "") for i in items)[:200],
                "total_amount": sum(float(i.get("price") or 0) * float(i.get("qty") or 1) for i in items),
                "quantity": str(int(sum(float(i.get("qty") or 1) for i in items))), "weight": str(int(float(parcel.get("weight") or 0.5) * 1000))}
        if not (ship["add"] and ship["pin"] and ship["phone"]):
            raise CourierError("Pickup ke liye graahak ka pata, PIN aur phone chahiye.")
        payload = {"shipments": [ship], "pickup_location": {"name": self.creds["pickup_location"]}}
        r = _http("POST", self.base() + "/api/cmu/create.json", content=("format=json&data=" + json.dumps(payload)).encode(),
                  headers={"Authorization": f"Token {self.creds['token']}", "Content-Type": "application/x-www-form-urlencoded"})
        try:
            d = r.json()
        except ValueError:
            d = {}
        pk = (d.get("packages") or [{}])[0] if isinstance(d, dict) else {}
        if r.status_code >= 400 or not pk.get("waybill"):
            raise CourierError("Delhivery: " + str(pk.get("remarks") or d.get("rmk") or r.status_code)[:200])
        return {"provider": "delhivery", "awb": str(pk["waybill"]), "status": "booked"}

    def track(self, pickup):
        if not pickup.get("awb"):
            return {"status": pickup.get("status", "booked"), "events": []}
        r = _http("GET", self.base() + "/api/v1/packages/json/", params={"waybill": pickup["awb"]},
                  headers={"Authorization": f"Token {self.creds.get('token', '')}"})
        try:
            s = ((r.json().get("ShipmentData") or [{}])[0].get("Shipment") or {})
        except (ValueError, AttributeError):
            s = {}
        cur = str(((s.get("Status") or {}).get("Status")) or "")
        scans = [{"at": str((x.get("ScanDetail") or {}).get("ScanDateTime", ""))[:19], "what": str((x.get("ScanDetail") or {}).get("Scan", ""))[:120],
                  "where": str((x.get("ScanDetail") or {}).get("ScannedLocation", ""))[:60]} for x in (s.get("Scans") or [])][-10:]
        return {"status": norm_status(cur) if cur else pickup.get("status", "booked"), "raw": cur[:80], "events": scans}


PROVIDERS = {"manual": Manual, "shiprocket": Shiprocket, "delhivery": Delhivery}


def get(name: str, creds: dict | None = None) -> Courier:
    return PROVIDERS.get(name or "manual", Manual)(creds)
