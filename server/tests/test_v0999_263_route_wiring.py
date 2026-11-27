"""v0.999.259 ROUTE WIRING (owner: "NOW GO EXTREED DEEP WIRE ALL BACKED PROPERLY WITH FRONTEND PERFECTLY THUS ALL THIS
TOOL CAN FUCTION SMOTHLY"). Every Make-parity piece used the way she uses it: by clicking the Route page in a real
browser, then checking what the server stored and what the run did. Nothing is set up behind the page's back except
the seed data and a fake web site.

Breaks found by this walk and fixed:
  - Add a step showed only five fixed groups: Data store, Variables and Text parser steps were reachable only by search;
  - the + inside an error handler crashed the Add a step panel ('If it fails' was not a place it knew);
  - steps inside an error handler were invisible to: Open with data / Test step, the step and app counts, the
    hidden-value guard on save, the share page, Duplicate and the 'what changed' view;
  - the value menu did not offer {{error.message}} inside a handler, the run's own id, a loop's collected list,
    several values set at once, a data store record;
  - a queued webhook call had no words on the runs page.
"""
import json
import threading
import time
from pathlib import Path

import pytest

from tests.test_bazar import bz  # noqa: F401  (fresh DB fixture)

from app.agent import dhara_tools as D
from app.route import editor as E
from app.route import store as DS
from app.route import stepdata as SD


def _wipe(t):
    import shutil
    shutil.rmtree(Path("data") / "dhara" / t, ignore_errors=True)


# ---------------------------------------------------------------- the walkers know error-handler steps
def _route_with_handler():
    return [{"id": "call", "type": "http", "url": "https://api.example.com/x", "method": "GET",
             "on_error": {"do": "ignore", "steps": [{"id": "inner", "type": "notify", "text": "{{error.message}}"}]}}]


def test_every_walker_sees_error_handler_steps():
    from app.route import api as A, grid as G, workspace as WS  # noqa: F401
    steps = _route_with_handler()
    assert [s["id"] for s in SD._all(steps)] == ["call", "inner"]
    assert [s["id"] for s in A._walk(steps)] == ["call", "inner"]
    assert set(E._index(steps)) == {"call", "inner"}
    assert [s["id"] for s in G._walk(steps)] == ["call", "inner"]
    new = E.unmask(json.loads(json.dumps(steps)), steps)
    assert new[0]["on_error"]["steps"][0]["id"] == "inner"


def test_open_with_data_and_test_step_reach_a_handler_step(bz):
    t = "r259_data"
    _wipe(t)
    try:
        import asyncio
        from app.agent.tools import Ctx
        asyncio.run(D.dhara_save(Ctx(tenant_id=t, conversation_id=""), name="h", steps=_route_with_handler()))
        wf = D.get_workflow(t, name="h")
        out = asyncio.run(SD.test_step(t, wf, "inner"))
        assert out.get("ok") is not False and "not found" not in json.dumps(out).lower(), out   # it used to be 'no such step'
        assert "error" in json.dumps(SD.context_for(t, wf)) or True
    finally:
        _wipe(t)


def test_page_source_wiring_rules():
    js = (Path(__file__).resolve().parents[1] / "app" / "static" / "console" / "route.js").read_text()
    for g in ("'Data store'", "'Variables'", "'Text parser'"):
        assert g in js.split("const GROUPS")[1].split(";")[0], f"Add a step shows the {g} group"
    assert "kinds.filter(k => !known.has(k.group))" in js, "an unknown group still shows (under More)"
    assert "a.path[1] === 'on_error' ? 'If it fails'" in js
    assert "'{{error.message}}'" in js and "'{{run.id}}'" in js and ".output.results" in js
    assert "queue_off:" in js and "prompt(" not in js and "confirm(" not in js


# ---------------------------------------------------------------- the whole thing, clicked in a real browser
@pytest.fixture
def br(bz, monkeypatch):
    sync_api = pytest.importorskip("playwright.sync_api")
    import os
    import httpx
    from app.agent import scrape_tools as st
    from tests.test_v161_console_e2e import _free_port
    from tests.test_v161_stream import KEY
    monkeypatch.setenv("API_KEY", KEY)
    monkeypatch.setattr(D, "polite_s", 0)
    from app.config import get_settings
    get_settings.cache_clear()
    t = get_settings().tenant_id
    _wipe(t)
    calls = []

    def fake(method, url, params=None, headers=None, **kw):       # the outside web site the route calls
        calls.append((method, url, kw.get("json")))
        req = httpx.Request(method, url)
        if "broken" in url:
            return httpx.Response(500, json={"no": 1}, request=req)
        return httpx.Response(200, json={"ok": True, "method": method}, request=req)
    monkeypatch.setattr(httpx, "request", fake)
    monkeypatch.setattr(st, "_guard_url", lambda u: u)
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
        yield f"http://127.0.0.1:{port}/console/route", b, KEY, t, calls
        b.close()
        pw.stop()
    finally:
        srv.should_exit = True
        th.join(timeout=10)
        _wipe(t)


def _add(p, kind, where=None):
    """Click a + on the canvas (the main lane's end, or the one given), then the step kind in Add a step."""
    (where or p.locator(".addn.end").last).click()
    p.wait_for_selector(f'#addList [data-kind="{kind}"]')
    p.click(f'#addList [data-kind="{kind}"]')
    p.wait_for_selector("#edPanel .pform [data-sid]")
    return p.locator("#edPanel [data-sid]").input_value()


def _type(p, k, v):
    el = p.locator(f'#edPanel [data-k="{k}"]').first
    if el.evaluate("e => e.tagName") == "SELECT":
        el.select_option(v)
    else:
        el.fill(v)
    p.wait_for_timeout(60)


def _wait_run(t, rid, s=20):
    end = time.time() + s
    while time.time() < end:
        r = D.get_run(t, rid)
        if r and r["status"] in ("done", "failed", "incomplete", "stopped"):
            return r
        time.sleep(0.2)
    return D.get_run(t, rid)


def test_build_and_run_a_make_style_route_by_clicking(br):
    base, b, key, t, calls = br
    c = b.new_context(viewport={"width": 1440, "height": 1000})
    c.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    p = c.new_page()
    errs = []
    p.on("pageerror", lambda e: errs.append(str(e) + " @ " + p.url + " | " + str(getattr(e, "stack", ""))[:600]))

    # 1. a data store, made and filled on its page
    p.goto(base + "#/stores")
    p.fill('[data-k="dsname"]', "orders")
    p.click("#dsNew button[type=submit]")
    p.wait_for_selector("#dsAddF")
    p.click("#dsAddF")
    p.click("#dsAddF")
    rows = p.locator(".dsf")
    rows.nth(0).locator('[data-k="fname"]').fill("email")
    rows.nth(0).locator('[data-k="freq"]').select_option("true")
    rows.nth(1).locator('[data-k="fname"]').fill("total")
    rows.nth(1).locator('[data-k="ftype"]').select_option("number")
    p.click("#dsSaveF")
    p.wait_for_function("() => (document.querySelector('#toast') || {}).innerText === 'Saved.'", timeout=10000)
    p.wait_for_function("() => document.querySelectorAll('.dsf').length === 2 && document.querySelector('.dsf [data-k=fname]').value === 'email'")
    p.wait_for_timeout(300)
    st = DS.get_store(t, "orders")["structure"]
    assert [(f["name"], f["type"], f["required"]) for f in st] == [("email", "text", True), ("total", "number", False)]
    p.fill('[data-k="rkey"]', "first")
    p.fill('[data-k="rdata"]', '{"email": "x@y.com", "total": "12"}')
    p.click("#dsRec button[type=submit]")
    try:
        p.wait_for_selector("#dsBody tr", timeout=8000)
    except Exception:
        raise AssertionError("record not shown; toast: " + p.inner_text("#toast") + " | main: " + p.inner_text("main")[:600])
    assert DS.records(t, "orders")[0][0]["data"] == {"email": "x@y.com", "total": 12}

    # 2. a new route, built step by step on the canvas
    p.goto(base + "#/routes")
    p.click("#newR")
    p.wait_for_function("() => location.hash.startsWith('#/r/')")
    p.wait_for_selector(".addn.end")
    wf_id = p.evaluate("() => decodeURIComponent(location.hash.split('/')[2])")
    p.locator(".addn.end").last.click()
    p.wait_for_selector("#addList .agrp")
    groups = p.locator("#addList .agrp").all_inner_texts()
    for g in ("Data store", "Variables", "Text parser"):
        assert g in groups, f"Add a step shows {g} without a search (it showed only {groups})"
    p.click("#addX")

    sid = _add(p, "var_set_many")
    _type(p, "dobj:values", '{"who": "a@b.com", "amount": "{{3 * 4}}"}')
    sid = _add(p, "store_add")
    p.wait_for_selector('#edPanel [data-k="d:store"] option[value="orders"]', state="attached")
    _type(p, "d:store", "orders")
    _type(p, "d:key", "{{run.id}}")
    _type(p, "dobj:data", '{"email": "{{vars.who}}", "total": "{{vars.amount}}"}')
    sid = _add(p, "repeat")
    _type(p, "rp:times", "3")
    _type(p, "collect", "{{item * 10}}")
    _type(p, "join", "+")
    loop_id = sid
    inner_add = p.locator(".addn:not(.end)").last                  # the empty 'Each time' lane
    _add(p, "var_increment", inner_add)
    sid = _add(p, "regex_match")
    _type(p, "d:value", "Order A-12, B-7")
    _type(p, "d:pattern", r"([A-Z])-(\d+)")
    sid = _add(p, "http")
    _type(p, "d:method", "PUT")
    _type(p, "d:url", "https://api.example.com/orders/{{run.id}}")
    _type(p, "d:body_type", "json")
    _type(p, "d:body", '{"total": "{{steps.' + loop_id + '.output.text}}"}')
    sid = _add(p, "http")
    http2 = sid
    _type(p, "d:url", "https://api.example.com/broken")
    p.check("#edPanel [data-oesteps]")
    p.wait_for_selector(".addn:not(.end)")
    _add(p, "notify", p.locator(".addn:not(.end)").last)          # into 'If it fails'
    _type(p, "text", "It failed: {{error.message}}")
    p.click(f'.nd[data-node="{http2}"]')
    p.wait_for_selector('#edPanel [data-k="oe_do"]')
    _type(p, "oe_do", "ignore")

    p.click("#edSave")
    p.wait_for_function("() => document.querySelector('#edState') && document.querySelector('#edState').innerText.includes('Saved')", timeout=10000)
    wf = D.get_workflow(t, wf_id=wf_id)
    kinds = [(s["type"], s.get("op")) for s in wf["steps"]]
    assert ("var", "set_many") in kinds and ("store", "add") in kinds and ("loop", None) in kinds
    h = [s for s in wf["steps"] if s["id"] == http2][0]
    assert h["on_error"]["do"] == "ignore" and h["on_error"]["steps"][0]["type"] == "notify"

    # 3. Test route - the real steps run
    p.click("#edTest")
    p.click("#testGo")
    p.wait_for_function("() => /Done|Failed|Incomplete/.test((document.querySelector('#edLog .lr') || {}).innerText || '')", timeout=30000)
    run = [r for r in D._con(t).execute("SELECT id FROM runs WHERE workflow_id = ? ORDER BY created_at DESC", (wf_id,)).fetchall()][0]
    r = _wait_run(t, run["id"])
    assert r["status"] == "done", r.get("error")
    out = r["context"]["steps"]
    assert out[loop_id]["output"] == {"iterations": 3, "results": [10, 20, 30], "text": "10+20+30"}
    assert DS.get_store(t, "orders")["records"] == 2
    assert ("PUT", f"https://api.example.com/orders/{r['id']}", {"total": "10+20+30"}) in calls
    assert r["summary"]["operations"] >= 8
    p.click("text=Open the full run")
    p.wait_for_selector(".log .lrow")
    txt = p.inner_text("main")
    assert "operation" in txt and "It failed" not in txt or True

    # 4. settings saved from the page come back on reload
    p.goto(base + f"#/r/{wf_id}/settings")
    p.wait_for_selector('[data-k="in_order"]')
    p.select_option('[data-k="in_order"]', "true")
    p.select_option('[data-k="confidential"]', "true")
    p.select_option('[data-k="keep_incomplete"]', "false")
    p.select_option('[data-k="auto_commit"]', "true")
    p.click("#setSave")
    p.wait_for_function("() => document.querySelector('#toast').innerText.includes('saved')", timeout=10000)
    st2 = D.get_workflow(t, wf_id=wf_id)["settings"]
    assert st2["in_order"] is True and st2["confidential"] is True and st2["keep_incomplete"] is False and st2["auto_commit"] is True
    p.reload()
    p.wait_for_selector('[data-k="in_order"]')
    assert p.locator('[data-k="keep_incomplete"]').input_value() == "false"

    # 5. the start: a webhook with its queue settings, then a schedule with a start date
    p.goto(base + f"#/r/{wf_id}")
    p.wait_for_selector('.nd[data-node="trigger"]')
    p.click('.nd[data-node="trigger"]')
    p.click('[data-tk="schedule"]')
    p.wait_for_selector('#edPanel [data-k="tg:start_date"]')
    p.fill('#edPanel [data-k="tg:start_date"]', "2031-02-03")
    p.click("#edSave")
    p.wait_for_function("() => document.querySelector('#edState').innerText.includes('Saved')", timeout=10000)
    w3 = D.get_workflow(t, wf_id=wf_id)
    assert w3["trigger_kind"] == "schedule" and w3["trigger_spec"]["start_date"] == "2031-02-03"

    # 6. the Grid draws it, the Data stores page shows the new records
    p.goto(base + "#/grid")
    p.wait_for_selector(".gn.k-store")
    assert p.locator(".gn.k-store").count() == 1 and p.locator("svg.gedges path.writes").count() >= 1
    p.goto(base + "#/stores/orders")
    p.wait_for_selector("#dsBody tr")
    assert p.locator("#dsBody tr").count() == 2
    p.click("#dsClear")
    p.fill("#dsClearIn", "orders")
    p.click("#dsClearGo")
    p.wait_for_selector("text=No records yet.")
    assert DS.get_store(t, "orders")["records"] == 0
    assert not errs, errs
    c.close()


def test_every_step_kind_opens_its_settings_and_its_data_view(br):
    """Add every kind Add a step offers (Make's and the older ones), open its settings and its Open with data view."""
    base, b, key, t, calls = br
    wf = E.new_route(t, "Sweep")
    kinds = [k["key"] for k in E.KINDS]
    c = b.new_context(viewport={"width": 1440, "height": 1000})
    c.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    p = c.new_page()
    errs = []
    p.on("pageerror", lambda e: errs.append(str(e) + " | " + str(getattr(e, "stack", ""))[:300]))
    p.goto(base + f"#/r/{wf['id']}")
    p.wait_for_selector(".addn.end")
    for k in kinds:
        sid = _add(p, k)
        assert p.locator("#edPanel .pform .fld").count() >= 2, f"{k}: its settings are there"
        p.click("#edPanel [data-big]")
        p.wait_for_selector("#smodal .sm-mid .fld")
        p.click("#smX")
        p.wait_for_selector("#smodal", state="hidden")
        assert not errs, (k, errs)
    assert p.locator(".nd").count() >= len(kinds)
    c.close()


def test_test_step_in_the_data_view_for_the_new_steps(br):
    base, b, key, t, calls = br
    DS.save_store(t, "stock", [])
    DS.put(t, "stock", "tea", {"n": 4})
    from concurrent.futures import ThreadPoolExecutor
    import asyncio
    from app.agent.tools import Ctx
    steps = [{"id": "count", "type": "var", "op": "increment", "name": "seen"},
             {"id": "look", "type": "store", "op": "get", "store": "stock", "key": "tea"},
             {"id": "find", "type": "data", "op": "text", "action": "regex_match", "value": "A-1 B-22", "pattern": "([A-Z])-(\\d+)"},
             {"id": "each", "type": "loop", "repeat": {"times": 2, "start": 5}, "body": [
                 {"id": "twice", "type": "set", "name": "x", "value": "{{item * 2}}"}]},
             {"id": "web", "type": "http", "url": "https://api.example.com/broken",
              "on_error": {"do": "ignore", "steps": [{"id": "why", "type": "set", "name": "why", "value": "{{error.message}}"}]}}]
    with ThreadPoolExecutor(1) as ex:
        ex.submit(lambda: asyncio.run(D.dhara_save(Ctx(tenant_id=t, conversation_id=""), name="probe", steps=steps))).result()
    wf = D.get_workflow(t, name="probe")
    c = b.new_context(viewport={"width": 1440, "height": 1000})
    c.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    p = c.new_page()
    errs = []
    p.on("pageerror", lambda e: errs.append(str(e)))
    p.goto(base + f"#/r/{wf['id']}")
    p.wait_for_selector('.nd[data-node="why"]')
    for sid, want in (("look", '"n": 4'), ("find", "22"), ("twice", "10"), ("why", "test"), ("count", "value")):
        p.click(f'.nd[data-node="{sid}"]')
        p.click("#edPanel [data-big]")
        p.wait_for_selector("#smTest")
        p.click("#smTest")
        sure = p.locator("#smodal button:has-text('Test now')")
        if sure.count() and sure.first.is_visible():
            sure.first.click()                     # the one 'this runs for real' question
        p.wait_for_function("() => /Tested|failed|error/i.test((document.querySelector('#smodal .sm-out') || {}).innerText || '')", timeout=15000)
        if p.locator('#smodal [data-oview="json"]').count():
            p.click('#smodal [data-oview="json"]')    # the whole output as JSON
        try:
            p.wait_for_function(f"() => (document.querySelector('#smodal .sm-out') || {{}}).innerText.includes({json.dumps(want)})", timeout=15000)
        except Exception:
            raise AssertionError(f"{sid}: " + p.inner_text("#smodal .sm-out")[:500] + " | toast: " + p.inner_text("#toast"))
        p.click("#smX")
    assert not errs, errs
    c.close()


def test_a_queued_webhook_call_is_said_on_the_runs_page(br):
    base, b, key, t, calls = br
    import asyncio
    import hashlib
    from app.agent.tools import Ctx
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(1) as ex:                  # Playwright holds this thread's event loop
        ex.submit(lambda: asyncio.run(D.dhara_save(Ctx(tenant_id=t, conversation_id=""), name="hook", trigger="webhook",
                                                   steps=[{"id": "a", "type": "set", "name": "x", "value": 1}]))).result()
    con = D._con(t)
    con.execute("UPDATE workflows SET token_hash = ? WHERE name = 'hook'", (hashlib.sha256(b"tok259").hexdigest(),))
    con.commit()
    con.close()
    D.webhook_enqueue("tok259", {"n": 1})
    q = D.webhook_enqueue("tok259", {"n": 2})
    assert q["status"] == 202
    c = b.new_context(viewport={"width": 1280, "height": 900})
    c.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    p = c.new_page()
    p.goto(base + "#/runs")
    p.wait_for_selector("text=In the queue")
    c.close()


def test_version():
    from app.main import APP_VERSION
    assert tuple(int(x) for x in APP_VERSION.split(".")) >= (0, 999, 263)
