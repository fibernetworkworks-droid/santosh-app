"""v0.739 MODEL PROFILE (owner: "WHY EVERY NEW MODEL NEED UPDATE IN CODE EVERY TIME --- WHY IT IS NOT GENERALIZE" ->
"GO"): the chat model's abilities are READ from OpenRouter's own model list (fixtures = real answers, 10 Nov 2026),
so a new GLM_MODEL needs no code change."""
from __future__ import annotations

import asyncio
import copy
import json
from pathlib import Path

import httpx
import pytest

FIX = Path(__file__).parent / "fixtures"
GLM = json.loads((FIX / "or_z-ai_glm-5.3-flash.json").read_text())
DS = json.loads((FIX / "or_deepseek_deepseek-chat-v3.1.json").read_text())


def _no_reasoning(d):
    d = copy.deepcopy(d)
    for e in d["data"]["endpoints"]:
        e["supported_parameters"] = [p for p in e["supported_parameters"] if "reason" not in p]
    return d


@pytest.fixture()
def mp(env, monkeypatch, tmp_path):
    from app.agent import modelprofile
    from app.config import get_settings
    for k, v in {"MODEL_PROFILE": "true", "MODEL_PROFILE_DIR": str(tmp_path / "mp"), "GLM_API_KEY": "k",
                 "GLM_BASE_URL": "https://openrouter.ai/api/v1", "GLM_MODEL": "z-ai/glm-5.3-flash",
                 "CHAT_LLM": "glm", "ANTHROPIC_API_KEY": "c", "GLM_IMAGES": "true"}.items():
        monkeypatch.setenv(k, v)
    get_settings.cache_clear()
    modelprofile._reset_for_tests()
    monkeypatch.setattr(modelprofile, "refresh_in_background", lambda model="": None)   # no thread, no network
    yield modelprofile
    modelprofile._reset_for_tests()
    get_settings.cache_clear()


def _serve(monkeypatch, answers: dict):
    """httpx.get -> the fixture for the model in the url."""
    def get(url, headers=None, timeout=None):
        for slug, data in answers.items():
            if f"/models/{slug}/endpoints" in url:
                return httpx.Response(200, json=data, request=httpx.Request("GET", url))
        return httpx.Response(404, text="no such model", request=httpx.Request("GET", url))
    monkeypatch.setattr(httpx, "get", get)


def _model(monkeypatch, slug):
    from app.config import get_settings
    monkeypatch.setenv("GLM_MODEL", slug)
    get_settings.cache_clear()


def test_parse_reads_the_real_glm_answer(mp):
    p = mp.parse("z-ai/glm-5.3-flash", GLM)
    assert p["known"] and p["inputs"] == ["image", "text", "video"]
    assert "tools" in p["params"] and "reasoning" in p["params"] and p["context"] >= 200000


def test_swapping_the_model_needs_no_code(mp, monkeypatch):
    from app.agent import llm
    _serve(monkeypatch, {"z-ai/glm-5.3-flash": GLM, "deepseek/deepseek-chat-v3.1": DS})
    mp.refresh()
    pic = [{"role": "user", "content": [{"type": "image", "source": {"type": "base64", "media_type": "image/png",
                                                                     "data": "AAAA"}}, {"type": "text", "text": "?"}]}]
    assert llm.glm_reads_images("glm") is True and llm.choose(pic) == "glm"
    _model(monkeypatch, "deepseek/deepseek-chat-v3.1")       # only .env changes
    mp.refresh()
    assert mp.summary()["inputs"] == ["text"]
    assert llm.glm_reads_images("glm") is False and llm.choose(pic) == "claude"   # pictures go where they can be read


def test_no_reasoning_field_for_a_model_that_takes_none(mp, monkeypatch):
    from app.agent import llm
    _serve(monkeypatch, {"z-ai/glm-5.3-flash": GLM, "acme/plain": _no_reasoning(DS)})
    mp.refresh()
    assert "reasoning" in llm._target("glm")[4] and llm.room(1000) > 1000
    _model(monkeypatch, "acme/plain")
    mp.refresh()
    assert llm._target("glm")[4] == {} and llm.room(1000) == 1000


def test_the_window_follows_the_model(mp, monkeypatch):
    from app.agent import context
    small = copy.deepcopy(DS)
    for e in small["data"]["endpoints"]:
        e["context_length"] = 64000
    _serve(monkeypatch, {"acme/small": small})
    _model(monkeypatch, "acme/small")
    mp.refresh()
    assert context.limit("glm") == 64000


def test_a_read_failure_keeps_the_old_behaviour(mp, monkeypatch):
    from app.agent import llm
    _serve(monkeypatch, {})
    _model(monkeypatch, "acme/unknown")
    p = mp.refresh()
    assert p["known"] is False and mp.reads("image") is None and mp.supports("reasoning") is None
    assert llm.glm_reads_images("glm") is True          # GLM_IMAGES decides, as before
    assert "reasoning" in llm._target("glm")[4]


def test_saved_on_disk_and_used_after_a_restart(mp, monkeypatch):
    _serve(monkeypatch, {"z-ai/glm-5.3-flash": GLM})
    mp.refresh()
    mp._reset_for_tests()
    _serve(monkeypatch, {})                              # the list cannot be reached after the restart
    assert mp.get()["known"] and mp.reads("image") is True


def test_learns_reasoning_is_mandatory_from_the_models_own_error(mp, monkeypatch):
    from app.agent import llm
    _serve(monkeypatch, {"acme/plain": _no_reasoning(DS)})
    _model(monkeypatch, "acme/plain")
    mp.refresh()
    seen = []

    class C:
        async def post(self, url, json=None, headers=None, **k):
            seen.append(json)
            if "reasoning" not in json:
                return httpx.Response(400, text='{"error":"Reasoning is mandatory for this endpoint"}')
            return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}, "finish_reason": "stop"}]})
    monkeypatch.setattr(llm, "_client", lambda: C())
    url, model, label, h, extra = llm._target("glm")
    asyncio.run(llm._post_with_retry(url, {"model": model, **extra}, h, label))
    assert "reasoning" not in seen[0] and "reasoning" in seen[1]
    assert mp.supports("reasoning") is True and "reasoning" in llm._target("glm")[4]   # next call sends it at once


def test_a_scanned_pdf_for_a_text_only_model_is_said_plainly(mp, monkeypatch):
    import base64
    import io
    from reportlab.pdfgen import canvas
    from app.agent import llm
    _serve(monkeypatch, {"deepseek/deepseek-chat-v3.1": DS})
    _model(monkeypatch, "deepseek/deepseek-chat-v3.1")
    mp.refresh()
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    c.showPage()
    c.save()
    parts = llm.pdf_parts({"type": "document", "source": {"type": "base64", "data": base64.b64encode(buf.getvalue()).decode()}})
    assert len(parts) == 1 and "cannot read its page pictures" in parts[0]["text"]


def test_switch_off_is_the_old_code(mp, monkeypatch):
    from app.agent import llm
    from app.config import get_settings
    _serve(monkeypatch, {"deepseek/deepseek-chat-v3.1": DS})
    _model(monkeypatch, "deepseek/deepseek-chat-v3.1")
    mp.refresh()
    monkeypatch.setenv("MODEL_PROFILE", "false")
    get_settings.cache_clear()
    assert mp.known() is False and llm.glm_reads_images("glm") is True


def test_endpoint_and_healthz(mp, monkeypatch):
    from fastapi.testclient import TestClient
    _serve(monkeypatch, {"z-ai/glm-5.3-flash": GLM})
    mp.refresh()
    c = TestClient(__import__("app.main", fromlist=["app"]).app)
    s = c.get("/api/model/profile").json()
    assert s["known"] and s["tools"] is True and "image" in s["inputs"]
    assert "image" in c.get("/healthz").json()["chat_model_reads"]
