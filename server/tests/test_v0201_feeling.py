"""v0.201.0 AWAAZ-2 (the feeling engine, Phase C's core, pulled forward): the owner's 8-point ear test on
v0.199.0 said pauses/breathing/soft-news/acks FAIL - the static delivery block teaches words, not sound.
gemini-3.8-live takes mid-call quiet notes (v0.150.1), so now her own words pick ONE delivery note at the
moment she is speaking, the prompt ends with a delivery reminder (recency), the list-pacing and laugh rules
got concrete, the kaamwatch rider grew a breath, and the ack clips carry a generation tag so a changed ask
regenerates instead of playing the old flat renders forever."""
import asyncio
import time

from app import voice, voiceaffect


# ---------------- the feeling engine: her words -> one state ----------------

def test_decide_low_heavy_news():
    for line in ("aaj bahut bura din tha, pet bhar gaya kaam se", "wo hospital mein hai, tabiyat theek nahi",
                 "main pareshan hoon us paise ko lekar", "माँ बीमार है, हॉस्पिटल में है", "feeling really upset today"):
        st, hit = voiceaffect.decide(line)
        assert st == "low", (line, st, hit)
        assert hit, line


def test_decide_glad_good_news():
    for line in ("suno, order double ho gaya is mahine!", "mujhe promotion mil gaya", "badhai ho mujhe bhi do",
                 "शादी पक्की हो गई, बधाई दो"):
        st, hit = voiceaffect.decide(line)
        assert st == "glad", (line, st, hit)


def test_decide_tense():
    for line in ("wo mujhse gussa ho gaya hai, ab kya karoon", "ye toh pura jhooth tha uska", "बहुत गुस्सा आ रहा है"):
        st, _ = voiceaffect.decide(line)
        assert st == "tense", line


def test_decide_stays_silent_on_neutral_and_short():
    for line in ("kal 4 baje meeting hai", "chai le aana", "reminder laga do", "ok", ""):
        assert voiceaffect.decide(line) == ("", ""), line


def test_low_beats_glad_and_tense():
    # heavy news wins: "shaadi" happiness inside a sad line must not get a celebration voice
    st, _ = voiceaffect.decide("shaadi mein sab theek tha, par ghar wapas aake bahut udaas ho gayi")
    assert st == "low"


def test_notes_are_spoken_shaped():
    for st, note in voiceaffect.NOTE.items():
        assert note and "{" not in note and "}" not in note          # the format() contract
        assert len(note) < 400                                       # a note, not a lecture
    assert "pause" in voiceaffect.NOTE["low"] and "naram" in voiceaffect.NOTE["low"]
    assert "garmi" in voiceaffect.NOTE["glad"]
    assert "shaant" in voiceaffect.NOTE["tense"]


# ---------------- the call wiring: one note, debounced ----------------

class _FakeCall:
    """Just the attributes _affect_watch touches."""

    def __init__(self, text):
        self.vid = None
        self.user_buf = text
        self._affect_last = ""
        self._affect_at = 0.0
        self.stats = {}
        self.notes = []

    async def _tell_quietly(self, note, live=False):
        self.notes.append(note)


def test_affect_watch_sends_one_note(monkeypatch):
    c = _FakeCall("mummy hospital mein hai, bahut pareshan hoon")
    asyncio.get_event_loop_policy().new_event_loop().run_until_complete(voice.Call._affect_watch(c))
    assert len(c.notes) == 1 and "naram" in c.notes[0]
    assert c.stats["affect_notes"] == 1 and c._affect_last == "low"


def test_affect_watch_debounces_same_state_and_bursts(monkeypatch):
    c = _FakeCall("mummy hospital mein hai")
    asyncio.get_event_loop_policy().new_event_loop().run_until_complete(voice.Call._affect_watch(c))
    c2 = _FakeCall("haan wo hi baat")          # same state, 0 s later: the 20 s burst guard holds it
    c2._affect_last, c2._affect_at = c._affect_last, c._affect_at
    asyncio.get_event_loop_policy().new_event_loop().run_until_complete(voice.Call._affect_watch(c2))
    assert c2.notes == []


def test_affect_watch_new_state_fires(monkeypatch):
    c = _FakeCall("mummy hospital mein hai")
    asyncio.get_event_loop_policy().new_event_loop().run_until_complete(voice.Call._affect_watch(c))
    c3 = _FakeCall("par suno, order double ho gaya!")
    c3._affect_last, c3._affect_at = c._affect_last, c._affect_at - 40   # 40 s gap, changed state
    asyncio.get_event_loop_policy().new_event_loop().run_until_complete(voice.Call._affect_watch(c3))
    assert len(c3.notes) == 1 and "garmi" in c3.notes[0]


def test_affect_watch_skips_other_mouths(monkeypatch):
    c = _FakeCall("mummy hospital mein hai")
    c.vid = type("V", (), {"current": {"relation": "maa"}})()          # not her voice: never a note
    asyncio.get_event_loop_policy().new_event_loop().run_until_complete(voice.Call._affect_watch(c))
    assert c.notes == []


# ---------------- the prompt: list pacing, laugh, the end reminder ----------------

def test_persona_teaches_list_pacing_and_breath_laugh():
    assert "one item per short sentence and a real breath between items" in voice.PERSONA
    assert "Never one long run-on line" in voice.PERSONA
    assert "she laughs herself" in voice.PERSONA and 'never the word "haha"' in voice.PERSONA
    # the v0.199 pins all survive the edits
    for pin in ("Pauses are punctuation", "One idea per breath", "newsreader", "robot rhythm",
                "laugh, short and real", "softer and lower", "no forced cheer", "own it in one plain line",
                "never an imitation"):
        assert pin in voice.PERSONA, pin


def test_delivery_end_rides_last(env):
    from app import voicelang
    ls = voicelang.LangState("hi")
    from app.config import get_settings
    cfg = voice.live_config("Puck", "hi", "(nothing saved yet)", None, langst=ls)
    text = cfg.system_instruction.parts[0].text
    assert text.rstrip().endswith("garmi.)")          # the VERY last line of the whole system prompt
    assert "list kabhi ek saans mein nahi" in text and voice.DELIVERY_END in text


# ---------------- ack clips: a changed ask regenerates ----------------

def test_ack_clip_filename_carries_generation():
    f = voice._ack_file("Puck", "m", 3)
    assert f.name == "Puck_m_3_a3.pcm" and f.parent == voice.ACK_DIR
    assert voice._ACK_GEN == "a3"   # v0.250 a2 -> a3: every clip re-rendered through the read-aloud check


# ---------------- the kaamwatch rider grew a breath ----------------

def test_kaamwatch_rider_still_pins_and_grew():
    import inspect
    from app import kaamwatch
    src = inspect.getsource(kaamwatch._voice)
    for pin in ("don't read symbols", "short sentences", "energy that matches the news",
                "a small smile in the voice"):                 # the v0.199 pins stay true
        assert pin in src, pin
    assert "two breaths, not one run-on line" in src           # the v0.201 addition


# ---------------- version ----------------

def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.293.0"
