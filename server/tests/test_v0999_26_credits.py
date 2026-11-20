"""v0.999.26 HOOLA CREDITS (owner: "GO Dodo Payments, Paddle, RAZORPAY, CASHFREE"; the rules: "FREE TIER WORKS ON
NORMAL TIER ONLY. ALL OTHER WILL BE LOCKED --- ONCE CREDIT PURCHASED --- USER CAN CHOOSE ANY TIER -- BASED ON CHOOSEN
TIER USER CREDIT WILL DEDUCT. WE WILL KEEP AI EMPLOYEE SECTION DIFFERENT PACKAGE PER EMPLOYEE", "PAYMENT WILL COME FROM
ANY COUNTRY"). Every network call here is a fake; nothing reaches a real payment service."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time

import httpx
import pytest
from fastapi.testclient import TestClient

DODO_SECRET = "whsec_" + base64.b64encode(b"dodo-test-secret-key").decode()


@pytest.fixture()
def cr(env, monkeypatch, tmp_path):
    from app.config import get_settings
    for k, v in {"CREDITS_ON": "true", "MODEL_TIER_DIR": str(tmp_path / "mt"), "MODEL_TIERS": "true",
                 "GLM_API_KEY": "k", "CHAT_LLM": "glm", "GLM_BASE_URL": "https://openrouter.ai/api/v1",
                 "GLM_MODEL": "z-ai/glm-5.3-flash",
                 "HOOLA_RAZORPAY_KEY_ID": "rzp_test_abc", "HOOLA_RAZORPAY_KEY_SECRET": "rs",
                 "HOOLA_RAZORPAY_WEBHOOK_SECRET": "rwh", "HOOLA_CASHFREE_CLIENT_ID": "TESTcf",
                 "HOOLA_CASHFREE_CLIENT_SECRET": "cfs", "DODO_API_KEY": "dodo_test_x", "DODO_WEBHOOK_SECRET": DODO_SECRET,
                 "DODO_PRODUCTS": json.dumps({"plan_plus_world": "pdt_plus", "topup_t5k_regional": "pdt_t5k", "pack_starter_world": "pdt_st", "topup_t1k_world": "pdt_t1k"}),
                 "PADDLE_API_KEY": "pdl_sdbx_apikey_x", "PADDLE_WEBHOOK_SECRET": "pdl_ntfset_sec",
                 "PADDLE_PRICES": json.dumps({"plan_pro_world": "pri_pro", "pack_starter_world": "pri_st"}),
                 "PUBLIC_BASE_URL": "https://hoola.test"}.items():
        monkeypatch.setenv(k, v)
    get_settings.cache_clear()
    from app.credits import pay, wallet
    wallet._UNLOCK_CACHE.clear()
    seen: list[tuple[str, str, dict]] = []

    def handler(req: httpx.Request) -> httpx.Response:
        body = json.loads(req.content or b"{}")
        seen.append((req.method, str(req.url), body))
        u = str(req.url)
        if "razorpay.com/v1/orders" in u and req.method == "POST":
            return httpx.Response(200, json={"id": "order_rz1", "amount": body["amount"]})
        if "cashfree.com/pg/orders" in u and req.method == "POST":
            return httpx.Response(200, json={"order_id": body["order_id"], "payment_session_id": "sess_cf"})
        if u.endswith("/checkouts"):
            return httpx.Response(200, json={"session_id": "cks_1", "checkout_url": "https://test.checkout.dodopayments.com/session/cks_1"})
        if u.endswith("/transactions") and req.method == "POST":
            return httpx.Response(200, json={"data": {"id": "txn_1", "checkout": {"url": "https://pay.test/?_ptxn=txn_1"}}})
        if req.method == "GET" and ("/payments" in u):
            return httpx.Response(200, json={"items": []})
        return httpx.Response(404, json={})
    pay.set_transport(httpx.MockTransport(handler))
    yield seen
    pay.set_transport(None)
    get_settings.cache_clear()


def _client():
    from app.main import app
    return TestClient(app)


def _rz_sig(raw: bytes) -> str:
    return hmac.new(b"rwh", raw, hashlib.sha256).hexdigest()


def _dodo_headers(raw: bytes) -> dict[str, str]:
    wid, ts = "msg_1", str(int(time.time()))
    key = base64.b64decode(DODO_SECRET[6:])
    sig = base64.b64encode(hmac.new(key, f"{wid}.{ts}.".encode() + raw, hashlib.sha256).digest()).decode()
    return {"webhook-id": wid, "webhook-timestamp": ts, "webhook-signature": f"v1,{sig}"}


def _paddle_headers(raw: bytes, ts: int | None = None) -> dict[str, str]:
    ts = ts or int(time.time())
    h = hmac.new(b"pdl_ntfset_sec", f"{ts}:".encode() + raw, hashlib.sha256).hexdigest()
    return {"Paddle-Signature": f"ts={ts};h1={h}"}


# ------------------------------------------------------------------ the price list
def test_the_price_list_is_the_worked_out_one():
    from app.credits import plans as P
    assert P.PLANS["lite"]["price"] == {"in": 399, "world": 8, "regional": 4.5}
    assert P.PLANS["lite"]["credits"] == {"in": 2000, "world": 3900, "regional": 1900}
    assert P.PLANS["max"]["credits"]["world"] == 111000 and P.PACKS["ultra"]["price"]["in"] == 29999
    assert P.parse_sku("plan_pro_world") == ("plan", "pro", "world")
    with pytest.raises(ValueError):
        P.parse_sku("plan_gold_world")


def test_the_country_decides_the_price_level(cr):
    from app.credits import plans as P
    assert P.region_of("IN") == "in" and P.region_of("pk") == "regional" and P.region_of("US") == "world"
    assert P.region_of("") == "world"


# ------------------------------------------------------------------ spending + the free rule
def test_free_credits_go_first_and_a_turn_stops_when_both_are_gone(cr):
    from app.credits import wallet as W
    t = "t_free"
    v = W.view(t)
    assert v["free_left"] == 60 and not v["unlocked"] and v["can_run"]
    W.note(t, 0.045)                 # 45 credits
    W.flush()
    assert W.view(t)["free_left"] == 15
    W.note(t, 0.02)
    W.flush()
    v = W.view(t)
    assert v["free_left"] == 0 and not v["can_run"] and "free credits" in W.out_text()


def test_free_is_normal_only_and_any_purchase_opens_every_tier(cr):
    from app import tiers as T
    from app.credits import wallet as W
    t = "t_lock"
    assert T.locked(t)
    with pytest.raises(T.TierError, match="Buy credits"):
        T.set_tier(t, "medium")
    assert T.view(t)["locked"] is True
    W.grant(t, "topup", "t1k", "world", "co_x")
    assert not T.locked(t)
    T.set_tier(t, "ultra", confirm_ultra=True)
    assert T.chosen(t) == "ultra"
    W.note(t, 2.0)                   # 2,000 credits: the top-up is gone
    W.flush()
    W._UNLOCK_CACHE.clear()
    assert T.locked(t) and T.chosen(t) == ""      # back on Normal, her pick kept for when she buys again


def test_plan_credits_go_before_top_ups_and_low_credits_are_said_once(cr, monkeypatch):
    from app.credits import wallet as W
    said = []
    monkeypatch.setattr(W, "_tell", lambda tenant, text: said.append(text))
    t = "t_plan"
    W.grant(t, "plan", "lite", "in", "co_p")
    W.grant(t, "topup", "t1k", "in", "co_t")
    W.note(t, (60 + 1500) * 0.001)
    W.flush()
    v = W.view(t)
    assert v["plan_left"] == 500 and v["topup_left"] == 1000
    W.note(t, 400 * 0.001)
    W.flush()
    W.note(t, 50 * 0.001)
    W.flush()
    assert len([x for x in said if "running low" in x]) == 0          # 1,100 left of a 2,000 plan: not low yet
    W.note(t, 1000 * 0.001)
    W.flush()
    assert any("running low" in x for x in said)
    W.note(t, 500 * 0.001)
    W.flush()
    assert any("used up" in x for x in said)


def test_credits_off_or_an_exempt_tenant_changes_nothing(cr, monkeypatch):
    from app.config import get_settings
    from app.credits import wallet as W
    from app import tiers as T
    monkeypatch.setenv("CREDITS_EXEMPT", "owner1")
    get_settings.cache_clear()
    assert W.unlocked("owner1") and W.can_run("owner1") and not T.locked("owner1")
    monkeypatch.setenv("CREDITS_ON", "false")
    get_settings.cache_clear()
    W.note("t9", 5.0)
    assert W._PEND == {} and W.view("t9") == {"on": False} and not T.locked("t9")


def test_every_model_call_is_noted_and_the_turn_checks_credits():
    import inspect
    from app import usage
    from app.agent import santosh
    assert "_cw.note(tenant" in inspect.getsource(usage.record) and "_cw.flush()" in inspect.getsource(usage.flush)
    src = inspect.getsource(santosh._run_turn)
    assert "_cw.begin_turn()" in src and "_cw.can_run(tenant_id)" in src and '"source": "credits"' in src
    assert "_cw.tool_gate(" in inspect.getsource(santosh._run_tool)


# ------------------------------------------------------------------ India: Razorpay / Cashfree
def test_india_buys_through_razorpay_and_is_paid_only_by_the_signed_webhook(cr):
    c = _client()
    r = c.post("/api/credits/checkout", json={"sku": "plan_plus_in", "country": "IN"})
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["provider"] == "razorpay" and d["amount"] == 999 and d["checkout"]["order_id"] == "order_rz1"
    assert ("POST", "https://api.razorpay.com/v1/orders", {"amount": 99900, "currency": "INR", "receipt": d["order"],
            "notes": {"hoola_order": d["order"], "sku": "plan_plus_in"}}) in cr
    page = c.get(d["pay_url"].replace("https://hoola.test", ""))
    assert page.status_code == 200 and "checkout.razorpay.com" in page.text and "Pay now" in page.text
    assert c.get(f"/pay/credits/{d['order']}?k=wrong").status_code == 404
    body = json.dumps({"event": "payment.captured", "payload": {"payment": {"entity": {
        "id": "pay_9", "order_id": "order_rz1", "amount": 99900, "method": "upi"}}}}).encode()
    assert c.post("/api/credits/webhook/razorpay", content=body, headers={"x-razorpay-signature": "bad"}).status_code == 401
    ok = c.post("/api/credits/webhook/razorpay", content=body, headers={"x-razorpay-signature": _rz_sig(body)})
    assert ok.status_code == 200 and ok.json()["done"] == 1
    again = c.post("/api/credits/webhook/razorpay", content=body, headers={"x-razorpay-signature": _rz_sig(body)})
    assert again.json()["done"] == 0                     # the same payment never gives twice
    w = c.get("/api/credits?country=IN").json()["wallet"]
    assert w["plan"] == "plus" and w["plan_left"] == 5400 and w["unlocked"]


def test_cashfree_when_she_picks_it(cr):
    c = _client()
    d = c.post("/api/credits/checkout", json={"sku": "topup_t1k_in", "country": "IN", "provider": "cashfree"}).json()
    assert d["provider"] == "cashfree" and d["checkout"]["session"] == "sess_cf"
    assert "sdk.cashfree.com" in c.get(d["pay_url"].replace("https://hoola.test", "")).text


def test_a_price_for_another_country_is_refused(cr):
    r = _client().post("/api/credits/checkout", json={"sku": "plan_plus_in", "country": "US"})
    assert r.status_code == 400 and "another country" in r.text


# ------------------------------------------------------------------ the world: Dodo / Paddle
def test_dodo_checkout_and_its_standard_webhook(cr):
    c = _client()
    d = c.post("/api/credits/checkout", json={"sku": "plan_plus_world", "country": "US", "email": "a@b.co"}).json()
    assert d["provider"] == "dodo" and d["redirect"].startswith("https://test.checkout.dodopayments.com/")
    sent = [b for m, u, b in cr if u == "https://test.dodopayments.com/checkouts"][0]
    assert sent["product_cart"] == [{"product_id": "pdt_plus", "quantity": 1}]
    assert sent["metadata"]["hoola_order"] == d["order"] and sent["return_url"].startswith("https://hoola.test/pay/credits/")
    raw = json.dumps({"type": "payment.succeeded", "data": {"payment_id": "pay_d1", "subscription_id": "sub_d1",
                                                            "metadata": {"hoola_order": d["order"]}}}).encode()
    bad = dict(_dodo_headers(raw), **{"webhook-signature": "v1,AAAA"})
    assert c.post("/api/credits/webhook/dodo", content=raw, headers=bad).status_code == 401
    assert c.post("/api/credits/webhook/dodo", content=raw, headers=_dodo_headers(raw)).json()["done"] == 1
    renew = json.dumps({"type": "subscription.renewed", "data": {"payment_id": "pay_d2", "subscription_id": "sub_d1"}}).encode()
    assert c.post("/api/credits/webhook/dodo", content=renew, headers=_dodo_headers(renew)).json()["done"] == 1
    assert c.post("/api/credits/webhook/dodo", content=renew, headers=_dodo_headers(renew)).json()["done"] == 0
    w = c.get("/api/credits?country=US").json()["wallet"]
    assert w["plan"] == "plus" and w["plan_left"] == 10600     # Plus does not carry over: a fresh month


def test_regional_price_through_dodo(cr):
    d = _client().post("/api/credits/checkout", json={"sku": "topup_t5k_regional", "country": "PK"}).json()
    assert d["provider"] == "dodo" and d["amount"] == 11.99 and d["currency"] == "USD"


def test_paddle_checkout_webhook_renewal_and_refund(cr, monkeypatch):
    from app.config import get_settings
    monkeypatch.setenv("CREDITS_WORLD_GATEWAY", "paddle")
    get_settings.cache_clear()
    c = _client()
    d = c.post("/api/credits/checkout", json={"sku": "plan_pro_world", "country": "DE"}).json()
    assert d["provider"] == "paddle" and d["redirect"] == "https://pay.test/?_ptxn=txn_1"
    sent = [b for m, u, b in cr if u == "https://sandbox-api.paddle.com/transactions"][0]
    assert sent == {"items": [{"price_id": "pri_pro", "quantity": 1}], "custom_data": {"hoola_order": d["order"], "sku": "plan_pro_world"}}
    raw = json.dumps({"event_type": "transaction.completed", "data": {"id": "txn_1", "subscription_id": "sub_p1",
                                                                       "custom_data": {"hoola_order": d["order"]}}}).encode()
    assert c.post("/api/credits/webhook/paddle", content=raw, headers=_paddle_headers(raw, ts=int(time.time()) - 900)).status_code == 401
    assert c.post("/api/credits/webhook/paddle", content=raw, headers=_paddle_headers(raw)).json()["done"] == 1
    ren = json.dumps({"event_type": "transaction.completed", "data": {"id": "txn_2", "subscription_id": "sub_p1",
                                                                       "origin": "subscription_recurring"}}).encode()
    assert c.post("/api/credits/webhook/paddle", content=ren, headers=_paddle_headers(ren)).json()["done"] == 1
    w = c.get("/api/credits?country=DE").json()["wallet"]
    assert w["plan_left"] == 55200 * 2                             # Pro carries up to one month over
    ref = json.dumps({"event_type": "adjustment.updated", "data": {"action": "refund", "status": "approved",
                                                                    "transaction_id": "txn_2"}}).encode()
    assert c.post("/api/credits/webhook/paddle", content=ref, headers=_paddle_headers(ref)).json()["done"] == 1
    assert c.get("/api/credits?country=DE").json()["wallet"]["plan_left"] == 55200


# ------------------------------------------------------------------ AI employees: a package each
def test_an_employee_needs_its_package_and_counts_one_job_a_turn(cr):
    from app.credits import service as S, wallet as W
    from app.employee import hire as H
    t = "t_emp"
    with pytest.raises(H.HireError, match="package"):
        H.hire(t, "seo")
    oid = S.checkout(t, "pack_starter_world", employee="seo", base_url="https://hoola.test")["order"]
    assert S.settle(oid, "txn_x") and not S.settle(oid, "txn_x")
    H.hire(t, "seo")
    import contextvars

    def turn():
        W.begin_turn()
        a = W.tool_gate(t, "seo")
        b = W.tool_gate(t, "seo_dekho")
        W.note(t, 0.5)                       # after the employee's tool: the package's cost, not her credits
        return a, b
    assert contextvars.copy_context().run(turn) == ("", "")
    W.flush()
    pv = W.pack_view(t, "seo")
    assert pv["used"] == 1 and pv["left"] == 59 and pv["tier"] == "medium"
    assert W.view(t)["free_left"] == 60
    from app.db import session
    with session() as s:
        r = W._pack_row(s, t, "seo")
        r.used = r.jobs
    assert "used all 60 jobs" in contextvars.copy_context().run(lambda: (W.begin_turn(), W.tool_gate(t, "seo"))[1])


def test_an_employee_she_never_hired_keeps_working_on_her_credits(cr):
    from app.credits import wallet as W
    assert W.tool_gate("t_open", "leads_run") == "" and W.employee_of("leads_run") == "leads"
    assert W.employee_of("guru") == "tutor" and W.employee_of("web_search") == ""


def test_the_pay_page_shows_a_paid_order_as_paid(cr):
    from app.credits import service as S
    o = S.checkout("t_pg", "topup_t1k_world", base_url="https://hoola.test")
    S.settle(o["order"], "pay_1")
    page = _client().get(f"/pay/credits/{o['order']}?k={S.token(o['order'])}").text
    assert "Payment received" in page and "1,000 credits added" in page and "Pay now" not in page


# ------------------------------------------------------------------ the screens
def test_the_console_has_a_credits_page_and_locks_the_tiers():
    from pathlib import Path
    root = Path(__file__).resolve().parents[1] / "app/static/console"
    js, html, page = (root / "v2.js").read_text(), (root / "v2.html").read_text(), (root / "credits.js").read_text()
    assert 'id="v-credits"' in html and "/static/console/credits.js" in html
    assert "go('credits')" in js and "CRD?.open($('#credits'))" in js
    assert "const lock = !!TIERS.locked" in js and "'🔒 Buy credits'" in js
    assert "/api/credits/checkout" in page and "/api/credits/orders/" in page and "Free works on Normal" in page


def test_the_phone_has_credits_in_settings_and_locks_the_tiers():
    from pathlib import Path
    root = Path(__file__).resolve().parents[2] / "lib"
    page = (root / "ui/shell/hoola_credits.dart").read_text()
    assert "class HoolaCreditsPage" in page and "creditsCheckout(" in page and "LaunchMode.externalApplication" in page
    assert "fontSize:" not in page and "Color(0x" not in page
    assert "HoolaCreditsPage(app: app)" in (root / "ui/shell/hoola_settings.dart").read_text()
    q = (root / "ui/shell/hoola_quality.dart").read_text()
    assert "hoolaTierNow.value?['locked'] == true" in q and "'🔒 Buy credits'" in q
    api = (root / "api.dart").read_text()
    assert "'/api/credits/checkout'" in api and "/api/credits/orders/" in api


def test_version():
    from pathlib import Path
    from app.main import APP_VERSION
    assert APP_VERSION == "0.999.51"
    assert "version: 0.999.51+1049" in (Path(__file__).resolve().parents[2] / "pubspec.yaml").read_text()
