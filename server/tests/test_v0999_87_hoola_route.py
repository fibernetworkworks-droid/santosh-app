"""v0.999.87 HOOLA ROUTE - the automation page on the DHARA engine (owner: "GO" on the Hoola Route panel canvas,
after "NOW MAKE IT IN ENGLISH AND FOR GLOBAL USER NOT ONLY FOR INDIA").

Tested for real, offline: the filter language (every operator, case-insensitive text, numbers as text, dates,
groups, nesting, refusals), the router (filtered routes, a route without a filter, the fallback), the filter gate
(a run that ends cleanly), every error directive (ignore, resume, commit, rollback, break -> retry later -> kept as
Incomplete -> hand retry), a retried router never re-runs a step that already finished, errors-in-a-row switching
a route off, the error route, the global scheduler (any time zone, weekdays, month days, dates, once, every N
minutes, quiet hours, a country's public holidays, end date) with the legacy IST spec unchanged, settings stored
and kept, the daily run cap, the /api/route/* page API end to end, the page itself (served, CSP-safe, house tokens,
the Tools card) and the version pin.
"""
import asyncio
import shutil
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from tests.test_bazar import bz  # noqa: F401  (the env fixture: fresh DB, dry-run WhatsApp)

from app.agent import dhara_tools as D
from app.agent.tools import Ctx, HANDLERS, ToolError

T = "route-test-tenant"
CTX = Ctx(tenant_id=T, conversation_id="c1")


def _wipe(tenant):
    shutil.rmtree(Path("data") / "dhara" / tenant, ignore_errors=True)


@pytest.fixture(autouse=True)
def _clean(monkeypatch):
    monkeypatch.setattr(D, "polite_s", 0)
    D._RUNNING.clear()
    _wipe(T)
    yield
    D._RUNNING.clear()
    _wipe(T)


def _run(coro):
    return asyncio.run(coro)


def _go(name, steps, **kw):
    """Save a workflow and run it to its first honest stop; returns the run row."""
    wf = _run(D.dhara_save(CTX, name=name, steps=steps, **kw))
    w = D.get_workflow(T, wf_id=wf["workflow_id"])
    rid = D.create_run(T, w)
    _run(D.execute_run(T, rid))
    return D.get_run(T, rid)


def _again(run):
    """Wake a parked run and let it continue (what the tick does)."""
    D.update_run(T, run["id"], status="queued", next_wake_at=None)
    _run(D.execute_run(T, run["id"]))
    return D.get_run(T, run["id"])


# ---------------------------------------------------------------- the filter language

def test_filter_every_operator():
    one = D._one
    assert one("x", "exists", None, False) and one(None, "not_exists", None, False)
    assert one("", "empty", None, False) and one([1], "not_empty", None, False)
    assert one("Paid", "eq", "paid", True) and not one("Paid", "eq", "paid", False)
    assert one("1,200", "gt", 1000, False) and one(5, "gte", "5", False) and one("3", "lt", 4, False) and one(4, "lte", 4, False)
    assert one(7, "between", [5, 10], False) and not one(11, "between", [5, 10], False)
    assert one("Order shipped", "contains", "SHIP", True) and one(["a", "b"], "contains", "b", False)
    assert one("hello", "not_contains", "z", False)
    assert one("INV-22", "starts_with", "inv", True) and one("report.pdf", "ends_with", ".pdf", False)
    assert one("ORD-2291", "matches", r"^ORD-\d+$", False)
    assert one("2026-01-01", "before", "2026-06-01", False) and one("2026-12-01T10:00", "after", "2026-06-01", False)
    assert one("yes", "is_true", None, False) and one(False, "is_false", None, False)
    assert one("US", "in", ["US", "GB"], False) and one("FR", "not_in", "US, GB", False)
    assert one([1, 2, 3], "length_eq", 3, False) and one("abcd", "length_gt", 2, False) and one([], "length_lt", 1, False)
    assert one(5, "eq", "5", False) and one(5, "ne", "6", False)
    # values that cannot be compared are simply False, never an exception
    assert not one("abc", "gt", 3, False) and not one(None, "before", "2026-01-01", False)


def test_filter_groups_and_refusals():
    ctx = {"vars": {"total": "640", "pay": "cod", "country": "GB"}, "steps": {}}
    f = {"all": [{"left": "{{vars.pay}}", "op": "eq", "right": "COD", "ci": True},
                 {"any": [{"left": "{{vars.total}}", "op": "gt", "right": 500},
                          {"left": "{{vars.country}}", "op": "in", "right": ["US"]}]}]}
    D.validate_filter(f)
    assert D.eval_filter(f, ctx) is True
    ctx["vars"]["total"] = "120"
    assert D.eval_filter(f, ctx) is False
    for bad, word in (({"left": "x", "op": "nope"}, "unknown"), ({"left": "x", "op": "matches", "right": "("}, "regular"),
                      ({"left": "x", "op": "between", "right": 3}, "between"), ({"op": "eq", "right": 1}, "left"),
                      ({"all": []}, "non-empty"), ("text", "object")):
        with pytest.raises(ToolError) as e:
            D.validate_filter(bad)
        assert word in str(e.value)
    deep = {"left": "x", "op": "exists"}
    for _ in range(6):
        deep = {"all": [deep]}
    with pytest.raises(ToolError):
        D.validate_filter(deep)


# ---------------------------------------------------------------- router + filter gate

def _router(pay):
    return [
        {"id": "pay", "type": "set", "name": "pay", "value": pay},
        {"id": "split", "type": "router", "routes": [
            {"label": "Paid online", "filter": {"left": "{{vars.pay}}", "op": "eq", "right": "online"},
             "steps": [{"id": "r1", "type": "set", "name": "went", "value": "online"}]},
            {"label": "Cash", "filter": {"left": "{{vars.pay}}", "op": "eq", "right": "cod"},
             "steps": [{"id": "r2", "type": "set", "name": "went", "value": "cod"}]},
            {"label": "Always", "steps": [{"id": "r3", "type": "set", "name": "always", "value": "yes"}]}],
         "fallback": [{"id": "fb", "type": "set", "name": "went", "value": "fallback"}]},
        {"id": "after", "type": "set", "name": "after", "value": "{{vars.went}}"}]


def test_router_runs_matching_routes_and_fallback(bz):
    r = _go("order_router", _router("cod"))
    assert r["status"] == "done"
    v = r["context"]["vars"]
    assert v["went"] == "cod" and v["always"] == "yes" and v["after"] == "cod"
    assert r["context"]["steps"]["split"]["output"]["routes"] == ["Cash", "Always"]
    r2 = _go("order_router2", _router("cheque"))
    assert r2["context"]["vars"]["went"] == "fallback"
    assert r2["context"]["steps"]["split"]["output"]["routes"] == ["Always", "fallback"]


def test_router_validation(bz):
    with pytest.raises(ToolError):
        _run(D.dhara_save(CTX, name="bad_router", steps=[{"id": "r", "type": "router", "routes": []}]))
    with pytest.raises(ToolError):
        _run(D.dhara_save(CTX, name="bad_router2", steps=[{"id": "r", "type": "router", "routes": [{"label": "x", "steps": []}]}]))
    nested = [{"id": "r", "type": "router", "routes": [{"label": "x", "steps": [
        {"id": "r_in", "type": "router", "routes": [{"label": "y", "steps": [{"id": "z", "type": "set", "name": "z", "value": 1}]}]}]}]}]
    with pytest.raises(ToolError) as e:
        _run(D.dhara_save(CTX, name="nested_router", steps=nested))
    assert "one level" in str(e.value)


def test_filter_step_ends_the_run_cleanly(bz):
    steps = [{"id": "amt", "type": "set", "name": "amt", "value": 40},
             {"id": "big_only", "type": "filter", "filter": {"left": "{{vars.amt}}", "op": "gt", "right": 100}},
             {"id": "never", "type": "set", "name": "reached", "value": True}]
    r = _go("big_orders_only", steps)
    assert r["status"] == "done" and "reached" not in r["context"]["vars"]
    assert r["steps_log"][-1]["status"] == "filtered"


# ---------------------------------------------------------------- error directives

FAIL = {"id": "boom", "type": "tool", "name": "no_such_tool_here"}


def test_on_error_ignore_resume_commit_rollback(bz):
    r = _go("ignore_it", [{**FAIL, "on_error": "ignore"}, {"id": "next", "type": "set", "name": "ok", "value": 1}])
    assert r["status"] == "done" and r["context"]["vars"]["ok"] == 1
    assert r["steps_log"][0]["status"] == "ignored"
    r = _go("resume_it", [{**FAIL, "on_error": {"do": "resume", "value": {"rows": 0}}},
                          {"id": "use", "type": "set", "name": "rows", "value": "{{steps.boom.output.rows}}"}])
    assert r["status"] == "done" and r["context"]["vars"]["rows"] == 0
    r = _go("commit_it", [{**FAIL, "on_error": "commit"}, {"id": "never", "type": "set", "name": "x", "value": 1}])
    assert r["status"] == "done" and "x" not in r["context"]["vars"] and "commit" in r["error"]
    r = _go("rollback_it", [{**FAIL, "on_error": "rollback"}])
    assert r["status"] == "failed" and "cannot be undone" in r["error"]
    with pytest.raises(ToolError):
        _run(D.dhara_save(CTX, name="bad_oe", steps=[{**FAIL, "on_error": {"do": "explode"}}]))


def test_break_retries_later_then_incomplete_then_hand_retry(bz):
    r = _go("flaky_sheet", [{**FAIL, "on_error": {"do": "break", "retries": 2, "wait_min": 10}}])
    assert r["status"] == "sleeping" and r["pause_reason"] == "retry" and r["tries"] == 0
    assert 9 * 60 < r["next_wake_at"] - time.time() <= 10 * 60 + 5
    r = _again(r)
    assert r["status"] == "sleeping" and r["context"]["_retries_boom"] == 2
    r = _again(r)
    assert r["status"] == "incomplete" and r["pause_reason"] == "retries_used"
    out = _run(D.dhara_control(CTX, action="retry", run_id=r["id"]))
    assert out["status"] == "queued"
    _run(D.drain())
    r = D.get_run(T, r["id"])
    assert r["status"] == "sleeping"          # its automatic retries came back with the hand retry
    assert D.forget_old_runs(T, keep_days=1, keep=0) == 0   # an unfinished run is never forgotten


def test_retried_router_never_reruns_a_finished_step(bz, monkeypatch):
    calls = []

    async def count_tool(ctx, **kw):
        calls.append(1)
        return {"sent": len(calls)}
    monkeypatch.setitem(HANDLERS, "route_test_counter", count_tool)
    steps = [{"id": "rt", "type": "router", "routes": [{"label": "all", "steps": [
        {"id": "send", "type": "tool", "name": "route_test_counter"},
        {**FAIL, "id": "sheet", "on_error": {"do": "break", "retries": 1, "wait_min": 1}}]}]}]
    r = _go("no_double_send", steps)
    assert r["status"] == "sleeping" and len(calls) == 1 and "rt#0/send" in r["context"]["_done"]
    r = _again(r)
    assert len(calls) == 1, "the message step ran twice on a retry"
    assert r["status"] == "incomplete"


def test_errors_in_a_row_switch_the_route_off_and_start_the_error_route(bz):
    _run(D.dhara_save(CTX, name="tell_me", steps=[{"id": "n", "type": "set", "name": "seen", "value": "{{vars.failed_route}}"}]))
    wf = _run(D.dhara_save(CTX, name="nightly_sync", steps=[FAIL], trigger="schedule",
                           trigger_spec={"timezone": "Europe/London", "at": ["02:00"]},
                           settings={"stop_after_errors": 2, "error_route": "tell_me"}))
    w = D.get_workflow(T, wf_id=wf["workflow_id"])
    assert w["settings"]["stop_after_errors"] == 2 and w["settings"]["error_route"] == "tell_me"
    for _ in range(2):
        rid = D.create_run(T, D.get_workflow(T, wf_id=w["id"]))
        _run(D.execute_run(T, rid))
    w = D.get_workflow(T, wf_id=w["id"])
    assert w["enabled"] == 0 and w["consecutive_errors"] == 2
    er = D.get_workflow(T, name="tell_me")
    runs = D.list_runs(T, wf_id=er["id"])
    assert len(runs) == 2
    assert D.get_run(T, runs[0]["id"])["context"]["vars"]["failed_route"] == "nightly_sync"
    # a good run resets the count
    D.set_enabled(T, w["id"], True)
    _run(D.dhara_save(CTX, name="nightly_sync", steps=[{"id": "ok", "type": "set", "name": "a", "value": 1}],
                      trigger="schedule", trigger_spec={"timezone": "Europe/London", "at": ["02:00"]}))
    w = D.get_workflow(T, wf_id=w["id"])
    assert w["settings"]["stop_after_errors"] == 2, "settings=None must keep the route's settings"
    rid = D.create_run(T, w)
    _run(D.execute_run(T, rid))
    assert D.get_workflow(T, wf_id=w["id"])["consecutive_errors"] == 0


# ---------------------------------------------------------------- the global scheduler

def _ts(y, mo, d, h=0, mi=0, tz="UTC"):
    return datetime(y, mo, d, h, mi, tzinfo=ZoneInfo(tz)).timestamp()


def _local(ts, tz):
    return datetime.fromtimestamp(ts, ZoneInfo(tz))


def test_schedule_any_time_zone_weekdays_monthdays_dates_once():
    ny = "America/New_York"
    nxt = D.next_due({"trigger_spec": {"timezone": ny, "days": ["mon", "wed"], "at": ["09:00"]}}, _ts(2026, 11, 21, 12))
    t = _local(nxt, ny)
    assert (t.strftime("%a"), t.hour, t.minute, t.day) == ("Mon", 9, 0, 23)
    nxt = D.next_due({"trigger_spec": {"timezone": "Asia/Tokyo", "monthdays": [1, 15], "at": ["08:30"]}}, _ts(2026, 11, 21))
    t = _local(nxt, "Asia/Tokyo")
    assert (t.month, t.day, t.hour, t.minute) == (12, 1, 8, 30)
    nxt = D.next_due({"trigger_spec": {"timezone": "Europe/Berlin", "dates": ["2027-02-10"], "at": ["10:00"]}}, _ts(2026, 11, 21))
    assert _local(nxt, "Europe/Berlin").strftime("%Y-%m-%d %H:%M") == "2027-02-10 10:00"
    assert D.next_due({"trigger_spec": {"timezone": "UTC", "once": "2026-11-01T09:00"}}, _ts(2026, 11, 21)) is None
    assert D.next_due({"trigger_spec": {"timezone": "UTC", "once": "2026-12-01T09:00"}}, _ts(2026, 11, 21)) == _ts(2026, 12, 1, 9)
    # the route's own settings give the time zone when the spec has none
    nxt = D.next_due({"trigger_spec": {"at": ["07:00"]}, "settings": {"timezone": "Australia/Sydney"}}, _ts(2026, 11, 21))
    assert _local(nxt, "Australia/Sydney").hour == 7
    # end date: nothing after it
    assert D.next_due({"trigger_spec": {"timezone": "UTC", "at": ["09:00"], "end_date": "2026-11-20"}}, _ts(2026, 11, 21)) is None


def test_schedule_quiet_hours_and_public_holidays():
    nxt = D.next_due({"trigger_spec": {"timezone": "Europe/London", "every_minutes": 30, "quiet": {"from": "21:00", "to": "08:00"}}},
                     _ts(2026, 11, 21, 21, 40, "Europe/London"))
    t = _local(nxt, "Europe/London")
    assert (t.day, t.hour, t.minute) == (22, 8, 0)
    # Fridays 09:00 in the US, skipping US public holidays: 25 Dec 2026 and 1 Jan 2027 are both Fridays
    nxt = D.next_due({"trigger_spec": {"timezone": "America/Chicago", "days": ["fri"], "at": ["09:00"], "skip_holidays": "US"}},
                     _ts(2026, 12, 21, 12))
    assert _local(nxt, "America/Chicago").strftime("%Y-%m-%d %H:%M") == "2027-01-08 09:00"


def test_schedule_legacy_ist_spec_unchanged():
    base = _ts(2026, 11, 21, 3, 0)          # 08:30 IST
    nxt = D.next_due({"trigger_spec": {"every_hours": 24, "at": ["09:30"]}}, base)
    assert _local(nxt, "Asia/Kolkata").strftime("%H:%M") == "09:30" and nxt - base == 3600
    assert D.next_due({"trigger_spec": {"every_hours": 3}}, base) == base + 3 * 3600


def test_schedule_validation_refuses_with_the_reason(bz):
    for spec, word in (({}, "Give a schedule"), ({"every_minutes": 5}, "15 or more"), ({"at": ["25:00"]}, "HH:MM"),
                       ({"days": ["funday"], "at": ["09:00"]}, "mon tue"), ({"timezone": "Mars/Base", "at": ["09:00"]}, "time zone"),
                       ({"at": ["09:00"], "skip_holidays": "ZZ"}, "country"), ({"monthdays": [40], "at": ["09:00"]}, "1-31"),
                       ({"at": ["09:00"], "quiet": {"from": "x"}}, "quiet")):
        with pytest.raises(ToolError) as e:
            _run(D.dhara_save(CTX, name="sched_bad", steps=[{"id": "a", "type": "set", "name": "a", "value": 1}],
                              trigger="schedule", trigger_spec=spec))
        assert word in str(e.value), (spec, str(e.value))
    with pytest.raises(ToolError):
        D.validate_settings({"timezone": "Nowhere/Land"})
    assert D.validate_settings({"folder": "Shop", "runs_per_day": 0, "currency": "eur"}) == {"folder": "Shop", "runs_per_day": 1, "currency": "EUR"}


def test_daily_run_cap(bz):
    wf = _run(D.dhara_save(CTX, name="capped", steps=[{"id": "a", "type": "set", "name": "a", "value": 1}],
                           settings={"runs_per_day": 2}))
    w = D.get_workflow(T, wf_id=wf["workflow_id"])
    assert not D._over_daily_cap(T, w)
    D.create_run(T, w)
    D.create_run(T, w)
    assert D._over_daily_cap(T, w)


def test_dsl_round_trip_keeps_settings(bz):
    _run(D.dhara_save(CTX, name="exp_me", steps=_router("online"), settings={"folder": "Shop", "timezone": "Europe/Paris"}))
    env = _run(D.dhara_dsl(CTX, action="export", name="exp_me"))["dsl"]
    assert env["settings"]["folder"] == "Shop"
    out = _run(D.dhara_dsl(CTX, action="import", dsl=env, new_name="exp_me_2"))
    assert out["ok"] and D.get_workflow(T, name="exp_me_2")["settings"]["timezone"] == "Europe/Paris"


# ---------------------------------------------------------------- the page API

def _client_and_tenant():
    from fastapi.testclient import TestClient
    from app.main import app
    from app.config import get_settings
    return TestClient(app), get_settings().tenant_id


def test_route_api_end_to_end(bz):
    c, tenant = _client_and_tenant()
    _wipe(tenant)
    try:
        ctx = Ctx(tenant_id=tenant, conversation_id="")
        _run(D.dhara_save(ctx, name="new_order_receipt", description="Receipt + sheet row",
                          steps=[{"id": "who", "type": "set", "name": "a", "value": 1},
                                 {"id": "mail", "type": "tool", "name": "email_send", "args": {"to": "x@example.com"}},
                                 {"id": "ok", "type": "approval", "question": "Send the receipt?"}],
                          trigger="schedule", trigger_spec={"timezone": "America/New_York", "days": ["mon"], "at": ["09:00"]},
                          settings={"folder": "Shop"}))
        lst = c.get("/api/route/routes").json()["routes"]
        assert len(lst) == 1 and lst[0]["folder"] == "Shop" and lst[0]["when"].startswith("Mon")
        assert any(a["slug"] == "gmail" for a in lst[0]["apps"])
        wid = lst[0]["id"]
        one = c.get(f"/api/route/routes/{wid}").json()
        assert [s["id"] for s in one["graph"]] == ["who", "mail", "ok"] and one["graph"][1]["app"]["slug"] == "gmail"
        assert c.get("/api/route/routes/wl_nope").status_code == 404
        # a manual run from the page: the set step is fine, then the email tool runs as a routine and the approval parks
        D.get_workflow(tenant, wf_id=wid)
        steps_ok = [{"id": "who", "type": "set", "name": "a", "value": 1}, {"id": "ok", "type": "approval", "question": "Send the receipt?"}]
        _run(D.dhara_save(ctx, name="new_order_receipt", steps=steps_ok, trigger="schedule",
                          trigger_spec={"timezone": "America/New_York", "days": ["mon"], "at": ["09:00"]}))
        rid = c.post(f"/api/route/routes/{wid}/run").json()["run_id"]
        if D.get_run(tenant, rid)["status"] != "waiting_approval":   # the request's loop may end before the task runs
            _run(D.execute_run(tenant, rid))
        for _ in range(50):
            if D.get_run(tenant, rid)["status"] == "waiting_approval":
                break
            time.sleep(0.05)
        summ = c.get("/api/route/summary").json()
        assert summ["routes_total"] == 1 and summ["needs_count"] >= 1
        assert summ["needs_you"][0]["kind"] == "approval" and "receipt" in summ["needs_you"][0]["text"]
        assert c.get(f"/api/route/runs?workflow_id={wid}").json()["runs"][0]["id"] == rid
        assert c.get(f"/api/route/runs/{rid}").json()["status"] == "waiting_approval"
        assert c.post(f"/api/route/runs/{rid}/approve").json()["status"] == "queued"
        assert c.post(f"/api/route/runs/{rid}/explode").status_code == 404
        sw = c.post(f"/api/route/routes/{wid}/switch", json={"on": False}).json()
        assert sw["enabled"] is False and D.get_workflow(tenant, wf_id=wid)["enabled"] == 0
        c.post(f"/api/route/routes/{wid}/switch", json={"on": True})
        assert D.get_workflow(tenant, wf_id=wid)["next_due_at"]
        tpl = c.get("/api/route/templates").json()["templates"]
        assert len(tpl) >= 6 and all("ask" in t for t in tpl)
        assert not any("₹" in t["ask"] or "GST" in t["ask"] or "India" in t["ask"] for t in tpl), "templates must be global"
    finally:
        _wipe(tenant)


def test_app_of_maps_tools_to_real_logos():
    from app.route.api import app_of, apps_of
    assert app_of({"type": "tool", "name": "email_send"})["slug"] == "gmail"
    assert app_of({"type": "tool", "name": "sheets_append"})["slug"] == "googlesheets"
    assert app_of({"type": "tool", "name": "composio_run", "args": {"app": "Slack"}})["slug"] == "slack"
    assert app_of({"type": "tool", "name": "kalam"})["kind"] == "hoola"
    assert app_of({"type": "approval"})["kind"] == "approval"
    assert [a["slug"] for a in apps_of([{"type": "router", "routes": [{"steps": [{"type": "tool", "name": "whatsapp_send"}]}]}])] == ["whatsapp"]


# ---------------------------------------------------------------- the page

def test_route_page_is_served_in_house_style(bz):
    c, _ = _client_and_tenant()
    r = c.get("/console/route")
    assert r.status_code == 200 and "route.js" in r.text and "Content-Security-Policy" in r.headers
    base = Path(__file__).resolve().parents[1] / "app" / "static" / "console"
    js = (base / "route.js").read_text()
    css = (base / "route.css").read_text()
    html = (base / "route.html").read_text()
    assert "onerror=" not in js and "onclick=" not in js and "eval(" not in js, "the page CSP allows no inline handlers"
    assert "/api/logo/cmp/" in js, "real app logos"
    assert "#5B45E0" in css and "Literata" in css and "--pill:#1F1E1D" in css, "the console's house tokens"
    assert "mark.js" in html and "Back to Hoola" in html
    for word in ("₹", "IST", "Haan", "udhaar", "GST"):
        assert word not in js and word not in html, f"'{word}' on a page meant for everyone"
    assert "Intl.DateTimeFormat" in js, "her own time zone goes to Hoola"
    v2 = (base / "v2.js").read_text()
    assert "['route', 'Route'," in v2 and "location.assign('/console/route')" in v2


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION.startswith("0.999.142")


# ---------------------------------------------------------------- a real browser walk

@pytest.fixture
def br_route(bz, monkeypatch):
    import os
    import threading
    import time as _t
    sync_api = pytest.importorskip("playwright.sync_api")
    from tests.test_v161_console_e2e import _free_port
    from tests.test_v161_stream import KEY
    monkeypatch.setenv("API_KEY", KEY)
    from app.config import get_settings
    get_settings.cache_clear()
    tenant = get_settings().tenant_id
    _wipe(tenant)
    ctx = Ctx(tenant_id=tenant, conversation_id="")
    _run(D.dhara_save(ctx, name="new_order_receipt", description="Receipt + sheet row", settings={"folder": "Shop"},
                      steps=_router("cod") + [{"id": "ok", "type": "approval", "question": "Send the receipt for order 2291?"}],
                      trigger="schedule", trigger_spec={"timezone": "Europe/London", "days": ["mon", "fri"], "at": ["09:00"],
                                                        "quiet": {"from": "21:00", "to": "08:00"}, "skip_holidays": "GB"}))
    wf = D.get_workflow(tenant, name="new_order_receipt")
    rid = D.create_run(tenant, wf)
    _run(D.execute_run(tenant, rid))
    assert D.get_run(tenant, rid)["status"] == "waiting_approval"
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
            browser = pw.chromium.launch(**({"executable_path": os.environ["HOOLA_CHROMIUM"]} if os.environ.get("HOOLA_CHROMIUM") else {}))
        except Exception as ex:      # noqa: BLE001
            pw.stop()
            pytest.skip(f"no Chromium for Playwright here: {str(ex)[:80]}")
        yield f"http://127.0.0.1:{port}", browser, KEY, wf["id"], rid, tenant
        browser.close()
        pw.stop()
    finally:
        srv.should_exit = True
        th.join(timeout=10)
        _wipe(tenant)


def test_route_page_in_a_real_browser(br_route):
    base, browser, key, wid, rid, tenant = br_route
    errors = []
    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    pg = ctx.new_page()
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.goto(base + "/console/route")
    pg.wait_for_function("() => document.querySelector('#main').innerText.includes('Needs you')", timeout=20000)
    txt = pg.inner_text("#main")
    assert "What should run by itself?" in txt and "new order receipt" in txt and "Send the receipt for order 2291?" in txt
    assert pg.inner_text("#needCount") == "1"
    assert pg.locator("#brandMark svg").count() == 1, "the Hoola Orbit mark"
    # the route: its flow, the router's labelled routes, a step's details, how it runs
    pg.click("a.rn")
    pg.wait_for_selector(".flow .node")
    flow = pg.inner_text(".flow")
    assert "Cash" in flow and "Paid online" in flow and "Anything else" in flow
    pg.click(".node[data-step='ok']")
    assert "Send the receipt for order 2291?" in pg.inner_text("#stepBox")
    how = pg.inner_text("#main")
    assert "Europe/London" in how and "21:00" in how and "GB" in how and "Always wait for your tap" in how
    # approve from the page: the run carries on past the gate
    pg.goto(base + "/console/route#/run/" + rid)
    pg.wait_for_selector("[data-act='approve']")
    pg.click("[data-act='approve']")
    for _ in range(100):
        if D.get_run(tenant, rid)["status"] != "waiting_approval":
            break
        time.sleep(0.05)
    assert D.get_run(tenant, rid)["status"] in ("queued", "running", "done")
    # templates are global and hand the words to Hoola
    pg.goto(base + "/console/route#/templates")
    pg.wait_for_selector("[data-use]")
    assert "Unpaid invoice reminders" in pg.inner_text("#main")
    ctx.close()
    c2 = browser.new_context(viewport={"width": 390, "height": 900})
    c2.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    p2 = c2.new_page()
    p2.on("pageerror", lambda e: errors.append(str(e)))
    p2.goto(base + "/console/route")
    p2.wait_for_function("() => document.querySelector('#main').innerText.includes('Your routes')", timeout=20000)
    assert p2.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1"), "sideways scroll on a phone"
    c2.close()
    assert not errors, errors
