"""v0.362 VARIANTS (App Sahayak Phase 26): sizes / weights with their own price - "pid::vid" behaves like a product: the
server prices it (never the phone), stock per size, coupons / GST work (the size keeps its product's HSN), the base product
of a sized item cannot be bought without a size, and the app content gives each product its `variants` for the size chips."""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tests.test_v0314_app_backend import _built
from tests.test_v0352_kaam_baanto import _acct, _login
from tests.test_v0355_gst_bill import GOOD, _text
from tests.test_v132_android import droid_env  # noqa: F401  (fixture)


def test_variants_end_to_end(droid_env):
    from app.appmaker import backend as BE
    from app.appmaker import gst as G
    from app.main import app
    c = TestClient(app)
    aid, conv, key, be = _built(droid_env)
    api = f"/api/app-api/{key}"
    p1 = c.get(f"/api/app-content/{key}").json()["lists"]["products"][0]
    _acct(c, api, "asha@example.com", "Asha")
    _acct(c, api, "ravi@example.com", "Ravi")
    mem = {m["email"]: m for m in c.get(f"/api/apps/{aid}/members").json()["members"]}
    c.post(f"/api/apps/{aid}/members/{mem['ravi@example.com']['id']}/role", json={"role": "staff"})
    ha, hr = _login(c, api, "asha@example.com", "Asha"), _login(c, api, "ravi@example.com", "Ravi")
    # setting sizes: bad prices refused; by product name too
    assert c.put(f"/api/apps/{aid}/variants", json={"product": p1["id"], "variants": [{"name": "1 kg", "price": "abc"}]}).status_code == 400
    assert c.put(f"/api/apps/{aid}/variants", json={"product": "no such thing", "variants": []}).status_code == 404
    v = c.put(f"/api/apps/{aid}/variants", json={"product": p1["name"].upper(), "variants": [{"name": "1 kg", "price": 60}, {"name": "5 kg", "price": "₹280"}]}).json()
    sizes = {p["id"]: p for p in v["products"]}[p1["id"]]["variants"]
    assert [x["id"] for x in sizes] == ["1-kg", "5-kg"] and sizes[1]["price"] == 280
    shown = {p["id"]: p for p in c.get(f"/api/app-content/{key}").json()["lists"]["products"]}[p1["id"]]
    assert [x["name"] for x in shown["variants"]] == ["1 kg", "5 kg"] and shown["price"] == 60
    # ordering a size: the server's price for that size; the base product alone is not buyable (no size = no price)
    o = c.post(f"{api}/c/orders", json={"name": "Asha", "phone": "9876543210", "address": "Pune",
                                        "cart": [{"id": f"{p1['id']}::5-kg", "qty": 2, "price": 1}]}, headers=ha).json()
    assert o["total"] == pytest.approx(560) and f"2 x {p1['name']} (5 kg)" in o["items"]
    assert c.post(f"{api}/c/orders", json={"name": "Asha", "phone": "9876543210", "cart": [{"id": p1["id"], "qty": 1}]}, headers=ha).status_code == 400
    assert c.post(f"{api}/c/orders", json={"name": "Asha", "phone": "9876543210", "cart": [{"id": f"{p1['id']}::9-kg", "qty": 1}]}, headers=ha).status_code == 400
    # stock per size
    c.put(f"/api/apps/{aid}/stock", json={"items": {f"{p1['id']}::5-kg": {"qty": 1}}})
    r = c.post(f"{api}/c/orders", json={"name": "Asha", "phone": "9876543210", "cart": [{"id": f"{p1['id']}::5-kg", "qty": 2}]}, headers=ha)
    assert r.status_code == 409 and "5 kg" in r.json()["error"]
    c.post(f"{api}/c/orders", json={"name": "Asha", "phone": "9876543210", "cart": [{"id": f"{p1['id']}::5-kg", "qty": 1}]}, headers=ha)
    shown = {p["id"]: p for p in c.get(f"/api/app-content/{key}").json()["lists"]["products"]}[p1["id"]]
    five = next(x for x in shown["variants"] if x["id"] == "5-kg")
    assert five["sold_out"] is True and "sold_out" not in shown                      # 1 kg still there
    # GST: the size keeps its product's HSN / rate
    c.put(f"/api/apps/{aid}/gst", json={"gstin": GOOD, "rate": 18, "items": {p1["id"]: {"hsn": "1101", "rate": 5}}})
    c.post(f"{api}/c/orders/{o['id']}", json={"status": "Delivered"}, headers=hr)
    rr = BE.by_key(key)
    col = next(x for x in BE.schema(rr)["collections"] if x["key"] == "orders")
    x = G.compute(rr, col, BE._assign_info(BE.bid(rr), [o["id"]])[o["id"]])
    assert x["lines"][0]["hsn"] == "1101" and x["lines"][0]["rate"] == 5 and x["totals"]["amount"] == pytest.approx(560)
    assert "(5 kg)" in _text(c.get(f"/api/apps/{aid}/data/orders/{o['id']}/receipt").content)
    # removing sizes = the product sells as before
    c.put(f"/api/apps/{aid}/variants", json={"product": p1["id"], "variants": []})
    assert "variants" not in {p["id"]: p for p in c.get(f"/api/app-content/{key}").json()["lists"]["products"]}[p1["id"]]
    assert c.post(f"{api}/c/orders", json={"name": "Asha", "phone": "9876543210", "cart": [{"id": p1["id"], "qty": 1}]}, headers=ha).status_code == 200


def test_tool_and_kits(droid_env):
    from app.agent.app_tools import _act
    from app.agent.tools import Ctx
    from app.main import app
    from tests.test_v128_appdesign import T
    aid, conv, key, be = _built(droid_env)
    p1 = TestClient(app).get(f"/api/app-content/{key}").json()["lists"]["products"][0]
    out = _act(Ctx(tenant_id=T, conversation_id=conv), "variants", {"app": aid, "product": p1["name"], "variants": [{"name": "S", "price": 499}]})
    assert "S Rs 499" in out["say"]
    root = Path(__file__).resolve().parents[1]
    kt = root / "app/appmaker/android/template/app/src/main/java/hoola/kit"
    assert "fun lineItem(name: String, id: String)" in (kt / "Data.kt").read_text() and "AppData.lineItem(list, id)" in (kt / "Data.kt").read_text()
    assert "fun SizeChips(p: Item)" in (kt / "Kit.kt").read_text() and "SizeChips(p); return" in (kt / "Kit.kt").read_text()
    sw = root / "app/appmaker/ios/template/Sources/Kit"
    assert "func lineItem(_ list: String, _ id: String)" in (sw / "Data.swift").read_text()
    assert "struct SizeChips: View" in (sw / "Kit.swift").read_text() and "SizeChips(p: r)" in (sw / "Kit.swift").read_text()
    assert "data-vsave" in (root / "app/static/console/build.js").read_text()
