"""v0.622 SAHI SAMAY (owner: "CHECK THE EXACT LOGS - WHY SETTING REMINDER HAVING ISSUE").

Her live call, 6 Nov 06:17-06:19 UTC: "do minute baad" -> refused twice ("time past ka hai"), once saved 9 s ahead;
"paanch minute baad" -> saved 2 minutes ahead. The call model was working out the clock time itself. Now a relative
ask goes as in_minutes and the SERVER counts it from its own exact clock.
"""
from __future__ import annotations

import asyncio
from datetime import timedelta

import pytest

from app.agent.tools import Ctx
from app.db import Conversation, Reminder, now, session


def _ctx():
    with session() as s:
        s.add(Conversation(id="conv_t", tenant_id="default"))
    return Ctx(tenant_id="default", conversation_id="conv_t")


def test_in_minutes_counts_from_the_server_clock(env):
    from app.agent import life_tools
    ctx = _ctx()
    before = now()
    out = asyncio.run(life_tools.create_reminder(ctx, text="Paani peena hai", in_minutes=2))
    with session() as s:
        r = s.get(Reminder, out["id"])
        gap = (r.due_at.replace(tzinfo=before.tzinfo) - before).total_seconds()
    assert 119 <= gap <= 125                                  # exactly two minutes, not 9 seconds


def test_five_minutes_is_five_and_strings_work(env):
    from app.agent import life_tools
    ctx = _ctx()
    out = asyncio.run(life_tools.create_reminder(ctx, text="chai", in_minutes="5"))
    with session() as s:
        r = s.get(Reminder, out["id"])
        gap = (r.due_at.replace(tzinfo=now().tzinfo) - now()).total_seconds()
    assert 290 <= gap <= 301


def test_a_past_clock_time_tells_the_model_the_way_out(env):
    from app.agent import life_tools
    from app.agent.tools import ToolError
    ctx = _ctx()
    with pytest.raises(ToolError, match="in_minutes"):
        asyncio.run(life_tools.create_reminder(ctx, text="x", when="2020-01-01T09:00"))
    with pytest.raises(ToolError):
        asyncio.run(life_tools.create_reminder(ctx, text="x"))
    with pytest.raises(ToolError):
        asyncio.run(life_tools.create_reminder(ctx, text="x", in_minutes=0))


def test_clock_time_still_works(env):
    from app.agent import life_tools
    ctx = _ctx()
    when = (now() + timedelta(days=1)).astimezone().strftime("%Y-%m-%dT09:00")
    out = asyncio.run(life_tools.create_reminder(ctx, text="dawai", when=when))
    assert out["status"] == "active"


def test_the_call_and_the_chat_are_told_to_use_in_minutes():
    from app import voice
    from app.agent import life_tools
    spec = next(t for t in life_tools.LIFE_TOOLS if t["name"] == "create_reminder")
    assert "in_minutes" in spec["input_schema"]["properties"] and spec["input_schema"]["required"] == ["text"]
    assert "ALWAYS in_minutes" in spec["description"]
    assert "create_reminder in_minutes=X" in voice.PERSONA


def test_every_call_is_on_gemini_even_if_she_had_picked_real_voice(env, monkeypatch):
    from app import voiceengine
    from app.config import Settings, get_settings
    assert Settings.model_fields["voice_openai_enabled"].default is False   # the production default
    monkeypatch.setenv("VOICE_OPENAI_ENABLED", "false")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    get_settings.cache_clear()
    monkeypatch.setattr(voiceengine, "chosen", lambda t: "openai")
    assert voiceengine.pick("default") == ("gemini", "")


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.777.0"
