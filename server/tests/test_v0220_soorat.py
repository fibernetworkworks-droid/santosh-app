"""v0.222.0 SOORAT - Wave 3 of the voice-to-voice PERFECT plan (Phase C's last remainder: prosody AT the moment).

The v0.201 note speaks once and dies; around it the scripted moments keep their fixed energy - after heavy
news a tool's ack clip can still go bright on 'mil gaya!', and when SHE MOVES (heavy to light, anger to
calm) nothing tells him to move with her. SOORAT: (1) the tone stays current for TONE_S after a note and
tints the scripted moments - the ack watch filters out the bright clips while she is low/tense (the pool's
position->line map survives failed renders), the stall nudge / result notes / reconnect re-brief carry the
tone clause; (2) a state FLIP adds the move-with-her clause and re-anchors the tone. Kill switch
voice_soorat: off = the v0.219 engine exactly."""
import asyncio
import time
from types import SimpleNamespace

from app import voice, voiceaffect


# ---------------- the tone tags themselves ----------------

def test_tag_exists_for_every_state_and_is_compact():
    assert set(voiceaffect.TAG) == {"low", "tense", "glad"}
    for tag in voiceaffect.TAG.values():
        assert len(tag) < 220
        assert "{" not in tag and "}" not in tag      # the format() contract of every prompt fragment


def test_flip_note_only_on_a_real_flip():
    f = voiceaffect.flip_note("low", "glad")
    assert f and "badli hai" in f and "chhod do" in f
    assert voiceaffect.flip_note("glad", "low")
    assert voiceaffect.flip_note("tense", "glad")
    assert voiceaffect.flip_note("low", "low") is None     # same state again: the note already said it
    assert voiceaffect.flip_note("", "glad") is None       # first note is not a transition
    assert voiceaffect.flip_note("glad", "xyz") is None    # unknown state: never
    assert voiceaffect.flip_note("xyz", "glad") is None


# ---------------- the tone surface on the call ----------------

class _TonedCall:
    """The attributes the tone surface and the scripted notes touch."""

    def __init__(self, tone="", age=0.0):
        self._tone = tone
        self._tone_at = time.monotonic() - age
        self._quiet_pending = []
        self.closed = asyncio.Event()
        self.stats = {}
        self.notes = []
        # the real tone surface, bound to this fake (the scripted-note methods call it through self)
        self._tone_now = lambda: voice.Call._tone_now(self)
        self._tone_tag = lambda: voice.Call._tone_tag(self)

    def push(self, kind, data, force=False):
        self.notes.append(str(data))

    def push_news(self, text):                       # v0.230 the news queue; tested in test_v0228
        self.push("text", text)

    async def send_audio(self, data):
        self.notes.append(data)


def _settings(**over):
    base = dict(voice_soorat=True, voice_tool_ack=True, voice_stall_watch=True, voice_stall_nudge_s=0,
                voice_prosody=True)
    base.update(over)
    return SimpleNamespace(**base)


def test_tone_now_decays_after_tone_s(monkeypatch):
    c = _TonedCall("low", age=10.0)
    monkeypatch.setattr(voice, "get_settings", lambda: _settings())
    assert voice.Call._tone_now(c) == "low"
    c._tone_at = time.monotonic() - (voiceaffect.TONE_S + 1)
    assert voice.Call._tone_now(c) == ""       # an old mood never tints a bright new topic


def test_tone_now_kill_switch(monkeypatch):
    c = _TonedCall("low")
    monkeypatch.setattr(voice, "get_settings", lambda: _settings(voice_soorat=False))
    assert voice.Call._tone_now(c) == ""
    assert voice.Call._tone_tag(c) == ""


# ---------------- the ack pool learns which lines render bright ----------------

def test_bright_ack_ix_is_the_same_rule_the_ask_speaks():
    bright = voice._bright_ack_ix()
    assert bright and len(bright) < len(voice.ACK_LINES)          # a filter needs both moods in the pool
    for i, line in enumerate(voice.ACK_LINES):
        ask = voice._ack_ask(line, "m")
        assert (i in bright) == ("bright, a small found-it lift" in ask)   # ONE source of truth
    assert 8 in bright    # "Haan, mil gaya... ek second."
    assert 0 not in bright


def test_build_acks_records_position_to_line_even_when_a_render_dies(tmp_path, monkeypatch):
    monkeypatch.setattr(voice, "_ack_file", lambda v, g, i: tmp_path / f"{v}_{g}_{i}.pcm")
    def tts(text, v, g, client=None):
        if "mil gaya" in text.lower():
            raise RuntimeError("tts down for one clip")
        return b"\x10\x04" * 400
    monkeypatch.setattr(voice, "_ack_tts", tts)
    voice._build_acks("t220:Puck:m", "Puck", "m")
    try:
        ixs = voice._ACK_IX["t220:Puck:m"]
        clips = voice._ACKS["t220:Puck:m"]
        assert len(clips) == 15 and len(ixs) == 15 and 8 not in ixs   # line 8 died: positions shifted
        assert ixs[8] == 9                                            # ...and the map followed the shift
    finally:
        with voice._ACK_LOCK:
            voice._ACKS.pop("t220:Puck:m", None)
            voice._ACK_IX.pop("t220:Puck:m", None)


# ---------------- the ack watch filters by mood ----------------

CLIPS = [bytes([i]) for i in range(16)]      # clip bytes identify their pool position


class _AckCall(_TonedCall):
    def __init__(self, tone, age=0.0):
        super().__init__(tone, age)
        self.voice, self.gender = "Puck", "m"
        self.hold = ""
        self._last_model_audio = -100.0
        self._last_voice_at = 0.0
        self._last_ack = 0.0
        self._bc_at = 0.0
        self._last_ack_i = -1
        self.ACK_AFTER_S = 0.0
        self.stats = {"silent_tools": 0, "acks": 0}
        self.sent = []

    async def send_audio(self, data):
        self.sent.append(data)


def _run_ack(c, monkeypatch):
    monkeypatch.setattr(voice, "get_settings", lambda: _settings())
    asyncio.get_event_loop_policy().new_event_loop().run_until_complete(
        voice.Call._ack_watch(c, 0.0))


def _ack_ix(ix):
    """Set the pool's position->line map for the test, restore the real one after."""
    def _clean():
        with voice._ACK_LOCK:
            voice._ACK_IX.pop("Puck:m", None)
    with voice._ACK_LOCK:
        voice._ACK_IX["Puck:m"] = list(ix)
    return _clean


def test_ack_watch_skips_bright_clips_while_she_is_heavy(monkeypatch):
    monkeypatch.setattr(voice, "ack_clips", lambda v, g: CLIPS)
    bright = voice._bright_ack_ix()
    clean = _ack_ix(range(16))
    try:
        chosen = set()
        for _ in range(30):
            c = _AckCall("low")
            _run_ack(c, monkeypatch)
            assert len(c.sent) == 1
            pos = CLIPS.index(c.sent[0])
            with voice._ACK_LOCK:
                li = voice._ACK_IX["Puck:m"][pos]
            chosen.add(li)
            assert c.stats["tone_soft_acks"] == 1
        assert chosen and not (chosen & bright)           # 30 draws, never one bright clip
    finally:
        clean()


def test_ack_watch_glad_or_neutral_keeps_the_whole_pool(monkeypatch):
    monkeypatch.setattr(voice, "ack_clips", lambda v, g: CLIPS)
    bright = voice._bright_ack_ix()
    clean = _ack_ix(range(16))
    try:
        chosen = set()
        for _ in range(60):
            c = _AckCall("glad")
            _run_ack(c, monkeypatch)
            with voice._ACK_LOCK:
                chosen.add(voice._ACK_IX["Puck:m"][CLIPS.index(c.sent[0])])
            assert "tone_soft_acks" not in c.stats
        assert chosen & bright                        # the bright clips are allowed back when she is glad
    finally:
        clean()


def test_ack_watch_all_bright_pool_still_speaks(monkeypatch):
    monkeypatch.setattr(voice, "ack_clips", lambda v, g: [CLIPS[8]])
    clean = _ack_ix([8])
    try:
        c = _AckCall("low")
        _run_ack(c, monkeypatch)
        assert c.sent == [CLIPS[8]]                   # nothing soft to pick: speak anyway, never dead air
        assert "tone_soft_acks" not in c.stats
    finally:
        clean()


def test_ack_watch_kill_switch_never_filters(monkeypatch):
    monkeypatch.setattr(voice, "ack_clips", lambda v, g: CLIPS)
    clean = _ack_ix(range(16))
    try:
        c = _AckCall("low")
        monkeypatch.setattr(voice, "get_settings", lambda: _settings(voice_soorat=False))
        asyncio.get_event_loop_policy().new_event_loop().run_until_complete(voice.Call._ack_watch(c, 0.0))
        assert len(c.sent) == 1 and "tone_soft_acks" not in c.stats
    finally:
        clean()


# ---------------- the feeling engine follows her transitions ----------------

class _AffectCall:
    def __init__(self, text, last=""):
        self.vid = None
        self.user_buf = text
        self._affect_last = last
        self._affect_at = 0.0
        self.stats = {}
        self.notes = []
        self.meter = None
        self._pros_base = {}

    async def _tell_quietly(self, note, live=False):
        self.notes.append(note)


def _run_affect(c, monkeypatch, **over):
    monkeypatch.setattr(voice, "get_settings", lambda: _settings(**over))
    asyncio.get_event_loop_policy().new_event_loop().run_until_complete(voice.Call._affect_watch(c))


GLAD = "haan suno, order double ho gaya is mahine!"
LOW = "mummy hospital mein hai, bahut pareshan hoon"


def test_flip_names_the_move_and_reanchors_the_tone(monkeypatch):
    c = _AffectCall(GLAD, last="low")
    _run_affect(c, monkeypatch)
    assert len(c.notes) == 1
    assert "garmi" in c.notes[0] and "badli hai" in c.notes[0]   # the glad note + the move-with-her clause
    assert c.stats["affect_transitions"] == 1
    assert c._tone == "glad" and c._tone_at > 0


def test_first_note_is_not_a_transition(monkeypatch):
    c = _AffectCall(GLAD)
    _run_affect(c, monkeypatch)
    assert len(c.notes) == 1 and "badli hai" not in c.notes[0]
    assert "affect_transitions" not in c.stats and c._tone == "glad"


def test_kill_switch_leaves_the_v219_engine(monkeypatch):
    c = _AffectCall(GLAD, last="low")
    _run_affect(c, monkeypatch, voice_soorat=False)
    assert len(c.notes) == 1 and "badli hai" not in c.notes[0]
    assert "affect_transitions" not in c.stats
    assert c.__dict__.get("_tone") is None            # never anchored: the scripted moments stay untinted


# ---------------- the scripted moments carry the tone ----------------

def test_note_result_rides_the_tone(monkeypatch):
    c = _TonedCall("low")
    monkeypatch.setattr(voice, "get_settings", lambda: _settings())
    voice.Call._note_result(c, "search_web", {"result": "mil gaya"})
    assert "ho chuka" in c.notes[0] and "naram" in c.notes[0]
    c2 = _TonedCall("low", age=voiceaffect.TONE_S + 5)
    voice.Call._note_result(c2, "search_web", {"result": "mil gaya"})
    assert "naram" not in c2.notes[0]


def test_reseed_tells_the_fresh_session_her_tone(monkeypatch):
    c = _TonedCall("tense")
    c.recent = [("usne kaha", "maine kaha")]
    monkeypatch.setattr(voice, "get_settings", lambda: _settings())
    seed = voice.Call._reseed(c, False)
    assert "HOOLA KI YAAD" in seed and "shaant" in seed
    c2 = _TonedCall("tense", age=voiceaffect.TONE_S + 5)
    c2.recent = [("usne kaha", "maine kaha")]
    assert "shaant" not in voice.Call._reseed(c2, False)


def test_stall_nudge_rides_the_tone(monkeypatch):
    c = _TonedCall("low")
    c.hold = ""
    c.user_buf = "sun rahe hain?"
    c._turn_audio = True
    c._tool_runs = 0
    c._last_model_audio = c._last_voice_at = c._last_user_text_at = 0.0
    c._stall_nudged = False
    c._stall_at = 0.0
    c._stall_reconnects = 0
    c.stats = {"stall_nudges": 0, "stall_reconnects": 0}

    class _S:
        async def close(self):
            c.closed.set()

    async def go():
        monkeypatch.setattr(voice, "_STALL_POLL_S", 0.01)
        monkeypatch.setattr(voice, "get_settings", lambda: _settings())
        t = asyncio.create_task(voice.Call._stall_watch(c, _S()))
        for _ in range(500):
            await asyncio.sleep(0.01)
            if c.stats.get("stall_nudges"):
                break
        c.closed.set()
        await asyncio.gather(t, return_exceptions=True)

    asyncio.get_event_loop_policy().new_event_loop().run_until_complete(go())
    assert c.stats.get("stall_nudges") == 1
    assert "turant bolo" in c.notes[0] and "naram" in c.notes[0]


def test_late_result_rides_the_tone(monkeypatch):
    from app.agent import santosh as santosh_mod
    monkeypatch.setitem(santosh_mod.LAST_OUTCOME, "c220", {"outcome": "done", "left": ""})
    monkeypatch.setattr(voice, "get_settings", lambda: _settings())
    c = _TonedCall("low")

    async def go():
        job = asyncio.create_task(asyncio.sleep(0))
        await job
        voice.Call._late_result(c, job)

    asyncio.get_event_loop_policy().new_event_loop().run_until_complete(go())
    assert "ho gaya" in c.notes[0] and "naram" in c.notes[0]


# ---------------- the scorecard counts the energy ----------------

def test_scorecard_counts_soorat():
    voice.STATS.append({"tenant": "t220", "call_id": "t220c", "ended": 1.0, "turns": 0, "acks": 2, "latency_ms": [],
                        "words": [], "question_endings": 0, "assistantisms": 0, "interruptions": 0,
                        "tools": 0, "silent_tools": 0, "affect_notes": 1, "affect_transitions": 1,
                        "tone_soft_acks": 2})
    try:
        s = voice.stats_summary("t220")
        assert s["affect_transitions"] == 1 and s["tone_soft_acks"] == 2
    finally:
        voice.STATS.pop()


# ---------------- version ----------------

def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.270.0"
