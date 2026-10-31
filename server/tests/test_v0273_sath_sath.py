"""v0.273.0 SATH SATH - captions appear as he SAYS them (owner: "BUT IN APP IT SHOWS TEXT FIRST" -> "SYNC CAPTIONS").
The model streams text and audio together; text showed at once while the audio played from her phone's queue."""
import asyncio
import json
import time
from pathlib import Path

from app import voice

ROOT = Path(__file__).resolve().parents[2]


class Phone:
    def __init__(self):
        self.got = []   # (t, kind, payload)

    async def send_bytes(self, b):
        self.got.append((time.monotonic(), "audio", len(b)))

    async def send_text(self, t):
        self.got.append((time.monotonic(), "json", json.loads(t)))


def _call():
    c = voice.Call.__new__(voice.Call)
    c.ws, c.closed, c._send_lock, c._missed = Phone(), asyncio.Event(), asyncio.Lock(), []
    return c


def _json(c):
    return [(t, p) for t, k, p in c.ws.got if k == "json"]


def test_send_audio_moves_the_playback_clock():
    async def go():
        c = _call()
        t0 = time.monotonic()
        await c.send_audio(b"\x00\x00" * 24000)          # one second of his voice
        await c.send_audio(b"\x00\x00" * 12000)          # half a second more
        return c._play_until - t0
    assert 1.45 < asyncio.run(go()) < 1.6


def test_caption_goes_at_once_when_nothing_is_queued():
    async def go():
        c = _call()
        await c._caption({"type": "santosh_text", "text": "Haan"})
        return _json(c)
    assert asyncio.run(go())[0][1] == {"type": "santosh_text", "text": "Haan"}


def test_caption_waits_for_his_voice_and_keeps_order():
    async def go():
        c = _call()
        t0 = time.monotonic()
        await c.send_audio(b"\x00\x00" * 14400)          # 0.6 s of voice queued on her phone
        await c._caption({"type": "santosh_text", "text": "Kal chaar baje"})
        await c._caption({"type": "santosh_text", "text": "Kal chaar baje free ho"})
        await c._caption({"type": "turn_done", "latency_ms": 700})
        assert not _json(c)                               # nothing shown before he says it
        await asyncio.sleep(0.8)
        return t0, _json(c)
    t0, got = asyncio.run(go())
    kinds = [p["type"] for _, p in got]
    assert kinds == ["santosh_text", "santosh_text", "turn_done"]          # never out of order
    assert got[0][0] - t0 >= 0.6 - voice.Call.CAPTION_EARLY_S - 0.05       # when his voice reaches those words


def test_her_new_words_drop_stale_captions_but_not_turn_done():
    async def go():
        c = _call()
        await c.send_audio(b"\x00\x00" * 48000)          # 2 s queued
        await c._caption({"type": "santosh_text", "text": "purana jawab"})
        await c._caption({"type": "turn_done"})
        await c._cap_flush()                              # she starts talking / cuts him off
        await asyncio.sleep(0.05)
        return _json(c)
    got = [p for _, p in asyncio.run(go())]
    assert got == [{"type": "turn_done"}]                 # the old caption never overwrites her new words


def test_both_engines_pace_captions():
    v = (ROOT / "server/app/voice.py").read_text()
    o = (ROOT / "server/app/voice_openai.py").read_text()
    assert 'await self._caption({"type": "santosh_text"' in v and "await self._caption(done)" in v
    assert 'await self._caption({"type": "santosh_text"' in o
    assert v.count("await self._cap_flush()") >= 2 and o.count("await self._cap_flush()") >= 1   # v0.285 OpenAI: only a real cut-in flushes
    assert "self._play_until = max(time.monotonic(), self._play_until) + dur" not in o   # one clock, in send_audio


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.337.0"
    assert "0.337.0+377" in (ROOT / "pubspec.yaml").read_text()
