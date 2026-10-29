"""v0.206.0 KAAN KAAPI (Phase B of the natural-voice plan: backchannels). The owner said GOOD to the
feeling engine and asked for the next phase. Gemini Live is half-duplex: while SHE talks (a story, a
list) he stays dead silent till his answer starts, and while a long tool runs the first "ek second" is
followed by dead air again. A real listener does neither: he murmurs tiny sounds in her pauses
("haan...", "achha...") and mutters one honest progress sound when the work runs long. Both silences now
get real sounds, pre-rendered in his own voice through the same TTS pipeline (generation tags b1/p1 ride
in the filenames, like the acks' a2), with hard guards: never on top of his answer, never on top of
another clip, max two murmurs per turn of hers, one clock for every clip."""
import asyncio
import threading
import time
from types import SimpleNamespace

import pytest

from app import voice
from app.main import APP_VERSION


# ---------------- the fakes ----------------

class _FakeCall:
    """Just the attributes the watchers touch (the _affect_watch pattern from the v0.201 tests)."""

    def __init__(self):
        self.voice, self.gender = "Cherry", "f"
        self.closed = threading.Event()
        self.hold = ""
        self.stats = {"backchannels": 0, "progress": 0, "acks": 0, "silent_tools": 0, "latency_ms": []}
        self._latency = None
        self._safe_worked = True               # _mark_audio's setup bookkeeping: already done
        self._safe = 0
        self._turn_end_at = 0.0
        self.user_buf = ""
        self._last_model_audio = 0.0
        self._last_voice_at = 0.0
        self._last_user_text_at = 0.0
        self._turn_audio = False
        self._last_ack = 0.0
        self._last_ack_i = -1
        self._bc_at = 0.0
        # v0.220 the tone surface exists but stays empty on this fake (the pool is never mood-filtered here)
        self._tone, self._tone_at = "", 0.0
        self._tone_now = lambda: voice.Call._tone_now(self)
        self._tone_tag = lambda: voice.Call._tone_tag(self)
        self._bc_this_turn = 0
        self._bc_task = None
        self._last_bc_i = -1
        self._last_prog_i = -1
        self.sent = []
        self.BC_AFTER_S = 0.01      # tests run fast; the real class values are 1.2 s / 8.0 s / 0.7 s
        self.PROG_AFTER_S = 0.01
        self.ACK_AFTER_S = 0.01
        self.BC_MIN_WORDS = 4
        self.BC_WINDOW_S = 0.5      # v0.230 the murmur watches her mic for a breath INSIDE her turn
        self.BC_END_MARGIN_S = 0.15
        self._bc_end_s = lambda: 0.55

    async def send_audio(self, data):
        self.sent.append(data)


def _run(coro):
    return asyncio.get_event_loop_policy().new_event_loop().run_until_complete(coro)


def _awake(c, words="suno na kal ka poora din bhar gaya tha kaam se"):
    """A fake call sitting in HER open turn, in a real pause: she said enough, then went quiet."""
    now = time.monotonic()
    c.user_buf = words
    c._last_voice_at = now - 0.3        # v0.230 a breath inside her sentence (before her end-of-turn pause)
    c._last_user_text_at = now - 0.3    # ...and her last transcription too
    c._last_model_audio = 0.0           # he has said nothing yet
    return c


@pytest.fixture(autouse=True)
def _clean_pools():
    voice._POOLS.clear()
    voice._POOL_BUSY.clear()
    yield
    voice._POOLS.clear()
    voice._POOL_BUSY.clear()


# ---------------- the asks: a murmur, not a question ----------------

def test_bc_ask_is_a_listening_murmur_never_a_question():
    for gender, who in (("f", "woman"), ("m", "guy")):
        a = voice._bc_ask("Haan...", gender)
        assert "listening hard" in a and "never a question" in a and who in a, a
        assert "{" not in a and "}" not in a            # the format() contract
        assert "murmur" in a and "trails off" in a


def test_prog_ask_is_half_to_himself():
    for gender, who in (("f", "woman"), ("m", "guy")):
        a = voice._prog_ask("Dekh raha hoon... ruko.", gender)
        assert "half to yourself" in a and "unhurried" in a and who in a, a
        assert "{" not in a and "}" not in a


# ---------------- the pools: tiny sounds, tagged renders ----------------

def test_clip_filenames_carry_the_generation_tag():
    assert voice._bc_file("Cherry", "f", 3).name == "bc_Cherry_f_3_b2.pcm"
    assert voice._prog_file("Chandu", "m", 1).name == "prog_Chandu_m_1_p2.pcm"
    assert voice._ack_file("Cherry", "f", 3).name == "Cherry_f_3_a3.pcm"     # acks untouched
    names = {voice._bc_file("Cherry", "f", 0).name, voice._prog_file("Cherry", "f", 0).name,
             voice._ack_file("Cherry", "f", 0).name}
    assert len(names) == 3                                                   # no collisions in one cache dir


def test_pool_lines_are_tiny_listener_sounds():
    assert len(voice.BC_LINES) >= 8 and len(voice.PROG_LINES) >= 5
    for line in voice.BC_LINES:
        assert len(line) < 40 and "?" not in line and "haha" not in line.lower(), line
    for line in voice.PROG_LINES:
        assert len(line) < 45 and "?" not in line, line
    assert len(set(voice.BC_LINES)) == len(voice.BC_LINES)                   # variety is the point


def test_pool_builder_uses_cache_and_renders_the_rest(monkeypatch, tmp_path):
    monkeypatch.setattr(voice, "ACK_DIR", tmp_path)
    first = tmp_path / "bc_Cherry_f_0_b2.pcm"
    first.write_bytes(b"CACHED0")
    calls = []

    def fake_tts(ask, voice_name, client=None):
        calls.append(ask)
        return b"\x24\x40" * 4800          # loud enough for _trim to keep

    monkeypatch.setattr(voice, "_tts_clip", fake_tts)
    voice._build_pool("bc", "Cherry", "f")
    clips = voice._POOLS["bc:Cherry:f"]
    assert len(clips) == len(voice.BC_LINES)
    assert clips[0] == b"CACHED0"          # the cached render is kept, not re-spoken
    assert len(calls) == len(voice.BC_LINES) - 1
    assert all("listening hard" in a for a in calls)
    assert (tmp_path / "bc_Cherry_f_1_b2.pcm").exists()
    assert "bc:Cherry:f" not in voice._POOL_BUSY


def test_prog_pool_builds_under_its_own_key(monkeypatch, tmp_path):
    monkeypatch.setattr(voice, "ACK_DIR", tmp_path)
    monkeypatch.setattr(voice, "_tts_clip", lambda ask, v, client=None: b"\x24\x40" * 4800)
    voice._build_pool("prog", "Cherry", "f")
    assert len(voice._POOLS["prog:Cherry:f"]) == len(voice.PROG_LINES)
    assert not (tmp_path / "bc_Cherry_f_0_b2.pcm").exists()        # bc renders were not touched


def test_pool_clips_never_let_a_call_wait(monkeypatch, tmp_path):
    monkeypatch.setattr(voice, "ACK_DIR", tmp_path)
    monkeypatch.setattr(voice, "_tts_clip", lambda ask, v, client=None: b"\x24\x40" * 4800)
    assert voice.pool_clips("prog", "Cherry", "f") == []           # first call: building in the background
    for _ in range(200):
        if "prog:Cherry:f" in voice._POOLS:
            break
        time.sleep(0.02)
    clips = voice.pool_clips("prog", "Cherry", "f")
    assert len(clips) == len(voice.PROG_LINES)                     # the next call gets the full pool


# ---------------- the murmur: her pause, one tiny sound ----------------

def _murmuring_pool(monkeypatch):
    monkeypatch.setattr(voice, "pool_clips", lambda kind, v, g: [b"a", b"b"] if kind == "bc" else [])


def test_bc_watch_plays_one_murmur(monkeypatch):
    _murmuring_pool(monkeypatch)
    c = _awake(_FakeCall())
    _run(voice.Call._bc_watch(c))
    assert len(c.sent) == 1 and c.sent[0] in (b"a", b"b")
    assert c.stats["backchannels"] == 1 and c._bc_this_turn == 1 and c._bc_at > 0
    assert c._last_bc_i in (0, 1)


def test_bc_watch_skips_when_he_is_talking(monkeypatch):
    _murmuring_pool(monkeypatch)
    c = _awake(_FakeCall())
    c._last_model_audio = time.monotonic()      # his audio is the newest sound: it is his turn
    _run(voice.Call._bc_watch(c))
    assert c.sent == [] and c.stats["backchannels"] == 0


def test_bc_watch_skips_when_he_took_this_turn(monkeypatch):
    _murmuring_pool(monkeypatch)
    c = _awake(_FakeCall())
    c._turn_audio = True                        # he already spoke in this turn
    _run(voice.Call._bc_watch(c))
    assert c.sent == []


def test_bc_watch_skips_when_she_resumed(monkeypatch):
    _murmuring_pool(monkeypatch)
    c = _awake(_FakeCall())
    c._last_user_text_at = time.monotonic() + 60     # words newer than now: she is speaking right now
    _run(voice.Call._bc_watch(c))
    assert c.sent == []


def test_bc_watch_skips_on_a_bare_haan(monkeypatch):
    _murmuring_pool(monkeypatch)
    for words in ("haan", "haan haan bolo", ""):
        c = _awake(_FakeCall(), words=words)
        _run(voice.Call._bc_watch(c))
        assert c.sent == [], words


def test_bc_watch_respects_the_per_turn_cap_and_cooldown(monkeypatch):
    _murmuring_pool(monkeypatch)
    c = _awake(_FakeCall())
    c._bc_this_turn = 2                         # two murmurs already went out this turn
    _run(voice.Call._bc_watch(c))
    assert c.sent == []
    c2 = _awake(_FakeCall())
    c2._bc_at = time.monotonic()                # one just played seconds ago
    _run(voice.Call._bc_watch(c2))
    assert c2.sent == []


def test_bc_watch_skips_on_hold_closed_and_flag_off(monkeypatch):
    _murmuring_pool(monkeypatch)
    c = _awake(_FakeCall())
    c.hold = "asked"                            # the talk is not for Hoola right now
    _run(voice.Call._bc_watch(c))
    assert c.sent == []
    c2 = _awake(_FakeCall())
    c2.closed.set()                             # the call is over
    _run(voice.Call._bc_watch(c2))
    assert c2.sent == []
    c3 = _awake(_FakeCall())
    monkeypatch.setattr(voice, "get_settings", lambda: SimpleNamespace(voice_backchannel=False))
    _run(voice.Call._bc_watch(c3))              # the kill switch
    assert c3.sent == []


def test_backchannel_never_lands_on_top_of_an_ack(monkeypatch):
    _murmuring_pool(monkeypatch)
    c = _awake(_FakeCall())
    c._last_ack = time.monotonic() - 2          # an ack clip just played: the ears are busy
    _run(voice.Call._bc_watch(c))
    assert c.sent == []


def test_arm_reschedules_and_mark_audio_cancels(monkeypatch):
    monkeypatch.setattr(voice, "pool_clips", lambda kind, v, g: [])

    async def main():
        c = _FakeCall()
        c._bc_watch = lambda: voice.Call._bc_watch(c)   # bind the real watcher to this fake
        now = time.monotonic()
        c.user_buf = "ek lambi baat bata rahi thi kaam ki poori"
        c._last_voice_at = c._last_user_text_at = now
        voice.Call._arm_backchannel(c)          # armed on her first words
        t1 = c._bc_task
        assert t1 is not None
        voice.Call._arm_backchannel(c)          # re-armed on her next transcription
        await asyncio.sleep(0)
        assert t1.cancelled()                   # the old timer did not survive
        voice.Call._mark_audio(c)               # his voice arrived: the murmur dies
        assert c._bc_task is None
        await asyncio.sleep(0.05)
        assert c.sent == []

    _run(main())


def test_finish_turn_clears_the_cap():
    src = ((__import__("pathlib").Path(__file__).parents[1]) / "app" / "voice.py").read_text(encoding="utf-8")
    assert "self._bc_this_turn = 0" in src      # every turn of hers starts with a fresh murmur budget


# ---------------- the progress sound: a long silent tool ----------------

def _prog_pool(monkeypatch):
    monkeypatch.setattr(voice, "pool_clips", lambda kind, v, g: [b"p1", b"p2"] if kind == "prog" else [])


def test_prog_watch_plays_one_progress_sound(monkeypatch):
    _prog_pool(monkeypatch)
    c = _FakeCall()
    now = time.monotonic()
    c._last_voice_at = now - 6.0                # she has been quiet the whole run
    c._last_ack = now - 7.5                     # the first "ek second" went out long ago
    _run(voice.Call._prog_watch(c, now - 1.0))
    assert len(c.sent) == 1 and c.sent[0] in (b"p1", b"p2")
    assert c.stats["progress"] == 1 and c._last_ack > now - 1


def test_prog_watch_aborts_when_the_result_came(monkeypatch):
    _prog_pool(monkeypatch)
    c = _FakeCall()
    now = time.monotonic()
    c._last_voice_at = now - 6.0
    c._last_ack = now - 7.5
    c._last_model_audio = now                   # he already spoke about it: the result is in
    _run(voice.Call._prog_watch(c, now - 1.0))
    assert c.sent == []


def test_prog_watch_aborts_when_she_talks_or_an_ack_is_fresh(monkeypatch):
    _prog_pool(monkeypatch)
    now = time.monotonic()
    c = _FakeCall()
    c._last_voice_at = now                      # she is talking: the silence is not dead air
    c._last_ack = now - 20
    _run(voice.Call._prog_watch(c, now - 1.0))
    assert c.sent == []
    c2 = _FakeCall()
    c2._last_voice_at = now - 6.0
    c2._last_ack = now - 1.0                    # the first ack just played
    _run(voice.Call._prog_watch(c2, now - 1.0))
    assert c2.sent == []


def test_ack_watch_avoids_the_same_clip_and_respects_a_fresh_murmur(monkeypatch):
    monkeypatch.setattr(voice, "ack_clips", lambda v, g: [b"x", b"y"])
    c = _FakeCall()
    now = time.monotonic()
    c._last_voice_at = now - 5.0
    _run(voice.Call._ack_watch(c, now - 1.0))
    assert len(c.sent) == 1 and c.stats["acks"] == 1 and c._last_ack_i in (0, 1)
    c2 = _FakeCall()
    now2 = time.monotonic()
    c2._last_voice_at = now2 - 5.0
    c2._bc_at = now2                            # a murmur just went out: no ack on top of it
    _run(voice.Call._ack_watch(c2, now2 - 1.0))
    assert c2.sent == [] and c2.stats["silent_tools"] == 1


# ---------------- the wiring ----------------

def test_call_wiring_source_pins():
    src = ((__import__("pathlib").Path(__file__).parents[1]) / "app" / "voice.py").read_text(encoding="utf-8")
    assert "self._arm_backchannel()      # v0.205" in src          # armed with her every transcription
    assert "prog = asyncio.create_task(self._prog_watch(t0))" in src   # every tool run arms the progress sound
    assert "prog.cancel()" in src                                  # ...and it dies with the tool
    assert "pool_clips(\"bc\", self.voice, self.gender)" in src    # the pools render at call start
    assert "pool_clips(\"prog\", self.voice, self.gender)" in src


def test_stats_carry_the_new_clips():
    tenant = "t-backchannels"
    voice.STATS.append({"tenant": tenant, "call_id": "c1", "started": time.time(), "ended": time.time(),
                        "turns": 1, "latency_ms": [500], "words": [3, 5],
                        "question_endings": 0, "assistantisms": 0, "interruptions": 0, "tools": 1,
                        "silent_tools": 1, "acks": 1, "backchannels": 2, "progress": 1})
    try:
        view = voice.stats_summary(tenant)
        assert view["backchannels_played"] == 2
        assert view["progress_clips"] == 1
    finally:
        for s in list(voice.STATS):
            if s.get("tenant") == tenant:
                voice.STATS.remove(s)


def test_version():
    assert APP_VERSION == "0.261.0"
