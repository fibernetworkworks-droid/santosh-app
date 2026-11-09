"""v0.728 SAB ENGLISH (owner: "MAKE ENTIRE HOOLA IN ENGLISH - MOST IMPORTANT"): wave 1 = what she sees most - the
replies (the two language rules the model reads), the working-row step label of all 644 tools, and the voice call's
language. hoola_language=auto brings back the old 'answer in her language' behaviour."""
from __future__ import annotations

import re

import pytest


@pytest.fixture()
def en(env, monkeypatch):
    monkeypatch.setenv("HOOLA_LANGUAGE", "en")
    from app.config import get_settings
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_english_is_the_default():
    from app.config import Settings
    assert Settings.model_fields["hoola_language"].default == "en"


def test_the_system_prompt_says_english(en):
    from app.agent.prompts import system_prompt
    p = system_prompt(False, "", "default")
    assert "Always write in clear, simple English" in p
    assert "Answer in clear, simple English, whatever language she writes in" in p
    assert "If they write Hinglish in Roman letters, reply in Hinglish" not in p
    assert "Answer in the language and script SHE used" not in p


def test_auto_keeps_her_language(env, monkeypatch):
    monkeypatch.setenv("HOOLA_LANGUAGE", "auto")
    from app.config import get_settings
    get_settings.cache_clear()
    from app.agent.prompts import system_prompt
    p = system_prompt(False, "", "default")
    assert "If they write Hinglish in Roman letters, reply in Hinglish" in p
    assert "Always write in clear, simple English" not in p


def test_every_tool_label_has_english():
    from app.agent.labels_en import LABELS_EN
    from app.agent.tools import TOOL_LABELS
    assert set(TOOL_LABELS) <= set(LABELS_EN) | {"tool_search"}
    hing = re.compile(r"\b(raha|rahi|hoon|kar raha|dekh|bhej|nikal|padh|dhoondh|mein|aapk|kaam)\b", re.I)
    assert not [v for v in LABELS_EN.values() if hing.search(v)]


def test_label_follows_the_setting(en, monkeypatch):
    from app import lang
    assert lang.label("list_lead_lists") == "Checking contact lists"
    assert lang.label("some_new_tool") == "Some new tool"
    monkeypatch.setenv("HOOLA_LANGUAGE", "auto")
    from app.config import get_settings
    get_settings.cache_clear()
    assert lang.label("list_lead_lists") == "Contact lists dekh raha hoon"


def test_a_call_is_locked_to_indian_english(en):
    from app import lang
    from app.voice import persona_prompt
    assert lang.call_lang("hi-IN") == "en-IN"
    p = persona_prompt("Santosh", "m")
    assert "Speak simple, warm Indian English" in p and "Spoken Hinglish the way people really talk" not in p


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION.startswith("0.728.0")
