"""Wave 10 LAMBA KAAM of the third deep audit (owner: "GO WAVE 10" - a long task finished properly, end to end).

10 a cleared old tool result keeps its head, links / ids and figures (never a bare "run it again")
11 a crew's deliverables keep their share (inline: 24k result limit; background: 24k stored, whole by id)
12 "haan aage badho" moves the minutes budget, never the job's start (the done-check's "made in this job")
13 a `tool:` check sees every round of the job, not only this one
14 her answer to a job that stopped to ask her puts the same job back to work
15 the "waiting on her" check is not blind past 40 events, and ignores an older goal's card
16 a round already queued is not queued again; the queued round reads the step list when it runs
17 a page / row check with no file named reads the newest file of the right kind
18 a job paused past resume_hours stops taking over the chat
19 a research run / Dhara run / crawl that gives up says so
"""
from __future__ import annotations

import asyncio
import inspect
import json
from datetime import datetime, timedelta, timezone

from app.db import Conversation, session

T = "default"


def _chat(cid: str) -> str:
    with session() as s:
        s.add(Conversation(id=cid, tenant_id=T))
    return cid


# ---------------------------------------------------------------- 10 cleared results keep the facts
def test_a_cleared_result_keeps_links_ids_and_figures(monkeypatch):
    from app.agent import prune
    page = ("Supplier A quotation " + "x" * 3000 + " price Rs 12,400 per ton https://supplier-a.in/q/77 "
            + "y" * 9000 + " Supplier B ₹ 13,900 GST 18%")
    hist = [{"role": "user", "content": "5 suppliers dhundo"}]
    for i in range(8):
        hist.append({"role": "assistant", "content": [{"type": "tool_use", "id": f"t{i}", "name": "open_website", "input": {}}]})
        hist.append({"role": "user", "content": [{"type": "tool_result", "tool_use_id": f"t{i}", "content": page}]})
    out = prune.clear_old(hist)
    cleared = [b["content"] for m in out if m["role"] == "user" and isinstance(m["content"], list)
               for b in m["content"] if str(b.get("content", "")).startswith("[Purana tool natija")]
    assert cleared, "nothing was cleared"
    c = cleared[0]
    assert "https://supplier-a.in/q/77" in c and "13,900" in c and "Supplier A quotation" in c and len(c) < 2600


# ---------------------------------------------------------------- 11 crews
def test_crew_results_keep_their_share():
    from app.agent import santosh, team
    assert santosh.RESULT_LIMIT["deploy_agents"] >= 24000 and santosh.RESULT_LIMIT["agent_status"] >= 24000
    five = [{"name": f"a{i}", "ok": True, "deliverable": f"Supplier {i}: " + "price table " * 300} for i in range(5)]
    d = team._digest(five, per=max(600, 24000 // 5))
    assert all(f"Supplier {i}:" in d for i in range(5)) and len(d) > 5 * 1500
    src = inspect.getsource(team.agent_status)
    assert 'str(r.result or "")[:24000] if id' in src


# ---------------------------------------------------------------- 12 + 14 + 18 goal state
def test_extending_a_job_keeps_its_start(env):
    from app.agent import goal
    from app.agent.goal import GoalRun
    _chat("g12")
    v = goal.set_goal(T, "g12", "kaam", ["a", "b"], origin="owner")
    old = datetime.now(timezone.utc) - timedelta(hours=2)
    with session() as s:
        r = s.get(GoalRun, v["id"])
        r.started_at, r.status, r.hold = old, "blocked", goal.LIMIT
    goal.reopen(T, "g12")
    with session() as s:
        r = s.get(GoalRun, v["id"])
        assert abs((goal._aware(r.started_at) - old).total_seconds()) < 2 and r.budget_at is not None
        assert goal._working_minutes(r) < 1


def test_her_answer_resumes_a_job_that_asked_her(env):
    from app.agent import goal
    from app.agent.goal import GoalRun
    _chat("g14")
    v = goal.set_goal(T, "g14", "GST bill banao", ["a", "b", "c"], origin="owner")
    goal.finish(T, v["id"], "blocked_on_her", reason="GST number chahiye")
    assert goal.active_for("g14") is None
    goal.resume_on_answer(T, "g14", "27ABCDE1234F1Z5")
    a = goal.active_for("g14")
    assert a is not None and a["id"] == v["id"]
    with session() as s:
        assert "27ABCDE1234F1Z5" in s.get(GoalRun, v["id"]).reason


def test_a_job_on_a_limit_hold_is_not_resumed_by_any_words(env):
    from app.agent import goal
    from app.agent.goal import GoalRun
    _chat("g14b")
    v = goal.set_goal(T, "g14b", "kaam", ["a", "b"], origin="owner")
    with session() as s:
        r = s.get(GoalRun, v["id"])
        r.status, r.hold = "blocked", goal.LIMIT
    assert goal.resume_on_answer(T, "g14b", "kal ka mausam?") is None


def test_a_long_paused_job_is_put_to_rest(env):
    from app.agent import goal
    from app.agent.goal import GoalRun
    _chat("g18")
    v = goal.set_goal(T, "g18", "kaam", ["a", "b"], origin="owner")
    old = datetime.now(timezone.utc) - timedelta(days=3)
    with session() as s:
        r = s.get(GoalRun, v["id"])
        r.paused_at, r.updated_at = old, old
    assert goal.active_for("g18") is None
    with session() as s:
        assert s.get(GoalRun, v["id"]).status == "blocked"


# ---------------------------------------------------------------- 13 tool checks across rounds
def test_a_tool_check_sees_earlier_rounds(env):
    from app.agent import verify
    from app.agent.eventlog import HarnessEvent, ensure_table
    _chat("v13")
    ensure_table()
    with session() as s:
        s.add(HarnessEvent(tenant_id=T, conversation_id="v13", kind="tool_result",
                           payload=json.dumps({"tool": "email_send", "ok": True})))
    step = [{"n": 6, "text": "mail best 2", "state": "done", "check": "tool:email_send"}]
    since = datetime.now(timezone.utc) - timedelta(hours=1)
    assert verify.gate(T, "v13", [], step, calls=[], since=since)["ok"]            # sent in an earlier round
    assert not verify.gate(T, "v13", [], [{**step[0], "check": "tool:whatsapp_send"}], calls=[], since=since)["ok"]


# ---------------------------------------------------------------- 15 waiting on her
def test_an_old_card_is_still_seen_past_many_steps(env):
    from app.agent import goal
    from app.db import Event
    _chat("w15")
    goal.set_goal(T, "w15", "kaam", ["a", "b"], origin="owner")
    with session() as s:
        s.add(Event(conversation_id="w15", kind="approval", payload={"status": "pending", "id": "ap1", "title": "Bhejun?"}))
        for i in range(80):
            s.add(Event(conversation_id="w15", kind="step", payload={"tool": "x", "state": "done", "id": f"s{i}"}))
    assert goal._waiting_on_her("w15")


# ---------------------------------------------------------------- 16 one queued round
def test_a_queued_round_is_not_queued_twice(env, monkeypatch):
    from app.agent import goal
    _chat("q16")
    v = goal.set_goal(T, "q16", "kaam", ["a", "b"], origin="owner")
    goal._PENDING[v["id"]] = 1
    try:
        from app.agent import santosh
        spawned = []
        monkeypatch.setattr(santosh, "_bg", lambda c: spawned.append(c) or c.close())
        assert goal._schedule("q16", T, goal.active_for("q16"), count_round=True) is True
        assert spawned == []
    finally:
        goal._PENDING.pop(v["id"], None)
    src = inspect.getsource(goal._continuation)
    assert "left0 = steps_left(v0)" in src


# ---------------------------------------------------------------- 17 the right file kind
def test_a_page_check_reads_a_pdf_not_the_newer_sheet(env, monkeypatch, tmp_path):
    from app.agent import verify
    picked = []
    monkeypatch.setattr(verify, "_delivered", lambda t: [("report.pdf", str(tmp_path / "r.pdf")), ("data.xlsx", str(tmp_path / "d.xlsx"))])
    import app.quality.longcard as lc
    monkeypatch.setattr(lc, "read_file", lambda path, kind: picked.append(kind) or {"ok": True, "pages": 6, "rows": 0})
    f, info = verify._file_info(T, "", "file_pages")
    assert f["name"] == "report.pdf" and picked == ["pdf"]


# ---------------------------------------------------------------- 19 giving up is told
def test_giving_up_is_told():
    from app.research import store
    from app.agent import dhara_tools, crawl_jobs
    assert "_publish(conv, rid, q, \"failed\"" in inspect.getsource(store)
    assert inspect.getsource(dhara_tools).count("_runs_tell(") >= 4
    assert "events.notify(conv" in inspect.getsource(crawl_jobs.claim)
