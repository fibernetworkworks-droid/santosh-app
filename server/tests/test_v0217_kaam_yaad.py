"""v0.217.0 KAAM YAAD - Wave 1 of the voice-to-voice PERFECT plan: the work the two of them share
becomes a first-class memory surface on a call.

1. UNDELIVERED WORK NEWS IS VISIBLE: v0.214 kept late results as call_followup notes and the NEXT call
   OPENS with the news - but only ONE note (the newest) was ever spoken; older pending news sat in the
   dark for its 7-day life. KAAM KA HAAL inside HOOLA KI YAAD now leads the block with the REST of the
   pending news (a fresh call skips the greeting's newest note so the same news is never said twice; a
   reconnect skips nothing), each line scrubbed like every memory surface, capped at 3, clipped, and
   held to the same freshness window as the take.
2. THE WORK DISCIPLINE IS IN THE BRIEF: continue open work on your own (never 'kya karna tha' again),
   bring up undelivered news ONCE yourself at a natural pause, ask ONE short clarifying line when her
   ask is half-clear and then proceed on your own (standing silent is failure), and one beat of
   result-check before saying a tool's / delegated result ('jo aaya woh yeh hai, par aapne yeh maanga tha').
3. THE GREETING TIES IN: with followup news, the greeting now points at KAAM KA HAAL for the rest of
   the pile instead of leaving it unspoken.
"""
import pytest

import app.yaad as yaad
from app import voice
from app.db import Conversation, Message, session
from app.main import APP_VERSION
from app.yaad import _news_pending, voice_block


def _conv(conv: str) -> None:
    with session() as sdb:
        if sdb.get(Conversation, conv) is None:
            sdb.add(Conversation(id=conv, tenant_id="default", title="t"))


def _her_words(conv: str, text: str) -> None:
    with session() as sdb:
        sdb.add(Message(conversation_id=conv, role="user", content=[{"type": "text", "text": text}],
                        display=text, in_history=True))


def _age_note(conv: str, minutes: int) -> None:
    """Push every note of this chat `minutes` into the past (test the freshness window)."""
    from datetime import datetime, timedelta, timezone
    with session() as sdb:
        for r in sdb.query(yaad.FocusNote).filter(yaad.FocusNote.conversation_id == conv).all():
            r.at = datetime.now(timezone.utc) - timedelta(minutes=minutes)


# ---------------- 1. the pending-news pile ----------------

def test_news_pending_skips_newest_for_fresh_call(env):
    conv = "c_ky_fresh"
    _conv(conv)
    yaad.note_call_followup(conv, "default", "pehli news - sheet taiyar hui thi")     # older
    yaad.note_call_followup(conv, "default", "doosri news - sabse nayi")              # newest
    news = _news_pending(conv, 720, skip_newest=True)
    assert news == ["pehli news - sheet taiyar hui thi"]      # the greeting speaks the newest; block lists the REST


def test_news_pending_reconnect_shows_everything(env):
    conv = "c_ky_re"
    _conv(conv)
    yaad.note_call_followup(conv, "default", "pehli news")
    yaad.note_call_followup(conv, "default", "doosri news - sabse nayi")
    news = _news_pending(conv, 720, skip_newest=False)
    assert news[0] == "doosri news - sabse nayi"              # newest first
    assert len(news) == 2                                     # nothing hidden on a reconnect


def test_news_pending_window_drops_stale_news(env):
    conv = "c_ky_old"
    _conv(conv)
    yaad.note_call_followup(conv, "default", "purani news jo ab kaam ki nahi")
    _age_note(conv, 800)                                      # past the 720-min take window
    assert _news_pending(conv, 720, skip_newest=True) == []   # stale news is nobody's news


def test_news_pending_capped_clipped_and_scrubbed(env):
    conv = "c_ky_cap"
    _conv(conv)
    yaad.note_call_followup(conv, "default", "n-1")
    yaad.note_call_followup(conv, "default", "n-2")
    yaad.note_call_followup(conv, "default", "n-3")
    yaad.note_call_followup(conv, "default", "n-4")
    yaad.note_call_followup(conv, "default", "order id 1234567890 bana diya tha " + "lamba " * 80)   # newest: skipped
    news = _news_pending(conv, 720, skip_newest=True)
    assert news == ["n-4", "n-3", "n-2"]                      # newest skipped, then newest-first, cap 3
    assert len(news[0]) <= 240 and all(len(t) <= 240 for t in news)
    yaad.note_call_followup(conv, "default", "order id 1234567890 ho gaya")
    yaad.note_call_followup(conv, "default", "ek aur")
    news = _news_pending(conv, 720, skip_newest=False)        # the digit run must never ride the prompt raw
    assert all("1234567890" not in t for t in news) and any("######" in t for t in news)


def test_voice_block_leads_with_kaam_ka_haal(env):
    conv = "c_ky_block"
    _conv(conv)
    _her_words(conv, "website ka colour scheme badalna hai")
    yaad.note_call_followup(conv, "default", "pehli news - website ka draft ban gaya tha")
    yaad.note_call_followup(conv, "default", "doosri news - sabse nayi")
    block = voice_block("default", conv, news_skip_newest=True)
    assert block.startswith("HOOLA KI YAAD")
    assert "KAAM KA HAAL" in block and "doosri news" not in block and "pehli news" in block
    assert block.index("KAAM KA HAAL") < block.index("IS WAQT KA KAAM")   # work news BEFORE chat memory


def test_voice_block_no_news_no_kaam_header(env):
    conv = "c_ky_empty"
    _conv(conv)
    _her_words(conv, "kal mandir jaana hai")
    assert "KAAM KA HAAL" not in voice_block("default", conv)   # nothing pending: no forced work report


# ---------------- 2. the discipline is in the brief ----------------

def test_brief_carries_the_work_discipline():
    brief = " ".join(voice.PERSONA.split())
    assert "never ask again what is already settled" in brief
    assert "bring it up ONCE yourself at a natural pause" in brief
    assert "ONE short clarifying line" in brief and "standing silent or waiting helpdesk-style is failure" in brief
    assert "par aapne yeh maanga tha" in brief                 # the result-check, in his own mouth


def test_run_wiring_pin_news_skip_newest():
    src = open(voice.__file__).read()
    assert "news_skip_newest=first" in src                     # fresh call hides the greeting's news
    assert "voice_block, self.ctx.tenant_id" in src


def test_greeting_followup_points_at_kaam_ka_haal():
    g = " ".join(voice.greeting("default", followup="sheet ban gayi thi").split())
    assert "KAAM KA HAAL" in g and "EK-EK karke" in g          # the rest of the pile gets a path to her ears


def test_greeting_fresh_still_carries_the_kaam_line():
    g = " ".join(voice.greeting("default").split())
    assert "if HOOLA KI YAAD shows a kaam still open" in g     # v0.214 continuity wording intact


def test_version():
    assert APP_VERSION == "0.300.0"
