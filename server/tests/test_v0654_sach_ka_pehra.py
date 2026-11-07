"""v0.654 SACH KA PEHRA (owner: "CKECK IT DOES NOT GIVE FALSE REPLY REDARDING TASK WORK" -> audit -> GO): a reply that
says the work is done is checked against what the tools REALLY did - a card / draft waiting for her tap is not "bhej
diya", a read is not an action, the claim's own clause decides, and a call's own unbacked "ho gaya" is corrected."""
from __future__ import annotations

import time
import types

import pytest

from app.agent import draftcheck as d

DRAFT = {"tool": "email_draft", "ok": True, "result": "{'draft_id': 'd1', 'to': 'sharma@x.in', 'status': 'pending_approval'}"}
APPROVAL = {"tool": "bazar_run", "ok": True, "result": "{'needs_approval': True, 'approval_id': 'ap1', 'say': 'card bheja'}"}
READ = {"tool": "email_check", "ok": True, "result": "3 new mails"}
SENT = {"tool": "email_send", "ok": True, "result": "{'status': 'sent', 'id': 'm1'}"}
REMINDER = {"tool": "create_reminder", "ok": True, "result": "{'id': 'r1', 'when': '5 pm', 'status': 'active'}"}
FAILED_SEND = {"tool": "email_send", "ok": False, "error": "token expired"}

FALSE = [   # (what ran, the reply, the nudge it must get)
    ([DRAFT], "Sharma ji ko mail bhej diya hai.", "card"),
    ([DRAFT], "Done, I've sent the email to Sharma.", "card"),
    ([APPROVAL], "Order kar diya, 20 minute mein aa jayega.", "card"),
    ([APPROVAL], "Payment ho gaya, Rs 500 chale gaye.", "card"),
    ([READ], "Mail bhej diya.", "plain"),
    ([], "Aapki website live ho gayi.", "plain"),
    ([], "Post kar diya Instagram par.", "plain"),
    ([], "The meeting has been booked for 4 pm.", "plain"),
    ([FAILED_SEND], "Mail bhej diya hai.", "plain"),
    ([READ, DRAFT], "WhatsApp kar diya sabko.", "card"),
]
TRUE = [    # honest replies that must pass untouched
    ([SENT], "Mail bhej diya."),
    ([REMINDER], "Reminder laga diya, 5 baje."),
    ([DRAFT], "Draft taiyaar hai, Bhejo dabaiye to chala jayega."),
    ([APPROVAL], "Card bheja hai, aapki haan se order hoga."),
    ([], "Aap haan kahein to bhej dunga."),
    ([], "Aapne mail bhej diya tha, maine dekh liya."),
    ([READ], "I haven't sent anything yet - want me to?"),
    ([], "Agar aap kahein to booking kar dunga."),
]


@pytest.mark.parametrize("calls,text,want", FALSE)
def test_a_false_done_is_caught(calls, text, want):
    got = d.fake_done({"calls": calls}, text)
    assert got == (d.NUDGE_CARD if want == "card" else d.NUDGE), text


@pytest.mark.parametrize("calls,text", TRUE)
def test_an_honest_reply_passes(calls, text):
    assert d.fake_done({"calls": calls}, text) == "", text


def test_second_time_the_honest_line_is_added_in_her_language():
    st = {"calls": [DRAFT]}
    assert d.fake_done(st, "Mail bhej diya hai.") == d.NUDGE_CARD
    assert d.fake_done(st, "Haan mail bhej diya hai.") == "" and st["correct"] == d.SAID_CARD
    st = {"calls": [DRAFT]}
    d.fake_done(st, "I've sent the email.")
    d.fake_done(st, "Yes, I've sent the email.")
    assert st["correct"] == d.SAID_CARD_EN


def test_effects_of_real_tool_results():
    assert d.effect(DRAFT) == "card" and d.effect(APPROVAL) == "card"
    assert d.effect(READ) == "read" and d.effect(SENT) == "did" and d.effect(REMINDER) == "did"
    assert d.effect(FAILED_SEND) == ""


def test_read_tools_are_known_by_name_across_the_whole_registry():
    from app.agent.tools import TOOLS
    names = {t["name"] for t in TOOLS}
    for n in ("email_check", "list_reminders", "get_campaign_status", "calendar_agenda", "kaam_status", "crawl_status"):
        if n in names:
            assert d._is_read(n), n
    for n in ("list_add", "list_done", "email_send", "create_reminder", "email_draft", "bazar_run", "calendar_add_event"):
        assert not d._is_read(n), n
    # nothing that changes the world may pass as a read
    for n in names:
        if d._is_read(n):
            assert not d._CHANGE_WORD.search(n + "_") or n in d.READS or n.endswith("_dekho"), n


def test_the_claims_own_clause_decides():
    assert d.claims_done("Order kar diya, 20 minute mein aa jayega.") != ""   # "jayega" is the NEXT clause
    assert d.claims_done("Haan kahenge to order kar dunga.") == ""


# ---------------------------------------------------------------- the call's own words
def _fake_call(did=0, news_ago=1000.0, started_ago=1000.0):
    from app import voice
    said = []
    now = time.monotonic()
    c = types.SimpleNamespace(did=[{"tool": "email_send", "ok": True, "n": i + 1} for i in range(did)], _did_mark=0, _news_sent_at=now - news_ago,
                              _started_at=now - started_ago, stats={}, push_news=said.append, call_id="t")
    return c, said, voice


def test_a_call_that_says_done_with_no_tool_is_corrected():
    c, said, voice = _fake_call()
    voice.Call._check_spoken_claim(c, "Haan, maine Sharma ji ko mail bhej diya.")
    assert said and "Sudhaar" in said[0] and "kuch nahi hua hai" in said[0] and c.stats["voice_fake_done"] == 1


def test_a_call_relaying_news_or_using_a_tool_is_left_alone():
    c, said, voice = _fake_call(did=1)
    voice.Call._check_spoken_claim(c, "Mail bhej diya.")                 # a tool ran this turn
    c2, said2, _ = _fake_call(news_ago=20)
    voice.Call._check_spoken_claim(c2, "Website ka kaam ho gaya.")      # it is saying the news it just got
    c3, said3, _ = _fake_call(started_ago=10)
    voice.Call._check_spoken_claim(c3, "Aapka report ho gaya tha, kaam ho gaya.")   # the opening brief
    c4, said4, _ = _fake_call()
    voice.Call._check_spoken_claim(c4, "Card bheja hai, aapki haan se bhej dunga.")  # honest
    assert said == said2 == said3 == said4 == []


def test_the_tool_count_is_per_turn():
    c, said, voice = _fake_call(did=2)
    voice.Call._check_spoken_claim(c, "Theek hai.")       # turn 1: two tools, nothing claimed
    voice.Call._check_spoken_claim(c, "Mail bhej diya.")  # turn 2: no new tool - corrected
    assert len(said) == 1
