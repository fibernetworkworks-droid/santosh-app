"""Audio editing (app/audedit + tool audio_edit): real ffmpeg on generated audio, measured, not mocked."""
import asyncio
import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.agent import admit, audedit_tools as T, tools
from app.audedit import ops

pytestmark = pytest.mark.skipif(not ops.ffmpeg_ok(), reason="ffmpeg not installed")


def run(c):
    return asyncio.run(c)


def _make(path: Path, src: str, secs: float = 6.0) -> str:
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *src.split(), "-t", str(secs), str(path)], check=True)
    return str(path)


@pytest.fixture(scope="module")
def media(tmp_path_factory):
    d = tmp_path_factory.mktemp("aud")
    voice = d / "voice.wav"            # 4 s of tone + hiss, then 2 s of silence
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi", "-i", "sine=f=300:d=4",
                    "-f", "lavfi", "-i", "anoisesrc=d=4:a=0.05", "-filter_complex", "[0][1]amix=2,apad=pad_dur=2",
                    "-t", "6", str(voice)], check=True)
    music = _make(d / "music.mp3", "-f lavfi -i sine=f=600", 3)
    quiet = _make(d / "quiet.wav", "-f lavfi -i sine=f=440 -af volume=0.02", 8)
    video = d / "clip.mp4"
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi", "-i", "color=c=blue:s=160x120:d=3",
                    "-f", "lavfi", "-i", "sine=f=500:d=3", "-shortest", "-c:v", "libx264", "-c:a", "aac", str(video)], check=True)
    silent_video = d / "mute.mp4"
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi", "-i", "color=c=red:s=160x120:d=2",
                    "-c:v", "libx264", str(silent_video)], check=True)
    tagged = d / "tagged.mp3"
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi", "-i", "sine=f=350:d=2",
                    "-metadata", "artist=SecretRecorder", "-metadata", "comment=Pixel 9 GPS 19.07", str(tagged)], check=True)
    return SimpleNamespace(dir=d, voice=str(voice), music=music, quiet=quiet, video=str(video), mute=str(silent_video),
                           tagged=str(tagged))


def _write(tmp: Path, r: dict, name="o") -> str:
    p = tmp / f"{name}.{r['ext']}"
    p.write_bytes(r["bytes"])
    return str(p)


# ----------------------------------------------------------------------------- parsing + validation
def test_times_parse_every_way_she_writes_them():
    assert ops.secs("90") == 90 and ops.secs("1:30") == 90 and ops.secs("1m30s") == 90 and ops.secs("01:02:03") == 3723
    assert ops.secs(2.5) == 2.5
    for bad in ("abc", "-3", "99:99:99:99"):
        with pytest.raises(ops.AudioError):
            ops.secs(bad)


def test_chain_refuses_before_any_ffmpeg_runs():
    for steps, needle in (([], "at least one"), ([{"op": "teleport"}], "not an op"), ([{"op": "trim", "start": 5, "end": 2}], "Nothing is left"),
                          ([{"op": "speed", "factor": 9}], "0.25"), ([{"op": "fade"}], "in or out"),
                          ([{"op": "cut", "start": 0, "end": 10}], "whole audio"), ([{"op": "volume", "db": 99}], "-40"),
                          ([{"op": "denoise", "strength": "max"}], "light"), ([{"op": "trim", "end": 1}] * 13, "12")):
        with pytest.raises(ops.AudioError, match=needle):
            ops.chain(steps, 6.0, 48000)


# ----------------------------------------------------------------------------- real edits, measured
def test_trim_cut_speed_change_the_real_length(media, tmp_path):
    assert abs(ops.probe(_write(tmp_path, ops.edit(media.voice, [{"op": "trim", "start": "0:01", "end": 4}], "wav"), "t"))["duration"] - 3.0) < 0.1
    assert abs(ops.probe(_write(tmp_path, ops.edit(media.voice, [{"op": "cut", "start": 1, "end": 3}], "wav"), "c"))["duration"] - 4.0) < 0.1
    assert abs(ops.probe(_write(tmp_path, ops.edit(media.voice, [{"op": "speed", "factor": 2}], "wav"), "s"))["duration"] - 3.0) < 0.15


def test_normalize_really_lands_on_the_target_loudness(media, tmp_path):
    before = ops.loudness(media.quiet)
    assert before["lufs"] < -24 and before["verdict"] == "very quiet"
    out = _write(tmp_path, ops.edit(media.quiet, [{"op": "normalize", "target": "podcast"}], "wav"), "n")
    after = ops.loudness(out)
    assert abs(after["lufs"] - (-16)) < 1.5, after
    assert ops.probe(out)["sample_rate"] == before["sample_rate"]          # loudnorm's 192 kHz never leaks into the file


def test_remove_silence_shortens_the_long_pause(media, tmp_path):
    out = _write(tmp_path, ops.edit(media.voice, [{"op": "remove_silence", "min_silence": 0.5}], "wav"), "rs")
    assert ops.probe(out)["duration"] < 5.0                               # the 2 s tail of silence is gone


def test_volume_and_mono(media, tmp_path):
    loud = ops.loudness(_write(tmp_path, ops.edit(media.quiet, [{"op": "volume", "db": 12}], "wav"), "v"))
    assert loud["lufs"] - ops.loudness(media.quiet)["lufs"] > 10
    stereo = _write(tmp_path, ops.edit(media.voice, [{"op": "stereo"}], "wav"), "st")
    assert ops.probe(stereo)["channels"] == 2
    assert ops.probe(_write(tmp_path, ops.edit(stereo, [{"op": "mono"}], "wav"), "mo"))["channels"] == 1


def test_every_op_runs_on_real_audio(media, tmp_path):
    steps = [{"op": "trim", "start": 0, "end": 5}, {"op": "denoise", "strength": "strong"}, {"op": "pitch", "semitones": -3},
             {"op": "eq", "bass": 4, "treble": -2}, {"op": "fade", "in": 0.5, "out": 0.5}, {"op": "enhance_voice"},
             {"op": "sample_rate", "hz": 22050}, {"op": "reverse"}]
    r = ops.edit(media.voice, steps, "m4a")
    p = ops.probe(_write(tmp_path, r, "all"))
    assert p["sample_rate"] == 22050 and len(r["steps"]) == len(steps)
    for f in ops.FORMATS:
        assert ops.probe(_write(tmp_path, ops.convert(media.voice, f), f"f_{f}"))["duration"] > 5.5


def test_metadata_never_travels(media, tmp_path):
    raw = Path(media.tagged).read_bytes()
    assert b"SecretRecorder" in raw
    out = ops.edit(media.tagged, [{"op": "volume", "percent": 100}], "mp3")["bytes"]
    assert b"SecretRecorder" not in out and b"Pixel 9" not in out


def test_video_gives_its_sound_and_silent_video_is_refused(media, tmp_path):
    r = ops.convert(media.video, "mp3")
    assert r["in"]["from_video"] and ops.probe(_write(tmp_path, r, "fromvid"))["duration"] > 2.5
    with pytest.raises(ops.AudioError, match="no audio"):
        ops.probe(media.mute)
    bad = tmp_path / "x.mp3"
    bad.write_bytes(b"not audio at all")
    with pytest.raises(ops.AudioError):
        ops.probe(str(bad))


def test_join_crossfade_and_gap_lengths(media, tmp_path):
    cf = ops.probe(_write(tmp_path, ops.join([media.voice, media.music], crossfade=1), "j1"))["duration"]
    gap = ops.probe(_write(tmp_path, ops.join([media.voice, media.music], gap=1), "j2"))["duration"]
    plain = ops.probe(_write(tmp_path, ops.join([media.voice, media.music]), "j3"))["duration"]
    assert abs(plain - 9) < 0.2 and abs(cf - 8) < 0.2 and abs(gap - 10) < 0.2
    with pytest.raises(ops.AudioError):
        ops.join([media.voice])
    with pytest.raises(ops.AudioError):
        ops.join([media.voice, media.music], crossfade=1, gap=1)


def test_mix_follows_the_voice_and_loops_short_music(media, tmp_path):
    r = ops.mix(media.voice, media.music, music_db=-20)
    assert r["music_looped"] is True
    assert abs(ops.probe(_write(tmp_path, r, "mix"))["duration"] - 6.0) < 0.2


def test_split_every_and_at(media):
    parts = ops.split(media.voice, every=2)
    assert [(p["from"], p["to"]) for p in parts] == [(0.0, 2.0), (2.0, 4.0), (4.0, 6.0)]
    parts = ops.split(media.voice, at=["0:01", "4"])
    assert [(p["from"], p["to"]) for p in parts] == [(0.0, 1.0), (1.0, 4.0), (4.0, 6.0)]
    with pytest.raises(ops.AudioError):
        ops.split(media.voice)
    with pytest.raises(ops.AudioError, match="1 second"):
        ops.split(media.quiet, every=0.4)
    with pytest.raises(ops.AudioError, match="20"):
        ops.split(media.quiet, at=[round(0.3 * k, 1) for k in range(1, 26)])


def test_loudness_report_and_waveform(media):
    rep = ops.loudness(media.voice)
    assert rep["lufs"] is not None and rep["duration"] == 6.0 and rep["clipping_risk"] is False
    png = ops.waveform(media.voice)
    assert png[:8] == b"\x89PNG\r\n\x1a\n"
    with pytest.raises(ops.AudioError):
        ops.waveform(media.voice, color="red; rm -rf /")


# ----------------------------------------------------------------------------- the tool
@pytest.fixture
def tool_env(media, monkeypatch):
    files = {"v": ("voice.wav", media.voice), "m": ("music.mp3", media.music), "vid": ("clip.mp4", media.video),
             "mute": ("mute.mp4", media.mute)}
    out = []
    monkeypatch.setattr(T, "_owner_path", lambda ctx, fid: files[fid] if fid in files else (_ for _ in ()).throw(T.ToolError("nahi mili")))

    def deliver(ctx, name, data):
        out.append((name, data))
        return {"file_id": f"o{len(out)}", "name": name}
    monkeypatch.setattr(T, "_deliver", deliver)
    return SimpleNamespace(ctx=SimpleNamespace(tenant_id="t1", conversation_id="c1", actor="owner"), out=out)


def test_registered_and_reachable_from_real_asks():
    assert "audio_edit" in {t["name"] for t in tools.TOOLS} and tools.HANDLERS["audio_edit"] is T.audio_edit
    assert tools.FAMILY_OF["audio_edit"] == "audio_edit"
    for ask in ("is voice note ka background noise hata do", "make a 30 second ringtone from this song",
                "podcast recording saaf karo", "video se audio nikalo mp3 mein", "merge audio files into one",
                "add background music under my voice"):
        assert "audio_edit" in admit._match(ask.lower()), ask


def test_tool_guide_run_and_batch(tool_env):
    g = run(T.audio_edit(tool_env.ctx, "guide"))
    assert g["ffmpeg"] and set(g["ops"]) == ops.STEP_OPS and "NOT done here" in g["guide"]
    r = run(T.audio_edit(tool_env.ctx, "run", file_ids=["v", "vid"], steps=[{"op": "normalize", "target": "social"}], format="mp3"))
    assert r["edited"] == 2 and r["results"][1]["note"] == "video ki awaaz nikali gayi"
    assert [n for n, _ in tool_env.out] == ["voice edited.mp3", "clip edited.mp3"]


def test_tool_refuses_bad_steps_before_touching_files(tool_env):
    with pytest.raises(T.ToolError, match="not an op"):
        run(T.audio_edit(tool_env.ctx, "run", file_ids=["v"], steps=[{"op": "vocal_remove"}]))
    assert tool_env.out == []
    with pytest.raises(T.ToolError, match="Kaunsa audio"):
        run(T.audio_edit(tool_env.ctx, "run", steps=[{"op": "mono"}]))


def test_one_bad_file_does_not_sink_the_batch(tool_env):
    r = run(T.audio_edit(tool_env.ctx, "run", file_ids=["v", "mute"], steps=[{"op": "mono"}]))
    assert r["edited"] == 1 and r["results"][1]["ok"] is False


def test_tool_info_join_mix_split_waveform(tool_env):
    info = run(T.audio_edit(tool_env.ctx, "info", file_ids=["v"]))
    assert info["files"][0]["lufs"] is not None
    assert run(T.audio_edit(tool_env.ctx, "join", file_ids=["v", "m"], crossfade=1))["pieces"] == 2
    mx = run(T.audio_edit(tool_env.ctx, "mix", file_ids=["v", "m"]))
    assert mx["music_looped"] is True and "haq" in mx["note"]
    assert len(run(T.audio_edit(tool_env.ctx, "split", file_ids=["v"], every="2"))["parts"]) == 3
    assert run(T.audio_edit(tool_env.ctx, "waveform", file_ids=["v"]))["name"].endswith(".png")
    with pytest.raises(T.ToolError):
        run(T.audio_edit(tool_env.ctx, "mix", file_ids=["v"]))
    with pytest.raises(T.ToolError):
        run(T.audio_edit(tool_env.ctx, "nope", file_ids=["v"]))


def test_prompt_line():
    p = (Path(__file__).resolve().parent.parent / "app" / "agent" / "prompts.py").read_text()
    assert "EDIT HER AUDIO: audio_edit" in p
