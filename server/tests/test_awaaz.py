"""Hoola Awaaz: the owner's own voice (consent recording) and designed voices, made and spoken by our worker.
A real worker process (fake engine, no GPU) runs on a local port, so core <-> worker is tested for real."""
import contextlib
import importlib.util
import io
import json
import math
import socket
import sys
import threading
import time
import wave
from array import array
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from google.genai import types

from app import voice
from tests.test_voice import FakeSession, _connector, _gemini_env, _msg, read_events, wait_until

pytest.importorskip("numpy")
WORKER_DIR = Path(__file__).resolve().parents[1] / "voice_worker"


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def worker(tmp_path_factory):
    import os
    import uvicorn
    port = _free_port()
    env = {"WORKER_KEY": "wk", "ENGINE": "fake", "VOICES_DIR": str(tmp_path_factory.mktemp("voices"))}
    old = {k: os.environ.get(k) for k in env}
    os.environ.update(env)
    sys.path.insert(0, str(WORKER_DIR))
    spec = importlib.util.spec_from_file_location("awaaz_worker_srv", WORKER_DIR / "worker.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    for k, v in old.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v
    server = uvicorn.Server(uvicorn.Config(mod.app, host="127.0.0.1", port=port, log_level="warning"))
    t = threading.Thread(target=server.run, daemon=True)
    t.start()
    assert wait_until(lambda: server.started, timeout=10)
    yield {"url": f"http://127.0.0.1:{port}", "mod": mod}
    server.should_exit = True
    t.join(5)


@pytest.fixture()
def aw(env, worker, monkeypatch):
    _gemini_env(monkeypatch, AWAAZ_WORKER_URL=worker["url"], AWAAZ_WORKER_KEY="wk", SECRET_KEY="s3cret-for-tests")
    from app.awaaz import service
    service._health.update(at=0.0)
    heard = {"digits": None, "permission": True, "single": True, "live": True}

    def fake_listen(data, script):
        code = heard["digits"]
        if code is None:   # read the code back out of the script, like a real listener would
            words = script.split("Mera code hai:")[1].split(".")[0]
            back = {v: k for k, v in service.DIGITS.items()}
            code = "".join(back[w.strip()] for w in words.split(","))
        return {"transcript": "Yeh meri apni awaaz hai ...", "code_digits": code, "gave_permission": heard["permission"],
                "single_speaker": heard["single"], "live_voice": heard["live"]}

    monkeypatch.setattr(service, "_listen", fake_listen)
    return service, heard


def speech_wav(seconds=14.0, rate=16000, level=0.3):
    """Something with the ups and downs of speech: syllables of a voiced tone with short pauses."""
    n = int(seconds * rate)
    a = array("h")
    for i in range(n):
        t = i / rate
        env_ = max(0.0, math.sin(2 * math.pi * 3.0 * t)) ** 2      # ~3 syllables a second
        a.append(int(level * env_ * math.sin(2 * math.pi * 160 * t) * 32767))
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(a.tobytes())
    return buf.getvalue()


def make_own(c, data=None):
    con = c.post("/api/awaaz/consent", json={}).json()
    r = c.post("/api/awaaz/own", data={"consent_id": con["consent_id"]},
               files={"file": ("me.wav", data or speech_wav(), "audio/wav")})
    return con, r


def test_own_voice_needs_the_consent_script_read_aloud(aw):
    from app import main
    service, heard = aw
    with TestClient(main.app) as c:
        assert "awaaz" in c.get("/healthz").json()["features"]
        con = c.post("/api/awaaz/consent", json={}).json()
        assert "Yeh meri apni awaaz hai" in con["script"] and "ijaazat deta hoon" in con["script"] and len(con["code"]) == 4
        # someone else's clip: the code is not in it
        heard["digits"] = "0000"
        r = c.post("/api/awaaz/own", data={"consent_id": con["consent_id"]}, files={"file": ("x.wav", speech_wav(), "audio/wav")})
        assert r.status_code == 400 and "code" in r.json()["detail"]
        heard["digits"] = None
        heard["live"] = False      # played from a speaker / video
        con, r = make_own(c)
        assert r.status_code == 400 and "live" in r.json()["detail"]
        heard["live"] = True
        con, r = make_own(c)
        assert r.status_code == 200, r.text
        v = r.json()
        assert v["kind"] == "own" and v["status"] == "ready" and v["voice"].startswith("awaaz:")
        # a script works once only
        r2 = c.post("/api/awaaz/own", data={"consent_id": con["consent_id"]}, files={"file": ("me.wav", speech_wav(), "audio/wav")})
        assert r2.status_code == 400 and "ek baar" in r2.json()["detail"]
        # the avatar can now speak in it
        a = c.get("/api/avatar").json()
        assert any(o["id"] == v["voice"] for o in a["own_voices"])
        assert c.put("/api/avatar", json={"voice": v["voice"]}).json()["voice"] == v["voice"]
        # the recording is kept only encrypted
        from app.awaaz.models import VoiceProfile
        from app.db import session
        with session() as s:
            p = s.get(VoiceProfile, v["id"])
            blob = Path(p.sample_file).read_bytes()
            assert p.consent["code"] == con["code"] and p.consent["transcript"]
        assert not blob.startswith(b"RIFF")
        pcm = c.post(f"/api/awaaz/{v['id']}/try", json={"text": "Haan boliye"}).content
        assert len(pcm) > 4800


def test_bad_recordings_are_explained(aw):
    from app import main
    with TestClient(main.app) as c:
        assert "chhoti" in make_own(c, speech_wav(seconds=5))[1].json()["detail"]
        assert "dheemi" in make_own(c, speech_wav(level=0.004))[1].json()["detail"]
        flat = io.BytesIO()
        with wave.open(flat, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(16000)
            w.writeframes(array("h", [int(6000 * math.sin(i / 3)) for i in range(16000 * 12)]).tobytes())
        assert "shor" in make_own(c, flat.getvalue())[1].json()["detail"]
        assert make_own(c, b"not audio")[1].status_code == 400


def test_a_voice_is_only_for_its_own_account(aw):
    from app import main
    from app.avatar import service as av
    service, _ = aw
    with TestClient(main.app) as c:
        v = make_own(c)[1].json()
    assert service.ready_profile("someone-else", v["voice"]) is None
    with pytest.raises(av.AvatarError):
        av.save("someone-else", voice=v["voice"])


def test_delete_removes_it_everywhere(aw, worker):
    from app import main
    import httpx
    with TestClient(main.app) as c:
        v = make_own(c)[1].json()
        c.put("/api/avatar", json={"voice": v["voice"]})
        from app.awaaz.models import VoiceProfile
        from app.db import session
        with session() as s:
            sample = s.get(VoiceProfile, v["id"]).sample_file
        voices_before = httpx.get(worker["url"] + "/healthz").json()["voices"]
        assert c.delete(f"/api/awaaz/{v['id']}").json()["deleted"] is True
        assert not Path(sample).exists()
        assert httpx.get(worker["url"] + "/healthz").json()["voices"] == voices_before - 1
        assert c.get("/api/avatar").json()["voice"] == "Puck"            # back to a Hoola voice
        assert c.delete(f"/api/awaaz/{v['id']}").status_code == 404
        assert all(x["id"] != v["id"] for x in c.get("/api/awaaz").json()["voices"])


def test_designed_voice_from_words(aw):
    from app import main
    with TestClient(main.app) as c:
        r = c.post("/api/awaaz/design/preview", json={"description": "Pune ki jawan ladki, garam awaaz", "gender": "f"})
        assert r.status_code == 200
        pid = r.json()["preview_id"]
        pcm = c.get(f"/api/awaaz/design/preview/{pid}/audio").content
        assert len(pcm) > 24000
        v = c.post("/api/awaaz/design/save", json={"preview_id": pid, "name": "Meera"}).json()
        print(v)
        assert v["kind"] == "design" and v["name"] == "Meera" and v["gender"] == "f"
        assert c.post("/api/awaaz/design/save", json={"preview_id": pid}).status_code == 404   # used up
        lst = c.get("/api/awaaz").json()
        assert lst["enabled"] and lst["worker_ok"] and lst["can_design"]


def _call_turns():
    return [[
        _msg(model_turn=types.Content(parts=[types.Part(inline_data=types.Blob(data=b"\x01\x00" * 100, mime_type="audio/pcm;rate=24000"))]),
             output_transcription=types.Transcription(text="Haan ji, kal ki meeting chaar baje hai.")),
        _msg(turn_complete=True),
    ]]


def test_call_speaks_in_the_owners_voice(aw, monkeypatch):
    from app import main
    fake = FakeSession(_call_turns())
    _connector(monkeypatch, fake)
    with TestClient(main.app) as c:
        v = make_own(c)[1].json()
        c.put("/api/avatar", json={"voice": v["voice"]})
        conv = c.post("/api/conversations").json()["id"]
        with c.websocket_connect(f"/api/voice/ws?conv={conv}&voice={v['voice']}") as ws:
            got, events = [], []
            end = time.time() + 8
            while time.time() < end:
                m = ws.receive()
                if m.get("bytes"):
                    got.append(m["bytes"])
                elif m.get("text"):
                    events.append(json.loads(m["text"]))
                if sum(len(b) for b in got) >= 24000 * 2 * 0.4:
                    break
            ws.send_text(json.dumps({"type": "end"}))
    assert events[0]["type"] == "ready" and events[0]["awaaz"] == "Meri awaaz"
    assert got and b"\x01\x00" * 100 not in got          # Gemini's own voice is not played
    assert sum(len(b) for b in got) >= 24000 * 2 * 0.4    # our worker spoke the transcript


def test_call_falls_back_to_hoola_voice_when_worker_is_down(aw, monkeypatch):
    from app import main
    from app.config import get_settings
    fake = FakeSession(_call_turns())
    _connector(monkeypatch, fake)
    with TestClient(main.app) as c:
        v = make_own(c)[1].json()
        c.put("/api/avatar", json={"voice": v["voice"]})
        monkeypatch.setenv("AWAAZ_WORKER_URL", f"http://127.0.0.1:{_free_port()}")
        get_settings.cache_clear()
        conv = c.post("/api/conversations").json()["id"]
        with c.websocket_connect(f"/api/voice/ws?conv={conv}") as ws:
            events = read_events(ws, lambda e: e["type"] == "turn_done")
            ws.send_text(json.dumps({"type": "end"}))
    kinds = [e.get("state") for e in events if e["type"] == "status"]
    assert "awaaz_off" in kinds
    assert [e for e in events if e["type"] == "ready"][0].get("awaaz") is None
