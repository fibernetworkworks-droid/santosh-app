"""v0.650 JAWAB MIL GAYA (owner: "DURING VOICE CALL WHEN CARD APPEARED AND IF USER APPROVE, SEND ETC TAP ON CARD --- VOICE
CALL DONT KNOW ... AFTER SOME TIME VOICE CALL AGAIN U HAVE A CARD CLICK ON APPROVE"): a live call learns, quietly, the moment
she answers a card on her phone, drops any unspoken note about it, and its brain reads which cards REALLY still wait."""
from __future__ import annotations

import asyncio
import inspect
import types

from app.db import Conversation, session

T = "default"


def _chat(cid: str) -> str:
    with session() as s:
        s.add(Conversation(id=cid, tenant_id=T))
    return cid


class _Loop:
    def call_soon_threadsafe(self, fn, *a):
        fn(*a)


class _FakeCall:
    def __init__(self):
        self.tenant = T
        self.answered = []
        self.notes = []

    def card_answered(self, title, word):
        self.answered.append((title, word))

    def push_news(self, text):
        self.notes.append(text)


def _card(status: str) -> dict:
    return {"id": "ap1", "title": "Swiggy order", "amount": "Rs 350", "status": status}


def test_her_tap_reaches_the_call(env, monkeypatch):
    from app import voice
    _chat("c1")
    fake = _FakeCall()
    monkeypatch.setattr(voice, "ACTIVE", {"c1": [(_Loop(), fake)]})
    voice._CARD_ASKED.clear()
    voice._CARD_TOLD.clear()
    assert voice.card_news("c1", "bazar_approval", _card("pending")) == 1     # the call is told the card waits
    assert fake.notes and "Card aaya" in fake.notes[0]
    assert voice.card_news("c1", "bazar_approval", _card("approved")) == 1    # her tap on the phone
    assert fake.answered == [("Swiggy order", "approved")]                     # named by the card's own title
    assert not voice._CARD_ASKED                                              # answered once, forgotten
    assert voice.card_news("c1", "bazar_approval", _card("approved")) == 0    # an echo says nothing


def test_a_card_the_call_never_heard_of_stays_quiet(env, monkeypatch):
    from app import voice
    _chat("c2")
    fake = _FakeCall()
    monkeypatch.setattr(voice, "ACTIVE", {"c2": [(_Loop(), fake)]})
    voice._CARD_ASKED.clear()
    voice.card_news("c2", "bazar_approval", {"id": "zz", "title": "Old", "status": "approved"})
    assert fake.answered == []


def test_a_split_call_is_told_once(env, monkeypatch):
    from app import voice
    _chat("c3")
    fake = _FakeCall()
    monkeypatch.setattr(voice, "ACTIVE", {"c3": [(_Loop(), fake)], "callrec": [(_Loop(), fake)]})
    voice._CARD_ASKED.clear()
    voice._CARD_TOLD.clear()
    voice.card_news("c3", "bazar_approval", _card("pending"))
    voice.card_news("c3", "bazar_approval", _card("rejected"))
    assert len(fake.answered) == 1 and fake.answered[0][1] == "rejected"


def test_the_call_drops_the_unspoken_note_and_learns_quietly():
    from app import voice
    quiet = []

    async def tell(note, live=False):
        quiet.append(note)

    fake = types.SimpleNamespace(_news=["[Card aaya phone par] Swiggy order - Rs 350. Isme uski haan chahiye",
                                        "(Website ka kaam ho gaya)"],
                                 stats={}, _tools=set(), _tell_quietly=tell)

    async def go():
        voice.Call.card_answered(fake, "Swiggy order", "approve")
        await asyncio.sleep(0)
        await asyncio.sleep(0)
    asyncio.run(go())
    assert fake._news == ["(Website ka kaam ho gaya)"]              # the stale ask is never spoken
    assert fake.stats["card_notes_dropped"] == 1
    assert quiet and "Card ka jawab mil gaya" in quiet[0] and "Never tell her" in quiet[0]


def test_the_brain_reads_which_cards_really_wait(env):
    from app import convs, events
    from app.events import bus
    _chat("c4")
    convs._CACHE.clear()
    convs.mark(T, "c4")
    bus.publish("c4", "bazar_approval", _card("pending"))
    blk = events.cards_block(T)
    assert "CARDS ABHI USKI HAAN KE INTEZAAR MEIN" in blk and "Swiggy order" in blk
    bus.publish("c4", "bazar_approval", _card("approved"))                   # she tapped Approve
    blk = events.cards_block(T)
    assert "abhi koi card uski haan ke intezaar mein NAHI hai" in blk and "Swiggy" not in blk


def test_wired_into_the_call_brain_and_the_voice():
    from app import voice
    from app.agent import santosh
    assert '("cards", lambda: _events_cb.cards_block(tenant_id))' in inspect.getsource(santosh._brain_memory)
    assert "Card ka jawab mil gaya" in voice.PERSONA_BRAIN and "never ask her to tap" in voice.PERSONA_BRAIN
    assert "never ask her to tap it again" in voice.PERSONA_LEAN
