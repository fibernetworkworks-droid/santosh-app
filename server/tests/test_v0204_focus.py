"""v0.204.0 FOCUSED WORD-LEVEL MEMORY (owner: "WHY HOOLA NOT ABLE TO KEEP THE THING INTACT ONCE TELL BY USER ---
FORGOT THE ENTIRE JUST PREVIOUS WORK. ALSO FORGOT WORD AND EVERYTHING. ALSO IF CALL DROPS WITH USER FORGOT ALL
CURRENT GOING WORK. IT MUST BE LIKE HUMAN. FOCUSED WORD LEVEL MEMORY WITH BOTH VOICE TO VOICE AND CHAT"):

The RCA: a fresh voice session was briefed by 360-char ONE-LINERS (one_line(ex, 360)), greeting() told a fresh
session to never bring up anything from before (a dropped call > 25s grace opened like a cold start), and in chat
everything older than the newest ~4 exchanges was compressed to gist lines with 40-60 char values.

The fix, tested here:
1. yaad.focus_block - her newest messages VERBATIM (word by word), chat AND [Voice call] turns alike, from the DB
   (a pm2 restart forgets nothing), capped and "focused"; rides every chat turn (turn_block) and every voice
   session (voice_block).
2. yaad.FocusNote - the call that died mid-air: voice.py saves her last words + the half-said sentence at grace
   expiry; the next call consumes it once and CONTINUES the work instead of a fresh greeting.
"""
import asyncio
from collections import deque

import app.yaad as yaad
from app.config import get_settings
from app.db import Conversation, session
from app.main import APP_VERSION
from app.agent.santosh import _save
from app.voice import Call, greeting


def _conv(conv):
    with session() as sdb:
        if sdb.get(Conversation, conv) is None:
            sdb.add(Conversation(id=conv, tenant_id="default", title="t"))


def _say(conv, text, voice=False):
    _conv(conv)
    if voice:
        _save(conv, "user", f"[Voice call] {text}", display=text)
    else:
        _save(conv, "user", text, display=text)


# ---------------- 1. the focus block: word by word ----------------

def test_focus_words_are_verbatim(env):
    conv = "c_focus"
    _say(conv, "Sharma Traders ko 12 kaam bhejne hain, file ka naam march.xlsx hai")
    _say(conv, "Ramesh ka number 98765 save kar lo, wo plumber hai")
    fb = yaad.focus_block("default", conv)
    assert "uske APNE shabd" in fb
    assert "march.xlsx" in fb and "98765" in fb          # the exact words, not a gist of them
    assert "Ramesh" in fb and "plumber" in fb
    assert "[/focus]" in fb


def test_voice_call_turns_are_words_too(env):
    """Both paths, ONE memory: a [Voice call] turn shows up word-for-word next to chat turns."""
    conv = "c_focus_voice"
    _say(conv, "chat wali baat: invoice 401 bhej do")
    _say(conv, "call wali baat: kal 4 baje plumber bulana", voice=True)
    fb = yaad.focus_block("default", conv)
    assert "invoice 401" in fb
    assert "kal 4 baje plumber bulana" in fb             # the call's words, verbatim, no [Voice call] prefix
    assert "[Voice call]" not in fb


def test_focus_excludes_the_current_message(env):
    conv = "c_focus_now"
    _say(conv, "purani baat: kaam 2 din pehle bataya tha")
    cur = "abhi ki message jo already jawab ho rahi hai"
    _say(conv, cur)
    fb = yaad.focus_block("default", conv, exclude_text=cur)
    assert "purani baat" in fb
    assert cur not in fb                                  # the current message is the message itself - never echoed


def test_turn_block_carries_focus(env):
    conv = "c_focus_turn"
    _say(conv, "file march.xlsx ke 12 row theek karne the")
    cur = "wahi file phir se dikha do"
    _say(conv, cur)
    tb = yaad.turn_block("default", conv, cur)
    assert "[Hoola ki yaad - FOCUS" in tb
    assert "march.xlsx" in tb                             # 'wahi file' now has its exact words one block above


def test_voice_block_leads_with_words(env):
    conv = "c_focus_vb"
    _say(conv, "petrol pump ka bill 950 ka tha", voice=True)
    vb = yaad.voice_block("default", conv)
    assert "uske APNE shabd" in vb
    assert "petrol pump ka bill 950 ka tha" in vb         # verbatim before any one-line gist


def test_focus_caps(env, monkeypatch):
    st = get_settings()
    monkeypatch.setattr(st, "focus_user_words", 2, raising=False)
    monkeypatch.setattr(st, "focus_word_chars", 80, raising=False)
    conv = "c_focus_cap"
    for i in range(6):
        _say(conv, f"baat number {i}: " + "lamba shabd " * 40)
    fb = yaad.focus_block("default", conv)
    assert len(fb) <= 800 + 200                           # cap + the tag lines
    assert "baat number 5" in fb and "baat number 0" not in fb   # only the newest 2


def test_empty_conversation_empty_block(env):
    _conv("c_focus_empty")
    assert yaad.focus_block("default", "c_focus_empty") == ""


# ---------------- 2. the call that died mid-air ----------------

def test_drop_note_write_read_consume_once(env):
    conv = "c_drop"
    _conv(conv)
    yaad.note_call_drop(conv, "default", "aakhri poori baat: pizza order karna tha | beech mein ye keh rahi thi: address 12 gaon road")
    assert "pizza order" in yaad.recent_call_drop(conv, 60)
    got = yaad.take_call_drop(conv, 60)                   # the next call consumes it ONCE
    assert "pizza order" in got
    assert yaad.take_call_drop(conv, 60) == ""            # ...and it is gone
    assert yaad.recent_call_drop(conv, 60) == ""


def test_old_drop_note_is_not_continued(env, monkeypatch):
    conv = "c_drop_old"
    _conv(conv)
    yaad.note_call_drop(conv, "default", "bahut purani baat")
    monkeypatch.setattr(env["settings"], "voice_continuation_min", 60, raising=False)
    with session() as sdb:                                # age the note beyond the continuation window
        r = sdb.query(yaad.FocusNote).order_by(yaad.FocusNote.id.desc()).first()
        from datetime import datetime, timedelta, timezone
        r.at = datetime.now(timezone.utc) - timedelta(hours=3)
    assert yaad.recent_call_drop(conv, 60) == ""


def test_grace_expiry_saves_her_words(env, monkeypatch):
    """The phone never came back: her last complete words + the half-said sentence survive the drop."""
    conv = "c_drop_call"
    _conv(conv)
    ws = type("FakeWS", (), {})()
    call = Call(ws, conv=conv, voice="Puck", lang="hi-IN", tenant="default")
    call.recent.append(("pizza order karni thi 2 logon ke liye", "theek hai, size batayen"))
    call.user_buf = "aur address hai 12 ga"
    call._save_drop_note()
    note = yaad.recent_call_drop(conv, 60)
    assert "pizza order karni thi" in note
    assert "aur address hai 12 ga" in note                # the half-said sentence is not lost with the call


def test_grace_timer_writes_note_and_closes(env, monkeypatch):
    conv = "c_drop_timer"
    _conv(conv)
    monkeypatch.setattr(env["settings"], "voice_resume_grace_s", 1, raising=False)
    ws = type("FakeWS", (), {})()
    call = Call(ws, conv=conv, voice="Puck", lang="hi-IN", tenant="default")
    call.ws = None
    call.recent.append(("sheet mein 500 rupay ka hisaab karna hai", "theek hai"))
    asyncio.run(call._grace_timer())
    assert call.closed.is_set()
    assert "500 rupay" in yaad.recent_call_drop(conv, 60)


def test_abandoned_dial_writes_no_note(env):
    """Nobody said anything: an abandoned dial is not a dropped chat - no note, no false continuation."""
    conv = "c_drop_silent"
    _conv(conv)
    ws = type("FakeWS", (), {})()
    call = Call(ws, conv=conv, voice="Puck", lang="hi-IN", tenant="default")
    call._save_drop_note()
    assert yaad.recent_call_drop(conv, 60) == ""


def test_greeting_continuation_vs_fresh(env):
    cont = greeting("default", "m", continuation="aakhri poori baat: march.xlsx ke rows")
    assert "NAYA CALL NAHI HAI" in cont and "march.xlsx" in cont
    assert "good morning" not in cont.lower()
    fresh = greeting("default", "m")
    assert "NAYA CALL NAHI HAI" not in fresh
    assert "The call just connected" in fresh


def test_ensure_focus_table_idempotent(env):
    yaad.ensure_focus_table()
    yaad.ensure_focus_table()                             # checkfirst: never raises, the live-DB self-heal


# ---------------- 3. the release pin ----------------

def test_version(env):
    assert APP_VERSION == "0.257.0"
