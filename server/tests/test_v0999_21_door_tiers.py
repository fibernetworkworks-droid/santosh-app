"""v0.999.21 THE DOOR FOLLOWS HER TIER (owner: "GO BUILD IT" after "IS CODE ROW IS GOOD FOR THIS TASKS"): every
Claude-style call goes through one shared door; a feature now names its kind of work there and the door asks her
tier's model for it on OpenRouter (backup next, today's path when both fail): App Studio, Game Desk, CAD, Blender,
motion, pages, Hoola Design = building (the Web Studio's row); the notebook + the video storyboard = writing; the
research engine = research; memory (facts, compaction, About me, the coder observer) = facts. No tier = as before."""
from __future__ import annotations

import asyncio
import inspect

import pytest


@pytest.fixture()
def tz(env, monkeypatch, tmp_path):
    from app.config import get_settings
    for k, v in {"MODEL_TIER_DIR": str(tmp_path / "mt"), "MODEL_TIERS": "true", "GLM_API_KEY": "k",
                 "CHAT_LLM": "glm", "GLM_BASE_URL": "https://openrouter.ai/api/v1",
                 "GLM_MODEL": "z-ai/glm-5.3-flash"}.items():
        monkeypatch.setenv(k, v)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


class _R:
    def __init__(self, model):
        self.status_code = 200
        self._m = model

    def json(self):
        return {"id": "x", "model": self._m, "usage": {"prompt_tokens": 5, "completion_tokens": 2},
                "choices": [{"message": {"role": "assistant", "content": "done"}, "finish_reason": "stop"}]}


def _fake_post(seen, fail=()):
    async def post(url, body, headers, label, *a, **k):
        seen.append((url, body["model"]))
        if body["model"] in fail:
            raise RuntimeError(f"{body['model']} refused")
        return _R(body["model"])
    return post


def _in(tier, job, fn):
    import contextvars
    from app import tiers as T

    def run():
        T.NOW.set(tier)
        with T.job(job):
            return fn()
    return contextvars.copy_context().run(run)


def test_each_engine_call_names_its_job_and_the_api_never_sees_it():
    from app.agent import door
    for job, want in (("cad", "web"), ("game_code", "web"), ("blender", "web"), ("page", "web"),
                      ("notebook", "write"), ("studio_plan", "write")):
        kw = door.shape(job, "claude-opus-5-5", 100, "s", [{"role": "user", "content": "x"}], skills=False)
        assert kw["_tier_job"] == want and "_tier_job" not in door._to_api(kw)
    assert "_tier_job" not in door.shape("other", "m", 10, "", [], skills=False)


def test_the_door_call_runs_inside_its_job():
    from app.agent import door
    from app import tiers as T
    seen = {}

    class C:
        class messages:
            @staticmethod
            def create(**kw):
                seen["job"], seen["kw"] = T.JOB.get(), kw
                return "ok"
    kw = door.shape("cad", "claude-opus-5-5", 100, "s", [{"role": "user", "content": "x"}], skills=False)
    assert door.create(C, kw) == "ok" and seen["job"] == "web" and "_tier_job" not in seen["kw"]
    assert T.JOB.get() == ""


def test_her_tier_names_the_model_for_the_job(tz):
    from app.agent import llm
    assert _in("ultra", "web", lambda: llm.model_in_force()) == "openrouter:anthropic/claude-opus-5.5"
    assert _in("low", "web", lambda: llm.model_in_force()) == "openrouter:deepseek/deepseek-v4.1-flash-1017"
    assert _in("high", "research", lambda: llm.model_in_force()) == "openrouter:qwen/qwen3.8-max-0902"
    assert _in("medium", "facts", lambda: llm.model_in_force()) == "openrouter:xiaomi/mimo-v2.6-flash"
    assert _in("", "web", lambda: llm.model_in_force()) == "z-ai/glm-5.3-flash"        # no tier: as before
    # v0.999.23 no job named = her tier's AI-employee row (was: as before)
    assert _in("ultra", "", lambda: llm.model_in_force()) == "openrouter:anthropic/claude-fable-5.2"


def test_a_picture_skips_a_text_only_model(tz):
    from app import tiers as T
    assert _in("medium", "write", lambda: T.door_models(media=True)) == ["deepseek/deepseek-v4.1-flash-1017"]
    assert _in("medium", "write", lambda: T.door_models())[0] == "z-ai/glm-5.3"


def test_a_call_that_must_be_claude_keeps_claude(tz):
    from app import glmdoor
    tok = glmdoor.CLAUDE_ONLY.set(True)
    try:
        assert _in("ultra", "web", lambda: glmdoor.tier_models({"messages": []})) == []
    finally:
        glmdoor.CLAUDE_ONLY.reset(tok)


def test_the_main_then_the_backup_on_openrouter(tz, monkeypatch):
    from app import glmdoor
    from app.agent import llm
    seen = []
    monkeypatch.setattr(llm, "_post_with_retry", _fake_post(seen, fail={"anthropic/claude-opus-5.5"}))
    kw = {"model": "claude-opus-5-5", "max_tokens": 50, "messages": [{"role": "user", "content": "build"}]}
    msg = _in("ultra", "web", lambda: asyncio.run(glmdoor.tier_acreate(kw, glmdoor.tier_models(kw))))
    assert [m for _, m in seen] == ["anthropic/claude-opus-5.5", "openai/gpt-6.1-sol"]
    assert all("openrouter.ai" in u for u, _ in seen) and msg.content[0].text == "done"


def test_through_the_real_sdk_door(tz, monkeypatch):
    """The Anthropic SDK call every engine makes, intercepted by the shared door, lands on her tier's model."""
    import anthropic
    from app import usage
    from app.agent import llm
    usage.install()
    seen = []
    monkeypatch.setattr(llm, "_post_with_retry", _fake_post(seen))

    async def call():
        c = anthropic.AsyncAnthropic(api_key="sk-test")
        return await c.messages.create(model="claude-opus-5-5", max_tokens=50,
                                       messages=[{"role": "user", "content": "make the CAD part"}])
    msg = _in("high", "web", lambda: asyncio.run(call()))
    assert seen and seen[-1][1] == "anthropic/claude-sonnet-5.5" and msg.content[0].text == "done"


def test_both_tier_models_failing_go_the_old_way_with_the_job_cleared(tz, monkeypatch):
    import anthropic
    from app import usage, glmdoor
    from app.agent import llm
    from app import tiers as T
    usage.install()
    seen = []
    monkeypatch.setattr(llm, "_post_with_retry", _fake_post(seen, fail={"anthropic/claude-sonnet-5.5", "qwen/qwen4-max"}))
    old = {}

    async def fake_old(kw):
        old["job"] = T.JOB.get()
        return "old way"
    monkeypatch.setattr(glmdoor, "active", lambda: True)
    monkeypatch.setattr(glmdoor, "acreate", fake_old)

    async def call():
        c = anthropic.AsyncAnthropic(api_key="sk-test")
        return await c.messages.create(model="claude-opus-5-5", max_tokens=50, messages=[{"role": "user", "content": "x"}])
    assert _in("high", "web", lambda: asyncio.run(call())) == "old way"
    assert [m for _, m in seen] == ["anthropic/claude-sonnet-5.5", "qwen/qwen4-max"] and old["job"] == T.OFF   # v0.999.23


def test_no_tier_changes_nothing(tz, monkeypatch):
    from app import glmdoor
    assert _in("", "web", lambda: glmdoor.tier_models({"messages": []})) == []


@pytest.mark.parametrize("kind,want", [("app", "web"), ("app_art", "web"), ("build", "web"), ("doc_art", "web"),
                                       ("seo_plan", "write"), ("social_plan", "write")])
def test_app_studio_and_pdf_design_name_their_job(monkeypatch, kind, want):
    from app.site import ai
    from app import tiers as T
    got = {}
    monkeypatch.setattr(ai, "_ask_app_on", lambda *a, **k: got.setdefault("job", T.JOB.get()) and "ok")
    ai._ask_app("s", "p", 10, kind)
    assert got["job"] == want and T.JOB.get() == ""


def test_memory_and_research_name_their_job(monkeypatch):
    from app.agent import compact
    from app.coder import observer
    from app import yaad, tiers as T
    got = []

    async def rec(*a, **k):
        got.append(T.JOB.get())
        return ("", "")
    monkeypatch.setattr(compact, "_model_on", rec)
    monkeypatch.setattr(observer, "_call_brain_on", rec)
    monkeypatch.setattr(yaad, "_ask_on", rec)
    asyncio.run(compact._model("s", "t", None, 100))
    asyncio.run(observer._call_brain("s", "u", None))
    asyncio.run(yaad._ask("s", "t"))
    assert got == ["facts", "facts", "facts"]
    from app.agent import research_tools
    assert 'with _tiers.job("research")' in inspect.getsource(research_tools)


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.999.159"
