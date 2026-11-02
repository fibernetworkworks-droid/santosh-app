"""v0.419 PAISA (App Sahayak Pillar E): online payments through HER gateway, against a fake gateway that answers in the
documented shapes. Paid ONLY from the gateway (signed webhook or server-to-server read), never the phone; amount
mismatch held; refunds only by her tap with a fixed number (timeout = ambiguous, checked with the same number, never twice);
payment links; AutoPay plans with the customer's own consent + cancel; split payouts only by her approved rule, once;
keys sealed and never returned; signature checks of all three gateways."""
import base64
import hashlib
import hmac
import json
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from tests.test_v0407_live import _shop
from tests.test_v132_android import droid_env  # noqa: F401  (fixture)

ROOT = Path(__file__).resolve().parents[1] / "app" / "appmaker"
SECRET = "whsec_test_123"


class FakeRazorpay:
    def __init__(self):
        self.orders, self.captured, self.refunds, self.transfers, self.calls = {}, {}, {}, [], []
        self.timeout_refund = False
        self.n = 0

    def __call__(self, req: httpx.Request) -> httpx.Response:
        self.calls.append((req.method, req.url.path))
        auth = req.headers.get("authorization", "")
        if auth != "Basic " + base64.b64encode(b"rzp_test_abc:sekret").decode():
            return httpx.Response(401, json={"error": {"description": "Authentication failed"}})
        p, body = req.url.path, json.loads(req.content or b"{}")
        if p == "/v1/orders" and req.method == "GET":
            return httpx.Response(200, json={"items": []})
        if p == "/v1/orders" and req.method == "POST":
            self.n += 1
            oid = f"order_{self.n}"
            self.orders[oid] = body
            return httpx.Response(200, json={"id": oid, "amount": body["amount"], "status": "created"})
        if p.startswith("/v1/orders/") and p.endswith("/payments"):
            oid = p.split("/")[3]
            pay = self.captured.get(oid)
            return httpx.Response(200, json={"items": [pay] if pay else []})
        if p.endswith("/refund"):
            if self.timeout_refund:
                raise httpx.ReadTimeout("slow")
            rid = f"rfnd_{len(self.refunds) + 1}"
            self.refunds[body["receipt"]] = {"id": rid, "status": "processed", "receipt": body["receipt"], "amount": body["amount"]}
            return httpx.Response(200, json=self.refunds[body["receipt"]])
        if p.endswith("/refunds"):
            return httpx.Response(200, json={"items": list(self.refunds.values())})
        if p == "/v1/settlements":
            return httpx.Response(200, json={"items": [{"id": "setl_1", "amount": 50000, "fees": 1000, "tax": 180, "status": "processed",
                                                        "utr": "UTR1", "created_at": 1700000000}]})
        if p == "/v1/payment_links":
            return httpx.Response(200, json={"id": "plink_1", "short_url": "https://rzp.io/i/abc"})
        if p == "/v1/plans":
            return httpx.Response(200, json={"id": "plan_1"})
        if p == "/v1/subscriptions":
            return httpx.Response(200, json={"id": "sub_1", "status": "created"})
        if p.endswith("/cancel"):
            return httpx.Response(200, json={"id": "sub_1", "status": "cancelled"})
        if p.endswith("/transfers"):
            self.transfers.append(body)
            return httpx.Response(200, json={"items": [{"id": f"trf_{i}"} for i, _ in enumerate(body["transfers"])]})
        return httpx.Response(404, json={})


def _hook(c, api, event: dict, secret: str = SECRET):
    raw = json.dumps(event).encode()
    sig = hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()
    return c.post(f"{api}/pay/webhook", content=raw, headers={"X-Razorpay-Signature": sig, "Content-Type": "application/json"})


def _paid_event(oid: str, pid: str, amount: int) -> dict:
    return {"event": "payment.captured", "payload": {"payment": {"entity": {"id": pid, "order_id": oid, "amount": amount,
                                                                            "status": "captured", "method": "upi"}}}}


@pytest.fixture()
def rzp():
    from app.paygate import gw as GW
    f = FakeRazorpay()
    GW.set_transport(httpx.MockTransport(f))
    yield f
    GW.set_transport(None)


def _setup(droid_env, rzp):
    c, aid, api, hs, p1, ids = _shop(droid_env)
    bad = c.put(f"/api/apps/{aid}/pay/keys", json={"gateway": "razorpay", "keys": {"key_id": "rzp_test_abc", "key_secret": "wrong",
                                                                                    "webhook_secret": SECRET}})
    assert bad.status_code == 400 and c.get(f"/api/apps/{aid}/pay").json()["on"] is False      # wrong keys are never saved
    st = c.put(f"/api/apps/{aid}/pay/keys", json={"gateway": "razorpay", "keys": {"key_id": "rzp_test_abc", "key_secret": "sekret",
                                                                                   "webhook_secret": SECRET}}).json()
    assert st["on"] and st["gateway"] == "razorpay" and st["test"] and st["webhook_url"].endswith("/pay/webhook")
    assert "sekret" not in json.dumps(st) and SECRET not in json.dumps(st)
    return c, aid, api, hs, p1, ids


def _order(c, api, h, p1, qty=1):
    return c.post(f"{api}/c/orders", json={"name": "Asha", "phone": "9876500002", "cart": [{"id": p1["id"], "qty": qty}]}, headers=h).json()


def test_paid_only_from_the_gateway(droid_env, rzp):
    c, aid, api, hs, p1, ids = _setup(droid_env, rzp)
    o = _order(c, api, hs["Asha"], p1)
    assert c.get(f"{api}/pay/c/orders/{o['id']}", headers=hs["Asha"]).json() == {"online": True, "paid": False, "can_pay": True}
    assert c.post(f"{api}/pay/c/orders/{o['id']}/start", headers=hs["Neha"]).status_code == 404       # never someone else's
    st = c.post(f"{api}/pay/c/orders/{o['id']}/start", headers=hs["Asha"]).json()
    amount = int(round(float(o["total"]) * 100))
    assert st["amount"] == amount and st["path"].startswith(f"{api}/pay/p/")
    again = c.post(f"{api}/pay/c/orders/{o['id']}/start", headers=hs["Asha"]).json()
    assert again["payment"] == st["payment"] and len(rzp.orders) == 1                                 # same order, same payment
    assert list(rzp.orders.values())[0]["amount"] == amount                                            # the SERVER's total
    pg = c.get(st["path"])
    assert pg.status_code == 200 and "checkout.razorpay.com" in pg.headers["content-security-policy"]
    assert "checkout.razorpay.com/v1/checkout.js" in pg.text and "sekret" not in pg.text and SECRET not in pg.text
    assert c.get(st["path"].rsplit(".", 1)[0] + ".deadbeef").status_code == 404                       # a forged link
    tok = st["path"].rsplit("/", 1)[1]
    assert c.get(f"{api}/pay/s/{tok}").json()["status"] == "created"                                  # gateway says nothing yet
    # the phone cannot mark it paid: there is no such route, and the customer cannot write `paid`
    c.patch(f"{api}/c/orders/{o['id']}", json={"paid": "Verified"}, headers=hs["Asha"])
    assert c.get(f"{api}/pay/c/orders/{o['id']}", headers=hs["Asha"]).json()["paid"] is False
    # a webhook with a bad signature changes nothing
    assert _hook(c, api, _paid_event("order_1", "pay_X", amount), secret="guess").status_code == 401
    assert c.get(f"{api}/pay/c/orders/{o['id']}", headers=hs["Asha"]).json()["paid"] is False
    # the real webhook: paid, once
    assert _hook(c, api, _paid_event("order_1", "pay_1", amount)).json()["applied"] == 1
    _hook(c, api, _paid_event("order_1", "pay_1", amount))
    assert c.get(f"{api}/pay/c/orders/{o['id']}", headers=hs["Asha"]).json()["paid"] is True
    row = next(x for x in c.get(f"{api}/c/orders", headers=hs["Asha"]).json()["rows"] if x["id"] == o["id"])
    assert row["paid"] == "Verified"
    assert c.get(f"{api}/pay/s/{tok}").json()["status"] == "paid"
    pays = c.get(f"/api/apps/{aid}/pay").json()
    assert pays["totals"]["paid"] == amount and pays["totals"]["count"] == 1
    assert c.post(f"{api}/pay/c/orders/{o['id']}/start", headers=hs["Asha"]).status_code == 409        # never paid twice
    # a SECOND order: the gateway says a DIFFERENT amount -> held, not paid
    o2 = _order(c, api, hs["Asha"], p1, qty=2)
    c.post(f"{api}/pay/c/orders/{o2['id']}/start", headers=hs["Asha"])
    _hook(c, api, _paid_event("order_2", "pay_2", 100))
    assert c.get(f"{api}/pay/c/orders/{o2['id']}", headers=hs["Asha"]).json()["paid"] is False
    assert c.get(f"/api/apps/{aid}/pay").json()["totals"]["mismatch"] == 1
    # a THIRD order paid but the webhook never came: the pay page's status read (server -> gateway) finds it
    o3 = _order(c, api, hs["Asha"], p1)
    st3 = c.post(f"{api}/pay/c/orders/{o3['id']}/start", headers=hs["Asha"]).json()
    rzp.captured["order_3"] = {"id": "pay_3", "status": "captured", "amount": st3["amount"], "method": "card"}
    assert c.get(f"{api}/pay/s/{st3['path'].rsplit('/', 1)[1]}").json()["status"] == "paid"


def test_refunds_links_settlements(droid_env, rzp):
    c, aid, api, hs, p1, ids = _setup(droid_env, rzp)
    o = _order(c, api, hs["Asha"], p1, qty=3)
    st = c.post(f"{api}/pay/c/orders/{o['id']}/start", headers=hs["Asha"]).json()
    _hook(c, api, _paid_event("order_1", "pay_1", st["amount"]))
    pid = st["payment"]
    assert c.post(f"/api/apps/{aid}/pay/{pid}/refund", json={"amount": 1}).status_code == 403          # her tap only
    assert c.post(f"/api/apps/{aid}/pay/{pid}/refund", json={"amount": 999999, "her_tap": True}).status_code == 400
    got = c.post(f"/api/apps/{aid}/pay/{pid}/refund", json={"amount": 1, "why": "late", "her_tap": True}).json()
    assert got["status"] == "done" and got["amount"] == 100
    p = next(x for x in c.get(f"/api/apps/{aid}/pay").json()["payments"] if x["id"] == pid)
    assert p["refunded"] == 100 and p["refunds"][0]["status"] == "counted"
    # the gateway times out: ambiguous, NOT failed, NOT sent again
    rzp.timeout_refund = True
    amb = c.post(f"/api/apps/{aid}/pay/{pid}/refund", json={"amount": 2, "her_tap": True}).json()
    assert amb["status"] == "ambiguous"
    left = st["amount"] - 100 - 200
    assert c.post(f"/api/apps/{aid}/pay/{pid}/refund", json={"amount": (left + 1) / 100, "her_tap": True}).status_code == 400  # held
    rzp.timeout_refund = False
    num = next(f["number"] for f in next(x for x in c.get(f"/api/apps/{aid}/pay").json()["payments"] if x["id"] == pid)["refunds"]
               if f["status"] == "ambiguous")
    rzp.refunds[num] = {"id": "rfnd_late", "status": "processed", "receipt": num, "amount": 200}   # it HAD happened
    fid = amb["refund"]
    assert c.post(f"/api/apps/{aid}/pay/refunds/{fid}/check").json()["status"] == "done"
    ev = {"event": "refund.processed", "payload": {"refund": {"entity": {"id": "rfnd_late", "receipt": num, "payment_id": "pay_1"}}}}
    _hook(c, api, ev)
    _hook(c, api, ev)
    p = next(x for x in c.get(f"/api/apps/{aid}/pay").json()["payments"] if x["id"] == pid)
    assert p["refunded"] == 300                                                                         # counted once
    assert sum(1 for m, path in rzp.calls if path.endswith("/refund")) == 2                             # never a 3rd send
    # settlements (read-only) + a payment link (her tap) paid by webhook
    s = c.get(f"/api/apps/{aid}/pay/settlements").json()
    assert s["settlements"][0]["utr"] == "UTR1"
    assert c.post(f"/api/apps/{aid}/pay/link", json={"amount": 250, "purpose": "Udhaar"}).status_code == 403
    lk = c.post(f"/api/apps/{aid}/pay/link", json={"amount": 250, "purpose": "Udhaar", "phone": "9876500002", "her_tap": True}).json()
    assert lk["url"] == "https://rzp.io/i/abc" and lk["amount"] == 25000
    _hook(c, api, {"event": "payment_link.paid", "payload": {"payment_link": {"entity": {"id": "plink_1", "reference_id": lk["payment"]}},
                                                             "payment": {"entity": {"id": "pay_L", "amount": 25000}}}})
    assert next(x for x in c.get(f"/api/apps/{aid}/pay").json()["payments"] if x["id"] == lk["payment"])["status"] == "paid"


def test_autopay_and_split(droid_env, rzp):
    c, aid, api, hs, p1, ids = _setup(droid_env, rzp)
    assert c.post(f"/api/apps/{aid}/pay/plans", json={"name": "Doodh", "amount": 900, "period": "month", "count": 12}).status_code == 403
    assert c.post(f"/api/apps/{aid}/pay/plans", json={"name": "Doodh", "amount": 900, "period": "decade", "count": 12,
                                                     "her_tap": True}).status_code == 400
    st = c.post(f"/api/apps/{aid}/pay/plans", json={"name": "Doodh", "amount": 900, "period": "month", "count": 12, "her_tap": True}).json()
    key = st["plans"][0]["key"]
    pl = c.get(f"{api}/pay/plans").json()
    assert pl["plans"][0]["amount_rs"] == "Rs 900" and "gw_plan" not in json.dumps(pl)
    sb = c.post(f"{api}/pay/plans/{key}/subscribe", headers=hs["Asha"]).json()
    page = c.get(sb["path"]).text
    assert "Approve AutoPay" in page and "12 times" in page and "cancel it any time" in page            # her consent, plainly
    _hook(c, api, {"event": "subscription.activated", "payload": {"subscription": {"entity": {"id": "sub_1", "status": "active"}}}})
    _hook(c, api, {"event": "subscription.charged", "payload": {"subscription": {"entity": {"id": "sub_1"}},
                                                                 "payment": {"entity": {"id": "pay_s1", "amount": 90000}}}})
    mine = c.get(f"{api}/pay/subs", headers=hs["Asha"]).json()["subs"]
    assert mine[0]["status"] == "activated" and mine[0]["charges"] == 1
    assert c.post(f"{api}/pay/plans/{key}/subscribe", headers=hs["Asha"]).status_code == 409             # already running
    assert c.post(f"{api}/pay/subs/{mine[0]['id']}/cancel", headers=hs["Neha"]).status_code == 404       # not hers
    assert c.post(f"{api}/pay/subs/{mine[0]['id']}/cancel", headers=hs["Asha"]).json()["status"] == "cancelled"
    # split: only her approved rule, once per payment
    assert c.put(f"/api/apps/{aid}/pay/split", json={"vendors": [{"key": "v1", "name": "Kisan", "account": "acc_K1"}],
                                                     "rules": [{"vendor": "v1", "percent": 20}]}).status_code == 403
    assert c.put(f"/api/apps/{aid}/pay/split", json={"vendors": [{"key": "v1", "name": "Kisan", "account": "acc_K1"}],
                                                     "rules": [{"vendor": "v1", "percent": 120}], "her_tap": True}).status_code == 400
    sp = c.put(f"/api/apps/{aid}/pay/split", json={"vendors": [{"key": "v1", "name": "Kisan", "account": "acc_K1"}],
                                                   "rules": [{"vendor": "v1", "percent": 20}], "her_tap": True}).json()["split"]
    assert sp["hash"] and sp["approved_at"]
    o = _order(c, api, hs["Asha"], p1, qty=2)
    s2 = c.post(f"{api}/pay/c/orders/{o['id']}/start", headers=hs["Asha"]).json()
    _hook(c, api, _paid_event("order_1", "pay_9", s2["amount"]))
    _hook(c, api, _paid_event("order_1", "pay_9", s2["amount"]))
    assert len(rzp.transfers) == 1
    t = rzp.transfers[0]["transfers"][0]
    assert t["account"] == "acc_K1" and t["amount"] == int(s2["amount"] * 0.2)
    # forgetting the keys turns payments off; nothing returns them
    assert c.delete(f"/api/apps/{aid}/pay/keys").json()["on"] is False
    o4 = _order(c, api, hs["Asha"], p1)
    assert c.post(f"{api}/pay/c/orders/{o4['id']}/start", headers=hs["Asha"]).status_code == 409


def test_signatures_of_each_gateway():
    from app.paygate import gw as GW
    raw = b'{"type":"PAYMENT_SUCCESS_WEBHOOK","data":{"order":{"order_id":"pay_1"},"payment":{"cf_payment_id":7,"payment_status":"SUCCESS","payment_amount":12.5}}}'
    cf = GW.Cashfree({"client_id": "TEST1", "client_secret": "cfsec"})
    ts = "1700000000"
    sig = base64.b64encode(hmac.new(b"cfsec", ts.encode() + raw, hashlib.sha256).digest()).decode()
    assert cf.verify({"x-webhook-signature": sig, "x-webhook-timestamp": ts}, raw)
    assert not cf.verify({"x-webhook-signature": sig, "x-webhook-timestamp": "1700000001"}, raw)
    ev = cf.events(json.loads(raw))
    assert ev == [{"kind": "paid", "gw_order": "pay_1", "payment_id": "7", "amount": 1250, "method": ""}]
    pp = GW.PhonePe({"client_id": "c", "client_secret": "s", "webhook_user": "u", "webhook_password": "p"})
    assert pp.verify({"authorization": hashlib.sha256(b"u:p").hexdigest()}, b"{}")
    assert not pp.verify({"authorization": hashlib.sha256(b"u:x").hexdigest()}, b"{}")
    rz = GW.Razorpay({"key_id": "rzp_live_x", "key_secret": "k", "webhook_secret": ""})
    assert not rz.verify({"x-razorpay-signature": "abc"}, b"{}")                 # no secret = nothing verifies
    seen = []

    def h(req):
        seen.append(json.loads(req.content))
        return httpx.Response(200, json={"order_id": "pay_2", "payment_session_id": "sess"})
    GW.set_transport(httpx.MockTransport(h))
    try:
        got = cf.create_order(50000, "pay_2", {"id": "m1", "name": "A"}, {"app": "x"}, "https://x/r",
                              split=[{"account": "V1", "amount": 10000}])
    finally:
        GW.set_transport(None)
    assert got["checkout"]["session"] == "sess" and seen[0]["order_splits"] == [{"vendor_id": "V1", "amount": 100.0}]
    assert seen[0]["order_amount"] == 500.0


def test_kits_carry_the_pay_flow():
    kt = (ROOT / "android/template/app/src/main/java/hoola/kit/Pay.kt").read_text()
    sw = (ROOT / "ios/template/Sources/Kit/Pay.swift").read_text()
    for src in (kt, sw):
        for s in ("/pay/c/", "/start", "/pay/plans", "/subscribe", "/pay/subs", "/cancel"):
            assert s in src, s
    assert "PayButton(coll, r)" in (ROOT / "android/template/app/src/main/java/hoola/kit/Accounts.kt").read_text()
    assert "PayButton(coll: coll, r: r)" in (ROOT / "ios/template/Sources/Kit/Accounts.swift").read_text()
