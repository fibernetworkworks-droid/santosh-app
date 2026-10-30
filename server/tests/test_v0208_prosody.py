"""v0.210.0 AWAAZ-3 - the TurnMeter joins the feeling engine (Phase C's remainder: prosody sharpening).

The v0.202 promise in voiceaffect's docstring is now kept: her words still pick the state (prosody NEVER
fires alone), but her voice THIS turn - measured mid-turn against HER OWN baseline (voicestyle profile
facts, not absolute numbers: a phone mic lies, her normal doesn't) - can VETO a glad note it contradicts
(sarcasm, thakaan: a celebration voice over flat words is the exact uncanny note the precision rule
forbids), CONFIRM a low one, and her measured thinking-pauses add the 'jaldi mat kaato' rider to whatever
note goes out (the ear test's list-rush failure, grounded in her own pauses)."""
import asyncio
import math
from types import SimpleNamespace

import numpy as np

from app import voice, voiceaffect

SR = 16000


def _tone(f, ms, amp=0.2):
    t = np.arange(int(SR * ms / 1000)) / SR
    return (amp * np.sin(2 * np.pi * f * t) * 32767).astype(np.int16).tobytes()


def _sil(ms):
    return np.zeros(int(SR * ms / 1000), dtype=np.int16).tobytes()


# her baseline (what voicestyle.profile_view facts carry for a speaker with these medians)
BASE = {"pitch_hz": 210.0, "level_db": -20.0, "tone_spread_st": 6.0}


def _pros(pitch=210.0, level=-20.0, spread=6.0, voiced=2.0, pauses=()):
    return {"voiced_s": voiced, "pauses": list(pauses), "level": level, "pitch": pitch, "spread": spread}


# ---------------- TurnMeter.peek: the mid-turn, non-destructive look ----------------

def _fed_meter():
    m = voiceaffect  # noqa: F841  (keep the import meaningful for readers)
    from app.voicestyle import TurnMeter
    tm = TurnMeter()
    for c in [_tone(200, 100)] * 8 + [_sil(100)] * 6 + [_tone(220, 100)] * 5 + [_sil(100)] * 3 + [_tone(180, 100)] * 4:
        tm.add(c)
    return tm


def test_peek_does_not_reset_the_meter():
    tm = _fed_meter()
    a, b = tm.peek(), tm.peek()
    assert a == b and a["voiced_s"] > 1.0          # two peeks, same data: nothing was consumed
    taken = tm.take()
    assert taken == a                              # take() returns exactly what peek saw...
    assert tm.take()["voiced_s"] == 0              # ...and only take() empties the turn


def test_peek_has_the_same_shape_take_had():
    tm = _fed_meter()
    p = tm.peek()
    assert set(p) == {"voiced_s", "speech_s", "pauses", "level", "pitch", "spread"}
    assert p["pauses"] == [600, 300]               # the same mid-sentence pauses v0.119 already measured
    assert 170 < p["pitch"] < 230 and p["spread"] > 1
    assert p["level"] is not None and p["level"] < 0


# ---------------- sharpen: words pick the state, her voice sharpens it ----------------

def test_prosody_never_fires_alone():
    assert voiceaffect.sharpen("", _pros(), BASE) == ("", "no_words")


def test_thin_prosody_leaves_the_words_in_charge():
    # less than 1.2 s of real voice proves nothing; no baseline (new speaker) proves nothing
    assert voiceaffect.sharpen("glad", _pros(voiced=0.6, pitch=160.0), BASE) == ("glad", "words_lead")
    assert voiceaffect.sharpen("low", None, BASE) == ("low", "words_lead")
    assert voiceaffect.sharpen("low", _pros(pitch=160.0), {}) == ("low", "words_lead")
    assert voiceaffect.sharpen("glad", _pros(pitch=None), BASE) == ("glad", "words_lead")


def test_glad_vetoed_when_her_voice_drops():
    # 12*log2(165/210) ~ -4.2 semitones under her own normal: sarcasm ya thakaan, no celebration voice
    assert voiceaffect.sharpen("glad", _pros(pitch=165.0), BASE) == ("", "veto_glad_down")


def test_glad_vetoed_when_she_goes_quiet():
    assert voiceaffect.sharpen("glad", _pros(level=-25.0), BASE) == ("", "veto_glad_quiet")


def test_glad_vetoed_when_her_expressive_voice_goes_flat():
    # her normal spread is 6 st, now she is flat at 1.8: no real joy in it
    assert voiceaffect.sharpen("glad", _pros(spread=1.8), BASE) == ("", "veto_glad_flat")
    # a naturally flat speaker (baseline 2.5 st) saying glad words: not a veto - that is her normal
    assert voiceaffect.sharpen("glad", _pros(spread=1.8), {**BASE, "tone_spread_st": 2.5}) == ("glad", "words_lead")


def test_glad_stands_when_her_voice_agrees():
    assert voiceaffect.sharpen("glad", _pros(pitch=225.0, level=-19.0, spread=7.0), BASE) == ("glad", "words_lead")


def test_low_confirmed_by_her_own_voice():
    # pitch ~1.75 st below her normal, or 4 dB quieter: the heavy-news note is twice as safe
    assert voiceaffect.sharpen("low", _pros(pitch=190.0), BASE) == ("low", "confirmed_low")
    assert voiceaffect.sharpen("low", _pros(level=-24.0), BASE) == ("low", "confirmed_low")


def test_low_without_prosody_agreement_passes_untouched():
    # words said it, her voice sits at her normal: the note still goes (words lead, voice never vetoes low)
    assert voiceaffect.sharpen("low", _pros(pitch=215.0, level=-20.0), BASE) == ("low", "words_lead")


def test_tense_is_never_vetoed():
    # her words said anger; a dropped/quiet voice must not silence that note
    assert voiceaffect.sharpen("tense", _pros(pitch=160.0, level=-26.0, spread=1.5), BASE) == ("tense", "words_lead")


def test_absurd_baseline_is_ignored():
    # a 30 Hz 'baseline' is a mic artefact: no semitone maths on it, words win
    assert voiceaffect.sharpen("glad", _pros(pitch=165.0), {**BASE, "pitch_hz": 30.0}) == ("glad", "words_lead")


# ---------------- the pause rider: her measured thinking-pauses ----------------

def test_rider_needs_two_real_thinking_pauses():
    assert voiceaffect.pause_rider(_pros(pauses=[700, 900])) is not None
    assert voiceaffect.pause_rider(_pros(pauses=[300, 900])) is None      # one 300 ms comma, one real pause
    assert voiceaffect.pause_rider(_pros(pauses=[700])) is None           # a single pause is not a pattern
    assert voiceaffect.pause_rider(_pros(pauses=[700, 900], voiced=0.8)) is None   # barely any voice: no
    assert voiceaffect.pause_rider(None) is None


def test_rider_is_a_small_clean_line():
    assert "jaldi mat kaato" in voiceaffect.PAUSE_RIDER
    assert "{" not in voiceaffect.PAUSE_RIDER and "}" not in voiceaffect.PAUSE_RIDER   # the format() contract
    assert len(voiceaffect.PAUSE_RIDER) < 300


# ---------------- the call wiring ----------------

class _FakeMeter:
    def __init__(self, pros):
        self._pros = pros
        self.peeks = 0

    def peek(self):
        self.peeks += 1
        return dict(self._pros)


class _FakeCall:
    """Just the attributes _affect_watch touches."""

    def __init__(self, text, pros=None, base=None):
        self.vid = None
        self.user_buf = text
        self._affect_last = ""
        self._affect_at = 0.0
        self.stats = {}
        self.notes = []
        self.meter = _FakeMeter(pros) if pros is not None else None
        self._pros_base = base or {}

    async def _tell_quietly(self, note, live=False):
        self.notes.append(note)


def _run(c):
    asyncio.get_event_loop_policy().new_event_loop().run_until_complete(voice.Call._affect_watch(c))


def test_affect_watch_veto_sends_nothing_and_moves_no_clock():
    c = _FakeCall("haan suno, order double ho gaya is mahine!", _pros(pitch=165.0), BASE)
    _run(c)
    assert c.notes == []                              # the celebration note never went out
    assert c.stats["affect_vetoed"] == 1
    assert c._affect_at == 0.0 and c._affect_last == ""   # NO debounce clock moved: later proof can still speak


def test_affect_watch_confirms_low_and_attaches_the_rider():
    c = _FakeCall("mummy hospital mein hai, bahut pareshan hoon",
                  _pros(pitch=190.0, level=-24.0, pauses=[700, 900]), BASE)
    _run(c)
    assert len(c.notes) == 1
    assert "naram" in c.notes[0] and "jaldi mat kaato" in c.notes[0]   # the note + her-pauses rider
    assert c.stats["affect_notes"] == 1 and c.stats["affect_confirmed"] == 1
    assert c.stats["affect_pauses_rider"] == 1


def test_affect_watch_neutral_words_get_no_rider_alone():
    c = _FakeCall("kal 4 baje meeting hai", _pros(pauses=[700, 900]), BASE)
    _run(c)
    assert c.notes == [] and "affect_pauses_rider" not in c.stats   # the rider never fires alone


def test_affect_watch_kill_switch_returns_to_words_only(monkeypatch):
    monkeypatch.setattr(voice, "get_settings", lambda: SimpleNamespace(voice_prosody=False))
    c = _FakeCall("haan suno, order double ho gaya is mahine!", _pros(pitch=165.0), BASE)
    _run(c)
    assert len(c.notes) == 1 and "garmi" in c.notes[0]     # the v0.202 words-only note, exactly as before
    assert c.meter.peeks == 0 and "affect_vetoed" not in c.stats


# ---------------- her baseline reaches the call ----------------

def test_for_call_carries_her_prosody_baseline(env):
    from app import voicestyle as vs
    cs = vs.CallStyle()
    for _ in range(12):
        cs.turn({"pauses": [400], "speech_s": 6.0, "level": -20.0, "pitch": 210.0, "spread": 5.0},
                "Haan ji, kal subah aath baje Rameshwar ko yaad dilana")
    vs.save_call("t208b", cs)
    facts = (vs.for_call("t208b").get("facts") or {})
    assert facts.get("pitch_hz") == 210.0 and facts.get("level_db") == -20.0 and facts.get("tone_spread_st") == 5.0


# ---------------- the scorecard counts the feeling ----------------

def test_scorecard_counts_the_feeling():
    voice.STATS.append({"tenant": "t208", "call_id": "t208c", "ended": 1.0, "turns": 0, "acks": 0, "latency_ms": [],
                        "words": [], "question_endings": 0, "assistantisms": 0, "interruptions": 0,
                        "tools": 0, "silent_tools": 0,
                        "affect_notes": 3, "affect_vetoed": 1, "affect_confirmed": 1, "affect_pauses_rider": 2})
    try:
        s = voice.stats_summary("t208")
        assert s["affect_notes"] == 3 and s["affect_vetoed"] == 1
        assert s["affect_confirmed"] == 1 and s["affect_pauses_rider"] == 2
    finally:
        voice.STATS.pop()


# ---------------- version ----------------

def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.278.0"
