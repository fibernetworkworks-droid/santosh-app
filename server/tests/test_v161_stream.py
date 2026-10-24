"""v0.161 Smooth replies: the reply streams word by word (CONSOLE_STREAM), live-only, scrubbed, stoppable, resumable,
falls back cleanly, and old clients see exactly the old final `message`."""
import asyncio
import json
import time
from types import SimpleNamespace

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

KEY = "owner-key-for-stream-tests"
SECRET = "sk-ant-api03-" + "Q" * 40          # a key the model "echoes": must never leave in a delta


def _on(monkeypatch, on=True):
    monkeypatch.setenv("CONSOLE_STREAM", "true" if on else "false")
    monkeypatch.setenv("API_KEY", KEY)
    from app.config import get_settings
    get_settings.cache_clear()


def _conv():
    from app.db import Conversation, session
    with session() as s:
        c = Conversation(tenant_id="default")
        s.add(c)
        s.flush()
        return c.id


class _Ev(SimpleNamespace):
    pass


class _Stream:
    """messages.stream(...) stand-in: Anthropic raw stream events, then get_final_message()."""

    def __init__(self, blocks, delay=0.0, fail_after=None):
        self.blocks, self.delay, self.fail_after = blocks, delay, fail_after

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    def __aiter__(self):
        return self._events()

    async def _events(self):
        n = 0
        for b in self.blocks:
            yield _Ev(type="content_block_start", content_block=SimpleNamespace(type=b["type"]))
            if b["type"] == "text":
                for piece in b.pop("_pieces", None) or [b["text"]]:
                    if self.fail_after is not None and n >= self.fail_after:
                        raise RuntimeError("overloaded mid-stream")
                    n += 1
                    if self.delay:
                        await asyncio.sleep(self.delay)
                    yield _Ev(type="content_block_delta", delta=SimpleNamespace(type="text_delta", text=piece))
            yield _Ev(type="content_block_stop")

    async def get_final_message(self):
        return SimpleNamespace(content=[{k: v for k, v in b.items() if not k.startswith("_")} for b in self.blocks],
                               stop_reason="tool_use" if any(b["type"] == "tool_use" for b in self.blocks) else "end_turn",
                               usage=SimpleNamespace(input_tokens=100, output_tokens=20), model="claude-test")


class StreamingClaude:
    """Plays back scripted answers through messages.stream (and messages.create for the old path)."""

    def __init__(self, script, delay=0.0, fail_after=None):
        self.script, self.delay, self.fail_after = list(script), delay, fail_after
        self.streams, self.creates = 0, 0
        self.messages = SimpleNamespace(stream=self._stream, create=self._create)

    def _stream(self, **kw):
        self.streams += 1
        return _Stream(self.script.pop(0), self.delay, self.fail_after)

    async def _create(self, **kw):
        self.creates += 1
        blocks = [{k: v for k, v in b.items() if not k.startswith("_")} for b in self.script.pop(0)]
        return SimpleNamespace(content=blocks, stop_reason="end_turn")


def _text(pieces):
    return {"type": "text", "text": "".join(pieces), "_pieces": list(pieces)}


async def _run(conv, text, brain, collect, until=None):
    from app.agent import run_turn, set_client
    from app.events import bus
    set_client(brain)
    q = bus.subscribe(conv)
    task = asyncio.ensure_future(run_turn(conv, text, tenant_id="default"))
    if until:
        await until(task)
    out = await task
    while not q.empty():
        collect.append(q.get_nowait())
    bus.unsubscribe(conv, q)
    return out


def test_deltas_in_order_scrubbed_and_final_message_unchanged(env, monkeypatch):
    _on(monkeypatch)
    conv = _conv()
    pieces = ["Namaste! ", "Aapka GST ", "return ", "taiyaar hai. ", "Key jo mili: ", SECRET[:10], SECRET[10:30],
              SECRET[30:], " ab hata di gayi. ", "Aage kya karna hai? " * 3]
    full = "".join(pieces)          # the final text is exactly what the model wrote (as today)
    evs = []
    calls = []
    from app import usage
    monkeypatch.setattr(usage, "from_anthropic", lambda model, resp: calls.append((model, resp.usage.output_tokens)))
    out = asyncio.run(_run(conv, "gst ka haal?", StreamingClaude([[_text(pieces)]], delay=0.03), evs))
    kinds = [e["kind"] for e in evs]
    assert kinds[0] == "typing" and "reply_start" in kinds and kinds.index("reply_end") < len(kinds) - 1
    deltas = [e for e in evs if e["kind"] == "delta"]
    assert len(deltas) >= 2
    assert [d["payload"]["seq"] for d in deltas] == sorted(d["payload"]["seq"] for d in deltas)
    shown = "".join(d["payload"]["text"] for d in deltas)
    assert "sk-ant" not in shown and "QQQQ" not in shown          # never the key, not even its first characters
    assert full.startswith(shown.split("[key hataya]")[0])
    turn = deltas[0]["payload"]["turn"]
    assert all(d["payload"]["turn"] == turn and d["id"] == 0 and d.get("live") for d in deltas)
    final = [e for e in evs if e["kind"] == "message" and e["payload"]["role"] == "assistant"]
    assert len(final) == 1 and final[0]["payload"]["text"] == full == out          # exactly today's final text
    assert final[0]["payload"]["turn"] == turn and final[0]["payload"]["seg"] == 0
    assert calls == [("claude-sonnet-5-5", 20)]                    # the streamed answer is counted in the cost report
    # live-only: nothing of the stream is stored; the final message is
    from app.db import Event, session
    from app.events import STREAM_KINDS
    with session() as s:
        stored = [e.kind for e in s.scalars(select(Event).where(Event.conversation_id == conv)).all()]
    assert not set(stored) & STREAM_KINDS and "message" in stored


def test_text_steps_text_are_separate_blocks(env, monkeypatch):
    _on(monkeypatch)
    conv = _conv()
    first = [_text(["Main reminders ", "dekh raha hoon, ", "ek second. " * 3]),
             {"type": "tool_use", "id": "tu_1", "name": "list_reminders", "input": {}}]
    second = [_text(["Aapke koi ", "reminder ", "nahi hain abhi. " * 3])]
    evs = []
    asyncio.run(_run(conv, "mere reminders?", StreamingClaude([first, second], delay=0.03), evs))
    segs = [e["payload"]["seg"] for e in evs if e["kind"] == "delta"]
    assert 0 in segs and 1 in segs and segs == sorted(segs)
    msgs = [e["payload"] for e in evs if e["kind"] == "message" and e["payload"]["role"] == "assistant"]
    assert [m["seg"] for m in msgs] == [0, 1] and len({m["turn"] for m in msgs}) == 1
    order = [e["kind"] for e in evs if e["kind"] in ("delta", "step")]
    assert order.index("step") > 0 and "delta" in order[order.index("step"):]   # text -> steps -> text


def test_stop_cancels_the_stream_within_a_second_and_keeps_what_she_saw(env, monkeypatch):
    _on(monkeypatch)
    conv = _conv()
    pieces = [f"shabd{i} " for i in range(200)]
    brain = StreamingClaude([[_text(pieces)]], delay=0.05)
    evs = []
    from app import livereply
    from app.agent.santosh import stop
    seen = {}

    async def until(task):
        for _ in range(100):
            await asyncio.sleep(0.05)
            snap = livereply.snapshot(conv)
            if snap and len(snap["text"]) > 40:
                seen["snap"] = snap
                break
        seen["t0"] = time.monotonic()
        stop(conv)
        await asyncio.wait({task})
        seen["dt"] = time.monotonic() - seen["t0"]

    asyncio.run(_run(conv, "lambi kahani", brain, evs, until))
    assert seen["dt"] < 1.0
    snap = seen["snap"]                                           # /live while it was running: what a reload resumes
    assert snap["turn"].startswith("t_") and snap["seq"] >= 1 and snap["text"].startswith("shabd0")
    assert livereply.snapshot(conv) is None                       # nothing running any more
    msgs = [e["payload"] for e in evs if e["kind"] == "message"]
    part = next(m for m in msgs if m.get("stopped"))
    assert part["text"].startswith("shabd0") and "shabd199" not in part["text"]
    assert msgs[-1]["text"].startswith("Theek hai, maine kaam rok diya")
    end = [e["payload"] for e in evs if e["kind"] == "reply_end"]
    assert end and end[0]["stopped"] is True
    from app.db import Message, session
    with session() as s:
        saved = [m.display for m in s.scalars(select(Message).where(Message.conversation_id == conv,
                                                                    Message.role == "assistant")).all()]
    assert part["text"] in saved


class _Broken(httpx.AsyncByteStream):
    def __init__(self, chunks):
        self.chunks = chunks

    async def __aiter__(self):
        for c in self.chunks:
            yield c
        raise httpx.ReadError("connection dropped")

    async def aclose(self):
        pass


def _sse(*objs, done=True):
    out = b"".join(b"data: " + json.dumps(o).encode() + b"\n\n" for o in objs)
    return out + (b"data: [DONE]\n\n" if done else b"")


def test_brain_failing_mid_stream_resets_and_the_other_brain_answers(env, monkeypatch):
    _on(monkeypatch)
    monkeypatch.setenv("GLM_API_KEY", "glm-test")
    from app.config import get_settings
    get_settings.cache_clear()
    from app.agent import llm
    monkeypatch.setattr(llm, "RETRY_DELAY", 0.01)
    words = [{"choices": [{"delta": {"content": "GLM ne likhna shuru kiya, bahut saare shabd yahan hain " * 2}}]}]

    def handler(req):
        assert json.loads(req.content)["stream"] is True
        return httpx.Response(200, headers={"content-type": "text/event-stream"}, stream=_Broken([_sse(*words, done=False)]))

    llm.set_http(httpx.AsyncClient(transport=httpx.MockTransport(handler)))
    conv = _conv()
    evs = []
    try:
        out = asyncio.run(_run(conv, "namaste", StreamingClaude([[_text(["Claude ka ", "poora jawab ", "yahan hai. " * 3])]]), evs))
    finally:
        llm.set_http(None)
    kinds = [e["kind"] for e in evs]
    assert "delta_reset" in kinds
    after = kinds[kinds.index("delta_reset"):]
    assert "delta" in after                                       # the other brain streamed the block again
    final = [e["payload"] for e in evs if e["kind"] == "message" and e["payload"]["role"] == "assistant"]
    assert len(final) == 1 and final[0]["text"].startswith("Claude ka poora jawab") and out == final[0]["text"]


def test_glm_stream_tool_call_parsed_only_when_complete(env, monkeypatch):
    _on(monkeypatch)
    monkeypatch.setenv("GLM_API_KEY", "glm-test")
    from app.config import get_settings
    get_settings.cache_clear()
    from app.agent import llm
    got = []
    body = _sse({"choices": [{"delta": {"content": "Dekhta hoon"}}]},
                {"choices": [{"delta": {"tool_calls": [{"index": 0, "id": "call_1", "function": {"name": "list_rem", "arguments": "{\"wh"}}]}}]},
                {"choices": [{"delta": {"tool_calls": [{"index": 0, "function": {"name": "inders", "arguments": "en\": \"aaj\"}"}}]}}]},
                {"choices": [{"delta": {}, "finish_reason": "tool_calls"}], "usage": {"prompt_tokens": 50, "completion_tokens": 9}})
    llm.set_http(httpx.AsyncClient(transport=httpx.MockTransport(
        lambda req: httpx.Response(200, headers={"content-type": "text/event-stream"}, content=body))))
    try:
        blocks, stop, usage = asyncio.run(llm.openai_stream("glm", "sys", [], [{"role": "user", "content": "hi"}], 100, got.append))
    finally:
        llm.set_http(None)
    assert got == ["Dekhta hoon"] and stop == "tool_use"
    tool = next(b for b in blocks if b["type"] == "tool_use")
    assert tool["name"] == "list_reminders" and tool["input"] == {"when": "aaj"} and usage["completion_tokens"] == 9


def test_old_client_path_unchanged_when_switch_is_off(env, monkeypatch):
    _on(monkeypatch, on=False)
    conv = _conv()
    brain = StreamingClaude([[_text(["Purana ", "raasta."])]])
    evs = []
    out = asyncio.run(_run(conv, "hello", brain, evs))
    assert brain.streams == 0 and brain.creates == 1               # the old messages.create path
    assert not [e for e in evs if e["kind"] in ("reply_start", "delta", "reply_end")]
    msg = [e["payload"] for e in evs if e["kind"] == "message" and e["payload"]["role"] == "assistant"]
    assert msg == [{"role": "assistant", "text": "Purana raasta.", "source": "agent"}] and out == "Purana raasta."


def test_clean_holds_back_a_key_split_over_chunks():
    from app import livereply
    lv = livereply.Live.__new__(livereply.Live)
    lv.__init__("conv_x", "default")
    sent = []
    lv.streaming, lv.seg = True, 0
    import app.livereply as L
    orig = L.bus.publish_live
    L.bus.publish_live = lambda conv, kind, p: sent.append(p) or p
    try:
        for piece in ["Yeh rahi key ", "sk-ant-", "api03-", "Z" * 30, "ZZZZZZ", " aur kuch nahi, bas itna hi. " * 2]:
            lv.raw += piece
            lv.flush()
        lv.flush(final=True)
    finally:
        L.bus.publish_live = orig
    shown = "".join(p["text"] for p in sent)
    assert "sk-ant" not in shown and "ZZZ" not in shown and "[key hataya]" in shown


def test_api_live_retry_feedback_and_config(env, monkeypatch):
    _on(monkeypatch)
    from app import main
    from app.agent import set_client
    H = {"Authorization": f"Bearer {KEY}"}
    with TestClient(main.app) as c:
        assert c.get("/api/console/config").json()["stream"] is True
        conv = c.post("/api/conversations", headers=H).json()["id"]
        assert c.get(f"/api/conversations/{conv}/live", headers=H).status_code == 204
        # nothing to retry yet
        assert c.post(f"/api/conversations/{conv}/retry", headers=H).status_code == 404
        brain = StreamingClaude([[_text(["Pehla ", "jawab hai yeh. "])], [_text(["Doosra ", "behtar jawab. "])]])
        set_client(brain)
        assert c.post(f"/api/conversations/{conv}/messages", json={"text": "ek sawaal"}, headers=H).status_code == 202
        tl = c.get(f"/api/conversations/{conv}/timeline", headers=H).json()["events"]
        first = [e for e in tl if e["kind"] == "message" and e["payload"]["role"] == "assistant" and e["payload"].get("turn")]
        assert first and first[-1]["payload"]["text"].strip() == "Pehla jawab hai yeh."
        turn = first[-1]["payload"]["turn"]
        r = c.post(f"/api/conversations/{conv}/feedback", json={"turn": turn, "value": "down"}, headers=H)
        assert r.status_code == 200 and r.json()["value"] == "down"
        assert c.post(f"/api/conversations/{conv}/feedback", json={"turn": turn, "value": "meh"}, headers=H).status_code == 400
        r = c.post(f"/api/conversations/{conv}/retry", headers=H)
        assert r.status_code == 202 and r.json()["text"] == "ek sawaal"
        tl = c.get(f"/api/conversations/{conv}/timeline", headers=H).json()["events"]
        replies = [e["payload"]["text"].strip() for e in tl if e["kind"] == "message" and e["payload"]["role"] == "assistant"
                   and e["payload"].get("turn")]
        assert replies == ["Doosra behtar jawab."]                 # the retried reply replaces the old one
        users = [e for e in tl if e["kind"] == "message" and e["payload"]["role"] == "user"]
        assert len(users) == 1                                     # her message is not repeated
        # the model's history for the retry no longer holds the old answer, and carries the retry rule
        from app.agent.santosh import _load_history
        hist = json.dumps(_load_history(conv), ensure_ascii=False)
        assert "Pehla jawab" not in hist and "Doosra behtar jawab" in hist and "tapped Retry" in hist
        from app.livereply import feedback_counts
        assert feedback_counts("default") == {"up": 0, "down": 1}
        rep = c.get("/api/usage", headers=H)
        if rep.status_code == 200 and "replies" in rep.json():
            assert rep.json()["replies"]["down"] == 1


def test_a_block_shown_only_by_its_message_still_gets_its_own_seg():
    """A Gyaan answer is not streamed (no words fed): the next block must not reuse its seg number."""
    from app import livereply
    lv = livereply.Live("conv_y", "default")
    lv.block(stream=False)
    assert lv.tag() == {"turn": lv.turn, "seg": 0}
    lv.block()                      # a tool-only call has no words and no message: its number is reused
    lv.block()
    lv.feed("Doosra jawab yahan")
    assert lv.tag()["seg"] == 1
    assert lv.tag(new_block=True)["seg"] == 2
