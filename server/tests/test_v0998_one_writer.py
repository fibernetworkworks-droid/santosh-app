"""v0.998 C1 ONE WRITER, SEVERAL WORKERS, SEVERAL CHECKERS (owner: "GO C1 -- 1 WRITER, SEVERAL WORKER, SEVRAL
CHECKER"). The model that talks to her is chosen once per chat and kept; it changes only for a reason she is told in
one line; the draft is checked by code + a model of another company BEFORE it is hers, and a problem goes back to the
same writer inside the one reply - never a second "correction" message. Fake models only, no network."""
from __future__ import annotations

import asyncio
import importlib.util
import json
import pathlib

import pytest

from tests.test_v0186_long_goal import gz, txt  # noqa: F401
from tests.test_bazar import bz  # noqa: F401

_spec = importlib.util.spec_from_file_location(
    "_p4", pathlib.Path(__file__).with_name("test_v0969_pipeline_p4.py"))
_p4 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_p4)
box = _p4.box          # the P4 fixture: tables on disk, Box on, OpenRouter brain, fake providers


def _r(mid, level="MID", kind="chat", backups=("b/mid2", "c/mid3")):
    M = _p4.M
    return {"model": M(mid), "backups": [M(b) for b in backups], "level": level, "level_used": level, "kind": kind,
            "language": "en"}


# ------------------------------------------------------------------ the writer: chosen once, kept
def test_the_first_message_pins_a_writer_at_least_mid(box):
    from app.pipeline import writer as WR
    d = WR.decide("w1", _r("a/low1", "LOW"), doc=_p4._doc(), health={})
    assert d["event"] == "pinned" and d["model"]["id"] == "a/mid1" and d["level"] == "MID" and not d["note"]
    assert WR.get("w1")["model"] == "a/mid1"


def test_a_later_message_keeps_the_writer_even_when_the_box_would_pick_another(box):
    from app.pipeline import writer as WR
    WR.decide("w2", _r("a/mid1"), doc=_p4._doc(), health={})
    d = WR.decide("w2", _r("b/mid2", backups=("c/mid3", "a/mid1")), doc=_p4._doc(), health={})
    assert d["event"] == "kept" and d["model"]["id"] == "a/mid1" and not d["note"]
    assert "a/mid1" not in [b["id"] for b in d["backups"]] and "b/mid2" in [b["id"] for b in d["backups"]]


def test_a_harder_ask_moves_up_once_and_never_back_down(box):
    from app.pipeline import writer as WR
    WR.decide("w3", _r("a/mid1"), doc=_p4._doc(), health={})
    d = WR.decide("w3", _r("a/high1", "HIGH"), doc=_p4._doc(), health={})
    assert d["event"] == "up" and d["model"]["id"] == "a/high1" and "stronger model" in d["note"]
    d2 = WR.decide("w3", _r("a/mid1"), doc=_p4._doc(), health={})
    assert d2["event"] == "kept" and d2["model"]["id"] == "a/high1" and not d2["note"]   # never down


def test_a_writer_that_is_off_moves_with_one_line(box):
    from app.pipeline import writer as WR
    WR.decide("w4", _r("a/mid1"), doc=_p4._doc(), health={})
    d = WR.decide("w4", _r("b/mid2"), doc=_p4._doc(), health={"a/mid1": {"paused": True}})
    assert d["event"] == "moved" and d["model"]["id"] == "b/mid2" and "not answering" in d["note"]
    assert WR.get("w4")["model"] == "b/mid2"


def test_a_writer_that_cannot_do_this_message_moves(box):
    from app.pipeline import writer as WR
    doc = _p4._doc()
    doc["models"]["x/img"] = {"ins": ["text", "image"], "outs": ["text"], "tools": True, "ctx": 100000}
    WR.decide("w5", _r("a/mid1"), doc=doc, health={})
    doc["models"]["a/mid1"]["ins"] = ["text"]
    d = WR.decide("w5", _r("x/img", kind="read.image"), doc=doc, health={})
    assert d["event"] == "moved" and d["model"]["id"] == "x/img" and "cannot take image" in d["note"]


def test_her_own_pick_is_always_the_writer_and_nothing_is_said(box):
    from app.pipeline import writer as WR
    WR.decide("w6", _r("a/mid1"), doc=_p4._doc(), health={})
    d = WR.decide("w6", _r("c/mid3"), doc=_p4._doc(), health={}, pin="c/mid3")
    assert d["event"] == "pick" and d["model"]["id"] == "c/mid3" and not d["note"]


def test_a_routine_never_chooses_the_chats_writer(box):
    from app.pipeline import writer as WR
    d = WR.decide("w7", _r("a/mid1"), doc=_p4._doc(), health={}, surface="background")
    assert d["event"] == "none" and WR.get("w7") is None


def test_the_switch_turns_it_off(box, monkeypatch):
    from app.config import get_settings
    from app.pipeline import writer as WR
    monkeypatch.setenv("PIPELINE_ONE_WRITER", "false")
    get_settings.cache_clear()
    assert WR.decide("w8", _r("a/mid1"), doc=_p4._doc(), health={})["event"] == "none" and WR.get("w8") is None


def test_two_messages_of_one_chat_run_on_the_same_writer(box):
    from app.agent import llm
    from app.pipeline import box as B
    b = box.begin("c1", "t1", "Kal ka mausam kaisa rahega Akola mein?")
    first = llm.MODEL_NOW.get()
    box.end(b, "Kal dhoop rahegi.")
    B._STICKY.clear()                                 # the old 30-minute sticky is gone: the writer pin still holds
    b = box.begin("c1", "t1", "Aur parson?")
    assert llm.MODEL_NOW.get() == first and b["sheet"]["parts"][0]["model"]["id"] == first.split(":", 1)[1]
    box.end(b, "Parson bhi.")


def test_a_hand_over_mid_reply_moves_the_writer_and_says_so(box, monkeypatch):
    from app.events import bus
    from app.pipeline import runner as R, writer as WR
    seen = []
    real = bus.publish
    monkeypatch.setattr(bus, "publish", lambda c, k, p, *a, **kw: (seen.append((k, p)), real(c, k, p, *a, **kw)))
    b = box.begin("c2", "t1", "hi")
    asyncio.run(R.call(R.HAND.get(), _p4._maker({"a/mid1": _p4.boom(_p4.BANNED if hasattr(_p4, "BANNED") else
                                                                     "404 No endpoints found"),
                                                 "b/mid2": _p4.ok()}, [])))
    box.end(b, "ok")
    assert WR.get("c2")["model"] == "b/mid2"
    line = [p for k, p in seen if k == "model_switch"]
    assert line and "finished this reply and continues this chat" in line[-1]["text"]


def test_the_held_out_share_is_per_chat_not_per_message(box, monkeypatch):
    from app.config import get_settings
    from app.pipeline import watch as W
    monkeypatch.setenv("PIPELINE_HOLDOUT_PCT", "50")
    get_settings.cache_clear()
    picks = {c: W.hold_out(c) for c in (f"chat{i}" for i in range(40))}
    assert all(W.hold_out(c) == v for c, v in picks.items())      # the same chat always gets the same answer
    assert 5 < sum(picks.values()) < 35


# ------------------------------------------------------------------ the checkers
def _cur(box, conv="k1", text="Blue shirt ka daam batao", tool=None):
    b = box.begin(conv, "t1", text)
    if tool:
        box.saw("shop_search", tool)
    return b


def test_the_code_checker_sends_a_wrong_figure_back_to_the_writer(box, monkeypatch):
    from app.pipeline import checkers as CK
    monkeypatch.setattr(CK, "model_check", lambda *a, **k: _done([], ""))
    b = _cur(box, tool={"items": [{"price": 1499}]})
    note = asyncio.run(CK.review(b, "The blue shirt costs Rs 2,350."))
    assert "2350" in note and "Write the whole answer again" in note
    assert asyncio.run(CK.review(b, "Still Rs 2,350.")) == ""      # one round per message, never a loop
    box.end(b, "The blue shirt costs Rs 1,499.")


async def _done(problems, mid):
    return problems, mid


def test_the_model_checker_is_another_company_and_its_problems_count(box, monkeypatch):
    from app.agent import llm
    from app.pipeline import checkers as CK
    seen = {}

    async def fake(brain, system, tools, msgs, cap):
        seen["model"], seen["system"] = llm.MODEL_NOW.get(), system
        return [{"type": "text", "text": '{"ok": false, "problems": ["It never says the delivery date she asked for"]}'}], \
            "end_turn", {}
    monkeypatch.setattr(llm, "_openai_create", fake)
    b = _cur(box, conv="k2", text="Shirt ka daam aur delivery date batao", tool={"items": [{"price": 1499}]})
    note = asyncio.run(CK.review(b, "The shirt costs Rs 1,499."))
    assert seen["system"] == CK.MODEL_CHECK and not seen["model"].startswith("openrouter:a/")   # writer is a/mid1
    assert "delivery date" in note
    assert b["review"]["by"][0] == "code" and len(b["review"]["by"]) == 2
    box.end(b, "x")


def test_a_failing_checker_never_blocks_the_reply(box, monkeypatch):
    from app.agent import llm
    from app.pipeline import checkers as CK

    async def broken(*a, **k):
        raise RuntimeError("503 upstream")
    monkeypatch.setattr(llm, "_openai_create", broken)
    b = _cur(box, conv="k3", tool={"items": [{"price": 1499}]})
    assert asyncio.run(CK.review(b, "The blue shirt costs Rs 1,499.")) == ""
    box.end(b, "x")


def test_a_short_answer_with_no_tools_gets_only_the_code_check(box, monkeypatch):
    from app.agent import llm
    from app.pipeline import checkers as CK
    called = []

    async def fake(*a, **k):
        called.append(1)
        return [{"type": "text", "text": '{"ok": true}'}], "end_turn", {}
    monkeypatch.setattr(llm, "_openai_create", fake)
    b = _cur(box, conv="k4", text="hi")
    assert asyncio.run(CK.review(b, "Namaste! Kaise madad karun?")) == "" and not called
    box.end(b, "x")


def test_the_checkers_switch(box, monkeypatch):
    from app.config import get_settings
    from app.pipeline import checkers as CK
    monkeypatch.setenv("PIPELINE_CHECKERS", "false")
    get_settings.cache_clear()
    b = _cur(box, conv="k5", tool={"items": [{"price": 1499}]})
    assert asyncio.run(CK.review(b, "Rs 2,350.")) == ""
    box.end(b, "x")


# ------------------------------------------------------------------ one real chat turn, end to end
@pytest.fixture
def turn(gz, tmp_path, monkeypatch):  # noqa: F811
    for k, v in {"PIPELINE_DIR": str(tmp_path / "pl"), "PIPELINE_ON": "true", "PIPELINE_HOLDOUT_PCT": "0",
                 "CHAT_LLM": "glm", "GLM_API_KEY": "k", "GLM_BASE_URL": "https://openrouter.ai/api/v1",
                 "GLM_MODEL": "z-ai/glm-5.3-flash", "PIPELINE_CHECKER_MIN_CHARS": "10"}.items():
        monkeypatch.setenv(k, v)
    from app.config import get_settings
    get_settings.cache_clear()
    from app.pipeline import store, turnbox as T, box as B
    store.root().mkdir(parents=True, exist_ok=True)
    (store.root() / "current.json").write_text(json.dumps(_p4._doc()))
    T._TABLES.update({"mtime": None, "doc": None})
    T._OUT.clear()
    T._DEAD.clear()
    B._STICKY.clear()
    from app.agent import llm, providers
    monkeypatch.setattr(llm, "cheap_brain", lambda: "glm")
    monkeypatch.setattr(providers, "ready", lambda m: True)
    yield gz
    get_settings.cache_clear()


@pytest.mark.parametrize("plain", ["true", "false"])
def test_a_wrong_draft_is_fixed_inside_the_one_reply_by_the_same_writer(turn, monkeypatch, plain):
    from app.agent import llm, santosh
    from app.config import get_settings
    from app.events import bus
    from app.pipeline import checkers as CK
    monkeypatch.setenv("CHAT_PLAIN_LOOP", plain)
    get_settings.cache_clear()
    writer_calls, checker_calls, published = [], [], []
    real = bus.publish
    monkeypatch.setattr(bus, "publish", lambda c, k, p, *a, **kw: (published.append((k, p)), real(c, k, p, *a, **kw)))

    async def fake(brain, system, tools, messages, max_tokens):
        m = llm.MODEL_NOW.get()
        if system == CK.MODEL_CHECK:
            checker_calls.append(m)
            draft = messages[-1]["content"]
            bad = "2,350" in draft
            return [txt('{"ok": false, "problems": ["The price 2,350 is not what she was told"]}' if bad
                        else '{"ok": true}')], "end_turn", {}
        writer_calls.append(m)
        last = json.dumps(messages[-1], ensure_ascii=False)
        fixed = "checkers found problems" in last
        return [txt("The blue shirt costs Rs 1,499 at the shop." if fixed
                    else "The blue shirt costs Rs 2,350 at the shop.")], "end_turn", {}
    monkeypatch.setattr(llm, "_openai_create", fake)
    monkeypatch.setattr(llm, "_openai_stream", lambda brain, s, t, m, mt, *a, **k: fake(brain, s, t, m, mt))
    out = asyncio.run(santosh.run_turn(turn["conv"], "Blue shirt ka daam batao, mujhe 1,499 bataya tha",
                                       tenant_id="default"))
    assert "1,499" in out and "2,350" not in out
    assert len(set(writer_calls)) == 1 and len(writer_calls) == 2        # one writer, the draft written again once
    assert checker_calls and checker_calls[0] != writer_calls[0]          # another model checked it
    shown = [p for k, p in published if k == "message" and p.get("role") == "assistant"]
    assert all("2,350" not in p.get("text", "") for p in shown)           # the wrong draft was never her reply
    assert not [p for k, p in published if k == "message" and p.get("source") == "box_fix"]   # no second message


def test_wiring_and_version():
    root = pathlib.Path(__file__).resolve().parents[1] / "app"
    s = (root / "agent" / "santosh.py").read_text()
    assert s.count("await _box_review(") == 2                              # the plain loop and the old loop
    assert "model_switch" in (root / "events.py").read_text()
    js = (root / "static" / "console" / "v2.js").read_text()
    assert "kind === 'model_switch'" in js and "'model_switch'," in js
    repo = root.parents[1]
    assert "case 'model_switch'" in (repo / "lib" / "ui" / "chat" / "hoola_cards_all.dart").read_text()
    assert "case 'model_switch'" in (repo / "lib" / "state.dart").read_text()
    assert "case 'model_switch'" in (repo / "lib" / "ui" / "chat_screen.dart").read_text()
    from app.main import APP_VERSION
    assert APP_VERSION.startswith("0.999.148")
