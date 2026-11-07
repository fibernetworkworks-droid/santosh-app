"""v0.659 CALL KI YAAD (owner: "Wave 2 (call memory and smoothness): 3, 4, 13-18, 23 -- WORK ON IT NOW").

3  a call on its own record reads the CHAT it came from (brief + brain)      4  the small brief keeps pending work
13 a "still working" check-in never keeps Gemini connected                  14 a second ask runs on a side record
15 two santosh_kaam calls in one turn never run her whole sentence twice    16 a brain-made card is not told twice
17 news still queued at the end of a call is saved                           18 news never cuts into speech
23 the call brain gets facts by meaning and is told what memory it lacks
"""
from __future__ import annotations

import asyncio
import collections
import inspect
import time
import types

from app.db import Conversation, Message, session

T = "default"


def _chat(cid: str) -> str:
    with session() as s:
        s.add(Conversation(id=cid, tenant_id=T))
    return cid


def _say(conv: str, role: str, text: str):
    with session() as s:
        content = text if role == "user" else [{"type": "text", "text": text}]
        s.add(Message(conversation_id=conv, role=role, content=content, display=text, in_history=True))


def _checkpoint(conv: str, summary: str):
    from app.agent import compact
    compact.ensure_table()
    with session() as s:
        s.add(compact.ChatCompact(conversation_id=conv, status="active", summary=summary, upto_id=0))


# ---------------------------------------------------------------- 3 + 4 the call brief
def test_a_call_record_reads_the_chat_it_came_from(env):
    from app import callconv, yaad
    _chat("chat1")
    _say("chat1", "user", "Sharma ji ka quotation 45000 ka banao")
    _say("chat1", "assistant", "Quotation ka draft taiyaar hai")
    rec = callconv.open_for(T, "chat1", "call-1")
    brief = yaad.voice_block(T, rec)
    assert "Sharma ji ka quotation" in brief


def test_the_small_brief_keeps_the_checkpoints_pending_tail(env):
    from app import callconv, yaad
    _chat("chat2")
    _say("chat2", "user", "pehle ka kaam")
    _checkpoint("chat2", "Is chat mein bahut kuch hua. " + ("lambi baat " * 900) + "\nPENDING: Sharma ji ko quotation bhejna hai")
    rec = callconv.open_for(T, "chat2", "call-2")
    brief = yaad.voice_block(T, rec, hard_cap=4500)
    assert len(brief) <= 4700
    assert "PENDING: Sharma ji ko quotation" in brief and "Is chat mein" in brief


def test_the_call_brain_reads_the_chats_checkpoint(env):
    from app import callconv
    from app.agent import santosh
    _chat("chat3")
    _checkpoint("chat3", "Kaam chal raha tha.\nPENDING: Rahul ko invoice")
    rec = callconv.open_for(T, "chat3", "call-3")
    out = santosh._call_chat_saar(rec)
    assert "PENDING: Rahul ko invoice" in out
    assert santosh._call_chat_saar("chat3") == ""          # a plain chat reads its own checkpoint already


# ---------------------------------------------------------------- 23 brain memory
def test_a_late_memory_part_is_named_and_kept_for_the_next_ask(env, monkeypatch):
    from app.agent import santosh
    from app import kaamwatch
    _chat("chat4")
    monkeypatch.setattr(kaamwatch, "block", lambda t, c: (time.sleep(1.2), "KAAM: website chal rahi")[1])
    st = types.SimpleNamespace(voice_brain_memory_s=0.4, voice_brain_yaad=False)
    santosh._BRAIN_CACHE.clear()

    async def go():
        out = await santosh._brain_memory(T, "chat4", "ho gaya kya?", st)
        await asyncio.sleep(1.2)                           # the slow part finishes in its thread
        return out, await santosh._brain_memory(T, "chat4", "ho gaya kya?", st)
    out, out2 = asyncio.run(go())
    assert "abhi load nahi hua" in out and "kaam ki taaza haalat" in out and "kaam_status" in out
    assert santosh._BRAIN_CACHE.get(("chat4", "kaam"), (0, ""))[1] == "KAAM: website chal rahi"
    assert "KAAM: website chal rahi" not in out2           # job state is never served stale: it moves


def test_the_call_brain_has_facts_by_meaning(env, monkeypatch):
    from app.agent import santosh
    from app import yaad
    monkeypatch.setattr(yaad, "relevant_facts", lambda t, q, shown, top=6, conversation_id="": [(1, "Godown Chakan mein hai")])
    out = santosh._call_facts(T, "x", "godown kahan hai")
    assert "Godown Chakan" in out
    assert santosh._call_facts(T, "x", "") == ""


# ---------------------------------------------------------------- 13 parking
def _busy_fake(**kw):
    from app import voice
    f = types.SimpleNamespace(user_buf="", reply_buf="", _turn_audio=None, _news=[], _goaway_at=0,
                              audio=types.SimpleNamespace(_queue=collections.deque()), _tools=set(),
                              _hold_timer=None, _news_task=None)
    for k, v in kw.items():
        setattr(f, k, v)
    return voice.Call._busy(f)


def test_a_checkin_never_keeps_the_call_awake():
    async def go():
        ck = asyncio.ensure_future(asyncio.sleep(5))
        ck._hoola_checkin = True
        tool = asyncio.ensure_future(asyncio.sleep(5))
        try:
            return _busy_fake(_tools={ck}), _busy_fake(_tools={ck, tool})
        finally:
            ck.cancel()
            tool.cancel()
    only_checkin, with_tool = asyncio.run(go())
    assert only_checkin is False and with_tool is True


# ---------------------------------------------------------------- 18 news timing
def test_capped_news_still_waits_for_a_gap_in_speech():
    from app import voice
    now = time.monotonic()
    f = types.SimpleNamespace(_news_since=now - 40, user_buf="", _last_voice_at=now - 5, _last_model_audio=now - 5,
                              NEWS_MAX_WAIT_S=voice.Call.NEWS_MAX_WAIT_S, NEWS_GAP_S=voice.Call.NEWS_GAP_S)
    assert voice.Call._news_forced(f, now) is True
    f.user_buf = "aur ek baat yeh ki"
    assert voice.Call._news_forced(f, now) is False      # she is mid-sentence
    f.user_buf, f._last_model_audio = "", now - 0.1
    assert voice.Call._news_forced(f, now) is False      # he is speaking
    f._last_model_audio, f._news_since = now - 5, now - 3
    assert voice.Call._news_forced(f, now) is False      # the cap has not run out
    f._news_since, f._last_voice_at, f.user_buf = now - 80, now, "shor"
    assert voice.Call._news_forced(f, now) is True       # a line that never looks quiet: 3x the cap, still not over him


# ---------------------------------------------------------------- 17 end of call
def test_news_still_in_the_queue_is_saved_for_the_next_call():
    from app import voice
    news = "(Website ka kaam ho gaya: https://x.in)"
    saved = []
    f = types.SimpleNamespace(audio=types.SimpleNamespace(_queue=collections.deque([("text", news)])),
                              _news_pushed={id(news): (news, ["Website ho gaya https://x.in"])},
                              _held_texts=["Reminder: 5 baje"], _after_release=[], stats={},
                              _orphan_note=saved.append)
    voice.Call._save_unsent(f)
    assert saved and "Website ho gaya" in saved[0] and "Reminder: 5 baje" in saved[0]


def test_a_hang_up_in_the_first_wait_still_keeps_the_result():
    from app import voice
    src = inspect.getsource(voice.Call._delegate)
    i = src.index("handed = {")
    assert src.index("job.add_done_callback", i) < src.index("await asyncio.wait({job}", i)


# ---------------------------------------------------------------- 15 two santosh_kaam calls
def test_a_second_kaam_call_in_the_same_turn_carries_only_its_part(monkeypatch):
    from app import voice
    from app.config import get_settings
    monkeypatch.setenv("VOICE_BRAIN", "true")
    get_settings.cache_clear()
    sent = []

    async def deleg(req):
        sent.append(req)
        return {"status": "working"}
    f = types.SimpleNamespace(user_buf="mail bhejo aur reminder lagao", _typed=None, ctx=types.SimpleNamespace(place=""),
                              _place=lambda r: "", _delegate=deleg, stats={}, call_id="c", _kaam_said="")
    f._her_words = lambda: f.user_buf

    async def go():
        await voice.Call._execute(f, "santosh_kaam", {"request": "Sharma ko mail"})
        await voice.Call._execute(f, "santosh_kaam", {"request": "5 baje reminder"})
    asyncio.run(go())
    assert "mail bhejo aur reminder lagao" in sent[0]
    assert sent[1] == "5 baje reminder"


# ---------------------------------------------------------------- 16 brain-made card
class _Loop:
    def call_soon_threadsafe(self, fn, *a):
        fn(*a)


class _FakeCall:
    tenant = T

    def __init__(self):
        self.notes = []

    def push_news(self, text):
        self.notes.append(text)

    def card_answered(self, title, word):
        self.notes.append(f"answered {title}")


def test_a_card_the_calls_own_brain_made_is_quiet_but_remembered(env, monkeypatch):
    from app import voice
    _chat("c16")
    fake = _FakeCall()
    monkeypatch.setattr(voice, "ACTIVE", {"c16": [(_Loop(), fake)]})
    voice._CARD_ASKED.clear()
    voice._CARD_TOLD.clear()
    tok = voice.VOICE_DIRECT.set("kaam:call16")
    try:
        n = voice.card_news("c16", "bazar_approval", {"id": "ap9", "title": "Swiggy order", "status": "pending"}, "call16")
    finally:
        voice.VOICE_DIRECT.reset(tok)
    assert n == 0 and fake.notes == []                    # its own ask's answer already says it
    assert voice._CARD_ASKED                               # ...but her tap will still reach the call
    voice.card_news("c16", "bazar_approval", {"id": "ap9", "title": "Swiggy order", "status": "approved"})
    assert fake.notes == ["answered Swiggy order"]


# ---------------------------------------------------------------- 14 side record
def test_a_second_ask_runs_on_a_hidden_side_record(env):
    from app import callconv, voice
    from app.agent import santosh
    _chat("chat14")
    rec = callconv.open_for(T, "chat14", "call-14")
    f = types.SimpleNamespace(conv=rec, ctx=types.SimpleNamespace(tenant_id=T), call_id="call-14", stats={},
                              MAX_SIDES=voice.Call.MAX_SIDES)

    async def go():
        assert voice.Call._run_conv(f) == rec                # free: the call record itself
        async with santosh._locks[rec]:
            side = voice.Call._run_conv(f)
            assert side != rec and voice.Call._run_conv(f) == side   # reused while free
        return side
    side = asyncio.run(go())
    assert callconv.origin_of(side) == "chat14"              # same memory scope as the chat
    assert [r["id"] for r in callconv.recent(T)] == [rec]   # never in her Calls list

    job_done = asyncio.Future if False else None
    async def copy():
        fut = asyncio.get_running_loop().create_future()
        fut.set_result("Calendar mein 3 meeting hain")
        await voice.Call._copy_back(f, side, "mera calendar batao", fut)
    asyncio.run(copy())
    with session() as s:
        shown = [m.display for m in s.query(Message).filter_by(conversation_id=rec).all()]
    assert shown == ["mera calendar batao", "Calendar mein 3 meeting hain"]


def test_a_call_brain_ask_never_takes_the_no_tools_quick_lane():
    from app.agent import santosh
    src = inspect.getsource(santosh._run_turn)
    assert 'not voice and not VOICE_BRAIN_NOW.get()' in src
