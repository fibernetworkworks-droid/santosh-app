"""v0.999.253 ROUTE CHECK - Hoola Route checked end to end again after R1-R8 (owner: "NOW CHECK THE ENTIRE ROUTE END
TO END"): every page walked in a real browser (computer + phone, light + dark) and the engine read through.

Engine faults found and fixed, each pinned here:
  - Stop pressed while a step ran was undone by the engine's next save (the run went on and ended 'done');
  - a run cut by a restart stayed 'running' for ever (the claim took only queued / sleeping runs);
  - a schedule with every_hours '2h' was stored, then broke the whole account's tick (no runs started at all);
  - a web request followed redirects to private addresses, and a saved sign-in header went to the redirect's site;
  - an app-event route marked every new item seen but started only 20 (the rest were lost);
  - runs were started without claiming them (could run twice); a test could run with real steps before its pins;
  - search never found values in other languages (stored as \\u escapes);
  - an n8n export with a number written as an expression gave a 500;
  - a route could start itself (dhara_run as a step), error routes could fail into each other for ever;
  - the 'wait for a reply' link was answered by a plain GET (an email link checker answers it for her) and two calls
    at once both went through;
  - steps inside a branch or a loop never showed in the run's step-by-step log;
  - Needs you showed an approval question with {{vars.a}} in it instead of the value;
  - switching a route on / off made an open editor's next save fail as 'changed since you opened it'.
Page faults: the past-run bar ran 265 px off a phone screen, the failing step was not marked on the canvas, the step
name was said twice ('boom: boom: ValueError'), form / chat / error routes showed the by-hand icon.
"""
import asyncio
import json
import shutil
import threading
import time
from pathlib import Path

import pytest

from tests.test_bazar import bz  # noqa: F401  (fresh DB fixture)

from app.agent import dhara_tools as D
from app.agent.tools import Ctx, HANDLERS, ToolError
from app.route import n8n as N
from app.route import runs as RU
from app.route import triggers as TR
from app.route import workspace as WS


def _wipe(t):
    shutil.rmtree(Path("data") / "dhara" / t, ignore_errors=True)


def _run(c):
    return asyncio.run(c)


def _save(t, name, steps, **kw):
    return _run(D.dhara_save(Ctx(tenant_id=t, conversation_id=""), name=name, steps=steps, **kw))


def _go(t, name, vars_=None):
    rid = D.create_run(t, D.get_workflow(t, name=name), vars_=vars_ or {})
    _run(D.execute_run(t, rid))
    return D.get_run(t, rid)


@pytest.fixture
def T(bz, monkeypatch):
    monkeypatch.setattr(D, "polite_s", 0)
    D._RUNNING.clear()
    t = "r250_check"
    _wipe(t)
    yield t
    D._RUNNING.clear()
    _wipe(t)


# ---------------------------------------------------------------- the run engine
def test_stop_while_a_step_runs_stays_stopped(T, monkeypatch):
    async def slow(ctx, **kw):
        await asyncio.sleep(0.4)
        return {"ok": True}
    monkeypatch.setitem(HANDLERS, "r250_slow", slow)
    _save(T, "slowly", [{"id": "wait_a_bit", "type": "tool", "name": "r250_slow"},
                        {"id": "after", "type": "set", "name": "x", "value": 1}])
    rid = D.create_run(T, D.get_workflow(T, name="slowly"))

    async def both():
        task = asyncio.ensure_future(D.execute_run(T, rid))
        await asyncio.sleep(0.1)
        D.update_run(T, rid, status="stopped")
        await task
    _run(both())
    r = D.get_run(T, rid)
    assert r["status"] == "stopped", "the engine's next save used to undo the stop and the run ended done"
    assert "x" not in r["context"]["vars"]


def test_a_run_cut_by_a_restart_is_picked_up_again(T):
    _save(T, "cut", [{"id": "a", "type": "set", "name": "x", "value": 1}])
    rid = D.create_run(T, D.get_workflow(T, name="cut"))
    D.update_run(T, rid, status="running", tries=1, updated_at=time.time() - 1000)
    assert D._claim(T, rid, 4, 180), "a 'running' run nobody wrote for long used to stay running for ever"
    D._RUNNING.add(f"{T}:{rid}")
    D.update_run(T, rid, status="running", updated_at=time.time() - 1000)
    assert not D._claim(T, rid, 9, 180), "never one this server is running right now"
    D._RUNNING.discard(f"{T}:{rid}")


def test_a_bad_schedule_is_refused_and_never_stops_the_others(T):
    with pytest.raises(ToolError):
        _save(T, "bad_sched", [{"id": "a", "type": "set", "name": "x", "value": 1}], trigger="schedule",
              trigger_spec={"every_hours": "2h", "timezone": "UTC"})
    _save(T, "ok_sched", [{"id": "a", "type": "set", "name": "x", "value": 1}], trigger="schedule",
          trigger_spec={"every_hours": 2, "timezone": "UTC"})
    _save(T, "ok_too", [{"id": "a", "type": "set", "name": "x", "value": 1}], trigger="schedule",
          trigger_spec={"every_hours": 3, "timezone": "UTC"})
    con = D._con(T)          # a schedule written before the check (or by hand) that cannot be read
    con.execute("UPDATE workflows SET trigger_spec = ?, next_due_at = ? WHERE name = 'ok_sched'",
                (json.dumps({"every_hours": "2h", "timezone": "UTC"}), time.time() - 5))
    con.execute("UPDATE workflows SET next_due_at = ? WHERE name = 'ok_too'", (time.time() - 5,))
    con.commit()
    con.close()
    due = D._scheduled_due(T)
    assert [w["name"] for w, _m in due] == ["ok_too"], "one broken schedule used to stop every route of the account"
    assert D.get_workflow(T, name="ok_sched")["next_due_at"] is None


def test_web_request_redirects_are_checked_and_sign_ins_stay_home(T, monkeypatch):
    import httpx
    from app.agent import scrape_tools as st
    calls = []

    def fake_get(url, headers=None, **kw):
        calls.append((url, dict(headers or {})))
        if "api.shop.example" in url:
            return httpx.Response(302, headers={"location": "https://other.example/land"}, request=httpx.Request("GET", url))
        return httpx.Response(200, json={"landed": True}, request=httpx.Request("GET", url))

    def guard(u):
        if "169.254" in u or "127.0.0.1" in u:
            raise ToolError("Only public addresses")
        return u
    monkeypatch.setattr(httpx, "get", fake_get)
    monkeypatch.setattr(st, "_guard_url", guard)
    WS.save_credential(T, {"name": "SHOP", "kind": "header", "host": "api.shop.example", "header": "X-Api-Key",
                           "value": "key_secret_9876"})
    _save(T, "hop", [{"id": "get", "type": "http", "url": "https://api.shop.example/o", "auth": "SHOP"}])
    r = _go(T, "hop")
    assert r["status"] == "done", r.get("error")
    assert calls[0][1].get("X-Api-Key") == "key_secret_9876"
    assert calls[1][0] == "https://other.example/land" and "X-Api-Key" not in calls[1][1], \
        "the sign-in header used to go to whatever site the redirect named"

    def to_private(url, headers=None, **kw):
        return httpx.Response(302, headers={"location": "http://169.254.169.254/latest"}, request=httpx.Request("GET", url))
    monkeypatch.setattr(httpx, "get", to_private)
    _save(T, "hop2", [{"id": "get", "type": "http", "url": "https://public.example/x"}])
    r = _go(T, "hop2")
    assert r["status"] == "failed" and "public" in (r["error"] or "").lower(), "a redirect to a private address was followed"


def test_app_items_beyond_one_look_are_not_lost(T, monkeypatch):
    feed = {"items": [{"id": 0, "title": "old"}]}

    async def lister(ctx, **kw):
        return dict(feed)
    monkeypatch.setitem(HANDLERS, "r250_list", lister)
    _save(T, "lots", [{"id": "n", "type": "set", "name": "got", "value": "{{vars.event.title}}"}], trigger="event",
          trigger_spec={"app": "app", "tool": "r250_list", "every_minutes": 5})
    wf = D.get_workflow(T, name="lots")
    assert _run(TR.poll(T, wf))["first_look"]
    feed["items"] = [{"id": i, "title": f"t{i}"} for i in range(25, 0, -1)] + [{"id": 0, "title": "old"}]
    one = _run(TR.poll(T, wf))
    assert one["new"] == 25 and one["started"] == 20 and one["waiting"] == 5
    two = _run(TR.poll(T, wf))
    assert two["started"] == 5, "the 5 over the limit used to be marked seen and never run"
    assert len(D.list_runs(T, wf_id=wf["id"], limit=100)) == 25


def test_a_test_run_carries_its_pins_from_the_start_and_starts_once(T):
    from fastapi.testclient import TestClient
    from app.main import app
    from app.config import get_settings
    from app.route import stepdata as SD
    t = get_settings().tenant_id
    _wipe(t)
    try:
        _save(t, "pinned", [{"id": "fetch", "type": "http", "url": "https://example.com/x"},
                            {"id": "after", "type": "set", "name": "v", "value": "{{steps.fetch.output.n}}"}])
        wf = D.get_workflow(t, name="pinned")
        SD.set_pin(t, wf, "fetch", {"n": 7})
        rid = D.create_run(t, wf, {}, extra={"_pins": {"fetch": {"n": 7}}})
        assert D.get_run(t, rid)["context"]["_pins"] == {"fetch": {"n": 7}}, "pins used to be written after the run existed"
        assert D._claim(t, rid, 4) and not D._claim(t, rid, 4), "a run can be claimed only once"
        with TestClient(app) as c:
            out = c.post(f"/api/route/routes/{wf['id']}/test", json={}).json()
            for _ in range(100):
                if D.get_run(t, out["run_id"])["status"] in ("done", "failed"):
                    break
                time.sleep(0.05)
        r = D.get_run(t, out["run_id"])
        assert r["status"] == "done" and r["context"]["vars"]["v"] == 7
    finally:
        _wipe(t)


def test_search_finds_values_in_any_language(T):
    _save(T, "names", [{"id": "a", "type": "set", "name": "x", "value": "{{vars.who}}"}])
    _go(T, "names", {"who": "Priyā Śarmā", "amount": "₹500"})
    assert RU.search(T, "Priyā")["runs"], "a name with ā was stored as \\u0101 and never found"
    assert RU.search(T, "₹500")["runs"]
    old = D.create_run(T, D.get_workflow(T, name="names"), {"who": "x"})      # a run kept the old (escaped) way
    con = D._con(T)
    con.execute("UPDATE runs SET context = ? WHERE id = ?", (json.dumps({"vars": {"who": "Zoë Old"}, "_start": {"who": "Zoë Old"}}), old))
    con.commit()
    con.close()
    assert [x["id"] for x in RU.search(T, "Zoë")["runs"]] == [old]


def test_n8n_numbers_written_as_expressions_become_placeholders():
    doc = {"name": "exprs", "nodes": [
        {"name": "Start", "type": "n8n-nodes-base.manualTrigger", "parameters": {}},
        {"name": "Limit", "type": "n8n-nodes-base.limit", "parameters": {"maxItems": "={{ $json.n }}"}},
        {"name": "Reply", "type": "n8n-nodes-base.respondToWebhook", "parameters": {"options": {"responseCode": "={{ 200 }}"}}}],
        "connections": {"Start": {"main": [[{"node": "Limit", "type": "main", "index": 0}]]},
                        "Limit": {"main": [[{"node": "Reply", "type": "main", "index": 0}]]}}}
    out = N.convert(doc)                       # used to raise ValueError -> a 500 on the page
    names = [p["node"] for p in out["report"]["placeholders"]]
    assert names == ["Limit", "Reply"] and "expression" in out["report"]["placeholders"][0]["why"]


def test_routes_cannot_start_themselves_or_ping_pong_on_errors(T):
    with pytest.raises(ToolError):
        _save(T, "loops", [{"id": "again", "type": "tool", "name": "dhara_run", "args": {"name": "loops"}}])
    _save(T, "reads", [{"id": "ls", "type": "tool", "name": "dhara_list"}])          # reading routes is fine
    _save(T, "a_fails", [{"id": "x", "type": "code", "code": "raise ValueError('a')"}], settings={"error_route": "b_fails"})
    _save(T, "b_fails", [{"id": "x", "type": "code", "code": "raise ValueError('b')"}], settings={"error_route": "a_fails"})
    _go(T, "a_fails")
    for _ in range(8):                         # run whatever the error routes queue, like the worker would
        q = [r for r in D.list_runs(T, limit=100) if r["status"] == "queued"]
        if not q:
            break
        for r in q:
            _run(D.execute_run(T, r["id"]))
    assert len(D.list_runs(T, limit=100)) <= 4, "two error routes used to fail into each other for ever"
    _save(T, "capped", [{"id": "a", "type": "set", "name": "x", "value": 1}], settings={"runs_per_day": 1})
    _go(T, "capped")
    with pytest.raises(ToolError):
        _run(D.dhara_run(Ctx(tenant_id=T, conversation_id=""), name="capped"))


def test_the_reply_link_needs_a_press_and_answers_once(T):
    from fastapi.testclient import TestClient
    from app.main import app
    _save(T, "waits", [{"id": "w", "type": "wait", "for": "call", "timeout_s": 3600},
                       {"id": "after", "type": "set", "name": "got", "value": "{{steps.w.output.body.ok}}"}])
    r = _go(T, "waits")
    url = r["context"]["vars"]["resume_url"]
    path = url[url.index("/api/dhara/resume/"):]
    with TestClient(app) as c:
        page = c.get(path + "?ok=yes", headers={"accept": "text/html"})
        assert page.status_code == 200 and "Send" in page.text
        assert D.get_run(T, r["id"])["status"] == "sleeping", "an email link checker opening it used to answer it"
        ok = c.post(path + "?ok=yes", headers={"accept": "text/html"})
        assert ok.status_code == 200 and "Sent" in ok.text
        again = c.post(path, json={"ok": "no"})
        assert again.status_code == 409
    for _ in range(100):
        if D.get_run(T, r["id"])["status"] == "done":
            break
        time.sleep(0.05)
    assert D.get_run(T, r["id"])["context"]["vars"]["got"] == "yes"


def test_branch_and_loop_steps_are_in_the_run_log(T):
    _save(T, "inner", [
        {"id": "big", "type": "condition", "filter": {"left": "{{vars.total}}", "op": "gt", "right": 20},
         "then": [{"id": "flag", "type": "set", "name": "big", "value": True}],
         "else": [{"id": "small", "type": "set", "name": "big", "value": False}]},
        {"id": "each", "type": "loop", "items": "{{vars.lines}}", "as": "line", "body": [
            {"id": "check", "type": "code", "code": "if '{{vars.line}}' == 'b':\n    raise ValueError('bad line {{vars.line}}')"}]}])
    r = _go(T, "inner", {"total": 30, "lines": ["a", "b"]})
    got = [(x["id"], x["status"], x.get("in")) for x in r["steps_log"]]
    assert ("flag", "ok", "big: if yes") in got, "steps inside a branch used to be missing from the log"
    assert ("check", "ok", "each: round 1") in got and ("check", "error", "each: round 2") in got
    assert RU.failed_step(r) == "check", "the step that failed inside the loop, not only the loop"
    from app.route import stepdata as SD
    assert SD._log_of(r["steps_log"])["check"]["status"] == "error"


def test_needs_you_shows_the_question_with_the_data(T):
    from fastapi.testclient import TestClient
    from app.main import app
    from app.config import get_settings
    t = get_settings().tenant_id
    _wipe(t)
    try:
        _save(t, "pay", [{"id": "ask", "type": "approval", "question": "Send {{vars.a}} payment?"}])
        _go(t, "pay", {"a": 50})
        with TestClient(app) as c:
            s = json.dumps(c.get("/api/route/summary").json())
        assert "Send 50 payment?" in s and "{{vars.a}}" not in s
    finally:
        _wipe(t)


def test_on_off_is_not_an_edit(T):
    _save(T, "toggle", [{"id": "a", "type": "set", "name": "x", "value": 1}])
    w = D.get_workflow(T, name="toggle")
    D.set_enabled(T, w["id"], False)
    D.set_enabled(T, w["id"], True)
    assert D.get_workflow(T, name="toggle")["updated_at"] == w["updated_at"], \
        "a switch used to make an open editor's next save fail as 'changed since you opened it'"


def test_huge_text_is_refused_before_it_is_built():
    from app.agent import dhara_data as DD
    with pytest.raises(DD.ExprError):
        DD._safe_replace("a" * 1000, "", "x" * 5000)
    with pytest.raises(DD.ExprError):
        DD._safe_join(["x" * 1000] * 3000, ",")
    assert DD._safe_replace("a-b", "-", "+") == "a+b" and DD._safe_join(["a", None, "c"], "/") == "a//c"


# ---------------------------------------------------------------- the pages in a real browser
@pytest.fixture
def br(bz, monkeypatch):
    sync_api = pytest.importorskip("playwright.sync_api")
    import os
    from tests.test_v161_console_e2e import _free_port
    from tests.test_v161_stream import KEY
    monkeypatch.setenv("API_KEY", KEY)
    monkeypatch.setattr(D, "polite_s", 0)
    from app.config import get_settings
    get_settings.cache_clear()
    t = get_settings().tenant_id
    _wipe(t)
    _save(t, "orders", [
        {"id": "each", "type": "loop", "items": "{{vars.lines}}", "as": "line", "body": [
            {"id": "seen", "type": "set", "name": "last", "value": "{{vars.line}}"}]},
        {"id": "boom", "type": "code", "code": "raise ValueError('row 14 has no total')"}])
    bad = _go(t, "orders", {"lines": ["a", "b"]})
    _save(t, "contact", [{"id": "got", "type": "set", "name": "x", "value": "{{vars.form.name}}"}], trigger="form",
          trigger_spec={"title": "Contact", "fields": [{"name": "name", "label": "Name"}]})
    _save(t, "pay", [{"id": "ask", "type": "approval", "question": "Send {{vars.a}} payment?"}])
    _go(t, "pay", {"a": 50})
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
        yield f"http://127.0.0.1:{port}/console/route", b, KEY, t, bad
        b.close()
        pw.stop()
    finally:
        srv.should_exit = True
        th.join(timeout=10)
        _wipe(t)


def test_the_pages_in_a_real_browser(br):
    base, b, key, t, bad = br
    wf = D.get_workflow(t, name="orders")
    for vw in (1440, 390):
        c = b.new_context(viewport={"width": vw, "height": 900})
        c.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
        p = c.new_page()
        errs = []
        p.on("pageerror", lambda e: errs.append(str(e)))
        p.goto(base + f"#/r/{wf['id']}/debug/{bad['id']}")
        p.wait_for_selector(".edbanner.debug #dbgPin")
        p.wait_for_timeout(400)
        assert p.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1"), \
            "the past-run bar used to run 265 px off a phone screen"
        txt = p.inner_text("#edBanner")
        assert "row 14 has no total" in txt and "boom: boom" not in txt.lower()
        assert p.locator('.nd.fail[data-node="boom"]').count() == 1, "the failing step is marked on the canvas"
        p.goto(base + f"#/run/{bad['id']}")
        p.wait_for_selector(".log .lrow")
        assert p.locator(".lrow.inner").count() == 2 and "in each: round 2" in p.inner_text(".log")
        p.goto(base + "#/")
        p.wait_for_selector(".needs .need")
        main_txt = p.inner_text("main")
        assert "Send 50 payment?" in main_txt and "{{vars.a}}" not in main_txt
        p.goto(base + "#/routes")
        p.wait_for_selector("tbody tr")
        assert p.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1")
        assert not errs, errs
        c.close()


def test_routes_list_uses_each_start_kinds_icon():
    js = (Path(__file__).resolve().parents[1] / "app" / "static" / "console" / "route.js").read_text()
    assert "svg(TKIC(r.trigger))" in js and "IC.bolt : IC.hand)" not in js


def test_version():
    from app.main import APP_VERSION
    assert tuple(int(x) for x in APP_VERSION.split(".")) >= (0, 999, 253)
