"""v0.999.23 THE TIER SHEET EVERYWHERE (owner: "show the 5 tiers only --- premium sheet" -> "DONT SHOW PRICE ... REMOVE
THAT SESSION SECTION BELOW CHAT BAR" -> "PERFECT NOW CHECK EVERY CHAT SECTION TOOLS AND FEATURE DEPLOY IT EVERWHERE ---
EXPECT ..."): every chat (console + phone) offers five choices - Normal, Ultra (asks first), High, Medium, Low - with no
prices and no model list; picking one clears an older one-model pick; and every feature that calls a model through the
shared door without naming its job now runs on her tier's AI-employee row. Not moved, as she listed: the call's voice,
pictures / music / voice-over / Cinema, Hoola PC and her PC, SEO AI visibility, embeddings and the hard-ask judge."""
from __future__ import annotations

import contextvars
import inspect
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
CONSOLE = ROOT / "server/app/static/console"


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


def _run(tier, fn, *, job=None, model_now="", feature=None):
    from app import tiers as T, usage
    from app.agent import llm

    def go():
        T.NOW.set(tier)
        if model_now:
            llm.MODEL_NOW.set(model_now)
        if feature:
            usage.bind("t1", feature)
        if job is None:
            return fn()
        with T.job(job):
            return fn()
    return contextvars.copy_context().run(go)


# ------------------------------------------------------------------------------------------------ the door default
def test_a_feature_that_names_no_job_runs_on_her_tiers_employee_row(tz):
    from app import tiers as T
    for t in T.ORDER:
        assert _run(t, T.door_models) == T.models(t, "employee"), t
        assert _run(t, T.job_model) == "openrouter:" + T.models(t, "employee")[0]
    assert _run("", T.door_models) == []                                  # Normal = Hoola's own setup, as before


def test_a_named_job_still_wins_over_the_default(tz):
    from app import tiers as T
    assert _run("high", T.door_models, job="web") == T.models("high", "web")
    assert _run("high", T.door_models, job="facts") == T.models("high", "facts")


def test_what_she_kept_out_is_never_moved(tz):
    from app import tiers as T
    assert _run("ultra", T.door_models, job=T.OFF) == []                 # the hard-ask judge / a fallback
    assert _run("ultra", T.door_models, model_now="openrouter:x/y") == [] # a turn with its writer / call brain
    assert _run("ultra", T.door_models, feature="pc") == []               # Hoola PC and her PC (frozen)


def test_claude_only_calls_keep_claude(tz):
    from app import glmdoor

    def go():
        from app import tiers as T
        T.NOW.set("ultra")
        tok = glmdoor.CLAUDE_ONLY.set(True)
        try:
            return glmdoor.tier_models({"messages": [{"role": "user", "content": "x"}]})
        finally:
            glmdoor.CLAUDE_ONLY.reset(tok)
    assert contextvars.copy_context().run(go) == []


def test_a_failed_tier_call_falls_back_with_the_job_switched_off_not_cleared():
    from app import glmdoor, usage
    src = inspect.getsource(usage) + inspect.getsource(glmdoor)
    assert 'job("")' not in src                       # '' would mean "use the default" again = the same models again
    assert src.count("job(_tiers.OFF)") == 2 and src.count("job(tiers.OFF)") == 2


def test_the_hard_judge_stays_a_fixed_one_word_check():
    from app.agent import hard
    src = inspect.getsource(hard.judge)
    assert "tiers.job(tiers.OFF)" in src and "hard_judge_timeout_s" in src and "max_tokens=3" in src


# ------------------------------------------------------------------------------------------------ the route
def test_picking_a_tier_clears_an_older_one_model_pick(tz, monkeypatch):
    from app import modelchoice
    from app.main import app
    seen = []
    monkeypatch.setattr(modelchoice, "chosen", lambda tenant: "deepseek/deepseek-v4.1-flash-1017")
    monkeypatch.setattr(modelchoice, "choose", lambda tenant, m: seen.append(m) or {})
    c = TestClient(app)
    assert c.put("/api/model/tier", json={"tier": "medium"}).json()["selected"] == "medium"
    assert seen == [""]
    assert c.put("/api/model/tier", json={"tier": "ultra"}).status_code == 400   # still asks before Ultra
    assert seen == [""]


# ------------------------------------------------------------------------------------------------ the console
def test_the_console_sheet_is_five_rows_with_no_prices_and_ultra_asks_first():
    js = (CONSOLE / "v2.js").read_text()
    a = js.index("THE TIER SHEET"); b = js.index("document.addEventListener('click', e => { if (e.target.closest && e.target.closest('#modelBtn'))")
    sheet = js[a:b]
    assert "TIER_ROWS = ['', 'ultra', 'high', 'medium', 'low']" in sheet
    for name in ("'Normal'", "'Ultra'", "'High'", "'Medium'", "'Low'"):
        assert name in sheet
    assert "Recommended" in sheet and "Up to 70× credit" in sheet
    assert "Better models give better answers and use your credit faster." in sheet
    assert "Use Ultra?" in sheet and "'Not now'" in sheet and "'Use Ultra'" in sheet
    assert "confirm_ultra: id === 'ultra'" in sheet
    assert "cost" not in sheet and "rs_step" not in sheet and "/api/model/choice'" not in sheet   # no prices, no list
    assert "window.confirm" not in sheet


def test_the_session_row_under_the_chat_bar_is_gone():
    js = (CONSOLE / "v2.js").read_text()
    assert 'id="sessBtn"' not in js and '<div class="appunder" id="appUnder"><span class="ugap"></span></div>' in js
    assert 'aria-label="Quality"' in (CONSOLE / "v2.html").read_text()


def test_the_menu_can_draw_the_note_the_tag_and_the_question():
    m = (CONSOLE / "menu.js").read_text()
    assert "class=\"mnote\"" in m and "class=\"mtag" in m and "class=\"mtitle\"" in m and "class=\"macts\"" in m
    css = (CONSOLE / "v2.css").read_text()
    assert ".hmenu .mtag.warn{background:var(--warn-soft);color:var(--warn)}" in css
    assert ".hmenu.tiers .mi .mc{color:var(--pri)}" in css


# ------------------------------------------------------------------------------------------------ the phone
def test_the_phone_chip_and_sheet_are_in_every_chat():
    q = (ROOT / "lib/ui/shell/hoola_quality.dart").read_text()
    assert "['', 'ultra', 'high', 'medium', 'low']" in q and "'Quality'" in q and "Recommended" in q
    assert "modelTierSet(pick, confirmUltra: pick == 'ultra')" in q and "_askUltra(context)" in q
    assert "cost" not in q and "rs_step" not in q and "fontSize:" not in q and "Color(0x" not in q
    shell = (ROOT / "lib/ui/shell/hoola_shell.dart").read_text()
    chat = (ROOT / "lib/ui/chat/hoola_chat.dart").read_text()
    assert "HoolaQualityChip(app: app)" in shell and "HoolaQualityChip(app: app)" in chat


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.999.193"
    assert "version: 0.999.193+1188" in (ROOT / "pubspec.yaml").read_text()
