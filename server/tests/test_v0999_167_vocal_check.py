"""v0.999.168 VOCAL CHECK (built as 0.999.167) - the live check of every Vocal tool, run against fake engines that answer in each engine's
documented shape (ElevenLabs API reference + Google's voices / interactions pages, read 23 Nov 2026): every tool reaches
its engine through the same server function its button uses and comes back as real sound; a tool whose engine refuses
is reported DEAD with the engine's own words; nothing is left behind. Also the own-voice dub's subtitles now come from
the language target's signed WebVTT link (the old transcript route belongs to the legacy API)."""
import base64
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

from app.vocal import check as CK
from app.vocal import eleven as EL
from app.vocal import gvoice as GV
from app.vocal import service as V
from tests.test_v0999_96_vocal_redesign_server import Resp, needs_ff, tone, vg  # noqa: F401


def _ff(args, data, ext):
    with tempfile.TemporaryDirectory() as d:
        src, out = Path(d) / "a.wav", Path(d) / f"b.{ext}"
        src.write_bytes(data)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(src), *args, str(out)], check=True)
        return out.read_bytes()


def _pcm(seconds=0.6):
    return tone(seconds)[44:]


@pytest.fixture
def engines(vg, monkeypatch):  # noqa: F811
    """ElevenLabs + Google voices answered by fakes in their documented shapes. `asked` = (method, path) in order."""
    asked = []
    mp3 = _ff(["-c:a", "libmp3lame"], tone(0.6), "mp3")
    flac = _ff(["-c:a", "flac"], tone(1.2), "flac")
    wav_b64 = base64.b64encode(tone(0.8)).decode()

    def el_http(method, url, **kw):
        path = url.split("api.elevenlabs.io", 1)[-1]
        asked.append(("eleven", method, path.split("?")[0], kw.get("params") or {}, kw.get("json") or kw.get("data") or {}))
        assert method == "GET" and "signed" in url or kw["headers"]["xi-api-key"] == "el-test"
        if path.startswith("/v2/voices"):
            return Resp(body={"voices": [{"voice_id": "e1", "name": "Ana", "labels": {"gender": "female"},
                                          "verified_languages": [{"language": "en"}]},
                                         {"voice_id": "e2", "name": "Ben", "labels": {"gender": "male"},
                                          "verified_languages": [{"language": "en"}]}], "has_more": False})
        if path == "/v1/user/subscription":
            return Resp(body={"tier": "creator", "character_count": 120, "character_limit": 100000})
        if path.startswith("/v1/shared-voices"):
            return Resp(body={"voices": [{"voice_id": "s1", "public_owner_id": "o1", "name": "Calm reader"}], "has_more": False})
        if path.startswith(("/v1/text-to-speech/", "/v1/text-to-dialogue", "/v1/voice-changer/")):
            return Resp(content=_pcm())
        if path.startswith("/v1/sound-generation"):
            return Resp(content=mp3)
        if path.startswith("/v1/audio-isolation"):
            return Resp(content=tone(1.0))
        if path == "/v1/dubbing/project":
            return Resp(body={"project_id": "dp1", "status": "queued"})
        if path == "/v1/dubbing/project/dp1/language":
            return Resp(body={"language_id": "lt1", "project_id": "dp1", "target_language": "es", "status": "queued"})
        if path == "/v1/dubbing/project/dp1/language/lt1":
            return Resp(body={"language_id": "lt1", "status": "completed",
                              "outputs": {"lossless_audio": "https://signed.example/a.flac", "subtitles": "https://signed.example/s.vtt"}})
        if url == "https://signed.example/a.flac":
            assert kw.get("follow_redirects") is True and "headers" not in kw         # a signed link: no key sent
            return Resp(content=flac)
        if url == "https://signed.example/s.vtt":
            return Resp(content=b"WEBVTT\n\n00:00:00.000 --> 00:00:01.000\nHola\n")
        return Resp(404, {"detail": {"message": f"unknown path {path}"}})

    def g_http(method, url, **kw):
        path = url.split("v1beta", 1)[-1]
        asked.append(("gemini", method, path, kw.get("params") or {}, kw.get("json") or {}))
        assert kw["headers"]["x-goog-api-key"] == "test-key"
        if method == "GET" and path == "/voices":
            return Resp(body={"voices": [{"id": "Puck", "display_name": "Puck", "gender": "male", "language_code": "en-US"}]})
        if method == "POST" and path == "/voices":
            v = kw["json"]["voice"]
            assert kw["json"]["store"] is True and v["type"] == "prompted" and v["prompted"]["input"]
            return Resp(body={"id": f"voice_{len(asked)}", "sample_audio": {"mime_type": "audio/wav", "data": wav_b64}})
        if method == "DELETE":
            return Resp(body={})
        if path == "/interactions":
            b = kw["json"]
            assert b["generation_config"]["speech_config"][0]["voice"].startswith("voice_")
            return Resp(body={"steps": [{"type": "model_output", "content": [{"type": "audio", "data": wav_b64}]}]})
        return Resp(404, {"error": {"message": f"unknown path {path}"}})

    monkeypatch.setattr(EL, "key", lambda: "el-test")
    monkeypatch.setattr(EL, "_http", el_http)
    monkeypatch.setattr(GV, "_http", g_http)
    monkeypatch.setattr(GV, "_multi_call", lambda contents, speakers: _pcm())
    monkeypatch.setattr(V, "_CAT", {"at": 0, "gemini": [], "eleven": [], "busy": False, "disk": True, "ok": False})
    monkeypatch.setattr(V, "_gem_json", lambda prompt: (
        {"title": "Check", "lines": [{"speaker": "Host", "text": "Welcome."}, {"speaker": "Guest", "text": "Thanks."}]}
        if "podcast" in prompt.lower() or "conversation" in prompt.lower() else {"text": "Heavy rain drumming on a tin roof", "why": "clearer"}))
    monkeypatch.setattr(V, "DUB_POLL_S", 0)
    from app.vocal import dubbing as DB                    # matched voices: Gemini's own dubbing steps, tested in their suite
    monkeypatch.setattr(DB, "run", lambda tenant, did, path: V._dub_update(
        tenant, did, status="ready", langs=[dict(x, status="ready") for x in V.dub_get(tenant, did)["langs"]]))
    return asked


def _by(rows):
    return {r["tool"]: r for r in rows}


@needs_ff
def test_every_tool_reaches_its_engine_and_brings_back_sound(engines, monkeypatch):
    rows = CK.Check(paid=True).go()
    got = _by(rows)
    live = [t for t, r in got.items() if r["result"] == "LIVE"]
    dead = {t: r["detail"] for t, r in got.items() if r["result"] == "DEAD"}
    assert not dead, dead
    for tool in ("Voice library (Standard voices)", "Voice library (Premium voices)", "ElevenLabs account",
                 "Voice library (shared, Add to my voices)", "Speech (Standard voice)", "Speech (Premium voice)",
                 "Voice preview (Play on a voice)", "Dictionary: Hear it", "Dialogue (line by line)",
                 "Dialogue (natural take, two voices)", "Dialogue (natural take, Premium voices)",
                 "Dialogue: Write it from a document", "Studio: make a chapter", "Sound effects: game sounds",
                 "Sound effects: from words", "Sound effects: Improve the words", "Clean-up (noise, loudness)",
                 "Clean-up: voice out of music", "Voice changer", "Your voice: describe a voice",
                 "Dubbing (matched voices)", "Dubbing (their own voices)", "Download as MP3 / OGG / M4A"):
        assert tool in live, (tool, got.get(tool))
    assert got["Your voice: copy my voice (clone)"]["result"] == "NOT CHECKED"
    # the requests really reached the engines' own endpoints
    paths = {(e, m, p) for e, m, p, *_ in engines}
    for want in (("eleven", "POST", "/v1/text-to-speech/e1"), ("eleven", "POST", "/v1/text-to-dialogue"),
                 ("eleven", "POST", "/v1/sound-generation"), ("eleven", "POST", "/v1/voice-changer/e1"),
                 ("eleven", "POST", "/v1/audio-isolation"), ("eleven", "POST", "/v1/dubbing/project"),
                 ("gemini", "POST", "/voices"), ("gemini", "POST", "/interactions"), ("gemini", "DELETE", "/voices/voice_" )):
        assert any(e == want[0] and m == want[1] and p.startswith(want[2]) for e, m, p in paths), want
    sfx = next(x for x in engines if x[2] == "/v1/sound-generation")
    assert sfx[4]["model_id"] == "eleven_text_to_sound_v3" and sfx[4]["duration_seconds"] == 0.5


@needs_ff
def test_a_refusing_engine_is_reported_dead_with_its_own_words(engines, monkeypatch):
    real = EL._http

    def refuse(method, url, **kw):
        if "/v1/sound-generation" in url:
            return Resp(401, {"detail": {"status": "invalid_api_key", "message": "Invalid API key"}})
        return real(method, url, **kw)
    monkeypatch.setattr(EL, "_http", refuse)
    got = _by(CK.Check().go())
    r = got["Sound effects: from words"]
    assert r["result"] == "DEAD" and "refused the key" in r["detail"]
    assert got["Your voice: describe a voice"]["result"] == "SKIPPED"           # paid checks only with --paid


def test_without_keys_every_engine_tool_says_not_connected(vg, monkeypatch):  # noqa: F811
    from app.create import service as CS
    monkeypatch.setattr(CS, "ready", lambda: {"voice": False, "song": False, "dub": False, "image": False})
    monkeypatch.setattr(EL, "key", lambda: "")
    got = _by(CK.Check().go())
    assert got["Speech (Standard voice)"]["result"] == "NOT CONNECTED"
    assert got["Voice changer"]["result"] == "NOT CONNECTED"
    assert got["Sound effects: game sounds"]["result"] == "LIVE"
    assert not [r for r in got.values() if r["result"] == "DEAD"]


@needs_ff
def test_main_prints_a_table_and_wipes_the_check_account(engines, capsys):
    code = CK.main([])
    out = capsys.readouterr().out
    assert code == 0 and "LIVE" in out and "Speech (Premium voice)" in out
    assert not (Path("data") / "vocal" / V._safe(CK.T)).exists()


@needs_ff
def test_own_voice_dub_subtitles_come_from_the_signed_webvtt_link(engines, tmp_path):
    vid = tmp_path / "v.mp4"
    (tmp_path / "a.wav").write_bytes(tone(1.2))
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "color=c=gray:s=160x120:r=10", "-i",
                    str(tmp_path / "a.wav"), "-shortest", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", str(vid)],
                   check=True)
    r = V.dub_start("t1", str(vid), ["es"], mode="own", name="Clip")
    import time
    end = time.time() + 60
    while time.time() < end and V.dub_get("t1", r["id"])["status"] == "working":
        time.sleep(0.3)
    d = V.dub_get("t1", r["id"])
    assert d["status"] == "ready", d
    lang = d["langs"][0]
    assert lang["subtitles"] == ["srt", "vtt"]
    srt, _ = V.dub_subtitles("t1", r["id"], "es", "srt")
    assert b"00:00:00,000 --> 00:00:01,000" in srt and b"Hola" in srt
    assert not any("/transcript" in p for _, _, p, *_ in engines)          # the legacy route was not needed
