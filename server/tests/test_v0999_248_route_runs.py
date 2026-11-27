"""v0.999.248 PAST RUNS, INSIGHTS, N8N IMPORT (R8 of the Hoola Route plan, the last phase; owner: "GO R8").

Find runs by a value; run again with the data a run started with; a past run's data in the editor (and pinned from it);
each route keeps its runs as long as its Settings say; insights from a tally that outlives the runs; an n8n workflow
brought in as a route - switched off, with a report of what came in, what to check and what to redo.
"""
import asyncio
import json
import shutil
import time
from pathlib import Path

import pytest

from tests.test_bazar import bz  # noqa: F401  (fresh DB fixture)

from app.agent import dhara_tools as D
from app.agent.tools import Ctx, ToolError
from app.route import n8n as N8
from app.route import runs as RU
from app.route import stepdata as SD

HERE = Path(__file__).resolve().parents[1]


def _wipe(t):
    shutil.rmtree(Path("data") / "dhara" / t, ignore_errors=True)


def _run(c):
    return asyncio.run(c)


def _save(t, name, steps, **kw):
    return _run(D.dhara_save(Ctx(tenant_id=t, conversation_id=""), name=name, steps=steps, **kw))


def _go(t, name, vars_=None):
    rid = D.create_run(t, D.get_workflow(t, name=name), vars_ or {})
    _run(D.execute_run(t, rid))
    return rid


ORDER = [{"id": "price", "type": "set", "name": "total", "value": "{{ vars.qty * 12 }}"},
         {"id": "shape", "type": "data", "op": "fields", "values": {"order": "{{vars.order}}", "total": "{{vars.total}}"}}]


def test_find_runs_by_a_value(bz, monkeypatch):
    monkeypatch.setattr(D, "polite_s", 0)
    t = "r8_find"
    _wipe(t)
    try:
        _save(t, "orders", ORDER)
        a = _go(t, "orders", {"order": "ORD-7781", "qty": 2})
        _go(t, "orders", {"order": "ORD-1000", "qty": 1, "card": "4111 1111 1111 1111"})
        got = RU.search(t, "ord-7781")                                   # any case
        assert [x["id"] for x in got["runs"]] == [a] and got["runs"][0]["found_in"] == "start data"
        assert "ORD-7781" in got["runs"][0]["match"]
        got = RU.search(t, "24")                                          # a value a step worked out
        assert got["runs"] and got["runs"][0]["found_in"].startswith("step ")
        card = RU.search(t, "ORD-1000")["runs"][0]
        assert "4111 1111 1111 1111" not in json.dumps(card)              # a card number never comes back whole
        with pytest.raises(RU.RunsError):
            RU.search(t, "x")
        assert RU.search(t, "no-such-value-here")["runs"] == []
        assert RU.search(t, "100%")["runs"] == []                         # % and _ are text, not patterns
    finally:
        _wipe(t)


def test_run_again_with_the_same_start_data(bz, monkeypatch):
    monkeypatch.setattr(D, "polite_s", 0)
    t = "r8_again"
    _wipe(t)
    try:
        _save(t, "orders", ORDER)
        old = _go(t, "orders", {"order": "ORD-5", "qty": 3})
        assert D.get_run(t, old)["context"]["vars"]["total"] == 36          # a step changed the variables...
        assert RU.start_data(D.get_run(t, old)) == {"order": "ORD-5", "qty": 3}   # ...the start data is kept apart
        new = RU.rerun(t, old)
        assert new["from_run"] == old and new["run_id"] != old
        _run(D.execute_run(t, new["run_id"]))
        x = D.get_run(t, new["run_id"])
        assert x["status"] == "done" and x["context"]["steps"]["shape"]["output"] == {"order": "ORD-5", "total": 36}
        assert D.get_run(t, old)["status"] == "done"                        # the old run is untouched
        with pytest.raises(RU.RunsError):
            RU.rerun(t, "rn_nope")
        _save(t, "orders", ORDER, settings={"runs_per_day": 2})
        with pytest.raises(RU.RunsError):
            RU.rerun(t, old)                                                 # its daily limit counts
    finally:
        _wipe(t)


def test_a_past_run_in_the_editor_and_pinned_from_it(bz, monkeypatch):
    monkeypatch.setattr(D, "polite_s", 0)
    t = "r8_debug"
    _wipe(t)
    try:
        steps = ORDER + [{"id": "check", "type": "code", "code": "raise ValueError('no stock for ' + str(vars['order']))"}]
        _save(t, "orders", steps)
        _save(t, "other", [{"id": "a", "type": "set", "name": "x", "value": 1}])
        bad = _go(t, "orders", {"order": "ORD-9", "qty": 4})
        _go(t, "orders", {"order": "ORD-10", "qty": 1})                    # a newer run
        wf = D.get_workflow(t, name="orders")
        d = SD.data(t, wf, bad)
        assert d["debug"] and d["run_id"] == bad and d["vars"] == {"order": "ORD-9", "qty": 4}
        assert d["steps"]["shape"]["output"]["total"] == 48 and d["failed_step"] == "check"
        assert SD.data(t, wf)["vars"]["order"] == "ORD-10"                 # without a run: the newest data
        other = _go(t, "other")
        with pytest.raises(ValueError):
            SD.data(t, wf, other)                                            # never another route's run
        ctx = SD.context_for(t, wf, False, bad)
        assert ctx["steps"]["shape"]["output"]["order"] == "ORD-9"
        assert SD.preview(t, wf, "{{steps.shape.output.total}}", run_id=bad)["value"] == 48
        out = RU.pin_from_run(t, wf, bad)
        assert set(out["pinned"]) == {"trigger", "shape"}                     # never the step that failed
        assert SD.pins(t, wf["id"])["trigger"] == {"order": "ORD-9", "qty": 4}
        with pytest.raises(RU.RunsError):
            RU.pin_from_run(t, wf, other)
    finally:
        _wipe(t)


def test_each_route_keeps_its_runs_as_its_settings_say(bz, monkeypatch):
    monkeypatch.setattr(D, "polite_s", 0)
    t = "r8_keep"
    _wipe(t)
    try:
        with pytest.raises(ToolError):
            D.validate_settings({"keep_runs_days": 0})
        with pytest.raises(ToolError):
            D.validate_settings({"keep_runs": "lots"})
        assert D.validate_settings({"keep_runs_days": "90", "keep_runs": 500, "minutes_saved": "2.5"}) == \
            {"keep_runs_days": 90, "keep_runs": 500, "minutes_saved": 2.5}
        _save(t, "kept", [{"id": "a", "type": "set", "name": "x", "value": 1}], settings={"keep_runs": 2})
        _save(t, "plain", [{"id": "a", "type": "set", "name": "x", "value": 1}])
        _save(t, "old", [{"id": "a", "type": "set", "name": "x", "value": 1}], settings={"keep_runs_days": 2})
        kept = [_go(t, "kept") for _ in range(4)]
        plain = [_go(t, "plain") for _ in range(4)]
        old = [_go(t, "old") for _ in range(3)]
        D.update_run(t, old[0], updated_at=time.time() - 3 * 86400)
        D.update_run(t, plain[0], updated_at=time.time() - 3 * 86400)
        D.forget_old_runs(t, keep_days=30, keep=40)
        ids = {r["id"] for r in D.list_runs(t, limit=100)}
        assert ids & set(kept) == set(kept[2:])                              # its own count: the newest 2
        assert set(plain) <= ids                                              # the server default: 30 days
        assert old[0] not in ids and set(old[1:]) <= ids                      # its own days
        D.forget_old_runs(t, keep_days=1, keep=40)
        ids = {r["id"] for r in D.list_runs(t, limit=100)}
        assert plain[0] not in ids and set(kept[2:]) <= ids                   # a route's own keeping is not the default's
    finally:
        _wipe(t)


def test_insights_from_the_tally(bz, monkeypatch):
    monkeypatch.setattr(D, "polite_s", 0)
    t = "r8_ins"
    _wipe(t)
    try:
        _save(t, "good", [{"id": "a", "type": "set", "name": "x", "value": 1}], settings={"minutes_saved": 6})
        _save(t, "flaky", [{"id": "a", "type": "code", "code": "raise ValueError('nope')" if True else ""}])
        for _ in range(3):
            _go(t, "good")
        f = _go(t, "flaky")
        x = RU.insights(t, 7, tz="Asia/Tokyo")
        assert x["totals"]["runs"] == 4 and x["totals"]["failed"] == 1 and x["totals"]["failure_rate"] == 25.0
        assert x["totals"]["minutes_saved"] == 18.0 and x["tz"] == "Asia/Tokyo" and len(x["series"]) == 7
        good = next(r for r in x["routes"] if r["name"] == "good")
        assert good["runs"] == 3 and good["minutes_saved"] == 18.0 and good["avg_s"] is not None
        assert x["failing_steps"][0]["step"] == "a" and x["failing_steps"][0]["route"] == "flaky"
        # the failed run is fixed and retried: it moves from failed to done, never counted twice
        _save(t, "flaky", [{"id": "a", "type": "set", "name": "x", "value": 2}])
        _run(D.dhara_control(Ctx(tenant_id=t, conversation_id=""), action="retry", run_id=f))
        _run(D.drain())
        x = RU.insights(t, 7)
        assert x["totals"]["runs"] == 4 and x["totals"]["failed"] == 0
        D.forget_old_runs(t, keep_days=1, keep=0)                              # the runs go, the figures stay
        assert D.list_runs(t, limit=10) == [] and RU.insights(t, 7)["totals"]["runs"] == 4
        assert RU.insights(t, 30, tz="Not/AZone")["tz"] == "UTC"
    finally:
        _wipe(t)


def _ex(name):
    return json.loads((HERE / "tests" / "data" / f"n8n_{name}.json").read_text())


def test_an_n8n_workflow_becomes_a_route(bz):
    p = N8.convert(_ex("orders"))
    assert p["name"] == "order_alert" and p["trigger"] == "webhook" and p["settings"] == {"timezone": "Europe/Berlin"}
    ids = [s["id"] for s in p["steps"]]
    assert ids == ["get_customer", "big_order", "merge", "code", "slack", "respond"]
    http = p["steps"][0]
    assert http["url"] == "https://api.example.com/customers/{{vars.body.customer_id}}?full=yes"
    cond = p["steps"][1]
    assert cond["filter"] == {"all": [{"left": "{{vars.body.total}}", "op": "gt", "right": 500}]}
    assert cond["then"][0]["values"]["email"] == "{{steps.get_customer.output.json.email}}"
    assert cond["else"][0]["values"]["up"].startswith("[n8n: ")             # JavaScript is never carried over as code
    assert p["steps"][3]["type"] == "stop" and "return items" not in json.dumps(p["steps"])
    assert {x["node"] for x in p["report"]["placeholders"]} == {"Code", "Slack"}
    assert any("toUpperCase" in c["why"] for c in p["report"]["check"])
    assert p["steps"][5] == {"id": "respond", "type": "respond", "status": 201, "body": {"ok": True}, "label": "Respond"}
    D.validate_steps(p["steps"])                                              # the engine's own checks pass


def test_n8n_loops_ways_ai_and_schedules(bz):
    p = N8.convert(_ex("leads"))
    assert p["trigger"] == "schedule" and p["trigger_spec"] == {"days": ["mon", "wed", "fri"], "at": ["09:30"]}
    loop = next(s for s in p["steps"] if s["type"] == "loop")
    assert loop["items"] == "{{steps.split_out.output}}"
    ai, ways = loop["body"]
    assert ai == {"id": "classify", "type": "ai", "op": "classify", "text": "{{item.message}}", "label": "Classify",
                  "categories": ["Hot", "Cold"]}
    assert [r["label"] for r in ways["routes"]] == ["Hot"]                    # Cold went back to the loop: on to the next
    sw = next(s for s in p["steps"] if s["id"] == "switch")
    assert sw["routes"][0]["steps"][0]["op"] == "write" and sw["fallback"][0]["message"] == "No leads"
    assert any(x["node"] == "OpenAI Chat Model" for x in p["report"]["skipped"])
    assert any(c["node"] == "Get leads" and "Sign-ins" in c["why"] for c in p["report"]["check"])
    D.validate_steps(p["steps"])
    assert N8._Conv._cron("30 9 * * 1,5") == {"at": ["09:30"], "days": ["mon", "fri"]}
    assert N8._Conv._cron("*/5 * * * *") == {"every_minutes": 15}
    assert N8._Conv._cron("0 9 1 1 *") is None
    for bad in ("not json", "{\"nodes\": 3}", json.dumps({"nodes": [{"name": str(i), "type": "x"} for i in range(301)]})):
        with pytest.raises(N8.N8nError):
            N8.convert(bad)


def test_bringing_it_in_lands_switched_off_and_runs(bz, monkeypatch):
    monkeypatch.setattr(D, "polite_s", 0)
    t = "r8_n8n"
    _wipe(t)
    try:
        doc = {"name": "Greet", "nodes": [
            {"name": "Form", "type": "n8n-nodes-base.formTrigger", "parameters": {"formTitle": "Hello", "formFields": {"values": [
                {"fieldLabel": "Your name", "requiredField": True}, {"fieldLabel": "Plan", "fieldType": "dropdown",
                                                                   "fieldOptions": {"values": [{"option": "Pro"}, {"option": "Free"}]}}]}}},
            {"name": "Greeting", "type": "n8n-nodes-base.set", "typeVersion": 3.4, "parameters": {"assignments": {"assignments": [
                {"name": "line", "value": "=Hello {{ $json['Your name'] }} on {{ $json.Plan }}"}]}}},
            {"name": "Pro?", "type": "n8n-nodes-base.if", "typeVersion": 2, "parameters": {"conditions": {"combinator": "and", "conditions": [
                {"leftValue": "={{ $('Form').item.json.Plan }}", "rightValue": "Pro", "operator": {"operation": "equals"}}]}}},
            {"name": "Thanks", "type": "n8n-nodes-base.set", "typeVersion": 3.4, "parameters": {"assignments": {"assignments": [
                {"name": "vip", "value": "=yes {{ $json.line }}"}]}}}],
            "connections": {"Form": {"main": [[{"node": "Greeting", "index": 0}]]}, "Greeting": {"main": [[{"node": "Pro?", "index": 0}]]},
                            "Pro?": {"main": [[{"node": "Thanks", "index": 0}], []]}}}
        out = N8.bring_in(t, json.dumps(doc))
        wf = D.get_workflow(t, wf_id=out["workflow_id"])
        assert out["enabled"] is False and not wf["enabled"] and wf["trigger_kind"] == "form"
        assert [f["name"] for f in wf["trigger_spec"]["fields"]] == ["your_name", "plan"]
        assert wf["trigger_spec"]["fields"][1]["options"] == ["Pro", "Free"]
        with pytest.raises(N8.N8nError):
            N8.bring_in(t, json.dumps(doc))                                    # never over one of her routes
        rid = D.create_run(t, wf, {"form": {"your_name": "Asha", "plan": "Pro"}})
        _run(D.execute_run(t, rid))
        x = D.get_run(t, rid)
        assert x["status"] == "done", x.get("error")
        assert x["context"]["steps"]["greeting"]["output"] == {"line": "Hello Asha on Pro"}
        assert x["context"]["steps"]["thanks"]["output"] == {"vip": "yes Hello Asha on Pro"}
        two = N8.bring_in(t, doc, new_name="greet_two")
        assert two["name"] == "greet_two"
    finally:
        _wipe(t)


def test_the_page_routes(bz, monkeypatch):
    from fastapi.testclient import TestClient
    from app.main import app
    from app.config import get_settings
    monkeypatch.setattr(D, "polite_s", 0)
    t = get_settings().tenant_id
    _wipe(t)
    try:
        c = TestClient(app)
        _save(t, "orders", ORDER)
        rid = _go(t, "orders", {"order": "ORD-42", "qty": 1})
        wf = D.get_workflow(t, name="orders")
        found = c.get("/api/route/runs", params={"q": "ORD-42"}).json()["runs"]
        assert found[0]["id"] == rid and found[0]["found_in"] == "start data"
        assert c.get("/api/route/runs", params={"q": "O"}).status_code == 400
        one = c.get(f"/api/route/runs/{rid}").json()
        assert one["start"] == {"order": "ORD-42", "qty": 1} and one["failed_step"] == ""
        assert c.get(f"/api/route/routes/{wf['id']}/data", params={"run_id": rid}).json()["debug"] is True
        assert c.get(f"/api/route/routes/{wf['id']}/data", params={"run_id": "rn_nope"}).status_code == 404
        assert c.post(f"/api/route/routes/{wf['id']}/pins/from-run", json={"run_id": rid}).json()["pinned"]
        again = c.post(f"/api/route/runs/{rid}/rerun").json()
        assert again["from_run"] == rid
        assert c.post("/api/route/runs/rn_nope/rerun").status_code == 404
        ins = c.get("/api/route/insights", params={"days": 30, "tz": "America/New_York"}).json()
        assert ins["days"] == 30 and ins["totals"]["runs"] >= 1
        st = c.put(f"/api/route/routes/{wf['id']}/settings", json={"keep_runs_days": 120, "minutes_saved": 4}).json()["settings"]
        assert st["keep_runs_days"] == 120 and st["minutes_saved"] == 4
        pv = c.post("/api/route/import/n8n", json={"workflow": _ex("orders")}).json()
        assert pv["name"] == "order_alert" and D.get_workflow(t, name="order_alert") is None   # a look saves nothing
        sv = c.post("/api/route/import/n8n", json={"workflow": _ex("orders"), "save": True}).json()
        assert sv["enabled"] is False and D.get_workflow(t, name="order_alert") is not None
        assert c.post("/api/route/import/n8n", json={"workflow": _ex("orders"), "save": True}).status_code == 409
        assert c.post("/api/route/import/n8n", json={"workflow": "nope"}).status_code == 400
    finally:
        _wipe(t)


# ---------------------------------------------------------------- a real browser
@pytest.fixture
def br8(bz, monkeypatch):
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
    _save(t, "orders", ORDER + [{"id": "check", "type": "code", "code": "raise ValueError('no stock')"}])
    _go(t, "orders", {"order": "ORD-77", "qty": 2})
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


def test_past_runs_insights_and_import_in_a_real_browser(br8):
    base, b, key, t = br8
    c = b.new_context(viewport={"width": 1440, "height": 900})
    c.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    p = c.new_page()
    errs = []
    p.on("pageerror", lambda e: errs.append(str(e)))
    p.goto(base + "#/runs")
    p.wait_for_selector("#runQ")
    p.fill("#runQ", "ord-77")
    p.press("#runQ", "Enter")
    p.wait_for_selector("td.found")
    assert "start data" in p.inner_text("#runList")
    p.click("#runList a.rn")
    p.wait_for_selector("#runAgain")
    p.click("text=What it started with")
    assert "ORD-77" in p.inner_text("main")                                    # what it started with
    p.click("#runDebug")
    p.wait_for_selector(".edbanner.debug #dbgPin")
    assert "Check" in p.inner_text("#edBanner") or "check" in p.inner_text("#edBanner")   # where it failed
    p.click("#dbgPin")
    p.wait_for_function("() => document.querySelector('#toast').innerText.includes('Pinned')", timeout=10000)
    wf = D.get_workflow(t, name="orders")
    assert SD.pins(t, wf["id"])["trigger"]["order"] == "ORD-77"
    p.click("#dbgAgain")
    p.wait_for_function("() => location.hash.startsWith('#/run/')", timeout=10000)
    p.goto(base + "#/insights/30")
    p.wait_for_selector(".stats .stat")
    assert "orders" in p.inner_text("main").lower() and p.locator(".bars .bar").count() == 30
    p.goto(base + "#/routes")
    p.click("text=Bring in from n8n")
    p.wait_for_selector("#n8nText")
    p.fill("#n8nText", (HERE / "tests" / "data" / "n8n_orders.json").read_text())
    p.click("#n8nForm button[type='submit']")
    p.wait_for_selector("#n8nSave")
    assert "To redo in Hoola" in p.inner_text("#n8nOut") and "Slack" in p.inner_text("#n8nOut")
    p.click("#n8nSave button[type='submit']")
    p.wait_for_function("() => location.hash.startsWith('#/r/')", timeout=10000)
    assert D.get_workflow(t, name="order_alert")["enabled"] in (0, False)
    p.set_viewport_size({"width": 390, "height": 844})
    p.goto(base + "#/insights")
    p.wait_for_selector(".stats .stat")
    assert p.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1")
    assert not errs, errs


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION >= "0.999.248"
