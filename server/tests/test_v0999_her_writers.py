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
    assert APP_VERSION.startswith("0.999")


# ------------------------------------------------------------------ v0.999.6 her live test fixes (18 Nov)
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


# ------------------------------------------------------------------ v0.999.6 her second live test (18 Nov 14:10)
CREDIT_ERR = ('OpenRouter error 402: {"error":{"message":"This request requires more credits, or fewer max_tokens."}} '
              '| OpenRouter credit is low')


def test_a_credit_failure_is_the_accounts_not_the_writers(box, monkeypatch):
    import asyncio
    from app.pipeline import runner as R, turnbox as TB
    noted: list = []
    monkeypatch.setattr(TB, "note", lambda mid, ok: noted.append((mid, ok)))
    log: list = []
    with pytest.raises(RuntimeError, match="402"):
        asyncio.run(R.call(_p4._hand(), _p4._maker({"a/mid1": _p4.boom(CREDIT_ERR), "b/mid2": _p4.ok()}, log)))
    assert log == ["a/mid1"] and noted == []          # no backup tried on the same empty account, no outage mark
    R.model_failed("openrouter:" + GLM, CREDIT_ERR)
    assert noted == []


def test_an_ordinary_error_still_goes_to_the_backup(box):
    import asyncio
    from app.pipeline import runner as R
    log: list = []
    asyncio.run(R.call(_p4._hand(), _p4._maker({"a/mid1": _p4.boom("503 upstream error"), "b/mid2": _p4.ok()}, log)))
    assert log == ["a/mid1", "b/mid2"]


def test_a_paused_brain_does_not_move_her_chat_past_the_box(box, monkeypatch):
    from app.agent import llm, providers as pv
    from app.pipeline import turnbox as TB
    monkeypatch.setattr(llm, "cheap_brain", lambda: None)          # the safety switch paused the brain
    monkeypatch.setattr(llm, "chat_brain", lambda: "glm")          # ... it is still her chat's brain
    monkeypatch.setattr(pv, "ready", lambda m: True)
    r = {"kind": "chat", "model": {"id": GLM, "route": "openrouter"}}
    assert TB._why_not("owner", False, r) == ""


# ------------------------------------------------------------------ v0.999.6 the model checker reads like a reviewer
def test_the_model_checker_lets_suggestions_through():
    from app.pipeline import checkers as CK
    assert "never flag those" in CK.MODEL_CHECK
    assert "AS A FACT" in CK.MODEL_CHECK and "earlier chat" in CK.MODEL_CHECK


def test_the_model_checker_sees_her_earlier_messages(box, monkeypatch):
    import asyncio
    from app import db
    from app.agent import llm
    from app.pipeline import checkers as CK
    with db.session() as s:
        s.add(db.Conversation(id="conv_cl", tenant_id="t1"))
        for t in ("My shop sold tea Rs 42,000 last month", "Grow sales 15%"):
            s.add(db.Message(conversation_id="conv_cl", role="user", content=t, display=t))
        s.commit()
    seen = {}

    async def fake(brain, system, tools, messages, mx):
        seen["msg"] = messages[0]["content"]
        return [{"type": "text", "text": '{"ok": true}'}], "end_turn", {}
    monkeypatch.setattr(llm, "_openai_create", fake)
    b = {"doc": _p4._doc(), "text": "Grow sales 15%", "sheet": {"conv": "conv_cl",
         "parts": [{"model": {"id": GLM}, "ran_on": GLM}]}}
    probs, mid = asyncio.run(CK.model_check(b, "Tea should sell Rs 6,300 more.", []))
    assert probs == [] and mid == DS
    assert "tea Rs 42,000" in seen["msg"] and seen["msg"].count("Grow sales 15%") == 1


def test_the_checker_knows_what_hoola_knows_about_her(box, monkeypatch):
    """v0.999.6 her live test: the sign-off with her own name / company and GST state code 27 (Maharashtra, from her
    profile) were sent back as 'not in her message'."""
    import asyncio
    from app import db
    from app.agent import llm, core_prompt as CP
    from app.pipeline import checkers as CK
    with db.session() as s:
        s.add(db.Conversation(id="conv_ab", tenant_id="t1"))
        s.add(db.Message(conversation_id="conv_ab", role="user", content="Write to Ramesh", display="Write to Ramesh"))
        s.commit()
    monkeypatch.setattr(CP, "chat_context", lambda tenant, conv, *a, **k:
                        "She: name Meghna Anil Ingle, city Akola. Her memory page: Director of Newtika Private "
                        "Limited, GST state code 27.")
    seen = {}

    async def fake(brain, system, tools, messages, mx):
        seen["msg"] = messages[0]["content"]
        seen["sys"] = system
        return [{"type": "text", "text": '{"ok": true}'}], "end_turn", {}
    monkeypatch.setattr(llm, "_openai_create", fake)
    sh = {"conv": "conv_ab", "tenant": "t1", "parts": [{"model": {"id": GLM}, "ran_on": GLM, "applied": True,
                                                          "level": "MAX"}]}
    b = {"doc": _p4._doc(), "text": "Write to Ramesh", "tenant": "t1", "conv": "conv_ab", "sheet": sh,
         "sink": ["search result"]}
    note = asyncio.run(CK.review(b, "Regards, Meghna Anil Ingle, Director, Newtika Private Limited (GST code 27)."))
    assert "Meghna Anil Ingle" in seen["msg"] and "What Hoola knows about her" in seen["msg"]
    assert "counts as hers" in seen["sys"]
    assert "figure 27" not in note        # her profile's figures are facts for the code check too
    assert note == ""


def test_long_tool_results_keep_their_figures(box):
    from app.pipeline import turnbox as TB
    sink: list = []
    tok = TB.TOOL_SINK.set(sink)
    try:
        TB.saw("web_search", "x" * 12000 + " 22 carat Rs 1,14,500 per 10 g")
    finally:
        TB.TOOL_SINK.reset(tok)
    assert "1,14,500" in sink[0]


def _live(monkeypatch):
    from app import livereply as LR
    sent: list = []
    monkeypatch.setattr(LR.bus, "publish_live", lambda conv, kind, p: sent.append((kind, dict(p))))
    lv = LR.Live("conv_hold", "t1")
    return lv, sent


def test_a_checked_reply_is_held_then_shown_once(monkeypatch):
    """v0.999.6 her live test: a reply the checker sent back landed, vanished and landed again. The writer's words
    now wait for the check; a draft that passes goes out once, whole, and the app paces it."""
    lv, sent = _live(monkeypatch)
    lv.block(stream=True, hold=True)
    lv.feed("Here is your answer with all the figures you gave.")
    lv.flush(final=True)
    assert [k for k, _ in sent] == []          # nothing reaches her while it is checked
    lv.release()
    deltas = [p for k, p in sent if k == "delta"]
    assert len(deltas) == 1 and deltas[0]["text"] == "Here is your answer with all the figures you gave."


def test_a_draft_sent_back_was_never_shown(monkeypatch):
    lv, sent = _live(monkeypatch)
    lv.block(stream=True, hold=True)
    lv.feed("A draft with an invented price of Rs 145.")
    lv.retract()
    assert sent == []                           # no words, and no take-back either
    lv.block(stream=True, hold=False)          # the corrected answer streams live, once
    lv.feed("The corrected answer.")
    lv.flush(final=True)
    assert [k for k, _ in sent] == ["delta"] and sent[0][1]["text"] == "The corrected answer."


def test_words_said_before_a_tool_are_not_held_back(monkeypatch):
    lv, sent = _live(monkeypatch)
    lv.block(stream=True, hold=True)
    lv.feed("Let me look up today's rate.")
    lv.block(stream=True, hold=True)           # the next model call starts after the tool
    assert [p["text"] for k, p in sent if k == "delta"] == ["Let me look up today's rate."]


def test_the_box_holds_only_a_turn_its_checkers_will_read(box, monkeypatch):
    from app.agent import santosh
    from app.config import get_settings
    from app.pipeline import turnbox as TB
    st = get_settings()
    b = {"sheet": {"parts": [{"applied": True}]}}
    tok = TB.CURRENT.set(b)
    try:
        assert santosh._box_holds(st) is True
        b["reviewed"] = True
        assert santosh._box_holds(st) is False   # the second draft streams live
        b.pop("reviewed")
        b["sheet"]["parts"][-1]["applied"] = False
        assert santosh._box_holds(st) is False   # not the Box's turn: as before
    finally:
        TB.CURRENT.reset(tok)
    assert santosh._box_holds(st) is False       # no Box turn at all
    monkeypatch.setenv("PIPELINE_CHECKER_HOLD", "false")
    get_settings.cache_clear()
    tok = TB.CURRENT.set({"sheet": {"parts": [{"applied": True}]}})
    try:
        assert santosh._box_holds(get_settings()) is False
    finally:
        TB.CURRENT.reset(tok)
        get_settings.cache_clear()


def test_a_passing_review_releases_the_held_words(box, monkeypatch):
    import asyncio
    from app.agent import santosh
    from app.pipeline import checkers as CK, turnbox as TB
    lv, sent = _live(monkeypatch)
    lv.block(stream=True, hold=True)
    lv.feed("All good.")

    async def ok(cur, draft):
        return ""
    monkeypatch.setattr(CK, "review", ok)
    tok = TB.CURRENT.set({"sheet": {"parts": [{"applied": True}]}})
    try:
        assert asyncio.run(santosh._box_review("All good.", lv)) == ""
    finally:
        TB.CURRENT.reset(tok)
    assert [p["text"] for k, p in sent if k == "delta"] == ["All good."]

    lv2, sent2 = _live(monkeypatch)
    lv2.block(stream=True, hold=True)
    lv2.feed("Bad draft.")

    async def back(cur, draft):
        return "[System: fix it]"
    monkeypatch.setattr(CK, "review", back)
    tok = TB.CURRENT.set({"sheet": {"parts": [{"applied": True}]}})
    try:
        assert asyncio.run(santosh._box_review("Bad draft.", lv2)).startswith("[System")
    finally:
        TB.CURRENT.reset(tok)
    assert sent2 == []


def test_the_checker_reads_her_real_messages_past_tool_rows(box):
    from app import db
    from app.pipeline import checkers as CK
    with db.session() as s:
        s.add(db.Conversation(id="conv_rows", tenant_id="t1"))
        s.add(db.Message(conversation_id="conv_rows", role="user", content="My bakery's October sales Rs 1,84,000",
                         display="My bakery's October sales Rs 1,84,000"))
        for i in range(8):   # tool results + the checkers' own notes are user rows with no display
            s.add(db.Message(conversation_id="conv_rows", role="user",
                             content=[{"type": "text", "text": f"[System: note {i}]"}], display=None))
        s.add(db.Message(conversation_id="conv_rows", role="user", content="GST number?", display="GST number?"))
        s.commit()
    lines = CK.chat_lines("conv_rows")
    assert "bakery" in lines and "GST number" not in lines and "note" not in lines
