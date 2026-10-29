"""v0.185.2 the voicecheck X-ray learned the real call loop's affective heal.

The live VPS answer (26 Oct): EVERY voicecheck rung — including bare no_tools — failed with the same
generic "1007 invalid argument", because the instrument built every config WITH enable_affective_dialog
on and never retried without it, so it reported "nothing works / model-key-Google" for what was really
just the affective field being refused. Now a generic setup refusal while affective is on drops it
(process-wide, exactly like voice.py's call loop) and retries the same rung; the report says which.
"""
import asyncio
import contextlib

import pytest
from google.genai import types

from app import voice
from tests.test_voice import _gemini_env, _msg


import pytest as _pytest


@_pytest.fixture(autouse=True)
def _older_live_model(monkeypatch):
    """v0.221 gemini-3.8-live dropped affective dialog (Hoola never sends it to 3.x); these heal paths are for
    older native-audio models that still take the field, so they pin one."""
    from app.config import get_settings
    monkeypatch.setenv("GEMINI_LIVE_MODEL", "gemini-2.5-flash-native-audio-preview-12-2025")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


BAD = "1007 None. Request contains an invalid argument."


def _audio(text="Haan, boliye."):
    return _msg(model_turn=types.Content(parts=[types.Part(inline_data=types.Blob(
        data=b"\x01\x00" * 80, mime_type="audio/pcm;rate=24000"))]),
        output_transcription=types.Transcription(text=text))


@pytest.fixture(autouse=True)
def _fresh():
    voice.SETUP.update(step=0, key="", at=0.0, refusals=0, healed=0, loaded=False)
    voice.QUIET.update(client_content=None, queued=0, live=0, sent=0, learned_off=0)
    voice.UNSUPPORTED.clear()
    yield
    voice.SETUP.update(step=0, key="", at=0.0, loaded=False)
    voice.QUIET.update(client_content=None)
    voice._AFFECTIVE["ok"] = True
    voice.UNSUPPORTED.clear()
    # remember_setup() persists data/voice_setup.json on disk - tests that walk the ladder must not
    # poison later suites (this file leaking into test_voice/test_v0181 is what broke the sweep once)
    with contextlib.suppress(Exception):
        voice._setup_file().unlink(missing_ok=True)


class _Live:
    """Answers one line, or refuses the connect per `refuse(config)`."""

    def __init__(self, config, refuse):
        if refuse(config):
            raise Exception(BAD)

    async def send_realtime_input(self, **_):
        pass

    async def send_client_content(self, **_):
        pass

    async def receive(self):
        yield _audio()
        yield _msg(turn_complete=True)


def _connect(refuse, seen):
    @contextlib.asynccontextmanager
    async def connect(config):
        seen.append(config)
        yield _Live(config, refuse)
    return connect


def test_voicecheck_names_affective_as_the_cause(env, monkeypatch):
    """THE live VPS shape: only the affective field is refused. The instrument must heal like the call loop
    (drop once, retry the same rung), report works_at=0, and SAY the exact root cause."""
    from app import voicecheck
    _gemini_env(monkeypatch)
    seen = []

    def refuse(config):
        return config.enable_affective_dialog is True

    monkeypatch.setattr(voice, "connector", _connect(refuse, seen))
    monkeypatch.setattr(voice, "_AFFECTIVE", {"ok": True})
    res = asyncio.run(voicecheck.run())
    assert res["works_at"] == 0 and res["affective"]["refused"] is True
    assert res["steps"][0]["ok"] is True and res["steps"][0]["without_affective"] is True
    assert seen[0].enable_affective_dialog is True and seen[1].enable_affective_dialog is None
    assert voice._AFFECTIVE["ok"] is False
    assert "enable_affective_dialog" in res["say"] and "poori call setup" in res["say"]


def test_voicecheck_total_failure_says_model_or_key(env, monkeypatch):
    """With affective already dropped and EVERY rung still refusing, the verdict must say bina-affective-bhi
    and point at the model name / key (the GEMINI_LIVE_MODEL test line) instead of mumbling."""
    from app import voicecheck
    _gemini_env(monkeypatch)
    seen = []

    def refuse(_config):
        return True

    monkeypatch.setattr(voice, "connector", _connect(refuse, seen))
    monkeypatch.setattr(voice, "_AFFECTIVE", {"ok": True})
    res = asyncio.run(voicecheck.run())
    assert res["works_at"] is None
    assert len(res["steps"]) == 7                      # full + 6 rungs, all refused
    assert res["steps"][0]["without_affective"] is True  # the one heal-retry happened on the full setup
    assert all(s["ok"] is False for s in res["steps"])
    assert "bina affective ke BHI" in res["say"] and "GEMINI_LIVE_MODEL" in res["say"]


def test_voicecheck_rung_refusal_still_reports_the_tool(env, monkeypatch):
    """Both troubles at once: affective refused AND a bad tool (maps_search). The instrument must walk the
    ladder (affective already off), stop at core_tools, bisect to maps_search, and say both."""
    from app import voicecheck
    _gemini_env(monkeypatch)
    seen = []

    def refuse(config):
        names = {d.name for d in (config.tools[0].function_declarations if config.tools else [])}
        return config.enable_affective_dialog is True or "maps_search" in names

    monkeypatch.setattr(voice, "connector", _connect(refuse, seen))
    monkeypatch.setattr(voice, "_AFFECTIVE", {"ok": True})
    res = asyncio.run(voicecheck.run())
    assert res["works_at"] == 5                        # 'without mcp, vocab, langcodes, compression, core_tools'
    assert res["refused_part"] == "core_tools" and res["culprit"] == "tool maps_search"
    assert res["affective"]["refused"] is True
    assert res["steps"][0]["without_affective"] is True
    assert "enable_affective_dialog" in res["say"] and "maps_search" in res["say"]
