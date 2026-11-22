"""v0.935 HOOLA CODE FEED (owner, on the design canvas claude.ai/artifact/27Hw4XRUj5qG83sWaeX2J5: "GO"): Qwen's words
reach the phone as they are written (OpenRouter stream -> engine.LIVE_TEXT -> task view "live"), Hoola's words between
steps are kept whole, and the phone draws the working row at the end of the thread with its words landing at reading
speed."""
import json
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[2]


def _sse(chunks):
    return "".join(f"data: {json.dumps(c)}\n\n" for c in chunks) + ": OPENROUTER PROCESSING\n\ndata: [DONE]\n\n"


def _client_with(monkeypatch, handler):
    real = httpx.Client
    monkeypatch.setattr(httpx, "Client", lambda **kw: real(transport=httpx.MockTransport(handler), **kw))


def test_a_streamed_answer_is_put_back_together_and_its_words_go_out_as_they_come(monkeypatch):
    from app.agent import llm
    from app.devsahayak import brain as B
    sent = {}

    def handler(req):
        sent["body"] = json.loads(req.content)
        return httpx.Response(200, text=_sse([
            {"model": "qwen/x", "choices": [{"delta": {"content": "I'll read "}}]},
            {"choices": [{"delta": {"content": "the README first."}}]},
            {"choices": [{"delta": {"tool_calls": [{"index": 0, "id": "c1", "function": {"name": "read", "arguments": '{"pa'}}]}}]},
            {"choices": [{"delta": {"tool_calls": [{"index": 0, "function": {"arguments": 'th": "README.md"}'}}]}, "finish_reason": "tool_calls"}]},
            {"choices": [], "usage": {"prompt_tokens": 10, "completion_tokens": 5}},
        ]), headers={"content-type": "text/event-stream"})
    _client_with(monkeypatch, handler)
    seen = []
    data = B._qwen_stream("https://openrouter.ai/api/v1/chat/completions", {"model": "qwen/x"}, {}, 10, seen.append)
    assert sent["body"]["stream"] is True and sent["body"]["usage"] == {"include": True}
    assert seen == ["I'll read ", "I'll read the README first."]
    blocks, stop = llm.from_openai(data)
    assert stop == "tool_use"
    assert [b["text"] for b in blocks if b["type"] == "text"] == ["I'll read the README first."]
    assert [b["input"] for b in blocks if b["type"] == "tool_use"] == [{"path": "README.md"}]
    assert data["usage"]["completion_tokens"] == 5


def test_a_refused_stream_says_why(monkeypatch):
    import pytest

    from app.devsahayak import brain as B
    _client_with(monkeypatch, lambda req: httpx.Response(402, text='{"error":"credits"}'))
    with pytest.raises(B.QwenError) as e:
        B._qwen_stream("https://openrouter.ai/api/v1/chat/completions", {}, {}, 10, lambda t: None)
    assert "402" in str(e.value)


def test_only_the_engines_main_call_streams_and_its_words_are_shown_while_it_runs(monkeypatch):
    from app.devsahayak import brain as B
    from app.devsahayak import engine as EN
    from app.devsahayak import service as S
    calls = []
    monkeypatch.setattr(B, "QWEN_STREAM", lambda url, body, h, to, on_text: calls.append("stream") or on_text("Hi") or
                        {"choices": [{"finish_reason": "stop", "message": {"content": "Hi"}}]})
    monkeypatch.setattr(B, "QWEN_POST", None)
    monkeypatch.setattr(B, "_qwen_post", lambda *a: calls.append("plain") or
                        {"choices": [{"finish_reason": "stop", "message": {"content": "Hi"}}]})
    monkeypatch.setattr(B, "_or_key", lambda: "k")
    B.TEXT_SINK.fn = None
    B._qwen_call("s", [{"role": "user", "content": "x"}], [], 100, False)
    assert calls == ["plain"]                                # no sink (plans, reviews, agents) = a plain call
    got = []
    B.TEXT_SINK.fn = got.append
    try:
        B._qwen_call("s", [{"role": "user", "content": "x"}], [], 100, False)
    finally:
        B.TEXT_SINK.fn = None
    assert calls == ["plain", "stream"] and got[0] == "" and got[-1] == "Hi"   # a try again starts the words over
    EN.LIVE_TEXT["tid1"] = "Looking at"
    assert S._live_text("tid1") == ""                        # no round running = nothing live
    S._RUNNING.add("tid1")
    try:
        assert S._live_text("tid1") == "Looking at"
    finally:
        S._RUNNING.discard("tid1")
        EN.LIVE_TEXT.pop("tid1", None)
    src = (ROOT / "server/app/devsahayak/engine.py").read_text()
    assert "B.TEXT_SINK.fn = None" in src and "LIVE_TEXT.pop(tid, None)" in src and "LIVE_TEXT.pop(t.id, None)" in src
    assert 'txt = str(b["text"]).strip()[:20000]' in src   # Hoola's words kept whole (were cut at 800)


def test_the_phone_draws_the_feed_like_the_hoola_chat():
    ses = (ROOT / "lib/ui/code/code_session.dart").read_text()
    words = (ROOT / "lib/ui/code/code_words.dart").read_text()
    composer = ses[ses.index("Widget _composer("):ses.index("String _envName(")]
    assert "HoolaMark" not in composer                       # the working row is no longer pinned above the typing box
    assert "if (running) out.add(_runningRow(c, t, nowGroup));" in ses   # v0.957 always the last row while it works   # v0.936 the working line
    assert "if (live.isNotEmpty) out.add(_land(live, 'live', done: false));" in ses
    assert "final every = live ? 1 : 10;" in ses             # every second while it works
    assert "class CodeLanding" in words and "CodeLanding.msPerWord(waiting)" in words   # v0.937 slower, each word fading in
    assert "class CodeShimmer" in words and "HoolaMotion.reduced(context)" in words


def test_version():
    main = (ROOT / "server/app/main.py").read_text()
    assert 'APP_VERSION = "0.999.140"' in main
    assert "version: 0.999.140+1135" in (ROOT / "pubspec.yaml").read_text()
