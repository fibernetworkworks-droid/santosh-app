"""v0.554 CARD KI KHABAR - the owner: "WHEN RESULT ON CARD / APPROVAL CARD / ANY CARD TASK APPEARS --- VOICE CALL
DONT KNOW THAT EVEN CARD IS ASSIGNED AND PUSH VIA VOICE CALL".

Before: every card reached her screen, the chat and her phone's notification, but the voice model on a live call was
told only kaamwatch JOB states - an approval card, a payment card, an email draft, a form, a finished result card
appeared on her phone while the call talked on as if nothing happened. Now bus.publish hands every card to
voice.card_news: one quiet note per card per state to her live call (same chat, else her call on another chat),
spoken at a pause; a money card is said to be tap-only; the call's own direct tool cards and job states are not
repeated (its tool result / kaamwatch already say them)."""
from pathlib import Path

import pytest

from app import voice

ROOT = Path(__file__).resolve().parents[1]


class _Loop:
    def call_soon_threadsafe(self, fn, *a):
        fn(*a)


class _Call:
    def __init__(self, tenant):
        self.tenant = tenant
        self.notes = []

    def push_news(self, text):
        self.notes.append(text)


@pytest.fixture
def live(monkeypatch):
    call = _Call("t-card")
    monkeypatch.setattr(voice, "ACTIVE", {"c-call": [(_Loop(), call)]})
    monkeypatch.setattr(voice, "_CARD_TOLD", {})
    import app.convs as convs
    monkeypatch.setattr(convs, "tenant_of", lambda conv: "t-card" if conv.startswith("c-") else "other")
    return call


def test_a_money_card_reaches_the_call_as_tap_only(live):
    n = voice.card_news("c-call", "bazar_approval", {"id": "ap1", "status": "pending", "title": "Bijli bill",
                                                      "amount": "Rs 1,240"})
    assert n == 1 and len(live.notes) == 1
    note = live.notes[0]
    assert "Card aaya" in note and "Bijli bill" in note and "SIRF phone par card tap" in note and "bolkar nahi" in note


def test_a_non_money_ask_says_she_can_answer(live):
    voice.card_news("c-call", "employee_ask", {"id": "e1", "status": "pending", "what": "Website live karna",
                                               "who": "Web Sahayak", "detail": "preview taiyaar"})
    assert live.notes and "haan / jawab chahiye" in live.notes[0] and "haan_karo" in live.notes[0]


def test_a_result_card_is_told_as_a_result(live):
    voice.card_news("c-call", "artifact", {"id": "a1", "status": "ready", "title": "Diwali offer page"})
    assert live.notes and "Diwali offer page" in live.notes[0] and "natija" in live.notes[0]


def test_the_same_card_state_is_told_once(live):
    p = {"id": "f1", "status": "pending", "title": "Admission form", "fields": [1, 2, 3]}
    voice.card_news("c-call", "ask_form", p)
    voice.card_news("c-call", "ask_form", p)
    assert len(live.notes) == 1


def test_the_calls_own_direct_tool_card_is_not_repeated(live):
    tok = voice.VOICE_DIRECT.set("call-123")
    try:
        assert voice.card_news("c-call", "email_draft", {"id": "d1", "subject": "Invoice"}, call="call-123") == 0
    finally:
        voice.VOICE_DIRECT.reset(tok)
    # ...but a card the full-brain job made (santosh_kaam clears VOICE_DIRECT) IS news
    assert voice.card_news("c-call", "email_draft", {"id": "d2", "subject": "Quote"}, call="call-123") == 1


def test_job_states_stay_with_kaamwatch(live):
    assert voice.card_news("c-call", "video_job", {"id": "v1", "status": "done", "name": "Reel"}) == 0
    assert not live.notes


def test_a_card_from_her_other_chat_reaches_her_call(live):
    assert voice.card_news("c-other-chat", "artifact", {"id": "a9", "status": "ready", "title": "Menu"}) == 1
    assert live.notes and "Menu" in live.notes[0]
    assert voice.card_news("x-someone-else", "artifact", {"id": "a8", "status": "ready", "title": "X"}) == 0


def test_no_call_and_plumbing_kinds_do_nothing(monkeypatch):
    monkeypatch.setattr(voice, "ACTIVE", {})
    assert voice.card_news("c-call", "artifact", {"id": "a1", "status": "ready", "title": "x"}) == 0
    for k in ("message", "delta", "step", "typing", "voice_ring", "goal"):
        assert k in voice._CARD_NOT


def test_bus_publish_hands_cards_to_the_call():
    src = (ROOT / "app" / "events.py").read_text()
    assert "_v.card_news(conversation_id, kind, payload, call)" in src
    assert '_sys.modules.get(__package__ + ".voice")' in src        # no voice import when no call can be live
    v = (ROOT / "app" / "voice.py").read_text()
    # v0.657: santosh_kaam marks its cards as the call's own brain ask ("kaam:<call>"): remembered for her tap, not
    # told twice (the brain's own answer says it)
    assert 'VOICE_DIRECT.set(f"kaam:{self.call_id}" if name == "santosh_kaam" else self.call_id)' in v


def test_the_call_screen_shows_the_generic_card():
    dart = (ROOT.parent / "lib" / "call_session.dart").read_text()
    assert "'any_card'" in dart


def test_end_to_end_a_published_card_reaches_the_live_call(env, monkeypatch):
    from app.db import Conversation, session
    from app.events import bus
    with session() as s:
        s.add(Conversation(id="c-e2e", tenant_id="t-e2e"))
    call = _Call("t-e2e")
    monkeypatch.setattr(voice, "ACTIVE", {"c-e2e": [(_Loop(), call)]})
    monkeypatch.setattr(voice, "_CARD_TOLD", {})
    bus.publish("c-e2e", "studio_approval", {"id": "sa1", "status": "pending", "title": "Video shots",
                                             "amount_inr": 340})
    assert len(call.notes) == 1 and "tap" in call.notes[0]
