"""v0.704 CARD KI KHABAR CHAT MEIN (owner: "WHEN ANY TASK LANDS ON CARD AND USER PRESS SEND, APPROVE ETC --- HOOLA DONT
KNOW THAT CARD ACTIVITY IS DONE" + "FOR EVERY WORK IT TAKES TIME"): (1) her Send tap on an email draft arrives as
email_sent, a different kind, so the draft looked pending for ever - now one card; (2) every chat turn hears which cards
she answered since the last reply and which still wait; (3) the chat turn's memory parts are read in parallel."""
from __future__ import annotations

import inspect
from datetime import datetime, timedelta, timezone

from app.db import Conversation, session

T = "default"


def _chat(cid):
    with session() as s:
        s.add(Conversation(id=cid, tenant_id=T))
    from app import convs
    convs._CACHE.clear()
    convs.mark(T, cid)
    return cid


def _draft(status):
    return {"id": "eml_1", "to": "kunal@example.com", "subject": "Kal meeting", "status": status}


def test_sent_email_is_no_longer_waiting(env):
    from app import events
    from app.events import bus
    _chat("c1")
    bus.publish("c1", "email_draft", _draft("pending"))
    ws = events.waiting_cards(T)
    assert ws and "Kal meeting" in ws[0]["title"]
    bus.publish("c1", "email_sent", _draft("sent"))                 # her Send tap
    assert events.waiting_cards(T) == []


def test_chat_turn_hears_her_tap(env):
    from app import events
    from app.events import bus
    _chat("c2")
    before = datetime.now(timezone.utc) - timedelta(seconds=5)
    bus.publish("c2", "email_draft", _draft("pending"))
    blk = events.card_news_block(T, before, "kaunse cards pending hain?")
    assert "still waiting" in blk and "Kal meeting" in blk
    bus.publish("c2", "email_sent", _draft("sent"))
    blk = events.card_news_block(T, before, "kaunse cards pending hain?")
    assert "answered since your last reply" in blk and "SENT" in blk and "still waiting" not in blk
    # an answer older than the last reply is old news
    assert events.card_news_block(T, datetime.now(timezone.utc) + timedelta(seconds=5)) == ""


def test_approval_and_cancel(env):
    from app import events
    from app.events import bus
    _chat("c3")
    before = datetime.now(timezone.utc) - timedelta(seconds=5)
    bus.publish("c3", "bazar_approval", {"id": "ap1", "title": "Swiggy order", "status": "pending"})
    bus.publish("c3", "bazar_approval", {"id": "ap1", "title": "Swiggy order", "status": "rejected"})
    blk = events.card_news_block(T, before)
    assert "Swiggy order" in blk and "REJECTED" in blk


def test_a_normal_ask_gets_no_waiting_list(env):
    """v0.709 her 9 Nov ask ('AI agent jo YouTube video dekh ke seekhe...') was answered with 'Good morning. Quick
    state: 4 site spec cards waiting...' - the waiting list rode EVERY turn. Now only when she asks about pending work."""
    from app import events
    from app.events import bus
    _chat("c5")
    bus.publish("c5", "email_draft", _draft("pending"))
    ask = "AI agent jo YouTube video dekh ke form bharna seekhe aur yaad rakhe"
    assert events.card_news_block(T, None, ask) == ""
    assert "Kal meeting" in events.card_news_block(T, None, "kya kya baaki hai?")


def test_chat_memory_parallel_and_wired():
    from app.agent import santosh
    src = inspect.getsource(santosh._run_turn) if hasattr(santosh, "_run_turn") else open("app/agent/santosh.py").read()
    full = open("app/agent/santosh.py").read()
    assert "block = await _chat_memory(" in full
    cm = inspect.getsource(santosh._chat_memory)
    assert "asyncio.wait(" in cm and "card_news_block" in cm and "kaamwatch.block" in cm
    assert cm.index("kaamwatch.block") < cm.index("_coder.inject.turn_block")
    del src


def test_card_alias_keeps_the_draft_place():
    from app import events
    assert events.card_key("email_sent", {"id": "x"}, 1) == events.card_key("email_draft", {"id": "x"}, 2)
