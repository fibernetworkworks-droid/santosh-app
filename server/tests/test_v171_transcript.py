"""v0.171 Console v2 transcript power (phase 2): the model's thinking arrives as live-only `think` events (Claude
thinking_delta / GLM reasoning_content, cleaned and never stored), every step chip can open to a masked args brief
+ the work line's facts, and the whole chat exports as Markdown or JSON. Secrets never travel."""
import asyncio
import json
from types import SimpleNamespace

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

KEY = "owner-key-for-transcript-tests"
SECRET = "sk-ant-api03-" + "Q" * 40


def _on(monkeypatch, on=True):
    monkeypatch.setenv("CONSOLE_V2", "true" if on else "false")
    monkeypatch.setenv("API_KEY", KEY)
    from app.config import get_settings
    get_settings.cache_clear()


@pytest.fixture()
def _no_title(monkeypatch):
    """Auto-title would eat a scripted answer through the fake brain; tests here name their own chats."""
    from app.agent import pakka
    monkeypatch.setattr(pakka, "_ask", lambda *a, **k: asyncio.sleep(0, result="Ek sawaal") or "Ek sawaal")


def _conv():
    from app.db import Conversation, session
    with session() as s:
        c = Conversation(tenant_id="default")
        s.add(c)
        s.flush()
        return c.id


async def _run(conv, text, brain, collect):
    from app.agent import run_turn, set_client
    from app.events import bus
    set_client(brain)
    q = bus.subscribe(conv)
    out = await run_turn(conv, text, tenant_id="default")
    while not q.empty():
        collect.append(q.get_nowait())
    bus.unsubscribe(conv, q)
    return out


class _Ev(SimpleNamespace):
    pass


class _ThinkStream:
    """messages.stream(...) stand-in that also emits thinking_delta events before the text."""

    def __init__(self, blocks):
        self.blocks = blocks

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    def __aiter__(self):
        return self._events()

    async def _events(self):
        for b in self.blocks:
            yield _Ev(type="content_block_start", content_block=SimpleNamespace(type=b["type"]))
            for piece in b.pop("_think_pieces", None) or []:
                yield _Ev(type="content_block_delta", delta=SimpleNamespace(type="thinking_delta", thinking=piece))
            for piece in b.pop("_pieces", None) or [b.get("text", "")]:
                yield _Ev(type="content_block_delta", delta=SimpleNamespace(type="text_delta", text=piece))
            yield _Ev(type="content_block_stop")

    async def get_final_message(self):
        return SimpleNamespace(content=[{k: v for k, v in b.items() if not k.startswith("_")} for b in self.blocks],
                               stop_reason="tool_use" if any(b["type"] == "tool_use" for b in self.blocks) else "end_turn",
                               usage=SimpleNamespace(input_tokens=100, output_tokens=20), model="claude-test")


class StreamingClaude:
    def __init__(self, script):
        self.script = list(script)
        self.creates = 0
        self.messages = SimpleNamespace(stream=self._stream, create=self._create)

    def _stream(self, **kw):
        return _ThinkStream(self.script.pop(0))

    async def _create(self, **kw):
        self.creates += 1
        blocks = [{k: v for k, v in b.items() if not k.startswith("_")} for b in self.script.pop(0)]
        return SimpleNamespace(content=blocks, stop_reason="end_turn")


def _text(pieces):
    return {"type": "text", "text": "".join(pieces), "_pieces": list(pieces)}


def test_thinking_streams_cleaned_never_stored_final_text_unchanged(env, monkeypatch, _no_title):
    _on(monkeypatch)
    conv = _conv()
    think = ["Pehle GST ka matlab samajhna hai. ", "Key mili: " + SECRET[:12], SECRET[12:] + " hataani hai. ",
             "Ab jawab likhta hoon. " * 3]
    full = "Aapka GST return taiyaar hai. " * 3
    brain = StreamingClaude([[{"type": "thinking", "thinking": "".join(think), "_think_pieces": list(think)},
                              _text([full])]])
    evs = []
    out = asyncio.run(_run(conv, "gst?", brain, evs))
    thinks = [e for e in evs if e["kind"] == "think"]
    assert len(thinks) >= 2 and all(e["id"] == 0 and e.get("live") for e in thinks)
    shown = "".join(e["payload"]["text"] for e in thinks)
    assert "sk-ant" not in shown and "QQQQ" not in shown          # the key never reaches the card, even in thinking
    assert "samajhna" in shown
    segs = {e["payload"]["seg"] for e in thinks}
    assert segs == {0}
    final = [e for e in evs if e["kind"] == "message" and e["payload"]["role"] == "assistant"]
    assert len(final) == 1 and final[0]["payload"]["text"] == out == full   # thinking is never part of the answer
    from app.db import Event, session
    from app.events import STREAM_KINDS
    with session() as s:
        stored = [e.kind for e in s.scalars(select(Event).where(Event.conversation_id == conv)).all()]
    assert not set(stored) & STREAM_KINDS                          # live-only, like the deltas


def test_think_reset_clears_the_card_when_the_brain_fails_mid_thought(env, monkeypatch):
    from app import livereply
    lv = livereply.Live("conv_t", "default")
    lv.block()
    sent = []
    import app.livereply as L
    orig = L.bus.publish_live
    L.bus.publish_live = lambda conv, kind, p: sent.append((kind, p)) or p
    try:
        lv.feed_think("Soch raha hoon, yeh raha safad again " * 3)
        lv.think_flush(final=True)
        lv.reset()
    finally:
        L.bus.publish_live = orig
    kinds = [k for k, _ in sent]
    assert "think" in kinds
    clear = [p for k, p in sent if k == "think" and p.get("clear")]
    assert clear and clear[0]["seg"] == 0                          # the card empties, the next brain starts clean
    assert lv.tsent == "" and lv.traw == ""


def test_think_snapshot_resumes_a_reload_mid_thought(env, monkeypatch):
    from app import livereply
    lv = livereply.Live("conv_s", "default")
    lv.start()
    lv.block()
    import app.livereply as L
    orig = L.bus.publish_live
    L.bus.publish_live = lambda conv, kind, p: p
    try:
        lv.feed_think("Yeh soch liya hai. ")
        lv.think_flush(final=True)
        snap = livereply.snapshot("conv_s")
    finally:
        L.bus.publish_live = orig
        livereply._LIVE.pop("conv_s", None)
    assert snap["think"].startswith("Yeh soch liya hai.") and snap["text"] == ""


def test_step_events_carry_a_masked_args_brief(env, monkeypatch, _no_title):
    _on(monkeypatch)
    conv = _conv()
    first = [_text(["Reminder dekh raha hoon. " * 3]),
             {"type": "tool_use", "id": "tu_1", "name": "list_reminders", "input": {"when": "aaj", "limit": 5,
                                                                                    "api_key": SECRET, "note": "x"}}]
    second = [_text(["Koi reminder nahi. " * 3])]
    evs = []
    asyncio.run(_run(conv, "reminders?", StreamingClaude([first, second]), evs))
    steps = [e for e in evs if e["kind"] == "step" and e["payload"].get("state") != "running"]
    assert steps
    args = steps[0]["payload"].get("args")
    assert isinstance(args, list) and args
    flat = json.dumps(args, ensure_ascii=False)
    assert "sk-ant" not in flat and "api_key" not in [a[0] for a in args]     # the secret key is dropped outright
    assert ("when", "aaj") in [tuple(a) for a in args]


def test_args_brief_drops_secrets_and_marks_multiline():
    from app.livework import args_brief
    args = {"to": "meghana@newtika.in", "password": "hunter2", "upi_pin": "123456", "body": "line1\nline2\nline3",
            "items": ["a", "b", "c"], "meta": {"x": 1}, "empty": "", "note": "1234567890123456"}
    out = args_brief(args)
    d = {k: v for k, v in out}
    assert "password" not in d and "upi_pin" not in d               # secret-looking keys never travel
    assert d["to"] == "meghana@newtika.in"
    assert d["body"].startswith("3 lines · line1")
    assert d["items"] == "3 ×"
    assert d["meta"] == "1 fields"
    assert "empty" not in d
    assert "••••" in d["note"]                                      # long digit runs are masked like everywhere
    assert len(out) <= 6


def _sse(*objs):
    return b"".join(b"data: " + json.dumps(o).encode() + b"\n\n" for o in objs) + b"data: [DONE]\n\n"


def test_glm_reasoning_content_goes_to_on_think_never_into_text(monkeypatch):
    from app.agent import llm
    got, think = [], []
    body = _sse({"choices": [{"delta": {"reasoning_content": "Pehle sochta hoon "}}]},
                {"choices": [{"delta": {"reasoning_content": "phir likhta hoon. "}}]},
                {"choices": [{"delta": {"content": "Yeh jawab hai."}}]})
    llm.set_http(httpx.AsyncClient(transport=httpx.MockTransport(
        lambda req: httpx.Response(200, headers={"content-type": "text/event-stream"}, content=body))))
    try:
        blocks, stop, usage = asyncio.run(llm.openai_stream("glm", "sys", [], [{"role": "user", "content": "hi"}],
                                                            100, got.append, on_think=think.append))
    finally:
        llm.set_http(None)
    assert think == ["Pehle sochta hoon ", "phir likhta hoon. "]
    assert got == ["Yeh jawab hai."]
    assert "".join(b.get("text", "") for b in blocks if b.get("type") == "text") == "Yeh jawab hai."


def _seed_conv_events(conv):
    """A small real story: her message, two steps, the reply, an old replaced branch."""
    from app.db import Event, session
    from app.events import bus
    bus.publish(conv, "message", {"role": "user", "text": "Bijli ka bill bharo", "source": "user"})
    bus.publish(conv, "step", {"tool": "fetch_bill", "label": "Bill nikala", "state": "done", "id": "c1",
                               "args": [["provider", "BESCOM"], ["account", "••••8901"]]})   # santosh.py publishes them masked
    bus.publish(conv, "step", {"tool": "pay_bill", "label": "Bill bhara", "state": "running", "id": "c1"})
    bus.publish(conv, "message", {"role": "assistant", "text": "Purana jawab", "turn": "t_old", "replaced_by": "retry"})
    bus.publish(conv, "message", {"role": "assistant", "text": "Bill bhar diya, ₹1,240 gaya.", "source": "agent",
                                  "turn": "t_new", "seg": 0})
    with session() as s:
        return s.scalars(select(Event).where(Event.conversation_id == conv).order_by(Event.id)).all()


def test_export_markdown_reads_like_the_chat(env, monkeypatch):
    _on(monkeypatch)
    conv = _conv()
    _seed_conv_events(conv)
    from app.main import app
    H = {"Authorization": f"Bearer {KEY}"}
    with TestClient(app) as c:
        r = c.get(f"/api/conversations/{conv}/export", headers=H)
        assert r.status_code == 200 and "text/markdown" in r.headers["content-type"]
        assert "attachment" in r.headers["content-disposition"] and r.headers["content-disposition"].endswith('.md"')
        md = r.text
        assert "# " in md and "## Aap ·" in md and "Bijli ka bill bharo" in md
        assert "Bill bhar diya, ₹1,240 gaya." in md
        assert "✓ Bill nikala `fetch_bill`" in md
        assert "••••8901" in md                                    # the masked account, not the raw one
        assert "Purana jawab" not in md                            # the replaced retry branch stays out
        assert "state" not in md                                   # running steps are never listed


def test_export_json_keeps_every_stored_event(env, monkeypatch):
    _on(monkeypatch)
    conv = _conv()
    rows = _seed_conv_events(conv)
    from app.main import app
    H = {"Authorization": f"Bearer {KEY}"}
    with TestClient(app) as c:
        r = c.get(f"/api/conversations/{conv}/export?fmt=json", headers=H)
        assert r.status_code == 200 and "application/json" in r.headers["content-type"]
        data = json.loads(r.text)
        from app.main import APP_VERSION
        assert data["conversation"] == conv and data["version"] == APP_VERSION   # stamps the server's APP_VERSION
        assert len(data["events"]) == len(rows)
        kinds = [e["kind"] for e in data["events"]]
        assert "message" in kinds and "step" in kinds and "typing" not in kinds
        assert c.get(f"/api/conversations/{conv}/export", headers=H, params={"fmt": "yaml"}).status_code == 200  # md default
    # without a key: no export
    with TestClient(app) as c:
        assert c.get(f"/api/conversations/{conv}/export").status_code == 401


def test_timeline_steps_flag_keeps_the_transcript_alive(env, monkeypatch):
    """v0.171: the console asks for steps=1 and the transcript keeps what each turn did; the phone (no param)
    sees exactly the old story — running + done of one call collapse to the latest."""
    _on(monkeypatch)
    conv = _conv()
    _seed_conv_events(conv)
    from app.main import app
    H = {"Authorization": f"Bearer {KEY}"}
    with TestClient(app) as c:
        base = c.get(f"/api/conversations/{conv}/timeline", headers=H).json()["events"]
        assert not [e for e in base if e["kind"] == "step"]            # default: unchanged for the phone
        st = c.get(f"/api/conversations/{conv}/timeline", headers=H, params={"steps": "1"}).json()["events"]
        steps = [e for e in st if e["kind"] == "step"]
        assert len(steps) == 1 and steps[0]["payload"]["state"] == "done" and steps[0]["payload"]["args"]
        kinds = [e["kind"] for e in st]
        assert kinds.index("step") > kinds.index("message")            # in order, where it happened


def test_export_off_when_the_switch_is_off(env, monkeypatch):
    _on(monkeypatch, on=False)
    monkeypatch.setenv("CONSOLE_STREAM", "false")
    from app.config import get_settings
    get_settings.cache_clear()
    conv = _conv()
    from app.main import app
    H = {"Authorization": f"Bearer {KEY}"}
    with TestClient(app) as c:
        assert c.get(f"/api/conversations/{conv}/export", headers=H).status_code == 404
