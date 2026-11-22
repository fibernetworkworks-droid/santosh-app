"""v0.999.11 TIER WRITERS (owner: "GO BUILD THE 4 CHANGES"): each tier's chat writer is good at words AND tools -
ULTRA Claude Opus 5.5, HIGH Gemini 4 Hydrogen, MEDIUM GLM-5.3, LOW DeepSeek V4.1 Flash - and the other model of
the pair (another company) checks the draft."""
from __future__ import annotations

import pytest


@pytest.fixture()
def tz(env, monkeypatch, tmp_path):
    from app.config import get_settings
    for k, v in {"MODEL_TIER_DIR": str(tmp_path / "mt"), "GLM_API_KEY": "k", "CHAT_LLM": "glm",
                 "GLM_BASE_URL": "https://openrouter.ai/api/v1", "GLM_MODEL": "z-ai/glm-5.3-flash",
                 "MODEL_TIERS": "true"}.items():
        monkeypatch.setenv(k, v)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_the_four_writers_and_their_backups():
    from app import tiers as T
    assert T.TABLE["chat"] == {
        "ultra": ["anthropic/claude-opus-5.5", "google/gemini-4-argon"],
        "high": ["google/gemini-4-hydrogen", "openai/gpt-6.1-terra"],
        "medium": ["z-ai/glm-5.3", "deepseek/deepseek-v4.1-flash-1017"],
        "low": ["deepseek/deepseek-v4.1-flash-1017", "z-ai/glm-5.3-flash"],
    }
    assert T.model("medium", "chat") == "z-ai/glm-5.3"          # MEDIUM writes like the normal setup
    assert T.TABLE["write"]["low"][0] == "deepseek/deepseek-v4.1-flash-1017"   # never GPT-6 Luna for words
    assert T.TABLE["image_in"]["high"][0] == "google/gemini-3.8-flash"          # Flash stays HIGH's reader
    assert T.COST["low"]["reply"] == "Rs 0.1" and T.COST["high"]["reply"] == "Rs 3.2"


def test_the_writers_of_a_tier_are_that_tiers_pair(tz):
    from app.pipeline import writer as WR
    assert WR.fixed("ultra")[0] == "anthropic/claude-opus-5.5"
    assert WR.fixed("low") == ["deepseek/deepseek-v4.1-flash-1017", "z-ai/glm-5.3-flash"]


@pytest.mark.parametrize("tier,writer,checker", [
    ("ultra", "anthropic/claude-opus-5.5", "google/gemini-4-argon"),
    ("high", "google/gemini-4-hydrogen", "openai/gpt-6.1-terra"),
    ("low", "deepseek/deepseek-v4.1-flash-1017", "z-ai/glm-5.3-flash"),
])
def test_the_checker_is_the_other_company_of_her_tier(tz, tier, writer, checker):
    from app.pipeline import checkers as CK
    b = {"tier": tier, "doc": None, "sheet": {"parts": [{"ran_on": writer}]}}
    m = CK.pick_checker(b)
    assert m and m["id"] == checker


def test_a_tier_backup_that_finished_a_reply_keeps_the_chat(tz, monkeypatch):
    from app import tiers as T
    from app.pipeline import writer as WR
    tok = T.NOW.set("high")
    try:
        monkeypatch.setattr(WR, "on", lambda: True)
        monkeypatch.setattr(WR, "get", lambda conv, now=None: {"model": "google/gemini-4-hydrogen", "level": "HIGH",
                                                                  "kind": "chat"})
        put = []
        monkeypatch.setattr(WR, "_put", lambda *a, **k: put.append(a))
        line = WR.handed("c1", "openai/gpt-6.1-terra", "HIGH", "no first word")
        assert put and put[0][1] == "openai/gpt-6.1-terra" and "continues this chat" in line
    finally:
        T.NOW.reset(tok)


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.999.116"
