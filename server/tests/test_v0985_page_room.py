"""v0.985 PAGE ROOM (built as 0.984): her 'Radiant Broadband Panel' page (~73,000 characters) never reached the panel - Hoola writes a
page itself inside the `artifact` tool call, the chat's 2000-token cap cut each write at ~10,000 characters, the
half-written call was dropped (words had come first, so v0.983's 'nothing usable' retry never fired) and the turn
kept re-writing at the same small cap; a cut-off page that did get through was saved and drew a blank preview.
Now: a cut tool call is asked again with room (2000 -> 16k -> 32k), the words already shown are cleared first, and
a page that visibly stops part-way is refused, never stored as a version."""
from __future__ import annotations

import asyncio
import json

import httpx
import pytest

PAGE = ("<!doctype html><html><head><title>Panel</title><style>h1{color:red}</style></head><body>"
        "<h1>Radiant Broadband</h1><script>let a=1;</script></body></html>")


@pytest.fixture
def glm(monkeypatch):
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


def _words_then_cut():
    """'I'll write the page now' then a page call cut part-way (finish length) - her case."""
    return _sse([{"choices": [{"delta": {"content": "Writing the full panel now."}}]},
                 {"choices": [{"delta": {"tool_calls": [{"index": 0, "id": "c1", "function": {
                     "name": "artifact", "arguments": '{"action": "create", "content": "<html><body><h1>Rad'}}]}}]},
                 {"choices": [{"delta": {}, "finish_reason": "length"}]}])


def _whole():
    args = json.dumps({"action": "create", "title": "Panel", "content": PAGE})
    return _sse([{"choices": [{"delta": {"content": "Writing the full panel now."}}]},
                 {"choices": [{"delta": {"tool_calls": [{"index": 0, "id": "c1", "function": {
                     "name": "artifact", "arguments": args}}]}}]},
                 {"choices": [{"delta": {}, "finish_reason": "tool_calls"}]}])


def _serve(llm, answers):
    seen = []

    def handler(req):
        seen.append(json.loads(req.content).get("max_tokens"))
        return httpx.Response(200, text=answers[min(len(seen) - 1, len(answers) - 1)],
                              headers={"content-type": "text/event-stream"})
    llm.set_http(httpx.AsyncClient(transport=httpx.MockTransport(handler)))
    return seen


def _run(llm, resets):
    tools = [{"name": "artifact", "description": "d", "input_schema": {"type": "object", "properties": {}}}]
    return asyncio.run(llm.openai_stream("glm", "sys", tools, [{"role": "user", "content": "fix the page"}], 2000,
                                         lambda t: None, on_reset=lambda: resets.append(1)))


def test_words_then_a_cut_page_call_is_asked_again_with_room(glm):
    resets = []
    seen = _serve(glm, [_words_then_cut(), _whole()])
    blocks, stop, _ = _run(glm, resets)
    assert stop == "tool_use" and any(b["type"] == "tool_use" and "</html>" in b["input"]["content"] for b in blocks)
    assert len(seen) == 2 and seen[1] >= 16000 > seen[0]
    assert resets == [1]                                     # the words already shown were cleared, not said twice


def test_room_steps_up_twice_then_stops(glm):
    resets = []
    seen = _serve(glm, [_words_then_cut(), _words_then_cut(), _whole()])
    blocks, stop, _ = _run(glm, resets)
    assert len(seen) == 3 and seen[0] < seen[1] < seen[2] == 32000 and stop == "tool_use"
    resets2 = []
    seen2 = _serve(glm, [_words_then_cut()])
    blocks, stop, _ = _run(glm, resets2)
    assert len(seen2) == 3 and seen2[-1] == 32000            # never a fourth ask
    assert stop == "max_tokens" and not any(b["type"] == "tool_use" for b in blocks)


@pytest.fixture()
def direct(env, monkeypatch):
    from app.config import get_settings
    monkeypatch.delenv("CHAT_ARTIFACT_DIRECT", raising=False)
    get_settings.cache_clear()
    from app.events import bus
    monkeypatch.setattr(bus, "publish", lambda c, k, p: None)
    yield
    get_settings.cache_clear()


def test_a_cut_off_page_is_never_saved(direct):
    from app import artifacts
    cut = PAGE[: len(PAGE) // 2]                             # stops inside <head>
    with pytest.raises(artifacts.EditError) as e:
        artifacts.write("t1", "c1", "create", title="Panel", content=cut)
    assert "cut off" in str(e.value)
    a = artifacts.write("t1", "c1", "create", title="Panel", content=PAGE)
    with pytest.raises(artifacts.EditError):
        artifacts.write("t1", "c1", "rewrite", artifact_id=a["id"], content=PAGE.replace("</script></body></html>", ""))
    assert artifacts.current_source(a["id"])[0] == 1         # version 1 stays, nothing half saved
    assert artifacts.cut_off("html", "<div>small piece</div>") == ""
    assert artifacts.cut_off("markdown", "# heading") == ""
