"""v0.999.246 ACCOUNTS, VARIABLES, SETTINGS, VERSIONS, SHARING (R7 of the Hoola Route plan; owner: "GO R7").

Variables every route reads as {{env.NAME}}; saved sign-ins for web requests (sealed, shown only as the last 4, never sent to
another site); which account a step uses; every route setting on the page (tags too); a version kept at every save and any
version brought back; a read-only link to look at a route; team members who may run a route (never change it); routes as
files in and out.
"""
import asyncio
import json
import shutil
from pathlib import Path

import pytest

from tests.test_bazar import bz  # noqa: F401  (fresh DB fixture)

from app.agent import dhara_tools as D
from app.agent.tools import Ctx, ToolError
from app.route import workspace as WS


def _wipe(t):
    shutil.rmtree(Path("data") / "dhara" / t, ignore_errors=True)


def _run(c):
    return asyncio.run(c)


def _save(t, name, steps, **kw):
    return _run(D.dhara_save(Ctx(tenant_id=t, conversation_id=""), name=name, steps=steps, **kw))


def test_variables_are_read_as_env(bz, monkeypatch):
    monkeypatch.setattr(D, "polite_s", 0)
    t = "r7_vars"
    _wipe(t)
    try:
        WS.set_variable(t, "SHOP_NAME", "Asha Bakes")
        WS.set_variable(t, "VAT", 20)
        with pytest.raises(WS.WorkspaceError):
            WS.set_variable(t, "bad name", 1)
        with pytest.raises(WS.WorkspaceError):
            WS.set_variable(t, "KEY", "sk_live_abcdefghijklmnop")          # a key is a sign-in, never a variable
        _save(t, "uses_env", [{"id": "a", "type": "set", "name": "line", "value": "{{env.SHOP_NAME}} adds {{ env.VAT * 2 }}%"}])
        rid = D.create_run(t, D.get_workflow(t, name="uses_env"))
        _run(D.execute_run(t, rid))
        assert D.get_run(t, rid)["context"]["vars"]["line"] == "Asha Bakes adds 40%"
        assert [v["name"] for v in WS.variables(t)] == ["SHOP_NAME", "VAT"]
        WS.drop_variable(t, "VAT")
        assert WS.env(t) == {"SHOP_NAME": "Asha Bakes"}
    finally:
        _wipe(t)


def test_sign_ins_are_sealed_and_only_go_to_their_site(bz):
    t = "r7_creds"
    _wipe(t)
    try:
        out = WS.save_credential(t, {"name": "SHOP_API", "kind": "bearer", "host": "https://api.shop.example/v1", "token": "tok_1234567890wxyz"})
        assert out == {"name": "SHOP_API", "kind": "bearer", "host": "api.shop.example", "hint": "••••wxyz"}
        listed = WS.credentials(t)
        assert listed[0]["hint"] == "••••wxyz" and "tok_1234567890wxyz" not in json.dumps(listed)
        con = WS._con(t)
        raw = con.execute("SELECT sealed FROM route_creds").fetchone()[0]
        con.close()
        assert "tok_1234567890wxyz" not in raw                                   # sealed at rest
        url, h = WS.apply_auth(t, "SHOP_API", "https://api.shop.example/orders", {})
        assert h["Authorization"] == "Bearer tok_1234567890wxyz"
        url, h = WS.apply_auth(t, "SHOP_API", "https://eu.api.shop.example/x", {})   # a subdomain of its site is fine
        with pytest.raises(WS.WorkspaceError):
            WS.apply_auth(t, "SHOP_API", "https://evil.example/steal", {})       # never another site
        WS.save_credential(t, {"name": "Q", "kind": "query", "host": "maps.example.com", "param": "key", "value": "k123"})
        assert WS.apply_auth(t, "Q", "https://maps.example.com/a?x=1", {})[0] == "https://maps.example.com/a?x=1&key=k123"
        WS.save_credential(t, {"name": "B", "kind": "basic", "host": "x.example.com", "user": "ana", "password": "pw"})
        assert WS.apply_auth(t, "B", "https://x.example.com", {})[1]["Authorization"].startswith("Basic ")
        WS.save_credential(t, {"name": "H", "kind": "header", "host": "x.example.com", "header": "X-Api-Key", "value": "v"})
        assert WS.apply_auth(t, "H", "https://x.example.com", {"A": "1"})[1] == {"A": "1", "X-Api-Key": "v"}
        for bad in ({"name": "N", "kind": "bearer", "host": "x.example.com"}, {"name": "N", "kind": "spell", "host": "x.example.com"},
                    {"name": "N", "kind": "bearer", "host": "not a site", "token": "t"}):
            with pytest.raises(WS.WorkspaceError):
                WS.save_credential(t, bad)
        with pytest.raises(WS.WorkspaceError):
            WS.apply_auth(t, "NOPE", "https://x.example.com", {})
        with pytest.raises(ToolError):
            D.validate_steps([{"id": "h", "type": "http", "url": "https://x.example.com", "auth": "bad name!"}])
    finally:
        _wipe(t)


def test_a_web_request_signs_in_with_a_saved_sign_in(bz, monkeypatch):
    monkeypatch.setattr(D, "polite_s", 0)
    import httpx
    from app.agent import scrape_tools as st
    t = "r7_http"
    _wipe(t)
    seen = {}

    def fake_get(url, headers=None, **kw):
        seen["url"], seen["headers"] = url, headers
        return httpx.Response(200, json={"ok": True}, request=httpx.Request("GET", url))
    monkeypatch.setattr(httpx, "get", fake_get)
    monkeypatch.setattr(st, "_guard_url", lambda u: u)
    try:
        WS.save_credential(t, {"name": "SHOP_API", "kind": "bearer", "host": "api.shop.example", "token": "tok_secret_abcd"})
        _save(t, "calls_api", [{"id": "get", "type": "http", "url": "https://api.shop.example/orders", "auth": "SHOP_API"}])
        rid = D.create_run(t, D.get_workflow(t, name="calls_api"))
        _run(D.execute_run(t, rid))
        r = D.get_run(t, rid)
        assert r["status"] == "done", r.get("error")
        assert seen["headers"]["Authorization"] == "Bearer tok_secret_abcd"
        assert "tok_secret_abcd" not in json.dumps(r)                            # never in the run
        _save(t, "leaks", [{"id": "get", "type": "http", "url": "https://other.example/x", "auth": "SHOP_API"}])
        rid = D.create_run(t, D.get_workflow(t, name="leaks"))
        _run(D.execute_run(t, rid))
        r = D.get_run(t, rid)
        assert r["status"] == "failed" and "only for api.shop.example" in r["error"]
    finally:
        _wipe(t)


def test_versions_are_kept_and_brought_back(bz):
    from fastapi.testclient import TestClient
    from app.main import app
    from app.config import get_settings
    t = get_settings().tenant_id
    _wipe(t)
    try:
        c = TestClient(app)
        r = c.post("/api/route/routes", json={"title": "Versioned"}).json()
        one = [{"id": "a", "type": "set", "name": "x", "value": 1}]
        two = one + [{"id": "b", "type": "notify", "text": "hi"}]
        c.put(f"/api/route/routes/{r['id']}/graph", json={"steps": one})
        r = c.put(f"/api/route/routes/{r['id']}/graph", json={"steps": two}).json()
        c.put(f"/api/route/routes/{r['id']}/graph", json={"steps": two})            # nothing changed: no new version
        vs = c.get(f"/api/route/routes/{r['id']}/versions").json()["versions"]
        assert len(vs) == 3 and vs[0]["current"] and vs[0]["change"] == "added b" and vs[-1]["change"] == "The first saved version"
        back = c.post(f"/api/route/routes/{r['id']}/versions/{vs[1]['id']}/restore").json()
        assert [s["id"] for s in back["graph"]] == ["a"]
        vs2 = c.get(f"/api/route/routes/{r['id']}/versions").json()["versions"]
        assert len(vs2) == 4 and "Brought back" in vs2[0]["note"] and vs2[0]["change"] == "removed b"
        assert c.post(f"/api/route/routes/{r['id']}/versions/rv_nope/restore").status_code == 400
    finally:
        _wipe(t)


def test_every_setting_from_the_page_and_tags(bz):
    from fastapi.testclient import TestClient
    from app.main import app
    from app.config import get_settings
    t = get_settings().tenant_id
    _wipe(t)
    try:
        c = TestClient(app)
        other = c.post("/api/route/routes", json={"title": "Handle errors"}).json()
        r = c.post("/api/route/routes", json={"title": "Daily"}).json()
        out = c.put(f"/api/route/routes/{r['id']}/settings", json={
            "description": "Every morning", "folder": "Sales", "tags": ["Orders", "daily", "orders"], "timezone": "Europe/Berlin",
            "stop_after_errors": 3, "runs_per_day": 50, "error_route": other["name"], "currency": "eur"}).json()
        st = out["settings"]
        assert st == {"folder": "Sales", "timezone": "Europe/Berlin", "stop_after_errors": 3, "runs_per_day": 50,
                      "error_route": other["name"], "currency": "EUR", "tags": ["orders", "daily"]}
        assert out["description"] == "Every morning" and out["tags"] == ["orders", "daily"]
        assert c.put(f"/api/route/routes/{r['id']}/settings", json={"error_route": r["name"]}).status_code == 400
        assert c.put(f"/api/route/routes/{r['id']}/settings", json={"timezone": "Mars/Base"}).status_code == 400
        assert c.put(f"/api/route/routes/{r['id']}/settings", json={"shared_with": ["tm_nobody"]}).status_code == 400
        js = (Path(__file__).resolve().parents[1] / "app" / "static" / "console" / "route.js").read_text()
        for part in ("Save settings", "versionsTab", "viewVariables", "viewSignins", "Sign in with", "Which account", "Bring in a file",
                     "Download as a file", "Team members who may run it", "Make a link"):
            assert part in js, part
        html = (Path(__file__).resolve().parents[1] / "app" / "static" / "console" / "route.html").read_text()
        assert "#/variables" in html and "#/signins" in html
    finally:
        _wipe(t)


def test_share_link_shows_the_steps_without_data(bz):
    from fastapi.testclient import TestClient
    from app.main import app
    from app.config import get_settings
    t = get_settings().tenant_id
    _wipe(t)
    try:
        _save(t, "secret_ops", [{"id": "mail", "type": "tool", "name": "email_check", "label": "Read new orders",
                                 "args": {"search": "from:boss@private.example"}},
                                {"id": "ok", "type": "condition", "left": "1", "op": "eq", "right": "1",
                                 "then": [{"id": "say", "type": "notify", "text": "PRIVATE TEXT 123"}]}])
        wf = D.get_workflow(t, name="secret_ops")
        sh = WS.share_make(t, wf["id"])
        assert sh["on"] and "/route-view/" in sh["url"]
        c = TestClient(app)
        page = c.get("/route-view/" + sh["url"].rsplit("/", 1)[1])
        assert page.status_code == 200 and "Read new orders" in page.text and "If yes" in page.text
        assert "boss@private.example" not in page.text and "PRIVATE TEXT" not in page.text
        WS.share_stop(t, wf["id"])
        assert c.get("/route-view/" + sh["url"].rsplit("/", 1)[1]).status_code == 404
    finally:
        _wipe(t)


def test_team_members_run_shared_routes_and_never_change_them(bz, monkeypatch):
    monkeypatch.setattr(D, "polite_s", 0)
    t = "r7_team"
    _wipe(t)
    try:
        _save(t, "restock", [{"id": "a", "type": "set", "name": "x", "value": 1}])
        _save(t, "payroll", [{"id": "a", "type": "set", "name": "x", "value": 1}])
        wf = D.get_workflow(t, name="restock")
        con = D._con(t)
        con.execute("UPDATE workflows SET settings = ? WHERE id = ?", (json.dumps({"shared_with": ["tm_ravi"]}), wf["id"]))
        con.commit()
        con.close()
        staff = Ctx(tenant_id=t, conversation_id="", actor="staff:tm_ravi")
        out = _run(D.dhara_run(staff, name="restock"))
        assert out["status"] == "queued"
        with pytest.raises(ToolError):
            _run(D.dhara_run(staff, name="payroll"))                            # not shared with him
        with pytest.raises(ToolError):
            _run(D.dhara_save(staff, name="restock", steps=[{"id": "a", "type": "set", "name": "x", "value": 2}]))
        with pytest.raises(ToolError):
            _run(D.dhara_control(staff, action="disable", name="restock"))
        with pytest.raises(ToolError):
            _run(D.dhara_run(Ctx(tenant_id=t, conversation_id="", actor="staff:tm_other"), name="restock"))
        _run(D.drain())
    finally:
        _wipe(t)


def test_routes_go_out_and_come_in_as_files(bz):
    from fastapi.testclient import TestClient
    from app.main import app
    from app.config import get_settings
    t = get_settings().tenant_id
    _wipe(t)
    try:
        c = TestClient(app)
        r = c.post("/api/route/routes", json={"title": "Copy me"}).json()
        dsl = c.get(f"/api/route/routes/{r['id']}/export").json()
        assert dsl["name"] == r["name"]
        out = c.post("/api/route/import", json={"dsl": dsl, "new_name": "copy_me_2"}).json()
        assert out["ok"] and D.get_workflow(t, name="copy_me_2")["enabled"] == 0      # lands off
        assert c.post("/api/route/import", json={"dsl": dsl}).status_code == 409     # the name is taken
    finally:
        _wipe(t)


def test_accounts_list_her_mailboxes(bz):
    from app.db import MailAccount, session
    from app.config import get_settings
    t = get_settings().tenant_id
    with session() as s:
        s.add(MailAccount(tenant_id=t, kind="gmail", address="shop@example.com", is_default=True))
    acc = WS.accounts(t)
    assert {"value": "shop@example.com", "label": "shop@example.com", "kind": "gmail", "default": True, "ok": True} in acc


# ---------------------------------------------------------------- a real browser
@pytest.fixture
def br7(bz, monkeypatch):
    import os
    import threading
    import time
    sync_api = pytest.importorskip("playwright.sync_api")
    from tests.test_v161_console_e2e import _free_port
    from tests.test_v161_stream import KEY
    monkeypatch.setenv("API_KEY", KEY)
    from app.config import get_settings
    get_settings.cache_clear()
    t = get_settings().tenant_id
    _wipe(t)
    _save(t, "page_route", [{"id": "a", "type": "set", "name": "x", "value": 1}])
    _save(t, "page_route", [{"id": "a", "type": "set", "name": "x", "value": 2}])
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
        yield f"http://127.0.0.1:{port}/console/route", b, KEY, t
        b.close()
        pw.stop()
    finally:
        srv.should_exit = True
        th.join(timeout=10)
        _wipe(t)


def test_settings_versions_variables_and_sign_ins_in_a_real_browser(br7):
    base, b, key, t = br7
    wf = D.get_workflow(t, name="page_route")
    c = b.new_context(viewport={"width": 1440, "height": 900})
    c.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    p = c.new_page()
    errs = []
    p.on("pageerror", lambda e: errs.append(str(e)))
    p.goto(base + "#/r/" + wf["id"] + "/settings")
    p.wait_for_selector("#setForm [data-k='tags']")
    p.fill("#setForm [data-k='tags']", "orders, daily")
    p.fill("#setForm [data-k='folder']", "Sales")
    p.click("#setSave")
    p.wait_for_function("() => document.querySelector('#toast') && document.querySelector('#toast').innerText.includes('Settings saved')", timeout=10000)
    st = D.get_workflow(t, wf_id=wf["id"])["settings"]
    assert st["tags"] == ["orders", "daily"] and st["folder"] == "Sales"
    p.click("#shareMake")
    p.wait_for_selector("#shareBox code.addr")
    assert "/route-view/" in p.inner_text("#shareBox code.addr")
    p.goto(base + "#/routes")
    p.wait_for_selector(".rtag")
    assert "orders" in p.inner_text("#rtable")
    p.goto(base + "#/r/" + wf["id"] + "/versions")
    p.wait_for_selector("[data-restore]")
    p.locator("[data-restore]").last.click()            # the oldest: the first version, value 1
    p.locator("[data-restore]").last.click()
    p.wait_for_function("() => document.querySelector('#toast').innerText.includes('Brought back')", timeout=10000)
    back = D.get_workflow(t, wf_id=wf["id"])
    assert back["steps"][0]["value"] == 1 and not back["settings"].get("tags")   # its settings come back with it
    p.goto(base + "#/variables")
    p.wait_for_selector("#varForm")
    p.fill("[data-k='vname']", "SHOP_NAME")
    p.fill("[data-k='vvalue']", "Asha Bakes")
    p.click("#varForm button[type='submit']")
    p.wait_for_selector("text=SHOP_NAME")
    assert WS.env(t)["SHOP_NAME"] == "Asha Bakes"
    p.goto(base + "#/signins")
    p.wait_for_selector("#credForm")
    p.fill("#credForm [data-k='name']", "SHOP_API")
    p.fill("#credForm [data-k='host']", "api.shop.example")
    p.fill("#credForm [data-k='token']", "tok_abcdef123456")
    p.click("#credForm button[type='submit']")
    p.wait_for_selector("text=••••3456")
    assert "tok_abcdef123456" not in p.content()
    assert not errs, errs


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION >= "0.999.246"
