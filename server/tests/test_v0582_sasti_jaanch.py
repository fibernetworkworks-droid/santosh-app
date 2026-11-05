"""v0.582 SASTI JAANCH - the owner: "TESTING IS VERY COSTY" then "SHIFT TO HAIKU AND TEST ON IT".
The quality cards can run on ONE cheap Claude model for the whole card process (`--model haiku` / QUALITY_MODEL /
vps-ops <card>_haiku) - every Claude setting a turn can reach moves with it, so a cheap run never spends Opus inside.
Her live server is untouched: only the card process's environment is set."""
import asyncio
from pathlib import Path

import pytest

from tests.test_bazar import bz  # noqa: F401
from tests.test_v0186_long_goal import FakeBrain, _set_brain, gz, txt  # noqa: F401

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def haiku(monkeypatch):
    from app.config import get_settings
    from app.quality import __main__ as Q
    for f in Q._CLAUDE_FIELDS:
        monkeypatch.delenv(f.upper(), raising=False)
    argv, model = Q.test_model(["tools", "--model", "haiku", "--fresh"])
    yield argv, model
    import os
    for f in Q._CLAUDE_FIELDS:
        os.environ.pop(f.upper(), None)
    get_settings.cache_clear()


def test_the_switch_moves_every_claude_setting_and_leaves_the_rest(haiku):
    from app.config import get_settings
    argv, model = haiku
    assert model == "claude-haiku-5-5" and argv == ["tools", "--fresh"]
    st = get_settings()
    for f in ("anthropic_model", "agent_hard_model", "cad_model", "game_model", "notebook_model", "site_model"):
        assert getattr(st, f) == "claude-haiku-5-5", f
    assert st.glm_model != "claude-haiku-5-5" and st.gemini_live_model.startswith("gemini")


def test_no_flag_changes_nothing(monkeypatch):
    from app.quality import __main__ as Q
    monkeypatch.delenv("QUALITY_MODEL", raising=False)
    assert Q.test_model(["tools"]) == (["tools"], "")


def test_a_hard_ask_on_a_haiku_card_never_reaches_opus(haiku, gz, monkeypatch):  # noqa: F811
    from app.agent.santosh import run_turn
    brain = _set_brain(monkeypatch, FakeBrain([([txt("12,000.")], "end_turn")] * 6))
    asyncio.run(run_turn(gz["conv"], "Ek dukaan ka maal 15% mehnga hua, phir 10% sasta - ab asli keemat ka kitna "
                                     "percent hai? 3 saal ke liye 8% compound interest bhi jodiye 50000 par.",
                         tenant_id="default"))
    assert brain.seen and all(kw["model"] == "claude-haiku-5-5" for kw in brain.seen)


def test_vps_ops_has_the_haiku_cards():
    y = (ROOT / ".github" / "workflows" / "vps-ops.yml").read_text()
    for j in ("tool_card_haiku", "hard_card_haiku", "long_card_try_haiku"):
        assert f"- {j}" in y
    assert "export QUALITY_MODEL=claude-haiku-5-5" in y and '${JOB%_haiku}' in y
