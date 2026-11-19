"""v0.360 DELIVERY (App Sahayak Phase 24): her delivery charge (added by the server, free above an amount, after any coupon),
delivery area (PIN codes) and opening hours; an order outside the area or while closed is still taken with a note (never
lost); receipts / GST invoices show delivery as its own line (SAC 9968); the cart sees the rule in the app content."""
from datetime import datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tests.test_v0314_app_backend import _built
from tests.test_v0352_kaam_baanto import _acct, _login
from tests.test_v0355_gst_bill import GOOD, _text
from tests.test_v132_android import droid_env  # noqa: F401  (fixture)


def test_is_open_and_pin():
    from app.appmaker import delivery as DL
    g = {"hours": {"open": "09:00", "close": "21:00", "days": [0, 1, 2, 3, 4, 5]}}
    assert DL.is_open(g, datetime(2026, 11, 2, 10, 0)) and not DL.is_open(g, datetime(2026, 11, 2, 22, 0))
    assert not DL.is_open(g, datetime(2026, 11, 1, 10, 0))                                # Sunday off
    assert DL.is_open({"hours": {"open": "18:00", "close": "02:00"}}, datetime(2026, 11, 2, 1, 0))   # past midnight
    assert DL.pin_of({"address": "Flat 4, Kothrud, Pune 411038", "phone": "9876543210"}) == "411038"
    assert DL.pin_of({"pin": "411001"}) == "411001" and DL.pin_of({"phone": "9876543210"}) == ""


def test_delivery_end_to_end(droid_env, monkeypatch):
    from app.appmaker import backend as BE
    from app.appmaker import delivery as DL
    from app.appmaker import gst as G
    from app.db import Message, session
    from app.main import app
    c = TestClient(app)
    aid, conv, key, be = _built(droid_env)
    api = f"/api/app-api/{key}"
    p1 = c.get(f"/api/app-content/{key}").json()["lists"]["products"][0]
    price = float(p1["price"])
    _acct(c, api, "asha@example.com", "Asha")
    _acct(c, api, "ravi@example.com", "Ravi")
    mem = {m["email"]: m for m in c.get(f"/api/apps/{aid}/members").json()["members"]}
    c.post(f"/api/apps/{aid}/members/{mem['ravi@example.com']['id']}/role", json={"role": "staff"})
    ha, hr = _login(c, api, "asha@example.com", "Asha"), _login(c, api, "ravi@example.com", "Ravi")
    assert "delivery" not in c.get(f"/api/app-content/{key}").json()["backend"]
    # settings: bad values refused
    assert c.put(f"/api/apps/{aid}/delivery", json={"pins": "41100"}).status_code == 400
    assert c.put(f"/api/apps/{aid}/delivery", json={"hours": {"open": "9am", "close": "21:00"}}).status_code == 400
    v = c.put(f"/api/apps/{aid}/delivery", json={"fee": 30, "free_above": price * 3, "pins": "411038, 411001",
                                               "hours": {"open": "00:00", "close": "23:59"}}).json()
    assert v["on"] and v["pins"] == ["411001", "411038"]
    pub = c.get(f"/api/app-content/{key}").json()["backend"]["delivery"]
    assert pub["fee"] == 30 and pub["area"] is True and pub["free_above"] == pytest.approx(price * 3)
    mk = lambda q, addr, **kw: c.post(f"{api}/c/orders", json={"name": "Asha", "phone": "9876543210", "address": addr, "total": 1,
                                                                "delivery": 0, "cart": [{"id": p1["id"], "qty": q}], **kw}, headers=ha).json()
    # a small order pays the fee (the server's, not the phone's); a big one is free
    o1 = mk(1, "Kothrud, Pune 411038")
    assert o1["total"] == pytest.approx(price + 30)
    o2 = mk(3, "Kothrud, Pune 411038")
    assert o2["total"] == pytest.approx(price * 3)
    rows = {x["id"]: x for x in c.get(f"{api}/c/orders", headers=ha).json()["rows"]}
    assert rows[o1["id"]]["delivery"] == 30 and "delivery_note" not in rows[o1["id"]]
    # outside the area: taken, with a note, and her chat told - never refused
    o3 = c.post(f"{api}/c/orders", json={"name": "Asha", "phone": "9876543210", "address": "Andheri, Mumbai 400053",
                                         "cart": [{"id": p1["id"], "qty": 1}]}, headers=ha)
    assert o3.status_code == 200
    assert "400053" in {x["id"]: x for x in c.get(f"{api}/c/orders", headers=ha).json()["rows"]}[o3.json()["id"]]["delivery_note"]
    with session() as s:
        assert any("400053" in str(m.content) for m in s.query(Message).filter(Message.conversation_id == conv).all())
    # closed: taken, with a note
    monkeypatch.setattr(DL, "is_open", lambda g, at=None: False)
    o4 = mk(1, "Pune 411001")
    assert "closed" in {x["id"]: x for x in c.get(f"{api}/c/orders", headers=ha).json()["rows"]}[o4["id"]]["delivery_note"]
    monkeypatch.undo()
    # a coupon discounts the goods only; the fee rule looks at the goods after the coupon
    c.put(f"/api/apps/{aid}/coupons", json={"code": "HALF50", "kind": "percent", "value": 50})
    o5 = mk(3, "Pune 411001", coupon="HALF50")
    assert o5["total"] == pytest.approx(round(price * 3 * 0.5, 2) + 30)
    # receipts and GST invoices: delivery as its own line, the total = what she paid
    for o in (o1, o5):
        c.post(f"{api}/c/orders/{o['id']}", json={"status": "Delivered"}, headers=hr)
    assert "Delivery" in _text(c.get(f"/api/apps/{aid}/data/orders/{o1['id']}/receipt").content)
    c.put(f"/api/apps/{aid}/gst", json={"gstin": GOOD, "rate": 5})
    r = BE.by_key(key)
    col = next(x for x in BE.schema(r)["collections"] if x["key"] == "orders")
    x = G.compute(r, col, BE._assign_info(BE.bid(r), [o5["id"]])[o5["id"]])
    dl = [ln for ln in x["lines"] if ln["name"] == "Delivery charges"]
    assert dl and dl[0]["hsn"] == "9968" and dl[0]["amount"] == pytest.approx(30)
    assert x["totals"]["amount"] == pytest.approx(o5["total"])
    assert "Delivery charges" in _text(c.get(f"/api/apps/{aid}/data/orders/{o5['id']}/receipt").content)
    # off = no rules
    c.put(f"/api/apps/{aid}/delivery", json={"off": True})
    assert mk(1, "Mumbai 400053")["total"] == pytest.approx(price)


def test_tool_and_kits(droid_env):
    from app.agent.app_tools import _act
    from app.agent.tools import Ctx
    from tests.test_v128_appdesign import T
    aid, conv, key, be = _built(droid_env)
    out = _act(Ctx(tenant_id=T, conversation_id=conv), "delivery", {"app": aid, "delivery": {"fee": 20, "free_above": 300}})
    assert "Rs 20" in out["say"] and "300" in out["say"]
    root = Path(__file__).resolve().parents[1]
    kt = root / "app/appmaker/android/template/app/src/main/java/hoola/kit"
    assert "fun DeliveryLine()" in (kt / "Pro.kt").read_text() and "DeliveryLine()" in (kt / "Backend.kt").read_text()
    assert "deliveryFee(AppState.cartTotal" in (kt / "Backend.kt").read_text()
    sw = root / "app/appmaker/ios/template/Sources/Kit"
    assert "struct DeliveryLine: View" in (sw / "Pro.swift").read_text() and "DeliveryLine()" in (sw / "Accounts.swift").read_text()
    assert "Save delivery" in (root / "app/static/console/build.js").read_text()
