"""v0.999.15 BOX WIRING (owner: "GO FIX BOTH"): (1) her tier no longer puts its MAIN model back on a Box turn - after
a hand-over the chat's writer is the tier's backup, and the main writing while the checker (picked as 'not the
writer') was that same main meant a model checked its own reply; (2) no chat is held out of the Box any more
(pipeline_holdout_pct 0), so every chat has its fixed writer and its checker."""
from __future__ import annotations

import pytest


@pytest.fixture()
def ultra(env, monkeypatch, tmp_path):
    from app.config import get_settings
    for k, v in {"MODEL_TIER_DIR": str(tmp_path / "mt"), "GLM_API_KEY": "k", "CHAT_LLM": "glm",
                 "GLM_BASE_URL": "https://openrouter.ai/api/v1", "GLM_MODEL": "z-ai/glm-5.3-flash",
                 "MODEL_TIERS": "true"}.items():
        monkeypatch.setenv(k, v)
    get_settings.cache_clear()
    from app import tiers as T
    T.set_tier("t1", "ultra", confirm_ultra=True)
    yield
    get_settings.cache_clear()


def _run(fn):
    """Run fn in a fresh context so the contextvars never leak into other tests."""
    import contextvars
    return contextvars.copy_context().run(fn)


def test_a_box_turn_keeps_the_writer_the_box_chose(ultra):
    from app.agent import llm, santosh
    from app.pipeline import turnbox as TB, checkers as CK
    from app import tiers as T

    def turn():
        llm.MODEL_NOW.set("openrouter:google/gemini-4-argon")   # the Box: Argon keeps this chat after a hand-over
        TB.APPLIED.set(True)
        assert santosh._apply_tier("t1") == "ultra"
        assert T.NOW.get() == "ultra"                            # helpers / checker / price ceiling still know it
        writing = llm.model_in_force()
        chk = CK.pick_checker({"tier": "ultra", "doc": None,
                               "sheet": {"parts": [{"ran_on": "google/gemini-4-argon"}]}})
        return writing, chk["id"]

    writing, checker = _run(turn)
    assert writing == "openrouter:google/gemini-4-argon"       # was put back to Opus before the fix
    assert checker == "anthropic/claude-opus-5.5" and checker not in writing   # never checks its own reply


def test_a_turn_outside_the_box_still_runs_on_her_tier(ultra):
    from app.agent import llm, santosh
    from app.pipeline import turnbox as TB

    def turn():
        TB.APPLIED.set(False)
        santosh._apply_tier("t1")
        return llm.MODEL_NOW.get()

    assert _run(turn) == "openrouter:anthropic/claude-opus-5.5"


def test_no_tier_sets_nothing(env):
    from app.agent import llm, santosh

    def turn():
        return santosh._apply_tier("nobody"), llm.MODEL_NOW.get()

    assert _run(turn) == ("", "")


def test_the_turn_calls_the_tier_step_and_never_sets_the_model_itself():
    import inspect
    from app.agent import santosh
    src = inspect.getsource(santosh._run_turn)
    assert "_apply_tier(" in src and "_llm_tier.MODEL_NOW.set" not in src
    assert "APPLIED.get()" in inspect.getsource(santosh._apply_tier)


def test_no_chat_is_held_out_of_the_box_by_default(monkeypatch):
    from app.config import Settings
    monkeypatch.delenv("PIPELINE_HOLDOUT_PCT", raising=False)
    assert Settings().pipeline_holdout_pct == 0.0


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.999.92"
