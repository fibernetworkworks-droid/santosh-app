"""v0.433 SOCH KE JAWAB step 4 - the reasoning recipe (owner: "GO STEP 4").

Steps 1-3 decided WHO thinks (a hard ask), on WHAT (Opus, effort high, 16k, thinking) and WITH WHAT (pylab). Nothing
said HOW: the reply rulebook is tuned for crisp chat. A hard turn's system prompt now carries HOW TO THINK - the
real question, facts vs stated assumptions, work in parts with pylab for every number, check before writing, answer
first + compact reasoning + assumptions + what would change it + next step - plus up to 3 lines for the kinds of
reasoning found (calculation, word problem, maths, decision, plan, diagnosis, analysis, rules, impact, deep).
Ordinary chat never carries it.
"""
import asyncio

import pytest

from tests.test_bazar import bz  # noqa: F401
from tests.test_v0186_long_goal import FakeBrain, _set_brain, gz, txt  # noqa: F401


def test_the_core_carries_the_whole_method():
    from app.agent import hard
    c = hard.RECIPE_CORE
    for must in ("HOW TO THINK", "The real question", "stated", "assumption", "pylab", "never mental",
                 "Check before you write", "answer or decision FIRST", "what would change the answer", "next step",
                 "uncertain", "private thinking is not the reply"):
        assert must in c, must
    assert len(c) < 2000                                     # a hard turn pays ~1.6 KB, not a second guide


@pytest.mark.parametrize("why,line", [
    (["calculation"], "Calculation:"), (["word problem"], "Word problem:"), (["maths"], "Maths / logic:"),
    (["decision"], "Decision:"), (["judgement"], "Decision:"), (["plan"], "Plan / strategy:"),
    (["diagnosis"], "Root cause:"), (["why"], "Root cause:"), (["analysis"], "Analysis:"),
    (["rules"], "Tax / legal"), (["what-if"], "Impact"), (["deep"], "Explanation:"),
])
def test_kind_lines(why, line):
    from app.agent import hard
    r = hard.recipe(why)
    assert r.startswith(hard.RECIPE_CORE) and line in r


def test_at_most_three_kind_lines_and_no_repeats():
    from app.agent import hard
    r = hard.recipe(["calculation", "numbers", "how-long", "decision", "judgement", "plan", "diagnosis", "rules"])
    extra = r[len(hard.RECIPE_CORE):].strip().splitlines()
    assert len(extra) == 3 and len(set(extra)) == 3
    assert hard.recipe([]) == hard.recipe(None) == hard.RECIPE_CORE


def test_almost_every_hard_ask_gets_its_own_guidance():
    from app.agent import hard
    from app.quality.hard_asks import HARD, HOLDOUT_HARD
    texts = [a["text"] for a in HARD] + HOLDOUT_HARD
    core_only = [t for t in texts if hard.recipe(hard.assess(t)["why"]) == hard.RECIPE_CORE]
    assert len(core_only) <= 2, core_only                    # 1 of 75 when written (a judge-zone Hindi ask)


def test_a_hard_turn_carries_the_recipe_and_a_chat_does_not(gz, monkeypatch):  # noqa: F811
    brain = _set_brain(monkeypatch, FakeBrain([([txt("Namaste!")], "end_turn"), ([txt("EMI ...")], "end_turn")]))
    from app.agent.santosh import run_turn
    asyncio.run(run_turn(gz["conv"], "namaste", tenant_id="default"))
    assert "HOW TO THINK" not in str(brain.seen[-1]["system"])
    asyncio.run(run_turn(gz["conv"], "20 lakh ke home loan ki EMI kitni banegi 9% pe 20 saal", tenant_id="default"))
    sysp = str(brain.seen[-1]["system"])
    assert "HOW TO THINK" in sysp and "Calculation:" in sysp
    assert "Her language, first and always" in sysp          # the reply rulebook still governs the writing


def test_switch_off(gz, monkeypatch):  # noqa: F811
    from app.config import get_settings
    st = get_settings()
    st.hard_recipe = False
    try:
        brain = _set_brain(monkeypatch, FakeBrain([([txt("Jawab.")], "end_turn")]))
        from app.agent.santosh import run_turn
        asyncio.run(run_turn(gz["conv"], "Prove that root 2 is irrational", tenant_id="default"))
        assert "HOW TO THINK" not in str(brain.seen[-1]["system"])
    finally:
        st.hard_recipe = True


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.843.0"
