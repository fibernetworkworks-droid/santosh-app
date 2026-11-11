"""v0.429 SOCH KE JAWAB step 2 - a hard reasoning ask runs on the strongest model with room to think (owner: "GO STEP 2").

Before: v0.272 spotted the hard ask and turned thinking on, v0.331 SOCH GEHRI raised its effort to high - but the model
stayed the chat model (Sonnet 5.5) and the call kept the chat-size 2,000 tokens, while thinking tokens count against
max_tokens (the answer got cut and stitched). Now a hard ask: agent_hard_model (Opus 5.5) for every call of that turn,
agent_hard_max_tokens 16,000, Claude even when a cheaper brain answers chat; any Opus failure retries the same call on
the chat model once (a 404 turns the switch off). Ordinary chat and long jobs are unchanged.
"""
import asyncio
import types

import pytest

from tests.test_bazar import bz  # noqa: F401
from tests.test_v0186_long_goal import FakeBrain, _set_brain, gz, txt  # noqa: F401


def test_model_for_hard_asks_only():
    from app.agent import santosh
    st = types.SimpleNamespace(agent_hard_model="claude-opus-5-5")
    assert santosh.model_for(st, hard=True, long_job=False) == "claude-opus-5-5"
    assert santosh.model_for(st, hard=True, long_job=True) == ""      # long jobs: many steps, stay on the chat model
    assert santosh.model_for(st, hard=False, long_job=False) == ""
    assert santosh.model_for(types.SimpleNamespace(agent_hard_model=""), True, False) == ""   # switched off


def test_a_hard_question_runs_on_opus_with_room_and_a_chat_does_not(gz, monkeypatch):  # noqa: F811
    conv = gz["conv"]
    brain = _set_brain(monkeypatch, FakeBrain([([txt("Namaste!")], "end_turn"),
                                               ([txt("Root 2 irrational hai, kyunki...")], "end_turn")]))
    from app.agent.santosh import run_turn
    asyncio.run(run_turn(conv, "namaste", tenant_id="default"))
    chat = brain.seen[-1]
    assert chat["model"] == "claude-sonnet-5-5" and chat["max_tokens"] == 2000 and "thinking" not in chat
    asyncio.run(run_turn(conv, "Prove that root 2 is irrational", tenant_id="default"))
    hard = brain.seen[-1]
    assert hard["model"] == "claude-opus-5-5" and hard["max_tokens"] == 16000
    assert hard["thinking"] == {"type": "adaptive"}
    assert hard.get("extra_body", {}).get("output_config", {}).get("effort") == "high"


class _Err(Exception):
    pass


def test_opus_failure_answers_on_the_chat_model(monkeypatch, env):
    from app.agent import santosh
    from app.config import get_settings
    seen = []

    async def create(**kw):
        seen.append(kw["model"])
        if kw["model"] == "claude-opus-5-5":
            raise _Err("Error code: 529 - overloaded_error")
        return types.SimpleNamespace(content=[types.SimpleNamespace(type="text", text="ok")], stop_reason="end_turn",
                                     usage=None)
    monkeypatch.setattr(santosh, "get_client", lambda: types.SimpleNamespace(messages=types.SimpleNamespace(create=create)))
    santosh.HARD_MODEL.update(ok=True, calls=0, failed=0)
    tok = santosh._MODEL_NOW.set("claude-opus-5-5")
    try:
        blocks, stop = asyncio.run(santosh._call_brain("claude", "sys", [{"role": "user", "content": "q"}],
                                                       get_settings(), tools=[]))
    finally:
        santosh._MODEL_NOW.reset(tok)
    assert seen == ["claude-opus-5-5", "claude-sonnet-5-5"] and stop == "end_turn"
    assert santosh.HARD_MODEL["ok"] is True and santosh.HARD_MODEL["failed"] == 1    # overloaded: try Opus next time


def test_unknown_model_turns_the_switch_off(monkeypatch, env):
    from app.agent import santosh
    from app.config import get_settings
    seen = []

    async def create(**kw):
        seen.append(kw["model"])
        if kw["model"] == "claude-opus-5-5":
            raise _Err("Error code: 404 - not_found_error: model: claude-opus-5-5")
        return types.SimpleNamespace(content=[types.SimpleNamespace(type="text", text="ok")], stop_reason="end_turn",
                                     usage=None)
    monkeypatch.setattr(santosh, "get_client", lambda: types.SimpleNamespace(messages=types.SimpleNamespace(create=create)))
    santosh.HARD_MODEL.update(ok=True, calls=0, failed=0)
    tok = santosh._MODEL_NOW.set("claude-opus-5-5")
    try:
        asyncio.run(santosh._call_brain("claude", "s", [{"role": "user", "content": "q"}], get_settings(), tools=[]))
        asyncio.run(santosh._call_brain("claude", "s", [{"role": "user", "content": "q"}], get_settings(), tools=[]))
    finally:
        santosh._MODEL_NOW.reset(tok)
        ok = santosh.HARD_MODEL["ok"]
        santosh.HARD_MODEL.update(ok=True, calls=0, failed=0)
    assert ok is False and seen == ["claude-opus-5-5", "claude-sonnet-5-5", "claude-sonnet-5-5"]   # asked once only


def test_switch_off_keeps_the_chat_model(gz, monkeypatch):  # noqa: F811
    from app.config import get_settings
    st = get_settings()
    st.agent_hard_model = ""
    try:
        brain = _set_brain(monkeypatch, FakeBrain([([txt("Jawab.")], "end_turn")]))
        from app.agent.santosh import run_turn
        asyncio.run(run_turn(gz["conv"], "Compare GST composition vs regular scheme and recommend", tenant_id="default"))
        assert brain.seen[-1]["model"] == "claude-sonnet-5-5" and brain.seen[-1]["max_tokens"] == 16000
    finally:
        st.agent_hard_model = "claude-opus-5-5"


def test_settings_defaults():
    from app.config import get_settings
    st = get_settings()
    assert st.agent_hard_model == "claude-opus-5-5" and st.agent_hard_max_tokens == 16000 and st.agent_hard_on_claude


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.817.0"
