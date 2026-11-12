"""ffmpeg-backed audio operations. Steps are validated in Python, turned into one filter chain, run by ffmpeg."""
from __future__ import annotations

import json
import math
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

MAX_BYTES = 200 * 1024 * 1024
MAX_SECONDS = 2 * 60 * 60          # 2 hours of audio per input
MAX_STEPS = 12
FORMATS = {"mp3": ("libmp3lame", "mp3"), "wav": ("pcm_s16le", "wav"), "m4a": ("aac", "ipod"),
           "ogg": ("libvorbis", "ogg"), "opus": ("libopus", "ogg"), "flac": ("flac", "flac")}
LOUDNESS = {"podcast": -16.0, "social": -14.0, "music": -14.0, "audiobook": -19.0, "broadcast": -23.0, "voice_note": -16.0}


class AudioError(ValueError):
    """A request Hoola can explain in one plain sentence."""


def ffmpeg_ok() -> bool:
    return bool(shutil.which("ffmpeg") and shutil.which("ffprobe"))


def _num(v: Any, name: str, lo: float, hi: float, default: float | None = None) -> float:
    if v is None or v == "":
        if default is None:
            raise AudioError(f"{name} is needed.")
        return default
    try:
        x = float(v)
    except (TypeError, ValueError):
        raise AudioError(f"{name} must be a number.") from None
    if math.isnan(x) or x < lo or x > hi:
        raise AudioError(f"Keep {name} between {lo:g} and {hi:g}.")
    return x


def secs(v: Any, name: str = "time") -> float:
    """'90', '1:30', '01:02:03', '1m30s', 90.5 -> seconds."""
    if isinstance(v, (int, float)):
        x = float(v)
    else:
        s = str(v or "").strip().lower()
        if not s:
            raise AudioError(f"{name} is needed (for example 1:30 or 90).")
        m = re.fullmatch(r"(?:(\d+)h)?\s*(?:(\d+)m)?\s*(?:(\d+(?:\.\d+)?)s)?", s)
        if m and any(m.groups()):
            x = int(m.group(1) or 0) * 3600 + int(m.group(2) or 0) * 60 + float(m.group(3) or 0)
        elif re.fullmatch(r"\d+(?::\d{1,2}){0,2}(?:\.\d+)?", s):
            x = 0.0
            for part in s.split(":"):
                x = x * 60 + float(part)
        else:
            try:
                x = float(s)
            except ValueError:
                raise AudioError(f"{name} '{v}' not understood (for example 1:30, 90 or 1m30s).") from None
    if x < 0 or x > MAX_SECONDS:
        raise AudioError(f"Keep {name} between 0 and {MAX_SECONDS // 3600} hours.")
    return round(x, 3)


# --------------------------------------------------------------------------- probe
def probe(path: str) -> dict[str, Any]:
    if not ffmpeg_ok():
        raise AudioError("ffmpeg is not on the server; the audio cannot be edited.")
    size = os.path.getsize(path)
    if size > MAX_BYTES:
        raise AudioError(f"The file is too big ({size // 1048576} MB); the limit is {MAX_BYTES // 1048576} MB.")
    try:
        out = subprocess.run(["ffprobe", "-v", "error", "-print_format", "json", "-show_streams", "-show_format", path],
                             capture_output=True, text=True, timeout=60)
        j = json.loads(out.stdout or "{}")
    except Exception:
        raise AudioError("The file could not be read.") from None
    streams = [s for s in j.get("streams") or [] if s.get("codec_type") == "audio"]
    if not streams:
        raise AudioError("This file has no audio; send an MP3 / WAV / M4A / OGG or a video with sound.")
    a = streams[0]
    dur = float((j.get("format") or {}).get("duration") or a.get("duration") or 0)
    if dur <= 0:
        raise AudioError("The length of the audio was not found; the file looks damaged.")
    if dur > MAX_SECONDS:
        raise AudioError(f"The audio is {dur / 3600:.1f} hours long; the limit is {MAX_SECONDS // 3600} hours.")
    has_video = any(s.get("codec_type") == "video" and not (s.get("disposition") or {}).get("attached_pic")
                    for s in j.get("streams") or [])
    return {"duration": round(dur, 3), "sample_rate": int(a.get("sample_rate") or 0), "channels": int(a.get("channels") or 0),
            "codec": a.get("codec_name"), "bit_rate": int((j.get("format") or {}).get("bit_rate") or 0),
            "size": size, "from_video": has_video}


# --------------------------------------------------------------------------- one step -> filters
def _atempo(f: float) -> list[str]:
    out = []
    while f > 2.0:
        out.append("atempo=2.0"); f /= 2.0
    while f < 0.5:
        out.append("atempo=0.5"); f /= 0.5
    out.append(f"atempo={f:.6f}")
    return out


def _rubberband() -> bool:
    try:
        r = subprocess.run(["ffmpeg", "-hide_banner", "-filters"], capture_output=True, text=True, timeout=20)
        return " rubberband " in r.stdout
    except Exception:
        return False


def step_filters(st: dict, dur: float, sr: int) -> tuple[list[str], float, str]:
    """Filters for one step, the duration after it, and a one-line description."""
    op = str(st.get("op") or "").lower()
    if op == "trim":
        a = secs(st.get("start", 0), "start")
        b = secs(st["end"], "end") if st.get("end") not in (None, "") else dur
        b = min(b, dur)
        if b - a < 0.05:
            raise AudioError("Nothing is left after the trim (start must be before end).")
        return [f"atrim=start={a}:end={b}", "asetpts=PTS-STARTPTS"], b - a, f"kept {a:g}s-{b:g}s"
    if op == "cut":
        a, b = secs(st.get("start"), "start"), secs(st.get("end"), "end")
        b = min(b, dur)
        if b <= a:
            raise AudioError("The end of the cut must be after its start.")
        if a <= 0 and b >= dur:
            raise AudioError("Cutting the whole audio leaves nothing.")
        return [f"aselect='not(between(t,{a},{b}))'", "asetpts=N/SR/TB"], dur - (b - a), f"removed {a:g}s-{b:g}s"
    if op == "fade":
        fi = _num(st.get("in"), "in", 0, 60, 0)
        fo = _num(st.get("out"), "out", 0, 60, 0)
        if not fi and not fo:
            raise AudioError("For fade, give the in or out seconds.")
        if fi + fo > dur:
            raise AudioError("The fade is longer than the audio.")
        f = []
        if fi:
            f.append(f"afade=t=in:st=0:d={fi}")
        if fo:
            f.append(f"afade=t=out:st={max(0.0, dur - fo):.3f}:d={fo}")
        return f, dur, f"fade in {fi:g}s / out {fo:g}s"
    if op == "volume":
        if st.get("db") not in (None, ""):
            db = _num(st.get("db"), "db", -40, 30)
            return [f"volume={db}dB"], dur, f"volume {db:+g} dB"
        pct = _num(st.get("percent"), "percent", 1, 1000)
        return [f"volume={pct / 100:.4f}"], dur, f"volume {pct:g}%"
    if op == "normalize":
        target = st.get("target", "podcast")
        lufs = LOUDNESS.get(str(target).lower()) if not isinstance(target, (int, float)) else None
        if lufs is None:
            lufs = _num(target, "target", -40, -5)
        return [f"loudnorm=I={lufs}:TP=-1.5:LRA=11"], dur, f"loudness {lufs:g} LUFS"
    if op == "speed":
        f = _num(st.get("factor"), "factor", 0.25, 4)
        return _atempo(f), dur / f, f"speed x{f:g} (pitch kept)"
    if op == "pitch":
        s = _num(st.get("semitones"), "semitones", -12, 12)
        ratio = 2 ** (s / 12)
        if _rubberband():
            return [f"rubberband=pitch={ratio:.6f}"], dur, f"pitch {s:+g} semitones"
        rate = sr or 44100
        return [f"asetrate={int(rate * ratio)}", f"aresample={rate}", *_atempo(1 / ratio)], dur, f"pitch {s:+g} semitones"
    if op == "denoise":
        lvl = str(st.get("strength", "medium")).lower()
        nr = {"light": 8, "medium": 14, "strong": 22}.get(lvl)
        if nr is None:
            raise AudioError("strength: light, medium or strong.")
        return ["highpass=f=60", f"afftdn=nr={nr}:nf=-35"], dur, f"noise reduced ({lvl})"
    if op == "enhance_voice":
        return ["highpass=f=80", "lowpass=f=12000", "afftdn=nr=12:nf=-35",
                "acompressor=threshold=-20dB:ratio=3:attack=5:release=120",
                "equalizer=f=3000:t=q:w=1.2:g=3", "loudnorm=I=-16:TP=-1.5:LRA=11"], dur, "voice cleaned + levelled"
    if op == "remove_silence":
        gap = _num(st.get("min_silence"), "min_silence", 0.2, 10, 0.7)
        th = _num(st.get("threshold_db"), "threshold_db", -80, -10, -40)
        keep = _num(st.get("keep"), "keep", 0, 2, 0.25)
        return [f"silenceremove=start_periods=1:start_threshold={th}dB:start_silence={keep}:"
                f"stop_periods=-1:stop_duration={gap}:stop_threshold={th}dB:stop_silence={keep}"], dur, \
            f"pauses over {gap:g}s shortened"
    if op == "eq":
        bass = _num(st.get("bass"), "bass", -20, 20, 0)
        treble = _num(st.get("treble"), "treble", -20, 20, 0)
        if not bass and not treble:
            raise AudioError("For eq, give bass or treble (dB).")
        f = ([f"bass=g={bass}"] if bass else []) + ([f"treble=g={treble}"] if treble else [])
        return f, dur, f"bass {bass:+g} dB, treble {treble:+g} dB"
    if op == "mono":
        return ["aformat=channel_layouts=mono"], dur, "mono"
    if op == "stereo":
        return ["aformat=channel_layouts=stereo"], dur, "stereo"
    if op == "sample_rate":
        hz = int(_num(st.get("hz"), "hz", 8000, 96000))
        return [f"aresample={hz}"], dur, f"{hz} Hz"
    if op == "reverse":
        if dur > 600:
            raise AudioError("Reverse works only on audio up to 10 minutes.")
        return ["areverse"], dur, "reversed"
    raise AudioError(f"'{op}' is not an op. Ops: " + ", ".join(sorted(STEP_OPS)))


STEP_OPS = {"trim", "cut", "fade", "volume", "normalize", "speed", "pitch", "denoise", "enhance_voice", "remove_silence",
            "eq", "mono", "stereo", "sample_rate", "reverse"}


def chain(steps: list[dict], dur: float, sr: int) -> tuple[str, float, list[str]]:
    if not isinstance(steps, list) or not steps:
        raise AudioError("Which changes should be made? Write at least one op in steps (see the guide).")
    if len(steps) > MAX_STEPS:
        raise AudioError(f"At most {MAX_STEPS} steps at a time.")
    filters, notes = [], []
    for i, st in enumerate(steps, 1):
        if not isinstance(st, dict) or not st.get("op"):
            raise AudioError(f"Step {i} needs an 'op' name.")
        if str(st["op"]).lower() not in STEP_OPS:
            raise AudioError(f"Step {i}: '{st['op']}' is not an op. Ops: " + ", ".join(sorted(STEP_OPS)))
        try:
            f, dur, note = step_filters(st, dur, sr)
        except AudioError as e:
            raise AudioError(f"Step {i} ({st['op']}): {e}") from None
        filters += [x for x in f if x]
        notes.append(note)
    if any(x.startswith("loudnorm") for x in filters) and not any(str(s.get("op")).lower() == "sample_rate" for s in steps):
        filters.append(f"aresample={sr or 48000}")   # loudnorm works at 192 kHz inside; give the file its own rate back
    return ",".join(filters), dur, notes


# --------------------------------------------------------------------------- running ffmpeg
def _enc_args(fmt: str, bitrate: str | int | None) -> tuple[list[str], str]:
    f = (fmt or "mp3").lower().lstrip(".")
    if f not in FORMATS:
        raise AudioError("Format: " + ", ".join(FORMATS))
    codec, mux = FORMATS[f]
    args = ["-c:a", codec, "-f", mux]
    if f in ("mp3", "m4a", "ogg", "opus"):
        kb = int(_num(str(bitrate or "").lower().rstrip("k") or None, "bitrate", 32, 320,
                      {"mp3": 192, "m4a": 160, "ogg": 160, "opus": 96}[f]))
        args += ["-b:a", f"{kb}k"]
    return args, f


def ffmpeg(args: list[str], timeout: float) -> None:
    cmd = ["ffmpeg", "-hide_banner", "-nostdin", "-loglevel", "error", "-y", *args]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        raise AudioError("Making the audio took too long (time limit); send a shorter part.") from None
    if r.returncode != 0:
        last = (r.stderr or "").strip().splitlines()[-1:] or ["unknown"]
        raise AudioError("ffmpeg refused: " + last[0][:200])


def _timeout(seconds: float) -> float:
    return max(60.0, min(900.0, 60 + seconds * 0.5))


def edit(src: str, steps: list[dict], fmt: str = "mp3", bitrate=None) -> dict[str, Any]:
    info = probe(src)
    filt, new_dur, notes = chain(steps, info["duration"], info["sample_rate"])
    enc, f = _enc_args(fmt, bitrate)
    with tempfile.TemporaryDirectory(prefix="audedit_") as td:
        out = Path(td) / f"out.{f}"
        ffmpeg(["-i", src, "-vn", "-map_metadata", "-1", "-af", filt, *enc, str(out)], _timeout(info["duration"]))
        data = out.read_bytes()
    if len(data) < 64:
        raise AudioError("No audio is left (silence removal / trim took everything).")
    return {"bytes": data, "ext": f, "steps": notes, "in": info, "est_seconds": round(new_dur, 2)}


def convert(src: str, fmt: str = "mp3", bitrate=None) -> dict[str, Any]:
    info = probe(src)
    enc, f = _enc_args(fmt, bitrate)
    with tempfile.TemporaryDirectory(prefix="audedit_") as td:
        out = Path(td) / f"out.{f}"
        ffmpeg(["-i", src, "-vn", "-map_metadata", "-1", *enc, str(out)], _timeout(info["duration"]))
        return {"bytes": out.read_bytes(), "ext": f, "in": info}


def join(srcs: list[str], crossfade: float = 0.0, gap: float = 0.0, fmt: str = "mp3", bitrate=None) -> dict[str, Any]:
    if not 2 <= len(srcs) <= 20:
        raise AudioError("Joining needs 2 to 20 audio files.")
    infos = [probe(s) for s in srcs]
    total = sum(i["duration"] for i in infos)
    if total > MAX_SECONDS:
        raise AudioError("Together it would be longer than 2 hours.")
    cf = _num(crossfade, "crossfade", 0, 10, 0)
    gp = _num(gap, "gap", 0, 10, 0)
    if cf and gp:
        raise AudioError("crossfade and gap cannot be used together; choose one.")
    if cf and min(i["duration"] for i in infos) <= cf * 2:
        raise AudioError("One audio is shorter than the crossfade.")
    enc, f = _enc_args(fmt, bitrate)
    inputs = []
    for s in srcs:
        inputs += ["-i", s]
    norm = "".join(f"[{i}:a]aformat=sample_rates=44100:channel_layouts=stereo[a{i}];" for i in range(len(srcs)))
    if cf:
        g, prev = norm, "a0"
        for i in range(1, len(srcs)):
            nxt = f"x{i}"
            g += f"[{prev}][a{i}]acrossfade=d={cf}:c1=tri:c2=tri[{nxt}];"
            prev = nxt
        graph, last = g.rstrip(";"), prev
    else:
        parts = ""
        n = len(srcs)
        if gp:
            pads = "".join(f"[a{i}]apad=pad_dur={gp}[p{i}];" for i in range(n - 1))
            labels = "".join(f"[p{i}]" for i in range(n - 1)) + f"[a{n - 1}]"
            parts = pads
        else:
            labels = "".join(f"[a{i}]" for i in range(n))
        graph = norm + parts + f"{labels}concat=n={n}:v=0:a=1[out]"
        last = "out"
    with tempfile.TemporaryDirectory(prefix="audedit_") as td:
        out = Path(td) / f"out.{f}"
        ffmpeg([*inputs, "-filter_complex", graph, "-map", f"[{last}]", "-map_metadata", "-1", *enc, str(out)], _timeout(total))
        return {"bytes": out.read_bytes(), "ext": f, "pieces": len(srcs),
                "est_seconds": round(total - cf * (len(srcs) - 1) + gp * (len(srcs) - 1), 2)}


def mix(voice: str, music: str, music_db: float = -18.0, duck: bool = True, fade_out: float = 3.0,
        fmt: str = "mp3", bitrate=None) -> dict[str, Any]:
    """Voice over background music: music looped to the voice's length, quieter, ducked under speech, faded at the end."""
    vi, mi = probe(voice), probe(music)
    mdb = _num(music_db, "music_db", -40, 0, -18)
    fo = _num(fade_out, "fade_out", 0, 15, 3)
    d = vi["duration"]
    enc, f = _enc_args(fmt, bitrate)
    m = (f"[1:a]aformat=sample_rates=44100:channel_layouts=stereo,volume={mdb}dB,atrim=0:{d},asetpts=PTS-STARTPTS"
         + (f",afade=t=out:st={max(0.0, d - fo):.3f}:d={fo}" if fo else "") + "[m];")
    v = "[0:a]aformat=sample_rates=44100:channel_layouts=stereo[v];"
    if duck:
        graph = v + m + "[v]asplit=2[v1][vk];[m][vk]sidechaincompress=threshold=0.03:ratio=8:attack=20:release=400[md];" \
                        "[v1][md]amix=inputs=2:duration=first:normalize=0[out]"
    else:
        graph = v + m + "[v][m]amix=inputs=2:duration=first:normalize=0[out]"
    with tempfile.TemporaryDirectory(prefix="audedit_") as td:
        out = Path(td) / f"out.{f}"
        ffmpeg(["-i", voice, "-stream_loop", "-1", "-i", music, "-filter_complex", graph, "-map", "[out]",
                "-t", f"{d:.3f}", "-map_metadata", "-1", *enc, str(out)], _timeout(d))
        return {"bytes": out.read_bytes(), "ext": f, "est_seconds": d, "music_looped": mi["duration"] < d}


def split(src: str, every: Any = None, at: list | None = None, fmt: str = "mp3", bitrate=None) -> list[dict[str, Any]]:
    info = probe(src)
    d = info["duration"]
    if at:
        cuts = sorted({secs(x, "at") for x in at if 0 < secs(x, "at") < d})
    elif every not in (None, ""):
        step = secs(every, "every")
        if step < 1:
            raise AudioError("Each part must be at least 1 second long.")
        cuts = [round(step * k, 3) for k in range(1, int(d // step) + 1) if step * k < d - 0.05]
    else:
        raise AudioError("For split, give every (how many seconds each) or at (which points).")
    edges = [0.0, *cuts, d]
    if len(edges) - 1 > 20:
        raise AudioError("At most 20 parts; use a bigger 'every'.")
    out = []
    enc, f = _enc_args(fmt, bitrate)
    with tempfile.TemporaryDirectory(prefix="audedit_") as td:
        for i in range(len(edges) - 1):
            p = Path(td) / f"p{i}.{f}"
            ffmpeg(["-i", src, "-vn", "-map_metadata", "-1", "-af",
                    f"atrim=start={edges[i]}:end={edges[i + 1]},asetpts=PTS-STARTPTS", *enc, str(p)], _timeout(d))
            out.append({"bytes": p.read_bytes(), "ext": f, "from": edges[i], "to": edges[i + 1]})
    return out


def loudness(src: str) -> dict[str, Any]:
    """Integrated loudness, true peak and range as ffmpeg's loudnorm measures them."""
    info = probe(src)
    cmd = ["ffmpeg", "-hide_banner", "-nostdin", "-i", src, "-vn", "-af", "loudnorm=print_format=json", "-f", "null", "-"]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=_timeout(info["duration"]))
        blob = r.stderr[r.stderr.rfind("{"):r.stderr.rfind("}") + 1]
        j = json.loads(blob)
        lufs, tp, lra = float(j["input_i"]), float(j["input_tp"]), float(j["input_lra"])
    except Exception:
        raise AudioError("The loudness could not be measured.") from None
    tip = ("very quiet" if lufs < -24 else "fine for a podcast / social media" if -18 <= lufs <= -13
           else "a little loud" if lufs > -13 else "a little quiet")
    return {**info, "lufs": round(lufs, 1) if math.isfinite(lufs) else None, "true_peak_db": round(tp, 1) if math.isfinite(tp) else None,
            "loudness_range": round(lra, 1) if math.isfinite(lra) else None, "verdict": tip,
            "clipping_risk": bool(math.isfinite(tp) and tp > -1.0)}


def waveform(src: str, width: int = 1600, height: int = 300, color: str = "#7C5CFF") -> bytes:
    info = probe(src)
    w = int(_num(width, "width", 300, 4000, 1600)); h = int(_num(height, "height", 80, 1200, 300))
    if not re.fullmatch(r"#?[0-9a-fA-F]{6}", str(color)):
        raise AudioError("Write the colour like #RRGGBB.")
    c = "0x" + str(color).lstrip("#")
    with tempfile.TemporaryDirectory(prefix="audedit_") as td:
        out = Path(td) / "wave.png"
        ffmpeg(["-i", src, "-filter_complex", f"aformat=channel_layouts=mono,showwavespic=s={w}x{h}:colors={c}",
                "-frames:v", "1", str(out)], _timeout(info["duration"]))
        return out.read_bytes()
