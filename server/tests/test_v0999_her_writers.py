"""v0.999 HER WRITERS (owner: "LETS GO WITH GLM 5.3 AND DEEPSEEKV4.1 FLASH --- FOR WRITER"): GLM-5.3 writes every chat,
DeepSeek V4.1 Flash takes over when it is down, and each checks the other's reply. Fake models only, no network."""
from __future__ import annotations

import importlib.util
import pathlib

import pytest

_spec = importlib.util.spec_from_file_location(
    "_p4w", pathlib.Path(__file__).with_name("test_v0969_pipeline_p4.py"))
_p4 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_p4)
_box = _p4.box

GLM, DS = "z-ai/glm-5.3", "deepseek/deepseek-v4.1-flash-1017"


@pytest.fixture
def box(_box, monkeypatch):
    from app.config import get_settings
    monkeypatch.setenv("PIPELINE_WRITERS", f"{GLM},{DS}")
    get_settings.cache_clear()
    yield _box
    get_settings.cache_clear()


def _r(mid="a/mid1", level="MID", kind="chat"):
    M = _p4.M
    return {"model": M(mid), "backups": [M("b/mid2")], "level": level, "level_used": level, "kind": kind,
            "language": "en"}


def test_the_default_writers_are_hers():
    from app.config import Settings
    assert Settings.model_fields["pipeline_writers"].default == f"{GLM},{DS}"


def test_glm_writes_the_chat_whatever_the_box_would_pick(box):
    from app.pipeline import writer as WR
    d = WR.decide("h1", _r("a/high1", "HIGH"), doc=_p4._doc(), health={})
    assert d["event"] == "pinned" and d["model"]["id"] == GLM and not d["note"]
    assert [b["id"] for b in d["backups"]] == [DS, "a/high1"]          # DeepSeek first, one safety after
    d2 = WR.decide("h1", _r("c/mid3"), doc=_p4._doc(), health={})
    assert d2["event"] == "kept" and d2["model"]["id"] == GLM


def test_glm_down_moves_the_chat_to_deepseek_with_one_line_and_it_stays(box):
    from app.pipeline import writer as WR
    WR.decide("h2", _r(), doc=_p4._doc(), health={})
    d = WR.decide("h2", _r(), doc=_p4._doc(), health={GLM: {"paused": True}})
    assert d["event"] == "moved" and d["model"]["id"] == DS and "not answering" in d["note"]
    d2 = WR.decide("h2", _r(), doc=_p4._doc(), health={})            # GLM back: the chat keeps DeepSeek
    assert d2["event"] == "kept" and d2["model"]["id"] == DS


def test_both_down_the_box_answers_this_message_only(box):
    from app.pipeline import writer as WR
    d = WR.decide("h3", _r("a/mid1"), doc=_p4._doc(), health={GLM: {"paused": True}, DS: {"paused": True}})
    assert d["event"] == "moved" and d["model"]["id"] == "a/mid1" and "cannot take this message" in d["note"]
    assert WR.get("h3") is None


def test_her_own_pick_still_wins(box):
    from app.pipeline import writer as WR
    d = WR.decide("h4", _r("c/mid3"), doc=_p4._doc(), health={}, pin="c/mid3")
    assert d["event"] == "pick" and d["model"]["id"] == "c/mid3"


def test_a_routine_turn_writes_with_her_writer_too(box):
    from app.pipeline import writer as WR
    d = WR.decide("h5", _r(), doc=_p4._doc(), health={}, surface="background")
    assert d["model"]["id"] == GLM


def test_an_old_chat_on_another_writer_moves_to_hers_quietly(box):
    from app.pipeline import writer as WR
    WR._put("h6", "anthropic/claude-sonnet-4.6", "MID", "chat", "first message of the chat", False, 1e12)
    d = WR.decide("h6", _r(), doc=_p4._doc(), health={}, now=1e12 + 5)
    assert d["model"]["id"] == GLM and d["event"] == "moved" and not d["note"]


def test_a_safety_model_finishing_a_reply_does_not_replace_her_writers(box):
    from app.pipeline import writer as WR
    WR.decide("h7", _r(), doc=_p4._doc(), health={})
    line = WR.handed("h7", "a/mid1", "MID", "error")
    assert "finished this reply" in line and "continues" not in line and WR.get("h7")["model"] == GLM
    line2 = WR.handed("h7", DS, "MID", "error")
    assert "continues this chat" in line2 and WR.get("h7")["model"] == DS


@pytest.mark.parametrize("writer,checker", [(GLM, DS), (DS, GLM), ("a/mid1", GLM)])
def test_they_check_each_other(box, writer, checker):
    from app.pipeline import checkers as K
    b = {"doc": _p4._doc(), "sheet": {"parts": [{"model": {"id": writer}, "ran_on": writer}]}}
    assert K.pick_checker(b)["id"] == checker


def test_a_chat_turn_runs_on_glm(box):
    from app.agent import llm
    b = box.begin("hc", "t1", "Kal ka mausam kaisa rahega Akola mein?")
    try:
        assert llm.MODEL_NOW.get() == "openrouter:" + GLM
        assert [x["id"] for x in b["sheet"]["parts"][0]["backups"]][0] == DS
    finally:
        box.end(b, "Kal dhoop rahegi.")


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION.startswith("0.999.1")


# ------------------------------------------------------------------ v0.999.1 her live test fixes (18 Nov)
def test_a_chat_writer_gets_room_before_its_first_word():
    from app.pipeline import handover as H
    assert H.first_word_limit("chat") >= 20 and H.first_word_limit("call") == 3.0


def test_a_box_call_streams_its_thinking_and_asks_the_fastest_provider(box):
    from app.agent import llm
    tok = llm.MODEL_NOW.set("openrouter:" + GLM)
    own = llm.BOX_OWNS.set(True)
    try:
        extra = llm._target("glm")[4]
    finally:
        llm.BOX_OWNS.reset(own)
    try:
        plain = llm._target("glm")[4]
    finally:
        llm.MODEL_NOW.reset(tok)
    if "reasoning" in extra:
        assert extra["reasoning"]["exclude"] is False
    assert extra.get("provider") == {"sort": "latency"}
    assert "provider" not in plain


def test_percentages_adding_to_100_are_not_a_made_up_figure():
    from app.pipeline import check as K
    r = K.final_check("Rent is 53% and food 47% - 100% of your spend.", "rent 18000 food 16000",
                      K.facts_from("rent 18000 food 16000", ["53 47"]), tools_ran=1)
    assert not any("100" in p for p in r["problems"])


def test_figures_from_her_earlier_messages_count_as_facts(box):
    from app import db
    from app.pipeline import checkers as CK, check as K
    with db.session() as s:
        s.add(db.Conversation(id="conv_hf", tenant_id="t1"))
        s.add(db.Message(conversation_id="conv_hf", role="user", content="groceries 9500, fuel 4200",
                         display="groceries 9500, fuel 4200"))
        s.commit()
    facts = K.facts_from("salary 55000, save 20%", ["ok"]) + CK.chat_facts("conv_hf")
    r = K.final_check("Cut groceries from 9500 to 7000 and fuel from 4200 to 3000.", "salary 55000, save 20%",
                      facts, tools_ran=1)
    assert not any("9500" in p or "4200" in p for p in r["problems"])
