"""v0.999.17 CODING ON HER TIER (owner: "OK FINE USE THIS MODELS FOR CODING"): every Hoola Code call follows her tier's
Hoola Code row - side-by-side agents too (they run in their own threads and lost the tier), the page names the model
that really runs (it said "Qwen 3.8 27B" on every tier), and a small code fix / a translation / the planner in the
chat follow her tier (the Box's names for those kinds were not in tiers.KIND_JOB)."""
from __future__ import annotations

import concurrent.futures as cf
import contextvars
import types

import pytest

ROW = {"ultra": "anthropic/claude-fable-5.2", "high": "openai/gpt-6.1-terra",
       "medium": "deepseek/deepseek-v4.1-flash-1017", "low": "openai/gpt-6-luna"}


@pytest.fixture()
def dev(env, monkeypatch, tmp_path):
    from app.config import get_settings
    for k, v in {"MODEL_TIER_DIR": str(tmp_path / "mt"), "MODEL_TIERS": "true", "GLM_API_KEY": "k",
                 "CHAT_LLM": "glm", "GLM_BASE_URL": "https://openrouter.ai/api/v1",
                 "GLM_MODEL": "z-ai/glm-5.3-flash", "DEV_BRAIN": "qwen"}.items():
        monkeypatch.setenv(k, v)
    get_settings.cache_clear()
    from app.devsahayak import brain as B
    seen: list[str] = []
    monkeypatch.setattr(B, "_qwen_one", lambda model, *a, **k: (seen.append(model) or ([], "end_turn")))
    yield seen
    get_settings.cache_clear()


def _call():
    from app.devsahayak import brain as B
    B._qwen_call("sys", [{"role": "user", "content": "x"}], [], 100, None)


@pytest.mark.parametrize("tier", list(ROW))
def test_the_session_and_a_side_by_side_agent_both_run_on_her_tier(dev, tier):
    from app import tiers as T
    from app.devsahayak import brain as B
    T.set_tier("t1", tier, confirm_ultra=True)
    B.session(types.SimpleNamespace(text="fix the bug", id="s1", tenant_id="t1"))
    B.PICK.model, B.PICK.effort = "", ""
    _call()
    snap = B.carry()

    def agent():                             # what subagent.run_one does in its worker thread
        B.PICK.model, B.PICK.effort = "", ""
        B.adopt(snap)
        _call()
    with cf.ThreadPoolExecutor(1) as ex:
        ex.submit(contextvars.copy_context().run, agent).result()
    assert dev[-2:] == [ROW[tier], ROW[tier]]
    assert B.shown_model("t1") == ROW[tier]


def test_agents_carry_the_session_in_the_code():
    import inspect
    from app.devsahayak import subagent as SA, engine as EN
    src = inspect.getsource(SA)
    assert "part = B.carry()" in src and "part=part" in src and "B.adopt(part)" in src
    assert "part=B.carry()" in inspect.getsource(EN)


def test_the_page_names_the_tier_model(dev):
    from app import tiers as T
    from app.devsahayak import brain as B, service as SV
    B.session(None)
    B.PICK.model = ""
    assert SV.models("t2")["forced"]["model"].startswith("Qwen")          # no tier: the server's own setting
    T.set_tier("t2", "high")
    out = SV.models("t2")
    assert out["default"] == "openai/gpt-6.1-terra" and out["forced"]["model"] == "GPT 6.1 Terra"
    assert "tier" in out["forced"]["why"]


def test_her_own_pick_in_the_session_still_wins(dev):
    from app import tiers as T
    from app.devsahayak import brain as B
    T.set_tier("t3", "ultra", confirm_ultra=True)
    B.session(types.SimpleNamespace(text="x", id="s3", tenant_id="t3"))
    B.PICK.model = "qwen/qwen3.8-max-0902"
    assert B.shown_model("t3") == "qwen/qwen3.8-max-0902"


def test_small_code_translation_and_planning_follow_her_tier():
    from app import tiers as T
    assert T.job_of("code.small") == "code" and T.job_of("translate") == "write" and T.job_of("plan") == "reason"
    assert T.models("high", T.job_of("code.small")) == T.TABLE["code"]["high"]


def test_the_coding_rows_she_chose_are_kept():
    from app import tiers as T
    assert T.TABLE["hoola_code"] == {
        "ultra": ["anthropic/claude-fable-5.2", "google/gemini-4-hydrogen"],
        "high": ["openai/gpt-6.1-terra", "anthropic/claude-sonnet-5.5"],
        "medium": ["deepseek/deepseek-v4.1-flash-1017", "qwen/qwen3.8-27b"],
        "low": ["openai/gpt-6-luna", "anthropic/claude-haiku-5.5"]}


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.999.116"
