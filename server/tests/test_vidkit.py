"""Video kit (app/vidkit + tool video_kit): real ffmpeg on generated video, measured, not mocked."""
import asyncio
import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest
from PIL import Image

from app.agent import admit, tools, vidkit_tools as T
from app.vidkit import ops

pytestmark = pytest.mark.skipif(not ops.ffmpeg_ok(), reason="ffmpeg not installed")


def run(c):
    return asyncio.run(c)


def _ff(*args: str) -> None:
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *args], check=True)


@pytest.fixture(scope="module")
def media(tmp_path_factory):
    d = tmp_path_factory.mktemp("vid")
    land = d / "land.mp4"                  # 640x360, 6 s, a tone; left half red, right half blue
    _ff("-f", "lavfi", "-i", "color=c=red:s=320x360:r=30:d=6", "-f", "lavfi", "-i", "color=c=blue:s=320x360:r=30:d=6",
        "-f", "lavfi", "-i", "sine=f=440:sample_rate=48000:d=6", "-filter_complex", "[0][1]hstack[v]",
        "-map", "[v]", "-map", "2", "-metadata", "comment=GPS 19.07 Pixel", "-metadata", "artist=Secret",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-t", "6", str(land))
    vert = d / "vert.mp4"                  # 360x640, 4 s, no sound
    _ff("-f", "lavfi", "-i", "testsrc=size=360x640:rate=25", "-t", "4", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(vert))
    busy = d / "busy.mp4"                  # noisy picture = a big file to compress
    _ff("-f", "lavfi", "-i", "testsrc2=size=640x360:rate=30", "-f", "lavfi", "-i", "sine=f=300:d=6",
        "-vf", "noise=alls=40:allf=t", "-c:v", "libx264", "-crf", "12", "-pix_fmt", "yuv420p", "-c:a", "aac", "-t", "6", str(busy))
    music = d / "music.mp3"
    _ff("-f", "lavfi", "-i", "sine=f=220:sample_rate=44100", "-t", "3", str(music))
    a, b = d / "a.jpg", d / "b.png"
    Image.new("RGB", (800, 600), (200, 60, 60)).save(a)
    Image.new("RGB", (600, 900), (60, 60, 200)).save(b)
    logo = d / "logo.png"
    Image.new("RGBA", (300, 120), (0, 255, 0, 255)).save(logo)
    srt = d / "c.srt"
    srt.write_text("1\n00:00:00,500 --> 00:00:02,500\nनमस्ते दोस्तों ₹499\n\n2\n00:00:03,000 --> 00:00:05,000\nHello\n",
                   encoding="utf-8")
    return SimpleNamespace(dir=d, busy=str(busy), land=str(land), vert=str(vert), music=str(music), a=str(a), b=str(b), logo=str(logo),
                           srt=str(srt))


def _write(tmp: Path, r: dict, name="o") -> str:
    p = tmp / f"{name}.{r['ext']}"
    p.write_bytes(r["bytes"])
    return str(p)


def _pixel(path: str, t: float, x: int, y: int) -> tuple[int, int, int]:
    f = ops.frames(path, at=[t])["frames"][0]["bytes"]
    from io import BytesIO
    im = Image.open(BytesIO(f)).convert("RGB")
    return im.getpixel((x, y))


def _tags(path: str) -> dict:
    out = subprocess.run(["ffprobe", "-v", "error", "-print_format", "json", "-show_format", path], capture_output=True, text=True)
    return (json.loads(out.stdout).get("format") or {}).get("tags") or {}


# ----------------------------------------------------------------------------- parsing + validation
def test_times_and_aspects_parse_every_way_she_writes_them():
    assert ops.secs("1:30") == 90 and ops.secs("1m30s") == 90 and ops.secs(12.5) == 12.5 and ops.secs("00:01:02") == 62
    assert ops.aspect("reel") == (9, 16) and ops.aspect("16x9") == (16, 9) and ops.aspect("square") == (1, 1)
    for bad in ("abc", "1:0", "50:1"):
        with pytest.raises(ops.VideoError):
            ops.aspect(bad)


def test_steps_refused_before_any_ffmpeg_runs():
    for bad in ([], [{"op": "explode"}], [{"nop": 1}], [{"op": "trim"}] * 20):
        with pytest.raises(ops.VideoError):
            ops.check_steps(bad)
    for evil in ("delogo", "remove_watermark", "face_swap", "deepfake"):
        with pytest.raises(ops.VideoError, match="deepfake"):
            ops.check_steps([{"op": evil}])


def test_info_and_verdict(media):
    p = ops.probe(media.land)
    assert (p["width"], p["height"], p["has_audio"]) == (640, 360, True) and abs(p["duration"] - 6) < 0.1
    assert "9:16" in ops.verdict(p)
    with pytest.raises(ops.VideoError, match="no video"):
        ops.probe(media.music)


# ----------------------------------------------------------------------------- the edit chain
def test_trim_cut_speed_change_the_real_length(media, tmp_path):
    r = ops.edit(media.land, [{"op": "trim", "start": 1, "end": 5}])
    assert abs(r["out"]["duration"] - 4) < 0.15 and r["out"]["has_audio"]
    r = ops.edit(media.land, [{"op": "cut", "start": "0:02", "end": "0:03"}])
    assert abs(r["out"]["duration"] - 5) < 0.15
    r = ops.edit(media.land, [{"op": "speed", "factor": 2}])
    assert abs(r["out"]["duration"] - 3) < 0.15
    r = ops.edit(media.land, [{"op": "speed", "factor": 0.5}, {"op": "trim", "end": 4}])
    assert abs(r["out"]["duration"] - 4) < 0.15 and "slow motion" in r["steps"][0]


def test_reframe_to_reel_keeps_the_whole_picture(media, tmp_path):
    r = ops.edit(media.land, [{"op": "reframe", "aspect": "9:16", "mode": "blur"}])
    o = r["out"]
    assert o["height"] > o["width"] and abs(o["width"] / o["height"] - 9 / 16) < 0.01
    path = _write(tmp_path, r)
    w, h = o["width"], o["height"]
    left, right = _pixel(path, 1, w // 4, h // 2), _pixel(path, 1, 3 * w // 4, h // 2)
    assert left[0] > 150 and right[2] > 150          # red half and blue half both still in the frame (nobody cut off)
    r = ops.edit(media.land, [{"op": "reframe", "aspect": "9:16", "mode": "pad", "color": "white"}])
    top = _pixel(_write(tmp_path, r, "pad"), 1, 10, 10)
    assert min(top) > 220                              # the pad is her white


def test_crop_rotate_flip_resize(media, tmp_path):
    r = ops.edit(media.land, [{"op": "crop", "aspect": "1:1", "position": "left"}])
    o = r["out"]
    assert o["width"] == o["height"] == 360
    assert _pixel(_write(tmp_path, r), 1, 180, 180)[0] > 150    # left crop = the red side
    r = ops.edit(media.land, [{"op": "rotate", "degrees": 90}])
    assert (r["out"]["width"], r["out"]["height"]) == (360, 640)
    r = ops.edit(media.land, [{"op": "flip"}])
    assert _pixel(_write(tmp_path, r, "flip"), 1, 50, 180)[2] > 150   # mirrored: blue now on the left
    r = ops.edit(media.land, [{"op": "resize", "preset": "240p"}])
    assert r["out"]["height"] == 240
    r = ops.edit(media.land, [{"op": "crop", "x": "50%", "y": 0, "w": "50%", "h": "100%"}])
    assert r["out"]["width"] == 320


def test_every_op_runs_on_real_video(media):
    steps = [{"op": "fade", "in": 0.5, "out": 0.5}, {"op": "color", "brightness": 10, "contrast": 10, "saturation": 20},
             {"op": "look", "name": "cinematic"}, {"op": "sharpen"}, {"op": "denoise", "strength": "light"},
             {"op": "stabilize"}, {"op": "blur_area", "x": 10, "y": 10, "w": 100, "h": 60, "start": 1, "end": 3},
             {"op": "text", "text": "दिवाली Sale ₹499", "position": "top", "box": "black"}, {"op": "zoom", "factor": 1.2},
             {"op": "fps", "value": 24}, {"op": "volume", "db": -3}, {"op": "normalize", "target": "social"},
             {"op": "denoise_audio"}]
    r = ops.edit(media.land, steps)
    assert len(r["steps"]) == len(steps) and r["out"]["fps"] == 24 and r["out"]["has_audio"]
    r = ops.edit(media.vert, [{"op": "reverse"}, {"op": "mute"}], "webm")
    assert r["ext"] == "webm" and r["out"]["vcodec"] == "vp9" and not r["out"]["has_audio"]


def test_text_lands_in_the_picture(media, tmp_path):
    r = ops.edit(media.land, [{"op": "text", "text": "SALE", "position": "center", "color": "yellow", "size_pct": 30}])
    path = _write(tmp_path, r)
    im = Image.open(__import__("io").BytesIO(ops.frames(path, at=[1])["frames"][0]["bytes"])).convert("RGB")
    yellow = sum(1 for px in im.getdata() if px[0] > 200 and px[1] > 200 and px[2] < 90)
    assert yellow > 500


def test_watermark_and_blur_area(media, tmp_path):
    r = ops.edit(media.land, [{"op": "watermark", "_path": media.logo, "position": "top-left", "size_pct": 30, "opacity": 100}])
    assert _pixel(_write(tmp_path, r), 1, 40, 25)[1] > 200          # her green logo in the top-left corner
    with pytest.raises(ops.VideoError, match="logo"):
        ops.edit(media.land, [{"op": "watermark"}])
    r = ops.edit(media.land, [{"op": "blur_area", "x": 280, "y": 100, "w": 80, "h": 80}])
    mid = _pixel(_write(tmp_path, r, "blur"), 1, 320, 140)
    assert mid[0] > 60 and mid[2] > 60                               # the red / blue edge is smeared inside the box


def test_audio_steps_on_a_silent_video_say_so(media):
    with pytest.raises(ops.VideoError, match="no sound"):
        ops.edit(media.vert, [{"op": "normalize"}])
    with pytest.raises(ops.VideoError, match="0.25"):
        ops.edit(media.land, [{"op": "speed", "factor": 0.1}])


def test_metadata_never_travels(media, tmp_path):
    assert "Secret" in json.dumps(_tags(media.land))
    path = _write(tmp_path, ops.edit(media.land, [{"op": "trim", "end": 2}]))
    assert "Secret" not in json.dumps(_tags(path)) and "GPS" not in json.dumps(_tags(path))


def test_big_video_is_brought_to_1080p(tmp_path):
    big = tmp_path / "big.mp4"
    _ff("-f", "lavfi", "-i", "color=c=gray:s=2560x1440:r=10:d=1", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(big))
    r = ops.edit(str(big), [{"op": "look", "name": "bw"}])
    assert (r["out"]["width"], r["out"]["height"]) == (1920, 1080)


# ----------------------------------------------------------------------------- whole-file actions
def test_compress_hits_the_target_size(media):
    assert ops.probe(media.busy)["size"] > 1048576
    r = ops.compress(media.busy, 0.5)
    assert len(r["bytes"]) <= 0.5 * 1048576 and r["out"]["has_audio"]
    with pytest.raises(ops.VideoError, match="already"):
        ops.compress(media.land, "whatsapp")
    assert ops.compress(media.land)["target_mb"] is None


def test_join_plain_and_crossfade_lengths(media):
    r = ops.join([media.land, media.vert])
    assert abs(r["out"]["duration"] - 10) < 0.2 and r["out"]["has_audio"] and r["size"] == "640x360"
    r = ops.join([media.land, media.vert, media.land], crossfade=0.5)
    assert abs(r["out"]["duration"] - 15) < 0.3


def test_slideshow_from_photos_with_music(media):
    r = ops.slideshow([media.a, media.b], 2, "9:16", media.music)
    p = __import__("tempfile").NamedTemporaryFile(suffix=".mp4", delete=False)
    p.write(r["bytes"]); p.close()
    o = ops.probe(p.name)
    assert abs(o["duration"] - 4) < 0.2 and o["has_audio"] and (o["width"], o["height"]) == (1080, 1920)
    r = ops.slideshow([media.a], 2, "1:1", None, zoom=False)
    assert r["size"] == "1920x1920" or r["size"].startswith("19")


def test_music_with_ducking_and_on_a_silent_video(media):
    r = ops.add_music(media.land, media.music)
    assert r["ducked"] and abs(r["out"]["duration"] - 6) < 0.15 and r["out"]["has_audio"]
    r = ops.add_music(media.vert, media.music)
    assert not r["original_sound"] and r["out"]["has_audio"]
    with pytest.raises(ops.VideoError, match="no sound"):
        ops.add_music(media.land, media.a)


def test_frames_sheet_gif_split(media):
    f = ops.frames(media.land, at=["0:02", 4])
    assert [x["at"] for x in f["frames"]] == [2, 4] and f["frames"][0]["bytes"][:2] == b"\xff\xd8"
    s = ops.frames(media.land, sheet=True)
    assert len(s["times"]) == 9 and s["sheet"][:2] == b"\xff\xd8"
    g = ops.gif(media.land, 1, 3)
    assert g["bytes"][:6] == b"GIF89a"
    with pytest.raises(ops.VideoError, match="0.3 second"):
        ops.gif(media.land, 3, 3.1)
    parts = ops.split(media.land, every=2)
    assert [(p["from"], p["to"]) for p in parts] == [(0, 2), (2, 4), (4, 6)]
    assert len(ops.split(media.land, at=["1", "5"])) == 3


def test_combine_layouts(media):
    r = ops.combine(media.land, media.vert, "pip")
    assert (r["out"]["width"], r["out"]["height"]) == (640, 360) and abs(r["out"]["duration"] - 6) < 0.15
    r = ops.combine(media.land, media.vert, "side_by_side")
    assert r["out"]["height"] == 360 and r["out"]["width"] > 640
    with pytest.raises(ops.VideoError):
        ops.combine(media.land, media.vert, "grid")


def test_captions_burned_with_hindi_and_srt_returned(media, tmp_path):
    cues = ops.parse_srt(Path(media.srt).read_text(encoding="utf-8"))
    assert len(cues) == 2 and cues[0]["start"] == 0.5
    r = ops.burn_captions(media.land, cues, box=True)
    assert r["cues"] == 2 and "नमस्ते" in r["srt"] and abs(r["out"]["duration"] - 6) < 0.15
    ass = ops.to_ass([{"start": 0, "end": 1, "text": "a {\\b1} b\\N"}], 640, 360)
    assert "{" not in ass.split("Dialogue:")[1] and "PlayResX: 640" in ass
    with pytest.raises(ops.VideoError):
        ops.parse_srt("no timings here")


# ----------------------------------------------------------------------------- the tool
@pytest.fixture
def tool_env(media, monkeypatch):
    files = {"busy": ("busy.mp4", media.busy), "land": ("shop.mp4", media.land), "vert": ("vert.mp4", media.vert), "m": ("song.mp3", media.music),
             "a": ("a.jpg", media.a), "b": ("b.png", media.b), "logo": ("logo.png", media.logo), "srt": ("c.srt", media.srt)}
    out = []
    monkeypatch.setattr(T, "_owner_path", lambda ctx, fid: files[fid] if fid in files else (_ for _ in ()).throw(T.ToolError("nahi mili")))

    def deliver(ctx, name, data):
        out.append((name, data))
        return {"file_id": f"o{len(out)}", "name": name}
    monkeypatch.setattr(T, "_deliver", deliver)
    return SimpleNamespace(ctx=SimpleNamespace(tenant_id="t1", conversation_id="c1", actor="owner"), out=out)


def test_registered_and_reachable_from_real_asks():
    assert "video_kit" in {t["name"] for t in tools.TOOLS} and tools.HANDLERS["video_kit"] is T.video_kit
    assert tools.FAMILY_OF["video_kit"] == "video_kit" and "video_edit" in tools.HANDLERS
    for ask in ("is video ko reel size mein karo", "compress this video for whatsapp", "video mein music daal do",
                "in photos se video bana do slideshow", "video par subtitles laga do", "make a gif from this clip",
                "number plate blur karo video mein", "status ke liye 30 second ke parts"):
        assert "video_kit" in admit._match(ask.lower()), ask


def test_tool_guide_run_batch_and_watermark(tool_env):
    g = run(T.video_kit(tool_env.ctx, "guide"))
    assert g["ffmpeg"] and set(g["ops"]) == ops.STEP_OPS and "NOT done" in g["guide"]
    r = run(T.video_kit(tool_env.ctx, "run", file_ids=["land", "vert"],
                        steps=[{"op": "trim", "end": 2}, {"op": "watermark", "file_id": "logo"}]))
    assert r["edited"] == 2 and [n for n, _ in tool_env.out] == ["shop edited.mp4", "vert edited.mp4"]
    assert r["results"][0]["steps"][1].startswith("her logo")


def test_tool_refuses_bad_steps_and_non_photo_logo_before_touching_files(tool_env):
    with pytest.raises(T.ToolError, match="There is no op"):
        run(T.video_kit(tool_env.ctx, "run", file_ids=["land"], steps=[{"op": "explode"}]))
    with pytest.raises(T.ToolError, match="deepfake"):
        run(T.video_kit(tool_env.ctx, "run", file_ids=["land"], steps=[{"op": "remove_watermark"}]))
    with pytest.raises(T.ToolError, match="photo"):
        run(T.video_kit(tool_env.ctx, "run", file_ids=["land"], steps=[{"op": "watermark", "file_id": "m"}]))
    with pytest.raises(T.ToolError, match="Which video"):
        run(T.video_kit(tool_env.ctx, "run", steps=[{"op": "mute"}]))
    assert tool_env.out == []


def test_one_bad_file_does_not_sink_the_batch(tool_env):
    r = run(T.video_kit(tool_env.ctx, "run", file_ids=["land", "m"], steps=[{"op": "mute"}]))
    assert r["edited"] == 1 and r["results"][1]["ok"] is False


def test_tool_whole_file_actions(tool_env):
    ctx = tool_env.ctx
    assert "9:16" in run(T.video_kit(ctx, "info", file_ids=["land"]))["files"][0]["verdict"]
    assert run(T.video_kit(ctx, "compress", file_ids=["busy"], target_mb="0.5"))["results"][0]["mb"] <= 0.5
    assert run(T.video_kit(ctx, "join", file_ids=["land", "vert"]))["pieces"] == 2
    s = run(T.video_kit(ctx, "slideshow", file_ids=["a", "b"], seconds=1, music_file_id="m"))
    assert s["photos"] == 2 and "right to use" in s["note"]
    with pytest.raises(T.ToolError, match="is not a photo"):
        run(T.video_kit(ctx, "slideshow", file_ids=["land"]))
    m = run(T.video_kit(ctx, "music", file_ids=["land"], music_file_id="m"))
    assert m["ducked"] and "right to use" in m["note"]
    c = run(T.video_kit(ctx, "captions", file_ids=["land"], srt_file_id="srt"))
    assert c["captions"] == 2 and c["srt_file_id"] and tool_env.out[-1][0].endswith(".srt")
    with pytest.raises(T.ToolError, match="Captions from where"):
        run(T.video_kit(ctx, "captions", file_ids=["land"]))
    assert len(run(T.video_kit(ctx, "frames", file_ids=["land"], at=["1", "2"]))["frames"]) == 2
    assert run(T.video_kit(ctx, "frames", file_ids=["land"], sheet=True))["name"].endswith(".jpg")
    assert run(T.video_kit(ctx, "gif", file_ids=["land"], start="1", end="2"))["name"].endswith(".gif")
    assert len(run(T.video_kit(ctx, "split", file_ids=["land"], every="3"))["parts"]) == 2
    assert run(T.video_kit(ctx, "combine", file_ids=["land", "vert"], layout="pip"))["name"] == "shop pip.mp4"
    with pytest.raises(T.ToolError):
        run(T.video_kit(ctx, "nope", file_ids=["land"]))


def test_auto_captions_without_a_speech_engine_say_the_other_way(tool_env, monkeypatch):
    monkeypatch.setattr(ops, "auto_cues", lambda path, lang=None: None)
    with pytest.raises(T.ToolError, match="kaan"):
        run(T.video_kit(tool_env.ctx, "captions", file_ids=["land"], auto=True))


def test_prompt_line():
    p = (Path(__file__).resolve().parent.parent / "app" / "agent" / "prompts.py").read_text()
    assert "EDIT HER VIDEO EXACTLY: video_kit" in p
