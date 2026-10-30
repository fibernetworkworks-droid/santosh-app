"""v0.258 CHALTE CHALTE BOLO (owner, with a screenshot of Claude working: "CHECK HOW CLAUDE GIVE PROPER RESPONSE
IN BETWEEN AND A FINAL RESULT PERFECTLY ... HOOLA DIRECTLY LOADS THE RESULT OR GIVE THE BULK BACKEND UNWANTED
RESPONSES"; then "GO").

Claude's rhythm, read off her screenshot: one sentence of intent BEFORE the first tool, then after every tool
group one short line = the real finding (with its number / id) + what it is doing now, with the tool noise
collapsed into a row beside it. Four tool groups in that turn, four lines.

Hoola's three flaws, each fixed here:
  1. narration lived behind `state["goal"]` (santosh.py), so an ordinary multi-tool ask said NOTHING until the
     answer - her "DIRECTLY LOADS THE RESULT";
  2. v0.240 then throttled even goal mode to one line per 8 silent rounds, max 2 a job;
  3. NARRATE forbade "koi number ya link", which is exactly what makes Claude's line worth reading.

What v0.240 actually won is untouched: no four-part bullet report in the chat, one short final answer.
"""
import asyncio
from pathlib import Path

from app.config import get_settings

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


# ---------------------------------------------------------------- flaw 1: the ordinary ask was silent
def test_a_plain_multi_tool_ask_now_gets_lines_without_any_plan(gz, monkeypatch):  # noqa: F811
    """THE one that made her write in. No kaam_plan anywhere: four tool rounds used to pass in total silence."""
    conv = gz["conv"]
    script = [([tu(i, "kaam_status", q=f"dekho {i}")], "tool_use") for i in range(1, 5)]
    script.append(([txt("Ho gaya.")], "end_turn"))
    brain = _set_brain(monkeypatch, FakeBrain(script))
    from app.agent.santosh import STATS_LONG, run_turn
    before = STATS_LONG["narrate"]
    asyncio.run(run_turn(conv, "status dekho", tenant_id="default"))
    seen = _texts(brain)
    assert "ab use EK chhoti line batao" in seen, "a plain multi-tool ask must talk too, not only a goal"
    assert STATS_LONG["narrate"] > before


def test_a_background_actor_stays_quiet():
    """A routine talking to itself has nobody reading the chat: the lane is pinned to the watched actors."""
    txt_ = (ROOT / "server/app/agent/santosh.py").read_text()
    assert '_narrate_lane = (getattr(ctx, "actor", "owner") or "owner") in ("owner", "goal")' in txt_
    assert "if _narrate_lane:" in txt_
    assert 'if state.get("goal"):\n                spoke' not in txt_          # the goal-only gate is gone


# ---------------------------------------------------------------- flaw 2: the cadence
def test_the_cadence_is_claudes_one_per_group_still_capped():
    st = get_settings()
    assert st.agent_narrate_every == 1 and st.agent_narrate_max == 6
    src = (ROOT / "server/app/config.py").read_text()
    assert "v0.258" in src and "8 in v0.240 = silence" in src


# ---------------------------------------------------------------- flaw 3: the line must carry the finding
def test_the_line_carries_the_tools_own_fact():
    from app.agent import goal as G
    bare = G.NARRATE
    assert "asli number / id / naam / link" in bare and "banaya hua nahi" in bare
    assert "koi number ya link nahi" not in bare                       # v0.240's ban, reversed
    withf = G.narrate_line(["12 naye mails aaye", "video taiyar - drive.google.com"])
    assert "12 naye mails aaye" in withf and "drive.google.com" in withf
    assert "naya mat banao" in withf
    assert G.narrate_line([]) == bare                                  # no fact -> the bare ask, never an empty tail


def test_the_true_facts_are_kept_for_the_line_not_only_whispered():
    """say.line_for already read the truth out of every tool result; livereply threw it away with the turn."""
    src = (ROOT / "server/app/agent/santosh.py").read_text()
    assert 'said_now = state.setdefault("saylines", [])' in src
    assert "_goal.narrate_line(state.get(\"saylines\"))" in src
    assert "del said_now[:-4]" in src                                   # bounded, never a growing list
    assert "live.feed_say(_s)" in src                                   # the live whisper still happens


# ---------------------------------------------------------------- the opener, and no contradictions left
def test_the_prompt_asks_for_the_opener_and_the_per_step_line():
    p = (ROOT / "server/app/agent/prompts.py").read_text()
    assert "CHALTE CHALTE BOLO" in p
    assert "bade kaam se PEHLE ek vaakya" in p                          # say it before touching a tool
    assert "har tool ke baad ek chhoti line" in p
    assert "har step ka koi line chat mein mat likho" not in p          # v0.240's order is gone
    for ban in ("koi bullet", "koi heading", "step-by-step list"):
        assert ban in p, ban


def test_no_prompt_contradicts_another_in_the_same_turn():
    """PLAN_FIRST asked for a line per step while prompts.py and kaam_plan forbade one - all three now agree."""
    from app.agent import goal as G
    from app.agent import goal_tools as GT  # noqa: F401
    assert "har bade step ke baad ek chhoti line" in G.PLAN_FIRST
    gt = (ROOT / "server/app/agent/goal_tools.py").read_text()
    assert "chat mein iska koi line mat likho" not in gt
    assert "is step se jo asli cheez mili" in gt


def test_the_rulebook_carries_both_rules_on_chat_only():
    from app.agent import replystyle as R
    assert "say it in ONE sentence before you touch a tool" in R.CHAT
    assert "While the work runs, keep talking" in R.CHAT
    assert "work out silently" not in R.CHAT
    # the call keeps its own pacing (v0.230 news queue / murmurs); the quick lane never runs tools
    for other in (R.VOICE, R.QUICK):
        assert "While the work runs, keep talking" not in other
    for t in (R.CHAT, R.QUICK, R.VOICE):
        assert "{" not in t and "}" not in t                            # voice.PERSONA is .format()ed


# ---------------------------------------------------------------- nothing CHHOTA JAWAB won is lost
def test_the_final_answer_is_still_short_and_the_report_still_lives_on_the_card():
    from app.agent import replystyle as R
    assert "Results of work, the short way" in R.CHAT
    assert "never a bullet list of the steps you ran" in R.CHAT
    gt = (ROOT / "server/app/agent/goal_tools.py").read_text()
    assert 'out["card_shows"]' in gt and "EK chhoti insaani line" in gt
    p = (ROOT / "server/app/agent/prompts.py").read_text()
    assert "Aakhri jawab hamesha chaar hisson mein" not in p


def test_the_console_already_folds_the_tool_noise_like_claude():
    """The UI needed no work: the step rows were already a collapsed, expandable group."""
    js = (ROOT / "server/app/static/console/v2.js").read_text()
    assert "STEPBUF = document.createElement('details')" in js
    assert "STEPBUF.className = 'tools'" in js and "STEPBUF.open = false" in js
    assert "`${n} step${n > 1 ? \"s\" : \"\"}`" in js


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.264.0"
    assert "0.264.0+304" in (ROOT / "pubspec.yaml").read_text()
