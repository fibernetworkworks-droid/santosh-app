"""v0.289.0 SAHI KRAM - the real-voice flaws from the code review (owner: "REAL VOICE LOT OF ISSUE --- FIRST CHECK THE
CODE" -> "FIX ALL"): her late transcript joins HER turn, a tool result never talks over her, her late words never wipe
his captions, early self-cuts are counted, semantic VAD waits at most ~4 s."""
import asyncio
from pathlib import Path

from app import voice_openai

ROOT = Path(__file__).resolve().parents[2]


class Rec:
    def __init__(self):
        self.sent = []

    async def send(self, ev):
        self.sent.append(ev)


def _call():
    c = voice_openai.OpenAICall.__new__(voice_openai.OpenAICall)
    c.stats, c._her_items, c._finish_wait, c._she_speaking, c._her_t0 = {}, [], None, False, 0.0
    c._responding, c._want_response, c._asked = False, False, False
    c.finished = []

    async def finish_turn(interrupted=False):
        c.finished.append(c.user_buf)
    c.finish_turn = finish_turn
    c.user_buf = ""
    return c


def test_late_transcript_joins_her_own_turn():
    async def go():
        c = _call()
        c._her_items.append("u1")                     # committed, her words still being written out
        await c._finish_when_heard()                  # his reply is done first (the OpenAI order)
        assert c.finished == [] and c.stats["finish_waited"] == 1
        c.user_buf = "kal ka mausam batao"            # her transcript arrives
        await c._her_item_done("u1")
        return c.finished
    assert asyncio.run(go()) == ["kal ka mausam batao"]   # saved together, one turn


def test_a_transcript_that_never_comes_does_not_hold_the_turn(monkeypatch):
    monkeypatch.setattr(voice_openai, "FINISH_WAIT_S", 0.05)

    async def go():
        c = _call()
        c._her_items.append("u1")
        await c._finish_when_heard()
        await asyncio.sleep(0.15)
        return c.finished, c._her_items
    finished, items = asyncio.run(go())
    assert finished == [""] and items == []


def test_her_next_words_close_a_waiting_turn_first():
    async def go():
        c = _call()
        c._her_items.append("u1")
        await c._finish_when_heard()
        await c._finish_now()                         # speech_started while waiting
        return c.finished
    assert asyncio.run(go()) == [""]


def test_tool_result_never_talks_over_her():
    async def go():
        import time
        c, s = _call(), Rec()
        c._she_speaking, c._her_t0 = True, time.monotonic()      # she started talking just now
        await c._reply(s)
        return s.sent, c.stats
    sent, stats = asyncio.run(go())
    assert sent == [] and stats["held_for_her"] == 1          # her own turn's reply will carry it


def test_a_lost_speech_stop_never_mutes_him():
    import time

    async def go():
        c, s = _call(), Rec()
        c._she_speaking, c._her_t0 = True, time.monotonic() - 30
        await c._reply(s)
        return s.sent
    assert asyncio.run(go()) == [{"type": "response.create"}]


def test_late_words_do_not_wipe_his_captions_and_early_cuts_count():
    src = (ROOT / "server/app/voice_openai.py").read_text()
    i = src.index("    async def _heard_her(")
    body = src[i:src.index("    async def _she_cut_in(")]
    assert "await self._cap_flush()" not in body
    assert '"early_cuts"' in src and "EARLY_CUT_S" in src
    assert '"input_audio_buffer.committed"' in src and "response.create" not in body


def test_vad_waits_at_most_about_four_seconds():
    from app.config import get_settings
    get_settings.cache_clear()
    assert get_settings().voice_openai_eagerness == "medium"


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.289.0"
    assert "0.289.0+329" in (ROOT / "pubspec.yaml").read_text()
