"""v0.235 (built as v0.232) LONG JOBS PHASE C - she SEES Hoola think (fix 6 of the long-task report).

The server could stream thinking since v0.171, but the chat brain never asked Claude to think, so no Soch card could
ever appear. Now: adaptive thinking on Claude while a long job runs (chat_thinking = goal), from the FIRST call of a
clearly big ask; never switched on in the middle of a tool loop (Claude's rule); a model that refuses it is healed
once and never asked again; thinking blocks never get saved or sent to GLM. The phone gets the Soch card.
"""
import asyncio
import types
from pathlib import Path

import pytest

from tests.test_bazar import bz  # noqa: F401
from tests.test_v0186_long_goal import FakeBrain, _set_brain, gz, tu, txt  # noqa: F401

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(autouse=True)
def _think_ok():
    from app.agent import santosh as s
    keep = dict(s.THINK)
    s.THINK.update(ok=True, calls=0, refused=0)
    yield
    s.THINK.clear()
    s.THINK.update(keep)


def _st(mode):
    return types.SimpleNamespace(chat_thinking=mode)


def test_think_wanted_modes():
    from app.agent.santosh import THINK, think_wanted
    assert think_wanted(_st("goal"), True) and not think_wanted(_st("goal"), False)
    assert think_wanted(_st("on"), False)
    assert not think_wanted(_st("off"), True)
    THINK["ok"] = False                                   # refused once by this model: never again
    assert not think_wanted(_st("on"), True)


def test_never_switched_on_inside_a_tool_loop_without_thinking():
    from app.agent.santosh import _loop_ok
    assert _loop_ok([{"role": "user", "content": "namaste"}])
    plain = [{"role": "assistant", "content": [{"type": "tool_use", "id": "a", "name": "x", "input": {}}]},
             {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "a", "content": "ok"}]}]
    assert not _loop_ok(plain)
    thought = [{"role": "assistant", "content": [{"type": "thinking", "thinking": "hmm", "signature": "s"},
                                                 {"type": "tool_use", "id": "a", "name": "x", "input": {}}]},
               plain[1]]
    assert _loop_ok(thought)


def test_call_brain_asks_for_adaptive_thinking_and_heals_a_refusal():
    from app.agent import santosh as s
    from app.config import get_settings
    seen = []

    class Api:
        async def create(self, **kw):
            seen.append(dict(kw))
            if "thinking" in kw and len(seen) == 1:
                raise Exception("Error code: 400 - invalid_request_error: thinking is not supported for this model")
            return types.SimpleNamespace(content=[{"type": "text", "text": "ok"}], stop_reason="end_turn")

    client = types.SimpleNamespace(messages=Api())
    orig = s.get_client
    s.get_client = lambda: client
    try:
        hist = [{"role": "user", "content": "bada kaam"}]
        blocks, stop = asyncio.run(s._call_brain("claude", "sys", hist, get_settings(), [], None, 3000, think=True))
    finally:
        s.get_client = orig
    assert seen[0]["thinking"] == {"type": "adaptive"}
    assert "thinking" not in seen[1]                      # healed in place, the answer still came
    assert blocks[0]["text"] == "ok" and s.THINK["ok"] is False and s.THINK["refused"] == 1


def test_thinking_blocks_are_never_saved_or_sent_to_glm(gz):  # noqa: F811
    from app.agent.santosh import _no_think, _save
    from app.db import Message, session
    from sqlalchemy import select
    blocks = [{"type": "thinking", "thinking": "andar ki baat", "signature": "s"},
              {"type": "redacted_thinking", "data": "x"}, {"type": "text", "text": "Jawab"}]
    assert _no_think(blocks) == [{"type": "text", "text": "Jawab"}]
    assert _no_think("plain") == "plain"
    _save(gz["conv"], "assistant", blocks, display="Jawab")
    with session() as s:
        row = s.scalars(select(Message).where(Message.conversation_id == gz["conv"]).order_by(Message.id.desc())).first()
    assert row.content == [{"type": "text", "text": "Jawab"}]


def test_long_job_turn_thinks_short_turn_does_not(gz, monkeypatch):  # noqa: F811
    conv = gz["conv"]
    brain = _set_brain(monkeypatch, FakeBrain([([txt("Namaste!")], "end_turn"),
                                               ([txt("Plan bana raha hoon.")], "end_turn")]))
    from app.agent.santosh import run_turn
    asyncio.run(run_turn(conv, "namaste", tenant_id="default"))
    assert "thinking" not in brain.seen[-1]               # short chats stay fast
    asyncio.run(run_turn(conv, "Pehle sales data nikalo, phir report banao, phir sabko mail bhejo", tenant_id="default"))
    assert brain.seen[-1]["thinking"] == {"type": "adaptive"}   # a big ask thinks from its first call


def test_open_goal_round_thinks(gz, monkeypatch):  # noqa: F811
    from app.agent import goal
    conv = gz["conv"]
    goal.set_goal("default", conv, "Website banana", ["a", "b"], origin="owner")
    brain = _set_brain(monkeypatch, FakeBrain([([txt("Aage badh raha hoon.")], "end_turn")] * 12))
    from app.agent.santosh import run_turn
    asyncio.run(run_turn(conv, "status", tenant_id="default"))
    assert brain.seen and brain.seen[0]["thinking"] == {"type": "adaptive"}


def test_off_switch(gz, monkeypatch):  # noqa: F811
    monkeypatch.setenv("CHAT_THINKING", "off")
    from app.config import get_settings
    get_settings.cache_clear()
    try:
        brain = _set_brain(monkeypatch, FakeBrain([([txt("Theek hai.")], "end_turn")]))
        from app.agent.santosh import run_turn
        asyncio.run(run_turn(gz["conv"], "Pehle sales data nikalo, phir report banao, phir sabko mail bhejo",
                             tenant_id="default"))
        assert "thinking" not in brain.seen[0]
    finally:
        monkeypatch.delenv("CHAT_THINKING")
        get_settings.cache_clear()


def test_phone_soch_card_wiring():
    st = (ROOT / "lib/state.dart").read_text()
    assert "case 'think':" in st and "void _onThink" in st and "void _thinkFold" in st
    assert "snap?['think']" in st                          # a reload mid-thought reopens the card
    card = (ROOT / "lib/ui/think_card.dart").read_text()
    assert "Soch raha hoon" in card and "ne socha" in card
    chat = (ROOT / "lib/ui/chat_screen.dart").read_text()
    assert "ThinkCard(" in chat and "import 'think_card.dart';" in chat


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.241.0"
    assert "0.241.0+281" in (ROOT / "pubspec.yaml").read_text()
