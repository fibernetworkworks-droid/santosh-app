"""v0.727 VAADA PAKKA (owner, screenshot: Hoola said "Now starting one fresh, simple demo-only NetMitra build." and,
asked "WHERE TO CHECK THAT", "Starting one fresh, simple demo-only NetMitra build now." - no build ever started, so no
page card: "HOW USER WILL KNOW THAT WORKING IS GOING OR NOT"). ROOT CAUSE: the v0.311 promise guard knew "I'll / let me /
kar raha hoon" but not an English line with no "I" ("Now starting...", "Starting ... now"), and it only ran in a turn
that had already used a tool - the second reply ran none."""
import asyncio

import pytest

from tests.test_bazar import bz  # noqa: F401
from tests.test_v0186_long_goal import FakeBrain, _set_brain, gz, tu, txt  # noqa: F401


@pytest.fixture(autouse=True)
def _no_plan_gate(monkeypatch):
    from app.agent import research_plan

    async def _off(*a, **k):
        return None
    monkeypatch.setattr(research_plan, "gate", _off)


@pytest.mark.parametrize("line", [
    "Both stuck builds are stopped. Now starting one fresh, simple demo-only NetMitra build.",
    "Both past builds are stopped. Starting one fresh, simple demo-only NetMitra build now.",
    "Rebuilding the dashboard now.",
    "Okay, building it.",
    "On it.",
])
def test_promises_without_i_are_caught(line):
    from app.agent import aage
    assert aage.promised(line)


@pytest.mark.parametrize("line", [
    "The NetMitra page is ready - open it from the card above.",
    "Both past builds are stopped.",
    "Should I start a fresh demo build?",
    "Starting tomorrow, the plan costs Rs 999 - want me to switch?",
])
def test_finished_answers_and_questions_are_not_promises(line):
    from app.agent import aage
    assert not aage.promised(line)


def test_a_promise_with_no_tool_at_all_is_pushed_to_do_it(gz, monkeypatch):  # noqa: F811
    """Her second message: the model answered with only the promise and ran nothing. Now it is nudged once and the
    build actually starts (here: the status tool stands in for the work)."""
    conv = gz["conv"]
    brain = _set_brain(monkeypatch, FakeBrain([
        ([txt("Both past builds are stopped. Starting one fresh, simple demo-only NetMitra build now.")], "end_turn"),
        ([tu(1, "kaam_status", q="netmitra")], "tool_use"),
        ([txt("The demo build is running - its card in the chat shows the clock and the step.")], "end_turn"),
    ]))
    from app.agent import aage
    from app.agent.santosh import run_turn
    before = aage.STATS["nudged"]
    out = asyncio.run(run_turn(conv, "WHERE TO CHECK THAT", tenant_id="default"))
    assert brain.script == [] and len(brain.seen) == 3
    assert aage.STATS["nudged"] == before + 1
    assert "card in the chat" in out


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION.startswith("0.727.0")
