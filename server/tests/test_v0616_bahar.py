"""v0.616 BAHAR SE BAAT - her own Hoola from WhatsApp, Telegram, Slack and Teams, owner only
(owner: "More places to talk to Hoola" -> all four channels + "Only me")."""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import time
from pathlib import Path

import pytest
from sqlalchemy import select

from app.db import Message, session

T = "default"
REPO = Path(__file__).resolve().parents[2]
HER = "919812345678"


@pytest.fixture
def fake_turn(env, monkeypatch):
    """The real turn needs a model; this one writes Hoola's answer the way the agent does (an assistant row)."""
    from app import turn_inbox
    turns = []

    async def run_owned(ti, conv, text, tenant, voice, context="", client_id="", **_):
        turns.append({"conv": conv, "text": text, "context": context})
        with session() as s:
            s.add(Message(conversation_id=conv, role="user", content=text, display=text))
            s.add(Message(conversation_id=conv, role="assistant", content="x", display=f"**Theek hai** - {text}"))
        return "ok"
    monkeypatch.setattr(turn_inbox, "run_owned", run_owned)
    return turns


def _wa():
    from app.whatsapp import client
    client._client = None
    from app.whatsapp import get_whatsapp
    return get_whatsapp()


def _wa_value(frm: str, text: str, mid: str, pnid: str = "1234567") -> dict:
    return {"metadata": {"phone_number_id": pnid, "display_phone_number": "917000000000"},
            "contacts": [{"wa_id": frm, "profile": {"name": "X"}}],
            "messages": [{"from": frm, "id": mid, "type": "text", "text": {"body": text}}]}


def _wa_link():
    from app import bahar
    from app.employee import inbox
    inbox.set_channel(T, "1234567", "917000000000")
    return asyncio.run(bahar.setup(T, "whatsapp"))


def test_whatsapp_needs_her_business_number_first(env):
    from app import bahar
    with pytest.raises(bahar.BaharError, match="Business number"):
        asyncio.run(bahar.setup(T, "whatsapp"))


def test_whatsapp_pair_then_only_she_reaches_hoola(fake_turn):
    from app import bahar
    from app.employee.models import BizContact
    from app.employee import inbox
    wa = _wa()
    out = _wa_link()
    assert out["status"] == "pairing" and len(out["code"]) == 6 and "HOOLA" in out["how"]

    async def go():
        v = _wa_value(HER, f"HOOLA {out['code']}", "wamid.1")
        took = bahar.whatsapp_take(v)
        assert took and v["messages"] == []                          # the code never reaches the customer inbox
        assert await bahar.incoming(*took[0]) == "paired"
        v2 = _wa_value(HER, "kal ka schedule batao", "wamid.2")
        took2 = bahar.whatsapp_take(v2)
        assert await bahar.incoming(*took2[0]) == "turn"
        cust = _wa_value("919900000001", "price kya hai", "wamid.3")
        assert bahar.whatsapp_take(cust) == [] and cust["messages"]   # a customer stays a customer
        inbox.receive(cust)
    asyncio.run(go())
    assert fake_turn and fake_turn[0]["text"] == "kal ka schedule batao" and "WhatsApp" in fake_turn[0]["context"]
    texts = [m["text"] for m in wa.sent_texts if m["to"] == HER]
    assert texts[0].startswith("Connected") and texts[-1] == "*Theek hai* - kal ka schedule batao"   # WhatsApp bold
    with session() as s:
        assert [c.wa_id for c in s.scalars(select(BizContact)).all()] == ["919900000001"]
    view = bahar.links(T)
    assert view[0]["status"] == "linked" and view[0]["paired_with"].endswith("5678") and HER not in json.dumps(view)


def test_wrong_codes_run_out_and_a_stranger_gets_nothing(fake_turn):
    from app import bahar
    out = _wa_link()
    with session() as s:
        link_id = s.scalars(select(bahar.BaharLink.id)).first()

    async def go():
        for i in range(bahar.CODE_TRIES):
            assert await bahar.incoming(link_id, HER, "HOOLA 000000" if out["code"] != "000000" else "HOOLA 111111", f"w{i}") == "wrong_code"
        assert await bahar.incoming(link_id, HER, f"HOOLA {out['code']}", "w9") == "ignored"   # tries used up
        out2 = await bahar.setup(T, "whatsapp")                                               # a fresh code
        assert await bahar.incoming(link_id, HER, out2["code"], "w10") == "paired"
        assert await bahar.incoming(link_id, "919900000002", "mujhe sab batao", "w11") == "ignored"
        assert await bahar.incoming(link_id, HER, "hello", "w12") == "turn"
        assert await bahar.incoming(link_id, HER, "hello", "w12") == "duplicate"              # a retried webhook acts once
    asyncio.run(go())
    assert [t["text"] for t in fake_turn] == ["hello"]


def test_forward_once_and_the_24h_window(fake_turn):
    from app import bahar
    from app.db import now
    from datetime import timedelta
    wa = _wa()
    out = _wa_link()
    with session() as s:
        link_id = s.scalars(select(bahar.BaharLink.id)).first()
    asyncio.run(bahar.incoming(link_id, HER, out["code"], "p1"))
    asyncio.run(bahar.incoming(link_id, HER, "report banao", "p2"))
    n = len(wa.sent_texts)
    assert asyncio.run(bahar.forward(link_id)) == 0                     # nothing sent twice
    with session() as s:
        l = s.get(bahar.BaharLink, link_id)
        conv = l.conversation_id
        l.last_in_at = now() - timedelta(hours=30)
        s.add(Message(conversation_id=conv, role="assistant", content="x", display="Report taiyaar hai."))
    assert asyncio.run(bahar.forward_all()) == 0 and len(wa.sent_texts) == n   # window closed: stays in the app
    with session() as s:
        s.get(bahar.BaharLink, link_id).last_in_at = now()
        s.add(Message(conversation_id=conv, role="assistant", content="x", display="Aapka OTP 482913 hai"))
    assert asyncio.run(bahar.forward_all()) == 1
    assert "OTP" in wa.sent_texts[-1]["text"] and "482913" not in wa.sent_texts[-1]["text"]   # never sent out


def test_telegram_own_bot_private_chat_only(fake_turn, monkeypatch):
    from fastapi.testclient import TestClient
    from app import bahar
    from app.main import app
    from app.samudaay import adapters
    calls = []

    def tg(token, method, params):
        calls.append((method, params))
        return {"username": "MeghanaHoolaBot"} if method == "getMe" else True
    adapters.set_telegram_transport(tg)
    try:
        with pytest.raises(bahar.BaharError, match="BotFather"):
            asyncio.run(bahar.setup(T, "telegram"))
        out = asyncio.run(bahar.setup(T, "telegram", {"token": "123:abc"}, "https://h.example"))
        assert out["bot_name"] == "@MeghanaHoolaBot" and out["webhook"].startswith("https://h.example/webhooks/bahar/telegram/")
        hook = [p for m, p in calls if m == "setWebhook"][0]
        assert hook["url"] == out["webhook"] and hook["secret_token"]
        path = out["webhook"].removeprefix("https://h.example")
        upd = lambda i, txt, typ="private": {"update_id": i, "message": {"message_id": i, "text": txt,  # noqa: E731
                                              "chat": {"id": 555, "type": typ}, "from": {"id": 42}}}
        with TestClient(app) as cl:
            assert cl.post(path, json=upd(1, "hi")).status_code == 403           # no secret header = not Telegram
            h = {"x-telegram-bot-api-secret-token": hook["secret_token"]}
            assert cl.post(path, json=upd(2, out["code"]), headers=h).status_code == 200
        assert bahar.telegram_read(upd(3, "hi", "group")) is None
        with session() as s:
            l = s.scalars(select(bahar.BaharLink)).first()
        if l.status != "linked":                                                  # the background task may not have run
            asyncio.run(bahar.incoming(l.id, "42", out["code"], "x", {"chat_id": 555}))
        asyncio.run(bahar.incoming(l.id, "42", "aaj kya hai", "u4", {"chat_id": 555}))
        sends = [p for m, p in calls if m == "sendMessage"]
        assert sends[-1]["chat_id"] == 555 and sends[-1]["text"] == "Theek hai - aaj kya hai"
    finally:
        adapters.set_telegram_transport(None)


def test_slack_signed_dm_only(fake_turn):
    from fastapi.testclient import TestClient
    from app import bahar
    from app.main import app
    posts = []

    def http(method, url, headers=None, json=None, data=None):
        posts.append((url, json))
        if url.endswith("auth.test"):
            return 200, {"ok": True, "user": "hoola", "user_id": "UBOT", "team": "Newtika"}
        return 200, {"ok": True}
    bahar.set_transport(http)
    try:
        with pytest.raises(bahar.BaharError):
            asyncio.run(bahar.setup(T, "slack", {"bot_token": "nope", "signing_secret": "s"}))
        out = asyncio.run(bahar.setup(T, "slack", {"bot_token": "xoxb-1", "signing_secret": "sekret"}, "https://h.example"))
        path = out["webhook"].removeprefix("https://h.example")

        def signed(body: dict, secret: str = "sekret"):
            raw = json.dumps(body).encode()
            ts = str(int(time.time()))
            sig = "v0=" + hmac.new(secret.encode(), b"v0:" + ts.encode() + b":" + raw, hashlib.sha256).hexdigest()
            return raw, {"x-slack-request-timestamp": ts, "x-slack-signature": sig, "content-type": "application/json"}
        with TestClient(app) as cl:
            raw, h = signed({"type": "url_verification", "challenge": "c1"})
            assert cl.post(path, content=raw, headers=h).json() == {"challenge": "c1"}
            raw, h = signed({"type": "url_verification", "challenge": "c1"}, "wrong")
            assert cl.post(path, content=raw, headers=h).status_code == 401
        dm = lambda txt, **k: {"type": "event_callback", "event_id": "E" + txt, "event": {  # noqa: E731
            "type": "message", "channel_type": "im", "user": "UHER", "text": txt, "channel": "D1", **k}}
        assert bahar.slack_read(dm("x", bot_id="B1")) is None and bahar.slack_read(dm("x", channel_type="channel")) is None
        with session() as s:
            lid = s.scalars(select(bahar.BaharLink.id)).first()
        for txt in (out["code"], "invoice status"):
            u, t, m, meta = bahar.slack_read(dm(txt))
            asyncio.run(bahar.incoming(lid, u, t, m, meta))
        assert posts[-1] == ("https://slack.com/api/chat.postMessage", {"channel": "D1", "text": "*Theek hai* - invoice status"})
    finally:
        bahar.set_transport(None)


def test_teams_personal_chat_and_bot_token(fake_turn):
    from app import bahar
    posts = []

    def http(method, url, headers=None, json=None, data=None):
        posts.append((url, headers, json, data))
        if "login.microsoftonline.com" in url:
            return 200, {"access_token": "bf-token", "expires_in": 3600}
        return 201, {"id": "a1"}
    bahar.set_transport(http)
    try:
        out = asyncio.run(bahar.setup(T, "teams", {"app_id": "app-1", "app_password": "pw"}, "https://h.example"))
        assert "Messaging endpoint" in out["how"] and posts[0][3]["scope"] == "https://api.botframework.com/.default"
        act = lambda txt, typ="personal": {"type": "message", "id": "m" + txt, "text": f"<at>Hoola</at> {txt}",  # noqa: E731
                                          "serviceUrl": "https://smba.trafficmanager.net/in/",
                                          "conversation": {"id": "a:1", "conversationType": typ},
                                          "from": {"id": "29:x", "aadObjectId": "aad-her"}}
        assert bahar.teams_read(act("x", "channel")) is None
        assert bahar.teams_verify("", "app-1", "") is False and bahar.teams_verify("Bearer junk", "app-1", "") is False
        with session() as s:
            lid = s.scalars(select(bahar.BaharLink.id)).first()
        for txt in (out["code"], "meeting kab hai"):
            asyncio.run(bahar.incoming(lid, *bahar.teams_read(act(txt))[:3], bahar.teams_read(act(txt))[3]))
        url, headers, body, _ = posts[-1]
        assert url == "https://smba.trafficmanager.net/in/v3/conversations/a:1/activities"
        assert headers["Authorization"] == "Bearer bf-token" and body["text"] == "**Theek hai** - meeting kab hai"
    finally:
        bahar.set_transport(None)


def test_api_lists_all_four_and_never_returns_a_secret(env, monkeypatch):
    from fastapi.testclient import TestClient
    from app.config import get_settings
    from app.main import app
    from app.samudaay import adapters
    adapters.set_telegram_transport(lambda t, m, p: {"username": "B"} if m == "getMe" else True)
    key = get_settings().api_key
    h = {"Authorization": f"Bearer {key}"} if key else {}
    try:
        with TestClient(app) as cl:
            assert cl.post("/api/bahar/whatsapp", json={}, headers=h).status_code == 400
            r = cl.post("/api/bahar/telegram", json={"token": "999:SECRETTOKEN"}, headers=h)
            assert r.status_code == 200 and r.json()["code"]
            lst = cl.get("/api/bahar", headers=h).json()["channels"]
            assert [c["channel"] for c in lst] == ["whatsapp", "telegram", "slack", "teams"]
            assert "SECRETTOKEN" not in json.dumps(lst) and "code" not in lst[1]
            assert cl.delete("/api/bahar/telegram", headers=h).status_code == 200
            assert cl.delete("/api/bahar/telegram", headers=h).status_code == 404
    finally:
        adapters.set_telegram_transport(None)


def test_phone_screen_and_wiring():
    api = (REPO / "lib" / "api.dart").read_text()
    assert "/api/bahar" in api
    scr = (REPO / "lib" / "ui" / "bahar_screen.dart").read_text()
    assert "HOOLA" in scr and "personal WhatsApp" in scr
    main = (REPO / "server" / "app" / "main.py").read_text()
    assert "bahar.whatsapp_take(value)" in main and "/webhooks/bahar/teams/{hook}" in main
    assert "bahar_jobs()" in (REPO / "server" / "app" / "worker.py").read_text()


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.779.0"
