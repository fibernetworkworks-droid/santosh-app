"""HOOLA FRAMES Phase 2 AVATAR FILMS (v0.476): spec -> voice -> word-timed film.

A fake `hyperframes` CLI stands in for the engine (the test_v0_frames FAKE_HF) and a
fake lab.voice stands in for the Modal GPU, but the AUDIO MATH IS REAL: ffprobe measures
the fake WAVs, real ffmpeg pads and concatenates them, and the plan must keep the voice
track frame-aligned with the scenes. Determinism is pinned: same spec + same audio
lengths -> byte-identical HTML. The estimated-word fallback is deterministic by design.
"""
import hashlib
import math
import os
import stat
import sys
import wave
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.agent import frames_tools as ft
from app.studio import avatar as av
from app.studio import frames
from tests.test_life import conv_ctx
from tests.test_v0_frames import FAKE_HF

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


@pytest.fixture
def hf(env, tmp_path, monkeypatch):
    d = tmp_path / "hf"
    d.mkdir()
    exe = d / "hyperframes"
    exe.write_text(FAKE_HF)
    exe.chmod(exe.stat().st_mode | stat.S_IEXEC)
    monkeypatch.setenv("FRAMES_BIN", str(exe))
    monkeypatch.setenv("FRAMES_ROOT", str(tmp_path / "frames_root"))
    monkeypatch.setenv("FRAMES_TIMEOUT_S", "60")
    monkeypatch.setenv("FRAMES_QUEUE_WAIT_S", "1")
    monkeypatch.setenv("FRAMES_KEEP_H", "6")
    monkeypatch.setenv("FRAMES_DISK_CAP_GB", "10")
    from app.config import get_settings
    get_settings.cache_clear()
    return d


def run(name, args, ctx):
    import asyncio
    from app.agent.tools import dispatch
    return asyncio.run(dispatch(name, args, ctx))


def fake_wav(seconds: float, rate: int = 22050) -> bytes:
    """A real, deterministic WAV: 440 Hz sine, mono, 16-bit."""
    import io
    import struct
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        n = int(rate * seconds)
        w.writeframes(b"".join(struct.pack("<h", int(12000 * math.sin(2 * math.pi * 440 * i / rate)))
                               for i in range(n)))
    return buf.getvalue()


SPEC = {"shape": "talking_head", "script": "Namaste doston. Aaj naya offer hai.",
        "title": "Sharma Store", "brand": {"name": "Sharma Store", "color": "#7C3AED"}}


# ---------------------------------------------------------------- registry + version
def test_version_pin():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.705.0"


def test_registry_avatar_film_action():
    assert "avatar_film" in frames._ACTIONS
    spec = ft.FRAMES_TOOLS[0]
    assert spec["name"] == "hoola_frames"
    assert "avatar_film" in spec["input_schema"]["properties"]["action"]["enum"]
    assert "spec" in spec["input_schema"]["properties"]
    assert "talking_head" in spec["input_schema"]["properties"]["spec"]["description"]
    prompts = (ROOT / "app" / "agent" / "prompts.py").read_text(encoding="utf-8")
    assert "action=avatar_film" in prompts and "silent:true" in prompts
    assert "AVATAR FILMS" in prompts


def test_status_carries_avatar_block(hf):
    st = frames.status()
    assert st["enabled"] is True
    a = st["avatar"]
    assert set(a["shapes"]) == {"talking_head", "product", "reel"}
    assert a["lab"] is False, "the lab is not configured in tests - honest status"
    assert list(a["voices"]) == ["chatterbox", "indicf5", "indic_parler"]
    assert a["whisper"] is False, "faster-whisper is not installed in this sandbox"


# ---------------------------------------------------------------- spec guards
def test_split_sentences_beats_and_cap():
    assert av.split_sentences("Yeh pehli line. Yeh doosri? Teesri।") == \
        ["Yeh pehli line.", "Yeh doosri?", "Teesri।"]
    long_one = "ek do teen " * 60                       # 660 chars, no punctuation
    parts = av.split_sentences(long_one)
    assert all(len(p) <= av.MAX_PIECE_CHARS for p in parts) and len(parts) >= 2
    assert "".join(parts).replace(" ", "").startswith("ekdoteen")


def test_validate_spec_guards():
    with pytest.raises(frames.FramesError, match="shape"):
        av.validate_spec({"shape": "hollywood"})
    with pytest.raises(frames.FramesError, match="script"):
        av.validate_spec({"shape": "talking_head"})
    with pytest.raises(frames.FramesError, match="items"):
        av.validate_spec({"shape": "product", "script": "a. b."})
    with pytest.raises(frames.FramesError, match="zyada"):
        av.validate_spec({"script": "ok. " * av.MAX_SENTENCES + "ek aur."})
    with pytest.raises(frames.FramesError, match="assets/"):
        av.validate_spec({"script": "hi.", "avatar": "/etc/passwd"})
    with pytest.raises(frames.FramesError, match="aspect"):
        av.validate_spec({"script": "hi.", "aspect": "21:9"})
    out = av.validate_spec({"shape": "reel", "script": "hi.", "aspect": "16:9"})
    assert out["aspect"] == "9:16" and out["dims"] == (1080, 1920), "reel forces vertical"
    assert av.validate_spec({"silent": True})["sentences"] == [], "silent mode may start empty"
    assert av.validate_spec({"script": "namaste."})["color"] == "#4F46E5", "default brand color"
    assert av.validate_spec({"script": "n.", "brand": {"color": "red"}})["color"] == "#4F46E5"


# ---------------------------------------------------------------- timing math
def test_timing_plan_frames_and_estimate():
    plan = av.timing_plan(["pehli baat.", "doosri baat."], [2.0, 1.5], [1.65, 1.15])
    assert plan["scenes"][0]["start"] == 0.0 and plan["scenes"][1]["start"] == 2.0
    assert plan["total"] == 3.5
    assert all(abs(s["dur"] * plan["fps"] - round(s["dur"] * plan["fps"])) < 1e-6
               for s in plan["scenes"]), "every scene sits on whole frames"
    assert plan["estimated"] is True
    assert plan["cues"], "words were shared out by length and grouped into cues"
    for c in plan["cues"]:
        assert len(c["text"].split()) <= 5 or len(c["text"]) >= 30 or c["text"][-1] in ".?!"


def test_timing_plan_whisper_words_stay_in_their_scene():
    words = [{"start": 0.2, "end": 0.5, "word": "namaste"},
             {"start": 0.6, "end": 1.1, "word": "doston."},
             {"start": 2.1, "end": 2.6, "word": "naya"},
             {"start": 2.7, "end": 3.3, "word": "offer."}]
    plan = av.timing_plan(["Namaste doston.", "Naya offer."], [2.0, 1.5], [1.65, 1.15], words=words)
    assert plan["estimated"] is False
    texts = [c["text"] for c in plan["cues"]]
    assert "namaste doston." in texts and "naya offer." in texts
    for c in plan["cues"]:
        scene = plan["scenes"][c["scene"]]
        assert scene["start"] <= c["start"] and c["end"] <= scene["start"] + scene["dur"] + 1e-6


# ---------------------------------------------------------------- determinism + contract
def test_build_html_deterministic():
    spec = av.validate_spec(SPEC)
    plan = av.timing_plan(spec["sentences"], [2.0, 2.4], [1.65, 2.0])
    h1 = av.build_html(spec, plan)
    h2 = av.build_html(av.validate_spec(dict(SPEC)), av.timing_plan(spec["sentences"], [2.0, 2.4], [1.65, 2.0]))
    assert hashlib.sha256(h1.encode()).hexdigest() == hashlib.sha256(h2.encode()).hexdigest()


def test_build_html_honours_the_contract():
    spec = av.validate_spec({**SPEC, "cta": {"text": "Abhi order kariye"},
                             "avatar": "assets/avatar.jpg"})
    spans = [av.scene_span(1.65, is_last=False, has_cta=True),
             av.scene_span(2.0, is_last=True, has_cta=True)]
    plan = av.timing_plan(spec["sentences"], spans, [1.65, 2.0])
    html = av.build_html(spec, plan)
    assert 'id="voice"' in html and 'src="assets/voice.wav"' in html
    assert f'data-duration="{plan["total"]}"' in html, "root and audio span the whole film"
    assert 'window.__timelines.main = tl' in html
    for banned in ("Date.now", "Math.random", "fetch(", "repeat: -1", "crossorigin"):
        assert banned not in html, f"the contract bans {banned}"
    assert "Noto Sans Devanagari" in html, "Hindi glyphs must resolve"
    assert "data-var-text" in html, "text stays editable"
    assert html.count('class="clip') >= len(plan["cues"]) + 2
    assert 'data-duration="%s"' % plan["total"] in html.split("</body>")[0]
    # the cta card never covers a spoken word
    cta = [l for l in html.splitlines() if 'id="cta"' in l][0]
    cta_start = float(cta.split('data-start="')[1].split('"')[0])
    assert cta_start >= plan["scenes"][-1]["speech"] + plan["scenes"][-1]["start"]


def test_reel_is_vertical_and_product_shows_items():
    spec = av.validate_spec({"shape": "reel", "script": "Naya collection aa gaya. Dekho.",
                             "brand": {"name": "Style"}})
    plan = av.timing_plan(spec["sentences"], [1.8, 1.8], [1.4, 1.4])
    html = av.build_html(spec, plan)
    assert 'data-width="1080"' in html and 'data-height="1920"' in html

    pspec = av.validate_spec({"shape": "product", "script": "Yeh kalam hai. Yeh copy hai.",
                              "title": "Naye items",
                              "items": [{"name": "Kalam", "price": "10 rupaye", "photo": "assets/item-1.png"},
                                        {"name": "Copy", "price": "40 rupaye"}]})
    pplan = av.timing_plan(pspec["sentences"], [1.8, 1.8], [1.4, 1.4])
    phtml = av.build_html(pspec, pplan)
    assert "Kalam" in phtml and "10 rupaye" in phtml and 'src="assets/item-1.png"' in phtml
    assert "40 rupaye" in phtml


# ---------------------------------------------------------------- the worker
def test_avatar_film_silent_end_to_end(hf):
    res = frames.run("default", "avatar_film",
                     spec={"shape": "talking_head", "silent": True,
                           "script": "Pehli baat. Doosri baat.", "brand": {"name": "Sharma Store"}})
    assert res["ok"] is True and res["silent"] is True and res["scenes"] == 2
    assert (Path(res["mp4_path"]).read_bytes() == b"FAKE-MP4-BYTES-0001")
    html = (Path(res["project"]) / "index.html").read_text(encoding="utf-8")
    assert "<audio" not in html and "assets/voice.wav" not in html
    assert res["words_estimated"] is True and res["total_s"] >= 2 * 1.6


def test_avatar_film_voice_end_to_end_frame_aligned(hf, monkeypatch):
    from app.interactive import lab
    monkeypatch.setattr(lab, "configured", lambda: True)
    LENGTHS = [0.5, 0.4]

    def voice(text, lang="hi", model="chatterbox", **_):
        return fake_wav(LENGTHS.pop(0))

    monkeypatch.setattr(lab, "voice", voice)
    res = frames.run("default", "avatar_film", spec={
        "shape": "talking_head", "script": "Namaste doston. Aaj offer hai.",
        "brand": {"name": "Sharma Store"}, "lang": "hi"})
    assert res["ok"] is True and res["silent"] is False
    assert res["words_estimated"] is True, "faster-whisper is absent here -> honest estimate"
    html = (Path(res["project"]) / "index.html").read_text(encoding="utf-8")
    assert 'src="assets/voice.wav"' in html
    voice = Path(res["project"]) / "assets" / "voice.wav"
    assert voice.is_file(), "the real concatenated track was copied into the project"
    with wave.open(str(voice)) as w:
        track = w.getnframes() / w.getframerate()
    assert abs(track - res["total_s"]) < 0.05, "voice track length == film length (frame-aligned)"


def test_avatar_film_lab_down_is_honest(hf, monkeypatch):
    from app.interactive import lab
    monkeypatch.setattr(lab, "configured", lambda: False)
    with pytest.raises(frames.NotConfigured, match="awaaz"):
        frames.run("default", "avatar_film", spec={"script": "hi."})


def test_avatar_film_lab_failure_is_honest(hf, monkeypatch):
    from app.interactive import lab
    monkeypatch.setattr(lab, "configured", lambda: True)

    def boom(text, **_):
        raise lab.LabError("engine did not answer")
    monkeypatch.setattr(lab, "voice", boom)
    with pytest.raises(frames.FramesError, match="awaaz nahi bani"):
        frames.run("default", "avatar_film", spec={"script": "hi."})


def test_avatar_film_missing_asset_refused(hf):
    with pytest.raises(frames.FramesError, match="file_id"):
        frames.run("default", "avatar_film",
                   spec={"script": "hi.", "avatar": "assets/avatar.jpg"})


def test_whisper_words_are_used_when_present(hf, monkeypatch):
    fake_words = [{"start": 0.2, "end": 0.6, "word": "namaste"},
                  {"start": 0.7, "end": 1.3, "word": "doston."},
                  {"start": 2.2, "end": 2.9, "word": "offer"},
                  {"start": 3.0, "end": 3.6, "word": "hai."}]
    monkeypatch.setattr("app.videoedit.captions.whisper_words", lambda path, lang: fake_words)
    from app.interactive import lab
    monkeypatch.setattr(lab, "configured", lambda: True)
    LEN = [0.5, 0.5]

    def voice(text, **_):
        return fake_wav(LEN.pop(0))
    monkeypatch.setattr(lab, "voice", voice)
    res = frames.run("default", "avatar_film", spec={"script": "Namaste doston. Offer hai."})
    assert res["ok"] is True and res["words_estimated"] is False
    html = (Path(res["project"]) / "index.html").read_text(encoding="utf-8")
    assert "namaste doston." in html, "the whisper-timed cue text is in the composition"


# ---------------------------------------------------------------- the tool layer
def test_resolve_spec_maps_file_ids_to_assets(env, tmp_path, monkeypatch):
    from app.mailbox import service as ms
    png = tmp_path / "me.png"
    png.write_bytes(b"PNG")
    jpg = tmp_path / "cup.jpg"
    jpg.write_bytes(b"JPG")
    rows = {"f1": SimpleNamespace(stored_path=str(png)),
            "f2": SimpleNamespace(stored_path=str(jpg))}
    monkeypatch.setattr(ms, "_file_row", lambda tenant, fid: rows[fid])
    ctx = conv_ctx()
    spec, files = ft._resolve_spec(ctx, {
        "shape": "product", "script": "a. b.", "avatar_file_id": "f1",
        "items": [{"name": "Cup", "file_id": "f2"}, {"name": "Plate"}],
        "cta": {"text": "Order karo", "file_id": "f1"}})
    assert spec["avatar"] == "assets/avatar.png" and files[0]["name"] == "assets/avatar.png"
    assert spec["items"][0]["photo"] == "assets/item-1.jpg"
    assert "file_id" not in spec["items"][0] and "file_id" not in spec["cta"]
    assert spec["cta"]["image"] == "assets/cta.png"
    assert len(files) == 3
    bad = tmp_path / "notes.txt"
    bad.write_text("x")
    monkeypatch.setattr(ms, "_file_row", lambda tenant, fid: SimpleNamespace(stored_path=str(bad)))
    with pytest.raises(Exception, match="photo"):
        ft._resolve_spec(ctx, {"script": "a.", "avatar_file_id": "f9"})


def test_avatar_film_via_dispatch_delivers_card(hf):
    ctx = conv_ctx()
    out = run("hoola_frames", {
        "action": "avatar_film",
        "spec": {"shape": "talking_head", "silent": True,
                 "script": "Diwali aa rahi hai. Offer sun lo.", "brand": {"name": "Sharma Store"}},
        "name": "Diwali film"}, ctx)
    assert out.get("made") == "mp4" and out.get("shape") == "talking_head"
    assert out.get("silent") is True and out.get("duration_s")
    assert out.get("file_id"), "delivered through the house mailbox path"


def test_avatar_film_needs_a_spec(hf):
    ctx = conv_ctx()
    from app.agent.tools import ToolError
    with pytest.raises(ToolError, match="Spec"):
        run("hoola_frames", {"action": "avatar_film"}, ctx)


# ---------------------------------------------------------------- the real GPU round (opt-in)
@pytest.mark.skipif(not (os.environ.get("HOOLA_TEST_LAB") and os.environ.get("AVATAR_ENGINE_URL")),
                    reason="real Model Lab round - HOOLA_TEST_LAB=1 with AVATAR_ENGINE_URL set")
def test_real_lab_voice_round():
    from app.interactive import lab
    data = lab.voice("नमस्ते, यह एक टेस्ट है।", lang="hi")
    assert len(data) > 4000 and data[:4] == b"RIFF"
