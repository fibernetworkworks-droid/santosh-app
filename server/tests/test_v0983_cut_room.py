"""v0.983 CUT ROOM: her ref 4576bd ("AI service is busy or unreachable") on a page-fix message was not an outage.
Qwen on OpenRouter started rewriting the page in a tool call, the chat's 2000-token cap cut the call half way, the half
call was dropped (never run with broken inputs) and nothing was left, so it was reported as an "empty answer". Now a cut
answer with nothing usable is asked again ONCE with real room (16k), and if even that cuts, she is told the answer was too
long, not that the service is busy."""
import asyncio
import json

import httpx
import pytest


@pytest.fixture
def glm(monkeypatch, tmp_path):
    for k, v in {"GLM_API_KEY": "k", "CHAT_LLM": "glm", "GLM_BASE_URL": "https://openrouter.ai/api/v1",
                 "GLM_MODEL": "qwen/qwen3.8-27b"}.items():
        monkeypatch.setenv(k, v)
    from app.config import get_settings
    get_settings.cache_clear()
    from app.agent import llm
    yield llm
    llm.set_http(None)
    get_settings.cache_clear()


def _sse(chunks):
    return "".join("data: " + json.dumps(c) + "\n\n" for c in chunks) + "data: [DONE]\n\n"


def _cut_stream():
    """A tool call whose arguments stop half way (an unfinished page), finish_reason length."""
    return _sse([{"choices": [{"delta": {"tool_calls": [{"index": 0, "id": "c1", "function": {
        "name": "artifact", "arguments": '{"action": "update", "html": "<html><body><h1>Shop'}}]}}]},
        {"choices": [{"delta": {}, "finish_reason": "length"}]}])


def _whole_stream():
    return _sse([{"choices": [{"delta": {"tool_calls": [{"index": 0, "id": "c1", "function": {
        "name": "artifact", "arguments": '{"action": "update", "html": "<html><body><h1>Shop</h1></body></html>"}'}}]}}]},
        {"choices": [{"delta": {}, "finish_reason": "tool_calls"}]},
        {"choices": [], "usage": {"prompt_tokens": 10, "completion_tokens": 5}}])


def _serve(llm, answers):
    seen = []

    def handler(req):
        body = json.loads(req.content)
        seen.append(body.get("max_tokens"))
        return httpx.Response(200, text=answers[min(len(seen) - 1, len(answers) - 1)],
                              headers={"content-type": "text/event-stream"})
    llm.set_http(httpx.AsyncClient(transport=httpx.MockTransport(handler)))
    return seen


def _run(llm, cap=2000):
    return asyncio.run(llm.openai_stream("glm", "sys", [{"name": "artifact", "description": "d",
                                                         "input_schema": {"type": "object", "properties": {}}}],
                                         [{"role": "user", "content": "fix the page"}], cap, lambda t: None))


def test_cut_page_rewrite_is_asked_again_with_real_room(glm):
    seen = _serve(glm, [_cut_stream(), _whole_stream()])
    blocks, stop, _ = _run(glm)
    assert stop == "tool_use"
    assert blocks[0]["name"] == "artifact" and "</html>" in blocks[0]["input"]["html"]
    assert seen[0] < seen[1] and seen[1] >= 16000          # the second ask had real room


def test_still_cut_says_too_long_not_busy(glm):
    seen = _serve(glm, [_cut_stream()])
    with pytest.raises(glm.LLMCut):
        _run(glm)
    assert len(seen) == 3 and seen[-1] == 32000             # v0.984: up to two bigger asks, never a loop
    from app.agent import santosh
    line = santosh._friendly_error(glm.LLMCut("OpenRouter ran out of room before finishing its answer (max_tokens 16000)"))
    assert "too long to finish" in line and "busy" not in line


def test_room_rules(glm):
    assert glm.cut_room(2000) == 16000
    assert glm.cut_room(6000) == 24000
    assert glm.cut_room(32000) == 0                         # already had the most room: no second ask


def test_true_empty_answer_unchanged(glm):
    _serve(glm, [_sse([{"choices": [{"delta": {}, "finish_reason": "stop"}]}])])
    with pytest.raises(glm.LLMError) as e:
        _run(glm)
    assert not isinstance(e.value, glm.LLMCut) and "empty answer" in str(e.value)
