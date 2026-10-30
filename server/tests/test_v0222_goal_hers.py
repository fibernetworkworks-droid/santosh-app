"""v0.222 GOAL HERS - a long job she asked for keeps her authority in its background rounds.

Root causes (found on v0.221): every background round of a long job ran as actor "routine", so (1) with Employee mode
on, the employee gate treated her own job like a scheduled routine - at trust 'seekh' every job-duty step became an
approval card and the job stalled; (2) once the month's AI limit hit 100%, run_turn refused the round as background
work, so her own job stopped half-way. Fix: the goal remembers who asked (origin); a round of HER job runs as actor
"goal" = her own authority at the gate and her own chat lane in the budget. A routine's job stays "routine".
"""
import asyncio

from app.agent.tools import Ctx, dispatch
from tests.test_bazar import bz  # noqa: F401
from tests.test_v0186_long_goal import FakeBrain, _set_brain, gz, tu, txt  # noqa: F401


def _gid(conv):
    from app.agent import goal
    return goal.active_for(conv)["id"]


def _origin(gid):
    from app.agent import goal
    from app.db import session
    with session() as s:
        return s.get(goal.GoalRun, gid).origin


def _captured_actor(coro):
    actor = coro.cr_frame.f_locals.get("actor")
    coro.close()
    return actor


def test_goal_remembers_who_asked(gz):  # noqa: F811
    from app.agent import goal
    conv = gz["conv"]
    goal.set_goal("default", conv, "Mera kaam", ["a", "b"], origin="owner")
    assert _origin(_gid(conv)) == "owner"
    goal.set_goal("default", conv, "Roz ka kaam", ["a", "b"], origin="routine")
    assert _origin(_gid(conv)) == "routine"
    goal.set_goal("default", conv, "Approved", ["a"], origin="approved:x1")
    assert _origin(_gid(conv)) == "owner"
    goal.set_goal("default", conv, "Goal round replans", ["a"], origin="goal")
    assert _origin(_gid(conv)) == "owner"                      # a replan inside her job stays hers
    assert goal.round_actor("owner") == "goal" and goal.round_actor("routine") == "routine"
    assert goal.round_actor(None) == "routine"                 # goals from before v0.222: the old behaviour


def test_kaam_plan_from_her_turn_records_her(gz):  # noqa: F811
    from app.agent import goal
    conv = gz["conv"]
    asyncio.run(dispatch("kaam_plan", {"action": "set", "goal": "Website", "steps": ["build", "launch"]},
                         Ctx(tenant_id="default", conversation_id=conv, actor="owner")))
    assert _origin(_gid(conv)) == "owner"
    asyncio.run(dispatch("kaam_plan", {"action": "set", "goal": "Report", "steps": ["a", "b"]},
                         Ctx(tenant_id="default", conversation_id=conv, actor="routine")))
    assert _origin(_gid(conv)) == "routine"
    assert goal.active_for(conv)["goal"] == "Report"


def test_rounds_of_her_job_run_as_goal_routines_stay_routine(gz, monkeypatch):  # noqa: F811
    from app.agent import goal, santosh
    conv = gz["conv"]
    seen = []
    monkeypatch.setattr(santosh, "_bg", lambda coro: seen.append(_captured_actor(coro)))
    monkeypatch.setattr(goal, "_waiting_on_her", lambda c: False)
    goal.set_goal("default", conv, "Mera kaam", ["a", "b"], origin="owner")
    assert goal.maybe_continue(conv, "default", "owner") and seen[-1] == "goal"
    assert goal.maybe_continue(conv, "default", "goal") and seen[-1] == "goal"   # a round may chain the next one
    goal.set_goal("default", conv, "Routine kaam", ["a", "b"], origin="routine")
    assert goal.maybe_continue(conv, "default", "routine") and seen[-1] == "routine"
    # the resume sweep after her answer keeps the same rule
    goal.set_goal("default", conv, "Mera kaam 2", ["a", "b"], origin="owner")
    goal._pause(_gid(conv))
    assert goal.resume_tick() == 1 and seen[-1] == "goal"
    # staff / customer turns never schedule rounds
    assert not goal.maybe_continue(conv, "default", "staff:m1")


def test_employee_gate_treats_her_job_as_hers(gz):  # noqa: F811
    from app.employee import service as emp
    from app.life import upcoming_reminders
    emp.setup("default", enabled=True, role="front_desk", business_name="Sharma Clinic", business_kind="clinic",
              about="Dant ka clinic", hours={"open": "10:00", "close": "19:00", "days": [0, 1, 2, 3, 4, 5]})
    conv = gz["conv"]
    out = asyncio.run(dispatch("create_reminder", {"text": "Patient ko call", "when": "2027-01-15T11:00"},
                               Ctx(tenant_id="default", conversation_id=conv, actor="routine")))
    assert out["status"] == "waiting_owner"                    # a scheduled routine at 'seekh': still her tap
    out = asyncio.run(dispatch("create_reminder", {"text": "Patient ko call 2", "when": "2027-01-15T12:00"},
                               Ctx(tenant_id="default", conversation_id=conv, actor="goal")))
    assert "waiting_owner" not in str(out)                     # her own long job: runs like her own word
    assert any(r["text"] == "Patient ko call 2" for r in upcoming_reminders("default"))
    assert emp.actor_label("default", "goal") == "Owner ka lamba kaam"
    # Pause still holds job duties for her own long job, exactly like her own turns
    emp.set_pause("default", True)
    import pytest
    from app.employee.service import Blocked
    with pytest.raises(Exception) as e:
        asyncio.run(dispatch("create_reminder", {"text": "X", "when": "2027-01-15T13:00"},
                             Ctx(tenant_id="default", conversation_id=conv, actor="goal")))
    assert "Pause" in str(e.value) or isinstance(e.value, Blocked)


def test_ai_limit_never_stops_her_job_but_still_stops_routines(gz, monkeypatch):  # noqa: F811
    from app import usage
    from app.agent import santosh
    conv = gz["conv"]
    asked = []

    def allowed(tenant, feature):
        asked.append(feature)
        return feature not in usage.BACKGROUND             # the month's limit is used up

    monkeypatch.setattr(usage, "allowed", allowed)
    monkeypatch.setattr(usage, "blocked_text", lambda t: "BUDGET KHATAM")
    _set_brain(monkeypatch, FakeBrain([([txt("Step ho gaya")], "end_turn")]))
    out = asyncio.run(santosh.run_turn(conv, "[Goal jaari: kaam — baaki steps: 1. a]", tenant_id="default", actor="goal"))
    assert out == "Step ho gaya" and asked[-1] == "chat"
    out = asyncio.run(santosh.run_turn(conv, "[Goal jaari: kaam — baaki steps: 1. a]", tenant_id="default", actor="routine"))
    assert out == "BUDGET KHATAM" and asked[-1] == "routine"


def test_goal_round_text_is_never_her_words(gz, monkeypatch):  # noqa: F811
    from app import yaad
    from app.agent import santosh
    conv = gz["conv"]
    _set_brain(monkeypatch, FakeBrain([([txt("Aage badh gaya")], "end_turn")]))
    asyncio.run(santosh.run_turn(conv, "[Goal jaari: secret-plan-77 — baaki steps: 1. a]", tenant_id="default",
                                 actor="goal"))
    assert all("secret-plan-77" not in t for _, t in yaad._recent_user_words(conv, 10, 600))


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.269.0"
