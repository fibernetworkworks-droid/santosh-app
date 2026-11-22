"""v0.999.96 HOOLA VOCAL REDESIGN - the server half (contract docs/HOOLA_VOCAL_REDESIGN.md sections 2, 3 and the server
part of 4). No network: ElevenLabs and Gemini are faked at their one seam each; ffmpeg is real (it is on the server)."""
import asyncio
import io
import json
import pathlib
import shutil
import subprocess
import wave

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.vocal import eleven as EL
from app.vocal import engines as EN
from app.vocal import gvoice as GV
from app.vocal import service as V

ROOT = pathlib.Path(__file__).resolve().parents[2]
FF = shutil.which("ffmpeg") and shutil.which("ffprobe")
needs_ff = pytest.mark.skipif(not FF, reason="ffmpeg is not installed here")


def tone(seconds=0.4, rate=24000):
    b = io.BytesIO()
    with wave.open(b, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate)
        w.writeframes(b"".join((int(8000 * ((i // 40) % 2 * 2 - 1))).to_bytes(2, "little", signed=True)
                               for i in range(int(rate * seconds))))
    return b.getvalue()


def run(c):
    return asyncio.run(c)


class Resp:
    def __init__(self, status=200, body=None, content=b""):
        self.status_code, self._b = status, body
        self.content = content if content else (json.dumps(body).encode() if body is not None else b"")
        self.text = self.content.decode("utf-8", "ignore")

    def json(self):
        return self._b if self._b is not None else json.loads(self.content or b"{}")


def comment_of(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format_tags=comment:stream_tags=comment", "-of", "json",
                        str(path)], capture_output=True, timeout=60)
    d = json.loads(r.stdout or b"{}")
    tags = [(d.get("format") or {}).get("tags") or {}] + [s.get("tags") or {} for s in d.get("streams") or []]
    return " ".join(str(v) for t in tags for k, v in t.items() if k.lower() == "comment")


def make_video(path, seconds=4):
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi", "-i", f"color=c=black:s=64x64:d={seconds}",
                    "-f", "lavfi", "-i", f"sine=frequency=440:duration={seconds}", "-shortest", "-c:v", "mpeg4", "-c:a", "aac",
                    str(path)], check=True, capture_output=True, timeout=120)


@pytest.fixture
def vg(tmp_path, monkeypatch):
    """Gemini ready (faked), ElevenLabs off, no GPU lab, credits off. `said` records what the engines were asked."""
    monkeypatch.chdir(tmp_path)
    from app.create import service as CS
    from app.interactive import lab
    said = []

    async def voice(text, voice_name="", language="English", style="friendly", speed=1.0, tenant=""):
        said.append(("gemini", voice_name, language, style, text))
        return {"bytes": tone(), "ext": ".wav", "voice": voice_name, "seconds": 0.4}

    monkeypatch.setattr(CS, "voice", voice)
    monkeypatch.setattr(CS, "ready", lambda: {"voice": True, "song": False, "dub": True, "image": True})
    monkeypatch.setattr(lab, "configured", lambda: False)
    monkeypatch.setattr(EL, "key", lambda: "")
    monkeypatch.setattr(V, "_CAT", {"at": 9e18, "gemini": [], "eleven": [], "busy": False})
    from app.config import get_settings
    monkeypatch.setattr(get_settings(), "gemini_api_key", "test-key", raising=False)
    monkeypatch.setattr(get_settings(), "vocal_page", True, raising=False)
    return said


@pytest.fixture
def eleven(monkeypatch):
    """ElevenLabs on, its one network seam recording every request."""
    sent = []
    replies = {}

    def http(method, url, **kw):
        sent.append((method, url, kw))
        for k, fn in replies.items():
            if k in url:
                return fn(method, url, kw)
        return Resp(content=b"\x00\x01" * 2400)
    monkeypatch.setattr(EL, "key", lambda: "xi-test")
    monkeypatch.setattr(EL, "_http", http)
    return sent, replies


@pytest.fixture
def client(vg):
    from app.vocal import api
    app = FastAPI()
    app.include_router(api.make_router(lambda: None, lambda: "t1"))
    return TestClient(app)


# ---------------------------------------------------------------- 2.3 / 2.4 / 2.12 formats + the AI mark
@needs_ff
def test_speech_format_is_honoured_and_each_file_carries_the_ai_mark(vg):
    for fmt, magic in (("mp3", (b"ID3", b"\xff\xfb", b"\xff\xf3")), ("ogg", (b"OggS",)), ("m4a", (b"\x00\x00\x00",)), ("wav", (b"RIFF",))):
        r = run(V.tts("t1", "Hello there, welcome.", voice="hv_Kore", fmt=fmt))
        assert r["ext"] == fmt and r["fmt"] == fmt and r["seconds"] > 0
        f, h = V.audio_file("t1", r["id"])
        assert f.suffix == f".{fmt}" and f.read_bytes()[:4].startswith(magic) or f.read_bytes()[:3] in magic, fmt
        if fmt == "m4a":
            assert f.read_bytes()[4:8] == b"ftyp"
        if fmt == "wav":
            assert b"Made with AI by Hoola Vocal" in f.read_bytes()
        else:
            assert "Made by AI · Hoola Vocal" in comment_of(f), fmt
    with pytest.raises(V.VocalError, match="MP3, WAV, OGG or M4A"):
        run(V.tts("t1", "Hello.", voice="hv_Kore", fmt="aiff"))


@needs_ff
def test_audio_download_converts_to_exactly_the_four_formats_and_overview_lists_them(vg, client):
    r = run(V.tts("t1", "A line to download.", voice="hv_Kore"))
    o = V.overview("t1")
    assert [f["id"] for f in o["formats"]] == ["mp3", "wav", "ogg", "m4a"] and all(f["name"] and f["note"] for f in o["formats"])
    assert {f["note"] for f in o["formats"]} == {"Small, for sharing", "Studio quality", "For WhatsApp", "For iPhone"}
    for fmt, mime in (("mp3", "audio/mpeg"), ("ogg", "audio/ogg"), ("m4a", "audio/mp4"), ("wav", "audio/wav")):
        res = client.get(f"/api/vocal/audio?id={r['id']}&format={fmt}")
        assert res.status_code == 200 and res.headers["content-type"].startswith(mime), fmt
        assert f'.{fmt}"' in res.headers["content-disposition"]
    assert client.get(f"/api/vocal/audio?id={r['id']}&format=exe").status_code == 422


@needs_ff
def test_an_engine_mp3_gets_the_mark_in_its_metadata(vg, eleven):
    sent, replies = eleven
    mp3 = V._convert(tone(1.0), "mp3")
    replies["/v1/sound-generation"] = lambda m, u, kw: Resp(content=mp3)
    out = V.sfx_text("t1", "rain on a tin roof", seconds=2, takes=1)
    f, _ = V.audio_file("t1", out["items"][0]["id"])
    assert "Made by AI · Hoola Vocal" in comment_of(f)


# ---------------------------------------------------------------- 2.5 prices by job id
def test_the_price_follows_the_job_id_never_a_label(client):
    assert client.post("/api/vocal/quote", json={"job": "Speech, 1 minute"}).status_code == 422
    q = client.post("/api/vocal/quote", json={"job": "dub_line"}).json()
    assert q["job"] == "dub_line" and q["credits"] == 1
    assert client.post("/api/vocal/quote", json={"job": "tts", "chars": 900}).json()["job"] == "tts"
    rows = EN.prices()
    assert all(r["id"] in EN.JOBS for r in rows) and {"tts", "dub_own", "dub_line", "cleanup"} <= {r["id"] for r in rows}


# ---------------------------------------------------------------- 2.10 the orphan music route
def test_the_orphan_music_route_is_gone(client):
    assert '"/music"' not in (ROOT / "server/app/vocal/api.py").read_text() and not hasattr(V, "music")
    assert client.post("/api/vocal/music", json={"brief": "x"}).status_code in (404, 405)


# ---------------------------------------------------------------- 2.11 zero credits
def test_zero_credits_refuses_before_any_engine_call(vg, client, monkeypatch, eleven):
    from app.credits import wallet as W
    sent, _ = eleven
    monkeypatch.setattr(W, "active", lambda t: True)
    monkeypatch.setattr(W, "can_run", lambda t: False)
    with pytest.raises(V.VocalNoCredits, match="no credits left"):
        run(V.tts("t1", "Hello.", voice="hv_Kore"))
    res = client.post("/api/vocal/tts", json={"text": "Hello there.", "voice": "hv_Kore"})
    assert res.status_code == 402 and res.json()["credits"] == "/console/?v=credits" and "no credits" in res.json()["detail"]
    assert client.post("/api/vocal/sfx", json={"prompt": "rain on a roof"}).status_code == 402
    assert client.post("/api/vocal/dialogue", json={"lines": [{"speaker": "A", "text": "Hi"}], "cast": {"A": "hv_Kore"}}).status_code == 402
    assert vg == [] and not [s for s in sent if "sound-generation" in s[1]]
    monkeypatch.setattr(W, "can_run", lambda t: True)
    assert client.post("/api/vocal/tts", json={"text": "Hello there.", "voice": "hv_Kore"}).status_code == 200


# ---------------------------------------------------------------- 2.9 design options with no sound
def test_a_designed_option_with_no_audio_is_never_returned(vg, monkeypatch):
    made, gone = [], []

    def design(desc, name, gender="", lang=""):
        made.append(name)
        return {"id": f"voice_{len(made)}", "sample": tone() if len(made) != 2 else b""}
    monkeypatch.setattr(GV, "design", design)
    monkeypatch.setattr(GV, "delete", lambda gid: gone.append(gid))
    out = V.design_preview("t1", "A calm older woman with a low warm voice, unhurried")
    assert len(out["previews"]) == 2 and all(p["audio_id"] for p in out["previews"]) and gone == ["voice_2"]
    monkeypatch.setattr(GV, "design", lambda *a, **k: {"id": "voice_x", "sample": b""})
    with pytest.raises(V.VocalError, match="no option you can hear"):
        V.design_preview("t1", "A calm older woman with a low warm voice, unhurried")


# ---------------------------------------------------------------- 2.8 voice changer
@needs_ff
def test_the_changer_takes_a_page_recording_and_refuses_a_google_only_voice(vg, eleven, tmp_path, monkeypatch):
    sent, replies = eleven
    wav = tmp_path / "r.wav"; wav.write_bytes(tone(1.0))
    webm = tmp_path / "rec.webm"
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(wav), "-c:a", "libopus", str(webm)],
                   check=True, capture_output=True, timeout=60)
    d = V._load("t1")
    d["voices"].insert(0, {"id": "mv_aaaaaaaaaaaa", "name": "Me", "kind": "clone", "engine": "gemini", "gid": "voice_1"})
    V._store("t1", d)
    with pytest.raises(V.VocalError, match="lives on Google's engine.*only with voices on ElevenLabs"):
        V.change("t1", str(webm), "mv_aaaaaaaaaaaa")
    replies["/v1/voices/add/"] = lambda m, u, kw: Resp(body={"voice_id": "el_new"})
    mine = V.library_add("t1", "pubvoice1", "owner1", "Narrator Nia")
    out = V.change("t1", str(webm), mine["id"])
    m, url, kw = sent[-1]
    assert url.endswith("/v1/voice-changer/el_new") and kw["files"]["audio"][1][:4] == b"RIFF"    # webm turned into WAV
    assert out["kind"] == "change" and out["engine"] == "eleven"


# ---------------------------------------------------------------- 2.1 / 2.2 / 2.6 dubbing: subtitles, the line editor, 6 speakers
@pytest.fixture
def matched(vg, monkeypatch, tmp_path):
    from app.create import service as CS
    vid = tmp_path / "tour.mp4"
    make_video(vid, 4)
    seen = {}

    async def dub(video, name, langs, keep_sound=True, voices_for=None, progress=None):
        seen["voices_for"] = voices_for
        keep = CS.KEEP_CLIPS.get()
        lines = [{"start": 0.2, "end": 1.6, "speaker": "S1", "text": "Hello and welcome.", "tr": {"Spanish": "Hola y bienvenidos."}},
                 {"start": 2.0, "end": 2.4, "speaker": "S2", "text": "Thanks.",
                  "tr": {"Spanish": "Muchísimas gracias a todos por venir hoy a esta presentación tan larga."}}]
        for i, _ in enumerate(lines):
            pathlib.Path(keep, f"Spanish_{i:03d}.wav").write_bytes(tone(0.8 if i == 0 else 3.0))
        return {"source_language": "English", "speakers": [{"id": "S1"}, {"id": "S2"}], "voices": {"S1": "Kore", "S2": "Puck"},
                "lines": lines, "outputs": [{"language": "Spanish", "bytes": vid.read_bytes(), "seconds": 4.0}]}
    monkeypatch.setattr(CS, "dub", dub)
    r = V.dub_start("t1", str(vid), ["es"], voices={"S1": "hv_Kore", "S2": "hv_Puck"})
    V._DUB_THREADS.get(r["id"]) and V._DUB_THREADS[r["id"]].join(20)
    return r["id"], seen


@needs_ff
def test_every_finished_dub_language_has_srt_and_vtt(matched, client):
    did, _ = matched
    g = V.dub_get("t1", did)
    assert g["status"] == "ready" and g["langs"][0]["subtitles"] == ["srt", "vtt"]
    srt = client.get(f"/api/vocal/dub/{did}/subtitles?lang=es&format=srt")
    assert srt.status_code == 200 and "00:00:00,200 --> 00:00:01,600" in srt.text and "Hola y bienvenidos." in srt.text
    assert srt.headers["content-disposition"].endswith('.srt"')
    vtt = client.get(f"/api/vocal/dub/{did}/subtitles?lang=es&format=vtt")
    assert vtt.text.startswith("WEBVTT") and "00:00:00.200 --> 00:00:01.600" in vtt.text and vtt.headers["content-type"].startswith("text/vtt")
    assert client.get(f"/api/vocal/dub/{did}/subtitles?lang=fr").status_code == 422


@needs_ff
def test_the_dub_line_editor_saves_and_redoes_one_line(matched, client, monkeypatch):
    from app.create import service as CS
    did, seen = matched
    assert seen["voices_for"] == {"S1": "Kore", "S2": "Puck"}                          # her pick per speaker reached the engine
    out = client.get(f"/api/vocal/dub/{did}/lines?lang=es").json()
    assert out["editable"] is True and len(out["lines"]) == 2
    first, second = out["lines"]
    assert set(first) >= {"n", "start", "end", "speaker", "src", "dst", "too_long"}
    assert first["src"] == "Hello and welcome." and first["dst"] == "Hola y bienvenidos." and not first["too_long"]
    assert second["too_long"] is True                                                   # 3 s of speech for a 2 s slot
    res = client.put(f"/api/vocal/dub/{did}/lines/1", json={"lang": "es", "text": "Gracias."})
    assert res.status_code == 200 and res.json()["dst"] == "Gracias."
    spoke = []
    monkeypatch.setattr(CS, "_pcm", lambda text, voice, how: spoke.append((text, voice, how)) or b"\x10\x00" * 12000)
    vid = V.dub_get("t1", did)["langs"][0]["video_id"]
    before = V.audio_file("t1", vid)[0].read_bytes()
    res = client.post(f"/api/vocal/dub/{did}/lines/1/redo", json={"lang": "es"})
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["credits"] == 1 and body["video_id"] == vid and body["line"]["too_long"] is False
    assert spoke == [("Gracias.", "Puck", spoke[0][2])] and "Spanish" in spoke[0][2]    # one line, its speaker's voice
    after = V.audio_file("t1", vid)[0].read_bytes()
    assert after != before and after[4:8] == b"ftyp"                                    # the language's video rebuilt


def test_the_editor_is_honest_about_old_and_own_voice_dubs(vg):
    d = V._load("t1")
    d["dubs"] = [{"id": "vd_old", "status": "ready", "mode": "matched", "name": "a.mp4", "seconds": 5, "lines":
                  [{"start": 0, "end": 1, "speaker": "S1", "text": "Hi", "tr": {"es": "Hola"}}],
                  "langs": [{"code": "es", "name": "Spanish", "status": "ready", "video_id": "vo_x"}]},
                 {"id": "vd_own", "status": "ready", "mode": "own", "name": "b.mp4", "seconds": 5, "lines": [],
                  "langs": [{"code": "es", "name": "Spanish", "status": "ready", "video_id": "vo_y"}]}]
    V._store("t1", d)
    V._DUB_THREADS.clear()
    old = V.dub_lines("t1", "vd_old", "es")
    assert old["editable"] is False and "made before" in old["why"] and old["lines"][0]["dst"] == "Hola"
    own = V.dub_lines("t1", "vd_own", "es")         # v0.999.125: own-voice lines come from ElevenLabs when it is on
    assert own == {**own, "editable": False, "lines": []} and "not connected" in own["why"]
    with pytest.raises(V.VocalError, match="not found"):
        V.dub_line_save("t1", "vd_own", 0, "es", "x")
    with pytest.raises(V.VocalError, match="made before"):
        V.dub_line_redo("t1", "vd_old", 0, "es")


@needs_ff
def test_matched_dubs_take_six_speakers_never_seven_and_only_standard_voices(vg, tmp_path):
    vid = tmp_path / "v.mp4"; make_video(vid, 2)
    with pytest.raises(V.VocalError, match="6 speakers"):
        V.dub_start("t1", str(vid), ["es"], voices={f"S{i}": "hv_Kore" for i in range(1, 8)})
    with pytest.raises(V.VocalError, match="6 speakers"):
        V.dub_start("t1", str(vid), ["es"], speakers=7)
    with pytest.raises(V.VocalError, match="up to 4 languages"):
        V.dub_start("t1", str(vid), ["es", "fr", "de", "it", "pt"])
    assert V.overview("t1")["limits"]["dub_speakers"] == 6
    assert V._dub_voices(V._load("t1"), [f"hv_{n}" for n in ("Kore", "Puck", "Charon", "Aoede", "Leda", "Orus")]) == \
        {"S1": "Kore", "S2": "Puck", "S3": "Charon", "S4": "Aoede", "S5": "Leda", "S6": "Orus"}


@needs_ff
def test_an_own_voice_dub_is_counted_in_credits_and_gets_subtitles(vg, eleven, tmp_path, monkeypatch):
    from app import usage
    sent, replies = eleven
    vid = tmp_path / "v.mp4"; make_video(vid, 2)
    monkeypatch.setattr(V, "DUB_POLL_S", 0)
    flac = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i", "sine=duration=2", "-f", "flac",
                           "pipe:1"], capture_output=True, timeout=60).stdout
    replies["/v1/dubbing/project/p1/language/"] = lambda m, u, kw: Resp(body={"status": "completed",
                                                                            "outputs": {"lossless_audio": {"url": "https://x.example/a.flac"}}})
    replies["/v1/dubbing/project/p1/language"] = lambda m, u, kw: Resp(body={"language_id": "L1"})
    replies["/v1/dubbing/project"] = lambda m, u, kw: Resp(body={"project_id": "p1"})
    replies["/transcript/es"] = lambda m, u, kw: Resp(body={"srt": "1\n00:00:00,000 --> 00:00:01,500\nHola\n"})
    replies["x.example"] = lambda m, u, kw: Resp(content=flac)
    rec = []
    real = usage.record
    monkeypatch.setattr(usage, "record", lambda model, **kw: rec.append((model, kw)) or real(model, **kw))
    r = V.dub_start("t1", str(vid), ["es"], mode="own")
    V._DUB_THREADS.get(r["id"]) and V._DUB_THREADS[r["id"]].join(30)
    g = V.dub_get("t1", r["id"])
    assert g["status"] == "ready" and g["langs"][0]["subtitles"] == ["srt", "vtt"]
    assert any(m == "elevenlabs-dub" and kw.get("tenant") == "t1" and kw.get("sec_out", 0) >= 1 for m, kw in rec)
    data, name = V.dub_subtitles("t1", r["id"], "es", "vtt")
    assert data.decode().startswith("WEBVTT") and "00:00:00.000 --> 00:00:01.500" in data.decode() and name.endswith(".vtt")
    hist = next(h for h in V._load("t1")["history"] if h["id"] == g["langs"][0]["video_id"])
    assert hist["credits"] == EN.quote("dub_own", seconds=g["seconds"], engine="eleven")["credits"]


# ---------------------------------------------------------------- 3.1 the shared voice library
def test_the_shared_library_without_elevenlabs_says_why(vg, client):
    out = client.get("/api/vocal/library").json()
    assert out["voices"] == [] and out["ready"] is False and "ElevenLabs" in out["why"] and "API_KEY" not in out["why"]


def test_the_shared_library_reads_filters_adds_and_proxies_previews(vg, eleven, client):
    sent, replies = eleven
    prev = "https://storage.googleapis.com/eleven-public-prod/abc/preview.mp3"
    replies["/v1/shared-voices"] = lambda m, u, kw: Resp(body={"has_more": True, "voices": [
        {"voice_id": "v1", "public_owner_id": "o1", "name": "Nia", "description": "Warm storyteller", "gender": "female",
         "age": "middle_aged", "accent": "british", "use_case": "narrative_story", "cloned_by_count": 812, "language": "en",
         "verified_languages": [{"language": "es"}], "preview_url": prev},
        {"voice_id": "v2", "public_owner_id": "", "name": "No owner"}]})
    out = client.get("/api/vocal/library?q=story&lang=Spanish&gender=female&age=middle%20aged&accent=british&use=narrative%20story&sort=popular&page=2").json()
    m, url, kw = sent[-1]
    p = kw["params"]
    assert url.endswith("/v1/shared-voices") and p["search"] == "story" and p["language"] == "es" and p["gender"] == "female"
    assert p["age"] == "middle_aged" and p["use_cases"] == "narrative_story" and p["sort"] == "usage_character_count_1y" and p["page"] == 2
    assert out["ready"] and out["more"] and len(out["voices"]) == 1
    v = out["voices"][0]
    assert {k: v[k] for k in ("id", "owner", "name", "line", "gender", "age", "accent", "use", "uses")} == \
        {"id": "v1", "owner": "o1", "name": "Nia", "line": "Warm storyteller", "gender": "female", "age": "middle aged",
         "accent": "british", "use": "narrative story", "uses": 812}
    assert v["langs"] == ["en", "es"] and v["preview"].startswith("/api/vocal/library/preview?url=")
    replies["eleven-public-prod"] = lambda m, u, kw: Resp(content=b"ID3preview")
    res = client.get(v["preview"])
    assert res.status_code == 200 and res.content == b"ID3preview" and res.headers["content-type"] == "audio/mpeg"
    assert client.get("/api/vocal/library/preview?url=https://evil.example/x.mp3").status_code == 422
    assert client.get("/api/vocal/library/preview?url=http://storage.googleapis.com/eleven-public-prod/x.mp3").status_code == 422
    replies["/v1/voices/add/"] = lambda m, u, kw: Resp(body={"voice_id": "el_added"})
    a = client.post("/api/vocal/library/add", json={"id": "v1", "owner": "o1", "name": "Nia"}).json()
    m, url, kw = sent[-1]
    assert url.endswith("/v1/voices/add/o1/v1") and kw["json"] == {"new_name": "Nia"}
    assert a["engine"] == "eleven" and a["eid"] == "el_added" and a["kind"] == "shared" and a["tier"] == "premium"
    again = client.post("/api/vocal/library/add", json={"id": "v1", "owner": "o1", "name": "Nia"}).json()
    assert again["id"] == a["id"] and len(V._load("t1")["voices"]) == 1                 # added once
    run(V.tts("t1", "Hello there.", voice=a["id"], lang="en"))
    assert sent[-1][1].endswith("/v1/text-to-speech/el_added")
    V.voice_remove("t1", a["id"])
    assert sent[-1][0] == "DELETE" and sent[-1][1].endswith("/v1/voices/el_added")


# ---------------------------------------------------------------- 3.2 natural dialogue
def test_natural_dialogue_two_standard_voices_in_one_gemini_take(vg, monkeypatch, client):
    asked = []
    monkeypatch.setattr(GV, "_multi_call", lambda contents, speakers: asked.append((contents, speakers)) or b"\x01\x00" * 24000)
    lines = [{"speaker": "Maya", "text": "[warm] Welcome back!"}, {"speaker": "Kofi", "text": "[laughs] Glad to be here. [pause] Really."}]
    res = client.post("/api/vocal/dialogue", json={"lines": lines, "cast": {"Maya": "hv_Kore", "Kofi": "hv_Puck"}, "mode": "natural"})
    assert res.status_code == 200, res.text
    r = res.json()
    contents, speakers = asked[0]
    assert speakers == {"Maya": "Kore", "Kofi": "Puck"} and r["mode"] == "natural" and r["engine"] == "gemini"
    body = contents.split("\n", 1)[1]
    assert body.startswith("Maya: Welcome back!") and "[" not in body and "<laugh>" in body and "<short pause>" in body
    assert "warm and kind" in contents.split("\n", 1)[0] and vg == []                   # one take, not line by line
    three = lines + [{"speaker": "Ana", "text": "Hi."}]
    bad = client.post("/api/vocal/dialogue", json={"lines": three, "cast": {"Maya": "hv_Kore", "Kofi": "hv_Puck", "Ana": "hv_Leda"},
                                                   "mode": "natural"})
    assert bad.status_code == 422 and "exactly two speakers" in bad.json()["detail"]
    old = client.post("/api/vocal/dialogue", json={"lines": three, "cast": {"Maya": "hv_Kore", "Kofi": "hv_Puck", "Ana": "hv_Leda"}})
    assert old.status_code == 200 and old.json()["mode"] == "lines" and len(vg) == 3


def test_natural_dialogue_on_elevenlabs_for_more_speakers(vg, eleven):
    sent, _ = eleven
    lines = [{"speaker": s, "text": f"[excited] Line {i}"} for i, s in enumerate(("A", "B", "C"))]
    r = run(V.dialogue("t1", lines, {"A": "ev_a1", "B": "ev_b2", "C": "ev_c3"}, mode="natural", lang="en"))
    m, url, kw = sent[-1]
    assert url.endswith("/v1/text-to-dialogue") and kw["json"]["model_id"] == "eleven_v3"
    assert kw["json"]["inputs"] == [{"text": "[excited] Line 0", "voice_id": "a1"}, {"text": "[excited] Line 1", "voice_id": "b2"},
                                    {"text": "[excited] Line 2", "voice_id": "c3"}]          # v3 reads the tags itself
    assert r["engine"] == "eleven" and r["seconds"] > 0 and len([s for s in sent if "text-to-dialogue" in s[1]]) == 1
    with pytest.raises(V.VocalError, match="one engine"):
        run(V.dialogue("t1", lines[:2], {"A": "ev_a1", "B": "hv_Kore"}, mode="natural", lang="en"))


# ---------------------------------------------------------------- 3.3 tone tags on every engine
def test_tone_tags_are_never_read_aloud_on_gemini(vg):
    run(V.tts("t1", "[warm] Hello. [whispers] a secret [laughs] then [excited] wow [pause] and [slowly] goodbye.", voice="hv_Kore", lang="en"))
    _, _, _, style, text = vg[-1]
    for tag in ("warm", "whispers", "laughs", "excited", "pause", "slowly"):
        assert f"[{tag}]" not in text
    assert "warm and kind" in style and "whispering" in style and "excited" in style and "speaking slowly" in style
    assert "<laugh>" in text and "<short pause>" in text and "secret" in text and "goodbye" in text


# ---------------------------------------------------------------- 3.4 the pronunciation dictionary with IPA
def test_rules_with_ipa_and_csv_import(vg, client):
    r = client.post("/api/vocal/rule", json={"word": "Hoola", "say": "", "ipa": "/ˈhuːlə/", "lang": "en"}).json()
    assert r["ipa"] == "ˈhuːlə" and r["say"] == "" and r["lang"] == "en"
    assert client.post("/api/vocal/rule", json={"word": "X", "ipa": "<b>"}).status_code == 422
    out = client.post("/api/vocal/rules/import", json={"text": "word,say,ipa,lang\nGST,G S T,,\nNewtika,New-tee-ka,njuːˈtiːkə,en\n,missing\nHola,Oh-la,,klingon\n"}).json()
    assert out["added"] == 2 and [s["line"] for s in out["skipped"]] == [3, 4] and "Unknown language" in out["skipped"][1]["why"]
    rules = V.overview("t1")["rules"]
    assert {x["word"] for x in rules} == {"Hoola", "GST", "Newtika"} and next(x for x in rules if x["word"] == "Newtika")["ipa"]
    run(V.tts("t1", "Hoola files GST for Newtika.", voice="hv_Kore", lang="en"))
    _, _, _, style, text = vg[-1]
    assert "G S T" in text and "New-tee-ka" in text and "Hoola" in text           # respellings by code, IPA-only word kept
    assert "pronounce" in style and "/ˈhuːlə/" in style and "ˈhuːlə" not in text  # the IPA is an instruction, never spoken


# ---------------------------------------------------------------- 3.5 studio re-reads only changed paragraphs
def test_studio_rereads_only_the_changed_paragraph(vg):
    p = V.project_save("t1", title="Book", voice="hv_Kore", lang="en",
                       chapters=[{"title": "One", "text": "First paragraph.\n\nSecond paragraph.\n\nThird paragraph."}])
    run(V.chapter_make("t1", p["id"], 0))
    assert len(vg) == 3
    V.project_save("t1", pid=p["id"], title="Book", voice="hv_Kore", lang="en",
                   chapters=[{"title": "One", "text": "First paragraph.\n\nSecond paragraph, changed.\n\nThird paragraph."}])
    row = run(V.chapter_make("t1", p["id"], 0))
    assert len(vg) == 4 and vg[-1][4] == "Second paragraph, changed." and row["read_again"] == 1 and row["reused"] == 2


# ---------------------------------------------------------------- 3.6 streaming is not faked
def test_streaming_is_not_offered(vg):
    assert V.connected()["stream"] is False          # v0.999.125: offered only when ElevenLabs is on (Premium voices)


# ---------------------------------------------------------------- 4 a Vocal take appears once in Create > My creations
def test_a_vocal_take_appears_once_in_my_creations(vg):
    from app.create import jobs as CJ
    r = run(V.tts("t1", "Welcome to the shop.", voice="hv_Kore", takes=2))
    shelf = [i for i in CJ.shelf("t1") if (i.get("meta") or {}).get("from") == "vocal"]
    assert len(shelf) == 2 and {i["kind"] for i in shelf} == {"voice"}
    assert {(i["meta"]["vocal"]) for i in shelf} == {x["id"] for x in r["items"]}
    one = r["items"][0]
    V._to_create("t1", dict(one), b"RIFF")                                    # never twice
    assert len([i for i in CJ.shelf("t1") if (i.get("meta") or {}).get("vocal") == one["id"]]) == 1
    V.history_remove("t1", one["id"])
    assert not [i for i in CJ.shelf("t1") if (i.get("meta") or {}).get("vocal") == one["id"]]


def test_no_visible_text_names_a_server_key(vg):
    o = V.overview("t1")
    assert "API_KEY" not in json.dumps(o) and ".env" not in json.dumps(o)
    with pytest.raises(V.VocalError) as e:
        V.sfx_text("t1", "rain on a roof")
    assert "API_KEY" not in str(e.value)


# ---------------------------------------------------------------- lead's additions: saved defaults, more languages, use words
def test_her_defaults_are_saved_and_come_back_in_the_overview(vg, client):
    r = client.put("/api/vocal/settings", json={"lang": "hi", "format": "ogg", "takes": 9, "voice": "hv_Kore", "junk": "x"})
    assert r.status_code == 200 and r.json() == {"lang": "hi", "format": "ogg", "takes": V.MAX_TAKES, "voice": "hv_Kore"}
    assert client.get("/api/vocal/settings").json()["format"] == "ogg"
    assert V.overview("t1")["settings"]["lang"] == "hi"
    assert client.put("/api/vocal/settings", json={"format": "flac"}).status_code == 422


@needs_ff
def test_more_languages_make_a_new_dub_of_the_same_video_with_the_same_voices(matched, client, monkeypatch):
    did, seen = matched
    seen.clear()
    r = client.post(f"/api/vocal/dub/{did}/langs", json={"langs": ["hi", "es"]})
    assert r.status_code == 200, r.text
    new = r.json()
    assert new["id"] != did and [x["code"] for x in new["langs"]] == ["hi"]
    V._DUB_THREADS.get(new["id"]) and V._DUB_THREADS[new["id"]].join(20)
    assert seen.get("voices_for") is not None
    assert client.post(f"/api/vocal/dub/{did}/langs", json={"langs": ["es"]}).status_code == 422
    assert client.post("/api/vocal/dub/vd_nope/langs", json={"langs": ["hi"]}).status_code in (404, 422)


def test_plain_use_words_reach_elevenlabs_as_its_use_cases(vg, eleven, client):
    sent, replies = eleven
    replies["/v1/shared-voices"] = lambda m, u, kw: Resp(body={"has_more": False, "voices": []})
    for word, want in (("ads", "advertisement"), ("stories", "narrative_story"), ("support", "conversational"), ("social", "social_media")):
        client.get(f"/api/vocal/library?use={word}")
        assert sent[-1][2]["params"]["use_cases"] == want
