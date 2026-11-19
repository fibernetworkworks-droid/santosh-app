"""The worker card (server/tools/worker_card.py): checkers, the Box-shaped call and the picks rule, no network."""
import asyncio
import importlib.util
import json
from pathlib import Path

import httpx
import pytest

_P = Path(__file__).resolve().parents[1] / "tools" / "worker_card.py"
_spec = importlib.util.spec_from_file_location("worker_card", _P)
W = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(W)


def test_checkers_pass_right_and_fail_wrong_answers():
    assert W.selftest() == 0


def test_every_job_has_a_checker_and_a_kind():
    for t in W.TASKS:
        ok, why = W.check(t["id"], "", [])
        assert why != "unknown job", t["id"]
        assert t["kind"] and t["max"] > 0


def test_code_guard_refuses_unsafe_code_before_running():
    assert "imports" in W._code_safe("import os\ndef inr_to_int(s): return 1")
    assert "uses" in W._code_safe("def inr_to_int(s): return eval(s)")
    assert "__class__" in W._code_safe("def inr_to_int(s): return s.__class__")
    assert W._code_safe("import re\ndef inr_to_int(s):\n    return 1") == ""


def _sse(chunks):
    return "".join("data: " + json.dumps(c) + "\n\n" for c in chunks) + "data: [DONE]\n\n"


def test_call_sends_the_box_shape_and_reads_the_stream():
    seen = {}

    def handler(req: httpx.Request):
        seen["body"] = json.loads(req.content)
        body = _sse([
            {"provider": "Wafer", "choices": [{"delta": {"reasoning": "thinking"}}]},
            {"provider": "Wafer", "choices": [{"delta": {"content": "Profit Rs 28,500, "}}]},
            {"provider": "Wafer", "choices": [{"delta": {"content": "margin 15.49%"}}]},
            {"provider": "Wafer", "choices": [], "usage": {"prompt_tokens": 90, "completion_tokens": 40, "cost": 0.0002,
                                                           "completion_tokens_details": {"reasoning_tokens": 12}}},
        ])
        return httpx.Response(200, text=body, headers={"content-type": "text/event-stream"})

    async def go():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as c:
            return await W.call(c, "k", "z-ai/glm-5.3", W.TASKS[0], "latency", "")

    out = asyncio.run(go())
    b = seen["body"]
    assert b["provider"] == {"sort": "latency"} and b["reasoning"] == {"effort": "low", "exclude": False}
    assert b["stream"] is True and b["usage"] == {"include": True} and b["max_tokens"] == 900 + W.REASONING_ROOM
    assert out["text"] == "Profit Rs 28,500, margin 15.49%" and out["provider"] == "Wafer"
    assert out["usage"]["cost"] == 0.0002 and out["first_any"] is not None
    assert W.check("math_profit", out["text"], out["tools"])[0]


def test_call_collects_tool_calls_and_stops_on_a_key_limit():
    def tools(req):
        return httpx.Response(200, headers={"content-type": "text/event-stream"}, text=_sse([
            {"choices": [{"delta": {"tool_calls": [{"index": 0, "function": {"name": "web_search", "arguments": "{\"qu"}}]}}]},
            {"choices": [{"delta": {"tool_calls": [{"index": 0, "function": {"arguments": "ery\": \"gold rate\"}"}}]}}]},
        ]))

    def limit(req):
        return httpx.Response(403, text='{"error":{"message":"Key limit exceeded (total limit)"}}')

    async def go(h, task):
        async with httpx.AsyncClient(transport=httpx.MockTransport(h)) as c:
            return await W.call(c, "k", "m", task, "latency", "")

    t = next(x for x in W.TASKS if x["id"] == "tool_needed")
    out = asyncio.run(go(tools, t))
    assert out["tools"] == [{"name": "web_search", "arguments": '{"query": "gold rate"}'}]
    assert W.check("tool_needed", out["text"], out["tools"])[0]
    with pytest.raises(W.Stop):
        asyncio.run(go(limit, t))


def test_picks_rule_needs_every_run_and_takes_the_cheapest_then_another_company():
    rows = []
    for mid, inr, ok in (("a/cheap", 0.05, True), ("a/cheap2", 0.06, True), ("b/other", 0.20, True),
                         ("c/flaky", 0.01, False)):
        for run in range(3):
            for tid in ("math_profit", "math_gst"):
                rows.append({"model": mid, "task": tid, "kind": "working out", "run": run, "routing": "box",
                             "ok": ok or run > 0, "why": "x", "provider": "P", "secs": 2.0, "first_any": 1.0,
                             "first_word": 1.5, "inr": inr, "reason_tok": 10, "error": ""})
    card = {"at": 0, "box_sort": "latency", "budget_inr": 400, "spent_inr": 1.0, "calls_planned": 24,
            "calls_done": 24, "stopped": "", "rows": rows,
            "models": [["a/cheap", "cand", "A"], ["a/cheap2", "cand", "A"], ["b/other", "cand", "B"],
                       ["c/flaky", "cand", "C"]]}
    rep = W.report(card)
    line = next(ln for ln in rep.splitlines() if ln.strip().startswith("working out"))
    assert "main a/cheap" in line and "backup b/other" in line and "c/flaky" not in line
    assert "3 models passed every run" in line


def test_whole_card_runs_end_to_end_on_a_fake_openrouter(monkeypatch, tmp_path):
    """Every job goes out once per run, the ceiling and the saved report hold, nothing needs the network."""
    answers = {"math_profit": "Profit 28,500, margin 15.49%", "math_gst": "CGST 405 SGST 405 total 5,310"}

    def handler(req: httpx.Request):
        if req.method == "GET":
            return httpx.Response(200, json={"data": [
                {"id": "x/one", "architecture": {"input_modalities": ["text", "image"]},
                 "pricing": {"prompt": "0.0000001", "completion": "0.0000002"}},
                {"id": "y/two", "architecture": {"input_modalities": ["text"]},
                 "pricing": {"prompt": "0.000001", "completion": "0.000002"}}]})
        b = json.loads(req.content)
        tid = next(t["id"] for t in W.TASKS if t["msgs"][-1]["content"] == b["messages"][-1]["content"]
                   or (isinstance(b["messages"][-1]["content"], list) and t.get("image")))
        return httpx.Response(200, headers={"content-type": "text/event-stream"}, text=_sse([
            {"provider": "P", "choices": [{"delta": {"content": answers.get(tid, "no")}}]},
            {"provider": "P", "choices": [], "usage": {"cost": 0.0001 if b["model"] == "x/one" else 0.001}}]))

    real = httpx.AsyncClient
    monkeypatch.setattr(W.httpx if hasattr(W, "httpx") else httpx, "AsyncClient",
                        lambda *a, **k: real(transport=httpx.MockTransport(handler)))
    monkeypatch.setattr(W, "_key", lambda: "k")
    monkeypatch.setattr(W, "_box_sort", lambda: "latency")
    monkeypatch.setattr(W, "MODELS", [("x/one", "cand", "X"), ("y/two", "ref", "Y"), ("z/gone", "cand", "Z")])
    monkeypatch.chdir(tmp_path)
    card = asyncio.run(W.run_card(400, 600, []))
    n = len(W.TASKS)
    # x/one: 3 Box runs + 1 cheapest run of every job; y/two (reference, no pictures): 1 run of every job but the picture
    assert card["calls_done"] == card["calls_planned"] == 4 * n + (n - 1)
    assert card["missing"] == ["z/gone"] and card["stopped"] == ""
    assert {r["routing"] for r in card["rows"] if r["model"] == "x/one"} == {"box", "cheapest"}
    rep = W.report(card)
    assert "working out" in rep and "main x/one" in rep
    p = W._save(card)
    assert Path(p).exists()
