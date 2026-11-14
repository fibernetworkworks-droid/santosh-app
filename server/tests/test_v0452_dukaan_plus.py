"""v0.452 DUKAAN PLUS (web Step 4B): GST invoice + credit note for website orders on HER ONE series (shared with her app),
marketplace sellers (her approval, product moderation, Route transfers of the sellers' shares once), Shiprocket courier
(her tap, AWB + label + tracking), opted-in cart reminders (SHE taps the WhatsApp link), AutoPay plans for website members."""
import json

import httpx
import pytest
from fastapi.testclient import TestClient

from tests.test_v0351_dukaan import _built_shop
from tests.test_v0419_paisa import SECRET, _paid_event
from tests.test_v0446_dukaan_paisa import _buy, _hook, _order_row, rzp, shop  # noqa: F401  (fixtures)
from tests.test_v121_site import T, site_env  # noqa: F401  (fixture)


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.906.0"


def _gstin():
    from app.appmaker import gst as G
    first = "27AAPFU0939F1Z"
    return first + G.check_digit(first)


# ---------------------------------------------------------------- 1. GST on one series
def test_website_gst_invoice_and_credit_note_share_her_one_series(shop):
    from app.appmaker import gst as G
    from app.site import service as S
    c, sid, app_id, key = shop
    o = _buy(c, sid, [{"slug": "kaju-katli", "qty": 1}], method="cod").json()
    r = c.get(f"/api/sites/{sid}/shop/orders/{o['number']}/invoice")
    assert r.status_code == 409 and "GSTIN" in r.json()["error"]                       # not registered = no tax invoice
    assert c.put(f"/api/apps/{app_id}/gst", json={"gstin": _gstin(), "legal_name": "Sharma Sweets LLP"}).status_code == 200
    assert c.get(f"/api/sites/{sid}/shop/orders/{o['number']}/invoice").status_code == 409   # not confirmed yet
    S.shop_move(T, sid, o["number"], "confirmed")
    pdf = c.get(f"/api/sites/{sid}/shop/orders/{o['number']}/invoice")
    assert pdf.status_code == 200 and pdf.content[:5] == b"%PDF-" and "INV-" in pdf.headers["content-disposition"]
    again = c.get(f"/api/sites/{sid}/shop/orders/{o['number']}/invoice")
    assert again.headers["content-disposition"] == pdf.headers["content-disposition"]      # the number is given ONCE
    o2 = _buy(c, sid, [{"slug": "motichoor-laddoo", "qty": 1}], method="cod").json()
    S.shop_move(T, sid, o2["number"], "confirmed")
    p2 = c.get(f"/api/site-shop/{sid}/order/{o2['number']}/invoice?t={o2['token']}")          # the buyer, by the private link
    assert p2.status_code == 200 and "INV-" in p2.headers["content-disposition"]
    assert c.get(f"/api/site-shop/{sid}/order/{o2['number']}/invoice?t=nope").status_code in (403, 404)
    nos = sorted(h.split('"')[1] for h in (pdf.headers["content-disposition"], p2.headers["content-disposition"]))
    assert nos[0].endswith("0001.pdf") and nos[1].endswith("0002.pdf")                       # consecutive, one series
    # the app's own series continues from the website's numbers (one GSTIN = one series)
    from app.site import shoppay as SP
    p = SP.project_of(sid)
    assert G._be(p)["gst"]["seq"][G.fy()] == 2
    # a cancelled invoiced order gets its credit note, once
    out = c.post(f"/api/sites/{sid}/shop/orders/{o['number']}", json={"to": "cancelled"}).json()
    cn = c.get(f"/api/sites/{sid}/shop/orders/{o['number']}/invoice?doc=credit")
    assert cn.status_code == 200 and "CN-" in cn.headers["content-disposition"]
    assert c.get(f"/api/sites/{sid}/shop/orders/{o2['number']}/invoice?doc=credit").status_code == 404   # never cancelled
    assert out


# ---------------------------------------------------------------- 2. marketplace
def test_marketplace_sellers_moderation_and_route_transfers_once(shop, rzp):
    c, sid, app_id, key = shop
    assert "Sell with us" in c.get(f"/api/site-shop/{sid}/seller").text
    assert c.post(f"/api/site-shop/{sid}/vendor/apply", json={"name": "Ravi Farsan", "phone": "123"}).status_code == 400
    assert c.post(f"/api/site-shop/{sid}/vendor/apply", json={"name": "Ravi Farsan", "phone": "9123456780", "gstin": "BAD"}).status_code == 400
    assert c.post(f"/api/site-shop/{sid}/vendor/apply", json={"name": "Ravi Farsan", "phone": "9123456780"}).json()["ok"]
    vs = c.get(f"/api/sites/{sid}/shop/vendors").json()["vendors"]
    vid = vs[0]["id"]
    assert vs[0]["status"] == "pending" and not vs[0].get("portal")
    assert c.post(f"/api/sites/{sid}/shop/vendors/{vid}", json={"account": "1234567890"}).status_code == 400   # never a bank no.
    v = c.post(f"/api/sites/{sid}/shop/vendors/{vid}", json={"status": "approved", "commission": 20, "account": "acc_RaviFarsan01"}).json()
    portal = v["portal"]
    assert c.get(f"/api/site-shop/{sid}/vendor/wrong").status_code == 404
    add = c.post(f"/api/site-shop/{sid}/vendor/{portal}/product", json={"title": "Bhakarwadi", "price": "200", "unit": "250 g"}).json()
    assert add["ok"]
    assert "bhakarwadi" not in {p["slug"] for p in c.get(f"/api/site-shop/{sid}/products").json()["products"]}   # waits for HER OK
    assert c.get(f"/api/sites/{sid}/shop/vendors").json()["pending_products"][0]["slug"] == "bhakarwadi"
    c.post(f"/api/sites/{sid}/shop/products/bhakarwadi/approve", json={"ok": True})
    assert "bhakarwadi" in {p["slug"] for p in c.get(f"/api/site-shop/{sid}/products").json()["products"]}
    # a paid online order with her item + the seller's item: the seller gets (200 x 2) - 20% = 320, once
    o = _buy(c, sid, [{"slug": "bhakarwadi", "qty": 2}, {"slug": "kaju-katli", "qty": 1}]).json()
    from app.site import shop as SH
    _hook(c, key, _paid_event("order_1", "pay_1", SH.paise(o["total"])))
    _hook(c, key, _paid_event("order_1", "pay_1", SH.paise(o["total"])))
    assert len(rzp.transfers) == 1 and rzp.transfers[0]["transfers"] == [
        {"account": "acc_RaviFarsan01", "amount": 32000, "currency": "INR", "notes": {"hoola": f"order {o['number']}"}}]
    page = c.get(f"/api/site-shop/{sid}/vendor/{portal}").json()
    assert page["orders"][0]["title"] == "Bhakarwadi" and page["sales"] == "₹400" and page["earn"] == "₹320"
    assert "9876543210" not in json.dumps(page) and "Station Road" not in json.dumps(page)       # never the buyer's details
    c.post(f"/api/sites/{sid}/shop/vendors/{vid}", json={"status": "blocked"})
    assert "bhakarwadi" not in {p["slug"] for p in c.get(f"/api/site-shop/{sid}/products").json()["products"]}
    assert c.get(f"/api/site-shop/{sid}/vendor/{portal}").status_code == 404


# ---------------------------------------------------------------- 3. Shiprocket
class FakeShiprocket:
    def __init__(self):
        self.calls = []

    def __call__(self, req: httpx.Request) -> httpx.Response:
        p = req.url.path
        self.calls.append(p)
        if p.endswith("/auth/login"):
            b = json.loads(req.content)
            return httpx.Response(200, json={"token": "srtok"}) if b["password"] == "right" else httpx.Response(400, json={"message": "Invalid"})
        assert req.headers.get("authorization") == "Bearer srtok"
        if p.endswith("/orders/create/adhoc"):
            b = json.loads(req.content)
            assert b["payment_method"] == "COD" and b["billing_pincode"] == "444101" and b["order_items"][0]["units"] == 1
            return httpx.Response(200, json={"order_id": 9001, "shipment_id": 7001, "status": "NEW"})
        if p.endswith("/courier/assign/awb"):
            return httpx.Response(200, json={"awb_assign_status": 1, "response": {"data": {"awb_code": "SR123456789", "courier_name": "Delhivery Surface"}}})
        if p.endswith("/courier/generate/label"):
            return httpx.Response(200, json={"label_created": 1, "label_url": "https://shiprocket.example/label.pdf"})
        if "/courier/track/awb/" in p:
            return httpx.Response(200, json={"tracking_data": {"shipment_track": [{"current_status": "IN TRANSIT"}],
                                                               "shipment_track_activities": [{"date": "2026-11-03", "activity": "Picked up", "location": "Akola"}]}})
        return httpx.Response(404, json={})


def test_shiprocket_ship_by_her_tap_and_tracking(shop):
    from app.site import service as S
    from app.site import shopplus as SPL
    c, sid, app_id, key = shop
    f = FakeShiprocket()
    SPL._TRANSPORT[0] = httpx.MockTransport(f)
    try:
        o = _buy(c, sid, [{"slug": "kaju-katli", "qty": 1}], method="cod").json()
        assert c.post(f"/api/sites/{sid}/shop/orders/{o['number']}/ship").status_code == 409            # not connected
        assert c.put(f"/api/sites/{sid}/shop/courier", json={"email": "api@x.in", "password": "wrong"}).status_code == 400
        v = c.put(f"/api/sites/{sid}/shop/courier", json={"email": "api@x.in", "password": "right", "pickup": "Akot shop"}).json()
        assert v["on"] and v["pickup"] == "Akot shop" and "right" not in json.dumps(v)
        assert c.post(f"/api/sites/{sid}/shop/orders/{o['number']}/ship").status_code == 409            # not confirmed yet
        S.shop_move(T, sid, o["number"], "confirmed")
        r = c.post(f"/api/sites/{sid}/shop/orders/{o['number']}/ship").json()
        assert r["awb"] == "SR123456789" and r["label"].endswith("label.pdf") and r["status"] == "shipped"
        assert _order_row(sid, o["number"]).status == "shipped"
        assert c.post(f"/api/sites/{sid}/shop/orders/{o['number']}/ship").status_code == 409            # never twice
        tr = c.get(f"/api/site-shop/{sid}/order/{o['number']}/track?t={o['token']}").json()
        assert tr["awb"] == "SR123456789" and tr["status"] == "IN TRANSIT" and tr["events"][0]["where"] == "Akola"
    finally:
        SPL._TRANSPORT[0] = None


# ---------------------------------------------------------------- 4. cart reminders, opted in, she sends
def test_cart_reminders_only_opted_in_and_she_sends(shop):
    from datetime import timedelta

    from app.db import now, session
    from app.site import shopplus as SPL
    c, sid, app_id, key = shop
    items = [{"slug": "kaju-katli", "qty": 1}]
    assert c.post(f"/api/site-shop/{sid}/cart/remind", json={"phone": "9876543210", "items": items}).status_code == 400   # no tick
    h = c.post(f"/api/site-shop/{sid}/cart/remind", json={"phone": "9876543210", "name": "Asha", "items": items, "consent": True}).json()
    c.post(f"/api/site-shop/{sid}/cart/remind", json={"phone": "9123456780", "name": "Meena", "items": items, "consent": True})
    assert c.get(f"/api/sites/{sid}/shop/carts").json()["carts"] == []                            # not 2 hours yet
    with session() as s:
        for x in s.query(SPL.SiteShopCart).all():
            x.updated_at = now() - timedelta(hours=3)
    _buy(c, sid, items, method="cod", phone="9123456780")                                          # Meena ordered -> closed
    carts = c.get(f"/api/sites/{sid}/shop/carts").json()["carts"]
    assert [x["name"] for x in carts] == ["Asha"] and carts[0]["wa"].startswith("https://wa.me/919876543210?text=")
    assert "Kaju Katli" in carts[0]["items"] and "STOP" in carts[0]["wa"] and carts[0]["phone"] == "98******10"
    c.post(f"/api/sites/{sid}/shop/carts/{carts[0]['id']}/reminded")
    assert c.get(f"/api/sites/{sid}/shop/carts").json()["carts"] == []                            # once
    assert c.post(f"/api/site-shop/{sid}/cart/stop", json={"token": h["stop"]}).json()["ok"]
    assert c.post(f"/api/site-shop/{sid}/cart/remind", json={"phone": "9876543210", "items": items, "consent": True}).status_code == 409


# ---------------------------------------------------------------- 5. AutoPay on the website + pages
def test_autopay_plans_reach_website_members(shop, rzp, monkeypatch):
    from app.appmaker import ai as AAI
    from app.site import applink as AL
    from app.site import service as S
    c, sid, app_id, key = shop
    lists = [{"key": "orders", "label": "Orders", "rules": {"create": "member", "read": "own", "update": "admin", "delete": "admin"},
              "fields": [{"key": "item", "label": "Item", "type": "text", "required": True}]}]
    monkeypatch.setattr(AAI, "ask_json", lambda system, prompt, max_tokens=7000: {"summary": "orders", "lists": lists, "fields": [], "logic": {}})
    d = S.design_app(T, sid, "customers apna order track karein")["draft"]   # a linked site: the app's author + her tap
    AL.logic_apply(T, sid, d["hash"])
    assert c.post(f"/api/apps/{app_id}/pay/plans", json={"name": "Monthly sweets box", "amount": "999", "period": "month", "count": 12,
                                                         "her_tap": True}).status_code == 200
    base = f"/api/site-app/{sid}"
    plans = c.get(f"{base}/pay/plans").json()["plans"]
    assert plans[0]["name"] == "Monthly sweets box"
    assert c.post(f"{base}/pay/plans/{plans[0]['key']}/subscribe").status_code == 401                  # members only
    tok = c.post(f"{base}/signup", json={"email": "asha@x.in", "password": "pass-word-1", "name": "Asha", "consent": True}).json()["token"]
    sub = c.post(f"{base}/pay/plans/{plans[0]['key']}/subscribe", headers={"Authorization": "Bearer " + tok}).json()
    assert "/pay/p/" in (sub.get("path") or sub.get("url") or "")
    assert c.get(f"{base}/pay/subs", headers={"Authorization": "Bearer " + tok}).json()["subs"]


def test_pages_carry_it():
    from pathlib import Path
    root = Path(__file__).resolve().parents[1] / "app"
    js = (root / "site" / "assets" / "hoola-shop.js").read_text()
    for k in ("wishOn", "/cart/remind", "/invoice?t=", "/track?t=", "Saved for later"):
        assert k in js, k
    assert "/pay/plans" in (root / "site" / "assets" / "hoola-app.js").read_text()
    con = (root / "static" / "console" / "build.js").read_text()
    for k in ("plusBox", "/shop/vendors", "/shop/courier", "/shop/carts", "data-ship", "data-inv", "/gst`"):
        assert k in con, k
