"""Ready-made edits built on the timeline engine. Every edit returns a verified RenderReport."""
from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any

from .core import (AR, FFMPEG, RenderReport, VeditError, parse_time, probe, render, run, to_fps)



def _out(output: dict | None, src: str | None = None) -> dict:
    return dict(output or {})  # "aspect" is handled by the timeline loader (standard 1080-based sizes)


def _single(src: str, out: str, clip: dict | None = None, output: dict | None = None, **extra) -> RenderReport:
    tl = {"output": _out(output), "clips": [{"src": str(src), **(clip or {})}], **extra}
    return render(tl, out)


# ----------------------------------------------------------------------------- analysis
def info(src: str) -> dict:
    return probe(src, count_frames=True).as_dict()


def detect_silence(src: str, noise_db: float = -35.0, min_silence: float = 0.4) -> list[tuple[float, float]]:
    """Silent stretches as (start, end) seconds."""
    i = probe(src)
    if not i.has_audio:
        raise VeditError("This file has no audio, so silence cannot be detected")
    p = run([FFMPEG, "-hide_banner", "-nostdin", "-i", src, "-vn", "-af",
             f"silencedetect=noise={noise_db}dB:d={min_silence}", "-f", "null", "-"])
    out, start = [], None
    for line in p.stderr.splitlines():
        m = re.search(r"silence_start: (-?[\d.]+)", line)
        if m:
            start = max(0.0, float(m.group(1)))
        m = re.search(r"silence_end: ([\d.]+)", line)
        if m and start is not None:
            out.append((round(start, 3), round(float(m.group(1)), 3)))
            start = None
    if start is not None:
        out.append((round(start, 3), round(i.duration, 3)))
    return out


def speech_ranges(src: str, noise_db: float = -35.0, min_silence: float = 0.4, pad: float = 0.12,
                  min_keep: float = 0.25) -> list[tuple[float, float]]:
    """The parts worth keeping: everything that is not silence, padded so words are not clipped."""
    dur = probe(src).duration
    sil = detect_silence(src, noise_db, min_silence)
    keep, cur = [], 0.0
    for s, e in sil:
        if s > cur:
            keep.append([cur, s])
        cur = e
    if cur < dur:
        keep.append([cur, dur])
    padded = []
    for s, e in keep:
        s, e = max(0.0, s - pad), min(dur, e + pad)
        if padded and s <= padded[-1][1]:
            padded[-1][1] = max(padded[-1][1], e)
        else:
            padded.append([s, e])
    return [(round(s, 3), round(e, 3)) for s, e in padded if e - s >= min_keep]


def detect_scenes(src: str, threshold: float = 10.0) -> list[float]:
    """Times (s) where the picture changes shot. threshold 0-100: lower finds more cuts."""
    p = run([FFMPEG, "-hide_banner", "-nostdin", "-i", src, "-an", "-vf", f"scdet=threshold={threshold}:sc_pass=1",
             "-f", "null", "-"])
    times = [float(m) for m in re.findall(r"lavfi\.scd\.time:\s*([\d.]+)", p.stderr)]
    return sorted(set(round(t, 3) for t in times))


# ----------------------------------------------------------------------------- edits
def trim(src: str, out: str, start: Any = 0, end: Any = None, output: dict | None = None) -> RenderReport:
    clip = {"in": start}
    if end is not None:
        clip["out"] = end
    return _single(src, out, clip, output)


def keep_ranges(src: str, out: str, ranges: list, output: dict | None = None,
                transition: str | None = None, transition_duration: float = 0.25) -> RenderReport:
    """Keep only these (start, end) ranges, in order, joined together."""
    if not ranges:
        raise VeditError("Nothing to keep")
    clips = []
    for k, (s, e) in enumerate(ranges):
        c = {"src": src, "in": s, "out": e}
        if transition and k < len(ranges) - 1:
            c["transition"] = {"type": transition, "duration": transition_duration}
        clips.append(c)
    return render({"output": _out(output), "clips": clips}, out)


def cut_out(src: str, out: str, remove: list, output: dict | None = None) -> RenderReport:
    """Remove these (start, end) ranges and join what is left."""
    dur = probe(src).duration
    rem = sorted((parse_time(s), parse_time(e)) for s, e in remove)
    keep, cur = [], 0.0
    for s, e in rem:
        if s > cur:
            keep.append((cur, s))
        cur = max(cur, e)
    if cur < dur:
        keep.append((cur, dur))
    keep = [(s, e) for s, e in keep if e - s > 0.05]
    return keep_ranges(src, out, keep, output)


def remove_silence(src: str, out: str, noise_db: float = -35.0, min_silence: float = 0.4, pad: float = 0.12,
                   output: dict | None = None) -> tuple[RenderReport, dict]:
    """Jump-cut: drop pauses. Returns the report and a summary of what was removed."""
    dur = probe(src).duration
    keep = speech_ranges(src, noise_db, min_silence, pad)
    if not keep:
        raise VeditError("Everything is below the silence threshold; try a lower noise_db such as -45")
    rep = keep_ranges(src, out, keep, output)
    kept = sum(e - s for s, e in keep)
    return rep, {"original_s": round(dur, 2), "kept_s": round(kept, 2), "removed_s": round(dur - kept, 2),
                 "segments": len(keep), "ranges": keep}


def split_scenes(src: str, out_dir: str, threshold: float = 10.0, min_len: float = 0.5,
                 output: dict | None = None) -> list[RenderReport]:
    cuts = detect_scenes(src, threshold)
    dur = probe(src).duration
    bounds = [0.0] + [c for c in cuts if 0 < c < dur] + [dur]
    os.makedirs(out_dir, exist_ok=True)
    reps = []
    for k in range(len(bounds) - 1):
        s, e = bounds[k], bounds[k + 1]
        if e - s >= min_len:
            reps.append(trim(src, str(Path(out_dir) / f"scene_{k + 1:03d}.mp4"), s, e, output))
    return reps


def reframe(src: str, out: str, aspect: str = "9:16", fit: str = "blur", output: dict | None = None) -> RenderReport:
    """Make vertical/square/wide versions. fit: crop (fill, cut edges), pad (black bars), blur (blurred bars)."""
    o = dict(output or {})
    o["aspect"], o["fit"] = aspect, fit
    return _single(src, out, None, o)


def change_speed(src: str, out: str, speed: float, output: dict | None = None) -> RenderReport:
    return _single(src, out, {"speed": speed}, output)


def join(files: list[str], out: str, transition: str | None = None, transition_duration: float = 0.5,
         output: dict | None = None) -> RenderReport:
    clips = []
    for k, f in enumerate(files):
        c: dict = {"src": f}
        if transition and k < len(files) - 1:
            c["transition"] = {"type": transition, "duration": transition_duration}
        clips.append(c)
    return render({"output": _out(output), "clips": clips}, out)


def add_text(src: str, out: str, texts: list, output: dict | None = None) -> RenderReport:
    return _single(src, out, None, output, texts=texts)


def add_logo(src: str, out: str, logo: str, position: str = "top-right", scale: float = 0.15, opacity: float = 0.9,
             output: dict | None = None) -> RenderReport:
    return _single(src, out, None, output, overlays=[{"src": logo, "position": position, "scale": scale, "opacity": opacity}])


def add_music(src: str, out: str, music: str, volume: float = 0.25, duck: bool = True, fade_out: float = 2.0,
              output: dict | None = None) -> RenderReport:
    return _single(src, out, None, output, music={"src": music, "volume": volume, "duck": duck, "fade_out": fade_out})


def add_subtitles(src: str, subtitles: str, out: str, style: dict | None = None, font: str | None = None,
                  output: dict | None = None) -> RenderReport:
    s: dict = {"src": subtitles}
    if style:
        s["style"] = style
    if font:
        s["font"] = font
    return _single(src, out, None, output, subtitles=s)


def normalize_audio(src: str, out: str, lufs: float = -14.0, output: dict | None = None) -> RenderReport:
    o = dict(output or {})
    o["loudnorm"] = {"I": lufs}
    return _single(src, out, None, o)


def thumbnail(src: str, out_png: str, time: Any = None, width: int = 0) -> str:
    i = probe(src)
    t = parse_time(time) if time is not None else i.duration / 3
    vf = ["scale=iw*sar:ih"] + ([f"scale={width}:-2"] if width else [])
    run([FFMPEG, "-hide_banner", "-nostdin", "-y", "-loglevel", "error", "-ss", f"{t:.3f}", "-i", src,
         "-frames:v", "1", "-vf", ",".join(vf), out_png])
    return out_png


def contact_sheet(src: str, out_png: str, count: int = 12, columns: int = 4, width: int = 320) -> dict:
    """A grid of frames across the video, each stamped with its time. Lets an AI 'look' at an edit."""
    i = probe(src)
    count = max(1, min(count, 48))
    rows = (count + columns - 1) // columns
    times = [i.duration * (k + 0.5) / count for k in range(count)]
    from .core import default_font
    font = default_font()
    tiles = []
    tmpdir = Path(out_png).parent
    for k, t in enumerate(times):
        f = tmpdir / f".cs_{os.getpid()}_{k}.png"
        stamp = (f",drawtext=fontfile='{font}':text='{int(t // 60):02d}\\:{t % 60:05.2f}':x=6:y=6:fontsize=20:"
                 "fontcolor=white:box=1:boxcolor=black@0.6") if font else ""
        run([FFMPEG, "-hide_banner", "-nostdin", "-y", "-loglevel", "error", "-ss", f"{t:.3f}", "-i", src, "-frames:v", "1",
             "-vf", f"scale={width}:-2{stamp}", str(f)])
        tiles.append(f)
    th = max(2, round(width * (i.height or 9) / (i.width or 16) / 2) * 2)
    inputs = []
    for f in tiles:
        inputs += ["-i", str(f)]
    for _ in range(rows * columns - len(tiles)):
        inputs += ["-f", "lavfi", "-i", f"color=c=black:s={width}x{th}:d=1"]
    n = rows * columns
    xs = [f"{'+'.join(['w0'] * (k % columns)) or '0'}_{'+'.join(['h0'] * (k // columns)) or '0'}" for k in range(n)]
    g = "".join(f"[{k}:v]scale={width}:{th},setsar=1[s{k}];" for k in range(n))
    g += "".join(f"[s{k}]" for k in range(n)) + f"xstack=inputs={n}:layout={'|'.join(xs)}:fill=black"
    if n == 1:
        g = f"[0:v]scale={width}:{th}"
    run([FFMPEG, "-hide_banner", "-nostdin", "-y", "-loglevel", "error", *inputs, "-filter_complex", g, "-frames:v", "1", out_png])
    for f in tiles:
        f.unlink(missing_ok=True)
    return {"image": out_png, "times": [round(t, 2) for t in times], "duration": round(i.duration, 2)}


def extract_audio(src: str, out: str) -> str:
    ext = Path(out).suffix.lower()
    codec = {".wav": ["-c:a", "pcm_s16le"], ".mp3": ["-c:a", "libmp3lame", "-q:a", "2"], ".m4a": ["-c:a", "aac", "-b:a", "192k"]}
    if ext not in codec:
        raise VeditError("Audio output must be .wav, .mp3 or .m4a")
    run([FFMPEG, "-hide_banner", "-nostdin", "-y", "-loglevel", "error", "-i", src, "-vn", "-ar", str(AR), *codec[ext], out])
    return out


# ----------------------------------------------------------------------------- speech to text (optional)
def _srt_time(t: float) -> str:
    ms = int(round(t * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def transcribe(src: str, out_srt: str, language: str | None = None, model: str = "small",
               max_chars: int = 32, max_words: int = 6) -> dict:
    """Speech to captions with faster-whisper (optional dependency: pip install faster-whisper).
    Captions are cut into short phrases timed from word timestamps, which suits reels/shorts."""
    try:
        from faster_whisper import WhisperModel  # type: ignore
    except ImportError:
        raise VeditError("Transcription needs faster-whisper: pip install 'vedit[captions]'. "
                         "You can also pass your own .srt to add_subtitles.") from None
    wav = str(Path(out_srt).with_suffix(".tmp.wav"))
    run([FFMPEG, "-hide_banner", "-nostdin", "-y", "-loglevel", "error", "-i", src, "-vn", "-ac", "1", "-ar", "16000", wav])
    try:
        m = WhisperModel(model, device="auto", compute_type="auto")
        segs, inf = m.transcribe(wav, language=language, word_timestamps=True, vad_filter=True)
        words = [w for s in segs for w in (s.words or [])]
    finally:
        Path(wav).unlink(missing_ok=True)
    cues, cur = [], []
    for w in words:
        cur.append(w)
        text = "".join(x.word for x in cur).strip()
        if len(cur) >= max_words or len(text) >= max_chars or w.word.strip().endswith((".", "?", "!", "।")):
            cues.append(cur)
            cur = []
    if cur:
        cues.append(cur)
    lines = []
    for k, c in enumerate(cues, 1):
        lines.append(f"{k}\n{_srt_time(c[0].start)} --> {_srt_time(c[-1].end)}\n{''.join(x.word for x in c).strip()}\n")
    Path(out_srt).write_text("\n".join(lines), encoding="utf-8")
    return {"srt": out_srt, "language": inf.language, "cues": len(cues), "words": len(words)}


def auto_captions(src: str, out: str, language: str | None = None, model: str = "small", style: dict | None = None,
                  font: str | None = None, output: dict | None = None) -> tuple[RenderReport, dict]:
    srt = str(Path(out).with_suffix(".srt"))
    t = transcribe(src, srt, language, model)
    return add_subtitles(src, srt, out, style, font, output), t
