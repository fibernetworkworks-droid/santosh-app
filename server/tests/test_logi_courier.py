"""Courier Sahayak (courier desk): weights / states / rules by code, parcel -> PIN + carrier's own quotes (fake Shiprocket +
Delhivery) -> booking card that ONLY her tap books (hash, stale after a change, fingerprint route) -> AWB + label PDF,
tracking in the carrier's own words + NDR -> re-attempt card, "where is my parcel?" for her and for a customer (only their
own), COD remittance sheet, manifest, return label through the Wapsi desk, tools (owner-only, no keys in chat), API, tick."""
import asyncio
import json
from datetime import datetime, timedelta, timezone

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.courier.models  # noqa: F401  (tables for the env fixture's init_db)
import app.wapsi.models  # noqa: F401
from tests.test_life import conv_ctx

T = "default"
PDF = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF"
WH = {"name": "Riya Fashions", "phone": "9822000000", "address": "Shop 4, Main Rd, Akot", "city": "Akot", "state": "Maharashtra", "pincode": "444101"}
CUST = {"name": "Sneha Patil", "phone": "+91 98765 43210", "address": "12 MG Road, Camp", "city": "Pune", "state": "Maharashtra", "pincode": "411001"}


class Fake:
    """Shiprocket + Delhivery + Blue Dart + label host, shaped like their documented answers."""

    def __init__(self):
        self.calls = []
        self.track_status = "In Transit"
        self.dl_status = ("Pending", "")

    def __call__(self, req: httpx.Request) -> httpx.Response:
        u = req.url
        path, host = u.path, u.host
        self.calls.append((req.method, host, path))
        body = {}
        if req.content and req.headers.get("content-type", "").startswith("application/json"):
            body = json.loads(req.content)
        if host == "apiv2.shiprocket.in":
            if path.endswith("/auth/login"):
                return httpx.Response(200, json={"token": "srtok"})
            assert req.headers.get("authorization") == "Bearer srtok"
            if "/courier/serviceability" in path:
                cod = u.params.get("cod")
                return httpx.Response(200, json={"data": {"available_courier_companies": [
                    {"courier_name": "Xpressbees Surface", "courier_company_id": 33, "rate": 72.5, "estimated_delivery_days": "4", "etd": "Oct 27, 2026", "cod": 1},
                    {"courier_name": "Delhivery Surface", "courier_company_id": 12, "rate": 81, "estimated_delivery_days": "3", "etd": "Oct 26, 2026", "cod": 1},
                    {"courier_name": "Ekart Logistics", "courier_company_id": 44, "rate": 65, "estimated_delivery_days": "5", "etd": "", "cod": 0 if cod == "1" else 1},
                ]}})
            if path.endswith("/orders/create/adhoc"):
                assert body["payment_method"] in ("COD", "Prepaid") and body["pickup_location"] == "Akot shop"
                return httpx.Response(200, json={"order_id": 9001, "shipment_id": 7001, "status": "NEW"})
            if path.endswith("/courier/assign/awb"):
                if body.get("is_return") == 1:
                    return httpx.Response(200, json={"response": {"data": {"awb_code": "RV998877", "courier_name": "Delhivery Reverse"}}})
                assert body["shipment_id"] == 7001 and body["courier_id"] in (33, 12, 44)
                return httpx.Response(200, json={"awb_assign_status": 1, "response": {"data": {"awb_code": "SR12345678", "courier_name": "Xpressbees Surface",
                                                                                             "freight_charges": 72.5}}})
            if path.endswith("/courier/generate/pickup"):
                return httpx.Response(200, json={"pickup_status": 1, "response": {"pickup_scheduled_date": "2026-10-24 10:00:00", "pickup_token_number": "PT1"}})
            if path.endswith("/courier/generate/label"):
                return httpx.Response(200, json={"label_created": 1, "label_url": "https://labels.example.in/l/7001.pdf"})
            if "/courier/track/awb/" in path:
                return httpx.Response(200, json={"tracking_data": {"track_status": 1, "shipment_track": [{"current_status": self.track_status, "edd": "2026-10-27"}],
                                                                   "shipment_track_activities": [{"date": "2026-10-24 18:00:00", "activity": self.track_status, "location": "Akola Hub"}]}})
            if "/ndr/" in path and path.endswith("/action"):
                return httpx.Response(200, json={"status": True, "message": "Reattempt raised"})
            if path.endswith("/orders/create/return"):
                return httpx.Response(200, json={"order_id": 9100, "shipment_id": 7100})
            if path.endswith("/orders/cancel"):
                return httpx.Response(200, json={"status": 200})
        if host == "labels.example.in":
            return httpx.Response(200, content=PDF, headers={"content-type": "application/pdf"})
        if host == "track.delhivery.com":
            assert req.headers.get("authorization") == "Token dltok"
            if path.startswith("/c/api/pin-codes/json"):
                return httpx.Response(200, json={"delivery_codes": [{"postal_code": {"pin": 411001, "cod": "Y", "pre_paid": "Y", "pickup": "Y"}}]})
            if path.startswith("/api/kinko/v1/invoice/charges"):
                return httpx.Response(200, json=[{"total_amount": 88.0}])
            if path == "/api/v1/packages/json/":
                st, ins = self.dl_status
                return httpx.Response(200, json={"ShipmentData": [{"Shipment": {"Status": {"Status": st, "Instructions": ins},
                                                                               "Scans": [{"ScanDetail": {"ScanDateTime": "2026-10-25T12:00:00", "Instructions": ins or st,
                                                                                                         "ScannedLocation": "Pune_Camp_DC"}}]}}]})
        return httpx.Response(404, json={"message": f"not faked {path}"})


@pytest.fixture
def cr(env, monkeypatch, tmp_path):
    from app.courier import carriers as K
    from app.courier import service as S
    from app.wapsi import couriers as wc
    monkeypatch.setenv("COURIER_DIR", str(tmp_path / "courier"))
    monkeypatch.setenv("WAPSI_DIR", str(tmp_path / "wapsi"))
    monkeypatch.setattr(K, "_public", lambda url: None)
    fake = Fake()
    wc.set_transport(httpx.MockTransport(fake))
    S.save_settings(T, business="Riya Fashions", warehouse=WH)
    yield S, fake
    wc.set_transport(None)


def test_rules():
    from app.courier import rules as R
    w = R.weights(0.8, {"l": 40, "b": 30, "h": 20})
    assert w["volumetric_kg"] == 4.8 and w["chargeable_kg"] == 5.0 and w["by"] == "volumetric" and any("Dabba bada" in n for n in w["notes"])
    assert R.weights(1.2, {"l": 10, "b": 10, "h": 10})["chargeable_kg"] == 1.5 and R.slab(0.5) == 0.5
    assert R.state_of("Undelivered - Customer not available") == "exception" and R.state_of("Delivered") == "delivered"
    assert R.state_of("Out For Delivery") == "out_for_delivery" and R.state_of("RTO Initiated") == "rto"
    assert R.state_of("Picked Up") == "picked" and R.state_of("In Transit") == "in_transit" and R.state_of("Pickup Scheduled") == "booked"
    assert R.state_of("Shipment cancelled") == "cancelled" and R.state_of("xyz hub ka ajeeb shabd") is None
    assert R.ndr_reason("Consignee refused to accept") == "refused" and R.ndr_reason("Incomplete address") == "address"
    assert R.ndr_reason("Customer not available") == "not_available"
    r, got = R.parse_rules("Sabse sasta courier lo. COD par Delhivery. Ekart mat lena. 5 kg se upar Xpressbees")
    assert r["prefer"] == "cheapest" and r["cod_carrier"] == "delhivery" and r["avoid"] == ["ekart"] and r["heavy_kg"] == 5 and len(got) == 4
    opts = [{"courier": "Xpressbees Surface", "rate": 72.5, "days": 4, "cod": True}, {"courier": "Delhivery Surface", "rate": 81, "days": 3, "cod": True},
            {"courier": "Ekart Logistics", "rate": 65, "days": 5, "cod": True}]
    assert R.choose(opts, r, cod=False, kg=1)["best"]["courier"] == "Xpressbees Surface"         # Ekart avoided, cheapest left
    assert R.choose(opts, r, cod=True, kg=1)["best"]["courier"] == "Delhivery Surface"           # her COD rule
    assert R.choose(opts, {"prefer": "fastest"}, cod=False, kg=1)["best"]["courier"] == "Delhivery Surface"
    assert R.choose([{"courier": "X", "rate": None}], {}, False, 1)["best"]["rate"] is None      # never invented
    assert R.goods_check("2 power bank aur patakhe")["prohibited"] == ["aag pakadne wali cheez"]
    assert R.goods_check("power bank 10000mAh")["restricted"]
    assert R.mask_phone("9876543210") == "98XXXXXX10" and R.pincode_ok("411001") and not R.pincode_ok("011001")
    h = R.remit_header(["Order ID", "AWB No", "COD Amount", "UTR", "Remittance Date"])
    assert h == {"awb": 1, "amount": 2, "utr": 3, "date": 4, "order": 0}


def test_parcel_quote_card_and_her_tap(cr):
    S, fake = cr
    S.set_keys(T, "shiprocket", {"email": "api@riya.in", "password": "x" * 10, "pickup_location": "Akot shop"})
    st = S.settings(T)
    assert st["joined"]["shiprocket"] and st["default_carrier"] == "shiprocket" and "x" * 10 not in json.dumps(st)
    S.set_rules(T, "Sabse sasta. Ekart mat lena.")
    p = S.new_parcel(T, order_ref="ORD-77", customer=CUST, items="Blue kurti x1 @ 899", payment="cod", weight_kg=0.6, dims={"l": 30, "b": 25, "h": 5})
    v = p["parcel"]
    assert v["number"] == "P-0001" and v["cod_amount"] == 899 and v["phone_masked"] == "98XXXXXX10" and not v["blocking"]
    with pytest.raises(S.CourierError):
        S.book_request(T, "P-0001")                    # no quote yet: nothing invented
    q = S.check(T, "P-0001")
    assert q["best"]["courier"] == "Xpressbees Surface" and q["parcel"]["serviceable"]["ok"] and q["parcel"]["serviceable"]["cod"]
    assert all(o["courier"] != "Ekart Logistics" for o in q["ranked"])
    b = S.book_request(T, "P-0001")
    card = b["card"]
    assert card["kind"] == "book" and card["money"] and card["body"]["rate"] == 72.5 and b["parcel"]["status"] == "waiting"
    assert not any(c[2].endswith("/orders/create/adhoc") for c in fake.calls)       # nothing booked before her tap
    with pytest.raises(S.CourierError):
        S.decide(T, card["id"], True, card["hash"])     # not by_tap -> refused
    with pytest.raises(S.CourierError):
        S.decide(T, card["id"], True, "0" * 64, by_tap=True)
    # a change after the card makes it stale
    S.update_parcel(T, "P-0001", weight_kg=0.7)
    assert S.cards(T, "stale")[0]["id"] == card["id"]
    S.check(T, "P-0001")
    card = S.book_request(T, "P-0001")["card"]
    out = S.decide(T, card["id"], True, card["hash"], by_tap=True)
    pv = out["parcel"]
    assert pv["status"] == "booked" and pv["awb"] == "SR12345678" and pv["carrier"] == "Xpressbees Surface"
    full = S.parcel_view(T, "SR12345678")
    assert full["label"].get("path", "").endswith(".pdf") and full["booking"]["pickup"]["date"].startswith("2026-10-24")
    assert out["card"]["status"] == "done" and "AWB SR12345678" in out["say"]
    with pytest.raises(S.CourierError):
        S.decide(T, card["id"], True, card["hash"], by_tap=True)        # once
    # tracking: the carrier's words kept exactly; unknown words never change the state
    fake.track_status = "Reached at destination hub"
    t = S.track(T, "P-0001")
    assert t["parcel"]["status"] == "in_transit" and t["parcel"]["raw"] == "Reached at destination hub" and t["parcel"]["edd"] == "2026-10-27"
    fake.track_status = "Kuch alag sa shabd"
    t = S.track(T, "P-0001")
    assert t["parcel"]["status"] == "in_transit" and "jo courier ne likha" in t["say"]
    fake.track_status = "Undelivered - Consignee not available"
    t = S.track(T, "P-0001")
    assert t["parcel"]["status"] == "exception" and t["parcel"]["ndr"]["reason"] == "not_available"
    m = S.ndr_message(T, "P-0001")
    assert "wa.me/919876543210" in m["whatsapp"] and "OTP" in m["text"] and "SR12345678" in m["text"]
    n = S.ndr_request(T, "P-0001", "reattempt", when="2099-01-02", note="shaam ko ghar")
    assert n["card"]["kind"] == "ndr" and not any("/ndr/" in c[2] for c in fake.calls)
    S.decide(T, n["card"]["id"], True, n["card"]["hash"], by_tap=True)
    assert any(c[2].endswith("/ndr/SR12345678/action") for c in fake.calls)
    fake.track_status = "Delivered"
    assert S.track(T, "P-0001")["parcel"]["status"] == "delivered"
    w = S.where(T, "ORD-77")
    assert "SR12345678" in w["say"] and "Delivered" in w["say"]


def test_delhivery_eway_goods_reject_and_manual(cr):
    S, fake = cr
    S.set_keys(T, "delhivery", {"token": "dltok", "pickup_location": "RIYA WH"})
    # above Rs 50,000 to another state (no GSTIN = treated as inter-state): e-way bill number needed before a card
    big = S.new_parcel(T, customer={**CUST, "state": "Karnataka"}, items=[{"name": "Saree set", "qty": 10, "price": 6000}], weight_kg=4)
    assert any("e-way bill" in b for b in big["parcel"]["blocking"])
    S.check(T, big["parcel"]["number"])
    with pytest.raises(S.CourierError):
        S.book_request(T, big["parcel"]["number"])
    S.update_parcel(T, big["parcel"]["number"], eway_no="351234567890")
    S.check(T, big["parcel"]["number"])
    card = S.book_request(T, big["parcel"]["number"])["card"]
    assert card["body"]["provider"] == "delhivery" and card["body"]["rate"] == 88.0
    r = S.decide(T, card["id"], False, card["hash"], by_tap=True, reason="kal bhejenge")
    assert r["card"]["status"] == "rejected" and r["parcel"]["status"] == "draft"
    # prohibited goods never get a card
    bad = S.new_parcel(T, customer=CUST, items="patakhe x2 @ 300", weight_kg=1)
    assert bad["parcel"]["blocking"]
    # manual carrier: she books, types the AWB; tracking link to the carrier's own page
    S.forget_keys(T, "delhivery")
    m = S.new_parcel(T, customer=CUST, items="Dupatta x1 @ 400", weight_kg=0.3)
    out = S.book_request(T, m["parcel"]["number"])
    assert out["parcel"]["status"] == "manual" and any("AWB" in x for x in out["manual"])
    a = S.set_awb(T, m["parcel"]["number"], "DT1234567", "DTDC")
    assert a["parcel"]["status"] == "booked" and a["parcel"]["track_link"] == "https://www.dtdc.com"
    tr = S.track(T, m["parcel"]["number"])
    assert "dtdc" in tr["say"].lower()
    with pytest.raises(S.CourierError):
        S.set_awb(T, big["parcel"]["number"], "DT1234567")                 # same AWB twice refused


def test_customer_cod_manifest_and_return(cr, monkeypatch):
    S, fake = cr
    from app.agent.courier_tools import COURIER_BIZ_HANDLERS
    from app.agent.tools import Ctx, ToolError
    from app.db import session
    from app.employee.models import BizContact
    S.set_keys(T, "shiprocket", {"email": "api@riya.in", "password": "x" * 10, "pickup_location": "Akot shop"})
    p1 = S.new_parcel(T, order_ref="ORD-1", customer=CUST, items="Kurti x1 @ 899", payment="cod", weight_kg=0.5)["parcel"]
    p2 = S.new_parcel(T, order_ref="ORD-2", customer={**CUST, "name": "Asha", "phone": "9000000001"}, items="Saree x1 @ 2500", weight_kg=0.8)["parcel"]
    for p in (p1, p2):
        S.check(T, p["number"])
        c = S.book_request(T, p["number"])["card"]
        S.decide(T, c["id"], True, c["hash"], by_tap=True)
    man = S.manifest(T)
    assert len(man["parcels"]) == 2 and man["cod_total"] == 899
    with session() as s:
        cid = BizContact(tenant_id=T, wa_id="919876543210", name="Sneha")
        s.add(cid)
        s.flush()
        cid = cid.id
    ctx = conv_ctx()
    cust = Ctx(T, ctx.conversation_id, actor=f"customer:{cid}")
    mine = asyncio.run(COURIER_BIZ_HANDLERS["biz_parcel_status"](cust))
    assert [x["order_ref"] for x in mine["parcels"]] == ["ORD-1"] and mine["parcels"][0]["cod_to_pay"] == "₹899"
    assert "address" not in json.dumps(mine) and "Asha" not in json.dumps(mine)
    assert asyncio.run(COURIER_BIZ_HANDLERS["biz_parcel_status"](cust, ref="ORD-2"))["parcels"] == []    # not theirs
    with pytest.raises(ToolError):
        asyncio.run(COURIER_BIZ_HANDLERS["biz_parcel_fix"](cust, when="2099-01-01"))                     # nothing stuck
    fake.track_status = "Undelivered - address incomplete"
    S.track(T, p1["number"])
    fx = asyncio.run(COURIER_BIZ_HANDLERS["biz_parcel_fix"](cust, address="12 MG Road, near Camp temple", note="landmark diya"))
    assert "dukaan" in fx["say"]
    assert S.cards(T)[0]["kind"] == "ndr" and S.cards(T)[0]["body"]["by"] == "customer"           # her card, nothing sent
    assert not any("/ndr/" in c[2] for c in fake.calls)
    # delivered COD -> remittance sheet
    fake.track_status = "Delivered"
    S.track(T, p1["number"])
    S.save_settings(T, remit_days=7)
    rep = S.cod_report(T)
    assert rep["pending_count"] == 1 and rep["pending_amount"] == 899 and rep["late"] == []
    csv_data = "Order ID,AWB No,COD Amount,UTR,Remittance Date\nORD-1,SR12345678,850,UTR555,2026-10-30\nX,ZZ99999999,100,UTR556,2026-10-30\n"
    out = S.remit_import(T, csv_data.encode(), "remit.csv")
    assert out["matched"] == 1 and out["unknown"] == ["ZZ99999999"] and out["report"]["mismatch"][0]["diff"] == -49
    again = S.remit_import(T, csv_data.encode(), "remit.csv")
    assert again["duplicates"] == 2 and again["added"] == 0
    # return label for a delivered parcel: card, then her tap -> reverse pickup through the Wapsi Shiprocket client
    r = S.return_request(T, ref=p1["number"], reason="size chhota")
    assert r["card"]["kind"] == "reverse" and r["parcel"]["kind"] == "reverse"
    d = S.decide(T, r["card"]["id"], True, r["card"]["hash"], by_tap=True)
    assert d["parcel"]["awb"] == "RV998877" and any(c[2].endswith("/orders/create/return") for c in fake.calls)
    # DPDP: forget a finished parcel
    assert "mita" in S.forget(T, p1["number"])["say"] and S.parcel_view(T, p1["number"])["customer"]["phone"] == ""


def test_wapsi_return_label(cr, monkeypatch):
    S, fake = cr
    from app.wapsi import service as W
    W.save_settings(T, business="Riya", warehouse=WH)
    W.set_policy(T, "7 din return. refund original mode mein.")
    r = W.new_return(T, customer={"name": "Sneha P", "phone": "9876543210", "address": "12 MG Rd", "city": "Pune", "pincode": "411001"},
                     items=[{"name": "Kurti", "qty": 1, "price": 899}], reason="wrong_item", delivered_on=datetime.now().date().isoformat(), want="refund")
    rid = r["return"]["id"]
    with pytest.raises(S.CourierError):
        S.return_request(T, wapsi_ref=rid)              # not approved in Wapsi yet
    W.decide(T, rid, "approve")
    assert W.return_view(T, rid)["status"] in ("approved", "pickup_manual")
    out = S.return_request(T, wapsi_ref=rid)
    assert out["card"]["body"]["provider"] == "wapsi" and out["parcel"]["wapsi_ref"] == rid and out["parcel"]["kind"] == "reverse"
    d = S.decide(T, out["card"]["id"], True, out["card"]["hash"], by_tap=True)
    assert d["card"]["status"] == "done" and d["parcel"]["status"] == "manual"      # Wapsi without keys: her checklist
    assert W.return_view(T, rid)["status"] == "pickup_manual"


def test_tools_api_and_tick(cr, monkeypatch):
    S, fake = cr
    from app.agent.courier_tools import COURIER_HANDLERS, COURIER_TOOLS
    from app.agent.tools import Ctx, ToolError
    from app.courier.api import make_router
    assert {t["name"] for t in COURIER_TOOLS} == {"courier", "courier_dekho"}
    ctx = conv_ctx()
    with pytest.raises(ToolError):
        asyncio.run(COURIER_HANDLERS["courier"](ctx, action="settings", warehouse={"token": "abc"}))
    with pytest.raises(ToolError):
        asyncio.run(COURIER_HANDLERS["courier"](Ctx(T, ctx.conversation_id, actor="staff:x"), action="rules", text="sabse sasta"))
    with pytest.raises(ToolError):
        asyncio.run(COURIER_HANDLERS["courier_dekho"](Ctx(T, ctx.conversation_id, actor="customer:x"), what="where"))
    r = asyncio.run(COURIER_HANDLERS["courier"](ctx, action="rules", text="sabse tez wala"))
    assert r["rules"]["prefer"] == "fastest"
    p = asyncio.run(COURIER_HANDLERS["courier"](ctx, action="new", customer=CUST, items="Kurti x1 @ 500", weight_kg=0.4))
    num = p["parcel"]["number"]
    staff = Ctx(T, ctx.conversation_id, actor="staff:s1")
    assert asyncio.run(COURIER_HANDLERS["courier_dekho"](staff, what="parcel", ref=num))["number"] == num
    # API: keys, check, card, decide (her tap) - the tool cannot decide
    app_ = FastAPI()
    app_.include_router(make_router(require_key=lambda: None, current_tenant=lambda: T))
    c = TestClient(app_)
    assert c.put("/api/courier/keys/shiprocket", json={"creds": {"email": "api@riya.in", "password": "p" * 8, "pickup_location": "Akot shop"}}).status_code == 200
    assert c.post(f"/api/courier/parcels/{num}/check").status_code == 200
    bk = asyncio.run(COURIER_HANDLERS["courier"](ctx, action="book", ref=num))
    assert bk["card"] and "next" in bk
    assert bk["card"]["body"]["courier"] == "Delhivery Surface"          # fastest rule
    home = c.get("/api/courier").json()
    assert home["cards"][0]["id"] == bk["card"]["id"] and "p" * 8 not in json.dumps(home)
    bad = c.post(f"/api/courier/cards/{bk['card']['id']}/decide", json={"yes": True, "hash": "x"})
    assert bad.status_code == 400
    ok = c.post(f"/api/courier/cards/{bk['card']['id']}/decide", json={"yes": True, "hash": bk["card"]["hash"]})
    assert ok.status_code == 200 and ok.json()["parcel"]["status"] == "booked"
    lab = c.get(f"/api/courier/parcels/{num}/label")
    assert lab.status_code == 200 and lab.content.startswith(b"%PDF")
    assert c.get("/api/courier/where", params={"q": num}).json()["parcels"][0]["number"] == num
    up = c.post("/api/courier/remit", files={"file": ("r.csv", b"AWB,Amount\nSR12345678,0\n", "text/csv")})
    assert up.status_code == 200
    # worker: tracking poll + morning note
    fake.track_status = "Out for delivery"
    from app.courier.models import CourierSettings
    from app.db import session
    with session() as s:
        s.get(CourierSettings, T).morning_time = "00:00"
    res = S.tick(datetime.now(timezone.utc))
    assert res["polled"] == 1 and S.parcel_view(T, num)["status"] == "out_for_delivery"
    assert S.tick(datetime.now(timezone.utc) + timedelta(minutes=1))["polled"] == 0           # throttled
