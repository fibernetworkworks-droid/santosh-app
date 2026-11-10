"""v0.741 MORE PROVIDERS (owner: "CHECK ALL MORE FREE POWERFUL OPTION" -> "GO"): the model dropdown also lists models
from Gemini / Groq / Mistral / NVIDIA / Z.ai (each key only in .env), described from OpenRouter's public catalogue
(fixture = its real entries, 10 Nov 2026)."""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

import httpx
import pytest

from tests.test_bazar import bz  # noqa: F401
from tests.test_v0186_long_goal import gz, txt  # noqa: F401

FIX = Path(__file__).parent / "fixtures"
CAT = json.loads((FIX / "or_catalogue_sample.json").read_text())
GLM = json.loads((FIX / "or_z-ai_glm-5.3-flash.json").read_text())


@pytest.fixture()
def pv(env, monkeypatch, tmp_path):
    from app.agent import modelprofile
    from app.config import get_settings
    for k, v in {"MODEL_PROFILE": "true", "CHAT_MODEL_CHOICE": "true", "MODEL_PROFILE_DIR": str(tmp_path / "mp"),
                 "MODEL_CHOICE_DIR": str(tmp_path / "mc"), "GLM_API_KEY": "k-or", "CHAT_LLM": "glm",
                 "GLM_BASE_URL": "https://openrouter.ai/api/v1", "GLM_MODEL": "z-ai/glm-5.3-flash",
                 "GROQ_API_KEY": "k-groq", "GEMINI_CHAT_API_KEY": "k-gem", "GEMINI_API_KEY": "k-voice",
                 "CHAT_MODELS": "groq:openai/gpt-oss-120b,gemini:gemini-2.5-flash,mistral:mistral-small-latest,"
                                "nvidia/nemotron-3.5-super-vl:free,groq:acme-unknown-1b"}.items():
        monkeypatch.setenv(k, v)
    get_settings.cache_clear()
    modelprofile._reset_for_tests()
    modelprofile._CAT.update(at=0.0, data=[])
    monkeypatch.setattr(modelprofile, "refresh_in_background", lambda model="": None)

    def get(url, headers=None, timeout=None):
        if url.endswith("/api/v1/models"):
            return httpx.Response(200, json=CAT, request=httpx.Request("GET", url))
        if "/models/z-ai/glm-5.3-flash/endpoints" in url:
            return httpx.Response(200, json=GLM, request=httpx.Request("GET", url))
        return httpx.Response(404, request=httpx.Request("GET", url))
    monkeypatch.setattr(httpx, "get", get)
    yield modelprofile
    modelprofile._reset_for_tests()
    get_settings.cache_clear()


def test_split_never_mistakes_the_free_suffix():
    from app.agent import providers as P
    assert P.split("groq:openai/gpt-oss-120b") == ("groq", "openai/gpt-oss-120b")
    assert P.split("nvidia/nemotron-3.5-super-vl:free") == ("", "nvidia/nemotron-3.5-super-vl:free")
    assert P.split("gemini:gemini-2.5-flash") == ("gemini", "gemini-2.5-flash")
    assert P.split("acme:thing") == ("", "acme:thing")


def test_only_models_whose_key_is_in_env_are_listed(pv):
    from app import modelchoice as mc
    ids = mc.allowed()
    assert "groq:openai/gpt-oss-120b" in ids and "gemini:gemini-2.5-flash" in ids
    assert "mistral:mistral-small-latest" not in ids                 # no MISTRAL_API_KEY -> not offered
    assert ids[0] == "z-ai/glm-5.3-flash"


def test_described_from_the_catalogue(pv):
    for m in ("groq:openai/gpt-oss-120b", "gemini:gemini-2.5-flash", "groq:acme-unknown-1b"):
        pv.refresh(model=m)
    from app import modelchoice as mc
    by = {m["id"]: m for m in mc.view("default")["models"]}
    g = by["gemini:gemini-2.5-flash"]
    assert "image" in g["reads"] and g["tools"] is True and g["provider"] == "Google Gemini" and g["free"] is None
    o = by["groq:openai/gpt-oss-120b"]
    assert o["reads"] == ["text"] and o["tools"] is True and o["provider"] == "Groq"
    u = by["groq:acme-unknown-1b"]
    assert u["reads"] == ["text"] and u["pickable"] and u["tools"] is None     # unknown: text only, still pickable


def test_a_turn_on_groq_goes_to_groq_with_its_own_key(pv, gz, monkeypatch):  # noqa: F811
    from app import modelchoice as mc
    from app.agent import llm, santosh
    pv.refresh(model="groq:openai/gpt-oss-120b")
    mc.choose("default", "groq:openai/gpt-oss-120b")
    seen = []

    async def fake(brain, system, tools, messages, max_tokens):
        url, model, label, h, extra = llm._target(brain)
        seen.append((url, model, h["Authorization"], extra, llm.is_openrouter(), llm.glm_reads_images(brain)))
        return [txt("ok")], "end_turn", {}
    monkeypatch.setattr(llm, "_openai_create", fake)
    monkeypatch.setattr(llm, "_openai_stream", lambda brain, s, t, m, mt, *a, **k: fake(brain, s, t, m, mt))
    asyncio.run(santosh.run_turn(gz["conv"], "hello", tenant_id="default"))
    url, model, auth, extra, is_or, pics = seen[0]
    assert url == "https://api.groq.com/openai/v1/chat/completions" and model == "openai/gpt-oss-120b"
    assert auth == "Bearer k-groq" and extra == {} and is_or is False and pics is False


def test_gemini_chat_never_spends_the_voice_key(pv):
    from app.agent import llm
    llm.MODEL_NOW.set("gemini:gemini-2.5-flash")
    try:
        url, model, label, h, extra = llm._target("glm")
    finally:
        llm.MODEL_NOW.set("")
    assert url.startswith("https://generativelanguage.googleapis.com/v1beta/openai") and model == "gemini-2.5-flash"
    assert h["Authorization"] == "Bearer k-gem" and "k-voice" not in json.dumps(h)


def test_an_undescribed_other_provider_model_never_gets_pictures(pv):
    from app.agent import llm
    pv.refresh(model="groq:acme-unknown-1b")
    llm.MODEL_NOW.set("groq:acme-unknown-1b")
    try:
        assert llm.glm_reads_images("glm") is False
    finally:
        llm.MODEL_NOW.set("")


def test_the_plain_openrouter_default_is_unchanged(pv):
    from app.agent import llm
    pv.refresh(model="z-ai/glm-5.3-flash")
    url, model, label, h, extra = llm._target("glm")
    assert url == "https://openrouter.ai/api/v1/chat/completions" and model == "z-ai/glm-5.3-flash"
    assert "reasoning" in extra and h["Authorization"] == "Bearer k-or"
