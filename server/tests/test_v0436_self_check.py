"""v0.436 SOCH KE JAWAB step 5 - the self-check before a hard answer goes out (owner: "GO STEP 5").

Before: a hard answer streamed to her as it was written; the only later look (draftcheck, a cheap model, numbers
nobody recomputed) could add a note AFTER she had read it. Now her hard answer is HELD (thinking still streams on the
Soch card): the free code check (a calculation answered without pylab) and then ONE independent reviewer call that
sees her question, the draft and the real tool evidence (pylab code + output). A problem goes back to the same brain
ONCE as a fix note; the corrected answer replaces the draft, which is kept for the model but never shown. A failing /
slow reviewer never blocks the answer; ordinary chat is never held.
"""
import asyncio
import json
import types

import pytest

from tests.test_bazar import bz  # noqa: F401
from tests.test_v0186_long_goal import FakeBrain, _set_brain, gz, tu, txt  # noqa: F401


@pytest.fixture
def check_on():
    from app.config import get_settings
    st = get_settings()
    st.hard_check = True
    yield st
    st.hard_check = False


# ---------------------------------------------------------------- the free code check
def test_code_check_catches_a_calculation_done_in_the_head():
    from app.agent import hard
    q = "20 lakh ke home loan ki EMI kitni banegi 9% pe 20 saal"
    draft = "EMI lagbhag 18,500 hogi aur total interest 24,40,000 banega."
    probs = hard.code_check(q, draft, ["calculation", "numbers"], ["google_search"])
    assert probs and "18,500" in probs[0] and "pylab" in probs[0]
    # wave 13: pylab having run is not enough - its printed output must carry the figures
    assert hard.code_check(q, draft, ["calculation"], ["pylab"], "RESULT: 18500.0 2440000") == []
    assert hard.code_check(q, draft, ["calculation"], ["pylab"], "RESULT: 7") != []
    assert hard.code_check(q, draft, ["decision"], []) == []                    # not a calculation ask
    assert hard.code_check(q, "EMI 9% pe 20 saal ke liye nikalni hogi.", ["calculation"], []) == []   # only her own numbers


def test_evidence_reads_this_turns_pylab_code_and_output():
    from app.agent import hard
    history = [
        {"role": "user", "content": "purana sawaal"},
        {"role": "assistant", "content": [txt("purana jawab")]},
        {"role": "user", "content": "EMI kitni banegi"},
        {"role": "assistant", "content": [tu(1, "pylab", code="print(17994.52)", purpose="emi")]},
        {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "t1", "content": '{"stdout": "17994.52"}'}]},
        {"role": "user", "content": [{"type": "text", "text": "[System: cut gaya]"}]},
    ]
    ev, names = hard.evidence(history)
    assert names == ["pylab"] and "print(17994.52)" in ev and "17994.52" in ev and "purana" not in ev


# ---------------------------------------------------------------- the reviewer
def _client(reply=None, boom=False):
    seen = []

    async def create(**kw):
        seen.append(kw)
        if boom:
            raise RuntimeError("down")
        return types.SimpleNamespace(content=[types.SimpleNamespace(text=reply)])
    return types.SimpleNamespace(messages=types.SimpleNamespace(create=create)), seen


@pytest.mark.parametrize("reply,want", [
    (json.dumps({"ok": False, "problems": ["Total interest is 23,18,684.59, not 24,40,000"]}),
     ["Total interest is 23,18,684.59, not 24,40,000"]),
    ('Sure: {"ok": true}', []), ("not json at all", []),
])
def test_reviewer_reads_its_verdict(monkeypatch, reply, want):
    from app.agent import hard, santosh
    from app.config import get_settings
    cli, seen = _client(reply)
    monkeypatch.setattr(santosh, "get_client", lambda: cli)
    got = asyncio.run(hard.review("EMI?", "draft", "RESULT: 17994.52", get_settings()))
    assert got == want
    assert seen[0]["system"] == hard.CHECK_SYSTEM and "RESULT: 17994.52" in seen[0]["messages"][0]["content"]


def test_reviewer_failure_never_blocks(monkeypatch):
    from app.agent import hard, santosh
    from app.config import get_settings
    cli, _ = _client(boom=True)
    monkeypatch.setattr(santosh, "get_client", lambda: cli)
    assert asyncio.run(hard.review("q", "d", "", get_settings())) == []


# ---------------------------------------------------------------- the turn: held, checked, fixed once
def _shown(conv):
    from app.db import Message, session
    from sqlalchemy import select
    with session() as s:
        return [m.display for m in s.scalars(select(Message).where(Message.conversation_id == conv,
                                                                    Message.role == "assistant")).all() if m.display]


def test_a_wrong_hard_answer_is_fixed_before_she_sees_it(gz, monkeypatch, check_on):  # noqa: F811
    conv = gz["conv"]
    brain = _set_brain(monkeypatch, FakeBrain([
        ([txt("EMI lagbhag 18,500 hogi, total interest 24,40,000.")], "end_turn"),     # mental maths
        ([txt("EMI **Rs 17,994.52** mahina hogi; 20 saal mein kul byaaj Rs 23,18,684.59.")], "end_turn"),
    ]))
    from app.agent.santosh import run_turn
    asyncio.run(run_turn(conv, "20 lakh ke home loan ki EMI kitni banegi 9% pe 20 saal", tenant_id="default"))
    assert len(brain.seen) == 2                                  # the code check caught it: no reviewer call needed
    note = brain.seen[1]["messages"][-1]["content"][0]["text"]
    assert note.startswith("[System: JAANCH") and "18,500" in note
    shown = _shown(conv)
    # draft never shown; wave 13: the fix round still ran no pylab, so the re-check labels its figures as unconfirmed
    from app.agent.santosh import HARD_UNSURE
    assert shown == ["EMI **Rs 17,994.52** mahina hogi; 20 saal mein kul byaaj Rs 23,18,684.59.\n\n" + HARD_UNSURE.strip()]


def test_a_right_hard_answer_passes_the_reviewer_and_goes_out(gz, monkeypatch, check_on):  # noqa: F811
    conv = gz["conv"]
    brain = _set_brain(monkeypatch, FakeBrain([
        ([txt("Composition sahi rahega: 80 lakh turnover, B2C, ITC ki zaroorat kam. CA se confirm karein.")], "end_turn"),
        ([txt('{"ok": true}')], "end_turn"),                    # the reviewer
    ]))
    from app.agent.santosh import run_turn
    asyncio.run(run_turn(conv, "Compare GST composition vs regular scheme for my 80 lakh kirana shop and recommend",
                         tenant_id="default"))
    assert len(brain.seen) == 2 and brain.seen[1]["system"] == __import__("app.agent.hard", fromlist=["x"]).CHECK_SYSTEM
    assert _shown(conv) == ["Composition sahi rahega: 80 lakh turnover, B2C, ITC ki zaroorat kam. CA se confirm karein."]


def test_the_reviewer_finds_a_problem_then_one_fix_only(gz, monkeypatch, check_on):  # noqa: F811
    conv = gz["conv"]
    brain = _set_brain(monkeypatch, FakeBrain([
        ([txt("Regular scheme better hai kyunki composition mein 5% tax lagta hai.")], "end_turn"),
        ([txt(json.dumps({"ok": False, "problems": ["Composition rate for a trader is 1%, not 5%"]}))], "end_turn"),
        ([txt("Composition better rahega: trader ke liye rate 1% hai. CA se confirm karein.")], "end_turn"),
    ]))
    from app.agent.santosh import run_turn
    asyncio.run(run_turn(conv, "Compare GST composition vs regular scheme for my 80 lakh kirana shop and recommend",
                         tenant_id="default"))
    assert len(brain.seen) == 3                                  # draft, reviewer, the fix - never a second review
    assert "Composition rate for a trader is 1%" in brain.seen[2]["messages"][-1]["content"][0]["text"]
    assert _shown(conv) == ["Composition better rahega: trader ke liye rate 1% hai. CA se confirm karein."]


def test_ordinary_chat_is_never_held_or_checked(gz, monkeypatch, check_on):  # noqa: F811
    brain = _set_brain(monkeypatch, FakeBrain([([txt("Namaste!")], "end_turn")]))
    from app.agent.santosh import run_turn
    asyncio.run(run_turn(gz["conv"], "namaste", tenant_id="default"))
    assert len(brain.seen) == 1 and _shown(gz["conv"]) == ["Namaste!"]


def test_settings():
    from app.config import Settings
    s = Settings()
    assert s.hard_check is True and s.hard_check_model == "" and s.hard_check_timeout_s == 60.0


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.906.0"
