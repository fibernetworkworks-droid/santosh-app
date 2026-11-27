"""v0.999.239 FLOW STEPS (R4 of the Hoola Route plan; owner: "GO R4"; built as 0.999.238,
their PUBLIC FINANCE DESK took 0.999.238, both kept).

A pause anywhere inside a branch or a loop (a wait, an approval, a sub-route still running) now really pauses the run
and the resume goes on from the same step - before, an approval inside an if / else never waited and the steps after it
ran. New: merge two lists (one after the other, matched by a field like a join, side by side, keep (non-)matches),
run another route (wait for its result or start it and go on; up to 3 deep, never itself), stop the run (as an error or
as done), answer the webhook caller (a Respond step), wait up to 30 days or until a date and time in the route's time
zone, wait until someone calls the run's resume link, loops up to 1,000 items and branches / loops three levels deep.
"""
import asyncio
import shutil
import time
from pathlib import Path

import pytest

from tests.test_bazar import bz  # noqa: F401  (fresh DB fixture)

from app.agent import dhara_data as DD
from app.agent import dhara_tools as D
from app.agent.tools import Ctx, ToolError


def _wipe(t):
    shutil.rmtree(Path("data") / "dhara" / t, ignore_errors=True)


def _run(c):
    return asyncio.run(c)


def _save(t, name, steps, **kw):
    return _run(D.dhara_save(Ctx(tenant_id=t, conversation_id=""), name=name, steps=steps, **kw))


def _go(t, name, vars_=None):
    wf = D.get_workflow(t, name=name)
    rid = D.create_run(t, wf, vars_=vars_)
    _run(D.execute_run(t, rid))
    return rid


def _approve(t, rid):
    async def go():
        await D.dhara_control(Ctx(tenant_id=t, conversation_id=""), action="approve", run_id=rid)
        await D.drain()
    _run(go())


def test_approval_inside_a_branch_really_waits_and_resumes_there(bz, monkeypatch):
    monkeypatch.setattr(D, "polite_s", 0)
    t = "r4_appr"
    _wipe(t)
    try:
        _save(t, "pay_flow", [
            {"id": "first", "type": "set", "name": "a", "value": 1},
            {"id": "check", "type": "condition", "filter": {"left": "{{vars.a}}", "op": "eq", "right": 1},
             "then": [{"id": "before", "type": "set", "name": "b", "value": 2},
                      {"id": "ask", "type": "approval", "question": "Send {{vars.a}} payment?"},
                      {"id": "after", "type": "set", "name": "c", "value": 3}]},
            {"id": "last", "type": "set", "name": "d", "value": 4}])
        rid = _go(t, "pay_flow")
        r = D.get_run(t, rid)
        assert r["status"] == "waiting_approval"
        assert "c" not in r["context"]["vars"] and "d" not in r["context"]["vars"]   # the bug: these used to run
        assert r["context"]["_wait_q"] == "Send 1 payment?" and r["cursor"] == 1
        _approve(t, rid)
        r = D.get_run(t, rid)
        assert r["status"] == "done", r.get("error")
        v = r["context"]["vars"]
        assert (v["b"], v["c"], v["d"]) == (2, 3, 4)
        assert r["context"].get("_done") == [] and "_wait_mark" not in r["context"]   # marks pruned after the step
    finally:
        _wipe(t)


def test_wait_inside_a_loop_pauses_each_round_and_never_repeats_work(bz, monkeypatch):
    monkeypatch.setattr(D, "polite_s", 0)
    t = "r4_loopwait"
    _wipe(t)
    try:
        _save(t, "drip", [
            {"id": "each", "type": "loop", "items": "{{vars.people}}", "as": "who", "body": [
                {"id": "count", "type": "set", "name": "seen", "value": "{{ default(vars.seen, 0) + 1 }}"},
                {"id": "pause", "type": "wait", "amount": 2, "unit": "days"}]},
            {"id": "end", "type": "set", "name": "done", "value": True}])
        rid = _go(t, "drip", {"people": ["a", "b"]})
        r = D.get_run(t, rid)
        assert r["status"] == "sleeping" and r["context"]["vars"]["seen"] == 1 and r["cursor"] == 0
        assert r["next_wake_at"] - time.time() > 2 * 86400 - 60
        assert r["context"]["vars"]["who"] == "a"
        for expect_seen, expect_status in ((2, "sleeping"), (2, "done")):
            D.update_run(t, rid, status="queued", next_wake_at=None)
            _run(D.execute_run(t, rid))
            r = D.get_run(t, rid)
            assert r["context"]["vars"]["seen"] == expect_seen and r["status"] == expect_status, r.get("error")
        assert r["context"]["vars"]["done"] is True and r["context"]["vars"]["who"] == "b"
    finally:
        _wipe(t)


def test_router_ways_are_decided_once_and_a_finished_way_never_runs_again(bz, monkeypatch):
    monkeypatch.setattr(D, "polite_s", 0)
    t = "r4_router"
    _wipe(t)
    try:
        _save(t, "ways", [
            {"id": "sw", "type": "router", "routes": [
                {"label": "Big", "filter": {"left": "{{vars.n}}", "op": "gt", "right": 5},
                 "steps": [{"id": "big", "type": "set", "name": "n", "value": 1},
                           {"id": "ok_big", "type": "approval", "question": "Big one, go?"}]},
                {"label": "Small", "filter": {"left": "{{vars.n}}", "op": "lte", "right": 5},
                 "steps": [{"id": "small", "type": "set", "name": "small", "value": True}]}]}])
        rid = _go(t, "ways", {"n": 9})
        assert D.get_run(t, rid)["status"] == "waiting_approval"
        _approve(t, rid)
        r = D.get_run(t, rid)
        assert r["status"] == "done" and "small" not in r["context"]["vars"]   # n became 1 but the ways were fixed
    finally:
        _wipe(t)


def test_merge_two_lists(bz):
    R = lambda v, ctx: D.resolve(v, ctx)  # noqa: E731
    ctx = {"vars": {"a": [{"id": 1, "n": "x"}, {"id": 2, "n": "y"}, {"id": 4}],
                    "b": [{"id": 1, "p": 10}, {"id": 3, "p": 30}, {"id": 1, "p": 11}]}, "steps": {}}
    m = lambda **k: DD.run("t", {"op": "merge", "a": "{{vars.a}}", "b": "{{vars.b}}", **k}, ctx, R)  # noqa: E731
    assert len(m(mode="append")) == 6
    assert m(mode="by_key", key="id") == [{"id": 1, "n": "x", "p": 10}, {"id": 1, "n": "x", "p": 11}]
    assert len(m(mode="by_key", key="id", join="left")) == 4
    assert {x["id"] for x in m(mode="by_key", key="id", join="outer")} == {1, 2, 3, 4}
    assert m(mode="by_position") == [{"id": 1, "n": "x", "p": 10}, {"id": 3, "n": "y", "p": 30}, {"id": 1, "p": 11}]
    assert [x["id"] for x in m(mode="keep_matches", key="id")] == [1]
    assert [x["id"] for x in m(mode="keep_non_matches", key="id")] == [2, 4]
    with pytest.raises(ToolError):
        DD.validate({"op": "merge", "a": "x", "b": "y", "mode": "by_key"}, "m")


def test_subroute_waits_for_the_result_and_refuses_a_loop(bz, monkeypatch):
    monkeypatch.setattr(D, "polite_s", 0)
    t = "r4_sub"
    _wipe(t)
    try:
        _save(t, "child_route", [{"id": "double", "type": "set", "name": "out", "value": "{{ vars.x * 2 }}"},
                                 {"id": "give", "type": "data", "op": "fields", "values": {"total": "{{vars.out}}"}}])
        _save(t, "parent_route", [
            {"id": "call", "type": "subroute", "route": "child_route", "vars": {"x": "{{vars.n}}"}},
            {"id": "use", "type": "set", "name": "got", "value": "{{steps.call.output.result.total}}"}])
        rid = _go(t, "parent_route", {"n": 21})
        r = D.get_run(t, rid)
        assert r["status"] == "done", r.get("error")
        assert r["context"]["vars"]["got"] == 42
        assert r["context"]["steps"]["call"]["output"]["vars"]["out"] == 42
        # a route that starts itself is refused
        _save(t, "selfish", [{"id": "again", "type": "subroute", "route": "selfish"}])
        rid = _go(t, "selfish")
        r = D.get_run(t, rid)
        assert r["status"] == "failed" and "cannot start itself" in r["error"]
        # start and go on
        _save(t, "fire", [{"id": "go", "type": "subroute", "route": "child_route", "vars": {"x": 1}, "wait": False}])
        rid = _go(t, "fire")
        r = D.get_run(t, rid)
        assert r["status"] == "done" and r["context"]["steps"]["go"]["output"]["started"] is True
        child = D.get_run(t, r["context"]["steps"]["go"]["output"]["run_id"])
        assert child["status"] == "queued" and child["context"]["_depth"] == 1
    finally:
        _wipe(t)


def test_subroute_that_pauses_makes_the_parent_wait(bz, monkeypatch):
    monkeypatch.setattr(D, "polite_s", 0)
    t = "r4_subwait"
    _wipe(t)
    try:
        _save(t, "needs_ok", [{"id": "ok", "type": "approval", "question": "Fine?"},
                              {"id": "v", "type": "set", "name": "r", "value": "yes"}])
        _save(t, "outer", [{"id": "inner", "type": "subroute", "route": "needs_ok"},
                           {"id": "after", "type": "set", "name": "after", "value": "{{steps.inner.output.vars.r}}"}])
        rid = _go(t, "outer")
        r = D.get_run(t, rid)
        assert r["status"] == "sleeping" and r["pause_reason"] == "waiting_subroute" and r["cursor"] == 0
        cid = r["context"]["_subs"]["/inner"]
        assert D.get_run(t, cid)["status"] == "waiting_approval"
        _approve(t, cid)
        assert D.get_run(t, cid)["status"] == "done"
        D.update_run(t, rid, status="queued", next_wake_at=None)
        _run(D.execute_run(t, rid))
        r = D.get_run(t, rid)
        assert r["status"] == "done" and r["context"]["vars"]["after"] == "yes"
    finally:
        _wipe(t)


def test_stop_step_as_error_and_as_done(bz, monkeypatch):
    monkeypatch.setattr(D, "polite_s", 0)
    t = "r4_stop"
    _wipe(t)
    try:
        _save(t, "guard", [
            {"id": "chk", "type": "condition", "filter": {"left": "{{vars.amount}}", "op": "gt", "right": 100},
             "then": [{"id": "no", "type": "stop", "as": "error", "message": "Too much: {{vars.amount}}"}],
             "else": [{"id": "fine", "type": "stop", "as": "done", "message": "Small, nothing to do"}]},
            {"id": "never", "type": "set", "name": "never", "value": 1}])
        r = D.get_run(t, _go(t, "guard", {"amount": 500}))
        assert r["status"] == "failed" and "Too much: 500" in r["error"] and "never" not in r["context"]["vars"]
        r = D.get_run(t, _go(t, "guard", {"amount": 5}))
        assert r["status"] == "done" and "never" not in r["context"]["vars"]
        with pytest.raises(ToolError):
            _save(t, "bad_stop", [{"id": "s", "type": "stop", "as": "maybe"}])
    finally:
        _wipe(t)


def test_respond_step_answers_the_webhook_caller(bz, monkeypatch):
    monkeypatch.setattr(D, "polite_s", 0)
    monkeypatch.setattr(D, "_TOKEN_MIN_RATE_S", 0)
    t = "r4_resp"
    _wipe(t)
    try:
        out = _save(t, "answers", [
            {"id": "sum", "type": "set", "name": "total", "value": "{{ vars.body.a + vars.body.b }}"},
            {"id": "reply", "type": "respond", "status": 201, "body": {"total": "{{vars.total}}"}},
            {"id": "later", "type": "set", "name": "later", "value": 1}],
            trigger="webhook")
        token = out["webhook_note"].rsplit(" ", 1)[1]

        async def go():
            res = await D.webhook_call(token, {"a": 2, "b": 3})
            await D.drain()
            return res
        res = _run(go())
        assert res["answered"] and res["status"] == 201 and res["answer"] == {"total": 5}
        r = D.get_run(t, res["run_id"])
        assert r["status"] == "done" and r["context"]["vars"]["later"] == 1
        from fastapi.testclient import TestClient
        from app.main import app
        resp = TestClient(app).post(f"/api/dhara/hook/{token}", json={"a": 10, "b": 1})
        assert resp.status_code == 201 and resp.json() == {"total": 11}
    finally:
        _wipe(t)


def test_wait_for_a_call_goes_on_when_the_resume_link_is_called(bz, monkeypatch):
    monkeypatch.setattr(D, "polite_s", 0)
    t = "r4_call"
    _wipe(t)
    try:
        _save(t, "ask_back", [
            {"id": "link", "type": "set", "name": "link", "value": "{{vars.resume_url}}"},
            {"id": "hold", "type": "wait", "for": "call", "timeout_s": 3 * 86400, "on_timeout": "fail"},
            {"id": "use", "type": "set", "name": "answer", "value": "{{steps.hold.output.body.choice}}"}])
        rid = _go(t, "ask_back")
        r = D.get_run(t, rid)
        assert r["status"] == "sleeping" and r["pause_reason"] == "waiting_call"
        link = r["context"]["vars"]["link"]
        assert link.startswith("https://santosh.example.in/api/dhara/resume/" + rid + ".")
        token = link.rsplit("/", 1)[1]
        assert D.resume_call(rid + ".wrong", {})["status"] == 404
        from fastapi.testclient import TestClient
        from app.main import app
        resp = TestClient(app).post(f"/api/dhara/resume/{token}", json={"choice": "blue"})
        assert resp.status_code == 200, resp.text
        _run(D.drain())
        r = D.get_run(t, rid)
        if r["status"] == "queued":
            _run(D.execute_run(t, rid))
            r = D.get_run(t, rid)
        assert r["status"] == "done", r.get("error")
        assert r["context"]["vars"]["answer"] == "blue"
        assert D.resume_call(token, {})["status"] == 409          # once only
        # nobody calls: on_timeout fail
        rid = _go(t, "ask_back")
        c = D.get_run(t, rid)["context"]
        c["_call"]["until"] = time.time() - 1
        D.update_run(t, rid, status="queued", next_wake_at=None, context=c)
        _run(D.execute_run(t, rid))
        r = D.get_run(t, rid)
        assert r["status"] == "failed" and "resume link" in r["error"]
    finally:
        _wipe(t)


def test_long_waits_dates_and_the_route_time_zone(bz):
    for ok in ({"duration_s": 20 * 86400}, {"amount": 3, "unit": "days"}, {"until": "2031-01-02 09:30"},
               {"until": "07:15"}, {"for": "call", "timeout_s": 600}):
        D._validate_wait({"id": "w", "type": "wait", **ok}, "w")
    for bad in ({"duration_s": 31 * 86400}, {"amount": 5, "unit": "weeks"}, {"until": "tomorrow"},
                {"for": "email"}, {"for": "call", "timeout_s": 10}, {}):
        with pytest.raises(ToolError):
            D._validate_wait({"id": "w", "type": "wait", **bad}, "w")
    from datetime import datetime, timedelta
    from zoneinfo import ZoneInfo
    tz = ZoneInfo("America/New_York")
    at = (datetime.now(tz) + timedelta(days=2)).replace(second=0, microsecond=0)
    secs = D._wait_secs({"until": at.strftime("%Y-%m-%d %H:%M")}, {"_tz": "America/New_York", "vars": {}, "steps": {}})
    assert abs(secs - (at - datetime.now(tz)).total_seconds()) < 5
    assert D._wait_secs({"until": "2020-01-01 10:00"}, {"vars": {}, "steps": {}}) == 0    # a past moment: go on


def test_loops_of_many_items_and_three_levels_deep(bz, monkeypatch):
    monkeypatch.setattr(D, "polite_s", 0)
    t = "r4_deep"
    _wipe(t)
    try:
        _save(t, "big_loop", [{"id": "each", "type": "loop", "items": "{{vars.xs}}", "body": [
            {"id": "add", "type": "set", "name": "sum", "value": "{{ default(vars.sum, 0) + item }}"}]}])
        r = D.get_run(t, _go(t, "big_loop", {"xs": list(range(600))}))
        assert r["status"] == "done", r.get("error")
        assert r["context"]["vars"]["sum"] == sum(range(600))
        _save(t, "nested", [{"id": "rows", "type": "loop", "items": "{{vars.grid}}", "as": "row", "body": [
            {"id": "cells", "type": "loop", "items": "{{vars.row}}", "body": [
                {"id": "odd", "type": "condition", "filter": {"left": "{{ item % 2 }}", "op": "eq", "right": 1},
                 "then": [{"id": "tick", "type": "set", "name": "odd", "value": "{{ default(vars.odd, 0) + 1 }}"}]}]},
            {"id": "row_done", "type": "set", "name": "rows_done", "value": "{{ default(vars.rows_done, 0) + 1 }}"}]}])
        r = D.get_run(t, _go(t, "nested", {"grid": [[1, 2, 3], [4, 5]]}))
        assert r["status"] == "done", r.get("error")
        assert r["context"]["vars"]["odd"] == 3 and r["context"]["vars"]["rows_done"] == 2
        four = {"id": "l1", "type": "condition", "left": "1", "op": "eq", "right": "1", "then": [
            {"id": "l2", "type": "condition", "left": "1", "op": "eq", "right": "1", "then": [
                {"id": "l3", "type": "condition", "left": "1", "op": "eq", "right": "1", "then": [
                    {"id": "l4", "type": "condition", "left": "1", "op": "eq", "right": "1", "then": [
                        {"id": "x", "type": "set", "name": "v", "value": 1}]}]}]}]}
        with pytest.raises(ToolError):
            _save(t, "too_deep", [four])
    finally:
        _wipe(t)


def test_waiting_time_does_not_use_up_the_run_time_limit(bz, monkeypatch):
    monkeypatch.setattr(D, "polite_s", 0)
    t = "r4_clock"
    _wipe(t)
    try:
        _save(t, "slow_week", [{"id": "w", "type": "wait", "duration_s": 7 * 86400},
                               {"id": "after", "type": "set", "name": "after", "value": 1}])
        rid = _go(t, "slow_week")
        D.update_run(t, rid, status="queued", next_wake_at=None, started_at=time.time() - 7 * 86400)
        _run(D.execute_run(t, rid))
        r = D.get_run(t, rid)
        assert r["status"] == "done" and r["context"]["vars"]["after"] == 1, r.get("error")
    finally:
        _wipe(t)


def test_page_and_catalog_know_the_flow_steps(bz):
    from app.route import editor as E
    keys = {k["key"] for k in E.KINDS}
    assert {"subroute", "stop", "respond", "wait_call", "merge"} <= keys
    js = (Path(__file__).resolve().parents[1] / "app" / "static" / "console" / "route.js").read_text()
    for part in ("Run another route", "Stop the run", "Answer the caller", "Until its link is called", "Merge two lists",
                 "waitWords", "pauseWords", "subOf", "{{vars.resume_url}}", "up to 1,000"):
        assert part in js, part
    from app.route import chat as RC
    assert "resume_url" in RC.RULES and "sub-route" in RC.RULES


def test_a_web_request_body_is_data_not_steps(bz):
    t = "r4_http"
    _wipe(t)
    try:
        _save(t, "post_it", [{"id": "send", "type": "http", "method": "POST", "url": "https://example.com/x",
                              "body": {"name": "{{vars.name}}", "list": [1, 2]}}])
        assert D.get_workflow(t, name="post_it")["steps"][0]["body"]["list"] == [1, 2]
    finally:
        _wipe(t)


# ---------------------------------------------------------------- a real browser
@pytest.fixture
def br4(bz, monkeypatch):
    import os
    import threading
    sync_api = pytest.importorskip("playwright.sync_api")
    from tests.test_v161_console_e2e import _free_port
    from tests.test_v161_stream import KEY
    monkeypatch.setenv("API_KEY", KEY)
    from app.config import get_settings
    get_settings.cache_clear()
    t = get_settings().tenant_id
    _wipe(t)
    _save(t, "helper_route", [{"id": "x", "type": "set", "name": "x", "value": 1}])
    _save(t, "flow_route", [{"id": "first", "type": "set", "name": "a", "value": 1}])
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


def test_add_the_flow_steps_in_a_real_browser(br4):
    base, b, key, t = br4
    wf = D.get_workflow(t, name="flow_route")
    c = b.new_context(viewport={"width": 1440, "height": 900})
    c.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    p = c.new_page()
    errs = []
    p.on("pageerror", lambda e: errs.append(str(e)))
    p.goto(base + "#/r/" + wf["id"])
    p.wait_for_selector(".nd[data-node='first']")

    def add(after, q, kind):
        p.click(f".nd[data-node='{after}'] .addaf", force=True)
        p.fill("#addQ", q)
        p.wait_for_selector(f"#addList .arow[data-kind='{kind}']")
        p.click(f"#addList .arow[data-kind='{kind}']")
    add("first", "another route", "subroute")
    p.wait_for_selector("#edPanel [data-k='route']")
    p.fill("#edPanel [data-k='route']", "helper_route")
    p.fill("#edPanel [data-k='svars']", '{"n": "{{vars.a}}"}')
    sid = D.get_workflow(t, name="flow_route")["steps"][0]["id"]  # noqa: F841  (still the old one until saved)
    p.click("#edSave")
    p.wait_for_function("() => document.querySelector('#edState').innerText === 'Saved'", timeout=10000)
    steps = D.get_workflow(t, wf_id=wf["id"])["steps"]
    assert steps[1]["type"] == "subroute" and steps[1]["route"] == "helper_route" and steps[1]["vars"] == {"n": "{{vars.a}}"}
    add(steps[1]["id"], "reply", "wait_call")
    p.wait_for_selector("#edPanel [data-k='wtimeout']")
    p.fill("#edPanel [data-k='wtimeout']", "48")
    p.select_option("#edPanel [data-k='wkind']", "time")
    p.wait_for_selector("#edPanel [data-k='wamount']")
    p.fill("#edPanel [data-k='wamount']", "3")
    p.select_option("#edPanel [data-k='wunit']", "days")
    add(D.get_workflow(t, wf_id=wf["id"])["steps"][1]["id"], "stop", "stop")
    p.wait_for_selector("#edPanel [data-k='message']")
    p.select_option("#edPanel [data-k='as']", "done")
    p.fill("#edPanel [data-k='message']", "All good")
    p.click("#edSave")
    p.wait_for_function("() => document.querySelector('#edState').innerText === 'Saved'", timeout=10000)
    steps = D.get_workflow(t, wf_id=wf["id"])["steps"]
    kinds = [s["type"] for s in steps]
    assert kinds == ["set", "subroute", "stop", "wait"], kinds
    w = steps[3]
    assert w["amount"] == 3 and w["unit"] == "days" and "for" not in w
    assert steps[2]["as"] == "done" and steps[2]["message"] == "All good"
    world = p.inner_text("#world")
    assert "Run another route" in world or "Helper route" in world
    assert "3 days" in world and "Ends as done" in world
    assert not errs, errs


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.999.239"
