"""v0.475 R4 LAMBA KAAM - research that runs in the background, survives a restart, narrates, and reports itself.

Pinned: old page text is cleared from a worker's context (and the notes survive), a page read twice costs one page of budget, the engine
checkpoints after each goal and a resumed run keeps the finished goals and the clock already used, the persisted run's lifecycle
(queued -> running -> done / failed / stopped; a stopped run stays stopped), the worker slot (starts queued runs within the per-tenant cap,
picks a stalled run up again from its checkpoint, gives up after its tries), live narration in her language, the finish event that wakes the
brain, the wake text that WRITES the report from the dossier, the wake turn being a held + checked answer, the tools (default background,
status / result / stop, owner only), and the R0 live card not tripping on the plan wait or the hand-off.
"""
from __future__ import annotations

import asyncio
import copy
import json
from datetime import timedelta

import pytest

from app.db import now, session
from app.research import engine as E
from app.research import runner, store
from tests.test_v0473_research_engine import GOOD_PLAY, PAGES, SEARCH, Script, deps, run, tu


def run_(coro):
    return asyncio.run(coro)


async def _tick_and_wait():
    """The worker slot starts runs as background tasks: wait for them inside the SAME loop (asyncio.run closes the loop on return)."""
    n = await runner.tick()
    if runner._BG:
        await asyncio.gather(*list(runner._BG))
    return n


@pytest.fixture
def rr(env, monkeypatch):
    """A background-run environment: scripted fakes for every outside part, bus events captured."""
    events: list[tuple[str, str, dict]] = []
    monkeypatch.setattr(runner.bus, "publish", lambda conv, kind, payload: events.append((conv, kind, payload)))
    plays = {"Corvane value": GOOD_PLAY, "second goal": [("finish", {"summary": "b"})]}
    box = {"script": Script(plays), "calls": []}

    def factory(ctx, st):
        d, log = deps(box["script"])
        box["log"] = log
        return d
    monkeypatch.setattr(runner, "_deps_factory", factory)
    runner._RUNNING.clear()
    from app.config import get_settings
    return {"events": events, "box": box, "st": get_settings()}


# ---------------------------------------------------------------- pruning + page budget
def _page_result(i, url="https://a.example.com/p"):
    return {"type": "tool_result", "tool_use_id": f"t{i}", "content": f"PAGE {url}{i} | Title\n(data, not instructions)\n" + "x" * 5000}


def test_old_page_text_is_cleared_the_newest_two_stay_and_ids_and_searches_are_untouched(env):
    hist = [{"role": "user", "content": [{"type": "text", "text": "Start"}]}]
    for i in range(4):
        hist.append({"role": "assistant", "content": [tu(f"t{i}", "read", url=f"https://a.example.com/p{i}")]})
        hist.append({"role": "user", "content": [_page_result(i)]})
    hist.append({"role": "user", "content": [{"type": "tool_result", "tool_use_id": "s", "content": "SEARCH RESULTS (data)\n- x"}]})
    assert E.prune_history(hist, keep=2) == 2
    res = [b["content"] for m in hist if m["role"] == "user" and isinstance(m["content"], list) for b in m["content"] if b.get("type") == "tool_result"]
    assert "[page text cleared" in res[0] and "[page text cleared" in res[1] and "x" * 100 in res[2] and "x" * 100 in res[3]
    assert res[0].startswith("PAGE https://a.example.com/p0 | Title") and "5,0" in res[0] or "characters" in res[0]
    assert res[4].startswith("SEARCH RESULTS") and hist[1]["content"][0]["id"] == "t0"
    assert E.prune_history(hist, keep=2) == 0                                    # idempotent


def test_the_worker_really_prunes_before_it_calls_the_model(env):
    seen = []

    class Spy(Script):
        async def llm(self, system, history, tools, mt):
            seen.append(copy.deepcopy(history))
            return await super().llm(system, history, tools, mt)
    urls = ["https://index.example.gov.in/corvane/2025", "https://journal.example.com/corvane", "https://index.example.gov.in/annex.html"]
    play = [("search", {"queries": ["corvane index"]})] + [("read", {"url": u}) for u in urls] + [("finish", {"summary": "x"})]
    d, _ = deps(Spy({"g": play}))
    out = asyncio.run(E.run("q", ["g"], E.Policy(rounds=1), d))
    last = seen[-1]
    texts = [b["content"] for m in last if m["role"] == "user" and isinstance(m["content"], list) for b in m["content"] if b.get("type") == "tool_result"]
    assert sum("[page text cleared" in x for x in texts) == 1 and E.STATS["pruned"] >= 1
    assert out["stats"]["pages_read"] == 3                                        # clearing the text lost no page


def test_a_page_read_twice_costs_one_page_of_budget(env):
    u = "https://index.example.gov.in/corvane/2025"
    play = [("search", {"queries": ["corvane index"]}), ("read", {"url": u}), ("read", {"url": u}), ("read", {"url": u}),
            ("read", {"url": "https://journal.example.com/corvane"}), ("finish", {"summary": "x"})]
    d, log = run(["g"], Script({"g": play}), E.Policy(pages_per_task=2))
    assert d["stats"]["pages_read"] == 2 and log["fetches"].count(u) == 1


# ---------------------------------------------------------------- checkpoint + resume
def test_the_engine_checkpoints_after_each_goal_and_a_resume_skips_the_finished_ones(env):
    plays = {"g1": GOOD_PLAY, "g2": [("finish", {"summary": "second"})]}
    cps = []
    d, _ = deps(Script(plays))
    d.checkpoint = lambda cp: cps.append(json.loads(json.dumps(cp)))              # must be JSON-able
    out = asyncio.run(E.run("What is the Corvane Index?", ["g1", "g2"], E.Policy(rounds=1, parallel=1), d))
    assert len(cps) == 2 and [r["goal"] for r in cps[0]["results"]] == ["g1"] and cps[0]["round"] == 1
    assert cps[0]["pages"] and cps[0]["admitted"] and cps[0]["counts"]["reads"] == 1 and cps[0]["rounds"][0]["goals"] == ["g1", "g2"]
    # a restart after g1: only g2 is run again, g1's notes and the pages it read come back, the clock already used stays used
    class Boom(Script):
        async def llm(self, system, history, tools, mt):
            assert "YOUR GOAL: g1" not in system, "a finished goal was run again"
            return await super().llm(system, history, tools, mt)
    cp = cps[0]
    cp["elapsed"] = 100.0
    d2, _ = deps(Boom({"g2": [("finish", {"summary": "second again"})]}))
    seen = {}
    before = E.STATS["resumed"]
    out2 = asyncio.run(E.run("What is the Corvane Index?", ["g1", "g2"], E.Policy(rounds=1, parallel=1), d2, resume=cp))
    assert E.STATS["resumed"] == before + 1
    assert [t["goal"] for t in out2["tasks"]] == ["g1", "g2"] and out2["tasks"][0]["notes"][0]["verified"]
    assert out2["stats"]["pages_read"] == 1 and out2["stats"]["seconds"] >= 100 and out2["fields"][0]["confidence"] == "high"


def test_a_resume_in_a_later_round_goes_on_from_that_round(env):
    plays = {"g1": [("finish", {"summary": "a", "unresolved": "gap"})], "g1b follow-up": [("finish", {"summary": "c"})]}
    cps = []
    s = Script(plays, replan={"action": "tasks", "reasoning": "gap", "tasks": ["g1b follow-up"]})
    d, _ = deps(s)
    d.checkpoint = lambda cp: cps.append(json.loads(json.dumps(cp)))
    asyncio.run(E.run("q", ["g1"], E.Policy(rounds=2), d))
    mid = next(c for c in cps if c["round"] == 2 and not any(r["round"] == 2 for r in c["results"]))   # the checkpoint written at the re-plan
    d2, _ = deps(Script({"g1b follow-up": [("finish", {"summary": "c2"})]}))
    out = asyncio.run(E.run("q", ["g1"], E.Policy(rounds=2), d2, resume=mid))
    assert [t["round"] for t in out["tasks"]] == [1, 2] and out["tasks"][1]["summary"] == "c2"


def test_a_checkpoint_that_cannot_be_written_never_kills_the_research(env):
    d, _ = deps(Script({"g": GOOD_PLAY}))
    d.checkpoint = lambda cp: (_ for _ in ()).throw(RuntimeError("disk full"))
    out = asyncio.run(E.run("q", ["g"], E.Policy(rounds=1), d))
    assert out["stats"]["verified_notes"] == 1


# ---------------------------------------------------------------- the persisted run
def test_the_run_lifecycle_and_a_stopped_run_stays_stopped(env):
    rid = store.create("t1", "c1", "Q?", ["a", "b"], {"hi": False})
    v = store.get(rid)
    assert v["status"] == "queued" and v["goals"] == ["a", "b"] and v["checkpoint"] is None and v["tries"] == 0
    assert store.set_status(rid, "running", only_from=("queued",)) and not store.set_status(rid, "running", only_from=("queued",))
    store.save_checkpoint(rid, {"round": 1, "results": []}, {"goals_done": 0})
    assert store.get(rid)["checkpoint"]["round"] == 1
    assert store.set_status(rid, "stopped", "owner ne roka")
    assert store.finish(rid, "done", {"x": 1}) is False and store.get(rid)["status"] == "stopped" and store.get(rid)["dossier"] is None
    store.save_checkpoint(rid, {"round": 9}, {})                                  # a stopped run takes no more checkpoints
    assert store.get(rid)["checkpoint"]["round"] == 1
    rid2 = store.create("t1", "c1", "Q?", ["a"], {})
    assert store.finish(rid2, "done", {"stats": {}}) and store.get(rid2)["dossier"] == {"stats": {}} and store.get(rid2)["checkpoint"] is None


def test_candidates_respect_the_tenant_cap_and_pick_up_a_stalled_run_and_give_up_after_the_tries(env):
    a, b, c = (store.create("t1", "c", "Q", ["g"], {}) for _ in range(3))
    other = store.create("t2", "c", "Q", ["g"], {})
    ids = store.candidates(now() - timedelta(seconds=180), per_tenant_running_max=2, tries_max=3)
    assert ids.count(a) + ids.count(b) + ids.count(c) == 2 and other in ids            # two for t1, the third waits
    # a running run that stopped heartbeating
    stalled = store.create("t3", "c", "Q", ["g"], {})
    with session() as s:
        r = s.get(store.ResearchRun, stalled)
        r.status, r.tries, r.updated_at = "running", 1, now() - timedelta(seconds=600)
    assert stalled in store.candidates(now() - timedelta(seconds=180), 2, 3)
    with session() as s:
        r = s.get(store.ResearchRun, stalled)
        r.tries = 3
        r.updated_at = now() - timedelta(seconds=600)
    assert stalled not in store.candidates(now() - timedelta(seconds=180), 2, 3)
    assert store.get(stalled)["status"] == "failed" and "too many times" in store.get(stalled)["error"]


def test_old_finished_rows_are_forgotten(env):
    rid = store.create("t", "c", "Q", ["g"], {})
    store.finish(rid, "done", {})
    with session() as s:
        s.get(store.ResearchRun, rid).updated_at = now() - timedelta(days=30)
    assert store.forget_old(14) >= 1 and store.get(rid) is None


# ---------------------------------------------------------------- the runner
def test_a_background_run_goes_end_to_end_narrates_and_reports_itself(rr):
    rid = runner.start("t1", "c1", "What is the Corvane Index?", ["Corvane value", "second goal"], {}, hi=True)
    assert rr["events"][0][1] == "research_run" and rr["events"][0][2]["status"] == "queued"
    run_(runner.run_background(rid))
    v = store.get(rid)
    assert v["status"] == "done" and v["dossier"]["stats"]["verified_notes"] == 1 and v["checkpoint"] is None
    kinds = [(k, p.get("status")) for _c, k, p in rr["events"]]
    assert ("research_run", "done") in kinds and kinds.count(("research_run", "running")) >= 2      # a progress event per finished goal
    steps = [p["label"] for _c, k, p in rr["events"] if k == "step"]
    assert any("khoj raha hoon" in x for x in steps) and any("padh raha hoon: index.example.gov.in" in x for x in steps)
    assert any(x.startswith("1/2 - ") for x in steps)                                  # the goal's number rides on every line
    done = [p for _c, k, p in rr["events"] if k == "research_run" and p["status"] == "done"][0]
    assert "report likhne ko taiyaar" in done["say"] and done["id"] == rid
    assert rid not in runner._RUNNING


def test_narration_is_in_her_language(rr):
    rid = runner.start("t1", "c1", "What is it?", ["Corvane value"], {}, hi=False)
    run_(runner.run_background(rid))
    steps = [p["label"] for _c, k, p in rr["events"] if k == "step"]
    assert any("reading: index.example.gov.in" in x for x in steps) and not any("padh raha" in x for x in steps)
    assert runner.line("note", True, 2, 5, "cbse.gov.in") == "2/5 - cbse.gov.in se baat note ki"


def test_a_run_that_found_nothing_fails_honestly(rr):
    rr["box"]["script"] = Script({"Corvane value": [("finish", {"summary": "nothing", "unresolved": "no pages"})]})
    rid = runner.start("t1", "c1", "Q?", ["Corvane value"], {}, hi=False)
    run_(runner.run_background(rid))
    assert store.get(rid)["status"] == "failed" and "no readable pages" in store.get(rid)["error"]
    assert [p for _c, k, p in rr["events"] if k == "research_run"][-1]["status"] == "failed"


def test_a_crash_in_the_engine_is_a_failed_run_not_a_dead_worker(rr, monkeypatch):
    async def boom(*a, **k):
        raise RuntimeError("engine blew up")
    monkeypatch.setattr(E, "run", boom)
    rid = runner.start("t1", "c1", "Q?", ["g"], {}, hi=True)
    run_(runner.run_background(rid))
    assert store.get(rid)["status"] == "failed" and "engine blew up" in store.get(rid)["error"]
    assert [p for _c, k, p in rr["events"] if k == "research_run"][-1]["say"] == "research beech mein ruk gaya"


def test_a_restart_carries_on_from_the_checkpoint(rr):
    """The process died after goal 1. The row says running with an old heartbeat and a checkpoint; the next worker tick resumes it."""
    class Boom(Script):
        async def llm(self, system, history, tools, mt):
            assert "YOUR GOAL: Corvane value" not in system, "a finished goal was run again after the restart"
            return await super().llm(system, history, tools, mt)
    first, _ = deps(Script({"Corvane value": GOOD_PLAY}))
    cps = []
    first.checkpoint = lambda cp: cps.append(json.loads(json.dumps(cp)))
    asyncio.run(E.run("What is the Corvane Index?", ["Corvane value", "second goal"], E.Policy(rounds=1, parallel=1), first))
    rid = runner.start("t1", "c1", "What is the Corvane Index?", ["Corvane value", "second goal"], {}, hi=True)
    with session() as s:
        r = s.get(store.ResearchRun, rid)
        r.status, r.tries, r.checkpoint, r.updated_at = "running", 1, json.dumps(cps[0]), now() - timedelta(seconds=900)
    rr["box"]["script"] = Boom({"second goal": [("finish", {"summary": "after restart"})]})
    assert run_(_tick_and_wait()) == 1
    v = store.get(rid)
    assert v["status"] == "done" and v["tries"] == 2 and [t["goal"] for t in v["dossier"]["tasks"]] == ["Corvane value", "second goal"]
    assert v["dossier"]["tasks"][0]["notes"][0]["verified"]


def test_the_tick_starts_queued_runs_within_the_cap_and_honours_the_switches(rr):
    rr["st"].research_bg_max_running = 1
    try:
        a = runner.start("t1", "c1", "Q", ["Corvane value"], {}, hi=True)
        b = runner.start("t1", "c1", "Q", ["Corvane value"], {}, hi=True)
        assert run_(_tick_and_wait()) == 1
        assert {store.get(a)["status"], store.get(b)["status"]} == {"done", "queued"}
        rr["st"].research_background = False
        assert run_(runner.tick()) == 0                                              # background switched off: nothing is started
    finally:
        rr["st"].research_bg_max_running, rr["st"].research_background = 2, True


def test_stop_ends_the_run_keeps_it_stopped_and_says_so(rr):
    rid = runner.start("t1", "c1", "Q", ["Corvane value"], {}, hi=True)
    assert runner.stop("t2", rid) == "missing"                                       # another tenant cannot stop it
    assert runner.stop("t1", rid) == "stopped" and runner.stop("t1", rid) == "stopped"
    run_(runner.run_background(rid))                                                  # a stopped run is not started
    assert store.get(rid)["status"] == "stopped" and store.get(rid)["dossier"] is None
    assert [p for _c, k, p in rr["events"] if k == "research_run"][-1]["status"] == "stopped"


def test_a_stop_in_the_middle_ends_the_run_at_its_next_step_without_a_report(rr):
    rid = runner.start("t1", "c1", "Q", ["Corvane value", "second goal"], {}, hi=True)
    orig = store.save_checkpoint

    def stop_after_first(run_id, cp, progress=None):
        orig(run_id, cp, progress)
        runner.stop("t1", run_id)
    store_cp = store.save_checkpoint
    store.save_checkpoint = stop_after_first
    try:
        run_(runner.run_background(rid))
    finally:
        store.save_checkpoint = store_cp
    assert store.get(rid)["status"] == "stopped" and not any(p["status"] == "done" for _c, k, p in rr["events"] if k == "research_run")


# ---------------------------------------------------------------- the tools
def _ctx(actor="owner", conv="c1", tenant="t1"):
    from app.agent.tools import Ctx
    return Ctx(tenant_id=tenant, conversation_id=conv, actor=actor)


def test_research_run_defaults_to_the_background_and_returns_at_once(rr):
    from app.agent.research_tools import research_run
    out = run_(research_run(_ctx(), question="Research karo: Corvane Index", sub_questions=["a", "b"], exclude_domains=["spam.example.org"]))
    assert out["started"] is True and out["run_id"].startswith("rr") and "ONE short line" in out["say"] and "END" not in out.get("dossier", "")
    v = store.get(out["run_id"])
    assert v["status"] == "queued" and v["goals"] == ["a", "b"] and v["policy"]["hi"] is True
    assert v["policy"]["over"] == {"exclude_domains": ["spam.example.org"]}
    inline = run_(research_run(_ctx(), question="What is it?", sub_questions=["Corvane value"], mode="inline"))
    assert "RESEARCH DOSSIER" in inline["dossier"]
    rr["st"].research_background = False
    try:
        assert "RESEARCH DOSSIER" in run_(research_run(_ctx(), question="What is it?", sub_questions=["Corvane value"]))["dossier"]
    finally:
        rr["st"].research_background = True


def test_research_status_check_result_and_stop(rr):
    from app.agent.research_tools import research_status
    assert "koi research run nahi" in run_(research_status(_ctx(), action="check"))["note"]
    rid = runner.start("t1", "c1", "What is the Corvane Index?", ["Corvane value"], {}, hi=False)
    chk = run_(research_status(_ctx(), action="check"))
    assert chk["runs"][0]["id"] == rid and chk["runs"][0]["status"] == "queued"
    assert run_(research_status(_ctx(), action="result"))["status"] == "queued"          # no dossier yet
    run_(runner.run_background(rid))
    res = run_(research_status(_ctx(), action="result"))
    assert "RESEARCH DOSSIER" in res["dossier"] and res["run_id"] == rid and "doc_studio" in res["say"]
    got = E.recall("c1")
    assert got is not None and got["_delivered"] > 0                                      # remembered for the report check
    assert "pehle hi done" in run_(research_status(_ctx(), action="stop", id=rid))["note"]
    other = runner.start("t1", "c1", "Q", ["g"], {}, hi=True)
    assert "roka gaya" in run_(research_status(_ctx(), action="stop", id=other))["note"] and store.get(other)["status"] == "stopped"
    from app.agent.tools import ToolError
    with pytest.raises(ToolError):
        run_(research_status(_ctx(actor="customer:1"), action="check"))
    assert "koi research run nahi" in run_(research_status(_ctx(tenant="t9", conv="c9"), action="check"))["note"]   # another tenant sees nothing


# ---------------------------------------------------------------- the finish -> wake path
def test_kaamwatch_shapes_the_research_events(env):
    from app import kaamwatch
    j = kaamwatch.shape("research_run", {"id": "rr_abcd1234", "number": "research 1234", "name": "Corvane", "status": "queued", "say": "starting"})
    assert j["state"] == "working" and j["label"] == "Research" and j["kind"] == "research_run"
    d = kaamwatch.shape("research_run", {"id": "rr_abcd1234", "number": "research 1234", "name": "Corvane", "status": "done", "say": "ready"})
    assert d["state"] == "done" and d["key"] == "research_run:rr_abcd1234"
    assert kaamwatch.shape("research_run", {"id": "x", "status": "failed", "say": "no"})["state"] == "failed"


def test_a_finished_run_wakes_the_brain_to_write_the_report_from_the_dossier(env):
    from app import kaam_followup as KF
    r = KF.KaamFollowup(tenant_id="t", conversation_id="c", key="research_run:rr_abc", kind="research_run", label="Research",
                        title="research abc · Corvane", state="done", detail="report likhne ko taiyaar: 6 pages")
    txt = KF._wake_text(r)
    assert txt.startswith("[Santosh worker update") and runner.is_report_due(txt) and 'run="rr_abc"' in txt
    assert "research_status" in txt and "id=rr_abc" in txt and "dobara mat chalao" in txt and "jo confirm nahi" in txt
    r.state = "failed"
    assert not runner.is_report_due(KF._wake_text(r))                                     # a failed run gets the ordinary news line


def test_the_wake_text_brings_the_research_tools_into_view(env):
    from app.agent import admit
    from app.config import get_settings
    names = {t["name"] for t in admit.plan_for('[Santosh worker update] <research_report_due run="rr_x"> research_status id=rr_x', get_settings()).specs()}
    assert {"research_status", "research_run"} <= names


def test_the_wake_turn_that_writes_the_report_is_checked_and_a_made_up_figure_goes_back_for_one_fix(env, monkeypatch):
    """End to end through run_turn(actor='wake'): the brain fetches the dossier with research_status, drafts a report with a figure
    no note carries, the R3 check sends it back once, and the corrected report is the one she gets."""
    from tests.test_bazar import bz  # noqa: F401
    from tests.test_v0186_long_goal import FakeBrain, _set_brain, txt
    import app.agent.santosh as S
    from app import chats, kaam_followup as KF
    from app.config import get_settings
    monkeypatch.setattr(chats, "enabled", lambda: False)
    d, _ = deps(Script({"Corvane value": GOOD_PLAY}))
    dossier = asyncio.run(E.run("What is the Corvane Index?", ["Corvane value"], E.Policy(rounds=1), d))
    from app.db import Conversation
    with session() as s:
        c = Conversation(tenant_id="default")
        s.add(c)
        s.flush()
        conv = c.id
    rid = store.create("default", conv, "What is the Corvane Index?", ["Corvane value"], {"hi": False})
    store.finish(rid, "done", dossier)
    good = ("The Corvane Index was 412.5 in March 2025 [1].\n\nWhat I could not confirm: whether the baseline was revised later.\n\n"
            "Sources:\n[1] Test Authority, 2025 - https://index.example.gov.in/corvane/2025\n")
    bad = good.replace("412.5", "999.9")
    st = get_settings()
    st.hard_check = True
    try:
        brain = _set_brain(monkeypatch, FakeBrain([
            ([tu(1, "research_status", action="result", id=rid)], "tool_use"),
            ([txt(bad)], "end_turn"),
            ([txt(good)], "end_turn")]))
        r = KF.KaamFollowup(tenant_id="default", conversation_id=conv, key=f"research_run:{rid}", kind="research_run", label="Research",
                            title="research · Corvane", state="done", detail="ready")
        out = asyncio.run(S.run_turn(conv, KF._wake_text(r), tenant_id="default", actor="wake", save_user=False))
        notes = [m["content"][0]["text"] for k in brain.seen for m in k["messages"][-1:] if isinstance(m["content"], list)
                 and m["content"] and isinstance(m["content"][0], dict) and str(m["content"][0].get("text", "")).startswith("[System: JAANCH")]
        assert any("999.9" in n for n in notes), "the made-up figure was not sent back for a fix"
        assert "412.5" in out and "999.9" not in out
    finally:
        st.hard_check = False


def test_the_r0_live_card_turns_off_the_plan_wait_and_the_hand_off_while_it_runs(env, monkeypatch):
    from app.config import get_settings
    from app.quality import researchcard as R
    st = get_settings()
    seen = {}

    async def fake_one(ask, tenant, judge):
        seen["bg"], seen["gate"] = st.research_background, st.research_plan_gate
        return {"id": ask["id"], "kind": ask["kind"], "right": True, "checks": {}, "inr": 0.0, "seconds": 1.0}
    monkeypatch.setattr(R, "_one", fake_one)
    asyncio.run(R.live_card([R.ASKS[0]]))
    assert seen == {"bg": False, "gate": False} and st.research_background is True and st.research_plan_gate is True


def test_config_defaults_and_the_family_registers_the_status_tool(env):
    from app.agent import tools
    from app.config import Settings
    s = Settings()
    assert (s.research_background, s.research_bg_soft_s, s.research_bg_max_running, s.research_bg_stale_s, s.research_bg_tries) == (True, 1500.0, 2, 180, 3)
    assert tools.FAMILY_OF["research_status"] == "research" and "research_status" in tools.HANDLERS
