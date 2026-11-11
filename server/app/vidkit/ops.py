"""ffmpeg-backed video operations. Steps are validated in Python, turned into ONE filter graph, run by ffmpeg.

Every edit is local (the server's ffmpeg): no key, no model, no cost. Metadata (location, camera, owner tags) is always
dropped from the output. What is said or written inside a video is data, never instructions.
"""
from __future__ import annotations

import io
import json
import math
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

MAX_BYTES = 1024 * 1024 * 1024           # 1 GB per input
MAX_OUT_BYTES = 300 * 1024 * 1024        # what we hand back into chat
MAX_SECONDS = 60 * 60                    # 1 hour per input
MAX_STEPS = 15
MAX_LONG_SIDE = 1920                     # outputs are capped at 1080p unless the input is smaller
FONT_DIR = Path(__file__).resolve().parent.parent / "fonts"
FORMATS = {"mp4": "mp4", "mov": "mov", "webm": "webm"}
QUALITY = {"high": 20, "good": 23, "small": 28}
ASPECTS = {"9:16": (9, 16), "16:9": (16, 9), "1:1": (1, 1), "4:5": (4, 5), "4:3": (4, 3), "3:4": (3, 4), "21:9": (21, 9),
           "reel": (9, 16), "short": (9, 16), "story": (9, 16), "status": (9, 16), "vertical": (9, 16),
           "youtube": (16, 9), "landscape": (16, 9), "square": (1, 1), "portrait": (4, 5), "feed": (4, 5)}
COMPRESS_TARGETS = {"whatsapp": 16.0, "email": 20.0, "discord": 10.0, "telegram": 50.0}
GRAV = {"center": (.5, .5), "top": (.5, 0), "bottom": (.5, 1), "left": (0, .5), "right": (1, .5),
        "top-left": (0, 0), "top-right": (1, 0), "bottom-left": (0, 1), "bottom-right": (1, 1)}
LOOKS = {
    "bw": "hue=s=0",
    "sepia": "colorchannelmixer=.393:.769:.189:0:.349:.686:.168:0:.272:.534:.131",
    "vintage": "curves=preset=vintage",
    "warm": "colorbalance=rs=.08:gs=.02:bs=-.08:rm=.05:bm=-.05",
    "cool": "colorbalance=rs=-.06:bs=.08:rm=-.04:bm=.06",
    "vivid": "eq=saturation=1.35:contrast=1.06",
    "cinematic": "curves=preset=medium_contrast,eq=saturation=0.85,colorbalance=rs=-.03:bs=.05:rh=.05:bh=-.04",
    "bright": "eq=brightness=0.06:gamma=1.08",
    "faded": "curves=preset=lighter,eq=saturation=0.75:contrast=0.92",
}


class VideoError(ValueError):
    """A request Hoola can explain in one plain sentence."""


def ffmpeg_ok() -> bool:
    return bool(shutil.which("ffmpeg") and shutil.which("ffprobe"))


def _num(v: Any, name: str, lo: float, hi: float, default: float | None = None) -> float:
    if v is None or v == "":
        if default is None:
            raise VideoError(f"{name} chahiye.")
        return default
    try:
        x = float(v)
    except (TypeError, ValueError):
        raise VideoError(f"{name} ek number hona chahiye.") from None
    if math.isnan(x) or x < lo or x > hi:
        raise VideoError(f"{name} {lo:g} se {hi:g} ke beech rakhiye.")
    return x


def secs(v: Any, name: str = "time") -> float:
    """'90', '1:30', '01:02:03', '1m30s', 90.5 -> seconds."""
    if isinstance(v, (int, float)):
        x = float(v)
    else:
        s = str(v or "").strip().lower()
        if not s:
            raise VideoError(f"{name} chahiye (jaise 1:30 ya 90).")
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
                raise VideoError(f"{name} '{v}' samajh nahi aaya (jaise 1:30, 90 ya 1m30s).") from None
    if x < 0 or x > MAX_SECONDS:
        raise VideoError(f"{name} 0 se {MAX_SECONDS // 60} minute ke beech rakhiye.")
    return round(x, 3)


def _even(x: float) -> int:
    return max(2, int(round(x / 2)) * 2)


def aspect(v: Any) -> tuple[int, int]:
    s = str(v or "").strip().lower().replace("x", ":").replace("/", ":")
    if s in ASPECTS:
        return ASPECTS[s]
    m = re.fullmatch(r"(\d{1,4}):(\d{1,4})", s)
    if m and int(m.group(1)) and int(m.group(2)):
        a, b = int(m.group(1)), int(m.group(2))
        if 0.2 <= a / b <= 5:
            return a, b
    raise VideoError(f"aspect '{v}' samajh nahi aaya: 9:16 (Reel / Short / Status), 16:9 (YouTube), 1:1, 4:5.")


# --------------------------------------------------------------------------- probe
def _ffprobe(path: str) -> dict:
    try:
        out = subprocess.run(["ffprobe", "-v", "error", "-print_format", "json", "-show_streams", "-show_format", path],
                             capture_output=True, text=True, timeout=60)
        return json.loads(out.stdout or "{}")
    except Exception:
        raise VideoError("File padhi nahi ja saki.") from None


def probe(path: str) -> dict[str, Any]:
    if not ffmpeg_ok():
        raise VideoError("Server par ffmpeg nahi hai; video edit nahi ho sakta.")
    size = os.path.getsize(path)
    if size > MAX_BYTES:
        raise VideoError(f"Video bahut bada hai ({size // 1048576} MB); {MAX_BYTES // 1048576} MB tak chalta hai.")
    j = _ffprobe(path)
    vs = [s for s in j.get("streams") or [] if s.get("codec_type") == "video"
          and not (s.get("disposition") or {}).get("attached_pic")]
    if not vs:
        raise VideoError("Is file mein video nahi hai (sirf awaaz ya photo hai). Awaaz ke liye audio_edit, photo ke liye image_edit.")
    v = vs[0]
    aud = [s for s in j.get("streams") or [] if s.get("codec_type") == "audio"]
    fmt = j.get("format") or {}
    dur = float(fmt.get("duration") or v.get("duration") or 0)
    if dur <= 0:
        raise VideoError("Video ki lambai nahi mili; file kharab lagti hai.")
    if dur > MAX_SECONDS:
        raise VideoError(f"Video {dur / 60:.0f} minute ka hai; {MAX_SECONDS // 60} minute tak chalta hai.")
    w, h = int(v.get("width") or 0), int(v.get("height") or 0)
    rot = 0
    for sd in v.get("side_data_list") or []:
        if "rotation" in sd:
            rot = int(float(sd.get("rotation") or 0))
    rot = int((v.get("tags") or {}).get("rotate") or rot)
    if abs(rot) % 180 == 90:               # ffmpeg auto-rotates on decode, so the frames we edit are turned
        w, h = h, w
    fps = 30.0
    for key in ("avg_frame_rate", "r_frame_rate"):
        n, _, d = str(v.get(key) or "").partition("/")
        try:
            f = float(n) / float(d or 1)
            if 1 <= f <= 240:
                fps = f
                break
        except (ValueError, ZeroDivisionError):
            continue
    return {"duration": round(dur, 3), "width": w, "height": h, "fps": round(fps, 3), "has_audio": bool(aud),
            "vcodec": v.get("codec_name"), "acodec": aud[0].get("codec_name") if aud else None, "size": size,
            "bit_rate": int(fmt.get("bit_rate") or 0), "rotation": rot}


def verdict(p: dict[str, Any]) -> str:
    w, h, d = p["width"], p["height"], p["duration"]
    shape = "vertical (Reel / Short / Status)" if h > w * 1.2 else "landscape (YouTube)" if w > h * 1.2 else "square-ish"
    bits = [f"{w}x{h} {shape}", f"{d:.1f} s", f"{p['fps']:g} fps", f"{p['size'] / 1048576:.1f} MB"]
    if not p["has_audio"]:
        bits.append("no sound")
    tips = []
    if h > w * 1.2 and d > 90:
        tips.append("Instagram Reel 90 s tak; isse lamba ho to trim ya split")
    if w > h * 1.2:
        tips.append("Reel / Status ke liye reframe aspect 9:16 (mode blur) karein")
    if p["size"] > 16 * 1048576:
        tips.append("WhatsApp par bhejne ke liye compress target whatsapp")
    return "; ".join(bits) + (". " + "; ".join(tips) + "." if tips else ".")


# --------------------------------------------------------------------------- the graph
class Graph:
    """One filter_complex graph. Video goes through labelled segments, audio through a plain chain."""

    def __init__(self, info: dict[str, Any]):
        self.segs: list[str] = []
        self.cur = "0:v"
        self.n = 0
        self.af: list[str] = []
        self.inputs: list[list[str]] = []        # extra inputs: each a list of ffmpeg args ending in "-i path"
        self.w, self.h = info["width"], info["height"]
        self.dur = info["duration"]
        self.fps = info["fps"]
        self.audio = info["has_audio"]
        self.tmp: list[str] = []

    def lab(self, p: str = "v") -> str:
        self.n += 1
        return f"{p}{self.n}"

    def lin(self, *filters: str) -> None:
        out = self.lab()
        self.segs.append(f"[{self.cur}]{','.join(filters)}[{out}]")
        self.cur = out

    def raw(self, seg: str, out: str) -> None:
        self.segs.append(seg)
        self.cur = out

    def add_input(self, *args: str) -> int:
        self.inputs.append(list(args))
        return len(self.inputs)              # input index (0 is the main video)


def _box(st: dict, g: Graph) -> tuple[int, int, int, int]:
    """x, y, w, h in pixels from px numbers or percent strings ('10%')."""
    def one(key: str, full: int, default: Any) -> int:
        v = st.get(key, default)
        if isinstance(v, str) and v.strip().endswith("%"):
            x = _num(v.strip()[:-1], key, 0, 100) * full / 100
        else:
            x = _num(v, key, 0, full)
        return int(round(x))
    x, y = one("x", g.w, 0), one("y", g.h, 0)
    w, h = one("w", g.w, "100%"), one("h", g.h, "100%")
    w, h = min(w, g.w - x), min(h, g.h - y)
    if w < 8 or h < 8:
        raise VideoError("Box bahut chhota hai ya frame ke bahar hai (x, y, w, h pixels ya '10%').")
    return x, y, _even(w) if w > 2 else w, _even(h) if h > 2 else h


def _window(st: dict, g: Graph) -> str:
    a = secs(st["start"], "start") if st.get("start") not in (None, "") else 0.0
    b = secs(st["end"], "end") if st.get("end") not in (None, "") else None
    if b is not None and b <= a:
        raise VideoError("end, start ke baad hona chahiye.")
    if a == 0 and b is None:
        return ""
    return f":enable='between(t,{a},{b if b is not None else 1e9})'"


def _crop_to(g: Graph, ar: tuple[int, int], position: str) -> None:
    tw, th = g.w, g.h
    if g.w / g.h > ar[0] / ar[1]:
        tw = _even(g.h * ar[0] / ar[1])
    else:
        th = _even(g.w * ar[1] / ar[0])
    gx, gy = GRAV.get(str(position or "center").lower(), (.5, .5))
    x, y = int((g.w - tw) * gx), int((g.h - th) * gy)
    g.lin(f"crop={tw}:{th}:{x}:{y}")
    g.w, g.h = tw, th


def _overlay_png(g: Graph, png: bytes, window: str) -> None:
    fd, path = tempfile.mkstemp(suffix=".png")
    os.write(fd, png)
    os.close(fd)
    g.tmp.append(path)
    idx = g.add_input("-loop", "1", "-i", path)
    ov, out = g.lab("o"), g.lab()
    g.raw(f"[{idx}:v]format=rgba[{ov}];[{g.cur}][{ov}]overlay=0:0:shortest=1{window}[{out}]", out)


def _text_png(st: dict, w: int, h: int) -> bytes:
    from PIL import Image
    from ..imgedit import ops as iops
    canvas = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    try:
        im = iops.op_text(canvas, text=st.get("text", ""), position=st.get("position", "bottom"),
                          size_pct=st.get("size_pct", 6), color=st.get("color", "white"), opacity=st.get("opacity", 100),
                          stroke=st.get("stroke", 2), margin_pct=st.get("margin_pct", 6), box=st.get("box"),
                          tile=st.get("tile", False), angle=st.get("angle", 0))
    except iops.EditError as e:
        raise VideoError(str(e)) from None
    buf = io.BytesIO()
    im.save(buf, "PNG")
    return buf.getvalue()


def _atempo(f: float) -> list[str]:
    out = []
    while f > 2.0:
        out.append("atempo=2.0"); f /= 2.0
    while f < 0.5:
        out.append("atempo=0.5"); f /= 0.5
    out.append(f"atempo={f:.6f}")
    return out


STEP_OPS = {"trim", "cut", "speed", "reverse", "fade", "crop", "reframe", "resize", "rotate", "flip", "color", "look",
            "sharpen", "denoise", "stabilize", "blur_area", "text", "watermark", "mute", "volume", "normalize",
            "denoise_audio", "fps", "zoom"}
REFUSED_OPS = {"delogo", "remove_watermark", "remove_logo", "face_swap", "deepfake", "faceswap", "lip_sync", "voice_clone"}


def step(st: dict, g: Graph) -> str:
    """Apply one step to the graph; return a one-line description."""
    op = str(st.get("op") or "").strip().lower()
    if op in REFUSED_OPS:
        raise VideoError("Yeh nahi hota: kisi aur ka watermark / logo hatana, chehra badalna ya kisi ki awaaz / chehre ki "
                         "nakal (deepfake). Apne hi video ka koi hissa chhupana ho to blur_area use karein.")
    if op == "trim":
        a = secs(st.get("start", 0), "start")
        b = min(secs(st["end"], "end"), g.dur) if st.get("end") not in (None, "") else g.dur
        if b - a < 0.1:
            raise VideoError("Trim ke baad kuch bachta hi nahi (start, end se pehle hona chahiye).")
        g.lin(f"trim=start={a}:end={b}", "setpts=PTS-STARTPTS")
        if g.audio:
            g.af += [f"atrim=start={a}:end={b}", "asetpts=PTS-STARTPTS"]
        g.dur = b - a
        return f"kept {a:g}s-{b:g}s"
    if op == "cut":
        a, b = secs(st.get("start"), "start"), min(secs(st.get("end"), "end"), g.dur)
        if b <= a:
            raise VideoError("Cut ka end, start ke baad hona chahiye.")
        if a <= 0 and b >= g.dur:
            raise VideoError("Poora video kaatne se kuch nahi bachega.")
        g.lin(f"select='not(between(t,{a},{b}))'", f"setpts=N/({g.fps:g}*TB)")
        if g.audio:
            g.af += [f"aselect='not(between(t,{a},{b}))'", "asetpts=N/SR/TB"]
        g.dur -= b - a
        return f"removed {a:g}s-{b:g}s"
    if op == "speed":
        f = _num(st.get("factor"), "factor", 0.25, 4)
        g.lin(f"setpts=PTS/{f:.6f}")
        if g.audio:
            g.af += _atempo(f)
        g.dur /= f
        return f"speed x{f:g}" + (" (slow motion)" if f < 1 else "")
    if op == "reverse":
        if g.dur > 60:
            raise VideoError("Ulta (reverse) 60 second tak ke video par hota hai; pehle trim karein.")
        g.lin("reverse")
        if g.audio:
            g.af.append("areverse")
        return "reversed"
    if op == "fade":
        fi, fo = _num(st.get("in"), "in", 0, 30, 0), _num(st.get("out"), "out", 0, 30, 0)
        if not fi and not fo:
            raise VideoError("fade ke liye in ya out seconds bataiye.")
        if fi + fo > g.dur:
            raise VideoError("Fade video se lamba hai.")
        vf = ([f"fade=t=in:st=0:d={fi}"] if fi else []) + ([f"fade=t=out:st={max(0.0, g.dur - fo):.3f}:d={fo}"] if fo else [])
        g.lin(*vf)
        if g.audio:
            g.af += ([f"afade=t=in:st=0:d={fi}"] if fi else []) + \
                    ([f"afade=t=out:st={max(0.0, g.dur - fo):.3f}:d={fo}"] if fo else [])
        return f"fade in {fi:g}s / out {fo:g}s"
    if op == "crop":
        if st.get("aspect"):
            ar = aspect(st["aspect"])
            _crop_to(g, ar, st.get("position", "center"))
            return f"cropped to {ar[0]}:{ar[1]} ({st.get('position', 'center')})"
        x, y, w, h = _box(st, g)
        g.lin(f"crop={w}:{h}:{x}:{y}")
        g.w, g.h = w, h
        return f"cropped to {w}x{h}"
    if op == "reframe":
        ar = aspect(st.get("aspect", "9:16"))
        mode = str(st.get("mode", "blur")).lower()
        if mode == "crop":
            _crop_to(g, ar, st.get("position", "center"))
            return f"reframed {ar[0]}:{ar[1]} by cropping"
        if mode not in ("blur", "pad"):
            raise VideoError("reframe mode: blur (dhundhla background), pad (rang ki patti) ya crop.")
        long = max(g.w, g.h)
        if ar[0] < ar[1]:
            ch, cw = _even(long), _even(long * ar[0] / ar[1])
        else:
            cw, ch = _even(long), _even(long * ar[1] / ar[0])
        if max(cw, ch) > MAX_LONG_SIDE:
            k = MAX_LONG_SIDE / max(cw, ch)
            cw, ch = _even(cw * k), _even(ch * k)
        n = g.n + 1
        out = f"v{n}r"
        fit = f"scale={cw}:{ch}:force_original_aspect_ratio=decrease,setsar=1"
        if mode == "pad":
            from ..imgedit.ops import _rgb
            r, gg, b = _rgb(st.get("color", "black"), "black")
            g.raw(f"[{g.cur}]{fit},pad={cw}:{ch}:(ow-iw)/2:(oh-ih)/2:color=0x{r:02x}{gg:02x}{b:02x}[{out}]", out)
        else:
            g.raw(f"[{g.cur}]split[a{n}][b{n}];[a{n}]scale={cw}:{ch}:force_original_aspect_ratio=increase,crop={cw}:{ch},"
                  f"boxblur=luma_radius=min(h\\,w)/20:luma_power=2,eq=brightness=-0.05,setsar=1[bg{n}];"
                  f"[b{n}]{fit}[fg{n}];[bg{n}][fg{n}]overlay=(W-w)/2:(H-h)/2[{out}]", out)
        g.w, g.h = cw, ch
        return f"reframed {ar[0]}:{ar[1]} ({cw}x{ch}, {mode} background)"
    if op == "resize":
        p = str(st.get("preset") or "").lower().rstrip("p")
        if p:
            if p not in {"2160", "1440", "1080", "720", "480", "360", "240"}:
                raise VideoError("resize preset: 1080p, 720p, 480p, 360p.")
            short = int(p)
            k = short / min(g.w, g.h)
        elif st.get("width") or st.get("height"):
            k = (_num(st["width"], "width", 16, 3840) / g.w) if st.get("width") else (_num(st["height"], "height", 16, 3840) / g.h)
        elif st.get("percent"):
            k = _num(st["percent"], "percent", 5, 400) / 100
        else:
            raise VideoError("resize: preset (720p) ya width / height ya percent bataiye.")
        w, h = _even(g.w * k), _even(g.h * k)
        if max(w, h) > 3840:
            raise VideoError("4K se bada video nahi banta.")
        g.lin(f"scale={w}:{h}:flags=lanczos")
        g.w, g.h = w, h
        return f"resized to {w}x{h}"
    if op == "rotate":
        d = int(_num(st.get("degrees", 90), "degrees", -270, 270)) % 360
        if d not in (90, 180, 270):
            raise VideoError("rotate degrees: 90, 180 ya 270.")
        g.lin({90: "transpose=1", 180: "hflip,vflip", 270: "transpose=2"}[d])
        if d != 180:
            g.w, g.h = g.h, g.w
        return f"rotated {d}°"
    if op == "flip":
        dr = str(st.get("direction", "horizontal")).lower()
        if dr not in ("horizontal", "vertical", "mirror"):
            raise VideoError("flip direction: horizontal (mirror) ya vertical.")
        g.lin("vflip" if dr == "vertical" else "hflip")
        return f"flipped {dr}"
    if op == "color":
        b = _num(st.get("brightness"), "brightness", -100, 100, 0)
        c = _num(st.get("contrast"), "contrast", -100, 100, 0)
        s = _num(st.get("saturation"), "saturation", -100, 100, 0)
        gm = _num(st.get("gamma"), "gamma", 0.3, 3, 1)
        if not (b or c or s) and gm == 1:
            raise VideoError("color: brightness / contrast / saturation (-100..100) ya gamma bataiye.")
        g.lin(f"eq=brightness={b / 250:.3f}:contrast={1 + c / 100:.3f}:saturation={1 + s / 100:.3f}:gamma={gm:.3f}")
        return f"colour brightness {b:+g} contrast {c:+g} saturation {s:+g}"
    if op == "look":
        name = str(st.get("name") or "").lower()
        if name not in LOOKS:
            raise VideoError("look name: " + ", ".join(LOOKS) + ".")
        g.lin(LOOKS[name])
        return f"look: {name}"
    if op == "sharpen":
        amt = _num(st.get("amount"), "amount", 0.1, 2.5, 0.8)
        g.lin(f"unsharp=5:5:{amt:.2f}:5:5:0")
        return "sharpened"
    if op == "denoise":
        lvl = str(st.get("strength", "medium")).lower()
        p = {"light": "2:1.5:3:2.5", "medium": "4:3:6:4.5", "strong": "7:5:10:8"}.get(lvl)
        if not p:
            raise VideoError("strength: light, medium ya strong.")
        g.lin(f"hqdn3d={p}")
        return f"grain / noise reduced ({lvl})"
    if op == "stabilize":
        g.lin("deshake=rx=32:ry=32")
        return "shake reduced (light stabilisation; heavy shake stays partly visible)"
    if op == "blur_area":
        x, y, w, h = _box(st, g)
        k = int(_num(st.get("strength"), "strength", 2, 40, 18))
        n = g.n + 1
        out = f"v{n}b"
        rad = max(1, min(k, min(w, h) // 2 - 1))
        crad = max(1, min(rad, min(w, h) // 4 - 1))          # chroma planes are half size
        g.raw(f"[{g.cur}]split[m{n}][s{n}];[s{n}]crop={w}:{h}:{x}:{y},"
              f"boxblur=luma_radius={rad}:luma_power=3:chroma_radius={crad}:chroma_power=3[bl{n}];"
              f"[m{n}][bl{n}]overlay={x}:{y}{_window(st, g)}[{out}]", out)
        return f"blurred area {w}x{h} at {x},{y}"
    if op == "text":
        txt = str(st.get("text") or "").strip()
        if not txt:
            raise VideoError("text likhiye.")
        _overlay_png(g, _text_png(st, g.w, g.h), _window(st, g))
        return f"text '{txt[:40]}' ({st.get('position', 'bottom')})"
    if op == "watermark":
        path = st.get("_path")
        if not path:
            raise VideoError("watermark ke liye uske logo ki photo ka file_id chahiye (sirf apna logo).")
        size = _num(st.get("size_pct"), "size_pct", 3, 60, 15)
        alpha = _num(st.get("opacity"), "opacity", 5, 100, 85) / 100
        gx, gy = GRAV.get(str(st.get("position", "bottom-right")).lower(), (1, 1))
        m = int(min(g.w, g.h) * _num(st.get("margin_pct"), "margin_pct", 0, 25, 4) / 100)
        idx = g.add_input("-loop", "1", "-i", str(path))
        lw = _even(g.w * size / 100)
        lg, out = g.lab("l"), g.lab()
        g.raw(f"[{idx}:v]scale={lw}:-2,format=rgba,colorchannelmixer=aa={alpha:.2f}[{lg}];"
              f"[{g.cur}][{lg}]overlay=x='{m}+(W-w-{2 * m})*{gx}':y='{m}+(H-h-{2 * m})*{gy}':shortest=1{_window(st, g)}[{out}]",
              out)
        return f"her logo at {st.get('position', 'bottom-right')} ({size:g}% wide)"
    if op == "zoom":
        f = _num(st.get("factor"), "factor", 1.05, 3, 1.3)
        gx, gy = GRAV.get(str(st.get("position", "center")).lower(), (.5, .5))
        cw, ch = _even(g.w / f), _even(g.h / f)
        g.lin(f"crop={cw}:{ch}:{int((g.w - cw) * gx)}:{int((g.h - ch) * gy)}", f"scale={g.w}:{g.h}:flags=lanczos")
        return f"zoomed x{f:g} ({st.get('position', 'center')})"
    if op == "fps":
        f = _num(st.get("value"), "value", 10, 60)
        g.lin(f"fps={f:g}")
        g.fps = f
        return f"{f:g} fps"
    if op == "mute":
        g.audio = False
        g.af = []
        return "sound removed"
    if op in ("volume", "normalize", "denoise_audio"):
        if not g.audio:
            raise VideoError("Is video mein awaaz nahi hai (ya pehle mute ho chuki hai).")
        if op == "volume":
            if st.get("db") not in (None, ""):
                db = _num(st.get("db"), "db", -40, 30)
                g.af.append(f"volume={db}dB")
                return f"volume {db:+g} dB"
            pct = _num(st.get("percent"), "percent", 1, 1000)
            g.af.append(f"volume={pct / 100:.4f}")
            return f"volume {pct:g}%"
        if op == "normalize":
            t = st.get("target", "social")
            lufs = {"social": -14.0, "podcast": -16.0, "broadcast": -23.0, "youtube": -14.0}.get(str(t).lower()) \
                if not isinstance(t, (int, float)) else None
            if lufs is None:
                lufs = _num(t, "target", -40, -5)
            g.af.append(f"loudnorm=I={lufs}:TP=-1.5:LRA=11")
            return f"sound level {lufs:g} LUFS"
        lvl = str(st.get("strength", "medium")).lower()
        nr = {"light": 8, "medium": 14, "strong": 22}.get(lvl)
        if nr is None:
            raise VideoError("strength: light, medium ya strong.")
        g.af += ["highpass=f=60", f"afftdn=nr={nr}:nf=-35"]
        return f"background noise reduced ({lvl})"
    raise VideoError(f"op '{op}' nahi hai. Ye hain: {', '.join(sorted(STEP_OPS))}.")


def check_steps(steps: Any) -> list[dict]:
    if not isinstance(steps, list) or not steps:
        raise VideoError("steps chahiye: [{op: ...}, ...]")
    if len(steps) > MAX_STEPS:
        raise VideoError(f"Ek baar mein {MAX_STEPS} steps tak.")
    out = []
    for st in steps:
        if not isinstance(st, dict) or not st.get("op"):
            raise VideoError("Har step {op: ...} hona chahiye.")
        op = str(st["op"]).strip().lower()
        if op not in STEP_OPS and op not in REFUSED_OPS:
            raise VideoError(f"op '{st['op']}' nahi hai. Ye hain: {', '.join(sorted(STEP_OPS))}.")
        if op in REFUSED_OPS:
            step(st, Graph({"width": 100, "height": 100, "duration": 1, "fps": 30, "has_audio": False}))
        out.append(st)
    return out


# --------------------------------------------------------------------------- encode
def _codec(fmt: str, crf: int) -> list[str]:
    if fmt == "webm":
        return ["-c:v", "libvpx-vp9", "-crf", str(crf + 8), "-b:v", "0", "-deadline", "realtime", "-cpu-used", "8",
                "-row-mt", "1", "-c:a", "libopus", "-b:a", "128k"]
    return ["-c:v", "libx264", "-preset", "veryfast", "-crf", str(crf), "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart"]


def _timeout(dur: float) -> int:
    return int(min(3600, max(180, dur * 8)))


def _run(cmd: list[str], timeout: int) -> None:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        raise VideoError("Video banane mein bahut der lag gayi; chhota hissa (trim) ya kam steps se try karein.") from None
    if r.returncode != 0:
        tail = " | ".join(x for x in (r.stderr or "").strip().splitlines()[-3:] if x)[-300:]
        raise VideoError(f"ffmpeg ne mana kar diya: {tail or 'unknown error'}")


def _finish(g: Graph, keep_size: bool = False) -> None:
    """Even size (x264 needs it), 1080p cap, square pixels, yuv420p."""
    if not keep_size and max(g.w, g.h) > MAX_LONG_SIDE:
        k = MAX_LONG_SIDE / max(g.w, g.h)
        g.w, g.h = _even(g.w * k), _even(g.h * k)
        g.lin(f"scale={g.w}:{g.h}:flags=lanczos")
    g.lin(f"scale=trunc(iw/2)*2:trunc(ih/2)*2", "setsar=1", "format=yuv420p")


def _read_out(path: str) -> bytes:
    size = os.path.getsize(path)
    if size > MAX_OUT_BYTES:
        raise VideoError(f"Bana hua video {size // 1048576} MB ka hai; chat mein {MAX_OUT_BYTES // 1048576} MB tak aata hai. "
                         "Saath mein compress step / 720p resize jodiye.")
    return Path(path).read_bytes()


def edit(path: str, steps: list[dict], fmt: str = "mp4", quality: str = "good") -> dict[str, Any]:
    info = probe(path)
    fmt = fmt if fmt in FORMATS else "mp4"
    crf = QUALITY.get(str(quality or "good").lower(), 23)
    g = Graph(info)
    done = []
    try:
        for st in check_steps(steps):
            done.append(step(st, g))
        _finish(g)
        with tempfile.TemporaryDirectory() as td:
            out = os.path.join(td, "out." + fmt)
            cmd = ["ffmpeg", "-hide_banner", "-nostdin", "-y", "-i", path]
            for extra in g.inputs:
                cmd += extra
            graph = ";".join(g.segs)
            if g.audio:
                graph += f";[0:a]{','.join(g.af) or 'anull'},aresample=48000[aout]"
            cmd += ["-filter_complex", graph, "-map", f"[{g.cur}]"]
            cmd += ["-map", "[aout]"] if g.audio else ["-an"]
            cmd += ["-map_metadata", "-1", "-map_chapters", "-1", "-t", f"{g.dur:.3f}"] + _codec(fmt, crf) + [out]
            _run(cmd, _timeout(info["duration"]))
            data = _read_out(out)
            res = probe(out)
    finally:
        for t in g.tmp:
            try:
                os.unlink(t)
            except OSError:
                pass
    return {"bytes": data, "ext": fmt, "steps": done, "in": info, "out": res}


def convert(path: str, fmt: str = "mp4", quality: str = "good") -> dict[str, Any]:
    info = probe(path)
    g = Graph(info)
    _finish(g)
    fmt = fmt if fmt in FORMATS else "mp4"
    with tempfile.TemporaryDirectory() as td:
        out = os.path.join(td, "out." + fmt)
        cmd = ["ffmpeg", "-hide_banner", "-nostdin", "-y", "-i", path, "-filter_complex", ";".join(g.segs),
               "-map", f"[{g.cur}]"] + (["-map", "0:a:0"] if info["has_audio"] else ["-an"]) + \
            ["-map_metadata", "-1"] + _codec(fmt, QUALITY.get(quality, 23)) + [out]
        _run(cmd, _timeout(info["duration"]))
        return {"bytes": _read_out(out), "ext": fmt, "in": info, "out": probe(out)}


def compress(path: str, target_mb: Any = None, quality: str = "") -> dict[str, Any]:
    """Make it smaller. target_mb (or whatsapp / email) = aim for that size; else a quality level."""
    info = probe(path)
    dur = info["duration"]
    target = None
    if target_mb not in (None, ""):
        target = COMPRESS_TARGETS.get(str(target_mb).lower()) or _num(target_mb, "target_mb", 0.1, 500)
        if info["size"] <= target * 1048576 * 0.98:
            raise VideoError(f"Video pehle se {info['size'] / 1048576:.1f} MB hai, {target:g} MB se chhota.")
    with tempfile.TemporaryDirectory() as td:
        out = os.path.join(td, "out.mp4")
        if target is None:
            crf = {"high": 23, "good": 27, "small": 31}.get(str(quality or "good").lower(), 27)
            short = min(info["width"], info["height"])
            sc = f"scale=-2:{min(720, short)}" if info["height"] <= info["width"] else f"scale={min(720, short)}:-2"
            cmd = ["ffmpeg", "-hide_banner", "-nostdin", "-y", "-i", path, "-vf", f"{sc},setsar=1,format=yuv420p",
                   "-c:v", "libx264", "-preset", "medium", "-crf", str(crf), "-c:a", "aac", "-b:a", "96k",
                   "-map_metadata", "-1", "-movflags", "+faststart", out]
            _run(cmd, _timeout(dur))
            return {"bytes": _read_out(out), "ext": "mp4", "in": info, "out": probe(out), "target_mb": None}
        abr = 64 if target < 8 else 96
        total = target * 8192 * 0.94 / dur                       # kbit/s for the whole file
        for attempt in range(3):
            vbr = int(total - (abr if info["has_audio"] else 0))
            if vbr < 60:
                raise VideoError(f"{dur:.0f} second ka video {target:g} MB mein dekhne laayak nahi banega; "
                                 "pehle trim / split karein ya bada size chuniye.")
            short = 1080 if vbr > 3000 else 720 if vbr > 1200 else 480 if vbr > 500 else 360
            short = min(short, min(info["width"], info["height"]))
            sc = f"scale=-2:{_even(short)}" if info["height"] <= info["width"] else f"scale={_even(short)}:-2"
            cmd = ["ffmpeg", "-hide_banner", "-nostdin", "-y", "-i", path, "-vf", f"{sc},setsar=1,format=yuv420p",
                   "-c:v", "libx264", "-preset", "medium", "-b:v", f"{vbr}k", "-maxrate", f"{int(vbr * 1.3)}k",
                   "-bufsize", f"{int(vbr * 2)}k"] + \
                (["-c:a", "aac", "-b:a", f"{abr}k"] if info["has_audio"] else ["-an"]) + \
                ["-map_metadata", "-1", "-movflags", "+faststart", out]
            _run(cmd, _timeout(dur))
            size = os.path.getsize(out)
            if size <= target * 1048576:
                break
            total *= 0.85 * target * 1048576 / size
        else:
            raise VideoError(f"{target:g} MB tak nahi aaya ({size / 1048576:.1f} MB bana); chhota hissa ya bada size chuniye.")
        return {"bytes": _read_out(out), "ext": "mp4", "in": info, "out": probe(out), "target_mb": target}


def _canvas(ar: tuple[int, int], long: int = 1920) -> tuple[int, int]:
    long = min(long, MAX_LONG_SIDE)
    return (_even(long * ar[0] / ar[1]), long) if ar[0] < ar[1] else (long, _even(long * ar[1] / ar[0]))


def join(paths: list[str], crossfade: Any = 0, fit: str = "blur", fmt: str = "mp4") -> dict[str, Any]:
    """Clips one after another in her order, all brought to the first clip's frame size."""
    infos = [probe(p) for p in paths]
    total = sum(i["duration"] for i in infos)
    if total > MAX_SECONDS:
        raise VideoError(f"Sab clips milakar {MAX_SECONDS // 60} minute tak.")
    cf = _num(crossfade, "crossfade", 0, 3, 0)
    if cf and min(i["duration"] for i in infos) <= cf * 2:
        raise VideoError("Crossfade har clip ki lambai ke aadhe se chhota rakhiye.")
    w, h = infos[0]["width"], infos[0]["height"]
    if max(w, h) > MAX_LONG_SIDE:
        k = MAX_LONG_SIDE / max(w, h)
        w, h = _even(w * k), _even(h * k)
    w, h = _even(w), _even(h)
    segs, vl, al = [], [], []
    cmd = ["ffmpeg", "-hide_banner", "-nostdin", "-y"]
    for i, p in enumerate(paths):
        cmd += ["-i", p]
    for i, inf in enumerate(infos):
        fitf = f"scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:color=black"
        if fit == "blur" and (inf["width"] * h != inf["height"] * w):
            segs.append(f"[{i}:v]split[x{i}][y{i}];[x{i}]scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},"
                        f"boxblur=20:2[bg{i}];[y{i}]scale={w}:{h}:force_original_aspect_ratio=decrease[fg{i}];"
                        f"[bg{i}][fg{i}]overlay=(W-w)/2:(H-h)/2,fps=30,setsar=1,format=yuv420p,setpts=PTS-STARTPTS[v{i}]")
        else:
            segs.append(f"[{i}:v]{fitf},fps=30,setsar=1,format=yuv420p,setpts=PTS-STARTPTS[v{i}]")
        if inf["has_audio"]:
            segs.append(f"[{i}:a]aresample=48000,aformat=channel_layouts=stereo,asetpts=PTS-STARTPTS[a{i}]")
        else:
            segs.append(f"anullsrc=r=48000:cl=stereo,atrim=0:{inf['duration']:.3f}[a{i}]")
        vl.append(f"v{i}")
        al.append(f"a{i}")
    if cf:
        cur_v, cur_a, off = vl[0], al[0], 0.0
        for i in range(1, len(paths)):
            off += infos[i - 1]["duration"] - cf
            nv, na = f"xv{i}", f"xa{i}"
            segs.append(f"[{cur_v}][{vl[i]}]xfade=transition=fade:duration={cf}:offset={off:.3f}[{nv}]")
            segs.append(f"[{cur_a}][{al[i]}]acrossfade=d={cf}[{na}]")
            cur_v, cur_a = nv, na
        vout, aout = cur_v, cur_a
        total -= cf * (len(paths) - 1)
    else:
        segs.append("".join(f"[{v}][{a}]" for v, a in zip(vl, al)) + f"concat=n={len(paths)}:v=1:a=1[vc][ac]")
        vout, aout = "vc", "ac"
    with tempfile.TemporaryDirectory() as td:
        out = os.path.join(td, "out." + (fmt if fmt in FORMATS else "mp4"))
        cmd += ["-filter_complex", ";".join(segs), "-map", f"[{vout}]", "-map", f"[{aout}]", "-map_metadata", "-1"] + \
            _codec(fmt, 23) + [out]
        _run(cmd, _timeout(total))
        return {"bytes": _read_out(out), "ext": fmt if fmt in FORMATS else "mp4", "pieces": len(paths),
                "out": probe(out), "size": f"{w}x{h}"}


def slideshow(images: list[str], seconds: Any = 3, aspect_v: Any = "9:16", music: str | None = None, zoom: bool = True,
              music_db: Any = -6) -> dict[str, Any]:
    """Her photos -> a video: each photo shown for N seconds, soft fade between, optional gentle zoom and her music."""
    if not 1 <= len(images) <= 40:
        raise VideoError("Slideshow ke liye 1 se 40 photos.")
    sec = _num(seconds, "seconds", 1, 15, 3)
    cw, ch = _canvas(aspect(aspect_v), 1920)
    fr = 30
    segs, labels = [], []
    cmd = ["ffmpeg", "-hide_banner", "-nostdin", "-y"]
    for p in images:
        cmd += ["-loop", "1", "-framerate", str(fr), "-t", f"{sec}", "-i", p]
    for i in range(len(images)):
        base = (f"[{i}:v]scale={cw}:{ch}:force_original_aspect_ratio=decrease,pad={cw}:{ch}:(ow-iw)/2:(oh-ih)/2:color=black,"
                f"setsar=1,format=yuv420p")
        if zoom:
            n = int(sec * fr)
            base += (f",scale={cw * 2}:{ch * 2},zoompan=z='min(zoom+{0.12 / n:.5f},1.12)':d={n}:"
                     f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={cw}x{ch}:fps={fr}")
        fd = min(0.4, sec / 4)
        base += f",fade=t=in:st=0:d={fd},fade=t=out:st={sec - fd:.3f}:d={fd},trim=duration={sec},setpts=PTS-STARTPTS[s{i}]"
        segs.append(base)
        labels.append(f"[s{i}]")
    segs.append("".join(labels) + f"concat=n={len(images)}:v=1:a=0[vout]")
    total = sec * len(images)
    maps = ["-map", "[vout]"]
    if music:
        mi = len(images)
        cmd += ["-stream_loop", "-1", "-i", music]
        db = _num(music_db, "music_db", -40, 10, -6)
        segs.append(f"[{mi}:a]atrim=0:{total:.3f},volume={db}dB,afade=t=out:st={max(0, total - 2):.3f}:d=2,"
                    f"aresample=48000[aout]")
        maps += ["-map", "[aout]"]
    else:
        maps += ["-an"]
    with tempfile.TemporaryDirectory() as td:
        out = os.path.join(td, "out.mp4")
        cmd += ["-filter_complex", ";".join(segs)] + maps + ["-t", f"{total:.3f}", "-map_metadata", "-1"] + \
            _codec("mp4", 22) + [out]
        _run(cmd, _timeout(total * 3))
        return {"bytes": _read_out(out), "ext": "mp4", "photos": len(images), "seconds": total, "size": f"{cw}x{ch}"}


def add_music(video: str, music: str, music_db: Any = -16, duck: bool = True, keep_original: bool = True,
              fade_out: Any = 2) -> dict[str, Any]:
    info = probe(video)
    mj = _ffprobe(music)
    if not any(s.get("codec_type") == "audio" for s in mj.get("streams") or []):
        raise VideoError("Music wali file mein awaaz nahi hai.")
    dur = info["duration"]
    db = _num(music_db, "music_db", -40, 6, -16)
    fo = _num(fade_out, "fade_out", 0, 10, 2)
    m = f"[1:a]atrim=0:{dur:.3f},asetpts=PTS-STARTPTS,aresample=48000,aformat=channel_layouts=stereo,volume={db}dB"
    if fo:
        m += f",afade=t=out:st={max(0.0, dur - fo):.3f}:d={fo}"
    if keep_original and info["has_audio"]:
        o = "[0:a]aresample=48000,aformat=channel_layouts=stereo"
        if duck:
            graph = (f"{o},asplit[o1][o2];{m}[mu];[mu][o2]sidechaincompress=threshold=0.03:ratio=8:attack=20:release=400[md];"
                     f"[o1][md]amix=inputs=2:duration=first:normalize=0[aout]")
        else:
            graph = f"{o}[o1];{m}[mu];[o1][mu]amix=inputs=2:duration=first:normalize=0[aout]"
    else:
        graph = f"{m}[aout]"
    with tempfile.TemporaryDirectory() as td:
        out = os.path.join(td, "out.mp4")
        cmd = ["ffmpeg", "-hide_banner", "-nostdin", "-y", "-i", video, "-stream_loop", "-1", "-i", music,
               "-filter_complex", graph, "-map", "0:v:0", "-map", "[aout]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
               "-t", f"{dur:.3f}", "-map_metadata", "-1", "-movflags", "+faststart", out]
        try:
            _run(cmd, _timeout(dur))
        except VideoError:                       # the video codec cannot sit in an mp4 as is -> re-encode it
            cmd[cmd.index("copy")] = "libx264"
            _run(cmd, _timeout(dur))
        return {"bytes": _read_out(out), "ext": "mp4", "in": info, "out": probe(out),
                "original_sound": bool(keep_original and info["has_audio"]), "ducked": bool(duck and keep_original and info["has_audio"])}


def frames(path: str, at: list | None = None, every: Any = None, count: Any = None, sheet: bool = False,
           width: Any = None) -> dict[str, Any]:
    """Still pictures from the video (a thumbnail, frames at times, or one contact sheet)."""
    info = probe(path)
    dur = info["duration"]
    if at:
        times = [min(secs(t, "at"), max(0.0, dur - 0.05)) for t in at][:24]
    elif every not in (None, ""):
        e = secs(every, "every")
        if e < 0.5:
            raise VideoError("every kam se kam 0.5 second.")
        times = [round(t * e, 3) for t in range(int(dur // e) + 1)][:24]
    else:
        n = int(_num(count, "count", 1, 24, 9 if sheet else 1))
        times = [round(dur * (i + 0.5) / n, 3) for i in range(n)]
    wpx = int(_num(width, "width", 160, 3840, min(1280, max(info["width"], info["height"]))))
    pics = []
    with tempfile.TemporaryDirectory() as td:
        for i, t in enumerate(times):
            out = os.path.join(td, f"f{i}.jpg")
            sc = f"scale='if(gt(iw,ih),{wpx},-2)':'if(gt(iw,ih),-2,{wpx})'"
            _run(["ffmpeg", "-hide_banner", "-nostdin", "-y", "-ss", f"{t:.3f}", "-i", path, "-frames:v", "1",
                  "-vf", sc, "-q:v", "3", "-map_metadata", "-1", out], 90)
            if os.path.exists(out):
                pics.append((t, Path(out).read_bytes()))
    if not pics:
        raise VideoError("Koi frame nahi nikla.")
    if not sheet:
        return {"frames": [{"at": t, "bytes": b} for t, b in pics]}
    from PIL import Image, ImageDraw
    ims = [Image.open(io.BytesIO(b)).convert("RGB") for _, b in pics]
    cols = 3 if len(ims) > 4 else 2 if len(ims) > 1 else 1
    tw = 480
    th = int(tw * ims[0].height / ims[0].width)
    rows = math.ceil(len(ims) / cols)
    pad = 8
    sheet_im = Image.new("RGB", (cols * (tw + pad) + pad, rows * (th + pad) + pad), (18, 18, 24))
    d = ImageDraw.Draw(sheet_im)
    for i, (im, (t, _)) in enumerate(zip(ims, pics)):
        x, y = pad + (i % cols) * (tw + pad), pad + (i // cols) * (th + pad)
        sheet_im.paste(im.resize((tw, th)), (x, y))
        lab = f"{int(t // 60)}:{t % 60:04.1f}"
        d.rectangle((x, y + th - 22, x + 64, y + th), fill=(0, 0, 0))
        d.text((x + 6, y + th - 18), lab, fill=(255, 255, 255))
    buf = io.BytesIO()
    sheet_im.save(buf, "JPEG", quality=88)
    return {"sheet": buf.getvalue(), "times": [t for t, _ in pics]}


def gif(path: str, start: Any = 0, end: Any = None, width: Any = 480, fps: Any = 12) -> dict[str, Any]:
    info = probe(path)
    a = secs(start, "start")
    b = min(secs(end, "end"), info["duration"]) if end not in (None, "") else min(info["duration"], a + 6)
    if b - a < 0.3:
        raise VideoError("GIF ke liye kam se kam 0.3 second chuniye.")
    if b - a > 15:
        raise VideoError("GIF 15 second tak (bada GIF bahut bhaari hota hai); chhota hissa chuniye.")
    w = int(_num(width, "width", 120, 960, 480))
    f = _num(fps, "fps", 5, 25, 12)
    with tempfile.TemporaryDirectory() as td:
        out = os.path.join(td, "out.gif")
        graph = (f"[0:v]fps={f:g},scale={w}:-2:flags=lanczos,split[a][b];[a]palettegen=max_colors=160:stats_mode=diff[p];"
                 f"[b][p]paletteuse=dither=bayer:bayer_scale=4")
        _run(["ffmpeg", "-hide_banner", "-nostdin", "-y", "-ss", f"{a}", "-t", f"{b - a:.3f}", "-i", path,
              "-filter_complex", graph, "-loop", "0", out], 300)
        data = _read_out(out)
    return {"bytes": data, "ext": "gif", "from": a, "to": b}


def split(path: str, every: Any = None, at: list | None = None) -> list[dict[str, Any]]:
    """Parts by length (WhatsApp Status = 30 / 60 s) or at times. Each part re-encoded so cuts land exactly."""
    info = probe(path)
    dur = info["duration"]
    if at:
        cuts = sorted({secs(t, "at") for t in at if 0 < secs(t, "at") < dur})
    elif every not in (None, ""):
        e = secs(every, "every")
        if e < 2:
            raise VideoError("every kam se kam 2 second.")
        cuts = [round(e * i, 3) for i in range(1, int(math.ceil(dur / e)))]
    else:
        raise VideoError("split: every (jaise 30) ya at [times] bataiye.")
    bounds = [0.0] + cuts + [dur]
    if len(bounds) - 1 > 20:
        raise VideoError("20 hisson tak; every bada rakhiye.")
    parts = []
    with tempfile.TemporaryDirectory() as td:
        for i in range(len(bounds) - 1):
            a, b = bounds[i], bounds[i + 1]
            if b - a < 0.2:
                continue
            out = os.path.join(td, f"p{i}.mp4")
            _run(["ffmpeg", "-hide_banner", "-nostdin", "-y", "-ss", f"{a}", "-i", path, "-t", f"{b - a:.3f}",
                  "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2,setsar=1,format=yuv420p", "-map", "0:v:0"]
                 + (["-map", "0:a:0"] if info["has_audio"] else ["-an"]) + ["-map_metadata", "-1"] + _codec("mp4", 22) + [out],
                 _timeout(b - a))
            parts.append({"from": a, "to": b, "bytes": _read_out(out), "ext": "mp4"})
    return parts


def combine(main: str, second: str, layout: str = "pip", position: str = "bottom-right", size_pct: Any = 30,
            audio: str = "main") -> dict[str, Any]:
    """Two videos in one frame: picture-in-picture, side by side or top / bottom. Sound from the main one (or both)."""
    a, b = probe(main), probe(second)
    layout = str(layout or "pip").lower()
    if layout == "pip":
        w, h = _even(a["width"]), _even(a["height"])
        if max(w, h) > MAX_LONG_SIDE:
            k = MAX_LONG_SIDE / max(w, h)
            w, h = _even(w * k), _even(h * k)
        sw = _even(w * _num(size_pct, "size_pct", 10, 60, 30) / 100)
        gx, gy = GRAV.get(str(position).lower(), (1, 1))
        m = int(min(w, h) * 0.04)
        vg = (f"[0:v]scale={w}:{h},setsar=1[m];[1:v]scale={sw}:-2,setsar=1[s];"
              f"[m][s]overlay=x='{m}+(W-w-{2 * m})*{gx}':y='{m}+(H-h-{2 * m})*{gy}':eof_action=pass[v]")
        dur = a["duration"]
    elif layout in ("side_by_side", "top_bottom"):
        if layout == "side_by_side":
            hh = _even(min(a["height"], b["height"], 1080))
            vg = f"[0:v]scale=-2:{hh},setsar=1[l];[1:v]scale=-2:{hh},setsar=1[r];[l][r]hstack=inputs=2:shortest=1[v]"
        else:
            ww = _even(min(a["width"], b["width"], 1080))
            vg = f"[0:v]scale={ww}:-2,setsar=1[l];[1:v]scale={ww}:-2,setsar=1[r];[l][r]vstack=inputs=2:shortest=1[v]"
        dur = min(a["duration"], b["duration"])
    else:
        raise VideoError("layout: pip (chhota video kone mein), side_by_side ya top_bottom.")
    vg = vg.replace("[v]", "[vx]") + ";[vx]scale=trunc(iw/2)*2:trunc(ih/2)*2,format=yuv420p[v]"
    maps = ["-map", "[v]"]
    if audio == "both" and a["has_audio"] and b["has_audio"]:
        vg += ";[0:a][1:a]amix=inputs=2:duration=first[a]"
        maps += ["-map", "[a]"]
    elif audio == "second" and b["has_audio"]:
        maps += ["-map", "1:a:0"]
    elif a["has_audio"]:
        maps += ["-map", "0:a:0"]
    else:
        maps += ["-an"]
    with tempfile.TemporaryDirectory() as td:
        out = os.path.join(td, "out.mp4")
        _run(["ffmpeg", "-hide_banner", "-nostdin", "-y", "-i", main, "-i", second, "-filter_complex", vg] + maps +
             ["-t", f"{dur:.3f}", "-map_metadata", "-1"] + _codec("mp4", 22) + [out], _timeout(dur))
        return {"bytes": _read_out(out), "ext": "mp4", "out": probe(out), "layout": layout}


# --------------------------------------------------------------------------- captions
_SRT_T = re.compile(r"(\d{1,2}):(\d{2}):(\d{2})[,.](\d{1,3})")


def parse_srt(text: str) -> list[dict[str, Any]]:
    cues = []
    for block in re.split(r"\n\s*\n", (text or "").replace("\r", "").strip()):
        lines = [x for x in block.split("\n") if x.strip()]
        for i, ln in enumerate(lines):
            if "-->" in ln:
                ts = _SRT_T.findall(ln)
                if len(ts) == 2:
                    a, b = [int(h) * 3600 + int(m) * 60 + int(s) + int(ms.ljust(3, "0")) / 1000 for h, m, s, ms in ts]
                    txt = " ".join(lines[i + 1:]).strip()
                    if txt and b > a:
                        cues.append({"start": a, "end": b, "text": txt[:200]})
                break
    if not cues:
        raise VideoError("SRT mein koi caption nahi mila (00:00:01,000 --> 00:00:03,000 jaisa format).")
    return cues[:3000]


def _srt_time(x: float) -> str:
    ms = int(round(x * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def to_srt(cues: list[dict[str, Any]]) -> str:
    return "\n".join(f"{i}\n{_srt_time(c['start'])} --> {_srt_time(c['end'])}\n{c['text']}\n" for i, c in enumerate(cues, 1))


def auto_cues(path: str, language: str | None = None) -> list[dict[str, Any]] | None:
    """Captions from the speech (faster-whisper when installed). None when it is not available."""
    from ..videoedit import captions as vc
    words = vc.whisper_words(path, language)
    if not words:
        return None
    out = []
    for c in vc.cues(words):
        txt = str(c.get("text") or "").strip()
        if txt:
            out.append({"start": float(c["start"]), "end": float(c["end"]), "text": txt})
    return out or None


def _ass_time(x: float) -> str:
    cs = int(round(x * 100))
    return f"{cs // 360000}:{cs // 6000 % 60:02d}:{cs // 100 % 60:02d}.{cs % 100:02d}"


def to_ass(cues: list[dict[str, Any]], w: int, h: int, position: str = "bottom", size: Any = None, color: str = "white",
           box: bool = False) -> str:
    """An ASS script at the video's own pixel size, so font size and margins are real pixels."""
    from ..imgedit.ops import _rgb
    short = min(w, h)
    fs = int(short * _num(size, "size", 2, 15, 6.5 if h > w else 5.5) / 100)
    r, g, b = _rgb(color, "white")
    align = {"bottom": 2, "top": 8, "center": 5, "middle": 5}.get(str(position).lower(), 2)
    mv = int(h * (0.12 if h > w else 0.07)) if align != 5 else 0
    style = (f"Style: Cap,Poppins,{fs},&H00{b:02X}{g:02X}{r:02X},&H00FFFFFF,&H00000000,&H90000000,-1,0,0,0,100,100,0,0,"
             f"{3 if box else 1},{max(2, fs // 14)},0,{align},{int(w * .06)},{int(w * .06)},{mv},1")
    head = ("[Script Info]\nScriptType: v4.00+\nWrapStyle: 0\nScaledBorderAndShadow: yes\n"
            f"PlayResX: {w}\nPlayResY: {h}\n\n[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
            "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, "
            "Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n" + style +
            "\n\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")
    lines = []
    for c in cues:
        txt = re.sub(r"[{}\\]", "", str(c["text"])).replace("\n", " ").strip()
        lines.append(f"Dialogue: 0,{_ass_time(c['start'])},{_ass_time(c['end'])},Cap,,0,0,0,,{txt}")
    return head + "\n".join(lines) + "\n"


def burn_captions(path: str, cues: list[dict[str, Any]], position: str = "bottom", size: Any = None,
                  color: str = "white", box: bool = False) -> dict[str, Any]:
    """Captions burned into the picture (libass with complex shaping, so Hindi joins letters properly)."""
    info = probe(path)
    w, h = _even(info["width"]), _even(info["height"])
    if max(w, h) > MAX_LONG_SIDE:
        k = MAX_LONG_SIDE / max(w, h)
        w, h = _even(w * k), _even(h * k)
    ass = to_ass(cues, w, h, position, size, color, box)
    with tempfile.TemporaryDirectory() as td:
        ap = os.path.join(td, "c.ass")
        Path(ap).write_text(ass, encoding="utf-8")
        out = os.path.join(td, "out.mp4")
        vf = f"scale={w}:{h},setsar=1,ass=filename={ap}:fontsdir={FONT_DIR}:shaping=complex,format=yuv420p"
        _run(["ffmpeg", "-hide_banner", "-nostdin", "-y", "-i", path, "-vf", vf, "-map", "0:v:0"]
             + (["-map", "0:a:0"] if info["has_audio"] else ["-an"]) + ["-map_metadata", "-1"] + _codec("mp4", 22) + [out],
             _timeout(info["duration"]))
        return {"bytes": _read_out(out), "ext": "mp4", "srt": to_srt(cues), "cues": len(cues), "out": probe(out)}
