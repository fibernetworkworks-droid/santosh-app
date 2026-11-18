"""v0.976 HOOLA PIPELINE P6 (built as 0.975) - the receipt line under a reply: which model did which part (plan section 10, P6).
Fake models only, no network."""
from __future__ import annotations

import asyncio
import importlib.util
import pathlib

_spec = importlib.util.spec_from_file_location(
    "_p4", pathlib.Path(__file__).with_name("test_v0969_pipeline_p4.py"))
_p4 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_p4)
box = _p4.box
ROOT = pathlib.Path(__file__).resolve().parents[2]
BANNED = 'OpenRouter error 403: {"error":{"message":"Model a/mid1 is banned","code":403}}'


def _capture(monkeypatch):
    from app.events import bus
    seen = []
    real = bus.publish

    def pub(conv, kind, payload, *a, **k):
        if kind == "model_receipt":
            seen.append((conv, payload))
        return real(conv, kind, payload, *a, **k)
    monkeypatch.setattr(bus, "publish", pub)
    return seen


def test_pretty_names():
    from app.pipeline.receipt import pretty
    assert pretty("anthropic/claude-opus-4.6") == "Claude Opus 4.6"
    assert pretty("z-ai/glm-5.3-flash") == "GLM 5.3 Flash"
    assert pretty("google/gemini-3.1-pro-preview") == "Gemini 3.1 Pro"
    assert pretty("openai/gpt-5.4") == "GPT 5.4"
    assert pretty("google/gemini-4-carbon-20261110") == "Gemini 4 Carbon"


def test_a_box_reply_gets_one_receipt_line(box, monkeypatch):
    seen = _capture(monkeypatch)
    b = box.begin("c1", "t1", "hi")
    box.end(b, "Namaste")
    assert len(seen) == 1
    conv, r = seen[0]
    assert conv == "c1"
    assert r["say"] == "Answer: Mid1"
    assert r["parts"][0]["model"] == "a/mid1" and r["parts"][0]["level"] == "MID"
    assert r["handovers"] == 0


def test_a_hand_over_names_the_model_that_took_over(box, monkeypatch):
    from app.pipeline import runner as R
    seen = _capture(monkeypatch)
    b = box.begin("c2", "t1", "hi")
    asyncio.run(R.call(R.HAND.get(), _p4._maker({"a/mid1": _p4.boom(BANNED), "b/mid2": _p4.ok()}, [])))
    box.end(b, "ok")
    r = seen[-1][1]
    part = r["parts"][0]
    assert part["model"] == "b/mid2"                        # what really answered
    assert part["chosen"]                                   # the first pick, kept for the details
    assert r["handovers"] == 1
    assert part["handover"][0]["why"] == "it failed"
    assert "Mid2" in r["say"]


def test_a_turn_not_through_the_box_gets_no_receipt(box, monkeypatch):
    seen = _capture(monkeypatch)
    b = box.begin("c3", "t1", "hi", actor="team")           # not a Box turn: today's model, which the Box did not choose
    box.end(b, "ok")
    assert seen == []


def test_the_switch_turns_it_off(box, monkeypatch):
    from app.config import get_settings
    monkeypatch.setenv("PIPELINE_RECEIPT", "false")
    get_settings.cache_clear()
    seen = _capture(monkeypatch)
    b = box.begin("c4", "t1", "hi")
    box.end(b, "ok")
    assert seen == []


def test_several_parts_group_by_label_and_model():
    from app.pipeline.receipt import build
    m = lambda i: {"id": i, "route": "openrouter"}          # noqa: E731
    sh = {"id": "s1", "multi": True, "parts": [
        {"n": 1, "kind": "research", "label": "Research", "applied": True, "model": m("anthropic/claude-sonnet-4.6"),
         "ran_on": "anthropic/claude-sonnet-4.6", "level": "MID", "state": "done"},
        {"n": 2, "kind": "research", "label": "Research", "applied": True, "model": m("anthropic/claude-sonnet-4.6"),
         "ran_on": "anthropic/claude-sonnet-4.6", "level": "MID", "state": "done"},
        {"n": 3, "kind": "image.make", "label": "Picture", "applied": False, "model": m("x/img"), "state": "done"},
        {"n": 4, "kind": "write", "label": "Writing", "applied": True, "model": m("anthropic/claude-opus-4.6"),
         "level": "HIGH", "state": "waiting_tap"}]}
    r = build(sh)
    assert r["say"] == "Research: Claude Sonnet 4.6 (2 parts) · Writing: Claude Opus 4.6"
    assert [p["n"] for p in r["parts"]] == [1, 2, 4]          # the part the Box did not run is left out
    assert r["parts"][-1]["note"] == "waiting for your tap"


def test_the_receipt_stays_in_its_own_chat_and_is_not_pushed():
    from app import events, push
    assert "model_receipt" in events.LOCAL_KINDS and "model_receipt" in events.CALL_ONLY_KINDS
    assert "model_receipt" not in push.PUSH_KINDS


def test_console_and_phone_draw_it():
    js = (ROOT / "server/app/static/console/v2.js").read_text()
    assert "kind === 'model_receipt'" in js and "Made with" in js and "'maps_places', 'ledger', 'model_receipt'" in js
    assert ".mreceipt" in (ROOT / "server/app/static/console/v2.css").read_text()
    state = (ROOT / "lib/state.dart").read_text()
    assert "case 'model_receipt':" in state and "FeedItem('model_receipt'" in state
    assert "ModelReceiptLine(" in (ROOT / "lib/ui/chat_screen.dart").read_text()
    new = (ROOT / "lib/ui/chat/hoola_cards_all.dart").read_text()
    assert "case 'model_receipt':" in new and "ModelReceiptLine(" in new
    w = (ROOT / "lib/ui/model_receipt.dart").read_text()
    assert "took over from" in w and "minHeight: 44" in w


def test_version():
    src = (ROOT / "server/app/main.py").read_text()
    assert "v0.976.0 HOOLA PIPELINE P6" in (ROOT / "docs/HISTORY.md").read_text()   # later stories drop it from main.py
