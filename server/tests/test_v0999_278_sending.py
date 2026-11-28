"""v0.999.278 SENDING (owner, on the workflow library's two limits - mails that waited as drafts, chat posts that only
came to her Hoola chat: "MAKE THIS FUCTIONAL FOR HOOLA ROUTE").

- a Send step really sends: mail from her mailbox, Telegram / Slack / Discord / Mattermost through her saved sign-in;
- nothing goes out until she taps Allow sending on the route; the tap is bound to WHERE it sends, so a new address,
  chat or channel stops it again (new words do not);
- a test run sends nothing, 50 a run, a per-day limit per route, every send written down;
- a Telegram bot starts a route (Telegram setWebhook to the route's address) and the reply goes back to that chat;
- the n8n importer turns mail and chat-app posts into Send steps and a Telegram trigger into the bot start.
"""
import asyncio
import json
import os
import threading
import time
from pathlib import Path

import pytest

from tests.test_bazar import bz  # noqa: F401  (fresh DB fixture)

from app.agent import dhara_tools as D
from app.agent.tools import Ctx, ToolError
from app.route import n8n as N
from app.route import send as SN
from app.route import workspace as WS

TG = "123456789:AAH" + "x" * 32


def _wipe(t):
    import shutil
    shutil.rmtree(Path("data") / "dhara" / t, ignore_errors=True)


def _run(c):
    return asyncio.run(c)


def _save(t, name, steps, **kw):
    return _run(D.dhara_save(Ctx(tenant_id=t, conversation_id=""), name=name, steps=steps, **kw))


def _go(t, name, vars_=None, test=False):
    rid = D.create_run(t, D.get_workflow(t, name=name), vars_=vars_ or {})
    if test:
        r = D.get_run(t, rid)
        r["context"]["_test"] = True
        D.update_run(t, rid, context=r["context"])
    _run(D.execute_run(t, rid))
    return D.get_run(t, rid)


@pytest.fixture
def T(bz, monkeypatch):
    monkeypatch.setattr(D, "polite_s", 0)
    D._RUNNING.clear()
    t = "r275_send"
    _wipe(t)
    yield t
    D._RUNNING.clear()
    _wipe(t)


@pytest.fixture
def posts(monkeypatch):
    got = []

    def fake(url, js, headers=None, guard=False):
        got.append({"url": url, "json": js, "headers": headers or {}, "guard": guard})
        if "api.telegram.org" in url:
            if url.endswith("/getMe"):
                return 200, {"ok": True, "result": {"username": "shop_bot"}}
            return 200, {"ok": True, "result": {"message_id": 7, "chat": {"id": js.get("chat_id")}}}
        if "slack.com/api" in url:
            return 200, {"ok": True, "ts": "1.2", "channel": js.get("channel")}
        return 200, {"id": "m1"}
    monkeypatch.setattr(SN, "_post", fake)
    return got


@pytest.fixture
def mails(monkeypatch):
    got = []

    def fake(tenant, to, cc, bcc, subject, body, account, md):
        got.append({"to": to, "cc": cc, "subject": subject, "body": body, "account": account})
        return {"sent": True, "to": to, "from": "me@example.com", "message_id": "<m1>"}
    monkeypatch.setattr(SN, "_email", fake)
    return got


MAIL = [{"id": "mail", "type": "send", "via": "email", "to": "{{vars.who}}", "subject": "Hello {{vars.name}}",
         "body": "Your order is ready."}]


# ---------------------------------------------------------------- the step + her permission
def test_a_send_step_checks_itself():
    D.validate_steps(MAIL)
    for bad in ({"via": "fax", "text": "x"}, {"via": "telegram"}, {"via": "email"},
                {"via": "slack", "text": "x", "connection": "bad name"}, {"via": "telegram", "text": "x", "format": "rtf"}):
        with pytest.raises(ToolError):
            D.validate_steps([{"id": "s", "type": "send", **bad}])
    D.validate_steps([{"id": "s", "type": "send", "via": "telegram", "chat": "1", "photo": "https://x.example/a.png"}])


def test_nothing_goes_out_until_she_allows_it(T, mails):
    _save(T, "orders", MAIL)
    r = _go(T, "orders", {"who": "a@example.com", "name": "Asha"})
    assert r["status"] == "failed" and "Allow sending" in (r.get("error") or "") and not mails
    wf = D.get_workflow(T, name="orders")
    st = SN.status(T, wf)
    assert not st["allowed"] and st["sends"][0]["via"] == "email" and "{{vars.who}}" in st["sends"][0]["words"]
    with pytest.raises(SN.SendError):
        SN.allow(T, wf, "wrong")
    assert SN.allow(T, wf, st["hash"])["allowed"]
    r = _go(T, "orders", {"who": "a@example.com", "name": "Asha"})
    assert r["status"] == "done", r.get("error")
    assert mails == [{"to": "a@example.com", "cc": "", "subject": "Hello Asha", "body": "Your order is ready.", "account": ""}]
    st = SN.status(T, wf)
    assert st["today"] == 1 and st["last"][0]["ok"] == 1 and st["last"][0]["dest"] == "a@example.com"


def test_new_words_keep_it_allowed_a_new_address_stops_it(T, mails):
    _save(T, "orders", MAIL)
    wf = D.get_workflow(T, name="orders")
    SN.allow(T, wf, SN.status(T, wf)["hash"])
    _save(T, "orders", [{**MAIL[0], "body": "New words."}])
    assert SN.status(T, D.get_workflow(T, name="orders"))["allowed"]
    _save(T, "orders", [{**MAIL[0], "to": "someone@else.example"}])
    st = SN.status(T, D.get_workflow(T, name="orders"))
    assert not st["allowed"] and st["changed"]
    r = _go(T, "orders", {})
    assert r["status"] == "failed" and "changed since you allowed" in r["error"] and not mails
    SN.allow(T, D.get_workflow(T, name="orders"), st["hash"], on=True)
    SN.allow(T, D.get_workflow(T, name="orders"), "", on=False)
    assert not SN.status(T, D.get_workflow(T, name="orders"))["allowed"]


def test_a_test_run_sends_nothing(T, mails):
    _save(T, "orders", MAIL)
    r = _go(T, "orders", {"who": "a@example.com", "name": "Asha"}, test=True)
    out = r["context"]["steps"]["mail"]["output"]
    assert r["status"] == "done" and out["would_send"] and out["to"] == "a@example.com" and not mails


def test_limits_a_run_and_a_day(T, mails, monkeypatch):
    _save(T, "many", [{"id": "each", "type": "loop", "items": "{{vars.people}}",
                       "body": [{"id": "m", "type": "send", "via": "email", "to": "{{item}}", "subject": "Hi", "body": "x"}]}],
          settings={"sends_per_day": 3})
    wf = D.get_workflow(T, name="many")
    assert SN.per_day(wf) == 3
    SN.allow(T, wf, SN.status(T, wf)["hash"])
    r = _go(T, "many", {"people": [f"p{i}@example.com" for i in range(5)]})
    assert len(mails) == 3 and r["status"] == "failed" and "3 a day" in r["error"]
    monkeypatch.setattr(SN, "RUN_MAX", 2)
    mails.clear()
    with D._con(T) as con:
        con.execute("DELETE FROM route_sends")
        con.commit()
    r = _go(T, "many", {"people": [f"p{i}@example.com" for i in range(5)]})
    assert len(mails) == 2 and "at most 2" in r["error"]


# ---------------------------------------------------------------- the sign-ins + each app
def test_chat_app_sign_ins(T):
    with pytest.raises(WS.WorkspaceError):
        WS.save_credential(T, {"name": "BOT", "kind": "telegram", "token": "not a token"})
    o = WS.save_credential(T, {"name": "BOT", "kind": "telegram", "token": TG})
    assert o["host"] == "api.telegram.org" and o["hint"].endswith(TG[-4:])
    with pytest.raises(WS.WorkspaceError):
        WS.save_credential(T, {"name": "SL", "kind": "slack", "webhook": "https://evil.example/hook"})
    WS.save_credential(T, {"name": "SL", "kind": "slack", "webhook": "https://hooks.slack.com/services/T1/B2/c3"})
    WS.save_credential(T, {"name": "DC", "kind": "discord", "webhook": "https://discordapp.com/api/webhooks/123/abc_d"})
    WS.save_credential(T, {"name": "MM", "kind": "mattermost", "server": "https://chat.example.com", "token": "t" * 26})
    assert WS.messaging_secret(T, "DC", "discord")["webhook"].startswith("https://discord.com/")
    assert all(TG not in json.dumps(c) for c in WS.credentials(T)), "the token is never shown again"
    with pytest.raises(WS.WorkspaceError):
        WS.messaging_secret(T, "BOT", "slack")
    with pytest.raises(WS.WorkspaceError):
        WS.apply_auth(T, "BOT", "https://api.telegram.org/x", {})


def test_each_app_is_asked_its_own_way(T, posts):
    WS.save_credential(T, {"name": "BOT", "kind": "telegram", "token": TG})
    WS.save_credential(T, {"name": "SL", "kind": "slack", "token": "xoxb-1-2-abc"})
    WS.save_credential(T, {"name": "DCH", "kind": "discord", "webhook": "https://discord.com/api/webhooks/123/abc"})
    WS.save_credential(T, {"name": "MM", "kind": "mattermost", "webhook": "https://chat.example.com/hooks/k1"})
    steps = [{"id": "tg", "type": "send", "via": "telegram", "chat": "{{vars.chat}}", "text": "<b>Hi</b>", "format": "html"},
             {"id": "pic", "type": "send", "via": "telegram", "connection": "BOT", "chat": "5", "text": "A photo",
              "photo": "https://img.example/a.png"},
             {"id": "sl", "type": "send", "via": "slack", "connection": "SL", "channel": "#sales", "text": "New lead"},
             {"id": "dc", "type": "send", "via": "discord", "connection": "DCH", "text": "Up"},
             {"id": "mm", "type": "send", "via": "mattermost", "connection": "MM", "text": "Report", "channel": "town"}]
    _save(T, "all", steps)
    wf = D.get_workflow(T, name="all")
    SN.allow(T, wf, SN.status(T, wf)["hash"])
    r = _go(T, "all", {"chat": "42"})
    assert r["status"] == "done", r.get("error")
    by = {p["url"].split("/")[-1].split("?")[0]: p for p in posts}
    assert posts[0]["url"] == f"https://api.telegram.org/bot{TG}/sendMessage"
    assert posts[0]["json"] == {"chat_id": "42", "text": "<b>Hi</b>", "parse_mode": "HTML"}
    assert by["sendPhoto"]["json"] == {"chat_id": "5", "photo": "https://img.example/a.png", "caption": "A photo"}
    assert by["chat.postMessage"]["headers"]["Authorization"] == "Bearer xoxb-1-2-abc"
    assert by["chat.postMessage"]["json"] == {"channel": "#sales", "text": "New lead"}
    assert posts[3]["url"] == "https://discord.com/api/webhooks/123/abc?wait=true" and posts[3]["json"] == {"content": "Up"}
    assert posts[4]["url"] == "https://chat.example.com/hooks/k1" and posts[4]["guard"] and posts[4]["json"]["channel"] == "town"
    assert r["context"]["steps"]["tg"]["output"]["message_id"] == 7


def test_a_refusal_is_said_and_written_down(T, monkeypatch):
    WS.save_credential(T, {"name": "BOT", "kind": "telegram", "token": TG})
    monkeypatch.setattr(SN, "_post", lambda *a, **k: (400, {"ok": False, "description": "Bad Request: chat not found"}))
    _save(T, "tg", [{"id": "tg", "type": "send", "via": "telegram", "chat": "9", "text": "x"}])
    wf = D.get_workflow(T, name="tg")
    SN.allow(T, wf, SN.status(T, wf)["hash"])
    r = _go(T, "tg")
    assert r["status"] == "failed" and "chat not found" in r["error"]
    last = SN.status(T, wf)["last"][0]
    assert last["ok"] == 0 and "chat not found" in last["error"]


def test_two_sign_ins_need_a_pick(T, posts):
    WS.save_credential(T, {"name": "A", "kind": "slack", "token": "xoxb-a"})
    WS.save_credential(T, {"name": "B", "kind": "slack", "token": "xoxb-b"})
    _save(T, "sl", [{"id": "sl", "type": "send", "via": "slack", "channel": "#x", "text": "x"}])
    wf = D.get_workflow(T, name="sl")
    SN.allow(T, wf, SN.status(T, wf)["hash"])
    r = _go(T, "sl")
    assert r["status"] == "failed" and "pick the one" in r["error"] and not posts


# ---------------------------------------------------------------- a Telegram bot starts the route
def test_the_bot_starts_the_route_and_gets_its_answer(T, posts, monkeypatch):
    WS.save_credential(T, {"name": "BOT", "kind": "telegram", "token": TG})
    _save(T, "bot", [{"id": "reply", "type": "send", "via": "telegram", "chat": "{{vars.body.message.chat.id}}",
                      "text": "You said: {{vars.body.message.text}}"}], trigger="webhook")
    wf = D.get_workflow(T, name="bot")
    with pytest.raises(SN.SendError):
        SN.connect_bot(T, wf, "BOT", "http://insecure.example")
    o = SN.connect_bot(T, wf, "BOT", "https://hoola.example")
    assert o["connected"] and o["bot"] == "shop_bot"
    hook = posts[0]["json"]["url"]
    assert posts[0]["url"].endswith("/setWebhook") and hook.startswith("https://hoola.example/api/dhara/hook/")
    assert SN.status(T, wf)["bot"]["connection"] == "BOT"
    SN.allow(T, wf, SN.status(T, wf)["hash"])
    D.set_enabled(T, wf["id"], True)
    tok = hook.rsplit("/", 1)[1]
    upd = {"update_id": 1, "message": {"message_id": 3, "text": "hello", "chat": {"id": 777}}}
    got = _run(D.webhook_call(tok, upd))
    assert got["ok"], got
    for _ in range(100):
        r = D.get_run(T, got["run_id"])
        if r["status"] in ("done", "failed"):
            break
        if r["status"] == "queued":
            _run(D.execute_run(T, got["run_id"]))
        time.sleep(0.05)
    assert r["status"] == "done", r.get("error")
    sent = [p for p in posts if p["url"].endswith("/sendMessage")]
    assert sent and sent[-1]["json"] == {"chat_id": "777", "text": "You said: hello"}
    SN.disconnect_bot(T, wf)
    assert SN.status(T, wf)["bot"] is None and posts[-1]["url"].endswith("/deleteWebhook")


# ---------------------------------------------------------------- the n8n importer
def _wf(nodes, links):
    conns: dict = {}
    for a, b in links:
        conns.setdefault(a, {}).setdefault("main", [[]])[0].append({"node": b, "type": "main", "index": 0})
    return {"name": "Flow", "nodes": [{"name": n, "type": "n8n-nodes-base." + t, "parameters": p, "typeVersion": 2}
                                       for n, t, p in nodes], "connections": conns}


def test_n8n_mail_and_chat_posts_become_send_steps():
    doc = _wf([("Start", "manualTrigger", {}),
               ("Mail", "gmail", {"sendTo": "boss@example.com", "subject": "Daily", "message": "All good",
                                  "options": {"ccList": "team@example.com"}}),
               ("Old mail", "emailSend", {"toEmail": "a@example.com", "subject": "S", "text": "T"}),
               ("Draft", "gmail", {"resource": "draft", "sendTo": "x@example.com", "subject": "D", "message": "M"}),
               ("Slack", "slack", {"select": "channel", "channelId": {"__rl": True, "mode": "id", "value": "C07"}, "text": "Hi"}),
               ("Discord", "discord", {"text": "Up", "webhookUri": "https://discord.com/api/webhooks/1/x"}),
               ("MM", "mattermost", {"channelId": "chan1", "message": "Report"})],
              [("Start", "Mail"), ("Mail", "Old mail"), ("Old mail", "Draft"), ("Draft", "Slack"), ("Slack", "Discord"),
               ("Discord", "MM")])
    plan = N.convert(doc)
    steps = D.validate_steps(plan["steps"])
    by = {s["label"]: s for s in steps}
    assert by["Mail"] == {**by["Mail"], "type": "send", "via": "email", "to": "boss@example.com", "cc": "team@example.com"}
    assert by["Old mail"]["type"] == "send" and by["Old mail"]["to"] == "a@example.com"
    assert by["Draft"]["type"] == "tool" and by["Draft"]["name"] == "email_draft", "a draft in n8n stays a draft"
    assert by["Slack"]["via"] == "slack" and by["Slack"]["channel"] == "C07"
    assert by["Discord"]["via"] == "discord" and by["MM"]["channel"] == "chan1" and by["MM"]["text"] == "Report"
    assert any("Allow sending" in n for n in plan["report"]["notes"])
    assert not plan["report"]["placeholders"]


# ---------------------------------------------------------------- the routes + the page
def test_the_routes(bz, monkeypatch):
    from fastapi.testclient import TestClient
    from tests.test_v161_stream import KEY
    monkeypatch.setenv("API_KEY", KEY)
    from app.config import get_settings
    get_settings.cache_clear()
    t = get_settings().tenant_id
    _wipe(t)
    try:
        from app import main
        h = {"Authorization": f"Bearer {KEY}"}
        _save(t, "r_send", MAIL)
        wf = D.get_workflow(t, name="r_send")
        with TestClient(main.app) as c:
            st = c.get(f"/api/route/routes/{wf['id']}/sending", headers=h).json()
            assert not st["allowed"] and len(st["sends"]) == 1
            assert c.post(f"/api/route/routes/{wf['id']}/sending", json={"hash": "x"}, headers=h).status_code == 409
            assert c.post(f"/api/route/routes/{wf['id']}/sending", json={"hash": st["hash"]}, headers=h).json()["allowed"]
            assert c.post(f"/api/route/routes/{wf['id']}/bot", json={"connection": "NONE"}, headers=h).status_code == 400
            assert c.get(f"/api/route/routes/{wf['id']}/sending").status_code in (401, 403)
            ks = {k["key"] for k in c.get("/api/route/catalog", headers=h).json().get("kinds", [])}
            assert {"send_email", "send_telegram", "send_slack"} <= ks or not ks
    finally:
        _wipe(t)


def test_sending_on_the_page_by_clicking(bz, monkeypatch, mails):
    sync_api = pytest.importorskip("playwright.sync_api")
    from tests.test_v161_console_e2e import _free_port
    from tests.test_v161_stream import KEY
    monkeypatch.setenv("API_KEY", KEY)
    from app.config import get_settings
    get_settings.cache_clear()
    t = get_settings().tenant_id
    _wipe(t)
    _save(t, "page_send", MAIL)
    wf = D.get_workflow(t, name="page_send")
    import uvicorn
    from app import main
    port = _free_port()
    srv = uvicorn.Server(uvicorn.Config(main.app, host="127.0.0.1", port=port, log_level="warning"))
    th = threading.Thread(target=srv.run, daemon=True)
    th.start()
    for _ in range(1200):
        if srv.started:
            break
        time.sleep(0.05)
    try:
        pw = sync_api.sync_playwright().start()
        try:
            b = pw.chromium.launch(**({"executable_path": os.environ["HOOLA_CHROMIUM"]} if os.environ.get("HOOLA_CHROMIUM") else {}))
        except Exception as ex:      # noqa: BLE001
            pw.stop()
            pytest.skip(f"no Chromium for Playwright here: {str(ex)[:80]}")
        try:
            for w, hgt in ((1440, 1000), (390, 844)):
                SN.allow(t, D.get_workflow(t, wf_id=wf["id"]), "", on=False)
                c = b.new_context(viewport={"width": w, "height": hgt})
                c.add_init_script(f"localStorage.setItem('hoola.console.token', '{KEY}')")
                p = c.new_page()
                errs = []
                p.on("pageerror", lambda e: errs.append(str(e)))
                p.goto(f"http://127.0.0.1:{port}/console/route#/r/{wf['id']}")
                p.wait_for_selector("#edSend:not([hidden])")
                txt = p.inner_text("#edSend")
                assert "It sends nothing until you allow it" in txt and "{{vars.who}}" in txt
                p.click("#sendOk")
                assert p.inner_text("#sendOk") == "Yes, let it send these"
                p.click("#sendOk")
                p.wait_for_selector("#sendOff")
                assert "Sending is allowed" in p.inner_text("#edSend")
                assert SN.status(t, D.get_workflow(t, wf_id=wf["id"]))["allowed"]
                # the step's own panel
                p.click(".nd[data-node='mail']")
                p.wait_for_selector("#edPanel [data-k='d:via']")
                assert p.locator("#edPanel [data-k='d:to']").count() == 1 and "Allow sending" in p.inner_text("#edPanel")
                p.select_option("#edPanel [data-k='d:via']", "telegram")
                p.wait_for_selector("#edPanel [data-k='d:chat']")
                assert p.locator("#edPanel [data-k='d:connection']").count() == 1
                if os.environ.get("HOOLA_SHOTS"):
                    p.screenshot(path=os.path.join(os.environ["HOOLA_SHOTS"], f"send_{w}.png"), full_page=True)
                sw = p.evaluate("document.documentElement.scrollWidth")
                assert sw <= w + 1, f"no sideways scroll at {w}: {sw}"
                assert not errs, errs
                c.close()
            # the sign-ins page offers the chat apps
            c = b.new_context(viewport={"width": 1440, "height": 1000})
            c.add_init_script(f"localStorage.setItem('hoola.console.token', '{KEY}')")
            p = c.new_page()
            p.goto(f"http://127.0.0.1:{port}/console/route#/signins/telegram")
            p.wait_for_selector("#credForm")
            assert p.locator("#cr_token").count() == 1 and p.locator("#credForm [data-k='host']").count() == 0
            p.fill("#credForm [data-k='name']", "MY_BOT")
            p.fill("#cr_token", TG)
            p.click("#credForm button[type=submit]")
            p.wait_for_selector("text=MY_BOT")
            assert any(x["name"] == "MY_BOT" and x["kind"] == "telegram" for x in WS.credentials(t))
            c.close()
        finally:
            b.close()
            pw.stop()
    finally:
        srv.should_exit = True
        th.join(timeout=10)
        _wipe(t)


def test_version():
    from app.main import APP_VERSION
    assert tuple(int(x) for x in APP_VERSION.split(".")) >= (0, 999, 278)
