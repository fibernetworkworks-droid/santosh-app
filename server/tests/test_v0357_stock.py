"""v0.357 STOCK (App Sahayak Phase 21): stock per product - orders take it under one lock before the row exists, more than
is left is refused (product named), a retried write never takes it twice, a cancelled order puts it back once, a low level
warns her chat once, the app sees stock / sold_out fresh, untracked products stay unlimited."""
import threading
from pathlib import Path

from fastapi.testclient import TestClient

from tests.test_v0314_app_backend import _built
from tests.test_v0352_kaam_baanto import _acct, _login
from tests.test_v132_android import droid_env  # noqa: F401  (fixture)


def test_stock_rules(droid_env):
    from app.appmaker import stock as SK
    from app.db import Message, session
    from app.main import app
    c = TestClient(app)
    aid, conv, key, be = _built(droid_env)
    api = f"/api/app-api/{key}"
    prods = c.get(f"/api/app-content/{key}").json()["lists"]["products"]
    p1, p2 = prods[0], prods[1]
    _acct(c, api, "asha@example.com", "Asha")
    _acct(c, api, "ravi@example.com", "Ravi")
    mem = {m["email"]: m for m in c.get(f"/api/apps/{aid}/members").json()["members"]}
    c.post(f"/api/apps/{aid}/members/{mem['ravi@example.com']['id']}/role", json={"role": "staff"})
    ha, hr = _login(c, api, "asha@example.com", "Asha"), _login(c, api, "ravi@example.com", "Ravi")
    # settings: a bad number is refused; untracked = unlimited
    assert c.put(f"/api/apps/{aid}/stock", json={"items": {p1["id"]: {"qty": -1}}}).status_code == 400
    assert c.put(f"/api/apps/{aid}/stock", json={"items": {p1["id"]: {"qty": "2.5"}}}).status_code == 400
    v = c.put(f"/api/apps/{aid}/stock", json={"items": {p1["id"]: {"qty": 5, "low": 2}, "nope": {"qty": 3}}}).json()
    assert v["tracked"] == 1 and {p["id"]: p for p in v["products"]}[p1["id"]]["qty"] == 5
    shown = {p["id"]: p for p in c.get(f"/api/app-content/{key}").json()["lists"]["products"]}
    assert shown[p1["id"]]["stock"] == 5 and shown[p1["id"]]["sold_out"] is False and "stock" not in shown[p2["id"]]
    order = lambda q, cid=None: c.post(f"{api}/c/orders", json={"name": "Asha", "phone": "9876543210", **({"cid": cid} if cid else {}),
                                                                 "cart": [{"id": p1["id"], "qty": q}, {"id": p2["id"], "qty": 50}]}, headers=ha)
    # an order takes it; the same write again (retry) takes nothing more
    o1 = order(2, "stockWrite00001").json()
    assert order(2, "stockWrite00001").json()["id"] == o1["id"]
    assert {p["id"]: p for p in c.get(f"/api/apps/{aid}/stock").json()["products"]}[p1["id"]]["qty"] == 3
    # more than is left is refused, product named, nothing taken
    r = order(4)
    assert r.status_code == 409 and p1["name"] in r.json()["error"] and "3" in r.json()["error"]
    assert {p["id"]: p for p in c.get(f"/api/apps/{aid}/stock").json()["products"]}[p1["id"]]["qty"] == 3
    # falling to the warning level tells her once
    order(1)                                                 # 3 -> 2 (= low): warn
    order(1)                                                 # 2 -> 1: no second warning
    with session() as s:
        notes = [m.content for m in s.query(Message).filter(Message.conversation_id == conv).all() if "low stock" in str(m.content)]
    assert len(notes) == 1 and p1["name"] in notes[0]
    # a cancelled order puts its quantity back, once
    c.post(f"{api}/c/orders/{o1['id']}", json={"status": "Cancelled"}, headers=hr)
    c.post(f"{api}/c/orders/{o1['id']}", json={"status": "Cancelled"}, headers=hr)
    assert {p["id"]: p for p in c.get(f"/api/apps/{aid}/stock").json()["products"]}[p1["id"]]["qty"] == 3
    # two customers racing for the last pieces: never more sold than there was
    c.put(f"/api/apps/{aid}/stock", json={"items": {p1["id"]: {"qty": 3}}})
    codes = []

    def buy():
        codes.append(order(1).status_code)
    ts = [threading.Thread(target=buy) for _ in range(6)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    assert codes.count(200) == 3 and codes.count(409) == 3, codes
    left = {p["id"]: p for p in c.get(f"/api/app-content/{key}").json()["lists"]["products"]}[p1["id"]]
    assert left["stock"] == 0 and left["sold_out"] is True
    # unlimited again
    c.put(f"/api/apps/{aid}/stock", json={"items": {p1["id"]: {"qty": None}}})
    assert order(10).status_code == 200
    assert SK.STATS["refused"] >= 4 and SK.STATS["returned"] >= 1


def test_tool_and_kits(droid_env):
    from app.agent.app_tools import _act
    from app.agent.tools import Ctx
    from tests.test_v128_appdesign import T
    from fastapi.testclient import TestClient
    from app.main import app
    aid, conv, key, be = _built(droid_env)
    p1 = TestClient(app).get(f"/api/app-content/{key}").json()["lists"]["products"][0]
    out = _act(Ctx(tenant_id=T, conversation_id=conv), "stock", {"app": aid, "items": {p1["name"].upper(): {"qty": 7}}})
    assert out["tracked"] == 1 and "1 products" in out["say"]
    root = Path(__file__).resolve().parents[1]
    kt = root / "app/appmaker/android/template/app/src/main/java/hoola/kit"
    assert 'Pill(Strings.soldOut, "bad")' in (kt / "Kit.kt").read_text() and "fun maxQty(id: String)" in (kt / "Data.kt").read_text()
    sw = root / "app/appmaker/ios/template/Sources/Kit"
    assert "Words.soldOut" in (sw / "Kit.swift").read_text() and "func maxQty(_ id: String)" in (sw / "Data.swift").read_text()
    assert "Save stock" in (root / "app/static/console/build.js").read_text()
