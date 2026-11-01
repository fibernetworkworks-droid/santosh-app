"""v0.358 COUPON (App Sahayak Phase 22): her discount codes - checked in the cart, applied again by the server from its own
subtotal at order time and counted under a lock; a failing code never loses the order (full price + coupon_note); once per
customer, uses, min order, last date; a cancelled order gives the use back; receipts / GST invoices show it right."""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tests.test_v0314_app_backend import _built
from tests.test_v0352_kaam_baanto import _acct, _login
from tests.test_v0355_gst_bill import GOOD, _text
from tests.test_v132_android import droid_env  # noqa: F401  (fixture)


def test_coupons_end_to_end(droid_env):
    from app.appmaker import backend as BE
    from app.appmaker import gst as G
    from app.main import app
    c = TestClient(app)
    aid, conv, key, be = _built(droid_env)
    api = f"/api/app-api/{key}"
    p1 = c.get(f"/api/app-content/{key}").json()["lists"]["products"][0]
    price = float(p1["price"])
    for e, n in (("asha@example.com", "Asha"), ("neha@example.com", "Neha"), ("ravi@example.com", "Ravi")):
        _acct(c, api, e, n)
    mem = {m["email"]: m for m in c.get(f"/api/apps/{aid}/members").json()["members"]}
    c.post(f"/api/apps/{aid}/members/{mem['ravi@example.com']['id']}/role", json={"role": "staff"})
    ha, hn, hr = (_login(c, api, e, n) for e, n in (("asha@example.com", "Asha"), ("neha@example.com", "Neha"), ("ravi@example.com", "Ravi")))
    assert c.get(f"/api/app-content/{key}").json()["backend"].get("coupons") is False
    # making codes: bad ones refused
    assert c.put(f"/api/apps/{aid}/coupons", json={"code": "ab", "value": 10}).status_code == 400
    assert c.put(f"/api/apps/{aid}/coupons", json={"code": "TEN10", "kind": "percent", "value": 95}).status_code == 400
    assert c.put(f"/api/apps/{aid}/coupons", json={"code": "TEN10", "until": "31-12-2026", "value": 10}).status_code == 400
    v = c.put(f"/api/apps/{aid}/coupons", json={"code": "ten10", "kind": "percent", "value": 10, "once": True, "uses": 2}).json()
    assert v["coupons"][0]["code"] == "TEN10" and v["coupons"][0]["live"]
    c.put(f"/api/apps/{aid}/coupons", json={"code": "BIG500", "kind": "flat", "value": 50, "min": price * 100})
    c.put(f"/api/apps/{aid}/coupons", json={"code": "OLD2020", "kind": "flat", "value": 20, "until": "2020-01-01"})
    assert c.get(f"/api/app-content/{key}").json()["backend"]["coupons"] is True          # the cart shows the box
    cart = [{"id": p1["id"], "qty": 3}]
    sub = round(price * 3, 2)
    # the cart's check: nothing counted
    ok = c.post(f"{api}/coupon", json={"code": "ten10", "cart": cart}, headers=ha).json()
    assert ok["ok"] and ok["discount"] == pytest.approx(round(sub * 0.1, 2)) and ok["total"] == pytest.approx(sub - ok["discount"])
    assert "khatam" in c.post(f"{api}/coupon", json={"code": "OLD2020", "cart": cart}, headers=ha).json()["why"]
    assert c.post(f"{api}/coupon", json={"code": "BIG500", "cart": cart}, headers=ha).json()["ok"] is False
    assert c.post(f"{api}/coupon", json={"code": "NOPE99", "cart": cart}, headers=ha).json()["ok"] is False
    assert {x["code"]: x for x in c.get(f"/api/apps/{aid}/coupons").json()["coupons"]}["TEN10"]["used"] == 0
    # the order: the server applies it (a total the phone sends is ignored)
    o = c.post(f"{api}/c/orders", json={"name": "Asha", "phone": "9876543210", "coupon": "TEN10", "total": 1, "discount": 999,
                                        "cart": cart}, headers=ha).json()
    assert o["total"] == pytest.approx(round(sub - round(sub * 0.1, 2), 2))
    mine = c.get(f"{api}/c/orders", headers=ha).json()["rows"][0]
    assert mine["coupon"] == "TEN10" and mine["discount"] == pytest.approx(round(sub * 0.1, 2)) and mine["subtotal"] == pytest.approx(sub)
    # once per customer: her second order goes through at FULL price with the reason - never lost
    o2 = c.post(f"{api}/c/orders", json={"name": "Asha", "phone": "9876543210", "coupon": "TEN10", "cart": cart}, headers=ha)
    assert o2.status_code == 200 and o2.json()["total"] == pytest.approx(sub)
    row2 = next(x for x in c.get(f"{api}/c/orders", headers=ha).json()["rows"] if x["id"] == o2.json()["id"])
    assert "nahi laga" in row2["coupon_note"] and "discount" not in row2
    # Neha uses the last of the 2 uses; then it is used up for everyone
    c.post(f"{api}/c/orders", json={"name": "Neha", "phone": "9876543211", "coupon": "TEN10", "cart": cart}, headers=hn)
    assert c.get(f"/api/app-content/{key}").json()["backend"]["coupons"] is True              # BIG500 is still live
    assert {x["code"]: x for x in c.get(f"/api/apps/{aid}/coupons").json()["coupons"]}["TEN10"]["live"] is False
    # a cancelled order gives its use back (once)
    c.post(f"{api}/c/orders/{o['id']}", json={"status": "Cancelled"}, headers=hr)
    c.post(f"{api}/c/orders/{o['id']}", json={"status": "Cancelled"}, headers=hr)
    t = {x["code"]: x for x in c.get(f"/api/apps/{aid}/coupons").json()["coupons"]}["TEN10"]
    assert t["used"] == 1 and t["live"] is True
    # receipts: subtotal / coupon / total; a GST invoice spreads the discount over the lines (total = what she paid)
    o3 = c.post(f"{api}/c/orders", json={"name": "Asha", "phone": "9876543210", "coupon": "TEN10", "address": "Pune",
                                         "cart": [{"id": p1["id"], "qty": 3}]}, headers=ha).json()
    c.post(f"{api}/c/orders/{o3['id']}", json={"status": "Delivered"}, headers=hr)
    txt = _text(c.get(f"/api/apps/{aid}/data/orders/{o3['id']}/receipt").content)
    assert "Subtotal" in txt and "Coupon TEN10" in txt
    c.put(f"/api/apps/{aid}/gst", json={"gstin": GOOD, "rate": 18})
    r = BE.by_key(key)
    col = next(x for x in BE.schema(r)["collections"] if x["key"] == "orders")
    x = G.compute(r, col, BE._assign_info(BE.bid(r), [o3["id"]])[o3["id"]])
    assert x["totals"]["amount"] == pytest.approx(o3["total"]) and x["lines"][0]["amount"] == pytest.approx(o3["total"])
    assert "Includes coupon TEN10" in _text(c.get(f"/api/apps/{aid}/data/orders/{o3['id']}/receipt").content)
    # delete
    c.put(f"/api/apps/{aid}/coupons", json={"code": "OLD2020", "delete": True})
    assert "OLD2020" not in {x["code"] for x in c.get(f"/api/apps/{aid}/coupons").json()["coupons"]}


def test_tool_and_kits(droid_env):
    from app.agent.app_tools import _act
    from app.agent.tools import Ctx
    from tests.test_v128_appdesign import T
    aid, conv, key, be = _built(droid_env)
    out = _act(Ctx(tenant_id=T, conversation_id=conv), "coupon", {"app": aid, "coupon": {"code": "FEST20", "value": 20}})
    assert "FEST20" in out["say"]
    root = Path(__file__).resolve().parents[1]
    kt = root / "app/appmaker/android/template/app/src/main/java/hoola/kit"
    assert "fun CouponBox()" in (kt / "Pro.kt").read_text() and '"/coupon"' in (kt / "Pro.kt").read_text()
    b = (kt / "Backend.kt").read_text()
    assert "if (Db.couponsOn && AppState.cartCount > 0) CouponBox()" in b and 'data["coupon"] = AppState.coupon.value' in b
    sw = root / "app/appmaker/ios/template/Sources/Kit"
    assert "struct CouponBox: View" in (sw / "Pro.swift").read_text() and "CouponBox()" in (sw / "Accounts.swift").read_text()
    assert 'data["coupon"] = st.coupon' in (sw / "Backend.swift").read_text()
    assert "Coupon codes" in (root / "app/static/console/build.js").read_text()
