"""v0.999.6 PARITY FOR ONE WRITER (owner: "GO PARITY"): the parity card's one_brain rule counts only the model that
wrote her replies. A Box helper part or crew agent (team.AGENT_NOW) is a helper, the planner / checker / memory calls
are "others" - neither is a second writer. Rubric v3."""
import asyncio

from tests.test_bazar import bz  # noqa: F401
from tests.test_v0186_long_goal import gz  # noqa: F401


def _row(writer_models, helper_models=()):
    steps = [{"brain": "glm", "answered": list(writer_models), "role": "writer"}]
    steps += [{"brain": "glm", "answered": [m], "role": "helper", "agent": "a1"} for m in helper_models]
    return {"reply": "The RBI repo rate is 5.5% (rbi.org.in).", "tools": [], "ttfw_ms": 900, "ms": 3000,
            "shown": ["The RBI repo rate is 5.5% (rbi.org.in)."], "steps": steps}


def test_helpers_are_not_a_second_writer():
    from app.quality import paritycard as PC
    conv = {"id": "x", "cat": "one_tool", "turns": [{"text": "What is the repo rate?"}]}
    tr = {"turns": [_row(["z-ai/glm-5.3"], ["anthropic/claude-sonnet-4.6", "anthropic/claude-opus-4.6"])],
          "inr": 1.0, "others": ["deepseek/deepseek-v4.1-flash-1017", "anthropic/claude-haiku-5.5", "z-ai/glm-5.3"]}
    s = PC.score_conv(conv, tr)
    assert s["dims"]["one_brain"] is True
    assert s["brains"] == ["z-ai/glm-5.3"]
    assert s["helpers"] == ["anthropic/claude-opus-4.6", "anthropic/claude-sonnet-4.6"]
    assert s["others"] == ["anthropic/claude-haiku-5.5", "deepseek/deepseek-v4.1-flash-1017"]   # the writer is not "other"


def test_two_writers_still_fail_and_say_who():
    from app.quality import paritycard as PC
    conv = {"id": "x", "cat": "one_tool", "turns": [{"text": "a"}, {"text": "b"}]}
    tr = {"turns": [_row(["z-ai/glm-5.3"]), _row(["deepseek/deepseek-v4.1-flash-1017"])], "inr": 1.0}
    s = PC.score_conv(conv, tr)
    assert s["dims"]["one_brain"] is False
    assert any("written by" in m for m in s["why"]["one_brain"])


def test_a_card_saved_before_v3_reads_every_step_as_the_writer():
    from app.quality import paritycard as PC
    old = {"reply": "ok", "tools": [], "steps": [{"brain": "glm", "answered": ["a"]}, {"brain": "glm", "answered": ["b"]}]}
    assert PC._models([old], "writer") == ["a", "b"] and PC._models([old], "helper") == []


def test_the_recorder_tags_a_helper_step(monkeypatch):
    from app import usage
    from app.agent import santosh, team
    from app.quality import paritycard as PC

    async def fake(brain, system, history, settings, tools=None, live=None, max_tokens=None, think=False):
        usage.record("helper-model" if team.AGENT_NOW.get() else "writer-model", 10, 10)
        return [], "end_turn", brain
    monkeypatch.setattr(santosh, "_call_brain", fake)

    async def go():
        with PC._Recorder() as rec:
            await santosh._call_brain("glm", "", [], None)
            tok = team.AGENT_NOW.set("research-1")
            try:
                await santosh._call_brain("glm", "", [], None)
            finally:
                team.AGENT_NOW.reset(tok)
        return rec
    rec = asyncio.run(go())
    steps = [st for v in rec.steps.values() for st in v]
    assert [(st["role"], st["answered"]) for st in steps] == [("writer", ["writer-model"]),
                                                              ("helper", ["helper-model"])]
    assert steps[1]["agent"] == "research-1"


def test_a_sub_agent_runs_marked_and_the_mark_is_gone_after(gz, monkeypatch):  # noqa: F811
    from app.agent import santosh, team
    from app.config import get_settings
    seen = []

    async def think(brain, system, history, settings, tools=None, live=None, *a, **k):
        seen.append(team.AGENT_NOW.get())
        return [{"type": "text", "text": "Four Diwali offers, done."}], "end_turn", brain
    monkeypatch.setattr(santosh, "_think", think)
    out = asyncio.run(team._run_agent({"name": "offers", "task": "Brainstorm 4 offers"}, "t1", "Diwali", set(),
                                      "default", gz["conv"], "", get_settings()))
    assert out["ok"] and seen and set(seen) == {"offers"}
    assert team.AGENT_NOW.get() == ""


def test_the_card_names_the_box_writers_and_checkers(monkeypatch):
    from app.config import get_settings
    from app.quality import paritycard as PC
    st = get_settings()
    monkeypatch.setattr(st, "pipeline_on", True)
    monkeypatch.setattr(st, "pipeline_writers", "z-ai/glm-5.3,deepseek/deepseek-v4.1-flash-1017")
    monkeypatch.setattr(st, "pipeline_checkers", True)
    monkeypatch.setattr(st, "pipeline_checker_hold", True)
    line = PC.brain_line()
    assert "Box on, writers z-ai/glm-5.3,deepseek/deepseek-v4.1-flash-1017, checkers on (held until checked)" in line
    assert PC.RUBRIC_V == 3


def test_the_printed_card_lists_writers_apart_from_helpers():
    from app.quality import paritycard as PC
    conv = {"id": "x", "cat": "one_tool", "turns": [{"text": "What is the repo rate?"}]}
    s = PC.score_conv(conv, {"turns": [_row(["z-ai/glm-5.3"], ["anthropic/claude-sonnet-4.6"])], "inr": 1.0,
                             "others": ["deepseek/deepseek-v4.1-flash-1017"]})
    text = "\n".join(PC.lines(PC.summarize([s])))
    assert "writers: z-ai/glm-5.3 (more than one in 0 conversations)" in text
    assert "helpers: anthropic/claude-sonnet-4.6; planner / checker / memory: deepseek/deepseek-v4.1-flash-1017" in text


def test_the_card_turns_the_watch_holdout_off_only_while_it_runs(monkeypatch):
    from app.config import get_settings
    from app.quality import paritycard as PC
    st = get_settings()
    monkeypatch.setattr(st, "pipeline_holdout_pct", 10.0)
    seen = []

    async def rows(items, judge, tenant, progress):
        seen.append(st.pipeline_holdout_pct)
        return {"kind": "live"}
    monkeypatch.setattr(PC, "_live_rows", rows)
    asyncio.run(PC.live_card([{"id": "x", "cat": "one_tool", "turns": [{"text": "hi"}]}]))
    assert seen == [0.0] and st.pipeline_holdout_pct == 10.0
