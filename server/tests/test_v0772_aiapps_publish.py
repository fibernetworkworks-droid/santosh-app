"""v0.772 HOOLA AI APPS - D2 publishing: the hosted page, the embed bubble, keys + limits, the service API, MCP and
the business WhatsApp number. Routers are mounted on a local FastAPI app (main.py is the integrator's)."""
import asyncio
import hashlib

import pytest
from fastapi import FastAPI, HTTPException, Request
from fastapi.testclient import TestClient

SOUL = {"name": "Sharma Kirana", "about": "Grocery shop in Pune", "facts": ["Open 9 am to 9 pm", "Delivery free above Rs 500"],
        "actions": ["ticket"], "opening": "Namaste! Ask me anything.", "suggested": ["Timings?", "Delivery?"],
        "persona": "SECRET-PERSONA warm", "refuse": ["SECRET-TOPIC"]}
OWNER = {"Authorization": "Bearer owner-key"}


def _client():
    from app.aiapps import keys as K, mcp as M, public as P

    def require_key(request: Request):
        if request.headers.get("authorization") != "Bearer owner-key":
            raise HTTPException(401, "Missing or wrong API key")

    def current_tenant(request: Request) -> str:
        return "t1"

    app = FastAPI()
    for mod in (K, P, M):
        app.include_router(mod.make_router(require_key, current_tenant))
    K.LIMITER.reset()
    P.IP_WINDOW.reset()
    P.SESSION_WINDOW.reset()
    return TestClient(app)


def _app(live=True, **channels):
    from app.aiapps import runtime as RT, store as ST
    RT.ASK[0] = lambda s, p, n: "We are open 9 am to 9 pm."
    a = ST.create("t1", "Sharma Kirana", soul=dict(SOUL))
    if live:
        ST.publish("t1", a["id"], a["draft_hash"])
    if channels:
        ST.set_channels("t1", a["id"], **channels)
    return ST.row("t1", a["id"])


def _consent(c, code, embed=False):
    q = "?embed=1" if embed else ""
    r = c.post(f"/api/aiapp-pub/{code}/session{q}", json={"consent": True})
    assert r.status_code == 200, r.text
    return {"X-Visitor-Token": r.json()["token"]}


def test_draft_and_paused_are_404(env):
    from app.aiapps import store as ST
    c = _client()
    a = _app(live=False)
    for path in (f"/ai/{a.code}", f"/api/aiapp-pub/{a.code}", f"/ai/{a.code}/embed.js"):
        assert c.get(path).status_code == 404
    assert c.post(f"/api/aiapp-pub/{a.code}/session", json={"consent": True}).status_code == 404
    assert c.get("/ai/nosuchcode").status_code == 404
    ST.publish("t1", a.id, ST.get("t1", a.id)["draft_hash"])
    assert c.get(f"/ai/{a.code}").status_code == 200
    ST.set_status("t1", a.id, "paused")
    assert c.get(f"/ai/{a.code}").status_code == 404
    assert c.get(f"/api/aiapp-pub/{a.code}").status_code == 404


def test_page_notice_csp_and_public_info(env):
    c = _client()
    a = _app()
    r = c.get(f"/ai/{a.code}")
    assert r.status_code == 200
    csp = r.headers["content-security-policy"]
    assert "default-src 'self' 'unsafe-inline'" in csp and "frame-ancestors 'none'" in csp
    assert r.headers["x-frame-options"] == "DENY"
    body = r.text
    assert "I agree" in body and "AI assistant" in body and "innerHTML" not in body and "<script src" not in body
    assert "fonts.googleapis" not in body and "Sharma Kirana" in body
    info = c.get(f"/api/aiapp-pub/{a.code}").json()
    assert info["name"] == "Sharma Kirana" and info["opening"] and info["suggested"] == ["Timings?", "Delivery?"]
    assert "OTP" in info["notice"]
    blob = str(info)
    for secret in ("facts", "about", "persona", "refuse", "limits", "Grocery shop", "SECRET-PERSONA", "SECRET-TOPIC",
                   "Delivery free"):
        assert secret not in blob, secret
    e = c.get(f"/ai/{a.code}?embed=1")
    assert e.status_code == 200 and "frame-ancestors *" in e.headers["content-security-policy"]
    assert "x-frame-options" not in e.headers


def test_escaping_of_a_hostile_name(env):
    from app.aiapps import store as ST
    c = _client()
    a = _app(live=False)
    sl = ST.get("t1", a.id)["draft"]
    sl["name"] = "<script>alert(1)</script>"
    d = ST.save_draft("t1", a.id, sl)
    ST.publish("t1", a.id, d["draft_hash"])
    body = c.get(f"/ai/{a.code}").text
    assert "<script>alert(1)</script>" not in body and "&lt;script&gt;" in body


def test_consent_chat_history_feedback(env):
    c = _client()
    a = _app()
    code = a.code
    assert c.post(f"/api/aiapp-pub/{code}/session", json={"consent": False}).status_code == 400
    assert c.post(f"/api/aiapp-pub/{code}/session", json={}).status_code == 400
    assert c.post(f"/api/aiapp-pub/{code}/chat", json={"text": "timings?"}).status_code == 401
    assert c.post(f"/api/aiapp-pub/{code}/chat", json={"text": "timings?"},
                  headers={"X-Visitor-Token": "avs_forged"}).status_code == 401
    h1 = _consent(c, code)
    r = c.post(f"/api/aiapp-pub/{code}/chat", json={"text": "When are you open?"}, headers=h1)
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["reply"] == "We are open 9 am to 9 pm." and j["outcome"] == "model" and j["message_id"]
    assert c.post(f"/api/aiapp-pub/{code}/chat", json={"text": "x" * 2001}, headers=h1).status_code == 413
    h2 = _consent(c, code)
    assert c.get(f"/api/aiapp-pub/{code}/history", headers=h2).json()["messages"] == []
    mine = c.get(f"/api/aiapp-pub/{code}/history", headers=h1).json()["messages"]
    assert len(mine) == 1 and mine[0]["q"] == "When are you open?"
    # feedback: only on your own message
    assert c.post(f"/api/aiapp-pub/{code}/feedback", json={"message_id": j["message_id"], "good": True},
                  headers=h2).status_code == 404
    ok = c.post(f"/api/aiapp-pub/{code}/feedback", json={"message_id": j["message_id"], "good": True}, headers=h1)
    assert ok.status_code == 200 and ok.json()["feedback"] == 1


def test_channel_page_off_and_session_limit(env, monkeypatch):
    from app.aiapps import public as P
    c = _client()
    a = _app(page=False)
    assert c.get(f"/ai/{a.code}").status_code == 404
    assert c.get(f"/api/aiapp-pub/{a.code}").status_code == 404
    assert c.get(f"/ai/{a.code}?embed=1").status_code == 200          # embed still on
    h = _consent(c, a.code, embed=True)
    monkeypatch.setattr(P, "SESSION_WINDOW", P._Window(2, 3600))
    assert c.post(f"/api/aiapp-pub/{a.code}/chat?embed=1", json={"text": "timings"}, headers=h).status_code == 200
    assert c.post(f"/api/aiapp-pub/{a.code}/chat?embed=1", json={"text": "timings"}, headers=h).status_code == 200
    r = c.post(f"/api/aiapp-pub/{a.code}/chat?embed=1", json={"text": "timings"}, headers=h)
    assert r.status_code == 429 and int(r.headers["retry-after"]) > 0


def test_ip_limit(env, monkeypatch):
    from app.aiapps import public as P
    c = _client()
    a = _app()
    h = _consent(c, a.code)
    monkeypatch.setattr(P, "IP_WINDOW", P._Window(1, 600))
    assert c.post(f"/api/aiapp-pub/{a.code}/chat", json={"text": "timings"}, headers=h).status_code == 200
    assert c.post(f"/api/aiapp-pub/{a.code}/chat", json={"text": "timings"}, headers=h).status_code == 429


def test_embed_js(env):
    from app.aiapps import store as ST
    c = _client()
    a = _app()
    r = c.get(f"/ai/{a.code}/embed.js")
    assert r.status_code == 200 and "javascript" in r.headers["content-type"]
    assert f"/ai/{a.code}?embed=1" in r.text and "sandbox" in r.text and "document.cookie" not in r.text
    ST.set_channels("t1", a.id, embed=False)
    assert c.get(f"/ai/{a.code}/embed.js").status_code == 404
    assert c.get(f"/ai/{a.code}?embed=1").status_code == 404


def test_keys_shown_once_hashed_revoked(env):
    from app.aiapps.models import AiAppKey
    from app.db import session
    c = _client()
    a = _app(api=True)
    assert c.post(f"/api/aiapps/{a.id}/keys", json={"name": "site"}).status_code == 401
    r = c.post(f"/api/aiapps/{a.id}/keys", json={"name": "site", "rpm": 5}, headers=OWNER)
    assert r.status_code == 200, r.text
    k = r.json()
    key = k["key"]
    assert key.startswith("aik_") and k["tail"] == key[-4:] and k["limits"]["rpm"] == 5
    with session() as s:
        row = s.get(AiAppKey, k["id"])
        assert row.key_hash == hashlib.sha256(key.encode()).hexdigest() and key not in str(row.__dict__)
    listed = c.get(f"/api/aiapps/{a.id}/keys", headers=OWNER).json()["keys"]
    assert len(listed) == 1 and "key" not in listed[0] and key not in str(listed)
    for bad in ({"rpm": 0}, {"rpm": 121}, {"rph": 5001}, {"concurrent": 11}, {"rpm": "x"}):
        assert c.post(f"/api/aiapps/{a.id}/keys", json=bad, headers=OWNER).status_code == 400
    auth = {"Authorization": f"Bearer {key}"}
    ok = c.post("/api/aiapp-api/v1/chat", json={"text": "When are you open?", "user": "u1"}, headers=auth)
    assert ok.status_code == 200 and ok.json()["reply"] == "We are open 9 am to 9 pm."
    sid = ok.json()["session_id"]
    again = c.post("/api/aiapp-api/v1/chat", json={"text": "timings", "user": "u1"}, headers=auth)
    assert again.json()["session_id"] == sid                       # one conversation per user id
    assert c.post("/api/aiapp-api/v1/chat", json={"text": "hi"}, headers={"Authorization": "Bearer aik_nope"}).status_code == 401
    assert c.post("/api/aiapp-api/v1/chat", json={"text": "hi"}).status_code == 401
    assert c.delete(f"/api/aiapps/{a.id}/keys/{k['id']}", headers=OWNER).status_code == 200
    assert c.post("/api/aiapp-api/v1/chat", json={"text": "hi"}, headers=auth).status_code == 401
    assert c.delete(f"/api/aiapps/{a.id}/keys/nokey", headers=OWNER).status_code == 404


def test_key_needs_api_channel_and_live(env):
    from app.aiapps import keys as K, store as ST
    c = _client()
    a = _app()                                                    # api channel is off by default
    key = K.create("t1", a.id, "x")["key"]
    auth = {"Authorization": f"Bearer {key}"}
    assert c.post("/api/aiapp-api/v1/chat", json={"text": "hi"}, headers=auth).status_code == 401
    ST.set_channels("t1", a.id, api=True)
    assert c.post("/api/aiapp-api/v1/chat", json={"text": "timings"}, headers=auth).status_code == 200
    ST.set_status("t1", a.id, "paused")
    assert c.post("/api/aiapp-api/v1/chat", json={"text": "timings"}, headers=auth).status_code == 401


def test_max_keys(env):
    from app.aiapps import keys as K, store as ST
    a = _app()
    for i in range(K.MAX_KEYS):
        K.create("t1", a.id, f"k{i}")
    with pytest.raises(ST.AppError) as e:
        K.create("t1", a.id, "one too many")
    assert e.value.code == 409
    with pytest.raises(ST.AppError):
        K.create("other-tenant", a.id, "not hers")


def test_rpm_and_concurrent_limits(env):
    from app.aiapps import keys as K
    c = _client()
    a = _app(api=True)
    key = K.create("t1", a.id, "x", rpm=2, rph=100, concurrent=1)["key"]
    auth = {"Authorization": f"Bearer {key}"}
    assert c.post("/api/aiapp-api/v1/chat", json={"text": "timings"}, headers=auth).status_code == 200
    assert c.post("/api/aiapp-api/v1/chat", json={"text": "timings"}, headers=auth).status_code == 200
    r = c.post("/api/aiapp-api/v1/chat", json={"text": "timings"}, headers=auth)
    assert r.status_code == 429 and 1 <= int(r.headers["retry-after"]) <= 61
    # hour window and the at-once counter, on the limiter itself
    L = K.Limiter()
    L.check("k", rpm=100, rph=2, concurrent=5, clock=0)
    L.check("k", rpm=100, rph=2, concurrent=5, clock=70)
    with pytest.raises(K.LimitError) as e:
        L.check("k", rpm=100, rph=2, concurrent=5, clock=140)
    assert 3000 < e.value.retry_after <= 3601
    L.check("k", rpm=100, rph=2, concurrent=5, clock=3601)        # the first one left the hour
    with L.running("c", 1):
        with pytest.raises(K.LimitError):
            with L.running("c", 1):
                pass
        with pytest.raises(K.LimitError):
            L.check("c", rpm=100, rph=100, concurrent=1)
    with L.running("c", 1):                                       # released after the call
        pass


def test_mcp(env):
    from app.aiapps import keys as K, store as ST
    c = _client()
    a = _app(mcp=True)
    key = K.create("t1", a.id, "mcp")["key"]
    auth = {"Authorization": f"Bearer {key}"}
    url = f"/mcp/aiapp/{a.code}"
    init = c.post(url, json={"jsonrpc": "2.0", "id": 1, "method": "initialize",
                             "params": {"protocolVersion": "2025-03-26"}}, headers=auth).json()
    assert init["result"]["protocolVersion"] == "2025-03-26" and init["result"]["serverInfo"]["name"] == "hoola-aiapp"
    tl = c.post(url, json={"jsonrpc": "2.0", "id": 2, "method": "tools/list"}, headers=auth).json()
    t = tl["result"]["tools"]
    assert [x["name"] for x in t] == ["ask"] and t[0]["inputSchema"]["required"] == ["text"]
    assert "Sharma Kirana" in t[0]["description"] and "Grocery" not in str(t)
    call = c.post(url, json={"jsonrpc": "2.0", "id": 3, "method": "tools/call",
                             "params": {"name": "ask", "arguments": {"text": "When are you open?", "user": "bot"}}},
                  headers=auth).json()
    assert call["result"]["content"] == [{"type": "text", "text": "We are open 9 am to 9 pm."}]
    bad = c.post(url, json={"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {"name": "pay"}}, headers=auth)
    assert bad.json()["error"]["code"] == -32602
    assert c.post(url, json={"jsonrpc": "2.0", "id": 5, "method": "nope"}, headers=auth).json()["error"]["code"] == -32601
    r = c.post(url, json={"jsonrpc": "2.0", "id": 6, "method": "tools/list"}, headers={"Authorization": "Bearer aik_bad"})
    assert r.status_code == 401 and r.json()["error"]["code"] == -32001
    # a key of ANOTHER app cannot open this one
    b = ST.create("t1", "Other", soul=dict(SOUL, name="Other"))
    ST.publish("t1", b["id"], b["draft_hash"])
    ST.set_channels("t1", b["id"], mcp=True)
    other = K.create("t1", b["id"], "x")["key"]
    assert c.post(url, json={"jsonrpc": "2.0", "id": 7, "method": "tools/list"},
                  headers={"Authorization": f"Bearer {other}"}).status_code == 401
    ST.set_channels("t1", a.id, mcp=False)
    assert c.post(url, json={"jsonrpc": "2.0", "id": 8, "method": "tools/list"}, headers=auth).status_code == 401
    assert c.post(url, content=b"not json", headers=auth).json()["error"]["code"] == -32700


# ---------------------------------------------------------------- WhatsApp
PNID = "123456789"
CUST = "919876543210"


def _hook(text, mid):
    return {"metadata": {"phone_number_id": PNID, "display_phone_number": "919800000000"},
            "contacts": [{"wa_id": CUST, "profile": {"name": "Ravi"}}],
            "messages": [{"from": CUST, "id": mid, "type": "text", "text": {"body": text}}]}


def _wa_setup():
    from app.employee import inbox
    from app.employee import service as emp
    emp.setup("t1", enabled=True, role="front_desk", business_name="Sharma Kirana", about="Grocery",
              hours={"open": "00:00", "close": "23:59", "days": [0, 1, 2, 3, 4, 5, 6]}, inbox_on=True)
    inbox.set_channel("t1", PNID, "919800000000")


class _Brain:
    def __init__(self):
        self.calls = 0

    async def __call__(self, system, history, tools):
        self.calls += 1
        return [{"type": "text", "text": "EMPLOYEE BRAIN REPLY"}], "end_turn"


def test_whatsapp_bound_app_answers(env, monkeypatch):
    from app.aiapps import wa as AW
    from app.employee import inbox
    _wa_setup()
    a = _app(whatsapp=PNID)
    assert AW.app_for_number("t1", PNID).id == a.id and AW.app_for_number("t1", "999") is None
    brain = _Brain()
    monkeypatch.setattr(inbox, "_brain", brain)
    inbox.receive(_hook("When are you open?", "w1"))
    assert asyncio.run(inbox.answer_pending()) == 1
    sent = env["wa"].sent_texts[-1]
    assert sent["to"] == CUST and sent["text"].endswith("We are open 9 am to 9 pm.") and "AI assistant" in sent["text"]
    assert brain.calls == 0
    inbox.receive(_hook("timings again?", "w2"))
    asyncio.run(inbox.answer_pending())
    assert env["wa"].sent_texts[-1]["text"] == "We are open 9 am to 9 pm."     # the notice only once
    t = inbox.thread("t1", inbox.contacts("t1")[0]["id"])
    assert [m["by"] for m in t["messages"] if m["direction"] == "out"] == ["ai_app", "ai_app"]


def test_whatsapp_unbound_number_unchanged(env, monkeypatch):
    from app.employee import inbox
    _wa_setup()
    _app(whatsapp="some-other-number")            # bound to a different number
    _app(live=False, whatsapp=PNID)               # a DRAFT bound to this number does not count
    brain = _Brain()
    monkeypatch.setattr(inbox, "_brain", brain)
    inbox.receive(_hook("When are you open?", "u1"))
    asyncio.run(inbox.answer_pending())
    assert brain.calls == 1 and env["wa"].sent_texts[-1]["text"] == "EMPLOYEE BRAIN REPLY"
    out = [m for m in inbox.thread("t1", inbox.contacts("t1")[0]["id"])["messages"] if m["direction"] == "out"]
    assert [m["by"] for m in out] == ["hoola"]


def test_whatsapp_human_mode_and_stop_not_answered(env, monkeypatch):
    from app.employee import inbox
    _wa_setup()
    _app(whatsapp=PNID)
    brain = _Brain()
    monkeypatch.setattr(inbox, "_brain", brain)
    inbox.receive(_hook("hello", "h1"))
    cid = inbox.contacts("t1")[0]["id"]
    inbox.set_human("t1", cid, True)
    before = len(getattr(env["wa"], "sent_texts", []))
    inbox.receive(_hook("When are you open?", "h2"))
    asyncio.run(inbox.answer_pending())
    assert asyncio.run(inbox.answer("t1", cid)) == ""                # even when asked directly
    assert len(getattr(env["wa"], "sent_texts", [])) == before and brain.calls == 0
    inbox.set_human("t1", cid, False)
    inbox.receive(_hook("STOP", "h3"))
    asyncio.run(inbox.flush_queued())
    n = len(getattr(env["wa"], "sent_texts", []))
    assert asyncio.run(inbox.answer("t1", cid)) == ""
    assert len(getattr(env["wa"], "sent_texts", [])) == n and brain.calls == 0
