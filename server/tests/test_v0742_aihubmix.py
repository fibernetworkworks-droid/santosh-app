"""v0.742 AIHUBMIX (owner: "AIHubMix -- LETS DO IT"): AIHubMix's free models (e.g. coding-glm-5.3-flash-free, the same
GLM 5.3 Flash Hoola runs on) usable in the dropdown AND as the whole server's model (GLM_MODEL), with only its key."""
from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

FIX = Path(__file__).parent / "fixtures"
CAT = json.loads((FIX / "or_catalogue_sample.json").read_text())
SLUG = "aihubmix:coding-glm-5.3-flash-free"


@pytest.fixture()
def ah(env, monkeypatch, tmp_path):
    from app.agent import modelprofile
    from app.config import get_settings
    for k in ("GLM_API_KEY", "GLM_BASE_URL"):
        monkeypatch.delenv(k, raising=False)
    for k, v in {"MODEL_PROFILE": "true", "CHAT_MODEL_CHOICE": "true", "MODEL_PROFILE_DIR": str(tmp_path / "mp"),
                 "MODEL_CHOICE_DIR": str(tmp_path / "mc"), "CHAT_LLM": "glm", "GLM_API_KEY": "",
                 "GLM_MODEL": SLUG, "AIHUBMIX_API_KEY": "k-ahm", "CHAT_MODELS": "aihubmix:gpt-5.5-free", "GLM_IMAGES": "true"}.items():
        monkeypatch.setenv(k, v)
    get_settings.cache_clear()
    modelprofile._reset_for_tests()
    modelprofile._CAT.update(at=0.0, data=[])
    monkeypatch.setattr(modelprofile, "refresh_in_background", lambda model="": None)
    monkeypatch.setattr(httpx, "get", lambda url, headers=None, timeout=None: httpx.Response(
        200, json=CAT, request=httpx.Request("GET", url)))
    yield modelprofile
    modelprofile._reset_for_tests()
    get_settings.cache_clear()


def test_names_and_free_flag():
    from app.agent import modelprofile as mp
    from app.agent import providers as P
    assert P.split(SLUG) == ("aihubmix", "coding-glm-5.3-flash-free")
    assert P.free(SLUG) is True and P.free("aihubmix:gpt-4o") is None and P.free("groq:x") is None
    assert mp._norm("coding-glm-5.3-flash-free") == mp._norm("z-ai/glm-5.3-flash")
    assert mp._norm("gemma-4-31b-it-free") == mp._norm("google/gemma-4-31b-it")


def test_the_whole_server_runs_on_aihubmix_with_only_its_key(ah):
    from app.agent import llm
    ah.refresh(model=SLUG)
    assert llm.glm_ready() and llm.chat_brain() == "glm"
    url, model, label, h, extra = llm._target("glm")
    assert url == "https://aihubmix.com/v1/chat/completions" and model == "coding-glm-5.3-flash-free"
    assert h["Authorization"] == "Bearer k-ahm" and extra == {} and label == "AIHubMix"
    p = ah.get(SLUG)
    assert p["known"] and "image" in p["inputs"] and "tools" in p["params"]   # GLM 5.3 Flash's own abilities
    pic = [{"role": "user", "content": [{"type": "image", "source": {"type": "base64", "media_type": "image/png",
                                                                     "data": "AAAA"}}, {"type": "text", "text": "?"}]}]
    assert llm.choose(pic) == "glm"


def test_the_sdk_door_takes_it_too(ah):
    from app import glmdoor
    assert glmdoor._ready("glm") is True


def test_dropdown_shows_it_free(ah):
    from app import modelchoice as mc
    v = mc.view("default")
    by = {m["id"]: m for m in v["models"]}
    assert v["available"] and by[SLUG]["free"] is True and by[SLUG]["provider"] == "AIHubMix"
    assert by[SLUG]["default"] and by["aihubmix:gpt-5.5-free"]["free"] is True


def test_its_limit_is_said_plainly():
    from app.agent import santosh
    line = santosh._friendly_error(RuntimeError('AIHubMix error 429: {"error":"rate limit"}'))
    assert "free AIHubMix limit" in line and "something went wrong" not in line
