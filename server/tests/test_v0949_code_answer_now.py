"""v0.949 HOOLA CODE ANSWER NOW (owner: "DONE CHECK" on the hard card after v0.948 = 11/12): the JS lock-file fix held,
but the vague ask still came back empty on high, medium AND low effort (finish=length every time). Three empty answers
now get two last tries told to answer now: thinking off, then thinking low if the model refuses to run without it."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _setup(monkeypatch, post):
    from app.devsahayak import brain as B
    import time as _t
    monkeypatch.setattr(B, "QWEN_POST", post)
    monkeypatch.setattr(B, "_or_key", lambda: "k")
    monkeypatch.setattr(_t, "sleep", lambda s: None)
    return B


EMPTY = {"choices": [{"finish_reason": "length", "message": {"role": "assistant", "content": ""}}]}
ASK = {"choices": [{"finish_reason": "stop", "message": {"role": "assistant", "content": "Which part of checkout is wrong?"}}],
       "usage": {}}


def test_three_empty_answers_get_a_try_with_thinking_off_told_to_answer_now(monkeypatch):
    bodies = []

    def post(url, body, headers, timeout):
        bodies.append(body)
        return EMPTY if len(bodies) <= 3 else ASK
    B = _setup(monkeypatch, post)
    blocks, stop = B._qwen_call("sys", [{"role": "user", "content": "Checkout mein kuch gadbad hai"}], [], 2000, True)
    assert blocks[0]["text"] == "Which part of checkout is wrong?"
    last = bodies[3]
    assert last["reasoning"] == {"enabled": False} and last["max_tokens"] == 2000 + B.ROOM["high"]
    assert last["messages"][-1] == {"role": "user", "content": B.ANSWER_NOW}
    assert all(b["messages"][-1]["content"] != B.ANSWER_NOW for b in bodies[:3])     # her conversation is not changed


def test_a_model_that_needs_thinking_gets_the_low_try_next(monkeypatch):
    bodies = []

    def post(url, body, headers, timeout):
        bodies.append(body)
        if len(bodies) <= 3:
            return EMPTY
        if body["reasoning"] == {"enabled": False}:
            from app.devsahayak.brain import QwenError
            raise QwenError("OpenRouter answered 400: Reasoning is mandatory for this endpoint")
        return ASK
    B = _setup(monkeypatch, post)
    blocks, _ = B._qwen_call("sys", [{"role": "user", "content": "x"}], [], 2000, True)
    assert blocks and bodies[4]["reasoning"] == {"effort": "low", "exclude": True}
    assert bodies[4]["messages"][-1]["content"] == B.ANSWER_NOW


def test_other_failures_do_not_get_the_answer_now_tries(monkeypatch):
    n = {"c": 0}

    def post(url, body, headers, timeout):
        n["c"] += 1
        raise TimeoutError("read timed out")
    B = _setup(monkeypatch, post)
    try:
        B._qwen_call("sys", [{"role": "user", "content": "x"}], [], 2000, True)
        raise AssertionError("must fail")
    except B.QwenError as e:
        assert "timed out" in str(e)
    assert n["c"] == 3


def test_still_empty_after_every_try_says_so(monkeypatch):
    n = {"c": 0}

    def post(url, body, headers, timeout):
        n["c"] += 1
        return EMPTY
    B = _setup(monkeypatch, post)
    try:
        B._qwen_call("sys", [{"role": "user", "content": "x"}], [], 2000, True)
        raise AssertionError("must fail")
    except B.QwenError as e:
        assert "empty answer" in str(e)
    assert n["c"] == 5


def test_version():
    main = (ROOT / "server/app/main.py").read_text()
    assert 'APP_VERSION = "0.999.63"' in main
    assert "version: 0.999.63+1061" in (ROOT / "pubspec.yaml").read_text()
