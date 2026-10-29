"""v0.259.0 CREATE STUDIO: Create opens a full-screen OpenArt-style studio; every page reaches a real engine."""
import asyncio
import io
import json
import re
import shutil
import subprocess
import time
import wave
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
CON = ROOT / "server" / "app" / "static" / "console"
FF = shutil.which("ffmpeg") and shutil.which("ffprobe")


def _read(name):
    return (CON / name).read_text(encoding="utf-8")


def _wav(seconds=1.0, rate=24000):
    b = io.BytesIO()
    with wave.open(b, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(b"\x10\x00" * int(seconds * rate))
    return b.getvalue()


# ---------------------------------------------------------------- engines
def test_song_prompt_keeps_her_lyrics_and_instrumentals_have_no_voice():
    from app.create import service as cs
    p = cs.song_prompt("chai shop love story", "Bollywood romantic", "Hindi", "duet", "Warm", 92, 120, "[Chorus]\nGaram chai")
    assert "male and female duet" in p and "Hindi" in p and "92 BPM" in p and "120 seconds" in p
    assert p.endswith("[Chorus]\nGaram chai")
    i = cs.song_prompt("study beat", "Lo-fi", vocals="none", lyrics="ignored words")
    assert "no vocals" in i and "ignored words" not in i


def test_fit_never_speeds_a_line_beyond_the_cap():
    from app.create import service as cs
    assert cs.fit(0, 5, 3.0, 20) == 1.0                  # fits its slot
    assert cs.fit(0, 3, 3.3, 20) == pytest.approx(3.3 / 2.95, rel=1e-3)
    assert cs.fit(0, 1, 9.0, 20) == cs.FIT_MAX           # never faster than 1.3x
    assert cs.fit(10, None, 4.0, 12) == cs.FIT_MAX       # the last line ends with the video


def test_each_speaker_gets_a_different_matched_voice():
    from app.avatar import service as av
    from app.create import service as cs
    v = cs.speaker_voices([{"id": "S1", "gender": "female"}, {"id": "S2", "gender": "male"}, {"id": "S3", "gender": "female"}])
    assert v["S1"] in av.FEMALE_VOICES and v["S3"] in av.FEMALE_VOICES and v["S2"] in av.MALE_VOICES
    assert v["S1"] != v["S3"]
    assert cs.pick_voice("Kore") == "Kore" and cs.pick_voice("nobody", "f") == "Kore" and cs.pick_voice("", "m") == "Puck"


def test_voice_needs_a_key_and_words(env):
    from app.create import service as cs
    with pytest.raises(cs.CreateError):
        asyncio.run(cs.voice("namaste"))                  # no GEMINI_API_KEY in tests
    assert cs.ready() == {"song": False, "voice": False, "dub": False}


@pytest.mark.skipif(not FF, reason="ffmpeg not installed")
def test_dub_lays_new_voices_over_the_picture(env, monkeypatch, tmp_path):
    """The whole dub pipeline with the two model calls faked: listen -> one voice per line -> ffmpeg mix -> an MP4."""
    from app.create import service as cs
    src = tmp_path / "in.mp4"
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "lavfi", "-i", "testsrc2=size=320x180:rate=25:duration=4",
                    "-f", "lavfi", "-i", "sine=frequency=440:duration=4", "-shortest", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", str(src)], check=True)
    monkeypatch.setattr(cs, "ready", lambda: {"song": True, "voice": True, "dub": True})
    heard = {"source_language": "English", "speakers": [{"id": "S1", "gender": "female"}],
             "lines": [{"start": 0.3, "end": 1.5, "speaker": "S1", "text": "Hello", "tr": {"Tamil": "வணக்கம்", "Hindi": "Namaste"}},
                       {"start": 2.0, "end": 3.5, "speaker": "S1", "text": "Welcome", "tr": {"Tamil": "வரவேற்கிறோம்", "Hindi": "Swagat hai"}}]}
    seen = []
    monkeypatch.setattr(cs, "_listen", lambda audio, langs: (seen.append(("listen", tuple(langs), len(audio) > 0)), heard)[1])
    monkeypatch.setattr(cs, "_pcm", lambda text, voice, how: (seen.append((text, voice)), b"\x20\x00" * 24000)[1])
    r = asyncio.run(cs.dub(src.read_bytes(), "ad.mp4", ["tamil", "Hindi"], keep_sound=True))
    assert [o["language"] for o in r["outputs"]] == ["Tamil", "Hindi"]
    assert ("listen", ("Tamil", "Hindi"), True) in seen and ("வணக்கம்", "Kore") in seen and ("Swagat hai", "Kore") in seen
    out = tmp_path / "out.mp4"
    out.write_bytes(r["outputs"][0]["bytes"])
    assert cs.duration(out) == pytest.approx(4.0, abs=0.3)            # the picture's length, not the voices'
    streams = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type", "-of", "csv=p=0", str(out)],
                             capture_output=True, text=True).stdout.split()
    assert sorted(streams) == ["audio", "video"]


def test_dub_refuses_long_videos_and_no_language(env, monkeypatch):
    from app.create import service as cs
    monkeypatch.setattr(cs, "ready", lambda: {"song": True, "voice": True, "dub": True})
    with pytest.raises(cs.CreateError, match="bhasha"):
        asyncio.run(cs.dub(b"x", "a.mp4", []))
    with pytest.raises(cs.CreateError, match="MB"):
        asyncio.run(cs.dub(b"x" * (cs.MAX_DUB_MB * 1024 * 1024 + 1), "a.mp4", ["Tamil"]))


# ---------------------------------------------------------------- jobs + the shelf + the API
def test_jobs_run_keep_the_file_and_post_a_chat_card(env, monkeypatch):
    from app import main
    from app.create import service as cs

    async def fake_song(*a, **k):
        return {"bytes": b"ID3fake-mp3", "ext": ".mp3", "prompt": "p", "model": "lyria-3.5"}

    async def fake_voice(text, voice_name="", language="Hindi", style="friendly", speed=1.0, tenant=""):
        assert voice_name == "Kore" and style == "calm" and speed == 0.8
        return {"bytes": _wav(), "ext": ".wav", "voice": "Kore", "seconds": 1.0}
    monkeypatch.setattr(cs, "song", fake_song)
    monkeypatch.setattr(cs, "voice", fake_voice)
    with TestClient(main.app) as c:
        conv = c.post("/api/conversations").json()["id"]
        assert c.get("/api/create").json()["voices"]["female"]["Kore"]
        j = c.post("/api/create/jobs", json={"kind": "song", "brief": "chai love", "genre": "Sufi", "conversation_id": conv}).json()
        v = c.post("/api/create/jobs", json={"kind": "voice", "text": "Namaste", "voice": "Kore", "style": "calm",
                                             "speed": 0.8, "conversation_id": conv}).json()
        for _ in range(50):
            if all(c.get(f"/api/create/jobs/{x['id']}").json()["status"] != "running" for x in (j, v)):
                break
            time.sleep(0.1)
        js = c.get(f"/api/create/jobs/{j['id']}").json()
        assert js["status"] == "done" and js["items"][0]["kind"] == "song", js
        items = c.get("/api/create/items").json()["items"]
        assert {i["kind"] for i in items} == {"song", "voice"} and all("file" not in i for i in items)
        song = next(i for i in items if i["kind"] == "song")
        f = c.get(f"/api/create/items/{song['id']}")
        assert f.status_code == 200 and f.content == b"ID3fake-mp3" and f.headers["content-type"].startswith("audio/mpeg")
        assert "sandbox" in f.headers["content-security-policy"]
        # the same file as a card in her chat, marked AI-made
        from sqlalchemy import select
        from app.db import session
        from app.db import Event
        with session() as s:
            cards = [json.loads(e.payload) if isinstance(e.payload, str) else e.payload
                     for e in s.scalars(select(Event).where(Event.conversation_id == conv, Event.kind == "pc_file")).all()]
        assert {x["studio"] for x in cards} == {"song", "voice"} and all(x["ai"] for x in cards)
        assert c.delete(f"/api/create/items/{song['id']}").json() == {"ok": True}
        assert c.get(f"/api/create/items/{song['id']}").status_code == 404
        assert c.post("/api/create/jobs", json={"kind": "nope"}).status_code == 422
        assert c.post("/api/create/jobs", json={"kind": "song", "conversation_id": "conv_missing"}).status_code == 404


def test_failed_job_says_why_and_running_jobs_are_capped(env, monkeypatch):
    from app.create import jobs
    with TestClient(__import__("app.main", fromlist=["app"]).app) as c:
        j = c.post("/api/create/jobs", json={"kind": "image", "prompt": "a chai poster"}).json()
        for _ in range(50):
            x = c.get(f"/api/create/jobs/{j['id']}").json()
            if x["status"] != "running":
                break
            time.sleep(0.1)
        assert x["status"] == "failed" and "GEMINI_API_KEY" in x["error"]
    hold = asyncio.Event()

    async def slow(j, p):
        await hold.wait()
    monkeypatch.setattr(jobs, "_run", slow)

    async def go():
        for _ in range(jobs.MAX_RUNNING):
            jobs.start("t-cap", "voice", {"text": "x"})
        with pytest.raises(jobs.JobError):
            jobs.start("t-cap", "voice", {"text": "x"})
        hold.set()
    asyncio.run(go())


def test_scripts_are_written_kept_and_editable(env, monkeypatch):
    from app import main
    from app.studio import service as ss
    got = {}

    async def fake_write(system, prompt, max_tokens=12000):
        got["system"], got["prompt"] = system, prompt
        return "```\n1. INT. KITCHEN - DAWN\n\nDADI lights a diya.\n```"
    monkeypatch.setattr(ss, "_write", fake_write)
    with TestClient(main.app) as c:
        r = c.post("/api/create/write", json={"kind": "script", "brief": "Diwali ad for chai", "format": "Ad film",
                                              "length": "45 seconds", "language": "Hinglish", "tone": "Warm"}).json()
        assert r["text"].startswith("1. INT. KITCHEN") and "```" not in r["text"]
        assert "screenwriter" in got["system"] and "45 seconds" in got["prompt"] and "Hinglish" in got["prompt"]
        sid = r["item"]["id"]
        assert c.put(f"/api/create/items/{sid}/text", json={"text": "1. EXT. TERRACE - NIGHT"}).json()["ok"]
        assert c.get(f"/api/create/items/{sid}").text == "1. EXT. TERRACE - NIGHT"
        lyr = c.post("/api/create/write", json={"kind": "lyrics", "brief": "monsoon love", "genre": "Sufi"}).json()
        assert lyr["item"] is None and "lyricist" in got["system"]


def test_cast_sheet_prompt_is_four_views_of_one_fictional_person():
    from app.create import service as cs
    p = cs.cast_prompt("Riya", "28, braid, mustard kurta")
    for k in ("ORIGINAL fictional", "front view", "three-quarter", "side profile", "back view", "Riya", "mustard kurta"):
        assert k in p


def test_studio_api_lists_models_and_passes_her_pick(env, monkeypatch):
    from app import main
    from app.studio import service as ss
    got = {}

    async def fake_generate(tenant, project, quality="preview", shot_ids=None, variants=1, model=None, conversation_id=""):
        got.update(quality=quality, model=model)
        return {"waiting_owner": "sa1", "inr": 120}
    monkeypatch.setattr(ss, "generate", fake_generate)
    with TestClient(main.app) as c:
        home = c.get("/api/studio").json()
        assert isinstance(home["models"], list)
        r = c.post("/api/studio/projects/p/generate", json={"quality": "final", "model": "or-wan-3"})
        assert r.json()["waiting_owner"] == "sa1" and got == {"quality": "final", "model": "or-wan-3"}
        c.post("/api/studio/projects/p/generate", json={"quality": "draft"})
        assert got["model"] is None


def test_agent_tool_is_registered_admitted_and_explained():
    from app.agent import admit, tools
    assert tools.FAMILY_OF["create_studio"] == "create" and "create_studio" in tools.HANDLERS
    spec = next(t for t in tools.TOOLS if t["name"] == "create_studio")
    assert set(spec["input_schema"]["properties"]["action"]["enum"]) == {"song", "voice", "dub", "voices"}
    assert "dubbing" in admit.EXTRA_KEYS["create"] and "gaana" in admit.EXTRA_KEYS["create"]
    src = (ROOT / "server" / "app" / "agent" / "prompts.py").read_text()
    assert "create_studio action=song" in src and "not cloned" in src


def test_usage_counts_create_and_a_lyria_song():
    from app import usage
    assert usage.feature_for_path("/api/create/jobs") == "create"
    assert usage.FEATURE_LABEL["create"] == "Create Studio"
    assert usage.cost("lyria-3.5", sec_out=60) == pytest.approx(0.08)


# ---------------------------------------------------------------- console
def test_create_opens_the_studio_and_research_keeps_the_workspace():
    js = _read("v2.js")
    assert "if (v === 'creative' && CREATE) { CREATE.open(); return; }" in js
    assert "CREATE.open(b.dataset.create)" in js and "showWorkspace(); WORKSPACE.open(b.dataset.create);" in js
    assert "CREATE?.reset()" in js and "CREATE?.isOpen()" in js
    html = _read("v2.html")
    assert html.index("studio.js") < html.index("v2.js")
    assert "create-on" in _read("chatlist.js")


def test_studio_is_isolated_and_follows_the_console_theme():
    js, css = _read("studio.js"), _read("studio.css")
    assert "attachShadow({mode: 'open'})" in js and '/static/console/studio.css?v=' in js
    assert css.count("{") == css.count("}")
    host = css[css.index(":host{"):css.index("}", css.index(":host{"))]
    for tok in ("--side:var(--side-bg)", "--priSoft:var(--pri-soft)", "--onPri:var(--on-acc)", "--sans:var(--fb)", "--serif:var(--fr)"):
        assert tok in host, tok
    assert ":root{" not in css and "@property" not in css            # the console's tokens and @property --a are used as they are
    assert not re.search(r"animation:[^;]*\b(both|forwards)\b", css) and "backdrop-filter" not in css   # crisp-text rules
    assert "<script" not in js.replace("'<script'", "")                # CSP script-src 'self': nothing inline


def test_every_page_reaches_a_real_engine():
    js = _read("studio.js")
    for page in ("studio", "image", "video", "music", "voice", "dubbing", "editor", "director", "script", "casting",
                 "templates", "library", "projects", "brand", "learn"):
        assert f"V.{page} = " in js, page
    for route in ("'/api/create/jobs'", "'/api/create/write'", "'/api/create/items'", "'/api/studio/projects'",
                  "/api/studio/approvals/", "'/api/studio/improve'", "'/api/video/jobs'", "/revise", "'/api/brand/kit'",
                  "/keyframes", "/generate", "/assemble", "/characters", "/music", "/pick"):
        assert route in js, route
    assert "e.status === 428 ? fp" in js                                # money cards keep the phone fingerprint rule
    assert "Voices are matched, not cloned" in js and "lips are not re-synced" in js
    assert "Math.random" not in js                                      # results are never invented


def test_results_mark_create_cards_ai_made():
    assert "kind === 'photo_made' || p.ai ? 'AI-generated'" in _read("results.js")
