"""v0.999.234 STEPS YOU CAN TEST (R2 of the Hoola Route plan; owner: "GO R2"; built as 0.999.233, their COMPUTER V2 took 0.999.233).

A step opens in a large view with what comes in (every earlier step's whole output from the newest run or single-step
tests, the data the route started with, the loop's item), its settings, and what goes out. A field is dragged (or
clicked) into a box as {{steps.<id>.output.<field>}}. One step can be tested on that data; steps that decide report the
way they would take, a wait / approval say what they would do. Test data can be pinned: a pinned step gives its pinned
output in a TEST run instead of running (never in a real run), and the trigger's pin is the data a test starts with.
The run view shows each step's whole output (the log kept 600 characters).
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


def _wipe(t):
    shutil.rmtree(Path("data") / "dhara" / t, ignore_errors=True)


def _run(c):
    return asyncio.run(c)


def _client():
    from fastapi.testclient import TestClient
    from app.main import app
    from app.config import get_settings
    return TestClient(app), get_settings().tenant_id


@pytest.fixture(autouse=True)
def _clean(monkeypatch):
    monkeypatch.setattr(D, "polite_s", 0)
    D._RUNNING.clear()
    yield
    D._RUNNING.clear()


STEPS = [{"id": "total", "type": "set", "name": "total", "value": "{{vars.amount}}"},
         {"id": "fetch", "type": "http", "method": "GET", "url": "https://example.invalid/orders"},
         {"id": "big", "type": "condition", "filter": {"left": "{{vars.amount}}", "op": "gt", "right": 100},
          "then": [{"id": "tell", "type": "notify", "text": "Big {{steps.fetch.output.body.name}}"}], "else": []},
         {"id": "each", "type": "loop", "items": "{{steps.fetch.output.body.rows}}",
          "body": [{"id": "row", "type": "set", "name": "last", "value": "{{item.n}}"}]},
         {"id": "ask", "type": "approval", "question": "Go with {{vars.amount}}?"}]


def _wait(t, rid):
    for _ in range(200):
        r = D.get_run(t, rid)
        if r and r["status"] not in ("queued", "running"):
            return r
        time.sleep(0.05)
    return D.get_run(t, rid)


def test_pins_test_one_step_and_test_runs_use_them(bz):
    c, t = _client()
    _wipe(t)
    try:
        _run(D.dhara_save(Ctx(tenant_id=t, conversation_id=""), name="orders_flow", steps=STEPS))
        wf = D.get_workflow(t, name="orders_flow")
        base = f"/api/route/routes/{wf['id']}"
        d0 = c.get(base + "/data").json()
        assert d0["steps"] == {} and d0["pins"] == {} and d0["run_id"] == ""
        # pins: the trigger takes an object, a deciding step cannot be pinned, an unknown step neither
        assert c.put(base + "/pins/trigger", json={"value": [1, 2]}).status_code == 400
        assert c.put(base + "/pins/big", json={"value": {"x": 1}}).status_code == 400
        assert c.put(base + "/pins/nope", json={"value": {"x": 1}}).status_code == 400
        assert c.put(base + "/pins/trigger", json={"value": {"amount": 250}}).status_code == 200
        long = "x" * 2000
        fetched = {"status": 200, "body": {"name": "Asha", "rows": [{"n": 1}, {"n": 2}], "note": long}}
        assert c.put(base + "/pins/fetch", json={"value": fetched}).json()["pins"] == ["trigger", "fetch"]
        assert c.put(base + "/pins/fetch", json={"value": {"big": "y" * 300_000}}).status_code == 400
        # one step: the set step reads the pinned start data and shows the value
        r = c.post(base + "/steps/total/test", json={}).json()
        assert r["ok"] and r["output"] == {"set": "total", "value": 250} and r["real"] is True
        # a deciding step reports its way; a loop its items; an approval what it would ask; inside a loop {{item}} is the first item
        assert c.post(base + "/steps/big/test", json={}).json()["output"] == {"passed": True, "way": "If yes"}
        lp = c.post(base + "/steps/each/test", json={}).json()
        assert lp["output"]["count"] == 2 and lp["real"] is False
        assert c.post(base + "/steps/ask/test", json={}).json()["output"] == {"would_ask": "Go with 250?"}
        assert c.post(base + "/steps/row/test", json={}).json()["output"] == {"set": "last", "value": 1}
        assert c.post(base + "/steps/nope/test", json={}).status_code == 400
        # the newest data: single-step tests are kept; pins listed apart
        d1 = c.get(base + "/data").json()
        assert d1["steps"]["total"]["from"] == "step test" and d1["steps"]["total"]["output"]["value"] == 250
        assert "big" not in d1["steps"], "a deciding step leaves no data"
        assert d1["pins"]["trigger"] == {"amount": 250}
        # a TEST run: starts with the pinned data, the pinned web request is NOT called, the rest runs
        x = c.post(base + "/test", json={}).json()
        run = _wait(t, x["run_id"])
        assert run["status"] == "waiting_approval", run
        log = {l["id"]: l for l in run["steps_log"]}
        assert log["fetch"]["status"] == "ok" and run["context"]["steps"]["fetch"]["output"] == fetched
        assert log["big"]["status"] == "ok", "the if ran on the pinned amount"
        assert run["context"]["vars"]["last"] == 2, "the loop went through the pinned rows"
        # the run view gives each step's whole output, and says which were pinned
        rv = c.get(f"/api/route/runs/{x['run_id']}").json()
        assert len(rv["outputs"]["fetch"]["body"]["note"]) == 2000 and len(log["fetch"]["output"]) <= 600
        assert rv["pinned"] == ["fetch"]
        # a REAL run never uses pins: the web request really runs (and fails on the made-up address)
        real = D.create_run(t, D.get_workflow(t, wf_id=wf["id"]), {"amount": 5})
        _run(D.execute_run(t, real))
        rr = D.get_run(t, real)
        assert "_pins" not in rr["context"] and rr["steps_log"][1]["id"] == "fetch" and rr["steps_log"][1]["status"] == "error"
        # newest data now comes from that real run (newer than the step tests)
        d2 = c.get(base + "/data").json()
        assert d2["run_id"] == real and d2["vars"]["amount"] == 5
        # unpin; a deleted step's pin goes with the next pin
        assert c.delete(base + "/pins/fetch").json()["pins"] == ["trigger"]
        steps2 = [s for s in STEPS if s["id"] != "ask"] + [{"id": "note", "type": "notify", "text": "hi"}]
        _run(D.dhara_save(Ctx(tenant_id=t, conversation_id=""), name="orders_flow", steps=steps2))
        c.put(base + "/pins/note", json={"value": {"ok": 1}})
        assert set(c.get(base + "/data").json()["pins"]) == {"trigger", "note"}
    finally:
        _wipe(t)


def test_page_has_the_step_view():
    js = (Path(__file__).resolve().parents[1] / "app" / "static" / "console" / "route.js").read_text()
    css = (Path(__file__).resolve().parents[1] / "app" / "static" / "console" / "route.css").read_text()
    for part in ("openModal", "What comes in", "What goes out", "draggable=\"true\"", "dataTransfer.setData('text/plain'",
                 "/steps/${enc(h.step.id)}/test", "/pins/", "Pin this output", "Testing runs this step for real",
                 "The data a test starts with", "lastTap", "x.outputs"):
        assert part in js, part
    for part in (".smodal{", ".sm-cols{", ".fr{", ".pinb{", ".dropok{"):
        assert part in css, part


# ---------------------------------------------------------------- a real browser
from tests.test_v0999_232_route_editor import br as _br_base  # noqa: E402,F401


@pytest.fixture
def br2(bz, monkeypatch):
    sync_api = pytest.importorskip("playwright.sync_api")
    from tests.test_v161_console_e2e import _free_port
    from tests.test_v161_stream import KEY
    monkeypatch.setenv("API_KEY", KEY)
    from app.config import get_settings
    get_settings.cache_clear()
    t = get_settings().tenant_id
    _wipe(t)
    _run(D.dhara_save(Ctx(tenant_id=t, conversation_id=""), name="orders_flow", steps=STEPS))
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


def test_step_view_in_a_real_browser(br2):
    base, b, key, t = br2
    wf = D.get_workflow(t, name="orders_flow")
    from app.route import stepdata as SD
    SD.set_pin(t, wf, "trigger", {"amount": 250})
    SD.set_pin(t, wf, "fetch", {"status": 200, "body": {"name": "Asha", "rows": [{"n": 1}]}})
    for w, h in ((1440, 900), (390, 860)):
        c = b.new_context(viewport={"width": w, "height": h})
        c.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
        p = c.new_page()
        errs = []
        p.on("pageerror", lambda e: errs.append(str(e)))
        p.goto(base + "#/r/" + wf["id"])
        p.wait_for_selector(".nd[data-node='tell']")
        p.wait_for_selector(".nd[data-node='fetch'] .pinb")
        # the large view: what comes in has the pinned fetch output as fields
        p.dblclick(".nd[data-node='tell']")
        p.wait_for_selector("#smodal .sm-in .fr[data-expr]")
        assert "The data a test starts with (pinned)" in p.inner_text("#smodal .sm-in")
        exprs = p.eval_on_selector_all("#smodal .sm-in .fr[data-expr]", "els => els.map(e => e.dataset.expr)")
        assert "{{steps.fetch.output.body.name}}" in exprs and "{{vars.amount}}" in exprs
        # click a box, then a field: the expression goes in at the caret
        p.click("#smodal .sm-mid [data-k='text']")
        p.press("#smodal .sm-mid [data-k='text']", "End")
        p.click("#smodal .sm-in .fr[data-expr='{{vars.amount}}']")
        assert p.input_value("#smodal .sm-mid [data-k='text']").endswith("{{vars.amount}}")
        if w == 1440:
            # drag a field onto a box
            p.fill("#smodal .sm-mid [data-k='label']", "")
            p.drag_and_drop("#smodal .sm-in .fr[data-expr='{{steps.fetch.output.body.name}}']", "#smodal .sm-mid [data-k='label']")
            assert "{{steps.fetch.output.body.name}}" in p.input_value("#smodal .sm-mid [data-k='label']")
            # test the step: asks once (it really runs), then shows what went out
            p.click("#smTest")
            p.wait_for_selector("#realGo")
            p.click("#realGo")
            p.wait_for_function("() => document.querySelector('#smodal .sm-out').innerText.includes('Tested')", timeout=15000)
            assert D.get_workflow(t, wf_id=wf["id"])["steps"][2]["then"][0]["text"].endswith("{{vars.amount}}"), "saved before the test"
            p.keyboard.press("Escape")
            p.wait_for_selector("#smodal", state="hidden")
            # the trigger's test data is shown and can be pinned again
            p.dblclick(".nd[data-node='trigger']")
            p.wait_for_selector("#trigData")
            assert '"amount": 250' in p.input_value("#trigData")
            p.fill("#trigData", '{"amount": 7}')
            p.click("#smodal [data-pin='trigger']")
            for _ in range(100):
                if SD.pins(t, wf["id"]).get("trigger") == {"amount": 7}:
                    break
                time.sleep(0.05)
            assert SD.pins(t, wf["id"])["trigger"] == {"amount": 7}
        else:
            over = p.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
            assert over <= 1, f"the step view scrolls sideways by {over}px on a phone"
        assert not errs, errs
        c.close()
