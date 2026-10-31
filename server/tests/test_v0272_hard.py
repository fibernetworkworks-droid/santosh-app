"""v0.272 SOCH KE JAWAB step 1 - spotting hard reasoning asks (owner: "NOW LETS WORK ON HARD, COMPLEX, REASONING WORK",
"GO ONE BY ONE").

The check: the only door to a deeper mode was goal.looks_big (lists / sequence words / many verbs = a multi-step JOB),
which caught 0 of 50 hard QUESTIONS - so a financial model, a proof, a GST comparison got no thinking. agent/hard.py
scores the kind of reasoning an ask needs (analysis, decision, calculation, maths, plan, diagnosis, deep explanation,
rules + general shapes: what-if, impact, difference, design, reasons, how-to-improve, judgement, word problems); the
'not sure' zone goes to one tiny time-limited judge call. A hard ask thinks from its first call.
"""
import asyncio
import types

import pytest

from tests.test_bazar import bz  # noqa: F401
from tests.test_v0186_long_goal import FakeBrain, _set_brain, gz, txt  # noqa: F401


def _st(**kw):
    base = dict(hard_judge=True, hard_judge_model="claude-haiku-5-5", hard_judge_timeout_s=2.5)
    base.update(kw)
    return types.SimpleNamespace(**base)


# ---------------------------------------------------------------- the rules on the sets
def test_every_hard_ask_is_spotted_and_no_everyday_ask_is():
    from app.agent import goal, hard
    from app.quality.hard_asks import EASY, HARD, check
    assert check() == [] and len(HARD) >= 50
    missed = [a["id"] for a in HARD if not hard.is_hard(a["text"])]
    assert not missed, missed
    assert not [t for t in EASY if hard.is_hard(t)]
    assert sum(goal.looks_big(a["text"]) for a in HARD) <= 2       # the old door missed them (the root cause)


def test_the_holdout_is_never_missed_outright_and_never_drags_an_easy_ask():
    from app.agent import hard
    from app.quality.hard_asks import HOLDOUT_EASY, HOLDOUT_HARD
    v = [hard.assess(t) for t in HOLDOUT_HARD]
    assert sum(x["hard"] for x in v) >= int(0.8 * len(HOLDOUT_HARD))          # rules alone (21/25 when written)
    assert not [t for t, x in zip(HOLDOUT_HARD, v) if not x["hard"] and not x["maybe"]]   # the rest go to the judge
    e = [hard.assess(t) for t in HOLDOUT_EASY]
    assert sum(x["hard"] for x in e) == 0 and sum(x["maybe"] for x in e) <= 2


def test_everyday_tool_asks_stay_fast():
    from app.agent import hard
    from app.quality.tool_asks import ASKS
    v = [hard.assess(a["text"]) for a in ASKS]
    assert sum(x["hard"] for x in v) <= 10 and sum(x["maybe"] for x in v) <= 10   # 6 + 6 of 163 when written


@pytest.mark.parametrize("text", ["Hoola bhej do mail Sharma ji ko, kyun ki meeting kal hai", "Alarm lagao 6 baje",
                                  "[System: goal steps baaki hain]", "(Result from HER PC task)", ""])
def test_actions_and_notes_are_never_hard(text):
    from app.agent import hard
    v = hard.assess(text)
    assert not v["hard"] and not v["maybe"]


# ---------------------------------------------------------------- the judge for the 'not sure' zone
class _Resp:
    def __init__(self, word):
        self.content = [types.SimpleNamespace(text=word)]


def _client(word=None, slow=False, boom=False):
    seen = []

    async def create(**kw):
        seen.append(kw)
        if boom:
            raise RuntimeError("no network")
        if slow:
            await asyncio.sleep(5)
        return _Resp(word)
    return types.SimpleNamespace(messages=types.SimpleNamespace(create=create)), seen


def test_judge_decides_the_maybe_zone_with_one_tiny_call(monkeypatch):
    from app.agent import hard, santosh
    hard._CACHE.clear()
    cli, seen = _client("HARD")
    monkeypatch.setattr(santosh, "get_client", lambda: cli)
    text = "Hamare employees jaldi naukri kyun chhod rahe hain? HR data dekh ke pattern batao"
    assert hard.assess(text)["maybe"]
    v = asyncio.run(hard.decide(text, _st()))
    assert v == {"hard": True, "by": "judge", "why": hard.assess(text)["why"]}
    assert seen[0]["max_tokens"] <= 3 and seen[0]["model"] == "claude-haiku-5-5"
    asyncio.run(hard.decide(text, _st()))
    assert len(seen) == 1                                         # cached: the same ask is judged once
    hard._CACHE.clear()


def test_judge_failure_or_timeout_keeps_the_fast_path(monkeypatch):
    from app.agent import hard, santosh
    text = "What would happen to my margins if raw material cost goes up 15 percent overall?"
    for kw in ({"boom": True}, {"slow": True}):
        hard._CACHE.clear()
        cli, _ = _client("HARD", **kw)
        monkeypatch.setattr(santosh, "get_client", lambda: cli)
        v = asyncio.run(hard.decide(text, _st(hard_judge_timeout_s=0.2)))
        assert v["hard"] is False or v["by"] == "rules"
    hard._CACHE.clear()
    assert asyncio.run(hard.judge(text, _st(hard_judge=False))) is None   # switched off: no call at all


def test_rules_decide_without_any_call(monkeypatch):
    from app.agent import hard, santosh
    monkeypatch.setattr(santosh, "get_client", lambda: (_ for _ in ()).throw(AssertionError("no call")))
    assert asyncio.run(hard.decide("Prove that root 2 is irrational", _st()))["by"] == "rules"
    assert asyncio.run(hard.decide("Alarm lagao 6 baje", _st()))["hard"] is False


# ---------------------------------------------------------------- the turn thinks from its first call
def test_a_hard_question_thinks_and_a_chat_does_not(gz, monkeypatch):  # noqa: F811
    conv = gz["conv"]
    brain = _set_brain(monkeypatch, FakeBrain([([txt("Namaste!")], "end_turn"),
                                               ([txt("Root 2 irrational hai kyunki...")], "end_turn")]))
    from app.agent.santosh import run_turn
    asyncio.run(run_turn(conv, "namaste", tenant_id="default"))
    assert "thinking" not in brain.seen[-1]
    asyncio.run(run_turn(conv, "Prove that root 2 is irrational", tenant_id="default"))
    assert brain.seen[-1]["thinking"] == {"type": "adaptive"}


def test_switches_off(gz, monkeypatch):  # noqa: F811
    from app.config import get_settings
    st = get_settings()
    conv = gz["conv"]
    for field in ("hard_thinking", "hard_detect"):
        setattr(st, field, False)
        try:
            brain = _set_brain(monkeypatch, FakeBrain([([txt("Jawab.")], "end_turn")]))
            from app.agent.santosh import run_turn
            asyncio.run(run_turn(conv, "Compare GST composition vs regular scheme and recommend", tenant_id="default"))
            assert "thinking" not in brain.seen[-1]
        finally:
            setattr(st, field, True)


def test_quality_card_lines():
    from app.quality import hard_asks as HA
    c = HA.card()
    assert c["spotted"] == c["hard_asks"] and c["missed"] == 0 and c["easy_marked_hard"] == 0
    assert HA.lines(c)[0].startswith("Hard asks (set v1): spotted by rules 50/50")


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.323.0"
