"""One adapter interface over the carriers' own documented APIs, with HER keys. Read-only calls (serviceability, rates,
tracking) run freely; anything that books / charges / changes a shipment is called ONLY from service.decide (her tap).

The Shiprocket and Delhivery clients are the Wapsi Sahayak ones (`app.wapsi.couriers`): same login / token cache, same HTTP
helper and the same test transport (`wapsi.couriers.set_transport`). Here they are extended (subclassed, not copied) with the
forward-shipment calls; the reverse pickup (return label) is the Wapsi client's own `book` unchanged.

- Shiprocket (base https://apiv2.shiprocket.in/v1/external, Bearer token from POST /auth/login with her API user):
  GET /courier/serviceability/?pickup_postcode&delivery_postcode&weight&cod -> data.available_courier_companies [{courier_name,
  courier_company_id, rate, etd, estimated_delivery_days, cod}]; POST /orders/create/adhoc -> order_id, shipment_id;
  POST /courier/assign/awb {shipment_id, courier_id} -> response.data.awb_code; POST /courier/generate/pickup {shipment_id: [..]};
  POST /courier/generate/label {shipment_id: [..]} -> label_url; GET /courier/track/awb/{awb}; POST /orders/cancel {ids};
  POST /ndr/{awb}/action {action: re-attempt|return, comments, phone, address1, deferred_date}.
- Delhivery (base https://track.delhivery.com, header "Authorization: Token <her token>"): GET /c/api/pin-codes/json/?filter_codes=;
  GET /api/kinko/v1/invoice/charges/.json?md=S&ss=Delivered&d_pin&o_pin&cgm&pt; POST /api/cmu/create.json (payment_mode
  Prepaid|COD); GET /api/p/packing_slip?wbns=&pdf=true; POST /fm/request/new/ (pickup request); GET /api/v1/packages/json/?waybill=;
  POST /api/p/edit {waybill, cancellation: "true"}; POST /api/p/update {data: [{waybill, act: "RE-ATTEMPT"}]}.
- Blue Dart (DHL developer portal, contract customers): GET https://apigateway.bluedart.com/in/transportation/token/v1/login
  (ClientID / clientSecret headers) -> JWTToken; GET .../tracking/v1?handler=tnt&action=custawbquery&loginid&awb=awb&numbers&
  format=xml&lickey&verno=1&scan=1 with the JWTToken header. Tracking only.
- Others (DTDC, Ekart, Xpressbees, India Post, local): manual - she books in their app / counter and types the AWB.
"""
from __future__ import annotations

import json
import os
import time
import xml.etree.ElementTree as ET
from datetime import date, timedelta
from typing import Any

from ..wapsi import couriers as wc
from . import rules as R

CarrierError = wc.CourierError


def _http(method: str, url: str, **kw):
    return wc._http(method, url, **kw)


def _days(v) -> int | None:
    try:
        n = int(float(v))
        return n if 0 < n < 60 else None
    except (TypeError, ValueError):
        return None


class Adapter:
    """What every carrier offers. A method a carrier can't do raises CarrierError with the manual steps."""
    name = "manual"
    can: tuple[str, ...] = ()

    def __init__(self, creds: dict[str, Any] | None = None):
        self.creds = creds or {}

    def check(self, src_pin: str, dst_pin: str, kg: float, cod: bool, value: float) -> dict[str, Any]:
        raise CarrierError("Is courier ka rate / serviceability API nahi: unke app mein dekhiye.")

    def book(self, parcel: dict, warehouse: dict, quote: dict) -> dict[str, Any]:
        raise CarrierError("Is courier par booking aap unke app / counter par kijiye, phir AWB Hoola ko bataiye.")

    def label(self, booking: dict) -> dict[str, Any]:
        return {}

    def track(self, booking: dict) -> dict[str, Any]:
        raise CarrierError("Is courier ki tracking unke apne page par dekhiye.")

    def ndr(self, booking: dict, action: str, fix: dict) -> dict[str, Any]:
        raise CarrierError("NDR ka jawab courier ke app / panel mein dijiye.")

    def cancel(self, booking: dict) -> dict[str, Any]:
        raise CarrierError("Cancel courier ke app / panel mein kijiye.")

    def reverse(self, ref: str, customer: dict, warehouse: dict, items: list, parcel: dict, qc: bool) -> dict[str, Any]:
        return wc.Manual().book(ref, customer, warehouse, items, parcel, qc)


class Manual(Adapter):
    name = "manual"


class ShiprocketDesk(wc.Shiprocket, Adapter):
    name = "shiprocket"
    can = ("rates", "book", "label", "pickup", "track", "ndr", "cancel", "reverse")

    def __init__(self, creds=None):
        wc.Shiprocket.__init__(self, creds)

    def check(self, src_pin, dst_pin, kg, cod, value):
        q = f"/courier/serviceability/?pickup_postcode={src_pin}&delivery_postcode={dst_pin}&weight={max(kg, 0.1):g}&cod={1 if cod else 0}"
        if value:
            q += f"&declared_value={int(value)}"
        d = self._call("GET", q)
        data = d.get("data") or {}
        comps = data.get("available_courier_companies") or []
        opts = []
        for c in comps[:30]:
            rate = R.num(c.get("rate") or c.get("freight_charge"))
            opts.append({"courier": str(c.get("courier_name") or "")[:60], "courier_id": c.get("courier_company_id"),
                         "rate": round(rate, 2) if rate else None,
                         "days": _days(c.get("estimated_delivery_days")), "etd": str(c.get("etd") or "")[:30],
                         "cod": (c.get("cod") in (1, True, "1")) if "cod" in c else None, "provider": "shiprocket"})
        return {"serviceable": bool(opts), "cod_ok": any(o["cod"] for o in opts) if cod else None, "options": opts,
                "recommended": data.get("recommended_courier_company_id")}

    def book(self, parcel, warehouse, quote):
        cust = parcel.get("customer") or {}
        if not self.creds.get("pickup_location"):
            raise CarrierError("Shiprocket ki pickup location ka naam (nickname) Courier > Niyam mein likhiye.")
        first, _, last = (cust.get("name") or "Customer").partition(" ")
        items = parcel.get("items") or [{"name": "Parcel", "qty": 1, "price": parcel.get("value") or 0}]
        w = parcel.get("weight") or {}
        dims = w.get("dims") or {}
        cod = parcel.get("payment") == "cod"
        body = {
            "order_id": parcel.get("number"), "order_date": time.strftime("%Y-%m-%d %H:%M"),
            "pickup_location": self.creds["pickup_location"],
            "billing_customer_name": first, "billing_last_name": last, "billing_address": cust.get("address", ""),
            "billing_city": cust.get("city", ""), "billing_pincode": cust.get("pincode", ""), "billing_state": cust.get("state", ""),
            "billing_country": "India", "billing_email": cust.get("email", ""), "billing_phone": cust.get("phone", ""),
            "shipping_is_billing": True,
            "order_items": [{"name": str(i.get("name") or "Item")[:100], "sku": str(i.get("sku") or i.get("name") or "item")[:40],
                             "units": int(R.num(i.get("qty")) or 1), "selling_price": R.num(i.get("price"))} for i in items],
            "payment_method": "COD" if cod else "Prepaid", "sub_total": float(parcel.get("cod_amount") if cod else parcel.get("value") or 0),
            "length": R.num(dims.get("l")) or 10, "breadth": R.num(dims.get("b")) or 10, "height": R.num(dims.get("h")) or 10,
            "weight": R.num(w.get("dead_kg")) or 0.5}
        if parcel.get("eway_no"):
            body["ewaybill_no"] = parcel["eway_no"]
        made = self._call("POST", "/orders/create/adhoc", body)
        sid = made.get("shipment_id")
        if not sid:
            raise CarrierError("Shiprocket ne order nahi banaya: " + str(made.get("message") or made)[:200])
        out = {"provider": "shiprocket", "order_id": made.get("order_id"), "shipment_id": sid}
        a = self._call("POST", "/courier/assign/awb", {"shipment_id": sid, "courier_id": quote.get("courier_id")})
        d = (a.get("response") or {}).get("data") or {}
        out["awb"], out["carrier"] = str(d.get("awb_code") or ""), str(d.get("courier_name") or quote.get("courier") or "")
        if d.get("applied_weight"):
            out["applied_weight"] = d.get("applied_weight")
        if d.get("freight_charges") or d.get("rate"):
            out["charged"] = R.num(d.get("freight_charges") or d.get("rate"))
        if not out["awb"]:
            out["note"] = "Order bana par AWB nahi mila: " + str(a.get("message") or "")[:160]
            return out
        try:
            p = self._call("POST", "/courier/generate/pickup", {"shipment_id": [sid]})
            pr = p.get("response") or {}
            out["pickup"] = {"date": str(pr.get("pickup_scheduled_date") or "")[:30], "token": str(pr.get("pickup_token_number") or "")[:40]}
        except CarrierError as e:
            out["pickup_note"] = f"Pickup request nahi gayi: {e}"
        return out

    def label(self, booking):
        if not booking.get("shipment_id"):
            return {}
        d = self._call("POST", "/courier/generate/label", {"shipment_id": [booking["shipment_id"]]})
        return {"url": str(d.get("label_url") or "")}

    def track(self, booking):
        if not booking.get("awb"):
            return {"raw": "", "events": []}
        d = self._call("GET", f"/courier/track/awb/{booking['awb']}")
        td = d.get("tracking_data") or {}
        st = td.get("shipment_track") or []
        cur = str((st[0] if st else {}).get("current_status") or "")
        acts = td.get("shipment_track_activities") or []
        if not cur and acts:
            cur = str(acts[0].get("activity") or acts[0].get("status") or "")
        edd = str((st[0] if st else {}).get("edd") or td.get("etd") or "")[:30]
        return {"raw": cur[:200], "edd": edd, "events": [{"at": str(a.get("date", ""))[:19], "what": str(a.get("activity", ""))[:160],
                                                         "where": str(a.get("location", ""))[:60]} for a in acts[:15]],
                "error": str(td.get("error") or "")[:160]}

    def ndr(self, booking, action, fix):
        body = {"action": "return" if action == "rto" else "re-attempt", "comments": str(fix.get("note") or "")[:200]}
        if fix.get("phone"):
            body["phone"] = fix["phone"]
        if fix.get("address"):
            body["address1"] = fix["address"][:180]
        if fix.get("date"):
            body["deferred_date"] = fix["date"]
        return self._call("POST", f"/ndr/{booking['awb']}/action", body)

    def cancel(self, booking):
        if not booking.get("order_id"):
            raise CarrierError("Shiprocket order id nahi mila.")
        return self._call("POST", "/orders/cancel", {"ids": [booking["order_id"]]})

    def reverse(self, ref, customer, warehouse, items, parcel, qc):
        return wc.Shiprocket.book(self, ref, customer, warehouse, items, parcel, qc)     # Wapsi's reverse pickup, unchanged


class DelhiveryDesk(wc.Delhivery, Adapter):
    name = "delhivery"
    can = ("rates", "book", "label", "pickup", "track", "ndr", "cancel", "reverse")

    def __init__(self, creds=None):
        wc.Delhivery.__init__(self, creds)

    def _h(self, form: bool = False) -> dict[str, str]:
        if not self.creds.get("token"):
            raise CarrierError("Delhivery token Courier > Niyam mein jodiye.")
        h = {"Authorization": f"Token {self.creds['token']}", "Accept": "application/json"}
        if form:
            h["Content-Type"] = "application/x-www-form-urlencoded"
        return h

    def _json(self, r) -> Any:
        try:
            return r.json()
        except ValueError:
            return {}

    def check(self, src_pin, dst_pin, kg, cod, value):
        r = _http("GET", self.base() + "/c/api/pin-codes/json/", params={"filter_codes": dst_pin}, headers=self._h())
        if r.status_code >= 400:
            raise CarrierError(f"Delhivery serviceability: {r.status_code}")
        codes = (self._json(r) or {}).get("delivery_codes") or []
        pc = (codes[0].get("postal_code") if codes else {}) or {}
        ok = bool(pc) and str(pc.get("pre_paid", "Y")).upper() == "Y"
        cod_ok = str(pc.get("cod", "N")).upper() == "Y"
        opts = []
        if ok:
            rate = None
            try:
                q = _http("GET", self.base() + "/api/kinko/v1/invoice/charges/.json", headers=self._h(),
                          params={"md": "S", "ss": "Delivered", "d_pin": dst_pin, "o_pin": src_pin, "cgm": int(max(kg, 0.1) * 1000),
                                  "pt": "COD" if cod else "Pre-paid"})
                d = self._json(q)
                row = d[0] if isinstance(d, list) and d else (d if isinstance(d, dict) else {})
                rate = R.num(row.get("total_amount")) or None
            except CarrierError:
                rate = None
            opts.append({"courier": "Delhivery Surface", "courier_id": "S", "rate": rate, "days": None, "etd": "", "cod": cod_ok,
                         "provider": "delhivery"})
        return {"serviceable": ok, "cod_ok": cod_ok if cod else None, "options": opts, "raw": {k: pc.get(k) for k in ("pin", "cod", "pre_paid", "pickup")}}

    def book(self, parcel, warehouse, quote):
        if not self.creds.get("pickup_location"):
            raise CarrierError("Delhivery mein registered warehouse ka naam Courier > Niyam mein likhiye.")
        cust = parcel.get("customer") or {}
        cod = parcel.get("payment") == "cod"
        w = parcel.get("weight") or {}
        dims = w.get("dims") or {}
        ship = {"name": cust.get("name", ""), "add": cust.get("address", ""), "pin": cust.get("pincode", ""), "city": cust.get("city", ""),
                "state": cust.get("state", ""), "country": "India", "phone": cust.get("phone", ""), "order": parcel.get("number"),
                "payment_mode": "COD" if cod else "Prepaid", "cod_amount": str(parcel.get("cod_amount") or 0) if cod else "0",
                "total_amount": str(parcel.get("value") or 0),
                "products_desc": ", ".join(str(i.get("name") or "") for i in parcel.get("items") or [])[:200],
                "quantity": str(int(sum(R.num(i.get("qty")) or 1 for i in parcel.get("items") or []) or 1)),
                "weight": str(int((R.num(w.get("dead_kg")) or 0.5) * 1000)), "shipment_length": str(R.num(dims.get("l")) or ""),
                "shipment_width": str(R.num(dims.get("b")) or ""), "shipment_height": str(R.num(dims.get("h")) or ""),
                "shipping_mode": "Surface"}
        if parcel.get("eway_no"):
            ship["waybill_ewbn"] = parcel["eway_no"]
        payload = {"shipments": [ship], "pickup_location": {"name": self.creds["pickup_location"]}}
        r = _http("POST", self.base() + "/api/cmu/create.json", content=("format=json&data=" + json.dumps(payload)).encode(), headers=self._h(True))
        d = self._json(r)
        pk = (d.get("packages") or [{}])[0] if isinstance(d, dict) else {}
        if r.status_code >= 400 or not pk.get("waybill"):
            raise CarrierError("Delhivery: " + str(pk.get("remarks") or (d or {}).get("rmk") or r.status_code)[:200])
        out = {"provider": "delhivery", "awb": str(pk["waybill"]), "carrier": "Delhivery"}
        try:
            when = date.today() + timedelta(days=1)
            p = _http("POST", self.base() + "/fm/request/new/", headers=self._h(),
                      json={"pickup_location": self.creds["pickup_location"], "pickup_date": when.isoformat(), "pickup_time": "11:00:00",
                            "expected_package_count": 1})
            pd = self._json(p)
            if p.status_code < 400:
                out["pickup"] = {"date": str((pd or {}).get("pickup_date") or when.isoformat())[:30], "token": str((pd or {}).get("pickup_id") or "")[:40]}
            else:
                out["pickup_note"] = "Pickup request nahi gayi (aaj ki request pehle se ho sakti hai)."
        except CarrierError as e:
            out["pickup_note"] = f"Pickup request nahi gayi: {e}"
        return out

    def label(self, booking):
        if not booking.get("awb"):
            return {}
        r = _http("GET", self.base() + "/api/p/packing_slip", params={"wbns": booking["awb"], "pdf": "true"}, headers=self._h())
        d = self._json(r)
        pk = ((d or {}).get("packages") or [{}])[0] if isinstance(d, dict) else {}
        return {"url": str(pk.get("pdf_download_link") or "")}

    def track(self, booking):
        if not booking.get("awb"):
            return {"raw": "", "events": []}
        r = _http("GET", self.base() + "/api/v1/packages/json/", params={"waybill": booking["awb"]}, headers=self._h())
        try:
            s = ((self._json(r).get("ShipmentData") or [{}])[0].get("Shipment") or {})
        except (AttributeError, IndexError):
            s = {}
        stt = s.get("Status") or {}
        cur = str(stt.get("Status") or "")
        instr = str(stt.get("Instructions") or "")
        raw = (cur + (f" - {instr}" if instr and instr.lower() not in cur.lower() else "")).strip()
        scans = [{"at": str((x.get("ScanDetail") or {}).get("ScanDateTime", ""))[:19], "what": str((x.get("ScanDetail") or {}).get("Instructions")
                  or (x.get("ScanDetail") or {}).get("Scan", ""))[:160], "where": str((x.get("ScanDetail") or {}).get("ScannedLocation", ""))[:60]}
                 for x in (s.get("Scans") or [])][-15:][::-1]
        return {"raw": raw[:200], "edd": str(s.get("ExpectedDeliveryDate") or s.get("PromisedDeliveryDate") or "")[:30], "events": scans}

    def ndr(self, booking, action, fix):
        if action == "rto":
            raise CarrierError("Delhivery par RTO ka faisla unke panel mein kijiye.")
        r = _http("POST", self.base() + "/api/p/update", headers=self._h(), json={"data": [{"waybill": booking["awb"], "act": "RE-ATTEMPT"}]})
        if r.status_code >= 400:
            raise CarrierError(f"Delhivery NDR: {r.status_code}")
        return self._json(r) or {"ok": True}

    def cancel(self, booking):
        r = _http("POST", self.base() + "/api/p/edit", headers=self._h(), json={"waybill": booking.get("awb"), "cancellation": "true"})
        if r.status_code >= 400:
            raise CarrierError(f"Delhivery cancel: {r.status_code}")
        return self._json(r) or {"ok": True}

    def reverse(self, ref, customer, warehouse, items, parcel, qc):
        return wc.Delhivery.book(self, ref, customer, warehouse, items, parcel, qc)      # Wapsi's reverse pickup, unchanged


_BD_TOKEN: dict[str, tuple[str, float]] = {}


class BlueDart(Adapter):
    name = "bluedart"
    can = ("track",)

    def base(self) -> str:
        return (os.environ.get("COURIER_BLUEDART_BASE") or "https://apigateway.bluedart.com/in/transportation").rstrip("/")

    def token(self) -> str:
        cid = self.creds.get("client_id", "")
        hit = _BD_TOKEN.get(cid)
        if hit and hit[1] > time.time():
            return hit[0]
        if not (cid and self.creds.get("client_secret")):
            raise CarrierError("Blue Dart ke Consumer key / secret Courier > Niyam mein jodiye.")
        r = _http("GET", self.base() + "/token/v1/login", headers={"ClientID": cid, "clientSecret": self.creds["client_secret"]})
        try:
            tok = (r.json() or {}).get("JWTToken", "")
        except ValueError:
            tok = ""
        if r.status_code >= 400 or not tok:
            raise CarrierError("Blue Dart ne token nahi diya: keys dekhiye.")
        _BD_TOKEN[cid] = (tok, time.time() + 3000)
        return tok

    def track(self, booking):
        if not booking.get("awb"):
            return {"raw": "", "events": []}
        r = _http("GET", self.base() + "/tracking/v1", headers={"JWTToken": self.token()},
                  params={"handler": "tnt", "action": "custawbquery", "loginid": self.creds.get("login_id", ""), "awb": "awb",
                          "numbers": booking["awb"], "format": "xml", "lickey": self.creds.get("license_key", ""), "verno": "1", "scan": "1"})
        try:
            root = ET.fromstring(r.text or "<x/>")
        except ET.ParseError:
            raise CarrierError("Blue Dart ka jawab samajh nahi aaya.")
        sh = root.find(".//Shipment")
        if sh is None:
            return {"raw": "", "events": []}
        cur = (sh.findtext("Status") or "").strip()
        ev = [{"at": f"{(x.findtext('ScanDate') or '').strip()} {(x.findtext('ScanTime') or '').strip()}".strip()[:19],
               "what": (x.findtext("Scan") or "").strip()[:160], "where": (x.findtext("ScannedLocation") or "").strip()[:60]}
              for x in sh.findall(".//ScanDetail")][:15]
        return {"raw": cur[:200], "edd": (sh.findtext("ExpectedDeliveryDate") or "").strip()[:30], "events": ev}


ADAPTERS: dict[str, type[Adapter]] = {"manual": Manual, "shiprocket": ShiprocketDesk, "delhivery": DelhiveryDesk, "bluedart": BlueDart}


def get(name: str, creds: dict | None = None) -> Adapter:
    return ADAPTERS.get(name or "manual", Manual)(creds)


def fetch_pdf(url: str) -> bytes:
    """Download a label PDF the carrier handed back (public https only, every hop checked)."""
    if not url.lower().startswith("https://"):
        raise CarrierError("Label ka link https nahi.")
    _public(url)
    r = _http("GET", url, follow_redirects=False)
    hops = 0
    while r.status_code in (301, 302, 303, 307, 308) and hops < 3:
        nxt = r.headers.get("location", "")
        if not nxt.lower().startswith("https://"):
            raise CarrierError("Label ka link https nahi.")
        _public(nxt)
        r = _http("GET", nxt, follow_redirects=False)
        hops += 1
    data = r.content or b""
    if r.status_code >= 400 or not data.startswith(b"%PDF") or len(data) > 10 * 1024 * 1024:
        raise CarrierError("Label PDF nahi mila (link khol kar dekhiye).")
    return data


def _public(url: str) -> None:
    from .. import web
    try:
        web._check_url(url)
    except web.WebError as e:
        raise CarrierError(str(e))
