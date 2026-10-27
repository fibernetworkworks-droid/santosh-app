"""v0.185.4 "PC par kaam ruk gaya" — root-caused live on the VPS (26 Oct 13:40 + 13:42) and fixed.

THE BUG: at the end of every action round the loop attaches the fresh screenshot INSIDE the last tool_result.
When that result was an error (is_error=true — REFUSED shortcuts, idvault refusals, held_blind guard, a busy
PC's ERROR), the screenshot's image block rode inside an is_error result, the Anthropic API rejected the WHOLE
next request with 400 'messages.N.tool_result: all content must be type `text` if `is_error` is true', and
_run's outer handler marked the task failed — Hoola said "Aapke PC par kaam ruk gaya" a few steps into nearly
every real task.

THE FIX, three layers:
1. the producer: the flag is dropped before the screenshot rides in (the error text itself stays);
2. the invariant: _sanitize() flattens any is_error result that carries non-text blocks, over the whole
   history, before every model call (a task started on an older build can carry one);
3. resilience: one 400 (sanitize + retry) or transient connection / 429 / 5xx / 529 failure no longer kills a
   20-minute task, and a single busy screenshot no longer does either (one retry).

Server-side tests run the real operator loop against FakePC + a scripted Claude (same style as
test_v0185_pc_browser.py).
"""
import asyncio
import base64
import sys
import types
from pathlib import Path

import pytest

from tests.test_bazar import _events, _notices, bz  # noqa: F401

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "desktop"))

JPEG = base64.b64encode(b"\xff\xd8\xff\xe0fakejpeg").decode()


class FakePC:
    def __init__(self):
        self.calls = []

    async def __call__(self, op, action, args=None, timeout=40, log=True):
        args = dict(args or {})
        self.calls.append((action, args))
        if action == "screen":
            return {"image_b64": JPEG, "width": 1280, "height": 720, "active_window": "IRCTC - Google Chrome",
                    "windows": ["IRCTC - Google Chrome"], "monitor": args.get("monitor", "primary")}
        return {"ok": True}


def tu(i, tool, **inp):
    return types.SimpleNamespace(model_dump=lambda exclude_none=True: {"type": "tool_use", "id": f"t{i}", "name": tool, "input": inp})


def txt(t):
    return types.SimpleNamespace(model_dump=lambda exclude_none=True: {"type": "text", "text": t})


class FlakyClaude:
    """Scripted Claude that raises `boom` on the first `fail_times` calls before playing its script."""

    def __init__(self, script, boom=None, fail_times=0):
        self.script = list(script)
        self.boom = boom
        self.fail_left = fail_times
        self.calls = 0
        self.seen = []
        self.messages = self

    async def create(self, **kw):
        self.calls += 1
        self.seen.append(kw)
        if self.fail_left > 0:
            self.fail_left -= 1
            raise self.boom
        return types.SimpleNamespace(content=self.script.pop(0))


@pytest.fixture
def op(bz, monkeypatch):  # noqa: F811
    from app.pc import operator
    pc = FakePC()
    monkeypatch.setattr(operator, "_pc", pc)

    class Conn:
        info = {"control": True}
    from app.pc.hub import hub
    monkeypatch.setattr(hub, "is_online", lambda t, d=None: True)
    monkeypatch.setattr(hub, "online", lambda t: [Conn()])
    yield operator, pc, bz


def _wire_claude(monkeypatch, claude):
    import app.agent.santosh as s
    monkeypatch.setattr(s, "get_client", lambda: claude)


def _bad_request():
    import anthropic, httpx
    req = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    resp = httpx.Response(400, request=req)
    return anthropic.BadRequestError(
        "Error code: 400 - {'type': 'error', 'error': {'type': 'invalid_request_error', 'message': "
        "'messages.4.content.1.tool_result: all content must be type `text` if `is_error` is true'}}",
        response=resp, body=None)


def _conn_error():
    import anthropic, httpx
    return anthropic.APIConnectionError(request=httpx.Request("POST", "https://api.anthropic.com/v1/messages"))


def _invariant_violations(messages):
    """Every is_error tool_result must carry text and nothing else — the exact rule the API enforces."""
    bad = []
    for mi, m in enumerate(messages):
        if m.get("role") != "user" or not isinstance(m.get("content"), list):
            continue
        for ci, b in enumerate(m["content"]):
            if isinstance(b, dict) and b.get("type") == "tool_result" and b.get("is_error"):
                c = b.get("content")
                if not (isinstance(c, str) or all(isinstance(x, dict) and x.get("type") == "text" for x in (c or []))):
                    bad.append(f"messages.{mi}.content.{ci}")
    return bad


def run(coro):
    return asyncio.run(coro)


# ---------------- the producer: error result + round-end screenshot ----------------

def test_error_result_survives_the_round_end_screenshot(op, monkeypatch):
    """A blocked shortcut (is_error, last tool of the round) must not poison the next model call: the flag is
    dropped before the screenshot rides in, the task goes on and finishes — it does NOT die as 'ruk gaya'."""
    operator, pc, bz = op
    from app.pc import operator as O
    claude = FlakyClaude([
        [tu(0, "key", keys="win+r")],                       # REFUSED -> is_error result, last of the round
        [tu(1, "done", answer="ho gaya", success=True)],
    ])
    _wire_claude(monkeypatch, claude)
    r = run(O.start("default", "conv1", "notepad kholo", wait=20))
    assert r["status"] == "done", r
    assert len(claude.seen) == 2
    # the rewritten error result now carries the fresh screenshot WITHOUT the is_error flag, text intact
    last_user = [m for m in claude.seen[1]["messages"] if m["role"] == "user"][-1]
    tr = [b for b in last_user["content"] if b.get("type") == "tool_result"]
    assert tr, "the error result should still be there"
    body = tr[-1]
    assert "is_error" not in body, "screenshot rode inside an is_error result -> the API 400s the next call"
    kinds = [b.get("type") for b in body["content"]]
    assert "image" in kinds and any("REFUSED" in b.get("text", "") for b in body["content"] if b.get("type") == "text")
    # and the invariant holds over the whole history the API is about to see
    assert _invariant_violations(claude.seen[1]["messages"]) == []


def test_pure_error_result_keeps_its_flag(op, monkeypatch):
    """An is_error result that does NOT get a screenshot attached stays is_error (the API allows text-only)."""
    operator, pc, bz = op
    from app.pc import operator as O
    claude = FlakyClaude([
        [tu(0, "key", keys="win+r"), tu(1, "click", x=10, y=10)],   # error FIRST, a clean click LAST
        [tu(2, "done", answer="ho gaya", success=True)],
    ])
    _wire_claude(monkeypatch, claude)
    r = run(O.start("default", "conv2", "notepad kholo", wait=20))
    assert r["status"] == "done", r
    last_user = [m for m in claude.seen[1]["messages"] if m["role"] == "user"][-1]
    trs = [b for b in last_user["content"] if b.get("type") == "tool_result"]
    assert len(trs) == 2
    assert trs[0].get("is_error") is True and isinstance(trs[0]["content"], str)   # untouched, legal
    assert "image" in [b.get("type") for b in trs[1]["content"]] and "is_error" not in trs[1]


# ---------------- the invariant: _sanitize ----------------

def test_sanitize_flattens_image_inside_error_result():
    from app.pc import operator as O
    img = {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": JPEG}}
    msgs = [{"role": "user", "content": [
        {"type": "tool_result", "tool_use_id": "t1", "is_error": True,
         "content": [{"type": "text", "text": "REFUSED: no"}, img]}]}]
    O._sanitize(msgs)
    b = msgs[0]["content"][0]
    assert isinstance(b["content"], str) and "REFUSED" in b["content"]
    assert "1 screenshot" in b["content"] and b.get("is_error") is True
    assert _invariant_violations(msgs) == []


def test_sanitize_leaves_legal_results_alone():
    from app.pc import operator as O
    img = {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": JPEG}}
    ok_text = {"type": "tool_result", "tool_use_id": "t1", "is_error": True, "content": "typed"}
    ok_shot = {"type": "tool_result", "tool_use_id": "t2", "content": [{"type": "text", "text": "looked"}, img]}
    msgs = [{"role": "user", "content": [ok_text, ok_shot]}]
    O._sanitize(msgs)
    assert msgs[0]["content"][0] is ok_text and msgs[0]["content"][0]["content"] == "typed"
    assert msgs[0]["content"][1] is ok_shot and "image" in [b["type"] for b in ok_shot["content"]]


# ---------------- resilience: one bad API call is no longer the end ----------------

def test_one_400_no_longer_kills_the_task(op, monkeypatch):
    """The EXACT VPS shape: a 400 invalid_request on a mid-task call (a history built by the old code) —
    the history is sanitized once, the SAME call is retried, the task plays out to done."""
    operator, pc, bz = op
    from app.pc import operator as O
    claude = FlakyClaude([
        [tu(0, "key", keys="win+r")],
        [tu(1, "done", answer="ho gaya", success=True)],
    ], boom=_bad_request(), fail_times=1)
    _wire_claude(monkeypatch, claude)
    r = run(O.start("default", "conv3", "notepad kholo", wait=20))
    assert r["status"] == "done", r
    assert claude.calls == 3          # 400 -> sanitize -> same call again -> next turn
    assert _invariant_violations(claude.seen[-1]["messages"]) == []


def test_one_connection_error_no_longer_kills_the_task(op, monkeypatch):
    operator, pc, bz = op
    from app.pc import operator as O
    claude = FlakyClaude([
        [tu(0, "done", answer="seedha done", success=True)],
    ], boom=_conn_error(), fail_times=1)
    _wire_claude(monkeypatch, claude)
    r = run(O.start("default", "conv4", "notepad kholo", wait=20))
    assert r["status"] == "done", r
    assert claude.calls == 2          # connection error -> retry -> answer


def test_screenshot_blip_no_longer_kills_the_task(op, monkeypatch):
    """One busy screen capture (the round-end screenshot raising once) must not fail the whole task."""
    operator, pc, bz = op
    from app.pc import operator as O
    claude = FlakyClaude([
        [tu(0, "key", keys="win+r")],               # a real round: error result, then the round-end screenshot
        [tu(1, "done", answer="ho gaya", success=True)],
    ])
    _wire_claude(monkeypatch, claude)

    real_pc = O._pc
    state = {"n": 0}

    async def flaky_screen(op_, action, args=None, timeout=40, log=True):
        if action == "screen":
            state["n"] += 1
            if state["n"] == 2:       # the round-end capture, once
                raise RuntimeError("The PC did not answer in time")
        return await real_pc(op_, action, args, timeout=timeout, log=log)

    monkeypatch.setattr(O, "_pc", flaky_screen)
    r = run(O.start("default", "conv5", "notepad kholo", wait=20))
    assert r["status"] == "done", r
    assert state["n"] >= 3            # the failed capture was retried and answered
