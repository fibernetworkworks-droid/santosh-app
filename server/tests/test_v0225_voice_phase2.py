"""v0.225 VOICE PHASE 2 - long calls that never break (owner: 'MERGE TO MAIN AND START PHASE 2').

1. GoAway (Gemini moves connections ~every 10 min): no more instant hard cut mid-sentence. Nobody talking = move at
   once; he is speaking = his sentence finishes first (turn_complete), at the latest just before Gemini's deadline.
   The next connection's brief is built in the background the moment the warning arrives, and a resumed session
   keeps the MCP tool list (no slow snapshot on every move).
2. Her last 2 s of mic audio survive a Gemini reconnect (only the older backlog is dropped).
3. Context compression starts early (trigger ~60k, window back to ~35k): long calls stay fast.
4. Every end that is not HER hang-up (server restart, connection error, stall close) leaves the continuation note,
   so the next call carries on the work. Server restarts save it before the phone is closed.
5. His voice the phone missed while its line was down (grace window) is replayed when it comes back (<= 10 s,
   only if fresh).
"""
import asyncio
import inspect
import time

from google.genai import types

from app import voice


def _call(env):
    return voice.Call(None, "conv-p2", "Puck", "hi-IN", env["settings"].tenant_id)


def _audio(n=100):
    return types.LiveServerMessage(server_content=types.LiveServerContent(
        model_turn=types.Content(parts=[types.Part(inline_data=types.Blob(data=b"\x01\x00" * n,
                                                                         mime_type="audio/pcm;rate=24000"))])))


def _goaway(left=None):
    return types.LiveServerMessage(go_away=types.LiveServerGoAway(time_left=left))


def _done():
    return types.LiveServerMessage(server_content=types.LiveServerContent(turn_complete=True))


class _Sess:
    def __init__(self, msgs, hang=False):
        self.msgs, self.hang, self.closed = list(msgs), hang, False

    async def receive(self):
        for m in self.msgs:
            yield m
        while self.hang and not self.closed:
            await asyncio.sleep(0.02)
        if self.closed:
            raise RuntimeError("connection closed")

    async def close(self):
        self.closed = True

    async def send_realtime_input(self, **_):
        pass


def _no_prebuild(c):
    async def nothing():
        c._prebuilt = (time.monotonic(), "ctx", [])
    c._prebuild = nothing


def test_seconds_parsing():
    assert voice._seconds("9.5s") == 9.5 and voice._seconds("1s") == 1.0 and voice._seconds(3) == 3.0
    assert voice._seconds(None) is None and voice._seconds("soon") is None


def test_goaway_when_idle_moves_at_once_and_prebuilds(env):
    async def go():
        c = _call(env)
        _no_prebuild(c)
        s = _Sess([_goaway("9s"), _audio()], hang=True)
        r = await asyncio.wait_for(c.downlink(s), 2)
        await asyncio.sleep(0.05)
        return c, r
    c, r = asyncio.run(go())
    assert r == "reconnect" and c.stats["goaway"] == 1
    assert c._prebuilt is not None                     # the next brief is ready before the reconnect
    assert c._missed == []                             # nothing after the warning was played


def test_goaway_mid_sentence_lets_him_finish(env):
    async def go():
        c = _call(env)
        _no_prebuild(c)
        c._session = s = _Sess([_audio(), _goaway("9s"), _audio(), _audio(), _done(), _audio()], hang=True)
        r = await asyncio.wait_for(c.downlink(s), 2)
        return c, r
    c, r = asyncio.run(go())
    assert r == "reconnect"
    assert len(c._missed) == 3                         # the rest of his sentence was delivered, the next turn wasn't
    assert c.stats["goaway_graceful"] == 1 and not c.stats.get("goaway_forced")


def test_goaway_deadline_forces_the_move(env):
    async def go():
        c = _call(env)
        _no_prebuild(c)
        c._session = s = _Sess([_audio(), _goaway("2s")], hang=True)      # he keeps "talking", no turn_complete
        t0 = time.monotonic()
        r = await asyncio.wait_for(c.downlink(s), 3)
        return c, r, time.monotonic() - t0, s
    c, r, took, s = asyncio.run(go())
    assert r == "reconnect" and s.closed and c.stats["goaway_forced"] == 1
    assert took < 2.0                                  # moved just before Gemini's own cut, never after it


def test_reconnect_keeps_her_last_two_seconds(env):
    async def go():
        c = _call(env)
        chunk = b"\x00\x01" * 640                      # 40 ms of 16 kHz mic audio
        for _ in range(100):                           # 4 s waited through the reconnect
            c.push("audio", chunk)
        c.push("text", "note")
        c._drop_stale_audio(keep_recent=True)
        q = list(c.audio._queue)
        return q
    q = asyncio.run(go())
    audio = [x for x in q if x[0] == "audio"]
    assert sum(len(x[1]) for x in audio) <= voice.Call.GAP_KEEP_BYTES and len(audio) == 50
    assert any(x[0] == "text" for x in q)              # notes are never dropped


def test_attach_still_drops_old_mic_audio(env):
    async def go():
        c = _call(env)
        c.push("audio", b"\x00" * 1280)
        c._drop_stale_audio()
        return list(c.audio._queue)
    assert asyncio.run(go()) == []


class _WS:
    def __init__(self):
        self.bytes, self.texts = [], []

    async def send_bytes(self, b):
        self.bytes.append(b)

    async def send_text(self, t):
        self.texts.append(t)

    async def receive(self):
        await asyncio.sleep(3600)

    async def close(self, code=1000):
        pass


def test_missed_voice_is_replayed_when_the_phone_comes_back(env):
    async def go():
        c = _call(env)
        await c.send_audio(b"\x01" * 4800)
        await c.send_audio(b"\x02" * 4800)
        ws = _WS()
        t = await c.attach(ws)
        t.cancel()
        return c, ws
    c, ws = asyncio.run(go())
    assert ws.bytes == [b"\x01" * 4800, b"\x02" * 4800] and c._missed == []
    assert c.stats["missed_replayed_s"] > 0


def test_stale_missed_voice_is_not_replayed(env):
    async def go():
        c = _call(env)
        await c.send_audio(b"\x01" * 4800)
        c._missed_at -= 60
        ws = _WS()
        t = await c.attach(ws)
        t.cancel()
        return ws
    assert asyncio.run(go()).bytes == []


def test_missed_buffer_is_capped(env):
    async def go():
        c = _call(env)
        for _ in range(40):
            await c.send_audio(b"\x00" * 24000)        # 0.5 s each = 20 s
        return c
    c = asyncio.run(go())
    assert sum(len(b) for b in c._missed) <= voice.Call.MISSED_MAX


def test_compression_starts_early(env):
    cfg = voice.live_config("Puck", "hi-IN", "", None)
    cw = cfg.context_window_compression
    assert cw.trigger_tokens == 60000 and cw.sliding_window.target_tokens == 35000


def test_resumed_session_keeps_mcp_tools(env):
    async def go():
        c = _call(env)
        c.handle, c._last_mcp_defs = "h1", [{"name": "mcp_x__y"}]

        async def boom():
            raise AssertionError("MCP snapshot re-run on a resumed session")
        c._load_mcp = boom
        return await c._build_context(False)
    ctx, defs = asyncio.run(go())
    assert defs == [{"name": "mcp_x__y"}] and isinstance(ctx, str)


def test_drop_note_once_and_on_every_non_hangup_end(env):
    from app import yaad
    c = _call(env)
    c.recent.append(("GST return ka draft banao", "ji, bana raha hoon"))
    c._save_drop_note()
    c._save_drop_note()                                # grace timer + shutdown + run() end: one note
    assert "GST return" in yaad.take_call_drop(c.conv, 60)
    assert yaad.take_call_drop(c.conv, 60) == ""
    src = (inspect.getsource(voice.Call.run) + inspect.getsource(voice.Call._wrap_up))
    assert "if not self._hung_up:" in src and "self._save_drop_note" in src
    assert "self._hung_up = True" in inspect.getsource(voice.Call.phone_reader)


def test_server_restart_saves_the_continuation_note(env):
    from app import yaad

    async def go():
        c = _call(env)
        c.recent.append(("Riya ka blouse order likh do", "haan likh raha hoon"))
        voice.CALLS[c.call_id] = c
        stop = asyncio.Event()
        voice.SHUTDOWN.set()
        try:
            await voice.shutdown_watchdog(stop)
        finally:
            voice.SHUTDOWN.clear()
            voice.CALLS.pop(c.call_id, None)
        return c
    c = asyncio.run(go())
    assert "blouse" in yaad.take_call_drop(c.conv, 60)


def test_version():
    from app import main
    assert main.APP_VERSION == "0.313.0"
