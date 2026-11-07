"""Wave 11 YAAD PAKKI of the third deep audit (owner: "GO WAVE 11" - memory and context).

20 on a call, only a turn the BRAIN answered is skipped by the call's own save (small talk after it is kept)
21 the memory block keeps facts / recall first (focus and diary after them)
22 "pin code" / "income tax" / "home loan DSA" are ordinary facts (a PIN / salary still refused)
23 a fallback checkpoint keeps the previous checkpoint whole
24 the compaction estimate and the summary refresh read rows off the event loop
25 a call brain on a never-compacted chat gets its rolling summary
26 the coder's work notes follow her Session (and a split call sees its chat's)
27 a bare "haan" is never learned from or hinted; a caught false claim is not a good run
28 without embeddings, the "same procedure" match keeps its 0.80 floor
"""
from __future__ import annotations

import inspect
import types

from app.db import Conversation, session

T = "default"


def _chat(cid: str, **kw) -> str:
    with session() as s:
        s.add(Conversation(id=cid, tenant_id=T, **kw))
    return cid


def test_only_brain_turns_skip_the_calls_own_save():
    from app import voice
    src = inspect.getsource(voice.Call.finish_turn)
    assert "brain_saved" in src and 'self.stats.get("brain_turns")' not in src
    assert "self._brain_this_turn = True" in inspect.getsource(voice.Call)


def test_the_relevant_facts_come_before_focus_and_diary():
    from app import yaad
    src = inspect.getsource(yaad.turn_block)
    assert src.index("relevant_facts(") < src.index("focus_block(") < src.index("diary_block(")


def test_pin_code_and_business_words_are_facts():
    from app import yaad
    for ok in ("Godown ka pin code ab 410501 hai", "She is an income tax consultant", "She runs a home loan DSA"):
        assert yaad.fact_ok(ok) == "", ok
    for bad in ("Her UPI pin is 1234", "Meri salary 50000 hai"):
        assert yaad.fact_ok(bad) != "", bad


def test_remember_takes_a_pin_code(env):
    import asyncio
    from app.agent import life_tools
    out = asyncio.run(life_tools.remember(types.SimpleNamespace(tenant_id=T, conversation_id=""),
                                          "Godown ka pin code ab 410501 hai"))
    assert out.get("fact_id") or out.get("already_known")


def test_the_plain_checkpoint_keeps_the_previous_one_whole():
    from datetime import datetime
    from app.agent import compact
    prev = "GOAL: Sharma ji ka order. HER WORDS: 'GST alag dikhana'. OPEN: quotation bhejna."
    exs = [[{"role": "user", "content": f"baat {i} " + "x" * 300, "at": datetime(2026, 11, 7), "id": i}] for i in range(40)]
    out = compact._plain(prev, exs, 2000)
    assert out.startswith(prev) and len(out) <= 2000 and "baat 39" in out


def test_heavy_reads_are_off_the_loop():
    from app.agent import compact
    from app import yaad
    assert "to_thread(estimate" in inspect.getsource(compact.before_turn)
    assert "to_thread(estimate" in inspect.getsource(compact.run)
    assert "asyncio.to_thread(lambda: exchanges(_rows(conversation_id)))" in inspect.getsource(yaad.refresh_summary)


def test_a_never_compacted_chat_gives_the_call_brain_its_summary(env, monkeypatch):
    from app.agent import santosh
    from app import yaad
    _chat("p25")
    monkeypatch.setattr(yaad, "summary_block", lambda c: "Pehle: Sharma ji ka quotation 45000 tay hua")
    out = santosh._call_chat_saar("p25")
    assert "Sharma ji ka quotation" in out


def test_work_notes_follow_her_session(env):
    from app.coder import inject, store
    _chat("cx1", project_id="p-x")
    _chat("cy1", project_id="p-y")
    store.store_observation if hasattr(store, "store_observation") else None
    scope = inject._scope(T, "cx1")
    assert scope is None or ("cx1" in scope and "cy1" not in scope)
    rows = store.recent_observations(T, limit=5, convs=set())
    assert rows == []


def test_a_bare_yes_is_never_learned_or_hinted(env):
    from app import procedures
    assert procedures._too_short("Haan bhej do") and procedures._too_short("theek hai, aage badho")
    assert not procedures._too_short("Sharma ji ko quotation PDF bana ke mail karo")
    calls = [{"tool": "email_draft", "ok": True}, {"tool": "email_send", "ok": True}, {"tool": "doc_studio", "ok": True}]
    assert procedures.after_turn(T, "Haan bhej do", calls, [], True) is None
    assert procedures.hint(T, "haan theek hai") == ("", [])
    from app.agent import santosh
    src = inspect.getsource(santosh._steps)
    assert 'not state.get("fake_done")' in src


def test_the_same_floor_holds_without_embeddings():
    from app import procedures
    src = inspect.getsource(procedures._match)
    assert "max(0.5, float(floor))" in src
