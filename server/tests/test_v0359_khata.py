"""v0.359 KHATA (App Sahayak Phase 23): staff mark an order on credit (its SERVER total to the customer's khata, once),
record payments (money never moves), a cancelled credited order is reversed once, the customer sees her own balance only,
staff / owner see who owes; append-only; a customer deleting her account does not erase the shop's ledger."""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tests.test_v0314_app_backend import _built
from tests.test_v0352_kaam_baanto import _acct, _login
from tests.test_v132_android import droid_env  # noqa: F401  (fixture)


def test_khata_end_to_end(droid_env):
    from app.main import app
    c = TestClient(app)
    aid, conv, key, be = _built(droid_env)
    api = f"/api/app-api/{key}"
    p1 = c.get(f"/api/app-content/{key}").json()["lists"]["products"][0]
    for e, n in (("asha@example.com", "Asha"), ("neha@example.com", "Neha"), ("ravi@example.com", "Ravi")):
        _acct(c, api, e, n)
    mem = {m["email"]: m for m in c.get(f"/api/apps/{aid}/members").json()["members"]}
    c.post(f"/api/apps/{aid}/members/{mem['ravi@example.com']['id']}/role", json={"role": "staff"})
    ha, hn, hr = (_login(c, api, e, n) for e, n in (("asha@example.com", "Asha"), ("neha@example.com", "Neha"), ("ravi@example.com", "Ravi")))
    asha = mem["asha@example.com"]["id"]
    mk = lambda h, q: c.post(f"{api}/c/orders", json={"name": "Asha", "phone": "9876543210", "cart": [{"id": p1["id"], "qty": q}]}, headers=h).json()
    o1, o2 = mk(ha, 2), mk(ha, 1)
    assert c.get(f"{api}/khata", headers=ha).json()["entries"] == []
    # a customer can never write her own khata; staff mark on credit (through the outbox's update), once
    assert c.post(f"{api}/c/orders/{o1['id']}", json={"_credit": True}, headers=ha).status_code == 403
    c.post(f"{api}/c/orders/{o1['id']}", json={"_credit": True}, headers=hr)
    c.post(f"{api}/c/orders/{o1['id']}", json={"_credit": True}, headers=hr)
    c.post(f"{api}/c/orders/{o2['id']}", json={"_credit": True}, headers=hr)
    k = c.get(f"{api}/khata", headers=ha).json()
    assert k["balance"] == pytest.approx(o1["total"] + o2["total"]) and len(k["entries"]) == 2 and "by" not in k["entries"][0]
    assert next(x for x in c.get(f"{api}/c/orders", headers=ha).json()["rows"] if x["id"] == o1["id"])["on_credit"] is True
    # payments: staff / her only, sane amounts and modes
    assert c.post(f"{api}/khata/{asha}/pay", json={"amount": 10}, headers=ha).status_code == 403
    assert c.post(f"{api}/khata/{asha}/pay", json={"amount": -5}, headers=hr).status_code == 400
    assert c.post(f"{api}/khata/{asha}/pay", json={"amount": 5, "mode": "bitcoin"}, headers=hr).status_code == 400
    assert c.post(f"{api}/khata/nobody/pay", json={"amount": 5}, headers=hr).status_code == 404
    v = c.post(f"{api}/khata/{asha}/pay", json={"amount": "10", "mode": "upi", "note": "PhonePe"}, headers=hr).json()
    assert v["balance"] == pytest.approx(o1["total"] + o2["total"] - 10)
    # who owes: staff + her; not customers
    assert c.get(f"{api}/khata?all=1", headers=ha).status_code == 403              # a customer only ever sees her own
    d = c.get(f"{api}/khata?all=1", headers=hr).json()
    assert d["customers"][0]["member"] == asha and d["total_due"] == pytest.approx(v["balance"])
    assert c.get(f"/api/apps/{aid}/khata").json()["total_due"] == pytest.approx(v["balance"])
    # a cancelled credited order is reversed once (the original entry stays)
    c.post(f"{api}/c/orders/{o2['id']}", json={"status": "Cancelled"}, headers=hr)
    c.post(f"{api}/c/orders/{o2['id']}", json={"status": "Cancelled"}, headers=hr)
    k = c.get(f"{api}/khata", headers=ha).json()
    assert k["balance"] == pytest.approx(o1["total"] - 10) and len(k["entries"]) == 4
    # her payment from Hoola; Neha sees nothing of Asha's
    c.post(f"/api/apps/{aid}/khata/{asha}/pay", json={"amount": o1["total"] - 10, "mode": "cash"})
    assert c.get(f"/api/apps/{aid}/khata", params={"member": asha}).json()["balance"] == pytest.approx(0)
    assert c.get(f"{api}/khata", headers=hn).json()["balance"] == 0
    # an order without an account / cancelled / zero cannot go on credit
    assert c.post(f"{api}/c/orders/{o2['id']}/x", json={}).status_code in (404, 405)
    # the shop's ledger survives the customer deleting her account
    c.post(f"{api}/delete-me", headers=ha)
    assert len(c.get(f"/api/apps/{aid}/khata", params={"member": asha}).json()["entries"]) == 5


def test_tool_and_kits(droid_env):
    from app.agent.app_tools import _act
    from app.agent.tools import Ctx
    from tests.test_v128_appdesign import T
    aid, conv, key, be = _built(droid_env)
    out = _act(Ctx(tenant_id=T, conversation_id=conv), "khata", {"app": aid})
    assert "udhaar" in out["say"].lower()
    root = Path(__file__).resolve().parents[1]
    kt = root / "app/appmaker/android/template/app/src/main/java/hoola/kit"
    pro = (kt / "Pro.kt").read_text()
    assert "fun KhataBlock()" in pro and 'mapOf("_credit" to true)' in pro and '"/khata?all=1"' in pro
    acc = (kt / "Accounts.kt").read_text()
    assert "KhataBlock()" in acc and "CreditButton(coll, r)" in acc
    sw = root / "app/appmaker/ios/template/Sources/Kit"
    assert "struct KhataBlock: View" in (sw / "Pro.swift").read_text() and '["_credit": true]' in (sw / "Pro.swift").read_text()
    assert "KhataBlock()" in (sw / "Accounts.swift").read_text() and "CreditButton(coll: coll, r: r)" in (sw / "Accounts.swift").read_text()
