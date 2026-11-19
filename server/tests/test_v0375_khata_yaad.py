"""v0.375 KHATA YAAD (App Sahayak Phase 39): payment reminders for customers who owe - the ready text + a wa.me link for her
own WhatsApp, or her approved UTILITY template through her business number ONLY by her tap; never to someone who wrote STOP,
never with an unapproved / marketing template, at most once per customer every 3 days."""
from urllib.parse import unquote

from fastapi.testclient import TestClient

from tests.test_v0314_app_backend import _built
from tests.test_v0352_kaam_baanto import _acct, _login
from tests.test_v128_appdesign import T
from tests.test_v132_android import droid_env  # noqa: F401  (fixture)


class FakeWA:
    def __init__(self):
        self.sent = []

    async def send_template(self, to, name, language, params):
        self.sent.append((to, name, language, params))
        return "wamid.TEST"


def test_reminders(droid_env):
    from app.db import Template, session
    from app.employee.models import BizContact
    from app.main import app
    from app.whatsapp import client as WC
    c = TestClient(app)
    aid, conv, key, be = _built(droid_env)
    api = f"/api/app-api/{key}"
    p1 = c.get(f"/api/app-content/{key}").json()["lists"]["products"][0]
    _acct(c, api, "asha@example.com", "Asha")
    _acct(c, api, "neha@example.com", "Neha")
    _acct(c, api, "ravi@example.com", "Ravi")
    mem = {m["email"]: m for m in c.get(f"/api/apps/{aid}/members").json()["members"]}
    c.post(f"/api/apps/{aid}/members/{mem['ravi@example.com']['id']}/role", json={"role": "staff"})
    ha, hn, hr = (_login(c, api, e, n) for e, n in (("asha@example.com", "Asha"), ("neha@example.com", "Neha"), ("ravi@example.com", "Ravi")))
    oa = c.post(f"{api}/c/orders", json={"name": "Asha", "phone": "9876543210", "cart": [{"id": p1["id"], "qty": 2}]}, headers=ha).json()
    on = c.post(f"{api}/c/orders", json={"name": "Neha", "phone": "9123456789", "cart": [{"id": p1["id"], "qty": 1}]}, headers=hn).json()
    for o in (oa, on):
        c.post(f"{api}/c/orders/{o['id']}", json={"_credit": True}, headers=hr)
    v = c.get(f"/api/apps/{aid}/khata-yaad").json()
    rows = {x["name"]: x for x in v["customers"]}
    assert set(rows) == {"Asha", "Neha"}
    a = rows["Asha"]
    assert a["phone"] == "9876543210" and a["link"].startswith("https://wa.me/919876543210?text=")
    assert "Asha" in unquote(a["link"]) and f"{oa['total']:,.0f}" in a["text"]
    wa = FakeWA()
    WC.set_whatsapp(wa)
    try:
        url = f"/api/apps/{aid}/khata-yaad/{mem['asha@example.com']['id']}"
        assert c.post(url, json={"template": "udhaar_yaad"}).status_code == 403                       # not her tap
        assert c.post(url, json={"template": "udhaar_yaad", "her_tap": True}).status_code == 409      # no approved template
        with session() as s:
            s.add(Template(tenant_id=T, name="promo_offer", language="hi", category="MARKETING", body="x", status="APPROVED"))
            s.add(Template(tenant_id=T, name="udhaar_yaad", language="hi", category="UTILITY", body="Namaste {{1}}", status="APPROVED"))
        assert c.post(url, json={"template": "promo_offer", "her_tap": True}).status_code == 409      # marketing never
        r = c.post(url, json={"template": "udhaar_yaad", "her_tap": True})
        assert r.status_code == 200 and wa.sent[-1][0] == "919876543210" and wa.sent[-1][3][0] == "Asha"
        assert c.post(url, json={"template": "udhaar_yaad", "her_tap": True}).status_code == 409      # once per 3 days
        assert {x["name"]: x for x in c.get(f"/api/apps/{aid}/khata-yaad").json()["customers"]}["Asha"]["recent"] is True
        # Neha wrote STOP to the business number
        with session() as s:
            s.add(BizContact(tenant_id=T, wa_id="919123456789", opted_out=True))
        r = c.post(f"/api/apps/{aid}/khata-yaad/{mem['neha@example.com']['id']}", json={"template": "udhaar_yaad", "her_tap": True})
        assert r.status_code == 409 and "STOP" in r.json()["detail"] and len(wa.sent) == 1
    finally:
        WC.set_whatsapp(None)
    assert "Credit reminders" in (__import__("pathlib").Path(__file__).resolve().parents[1] / "app/static/console/build.js").read_text()
