"""v0.970 HOOLA PIPELINE P4 FIX - her live v0.969 test: 'better answer' moved up to ULTRA, OpenRouter answered 403
'Model google/gemini-4-carbon is banned', the Box handed over to the backup in 2.5 s and the reply came - but the rest
of that turn (its after-turn calls) still asked the banned model, failed twice and paused the whole OpenRouter brain
for 10 minutes, so her next two messages went outside the Box. Fake models only, no network."""
from __future__ import annotations

import asyncio
import importlib.util
import pathlib

import pytest

_spec = importlib.util.spec_from_file_location(
    "_p4", pathlib.Path(__file__).with_name("test_v0969_pipeline_p4.py"))
_p4 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_p4)
box = _p4.box
BANNED = 'OpenRouter error 403: {"error":{"message":"Model a/mid1-20261110 is banned","code":403}}'


def test_after_a_hand_over_the_rest_of_the_turn_asks_the_model_that_took_over(box):
    from app.agent import llm
    from app.pipeline import runner as R
    b = box.begin("c1", "t1", "hi")
    assert llm.MODEL_NOW.get() == "openrouter:a/mid1"
    hand = R.HAND.get()
    asyncio.run(R.call(hand, _p4._maker({"a/mid1": _p4.boom(BANNED), "b/mid2": _p4.ok()}, [])))
    assert llm.model_in_force() == "openrouter:b/mid2"     # the turn's other calls: the banned model never again
    box.end(b, "ok")
    assert R.TURN_SWAP.get() is None                       # the swap lives for this message only


def test_a_banned_model_is_off_for_a_day_and_the_next_message_starts_on_a_backup(box):
    from app.pipeline import runner as R
    b = box.begin("c2", "t1", "hi")
    asyncio.run(R.call(R.HAND.get(), _p4._maker({"a/mid1": _p4.boom(BANNED), "b/mid2": _p4.ok()}, [])))
    box.end(b, "ok")
    h = box.health()
    assert h["a/mid1"]["paused"] and "banned" in h["a/mid1"]["dead"]
    b2 = box.begin("c3", "t1", "hi")
    assert b2["sheet"]["parts"][0]["model"]["id"] != "a/mid1"
    box.end(b2, "ok")


def test_a_key_or_credit_403_is_not_the_models_fault(box):
    from app.pipeline import runner as R
    assert not R.hard('OpenRouter error 403: {"error":{"message":"Key limit exceeded"}}')
    assert R.hard(BANNED) and R.hard("404 No endpoints found for x/y")
    R.model_failed("openrouter:a/mid1", 'OpenRouter error 403: Key limit exceeded')
    assert "dead" not in box.health().get("a/mid1", {})


def test_a_failing_after_turn_call_in_a_box_turn_never_pauses_the_whole_brain(box, monkeypatch):
    from app.agent import llm
    from app import glmdoor

    async def bad(*a, **k):
        raise llm.LLMError(BANNED)
    monkeypatch.setattr(llm, "_openai_create", bad)
    monkeypatch.setattr(glmdoor, "_acreate", bad)
    before = llm.BREAKERS["glm"]["fails"]
    b = box.begin("c4", "t1", "hi")
    for _ in range(3):
        with pytest.raises(llm.LLMError):
            asyncio.run(llm.openai_create("glm", "s", [], [{"role": "user", "content": "x"}], 50))
        with pytest.raises(llm.LLMError):
            asyncio.run(glmdoor.acreate({}))
    box.end(b, "ok")
    assert llm.BREAKERS["glm"]["fails"] == before and not llm.brain_paused("glm")
    assert box.health()["a/mid1"]["paused"]               # it went to that model's own record instead


def test_outside_a_box_turn_the_brain_switch_still_counts(box, monkeypatch):
    from app.agent import llm

    async def bad(*a, **k):
        raise llm.LLMError("502 bad gateway")
    monkeypatch.setattr(llm, "_openai_create", bad)
    before = llm.BREAKERS["glm"]["fails"]
    with pytest.raises(llm.LLMError):
        asyncio.run(llm.openai_create("glm", "s", [], [{"role": "user", "content": "x"}], 50))
    assert llm.BREAKERS["glm"]["fails"] == before + 1 or llm.brain_paused("glm")
    llm.BREAKERS["glm"].update({"fails": 0, "until": 0.0})


def test_a_box_part_attempt_runs_on_exactly_its_own_model(box):
    from app.agent import llm
    from app.pipeline import runner as R
    seen = []
    b = box.begin("c5", "t1", "hi")
    R.TURN_SWAP.get()["b/mid2"] = "c/mid3"                 # an earlier hand-over in this message

    def make(first):
        async def run():
            seen.append(llm.model_in_force())
            return [{"type": "text", "text": "x"}], "end_turn", {}
        return run()
    hand = _p4._hand(model="b/mid2", backups=("c/mid3",))
    asyncio.run(R.call(hand, make))
    box.end(b, "ok")
    assert seen == ["openrouter:b/mid2"]


def test_a_percent_of_hers_counts_as_one_step(box):
    from app.pipeline import check as C
    facts = [{"value": v, "source": "her"} for v in (120, 180, 60, 12, 5)]
    chk = C.final_check("Chai: 120 x 1.12 = 134.4, plus 5% GST. Margin 14.4 on chai.", "x", facts=facts, tools_ran=1)
    assert chk["ok"], chk


def test_the_sheet_print_shows_the_hand_over(box, capsys):
    from app.pipeline import runner as R, sheet as S
    sh = S.new("c6", "t1", "better answer please", [{"kind": "reason", "level": "ULTRA", "model": {"id": "a/mid1"},
                                                       "applied": True}])
    asyncio.run(R.call(_p4._hand(sheet=sh, n=1), _p4._maker({"a/mid1": _p4.boom(BANNED), "b/mid2": _p4.ok()}, [])))
    S.main()
    out = capsys.readouterr().out
    assert "hand-over (error): a/mid1 -> b/mid2" in out and "ran on b/mid2" in out and "-> a/mid1" in out


def test_version():
    src = (pathlib.Path(__file__).parents[1] / "app" / "main.py").read_text()
    assert 'APP_VERSION = "0.999.15"' in src
    # v0.976: later releases rewrote the story chain in main.py; the record of this fix lives in HISTORY
    hist = (pathlib.Path(__file__).parents[2] / "docs" / "HISTORY.md").read_text()
    assert "v0.971.0 HOOLA PIPELINE P4 FIX" in hist
