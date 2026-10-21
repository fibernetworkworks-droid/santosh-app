"""Core engine: probe, timeline validation, parallel frame-accurate rendering, verification.

Design
------
* The AI (or a person) writes a *timeline* (plain JSON). The engine never guesses:
  it validates the timeline, snaps every time to the project frame grid, renders,
  then measures the result and reports whether it matches what was asked.
* Stage 1 renders every clip in parallel to an identical intermediate format
  (same size, fps, pixel format, GOP, 48 kHz stereo PCM). Each clip is cut to an
  exact frame count and its audio to the exact matching sample count, so audio
  and video can never drift apart at joins.
* Stage 2 joins the clips (lossless stream copy when there are only hard cuts,
  one filter pass when there are transitions) and applies whole-video work
  (subtitles, text, logos, music with ducking, two-pass loudness normalisation)
  in a single final encode.
* Rendered clips are cached by content hash, so re-rendering after a small
  change only re-does the clips that changed.
"""
from __future__ import annotations

import concurrent.futures as cf
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass, field
from fractions import Fraction
from pathlib import Path
from typing import Any

ENGINE_VERSION = "1.0.0"
FFMPEG = os.environ.get("VEDIT_FFMPEG", "ffmpeg")
FFPROBE = os.environ.get("VEDIT_FFPROBE", "ffprobe")
AR = 48000  # project audio sample rate
IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}
XFADE = {
    "fade", "dissolve", "fadeblack", "fadewhite", "wipeleft", "wiperight", "wipeup", "wipedown",
    "slideleft", "slideright", "slideup", "slidedown", "circleopen", "circleclose", "radial",
    "smoothleft", "smoothright", "smoothup", "smoothdown", "pixelize", "zoomin", "distance",
    "hblur", "squeezeh", "squeezev", "diagtl", "diagtr", "diagbl", "diagbr",
}
POSITIONS = {  # overlay: W/H = frame, w/h = the image
    "top-left": ("{m}", "{m}"), "top": ("(W-w)/2", "{m}"), "top-right": ("W-w-{m}", "{m}"),
    "left": ("{m}", "(H-h)/2"), "center": ("(W-w)/2", "(H-h)/2"), "right": ("W-w-{m}", "(H-h)/2"),
    "bottom-left": ("{m}", "H-h-{m}"), "bottom": ("(W-w)/2", "H-h-{m}"), "bottom-right": ("W-w-{m}", "H-h-{m}"),
}


class VeditError(Exception):
    """Base error. Messages are written for the person or agent using the editor."""


class TimelineError(VeditError):
    def __init__(self, problems: list[str]):
        self.problems = problems
        super().__init__("Timeline has problems:\n- " + "\n- ".join(problems))


class RenderError(VeditError):
    pass


# ----------------------------------------------------------------------------- helpers
def run(cmd: list[str], cwd: str | None = None, check: bool = True) -> subprocess.CompletedProcess:
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, errors="replace")
    if check and p.returncode != 0:
        tail = "\n".join(p.stderr.strip().splitlines()[-25:])
        raise RenderError(f"ffmpeg failed (exit {p.returncode}):\n{tail}\nCommand: {' '.join(cmd)[:2000]}")
    return p


def parse_time(v: Any, fps: Fraction | None = None) -> float:
    """Seconds (number), 'HH:MM:SS.mmm', 'MM:SS', '12.5s', or '123f' (frames at source fps)."""
    if v is None:
        return None  # type: ignore[return-value]
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip().lower()
    if s.endswith("f"):
        if not fps:
            raise VeditError(f"Frame time '{v}' needs a known frame rate")
        return int(s[:-1]) / float(fps)
    if s.endswith("s"):
        return float(s[:-1])
    if ":" in s:
        parts = [float(x) for x in s.split(":")]
        sec = 0.0
        for x in parts:
            sec = sec * 60 + x
        return sec
    return float(s)


def to_fps(v: Any) -> Fraction:
    if isinstance(v, Fraction):
        return v
    if isinstance(v, str) and "/" in v:
        n, d = v.split("/")
        return Fraction(int(n), int(d))
    f = Fraction(str(v)).limit_denominator(1001)
    return f


def fstr(x: float | Fraction) -> str:
    return f"{float(x):.6f}"


def default_font() -> str | None:
    env = os.environ.get("VEDIT_FONT")
    if env and Path(env).exists():
        return env
    cands = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/Library/Fonts/Arial Bold.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
    ]
    for c in cands:
        if Path(c).exists():
            return c
    try:
        p = subprocess.run(["fc-match", "-f", "%{file}", "sans:bold"], capture_output=True, text=True)
        if p.returncode == 0 and Path(p.stdout.strip()).exists():
            return p.stdout.strip()
    except FileNotFoundError:
        pass
    return None


def color_ok(c: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z]+(@[0-9.]+)?|#?[0-9A-Fa-f]{6}([0-9A-Fa-f]{2})?(@[0-9.]+)?|0x[0-9A-Fa-f]{6,8}", str(c)))


def ffcolor(c: str) -> str:
    c = str(c)
    return "0x" + c[1:] if c.startswith("#") else c


# ----------------------------------------------------------------------------- probe
@dataclass
class MediaInfo:
    path: str
    duration: float
    has_video: bool
    has_audio: bool
    width: int = 0
    height: int = 0
    fps: Fraction = Fraction(0)
    vcodec: str = ""
    acodec: str = ""
    sample_rate: int = 0
    channels: int = 0
    rotation: int = 0
    is_image: bool = False
    frames: int | None = None

    def as_dict(self) -> dict:
        d = self.__dict__.copy()
        d["fps"] = f"{self.fps.numerator}/{self.fps.denominator}" if self.fps else None
        d["fps_float"] = round(float(self.fps), 4) if self.fps else None
        return d


_probe_cache: dict[tuple, MediaInfo] = {}


def probe(path: str | os.PathLike, count_frames: bool = False) -> MediaInfo:
    path = str(path)
    if not Path(path).is_file():
        raise VeditError(f"File not found: {path}")
    st = os.stat(path)
    key = (os.path.abspath(path), st.st_size, st.st_mtime_ns, count_frames)
    if key in _probe_cache:
        return _probe_cache[key]
    cmd = [FFPROBE, "-v", "error", "-print_format", "json", "-show_format", "-show_streams"]
    if count_frames:
        cmd += ["-count_packets"]
    p = run(cmd + [path], check=False)
    if p.returncode != 0:
        raise VeditError(f"Not a readable media file: {path} ({p.stderr.strip()[:300]})")
    j = json.loads(p.stdout or "{}")
    streams = j.get("streams", [])
    v = next((s for s in streams if s.get("codec_type") == "video" and not s.get("disposition", {}).get("attached_pic")), None)
    a = next((s for s in streams if s.get("codec_type") == "audio"), None)
    is_image = Path(path).suffix.lower() in IMAGE_EXT
    dur = float(j.get("format", {}).get("duration") or 0)
    info = MediaInfo(path=path, duration=dur, has_video=v is not None, has_audio=a is not None, is_image=is_image)
    if v:
        info.vcodec = v.get("codec_name", "")
        w, h = int(v.get("width", 0)), int(v.get("height", 0))
        rot = 0
        for sd in v.get("side_data_list", []) or []:
            if "rotation" in sd:
                rot = int(sd["rotation"])
        if not rot and v.get("tags", {}).get("rotate"):
            rot = int(v["tags"]["rotate"])
        info.rotation = rot
        if abs(rot) % 180 == 90:
            w, h = h, w
        info.width, info.height = w, h
        for k in ("avg_frame_rate", "r_frame_rate"):
            fr = v.get(k, "0/0")
            try:
                f = to_fps(fr)
                if 0 < f < 1000:
                    info.fps = f
                    break
            except (ZeroDivisionError, ValueError):
                continue
        if count_frames and v.get("nb_read_packets"):
            info.frames = int(v["nb_read_packets"])
        if not dur and v.get("duration"):
            info.duration = float(v["duration"])
    if a:
        info.acodec = a.get("codec_name", "")
        info.sample_rate = int(a.get("sample_rate", 0) or 0)
        info.channels = int(a.get("channels", 0) or 0)
    _probe_cache[key] = info
    return info


# ----------------------------------------------------------------------------- timeline model
@dataclass
class Text:
    text: str
    start: float = 0.0
    end: float | None = None
    position: str = "bottom"
    size: int = 0           # 0 = auto (5% of height)
    color: str = "white"
    box: bool = True
    box_color: str = "black@0.55"
    margin: int = 0         # 0 = auto (5% of height)
    font: str | None = None
    fade: float = 0.0       # seconds of fade in/out
    x: str | None = None    # optional raw x/y expressions override position
    y: str | None = None


@dataclass
class Clip:
    kind: str                      # video | image | color
    src: str | None = None
    tin: float = 0.0               # source in (s)
    tout: float | None = None      # source out (s)
    duration: float | None = None  # for image / color
    speed: float = 1.0
    volume: float = 1.0
    mute: bool = False
    fade_in: float = 0.0
    fade_out: float = 0.0
    color: str = "black"
    crop: dict | None = None       # {x,y,w,h} in source pixels, applied before fit
    fit: str | None = None         # overrides project fit
    texts: list[Text] = field(default_factory=list)
    transition: str | None = None  # transition INTO the next clip
    transition_duration: float = 0.0
    frames: int = 0                # computed: output frame count
    tframes: int = 0               # computed: transition frames into next clip
    info: MediaInfo | None = None


@dataclass
class Project:
    width: int
    height: int
    fps: Fraction
    fit: str = "crop"              # crop | pad | blur
    crf: int = 18
    preset: str = "veryfast"
    codec: str = "h264"            # h264 | hevc
    audio_bitrate: str = "192k"
    loudnorm: dict | None = None
    background: str = "black"


@dataclass
class Overlay:
    src: str
    position: str = "top-right"
    scale: float = 0.15            # width as a fraction of video width
    opacity: float = 1.0
    start: float = 0.0
    end: float | None = None
    margin: int = 0


@dataclass
class Music:
    src: str
    volume: float = 0.25
    start: float = 0.0             # where it starts on the output timeline
    offset: float = 0.0            # where to start inside the music file
    loop: bool = True
    duck: bool = True              # lower music while there is speech/sound in the main track
    fade_in: float = 0.0
    fade_out: float = 2.0


@dataclass
class Timeline:
    project: Project
    clips: list[Clip]
    texts: list[Text] = field(default_factory=list)
    overlays: list[Overlay] = field(default_factory=list)
    music: Music | None = None
    subtitles: dict | None = None  # {"src": "x.srt"|".ass", "style": {...}, "font": path}
    base_dir: str = "."

    @property
    def total_frames(self) -> int:
        return sum(c.frames for c in self.clips) - sum(c.tframes for c in self.clips)

    @property
    def total_duration(self) -> float:
        return self.total_frames / float(self.project.fps)


def _text(d: dict | str, problems: list[str], where: str) -> Text:
    if isinstance(d, str):
        d = {"text": d}
    if not isinstance(d, dict) or not str(d.get("text", "")).strip():
        problems.append(f"{where}: text item needs a non-empty 'text'")
        return Text(text=" ")
    t = Text(text=str(d["text"]))
    t.start = parse_time(d.get("start", 0))
    t.end = parse_time(d["end"]) if d.get("end") is not None else None
    t.position = d.get("position", "bottom")
    t.size = int(d.get("size", 0))
    t.color = d.get("color", "white")
    t.box = bool(d.get("box", True))
    t.box_color = d.get("box_color", "black@0.55")
    t.margin = int(d.get("margin", 0))
    t.font = d.get("font")
    t.fade = float(d.get("fade", 0))
    t.x, t.y = d.get("x"), d.get("y")
    if t.position not in POSITIONS and t.x is None:
        problems.append(f"{where}: position '{t.position}' unknown; use one of {sorted(POSITIONS)}")
    for c in (t.color, t.box_color):
        try:
            ass_color(c)
        except ValueError as e:
            problems.append(f"{where}: {e}")
    if (t.x is None) != (t.y is None):
        problems.append(f"{where}: give both x and y (pixels from the top-left) or neither")
    try:
        if t.x is not None:
            float(t.x), float(t.y)
    except (TypeError, ValueError):
        problems.append(f"{where}: x and y must be numbers of pixels")
    if t.end is not None and t.end <= t.start:
        problems.append(f"{where}: text end ({t.end}) must be after start ({t.start})")
    if t.font and not Path(t.font).is_file():
        problems.append(f"{where}: font file not found: {t.font}")
    return t


def load_timeline(spec: dict | str | os.PathLike, base_dir: str | None = None) -> Timeline:
    """Parse + validate. Raises TimelineError listing every problem found (not just the first)."""
    try:
        if isinstance(spec, (str, os.PathLike)) and Path(str(spec)).is_file():
            base_dir = base_dir or str(Path(str(spec)).parent)
            spec = json.loads(Path(str(spec)).read_text(encoding="utf-8"))
        elif isinstance(spec, str) and spec.lstrip().startswith("{"):
            spec = json.loads(spec)
        elif isinstance(spec, (str, os.PathLike)):
            raise TimelineError([f"timeline file not found: {spec}"])
    except json.JSONDecodeError as e:
        raise TimelineError([f"timeline is not valid JSON: {e}"]) from None
    if not isinstance(spec, dict):
        raise TimelineError(["timeline must be a JSON object with a 'clips' list"])
    base = Path(base_dir or ".")
    problems: list[str] = []

    def resolve(p: str) -> str:
        q = Path(p).expanduser()
        return str((q if q.is_absolute() else (base / q)).resolve())

    raw_clips = spec.get("clips") or []
    if not raw_clips:
        raise TimelineError(["timeline needs at least one clip in 'clips'"])

    clips: list[Clip] = []
    for i, rc in enumerate(raw_clips):
        where = f"clip {i + 1}"
        if isinstance(rc, str):
            rc = {"src": rc}
        c = Clip(kind="video")
        if rc.get("src"):
            c.src = resolve(rc["src"])
            if not Path(c.src).is_file():
                problems.append(f"{where}: file not found: {rc['src']}")
                clips.append(c)
                continue
            try:
                c.info = probe(c.src)
            except VeditError as e:
                problems.append(f"{where}: {e}")
                clips.append(c)
                continue
            c.kind = "image" if c.info.is_image else "video"
            if c.kind == "video" and not c.info.has_video:
                problems.append(f"{where}: {rc['src']} has no video stream (use it as 'music' instead?)")
        elif rc.get("color") or rc.get("duration"):
            c.kind = "color"
            c.color = rc.get("color", "black")
            if not color_ok(c.color):
                problems.append(f"{where}: colour '{c.color}' not understood")
        else:
            problems.append(f"{where}: needs 'src' (a video/image file) or 'color' + 'duration'")
            clips.append(c)
            continue
        sfps = c.info.fps if c.info and c.info.fps else None
        try:
            c.tin = parse_time(rc.get("in", 0), sfps) or 0.0
            c.tout = parse_time(rc["out"], sfps) if rc.get("out") is not None else None
            c.duration = parse_time(rc["duration"], sfps) if rc.get("duration") is not None else None
        except (ValueError, VeditError) as e:
            problems.append(f"{where}: bad time value ({e})")
        c.speed = float(rc.get("speed", 1.0))
        c.volume = float(rc.get("volume", 1.0))
        c.mute = bool(rc.get("mute", False))
        c.fade_in = float(rc.get("fade_in", 0))
        c.fade_out = float(rc.get("fade_out", 0))
        c.crop = rc.get("crop")
        c.fit = rc.get("fit")
        tr = rc.get("transition")
        if isinstance(tr, str):
            tr = {"type": tr}
        if tr:
            c.transition = tr.get("type", "fade")
            c.transition_duration = float(tr.get("duration", 0.5))
            if c.transition not in XFADE:
                problems.append(f"{where}: transition '{c.transition}' unknown; use one of {sorted(XFADE)}")
        c.texts = [_text(t, problems, f"{where} text {j + 1}") for j, t in enumerate(rc.get("texts", []) or [])]
        if not (0.25 <= c.speed <= 4.0):
            problems.append(f"{where}: speed {c.speed} out of range (0.25 to 4)")
        if c.volume < 0:
            problems.append(f"{where}: volume cannot be negative")
        if c.kind == "video" and c.info:
            if c.duration is not None and c.tout is None:
                c.tout = c.tin + c.duration
            if c.tout is None:
                c.tout = c.info.duration
            if c.tin < 0:
                problems.append(f"{where}: 'in' cannot be negative")
            if c.tout - c.tin <= 0:
                problems.append(f"{where}: 'out' ({c.tout:.3f}s) must be after 'in' ({c.tin:.3f}s)")
            if c.tout > c.info.duration + 0.05:
                problems.append(f"{where}: 'out' {c.tout:.3f}s is past the end of {Path(c.src).name} ({c.info.duration:.3f}s)")
            span = (c.tout - c.tin) / c.speed
        else:
            if not c.duration or c.duration <= 0:
                problems.append(f"{where}: image/colour clips need a positive 'duration'")
                span = 0
            else:
                span = c.duration
        if c.crop:
            if not all(k in c.crop for k in ("x", "y", "w", "h")):
                problems.append(f"{where}: crop needs x, y, w, h (source pixels)")
        if c.fit and c.fit not in ("crop", "pad", "blur"):
            problems.append(f"{where}: fit must be crop, pad or blur")
        c._span = span  # type: ignore[attr-defined]
        clips.append(c)

    # project defaults come from the first real video clip
    first = next((c.info for c in clips if c.info and c.info.has_video and not c.info.is_image), None)
    po = spec.get("output", {}) or {}
    width = int(po.get("width") or (first.width if first else 1080))
    height = int(po.get("height") or (first.height if first else 1920))
    if po.get("aspect") and not (po.get("width") and po.get("height")):
        try:
            aw, ah = [int(x) for x in str(po["aspect"]).split(":")]
            assert aw > 0 and ah > 0
        except (ValueError, AssertionError):
            raise TimelineError([f"output.aspect '{po['aspect']}' must look like 9:16"]) from None
        short = int(po.get("short_side", 1080))  # 9:16 -> 1080x1920, 16:9 -> 1920x1080, 4:5 -> 1080x1350
        if aw >= ah:
            width, height = round(short * aw / ah), short
        else:
            width, height = short, round(short * ah / aw)
    width -= width % 2
    height -= height % 2
    fps = to_fps(po.get("fps") or (first.fps if first and first.fps else 30))
    proj = Project(width=width, height=height, fps=fps)
    proj.fit = po.get("fit", "crop")
    proj.crf = int(po.get("crf", 18))
    proj.preset = po.get("preset", "veryfast")
    proj.codec = po.get("codec", "h264")
    proj.audio_bitrate = str(po.get("audio_bitrate", "192k"))
    ln = po.get("loudnorm", False)
    if ln:
        proj.loudnorm = {"I": -14.0, "TP": -1.0, "LRA": 11.0} | (ln if isinstance(ln, dict) else {})
    if proj.fit not in ("crop", "pad", "blur"):
        problems.append("output.fit must be crop, pad or blur")
    if proj.codec not in ("h264", "hevc"):
        problems.append("output.codec must be h264 or hevc")
    if not (0 <= proj.crf <= 51):
        problems.append("output.crf must be 0 to 51 (18 is visually lossless, 23 is the x264 default)")
    if not (16 <= width <= 7680 and 16 <= height <= 7680):
        problems.append(f"output size {width}x{height} out of range")
    if not (1 <= float(fps) <= 240):
        problems.append(f"output fps {float(fps)} out of range")

    # frame-snap every clip and transition
    for i, c in enumerate(clips):
        span = getattr(c, "_span", 0) or 0
        c.frames = max(1, round(span * fps)) if span > 0 else 0
        if span > 0 and c.frames < 2:
            problems.append(f"clip {i + 1}: shorter than 2 frames")
    for i, c in enumerate(clips):
        if c.transition and i == len(clips) - 1:
            problems.append(f"clip {i + 1}: last clip cannot have a transition (it joins into the next clip)")
            c.transition = None
        if c.transition:
            c.tframes = max(1, round(c.transition_duration * fps))
            nxt = clips[i + 1]
            if c.tframes >= min(c.frames, nxt.frames):
                problems.append(f"clip {i + 1}: transition ({c.transition_duration}s) is as long as a clip it joins; shorten it")
        for j, t in enumerate(c.texts):
            if c.frames and t.start >= c.frames / float(fps):
                problems.append(f"clip {i + 1} text {j + 1}: starts after the clip ends")

    texts = [_text(t, problems, f"text {j + 1}") for j, t in enumerate(spec.get("texts", []) or [])]
    overlays = []
    for j, o in enumerate(spec.get("overlays", []) or []):
        where = f"overlay {j + 1}"
        if not o.get("src") or not Path(resolve(o["src"])).is_file():
            problems.append(f"{where}: image not found: {o.get('src')}")
            continue
        ov = Overlay(src=resolve(o["src"]), position=o.get("position", "top-right"), scale=float(o.get("scale", 0.15)),
                     opacity=float(o.get("opacity", 1.0)), start=parse_time(o.get("start", 0)),
                     end=parse_time(o["end"]) if o.get("end") is not None else None, margin=int(o.get("margin", 0)))
        if ov.position not in POSITIONS:
            problems.append(f"{where}: position '{ov.position}' unknown")
        if not (0 < ov.scale <= 1) or not (0 <= ov.opacity <= 1):
            problems.append(f"{where}: scale must be 0-1 and opacity 0-1")
        overlays.append(ov)
    music = None
    if spec.get("music"):
        m = spec["music"]
        m = {"src": m} if isinstance(m, str) else m
        if not m.get("src") or not Path(resolve(m["src"])).is_file():
            problems.append(f"music: file not found: {m.get('src')}")
        else:
            music = Music(src=resolve(m["src"]), volume=float(m.get("volume", 0.25)), start=parse_time(m.get("start", 0)),
                          offset=parse_time(m.get("offset", 0)), loop=bool(m.get("loop", True)), duck=bool(m.get("duck", True)),
                          fade_in=float(m.get("fade_in", 0)), fade_out=float(m.get("fade_out", 2.0)))
            try:
                if not probe(music.src).has_audio:
                    problems.append("music: file has no audio")
            except VeditError as e:
                problems.append(f"music: {e}")
    subs = spec.get("subtitles")
    if subs:
        subs = {"src": subs} if isinstance(subs, str) else dict(subs)
        if not subs.get("src") or not Path(resolve(subs["src"])).is_file():
            problems.append(f"subtitles: file not found: {subs.get('src')}")
        else:
            subs["src"] = resolve(subs["src"])
            if Path(subs["src"]).suffix.lower() not in (".srt", ".ass", ".ssa", ".vtt"):
                problems.append("subtitles: use an .srt, .vtt or .ass file")
    if problems:
        raise TimelineError(problems)
    tl = Timeline(project=proj, clips=clips, texts=texts, overlays=overlays, music=music, subtitles=subs, base_dir=str(base))
    if tl.total_frames <= 0:
        raise TimelineError(["timeline has zero length"])
    for j, t in enumerate(texts):
        if t.start >= tl.total_duration:
            raise TimelineError([f"text {j + 1}: starts at {t.start}s but the video is only {tl.total_duration:.2f}s"])
    return tl


# ----------------------------------------------------------------------------- filter builders
def _encoder_args(p: Project, frames_gop: int, final: bool = False) -> list[str]:
    # intermediate clips repeat stream headers so they can be joined by stream copy
    rh = "" if final else ":repeat-headers=1"
    if p.codec == "hevc":
        return ["-c:v", "libx265", "-preset", p.preset, "-crf", str(p.crf), "-pix_fmt", "yuv420p", "-tag:v", "hvc1",
                "-x265-params", f"keyint={frames_gop}:min-keyint={frames_gop}:scenecut=0{rh}:log-level=error"]
    a = ["-c:v", "libx264", "-preset", p.preset, "-crf", str(p.crf), "-pix_fmt", "yuv420p", "-profile:v", "high",
         "-g", str(frames_gop), "-keyint_min", str(frames_gop), "-sc_threshold", "0"]
    return a if final else a + ["-x264-params", "repeat-headers=1"]


def _fit_chain(fit: str, W: int, H: int, bg: str, label_in: str, label_out: str) -> str:
    if fit == "pad":
        return (f"[{label_in}]scale={W}:{H}:force_original_aspect_ratio=decrease:flags=lanczos,"
                f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color={ffcolor(bg)}[{label_out}]")
    if fit == "blur":
        # blur at 1/8 size then scale up: same look, a fraction of the cost
        bw, bh = max(2, (W // 8) // 2 * 2), max(2, (H // 8) // 2 * 2)
        return (f"[{label_in}]split=2[fbg][ffg];"
                f"[fbg]scale={bw}:{bh}:force_original_aspect_ratio=increase,crop={bw}:{bh},boxblur=4:2,"
                f"scale={W}:{H}:flags=bicubic[fbg2];"
                f"[ffg]scale={W}:{H}:force_original_aspect_ratio=decrease:flags=lanczos[ffg2];"
                f"[fbg2][ffg2]overlay=(W-w)/2:(H-h)/2[{label_out}]")
    return (f"[{label_in}]scale={W}:{H}:force_original_aspect_ratio=increase:flags=lanczos,"
            f"crop={W}:{H}[{label_out}]")


NAMED = {"white": "FFFFFF", "black": "000000", "red": "FF0000", "green": "00C853", "lime": "00FF00", "blue": "0000FF",
         "yellow": "FFFF00", "orange": "FF8C00", "cyan": "00FFFF", "magenta": "FF00FF", "pink": "FF69B4",
         "purple": "800080", "gray": "808080", "grey": "808080", "gold": "FFD700", "navy": "000080", "brown": "8B4513",
         "transparent": "000000@0"}


def ass_color(c: str) -> str:
    """'white', '#FF8800', '0xFF8800', 'black@0.5' -> ASS &HAABBGGRR (AA: 00 opaque, FF transparent)."""
    c = str(c).strip()
    alpha = 1.0
    if "@" in c:
        c, a = c.split("@", 1)
        alpha = float(a)
    low = c.lower()
    if low in NAMED:
        hexv = NAMED[low]
        if "@" in hexv:
            hexv, a = hexv.split("@")
            alpha = float(a)
    else:
        hexv = low[1:] if low.startswith("#") else low[2:] if low.startswith("0x") else low
    if not re.fullmatch(r"[0-9a-f]{6}", hexv, re.I):
        raise ValueError(f"colour '{c}' not understood: use #RRGGBB or one of {sorted(NAMED)}")
    r, g, b = hexv[0:2], hexv[2:4], hexv[4:6]
    aa = max(0, min(255, round((1 - alpha) * 255)))
    return f"&H{aa:02X}{b}{g}{r}".upper().replace("&H", "&H")


def font_family(path: str) -> str | None:
    """Family name from a .ttf/.otf/.ttc 'name' table (no dependencies)."""
    import struct
    try:
        data = Path(path).read_bytes()
        off = 0
        if data[:4] == b"ttcf":
            off = struct.unpack(">I", data[12:16])[0]
        num = struct.unpack(">H", data[off + 4:off + 6])[0]
        name_off = None
        for k in range(num):
            rec = off + 12 + 16 * k
            if data[rec:rec + 4] == b"name":
                name_off = struct.unpack(">I", data[rec + 8:rec + 12])[0]
        if name_off is None:
            return None
        _, count, sto = struct.unpack(">HHH", data[name_off:name_off + 6])
        best = {}
        for k in range(count):
            pid, eid, lid, nid, ln, o = struct.unpack(">HHHHHH", data[name_off + 6 + 12 * k:name_off + 18 + 12 * k])
            if nid not in (1, 16):
                continue
            raw = data[name_off + sto + o:name_off + sto + o + ln]
            txt = raw.decode("utf-16-be", "ignore") if pid in (0, 3) else raw.decode("mac_roman", "ignore")
            if txt and (nid, pid == 3 and lid == 0x409) not in best:
                best[(nid, pid == 3 and lid == 0x409)] = txt
        for key in ((16, True), (16, False), (1, True), (1, False)):
            if key in best:
                return best[key]
    except (OSError, struct.error, IndexError):
        return None
    return None


ALIGN = {"bottom-left": 1, "bottom": 2, "bottom-right": 3, "left": 4, "center": 5, "right": 6,
         "top-left": 7, "top": 8, "top-right": 9}


def _ass_time(t: float) -> str:
    cs = max(0, int(round(t * 100)))
    return f"{cs // 360000}:{cs // 6000 % 60:02d}:{cs // 100 % 60:02d}.{cs % 100:02d}"


def _ass_escape(s: str) -> str:
    return (s.replace("\\", "\u29f5").replace("{", "\\{").replace("}", "\\}").replace("\r", "")
            .replace("\n", "\\N"))


def _auto_size(t: Text, W: int, H: int) -> int:
    size = t.size or max(16, round(min(W, H) * 0.06))
    if t.size:
        return size
    for _ in range(8):
        per_line = max(6, int(0.9 * W / (0.6 * size)))
        lines = sum(max(1, -(-len(p) // per_line)) for p in (t.text.splitlines() or [""]))
        if lines <= 4:
            break
        size = max(16, int(size * 0.85))
    return size


def _install_font(path: str, tmp: Path) -> str:
    fd = tmp / "fonts"
    fd.mkdir(exist_ok=True)
    dst = fd / Path(path).name
    if not dst.exists():
        shutil.copyfile(path, dst)
    return font_family(path) or Path(path).stem


def _ass_doc(W: int, H: int, styles: list[str], events: list[str]) -> str:
    return ("[Script Info]\nScriptType: v4.00+\n"
            f"PlayResX: {W}\nPlayResY: {H}\nWrapStyle: 0\nScaledBorderAndShadow: yes\nYCbCr Matrix: TV.709\n\n"
            "[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, "
            "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, "
            "MarginL, MarginR, MarginV, Encoding\n" + "\n".join(styles) +
            "\n\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
            + "\n".join(events) + "\n")


def _crop_to_content(tmp: Path, png: str) -> tuple[int, int]:
    """Crop a transparent PNG to its visible area (much cheaper to overlay). Returns the crop's top-left corner."""
    p = run([FFMPEG, "-hide_banner", "-nostdin", "-i", png, "-vf", "alphaextract,bbox=min_val=1", "-f", "null", "-"],
            cwd=str(tmp))
    m = re.findall(r"x1:(\d+) x2:(\d+) y1:(\d+) y2:(\d+)", p.stderr)
    if not m:
        return 0, 0
    x1, x2, y1, y2 = map(int, m[-1])
    x1, y1 = x1 // 2 * 2, y1 // 2 * 2
    w, h = (x2 - x1 + 2) // 2 * 2, (y2 - y1 + 2) // 2 * 2
    run([FFMPEG, "-hide_banner", "-nostdin", "-y", "-loglevel", "error", "-i", png, "-vf", f"crop={w}:{h}:{x1}:{y1}",
         "c_" + png], cwd=str(tmp))
    os.replace(tmp / ("c_" + png), tmp / png)
    return x1, y1


def times_of(ev: str) -> str:
    return ",".join(ev.split(",")[1:3])


def _ass_texts(texts: list[Text], W: int, H: int, fps: Fraction, tmp: Path, name: str, length: float,
               lin: str, lout: str) -> list[str]:
    """Filter-graph statements drawing text items from [lin] to [lout] with libass: correct shaping for Hindi,
    Marathi, Tamil, Arabic..., automatic wrapping inside the margins, fades, font fallback for missing characters.
    Boxes are drawn on their own transparent layer first, then faded to the box opacity, so see-through boxes
    stay one even block."""
    (tmp / "fonts").mkdir(exist_ok=True)
    text_styles, text_events = [], []
    boxes: list[tuple[int, str, str, float, float, float]] = []  # (opacity %, style, event, start, end, fade)
    for k, t in enumerate(texts):
        size = _auto_size(t, W, H)
        font = t.font or default_font()
        fam = _install_font(font, tmp) if font else "Sans"
        mv = t.margin or round(H * 0.05)
        mh = t.margin or round(W * 0.05)
        prim = ass_color(t.color)
        bold = 0 if t.font else -1
        al = ALIGN.get(t.position, 2)
        end = t.end if t.end is not None else length
        tags = ""
        if t.fade > 0:
            f = int(t.fade * 1000)
            tags += f"\\fad({f},{f})"
        if t.x is not None and t.y is not None:
            tags += f"\\an7\\pos({float(t.x):.0f},{float(t.y):.0f})"
        body = ("{" + tags + "}" if tags else "") + _ass_escape(t.text)
        times = f"{_ass_time(t.start)},{_ass_time(end)}"
        if t.box:
            bc = ass_color(t.box_color)              # &HAABBGGRR
            a = 1 - int(bc[2:4], 16) / 255           # opacity 0..1
            solid = "&H00" + bc[4:]
            box_body = _ass_escape(t.text)  # fades are applied to the still image instead
            if t.x is not None:
                box_body = "{" + f"\\an7\\pos({float(t.x):.0f},{float(t.y):.0f})" + "}" + _ass_escape(t.text)
            boxes.append((round(a * 100), f"Style: B{k},{fam},{size},&HFF000000,&HFF000000,&HFF000000,{solid},{bold},0,0,0,"
                          f"100,100,0,0,4,{max(4, size // 4)},0,{al},{mh},{mh},{mv},1",
                          f"Dialogue: 0,{times},B{k},,0,0,0,,{box_body}", t.start, end, t.fade))
            # same box metrics as the box layer (so the layout is identical) but an invisible box
            text_styles.append(f"Style: S{k},{fam},{size},{prim},{prim},&HFF000000,&HFF000000,{bold},0,0,0,100,100,0,0,"
                               f"4,{max(4, size // 4)},0,{al},{mh},{mh},{mv},1")
        else:
            text_styles.append(f"Style: S{k},{fam},{size},{prim},{prim},&H00000000,&H80000000,{bold},0,0,0,100,100,0,0,"
                               f"1,{max(2, round(size * 0.07))},0,{al},{mh},{mh},{mv},1")
        # one layer per item: libass only moves overlapping events that share a layer, so nothing gets pushed
        text_events.append(f"Dialogue: {k},{times},S{k},,0,0,0,,{body}")
    out, cur = [], lin
    for k, (pct, st, ev, t0, t1, fade) in enumerate(boxes):
        # draw this box once as a still image (box opacity baked in), then overlay it only while the text shows
        fn = f"{name}_box{k}"
        (tmp / f"{fn}.ass").write_text(_ass_doc(W, H, [st], [ev.replace(times_of(ev), "0:00:00.00,0:00:10.00")]),
                                       encoding="utf-8")
        run([FFMPEG, "-hide_banner", "-nostdin", "-y", "-loglevel", "error", "-f", "lavfi", "-i",
             f"color=c=black@0:s={W}x{H}:d=1,format=rgba", "-vf",
             f"ass=filename={fn}.ass:fontsdir=fonts:alpha=1,colorchannelmixer=aa={pct / 100:.3f}", "-frames:v", "1",
             f"{fn}.png"], cwd=str(tmp))
        bx, by = _crop_to_content(tmp, f"{fn}.png")
        chain = f"movie={fn}.png,loop=loop=-1:size=1,setpts=N/({fps.numerator}/{fps.denominator})/TB,format=rgba"
        if fade > 0:
            chain += (f",fade=t=in:st={t0:.4f}:d={fade:.4f}:alpha=1"
                      f",fade=t=out:st={max(t0, t1 - fade):.4f}:d={fade:.4f}:alpha=1")
        out.append(chain + f"[{name}bx{k}]")
        out.append(f"[{cur}][{name}bx{k}]overlay={bx}:{by}:shortest=1:eof_action=pass:"
                   f"enable='between(t,{t0:.4f},{t1:.4f})'[{name}bo{k}]")
        cur = f"{name}bo{k}"
    (tmp / f"{name}.ass").write_text(_ass_doc(W, H, text_styles, text_events), encoding="utf-8")
    out.append(f"[{cur}]ass=filename={name}.ass:fontsdir=fonts[{lout}]")
    return out


def _atempo(speed: float) -> list[str]:
    out, s = [], speed
    while s > 2.0:
        out.append("atempo=2.0")
        s /= 2.0
    while s < 0.5:
        out.append("atempo=0.5")
        s /= 0.5
    if abs(s - 1.0) > 1e-6:
        out.append(f"atempo={s:.6f}")
    return out


def _clip_job(c: Clip, p: Project, out: Path, tmp: Path, idx: int, threads: int) -> list[str]:
    fps, W, H = p.fps, p.width, p.height
    N = c.frames
    dur = Fraction(N) / fps
    samples = round(dur * AR)
    cmd = [FFMPEG, "-hide_banner", "-nostdin", "-y", "-loglevel", "error", "-threads", str(threads)]
    margin = 1.0
    if c.kind == "video":
        cmd += ["-ss", fstr(c.tin), "-t", fstr((c.tout - c.tin) + margin), "-i", c.src]
    elif c.kind == "image":
        cmd += ["-loop", "1", "-framerate", f"{fps.numerator}/{fps.denominator}", "-t", fstr(dur + margin), "-i", c.src]
    else:
        cmd += ["-f", "lavfi", "-i", f"color=c={ffcolor(c.color)}:s={W}x{H}:r={fps.numerator}/{fps.denominator}:d={fstr(dur + margin)}"]
    use_src_audio = c.kind == "video" and c.info and c.info.has_audio and not c.mute and c.volume > 0
    if not use_src_audio:
        cmd += ["-f", "lavfi", "-t", fstr(dur + margin), "-i", f"anullsrc=r={AR}:cl=stereo"]
    g = []
    v = "[0:v]setpts=PTS-STARTPTS"
    if c.crop:
        cr = c.crop
        v += f",crop={int(cr['w'])}:{int(cr['h'])}:{int(cr['x'])}:{int(cr['y'])}"
    if c.speed != 1.0:
        v += f",setpts=PTS/{c.speed:.6f}"
    v += f",fps={fps.numerator}/{fps.denominator}[vr]"
    g.append(v)
    g.append(_fit_chain(c.fit or p.fit, W, H, p.background, "vr", "vf"))
    post = [f"setsar=1,format=yuv420p,tpad=stop_mode=clone:stop_duration=2,trim=end_frame={N},setpts=PTS-STARTPTS"]
    clip_len = float(dur)
    if c.fade_in > 0:
        post.append(f"fade=t=in:st=0:d={c.fade_in:.4f}")
    if c.fade_out > 0:
        post.append(f"fade=t=out:st={max(0.0, clip_len - c.fade_out):.4f}:d={c.fade_out:.4f}")
    if c.texts:
        g.append("[vf]" + ",".join(post) + "[vpre]")
        g += _ass_texts(c.texts, W, H, fps, tmp, f"c{idx}", clip_len, "vpre", "vout")
    else:
        g.append("[vf]" + ",".join(post) + "[vout]")
    a = "[0:a]" if use_src_audio else "[1:a]"
    a += f"asetpts=PTS-STARTPTS,aresample={AR}:async=1:first_pts=0,aformat=sample_fmts=fltp:channel_layouts=stereo"
    if use_src_audio:
        for t in _atempo(c.speed):
            a += "," + t
        if c.volume != 1.0:
            a += f",volume={c.volume:.4f}"
    a += f",apad,atrim=end_sample={samples},asetpts=PTS-STARTPTS"
    if c.fade_in > 0 and use_src_audio:
        a += f",afade=t=in:st=0:d={c.fade_in:.4f}"
    if c.fade_out > 0 and use_src_audio:
        a += f",afade=t=out:st={max(0.0, clip_len - c.fade_out):.4f}:d={c.fade_out:.4f}"
    g.append(a + "[aout]")
    gop = max(1, round(float(fps) * 2))
    cmd += ["-filter_complex", ";".join(g), "-map", "[vout]", "-map", "[aout]", *(_encoder_args(p, gop)),
            "-r", f"{fps.numerator}/{fps.denominator}", "-frames:v", str(N),
            "-c:a", "pcm_s16le", "-ar", str(AR), "-ac", "2", str(out)]
    return cmd


def _clip_key(c: Clip, p: Project) -> str:
    d = {k: v for k, v in c.__dict__.items() if k not in ("info", "transition", "transition_duration", "tframes")}
    d["texts"] = [t.__dict__ for t in c.texts]
    if c.src:
        st = os.stat(c.src)
        d["src_sig"] = [os.path.abspath(c.src), st.st_size, st.st_mtime_ns]
    for t in c.texts:
        f = t.font or default_font()
        d.setdefault("fonts", []).append(f)
    d["project"] = {"w": p.width, "h": p.height, "fps": str(p.fps), "fit": p.fit, "crf": p.crf, "preset": p.preset,
                    "codec": p.codec, "bg": p.background}
    d["v"] = ENGINE_VERSION
    return hashlib.sha256(json.dumps(d, sort_keys=True, default=str).encode()).hexdigest()[:24]


# ----------------------------------------------------------------------------- render
@dataclass
class RenderReport:
    output: str
    ok: bool
    expected_frames: int
    actual_frames: int | None
    expected_duration: float
    video_duration: float
    audio_duration: float
    av_offset_ms: float
    width: int
    height: int
    fps: str
    clips: int
    clips_from_cache: int
    seconds: float
    checks: list[str]

    def as_dict(self) -> dict:
        return self.__dict__.copy()


def _measure_loudness(cmd_inputs: list[str], agraph: str, alabel: str, ln: dict, cwd: str) -> dict:
    g = agraph + f";[{alabel}]loudnorm=I={ln['I']}:TP={ln['TP']}:LRA={ln['LRA']}:print_format=json[lnm]"
    p = run([FFMPEG, "-hide_banner", "-nostdin", "-y", *cmd_inputs, "-filter_complex", g, "-map", "[lnm]", "-f", "null", "-"],
            cwd=cwd)
    m = re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", p.stderr, re.S)
    if not m:
        raise RenderError("Could not measure loudness")
    return json.loads(m.group(0))


def render(spec: dict | str | Timeline, output: str | os.PathLike, *, base_dir: str | None = None,
           cache_dir: str | os.PathLike | None = None, workers: int | None = None, keep_temp: bool = False,
           progress=None) -> RenderReport:
    t0 = time.time()
    tl = spec if isinstance(spec, Timeline) else load_timeline(spec, base_dir)
    p = tl.project
    output = Path(output).expanduser().resolve()
    if output.suffix.lower() not in (".mp4", ".mov", ".m4v", ".mkv"):
        raise VeditError("Output must be .mp4, .mov, .m4v or .mkv")
    output.parent.mkdir(parents=True, exist_ok=True)
    cache = (Path(cache_dir).expanduser().resolve() if cache_dir else output.parent / ".vedit_cache")
    cache.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix="vedit_"))
    ncpu = os.cpu_count() or 2
    workers = workers or max(1, min(len(tl.clips), ncpu // 2 or 1, 8))
    threads = max(1, ncpu // workers)
    checks: list[str] = []
    try:
        # ---- stage 1: clips in parallel (cached)
        mezz: list[Path] = []
        jobs = []
        from_cache = 0
        for i, c in enumerate(tl.clips):
            f = cache / f"{_clip_key(c, p)}.mkv"
            mezz.append(f)
            if f.exists() and f.stat().st_size > 0:
                from_cache += 1
            else:
                part = tmp / f"clip{i}.mkv"
                jobs.append((i, _clip_job(c, p, part, tmp, i, threads), part, f))
        done = 0
        with cf.ThreadPoolExecutor(max_workers=workers) as ex:
            futs = {ex.submit(run, cmd, str(tmp)): (i, part, final) for i, cmd, part, final in jobs}
            for fu in cf.as_completed(futs):
                i, part, final = futs[fu]
                try:
                    fu.result()
                except RenderError as e:
                    raise RenderError(f"Clip {i + 1} failed: {e}") from None
                os.replace(part, final)
                done += 1
                if progress:
                    progress(f"clip {i + 1}/{len(tl.clips)} rendered ({done}/{len(jobs)} new)")
        for i, (c, f) in enumerate(zip(tl.clips, mezz)):
            got = probe(f, count_frames=True).frames
            if got != c.frames:
                f.unlink(missing_ok=True)
                raise RenderError(f"Clip {i + 1}: expected {c.frames} frames, got {got}. Source may be damaged near "
                                  f"{c.tin:.2f}-{c.tout or 0:.2f}s.")
        checks.append(f"all {len(tl.clips)} clips frame-exact")

        # ---- stage 2: join + global effects, single final pass
        fps, W, H = p.fps, p.width, p.height
        total_frames = tl.total_frames
        total = Fraction(total_frames) / fps
        total_samples = round(total * AR)
        has_tr = any(c.transition for c in tl.clips)
        inputs: list[str] = []
        g: list[str] = []
        if has_tr:
            for f in mezz:
                inputs += ["-i", str(f)]
            vl, al = "0:v", "0:a"
            acc = Fraction(tl.clips[0].frames)  # running length in frames
            for k in range(1, len(tl.clips)):
                prev = tl.clips[k - 1]
                nv, na = f"jv{k}", f"ja{k}"
                if prev.transition:
                    td = Fraction(prev.tframes) / fps
                    off = (acc - prev.tframes) / fps
                    g.append(f"[{vl}][{k}:v]xfade=transition={prev.transition}:duration={fstr(td)}:offset={fstr(off)}[{nv}]")
                    g.append(f"[{al}][{k}:a]acrossfade=ns={round(td * AR)}:c1=tri:c2=tri[{na}]")
                    acc += tl.clips[k].frames - prev.tframes
                else:
                    g.append(f"[{vl}][{k}:v]concat=n=2:v=1:a=0[{nv}]")
                    g.append(f"[{al}][{k}:a]concat=n=2:v=0:a=1[{na}]")
                    acc += tl.clips[k].frames
                vl, al = nv, na
            if acc != total_frames:
                raise RenderError(f"internal: join length {acc} != {total_frames}")
        else:
            lst = tmp / "list.txt"
            lst.write_text("".join(f"file '{str(f).replace(chr(39), chr(39) + chr(92) + chr(39) + chr(39))}'\n" for f in mezz))
            inputs += ["-f", "concat", "-safe", "0", "-i", str(lst)]
            vl, al = "0:v", "0:a"
        n_in = len(mezz) if has_tr else 1

        # global video filters
        vf: list[str] = []
        if tl.subtitles:
            src = Path(tl.subtitles["src"])
            shutil.copyfile(src, tmp / f"subs{src.suffix.lower()}")
            st = tl.subtitles.get("style") or {}
            default = {"Fontname": "DejaVu Sans", "Fontsize": "16", "PrimaryColour": "&H00FFFFFF", "OutlineColour": "&H00000000",
                       "BorderStyle": "1", "Outline": "2", "Shadow": "0", "Alignment": "2", "MarginV": "40", "Bold": "1"}
            if tl.subtitles.get("font") and "Fontname" not in st:
                default["Fontname"] = font_family(tl.subtitles["font"]) or default["Fontname"]
            default.update({k: str(v) for k, v in st.items()})
            fstyle = ",".join(f"{k}={v}" for k, v in default.items())
            sub = f"subtitles=filename=subs{src.suffix.lower()}"
            fontsdir = tl.subtitles.get("fonts_dir")
            if tl.subtitles.get("font"):
                fd = tmp / "fonts"
                fd.mkdir(exist_ok=True)
                shutil.copyfile(tl.subtitles["font"], fd / Path(tl.subtitles["font"]).name)
                fontsdir = "fonts"
            if fontsdir:
                if fontsdir != "fonts":
                    shutil.copytree(fontsdir, tmp / "fonts", dirs_exist_ok=True)
                sub += ":fontsdir=fonts"
            if src.suffix.lower() != ".ass":
                sub += f":force_style='{fstyle}'"
            vf.append(sub)

        ov_inputs: list[str] = []
        for j, o in enumerate(tl.overlays):
            ov_inputs += ["-loop", "1", "-i", o.src]
        chain_needed = bool(vf or tl.texts or tl.overlays or has_tr)
        cur = vl
        if vf:
            g.append(f"[{cur}]" + ",".join(vf) + "[gv0]")
            cur = "gv0"
        if tl.texts:
            g += _ass_texts(tl.texts, W, H, fps, tmp, "gt", float(total), cur, "gtx")
            cur = "gtx"
        for j, o in enumerate(tl.overlays):
            idx = n_in + j
            m = o.margin or round(H * 0.03)
            x, y = (s.format(m=m) for s in POSITIONS[o.position])
            end = o.end if o.end is not None else float(total)
            g.append(f"[{idx}:v]format=rgba,scale={max(2, round(W * o.scale))}:-1,colorchannelmixer=aa={o.opacity:.3f}[lg{j}]")
            g.append(f"[{cur}][lg{j}]overlay=x={x}:y={y}:shortest=1:enable='between(t,{o.start:.4f},{end:.4f})'[ov{j}]")
            cur = f"ov{j}"
        if chain_needed:
            g.append(f"[{cur}]format=yuv420p,trim=end_frame={total_frames},setpts=PTS-STARTPTS[vfinal]")
            vmap = "[vfinal]"
        else:
            vmap = f"{vl}"

        # audio: music + ducking
        mus_inputs: list[str] = []
        a_cur = al
        ag: list[str] = []
        if tl.music:
            mi = n_in + len(tl.overlays)
            mu = tl.music
            if mu.loop:
                mus_inputs += ["-stream_loop", "-1"]
            if mu.offset:
                mus_inputs += ["-ss", fstr(mu.offset)]
            mus_inputs += ["-i", mu.src]
            delay = int(round(mu.start * 1000))
            mch = (f"[{mi}:a]aresample={AR},aformat=sample_fmts=fltp:channel_layouts=stereo,volume={mu.volume:.4f}"
                   + (f",afade=t=in:st=0:d={mu.fade_in:.3f}" if mu.fade_in else "")
                   + (f",adelay={delay}|{delay}" if delay else "")
                   + f",apad,atrim=end_sample={total_samples}")
            if mu.fade_out:
                mch += f",afade=t=out:st={max(0.0, float(total) - mu.fade_out):.4f}:d={mu.fade_out:.4f}"
            ag.append(mch + "[mus]")
            if mu.duck:
                ag.append(f"[{a_cur}]asplit=2[vo1][vo2]")
                ag.append("[mus][vo2]sidechaincompress=threshold=0.03:ratio=6:attack=15:release=400:makeup=1[musd]")
                ag.append("[vo1][musd]amix=inputs=2:duration=first:normalize=0:dropout_transition=0[amx]")
            else:
                ag.append(f"[{a_cur}][mus]amix=inputs=2:duration=first:normalize=0:dropout_transition=0[amx]")
            a_cur = "amx"
        all_inputs = inputs + ov_inputs + mus_inputs
        if p.loudnorm:
            # measure with the same audio graph (video branch excluded), then apply in linear mode
            meas_g = ";".join(([x for x in g if "acrossfade" in x or ("concat" in x and "a=1" in x)]) + ag)
            # same inputs in the same order, so stream indexes match
            meas_inputs = inputs + ov_inputs + mus_inputs
            meas = _measure_loudness(meas_inputs, meas_g or f"[{a_cur}]anull[apre]", a_cur if meas_g else "apre",
                                     p.loudnorm, str(tmp))
            ln = p.loudnorm
            ag.append(f"[{a_cur}]loudnorm=I={ln['I']}:TP={ln['TP']}:LRA={ln['LRA']}:measured_I={meas['input_i']}:"
                      f"measured_TP={meas['input_tp']}:measured_LRA={meas['input_lra']}:measured_thresh={meas['input_thresh']}:"
                      f"offset={meas['target_offset']}:linear=true,aresample={AR}[aln]")
            a_cur = "aln"
            checks.append(f"loudness measured {meas['input_i']} LUFS -> target {ln['I']} LUFS")
        ag.append(f"[{a_cur}]apad,atrim=end_sample={total_samples},asetpts=PTS-STARTPTS[afinal]")
        g += ag
        tmp_out = output.with_name(output.stem + ".partial" + output.suffix)
        gop = max(1, round(float(fps) * 2))
        cmd = [FFMPEG, "-hide_banner", "-nostdin", "-y", "-loglevel", "error", *all_inputs,
               "-filter_complex", ";".join(g), "-map", vmap, "-map", "[afinal]"]
        if chain_needed:
            cmd += [*(_encoder_args(p, gop, final=True)), "-frames:v", str(total_frames)]
        else:
            cmd += ["-c:v", "copy"]
            if p.codec == "hevc":
                cmd += ["-tag:v", "hvc1"]  # plays on Apple devices
            checks.append("video joined losslessly (stream copy, no re-encode)")
        cmd += ["-c:a", "aac", "-b:a", p.audio_bitrate, "-ar", str(AR), "-ac", "2"]
        if output.suffix.lower() in (".mp4", ".mov", ".m4v"):
            cmd += ["-movflags", "+faststart"]
        cmd += [str(tmp_out)]
        if progress:
            progress("joining and finishing")
        run(cmd, cwd=str(tmp))
        os.replace(tmp_out, output)
        rep = verify(output, total_frames, fps, (W, H))
        rep.clips, rep.clips_from_cache, rep.seconds = len(tl.clips), from_cache, round(time.time() - t0, 2)
        rep.checks = checks + rep.checks
        return rep
    finally:
        if keep_temp:
            print("temp kept at", tmp)
        else:
            shutil.rmtree(tmp, ignore_errors=True)


def verify(path: str | os.PathLike, expected_frames: int, fps: Fraction, size: tuple[int, int] | None = None) -> RenderReport:
    path = str(path)
    p = run([FFPROBE, "-v", "error", "-count_packets", "-print_format", "json", "-show_streams", "-show_format", path])
    j = json.loads(p.stdout)
    v = next((s for s in j["streams"] if s["codec_type"] == "video"), None)
    a = next((s for s in j["streams"] if s["codec_type"] == "audio"), None)
    checks, ok = [], True
    frames = int(v.get("nb_read_packets", 0)) if v else None
    vdur = float(v.get("duration", 0)) if v else 0.0
    adur = float(a.get("duration", 0)) if a else 0.0
    exp = expected_frames / float(fps)
    if frames != expected_frames:
        ok = False
        checks.append(f"FAIL frame count {frames} != expected {expected_frames}")
    else:
        checks.append(f"frame count exact ({frames})")
    off = (adur - vdur) * 1000
    tol = 1000 / float(fps) + 50  # one frame + AAC padding
    if a is None:
        ok = False
        checks.append("FAIL no audio track")
    elif abs(off) > tol:
        ok = False
        checks.append(f"FAIL audio/video length differ by {off:.0f} ms")
    else:
        checks.append(f"audio/video aligned ({off:+.0f} ms)")
    w, h = (int(v["width"]), int(v["height"])) if v else (0, 0)
    if size and (w, h) != tuple(size):
        ok = False
        checks.append(f"FAIL size {w}x{h} != {size[0]}x{size[1]}")
    return RenderReport(output=path, ok=ok, expected_frames=expected_frames, actual_frames=frames, expected_duration=round(exp, 4),
                        video_duration=round(vdur, 4), audio_duration=round(adur, 4), av_offset_ms=round(off, 1), width=w,
                        height=h, fps=f"{fps.numerator}/{fps.denominator}", clips=0, clips_from_cache=0, seconds=0.0,
                        checks=checks)
