"""v0.665 SACH KA HISAAB (owner: "GO WAVE 5" of the second deep audit - Hoola never says something false).

1  a tool result like {"ok": False} / status failed is a failure, not a success
2  a true report of work done earlier ("haan, bhej diya tha") is not called a lie
3  a claim is backed only by a tool of ITS kind (a reminder does not back "mail bhej diya")
4  the quick lane never says done and never swallows a request for work
5  a call's "mail bhej diya" after a failed / read-only tool is corrected
6  one-clause excuses no longer hide a claim; "PDF bana diya" is a claim
7  a call job that only talked is not relayed as "ho gaya"
8  the server's own plan is not closed as done on a failure or a question
9  the step cap always says the job is not finished, and the outcome is not done
10 "Kaam ho gaya" is never made up when every tool failed
11 a goal round does not overwrite a stuck job's outcome with "continuing"
12 "done = verified" counts only what this job made
13 a correct figure from deep inside a tool result is not flagged
14 a fact Hoola guessed is labelled and dated, never shown as her instruction
"""
from __future__ import annotations

import asyncio
import inspect
import json
import types
from datetime import datetime, timedelta, timezone

import pytest

from app.db import Conversation, session

T = "default"


def _chat(cid: str) -> str:
    with session() as s:
        s.add(Conversation(id=cid, tenant_id=T))
    return cid


# ---------------------------------------------------------------- 1 {"ok": False} is a failure
def test_ok_false_and_failed_status_are_failures():
    from app.agent.santosh import tool_failure
    assert tool_failure({"ok": False, "stage": "check", "errors": ["no timeline"]})
    assert tool_failure({"status": "refused", "reason": "cap"}) == "cap"
    assert tool_failure({"error": "boom"}) == "boom"
    assert tool_failure({"ok": True, "id": 1}) == ""
    assert tool_failure({"status": "working"}) == ""
    assert tool_failure("plain text") == ""
    src = inspect.getsource(__import__("app.agent.santosh", fromlist=["x"])._steps_inner)
    assert "tool_failure(out)" in src


# ---------------------------------------------------------------- 2 a true past report
def _logged(conv, tool, ok=True, days_ago=0):
    from app.agent.eventlog import HarnessEvent, ensure_table
    ensure_table()
    with session() as s:
        s.add(HarnessEvent(conversation_id=conv, kind="tool_result", tenant_id=T,
                           payload=json.dumps({"tool": tool, "ok": ok}),
                           created_at=datetime.now(timezone.utc) - timedelta(days=days_ago)))


def test_a_true_report_of_earlier_work_is_not_called_false(env):
    from app.agent import draftcheck as d
    _chat("p1")
    _logged("p1", "email_send")
    st = {"calls": [], "request": "Rahul ko mail gaya kya?"}
    assert d.fake_done(st, "Haan, Rahul ko mail bhej diya tha.", "p1") == ""
    wake = {"calls": [], "request": "[kaam ho gaya]", "actor": "wake"}
    assert d.fake_done(wake, "Rahul ko mail bhej di gayi hai.", "p1") == ""


def test_a_past_claim_with_nothing_behind_it_is_still_caught(env):
    from app.agent import draftcheck as d
    _chat("p2")
    _logged("p2", "create_reminder")             # something else ran, never a mail
    _logged("p2", "email_send", days_ago=20)      # a mail long ago does not count
    st = {"calls": [], "request": "Rahul ko mail gaya kya?"}
    assert d.fake_done(st, "Haan, Rahul ko mail bhej diya tha.", "p2") == d.NUDGE


# ---------------------------------------------------------------- 3 a claim needs a tool of its kind
def test_a_reminder_does_not_back_a_mail_claim():
    from app.agent import draftcheck as d
    st = {"calls": [{"tool": "create_reminder", "ok": True, "result": "{'id': 'r1'}"}], "request": "mail bhejo aur yaad dilana"}
    out = d.fake_done(st, "Mail bhej diya aur reminder laga diya.")
    assert out.startswith("[System check") and "bhej diya" in out and out != d.NUDGE
    ok = {"calls": [{"tool": "email_send", "ok": True, "result": "{'id': 'm1'}"},
                    {"tool": "create_reminder", "ok": True, "result": "{'id': 'r1'}"}]}
    assert d.fake_done(ok, "Mail bhej diya aur reminder laga diya.") == ""
    crew = {"calls": [{"tool": "delegate_task", "ok": True, "result": "{'done': True}"}]}
    assert d.fake_done(crew, "Mail bhej diya.") == ""


# ---------------------------------------------------------------- 4 the quick lane
def _quick(monkeypatch, reply):
    from app.agent import quick

    async def fake(system, prompt):
        return reply
    monkeypatch.setattr(quick, "_ask", fake)
    return quick


def test_quick_lane_never_claims_done_or_swallows_work(env, monkeypatch):
    _chat("q1")
    quick = _quick(monkeypatch, "Theek hai, Sharma ji ko invoice bhej diya.")
    got = asyncio.run(quick.answer("q1", T, "Sharma ji ko invoice bhej do"))
    assert got["queued"] and "bhej diya" not in got["text"]
    quick = _quick(monkeypatch, "Haan, abhi 3 mein se 2 step ho gaye hain.")
    got = asyncio.run(quick.answer("q1", T, "kitna hua?"))
    assert got["queued"] is False                                   # a plain question is still answered at once
    quick = _quick(monkeypatch, "Ji, zaroor.")
    got = asyncio.run(quick.answer("q1", T, "Sharma ji ko invoice bhej do"))
    assert got["queued"]                                            # work goes to the job, even with an innocent reply


# ---------------------------------------------------------------- 5 the call's spoken claim
def _call():
    from app.voice import Call
    c = Call.__new__(Call)
    c.did, c._did_mark, c.stats, c._news_sent_at, c._started_at = [], 0, {}, -1e9, -1e9
    c.call_id = "c"
    said = []
    c.push_news = lambda t: said.append(t)
    return c, said


@pytest.mark.parametrize("did", [[{"tool": "email_send", "ok": False, "n": 1}],
                                 [{"tool": "email_check", "ok": True, "n": 1}],
                                 [{"tool": "create_reminder", "ok": True, "n": 1}]])
def test_a_call_claim_after_a_failed_or_unrelated_tool_is_corrected(did):
    c, said = _call()
    c.did = did
    c._check_spoken_claim("Haan, mail bhej diya.")
    assert said and "Sudhaar" in said[0]


def test_a_call_claim_after_the_real_tool_stands():
    c, said = _call()
    c.did = [{"tool": "email_send", "ok": True, "n": 1}]
    c._check_spoken_claim("Haan, mail bhej diya.")
    assert said == []


def test_voice_tool_with_ok_false_is_an_error():
    from app import voice
    assert voice._fails({"ok": False, "stage": "check"}) and not voice._fails({"ok": True})


# ---------------------------------------------------------------- 6 claims in one clause
@pytest.mark.parametrize("text", ["Maine aapka order place kar diya hai jo kal tak aa jayega",
                                  "I have sent the invoice to Sharma ji and you can track it here",
                                  "Invoice PDF bana diya hai.", "Aapne jo list di thi un sabko mail bhej diya",
                                  "Website ban gayi hai", "Aapki report taiyaar ho gayi hai"])
def test_claims_the_excuses_used_to_hide(text):
    from app.agent import draftcheck as d
    assert d.claims_done(text), text


@pytest.mark.parametrize("text", ["Aapne mail bhej diya tha", "I haven't sent anything", "Order place ho jayega.",
                                  "Card par tap karte hi bhej diya jayega", "Main aapke liye ek plan bana diya hai",
                                  "I will send it once you approve", "Aap haan kahein to reminder set ho jayega."])
def test_honest_sentences_stay_honest(text):
    from app.agent import draftcheck as d
    assert d.claims_done(text) == "", text


# ---------------------------------------------------------------- 7 a call job that only talked
def test_a_talk_outcome_is_not_relayed_as_done():
    from app import voice
    src = inspect.getsource(voice.Call._late_result)
    assert 'if outcome == "done":' in src and 'outcome in ("done", "talk")' not in src


# ---------------------------------------------------------------- 8 the server's plan
def _plan(conv, steps):
    from app.agent import goal
    v = goal.set_goal(T, conv, "kaam", steps, origin="owner")
    goal.mark_step(T, v["id"], 1, "current", conv=conv)
    return goal.show(T, v["id"]) if hasattr(goal, "show") else v


@pytest.mark.parametrize("text,calls,status", [
    ("Kaunsi date chahiye?", [], "blocked"),
    ("Step 2 fail ho gaya, API key nahi hai.", [{"tool": "x", "ok": False}], "failed"),
    ("Teeno kaam ho gaye. Aur kuch karna hai?", [{"tool": "x", "ok": True}], "done"),
])
def test_the_auto_plan_closes_with_the_truth(env, text, calls, status):
    from app.agent import goal, santosh
    from app.agent.goal import GoalRun
    _chat("a1")
    v = goal.set_goal(T, "a1", "kaam", ["a", "b", "c"], origin="owner")
    santosh._close_auto_plan(T, "a1", goal.active_for("a1"), text, calls)
    with session() as s:
        r = s.get(GoalRun, v["id"])
        assert r.status == status, (r.status, text)
        done = sum(1 for x in json.loads(r.steps) if x.get("state") == "done")
    assert (done == 3) == (status == "done")


# ---------------------------------------------------------------- 9 + 10 honest endings
def test_step_cap_and_empty_endings_are_honest():
    from app.agent import santosh
    src = inspect.getsource(santosh._steps_inner)
    assert "Yeh kaam lamba ho gaya aur abhi poora nahi hua" in src and 'state["left"] = state.get("left") or "steps ki had' in src
    assert "yeh kaam nahi ho paya" in src and "len(_bad) == len(_cs)" in src


# ---------------------------------------------------------------- 11 a goal round's outcome
def test_a_goal_round_keeps_a_stuck_outcome(env, monkeypatch):
    from app.agent import goal, santosh
    _chat("g1")
    v = goal.set_goal(T, "g1", "kaam", ["a", "b"], origin="owner")

    async def turn(conv, ask, tenant_id=None, actor=None):
        santosh.LAST_OUTCOME[conv] = {"outcome": "stuck", "left": "atka", "at": 1}
        return "atka"
    monkeypatch.setattr(santosh, "run_turn", turn)
    _real = asyncio.sleep
    monkeypatch.setattr(goal.asyncio, "sleep", lambda s: _real(0))
    asyncio.run(goal._continuation("g1", T, "aage", v["id"]))
    assert santosh.LAST_OUTCOME["g1"]["outcome"] == "stuck"


# ---------------------------------------------------------------- 12 verify counts only this job's rows
def test_verify_counts_only_what_this_job_made(env):
    from app.agent import verify
    from app.db import Reminder
    _chat("v1")
    old = datetime.now(timezone.utc) - timedelta(days=30)
    with session() as s:
        for i in range(3):
            s.add(Reminder(tenant_id=T, conversation_id="v1", text=f"r{i}", due_at=old + timedelta(days=60), created_at=old))
    step = [{"n": 1, "text": "3 reminder", "state": "done", "check": "reminder>=3"}]
    assert verify.gate(T, "v1", [], step)["ok"]                                    # no start known: old behaviour
    assert not verify.gate(T, "v1", [], step, since=datetime.now(timezone.utc) - timedelta(minutes=5))["ok"]


# ---------------------------------------------------------------- 13 figures deep in a result
def test_a_figure_from_row_ten_is_backed():
    from app.agent import draftcheck as d
    from app.agent.santosh import _facts_of
    rows = json.dumps([{"name": f"party {i}", "due": 1000 + i} for i in range(9)] + [{"name": "Sharma ji", "due": 12400}])
    big = ("x" * 400) + rows
    call = {"tool": "invoice_list", "ok": True, "result": big[:300], "digits": _facts_of(big)}
    src = d.sources_text("kiska kitna baaki?", [call])
    assert d.loose_facts("Sharma ji ka Rs 12,400 baaki hai.", src) == []


# ---------------------------------------------------------------- 14 guessed facts labelled
def test_guessed_facts_are_labelled_and_dated(env):
    from app import life, yaad
    from app.db import MemoryFact
    with session() as s:
        s.add(MemoryFact(tenant_id=T, text="Budget Rs 50k hai", source="auto"))
        s.add(MemoryFact(tenant_id=T, text="Riya meri beti hai", source=None))
        s.flush()
        ids = [f.id for f in s.query(MemoryFact).all()]
    blk = life.context_block(T)
    asked = blk.split("Things YOU picked up")[0]
    assert "Riya meri beti hai (saved" in asked and "Budget Rs 50k" not in asked
    assert "Budget Rs 50k hai (noted" in blk.split("Things YOU picked up")[1]
    marks = yaad.fact_marks(ids)
    assert any("Hoola ne samjha" in m for m in marks.values()) and any("(saved" in m for m in marks.values())
