"""v0.560 EK DARWAZA - the owner: "BUILD THE 3 FIXES" from the Hoola Structure Audit (claude.ai/artifact/PbsgDmh36rY1FvjyhpDU6m).

1. ONE ENGINE DOOR (agent/door.py): Game Desk, 3D (Blender), CAD, Motion, Notebook, Studio planning and Pages now
   build every Claude call the way the website / app helper already did - model from settings, adaptive thinking
   with an effort per job, room for the thinking (capped under the SDK's non-stream limit), a refusal ladder.
   CAD left the deprecated fixed `budget_tokens` thinking.
2. SKILLS REACH THE ENGINES: the top matching skill's text rides in the engine's system prompt (engines have no
   tool loop, so they cannot skill_manage read - Claude's level 2 instead).
3. ONE MODEL REGISTRY: CAD and Motion get settings (cad_model, motion_model); the Gemini text default moves from
   gemini-2.5-flash to Google's newest-Flash alias, with ONE fallback in the wrapper every Gemini call passes.
"""
import asyncio
import re
import types
from pathlib import Path

import pytest

from app.agent import door

ROOT = Path(__file__).resolve().parents[1] / "app"


@pytest.fixture(autouse=True)
def _fresh(monkeypatch):
    door._OFF.clear()
    monkeypatch.setattr(door, "skills_for", lambda text, tenant="": "")
    yield
    door._OFF.clear()


class _Client:
    def __init__(self, fail=None):
        self.seen, self.fail = [], fail
        self.messages = self

    def create(self, **kw):
        self.seen.append(kw)
        if self.fail and len(self.seen) == 1:
            raise Exception(self.fail)
        return types.SimpleNamespace(content=[types.SimpleNamespace(type="text", text="ok")], stop_reason="end_turn")


def test_the_door_builds_a_claude_style_request():
    kw = door.shape("game_code", "claude-opus-5-5", 16000, "sys", [{"role": "user", "content": "x"}])
    assert kw["thinking"] == {"type": "adaptive"} and kw["output_config"] == {"effort": "high"}
    assert kw["max_tokens"] == min(16000 + door.JOBS["game_code"][1], door.NONSTREAM_CAP)
    assert kw["max_tokens"] <= 21000
    api = door._to_api(kw)
    assert api["extra_body"]["output_config"]["effort"] == "high" and "output_config" not in api
    small = door.shape("cad_look", "m", 1500, "", [{"role": "user", "content": "x"}])
    assert "system" not in small and small["output_config"]["effort"] == "medium"


def test_thinking_can_be_switched_off(monkeypatch):
    from app.config import get_settings
    monkeypatch.setattr(get_settings(), "engine_thinking", "off", raising=False)
    kw = door.shape("notebook", "m", 4000, "s", [{"role": "user", "content": "x"}])
    assert "thinking" not in kw and kw["max_tokens"] == 4000


def test_a_refused_field_is_dropped_once_and_not_sent_again():
    c = _Client(fail="Error code: 400 - thinking is not supported for this model")
    out = door.create(c, door.shape("blender", "m", 3000, "s", [{"role": "user", "content": "x"}]))
    assert out.content[0].text == "ok" and "thinking" in c.seen[0] and "thinking" not in c.seen[1]
    assert "thinking" not in door.shape("blender", "m", 3000, "s", [{"role": "user", "content": "x"}])


def test_an_unrelated_error_is_not_swallowed():
    c = _Client(fail="Error code: 529 - overloaded")
    with pytest.raises(Exception):
        door.create(c, door.shape("cad", "m", 3000, "s", [{"role": "user", "content": "x"}]))


def test_game_desk_rides_the_door(monkeypatch):
    from app.config import get_settings
    from app.gamedesk import ai
    c = _Client()
    monkeypatch.setattr(ai, "_client", lambda: c)
    monkeypatch.setattr(get_settings(), "anthropic_api_key", "k", raising=False)
    assert ai.ask("sys", "make a runner game", max_tokens=8000, job="game_code") == "ok"
    kw = c.seen[0]
    assert kw["model"] == (get_settings().game_model or "claude-opus-5-5")
    assert kw["thinking"] == {"type": "adaptive"} and kw["extra_body"]["output_config"]["effort"] == "high"


def test_cad_left_the_deprecated_budget_and_reads_its_setting(monkeypatch):
    from app.config import get_settings
    from app.engineering import ai
    c = _Client()
    monkeypatch.setattr(ai, "_client", lambda: c)
    monkeypatch.setattr(get_settings(), "anthropic_api_key", "k", raising=False)
    ai.ask("sys", "bracket", think=True)
    kw = c.seen[0]
    assert kw["model"] == get_settings().cad_model and kw["thinking"] == {"type": "adaptive"}
    assert "budget_tokens" not in str(kw)
    assert "budget_tokens" not in (ROOT / "engineering" / "ai.py").read_text()


def test_async_engines_ride_the_door(monkeypatch):
    seen = []

    class _A:
        def __init__(self):
            self.messages = self

        async def create(self, **kw):
            seen.append(kw)
            return types.SimpleNamespace(content=[types.SimpleNamespace(type="text", text="page")], stop_reason="end_turn")
    from app.agent import santosh
    from app.config import get_settings
    monkeypatch.setattr(santosh, "get_client", lambda: _A())
    monkeypatch.setattr(get_settings(), "anthropic_api_key", "k", raising=False)
    from app import artifacts
    assert asyncio.run(artifacts._llm("sys", "a page", max_tokens=4000)) == "page"
    assert seen[0]["thinking"] == {"type": "adaptive"}


def test_no_heavy_engine_calls_the_model_around_the_door():
    """The audit's guard: these engines may only reach Claude through door.create / door.acreate."""
    for rel in ("gamedesk/ai.py", "blender3d/ai.py", "engineering/ai.py", "motion/ai.py",
                "notebook/service.py", "studio/service.py", "artifacts.py"):
        src = (ROOT / rel).read_text()
        direct = re.findall(r"(?<!door\.)\b(?:_client\(\)|client|get_client\(\))\.messages\.create\(", src)
        assert not direct, (rel, direct)
        assert "door.create(" in src or "door.acreate(" in src, rel


def test_her_skill_text_reaches_an_engine(monkeypatch):
    monkeypatch.undo()
    from app.coder import inject, store
    monkeypatch.setattr(inject, "_skills_enabled", lambda: True)
    monkeypatch.setattr(inject, "_matched", lambda tenant, q, limit=4: [{"name": "fe-ui-kit", "body": "Use saffron #FFB15C."}])
    monkeypatch.setattr(store, "skill_use_mark", lambda *a, **k: None)
    txt = door.skills_for("make the shop page in my brand colours", tenant="t1")
    assert "HER SKILL 'fe-ui-kit'" in txt and "#FFB15C" in txt
    kw = door.shape("page", "m", 2000, "base", [{"role": "user", "content": "brand page"}], tenant="t1")
    assert kw["system"].startswith("base") and "HER SKILL" in kw["system"]


def test_one_model_registry_for_gemini_text():
    from app import usage
    from app.config import Settings
    assert Settings.model_fields["youtube_gemini_model"].default == "gemini-flash-latest"
    assert usage._gemini_fallback({"model": "gemini-flash-latest"}, Exception("404 model not found")) == "gemini-2.5-flash"
    assert usage._gemini_fallback({"model": "gemini-flash-latest"}, Exception("429 quota")) == ""
    assert usage._gemini_fallback({"model": "gemini-2.5-flash"}, Exception("404 not found")) == ""
