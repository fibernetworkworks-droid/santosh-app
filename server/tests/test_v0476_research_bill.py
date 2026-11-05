"""v0.476 R5 KHARCHA - what a research run costs, and a ceiling that refuses BEFORE it spends.

Pinned: the run-scoped meter counts exactly the model calls made inside its block (a sibling task and a call outside are not in it),
the rupee figure is the list price x the server's rate (not a typed number), web calls are counted but UNPRICED and every cost line says so,
the per-run ceiling and the per-tenant per-day ceiling (other runs' spend counts, another tenant's does not, yesterday's does not), a run
restarted after a crash starts from what it had already spent, the engine asks BEFORE every model call and stops with what it has
("cost ceiling"), a stopped run still records its spend, a new run is refused when the day's room is gone, inline runs are a ledger row too,
the plan card uses the MEASURED cost per goal once three runs exist (and says which it used) and shows the ceilings, and the HTTP routes work.
"""
from __future__ import annotations

import asyncio
import json
from datetime import timedelta

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app import usage
from app.config import get_settings
from app.db import now, session
from app.research import bill, runner, store
from app.research import engine as E
from tests.test_v0473_research_engine import GOOD_PLAY, Script, deps, tu


def run_(c):
    return asyncio.run(c)


@pytest.fixture
def caps(env):
    st = get_settings()
    saved = (st.research_run_cap_inr, st.research_daily_inr, st.research_call_reserve_inr, st.research_search_inr, st.research_fetch_inr)
    yield st
    st.research_run_cap_inr, st.research_daily_inr, st.research_call_reserve_inr, st.research_search_inr, st.research_fetch_inr = saved


MODEL = "claude-sonnet-5-5"


# ---------------------------------------------------------------- the meter
def test_the_run_meter_counts_only_the_calls_made_inside_it(env):
    usage.record(MODEL, tok_in=5000, tok_out=1000, tenant="t", feature="chat")          # outside: not in any run
    with usage.run_meter() as acc:
        a = usage.record(MODEL, tok_in=10_000, tok_out=2_000, tenant="t", feature="research")
        b = usage.record(MODEL, tok_in=1_000, tok_out=500, tenant="t", feature="research")
    assert acc["calls"] == 2 and abs(acc["usd"] - (a + b)) < 1e-9 and acc["tok_in"] == 11_000 and acc["tok_out"] == 2_500
    assert acc["by_model"][MODEL]["calls"] == 2
    usage.record(MODEL, tok_in=99_999, tenant="t", feature="chat")                        # after the block: not added
    assert acc["calls"] == 2


def test_two_runs_at_once_do_not_see_each_others_calls_and_a_chat_is_in_neither(env):
    async def worker(tok):
        with usage.run_meter() as acc:
            await asyncio.sleep(0)
            usage.record(MODEL, tok_in=tok, tenant="t", feature="research")
            await asyncio.sleep(0)
            return acc["usd"], acc["calls"]

    async def chat():
        await asyncio.sleep(0)
        usage.record(MODEL, tok_in=50_000, tenant="t", feature="chat")

    async def main():
        return await asyncio.gather(worker(1_000), worker(100_000), chat())
    (u1, c1), (u2, c2), _ = run_(main())
    assert c1 == c2 == 1 and u2 > u1 * 50                                                  # each saw only its own call


def test_tasks_started_inside_a_run_count_into_that_run(env):
    async def main():
        with usage.run_meter() as acc:
            await asyncio.gather(*(asyncio.ensure_future(asyncio.sleep(0, result=usage.record(MODEL, tok_in=1000, tenant="t"))) for _ in range(3)))
            return acc
    assert run_(main())["calls"] == 3


def test_the_rupee_figure_is_the_list_price_times_the_servers_rate(caps):
    m = bill.Meter("t")
    with usage.run_meter(m.acc):
        usd = usage.record(MODEL, tok_in=200_000, tok_out=20_000, tenant="t")
    assert m.model_inr() == round(usd * usage.usd_inr(), 4) and m.model_inr() > 0
    assert m.total_inr() == m.model_inr()                                                  # web calls are unpriced: they add nothing


def test_web_calls_are_counted_but_unpriced_and_every_line_says_so_until_a_price_is_set(caps):
    m = bill.Meter("t")
    m.counts["searches"], m.counts["fetches"] = 4, 9
    b = m.breakdown()
    assert b["searches"] == 4 and b["fetches"] == 9 and b["web_inr"] == 0 and b["web_price_known"] is False
    assert "web price not known" in bill.format_line(b, hi=False) and "web price abhi pata nahi" in bill.format_line(b, hi=True)
    caps.research_search_inr, caps.research_fetch_inr = 0.5, 0.2
    b = m.breakdown()
    assert b["web_inr"] == round(4 * 0.5 + 9 * 0.2, 4) and b["web_price_known"] is True and "not known" not in bill.format_line(b, hi=False)
    assert bill.usage_report("t")["web"]["known"] is True


# ---------------------------------------------------------------- the ceilings
def _spend(m, usd):
    m.acc["usd"] += usd


def test_the_per_run_ceiling_refuses_before_the_call_that_would_cross_it(caps):
    caps.research_run_cap_inr, caps.research_call_reserve_inr = 100.0, 10.0
    m = bill.Meter("t")
    assert m.afford() == (True, "")
    _spend(m, 80 / usage.usd_inr())                       # Rs 80 spent: 80 + the Rs 10 reserve is under 100
    assert m.afford()[0] is True
    _spend(m, 15 / usage.usd_inr())                       # Rs 95: the next call could cross it - refused NOW
    ok, why = m.afford()
    assert ok is False and "ceiling" in why and "Rs 95" in why and "Rs 100" in why


def test_the_daily_ceiling_counts_other_runs_of_the_tenant_and_nobody_elses_and_not_yesterday(caps):
    caps.research_run_cap_inr, caps.research_daily_inr, caps.research_call_reserve_inr = 1000.0, 200.0, 5.0
    a = store.create("t1", "c", "Q", ["g"], {})
    b = store.create("t1", "c", "Q", ["g"], {})
    other = store.create("t2", "c", "Q", ["g"], {})
    old = store.create("t1", "c", "Q", ["g"], {})
    store.finish(a, "done", {}, cost={"total_inr": 120.0})
    store.finish(other, "done", {}, cost={"total_inr": 900.0})                              # another tenant: never counts
    store.finish(old, "done", {}, cost={"total_inr": 900.0})
    with session() as s:
        s.get(store.ResearchRun, old).updated_at = now() - timedelta(days=2)                 # yesterday's money is not today's
    m = bill.Meter("t1", b)
    assert m.day_spent_inr() == 120.0 and m.afford()[0] is True
    _spend(m, 76 / usage.usd_inr())                                                          # 120 + 76 + 5 reserve > 200
    ok, why = m.afford()
    assert ok is False and "daily ceiling" in why
    assert bill.usage_report("t1")["today_inr"] == 120.0 and bill.usage_report("t2")["today_inr"] == 900.0


def test_a_new_run_is_refused_when_the_days_room_is_gone_and_the_message_says_how_to_change_it(caps):
    caps.research_daily_inr, caps.research_call_reserve_inr = 100.0, 3.0
    bill.preflight("t1")                                                                      # room: fine
    r = store.create("t1", "c", "Q", ["g"], {})
    store.finish(r, "done", {}, cost={"total_inr": 98.0})
    with pytest.raises(bill.ResearchCapped, match="RESEARCH_DAILY_INR"):
        bill.preflight("t1")
    bill.preflight("t2")                                                                      # another tenant is unaffected
    caps.research_daily_inr = 0.0
    with pytest.raises(bill.ResearchCapped):
        bill.preflight("t2")                                                                  # 0 = no research that day


def test_a_restarted_run_starts_from_what_it_had_already_spent(caps):
    caps.research_run_cap_inr, caps.research_call_reserve_inr = 100.0, 5.0
    m = bill.Meter("t", "r", base={"model_inr": 70.0, "model_calls": 30, "tok_in": 1000, "tok_out": 100, "searches": 12, "fetches": 20,
                                   "by_model": {MODEL: {"calls": 30, "inr": 70.0}}})
    assert m.total_inr() == 70.0 and m.afford()[0] is True
    _spend(m, 30 / usage.usd_inr())
    assert m.afford()[0] is False
    b = m.breakdown()
    assert b["model_calls"] == 30 and b["searches"] == 12 and b["fetches"] == 20 and b["by_model"][MODEL]["inr"] == 70.0


# ---------------------------------------------------------------- the engine
def test_the_engine_stops_before_the_call_that_would_cross_the_ceiling_and_keeps_what_it_found(env):
    allowed = {"n": 0}

    def afford():
        allowed["n"] += 1
        return (allowed["n"] <= 4, "this run has spent Rs 97 of its Rs 100 ceiling")        # four model calls, then no more
    d_, _ = deps(Script({"g1": GOOD_PLAY, "g2": GOOD_PLAY}, replan={"action": "tasks", "reasoning": "x", "tasks": ["g3"]}))
    d_.afford = afford
    d_.cost = lambda stop: {"total_inr": 97.0, "model_inr": 97.0, "web_inr": 0.0, "model_calls": 4, "searches": 1, "fetches": 1,
                            "web_price_known": False, "run_cap_inr": 100.0, "stopped_by_cost": bool(stop), "stop": stop}
    out = asyncio.run(E.run("q", ["g1", "g2"], E.Policy(rounds=2, parallel=1), d_))
    assert out["stop_reason"].startswith("cost ceiling") and out["cost"]["stopped_by_cost"] is True
    assert any("cost ceiling" in t["unresolved"] for t in out["tasks"]) and len(out["tasks"]) == 2          # no re-plan round after it
    assert E.STATS["cost_stops"] >= 1 and out["stats"]["cost_inr"] == 97.0
    assert "STOPPED" in E.render(out) and "Rs 97.0" in E.render(out)
    assert any(t["notes"] for t in out["tasks"][:1])                                                       # what was found is kept


def test_a_failing_cost_reader_never_loses_the_research(env):
    d_, _ = deps(Script({"g": GOOD_PLAY}))
    d_.cost = lambda stop: (_ for _ in ()).throw(RuntimeError("meter broke"))
    out = asyncio.run(E.run("q", ["g"], E.Policy(rounds=1), d_))
    assert out["cost"] == {} and out["stats"]["verified_notes"] == 1


# ---------------------------------------------------------------- the runner
@pytest.fixture
def bg(caps, monkeypatch):
    events = []
    monkeypatch.setattr(runner.bus, "publish", lambda conv, kind, payload: events.append((conv, kind, payload)))
    box = {"script": Script({"Corvane value": GOOD_PLAY, "second goal": [("finish", {"summary": "b"})]})}

    def factory(ctx, st):
        d_, _ = deps(box["script"])
        inner = d_.llm

        async def metered(system, history, tools, mt):               # a real model call is recorded by usage.record: do the same
            usage.record(MODEL, tok_in=40_000, tok_out=3_000)
            return await inner(system, history, tools, mt)
        d_.llm = metered
        return d_
    monkeypatch.setattr(runner, "_deps_factory", factory)
    runner._RUNNING.clear()
    return {"events": events, "box": box, "st": caps}


def test_a_background_run_records_its_own_cost_and_reports_it(bg):
    rid = runner.start("t1", "c1", "What is the Corvane Index?", ["Corvane value", "second goal"], {}, hi=False)
    run_(runner.run_background(rid))
    v = store.get(rid)
    c = v["cost"]
    assert v["status"] == "done" and v["cost_inr"] > 0 and v["cost_inr"] == c["total_inr"] and c["model_calls"] >= 4
    assert c["searches"] >= 1 and c["fetches"] >= 1 and c["web_price_known"] is False and c["by_model"][MODEL]["calls"] == c["model_calls"]
    assert v["dossier"]["cost"]["total_inr"] == c["total_inr"] and "Cost: Rs" in E.render(v["dossier"])
    rows = runner.status("t1")
    assert rows[0]["cost_inr"] == round(v["cost_inr"], 2)


def test_the_run_is_counted_under_the_tenant_as_research_not_as_chat(bg):
    rid = runner.start("t9", "c1", "What is it?", ["Corvane value"], {}, hi=False)
    run_(runner.run_background(rid))
    usage.flush()
    rep = usage.report("t9", 1)
    feats = json.dumps(rep, default=str)
    assert "research" in feats.lower() or "Research" in feats


def test_a_run_that_hits_its_ceiling_stops_early_and_says_so(bg):
    bg["st"].research_run_cap_inr, bg["st"].research_call_reserve_inr = 20.0, 1.0
    rid = runner.start("t1", "c1", "What is the Corvane Index?", ["Corvane value", "second goal"], {}, hi=False)
    run_(runner.run_background(rid))
    v = store.get(rid)
    assert v["cost"]["stopped_by_cost"] is True and v["dossier"]["stop_reason"].startswith("cost ceiling")
    assert v["cost_inr"] <= 20.0 + 15                                                         # at most one call past: it asked BEFORE each one
    done = [p for _c, k, p in bg["events"] if k == "research_run"][-1]
    assert "stopped at the cost ceiling" in done["say"] or done["status"] == "failed"


def test_a_resume_after_a_crash_counts_the_money_already_spent(bg):
    bg["st"].research_run_cap_inr, bg["st"].research_call_reserve_inr = 100.0, 5.0
    rid = runner.start("t1", "c1", "What is the Corvane Index?", ["Corvane value", "second goal"], {}, hi=False)
    first, _ = deps(Script({"Corvane value": GOOD_PLAY}))
    cps = []
    first.checkpoint = lambda cp: cps.append(json.loads(json.dumps(cp)))
    asyncio.run(E.run("What is the Corvane Index?", ["Corvane value", "second goal"], E.Policy(rounds=1, parallel=1), first))
    with session() as s:
        r = s.get(store.ResearchRun, rid)
        r.status, r.tries, r.checkpoint, r.updated_at = "running", 1, json.dumps(cps[0]), now() - timedelta(seconds=900)
        r.cost_inr, r.cost = 99.0, json.dumps({"total_inr": 99.0, "model_inr": 99.0, "model_calls": 40, "searches": 3, "fetches": 5,
                                               "tok_in": 1, "tok_out": 1, "by_model": {MODEL: {"calls": 40, "inr": 99.0}}})
    calls = {"n": 0}
    inner = bg["box"]["script"].llm

    async def counting(*a, **k):
        calls["n"] += 1
        return await inner(*a, **k)
    bg["box"]["script"].llm = counting
    run_(runner.run_background(rid))
    v = store.get(rid)
    assert calls["n"] == 0, "a run with Rs 99 of its Rs 100 ceiling already spent made another model call after the restart"
    assert v["cost"]["model_calls"] >= 40 and v["cost_inr"] >= 99.0 and v["cost"]["stopped_by_cost"] is True


def test_a_stopped_run_still_records_what_it_spent(bg):
    rid = runner.start("t1", "c1", "Q", ["Corvane value", "second goal"], {}, hi=False)
    orig = store.save_checkpoint

    def stop_after_first(run_id, cp, progress=None):
        orig(run_id, cp, progress)
        runner.stop("t1", run_id)
    store.save_checkpoint = stop_after_first
    try:
        run_(runner.run_background(rid))
    finally:
        store.save_checkpoint = orig
    v = store.get(rid)
    assert v["status"] == "stopped" and v["cost_inr"] > 0


# ---------------------------------------------------------------- the tool
def _ctx(tenant="t1", conv="c1"):
    from app.agent.tools import Ctx
    return Ctx(tenant_id=tenant, conversation_id=conv, actor="owner")


def test_the_tool_refuses_a_new_run_when_the_days_room_is_gone(bg):
    from app.agent.research_tools import research_run
    from app.agent.tools import ToolError
    bg["st"].research_daily_inr = 10.0
    r = store.create("t1", "c1", "Q", ["g"], {})
    store.finish(r, "done", {}, cost={"total_inr": 9.0})
    with pytest.raises(ToolError, match="budget khatam"):
        run_(research_run(_ctx(), question="Q?", sub_questions=["g"]))
    with pytest.raises(ToolError, match="budget khatam"):
        run_(research_run(_ctx(), question="Q?", sub_questions=["g"], mode="inline"))
    assert run_(research_run(_ctx("t2"), question="Q?", sub_questions=["g"]))["started"] is True       # another tenant


def test_an_inline_run_is_metered_ceilinged_and_written_to_the_ledger(bg, monkeypatch):
    from app.agent import research_tools as RT
    d_, _ = deps(bg["box"]["script"])
    inner = d_.llm

    async def metered(s, h, t, m):
        usage.record(MODEL, tok_in=40_000, tok_out=3_000)
        return await inner(s, h, t, m)
    d_.llm = metered
    monkeypatch.setattr(RT, "_deps", lambda ctx, st: d_)
    out = run_(RT.research_run(_ctx(), question="What is the Corvane Index?", sub_questions=["Corvane value"], mode="inline"))
    assert out["stats"]["cost_inr"] > 0 and "Cost: Rs" in out["dossier"]
    rows = store.recent("t1")
    assert rows and rows[0]["cost_inr"] > 0 and rows[0]["status"] == "done" and rows[0]["policy"]["inline"] is True
    bg["st"].research_run_cap_inr, bg["st"].research_call_reserve_inr = 10.0, 1.0
    d2, _ = deps(Script({"Corvane value": GOOD_PLAY}))
    inner2 = d2.llm

    async def metered2(s, h, t, m):
        usage.record(MODEL, tok_in=400_000, tok_out=30_000)
        return await inner2(s, h, t, m)
    d2.llm = metered2
    monkeypatch.setattr(RT, "_deps", lambda ctx, st: d2)
    out = run_(RT.research_run(_ctx(), question="What is the Corvane Index?", sub_questions=["Corvane value"], mode="inline"))
    assert out["cost"]["stopped_by_cost"] is True and "STOPPED at its cost ceiling" in out["say"]


# ---------------------------------------------------------------- measured, not assumed (the R1 plan card)
def _finished(tenant, goals, inr):
    rid = store.create(tenant, "c", "Q", [f"g{i}" for i in range(goals)], {})
    store.finish(rid, "done", {}, cost={"total_inr": inr})
    return rid


def test_the_median_cost_per_goal_needs_three_finished_runs_and_ignores_free_ones(caps):
    assert bill.measured_per_goal("t1") is None
    _finished("t1", 5, 50.0)
    _finished("t1", 5, 100.0)
    assert bill.measured_per_goal("t1") is None
    _finished("t1", 4, 0.0)                                                                  # a run that cost nothing is not a measurement
    assert bill.measured_per_goal("t1") is None
    _finished("t1", 4, 120.0)
    m = bill.measured_per_goal("t1")
    assert m["runs"] == 3 and m["per_goal_inr"] == 20.0 and m["max_run_inr"] == 120.0           # per goal: 10, 20, 30 -> median 20


def test_the_plan_card_uses_the_measured_cost_once_it_exists_and_says_which_it_used(caps, monkeypatch):
    from app.agent import research_plan as P

    async def fake_q(ask, note, a, settings):
        return {"sub_questions": ["a?", "b?", "c?", "d?"], "look_in": ["x"], "as_of": "today", "from_model": True}
    monkeypatch.setattr(P, "_questions", fake_q)
    ask = "Do deep research on the Corvane Index market: size, players, growth. Sources with dates."
    first = run_(P.build(ask, caps, tenant="t5"))
    assert first["est"]["assumed"] is True and first["est"]["caps"]["run_inr"] == caps.research_run_cap_inr
    txt = P.card_text(first)
    assert "an estimate" in txt and "Ceiling:" in txt and "left today" in txt
    for goals, inr in ((4, 40.0), (4, 80.0), (4, 120.0)):
        _finished("t5", goals, inr)
    p = run_(P.build(ask, caps, tenant="t5"))
    assert p["est"]["assumed"] is False and p["est"]["measured_runs"] == 3 and p["est"]["inr"] == 80.0       # median 20 / goal x 4 goals
    hi = P.card_text({**p, "hinglish": True})
    assert "aapke pichhle 3 runs" in hi and "Seema:" in hi and "andaza hai" not in hi
    assert "from your last 3 runs" in P.card_text({**p, "hinglish": False})


def test_the_gate_passes_the_tenant_so_the_card_is_measured_per_tenant(caps, monkeypatch):
    from app.agent import research_plan as P

    async def fake_q(ask, note, a, settings):
        return {"sub_questions": ["a?", "b?", "c?", "d?"], "look_in": ["x"], "as_of": "today", "from_model": True}
    monkeypatch.setattr(P, "_questions", fake_q)
    for goals, inr in ((4, 40.0), (4, 80.0), (4, 120.0)):
        _finished("t6", goals, inr)
    big = "Do deep research on the Corvane Index market: size, players, growth. Sources with dates."
    out = run_(P.gate("t6", "c6", big, caps))
    assert "aapke pichhle" in out["text"] or "from your last 3 runs" in out["text"]
    out2 = run_(P.gate("t7", "c7", big, caps))
    assert "an estimate" in out2["text"]                                                               # another tenant: nothing measured


# ---------------------------------------------------------------- the report + the routes
def test_the_usage_report_says_what_is_assumed_or_unpriced(caps):
    _finished("t8", 4, 40.0)
    rep = bill.usage_report("t8")
    assert rep["today_inr"] == 40.0 and rep["left_today_inr"] == round(caps.research_daily_inr - 40.0, 2) and rep["measured"] is None
    txt = " ".join(rep["assumed"])
    assert "defaults" in txt and "UNKNOWN" in txt and "list price" in txt
    caps.research_search_inr = 0.4
    assert "UNKNOWN" not in " ".join(bill.usage_report("t8")["assumed"])
    assert rep["runs"][0]["cost_inr"] == 40.0


def test_the_http_routes_work_and_are_mounted(env):
    from app.research.api import make_router
    a = FastAPI()
    a.include_router(make_router(lambda: None, lambda: "default"))
    c = TestClient(a)
    rid = runner.start("default", "c1", "Q", ["g"], {}, hi=True)
    store.finish(store.create("default", "c", "Q", ["g"], {}), "done", {}, cost={"total_inr": 12.5})
    u = c.get("/api/research/usage").json()
    assert u["today_inr"] == 12.5 and u["caps"]["run_inr"] > 0 and u["assumed"]
    assert any(r["id"] == rid for r in c.get("/api/research/runs").json()["runs"])
    assert c.post(f"/api/research/runs/{rid}/stop").json() == {"status": "stopped"}
    assert c.post("/api/research/runs/rr_nope/stop").status_code == 404
    from app.main import app as real
    assert TestClient(real).get("/api/research/usage").status_code != 404, "/api/research is not mounted on the app"


def test_defaults_and_the_usage_label(env):
    s = get_settings()
    assert (s.research_run_cap_inr, s.research_daily_inr, s.research_call_reserve_inr, s.research_search_inr, s.research_fetch_inr) == (150.0, 600.0, 3.0, 0.0, 0.0)
    assert usage.FEATURE_LABEL["research"] == "Research"
