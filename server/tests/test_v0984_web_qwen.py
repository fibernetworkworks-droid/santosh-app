"""v0.984 WEB ON QWEN (owner: "FIRST GIVE WEB DEVLOPMENT QWEN 3.8 MODEL"): every Web Studio model call - the plan
architect, art direction, every section, fixes, changes, looks, critique, translations and the name - runs on Qwen 3.8
through OpenRouter, on its own request and clock; App Sahayak / PDF jobs keep their own models; Opus is one setting
away and a failed Qwen call is never quietly moved to Opus."""
import pytest

from app.config import Settings, get_settings
from app.devsahayak import brain as DB
from app.site import ai as AI


def _st(monkeypatch, **env):
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    get_settings.cache_clear()


def _ans(text, usage=None):
    return {"choices": [{"finish_reason": "stop", "message": {"content": text}}],
            "usage": usage or {"prompt_tokens": 900, "completion_tokens": 300}}


@pytest.fixture
def qwen(monkeypatch, tmp_path):
    _st(monkeypatch, WEB_BRAIN="qwen", OPENROUTER_API_KEY="or-key", SITE_DIR=str(tmp_path / "sites"))
    seen: list = []
    answers: list = []

    def post(url, body, headers, timeout):
        seen.append(dict(url=url, body=body, headers=headers, timeout=timeout))
        a = answers.pop(0) if answers else _ans('{"ok": true}')
        if isinstance(a, Exception):
            raise a
        return a

    def no_claude(*a, **k):
        raise AssertionError("a website call reached Claude")

    monkeypatch.setattr(DB, "QWEN_POST", post)
    monkeypatch.setattr(AI, "_app_client", no_claude)
    monkeypatch.setattr(AI, "_client", no_claude)
    monkeypatch.setattr(AI.time, "sleep", lambda s: None)
    yield seen, answers
    get_settings.cache_clear()


def test_version():
    import pathlib
    from app.main import APP_VERSION
    assert APP_VERSION.startswith("0.999.122")
    assert "v0.985.0 PAGE ROOM" in (pathlib.Path(AI.__file__).parents[1] / "main.py").read_text()


def test_defaults_are_qwen_38_27b():
    f = Settings.model_fields
    assert f["web_brain"].default == "qwen"
    assert f["web_qwen_model"].default == "qwen/qwen3.8-27b"
    assert f["web_qwen_timeout_s"].default >= 180         # a big plan takes minutes, never the chat's 45 s clock
    assert f["web_qwen_fallback_claude"].default is False  # no surprise Opus bill


def test_every_web_job_goes_to_openrouter_qwen(qwen):
    seen, answers = qwen
    for kind in AI.WEB_KINDS:
        answers.append(_ans('{"kind": "%s"}' % kind))
        assert AI.ask_json("SYS", "PROMPT", 3000, kind) == {"kind": kind}
    assert len(seen) == len(AI.WEB_KINDS)
    for s in seen:
        assert s["url"] == "https://openrouter.ai/api/v1/chat/completions"
        b = s["body"]
        assert b["model"] == "qwen/qwen3.8-27b"
        assert b["messages"][0]["role"] == "system" and b["messages"][0]["content"].startswith("SYS")
        assert b["messages"][1]["content"].startswith("PROMPT")
        assert b["reasoning"]["exclude"] is True
        assert b["max_tokens"] > 3000                      # the answer plus thinking room
        assert s["headers"]["Authorization"] == "Bearer or-key"
        assert s["timeout"] >= 180
    assert seen[0]["body"]["reasoning"]["effort"] == "high"   # build
    assert AI.model_for("build") == "qwen/qwen3.8-27b"
    assert AI.label_for("build") == "Qwen 3.8 27B"


def test_app_and_pdf_jobs_keep_their_own_models(qwen, monkeypatch):
    seen, _ = qwen
    got = []
    monkeypatch.setattr(AI, "_ask_app", lambda system, prompt, mt, kind, images=None, effort="": got.append(kind) or "{}")
    for kind in ("app", "app_art", "app_code", "doc_art"):
        AI.ask("S", "P", 1000, kind)
    assert got == ["app", "app_art", "app_code", "doc_art"] and not seen
    assert AI.model_for("app") != "qwen/qwen3.8-27b"


def test_pictures_go_as_image_parts(qwen):
    seen, answers = qwen
    png = b"\x89PNG\r\n\x1a\n" + b"0" * 20
    answers.append(_ans('{"score": 8}'))
    assert AI.ask_json("S", "Judge this.", 1000, "site_critique", images=[png]) == {"score": 8}
    parts = seen[0]["body"]["messages"][1]["content"]
    assert parts[0]["type"] == "image_url" and parts[0]["image_url"]["url"].startswith("data:image/png;base64,")
    assert parts[-1]["type"] == "text"


def test_the_architect_plan_is_on_qwen_too(qwen, monkeypatch):
    seen, answers = qwen
    _st(monkeypatch, ARCHITECT_OPUS="true")
    from app.site import architect as A
    answers.append(_ans('{"pages": []}'))
    assert A._ask("ARCH", "her words", 16000, "site_art") == {"pages": []}
    assert seen and seen[0]["body"]["model"] == "qwen/qwen3.8-27b"


def test_a_refused_call_is_said_at_once_and_never_moved_to_opus(qwen):
    seen, answers = qwen
    answers.append(DB.QwenError("OpenRouter answered 402: no credit"))
    with pytest.raises(AI.AiError) as e:
        AI.ask("S", "P", 1000, "build")
    assert "Qwen 3.8 27B" in str(e.value) and "refused" in str(e.value)
    assert len(seen) == 1                                 # a refused request is not asked again


def test_a_timeout_is_tried_again(qwen):
    seen, answers = qwen
    answers.extend([TimeoutError("slow"), _ans('{"ok": 1}')])
    assert AI.ask_json("S", "P", 1000, "site_edit") == {"ok": 1}
    assert len(seen) == 2


def test_an_empty_answer_thinks_one_level_less(qwen):
    seen, answers = qwen
    answers.extend([_ans(""), _ans('{"ok": 2}')])
    assert AI.ask_json("S", "P", 1000, "site_art") == {"ok": 2}
    assert seen[0]["body"]["reasoning"]["effort"] == "high"
    assert seen[1]["body"]["reasoning"]["effort"] == "medium"


def test_fallback_to_opus_only_when_switched_on(qwen, monkeypatch):
    seen, answers = qwen
    _st(monkeypatch, WEB_QWEN_FALLBACK_CLAUDE="true", ANTHROPIC_API_KEY="sk-test")
    used = []
    monkeypatch.setattr(AI, "_ask_app", lambda system, prompt, mt, kind, images=None, effort="":
                        used.append(AI._claude_model(kind)) or "opus words")
    answers.append(DB.QwenError("OpenRouter answered 403: blocked"))
    assert AI.ask("S", "P", 1000, "build") == "opus words"
    assert used and used[0].startswith("claude-")         # the fallback asks a real Claude model, not the Qwen name


def test_a_section_streams_to_the_live_canvas(qwen, monkeypatch):
    seen, _ = qwen
    from app.site import stream as ST
    fed = []

    def stream(url, body, headers, timeout, on_text):
        seen.append(dict(url=url, body=body))
        on_text('{"html": "<section>Hi')
        return _ans('{"html": "<section>Hi</section>", "css": ""}')

    monkeypatch.setattr(DB, "QWEN_STREAM", stream)
    real_feed = ST.feed
    monkeypatch.setattr(ST, "feed", lambda text, force=False: fed.append(text) or real_feed(text, force))
    with ST.watch("site1", "home__hero", "Hero", "home"):
        out = AI.ask_json("S", "P", 2000, "build")
    assert out["html"] == "<section>Hi</section>"
    assert any("<section>Hi" in t for t in fed)


def test_claude_is_one_setting_away(monkeypatch):
    _st(monkeypatch, WEB_BRAIN="claude", OPENROUTER_API_KEY="or-key")
    try:
        assert AI.web_qwen() is False
        assert AI.model_for("build").startswith("claude-")
    finally:
        get_settings.cache_clear()


def test_no_openrouter_key_keeps_the_old_path(monkeypatch):
    _st(monkeypatch, WEB_BRAIN="qwen", OPENROUTER_API_KEY="", GLM_BASE_URL="https://example.invalid/v1")
    try:
        assert AI.web_qwen() is False
    finally:
        get_settings.cache_clear()


def test_the_studio_names_the_real_model(qwen):
    from app.site import quality as Q
    est = Q.estimate({"pages": [{"sections": ["hero", "about"]}]}, looks=0)
    assert est["model"] == "Qwen 3.8 27B" and "Qwen 3.8 27B" in est["say"]
    import pathlib
    js = (pathlib.Path(AI.__file__).parents[1] / "static" / "console")
    assert "Opus is designing" not in (js / "webstudio.js").read_text()
    b = (js / "build.js").read_text()
    assert "Opus is planning the whole site map" not in b and "|| 'Opus 5.5'" not in b
