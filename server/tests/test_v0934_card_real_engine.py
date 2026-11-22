"""v0.934 HOOLA CODE WAVE 3 (owner: "GO WAVE 3"): the coding card runs THE engine her Hoola Code sessions use (a real
working copy, Claude Code's tools, bash in the locked box), not the older 8-tool loop - so its score measures what
she gets. Qwen and Claude can be scored on the same jobs (--brain)."""
from pathlib import Path

import pytest

from tests.test_v0787_hoola_code_engine import FakeClient, tu

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def eng(monkeypatch, tmp_path):
    from app.config import get_settings
    from app.devlab import box
    from app.devsahayak import brain as B
    monkeypatch.chdir(tmp_path)                       # the working copies land in the test's own folder
    for k, v in {"DEV_WORKSPACE": "true", "DEV_BRAIN": "claude", "DEV_CLAUDE": "true", "DEV_MEMORY": "false",
                 "DEV_REALITY_CHECK": "false", "DEV_ECC_GATE": "false", "ANTHROPIC_API_KEY": "x"}.items():
        monkeypatch.setenv(k, v)
    get_settings.cache_clear()
    monkeypatch.setattr(box, "available", lambda: {"ok": True, "base_built": True, "base_stale": False})
    from app.devlab import service as LS
    monkeypatch.setattr(LS, "spec_for", lambda *a, **k: {"setup": "", "test": "", "confirm": False, "deps_key": ""})
    yield B
    B.CLIENT = None
    get_settings.cache_clear()


def test_a_card_job_runs_through_the_real_engine(eng):
    from app.devsahayak import engine as EN
    from app.quality import code_tasks as T
    from app.quality import codecard as K
    task = next(t for t in T.TASKS if t["id"] == "fix_empty_average")
    sol = task["solution"]
    turns = [[tu(1, "read", path=p)] for p in sol] + \
            [[tu(10 + i, "write", path=p, content=c)] for i, (p, c) in enumerate(sol.items())] + \
            [[tu(30, "done", explain="average() returns 0.0 for an empty list now", pr_title="Fix empty average")]]
    eng.CLIENT = FakeClient(turns)
    row = K.run_task_engine(task)
    assert row["right"], row
    assert row["steps"] == len(turns)
    sys_prompt = eng.CLIENT.calls[0]["system"][0]["text"]
    assert "REAL working copy" in sys_prompt                         # the engine's own prompt, not the old loop's
    assert not EN.LOCAL_FILES and not any(Path("data/devsahayak/ws").glob("card-*"))   # nothing left behind


def test_a_job_that_cannot_run_is_one_honest_row(eng, monkeypatch):
    from app.devsahayak import engine as EN
    from app.quality import code_tasks as T
    from app.quality import codecard as K

    def boom(*a, **k):
        raise EN.Unavailable("no box")
    monkeypatch.setattr(EN, "run", boom)
    row = K.run_task_engine(T.TASKS[0])
    assert row["right"] is False and "engine error: Unavailable: no box" in row["why"][0]


def test_the_card_refuses_to_pretend_without_the_box(monkeypatch):
    from app.devlab import box
    from app.quality import codecard as K
    monkeypatch.setattr(box, "available", lambda: {"ok": False, "why": "docker nahi hai"})
    with pytest.raises(RuntimeError, match="real engine cannot run here"):
        K.card(only=["fix_empty_average"], engine=True)


def test_cli_and_vps_jobs():
    cli = (ROOT / "server/app/quality/__main__.py").read_text()
    assert '"--engine" in argv' in cli and 'os.environ["DEV_BRAIN"] = brain' in cli and 'os.environ["DEV_MEMORY"] = "false"' in cli
    ops = (ROOT / ".github/workflows/vps-ops.yml").read_text()
    for job in ("code_card_engine)", "code_card_engine_hard)", "code_card_engine_claude)"):
        assert job in ops
    assert "code --engine --brain claude" in ops and "timeout-minutes: 50" in ops
    lines = __import__("app.quality.codecard", fromlist=["lines"]).lines(
        {"set": 1, "engine": "workspace", "model": "qwen/qwen3.8-27b", "jobs": 1, "right": 1, "works": 1, "scope": 1,
         "rules": 1, "tests": 0, "tests_of": 0, "proves": 0, "proves_of": 0, "steps_avg": 5, "bash_avg": 2, "minutes": 1,
         "rows": []})
    assert "on the real engine" in lines[0] and "2 box commands a job" in lines[1]


def test_version():
    main = (ROOT / "server/app/main.py").read_text()
    assert 'APP_VERSION = "0.999.138"' in main
    assert "version: 0.999.138+1133" in (ROOT / "pubspec.yaml").read_text()
