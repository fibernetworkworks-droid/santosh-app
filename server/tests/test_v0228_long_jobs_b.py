"""v0.228 PHASE B - long jobs talk like Claude.

(1) NARRATE: a long job used to tick steps in silence; now a run of silent tool rounds asks for ONE progress line.
(2) PLAN FIRST: a clearly big ask gets "first tool call = kaam_plan set"; 6 tool steps without a plan ask for it
    (before, the plan was forced only at step 24).
(3) MILESTONES: at most 2 pushes per job (1/3, 2/3; 1/2 for 4-5 steps) - never every step.
(4) FOUR-PART REPORT on every finish: kya hua / kya bana / kya baaki / aapko kya karna hai, built from the plan.
"""
import asyncio
from pathlib import Path

from tests.test_bazar import bz  # noqa: F401
from tests.test_v0186_long_goal import FakeBrain, _set_brain, gz, tu, txt  # noqa: F401

ROOT = Path(__file__).resolve().parents[2]


def _texts(brain):
    out = []
    for call in brain.seen:
        for m in call["messages"]:
            for b in (m["content"] if isinstance(m["content"], list) else [{"text": m["content"]}]):
                if isinstance(b, dict):
                    out.append(str(b.get("text") or b.get("content") or ""))
    return "\n".join(out)


def _goal_events(conv):
    from app.db import Event, session
    from sqlalchemy import select
    with session() as s:
        return [e.payload for e in s.scalars(select(Event).where(Event.conversation_id == conv, Event.kind == "goal")
                                             .order_by(Event.id)).all()]


# ---------------------------------------------------------------- (2) plan first
def test_looks_big_rules():
    from app.agent.goal import looks_big
    assert looks_big("Pehle sales data nikalo, phir report banao, phir sabko mail bhejo")
    assert looks_big("1. website check karo\n2. errors list karo\n3. fix karke deploy karo")
    assert looks_big("Mere 5 competitors dhoondho, unke prices compare karo, ek Excel banao aur summary likho "
                     "jo main kal meeting mein dikha sakoon - sab kuch saaf ho")
    assert not looks_big("namaste")
    assert not looks_big("aaj mausam kaisa hai?")
    assert not looks_big("Ravi ko call reminder laga do kal 5 baje")
    assert not looks_big("[Goal jaari: steps baaki hain, phir aage badho]")   # system text is never her ask


def test_big_ask_gets_plan_first_short_ask_does_not(gz, monkeypatch):  # noqa: F811
    conv = gz["conv"]
    brain = _set_brain(monkeypatch, FakeBrain([([txt("Theek hai.")], "end_turn"), ([txt("Namaste!")], "end_turn")]))
    from app.agent.santosh import STATS_LONG, run_turn
    before = STATS_LONG["plan_first"]
    asyncio.run(run_turn(conv, "Pehle sales data nikalo, phir report banao, phir sabko mail bhejo",
                         tenant_id="default"))
    assert "Sabse PEHLA tool call `kaam_plan set`" in _texts(brain)
    assert STATS_LONG["plan_first"] == before + 1
    brain.seen.clear()
    asyncio.run(run_turn(conv, "namaste", tenant_id="default"))
    assert "Sabse PEHLA" not in _texts(brain)


def test_no_plan_after_six_steps_asks_for_it_once(gz, monkeypatch):  # noqa: F811
    conv = gz["conv"]
    script = [([tu(i, "kaam_status", q=f"kaam {i}")], "tool_use") for i in range(1, 9)]
    script.append(([txt("Ho gaya.")], "end_turn"))
    brain = _set_brain(monkeypatch, FakeBrain(script))
    from app.agent.santosh import run_turn
    asyncio.run(run_turn(conv, "status dekho", tenant_id="default"))
    seen = _texts(brain)
    assert seen.count("par plan nahi likha") >= 1
    # asked exactly once (the message rides in every later call's history, so count the calls that first saw it)
    first = next(i for i, c in enumerate(brain.seen) if "par plan nahi likha" in str(c["messages"]))
    assert first == 6                                  # after the 6th tool step, not at step 24
    assert sum(str(c["messages"][-1]).count("par plan nahi likha") for c in brain.seen) == 1


# ---------------------------------------------------------------- (1) narrate
def test_silent_goal_rounds_ask_for_one_progress_line(gz, monkeypatch):  # noqa: F811
    conv = gz["conv"]
    brain = _set_brain(monkeypatch, FakeBrain([
        ([txt("Plan."), tu(1, "kaam_plan", action="set", goal="Bada kaam",
                           steps=["a", "b", "c", "d", "e", "f"])], "tool_use"),
        ([tu(2, "kaam_plan", action="step", n=1, state="done")], "tool_use"),     # silent 1
        ([tu(3, "kaam_plan", action="step", n=2, state="done")], "tool_use"),     # silent 2
        ([tu(4, "kaam_plan", action="step", n=3, state="done")], "tool_use"),     # silent 3 -> narrate
        ([txt("3 ho gaye, ab d."), tu(5, "kaam_plan", action="step", n=4, state="done")], "tool_use"),
        ([tu(6, "kaam_plan", action="step", n=5, state="done")], "tool_use"),
        ([tu(7, "kaam_plan", action="step", n=6, state="done")], "tool_use"),
        ([txt("Sab ho gaya."), tu(8, "kaam_plan", action="finish", outcome="done", reason="poora")], "tool_use"),
        ([txt("Sab ho gaya.")], "end_turn"),
    ]))
    from app.agent.santosh import STATS_LONG, run_turn
    before = STATS_LONG["narrate"]
    asyncio.run(run_turn(conv, "bada kaam karo", tenant_id="default"))
    assert "kaafi der se tumne use kuch nahi bataya" in _texts(brain)
    assert STATS_LONG["narrate"] == before + 1         # the line she got reset the count: asked once, not every round
    # kaam_plan step done itself asks for the one line while steps are left
    assert "EK chhoti line mein use batao" in _texts(brain)


# ---------------------------------------------------------------- (3) milestones
def test_milestones_push_at_most_twice_never_every_step(gz):  # noqa: F811
    from app import push
    from app.agent import goal
    conv = gz["conv"]
    v = goal.set_goal("default", conv, "Website banana", [f"s{i}" for i in range(1, 7)], origin="owner")
    for n in range(1, 7):
        goal.mark_step("default", v["id"], n, "done")
    evs = _goal_events(conv)
    marks = [e["milestone"] for e in evs if e.get("milestone")]
    assert marks == ["2/6", "4/6"]                     # 1/3 and 2/3, never the last step
    pushed = [push.render("goal", e, "Hoola") for e in evs]
    sent = [p for p in pushed if p]
    assert len(sent) == 2 and "2/6 steps ho gaye" in sent[0][1]
    v2 = goal.set_goal("default", conv, "Chhota", ["a", "b", "c", "d"], origin="owner")
    for n in range(1, 5):
        goal.mark_step("default", v2["id"], n, "done")
    assert [e["milestone"] for e in _goal_events(conv) if e.get("milestone") and e["id"] == v2["id"]] == ["2/4"]
    v3 = goal.set_goal("default", conv, "Teen", ["a", "b", "c"], origin="owner")
    for n in range(1, 4):
        goal.mark_step("default", v3["id"], n, "done")
    assert not [e for e in _goal_events(conv) if e.get("milestone") and e["id"] == v3["id"]]   # small jobs: none


# ---------------------------------------------------------------- (4) the four-part report
def test_finish_builds_the_four_part_report(gz):  # noqa: F811
    from app import push
    from app.agent import goal
    conv = gz["conv"]
    v = goal.set_goal("default", conv, "Report", ["data", "draft", "bhejo"], origin="owner")
    goal.mark_step("default", v["id"], 1, "done", "https://docs.google.com/x/abc")
    goal.mark_step("default", v["id"], 2, "done", "report.pdf bana")
    out = goal.finish("default", v["id"], "done", "Report taiyaar", made=["https://drive.google.com/file/d/9"],
                      your_turn="Report dekh ke haan bolo")
    r = out["report"]
    assert r["summary"] == "Report taiyaar"
    assert r["hua"][0].startswith("data") and len(r["hua"]) == 2
    assert "https://drive.google.com/file/d/9" in r["bana"] and "https://docs.google.com/x/abc" in r["bana"]
    assert "report.pdf" in r["bana"]
    assert r["baaki"] == ["bhejo"] and r["aapka"] == "Report dekh ke haan bolo"
    text = goal.report_text(r)
    for part in ("✅ Kya hua", "📎 Kya bana", "⏳ Kya baaki hai", "👉 Aapko kya karna hai"):
        assert part in text
    last = _goal_events(conv)[-1]
    assert last["report"]["aapka"] == "Report dekh ke haan bolo"
    title, body = push.render("goal", last, "Hoola")
    assert "Report dekh ke haan bolo" in body
    # everything done, nothing for her: the report says so plainly
    v2 = goal.set_goal("default", conv, "Chhota", ["a"], origin="owner")
    goal.mark_step("default", v2["id"], 1, "done")
    r2 = goal.finish("default", v2["id"], "done", "ho gaya")["report"]
    assert r2["baaki"] == [] and r2["aapka"].startswith("Kuch nahi")


def test_kaam_plan_finish_returns_the_report_for_her_final_answer(gz):  # noqa: F811
    from app.agent.goal_tools import kaam_plan
    from app.agent.tools import Ctx
    conv = gz["conv"]
    ctx = Ctx(tenant_id="default", conversation_id=conv)
    asyncio.run(kaam_plan(ctx, action="set", goal="Mail", steps=["likho", "bhejo"]))
    asyncio.run(kaam_plan(ctx, action="step", n=1, state="done"))
    out = asyncio.run(kaam_plan(ctx, action="finish", outcome="blocked_on_her", reason="Aapka OTP chahiye",
                                made=["draft-42"]))
    assert "👉 Aapko kya karna hai: Aapka OTP chahiye" in out["report"]
    assert "chaar hisson" in out["note"]


# ---------------------------------------------------------------- the phone + console + wiring
def test_phone_and_console_show_report_and_continue():
    card = (ROOT / "lib/ui/goal_card.dart").read_text()
    assert "Aage badhao" in card and "continueGoal" in card and "KYA BANA" in card and "AAPKO KYA KARNA HAI" in card
    assert "continueGoal" in (ROOT / "lib/api.dart").read_text()
    js = (ROOT / "server/app/static/console/v2.js").read_text()
    assert "function goalReport" in js and "goalReport(p.report)" in js
    assert ".greport" in (ROOT / "server/app/static/console/v2.css").read_text()
    prompt = (ROOT / "server/app/agent/prompts.py").read_text()
    assert "Kaam karte hue BOLTE raho" in prompt and "Aapko kya karna hai" in prompt


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.235.0"
    assert "0.235.0+275" in (ROOT / "pubspec.yaml").read_text()
