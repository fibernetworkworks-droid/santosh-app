"""v0.999.242 NEW TRIGGERS (R5 of the Hoola Route plan; owner: "GO R5"; built as 0.999.240).

A route can now start on an app event (new email / sheet row / form answer / calendar event / Drive file / feed item /
any app's list through a tool that only reads - the first look only notes what is there), from a Hoola form page, from a
Hoola chat page, when another route fails, when another route runs it, or as a tool AI apps call over MCP.
"""
import asyncio
import shutil
import time
from pathlib import Path

import pytest

from tests.test_bazar import bz  # noqa: F401  (fresh DB fixture)

from app.agent import dhara_tools as D
from app.agent.tools import HANDLERS, Ctx, ToolError
from app.route import triggers as TR


def _wipe(t):
    shutil.rmtree(Path("data") / "dhara" / t, ignore_errors=True)


def _run(c):
    return asyncio.run(c)


def _save(t, name, steps, **kw):
    return _run(D.dhara_save(Ctx(tenant_id=t, conversation_id=""), name=name, steps=steps, **kw))


ANSWER = [{"id": "reply", "type": "respond", "body": "Hello {{vars.form.name}}{{vars.message}}"}]


def test_every_trigger_kind_is_checked(bz):
    V = TR.validate
    assert V("event", {"app": "email", "search": "invoice"})["every_minutes"] == 15
    assert V("event", {"app": "rss", "url": "https://example.com/feed", "every_minutes": 30})["url"].startswith("https://")
    for bad in ({"app": "fax"}, {"app": "rss", "url": "ftp://x"}, {"app": "sheet_row"}, {"app": "email", "every_minutes": 1},
                {"app": "app", "tool": "email_draft"}, {"app": "app", "tool": "no_such_tool"}):
        with pytest.raises(ToolError):
            V("event", bad)
    assert TR.read_only("sheet_read", {}) and TR.read_only("composio_apps", {"action": "STRIPE_LIST_CHARGES"})
    assert not TR.read_only("composio_apps", {"action": "SLACK_SEND_MESSAGE"}) and not TR.read_only("email_bulk", {})
    f = V("form", {"title": "Book a call", "fields": [{"name": "name", "label": "Name", "required": True},
                                                      {"name": "size", "type": "select", "options": ["S", "M"]}]})
    assert f["fields"][1]["options"] == ["S", "M"] and f["button"] == "Send"
    for bad in ({}, {"fields": [{"name": "1x"}]}, {"fields": [{"name": "a", "type": "select"}]}, {"fields": [{"name": "a"}, {"name": "a"}]}):
        with pytest.raises(ToolError):
            V("form", bad)
    assert V("chat", {})["greeting"]
    assert V("error", {"routes": "Daily Sync, other"})["routes"] == ["daily_sync", "other"]
    assert V("route", {"inputs": ["order_id"]})["inputs"][0]["name"] == "order_id"
    with pytest.raises(ToolError):
        V("tool", {"inputs": []})                           # an AI app needs to know what it does
    assert V("tool", {"description": "Price a parcel", "inputs": [{"name": "kg", "type": "number", "required": True}]})["inputs"][0]["required"]
    with pytest.raises(ToolError):
        V("telepathy", {})


def test_app_event_first_look_notes_then_new_items_run(bz, monkeypatch):
    monkeypatch.setattr(D, "polite_s", 0)
    t = "r5_event"
    _wipe(t)
    feed = {"items": [{"id": 1, "title": "old one"}]}

    async def lister(ctx, **kw):
        return dict(feed)
    monkeypatch.setitem(HANDLERS, "route_test_list", lister)
    try:
        _save(t, "on_orders", [{"id": "note", "type": "set", "name": "got", "value": "{{vars.event.title}}"}], trigger="event",
              trigger_spec={"app": "app", "tool": "route_test_list", "every_minutes": 5})
        wf = D.get_workflow(t, name="on_orders")
        assert wf["next_due_at"] and wf["next_due_at"] - time.time() < 60
        first = _run(TR.poll(t, wf))
        assert first["first_look"] and first["noted"] == 1 and not D.list_runs(t, wf_id=wf["id"])
        feed["items"] = [{"id": 3, "title": "newest"}, {"id": 2, "title": "new"}, {"id": 1, "title": "old one"}]
        out = _run(TR.poll(t, wf))
        assert out["new"] == 2 and out["started"] == 2
        runs = D.list_runs(t, wf_id=wf["id"])
        assert len(runs) == 2
        assert _run(TR.poll(t, wf))["new"] == 0                       # never twice
        for r in runs:
            _run(D.execute_run(t, r["id"]))
        got = sorted(D.get_run(t, r["id"])["context"]["vars"]["got"] for r in runs)
        assert got == ["new", "newest"]
        D.set_enabled(t, wf["id"], False)
        D.set_enabled(t, wf["id"], True)                              # switched on again: fresh first look
        feed["items"].insert(0, {"id": 4, "title": "while off"})
        assert _run(TR.poll(t, wf)).get("first_look")
        st = TR.poll_state(t, wf["id"])
        assert st["looked"] and st["seen"] >= 4
        # a failing look is noted, never a crash
        async def broken(ctx, **kw):
            raise ToolError("Google is not connected")
        monkeypatch.setitem(HANDLERS, "route_test_list", broken)
        bad = _run(TR.poll(t, wf))
        assert bad["ok"] is False and "not connected" in TR.poll_state(t, wf["id"])["error"]
        # the tick finds due event routes and sets the next look
        D.update_run  # noqa: B018
        con = D._con(t)
        con.execute("UPDATE workflows SET next_due_at = ? WHERE id = ?", (time.time() - 1, wf["id"]))
        con.commit()
        con.close()
        due = TR.events_due(t)
        assert [w["id"] for w in due] == [wf["id"]] and D.get_workflow(t, wf_id=wf["id"])["next_due_at"] > time.time() + 200
    finally:
        _wipe(t)


def test_feed_items_are_read_from_rss_and_atom(bz):
    rss = """<?xml version="1.0"?><rss><channel><title>x</title><item><title>One</title><link>https://a/1</link><guid>g1</guid>
      <pubDate>Mon, 01 Jan 2029 10:00:00 GMT</pubDate><description>first</description></item><item><title>Two</title><guid>g2</guid></item></channel></rss>"""
    items = TR._rss_parse(rss)
    assert [i["title"] for i in items] == ["One", "Two"] and items[0]["guid"] == "g1" and items[0]["link"] == "https://a/1"
    atom = """<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>A</title><id>urn:1</id><link href="https://b/1"/><summary>s</summary></entry></feed>"""
    a = TR._rss_parse(atom)
    assert a == [{"title": "A", "guid": "urn:1", "link": "https://b/1", "description": "s"}]
    with pytest.raises(TR.TriggerError):
        TR._rss_parse('<?xml version="1.0"?><!DOCTYPE x [<!ENTITY e "boom">]><rss>&e;</rss>')
    assert TR.id_of({"guid": "g1"}) == "guid:g1"


def test_form_page_starts_the_route_and_shows_its_answer(bz, monkeypatch):
    monkeypatch.setattr(D, "polite_s", 0)
    from fastapi.testclient import TestClient
    from app.main import app
    from app.config import get_settings
    t = get_settings().tenant_id
    _wipe(t)
    try:
        out = _save(t, "contact_form", ANSWER, trigger="form",
                    trigger_spec={"title": "Contact us", "fields": [{"name": "name", "label": "Your name", "required": True},
                                                                   {"name": "email", "label": "Email", "type": "email"}]})
        path = out["address"].split("santosh.example.in")[-1]
        assert path.startswith("/route-form/")
        wf = D.get_workflow(t, name="contact_form")
        assert TR.public_address(t, wf).endswith(path)                 # kept to show again
        c = TestClient(app)
        page = c.get(path)
        assert page.status_code == 200 and "Contact us" in page.text and 'name="email"' in page.text
        assert "script-src 'self'" in page.headers["content-security-policy"]
        bad = c.post(path, data={"name": "", "email": "nope"})
        assert bad.status_code == 400 and "Fill in" in bad.text and "not an email" in bad.text
        ok = c.post(path, data={"name": "Ana", "email": "ana@example.com"})
        assert ok.status_code == 200 and "Hello Ana" in ok.text
        runs = D.list_runs(t, wf_id=wf["id"])
        assert len(runs) == 1
        assert D.get_run(t, runs[0]["id"])["context"]["vars"]["form"] == {"name": "Ana", "email": "ana@example.com"}
        robot = c.post(path, data={"name": "Bot", "_hp": "x"})
        assert robot.status_code == 200 and len(D.list_runs(t, wf_id=wf["id"])) == 1   # a robot starts nothing
        D.set_enabled(t, wf["id"], False)
        assert c.get(path).status_code == 404
        assert c.get("/route-form/nope").status_code == 404
    finally:
        _wipe(t)


def test_chat_page_replies_from_the_route_and_keeps_the_conversation(bz, monkeypatch):
    monkeypatch.setattr(D, "polite_s", 0)
    from fastapi.testclient import TestClient
    from app.main import app
    from app.config import get_settings
    t = get_settings().tenant_id
    _wipe(t)
    try:
        out = _save(t, "help_bot", [
            {"id": "count", "type": "set", "name": "n", "value": "{{ len(vars.history) }}"},
            {"id": "reply", "type": "respond", "body": {"reply": "You said {{vars.message}} ({{vars.n}} before)"}}], trigger="chat")
        path = out["address"].split("santosh.example.in")[-1]
        c = TestClient(app)
        page = c.get(path)
        assert page.status_code == 200 and "routechat.js" in page.text and "How can I help" in page.text
        api = "/api/route-chat/" + path.rsplit("/", 1)[1]
        r1 = c.post(api, json={"session": "s1", "text": "hello"}).json()
        assert r1["ok"] and r1["reply"] == "You said hello (0 before)"
        r2 = c.post(api, json={"session": "s1", "text": "again"}).json()
        assert r2["reply"] == "You said again (2 before)"            # her message + the reply
        assert c.post(api, json={"session": "s1", "text": ""}).status_code == 400
        assert (Path(__file__).resolve().parents[1] / "app" / "static" / "console" / "routechat.js").exists()
    finally:
        _wipe(t)


def test_a_route_runs_when_another_route_fails(bz, monkeypatch):
    monkeypatch.setattr(D, "polite_s", 0)
    t = "r5_err"
    _wipe(t)
    try:
        _save(t, "fix_it", [{"id": "n", "type": "set", "name": "seen", "value": "{{vars.failed_route}}: {{vars.error}}"}],
              trigger="error", trigger_spec={"routes": ["breaks"]})
        _save(t, "any_fail", [{"id": "n", "type": "set", "name": "seen", "value": 1}], trigger="error")
        _save(t, "breaks", [{"id": "s", "type": "stop", "as": "error", "message": "no stock"}])
        _run(D.execute_run(t, D.create_run(t, D.get_workflow(t, name="breaks"))))
        for name in ("fix_it", "any_fail"):
            runs = D.list_runs(t, wf_id=D.get_workflow(t, name=name)["id"])
            assert len(runs) == 1, name
        r = D.get_run(t, D.list_runs(t, wf_id=D.get_workflow(t, name="fix_it")["id"])[0]["id"])
        assert r["context"]["vars"]["failed_route"] == "breaks" and "no stock" in r["context"]["vars"]["error"]
        # a failing error route never starts error routes
        _save(t, "fix_it", [{"id": "s", "type": "stop", "as": "error", "message": "x"}], trigger="error", trigger_spec={"routes": ["breaks"]})
        before = len(D.list_runs(t, wf_id=D.get_workflow(t, name="any_fail")["id"]))
        _run(D.execute_run(t, D.create_run(t, D.get_workflow(t, name="fix_it"))))
        assert len(D.list_runs(t, wf_id=D.get_workflow(t, name="any_fail")["id"])) == before
    finally:
        _wipe(t)


def test_routes_are_tools_for_ai_apps_over_mcp(bz, monkeypatch):
    monkeypatch.setattr(D, "polite_s", 0)
    from fastapi.testclient import TestClient
    from app.main import app
    from app.config import get_settings
    t = get_settings().tenant_id
    _wipe(t)
    try:
        _save(t, "parcel_price", [{"id": "p", "type": "set", "name": "price", "value": "{{ vars.kg * 4 }}"},
                                  {"id": "a", "type": "respond", "body": {"price": "{{vars.price}}"}}], trigger="tool",
              trigger_spec={"description": "Price a parcel by weight", "inputs": [{"name": "kg", "type": "number", "required": True}]})
        _save(t, "not_a_tool", [{"id": "p", "type": "set", "name": "x", "value": 1}])
        key = TR.mcp_key(t)
        assert TR.mcp_state(t)["made"]
        c = TestClient(app)
        url = key["path"]
        rpc = lambda m, p=None, i=1: c.post(url, json={"jsonrpc": "2.0", "id": i, "method": m, "params": p or {}})  # noqa: E731
        init = rpc("initialize", {"protocolVersion": "2025-06-18"}).json()
        assert init["result"]["protocolVersion"] == "2025-06-18" and "tools" in init["result"]["capabilities"]
        assert c.post(url, json={"jsonrpc": "2.0", "method": "notifications/initialized"}).status_code == 202
        tools = rpc("tools/list").json()["result"]["tools"]
        assert [x["name"] for x in tools] == ["parcel_price"]
        assert tools[0]["inputSchema"]["required"] == ["kg"] and tools[0]["inputSchema"]["properties"]["kg"]["type"] == "number"
        res = rpc("tools/call", {"name": "parcel_price", "arguments": {"kg": 3}}).json()["result"]
        assert not res.get("isError") and '"price": 12' in res["content"][0]["text"]
        miss = rpc("tools/call", {"name": "parcel_price", "arguments": {}}).json()["result"]
        assert miss["isError"] and "kg" in miss["content"][0]["text"]
        assert "error" in rpc("tools/call", {"name": "not_a_tool"}).json()
        assert c.post("/mcp/route/rmcp_wrong", json={"jsonrpc": "2.0", "id": 1, "method": "ping"}).status_code == 401
        TR.mcp_key(t)                                                   # a new address: the old one stops
        assert rpc("ping").status_code == 401
    finally:
        _wipe(t)


def test_the_editor_saves_every_trigger_and_the_page_knows_them(bz):
    from fastapi.testclient import TestClient
    from app.main import app
    from app.config import get_settings
    t = get_settings().tenant_id
    _wipe(t)
    try:
        c = TestClient(app)
        r = c.post("/api/route/routes", json={"title": "Triggers"}).json()
        for kind, spec in (("event", {"app": "rss", "url": "https://example.com/feed"}), ("form", {"fields": [{"name": "q"}]}),
                           ("chat", {}), ("error", {"routes": []}), ("route", {"inputs": [{"name": "id"}]}),
                           ("tool", {"description": "Does a thing"}), ("schedule", {"at": ["09:00"]}), ("manual", {})):
            got = c.put(f"/api/route/routes/{r['id']}/graph", json={"steps": r["graph"], "trigger": kind, "trigger_spec": spec})
            assert got.status_code == 200, (kind, got.text)
            r = got.json()
            assert r["trigger"] == kind
        bad = c.put(f"/api/route/routes/{r['id']}/graph", json={"steps": r["graph"], "trigger": "tool", "trigger_spec": {}})
        assert bad.status_code == 400
        cat = c.get("/api/route/triggers").json()
        assert {e["key"] for e in cat["events"]} == set(TR.EVENTS) and "select" in cat["form_types"]
        js = (Path(__file__).resolve().parents[1] / "app" / "static" / "console" / "route.js").read_text()
        for part in ("TKINDS", "When something happens in an app", "From a form", "From a chat", "When a route fails",
                     "As a tool for AI apps", "/api/route/mcp", "Look now", "rowsEditor"):
            assert part in js, part
    finally:
        _wipe(t)


# ---------------------------------------------------------------- a real browser
@pytest.fixture
def br5(bz, monkeypatch):
    import os
    import threading
    sync_api = pytest.importorskip("playwright.sync_api")
    from tests.test_v161_console_e2e import _free_port
    from tests.test_v161_stream import KEY
    monkeypatch.setenv("API_KEY", KEY)
    monkeypatch.setattr(D, "polite_s", 0)
    from app.config import get_settings
    get_settings.cache_clear()
    t = get_settings().tenant_id
    _wipe(t)
    _save(t, "ask_form", ANSWER)
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
        yield f"http://127.0.0.1:{port}", b, KEY, t
        b.close()
        pw.stop()
    finally:
        srv.should_exit = True
        th.join(timeout=10)
        _wipe(t)


def test_make_a_form_route_in_a_real_browser(br5):
    base, b, key, t = br5
    wf = D.get_workflow(t, name="ask_form")
    c = b.new_context(viewport={"width": 1440, "height": 900})
    c.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    p = c.new_page()
    errs = []
    p.on("pageerror", lambda e: errs.append(str(e)))
    p.goto(base + "/console/route#/r/" + wf["id"])
    p.wait_for_selector(".nd[data-node='trigger']")
    p.click(".nd[data-node='trigger']")
    p.wait_for_selector("#edPanel [data-tk='form']")
    p.click("#edPanel [data-tk='event']")
    p.wait_for_selector("#edPanel [data-k='tg:app']")
    p.select_option("#edPanel [data-k='tg:app']", "rss")
    p.wait_for_selector("#edPanel [data-k='tg:url']")
    p.click("#edPanel [data-tk='form']")
    p.wait_for_selector("#edPanel [data-radd='fields']")
    p.fill("#edPanel [data-k='tg:title']", "Ask us")
    p.press("#edPanel [data-k='tg:title']", "Tab")
    p.click("#edSave")
    p.wait_for_function("() => document.querySelector('#edState').innerText === 'Saved'", timeout=10000)
    w = D.get_workflow(t, wf_id=wf["id"])
    assert w["trigger_kind"] == "form" and w["trigger_spec"]["title"] == "Ask us" and len(w["trigger_spec"]["fields"]) == 3
    p.wait_for_selector("#edPanel #addrNew")
    p.click("#edPanel #addrNew")
    p.wait_for_selector("#edPanel #addrBox code.addr")
    url = p.inner_text("#edPanel #addrBox code.addr")
    assert "/route-form/" in url
    f = c.new_page()
    f.goto(base + "/route-form/" + url.rsplit("/", 1)[1])
    f.fill("input[name='name']", "Ana")
    f.fill("input[name='email']", "ana@example.com")
    f.click("button[type='submit']")
    f.wait_for_selector(".done")
    assert "Hello Ana" in f.inner_text(".done")
    assert "From a form" in p.inner_text("#world")
    assert not errs, errs


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION >= "0.999.242"
