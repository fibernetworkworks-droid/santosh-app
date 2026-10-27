"""Santosh Shopping inside Santosh: search -> cart -> all-in quote -> confirm card -> UPI intent -> order tracking,
cancel and return; consent ledger; caps and expiry; tenant isolation; ONDC callbacks; the Commerce MCP server."""
import datetime as dt
import hashlib
import hmac
import json
import socket
import threading
import time

import pytest
from sqlalchemy import select


@pytest.fixture
def shop_env(env, monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "test-secret-key-0123456789-abcdefghij")
    monkeypatch.setenv("PUBLIC_BASE_URL", "https://santosh.example.in")
    monkeypatch.setenv("BAZAR_ENV", "dev")
    monkeypatch.setenv("BAZAR_WEBHOOK_SECRET", "whsec")
    from app.config import get_settings
    get_settings.cache_clear()
    from app.bazar import config as bzc, security, service
    from app.bazar.commerce.ondc import sandbox
    bzc.reset_settings()
    security._vault = None
    service.set_executors(None)
    sandbox.reset()
    from app.db import Conversation, session
    with session() as s:
        convs = []
        for t in ("default", "usr_other"):
            c = Conversation(tenant_id=t)
            s.add(c)
            s.flush()
            convs.append(c.id)
    for t in ("default", "usr_other"):
        service.set_user_settings(t, {"pincode": "444001", "address": "Plot 4, Akot Road, Akola"})
    yield {"svc": service, "conv": convs[0], "conv_other": convs[1]}
    bzc.reset_settings()
    security._vault = None
    service.set_executors(None)


def _events(conv, kind):
    from app.db import Event, session
    with session() as s:
        return [e.payload for e in s.scalars(select(Event).where(Event.conversation_id == conv, Event.kind == kind)
                                             .order_by(Event.id)).all()]


def _kirana(svc):
    shop = svc.create_shop("default", {"template_id": "kirana-store", "name": "Ramesh Kirana Stores", "owner_phone": "9800000003",
                                       "upi_id": "ramesh.kirana@okicici", "city": "Akola", "pincodes": ["444001"],
                                       "slots": ["Today 6-7 pm"], "min_order_rupees": 100})
    svc.add_items(shop["id"], [{"name": "Atta (wheat flour)", "price_rupees": 53, "unit": "kg", "aliases": ["atta", "gehu atta"]}],
                  None, shop["merchant_token"])
    return shop


def _db(fn):
    from app.bazar.db import session_factory
    with session_factory() as s:
        return fn(s)


def _shop(svc, conv, query, pick, qty, sources, tenant="default"):
    r = svc.run(tenant, conv, "santosh-shopping", "search_products", {"query": query, "sources": sources})
    n = next(i for i, x in enumerate(r["results"], 1) if pick.lower() in x["name"].lower())
    svc.run(tenant, conv, "santosh-shopping", "add_to_cart", {"pick": str(n), "quantity": qty})
    return svc.run(tenant, conv, "santosh-shopping", "checkout", {})


# ------------------------------------------------------------------ search
def test_search_across_sources_cheapest_first_with_labels(shop_env):
    svc, conv = shop_env["svc"], shop_env["conv"]
    _kirana(svc)
    r = svc.run("default", conv, "santosh-shopping", "search_products", {"query": "atta"})
    srcs = [x["source"] for x in r["results"]]
    assert srcs[:2] == ["bazar", "ondc"] and "1. Atta (wheat flour)" in r["message"]
    prices = [x["price_paise"] for x in r["results"]]
    assert prices == sorted(prices)
    ondc = next(x for x in r["results"] if x["source"] == "ondc")
    assert ondc["demo"] and ondc["mrp"] == "₹280" and ondc["country_of_origin"] == "IND" and ondc["seller"] == "Akola Fresh Mart"
    # Flipkart: search + link only, the purchase finishes in the Flipkart app
    fk = svc.run("default", conv, "santosh-shopping", "search_products", {"query": "kettle", "sources": ["flipkart"]})
    out = svc.run("default", conv, "santosh-shopping", "add_to_cart", {"pick": "1"})
    assert out["added"] is False and out["url"].startswith("https://dl.flipkart.com") and "referral fee" in out["message"]
    assert fk["results"][0]["buy_mode"] == "handoff"
    assert _events(conv, "bazar_open")[-1]["url"].startswith("https://dl.flipkart.com")


# ------------------------------------------------------------------ ONDC (sandbox network) through the card
def test_ondc_card_shows_breakup_and_disclosures_and_is_never_auto_approved(shop_env):
    svc, conv = shop_env["svc"], shop_env["conv"]
    svc.set_user_settings("default", {"cap_per_order_rupees": 5000, "cap_per_day_rupees": 20000})
    pay = _shop(svc, conv, "toor dal", "toor", 1, ["ondc"])
    assert pay["needs_approval"]
    card = _events(conv, "bazar_approval")[-1]
    assert card["title"] == "[DEMO] Order from Akola Fresh Mart" and card["demo"]
    assert card["amount_paise"] == 15800 + 3000 + 1000  # item + delivery (< ₹499) + packing, all-in
    assert [i["name"] for i in card["items"]] == ["Toor dal 1 kg", "Delivery charges", "Packing charges"]
    labels = {d["label"]: d["value"] for d in card["disclosures"]}
    assert {"Seller", "Delivery", "Deliver to", "Returns", "Country of origin", "Customer care", "Paid to", "Price check"} <= set(labels)
    assert labels["Delivery"] == "60 min" and labels["Country of origin"] == "India" and "7 days" in labels["Returns"]
    assert "444001" in labels["Deliver to"] and "Akola Fresh Mart" in labels["Seller"]
    res = svc.decide("default", pay["approval_id"], "approve")
    assert res["outcome"]["status"] == "demo_placed" and res["open"] is None  # sandbox: no money moves
    # even after approving this seller once and with caps set, the next order is a card again
    again = _shop(svc, conv, "toor dal", "toor", 1, ["ondc"])
    assert again["needs_approval"] and not again.get("auto_approved")
    from app.bazar.db import CommerceOrder, ConsentRecord
    rows = _db(lambda s: [(c.surface, c.amount_paise, c.quote_hash) for c in s.scalars(select(ConsentRecord)).all()])
    assert rows == [("santosh_card", 19800, rows[0][2])] and len(rows[0][2]) == 64
    order = _db(lambda s: s.scalars(select(CommerceOrder)).one())
    assert order.payment_status == "paid" and order.status == "accepted" and order.meta["demo"]


def test_ondc_status_cancel_return(shop_env):
    svc, conv = shop_env["svc"], shop_env["conv"]
    from app.bazar.connectors.base import ToolError
    p = _shop(svc, conv, "atta", "atta 5 kg", 2, ["ondc"])
    assert _events(conv, "bazar_approval")[-1]["amount"] == "₹540"  # free delivery above ₹499 + ₹10 packing
    svc.decide("default", p["approval_id"], "approve")
    st = svc.run("default", conv, "santosh-shopping", "order_status", {})
    assert st["status"] == "packed"
    c = svc.run("default", conv, "santosh-shopping", "cancel_order", {"reason": "galti se"})
    assert c["status"] == "cancelled"
    # toor dal: track to delivery, cancel refused after shipping, then return
    p = _shop(svc, conv, "toor dal", "toor", 1, ["ondc"])
    svc.decide("default", p["approval_id"], "approve")
    for _ in range(2):
        svc.run("default", conv, "santosh-shopping", "order_status", {})
    with pytest.raises(ToolError, match="already shipped"):
        svc.run("default", conv, "santosh-shopping", "cancel_order", {})
    for _ in range(3):
        st = svc.run("default", conv, "santosh-shopping", "order_status", {})
    assert st["status"] == "delivered"
    r = svc.run("default", conv, "santosh-shopping", "request_return", {"reason": "toota hua packet"})
    assert r["status"] == "return_requested"


# ------------------------------------------------------------------ Santosh Bazar shop: real UPI rails
def test_bazar_shop_upi_intent_consent_and_payment_webhook(shop_env):
    svc, conv = shop_env["svc"], shop_env["conv"]
    _kirana(svc)
    pay = _shop(svc, conv, "atta", "Atta (wheat", 5, ["bazar"])
    card = _events(conv, "bazar_approval")[-1]
    assert card["amount"] == "₹265" and card["payee"] == "Ramesh Kirana Stores" and not card["demo"] and card["needs_pin"]
    res = svc.decide("default", pay["approval_id"], "approve")
    assert res["open"]["kind"] == "upi" and res["open"]["url"].startswith("upi://pay?pa=ramesh.kirana%40okicici")
    assert "am=265.00" in res["open"]["url"]
    ref = res["outcome"]["txn_ref"]
    from app.bazar.db import CommerceOrder, ConsentRecord, ShopOrder
    consent = _db(lambda s: s.scalars(select(ConsentRecord)).one())
    assert consent.surface == "santosh_card" and consent.amount_paise == 26500 and "ramesh.kirana@okicici" in consent.payee
    assert _db(lambda s: s.scalars(select(CommerceOrder)).one().status) == "payment_pending"
    # the payment aggregator's signed webhook confirms the money -> the shop has the order
    from fastapi.testclient import TestClient
    from app import main
    raw = json.dumps({"txn_ref": ref, "status": "SUCCESS", "provider_ref": "UPI-77"}).encode()
    sig = hmac.new(b"whsec", raw, hashlib.sha256).hexdigest()
    r = TestClient(main.app).post("/bazar/webhooks/payment", content=raw, headers={"x-signature": sig})
    assert r.status_code == 200 and r.json()["status"] == "completed"
    o = _db(lambda s: s.scalars(select(CommerceOrder)).one())
    assert o.payment_status == "paid" and o.status == "placed"
    assert _db(lambda s: s.get(ShopOrder, o.external_id).payment_status) == "paid"


def test_failed_payment_and_cancel_before_payment(shop_env):
    svc, conv = shop_env["svc"], shop_env["conv"]
    _kirana(svc)
    from app.bazar.db import CommerceOrder, ShopOrder
    pay = _shop(svc, conv, "atta", "Atta (wheat", 3, ["bazar"])
    ref = svc.decide("default", pay["approval_id"], "approve")["outcome"]["txn_ref"]
    svc.payment_confirmed(ref, False)
    o = _db(lambda s: s.scalars(select(CommerceOrder)).one())
    assert o.status == "failed" and o.payment_status == "unpaid"
    assert _db(lambda s: s.get(ShopOrder, o.external_id).status) == "cancelled"
    pay = _shop(svc, conv, "atta", "Atta (wheat", 2, ["bazar"])
    svc.decide("default", pay["approval_id"], "approve")
    c = svc.run("default", conv, "santosh-shopping", "cancel_order", {})
    assert c["status"] == "cancelled" and "Nothing was paid" in c["message"]


# ------------------------------------------------------------------ rules: expiry, changed cart, cap
def test_expired_quote_is_refused_on_approve(shop_env):
    svc, conv = shop_env["svc"], shop_env["conv"]
    from app.bazar.db import CommerceOrder, CommerceQuote
    pay = _shop(svc, conv, "sugar", "sugar", 1, ["ondc"])

    def expire(s):
        for q in s.scalars(select(CommerceQuote)).all():
            q.expires_at = dt.datetime(2020, 1, 1)
        s.commit()
    _db(expire)
    res = svc.decide("default", pay["approval_id"], "approve")
    assert "expired" in res["outcome"]["error"]
    assert _db(lambda s: s.scalars(select(CommerceOrder)).all()) == []


def test_changed_cart_invalidates_quote(shop_env):
    svc, conv = shop_env["svc"], shop_env["conv"]
    pay = _shop(svc, conv, "rice", "basmati", 1, ["ondc"])
    from app.bazar.commerce.service import CommerceService
    from app.bazar.config import get_settings
    from app.bazar.db import CommerceCart, User

    def change(s):
        cart = s.scalars(select(CommerceCart)).one()
        CommerceService(s, get_settings()).update_cart(s.get(User, "default"), cart.id, cart.lines[0]["offer_id"], 3)
    _db(change)
    res = svc.decide("default", pay["approval_id"], "approve")
    assert "no longer valid" in res["outcome"]["error"]


def test_per_order_cap(shop_env, monkeypatch):
    svc, conv = shop_env["svc"], shop_env["conv"]
    monkeypatch.setenv("BAZAR_COMMERCE_MAX_ORDER_PAISE", "10000")
    from app.bazar import config as bzc
    bzc.reset_settings()
    from app.bazar.connectors.base import ToolError
    with pytest.raises(ToolError, match="per-order limit"):
        _shop(svc, conv, "atta", "atta 5 kg", 1, ["ondc"])


def test_one_seller_per_cart_and_handoff_store(shop_env):
    svc, conv = shop_env["svc"], shop_env["conv"]
    svc.run("default", conv, "santosh-shopping", "search_products", {"query": "kurta", "sources": ["shopify"]})
    svc.run("default", conv, "santosh-shopping", "add_to_cart", {"pick": "1"})
    out = svc.run("default", conv, "santosh-shopping", "checkout", {})
    assert not out.get("needs_approval") and out["checkout_url"].startswith("https://demo-kurta.example/checkouts/")
    assert out["total_paise"] == 129900 and _events(conv, "bazar_open")[-1]["url"] == out["checkout_url"]


# ------------------------------------------------------------------ isolation + routes
def _client():
    from fastapi.testclient import TestClient
    from app import main
    return TestClient(main.app)


def _signed_in(monkeypatch):
    monkeypatch.setenv("API_KEY", "")
    from app.config import get_settings
    get_settings.cache_clear()
    from app import accounts
    from app.db import User, session
    with session() as s:
        s.add_all([User(id="usr_a", email="a@gmail.com"), User(id="usr_b", email="b@gmail.com")])
    return ({"Authorization": f"Bearer {accounts.issue_session('usr_a')}"},
            {"Authorization": f"Bearer {accounts.issue_session('usr_b')}"})


def test_tenant_isolation_orders_tokens_cards(shop_env, monkeypatch):
    svc, conv, conv_b = shop_env["svc"], shop_env["conv"], shop_env["conv_other"]
    a, b = _signed_in(monkeypatch)
    from app import accounts
    ta, tb = accounts.tenant_of_user("usr_a"), accounts.tenant_of_user("usr_b")
    for t in (ta, tb):
        svc.set_user_settings(t, {"pincode": "444001"})
    pay = _shop(svc, conv, "toor dal", "toor", 1, ["ondc"], tenant=ta)
    from app.bazar.connectors.base import ToolError
    with pytest.raises(ToolError):
        svc.decide(tb, pay["approval_id"], "approve")
    svc.decide(ta, pay["approval_id"], "approve")
    c = _client()
    mine = c.get("/api/bazar/commerce/orders", headers=a).json()["orders"]
    assert len(mine) == 1 and mine[0]["seller"] == "Akola Fresh Mart"
    assert c.get("/api/bazar/commerce/orders", headers=b).json()["orders"] == []
    assert c.get(f"/api/bazar/commerce/orders/{mine[0]['order_id']}", headers=b).status_code == 404
    assert c.get(f"/api/bazar/commerce/orders/{mine[0]['order_id']}", headers=a).json()["status"] == "packed"
    with pytest.raises(ToolError, match="No open orders"):
        svc.run(tb, conv_b, "santosh-shopping", "cancel_order", {})
    tok = c.post("/api/bazar/commerce/mcp-tokens", json={"label": "Claude"}, headers=a).json()
    tid = c.get("/api/bazar/commerce/mcp-tokens", headers=a).json()["tokens"][0]["id"]
    assert c.get("/api/bazar/commerce/mcp-tokens", headers=b).json()["tokens"] == []
    assert c.delete(f"/api/bazar/commerce/mcp-tokens/{tid}", headers=b).status_code == 404
    assert tok["token"].startswith("snt_mcp_")


def test_mcp_token_routes_and_ondc_callbacks(shop_env):
    c = _client()
    tok = c.post("/api/bazar/commerce/mcp-tokens", json={"label": "Claude"}).json()
    assert tok["token"].startswith("snt_mcp_") and tok["mcp_url"] == "https://santosh.example.in/mcp/commerce"
    from app.bazar.db import McpToken
    row = _db(lambda s: s.scalars(select(McpToken)).one())
    assert row.token_hash == hashlib.sha256(tok["token"].encode()).hexdigest() and tok["token"] not in row.token_hash
    rows = c.get("/api/bazar/commerce/mcp-tokens").json()["tokens"]
    assert rows[0]["label"] == "Claude" and "token" not in rows[0]
    assert c.delete(f"/api/bazar/commerce/mcp-tokens/{rows[0]['id']}").json()["revoked"] == rows[0]["id"]
    # ONDC network callbacks: public, but only signed messages from registry-known senders are accepted
    from app.bazar.commerce.ondc import crypto, sandbox
    from app.bazar.config import get_settings
    body = json.dumps({"context": {"bap_id": get_settings().ondc_subscriber_id, "message_id": "m", "transaction_id": "t"}}).encode()
    stranger = crypto.generate_keys()
    bad = crypto.sign_body(body, sandbox.GATEWAY, f"{sandbox.GATEWAY}-k1", stranger.signing_private)
    r = c.post("/ondc/on_search", content=body, headers={"Authorization": bad})
    assert r.status_code == 401 and r.json()["message"]["ack"]["status"] == "NACK"
    assert c.post("/ondc/on_search", content=body).status_code == 401
    good = crypto.sign_body(body, sandbox.GATEWAY, f"{sandbox.GATEWAY}-k1", sandbox._KEYS[sandbox.GATEWAY].signing_private)
    ok = c.post("/ondc/on_search", content=body, headers={"Authorization": good})
    assert ok.status_code == 200 and ok.json()["message"]["ack"]["status"] == "ACK"
    assert c.post("/ondc/search", content=body).status_code == 400
    assert c.post("/ondc/on_subscribe", json={"subscriber_id": "someone.else", "challenge": "x"}).status_code == 400
    assert c.get("/ondc-site-verification.html").status_code == 404  # until the ONDC request_id is set


def test_signing_roundtrip_and_onboarding_crypto():
    from app.bazar.commerce.ondc import crypto
    k = crypto.generate_keys()
    body = b'{"context":{"action":"search"}}'
    h = crypto.sign_body(body, "santosh.example.in", "k1", k.signing_private)
    assert crypto.verify_body(h, body, k.signing_public)
    assert not crypto.verify_body(h, body + b" ", k.signing_public)
    me, ondc = crypto.generate_keys(), crypto.generate_keys()
    ch = crypto.encrypt_challenge("ondc-challenge-123", ondc.encryption_private, me.encryption_public)
    assert crypto.decrypt_challenge(ch, me.encryption_private, ondc.encryption_public) == "ondc-challenge-123"


# ------------------------------------------------------------------ Commerce MCP server at /mcp/commerce
def _free_port() -> int:
    with socket.socket() as sk:
        sk.bind(("127.0.0.1", 0))
        return sk.getsockname()[1]


@pytest.fixture
def mcp_url(shop_env):
    pytest.importorskip("mcp.server.mcpserver")
    import uvicorn
    from fastapi import FastAPI
    from app.bazar.api import commerce
    from app.bazar.commerce.mcp_server import issue_token
    from app.bazar.db import session_factory
    from app.bazar.service import ensure_user
    with session_factory() as s:
        ensure_user(s, "default")
        s.commit()
        token = issue_token(s, "default", "pytest")
    app = FastAPI()
    m = commerce.mount(app, lambda: None, lambda: "default")
    port = _free_port()
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error"))
    th = threading.Thread(target=server.run, daemon=True)
    th.start()
    for _ in range(200):
        if server.started:
            break
        time.sleep(0.05)
    yield f"http://127.0.0.1:{port}/mcp/commerce", token, m, shop_env
    server.should_exit = True
    th.join(timeout=5)


def test_mcp_server_end_to_end(mcp_url):
    from app.bazar.connectors.mcp_remote import McpHttpRemote
    url, token, _, env = mcp_url
    _kirana(env["svc"])
    remote = McpHttpRemote(url, token)
    names = {t["name"] for t in remote.list_tools()}
    assert {"search_products", "add_to_cart", "get_quote", "place_order", "order_status", "cancel_order", "request_return"} <= names
    found = remote.call_tool("search_products", {"query": "atta", "sources": ["bazar", "ondc"]})["data"]
    offer = found["results"][0]
    assert offer["source"] == "bazar" and offer["price"] == "₹53"
    cart = remote.call_tool("add_to_cart", {"offer_id": offer["offer_id"], "quantity": 4})["data"]
    quote = remote.call_tool("get_quote", {"cart_id": cart["cart_id"]})["data"]
    assert quote["needs_confirmation"] and quote["total"] == "₹212" and quote["disclosures"]["seller"] == "Ramesh Kirana Stores"
    first = remote.call_tool("place_order", {"quote_id": quote["quote_id"], "idempotency_key": "mcp-1"})["data"]
    assert first["placed"] is False and first["needs_user_confirmation"]  # never without the user's yes
    placed = remote.call_tool("place_order", {"quote_id": quote["quote_id"], "idempotency_key": "mcp-1", "user_confirmed": True})["data"]
    assert placed["placed"] and placed["pay"]["upi_link"].startswith("upi://pay?pa=ramesh.kirana%40okicici")
    again = remote.call_tool("place_order", {"quote_id": quote["quote_id"], "idempotency_key": "mcp-1", "user_confirmed": True})["data"]
    assert again["order_id"] == placed["order_id"]  # idempotent
    assert remote.call_tool("order_status", {"order_id": placed["order_id"]})["data"]["status"] == "payment_pending"
    from app.bazar.db import ConsentRecord
    assert _db(lambda s: s.scalars(select(ConsentRecord)).one().surface) == "mcp_user_confirmed"


def test_mcp_server_token_required_and_rate_limited(mcp_url):
    import httpx
    url, token, m, _ = mcp_url
    init = {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
        "protocolVersion": "2025-11-25", "capabilities": {}, "clientInfo": {"name": "t", "version": "1"}}}
    hdr = {"Accept": "application/json, text/event-stream"}
    assert httpx.post(url, json=init, headers={**hdr, "Authorization": "Bearer snt_mcp_wrong"}).status_code == 401
    assert httpx.post(url, json=init, headers=hdr).status_code == 401
    assert httpx.post(url, json=init, headers={**hdr, "Authorization": f"Bearer {token}"}).status_code == 200
    m.limited.per_minute = 2
    codes = [httpx.post(url, json=init, headers={**hdr, "Authorization": f"Bearer {token}"}).status_code for _ in range(3)]
    assert codes[-1] == 429


def test_mcp_mounted_in_main_app(shop_env):
    pytest.importorskip("mcp.server.mcpserver")
    from fastapi.testclient import TestClient
    from app import main
    init = {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
        "protocolVersion": "2025-11-25", "capabilities": {}, "clientInfo": {"name": "t", "version": "1"}}}
    hdr = {"Accept": "application/json, text/event-stream", "Host": "santosh.example.in"}
    with TestClient(main.app) as c:
        tok = c.post("/api/bazar/commerce/mcp-tokens", json={"label": "Claude"}).json()["token"]
        assert c.post("/mcp/commerce", json=init, headers=hdr).status_code == 401
        r = c.post("/mcp/commerce", json=init, headers={**hdr, "Authorization": f"Bearer {tok}"})
        assert r.status_code == 200 and "santosh-commerce" in r.text
    with TestClient(main.app) as c:  # restartable: a fresh MCP session manager per app start
        assert c.post("/mcp/commerce", json=init, headers={**hdr, "Authorization": f"Bearer {tok}"}).status_code == 200
