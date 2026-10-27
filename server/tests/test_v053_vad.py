"""v0.53 Silero VAD: server stream, voice-id only takes real speech, gate stats + config reach the call."""
import math
import struct

import pytest


def _pcm(samples):
    return b"".join(struct.pack("<h", max(-32767, min(32767, int(x * 32767)))) for x in samples)


def test_silero_on_server_tells_noise_from_silence(env):
    from app import vad
    if not vad.available():
        pytest.skip("onnxruntime not installed")
    import random
    random.seed(1)
    s = vad.Stream()
    noise = _pcm([random.gauss(0, 0.05) for _ in range(16000)])
    probs = [s.prob(noise[i:i + 1280]) for i in range(0, len(noise), 1280)]
    assert max(p for p in probs if p is not None) < 0.3
    assert vad.Stream().prob(b"\x00\x00" * 100) is None          # less than one 512-sample window


def test_voiceid_listener_skips_loud_non_voice(env, monkeypatch):
    from app import vad
    from app.voiceid import live
    if not vad.available():
        pytest.skip("onnxruntime not installed")
    monkeypatch.setattr(env["settings"], "voiceid_vad", True)
    l = live.Listener([{"name": "Meghana", "relation": "self"}], "on")
    buzz = _pcm([0.3 * (1 if math.sin(2 * math.pi * 120 * i / 16000) > 0 else -1) for i in range(1280)])
    for _ in range(80):
        l.add(buzz)
    assert l.not_speech > 50 and l.speech_s < 0.5


def test_gate_stats_and_vad_config(env):
    from app import voice
    cfg = voice.vad_config()
    assert cfg["need"] == 0.5 and cfg["idle_gate"] is True
    voice.STATS.clear()
    voice.STATS.append({"tenant": "default", "call_id": "x", "ended": 1, "turns": 1, "latency_ms": [500], "words": [8],
                        "question_endings": 0, "assistantisms": 0, "interruptions": 0, "tools": 0, "silent_tools": 0,
                        "acks": 0, "false_stops": 0,
                        "gate": {"chunks": 1000, "vad_blocked": 12, "idle_muted": 400, "opens": 3, "vad": 1}})
    s = voice.stats_summary("default")
    assert s["vad_calls"] == 1 and s["vad_blocked_per_call"] == 12 and s["noise_muted_pct"] == 40.0
