"""v0.851 PC BRAIN: the PC loop runs on Qwen 3.8 Max or Sonnet 5.5, chosen for the PC alone."""
import asyncio
import json
import types

import pytest

from app.config import get_settings
from app.pc import brain


def _st(monkeypatch, **env):
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    get_settings.cache_clear()


def test_choose_qwen_default_with_key(monkeypatch):
    _st(monkeypatch, PC_MODEL="qwen", QWEN_API_KEY="k", QWEN_BASE_URL="")
    assert brain.choose() == ("qwen", "qwen3.8-max", "")
    assert brain.choose("sonnet")[:2] == ("sonnet", "claude-sonnet-5-5")   # a task can name its own


def test_qwen_without_key_runs_on_sonnet_and_says_so(monkeypatch):
    _st(monkeypatch, PC_MODEL="qwen", QWEN_API_KEY="", OPENROUTER_API_KEY="", GLM_API_KEY="")
    b, m, note = brain.choose()
    assert (b, m) == ("sonnet", "claude-sonnet-5-5") and "QWEN_API_KEY" in note


def test_qwen_via_openrouter_with_the_servers_openrouter_key(monkeypatch):
    _st(monkeypatch, PC_MODEL="qwen", QWEN_API_KEY="", OPENROUTER_API_KEY="or-key")
    assert brain.choose() == ("qwen", "qwen/qwen3.8-max-0902", "")
    url, key, model = brain.qwen_route()
    assert url == "https://openrouter.ai/api/v1/chat/completions" and key == "or-key"
    seen = {}

    async def post(url, key, body, timeout):
        seen.update(url=url, key=key, body=body)
        return {"choices": [{"finish_reason": "stop", "message": {"content": "ok"}}]}
    monkeypatch.setattr(brain, "_post", post)
    monkeypatch.setenv("PC_QWEN_THINKING", "off"); get_settings.cache_clear()
    op = types.SimpleNamespace(brain="qwen", brain_model="qwen/qwen3.8-max-0902", step=1)
    asyncio.run(brain.think(op, None, [{"role": "user", "content": "x"}], {"system": "S", "tools": []}, None))
    assert seen["key"] == "or-key" and seen["body"]["model"] == "qwen/qwen3.8-max-0902"
    assert "enable_thinking" not in seen["body"] and seen["body"]["reasoning"] == {"enabled": False}


def test_defaults_on_the_server():
    from app.config import Settings
    f = Settings.model_fields
    s = types.SimpleNamespace(**{k: f[k].default for k in ("pc_model", "pc_qwen_model", "pc_sonnet_model", "pc_max_tokens")})
    assert s.pc_model == "qwen" and s.pc_qwen_model == "qwen3.8-max" and s.pc_sonnet_model == "claude-sonnet-5-5"
    assert s.pc_max_tokens >= 4000


def _img():
    return {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": "QUJD"}}


def test_to_openai_keeps_order_and_moves_screenshots_out_of_tool_messages():
    msgs = [{"role": "user", "content": [{"type": "text", "text": "Task: x"}, _img()]},
            {"role": "assistant", "content": [{"type": "text", "text": "kholta hoon"},
                                              {"type": "tool_use", "id": "a1", "name": "open_app", "input": {"name": "Excel"}}]},
            {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "a1",
                                          "content": [{"type": "text", "text": "opened"}, _img()]}]}]
    out = brain.to_openai("SYS", msgs)
    assert [m["role"] for m in out] == ["system", "user", "assistant", "tool", "user"]
    assert out[1]["content"][1]["image_url"]["url"] == "data:image/jpeg;base64,QUJD"
    call = out[2]["tool_calls"][0]
    assert call["function"]["name"] == "open_app" and json.loads(call["function"]["arguments"]) == {"name": "Excel"}
    assert out[3] == {"role": "tool", "tool_call_id": "a1", "content": "opened"}          # text only
    assert any(p.get("type") == "image_url" for p in out[4]["content"])                  # the screen after it


def test_tools_and_reply_shapes():
    t = brain.tools_openai([{"name": "click", "description": "d", "input_schema": {"type": "object", "properties": {"x": {"type": "integer"}}}}])
    assert t[0]["function"]["parameters"]["properties"]["x"]["type"] == "integer"
    r = brain.from_openai({"model": "qwen3.8-max", "choices": [{"finish_reason": "tool_calls", "message": {
        "content": "dekhta hoon", "tool_calls": [{"id": "c1", "function": {"name": "click", "arguments": "{\"x\": 5}"}},
                                                 {"id": "c2", "function": {"name": "type", "arguments": "not json"}}]}}]})
    assert r.stop == "tool_use" and r.content[0] == {"type": "text", "text": "dekhta hoon"}
    assert r.content[1]["input"] == {"x": 5} and r.content[2]["input"] == {}
    cut = brain.from_openai({"choices": [{"finish_reason": "length", "message": {"content": ""}}]})
    assert cut.stop == "max_tokens" and cut.content == []


def test_qwen_call_hits_her_endpoint_and_counts_tokens(monkeypatch):
    _st(monkeypatch, QWEN_API_KEY="secret", QWEN_BASE_URL="https://example.test/v1")
    seen = {}

    async def post(url, key, body, timeout):
        seen.update(url=url, key=key, body=body)
        return {"model": "qwen3.8-max", "usage": {"prompt_tokens": 1000, "completion_tokens": 50},
                "choices": [{"finish_reason": "stop", "message": {"content": "ho gaya"}}]}
    monkeypatch.setattr(brain, "_post", post)
    rec = []
    from app import usage
    monkeypatch.setattr(usage, "record", lambda m, **k: rec.append((m, k)))
    op = types.SimpleNamespace(brain="qwen", brain_model="qwen3.8-max", step=1)
    rep = asyncio.run(brain.think(op, None, [{"role": "user", "content": "Task: x"}],
                                  {"system": "S", "tools": [], "max_tokens": 4000}, None))
    assert seen["url"] == "https://example.test/v1/chat/completions" and seen["key"] == "secret"
    assert seen["body"]["model"] == "qwen3.8-max" and "enable_thinking" not in seen["body"]
    assert rep.content == [{"type": "text", "text": "ho gaya"}]
    assert rec and rec[0][0] == "qwen3.8-max" and rec[0][1]["tok_in"] == 1000


def test_sonnet_path_is_never_rewritten_to_haiku_or_glm(monkeypatch):
    from app import usage, glmdoor
    seen = {}

    async def retry(op, client, messages, params):
        seen.update(model=params["model"], bypass=usage.ONE_MODEL_BYPASS.get(), claude_only=glmdoor.CLAUDE_ONLY.get())
        return types.SimpleNamespace(content=[{"type": "text", "text": "ok"}], stop_reason="end_turn", model=params["model"])
    op = types.SimpleNamespace(brain="sonnet", brain_model="claude-sonnet-5-5", step=0)
    rep = asyncio.run(brain.think(op, None, [], {"model": "x", "system": "S", "tools": []}, retry))
    assert seen == {"model": "claude-sonnet-5-5", "bypass": True, "claude_only": True}
    assert not usage.ONE_MODEL_BYPASS.get() and not glmdoor.CLAUDE_ONLY.get()          # reset after the step
    assert rep.stop == "end_turn"


def test_pc_tools_take_a_model_pick():
    from app.agent import pc_tools
    specs = {t["name"]: t for t in pc_tools.PC_TOOLS}
    for n in ("pc_do", "hoola_pc_do"):
        assert specs[n]["input_schema"]["properties"]["model"]["enum"] == ["qwen", "sonnet"]


def test_operator_wiring_pins():
    import inspect
    from app.pc import operator
    src = inspect.getsource(operator._run)
    assert "_brain.think(" in src and "max_tokens=1500" not in src
    assert 'resp.stop in ("max_tokens", "refusal")' in src            # a cut-off step is not 'done'
    assert "brain" in inspect.signature(operator.start).parameters
