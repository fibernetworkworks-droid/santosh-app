"""Santosh Bazar wired into Santosh core: packs, approvals, payments, merchants, linking, isolation."""
import json

import httpx
import pytest
from sqlalchemy import select


@pytest.fixture
def bz(env, monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "test-secret-key-0123456789-abcdefghij")
    monkeypatch.setenv("PUBLIC_BASE_URL", "https://santosh.example.in")
    monkeypatch.setenv("BAZAR_ENV", "dev")
    from app.config import get_settings
    get_settings.cache_clear()
    from app.bazar import config as bzc, security
    bzc.reset_settings()
    security._vault = None
    from app.bazar import service
    service.set_executors(None)
    from app.db import Conversation, session
    with session() as s:
        c = Conversation(tenant_id="default")
        s.add(c)
        s.flush()
        conv = c.id
    yield {"svc": service, "conv": conv}
    bzc.reset_settings()
    security._vault = None
    service.set_executors(None)


def _events(conv, kind):
    from app.db import Event, session
    with session() as s:
        return [e.payload for e in s.scalars(select(Event).where(Event.conversation_id == conv, Event.kind == kind)
                                             .order_by(Event.id)).all()]


def _notices(conv):
    from app.db import Message, session
    with session() as s:
        return [m.display for m in s.scalars(select(Message).where(Message.conversation_id == conv)).all()]


def _kirana(svc, tenant="default"):
    shop = svc.create_shop(tenant, {"template_id": "kirana-store", "name": "Ramesh Kirana Stores", "owner_phone": "9800000003",
                                    "upi_id": "ramesh.kirana@okicici", "city": "Akola", "aliases": ["ramesh bhau", "ramesh"],
                                    "slots": ["Today 6-7 pm"], "min_order_rupees": 100})
    svc.add_items(shop["id"], [
        {"name": "Atta (wheat flour)", "price_rupees": 53, "unit": "kg", "aliases": ["atta", "gehu atta"]},
        {"name": "Sunflower oil", "price_rupees": 145, "unit": "l", "aliases": ["tel", "oil"]},
    ], None, shop["merchant_token"])
    return shop


def test_all_159_packs_have_a_status(bz):
    cat = bz["svc"].catalog("default")
    assert cat["total"] == 694   # 159 MVP + 515 P1 + 6 devices + shopping + Mera PC + Santosh Browser + PC operator + Santosh Email + Santosh Calendar + Santosh Sheets + Drive + Forms + Slides + Photos + Notebook + YouTube + App Jaanch
    st = cat["by_status"]
    assert st["demo"] == 98 + 44 and st["core"] == 7 + 3 and st["no_shop_yet"] == 20 + 122 and st["needs_link"] == 4
    assert st["not_configured"] == 4  # Zepto + District endpoints blank, browser worker not set, App Jaanch (REA) not installed
    assert st["ready"] == 377  # (+ Santosh Notebook, always ready) (P1 translator, email summary, recipe -> core tools) UPI, rides, native helpers + P1 skills, readers, handoffs, speaker, shopping
    assert st["no_device"] == 5  # TV, AC, SmartThings, LG ThinQ, Home Connect until added/linked in Santosh app > Ghar


def test_find_gives_tools(bz):
    r = bz["svc"].find("default", "bijli bill msedcl bharna hai")
    top = r["packs"][0]
    assert top["pack_id"] == "msedcl-mahavitaran" and top["status"] == "demo"
    assert {t["tool"] for t in top["tools"]} == {"fetch_bill", "pay_bill"}
    r = bz["svc"].find("default", "kal subah reminder")
    assert any(p["status"] == "core" and "create_reminder" in p["use_core_tools"] for p in r["packs"])
    assert bz["svc"].find("default", "")["total_packs"] == 694   # 159 MVP + 515 P1 + 6 devices + shopping + Mera PC + Santosh Browser + PC operator + Santosh Email + Santosh Calendar + Santosh Sheets + Drive + Forms + Slides + Photos + Notebook + YouTube + App Jaanch


def test_demo_bill_flow_never_sends_money_to_placeholder(bz):
    svc, conv = bz["svc"], bz["conv"]
    from app.bazar.connectors.base import ToolError
    with pytest.raises(ToolError, match="consumer number"):
        svc.run("default", conv, "msedcl-mahavitaran", "fetch_bill", {})
    bill = svc.run("default", conv, "msedcl-mahavitaran", "fetch_bill", {"consumer_number": "330012345678", "billing_unit": "4630"})
    assert bill["demo"] is True and bill["amount_paise"] > 0
    # the model asks for 1 rupee; the card shows the real fetched amount
    pay = svc.run("default", conv, "msedcl-mahavitaran", "pay_bill", {"bill_ref": bill["bill_ref"], "amount": 1})
    assert pay["needs_approval"] and pay["card"]["title"].startswith("[DEMO]")
    card = _events(conv, "bazar_approval")[-1]
    assert card["amount_paise"] == bill["amount_paise"] and card["demo"]
    res = svc.decide("default", pay["approval_id"], "approve")
    assert res["outcome"]["status"] == "demo_paid" and "intent_url" not in res["outcome"]
    assert res["open"] is None
    assert any("DEMO" in (m or "") for m in _notices(conv))
    act = svc.activity("default")
    assert act["payments"][0]["status"] == "completed" and act["payments"][0]["demo"]
    # saved consumer number is reused next time
    again = svc.run("default", conv, "msedcl-mahavitaran", "fetch_bill", {})
    assert again["bill_ref"] == bill["bill_ref"]


def test_live_bills_need_partner_and_real_vpa(bz, monkeypatch):
    monkeypatch.setenv("BAZAR_BBPS_MODE", "http")
    monkeypatch.setenv("BAZAR_BBPS_BASE_URL", "https://bbps.partner.example")
    from app.bazar import config as bzc
    bzc.reset_settings()
    assert not bzc.get_settings().bills_live  # no collection VPA yet
    monkeypatch.setenv("BAZAR_COLLECTION_VPA", "newtika.collect@upi")
    bzc.reset_settings()
    assert not bzc.get_settings().bills_live  # placeholder is refused
    from app.bazar.connectors.base import ToolError
    with pytest.raises(ToolError, match="not mapped"):
        bz["svc"].run("default", bz["conv"], "msedcl-mahavitaran", "fetch_bill", {"consumer_number": "1", "billing_unit": "2"})


def test_shop_order_merchant_token_and_isolation(bz):
    svc, conv = bz["svc"], bz["conv"]
    shop = _kirana(svc)
    assert svc.find("default", "kirana atta")["packs"][0]["status"] == "ready"
    cart = svc.run("default", conv, "kirana-store", "build_cart", {"shop": "Ramesh bhau", "lines": "5 kilo atta aur 1 litre tel"})
    assert cart["total"] == "₹410"
    pay = svc.run("default", conv, "kirana-store", "place_order", {"cart_id": cart["cart_id"]})
    assert pay["needs_approval"] and pay["card"]["amount"] == "₹410"
    from app.bazar.connectors.base import ToolError
    with pytest.raises(ToolError):  # another user cannot approve my card
        svc.decide("someone-else", pay["approval_id"], "approve")
    res = svc.decide("default", pay["approval_id"], "approve")
    assert res["open"]["kind"] == "upi" and res["open"]["url"].startswith("upi://pay?pa=ramesh.kirana%40okicici")
    assert "am=410.00" in res["open"]["url"]
    orders = svc.shop_orders(shop["id"], None, shop["merchant_token"])
    assert orders[0]["status"] == "placed" and orders[0]["whatsapp_alert"].startswith("not sent")
    with pytest.raises(PermissionError):
        svc.update_order(shop["id"], orders[0]["id"], "accepted", True, "someone-else", "wrong-token")
    out = svc.update_order(shop["id"], orders[0]["id"], "accepted", True, None, shop["merchant_token"])
    assert out["payment"] == "paid"
    notes = " ".join(m or "" for m in _notices(conv))
    assert "accept" in notes and "received" in notes


def test_upi_to_person_always_needs_tap_even_with_caps(bz):
    svc, conv = bz["svc"], bz["conv"]
    svc.set_user_settings("default", {"cap_per_order_rupees": 5000, "cap_per_day_rupees": 10000})
    svc.add_contact("default", "Priya", upi_id="priya.demo@okaxis")
    r = svc.run("default", conv, "phonepe", "send_money", {"to": "Priya", "amount_rupees": 500, "note": "dinner"})
    assert r["needs_approval"]
    res = svc.decide("default", r["approval_id"], "approve")
    # v0.120 PhonePe refuses payment links to a person: the app opens without a link, the phone copies the UPI ID
    assert res["open"]["kind"] == "upi_copy" and res["open"]["vpa"] == "priya.demo@okaxis" and res["open"]["package"] == "com.phonepe.app"
    r2 = svc.run("default", conv, "paytm", "send_money", {"to": "Priya", "amount_rupees": 500, "note": "dinner"})
    res2 = svc.decide("default", r2["approval_id"], "approve")
    # v0.322 every UPI app refuses a link to a person now (her GPay: "server not responding / limit exceeded")
    assert res2["open"]["kind"] == "upi_copy" and res2["open"]["package"] == "net.one97.paytm"
    with pytest.raises(Exception):
        svc.add_contact("default", "Bad", upi_id="not-a-vpa")


def test_auto_approve_repeat_shop_under_cap(bz):
    svc, conv = bz["svc"], bz["conv"]
    _kirana(svc)
    svc.set_user_settings("default", {"cap_per_order_rupees": 500, "cap_per_day_rupees": 1000})
    c1 = svc.run("default", conv, "kirana-store", "build_cart", {"shop": "ramesh", "lines": "2 kg atta"})
    p1 = svc.run("default", conv, "kirana-store", "place_order", {"cart_id": c1["cart_id"]})
    assert p1["needs_approval"]  # first time with this shop: always a tap
    svc.decide("default", p1["approval_id"], "approve")
    c2 = svc.run("default", conv, "kirana-store", "build_cart", {"shop": "ramesh", "lines": "1 kg atta, 1 litre tel"})
    p2 = svc.run("default", conv, "kirana-store", "place_order", {"cart_id": c2["cart_id"]})
    assert p2.get("auto_approved") and p2["intent_url"].startswith("upi://")


class FakeRemote:
    def __init__(self):
        self.calls = []

    def list_tools(self):
        return [{"name": "get_cart", "description": "Cart", "input_schema": {"type": "object"}},
                {"name": "place_order", "description": "Place", "input_schema": {"type": "object"}}]

    def call_tool(self, name, args):
        self.calls.append(name)
        if name == "get_cart":
            return {"is_error": False, "text": "", "data": {"items": [{"name": "Biryani", "quantity": 2}], "to_pay": 389.0}}
        return {"is_error": False, "text": "", "data": {"order_id": "SW-1", "status": "PLACED"}}


def test_swiggy_link_cart_then_frozen_order(bz):
    svc, conv = bz["svc"], bz["conv"]
    from app.bazar.agent.toolbox import default_executors
    from app.bazar.connectors.mcp_remote import McpExecutor
    remote = FakeRemote()
    ex = default_executors()
    ex["mcp"] = McpExecutor(remote_factory=lambda url, tok: remote)
    ex["mcp"]._cache.clear()
    svc.set_executors(ex)
    from app.bazar.connectors.base import ToolError
    with pytest.raises(ToolError, match="Link your Swiggy Food"):
        svc.run("default", conv, "swiggy-food", "get_cart", {})
    assert _events(conv, "bazar_link")[-1]["pack_id"] == "swiggy-food"
    svc.link_token("default", "swiggy_food", "tok-123456789")
    with pytest.raises(ToolError, match="cart"):
        svc.run("default", conv, "swiggy-food", "place_order", {})
    svc.run("default", conv, "swiggy-food", "get_cart", {})
    p = svc.run("default", conv, "swiggy-food", "place_order", {"payment": "upi"})
    assert p["needs_approval"] and p["card"]["amount"] == "₹389"
    assert remote.calls == ["get_cart"]  # nothing ordered before the tap
    res = svc.decide("default", p["approval_id"], "approve")
    assert res["outcome"]["status"] == "placed" and remote.calls == ["get_cart", "place_order"]


def test_greetings_are_sent_by_the_user(bz):
    svc, conv = bz["svc"], bz["conv"]
    svc.add_contact("default", "Priya", phone="9800000002")
    r = svc.run("default", conv, "festival-greetings-sender", "send_greetings", {"festival": "Diwali"})
    res = svc.decide("default", r["approval_id"], "approve")
    assert res["open"]["kind"] == "links" and res["open"]["links"][0]["url"].startswith("https://wa.me/919800000002?text=")


def test_uber_with_place_name_only(bz):
    r = bz["svc"].run("default", bz["conv"], "uber-india", "ride_link", {"drop": {"name": "Akola Railway Station"}})
    assert r["deep_link"].startswith("https://m.uber.com/ul/?action=setPickup&pickup=my_location")
    assert _events(bz["conv"], "bazar_open")[-1]["kind"] == "app"


def test_bill_reminder_fires_into_chat(bz):
    svc, conv = bz["svc"], bz["conv"]
    import datetime as dt
    from app.bazar.db import Reminder
    from app.db import session
    svc.ensure_user  # noqa: B018
    with session() as s:
        svc.ensure_user(s, "default")
        s.add(Reminder(user_id="default", kind="bill", text="MSEDCL bill due soon", repeat="monthly",
                       due_at=dt.datetime.now(dt.timezone.utc).replace(tzinfo=None) - dt.timedelta(minutes=1)))
    assert svc.fire_due_reminders() == 1
    assert any("MSEDCL bill due soon" in (m or "") for m in _notices(conv))
    assert svc.fire_due_reminders() == 0  # moved to next month


def test_tools_through_agent_dispatch(bz):
    import asyncio
    from app.agent.tools import HANDLERS, TOOLS, Ctx, dispatch
    assert {"bazar_find", "bazar_run", "bazar_contact", "bazar_activity"} <= {t["name"] for t in TOOLS}
    ctx = Ctx(tenant_id="default", conversation_id=bz["conv"])
    from app.agent.tools import ToolError
    with pytest.raises(ToolError, match="no tool"):
        asyncio.run(dispatch("bazar_run", {"pack_id": "uber-india", "tool": "nope", "args": {}}, ctx))
    out = asyncio.run(dispatch("bazar_find", {"query": "rapido"}, ctx))
    assert out["packs"][0]["pack_id"] == "rapido"


def test_mcp_oauth_discovery_register_pkce_refresh(bz):
    from app.bazar import mcp_auth
    from app.bazar.db import Connection
    from app.db import session
    seen = {}

    def handler(req: httpx.Request):
        p = req.url.path
        if p == "/.well-known/oauth-protected-resource/food" or p == "/.well-known/oauth-protected-resource":
            return httpx.Response(200, json={"authorization_servers": ["https://mcp.swiggy.test/auth"]})
        if p == "/.well-known/oauth-authorization-server/auth":
            return httpx.Response(200, json={"issuer": "https://mcp.swiggy.test/auth",
                                             "authorization_endpoint": "https://mcp.swiggy.test/auth/authorize",
                                             "token_endpoint": "https://mcp.swiggy.test/auth/token",
                                             "registration_endpoint": "https://mcp.swiggy.test/auth/register",
                                             "scopes_supported": ["mcp:tools", "mcp:resources"]})
        if p == "/auth/register":
            seen["reg"] = json.loads(req.content)
            return httpx.Response(201, json={"client_id": "cli-1"})
        if p == "/auth/token":
            body = dict(httpx.QueryParams(req.content.decode()))
            seen.setdefault("tok", []).append(body)
            if body["grant_type"] == "authorization_code":
                return httpx.Response(200, json={"access_token": "AT1", "refresh_token": "RT1", "expires_in": 60})
            return httpx.Response(200, json={"access_token": "AT2", "refresh_token": "RT2", "expires_in": 432000})
        return httpx.Response(404)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    with session() as s:
        bz["svc"].ensure_user(s, "default")
        url = mcp_auth.start(s, "default", "swiggy_food", "https://mcp.swiggy.test/food", client=client)
    q = dict(httpx.URL(url).params)
    assert url.startswith("https://mcp.swiggy.test/auth/authorize?") and q["code_challenge_method"] == "S256"
    assert q["redirect_uri"] == "https://santosh.example.in/bazar/link/callback" and q["scope"] == "mcp:tools mcp:resources"
    assert seen["reg"]["redirect_uris"] == ["https://santosh.example.in/bazar/link/callback"]
    with session() as s:
        uid, prov = mcp_auth.finish(s, q["state"], "CODE", client=client)
    assert (uid, prov) == ("default", "swiggy_food") and seen["tok"][0]["code_verifier"]
    with session() as s:
        conn = s.scalars(select(Connection).where(Connection.provider == "swiggy_food", Connection.status == "active")).one()
        assert "AT1" not in conn.token_enc  # encrypted at rest
        assert mcp_auth.access_token(s, conn, client=client) == "AT2"  # expires in 60 s -> refreshed (rotating)
    assert seen["tok"][1] == {"grant_type": "refresh_token", "refresh_token": "RT1", "client_id": "cli-1",
                              "resource": "https://mcp.swiggy.test/food"}   # v0.162 RFC 8707 on refresh too
    with session() as s:
        with pytest.raises(mcp_auth.LinkError):
            mcp_auth.finish(s, q["state"], "CODE", client=client)  # state is single-use


def test_signed_in_users_are_isolated(bz, monkeypatch):
    monkeypatch.setenv("API_KEY", "")
    monkeypatch.setenv("EMAIL_ADDRESS", "owner@gmail.com")
    from app.config import get_settings
    get_settings.cache_clear()
    from fastapi.testclient import TestClient
    from app import accounts, main
    from app.db import User, session
    with session() as s:
        s.add_all([User(id="usr_owner", email="owner@gmail.com"), User(id="usr_kunal", email="kunal@gmail.com")])
    t_owner, t_kunal = accounts.issue_session("usr_owner"), accounts.issue_session("usr_kunal")
    c = TestClient(main.app)
    conv_owner = c.post("/api/conversations", headers={"Authorization": f"Bearer {t_owner}"}).json()["id"]
    conv_kunal = c.post("/api/conversations", headers={"Authorization": f"Bearer {t_kunal}"}).json()["id"]
    from app.db import Conversation
    with session() as s:
        assert s.get(Conversation, conv_owner).tenant_id == "default"  # owner keeps the .env-connected tenant
        assert s.get(Conversation, conv_kunal).tenant_id == "usr_kunal"
    r = c.get(f"/api/conversations/{conv_owner}/messages", headers={"Authorization": f"Bearer {t_kunal}"})
    assert r.status_code == 404
    # Kunal's Bazar data is his own
    c.post("/api/bazar/contacts", json={"name": "Amit", "upi_id": "amit@ybl"}, headers={"Authorization": f"Bearer {t_kunal}"})
    assert c.get("/api/bazar/contacts", headers={"Authorization": f"Bearer {t_owner}"}).json()["contacts"] == []
    assert c.get("/api/bazar/catalog", headers={"Authorization": f"Bearer {t_kunal}"}).json()["total"] == 694   # 159 MVP + 515 P1 + 6 devices + shopping + Mera PC + Santosh Browser + PC operator + Santosh Email + Santosh Calendar + Santosh Sheets + Drive + Forms + Slides + Photos + Notebook + YouTube + App Jaanch
    # the owner's .env email is not reachable by another signed-in user
    import asyncio
    from app.agent.tools import Ctx, dispatch
    monkeypatch.setenv("EMAIL_PASSWORD", "app-pass")
    get_settings.cache_clear()
    from app.agent.tools import ToolError
    with pytest.raises(ToolError, match="juda nahi"):   # the server .env mailbox is only for the owner
        asyncio.run(dispatch("email_check", {}, Ctx(tenant_id="usr_kunal", conversation_id=conv_kunal)))


def test_payment_webhook_needs_signature(bz, monkeypatch):
    from fastapi.testclient import TestClient
    from app import main
    c = TestClient(main.app)
    assert c.post("/bazar/webhooks/payment", content=b'{"txn_ref":"x","status":"SUCCESS"}').status_code == 401
    monkeypatch.setenv("BAZAR_WEBHOOK_SECRET", "whsec")
    from app.bazar import config as bzc
    bzc.reset_settings()
    import hashlib, hmac as h
    raw = b'{"txn_ref":"nope","status":"SUCCESS"}'
    sig = h.new(b"whsec", raw, hashlib.sha256).hexdigest()
    r = c.post("/bazar/webhooks/payment", content=raw, headers={"x-signature": sig})
    assert r.status_code == 400 and "Unknown payment" in r.text


def test_owner_tenant_finds_owner_google_signin(bz, monkeypatch):
    monkeypatch.setenv("EMAIL_ADDRESS", "owner@gmail.com")
    from app.config import get_settings
    get_settings.cache_clear()
    from app import accounts, google_auth
    from app.db import OAuthConnection, User, session
    with session() as s:
        s.add(User(id="usr_owner", email="owner@gmail.com"))
        s.add(OAuthConnection(user_id="usr_owner", provider="google", access_token_enc=accounts.encrypt("a"),
                              refresh_token_enc=accounts.encrypt("r"), scopes="openid"))
    assert google_auth.has_google("default")      # the owner's chats run as 'default'
    assert google_auth.has_google("usr_owner")
    assert not google_auth.has_google("usr_other")


def test_agent_chat_runs_bazar_end_to_end(bz):
    """Scripted Claude: find the pack, fetch the bill, ask to pay -> confirm card appears in the chat stream."""
    import asyncio
    from app.agent import run_turn, set_client
    from tests.test_campaign_flow import ScriptedClaude, last_result, text, tool
    conv = bz["conv"]
    seen = {}

    def after_find(msgs):
        r = json.loads(last_result(msgs)["content"])
        seen["find"] = r
        return tool("bazar_run", {"pack_id": r["packs"][0]["pack_id"], "tool": "fetch_bill",
                                  "args": {"consumer_number": "330012345678", "billing_unit": "4630"}}, 2)

    def after_fetch(msgs):
        r = json.loads(last_result(msgs)["content"])
        seen["bill"] = r
        return tool("bazar_run", {"pack_id": "msedcl-mahavitaran", "tool": "pay_bill", "args": {"bill_ref": r["bill_ref"]}}, 3)

    def after_pay(msgs):
        seen["pay"] = json.loads(last_result(msgs)["content"])
        return text("Bill " + seen["bill"]["amount"] + " ka hai. Approve dabaiye.")

    set_client(ScriptedClaude([tool("bazar_find", {"query": "msedcl bijli bill"}, 1), after_find, after_fetch, after_pay]))
    out = asyncio.run(run_turn(conv, "MSEDCL ka bill bhar do", tenant_id="default"))
    assert seen["find"]["packs"][0]["pack_id"] == "msedcl-mahavitaran"
    assert seen["pay"]["needs_approval"] is True
    assert "Approve" in out
    assert _events(conv, "bazar_approval")[-1]["amount"] == seen["bill"]["amount"]


def test_card_reaches_live_stream_from_worker_thread(bz):
    """Bazar tools run in a thread; the live SSE listener must still wake up with the card."""
    import asyncio
    from app.events import bus
    conv = bz["conv"]

    async def go():
        q = bus.subscribe(conv)
        waiter = asyncio.ensure_future(q.get())   # the SSE stream is already waiting
        await asyncio.sleep(0)
        bill = await asyncio.to_thread(bz["svc"].run, "default", conv, "msedcl-mahavitaran", "fetch_bill",
                                       {"consumer_number": "330012345678", "billing_unit": "4630"})
        await asyncio.to_thread(bz["svc"].run, "default", conv, "msedcl-mahavitaran", "pay_bill", {"bill_ref": bill["bill_ref"]})
        first = await asyncio.wait_for(waiter, timeout=2)
        ev = first
        while ev["kind"] != "bazar_approval":
            ev = await asyncio.wait_for(q.get(), timeout=2)
        bus.unsubscribe(conv, q)
        return ev

    ev = asyncio.run(go())
    assert ev["kind"] == "bazar_approval" and ev["payload"]["title"].startswith("[DEMO]")


def test_catchup_lists_what_happened_while_offline(bz):
    from fastapi.testclient import TestClient
    from app import main
    from app.events import notify
    notify(bz["conv"], "Diwali campaign 240 logon ko bhej diya.")
    c = TestClient(main.app)
    r = c.get("/api/catchup", params={"since": "2020-01-01T00:00:00Z"}).json()
    assert r["count"] >= 1 and "Diwali" in r["items"][-1]["text"]
    assert c.get("/api/catchup", params={"since": "bad"}).status_code == 400
