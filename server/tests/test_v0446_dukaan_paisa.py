"""v0.446 DUKAAN PAISA (web Step 4 = W4 + the first of W5): her website shop takes online payments through HER gateway on the
app payment engine - paid ONLY from the gateway (signed webhook or server read, amount must match), unpaid online orders
released, late money never lost, refunds only by her tap; coupons applied by the server (once per mobile number, a cancel
gives the use back); reviews only from buyers whose order was delivered, once per item, her hide."""
import json
from datetime import timedelta

import httpx
import pytest
from fastapi.testclient import TestClient

from tests.test_v0351_dukaan import BUYER, _built_shop
from tests.test_v0419_paisa import SECRET, FakeRazorpay, _paid_event
from tests.test_v121_site import T, site_env  # noqa: F401  (fixture)


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.471.0"


@pytest.fixture()
def rzp():
    from app.paygate import gw as GW
    f = FakeRazorpay()
    GW.set_transport(httpx.MockTransport(f))
    yield f
    GW.set_transport(None)


_N = iter(range(1, 100000))


def _buy(c, sid, items, method="online", phone="9876543210", **kw):
    return c.post(f"/api/site-shop/{sid}/order", json={**BUYER, "phone": phone, "method": method, "items": items, **kw},
                  headers={"x-real-ip": f"10.9.{next(_N)}.1"})


def _hook(c, key, event, secret=SECRET):
    import hashlib
    import hmac
    raw = json.dumps(event).encode()
    sig = hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()
    return c.post(f"/api/app-api/{key}/pay/webhook", content=raw, headers={"X-Razorpay-Signature": sig, "Content-Type": "application/json"})


@pytest.fixture()
def shop(site_env, rzp):
    from app.main import app
    from app.site import service as S
    from app.site import shoppay as SP
    sid = _built_shop(S)
    c = TestClient(app)
    assert c.get(f"/api/site-shop/{sid}/products").json()["online"] is False
    assert _buy(c, sid, [{"slug": "kaju-katli", "qty": 1}]).status_code == 400                    # no gateway = no online
    con = c.post(f"/api/sites/{sid}/payments/connect").json()
    app_id = con["app"]
    assert con["on"] is False
    st = c.put(f"/api/apps/{app_id}/pay/keys", json={"gateway": "razorpay", "keys": {"key_id": "rzp_test_abc", "key_secret": "sekret",
                                                                                       "webhook_secret": SECRET}}).json()
    assert st["on"] and "sekret" not in json.dumps(st)
    assert c.get(f"/api/site-shop/{sid}/products").json()["online"] is True
    key = json.loads(SP.project_of(sid).android)["app_key"]
    return c, sid, app_id, key


def _order_row(sid, number):
    from app.db import session
    from app.site import shop as SH
    with session() as s:
        o = s.query(SH.SiteShopOrder).filter_by(site_id=sid, number=number).one()
        s.expunge(o)
    return o


def test_online_order_is_paid_only_by_the_gateway(shop, rzp):
    from app.site import shop as SH
    c, sid, app_id, key = shop
    o = _buy(c, sid, [{"slug": "kaju-katli", "qty": 2, "price": 1}], total=5).json()
    assert o["status"] == "new" and o["total"] == "₹1,840" and o["method"] == "online"
    assert f"/api/app-api/{key}/pay/p/" in o["online"]["url"]                                       # Hoola's pay page
    assert rzp.orders["order_1"]["amount"] == 184000                                                 # the SERVER's total
    u = o["online"]["url"]
    page = c.get(u if u.startswith("/") else "/" + u.split("/", 3)[3])
    assert page.status_code == 200 and "checkout.razorpay.com" in page.text and "sekret" not in page.text
    # the customer cannot mark it paid: the old UPI 'I paid' path is for UPI orders only, and a bad signature changes nothing
    assert _hook(c, key, _paid_event("order_1", "pay_1", 184000), secret="guess").status_code == 401
    assert _order_row(sid, o["number"]).status == "new"
    assert _hook(c, key, _paid_event("order_1", "pay_1", 184000)).json()["applied"] == 1
    _hook(c, key, _paid_event("order_1", "pay_1", 184000))                                           # twice = once
    row = _order_row(sid, o["number"])
    assert row.status == "confirmed" and row.utr == "pay_1"
    tr = c.get(f"/api/site-shop/{sid}/order/{o['number']}?t={o['token']}").json()
    assert tr["paid_online"] is True and tr["status"] == "confirmed"
    hist = json.loads(row.history)
    assert hist[-1]["to"] == "confirmed" and "verified" in hist[-1]["by"]
    # a wrong amount from the gateway: held, not paid
    o2 = _buy(c, sid, [{"slug": "motichoor-laddoo", "qty": 1}]).json()
    _hook(c, key, _paid_event("order_2", "pay_2", 100))
    assert _order_row(sid, o2["number"]).status == "new"
    assert c.get(f"/api/apps/{app_id}/pay").json()["totals"]["mismatch"] == 1
    # paid but the webhook never came: the pay page asks the gateway itself (her keys)
    o3 = _buy(c, sid, [{"slug": "motichoor-laddoo", "qty": 1}]).json()
    rzp.captured["order_3"] = {"id": "pay_3", "status": "captured", "amount": SH.paise(o3["total"]), "method": "upi"}
    tok = o3["online"]["url"].rsplit("/", 1)[1]
    assert c.get(f"/api/app-api/{key}/pay/s/{tok}").json()["status"] == "paid"
    assert _order_row(sid, o3["number"]).status == "confirmed"
    # pay again for a waiting order gives the SAME payment within its window
    o4 = _buy(c, sid, [{"slug": "motichoor-laddoo", "qty": 1}]).json()
    again = c.post(f"/api/site-shop/{sid}/order/{o4['number']}/pay", json={"token": o4["token"]}).json()
    assert again["payment"] == o4["online"]["payment"]
    assert c.post(f"/api/site-shop/{sid}/order/{o4['number']}/pay", json={"token": "x"}).status_code in (403, 404)
    new2 = c.post(f"/api/site-shop/{sid}/order/{o2['number']}/pay", json={"token": o2["token"]}).json()
    assert new2["payment"] != o2["online"]["payment"]                       # the held (mismatch) one is never reused


def test_refund_only_by_her_tap_and_only_online_orders(shop, rzp):
    c, sid, app_id, key = shop
    o = _buy(c, sid, [{"slug": "kaju-katli", "qty": 1}]).json()
    _hook(c, key, _paid_event("order_1", "pay_1", 90000 + 4000))
    assert _order_row(sid, o["number"]).status == "confirmed"
    r = c.post(f"/api/sites/{sid}/shop/orders/{o['number']}/refund", json={"amount": "100", "why": "late"}).json()
    assert r["status"] in ("done", "processed") and len(rzp.refunds) == 1
    assert "Refund" in json.loads(_order_row(sid, o["number"]).history)[-1]["note"]
    assert c.post(f"/api/sites/{sid}/shop/orders/{o['number']}/refund", json={"amount": "99999"}).status_code == 400   # never more
    cod = _buy(c, sid, [{"slug": "motichoor-laddoo", "qty": 1}], method="cod").json()
    assert c.post(f"/api/sites/{sid}/shop/orders/{cod['number']}/refund", json={}).status_code == 409


def test_unpaid_online_orders_are_released_and_late_money_is_never_lost(shop, rzp):
    from app.db import now, session
    from app.site import shop as SH
    from app.site import shoppay as SP
    c, sid, app_id, key = shop
    before = next(p for p in SH.products(sid) if p["slug"] == "kaju-katli")["stock"]
    o = _buy(c, sid, [{"slug": "kaju-katli", "qty": 1}]).json()
    assert next(p for p in SH.products(sid) if p["slug"] == "kaju-katli")["stock"] == before - 1
    assert SP.release_unpaid() == 0                                                                 # not yet
    with session() as s:
        x = s.query(SH.SiteShopOrder).filter_by(site_id=sid, number=o["number"]).one()
        x.created_at = now() - timedelta(hours=4)
    assert SP.release_unpaid() == 1
    assert _order_row(sid, o["number"]).status == "cancelled"
    assert next(p for p in SH.products(sid) if p["slug"] == "kaju-katli")["stock"] == before          # stock back
    _hook(c, key, _paid_event("order_1", "pay_9", SH.paise(o["total"])))                             # the money came late
    row = _order_row(sid, o["number"])
    assert row.status == "cancelled" and row.utr == "pay_9" and "refund" in json.loads(row.history)[-1]["note"]


def test_coupons_on_the_website_are_the_servers(shop):
    c, sid, app_id, key = shop
    assert c.put(f"/api/apps/{app_id}/coupons", json={"code": "DIWALI10", "kind": "percent", "value": 10, "once": True}).status_code == 200
    chk = c.post(f"/api/site-shop/{sid}/coupon", json={"code": "diwali10", "items": [{"slug": "kaju-katli", "qty": 1}]}).json()
    assert chk["ok"] and chk["discount"] == "₹90" and chk["total"] == "₹810"
    assert c.post(f"/api/site-shop/{sid}/coupon", json={"code": "NOPE99", "items": []}).json()["ok"] is False
    o = _buy(c, sid, [{"slug": "kaju-katli", "qty": 1}], method="cod", coupon="DIWALI10", discount=900).json()
    assert o["discount"] == "₹90" and o["coupon"] == "DIWALI10" and o["total"] == "₹850"            # 900-90 + ₹40 delivery
    again = _buy(c, sid, [{"slug": "motichoor-laddoo", "qty": 1}], method="cod", coupon="DIWALI10").json()
    assert again["discount"] == "" and "DIWALI10" in again["coupon_note"]                            # once per mobile
    other = _buy(c, sid, [{"slug": "motichoor-laddoo", "qty": 1}], method="cod", coupon="DIWALI10", phone="9123456789").json()
    assert other["discount"]                                                                         # someone else may
    assert c.post(f"/api/sites/{sid}/shop/orders/{o['number']}", json={"to": "cancelled"}).status_code == 200
    back = _buy(c, sid, [{"slug": "motichoor-laddoo", "qty": 1}], method="cod", coupon="DIWALI10").json()
    assert back["discount"]                                                                          # the cancel gave it back


def test_reviews_only_from_delivered_buyers(shop):
    from app.site import service as S
    c, sid, app_id, key = shop
    o = _buy(c, sid, [{"slug": "kaju-katli", "qty": 1}], method="cod").json()
    rv = lambda slug, stars=5, tok=None: c.post(f"/api/site-shop/{sid}/order/{o['number']}/review",  # noqa: E731
                                                json={"token": tok or o["token"], "slug": slug, "stars": stars, "text": "Bahut badhiya"})
    assert rv("kaju-katli").status_code == 409                                                       # not delivered yet
    for to in ("confirmed", "shipped", "delivered"):
        S.shop_move(T, sid, o["number"], to)
    assert rv("kaju-katli", tok="wrong").status_code in (403, 404)
    assert rv("motichoor-laddoo").status_code == 400                                                 # not in this order
    assert rv("kaju-katli", stars=9).status_code == 400
    assert rv("kaju-katli").json()["ok"]
    assert rv("kaju-katli").status_code == 409                                                       # once
    pub = c.get(f"/api/site-shop/{sid}/reviews?slug=kaju-katli").json()
    assert pub["summary"]["kaju-katli"] == {"avg": 5.0, "count": 1} and pub["reviews"][0]["name"] == "Asha"
    assert "phone" not in json.dumps(pub) and "9876543210" not in json.dumps(pub)
    assert c.get(f"/api/site-shop/{sid}/products").json()["ratings"]["kaju-katli"]["count"] == 1
    mine = c.get(f"/api/sites/{sid}/shop/reviews").json()["reviews"]
    c.post(f"/api/sites/{sid}/shop/reviews/{mine[0]['id']}", json={"hide": True})
    assert c.get(f"/api/site-shop/{sid}/reviews").json()["reviews"] == []


def test_the_shop_page_and_console_carry_it():
    from pathlib import Path
    root = Path(__file__).resolve().parents[1] / "app"
    js = (root / "site" / "assets" / "hoola-shop.js").read_text()
    for k in ("'online'", "/coupon", "/review", "reviewBox", "starsOn", "Abhi pay karein"):
        assert k in js, k
    con = (root / "static" / "console" / "build.js").read_text()
    assert "payBox" in con and "/payments/connect" in con and "data-refund" in con and "/coupons" in con
