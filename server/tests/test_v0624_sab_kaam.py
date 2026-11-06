"""v0.624 SAB KAAM CALL PAR (owner: "ANY JOB GIVEN EVEN EMAIL OR ANY TASK ---- IT IS GOING TO SETTING REMINDER TOOL ...
MAKE VOICE CALL GENERALIZE FOR ALL TASKS AND ALL 100% WORK THAT IS PERFORM BY CHAT").
A create_reminder the call model reaches for when her words carry no reminder ask is refused BY CODE and her real ask goes
to santosh_kaam (the full chat brain). Every call tool is logged with her words, so the next report has evidence."""
from __future__ import annotations

import asyncio
import logging
from collections import deque
from types import SimpleNamespace

from app import voice


def _fake(words="", recent=()):
    got = []

    async def delegate(req):
        got.append(req)
        return {"status": "working", "note": "chal raha hai"}

    c = SimpleNamespace(user_buf=words, recent=deque(recent, maxlen=20), call_id="c1", stats={}, _delegate=delegate,
                        ctx=SimpleNamespace(place=None), _mcp_route={}, _place=lambda t: None)
    c._her_words = lambda: voice.Call._her_words(c)
    return c, got


def test_reminder_words_are_told_apart_from_other_jobs():
    yes = ["do minute baad yaad dilana", "5 baje paani peena", "बीपी की दवाई याद दिलाना", "10 मिनट बाद बताना",
           "remind me in 10 minutes", "kal subah 9 baje dawai", "alarm laga do 6 ka", "paanch minute baad bolna"]
    no = ["Rahul ko email bhejo ki meeting kal hai", "meri inbox check karo", "Gmail mein naya mail dekho",
          "google pe weather dekho", "Excel sheet bana do sales ki", "Riya ko whatsapp karo ki aaj aana",
          "kal ki meeting ka agenda bana do"]
    assert all(voice.reminder_wanted(x) for x in yes)
    assert not any(voice.reminder_wanted(x) for x in no)


def test_an_email_ask_never_becomes_a_reminder(env, caplog):
    c, got = _fake("Rahul ko email bhejo ki kal meeting 4 tareekh ko hai")
    with caplog.at_level(logging.INFO, logger="santosh.voice"):
        out = asyncio.run(voice.Call._execute(c, "create_reminder", {"text": "Rahul ko email", "in_minutes": 1}))
    assert got == ["Rahul ko email bhejo ki kal meeting 4 tareekh ko hai"]
    assert "reminder_nahi" in out and c.stats["reminder_redirects"] == 1
    from app.db import Reminder, session
    with session() as s:
        assert s.query(Reminder).count() == 0                 # nothing she did not ask for was set
    assert "tool create_reminder | she said" in caplog.text


def test_a_real_reminder_still_sets(env, monkeypatch):
    seen = []

    async def fake_dispatch(name, args, ctx):
        seen.append(name)
        return {"ok": True}
    monkeypatch.setattr(voice, "dispatch", fake_dispatch)
    c, got = _fake("do minute baad yaad dilana paani peena")
    out = asyncio.run(voice.Call._execute(c, "create_reminder", {"text": "paani", "in_minutes": 2}))
    assert seen == ["create_reminder"] and got == [] and out == {"result": {"ok": True}}


def test_typed_line_and_last_turn_count_as_her_words():
    import time
    c, _ = _fake("", recent=[("meri inbox dekho", "dekh raha hoon")])
    assert voice.Call._her_words(c) == "meri inbox dekho"
    c._typed = ("Excel sheet bana do", time.monotonic())
    assert voice.Call._her_words(c) == "Excel sheet bana do"


def test_switch_and_words_in_the_call():
    from app.config import Settings
    assert Settings.model_fields["voice_reminder_guard"].default is True
    p = voice.persona_prompt("Santosh", "m")
    assert "EVERY job she can give in chat works on this call" in p
    spec = next(t for t in voice._tool_specs() if t["name"] == "create_reminder")
    assert "NEVER a reminder" in spec["description"] 
