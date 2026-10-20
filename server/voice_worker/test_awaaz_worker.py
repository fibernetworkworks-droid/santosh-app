"""Hoola Awaaz worker with the fake engine (no GPU needed). Run: cd server && python -m pytest -q voice_worker"""
from __future__ import annotations

import importlib.util
import io
import json
import struct
import sys
import time
import wave
from pathlib import Path

import pytest

np = pytest.importorskip("numpy")
HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))


@pytest.fixture()
def w(tmp_path, monkeypatch):
    monkeypatch.setenv("WORKER_KEY", "k1")
    monkeypatch.setenv("ENGINE", "fake")
    monkeypatch.setenv("VOICES_DIR", str(tmp_path / "voices"))
    spec = importlib.util.spec_from_file_location("awaaz_worker", HERE / "worker.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    from fastapi.testclient import TestClient
    with TestClient(mod.app) as c:
        yield mod, c


def wav(seconds=8.0, rate=16000, freq=180):
    t = np.arange(int(seconds * rate)) / rate
    pcm = (0.3 * np.sin(2 * np.pi * freq * t) * 32767).astype("<i2").tobytes()
    buf = io.BytesIO()
    with wave.open(buf, "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(rate)
        f.writeframes(pcm)
    return buf.getvalue()


H = {"x-worker-key": "k1"}


def add(c, vid="voice_abc123", data=None):
    return c.post("/v1/voices", headers=H, data={"voice_id": vid, "lang": "hi", "ref_text": "Main Meghana hoon"},
                  files={"file": ("ref.wav", data or wav(), "audio/wav")})


def test_key_voice_lifecycle_and_tts(w):
    mod, c = w
    assert c.get("/healthz").json()["engine"] == "fake"
    assert c.post("/v1/voices", data={"voice_id": "voice_abc123"}, files={"file": ("a.wav", wav())}).status_code == 401
    r = add(c)
    assert r.status_code == 200 and r.json()["seconds"] == 8.0
    assert c.get("/healthz").json()["voices"] == 1
    pcm = c.post("/v1/tts", headers=H, json={"voice_id": "voice_abc123", "text": "Haan, ek second"}).content
    assert len(pcm) >= 24000 * 2 * 0.2 and len(pcm) % 2 == 0
    assert c.post("/v1/tts", headers=H, json={"voice_id": "nobody_123", "text": "x"}).status_code == 404
    assert c.delete("/v1/voices/voice_abc123", headers=H).json()["deleted"] is True
    assert c.get("/healthz").json()["voices"] == 0
    assert c.post("/v1/tts", headers=H, json={"voice_id": "voice_abc123", "text": "x"}).status_code == 404


def test_bad_recordings_and_ids_are_refused(w):
    _, c = w
    assert add(c, data=wav(2.0)).status_code == 400                      # too short
    assert add(c, data=b"RIFF....not a wav").status_code == 400
    assert add(c, vid="../../etc").status_code in (400, 422)
    assert c.delete("/v1/voices/..", headers=H).status_code in (400, 404)


def test_design_makes_a_new_voice(w):
    _, c = w
    r = c.post("/v1/design", headers=H, json={"description": "young woman from Pune, warm", "text": "Namaste, main Meera hoon"})
    assert r.status_code == 200 and r.content[:4] == b"RIFF"


def test_live_stream_speaks_in_order_and_cancel_drops_old_replies(w):
    mod, c = w
    add(c)
    with c.websocket_connect("/v1/stream?voice_id=voice_abc123&lang=hi", headers=H) as ws:
        ws.send_text(json.dumps({"type": "say", "gen": 1, "text": "Kal ki meeting chaar baje hai"}))
        gens, done = [], []
        while not done:
            m = ws.receive()
            if m.get("bytes"):
                gens.append(struct.unpack(">I", m["bytes"][:4])[0])
                assert len(m["bytes"]) > 4
            elif m.get("text"):
                done.append(json.loads(m["text"]))
        assert set(gens) == {1} and done[0] == {"type": "done", "gen": 1}
        # the user interrupts reply 2: nothing of it may come out after the cancel
        from engines import fake
        fake.FakeEngine.delay_s = 0.05
        try:
            ws.send_text(json.dumps({"type": "say", "gen": 2, "text": " ".join(["bahut"] * 60)}))
            first = ws.receive()
            assert struct.unpack(">I", first["bytes"][:4])[0] == 2
            ws.send_text(json.dumps({"type": "cancel", "gen": 2}))
            ws.send_text(json.dumps({"type": "say", "gen": 3, "text": "Haan boliye"}))
            after, end = [], time.time() + 10
            while time.time() < end:
                m = ws.receive()
                if m.get("bytes"):
                    after.append(struct.unpack(">I", m["bytes"][:4])[0])
                elif m.get("text") and json.loads(m["text"]).get("gen") == 3:
                    break
            # at most one chunk of 2 was already in flight; then only reply 3
            assert after and after[-1] == 3 and after.count(2) <= 2
            assert 3 in after and all(g == 3 for g in after[after.index(3):])
        finally:
            fake.FakeEngine.delay_s = 0.0


def test_stream_needs_key_and_known_voice(w):
    _, c = w
    from starlette.websockets import WebSocketDisconnect
    with pytest.raises(WebSocketDisconnect):
        with c.websocket_connect("/v1/stream?voice_id=voice_abc123") as ws:
            ws.receive_text()
    with pytest.raises(WebSocketDisconnect):
        with c.websocket_connect("/v1/stream?voice_id=voice_none00", headers=H) as ws:
            ws.receive_text()


def test_resample_to_24k(w):
    mod, _ = w
    x = np.sin(np.linspace(0, 100, 22050)).astype(np.float32)
    assert len(mod.to_pcm16(x, 22050)) == 24000 * 2
    assert len(mod.to_pcm16(x[:24000] if len(x) >= 24000 else x, 24000)) == len(x) * 2
