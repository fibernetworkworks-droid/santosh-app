"""v0.876 EK BHASHA CALL (owner: "voice call is talking in english inbetween find root cause" -> "Hinglish on calls").

Root cause: with Hoola set to English (v0.728) a call got two opposite rules - the language lock said English, but the
short / brain call scripts kept "Spoken Hinglish ... match her mix" (the English swap only matched the long script's
line), the note on every call-brain ask said "in clear simple English" so the brain answered in English and the voice
read it out, and the console always asks for an en-IN call. Now calls have ONE language: `voice_language`."""
from __future__ import annotations

import pytest

from app.config import get_settings


@pytest.fixture
def english_hoola(monkeypatch):
    monkeypatch.setenv("HOOLA_LANGUAGE", "en")
    monkeypatch.delenv("VOICE_LANGUAGE", raising=False)
    get_settings.cache_clear()
    yield monkeypatch
    get_settings.cache_clear()


def test_calls_speak_hinglish_by_default(english_hoola):
    from app import lang
    assert lang.english() is True and lang.call_english() is False
    assert lang.call_lang("en-IN") == "hi-IN" and lang.call_lang("") == "hi-IN"
    assert lang.call_lang("mr-IN") == "mr-IN"


def test_english_calls_on_request(english_hoola):
    english_hoola.setenv("VOICE_LANGUAGE", "en")
    get_settings.cache_clear()
    from app import lang
    assert lang.call_english() is True and lang.call_lang("hi-IN") == "en-IN"


@pytest.mark.parametrize("which", ["PERSONA", "PERSONA_LEAN", "PERSONA_BRAIN"])
def test_every_call_script_has_one_language(english_hoola, monkeypatch, which):
    from app import voice
    english_hoola.setenv("VOICE_LEAN_TOOLS", "true" if which != "PERSONA" else "false")
    english_hoola.setenv("VOICE_BRAIN", "true" if which == "PERSONA_BRAIN" else "false")
    get_settings.cache_clear()
    hi = voice.persona_prompt("Santosh", "m")
    assert "Spoken Hinglish" in hi and "Speak simple, warm Indian English" not in hi
    english_hoola.setenv("VOICE_LANGUAGE", "en")
    get_settings.cache_clear()
    en = voice.persona_prompt("Santosh", "m")
    assert "Spoken Hinglish" not in en and "Speak simple, warm Indian English" in en


def test_lock_matches_the_call_language(english_hoola):
    from app import voice
    cfg_hi = str(voice.live_config("", "en-IN", "", None))
    assert "RESPOND IN HINDI" in cfg_hi
    english_hoola.setenv("VOICE_LANGUAGE", "en")
    get_settings.cache_clear()
    assert "RESPOND IN ENGLISH" in str(voice.live_config("", "hi-IN", "", None))


def test_brain_note_and_brain_prompt_follow_the_call(english_hoola):
    from app import lang, voice
    from app.agent import santosh
    assert "Hinglish" in voice.brain_note() and "simple English" not in voice.brain_note()
    rule = "- Reply in the user's language and script. x asks you to."
    assert lang.apply(rule) != rule                      # a chat turn: English
    tok = santosh.VOICE_BRAIN_NOW.set(True)
    try:
        assert lang.apply(rule) == rule                  # a call turn: her language, the voice reads it aloud
    finally:
        santosh.VOICE_BRAIN_NOW.reset(tok)
    english_hoola.setenv("VOICE_LANGUAGE", "en")
    get_settings.cache_clear()
    assert voice.brain_note() == voice.BRAIN_NOTE
