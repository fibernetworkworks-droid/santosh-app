"""v0.241.0 VOICE PHASE 5 - the plan's leftovers: the slowest 1% (p99), dead air, talk-over and repeats, the once-a-day
slow-tail alert, the ear test compared with the previous version, the stall watchdog ignoring noise, the clips matched
to his live loudness and no silently swallowed TTS fallback."""
import asyncio
import time
from array import array
from pathlib import Path

import pytest

from app import callquality as cq
from app import voice

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture()
def qdir(tmp_path, monkeypatch):
    monkeypatch.setattr(cq, "DIR", tmp_path / "voice_calls")
    monkeypatch.setattr(cq, "EAR_DIR", tmp_path / "voice_eartest")
    monkeypatch.setattr(cq, "_ratings", lambda tenant: {})
    return tmp_path


def _stats(cid, tenant="t1", lat=(800, 900), end="hung_up", **kw):
    now = time.time()
    s = {"tenant": tenant, "call_id": cid, "started": now - 120, "ended": now, "turns": 4, "latency_ms": list(lat),
         "words": [5, 7], "tools": 2, "end": end}
    s.update(kw)
    return s


def test_p99_dead_air_talk_over_repeats_rolled_up(qdir, monkeypatch):
    monkeypatch.setattr(cq, "maybe_alert", lambda tenant: False)
    cq.record(_stats("c1", lat=[800] * 49 + [6000], talk_over=3, repeats=2, turns=10))
    q = cq.quality("t1")
    o = q["overall"]
    assert o["reply_start_ms_p99"] == 6000 and o["reply_start_ms_p90"] == 800
    assert o["dead_air_s"] == 4.8                       # only the 6 s turn waited past 1.2 s
    assert o["talk_over_per_100"] == 30.0 and o["repeats_per_100"] == 20.0
    assert q["targets"]["reply_start_ms_p99"] == cq.P99_ALERT_MS
    assert "1%" in q["say"]
    g = cq.grade(cq.load("t1")[0])
    assert any("bolte hue" in p for p in g["problems"]) and any("dobara boli" in p for p in g["problems"])


def test_alert_once_a_day(qdir, monkeypatch):
    sent = []
    import app.events as ev
    import app.net.service as ns
    monkeypatch.setattr(ns, "home_conv", lambda tenant: "conv-1")
    monkeypatch.setattr(ev.bus, "publish", lambda conv, kind, payload, **k: sent.append((conv, kind, payload)))
    for i in range(4):
        cq.record(_stats(f"ok{i}", lat=[700] * 10))
    assert not sent
    cq.record(_stats("slow", lat=[700] * 20 + [5000, 5200, 5500]))   # 5 calls, p99 over 4 s
    assert len(sent) == 1 and sent[0][1] == "voice_alert" and "1%" in sent[0][2]["text"]
    cq.record(_stats("slow2", lat=[5000] * 5))
    assert len(sent) == 1                               # once a day, never more
    a = cq.alert_state("t1")
    assert a["on"] and a["last_sent"]
    assert cq.quality("t1")["alert"]["on"]


def test_alert_for_broken_calls(qdir):
    for i in range(3):
        cq.record(_stats(f"b{i}", end="stall"))
    a = cq.alert_state("t1")
    assert a["on"] and any("tooti" in w for w in a["why"])
    assert not cq.alert_state("t2")["on"]


def test_alert_push_kind_registered():
    from app import push
    assert "voice_alert" in push.PUSH_KINDS


def test_eartest_compare_before_after(qdir):
    # made-up versions (9.x) so a version bump never rewrites them
    cq.eartest_mark("t1", "hello_speed", "fail", version="9.2.0")
    cq.eartest_mark("t1", "interrupt", "pass", version="9.2.0")
    cq.eartest_mark("t1", "list_pace", "pass", version="9.2.0")
    cq.eartest_mark("t1", "hello_speed", "pass", version="9.4.0")
    cq.eartest_mark("t1", "interrupt", "fail", version="9.4.0")
    cq.eartest_mark("t1", "list_pace", "pass", version="9.4.0")
    cq.eartest_mark("t1", "headset", "pass", version="9.4.0")
    c = cq.eartest("t1", "9.4.0")["compare"]
    assert c["against"] == "9.2.0"
    assert c["better"] == ["hello_speed"] and c["worse"] == ["interrupt"] and c["same"] == 1
    assert c["rows"]["headset"] == "new"
    assert cq.eartest("t1", "9.2.0")["compare"]["against"] is None   # nothing older
    cq.eartest_mark("t1", "hello_speed", "pass", version="9.10.0")
    assert cq.eartest_compare("t1", "9.10.0")["against"] == "9.4.0"   # newest older version, numeric order (9.10 > 9.4)


def test_real_words_and_repeats():
    assert not voice.real_words("<noise>") and not voice.real_words(" . ") and not voice.real_words("hmm")
    assert voice.real_words("mausam batao") and voice.real_words("haan haan") and voice.real_words("कल") and voice.real_words("है?")
    said = [voice._wordset("Kal Pune mein baarish hogi, chhata le jaana zaroor")]
    assert voice.is_repeat("Kal Pune mein baarish hogi, chhata zaroor le jaana", said)
    assert not voice.is_repeat("Aaj dhoop rahegi, garmi bahut hai bahar", said)
    assert not voice.is_repeat("haan theek", said)   # short lines never count


def _pcm(amp, n=4800):
    return array("h", [amp if i % 2 else -amp for i in range(n)]).tobytes()


def test_clip_level_matched_and_clamped():
    loud = _pcm(8000)
    out = array("h")
    out.frombytes(voice._level(loud, 4000))
    assert abs(max(out) - 4000) < 50                    # halved to his level
    out = array("h")
    out.frombytes(voice._level(_pcm(1000), 9000))
    assert max(out) == 2000                             # never more than twice as loud
    assert voice._level(loud, 8100) is loud             # close enough: untouched
    assert voice._level(loud, 0) is loud


class _C:
    """The bits of Call the Phase 5 helpers use."""
    _hear_him = voice.Call._hear_him
    _clip = voice.Call._clip
    _mark_audio = voice.Call._mark_audio

    def __init__(self):
        self.stats = {"latency_ms": []}
        self._his_rms, self._his_n = 0.0, 0
        self._bc_task = None
        self._stall_nudged, self._stall_reconnects = False, 0
        self._safe_worked, self._safe = True, 0
        self._turn_audio = False
        self._turn_end_at = 0.0
        self._last_voice_at = 0.0
        self._last_model_audio = 0.0
        self._tool_runs = 0
        self.user_buf = ""


def test_clips_follow_his_live_loudness():
    c = _C()
    clip = _pcm(8000)
    assert c._clip(clip) is clip                         # nothing of his voice heard yet
    for _ in range(40):
        c._hear_him(_pcm(5000))
    assert 4500 < c._his_rms < 5500
    out = array("h")
    out.frombytes(c._clip(clip))
    assert 4500 < max(out) < 5500 and c.stats["level_matched"] == 1
    for _ in range(8):
        c._hear_him(_pcm(10))                            # silence between words never drags the level down
    assert c._his_rms > 4500


def test_talk_over_counted_only_when_she_was_still_talking():
    c = _C()
    c._turn_end_at = 1.0
    c.user_buf = "aur phir maine kaha"
    c._last_voice_at = time.monotonic()                  # her mic was loud just now
    c._mark_audio()
    assert c.stats.get("talk_over") == 1
    c2 = _C()
    c2._turn_end_at = 1.0
    c2.user_buf = "mausam batao"
    c2._last_voice_at = time.monotonic() - 0.7           # she finished, normal pause, then he spoke
    c2._mark_audio()
    assert not c2.stats.get("talk_over") and c2.stats["latency_ms"]


def test_stall_watch_ignores_noise(monkeypatch):
    monkeypatch.setattr(voice, "_STALL_POLL_S", 0.01)

    class S:
        voice_stall_watch = True
        voice_stall_nudge_s = 0.0

    monkeypatch.setattr(voice, "get_settings", lambda: S())
    c = _C()
    c.closed = asyncio.Event()
    c.hold = ""
    c.user_buf = "<noise>"
    c._last_user_text_at = 0.0
    c.stats.update({"stall_nudges": 0, "stall_reconnects": 0})
    pushed = []
    c.push = lambda kind, data: pushed.append(data)

    async def go():
        t = asyncio.create_task(voice.Call._stall_watch(c, None))
        await asyncio.sleep(0.08)
        c.closed.set()
        await t
    asyncio.run(go())
    assert not pushed and c.stats["stall_nudges"] == 0 and c.stats["stall_noise_skips"] == 1


def test_wiring_in_voice_and_api(env, qdir, monkeypatch):
    src = (ROOT / "server/app/voice.py").read_text()
    assert "self._hear_him(blob.data)" in src and src.count("send_audio(matched_clip(self, clips[i]))") == 3
    assert "TTS_FALLBACKS[\"count\"] += 1" in src and "self._noise_skipped = False" in src
    monkeypatch.setenv("API_KEY", "owner-key-phase5")
    from app.config import get_settings
    get_settings.cache_clear()
    from fastapi.testclient import TestClient
    from app.main import app
    H = {"Authorization": "Bearer owner-key-phase5"}
    with TestClient(app) as c:
        st = c.get("/api/voice/stats", headers=H).json()
        assert "alert" in st["quality"] and "ack_tts_fallbacks" in st
        q = c.get("/api/voice/quality", headers=H).json()
        assert "reply_start_ms_p99" in q["overall"] and "alert" in q
        assert "compare" in c.get("/api/voice/eartest", headers=H).json()


def test_phone_screen_wired():
    dart = (ROOT / "lib/ui/call_quality_screen.dart").read_text()
    assert "reply_start_ms_p99" in dart and "dead_air_s" in dart and "talk_over_per_100" in dart
    assert "pehle se behtar" in dart and "ke muqable" in dart and "_alert(alert)" in dart


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.324.0"
    assert "0.324.0+364" in (ROOT / "pubspec.yaml").read_text()
