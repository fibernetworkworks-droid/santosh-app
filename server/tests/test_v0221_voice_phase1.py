"""v0.221 VOICE PHASE 1 - stop the breakage (owner: 'START PHASE 1' after the voice-to-voice report).

1. Affective dialog never goes to a 3.x live model (Google's gemini-3.8-live page: 'Affective dialogue is removed
   from the API'): no lost first connect, no heal flip on an unrelated refusal.
2. Every call tool says how it runs: slow work NON_BLOCKING (he keeps talking, result at a pause, WHEN_IDLE),
   quick tools BLOCKING (the exact answer, never a guess). Kill switch voice_tool_behavior.
3. The passive call listener answers only a card that came up since her LAST turn, and one turn's words never
   combine with the next: a "haan" to his own question never approves a step card from minutes ago.
4. Voice-turn saving and the facts block run off the audio loop.
"""
import asyncio
import inspect
from datetime import timedelta

import pytest
from google.genai import types

from app import voice
from app.db import now
from tests.test_voice import _gemini_env


def test_affective_never_for_3x_live_models(env):
    assert voice.affective_allowed("gemini-3.8-live") is False
    assert voice.affective_allowed("models/gemini-3.1-flash-live-preview") is False
    assert voice.affective_allowed("gemini-2.5-flash-native-audio-preview-12-2025") is True
    cfg = voice.live_config("Puck", "hi-IN", "", None)          # default model = gemini-3.8-live
    assert cfg.enable_affective_dialog is None


def test_generic_refusal_on_3x_never_flips_affective(env):
    src = inspect.getsource(voice.Call.run)
    # both heal sites are gated on the model: a 1007 on 3.8 is about something else and climbs the ladder
    assert src.count("voice_affective and affective_allowed()") == 2


def _decl(cfg, name):
    for d in cfg.tools[0].function_declarations:
        if d.name == name:
            return d
    raise AssertionError(name)


def test_slow_tools_non_blocking_quick_tools_blocking(env):
    cfg = voice.live_config("Puck", "hi-IN", "", None,
                            extra_tools=[{"name": "mcp_kite__quote", "description": "x",
                                          "input_schema": {"type": "object"}}])
    for slow in ("santosh_kaam", "browse_web", "pc_do", "google_search", "email_check", "mcp_kite__quote"):
        assert _decl(cfg, slow).behavior == types.Behavior.NON_BLOCKING, slow
    for quick in ("create_reminder", "haan_karo", "side_talk", "get_weather", "list_add", "set_phone_alarm"):
        assert _decl(cfg, quick).behavior == types.Behavior.BLOCKING, quick


def test_behavior_kill_switch(env, monkeypatch):
    _gemini_env(monkeypatch, VOICE_TOOL_BEHAVIOR="false")
    cfg = voice.live_config("Puck", "hi-IN", "", None)
    assert all(d.behavior is None for d in cfg.tools[0].function_declarations)


def test_every_slow_name_is_spelled_like_a_real_tool():
    from app.agent.tools import TOOLS
    real = {t["name"] for t in TOOLS} | {"santosh_kaam", "side_talk"}
    assert voice.SLOW_TOOLS - real == set()


class _Sess:
    def __init__(self):
        self.sent = []

    async def send_tool_response(self, function_responses):
        self.sent.extend(function_responses)


class _FC:
    def __init__(self, i, name):
        self.id, self.name = i, name


def _call(env):
    return voice.Call(None, "conv1", "Puck", "hi-IN", env["settings"].tenant_id)


def test_scheduling_only_for_non_blocking_results(env):
    async def go():
        c = _call(env)
        s = _Sess()
        await c._answer_tool(s, _FC("a", "browse_web"), "browse_web", {"ok": True}, "done")
        await c._answer_tool(s, _FC("b", "create_reminder"), "create_reminder", {"ok": True}, "done")
        return s.sent
    sent = asyncio.run(go())
    assert sent[0].scheduling == types.FunctionResponseScheduling.WHEN_IDLE
    assert sent[1].scheduling is None


def test_passive_listener_answers_only_cards_since_her_last_turn(env, monkeypatch):
    from app.bazar import service
    seen = []
    monkeypatch.setattr(service, "voice_approve",
                        lambda t, conv, text, pure, src, since=None: seen.append(since) or None)

    async def go():
        c = _call(env)
        start = c._appr_since
        assert start is not None and abs((now() - start).total_seconds()) < 5   # the call's own start
        await c._approval_listen("haan karo")
        assert seen[-1] == start
        c.user_buf = "haan chai bana do"
        await c.finish_turn()
        assert c._appr_heard == ""                     # one turn's words never carry into the next
        assert c._appr_since > start                   # next voice answer only for a card newer than this turn
        await c._approval_listen("haan")
        assert seen[-1] == c._appr_since
    asyncio.run(go())


def test_voice_pending_since_filters_older_cards(env):
    from app.bazar.db import Approval, Task
    from app.bazar.service import ensure_user, voice_pending
    from app.db import Conversation, session
    t = env["settings"].tenant_id
    with session() as s:
        conv = Conversation(tenant_id=t)
        s.add(conv)
        s.flush()
        u = ensure_user(s, t)
        task = Task(user_id=u.id, text="x", conversation_id=conv.id)
        s.add(task)
        s.flush()
        ap = Approval(task_id=task.id, user_id=u.id, tier=2, title="Aapka PC: next dabaun?", amount_paise=0,
                      conversation_id=conv.id, action={"executor": "pcop"}, items=[])
        s.add(ap)
        s.flush()
        ap.created_at = now() - timedelta(minutes=3)
        cid = conv.id
    assert len(voice_pending(t, cid)) == 1                                   # haan_karo / chat: unchanged
    assert len(voice_pending(t, cid, now() - timedelta(minutes=5))) == 1     # card came after her last turn
    assert voice_pending(t, cid, now() - timedelta(minutes=1)) == []         # card older than her last turn


def test_db_work_off_the_audio_loop():
    src = inspect.getsource(voice.Call)
    assert "await asyncio.to_thread(_save_turn" in src
    assert "await asyncio.to_thread(life.context_block" in src


def test_persona_teaches_slow_tools_and_still_formats(env):
    assert "Slow tools" in voice.PERSONA and "never guess or invent it" in voice.PERSONA
    voice.persona_prompt("Santosh", "f").format(lang="Hinglish", now="x", context="y")


def test_version():
    from app import main
    assert main.APP_VERSION == "0.224.0"
