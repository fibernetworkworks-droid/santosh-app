"""v0.999.122 ROUTE CHECK - every Hoola Route page walked in a real browser (computer + phone, light + dark) and the
engine behind it read end to end (owner: "CHECK EVERY SECTION ... DESIGN AND MISPLACED TEXT, BUTTON ... FLAWS ...
BACKEND FUNCTIONING MISSED ... FIX").

Backend faults found and fixed, each pinned here:
  - a code step whose Python failed counted as DONE (the run said done, the route said Working);
  - a web request answered 4xx / 5xx counted as DONE;
  - the Runs page filtered by state AFTER the 60-row limit, so older failed / waiting runs vanished;
  - Approve / Retry / Stop showed success even when the engine said "not done" (expired approval, not waiting);
  - Needs you showed the question of the LAST approval step, not the one the run waits on;
  - a failure stayed in Needs you after a later good run;
  - a route that never ran said "Working";
  - a webhook route never showed the address that starts it; a route could not be deleted.
Page faults: tables cut on a phone, if / else and loop steps not drawn, raw JSON for a step, the browser's prompt()
for "Change it", a squeezed header, a cramped phone sidebar, meaningless KPI bars.
"""
import asyncio
import os
import shutil
import threading
import time
from pathlib import Path

import pytest

from tests.test_bazar import bz  # noqa: F401  (fresh DB fixture)

from app.agent import dhara_tools as D
from app.agent.tools import Ctx

T = "route-check-tenant"
CTX = Ctx(tenant_id=T, conversation_id="")
BASE = Path(__file__).resolve().parents[1] / "app" / "static" / "console"


def _wipe(t):
    shutil.rmtree(Path("data") / "dhara" / t, ignore_errors=True)


@pytest.fixture(autouse=True)
def _clean(monkeypatch):
    monkeypatch.setattr(D, "polite_s", 0)
    D._RUNNING.clear()
    _wipe(T)
    yield
    D._RUNNING.clear()
    _wipe(T)


def _run(c):
    return asyncio.run(c)


def _go(t, name, steps, **kw):
    ctx = Ctx(tenant_id=t, conversation_id="")
    wf = _run(D.dhara_save(ctx, name=name, steps=steps, **kw))
    w = D.get_workflow(t, wf_id=wf["workflow_id"])
    rid = D.create_run(t, w)
    _run(D.execute_run(t, rid))
    return D.get_run(t, rid)


def _client():
    from fastapi.testclient import TestClient
    from app.main import app
    from app.config import get_settings
    return TestClient(app), get_settings().tenant_id


# ---------------------------------------------------------------- engine: honest step results

def test_a_failing_code_step_fails_the_run(bz):
    r = _go(T, "bad_code", [{"id": "boom", "type": "code", "code": "raise ValueError('row 14 has no total')"}])
    assert r["status"] == "failed", "a Python error used to end the run as done"
    assert "row 14 has no total" in (r["error"] or "")
    ok = _go(T, "good_code", [{"id": "fine", "type": "code", "code": "print(2 + 2)"}])
    assert ok["status"] == "done"


def test_a_refused_web_request_fails_the_step(bz, monkeypatch):
    async def fake(tenant, step, ctx):
        return {"status": 503, "json": None, "text": "down"}
    monkeypatch.setattr(D, "_http_step", fake)
    r = _go(T, "web_down", [{"id": "call", "type": "http", "method": "GET", "url": "https://example.com/x"}])
    assert r["status"] == "failed" and "503" in (r["error"] or "")

    async def good(tenant, step, ctx):
        return {"status": 200, "json": {"a": 1}, "text": None}
    monkeypatch.setattr(D, "_http_step", good)
    assert _go(T, "web_up", [{"id": "call", "type": "http", "method": "GET", "url": "https://example.com/x"}])["status"] == "done"


def test_runs_filter_in_the_database_not_after_the_limit(bz):
    bad = _go(T, "old_bad", [{"id": "boom", "type": "code", "code": "raise ValueError('x')"}])
    w = D.get_workflow(T, name="old_bad")
    good = _run(D.dhara_save(CTX, name="many_good", steps=[{"id": "s", "type": "set", "name": "a", "value": 1}]))
    g = D.get_workflow(T, wf_id=good["workflow_id"])
    for _ in range(5):
        _run(D.execute_run(T, D.create_run(T, g)))
    assert bad["id"] not in [x["id"] for x in D.list_runs(T, limit=3)], "the failure is older than the newest 3"
    got = D.list_runs(T, limit=3, status="failed")
    assert [x["id"] for x in got] == [bad["id"]] and got[0]["workflow_id"] == w["id"]


# ---------------------------------------------------------------- the page API

def test_api_status_needs_actions_address_and_delete(bz):
    c, t = _client()
    _wipe(t)
    try:
        ctx = Ctx(tenant_id=t, conversation_id="")
        # never ran: not "Working"
        _run(D.dhara_save(ctx, name="hook_route", steps=[{"id": "n", "type": "notify", "text": "New lead"}], trigger="webhook"))
        _run(D.dhara_save(ctx, name="hand_route", steps=[{"id": "n", "type": "notify", "text": "Hi"}]))
        cards = {r["name"]: r for r in c.get("/api/route/routes").json()["routes"]}
        assert cards["hook_route"]["status"]["text"] == "Waiting for data"
        assert cards["hand_route"]["status"]["text"] == "Not run yet"
        # the question of the approval the run WAITS on, not the last one in the route
        r = _go(t, "two_gates", [{"id": "a1", "type": "approval", "question": "First: send the quote?"},
                                 {"id": "a2", "type": "approval", "question": "Second: send the invoice?"}])
        assert r["status"] == "waiting_approval"
        needs = c.get("/api/route/summary").json()["needs_you"]
        q = [n["text"] for n in needs if n["kind"] == "approval"]
        assert q == ["First: send the quote?"]
        # actions: success only when it really happened; a run that is not waiting says so (409)
        assert c.post(f"/api/route/runs/{r['id']}/approve").json()["status"] == "queued"
        for _ in range(100):
            if D.get_run(t, r["id"])["status"] != "queued":
                break
            time.sleep(0.03)
        _run(D.execute_run(t, r["id"])) if D.get_run(t, r["id"])["status"] == "queued" else None
        again = c.post(f"/api/route/runs/{r['id']}/retry")
        assert again.status_code == 409 and "retry" in again.json()["detail"]
        # a failure leaves Needs you once a later run of the same route went well
        bad = _go(t, "flaky", [{"id": "boom", "type": "code", "code": "raise ValueError('nope')"}])
        assert any(n.get("run_id") == bad["id"] for n in c.get("/api/route/summary").json()["needs_you"])
        _run(D.dhara_save(ctx, name="flaky", steps=[{"id": "fine", "type": "set", "name": "a", "value": 1}]))
        _run(D.execute_run(t, D.create_run(t, D.get_workflow(t, name="flaky"))))
        assert not any(n.get("run_id") == bad["id"] for n in c.get("/api/route/summary").json()["needs_you"])
        # the webhook address: made new, shown once, only for a webhook route; the old one stops working
        hook = D.get_workflow(t, name="hook_route")
        a = c.post(f"/api/route/routes/{hook['id']}/address").json()
        assert a["path"].startswith("/api/dhara/hook/") and "old address" in a["note"]
        tok = a["path"].rsplit("/", 1)[1]
        assert D.webhook_enqueue(tok, {"name": "Ana"})["ok"] is True
        b = c.post(f"/api/route/routes/{hook['id']}/address").json()
        assert D.webhook_enqueue(tok, {})["ok"] is False and b["path"] != a["path"]
        assert c.post(f"/api/route/routes/{D.get_workflow(t, name='hand_route')['id']}/address").status_code == 400
        # delete: needs the route's name, refuses while a run is going, then removes the route and its runs
        hand = D.get_workflow(t, name="hand_route")
        assert c.request("DELETE", f"/api/route/routes/{hand['id']}", json={"confirm": "wrong"}).status_code == 400
        gate = D.get_workflow(t, name="two_gates")
        rid = D.create_run(t, gate)
        _run(D.execute_run(t, rid))
        assert c.request("DELETE", f"/api/route/routes/{gate['id']}", json={"confirm": "two_gates"}).status_code == 409
        d = c.request("DELETE", f"/api/route/routes/{hand['id']}", json={"confirm": "hand_route"})
        assert d.status_code == 200 and D.get_workflow(t, wf_id=hand["id"]) is None
        assert c.get(f"/api/route/routes/{hand['id']}").status_code == 404
    finally:
        _wipe(t)


def test_page_source_carries_the_fixes():
    js = (BASE / "route.js").read_text()
    css = (BASE / "route.css").read_text()
    assert "prompt(" not in js and "confirm(" not in js, "no browser dialogs - in-page boxes only"
    assert "s.type === 'condition'" in js and "s.type === 'loop'" in js, "if / else and loop contents are drawn"
    assert 'data-l="Runs when"' in js and "table.rt td[data-l]::before" in css, "tables become cards on a phone"
    assert "/address`" in js and "'DELETE'" in js and "Switch back on" in js
    assert ".lane{flex-direction:column" in css, "the flow reads top to bottom on a phone"
    assert ".tog::before" in css, "a bigger tap area for the switch"
    assert "JSON.stringify(rest, null, 2)" not in js, "step details in plain rows, not a JSON dump"


# ---------------------------------------------------------------- a real browser: phone + computer

@pytest.fixture
def br(bz, monkeypatch):
    sync_api = pytest.importorskip("playwright.sync_api")
    from tests.test_v161_console_e2e import _free_port
    from tests.test_v161_stream import KEY
    monkeypatch.setenv("API_KEY", KEY)
    from app.config import get_settings
    get_settings.cache_clear()
    t = get_settings().tenant_id
    _wipe(t)
    ctx = Ctx(tenant_id=t, conversation_id="")
    _run(D.dhara_save(ctx, name="invoice_chase_for_every_customer_with_an_open_balance", settings={"folder": "Accounts"},
                      steps=[{"id": "check", "type": "condition", "filter": {"left": "{{vars.x}}", "op": "exists"},
                              "then": [{"id": "t1", "type": "notify", "text": "Has value"}],
                              "else": [{"id": "e1", "type": "notify", "text": "No value"}]},
                             {"id": "each", "type": "loop", "items": "{{vars.list}}",
                              "body": [{"id": "b1", "type": "set", "name": "n", "value": "{{item}}"}]}]))
    _run(D.dhara_save(ctx, name="lead_hook", steps=[{"id": "n", "type": "notify", "text": "New lead"}], trigger="webhook"))
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


def test_every_page_fits_a_phone_and_the_new_parts_work(br):
    base, b, key, t = br
    errors = []
    inv = D.get_workflow(t, name="invoice_chase_for_every_customer_with_an_open_balance")
    hook = D.get_workflow(t, name="lead_hook")
    c = b.new_context(viewport={"width": 390, "height": 860})
    c.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    p = c.new_page()
    p.on("pageerror", lambda e: errors.append(str(e)))
    for h in ("", "#/routes", "#/r/" + inv["id"], "#/r/" + hook["id"], "#/runs", "#/templates"):
        p.goto(base + h)
        p.wait_for_function("() => !document.querySelector('#main').innerText.includes('Opening Hoola Route')", timeout=20000)
        time.sleep(0.4)
        over = p.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
        assert over <= 1, f"{h or 'home'} scrolls sideways by {over}px on a phone"
    # the route: both ways of the if / else and the loop body are drawn, top to bottom
    p.goto(base + "#/r/" + inv["id"])
    p.wait_for_selector(".flow .node")
    flow = p.inner_text(".flow")
    assert "If yes" in flow and "If no" in flow and "For each item" in flow and "Set a value" in flow
    assert p.evaluate("getComputedStyle(document.querySelector('.lane')).flexDirection") == "column"
    p.click(".node[data-step='each']")
    box = p.inner_text("#stepBox")
    assert "Repeat for each" in box and "{" not in box.split("If it fails")[0][:5]
    # Change it: an in-page box, not the browser's prompt
    p.click("#changeIt")
    assert p.is_visible("#chgText")
    p.click("#chgCancel")
    # the webhook route shows how to get its address; two taps make it
    p.goto(base + "#/r/" + hook["id"])
    p.wait_for_selector("#addrNew")
    p.click("#addrNew")
    assert "stops working" in p.inner_text("#addrNew")
    p.click("#addrNew")
    p.wait_for_selector(".addr")
    assert "/api/dhara/hook/" in p.inner_text(".addr")
    # delete asks first, then the route is gone
    p.click("#delAsk")
    p.click("#delGo")
    p.wait_for_function("() => location.hash === '#/routes'", timeout=10000)
    assert D.get_workflow(t, wf_id=hook["id"]) is None
    c.close()
    # the computer: the routes table keeps its header and the search finds a route
    c2 = b.new_context(viewport={"width": 1440, "height": 900})
    c2.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    p2 = c2.new_page()
    p2.on("pageerror", lambda e: errors.append(str(e)))
    p2.goto(base + "#/routes")
    p2.wait_for_selector("#rq")
    assert p2.is_visible("table.rt thead")
    p2.fill("#rq", "nothing like this")
    assert "No route matches" in p2.inner_text("#rtable")
    p2.fill("#rq", "invoice")
    assert "invoice chase" in p2.inner_text("#rtable")
    c2.close()
    assert not errors, errors
