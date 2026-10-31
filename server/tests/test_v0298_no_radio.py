"""v0.298.0 NO RADIO (owner: "WHEN HOOLA AI INITIATES TALK, BEFORE THAT I GET A RADIO LIKE SOUND --- CHECK FIRST THEN FIX"):
the sound was v0.266's breath - when no real recorded breath was ready (every first call after a restart) the server
played a GENERATED one, band-limited noise, which on a phone sounds like radio static right before his first word."""
from pathlib import Path

from app import breath

ROOT = Path(__file__).resolve().parents[2]


def test_breath_is_off_by_default():
    from app.config import get_settings
    get_settings.cache_clear()
    assert get_settings().voice_openai_breath is False


def test_generated_noise_never_plays(monkeypatch):
    monkeypatch.setattr(breath, "_READY", [])
    monkeypatch.setattr(breath, "_BUSY", {"on": True, "done": False})
    assert breath.clips() == [] and breath.pick()[0] == b""


def test_plan_breath_does_nothing_when_off():
    from app import voice_openai
    c = voice_openai.OpenAICall.__new__(voice_openai.OpenAICall)
    c._her_s, c._breath_next, c._breathed_last = 9.0, False, False
    c._tone_now = lambda: "low"
    c._plan_breath()
    assert c._breath_next is False


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.324.0"
    assert "0.324.0+364" in (ROOT / "pubspec.yaml").read_text()
