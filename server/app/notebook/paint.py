"""Hoola Notebook designer: finished slides, infographics and video frames PAINTED by Google's image models, the way
NotebookLM does it (its slide decks, infographics and Video Overview visuals are Nano Banana Pro images).

Why (owner, 23 Oct 2026: "quality, design and arrangement everything is very bad"): HTML templates filled with text
look like templates. A designer model lays out each slide as a whole picture (hierarchy, illustration, diagram).

How it stays correct:
- the words come from OUR plan (sources only); the model is told to render exactly those words and nothing else;
- every painted page is read back by a Gemini text model and its words are compared with the plan (all numbers must be
  there, most words must be there); a bad page is painted once more with the misses named, and if it is still wrong
  the page falls back to the HTML renderer (always exact text), so a wrong number never ships;
- slide 1 (or frame 1) is painted first and handed to the rest as the style reference, so a deck looks like one deck;
- every page gets the small "AI se bana · Hoola" label (IT Rules 2026) drawn by us, not by the model.

Models (settings, comma lists, first that works wins): slides / infographic = Nano Banana Pro (`gemini-3-pro-image`),
then Nano Banana 2.1; video frames = Nano Banana 2.1 first (cheaper, nine frames), then Pro. Blocking: run in threads.
"""
from __future__ import annotations

import io
import logging
import re
import threading
import unicodedata
from typing import Any

from ..config import get_settings

log = logging.getLogger("santosh.notebook.paint")

PRO_CHAIN = ["gemini-3-pro-image", "gemini-nano-banana-2.1", "gemini-3-pro-image-preview", "gemini-3.1-flash-image"]
FRAME_CHAIN = ["gemini-nano-banana-2.1", "gemini-3-pro-image", "gemini-3.1-flash-image", "gemini-3-pro-image-preview"]
CHECK_MODELS = ["gemini-3.8-flash", "gemini-3.6-flash", "gemini-3-flash-preview", "gemini-2.5-flash"]
AI_LABEL = "AI se bana · Hoola"
_GOOD: dict[str, str] = {}          # chain name -> model that worked last (tried first next time)
_LOCK = threading.Lock()

SCRIPTS = {"hi": "Devanagari (Hindi)", "mr": "Devanagari (Marathi)", "ne": "Devanagari (Nepali)", "sa": "Devanagari (Sanskrit)",
           "kok": "Devanagari (Konkani)", "bn": "Bengali script", "as": "Assamese (Bengali) script", "ta": "Tamil script",
           "te": "Telugu script", "kn": "Kannada script", "ml": "Malayalam script", "gu": "Gujarati script",
           "pa": "Gurmukhi (Punjabi) script", "or": "Odia script", "ur": "Urdu (Nastaliq, right to left)",
           "hinglish": "Latin letters (Hinglish: Hindi words written in English letters)"}


class PaintError(Exception):
    pass


def enabled() -> bool:
    st = get_settings()
    return bool(st.gemini_api_key) and str(getattr(st, "notebook_paint", "true")).lower() not in ("0", "false", "off", "no")


def _chain(kind: str) -> list[str]:
    st = get_settings()
    own = getattr(st, "notebook_frame_models" if kind == "frame" else "notebook_image_models", "") or ""
    chain = [m.strip() for m in own.split(",") if m.strip()] or (FRAME_CHAIN if kind == "frame" else PRO_CHAIN)
    good = _GOOD.get(kind)
    return ([good] + [m for m in chain if m != good]) if good in chain else chain


def _client():
    from google import genai
    return genai.Client(api_key=get_settings().gemini_api_key)


def _skippable(e: Exception) -> bool:
    s = str(e).lower()
    return any(w in s for w in ("not found", "404", "not supported", "unsupported", "is not available", "deprecated",
                                "permission", "403", "does not exist", "invalid model", "unknown model", "no longer",
                                "quota", "429", "resource_exhausted", "503", "unavailable", "overloaded"))


def _pull(resp) -> bytes:
    for cand in getattr(resp, "candidates", None) or []:
        for part in (getattr(getattr(cand, "content", None), "parts", None) or []):
            inline = getattr(part, "inline_data", None)
            if inline is not None and getattr(inline, "data", None) and not getattr(part, "thought", False):
                return inline.data
    return b""


def paint(prompt: str, aspect: str, kind: str = "page", refs: list[bytes] | None = None, size: str = "") -> tuple[bytes, str]:
    """One picture from the first model in the chain that answers. refs = style reference pages (JPEG/PNG bytes)."""
    from google.genai import types
    client = _client()
    size = size or str(getattr(get_settings(), "notebook_image_size", "") or "2K")
    parts: list[Any] = []
    for r in (refs or [])[:3]:
        parts.append(types.Part.from_bytes(data=r, mime_type="image/png" if r[:4] == b"\x89PNG" else "image/jpeg"))
    parts.append(prompt)
    last = ""
    for model in _chain(kind):
        for variant in ("full", "aspect", "bare"):
            kw: dict[str, Any] = {"response_modalities": ["IMAGE", "TEXT"]}
            try:
                if variant == "full":
                    kw["image_config"] = types.ImageConfig(aspect_ratio=aspect, image_size=size)
                elif variant == "aspect":
                    kw["image_config"] = types.ImageConfig(aspect_ratio=aspect)
            except Exception:
                continue
            try:
                r = client.models.generate_content(model=model, contents=parts, config=types.GenerateContentConfig(**kw))
            except Exception as e:
                last = str(e)[:300]
                low = last.lower()
                if variant != "bare" and any(w in low for w in ("image_config", "image_size", "aspect", "unknown field",
                                                                 "invalid argument", "invalid value")) and not _skippable(e):
                    continue
                break
            data = _pull(r)
            if data:
                with _LOCK:
                    _GOOD[kind] = model
                return data, model
            last = "no image returned"
            break
    raise PaintError(f"Design model ne tasveer nahi di: {last[:160]}")


# ---------------------------------------------------------------- reading the page back
def _norm(s: str) -> str:
    s = unicodedata.normalize("NFC", str(s or "")).lower()
    s = s.replace("₹", " ₹ ").replace("%", " % ")
    return re.sub(r"[^\w₹%ऀ-෿]+", " ", s)


def _words(s: str) -> list[str]:
    return [w for w in _norm(s).split() if len(w) > 1 or w.isdigit()]


def read_text(img: bytes) -> str | None:
    """All visible text on a page, read by a Gemini text model. None = could not check (no model answered)."""
    from google.genai import types
    client = _client()
    ask = ("Transcribe ALL visible text in this image exactly as written, in its own script, line by line. Do not translate, "
           "do not fix spelling, do not describe the picture. If there is no text, reply NONE.")
    mime = "image/png" if img[:4] == b"\x89PNG" else "image/jpeg"
    for model in CHECK_MODELS:
        try:
            r = client.models.generate_content(model=model, contents=[types.Part.from_bytes(data=img, mime_type=mime), ask])
            return (getattr(r, "text", "") or "").strip()
        except Exception as e:
            if _skippable(e):
                continue
            log.info("paint read_text failed: %s", e)
            return None
    return None


def check(img: bytes, expected: list[str]) -> dict[str, Any]:
    """How much of the planned text is really on the page. ok = every number there and >= 80% of the words."""
    exp = [w for line in expected for w in _words(line)]
    if not exp:
        return {"ok": True, "score": 1.0, "missing": [], "checked": False}
    seen = read_text(img)
    if seen is None:
        return {"ok": True, "score": None, "missing": [], "checked": False}
    have = set(_words(seen))
    joined = " ".join(_words(seen))
    missing = [w for w in dict.fromkeys(exp) if w not in have and w not in joined]
    nums = [w for w in exp if re.search(r"\d", w)]
    num_miss = [w for w in nums if w in missing]
    score = 1 - len(missing) / max(1, len(set(exp)))
    return {"ok": not num_miss and score >= 0.8, "score": round(score, 2), "missing": missing[:20], "checked": True}


# ---------------------------------------------------------------- finishing touches
def finish(img: bytes, width: int, height: int, label: bool = True, quality: int = 90) -> bytes:
    """Cover-fit to the exact page size, draw the AI label, return JPEG bytes."""
    from PIL import Image, ImageDraw, ImageFont
    im = Image.open(io.BytesIO(img)).convert("RGB")
    sw, sh = im.size
    scale = max(width / sw, height / sh)
    im = im.resize((max(width, round(sw * scale)), max(height, round(sh * scale))), Image.LANCZOS)
    left, top = (im.width - width) // 2, (im.height - height) // 2
    im = im.crop((left, top, left + width, top + height))
    if label:
        d = ImageDraw.Draw(im, "RGBA")
        fs = max(14, width // 90)
        try:
            from pathlib import Path
            fp = Path(__file__).resolve().parent.parent / "videoedit" / "fonts" / "NotoSansDevanagari-Bold.ttf"
            font = ImageFont.truetype(str(fp), fs)
        except Exception:
            font = ImageFont.load_default()
        tw = d.textlength(AI_LABEL, font=font)
        pad = fs // 2
        x1, y1 = width - tw - pad * 3, height - fs - pad * 3
        d.rounded_rectangle((x1, y1, width - pad, height - pad), radius=fs, fill=(0, 0, 0, 110))
        d.text((x1 + pad, y1 + pad * 0.6), AI_LABEL, fill=(255, 255, 255, 235), font=font)
    out = io.BytesIO()
    im.save(out, "JPEG", quality=quality, optimize=True, progressive=True)
    return out.getvalue()


# ---------------------------------------------------------------- briefs
DESIGN_RULES = ("Design quality: a finished page by a top presentation designer (think McKinsey / Apple keynote / The Economist "
                "graphics): one clear focal point, strong visual hierarchy (title biggest), generous margins (at least 6% on "
                "every side), aligned grid, at most 3 type sizes, high contrast text on calm areas, one consistent colour palette, "
                "crisp vector-like rendering. Any illustration, icon, chart or diagram must EXPLAIN the content (show the idea, "
                "the numbers, the comparison or the flow), never random decoration. Nothing cut off at the edges. The image IS "
                "the page edge to edge: no device mockup, no frame, no shadow around it, no page number, no logo, no watermark, "
                "no signature, no lorem ipsum.")


def _script_rule(lang: str) -> str:
    sc = SCRIPTS.get(lang or "", "")
    return (f"All text is in {sc}; use correct spelling and correct conjuncts / matras for that script. " if sc else "")


def _text_block(lines: list[tuple[str, str]]) -> str:
    out = []
    for role, text in lines:
        if str(text or "").strip():
            out.append(f'- {role}: "{str(text).strip()}"')
    return "\n".join(out)


LAYOUT_IDEA = {
    "title": "Title slide: the title very large, the subtitle under it, a bold hero illustration of the topic taking about 40% of the page.",
    "section": "Section divider: the section title large on a strong colour field, a simple symbolic illustration.",
    "bullets": "Content slide: title at the top; the points as short lines with small matching icons, laid out in a clean "
               "column or 2x2 cards; an explanatory illustration or diagram on one side.",
    "two_col": "Comparison slide: two clearly separated columns or cards with their headings and points, visually balanced, "
               "a small icon for each side; make the contrast obvious.",
    "stats": "Big-number slide: each number huge in the accent colour with its label under it, on 2-4 cards or a simple bar / "
             "proportion chart that shows the numbers to scale.",
    "quote": "Quote slide: the quote very large in an elegant serif or display font with big quotation marks, who said it under it.",
    "timeline": "Timeline slide: a horizontal timeline with dots, each date above and its event below, evenly spaced.",
    "image": "Visual slide: one large meaningful illustration with the title and one line of text.",
    "closing": "Closing slide: the key takeaway large and confident, 2-3 short next steps or a recap, warm finishing illustration.",
}


def slide_brief(sl: dict, n: int, total: int, deck: str, style_img: str, custom: str, lang: str, audience: str,
                with_ref: bool, fix: list[str] | None = None) -> tuple[str, list[str]]:
    lines: list[tuple[str, str]] = [("Small label above the title", sl.get("kicker", "")), ("Title", sl.get("title", "")),
                                    ("Subtitle", sl.get("subtitle", "")), ("Body", sl.get("body", ""))]
    for b in sl.get("bullets") or []:
        lines.append(("Point", b))
    for s in sl.get("stats") or []:
        lines.append(("Big number", f"{s.get('value', '')}  —  {s.get('label', '')}"))
    for s in sl.get("steps") or []:
        lines.append(("Timeline item", f"{s.get('when', '')}: {s.get('text', '')}"))
    for side in ("left", "right"):
        c = sl.get(side) or {}
        if c.get("heading"):
            lines.append((f"{side.title()} column heading", c["heading"]))
        for p in c.get("points") or []:
            lines.append((f"{side.title()} column point", p))
    if sl.get("quote"):
        lines.append(("Quote", sl["quote"]))
        lines.append(("Who said it", sl.get("who", "")))
    layout = sl.get("layout", "bullets")
    look = custom or style_img
    p = (f"Design slide {n} of {total} of a presentation titled \"{deck}\" as ONE finished 16:9 slide image.\n"
         f"Visual style: {look}.\n" + (f"Audience: {audience}.\n" if audience else "")
         + f"Layout: {LAYOUT_IDEA.get(layout, LAYOUT_IDEA['bullets'])}\n"
         + (f"Illustration idea: {sl['visual']}.\n" if sl.get("visual") else "")
         + "TEXT ON THE SLIDE - render exactly these words, spelled exactly, each once, and NO other words, letters or numbers "
           "anywhere (no invented labels, no fake chart axes text):\n" + _text_block(lines) + "\n"
         + _script_rule(lang) + DESIGN_RULES
         + (" Match the attached reference slide's design system exactly: same background treatment, palette, fonts, "
            "margins, icon and illustration style. Do not copy its words or its layout if this slide's layout differs." if with_ref else "")
         + (f"\nIMPORTANT: an earlier try misspelled or left out these words; render them exactly: {', '.join(fix)}" if fix else ""))
    return p, [t for _, t in lines if str(t or "").strip()]


def info_brief(js: dict, orient: str, style_img: str, custom: str, lang: str, fix: list[str] | None = None) -> tuple[str, list[str]]:
    lines: list[tuple[str, str]] = [("Title", js.get("title", "")), ("Subtitle", js.get("subtitle", ""))]
    hero = js.get("hero") or {}
    if hero.get("value"):
        lines.append(("Hero number", f"{hero.get('value')}  —  {hero.get('label', '')}"))
    for s in js.get("stats") or []:
        if isinstance(s, dict) and s.get("value"):
            lines.append(("Stat", f"{s.get('value')}  —  {s.get('label', '')}"))
    for i, sec in enumerate(js.get("sections") or [], 1):
        if not isinstance(sec, dict):
            continue
        lines.append((f"Section {i} heading", sec.get("heading", "")))
        lines.append((f"Section {i} text", sec.get("text", "")))
        for p in sec.get("points") or []:
            lines.append((f"Section {i} point", p))
    for i, s in enumerate(js.get("steps") or [], 1):
        lines.append((f"Step {i}", s if isinstance(s, str) else (s.get("text") if isinstance(s, dict) else "")))
    lines.append(("Takeaway (bottom banner)", js.get("takeaway", "")))
    shape = {"portrait": "tall portrait (phone / poster)", "landscape": "wide landscape (screen)", "square": "square (social post)"}[orient]
    p = (f"Design ONE finished {shape} infographic image that explains the topic at a glance.\n"
         f"Visual style: {custom or style_img}.\n"
         "Structure: a bold title band at the top; the hero number (if any) as the biggest element; stats as big numbers "
         "with icons or a small chart drawn to scale; each section as a clearly separated block with an icon or mini-diagram "
         "that shows its idea; steps (if any) as a numbered flow with arrows; the takeaway in a banner at the bottom. Read "
         "top-to-bottom (or left-to-right), lots of white space, every block aligned.\n"
         "TEXT ON THE INFOGRAPHIC - render exactly these words, spelled exactly, each once, and NO other words or numbers:\n"
         + _text_block(lines) + "\n" + _script_rule(lang) + DESIGN_RULES
         + (f"\nIMPORTANT: an earlier try misspelled or left out these words; render them exactly: {', '.join(fix)}" if fix else ""))
    return p, [t for _, t in lines if str(t or "").strip()]


def frame_brief(sc: dict, n: int, total: int, title: str, style_img: str, custom: str, lang: str, with_ref: bool,
                fix: list[str] | None = None) -> tuple[str, list[str]]:
    lines: list[tuple[str, str]] = [("Headline", sc.get("headline", ""))]
    for p in sc.get("points") or []:
        lines.append(("Short point", p))
    for s in sc.get("stats") or []:
        lines.append(("Big number", f"{s.get('value', '')}  —  {s.get('label', '')}"))
    p = (f"Create frame {n} of {total} of an animated explainer video titled \"{title}\" as ONE 16:9 still image.\n"
         f"Visual style: {custom or style_img}.\n"
         f"What the frame shows: {sc.get('visual') or sc.get('headline') or title}. The narrator is saying: "
         f"\"{str(sc.get('narration') or '')[:400]}\" - the picture must make that idea easy to see (a scene, a diagram or a "
         "visual metaphor with Indian everyday context where it fits).\n"
         "Composition: a rich, beautiful illustration filling the frame, with a calm area for the headline; keep the bottom "
         "15% free of text (captions go there).\n"
         "TEXT IN THE FRAME - only these words, spelled exactly, large and readable, NO other words:\n" + _text_block(lines) + "\n"
         + _script_rule(lang) + DESIGN_RULES
         + (" Keep the attached reference frame's art style, palette and type exactly (same video), new scene." if with_ref else "")
         + (f"\nIMPORTANT: an earlier try misspelled or left out these words; render them exactly: {', '.join(fix)}" if fix else ""))
    return p, [t for _, t in lines if str(t or "").strip()]


def paint_checked(brief_fn, aspect: str, kind: str, refs: list[bytes] | None, verify: bool = True) -> dict[str, Any]:
    """brief_fn(fix) -> (prompt, expected lines). Paints, reads it back, repaints once with the misses named.
    Returns {"img", "model", "check", "tries"}; raises PaintError when no good page could be made."""
    prompt, expected = brief_fn(None)
    best: dict[str, Any] | None = None
    fix: list[str] | None = None
    for attempt in (1, 2):
        if attempt == 2:
            prompt, expected = brief_fn(fix)
        img, model = paint(prompt, aspect, kind, refs)
        chk = check(img, expected) if verify else {"ok": True, "score": None, "missing": [], "checked": False}
        cur = {"img": img, "model": model, "check": chk, "tries": attempt}
        if chk["ok"]:
            return cur
        if best is None or (chk["score"] or 0) > (best["check"]["score"] or 0):
            best = cur
        fix = chk["missing"][:12]
        log.info("paint %s text check %.2f, missing %s - repainting", kind, chk["score"] or 0, fix)
    raise PaintError(f"text check failed ({best['check']['score'] if best else '?'}): {', '.join((best or {}).get('check', {}).get('missing', [])[:6])}")
