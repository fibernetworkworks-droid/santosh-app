"""v0.926 HOOLA CODE ON QWEN (owner: "27B FOR CODING ALSO"): every Hoola Code model call - the coding round, plans,
reviews, agents, compaction, the hint and the memory - runs on Qwen 3.8 27B through OpenRouter, on its own request
(its own clock, never the chat's GLM door), and Claude is one setting away."""
from pathlib import Path

import pytest

from app.config import Settings, get_settings
from app.devsahayak import brain as B
from app.devsahayak import service as S

ROOT = Path(__file__).resolve().parents[2]


def _st(monkeypatch, **env):
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    get_settings.cache_clear()


@pytest.fixture
def qwen(monkeypatch):
    _st(monkeypatch, DEV_BRAIN="qwen", OPENROUTER_API_KEY="or-key")
    seen: list = []

    def post(url, body, headers, timeout):
        seen.append(dict(url=url, body=body, headers=headers, timeout=timeout))
        return seen_answer[0]

    seen_answer = [{"choices": [{"finish_reason": "tool_calls", "message": {"content": "Reading the file.", "tool_calls": [
        {"id": "call_1", "type": "function", "function": {"name": "read_file", "arguments": '{"path": "a.py"}'}}]}}],
        "usage": {"prompt_tokens": 1200, "completion_tokens": 80}}]
    monkeypatch.setattr(B, "QWEN_POST", post)
    monkeypatch.setattr(B, "CLIENT", None)
    B.PICK.model, B.PICK.effort = "", ""
    yield seen, seen_answer
    B.PICK.model, B.PICK.effort = "", ""
    get_settings.cache_clear()


def test_defaults_are_qwen_27b():
    f = Settings.model_fields
    assert f["dev_brain"].default == "qwen"
    assert f["dev_qwen_model"].default == "qwen/qwen3.8-27b"
    assert f["dev_qwen_timeout_s"].default >= 120          # never the chat's 45 s door clock
    assert f["dev_qwen_fallback_claude"].default is False  # no surprise Opus bill


def test_a_coding_step_goes_to_openrouter(qwen):
    seen, _ = qwen
    tools = [{"name": "read_file", "description": "read", "input_schema": {"type": "object", "properties": {"path": {"type": "string"}}}}]
    msgs = [{"role": "user", "content": "fix the bug"},
            {"role": "assistant", "content": [{"type": "thinking", "thinking": "old Claude thought", "signature": "x"},
                                              {"type": "text", "text": "Looking."}]},
            {"role": "user", "content": "go on"}]
    blocks, stop = B.call("You are Hoola Code.", msgs, tools)
    assert stop == "tool_use"
    assert blocks[0] == {"type": "text", "text": "Reading the file."}
    assert blocks[1]["type"] == "tool_use" and blocks[1]["name"] == "read_file" and blocks[1]["input"] == {"path": "a.py"}
    r = seen[0]
    assert r["url"] == "https://openrouter.ai/api/v1/chat/completions"
    assert r["headers"]["Authorization"] == "Bearer or-key" and r["timeout"] == 180.0
    b = r["body"]
    assert b["model"] == "qwen/qwen3.8-27b"
    assert b["reasoning"] == {"effort": "high", "exclude": True}       # her default effort, thinking kept out
    assert b["max_tokens"] == 16000 + B.ROOM["high"]
    assert b["tools"][0]["function"]["name"] == "read_file" and b["tool_choice"] == "auto"
    assert b["provider"] == {"require_parameters": True}               # only providers that really take tools
    assert "thinking" not in b and "extra_body" not in b
    assert not any("old Claude thought" in str(m.get("content")) for m in b["messages"])   # unsigned thoughts never sent
    assert B.model_for() == "qwen/qwen3.8-27b"


def test_claude_picks_mean_nothing_on_qwen_but_a_qwen_pick_wins(qwen):
    seen, _ = qwen
    B.PICK.model, B.PICK.effort = "claude-haiku-5-5", "low"   # the hint / memory callers ask for Haiku
    B.call("hint", [{"role": "user", "content": "x"}], [], max_tokens=60, think=False)
    assert seen[-1]["body"]["model"] == "qwen/qwen3.8-27b"
    assert seen[-1]["body"]["reasoning"]["effort"] == "low" and "tools" not in seen[-1]["body"]
    B.PICK.model = "qwen/qwen3.8-max-0902"
    B.call("x", [{"role": "user", "content": "x"}], [])
    assert seen[-1]["body"]["model"] == "qwen/qwen3.8-max-0902"


def test_a_slow_or_empty_answer_is_asked_again_then_said(qwen, monkeypatch):
    seen, answer = qwen
    monkeypatch.setattr("time.sleep", lambda s: None)
    calls = {"n": 0}

    def flaky(url, body, headers, timeout):
        calls["n"] += 1
        if calls["n"] == 1:
            raise TimeoutError("read timed out")
        return answer[0]
    monkeypatch.setattr(B, "QWEN_POST", flaky)
    blocks, _ = B.call("x", [{"role": "user", "content": "x"}], [])
    assert calls["n"] == 2 and blocks
    monkeypatch.setattr(B, "QWEN_POST", lambda *a: {"choices": [{"finish_reason": "stop", "message": {"content": ""}}]})
    with pytest.raises(B.QwenError):
        B.call("x", [{"role": "user", "content": "x"}], [])


def test_a_refused_request_is_not_retried_and_never_moved_to_claude(qwen, monkeypatch):
    calls = {"n": 0}

    def refused(url, body, headers, timeout):
        calls["n"] += 1
        raise B.QwenError("OpenRouter answered 402: no credit")
    monkeypatch.setattr(B, "QWEN_POST", refused)

    class Boom:
        class messages:
            @staticmethod
            def create(**kw):
                raise AssertionError("Claude must not be asked")
    monkeypatch.setattr(B, "CLIENT", Boom)
    with pytest.raises(B.QwenError):
        B.call("x", [{"role": "user", "content": "x"}], [])
    assert calls["n"] == 1


def test_no_openrouter_key_means_claude(monkeypatch):
    _st(monkeypatch, DEV_BRAIN="qwen", OPENROUTER_API_KEY="", GLM_API_KEY="")
    monkeypatch.setattr(B, "QWEN_POST", None)
    assert B.brain_name() == "claude"
    _st(monkeypatch, DEV_BRAIN="claude", OPENROUTER_API_KEY="or-key")
    assert B.brain_name() == "claude"
    get_settings.cache_clear()


def test_the_page_shows_qwen_as_the_model(qwen):
    m = S.models()
    assert m["brain"] == "qwen" and m["forced"]["model"] == "Qwen 3.8 27B"
    assert m["options"] == [{"id": "qwen/qwen3.8-27b", "label": "Qwen 3.8 27B"}]


def test_one_shot_json_calls_ride_qwen(qwen):
    seen, answer = qwen
    answer[0] = {"choices": [{"finish_reason": "stop", "message": {"content": '```json\n{"files": [], "summary": "ok"}\n```'}}]}
    out = S.model_json("You write code.", "do it")
    assert out == {"files": [], "summary": "ok"} and seen[-1]["body"]["model"] == "qwen/qwen3.8-27b"


def test_the_loop_runs_without_a_claude_key(qwen, monkeypatch):
    from app.devsahayak import loop
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")
    get_settings.cache_clear()
    blocks, _ = loop._anthropic_brain("x", [{"role": "user", "content": "x"}], [])
    assert blocks


def test_price_and_version():
    from app import usage
    assert usage.price_of("qwen/qwen3.8-27b")[0]["out"] == 1.875
    main = (ROOT / "server/app/main.py").read_text()
    assert 'APP_VERSION = "0.939.0"' in main and "HOOLA CODE" in main
    assert "version: 0.939.0+938" in (ROOT / "pubspec.yaml").read_text()


def test_v0927_times_carry_their_zone_and_the_round_start():
    """v0.927 (owner's phone: the working clock read 5:30:57 on a one-minute plan pass): SQLite hands created_at back
    without a zone and the phone read the bare time as India time. Every time now carries +00:00, the running round
    has its own start (run_at), and the phone reads any bare time as UTC."""
    from datetime import datetime
    src = (ROOT / "server/app/devsahayak/service.py").read_text()
    assert '"at": _aware(t.created_at).isoformat()' in src and '"run_at": _RUN_AT.get(t.id, "")' in src
    assert "_RUN_AT[tid] = now().isoformat()" in src and "_RUN_AT.pop(tid, None)" in src
    assert S._aware(datetime(2026, 11, 15, 9, 40)).isoformat().endswith("+00:00")
    kit = (ROOT / "lib/ui/code/code_kit.dart").read_text()
    assert "DateTime? codeTime(String iso)" in kit and "'${v}Z'" in kit
    for f in ("code_session.dart", "code_home.dart"):
        d = (ROOT / "lib/ui/code" / f).read_text()
        assert "DateTime.tryParse" not in d and "cs(t['run_at'])" in d
    ses = (ROOT / "lib/ui/code/code_session.dart").read_text()
    assert "'plan' => 'Planning · reading the code'" in ses and "if (parts.isEmpty) return _passTitle(g);" in ses
    assert "TASK.run_at || TASK.at" in (ROOT / "server/app/static/console/code.js").read_text()
    assert 'log.info("hoola code qwen %s %.1fs' in (ROOT / "server/app/devsahayak/brain.py").read_text()


def test_v0930_card_names_the_model_that_answered():
    src = (ROOT / "server/app/quality/codecard.py").read_text()
    assert '_B.model_for() if _B.brain_name() == "qwen" else model' in src
