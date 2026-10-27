"""v0.140 App Sahayak designs and builds with Claude Opus 5.5 (owner: "USE OPUS 5.5 FOR APP DEVELOPMENT AND DESIGN").
Every design / screen / fix / change / Kotlin call goes to settings.app_model; busy Opus is tried again; nothing falls
back to another model unless APP_MODEL_FALLBACK is switched on; an Android build stops instead of shipping model-less screens."""
import types

import pytest


class _Busy(Exception):
    status_code = 529


class _Gone(Exception):
    status_code = 404


def _client(script, seen, kws=None):
    class Msgs:
        def create(self, **kw):
            seen.append(kw["model"])
            if kws is not None:
                kws.append(kw)
            step = script.pop(0)
            if isinstance(step, Exception):
                raise step
            return types.SimpleNamespace(content=[types.SimpleNamespace(text=step)])
    return types.SimpleNamespace(messages=Msgs())


@pytest.fixture
def opus(env, monkeypatch):
    from app.config import get_settings
    from app.site import ai as SA
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-not-real")
    get_settings.cache_clear()
    monkeypatch.setattr(SA.time, "sleep", lambda s: None)
    for k in SA.STATS:
        SA.STATS[k] = 0
    return SA


def test_every_app_call_is_opus_and_busy_is_retried(opus, monkeypatch):
    SA = opus
    assert SA.app_model() == "claude-opus-5-5" and SA.app_model_label() == "Claude Opus 5.5"
    for kind in ("app", "app_edit", "app_code"):
        assert SA.model_for(kind) == "claude-opus-5-5"
    seen: list[str] = []
    monkeypatch.setattr(SA, "_app_client", (lambda c: (lambda: c))(_client([_Busy("overloaded"), _Busy("overloaded"), '{"html": "<p>ok</p>"}'], seen)))
    assert SA.ask_json("sys", "prompt", 100, "app") == {"html": "<p>ok</p>"}
    assert seen == ["claude-opus-5-5"] * 3 and SA.STATS["app_retries"] == 2 and SA.STATS["app_failed"] == 0


def test_how_opus_is_asked_thinking_effort_images(opus, monkeypatch):
    """The way Claude itself works with Opus 5.5: adaptive thinking, an effort level per job, images for self-review;
    a model / key that refuses a field gets the same request without it (once), never a different model."""
    SA = opus
    SA._EXTRAS_OFF.clear()
    seen, kws = [], []
    monkeypatch.setattr(SA, "_app_client", (lambda c: (lambda: c))(_client(['{"a": 1}'] * 4, seen, kws)))
    SA.ask_json("sys", "p", 6000, "app_art")
    SA.ask_json("sys", "p", 1500, "app_edit")
    SA.ask_json("sys", "look", 1800, "app_critique", images=[b"\x89PNG\r\n\x1a\nxx"])
    art, edit, crit = kws[0], kws[1], kws[2]
    assert art["thinking"] == {"type": "adaptive"} and art["output_config"] == {"effort": "xhigh"}
    assert art["max_tokens"] > 6000 and art["max_tokens"] <= 20000          # room for thinking, under the SDK limit
    assert edit["output_config"] == {"effort": "medium"}
    blocks = crit["messages"][0]["content"]
    assert blocks[0]["type"] == "image" and blocks[0]["source"]["media_type"] == "image/png" and blocks[-1]["text"] == "look"

    class _Bad(Exception):
        status_code = 400
    kws.clear()
    seen.clear()
    monkeypatch.setattr(SA, "_app_client", (lambda c: (lambda: c))(_client([_Bad("thinking: adaptive is not supported on this model"),
                                                            '{"ok": 1}'], seen, kws)))
    assert SA.ask_json("sys", "p", 100, "app") == {"ok": 1}
    assert "thinking" in kws[0] and "thinking" not in kws[1] and seen == ["claude-opus-5-5"] * 2
    SA._EXTRAS_OFF.clear()


def test_no_quiet_fallback_to_another_model(opus, monkeypatch):
    SA = opus
    seen: list[str] = []
    called = []
    import app.net.ai as NA
    monkeypatch.setattr(NA, "llm", lambda *a, **k: called.append(1) or "cheap")
    monkeypatch.setattr(SA, "_app_client", (lambda c: (lambda: c))(_client([_Gone("model not found")], seen)))
    with pytest.raises(SA.AiError) as e:
        SA.ask("sys", "prompt", 100, "app")
    assert "Claude Opus 5.5" in str(e.value) and "API key" in str(e.value)
    assert seen == ["claude-opus-5-5"] and not called and SA.STATS["app_failed"] == 1   # a 404 isn't tried 5 times
    seen.clear()
    monkeypatch.setattr(SA, "_app_client", (lambda c: (lambda: c))(_client([_Busy("x")] * 5, seen)))
    with pytest.raises(SA.AiError) as e2:
        SA.ask("sys", "prompt", 100, "app_code")
    assert seen == ["claude-opus-5-5"] * 5 and "busy" in str(e2.value) and not called
    # only when she switches the fallback on does another model step in
    monkeypatch.setenv("APP_MODEL_FALLBACK", "true")
    from app.config import get_settings
    get_settings.cache_clear()
    seen.clear()
    shared = _client([_Gone("x"), "sonnet answer"], seen)
    monkeypatch.setattr(SA, "_app_client", lambda: shared)
    monkeypatch.setattr(SA, "_client", lambda: shared)
    assert SA.ask("sys", "prompt", 100, "app") == "sonnet answer"
    assert seen == ["claude-opus-5-5", get_settings().anthropic_model] and SA.STATS["app_fallback"] == 1


def test_appmaker_and_android_route_to_opus(opus, monkeypatch):
    SA = opus
    kinds = []
    monkeypatch.setattr(SA, "ask_json", lambda s, p, m, k, **kw: kinds.append(k) or {"ok": 1})
    monkeypatch.setattr(SA, "ask", lambda s, p, m, k, **kw: kinds.append(k) or "```kotlin\nx\n```")
    from app.appmaker import ai as AI
    from app.appmaker.android import service as AN
    AI.ask_json("s", "p")
    AI.ask_edit("s", "p")
    AI.ask_art("s", "p")
    AI.ask_critique("s", "p", b"\xff\xd8jpeg")
    AN._ask("s", "p")
    assert kinds == ["app", "app_edit", "app_art", "app_critique", "app_code"]


def test_view_says_which_model(opus, monkeypatch, tmp_path):
    monkeypatch.setenv("APP_DIR", str(tmp_path / "apps"))
    monkeypatch.setenv("APP_WORKER", "false")
    monkeypatch.setenv("APP_FONTS_FETCH", "false")
    monkeypatch.setenv("SEMANTIC_OFF", "1")
    from app.config import get_settings
    get_settings.cache_clear()
    from app.appmaker import service as S
    v = S.new("default", "kirana ki app ghar pe delivery")
    assert v["model"] == "Claude Opus 5.5"
