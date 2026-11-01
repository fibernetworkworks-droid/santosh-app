"""v0.356 WAPSI (App Sahayak Phase 20): an invoiced row cancelled -> a GST credit note (CN/<FY>/0001, its own series, given
once) for the full value, against the original invoice; her own credit note for a return; the customer's document becomes the
credit note; her original invoice stays downloadable; no invoice = no credit note; money never moves."""
from pathlib import Path

from fastapi.testclient import TestClient

from tests.test_v0314_app_backend import _built
from tests.test_v0352_kaam_baanto import _acct, _login
from tests.test_v0355_gst_bill import GOOD, _text
from tests.test_v132_android import droid_env  # noqa: F401  (fixture)


def test_credit_notes(droid_env):
    from app.appmaker import gst as G
    from app.db import Message, session
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
    c.put(f"/api/apps/{aid}/gst", json={"gstin": GOOD, "rate": 18})
    mk = lambda: c.post(f"{api}/c/orders", json={"name": "Asha", "phone": "9876543210", "address": "Pune",
                                                  "cart": [{"id": p1["id"], "qty": 2}]}, headers=ha).json()["id"]
    o1, o2, o3 = mk(), mk(), mk()
    fy = G.fy()
    for o in (o1, o2):
        c.post(f"{api}/c/orders/{o}", json={"status": "Delivered"}, headers=hr)
        c.get(f"/api/apps/{aid}/data/orders/{o}/receipt")                     # the invoice number is given here
    # no invoice yet -> no credit note (cancel before delivery = nothing to credit)
    c.post(f"{api}/c/orders/{o3}", json={"status": "Cancelled"}, headers=hr)
    assert c.post(f"/api/apps/{aid}/data/orders/{o3}/credit-note", json={"reason": "x"}).status_code == 409
    assert next(x for x in c.get(f"{api}/c/orders", headers=ha).json()["rows"] if x["id"] == o3)["receipt"] is False
    # an invoiced row cancelled -> its credit note by itself, against the invoice; her chat told (refund = hers)
    c.post(f"{api}/c/orders/{o1}", json={"status": "Cancelled"}, headers=hr)
    row = next(x for x in c.get(f"{api}/c/orders", headers=ha).json()["rows"] if x["id"] == o1)
    assert row["receipt"] is True and row["receipt_kind"] == "credit_note"
    url = c.post(f"{api}/c/orders/{o1}/receipt-link", headers=ha).json()["url"]
    got = c.get(url[url.index("/api/app-api/"):])
    assert "credit-note-CN-" in got.headers["content-disposition"]
    t = _text(got.content)
    for want in ("CREDIT NOTE", f"CN/{fy}/0001", f"Against tax invoice INV/{fy}/0001", "Order cancelled", GOOD, "CGST", "refund"):
        assert want in t, want
    with session() as s:
        assert any("credit note" in str(m.content).lower() and f"CN/{fy}/0001" in str(m.content)
                   for m in s.query(Message).filter(Message.conversation_id == conv).all())
    # cancelling again / her button again = the same number (given once)
    c.post(f"{api}/c/orders/{o1}", json={"status": "Cancelled"}, headers=hr)
    assert c.post(f"/api/apps/{aid}/data/orders/{o1}/credit-note", json={}).json()["credit_note"] == f"CN/{fy}/0001"
    # her original invoice is still there
    inv = c.get(f"/api/apps/{aid}/data/orders/{o1}/receipt?doc=invoice")
    assert "TAX INVOICE" in _text(inv.content) and "invoice-INV-" in inv.headers["content-disposition"]
    # her own credit note for a delivered row (a return): the next number, her reason
    v = c.post(f"/api/apps/{aid}/data/orders/{o2}/credit-note", json={"reason": "Goods returned\x00 damaged"}).json()
    assert v["credit_note"] == f"CN/{fy}/0002"
    assert "Goods returned" in _text(c.get(f"/api/apps/{aid}/data/orders/{o2}/receipt").content)


def test_tool_and_markers(droid_env):
    from app.agent.app_tools import _act
    from app.agent.tools import Ctx
    from tests.test_v128_appdesign import T
    aid, conv, key, be = _built(droid_env)
    import pytest
    from app.agent.tools import ToolError
    from app.site.webapp import AppError
    with pytest.raises((ToolError, AppError)):
        _act(Ctx(tenant_id=T, conversation_id=conv), "credit_note", {"app": aid, "coll": "orders", "row": "nope"})
    root = Path(__file__).resolve().parents[1]
    assert "Strings.creditNote" in (root / "app/appmaker/android/template/app/src/main/java/hoola/kit/Pro.kt").read_text()
    assert "Words.creditNote" in (root / "app/appmaker/ios/template/Sources/Kit/Pro.swift").read_text()
    js = (root / "app/static/console/build.js").read_text()
    assert "data-cn" in js and "/credit-note`" in js and "?doc=invoice" in js
