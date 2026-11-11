"""v0.480 R9 NIGRANI - watched research topics, and the held review.

Pinned: the diff (changed / new / not seen / unchanged, one-to-one matching, rounding is not a change), that a watch needs her yes and a cost shown, the limits (three
active, never faster than daily, a monthly cap, three failed checks pause it), the scheduler (due only, never two runs of one watch, the daily ceiling skips, an
unavailable engine skips), that a check that changed nothing says NOTHING (and the baseline too) while a real change wakes the brain with a digest, that the change
message is checked with the EARLIER values admitted, and the reviewer (named problems, ≤ 4, never blocking, after the code checks, replacing the generic one).
"""
from __future__ import annotations

import asyncio
import json
import re
from datetime import timedelta
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.config import get_settings
from app.db import now, session
from app.research import claims as C
from app.research import engine as E
from app.research import review as RV
from app.research import runner, store
from app.research import watch as W
from tests.test_v0473_research_engine import GOOD_PLAY, PAGES, Script, deps, tu


def run_(c):
    return asyncio.run(c)


def snap(claim, figs, host="a.gov.in", conf="high", date="March 2025", n=1):
    return {"claim": claim, "figures": list(figs), "host": host, "date": date, "conf": conf, "url": f"https://{host}/p", "n": n}


# ---------------------------------------------------------------- the diff
def test_the_first_comparison_is_a_baseline_and_says_nothing(env):
    d = W.diff(None, [snap("The Corvane Index was 412.5", [412.5])])
    assert d["baseline"] is True and d["material"] is False and W.diff([], [snap("x y z", [1.5])])["baseline"] is True


def test_unchanged_changed_new_and_not_seen_are_told_apart(env):
    old = [snap("The Corvane Index was 412.5 in March", [412.5]), snap("Output of Corvane units was 18240", [18240.0]), snap("Dispatch backlog stood at 77.7", [77.7], host="b.gov.in")]
    new = [snap("The Corvane Index was 430.0 in April", [430.0], date="April 2025"),                 # same finding, the figure moved
           snap("Output of Corvane units was 18240", [18240.0]),                                         # same
           snap("Imports of rare Corvane crystals rose to 9.5 lakh", [950000.0], host="c.gov.in")]       # new; the backlog finding is not seen this time
    d = W.diff(old, new)
    assert d["baseline"] is False and d["material"] is True and d["unchanged"] == 1
    assert len(d["changed"]) == 1 and d["changed"][0]["old_figures"] == [412.5] and d["changed"][0]["new_figures"] == [430.0] and d["changed"][0]["old_date"] == "March 2025"
    assert [n["claim"][:20] for n in d["new"]] == ["Imports of rare Corv"] and [g["claim"][:20] for g in d["gone"]] == ["Dispatch backlog sto"]


def test_rounding_is_not_a_change_and_a_pure_not_seen_is_not_material(env):
    old = [snap("The Corvane Index was 412.5 in March", [412.5])]
    assert W.diff(old, [snap("The Corvane Index was 412.6 in March", [412.6])])["material"] is False         # inside the rounding tolerance
    gone_only = W.diff(old, [])
    assert gone_only["material"] is False and len(gone_only["gone"]) == 1                                      # not seen is information, never an alarm
    nofig = W.diff([snap("The scheme remains open to applicants nationwide", [])], [snap("The scheme remains open to applicants nationwide", [])])
    assert nofig["unchanged"] == 1 and nofig["material"] is False


def test_matching_is_one_to_one_so_two_new_findings_cannot_hide_behind_one_old_one(env):
    old = [snap("The Corvane Index was 412.5 in March", [412.5])]
    new = [snap("The Corvane Index was 430.0 in April", [430.0]), snap("The Corvane Index was 99.0 for exports in April", [99.0])]
    d = W.diff(old, new)
    assert len(d["changed"]) == 1 and len(d["new"]) == 1


def test_the_snapshot_keeps_only_verified_backed_medium_or_high_findings(env):
    fields = [{"verified": True, "supported": True, "confidence": "high", "claim": "a 12.5", "figures": [12.5], "url": "https://x.gov.in/a", "n": 1, "date": "2025"},
              {"verified": True, "supported": True, "confidence": "low", "claim": "b 13.5", "figures": [13.5], "url": "https://y.com/a", "n": 2},
              {"verified": False, "supported": True, "confidence": "unconfirmed", "claim": "c 14.5", "figures": [14.5], "url": "https://z.com/a", "n": 3},
              {"verified": True, "supported": False, "confidence": "low", "claim": "d 15.5", "figures": [15.5], "url": "https://w.com/a", "n": 4}]
    s = W.snapshot_of({"fields": fields})
    assert [x["claim"] for x in s] == ["a 12.5"] and s[0]["host"] == "x.gov.in"


def test_the_change_message_is_checked_with_the_earlier_values_admitted(env):
    d, _ = deps(Script({"g": GOOD_PLAY}))
    dossier = run_(E.run("What is the Corvane Index?", ["g"], E.Policy(rounds=1), d))
    new_fields = dossier["fields"]
    diff = {"baseline": False, "changed": [{"claim": "The Corvane Index was 412.5", "old_claim": "The Corvane Index was 388.0", "old_figures": [388.0], "new_figures": [412.5],
                                            "date": "March 2025", "old_date": "Feb 2025", "url": new_fields[0]["url"], "n": new_fields[0]["n"], "old_n": 1}],
            "new": [], "gone": [{"claim": "Backlog stood at 77.7", "figures": [77.7], "url": "https://b.gov.in/x", "date": "", "host": "b.gov.in"}], "unchanged": 0, "material": True}
    chk = W.check_dossier(dossier, diff)
    msg = ("The Corvane Index moved from 388.0 earlier to 412.5 in March 2025 [1]. The backlog of 77.7 was not seen this time. "
           "What I could not confirm: whether the earlier reading was revised.")
    assert C.check_report(msg, chk) == []
    assert C.check_report(msg, dossier) != []                                                              # without the earlier values the same message would be refused
    bad = C.check_report(msg.replace("388.0", "399.9"), chk)
    assert bad and "399.9" in bad[0]
    txt = W.render_change({"id": "rw_1", "every_days": 7, "question": "Corvane?", "last_checked_at": None}, diff, {"cost": {"total_inr": 12.0}}, dossier)
    assert "CHANGED (1)" in txt and "was 388.0 (Feb 2025) -> now 412.5 (March 2025)" in txt and "NOT SEEN THIS TIME (1)" in txt and "not proof it changed" in txt and "Rs 12.0" in txt


# ---------------------------------------------------------------- the tool: a watch needs her yes
@pytest.fixture
def wx(env, monkeypatch):
    st = get_settings()
    keep = (st.research_watch_month_inr, st.research_daily_inr, st.research_run_cap_inr, st.research_background, st.research_engine_on)
    events = []
    monkeypatch.setattr(runner.bus, "publish", lambda conv, kind, payload: events.append((conv, kind, payload)))
    from app.events import bus
    monkeypatch.setattr(bus, "publish", lambda conv, kind, payload: events.append((conv, kind, payload)))
    runner._RUNNING.clear()
    yield {"st": st, "events": events}
    st.research_watch_month_inr, st.research_daily_inr, st.research_run_cap_inr, st.research_background, st.research_engine_on = keep


def _ctx(actor="owner", tenant="t1", conv="c1"):
    from app.agent.tools import Ctx
    return Ctx(tenant_id=tenant, conversation_id=conv, actor=actor)


def tool(**kw):
    from app.agent.research_tools import research_watch
    return run_(research_watch(_ctx(kw.pop("actor", "owner"), kw.pop("tenant", "t1"), kw.pop("conv", "c1")), **kw))


ADD = dict(action="add", question="Research karo: Corvane Index ka latest value", sub_questions=["value?", "growth?", "players?"])


def test_adding_a_watch_first_shows_the_cost_and_creates_nothing_until_she_says_yes(wx):
    p = tool(**ADD, every="weekly")
    assert p["proposal"] is True and p["every_days"] == 7 and p["goals"] == 3 and p["est_per_check_inr"] is None and "not measured" in p["estimate_source"] or "no measured cost" in p["estimate_source"]
    assert p["month_cap_inr"] == 300.0 and p["run_ceiling_inr"] > 0 and "confirm=true" in p["say"] and "says nothing" in p["say"]
    assert W.list_for("t1") == []
    made = tool(**ADD, every="weekly", confirm=True)
    assert made["created"] is True and made["every_days"] == 7 and "now (it sets the baseline quietly)" in made["first_check"]
    w = W.get(made["id"])
    assert w["status"] == "active" and w["hi"] is True and w["goals"] == ["value?", "growth?", "players?"] and w["next_run_at"] <= now() + timedelta(seconds=5)
    assert tool(action="list")["watches"][0]["id"] == made["id"] and tool(action="list", tenant="t2")["watches"] == []


def test_a_measured_cost_replaces_the_unknown_in_the_proposal(wx):
    for goals, inr in ((3, 30.0), (3, 60.0), (3, 90.0)):
        r = store.create("t1", "c", "Q", [f"g{i}" for i in range(goals)], {})
        store.finish(r, "done", {}, cost={"total_inr": inr})
    p = tool(**ADD, every="daily")
    assert p["est_per_check_inr"] == 60.0 and "from your last 3 runs" in p["estimate_source"] and p["est_per_month_inr"] == 1800.0


def test_the_frequency_is_parsed_and_never_faster_than_daily(wx):
    assert [tool(**ADD, every=e)["every_days"] for e in ("daily", "weekly", "fortnightly", "monthly", "3", 0, "0.2")] == [1, 7, 14, 30, 3, 1, 1]
    from app.agent.tools import ToolError
    with pytest.raises(ToolError, match="daily | weekly"):
        tool(**ADD, every="hourly")


def test_at_most_three_active_watches_and_a_vendor_needs_its_gates(wx):
    from app.agent.tools import ToolError
    ids = [tool(**ADD, confirm=True)["id"] for _ in range(3)]
    with pytest.raises(ToolError, match="already watch 3"):
        tool(**ADD, confirm=True)
    assert tool(action="pause", id=ids[0])["done"] == "pause" and W.get(ids[0])["status"] == "paused"
    fourth = tool(**ADD, confirm=True)["id"]
    with pytest.raises(ToolError, match="already watch 3"):
        tool(action="resume", id=ids[0])
    with pytest.raises(ToolError, match="RESEARCH_ENGINES_ALLOWED"):
        tool(**ADD, engine="exa", confirm=True)
    assert fourth


def test_delete_needs_a_yes_and_belongs_to_its_tenant_and_only_the_owner_may_watch(wx):
    from app.agent.tools import ToolError
    wid = tool(**ADD, confirm=True)["id"]
    assert tool(action="delete", id=wid)["proposal"] is True and W.get(wid)["status"] == "active"
    assert tool(action="delete", id=wid, confirm=True)["done"] == "delete" and W.get(wid)["status"] == "deleted" and tool(action="list")["watches"] == []
    with pytest.raises(ToolError, match="was not found"):
        tool(action="pause", id=wid, tenant="t2")
    with pytest.raises(ToolError, match="Only the owner"):
        tool(action="list", actor="customer:3")


def test_a_baseline_from_the_research_just_delivered_needs_one_and_waits_a_period(wx):
    from app.agent.tools import ToolError
    with pytest.raises(ToolError, match="no research in this chat"):
        tool(**ADD, baseline="last", confirm=True)
    d, _ = deps(Script({"g": GOOD_PLAY}))
    E.remember("c1", run_(E.run("What is the Corvane Index?", ["g"], E.Policy(rounds=1), d)))
    made = tool(**ADD, every="weekly", baseline="last", confirm=True)
    w = W.get(made["id"])
    assert "after one period" in made["first_check"] and w["snapshot"] and w["next_run_at"] > now() + timedelta(days=6) and w["last_checked_at"] is not None


# ---------------------------------------------------------------- the scheduler
def test_only_due_active_watches_start_and_never_two_runs_of_one(wx):
    due = W.add("t1", "c1", "Q due?", ["g"], 7)["id"]
    later = W.add("t1", "c2", "Q later?", ["g"], 7, baseline={"fields": []})["id"]
    paused = W.add("t1", "c3", "Q paused?", ["g"], 7)["id"]
    W.set_status(paused, "t1", "paused")
    assert run_(W.tick()) == 1
    w = W.get(due)
    assert w["last_run_id"] and w["next_run_at"] > now() + timedelta(days=6) and store.get(w["last_run_id"])["policy"]["watch"] == due
    assert W.get(later)["last_run_id"] == "" and W.get(paused)["last_run_id"] == ""
    with session() as s:                                                       # due again, but its last run has not finished
        s.get(W.ResearchWatch, due).next_run_at = now() - timedelta(minutes=1)
    assert run_(W.tick()) == 0


def test_a_scheduled_check_is_quiet_when_it_starts(wx):
    W.add("t1", "c1", "Q due?", ["g"], 7)
    run_(W.tick())
    assert not [e for e in wx["events"] if e[1] == "research_run"]


def test_two_watches_per_pass_at_most(wx):
    for i in range(3):
        W.add("t1", f"c{i}", f"Q{i}?", ["g"], 7)
    assert run_(W.tick()) == 2 and run_(W.tick()) == 1


def test_the_daily_ceiling_skips_a_check_and_notes_why_then_tries_again_later(wx):
    wx["st"].research_daily_inr = 10.0
    r = store.create("t1", "c", "Q", ["g"], {})
    store.finish(r, "done", {}, cost={"total_inr": 9.0})
    wid = W.add("t1", "c1", "Q?", ["g"], 7)["id"]
    assert run_(W.tick()) == 0
    w = W.get(wid)
    assert "skipped" in w["note"] and w["next_run_at"] > now() + timedelta(hours=5) and w["last_run_id"] == "" and W.STATS["skipped"] >= 1


def test_an_unavailable_engine_skips_the_check_with_the_reason(wx):
    wid = W.add("t1", "c1", "Q?", ["g"], 7, engine="exa")["id"]
    assert run_(W.tick()) == 0 and "engine not available" in W.get(wid)["note"] and "RESEARCH_ENGINES_ALLOWED" in W.get(wid)["note"]


def test_a_watch_that_spent_its_monthly_cap_pauses_itself_and_says_so_once(wx):
    wid = W.add("t1", "c1", "Q?", ["g"], 7)["id"]
    with session() as s:
        s.get(W.ResearchWatch, wid).month_cap_inr = 50.0
    r = store.create("t1", "c1", "Q?", ["g"], {"watch": wid})
    store.finish(r, "done", {}, cost={"total_inr": 55.0})
    assert W.spent_this_month(wid, "t1") == 55.0
    assert run_(W.tick()) == 0
    assert W.get(wid)["status"] == "paused" and W.get(wid)["note"] == "monthly cap reached"
    ev = [p for _c, k, p in wx["events"] if k == "research_watch"]
    assert len(ev) == 1 and ev[0]["status"] == "stopped" and "monthly cap" in ev[0]["say"]
    assert run_(W.tick()) == 0 and len([1 for _c, k, p in wx["events"] if k == "research_watch"]) == 1             # paused: nothing more is said


# ---------------------------------------------------------------- a finished check: quiet, or a real change
def _done_run(wid, dossier, tenant="t1", conv="c1"):
    rid = store.create(tenant, conv, "Q?", ["g"], {"watch": wid})
    store.finish(rid, "done", dossier, cost={"total_inr": 20.0})
    return {**store.get(rid), "id": rid}


def _dossier(value="412.5", period="March 2025"):
    d, _ = deps(Script({"g": GOOD_PLAY}))
    base = run_(E.run("What is the Corvane Index?", ["g"], E.Policy(rounds=1), d))
    for fld in base["fields"]:
        fld["claim"] = fld["claim"].replace("412.5", value)
        fld["figures"] = [float(value)]
        fld["date"] = period
    return base


def test_the_baseline_and_an_unchanged_check_say_nothing_and_a_change_wakes_the_brain(wx):
    wid = W.add("t1", "c1", "What is the Corvane Index?", ["g"], 7)["id"]
    assert W.on_run_done(_done_run(wid, _dossier()), "done", _dossier()) == "baseline"
    assert W.get(wid)["snapshot"] and W.get(wid)["checks"] == 1 and not [e for e in wx["events"] if e[1] == "research_watch"]
    assert W.on_run_done(_done_run(wid, _dossier()), "done", _dossier()) == "quiet"
    assert W.get(wid)["checks"] == 2 and W.get(wid)["changes"] == 0 and not [e for e in wx["events"] if e[1] == "research_watch"]
    moved = _dossier("430.0", "April 2025")
    run = _done_run(wid, moved)
    assert W.on_run_done(run, "done", moved) == "changed"
    w = W.get(wid)
    assert w["changes"] == 1 and w["last_change_at"] is not None and w["last_diff"]["changed"][0]["old_figures"] == [412.5] and w["last_diff"]["changed"][0]["new_figures"] == [430.0]
    ev = [(c, p) for c, k, p in wx["events"] if k == "research_watch"]
    assert len(ev) == 1 and ev[0][0] == "c1" and ev[0][1]["status"] == "done" and ev[0][1]["watch"] == wid and "1 change(s) found" in ev[0][1]["say"]


def test_failed_checks_are_counted_and_the_third_in_a_row_pauses_the_watch(wx):
    wid = W.add("t1", "c1", "Q?", ["g"], 7)["id"]
    rid = store.create("t1", "c1", "Q?", ["g"], {"watch": wid})
    run = {**store.get(rid), "id": rid, "error": "no readable pages were found"}
    assert W.on_run_done(run, "failed", None) == "failed" and W.get(wid)["fail_count"] == 1 and "no readable pages" in W.get(wid)["note"]
    assert W.on_run_done(run, "failed", None) == "failed"
    assert W.on_run_done(run, "failed", None) == "paused" and W.get(wid)["status"] == "paused"
    ev = [p for _c, k, p in wx["events"] if k == "research_watch"]
    assert len(ev) == 1 and "3 checks in a row" in ev[0]["say"]
    assert W.on_run_done(run, "stopped", None) == "stopped"
    W.set_status(wid, "t1", "active")
    assert W.get(wid)["fail_count"] == 0                                                     # resuming starts clean
    assert W.on_run_done({**run, "policy": {}}, "done", {"fields": []}) == "gone"


# ---------------------------------------------------------------- the run, end to end through the runner
def play_for(value):
    """GOOD_PLAY with the figure the page carries NOW (a note's words must really be on the page, or it is NOT VERIFIED and no finding exists to compare)."""
    return [(n, ({**a, "claim": a["claim"].replace("412.5", value), "excerpt": a["excerpt"].replace("412.5", value)} if n == "note" else a)) for n, a in GOOD_PLAY]


@pytest.fixture
def pages(wx, monkeypatch):
    state = {"value": "412.5"}
    base = PAGES["https://index.example.gov.in/corvane/2025"]["text"]

    def factory(ctx, st):
        d, _ = deps(Script({}))
        from tests.test_v0478_research_runoff import AnyGoal
        d.llm = AnyGoal(play_for(state["value"])).llm

        async def fetch(url):
            got = dict(PAGES.get(url) or PAGES["https://index.example.gov.in/corvane/2025"])
            got["text"] = base.replace("412.5", state["value"])
            return got
        d.fetch = fetch
        return d
    monkeypatch.setattr(runner, "_deps_factory", factory)
    return state


def test_a_watch_run_goes_through_the_runner_quietly_and_only_the_change_reaches_the_chat(pages, wx):
    wid = W.add("t1", "c1", "What is the Corvane Index?", ["value?"], 7)["id"]
    assert run_(W.tick()) == 1
    rid = W.get(wid)["last_run_id"]
    run_(runner.run_background(rid))
    assert store.get(rid)["status"] == "done" and W.get(wid)["checks"] == 1
    kinds = {k for _c, k, _p in wx["events"]}
    assert "step" not in kinds and "research_run" not in kinds and "research_watch" not in kinds         # baseline: nothing in her chat at all
    pages["value"] = "430.0"
    with session() as s:
        s.get(W.ResearchWatch, wid).next_run_at = now() - timedelta(minutes=1)
    assert run_(W.tick()) == 1
    rid2 = W.get(wid)["last_run_id"]
    assert rid2 != rid
    run_(runner.run_background(rid2))
    ev = [p for _c, k, p in wx["events"] if k == "research_watch"]
    assert len(ev) == 1 and ev[0]["status"] == "done" and W.get(wid)["changes"] == 1
    assert "research_run" not in {k for _c, k, _p in wx["events"]}                                          # the full-report wake did NOT fire


def test_the_result_tool_hands_over_the_digest_and_remembers_the_dossier_to_check_against(pages, wx):
    wid = W.add("t1", "c1", "What is the Corvane Index?", ["value?"], 7)["id"]
    for text in (None, "430.0"):
        if text:
            pages["value"] = text
            with session() as s:
                s.get(W.ResearchWatch, wid).next_run_at = now() - timedelta(minutes=1)
        run_(W.tick())
        run_(runner.run_background(W.get(wid)["last_run_id"]))
    rid = W.get(wid)["last_run_id"]
    out = tool(action="result", run_id=rid)
    assert out["changed"] == 1 and "CHANGED (1)" in out["digest"] and "was 412.5" in out["digest"] and "now 430.0" in out["digest"] and "SHORT message" in out["say"]
    kept = E.recall("c1")
    assert kept is not None and any(f["id"].startswith("prior-c") for f in kept["fields"])
    from app.agent.tools import ToolError
    with pytest.raises(ToolError, match="No change digest found"):
        tool(action="result", run_id="rr_nope")
    with pytest.raises(ToolError):
        tool(action="result", run_id=rid, tenant="t2")


def test_check_now_runs_one_check_and_respects_the_ceiling(pages, wx):
    from app.agent.tools import ToolError
    wid = W.add("t1", "c1", "Q?", ["value?"], 30, baseline={"fields": []})["id"]
    out = tool(action="check_now", id=wid)
    assert out["started"] is True and W.get(wid)["last_run_id"] == out["run_id"]
    wx["st"].research_daily_inr = 0.0
    with pytest.raises(ToolError, match="budget is used up"):
        tool(action="check_now", id=wid)


# ---------------------------------------------------------------- the wake path
def test_the_wake_text_for_a_change_asks_for_a_short_message_and_is_a_held_checked_turn(env):
    from app import kaam_followup as KF
    from app import kaamwatch
    r = KF.KaamFollowup(tenant_id="t", conversation_id="c", key="research_watch:rr_abc", kind="research_watch", label="Research watch", title="watch 1234 · Corvane",
                        state="done", detail="1 badlaav mile - watch rw_1")
    txt = KF._wake_text(r)
    assert runner.is_report_due(txt) and runner.is_change_due(txt) and 'run="rr_abc"' in txt and "research_watch tool" in txt and "run_id=rr_abc" in txt and "SHORT message" in txt and "not seen this time" in txt
    r.state = "stopped"
    assert not runner.is_report_due(KF._wake_text(r))                                           # a paused watch gets the ordinary news line
    j = kaamwatch.shape("research_watch", {"id": "rr_abc", "number": "watch 1234", "name": "Corvane", "status": "done", "say": "x", "watch": "rw_1"})
    assert j["state"] == "done" and j["label"] == "Research watch" and j["kind"] == "research_watch"
    from app.agent import admit
    names = {t["name"] for t in admit.plan_for("[Santosh worker update] <research_change_due> research_watch tool run_id=rr_abc", get_settings()).specs()}
    assert {"research_watch", "research_status"} <= names


def test_the_wake_turn_that_writes_the_change_is_checked_with_the_earlier_value_admitted(pages, wx, monkeypatch):
    """run_turn(actor='wake'): the brain fetches the digest, drafts a message with a made-up number, the check sends it back once, the corrected one goes out."""
    from tests.test_v0186_long_goal import FakeBrain, _set_brain, txt
    import app.agent.santosh as S
    from app import chats, kaam_followup as KF
    monkeypatch.setattr(chats, "enabled", lambda: False)
    from app.db import Conversation
    with session() as s:
        c = Conversation(tenant_id="default")
        s.add(c)
        s.flush()
        conv = c.id
    wid = W.add("default", conv, "What is the Corvane Index?", ["value?"], 7)["id"]
    for text in (None, "430.0"):
        if text:
            pages["value"] = text
            with session() as s:
                s.get(W.ResearchWatch, wid).next_run_at = now() - timedelta(minutes=1)
        run_(W.tick())
        run_(runner.run_background(W.get(wid)["last_run_id"]))
    rid = W.get(wid)["last_run_id"]
    good = ("The Corvane Index moved: it was 412.5 earlier and is now 430.0 [1].\n\nWhat I could not confirm: whether the earlier reading was revised later.\n")
    bad = good.replace("430.0", "999.9")
    st = get_settings()
    st.hard_check, st.research_review = True, False
    try:
        brain = _set_brain(monkeypatch, FakeBrain([([tu(1, "research_watch", action="result", run_id=rid)], "tool_use"), ([txt(bad)], "end_turn"), ([txt(good)], "end_turn")]))
        r = KF.KaamFollowup(tenant_id="default", conversation_id=conv, key=f"research_watch:{rid}", kind="research_watch", label="Research watch", title="watch", state="done",
                            detail="1 badlaav mile")
        out = asyncio.run(S.run_turn(conv, KF._wake_text(r), tenant_id="default", actor="wake", save_user=False))
        notes = [m["content"][0]["text"] for k in brain.seen for m in k["messages"][-1:] if isinstance(m["content"], list) and m["content"]
                 and isinstance(m["content"][0], dict) and str(m["content"][0].get("text", "")).startswith("[System: JAANCH")]
        assert any("999.9" in n for n in notes)
        assert not any("cites no sources" in n for n in notes)                                    # a change message cites [n]; the link-list rule is for full reports
        assert "430.0" in out and "412.5" in out and "999.9" not in out                         # the earlier value was admitted by the check, the made-up one was not
    finally:
        st.hard_check, st.research_review = False, True


# ---------------------------------------------------------------- the held review
class FakeClient:
    def __init__(self, text="", boom=False):
        self.text, self.boom, self.calls = text, boom, []
        self.messages = self

    async def create(self, **kw):
        self.calls.append(kw)
        if self.boom:
            raise RuntimeError("model down")
        return SimpleNamespace(content=[{"type": "text", "text": self.text}], stop_reason="end_turn")


def _fields_dossier():
    d = _dossier()
    d["tasks"][0]["unresolved"] = "the 2019 baseline; the revision history"
    return d


def test_the_reviewer_sees_the_notes_the_pages_words_and_the_gaps(env):
    txt = RV.digest(_fields_dossier())
    assert "NOTES:" in txt and "(high)" in txt and "page's words:" in txt and "The Corvane Index stood at 412.5" in txt
    assert "NOT CONFIRMED by the research:" in txt and "the 2019 baseline" in txt and "the revision history" in txt and "CALCULATIONS" in txt
    flagged = _fields_dossier()
    flagged["fields"][0]["verified"] = False
    assert "[NOT VERIFIED" in RV.digest(flagged)
    assert len(RV.digest({"question": "q", "fields": [{"n": 1, "confidence": "high", "claim": "x" * 300, "excerpt": "y" * 300, "verified": True, "supported": True}] * 200, "tasks": []}, 3000)) <= 3010


def test_the_reviewer_names_up_to_four_problems_and_a_failure_never_blocks(env, monkeypatch):
    import app.agent.santosh as S
    st = get_settings()
    probs = json.dumps({"ok": False, "problems": [f"\"sentence {i}\" overstates the note" for i in range(6)]})
    fc = FakeClient(probs)
    monkeypatch.setattr(S, "get_client", lambda: fc)
    got = run_(RV.review_report("Q?", "The market always grows.", _fields_dossier(), st))
    assert len(got) == 4 and "overstates" in got[0]
    sent = fc.calls[0]
    assert "page's words" in sent["messages"][0]["content"] and "The market always grows." in sent["messages"][0]["content"] and "REVIEWER" in sent["system"]
    monkeypatch.setattr(S, "get_client", lambda: FakeClient('{"ok": true, "problems": []}'))
    assert run_(RV.review_report("Q?", "fine", _fields_dossier(), st)) == []
    monkeypatch.setattr(S, "get_client", lambda: FakeClient(boom=True))
    assert run_(RV.review_report("Q?", "fine", _fields_dossier(), st)) == [] and RV.STATS["failed"] >= 1
    monkeypatch.setattr(S, "get_client", lambda: FakeClient("not json at all"))
    assert run_(RV.review_report("Q?", "fine", _fields_dossier(), st)) == []
    st.research_review = False
    try:
        monkeypatch.setattr(S, "get_client", lambda: FakeClient(probs))
        assert run_(RV.review_report("Q?", "x", _fields_dossier(), st)) == []                     # switched off
    finally:
        st.research_review = True
    assert run_(RV.review_report("Q?", "x", {"fields": []}, st)) == []                           # nothing to review against


def test_the_reviewer_runs_after_the_code_checks_and_replaces_the_generic_one(env, monkeypatch):
    import app.agent.santosh as S
    from app.agent import hard
    st = get_settings()
    d = _fields_dossier()
    E.remember("rv1", d)
    history = [{"role": "user", "content": "Do deep research on the Corvane Index"},
               {"role": "assistant", "content": [tu("a", "research_status", action="result")]},
               {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "a", "content": "https://index.example.gov.in/corvane/2025"}]}]
    state = {"request": "Do deep research on the Corvane Index", "hard_why": {"why": ["research"]}}
    honest = ("The Corvane Index was 412.5 in March 2025 [1].\n\nWhat I could not confirm: the 2019 baseline and the revision history.\n\nSources:\n[1] Test Authority, 2025 - "
              "https://index.example.gov.in/corvane/2025\n")
    generic = {"n": 0}

    async def generic_review(*a, **k):
        generic["n"] += 1
        return ["GENERIC"]
    monkeypatch.setattr(hard, "review", generic_review)
    monkeypatch.setattr(S, "get_client", lambda: FakeClient(json.dumps({"ok": False, "problems": ["\"market leader\" is one company's own claim"]})))
    bad = asyncio.run(S._hard_check("rv1", dict(state), honest, history, st))
    assert bad == ["\"market leader\" is one company's own claim"] and generic["n"] == 0            # the research reviewer spoke; the generic one was not asked
    monkeypatch.setattr(S, "get_client", lambda: FakeClient('{"ok": true, "problems": []}'))
    assert asyncio.run(S._hard_check("rv1", dict(state), honest, history, st)) == [] and generic["n"] == 0
    figure = asyncio.run(S._hard_check("rv1", dict(state), honest.replace("412.5", "999.9"), history, st))
    assert figure and "999.9" in figure[0]                                                           # the code check still comes FIRST (and the model is not asked)
    st.research_review = False
    try:
        assert asyncio.run(S._hard_check("rv1", dict(state), honest, history, st)) == ["GENERIC"] and generic["n"] == 1     # off: the generic reviewer, as before
    finally:
        st.research_review = True


# ---------------------------------------------------------------- the route, the worker slot, the defaults
def test_the_route_lists_her_watches_and_the_worker_slot_ticks_them(wx, monkeypatch):
    from app.research.api import make_router
    wid = W.add("default", "c1", "Q?", ["g"], 7)["id"]
    a = FastAPI()
    a.include_router(make_router(lambda: None, lambda: "default"))
    r = TestClient(a).get("/api/research/watches").json()["watches"]
    assert r[0]["id"] == wid and r[0]["every_days"] == 7 and r[0]["month_cap_inr"] == 300.0 and "spent_this_month_inr" in r[0]
    called = []

    async def fake_tick():
        called.append(1)
        return 0
    monkeypatch.setattr(W, "tick", fake_tick)
    import app.worker as WK
    WK._rs_last = 0.0
    run_(WK.research_jobs())
    assert called == [1]
    from app.config import Settings
    s = Settings()
    assert (s.research_review, s.research_watch_month_inr) == (True, 300.0) and (W.MAX_ACTIVE, W.MIN_DAYS, W.FAIL_PAUSE) == (3, 1, 3)
