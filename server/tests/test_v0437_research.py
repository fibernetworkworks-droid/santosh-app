"""v0.437 SOCH KE JAWAB step 6 - deep research (owner: "GO STEP 6").

The check: 5 of 5 deep-research asks scored 0 in agent/hard.py, so research got no Opus, no thinking, no recipe and no
self-check; the crew had 8 steps and 1,500 tokens an agent, reports capped at ~8 lines with no sources asked for, and a
crew that ran out of clock lost everything. Now: a "research" signal (3 points = hard on its own) -> Opus + thinking +
the DEEP RESEARCH recipe line first (4-6 sub-questions, deploy_agents + own reading, primary sources, [n] sources with
dates, two sources for key numbers, pylab for derived figures, summary first + Sources list, PDF when asked / long);
ctx.research -> the crew gets 14 steps, 4,000 tokens, a RESEARCH_RULE (open real pages, link + date per fact) and a
graceful wrap-up (soft deadline 170 s inline / 75% of the background clock, or steps used up mid-search) so what was
found comes back WITH sources; the self-check's free research_check refuses an answer with no sources or with a link
no tool returned.
"""
import asyncio
import types

import pytest

from tests.test_bazar import bz  # noqa: F401
from tests.test_v0186_long_goal import FakeBrain, _set_brain, gz, tu, txt  # noqa: F401

@pytest.fixture(autouse=True)
def _no_plan_gate(monkeypatch):
    """v0.472 R1: a big research ask now shows its plan and waits for her Haan. These tests are about the research
    engine AFTER that (recipe, crew, source check), so the gate steps aside here; test_v0472_research_plan.py covers it."""
    from app.agent import research_plan

    async def _off(*a, **k):
        return None
    monkeypatch.setattr(research_plan, "gate", _off)


RESEARCH = [
    "Do deep research on the Indian EV two-wheeler market and give me a PDF report",
    "Deep research karo AI agents ke market pe aur PDF do",
    "Research karo ki Pune mein cloud kitchen kholna kaisa rahega",
    "Indian fintech industry pe detailed report banao with sources",
    "Mere competitors ka market study karo",
    "Research the solar rooftop market in Maharashtra with sources",
    "Quick commerce sector analysis for India 2026",
    "Write a white paper on UPI adoption in rural India",
    "Feasibility study for a cold storage in Nashik",
    "शोध करके बताइए भारत में इलेक्ट्रिक बसों का बाजार कैसा है",
]


# ---------------------------------------------------------------- spotting research
@pytest.mark.parametrize("text", RESEARCH)
def test_research_asks_are_hard_research(text):
    from app.agent import hard
    a = hard.assess(text)
    assert a["hard"] and "research" in a["why"] and hard.research_wanted(text)


def test_everyday_asks_are_never_research():
    from app.agent import hard
    from app.quality.hard_asks import EASY, HOLDOUT_EASY
    assert not [t for t in EASY + HOLDOUT_EASY if hard.research_wanted(t)]


def test_the_research_line_leads_the_recipe():
    from app.agent import hard
    r = hard.recipe(["decision", "research", "calculation"])
    extra = r[len(hard.RECIPE_CORE):].strip().splitlines()
    assert extra[0].startswith("- DEEP RESEARCH:") and "deploy_agents" in extra[0] and "Sources:" in extra[0]
    assert "Never cite a link you did not get from a tool" in extra[0]


# ---------------------------------------------------------------- the free source check
def test_research_check_wants_sources_from_the_tools():
    from app.agent import hard
    ev = ("TOOL web_sources input: {...}\nRESULT: EV sales 2025 ... https://www.vahan.parivahan.gov.in/report?y=2025 "
          "and https://mospi.gov.in/data/ev")
    assert "cites no sources" in hard.research_check("EV sales grew 40% last year.", ev)[0]
    made = hard.research_check("Sales grew 40% [1].\nSources: [1] https://example-blog.com/ev-boom", ev)
    assert made and "example-blog.com/ev-boom" in made[0]
    ok = "Sales grew 40% [1][2].\nSources: [1] https://vahan.parivahan.gov.in/report?y=2025 [2] https://mospi.gov.in/data/ev."
    assert hard.research_check(ok, ev) == []
    assert hard.code_check("research EV", "no links here", ["research"], ["web_sources"], ev)    # wired into code_check


# ---------------------------------------------------------------- the crew
def test_a_research_agent_is_told_to_cite():
    from app.agent import team
    assert team.RESEARCH_RULE in team._agent_system("a", "t", research=True)
    assert team.RESEARCH_RULE not in team._agent_system("a", "t")


def _agent_run(monkeypatch, script, shared, settings_over=None):
    from app.agent import santosh, team
    from app.config import get_settings
    st = get_settings()
    seen = []
    queue = list(script)

    async def fake_think(brain, system, history, settings, tools=None, live=None, max_tokens=None):
        seen.append({"system": system, "max_tokens": max_tokens, "last": history[-1]})
        blocks, stop = queue.pop(0)
        return blocks, stop, "claude"

    async def fake_tool(b, ctx, settings, conv):
        return {"type": "tool_result", "tool_use_id": b["id"], "content": "page text https://mospi.gov.in/x"}
    monkeypatch.setattr(santosh, "_think", fake_think)
    monkeypatch.setattr(team, "_agent_tool", fake_tool)
    old = {}
    for k, v in (settings_over or {}).items():
        old[k] = getattr(st, k)
        setattr(st, k, v)
    try:
        out = asyncio.run(team._run_agent({"name": "ev", "task": "EV sales 2025"}, "tm1", "EV report", {"web"},
                                          "default", "c-res", "turn1", st, shared))
    finally:
        for k, v in old.items():
            setattr(st, k, v)
    return out, seen


def test_a_research_agent_gets_room_and_hands_in_its_sources_when_steps_run_out(env, monkeypatch):
    script = [([tu(i, "web_sources", query=f"q{i}")], "tool_use") for i in range(3)] + \
             [([txt("EV 2W sales 2025: 1.9 lakh/month [https://mospi.gov.in/x, Oct 2025]")], "end_turn")]
    out, seen = _agent_run(monkeypatch, script, {"research": True, "place": ""}, {"team_research_max_steps": 3})
    assert all(s["max_tokens"] == 4000 for s in seen)
    assert len(seen) == 4 and "time is almost up" in str(seen[-1]["last"])      # 3 steps, then the wrap-up
    assert "mospi.gov.in" in out["deliverable"] and out["ok"]


def test_the_soft_deadline_wraps_up_instead_of_losing_the_work(env, monkeypatch):
    script = [([tu(1, "web_sources", query="q")], "tool_use"),
              ([txt("Found: 1.9 lakh/month [https://mospi.gov.in/x]")], "end_turn")]
    out, seen = _agent_run(monkeypatch, script, {"research": True, "soft_s": 0.0})
    assert len(seen) == 2 and "time is almost up" in str(seen[-1]["last"]) and "mospi" in out["deliverable"]


def test_an_ordinary_crew_is_unchanged(env, monkeypatch):
    script = [([txt("Done: 3 prices")], "end_turn")]
    out, seen = _agent_run(monkeypatch, script, {"place": ""})
    assert seen[0]["max_tokens"] == 1500 and len(seen) == 1 and team_rule_absent(seen[0]["system"])


def team_rule_absent(system):
    from app.agent import team
    return team.RESEARCH_RULE not in system


def test_deploy_agents_hands_the_research_flag_to_the_crew(env, monkeypatch):
    from app.agent import team
    from app.agent.tools import Ctx
    got = []

    async def fake_run(spec, team_id, mission, main_fams, tenant, conv, turn_id, settings, shared=None):
        got.append(dict(shared or {}))
        return {"name": spec["name"], "ok": True, "stopped": False, "seconds": 1, "tools": [], "deliverable": "x"}
    monkeypatch.setattr(team, "_run_agent", fake_run)
    ctx = Ctx("default", "c-res")
    ctx.research = True
    asyncio.run(team.deploy_agents(ctx, mission="EV report", agents=[{"name": "a", "task": "EV sales"}]))
    assert got and got[0]["research"] is True


# ---------------------------------------------------------------- the turn
def test_a_research_turn_marks_the_crew_and_carries_the_research_line(gz, monkeypatch):  # noqa: F811
    from app.agent import santosh
    seen_ctx = []
    real = santosh._steps

    async def spy(conversation_id, ctx, *a, **k):
        seen_ctx.append(ctx)
        return await real(conversation_id, ctx, *a, **k)
    monkeypatch.setattr(santosh, "_steps", spy)
    brain = _set_brain(monkeypatch, FakeBrain([([txt("Report ...")], "end_turn")]))
    asyncio.run(santosh.run_turn(gz["conv"], RESEARCH[0], tenant_id="default"))
    assert seen_ctx and getattr(seen_ctx[0], "research", False) is True
    assert "DEEP RESEARCH:" in str(brain.seen[-1]["system"]) and brain.seen[-1]["model"] == "claude-opus-5-5"


def test_a_research_answer_without_sources_is_fixed_before_she_sees_it(gz, monkeypatch):  # noqa: F811
    from app.config import get_settings
    st = get_settings()
    st.hard_check = True
    try:
        brain = _set_brain(monkeypatch, FakeBrain([
            ([txt("EV two-wheeler sales grew strongly in 2025 and will keep growing.")], "end_turn"),
            ([txt("EV 2W sales grew 21% in 2025 [1].\nSources: [1] https://vahan.parivahan.gov.in/ - Oct 2025")],
             "end_turn"),
        ]))
        from app.agent.santosh import run_turn
        asyncio.run(run_turn(gz["conv"], RESEARCH[0], tenant_id="default"))
        note = brain.seen[1]["messages"][-1]["content"][0]["text"]
        assert note.startswith("[System: JAANCH") and "cites no sources" in note
    finally:
        st.hard_check = False


def test_settings():
    from app.config import Settings
    s = Settings()
    assert (s.team_research_max_steps, s.team_research_max_tokens, s.team_research_soft_s) == (14, 4000, 170.0)


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.548.0"
