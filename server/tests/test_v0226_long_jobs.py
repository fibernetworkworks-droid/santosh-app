"""v0.223 PHASE A - long jobs like Claude: restart-proof, steerable, and they ASK instead of failing.

(1) A server restart used to leave a background long job half-done for ever (only paused jobs were restarted).
(2) A message she sent mid-job waited until the whole turn ended (up to 45 min); the job kept the old plan.
(3) When the rounds / minutes budget ran out the job was marked 'failed'; she had to ask for it all over again.
"""
import asyncio
from datetime import timedelta

from tests.test_bazar import bz  # noqa: F401
from tests.test_v0186_long_goal import FakeBrain, _set_brain, gz, tu, txt  # noqa: F401


def _age(gid, minutes):
    from app.agent import goal
    from app.db import now, session
    with session() as s:
        r = s.get(goal.GoalRun, gid)
        r.updated_at = now() - timedelta(minutes=minutes)


def _row(gid):
    from app.agent import goal
    from app.db import session
    with session() as s:
        r = s.get(goal.GoalRun, gid)
        return {"status": r.status, "hold": r.hold, "recovered": r.recovered, "rounds": r.rounds,
                "paused_at": r.paused_at}


def _capture(monkeypatch):
    from app.agent import goal, santosh
    seen = []

    def bg(coro):
        seen.append(coro.cr_frame.f_locals.get("actor"))
        coro.close()
    monkeypatch.setattr(santosh, "_bg", bg)
    monkeypatch.setattr(goal, "_waiting_on_her", lambda c: False)
    goal._PENDING.clear()
    return seen


# ---------------------------------------------------------------- (1) restart-proof
def test_restart_picks_up_a_half_done_job(gz, monkeypatch):  # noqa: F811
    from app.agent import goal
    from app.db import Message, session
    from sqlalchemy import select
    conv = gz["conv"]
    seen = _capture(monkeypatch)
    v = goal.set_goal("default", conv, "Website banana", ["design", "build", "launch"], origin="owner")
    goal.mark_step("default", v["id"], 1, "done")
    assert goal.recover_tick() == 0 and not seen                 # still moving: nothing to recover
    _age(v["id"], 15)
    assert goal.recover_tick() == 1 and seen == ["goal"]         # her own job, picked up with her authority
    assert _row(v["id"])["recovered"] == 1 and _row(v["id"])["rounds"] == 1   # a recovery never uses a round
    with session() as s:
        lines = [m.display for m in s.scalars(select(Message).where(Message.conversation_id == conv)).all()]
    assert any("Server dobara chalu hua" in (x or "") and "1/3" in (x or "") for x in lines)
    _age(v["id"], 15)
    assert goal.recover_tick() == 0                              # its round is pending in this process: never doubled


def test_recovery_respects_lock_her_card_stop_and_a_cap(gz, monkeypatch):  # noqa: F811
    from app.agent import goal, santosh
    conv = gz["conv"]
    seen = _capture(monkeypatch)
    v = goal.set_goal("default", conv, "Report", ["a", "b"], origin="owner")
    _age(v["id"], 15)

    async def held():
        async with santosh._locks[conv]:
            return goal.recover_tick()
    assert asyncio.run(held()) == 0 and not seen                 # a turn is running it right now
    monkeypatch.setattr(goal, "_waiting_on_her", lambda c: True)
    assert goal.recover_tick() == 0 and _row(v["id"])["paused_at"] is not None   # her card waits: paused instead
    monkeypatch.setattr(goal, "_waiting_on_her", lambda c: False)
    # restarted too many times: stop and ASK her instead of looping
    v2 = goal.set_goal("default", conv, "Report 2", ["a", "b"], origin="owner")
    with goal.session() as s:
        s.get(goal.GoalRun, v2["id"]).recovered = 3
    _age(v2["id"], 15)
    assert goal.recover_tick() == 0 and _row(v2["id"])["hold"] == "limit"
    # Rokiye: never resurrected
    v3 = goal.set_goal("default", conv, "Report 3", ["a"], origin="owner")
    goal.mark_stopped(conv)
    _age(v3["id"], 15)
    assert goal.recover_tick() == 0 and not seen


# ---------------------------------------------------------------- (3) limits ask, her yes carries on
def test_used_up_budget_asks_and_her_yes_reopens_with_a_fresh_budget(gz, monkeypatch):  # noqa: F811
    from app.agent import goal
    from app.config import get_settings
    conv = gz["conv"]
    seen = _capture(monkeypatch)
    v = goal.set_goal("default", conv, "Bada kaam", ["a", "b", "c"], origin="owner")
    goal.mark_step("default", v["id"], 1, "done")
    with goal.session() as s:
        s.get(goal.GoalRun, v["id"]).rounds = get_settings().agent_goal_rounds
    assert goal.maybe_continue(conv, "default", "owner") is False
    r = _row(v["id"])
    assert r["status"] == "blocked" and r["hold"] == "limit"
    assert goal.active_for(conv) is None and goal.held_for_limit(conv)["id"] == v["id"]
    assert "1/3" in goal.show("default", v["id"])["reason"]
    # only a real "carry on" reopens it
    assert goal.wants_continue("haan aage badho") and goal.wants_continue("continue") and goal.wants_continue("haan")
    assert not goal.wants_continue("aaj mausam kaisa hai?")
    # her yes in chat: the same job works again, done steps kept, fresh budget
    _set_brain(monkeypatch, FakeBrain([([txt("Theek hai, aage badh raha hoon.")], "end_turn")]))
    from app.agent.santosh import run_turn
    asyncio.run(run_turn(conv, "haan aage badho", tenant_id="default"))
    r = _row(v["id"])
    assert r["status"] == "working" and r["hold"] is None and r["rounds"] >= 1
    assert goal.show("default", v["id"])["done"] == 1


def test_continue_button_api(gz, monkeypatch):  # noqa: F811
    from fastapi.testclient import TestClient
    from app.agent import goal
    from app.config import get_settings
    from app.main import app
    conv = gz["conv"]
    seen = _capture(monkeypatch)
    with TestClient(app) as c:
        k = get_settings().api_key
        h = {"Authorization": f"Bearer {k}"} if k else {}
        assert c.post(f"/api/conversations/{conv}/goal/continue", headers=h).status_code == 409
        v = goal.set_goal("default", conv, "Bada kaam", ["a", "b"], origin="owner")
        with goal.session() as s:
            s.get(goal.GoalRun, v["id"]).rounds = get_settings().agent_goal_rounds
        goal.maybe_continue(conv, "default", "owner")
        r = c.post(f"/api/conversations/{conv}/goal/continue", headers=h)
        assert r.status_code == 200 and r.json()["goal"]["status"] == "working"
    assert seen and seen[-1] == "goal"                            # the next round started right away


def test_card_event_carries_the_hold(gz, monkeypatch):  # noqa: F811
    from app.agent import goal
    from app.config import get_settings
    from tests.test_bazar import _events
    conv = gz["conv"]
    _capture(monkeypatch)
    v = goal.set_goal("default", conv, "Kaam", ["a"], origin="owner")
    with goal.session() as s:
        s.get(goal.GoalRun, v["id"]).rounds = get_settings().agent_goal_rounds
    goal.maybe_continue(conv, "default", "owner")
    last = [e for e in _events(conv, "goal") if e.get("id") == v["id"]][-1]
    assert last["status"] == "blocked" and last["hold"] == "limit"


def test_ask_on_limit_off_keeps_the_old_failed(gz, monkeypatch):  # noqa: F811
    from app.agent import goal
    from app.config import get_settings
    conv = gz["conv"]
    _capture(monkeypatch)
    monkeypatch.setattr(get_settings(), "agent_goal_ask_on_limit", False, raising=False)
    v = goal.set_goal("default", conv, "Kaam", ["a"], origin="owner")
    with goal.session() as s:
        s.get(goal.GoalRun, v["id"]).rounds = get_settings().agent_goal_rounds
    goal.maybe_continue(conv, "default", "owner")
    assert _row(v["id"])["status"] == "failed"


# ---------------------------------------------------------------- (2) steering
def _steer_setup(monkeypatch, brain):
    """A running turn whose first tool blocks until released; the quick lane queues her message."""
    from app.agent import quick, santosh
    gate = asyncio.Event()

    async def tool(name, args, ctx, settings, route):
        await gate.wait()
        return {"status": "ok", "rows": 12}
    monkeypatch.setattr(santosh, "_run_tool", tool)

    async def qa(conv, tenant, text, steering=False):
        return {"text": "Theek hai, chal rahe kaam mein jod raha hoon.", "queued": True, "steering": steering}
    monkeypatch.setattr(quick, "answer", qa)
    _set_brain(monkeypatch, brain)
    return gate


def test_message_mid_job_reaches_the_running_job_at_its_next_step(gz, monkeypatch):  # noqa: F811
    from app.agent import santosh
    from app.db import Message, session
    from sqlalchemy import select
    conv = gz["conv"]
    brain = FakeBrain([([tu("1", "sheet_read", sheet="x")], "tool_use"),
                       ([txt("Samajh gaya, ab PDF ki jagah Excel bana raha hoon.")], "end_turn")])
    gate = _steer_setup(monkeypatch, brain)

    async def scene():
        job = asyncio.create_task(santosh.run_turn(conv, "Report banao PDF mein", tenant_id="default"))
        for _ in range(200):                                     # wait until the job is inside its tool step
            await asyncio.sleep(0.01)
            if santosh._locks[conv].locked() and brain.seen:
                break
        her = asyncio.create_task(santosh.run_turn(conv, "ruko, PDF nahi Excel banao", tenant_id="default"))
        await asyncio.sleep(0.05)
        gate.set()
        return await job, await her
    out, her_out = asyncio.run(scene())
    assert "Excel" in out and her_out == ""                      # her message did not start a 2nd job
    assert len(brain.seen) == 2                                  # ... and no 3rd model call ran for it
    last = brain.seen[1]["messages"][-1]["content"]
    said = " ".join(b.get("text", "") for b in last if isinstance(b, dict) and b.get("type") == "text")
    assert "PDF nahi Excel banao" in said and "BEECH" in said    # the running job read it before its next move
    assert last[0]["type"] == "tool_result"                      # results first: a valid request shape
    with session() as s:
        rows = s.scalars(select(Message).where(Message.conversation_id == conv,
                                               Message.display == "ruko, PDF nahi Excel banao")).all()
    assert rows                                                  # her words stay in the chat record


def test_message_after_the_job_ended_runs_normally(gz, monkeypatch):  # noqa: F811
    from app.agent import santosh, steer
    conv = gz["conv"]
    brain = FakeBrain([([txt("Report ready.")], "end_turn"), ([txt("Excel bhi bana diya.")], "end_turn")])
    _steer_setup(monkeypatch, brain)

    async def scene():
        async with santosh._locks[conv]:                          # a turn holds the chat but takes no more steps
            her = asyncio.create_task(santosh.run_turn(conv, "Excel bhi banao", tenant_id="default"))
            await asyncio.sleep(0.05)
        return await her
    before = steer.STATS["ran_after"]
    out = asyncio.run(scene())
    assert out == "Report ready." and steer.STATS["ran_after"] == before + 1   # it ran as its own turn


def test_quick_lane_says_it_reaches_the_job():
    from app.agent import quick
    assert "jod raha hoon" in quick.QUEUE_STEER and "next step" in quick.QUEUE_STEER
    assert "{queue_line}" in quick.SYSTEM


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.279.0"
