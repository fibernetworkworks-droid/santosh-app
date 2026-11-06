"""HOOLA FRAMES Phase 2 AVATAR FILMS: a SPEC -> a deterministic talking film (v0.476).

The model sends a spec, never HTML, on this path:

    {"shape": "talking_head" | "product" | "reel",
     "script": "...one short line per beat...",          # what the voice says
     "title": "...", "brand": {"name": "...", "color": "#7C3AED"},
     "items": [{"name", "price", "note", "photo"}],      # product shape
     "cta": {"text": "...", "image": "assets/cta.png"},  # closing card (UPI QR etc.)
     "avatar": "assets/avatar.jpg",                       # her photo; else an illustrated disc
     "lang": "hi", "voice": "chatterbox", "aspect": "16:9", "silent": false}

The worker (frames.do_avatar_film) speaks each sentence with the Model Lab (Chatterbox),
pads every WAV to a whole-frame scene span, concatenates one voice track, aligns words
with on-box faster-whisper (captions.whisper_words; without it words are shared out by
length - deterministic, marked estimated), then this module builds the composition:

    timing_plan(sentences, spans, speech, words)  -> scenes + caption cues (absolute time)
    build_html(spec, plan, assets)                -> index.html honouring the 12 rules

Same spec + same audio lengths -> byte-identical HTML (test-pinned). No clock, no dice,
no network in the generated composition; fonts are the bundled Noto families. Real data
only: prices, names, QR come from the spec exactly as given - the builder invents nothing.
"""
from __future__ import annotations

import html as _html
import math
import re
from typing import Any

from .frames import FramesError

SHAPES = ("talking_head", "product", "reel")
VOICE_MODEL_DEFAULT = "chatterbox"
VOICE_LANG_DEFAULT = "hi"
MAX_SENTENCES = 12
MAX_TOTAL_CHARS = 2400
MAX_PIECE_CHARS = 580          # one lab.voice() call caps at 600 - stay under it
FPS = 30
BREATH_S = 0.35                # silence glued after every spoken sentence
HOLD_S = 1.2                   # end hold on the last scene
MIN_SCENE_S = 1.2
ESTIMATE_CPS = 13.0            # silent mode: characters of script read per second
CTA_SCENE_S = 2.2              # the closing card, when a cta is given

_DIMS = {"16:9": (1920, 1080), "9:16": (1080, 1920), "1:1": (1080, 1080)}
_IMG_OK = re.compile(r"^assets/[A-Za-z0-9][A-Za-z0-9._-]*\.(png|jpg|jpeg|webp)$")
_HEX = re.compile(r"^#[0-9a-fA-F]{6}$")
_FONT = "'Noto Sans','Noto Sans Devanagari',sans-serif"

_DEFAULT_COLOR = {"talking_head": "#4F46E5", "product": "#0F766E", "reel": "#7C3AED"}


def _esc(s: Any) -> str:
    return _html.escape(str(s), quote=True)


def snap(x: float, fps: int = FPS) -> float:
    """Up to a whole frame - film time is frames."""
    return math.ceil(x * fps - 1e-6) / fps


# ------------------------------------------------------------------ the spec ---

def split_sentences(script: str) -> list[str]:
    """Sentence beats: split on .!? and the Hindi danda; hard-split pieces the TTS cap would refuse."""
    text = re.sub(r"\s+", " ", (script or "").strip())
    if not text:
        return []
    out: list[str] = []
    for part in re.split(r"(?<=[.!?।])\s+", text):
        p = part.strip()
        while len(p) > MAX_PIECE_CHARS:
            cut = p.rfind(",", 0, MAX_PIECE_CHARS)
            if cut < MAX_PIECE_CHARS // 2:
                cut = p.rfind(" ", 0, MAX_PIECE_CHARS)
            if cut < MAX_PIECE_CHARS // 2:
                cut = MAX_PIECE_CHARS
            out.append(p[:cut + 1].strip())
            p = p[cut + 1:].strip()
        if p:
            out.append(p)
    return out


def _asset(name: Any, what: str) -> str:
    n = str(name or "").strip()
    if not n:
        return ""
    if not _IMG_OK.match(n):
        raise FramesError(f"{what}: photo ka naam assets/<naam>.png|jpg|jpeg|webp jaisa hona chahiye (mil: {n!r}).")
    return n


def validate_spec(spec: dict) -> dict:
    """Honest gate: everything wrong is refused here, before any TTS or render."""
    if not isinstance(spec, dict):
        raise FramesError("spec ek object hona chahiye (shape, script, ...).")
    shape = str(spec.get("shape") or "talking_head").strip()
    if shape not in SHAPES:
        raise FramesError(f"shape {shape!r} nahi jaanta; inme se ek: {', '.join(SHAPES)}")
    silent = bool(spec.get("silent"))
    sentences = split_sentences(str(spec.get("script") or ""))
    if not sentences and not silent:
        raise FramesError("script khaali hai - jo baat bolni hai woh script mein dijiye.")
    if len(sentences) > MAX_SENTENCES:
        raise FramesError(f"script ke {len(sentences)} vaakya - {MAX_SENTENCES} se zyada nahi (chhoti film behtar hoti hai).")
    if sum(len(s) for s in sentences) > MAX_TOTAL_CHARS:
        raise FramesError(f"script {MAX_TOTAL_CHARS} characters se lambi hai - use chhota kijiye.")

    items: list[dict[str, str]] = []
    for i, it in enumerate(spec.get("items") or []):
        if not isinstance(it, dict) or not str(it.get("name") or "").strip():
            raise FramesError(f"item {i + 1}: naam zaroori hai.")
        items.append({"name": str(it.get("name")).strip(),
                      "price": str(it.get("price") or "").strip(),
                      "note": str(it.get("note") or "").strip(),
                      "photo": _asset(it.get("photo"), f"item {i + 1} ka photo")})
    if shape == "product" and not items:
        raise FramesError("product film mein items chahiye (naam + price; photo file_id se aati hai).")

    aspect = "9:16" if shape == "reel" else str(spec.get("aspect") or "16:9")
    if aspect not in _DIMS:
        raise FramesError("aspect 16:9, 9:16 ya 1:1 hona chahiye (reel hamesha 9:16).")

    brand = spec.get("brand") if isinstance(spec.get("brand"), dict) else {}
    color = str(brand.get("color") or "").strip()
    if not _HEX.match(color):
        color = _DEFAULT_COLOR[shape]

    cta = spec.get("cta") if isinstance(spec.get("cta"), dict) else {}
    return {"shape": shape, "silent": silent,
            "sentences": sentences,
            "title": str(spec.get("title") or "").strip(),
            "brand_name": str(brand.get("name") or "").strip(),
            "color": color,
            "items": items,
            "cta_text": str(cta.get("text") or "").strip(),
            "cta_image": _asset(cta.get("image"), "cta ka image"),
            "avatar": _asset(spec.get("avatar"), "avatar"),
            "aspect": aspect, "dims": _DIMS[aspect],
            "lang": str(spec.get("lang") or VOICE_LANG_DEFAULT).strip() or VOICE_LANG_DEFAULT,
            "voice_model": str(spec.get("voice") or VOICE_MODEL_DEFAULT).strip() or VOICE_MODEL_DEFAULT}


# ------------------------------------------------------------------ the plan ---

def scene_span(speech: float, *, is_last: bool, has_cta: bool) -> float:
    """One scene's final length: the speech, a breath after it, and a hold on the last -
    long enough for the closing card when there is one. Whole frames."""
    tail = BREATH_S if not is_last else (max(HOLD_S, CTA_SCENE_S) if has_cta else HOLD_S)
    return snap(max(MIN_SCENE_S, float(speech) + tail))


def timing_plan(sentences: list[str], spans: list[float], speech: list[float],
                words: list[dict[str, Any]] | None = None, fps: int = FPS) -> dict[str, Any]:
    """Scenes (frame-aligned) + caption cues in absolute film time.

    spans: final per-sentence scene lengths (already snapped - the WAVs are padded to
    exactly these), speech: the spoken seconds inside each span. words: absolute-time
    word timestamps (faster-whisper) or None for the deterministic estimate.
    """
    from ..videoedit.captions import cues, words_from_segments
    scenes, t = [], 0.0
    for i, text in enumerate(sentences):
        span = round(float(spans[i]), 3)
        scenes.append({"text": text, "start": round(t, 3), "dur": span,
                       "speech": round(min(float(speech[i]), span), 3)})
        t += span
    total = round(t, 3)
    if not words:
        segs = [{"start": sc["start"],
                 "end": sc["start"] + max(0.6, sc["speech"]), "text": sc["text"]} for sc in scenes]
        words = words_from_segments(segs, total)
        estimated = True
    else:
        estimated = False
    # group per scene so no cue straddles a scene boundary
    cue_list: list[dict[str, Any]] = []
    for i, sc in enumerate(scenes):
        end = sc["start"] + sc["dur"]
        mine = [w for w in (words or [])
                if sc["start"] <= (w["start"] + w["end"]) / 2 < end]
        for c in cues(mine):
            cue_list.append({"start": round(max(c["start"], sc["start"]), 3),
                             "end": round(min(c["end"], end - 0.05), 3),
                             "text": c["text"], "scene": i})
    cue_list = [c for c in cue_list if c["end"] - c["start"] >= 0.2]
    return {"fps": fps, "total": total, "scenes": scenes, "cues": cue_list, "estimated": estimated}


# ------------------------------------------------------------------ the html ---

def _css(spec: dict, plan: dict) -> str:
    w, h = spec["dims"]
    return f"""
  <style>
    :root {{ --brand: {spec['color']}; --ground: #101426; --ink: #ffffff; --muted: #B8C0D9; }}
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    html, body {{ width: {w}px; height: {h}px; overflow: hidden; background: var(--ground);
                 font-family: {_FONT}; color: var(--ink); }}
    #root {{ width: 100%; height: 100%; position: relative; }}
    .cap {{ font-weight: 700; line-height: 1.3; }}
  </style>"""


def _audio(plan: dict) -> str:
    return (f'    <audio id="voice" class="clip" data-start="0" data-duration="{plan["total"]}"'
            f' data-track-index="0" src="assets/voice.wav"></audio>\n')


def _avatar_box(spec: dict, total: float, side: str = "left") -> str:
    a = spec["avatar"]
    w, h = spec["dims"]
    size = int(min(w, h) * 0.30)
    inner = (f'<img src="{_esc(a)}" alt="" style="width:100%;height:100%;object-fit:cover;'
             f'border-radius:28px;display:block"/>'
             if a else
             f'<div style="width:100%;height:100%;border-radius:50%;display:flex;align-items:center;'
             f'justify-content:center;background:linear-gradient(140deg,var(--brand),#1E293B);'
             f'color:#fff;font-size:{size // 4}px;font-weight:800;">'
             f'{_esc((spec["brand_name"] or "H")[:2].upper())}</div>')
    pos = (f"left:6%;top:{(h - size) // 2}px;" if side == "left"
           else f"left:{(w - size) // 2}px;top:{int(h * 0.62)}px;")
    return (f'    <div id="avatarbox" class="clip" data-start="0" data-duration="{total}" data-track-index="1" '
            f'style="position:absolute;{pos}width:{size}px;height:{size}px;">\n'
            f'      <div class="in" style="width:100%;height:100%;">{inner}</div>\n    </div>\n')


def _cta_start(spec: dict, plan: dict) -> float:
    """The closing card opens after the last spoken word (the last scene's hold is
    CTA_SCENE_S-long when a card exists, so it always gets real screen time)."""
    last = plan["scenes"][-1] if plan["scenes"] else None
    after_speech = (last["start"] + last["speech"] + 0.3) if last else 0.0
    return max(plan["total"] - CTA_SCENE_S, after_speech)


def _cue_divs(spec: dict, plan: dict, css_class: str, style: str, track: int) -> str:
    out = []
    for i, c in enumerate(plan["cues"]):
        dur = round(c["end"] - c["start"], 3)
        out.append(f'    <div id="cue-{i}" class="clip {css_class}" data-start="{c["start"]}" '
                   f'data-duration="{dur}" data-track-index="{track}" '
                   f'style="position:absolute;{style}"><span data-var-text="{_esc(c["text"])}">'
                   f'{_esc(c["text"])}</span></div>')
    return "\n".join(out) + "\n"


def _cta_div(spec: dict, plan: dict, start: float) -> str:
    dur = round(plan["total"] - start, 3)
    w, h = spec["dims"]
    img = (f'<img src="{_esc(spec["cta_image"])}" alt="" '
           f'style="height:{int(h * 0.34)}px;border-radius:20px;display:block"/>'
           if spec["cta_image"] else "")
    text = (f'<div style="font-size:{int(h * 0.05)}px;font-weight:800;" '
            f'data-var-text="{_esc(spec["cta_text"])}">{_esc(spec["cta_text"])}</div>' if spec["cta_text"] else "")
    return (f'    <div id="cta" class="clip" data-start="{round(start, 3)}" data-duration="{dur}" '
            f'data-track-index="4" style="position:absolute;left:5%;top:5%;width:90%;height:90%;'
            f'background:var(--brand);border-radius:32px;display:flex;flex-direction:column;'
            f'align-items:center;justify-content:center;gap:{int(h * 0.03)}px;">\n'
            f'      <div class="in" style="display:flex;flex-direction:column;align-items:center;'
            f'gap:{int(h * 0.03)}px;">{img}{text}</div>\n    </div>\n')


def _script(plan: dict, reel: bool = False) -> str:
    lines = ["    <script>", "      const tl = gsap.timeline({ paused: true });"]
    for i, c in enumerate(plan["cues"]):
        at = c["start"]
        if reel:
            lines.append(f'      tl.from("#cue-{i}", {{ opacity: 0, scale: 0.92, duration: 0.3 }}, {at});')
        else:
            lines.append(f'      tl.from("#cue-{i}", {{ opacity: 0, y: 26, duration: 0.3 }}, {at});')
    lines += ['      window.__timelines = window.__timelines || {};',
              '      window.__timelines.main = tl;', '    </script>']
    return "\n".join(lines) + "\n"


def build_html(spec: dict, plan: dict) -> str:
    """The deterministic composition. Same spec + same plan -> byte-identical output."""
    shape, dims = spec["shape"], spec["dims"]
    w, h = dims
    total = plan["total"]
    head = (f"<!doctype html>\n<html lang=\"{_esc(spec['lang'])}\">\n<head>\n"
            f'  <meta charset="UTF-8"/>\n  <meta name="viewport" content="width={w}, height={h}"/>\n'
            f"{_css(spec, plan)}\n</head>\n<body>\n"
            f'  <div id="root" data-composition-id="main" data-start="0" data-duration="{total}" '
            f'data-width="{w}" data-height="{h}" data-fps="{plan["fps"]}">\n')
    brand_line = (f'    <div id="brand" class="clip" data-start="0" data-duration="{total}" data-track-index="2" '
                  f'style="position:absolute;left:5%;top:5%;font-size:{int(h * 0.032)}px;'
                  f'font-weight:600;color:var(--muted);" data-var-text="{_esc(spec["brand_name"])}">'
                  f'{_esc(spec["brand_name"])}</div>\n') if spec["brand_name"] else ""
    tail = "  </div>\n</body>\n</html>\n"

    if shape == "talking_head":
        body = "" if spec["silent"] else _audio(plan)
        body += _avatar_box(spec, total, "left")
        body += brand_line
        cap_style = (f"right:5%;top:{int(h * 0.2)}px;width:{int(w * 0.44)}px;"
                     f"font-size:{int(h * 0.072)}px;color:var(--ink);")
        body += _cue_divs(spec, plan, "cap", cap_style, 3)
        if spec["cta_text"] or spec["cta_image"]:
            body += _cta_div(spec, plan, _cta_start(spec, plan))
        return head + body + _script(plan) + tail

    if shape == "product":
        body = "" if spec["silent"] else _audio(plan)
        body += brand_line
        first = plan["scenes"][0]
        if spec["title"]:
            body += (f'    <div id="titlecard" class="clip cap" data-start="0" data-duration="{first["dur"]}" '
                     f'data-track-index="1" style="position:absolute;left:8%;top:{int(h * 0.3)}px;'
                     f'width:84%;font-size:{int(h * 0.09)}px;" data-var-text="{_esc(spec["title"])}">'
                     f'{_esc(spec["title"])}</div>\n')
        for i, sc in enumerate(plan["scenes"]):
            item = spec["items"][i] if i < len(spec["items"]) else None
            inner = ""
            if item:
                photo = (f'<img src="{_esc(item["photo"])}" alt="" '
                         f'style="width:100%;height:100%;object-fit:contain;display:block"/>'
                         if item["photo"] else "")
                inner = (f'<div class="in" style="display:flex;align-items:center;gap:{int(w * 0.04)}px;'
                         f'width:100%;">'
                         f'<div style="width:{int(w * 0.34)}px;height:{int(w * 0.34)}px;'
                         f'background:#1B2240;border-radius:24px;overflow:hidden;">{photo}</div>'
                         f'<div style="flex:1;">'
                         f'<div style="font-size:{int(h * 0.055)}px;font-weight:700;" '
                         f'data-var-text="{_esc(item["name"])}">{_esc(item["name"])}</div>'
                         + (f'<div style="font-size:{int(h * 0.075)}px;font-weight:800;color:var(--brand);" '
                            f'data-var-text="{_esc(item["price"])}">{_esc(item["price"])}</div>'
                            if item["price"] else "")
                         + (f'<div style="font-size:{int(h * 0.032)}px;color:var(--muted);" '
                            f'data-var-text="{_esc(item["note"])}">{_esc(item["note"])}</div>'
                            if item["note"] else "")
                         + '</div></div>')
            else:
                inner = (f'<div class="in" style="font-size:{int(h * 0.055)}px;font-weight:700;">'
                         f'{_esc(sc["text"])}</div>')
            body += (f'    <div id="scene-{i}" class="clip cap" data-start="{sc["start"]}" '
                     f'data-duration="{sc["dur"]}" data-track-index="3" '
                     f'style="position:absolute;left:8%;top:{int(h * 0.26)}px;width:84%;'
                     f'display:flex;align-items:center;">{inner}</div>\n')
        if spec["cta_text"] or spec["cta_image"]:
            body += _cta_div(spec, plan, _cta_start(spec, plan))
        return head + body + _script(plan) + tail

    # reel: 9:16 kinetic captions
    body = "" if spec["silent"] else _audio(plan)
    body += (f'    <div id="brand" class="clip" data-start="0" data-duration="{total}" data-track-index="1" '
             f'style="position:absolute;left:0;top:{int(h * 0.06)}px;width:100%;text-align:center;'
             f'font-size:{int(h * 0.026)}px;font-weight:700;color:var(--muted);" '
             f'data-var-text="{_esc(spec["brand_name"])}">{_esc(spec["brand_name"])}</div>\n')
    body += _avatar_box(spec, total, "center")
    cap_style = (f"left:11%;top:{int(h * 0.34)}px;width:78%;text-align:center;"
                 f"font-size:{int(h * 0.052)}px;color:var(--ink);")
    body += _cue_divs(spec, plan, "cap", cap_style, 2)
    if spec["cta_text"] or spec["cta_image"]:
        body += _cta_div(spec, plan, _cta_start(spec, plan))
    return head + body + _script(plan, reel=True) + tail
