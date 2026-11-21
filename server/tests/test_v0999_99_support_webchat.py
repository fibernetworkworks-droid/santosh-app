"""SUPPORT WEB CHAT (G5 of docs/SUPPORT_GLOBAL_PLAN.md): the chat on her website and inside her own app - one line of
code, only her listed website addresses, a signed visitor token, signed-in users by HMAC (their own thread), files
(pictures / PDF, checked by their bytes), "Call me" as a call-back hand-over, a contact form with a honeypot, her app's
REST API with its own key + her signed webhook, the hosted chat page; the same answer engine / hand-over / ticket
updates as every channel. Walked in a real browser on another website's address."""
from __future__ import annotations

import hashlib
import hmac
import json

import pytest
from fastapi.testclient import TestClient

import app.seva.service  # noqa: F401  (tables for init_db)

T = "default"
SHOP = "https://shop.example.com"


@pytest.fixture
def wc(env, monkeypatch):
    from app.seva import channels as CH
    from app.seva import service as S
    from app.seva import webchat as WC
    monkeypatch.setattr(S, "_ai", lambda *a, **k: "")
    monkeypatch.setattr(S, "_ai_json", lambda *a, **k: {})
    monkeypatch.setattr(S, "_note_chat", lambda *a, **k: None)
    WC._HITS.clear()
    calls = []
    CH.set_transport(lambda method, url, headers=None, json=None, data=None, auth=None:
                     (calls.append({"url": url, "headers": headers, "json": json}), (200, {}))[1])
    S.kb_add(T, "What are your timings?", "10 am to 7 pm, Monday to Saturday.")
    from app.main import app
    yield WC, S, CH, TestClient(app), calls
    CH.set_transport(None)


def _web(WC, **kw):
    return WC.setup(T, "web", {"domains": ["shop.example.com"]} | kw)


def test_setup_secrets_once_and_allowed_sites(wc):
    WC, S, CH, c, _ = wc
    v = _web(WC)
    assert v["secrets_once"]["identity_secret"].startswith("hid_") and 'data-hoola-support="' in v["snippet"]
    again = _web(WC, title="Talk to Asha's shop")
    assert "secrets_once" not in again and again["settings"]["title"] == "Talk to Asha's shop"
    assert "hid_" not in json.dumps(WC.view(T))                                  # never shown again
    key = v["key"]
    ok = c.post(f"/api/support/web/{key}/session", json={}, headers={"Origin": SHOP})
    assert ok.status_code == 200 and ok.json()["token"] and ok.headers["access-control-allow-origin"] == SHOP
    assert c.post(f"/api/support/web/{key}/session", json={}, headers={"Origin": "https://evil.example"}).status_code == 403
    assert c.post(f"/api/support/web/{key}/session", json={}).status_code == 403          # no website at all
    assert c.post(f"/api/support/web/{key}/session", json={}, headers={"Origin": "http://testserver"}).status_code == 200  # her hosted page
    assert c.options(f"/api/support/web/{key}/messages", headers={"Origin": SHOP}).headers["access-control-allow-methods"]
    with pytest.raises(WC.WebError, match="website address"):
        WC.setup(T, "web", {"domains": ["not a site!"]})
    assert "<script src='/static/support/widget.js'" in c.get(f"/support/chat/{key}").text


def test_visitor_chat_answers_hands_over_and_hears_the_team(wc):
    WC, S, CH, c, _ = wc
    key = _web(WC)["key"]
    h = {"Origin": SHOP}
    tok = c.post(f"/api/support/web/{key}/session", json={}, headers=h).json()["token"]
    r = c.post(f"/api/support/web/{key}/messages", json={"token": tok, "text": "what are your timings?"}, headers=h).json()
    assert [m["from"] for m in r["messages"]] == ["you", "hoola"] and "10 am" in r["messages"][1]["text"]
    assert c.post(f"/api/support/web/{key}/messages", json={"token": "forged.token", "text": "hi"}, headers=h).status_code == 401
    r = c.post(f"/api/support/web/{key}/messages", json={"token": tok, "text": "I want to talk to a person"}, headers=h).json()
    assert "passed this to" in r["messages"][-1]["text"]
    n = len(c.post(f"/api/support/web/{key}/messages", json={"token": tok, "text": "hello?"}, headers=h).json()["messages"])
    cust = next(x["customer"] for x in CH.conversations(T))
    CH.reply_as_person(T, cust, "Hi, Meena here.", "staff:Meena")
    got = c.get(f"/api/support/web/{key}/messages", params={"token": tok}, headers=h).json()["messages"]
    assert len(got) == n + 1 and got[-1] == got[-1] | {"from": "team", "text": "Hi, Meena here."}
    from app.seva import handover as H
    num = H.handovers(T, "open")[0]["ticket"]
    S.update(T, num, status="pending", public="Please send a photo of the bill.")
    assert "photo of the bill" in c.get(f"/api/support/web/{key}/messages", params={"token": tok}, headers=h).json()["messages"][-1]["text"]


def test_signed_in_user_sees_only_their_thread(wc):
    WC, S, CH, c, _ = wc
    v = _web(WC)
    sec, key, h = v["secrets_once"]["identity_secret"], v["key"], {"Origin": SHOP}
    good = hmac.new(sec.encode(), b"42", hashlib.sha256).hexdigest()
    assert c.post(f"/api/support/web/{key}/session", json={"user_id": "42", "user_hash": "bad"}, headers=h).status_code == 403
    t1 = c.post(f"/api/support/web/{key}/session", json={"user_id": "42", "user_hash": good}, headers=h).json()["token"]
    c.post(f"/api/support/web/{key}/messages", json={"token": t1, "text": "what are your timings"}, headers=h)
    again = c.post(f"/api/support/web/{key}/session", json={"user_id": "42", "user_hash": good}, headers=h).json()
    assert again["signed_in"] and len(again["messages"]) == 2                      # the same thread on another device
    other = c.post(f"/api/support/web/{key}/session", json={}, headers=h).json()
    assert other["messages"] == []


def test_files_call_me_and_the_form(wc):
    WC, S, CH, c, _ = wc
    key, h = _web(WC)["key"], {"Origin": SHOP}
    tok = c.post(f"/api/support/web/{key}/session", json={}, headers=h).json()["token"]
    png = b"\x89PNG\r\n\x1a\n" + b"0" * 100
    r = c.post(f"/api/support/web/{key}/file", data={"token": tok}, files={"file": ("bill.png", png, "image/png")}, headers=h)
    assert r.status_code == 200 and "Sent a file: bill.png" in r.json()["messages"][-1]["text"]
    assert c.post(f"/api/support/web/{key}/file", data={"token": tok}, files={"file": ("x.exe", b"MZ\x90\x00", "image/png")},
                  headers=h).status_code == 400                                     # checked by its bytes, not its name
    cust = CH.conversations(T)[0]["customer"]
    fid = CH.thread(T, cust)["messages"][-1]["file"]
    assert c.get(f"/api/seva/chatfiles/{fid}").content == png
    r = c.post(f"/api/support/web/{key}/callme", json={"token": tok, "phone": "+91 98000 00001", "note": "about my bill"}, headers=h).json()
    assert "call you back between" in r["line"]
    from app.seva import handover as H
    assert H.handovers(T, "open")[0]["channel"] == "phone"
    f = c.post(f"/api/support/form/{key}", data={"name": "Ana", "email": "ana@example.com", "message": "My order is late"}, headers=h).json()
    assert f["number"] and S.ticket(T, f["number"])["channel"] == "web"
    assert c.post(f"/api/support/form/{key}", data={"message": "x", "website": "http://spam"}, headers=h).json() == {"ok": True}
    assert c.post(f"/api/support/form/{key}", data={"message": "hi"}, headers=h).status_code == 400


def test_her_app_api_and_signed_webhook(wc):
    WC, S, CH, c, calls = wc
    v = WC.setup(T, "api", {"webhook_url": "https://app.example/hoola"})
    key, whs = v["secrets_once"]["api_key"], v["secrets_once"]["webhook_secret"]
    assert c.post("/api/support/v1/messages", json={"user_id": "u7", "text": "hi"}, headers={"Authorization": "Bearer hsk_wrong"}).status_code == 401
    r = c.post("/api/support/v1/messages", json={"user_id": "u7", "text": "what are your timings?"}, headers={"Authorization": f"Bearer {key}"}).json()
    assert "10 am" in r["replies"][0]["text"]
    CH.reply_as_person(T, "user:u7", "We also open on Sunday mornings.", "owner")
    hook = calls[-1]
    assert hook["url"] == "https://app.example/hoola" and hook["json"]["user_id"] == "u7"
    body = json.dumps(hook["json"]).encode()
    assert hook["headers"]["X-Hoola-Signature"] == "sha256=" + hmac.new(whs.encode(), body, hashlib.sha256).hexdigest()
    got = c.get("/api/support/v1/messages", params={"user_id": "u7"}, headers={"Authorization": f"Bearer {key}"}).json()
    assert got["messages"][-1]["from"] == "team"
    new = WC.rotate(T, "api", "api_key")["secrets_once"]["api_key"]
    assert c.get("/api/support/v1/messages", params={"user_id": "u7"}, headers={"Authorization": f"Bearer {key}"}).status_code == 401
    assert c.get("/api/support/v1/messages", params={"user_id": "u7"}, headers={"Authorization": f"Bearer {new}"}).status_code == 200


def test_limits_and_routes(wc):
    WC, S, CH, c, _ = wc
    key, h = _web(WC)["key"], {"Origin": SHOP}
    tok = c.post(f"/api/support/web/{key}/session", json={}, headers=h).json()["token"]
    codes = [c.post(f"/api/support/web/{key}/messages", json={"token": tok, "text": f"thanks {i}"}, headers=h).status_code for i in range(22)]
    assert 429 in codes
    assert c.get("/api/seva/webchat").json()["web"]["key"] == key
    assert c.put("/api/seva/webchat/web", json={"colour": "red"}).status_code == 400
    assert c.post("/api/seva/channels", json={"kind": "web"}).status_code == 400          # set up on its own page
    assert "web" not in [k["kind"] for k in CH.catalog()["kinds"]]


@pytest.fixture
def w_server(wc, monkeypatch):
    import os
    import threading
    import time as _t
    sync_api = pytest.importorskip("playwright.sync_api")
    from tests.test_v161_console_e2e import _free_port
    from tests.test_v161_stream import KEY
    monkeypatch.setenv("API_KEY", KEY)
    from app.config import get_settings
    get_settings.cache_clear()
    from app.employee import hire
    WC, S, CH, c, calls = wc
    hire.hire(T, "support", trust="seekh")
    key = WC.setup(T, "web", {"domains": ["shop.localhost"]})["key"]
    import uvicorn
    from app import main
    port = _free_port()
    srv = uvicorn.Server(uvicorn.Config(main.app, host="127.0.0.1", port=port, log_level="warning"))
    th = threading.Thread(target=srv.run, daemon=True)
    th.start()
    for _ in range(1200):
        if srv.started:
            break
        _t.sleep(0.05)
    assert srv.started
    try:
        pw = sync_api.sync_playwright().start()
        try:
            # the test website and the test server are both on this machine; a real site and Hoola are both public
            args = ["--disable-features=LocalNetworkAccessChecks,PrivateNetworkAccessChecks,BlockInsecurePrivateNetworkRequests,"
                    "PrivateNetworkAccessSendPreflights"]
            browser = pw.chromium.launch(args=args, **({"executable_path": os.environ["HOOLA_CHROMIUM"]} if os.environ.get("HOOLA_CHROMIUM") else {}))
        except Exception as ex:      # noqa: BLE001
            pw.stop()
            pytest.skip(f"no Chromium for Playwright here: {str(ex)[:80]}")
        yield f"http://127.0.0.1:{port}", browser, KEY, key
        browser.close()
        pw.stop()
    finally:
        srv.should_exit = True
        th.join(timeout=10)


def test_widget_on_her_website_in_a_real_browser(w_server):
    base, browser, key, wkey = w_server
    errors = []
    ctx = browser.new_context(viewport={"width": 1280, "height": 860})
    page_html = (f"<!doctype html><html><head><title>Asha's shop</title></head><body><h1>Asha's shop</h1>"
                 f"<script src='{base}/static/support/widget.js' data-hoola-support='{wkey}' async></script></body></html>")
    ctx.route("http://shop.localhost/**", lambda route: route.fulfill(status=200, content_type="text/html", body=page_html))
    pg = ctx.new_page()
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.goto("http://shop.localhost/")
    fab = pg.locator("#hoola-support").locator("button.fab")
    fab.wait_for()
    fab.click()
    box = pg.locator("#hoola-support")
    box.locator("input.in").first.wait_for()
    box.locator("#hsIn").fill("what are your timings?")
    box.locator("form.bar button[type=submit]").click()
    pg.wait_for_function("() => document.querySelector('#hoola-support').shadowRoot.querySelector('.msgs').innerText.includes('10 am')",
                         timeout=15000)
    ctx.close()
    p2 = browser.new_context(viewport={"width": 390, "height": 800})
    m = p2.new_page()
    m.on("pageerror", lambda e: errors.append(str(e)))
    m.goto(f"{base}/support/chat/{wkey}")
    m.wait_for_function("() => { const r = document.querySelector('#hoola-support'); return r && r.shadowRoot.querySelector('.hd').innerText.includes('Chat with us'); }",
                        timeout=15000)
    assert m.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1"), "sideways scroll"
    p2.close()
    c3 = browser.new_context(viewport={"width": 1440, "height": 900})
    c3.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    d = c3.new_page()
    d.on("pageerror", lambda e: errors.append(str(e)))
    d.goto(base + "/console/support#/settings")
    d.wait_for_function("() => document.querySelector('#spPage').innerText.includes('Put this one line on every page')", timeout=20000)
    c3.close()
    assert not errors, errors
