"""v0.546 CHALTA KAAM (App Sahayak Pillar L): the app AFTER it ships.

What is worth testing here is not that a dashboard renders - it is that the numbers are MEASURED and that the honest
ones stay honest: latency comes from the app's own requests through the real middleware, cost comes from the real
usage meter, an unpriced thing is never silently zero, an alert is arithmetic with a stated threshold and is said
once a day, and an estimate with nothing behind it says "pata nahi" instead of inventing rupees.
"""
from __future__ import annotations

import json

from fastapi.testclient import TestClient

from tests.test_v0314_app_backend import _built
from tests.test_v128_appdesign import T
from tests.test_v132_android import FakeBuild, droid_env  # noqa: F401  (fixture)


def _app(aid: str):
    from app.appmaker.models import AppProject
    from app.db import session
    with session() as s:
        r = s.get(AppProject, aid)
        s.expunge(r)
    return r


# ---------------------------------------------------------------- latency + errors are really measured
def test_the_middleware_measures_the_apps_own_requests(droid_env):
    """Not a counter somebody has to remember to call: every /api/app-api/ request, through the real app."""
    from app.appmaker import ops as OPS
    from app.main import app
    aid, _c, key, _b = _built(droid_env)
    c = TestClient(app)
    for _ in range(3):
        c.get(f"/api/app-api/{key}/schema")
    c.get("/api/app-api/akdeadbeefdeadbeefdeadbeef/schema")      # a 404 app: still a call, not an error of hers
    OPS.flush()

    tr = OPS.traffic(_app(aid))
    assert tr["calls"] == 3, tr
    assert tr["average_ms"] is not None and tr["p50"] and tr["estimated"] is True
    assert tr["error_percent"] == 0.0
    assert sum(tr["bins"].values()) == 3


def test_a_failing_call_is_counted_as_a_failure_and_a_refusal_is_not(droid_env):
    from app.appmaker import ops as OPS
    aid, _c, key, _b = _built(droid_env)
    OPS.seen(key, 12.0, 200)
    OPS.seen(key, 15.0, 400)          # her customer sent something wrong: not a failure of the app
    OPS.seen(key, 9000.0, 500)        # this one is
    OPS.flush()
    tr = OPS.traffic(_app(aid))
    assert tr["calls"] == 3 and tr["errors"] == 1
    assert tr["error_percent"] == 33.33
    assert tr["slowest_ms"] == 9000
    assert tr["p95"] == ">6s", tr


def test_several_workers_merge_and_nobody_overwrites(droid_env):
    """Four processes write the same app's file; the counts add up instead of the last one winning."""
    from app.appmaker import ops as OPS
    aid, _c, key, _b = _built(droid_env)
    for _ in range(5):
        OPS.seen(key, 30.0, 200)
    OPS.flush()
    for _ in range(4):                 # a second "worker" with its own buffer
        OPS.seen(key, 30.0, 200)
    OPS.flush()
    assert OPS.traffic(_app(aid))["calls"] == 9


def test_old_hours_are_forgotten(droid_env):
    from datetime import datetime, timedelta, timezone
    from app.appmaker import ops as OPS
    aid, _c, key, _b = _built(droid_env)
    OPS.seen(key, 10.0, 200)
    OPS.flush()
    r = _app(aid)
    f = OPS._file(r)
    data = json.loads(f.read_text())
    old = (datetime.now(timezone.utc) - timedelta(days=40)).strftime("%Y-%m-%dT%H")
    data["traffic"][old] = {"n": 999, "ms": 1.0, "err": 0, "bins": [0] * len(OPS.BINS), "slow": 1.0}
    f.write_text(json.dumps(data))
    OPS.seen(key, 10.0, 200)
    OPS.flush()
    assert old not in json.loads(f.read_text())["traffic"], "a fortnight is the window"
    assert OPS.traffic(_app(aid))["calls"] == 2


# ---------------------------------------------------------------- cost is the real meter, and gaps are said
def test_the_cost_is_what_the_model_really_cost(droid_env, monkeypatch):
    from app import usage
    from app.appmaker import ops as OPS
    aid, _c, _k, _b = _built(droid_env)
    r = _app(aid)
    monkeypatch.setattr(usage, "usd_inr", lambda: 80.0)

    with OPS.meter(r, note="build") as acc:
        acc["usd"] = 0.25          # what the run really spent, as usage.run_meter would have filled it
        acc["calls"] = 3
    cs = OPS.cost(_app(aid))
    assert cs["inr"] == 20.0, cs           # 0.25 USD x 80
    assert cs["by_kind"][0]["kind"] == "model" and cs["by_kind"][0]["count"] == 3
    assert "Rs 20.00" in cs["says"]


def test_an_unpriced_thing_is_counted_and_said_never_silently_zero(droid_env):
    from app.appmaker import ops as OPS
    aid, _c, _k, _b = _built(droid_env)
    r = _app(aid)
    OPS.spend(r, "sms", 0.0, 40, "reminders")
    OPS.spend(r, "push", 0.0, 120)
    cs = OPS.cost(_app(aid))
    assert cs["inr"] == 0.0
    assert set(cs["not_priced"]) == {OPS.KINDS["sms"], OPS.KINDS["push"]}
    assert "daam abhi set nahi hai" in cs["says"], cs["says"]
    kinds = {b["kind"]: b for b in cs["by_kind"]}
    assert kinds["sms"]["count"] == 40 and kinds["sms"]["priced"] is False


def test_the_estimate_is_her_own_history_or_an_honest_blank(droid_env, monkeypatch):
    from app import usage
    from app.appmaker import ops as OPS
    aid, _c, _k, _b = _built(droid_env)
    r = _app(aid)
    monkeypatch.setattr(usage, "usd_inr", lambda: 80.0)

    blank = OPS.estimate(r, "build")
    assert blank["measured"] is False and blank["inr"] is None
    assert "naapa nahi gaya" in blank["says"], blank["says"]

    for usd in (0.10, 0.20, 0.30):
        with OPS.meter(_app(aid), note="build") as acc:
            acc["usd"] = usd
            acc["calls"] = 1
    got = OPS.estimate(_app(aid), "build")
    assert got["measured"] is True and got["from_runs"] == 3
    assert got["inr"] == 16.0                       # the MEDIAN of 8 / 16 / 24, not the average, not the worst
    assert got["month_after"] == round(got["month_so_far"] + 16.0, 2)
    assert "Rs 16.00" in got["says"]
    # a job she has never run is not estimated from a different job's history
    assert OPS.estimate(_app(aid), "naksha")["measured"] is False


# ---------------------------------------------------------------- alerts are rules, and they are said once
def test_failures_raise_an_alert_only_when_there_is_enough_to_judge(droid_env):
    from app.appmaker import ops as OPS
    aid, _c, key, _b = _built(droid_env)
    for _ in range(3):                 # 3 calls, 1 failure = 33% but far too few to mean anything
        OPS.seen(key, 10.0, 200)
    OPS.seen(key, 10.0, 500)
    OPS.flush()
    assert not [a for a in OPS.rules(_app(aid)) if a["key"] == "errors"]

    for _ in range(40):
        OPS.seen(key, 10.0, 200)
    for _ in range(6):
        OPS.seen(key, 10.0, 500)
    OPS.flush()
    hit = [a for a in OPS.rules(_app(aid)) if a["key"] == "errors"]
    assert hit and hit[0]["level"] == "bad"
    assert "fail ho rahi hain" in hit[0]["say"]


def test_she_is_told_once_a_day_per_kind(droid_env):
    from app.appmaker import ops as OPS
    aid, _c, key, _b = _built(droid_env)
    said: list[str] = []
    import app.appmaker.android.service as AN
    AN._note_orig = AN._note
    AN._note = lambda r, text: said.append(text)
    try:
        for _ in range(40):
            OPS.seen(key, 10.0, 200)
        for _ in range(6):
            OPS.seen(key, 10.0, 500)
        OPS.flush()
        first = OPS.watch(_app(aid))
        again = OPS.watch(_app(aid))
    finally:
        AN._note = AN._note_orig
    assert first["sent"] >= 1 and len(said) == first["sent"]
    assert again["sent"] == 0, "an alert that cries every hour is one she turns off"


def test_an_app_that_got_slower_than_itself_is_named(droid_env):
    from datetime import datetime, timedelta, timezone
    from app.appmaker import ops as OPS
    aid, _c, key, _b = _built(droid_env)
    r = _app(aid)
    # her own fortnight: fast. Then today: four times slower.
    f = OPS._file(r)
    old_hour = (datetime.now(timezone.utc) - timedelta(days=3)).strftime("%Y-%m-%dT%H")
    f.write_text(json.dumps({"traffic": {old_hour: {"n": 200, "ms": 200 * 100.0, "err": 0,
                                                    "bins": [0] * len(OPS.BINS), "slow": 150.0}}}))
    for _ in range(30):
        OPS.seen(key, 900.0, 200)
    OPS.flush()
    hit = [a for a in OPS.rules(_app(aid)) if a["key"] == "slow"]
    assert hit, OPS.rules(_app(aid))
    assert "dhimi ho gayi hai" in hit[0]["say"] and "900ms" in hit[0]["say"]


# ---------------------------------------------------------------- the card, and what it does not know
def test_the_card_says_what_is_not_measured(droid_env):
    from app.appmaker import ops as OPS
    aid, _c, _k, _b = _built(droid_env)
    card = OPS.dashboard(_app(aid))
    assert card["traffic"]["calls"] == 0
    assert any("koi call nahi" in g for g in card["not_measured"])
    assert any("kharche ka koi hisaab" in g for g in card["not_measured"])
    assert "people" in card and "cost" in card and "field" in card


def test_the_dashboard_carries_the_real_numbers(droid_env, monkeypatch):
    from app import usage
    from app.appmaker import ops as OPS
    aid, _c, key, _b = _built(droid_env)
    monkeypatch.setattr(usage, "usd_inr", lambda: 80.0)
    for _ in range(12):
        OPS.seen(key, 60.0, 200)
    OPS.flush()
    with OPS.meter(_app(aid), note="build") as acc:
        acc["usd"], acc["calls"] = 0.05, 1
    card = OPS.dashboard(_app(aid))
    assert card["traffic"]["calls"] == 12
    assert card["cost"]["inr"] == 4.0
    assert "12 calls" in card["says"] and "Rs 4.00" in card["says"]
    assert card["people"]["accounts"] >= 0


# ---------------------------------------------------------------- the surfaces
def test_the_routes_are_not_eaten_by_the_catch_all(droid_env):
    from app.main import app
    aid, _c, _k, _b = _built(droid_env)
    c = TestClient(app)
    paths = {getattr(x, "path", "") for x in app.routes}
    assert "/api/apps/{ref}/ops" in paths and "/api/apps/{ref}/ops/{what}" in paths
    assert c.get(f"/api/apps/{aid}/ops").status_code == 200
    assert c.post(f"/api/apps/{aid}/ops/nope").status_code == 404
    got = c.post(f"/api/apps/{aid}/ops/estimate", json={"job": "build"}).json()
    assert got["job"] == "build" and got["measured"] is False


def test_the_tool_reads_it_and_the_estimate_is_askable(droid_env):
    import asyncio
    from app.agent.tools import Ctx, dispatch
    aid, conv, _k, _b = _built(droid_env)
    ctx = Ctx(tenant_id=T, conversation_id=conv)
    card = asyncio.run(dispatch("app_dekho", {"what": "chaal", "app": aid}, ctx))
    assert "traffic" in card and "not_measured" in card
    est = asyncio.run(dispatch("app_banao", {"action": "kharcha", "app": aid, "job": "build"}, ctx))
    assert est["measured"] is False and "naapa nahi gaya" in est["says"]


def test_the_middleware_never_breaks_a_request(droid_env, monkeypatch):
    """Telemetry is never worth an error page."""
    from app.appmaker import ops as OPS
    from app.main import app
    _aid, _c, key, _b = _built(droid_env)
    monkeypatch.setattr(OPS, "seen", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))
    assert TestClient(app).get(f"/api/app-api/{key}/schema").status_code == 200


def test_the_twin_is_never_alerted_about(droid_env):
    """Pillar J's test copy makes rows and calls of its own; she must never be told about it."""
    from app.appmaker import quality as QA
    aid, _c, _k, _b = _built(droid_env)
    t = QA.twin(_app(aid))
    import json as _j
    assert '"jaanch_of"' in (t.plan or ""), "the worker skips a twin by this mark"
    assert _j.loads(t.plan)["jaanch_of"] == aid


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.550.0"
