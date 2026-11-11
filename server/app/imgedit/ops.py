"""Local (no key, no network) image operations. Pure functions: image in, image out, parameters validated and clamped."""
from __future__ import annotations

import functools
import io
import math
import re
from pathlib import Path
from typing import Any, Callable

from PIL import Image, ImageChops, ImageColor, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps

MAX_IN_PIXELS = 50_000_000          # refuse bigger inputs (decompression bombs, 8K+ stitched panoramas)
MAX_SIDE = 8192                     # no output side beyond this
MAX_STEPS = 12
FONT_DIR = Path(__file__).resolve().parent.parent / "fonts"

Image.MAX_IMAGE_PIXELS = MAX_IN_PIXELS * 2     # PIL's own bomb guard stays above our explicit refusal


class EditError(ValueError):
    """A request Hoola can explain in one plain sentence."""


# --------------------------------------------------------------------------- loading and saving
def load(data: bytes) -> Image.Image:
    try:
        im = Image.open(io.BytesIO(data))
        w, h = im.size
        if w * h > MAX_IN_PIXELS:
            raise EditError(f"Photo bahut badi hai ({w}x{h}); {MAX_IN_PIXELS // 1_000_000} megapixel tak chalti hai.")
        im = ImageOps.exif_transpose(im)
        im.load()
    except EditError:
        raise
    except Exception:
        raise EditError("Yeh file photo nahi lagti; JPG / PNG / WEBP / GIF photo bhejiye.") from None
    if im.mode in ("P", "LA", "PA"):
        im = im.convert("RGBA")
    elif im.mode not in ("RGB", "RGBA", "L"):
        im = im.convert("RGB")
    return im


def _has_alpha(im: Image.Image) -> bool:
    return im.mode in ("RGBA", "LA") and im.getchannel("A").getextrema()[0] < 255


def flatten(im: Image.Image, color: str = "white") -> Image.Image:
    if im.mode == "RGBA":
        bg = Image.new("RGB", im.size, _rgb(color))
        bg.paste(im, mask=im.getchannel("A"))
        return bg
    return im.convert("RGB") if im.mode != "RGB" else im


def encode(im: Image.Image, fmt: str = "", quality: int = 92, target_kb: float | None = None) -> tuple[bytes, str]:
    """Re-encode (this alone drops EXIF / GPS). fmt png|jpg|webp, '' = png when there is transparency else jpg."""
    f = (fmt or "").lower().replace("jpeg", "jpg")
    if f not in ("png", "jpg", "webp", ""):
        raise EditError("Format png, jpg ya webp mein se chuniye.")
    if not f:
        f = "png" if _has_alpha(im) else "jpg"
    quality = int(max(20, min(100, quality)))

    def once(img: Image.Image, q: int) -> bytes:
        out = io.BytesIO()
        if f == "png":
            (img if img.mode in ("RGB", "RGBA", "L") else img.convert("RGBA")).save(out, "PNG", optimize=True)
        elif f == "jpg":
            flatten(img).save(out, "JPEG", quality=q, optimize=True, progressive=True)
        else:
            (img if img.mode in ("RGB", "RGBA") else img.convert("RGB")).save(out, "WEBP", quality=q, method=6)
        return out.getvalue()

    if not target_kb:
        return once(im, quality), f
    limit = int(float(target_kb) * 1024)
    if limit < 2048:
        raise EditError("Target size 2 KB se bada rakhiye.")
    cur = im
    best = b""
    for _ in range(14):                      # lower quality first, then shrink, until it fits
        q = 92
        while q >= 30:
            best = once(cur, q)
            if len(best) <= limit or f == "png":
                break
            q -= 8
        if len(best) <= limit:
            return best, f
        w, h = cur.size
        if min(w, h) <= 160:
            break
        cur = cur.resize((max(1, int(w * 0.85)), max(1, int(h * 0.85))), Image.LANCZOS)
    raise EditError(f"{target_kb:g} KB mein yeh photo nahi aa rahi (sabse chhota {len(best) // 1024} KB bana). "
                    "Bada target rakhiye ya photo ka size ghataiye.")


# --------------------------------------------------------------------------- small helpers
def _rgb(c: Any, default: str = "white") -> tuple[int, int, int]:
    s = str(c or default).strip()
    if re.fullmatch(r"[0-9a-fA-F]{6}", s):
        s = "#" + s
    try:
        return ImageColor.getrgb(s)[:3]
    except ValueError:
        raise EditError(f"Rang '{s}' samajh nahi aaya (jaise white, black, #ff8800).") from None


def _num(v: Any, name: str, lo: float, hi: float, default: float | None = None) -> float:
    if v is None or v == "":
        if default is None:
            raise EditError(f"{name} chahiye.")
        return default
    try:
        x = float(v)
    except (TypeError, ValueError):
        raise EditError(f"{name} ek number hona chahiye.") from None
    if math.isnan(x) or x < lo or x > hi:
        raise EditError(f"{name} {lo:g} se {hi:g} ke beech rakhiye.")
    return x


def _check_size(w: int, h: int) -> None:
    if w < 1 or h < 1:
        raise EditError("Size 1 pixel se chhota nahi ho sakta.")
    if max(w, h) > MAX_SIDE:
        raise EditError(f"Ek side {MAX_SIDE} pixel se zyada nahi ho sakti.")


def _aspect(s: Any) -> float:
    m = re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*[:x/]\s*(\d+(?:\.\d+)?)\s*", str(s or ""))
    if not m or float(m.group(2)) == 0 or float(m.group(1)) == 0:
        raise EditError("Aspect 4:5, 1:1, 16:9 jaise likhiye.")
    return float(m.group(1)) / float(m.group(2))


PRESETS = {                       # name -> (w, h) common Indian-seller / creator sizes
    "insta_post": (1080, 1350), "insta_square": (1080, 1080), "story": (1080, 1920), "reel_cover": (1080, 1920),
    "status": (1080, 1920), "youtube_thumb": (1280, 720), "youtube_banner": (2560, 1440), "facebook_cover": (1640, 624),
    "linkedin_banner": (1584, 396), "linkedin_post": (1200, 627), "x_post": (1600, 900), "whatsapp_dp": (640, 640),
    "marketplace": (1000, 1000), "amazon_main": (2000, 2000), "a4_300dpi": (2480, 3508), "a4_150dpi": (1240, 1754),
    "visiting_card": (1050, 600),
}
_GRAV = {"center": (.5, .5), "top": (.5, 0), "bottom": (.5, 1), "left": (0, .5), "right": (1, .5),
         "top-left": (0, 0), "top-right": (1, 0), "bottom-left": (0, 1), "bottom-right": (1, 1)}


# --------------------------------------------------------------------------- the operations
def op_resize(im, width=None, height=None, percent=None, preset=None, fit=None, bg="white", **_):
    w0, h0 = im.size
    if preset:
        p = PRESETS.get(str(preset).lower())
        if not p:
            raise EditError("Preset ye hain: " + ", ".join(sorted(PRESETS)))
        width, height = p
        if fit is None:                     # a feed picture fills its frame; a print / listing size keeps the whole photo
            fit = "cover" if str(preset).lower() in ("insta_post", "insta_square", "story", "reel_cover", "status",
                                                    "youtube_thumb", "whatsapp_dp") else "contain"
    if percent is not None:
        k = _num(percent, "percent", 1, 800) / 100
        width, height = round(w0 * k), round(h0 * k)
    elif width and not height:
        width = int(_num(width, "width", 1, MAX_SIDE)); height = max(1, round(h0 * width / w0))
    elif height and not width:
        height = int(_num(height, "height", 1, MAX_SIDE)); width = max(1, round(w0 * height / h0))
    elif not (width and height):
        raise EditError("width, height, percent ya preset mein se kuch bataiye.")
    width, height = int(width), int(height)
    _check_size(width, height)
    fit = str(fit or "contain").lower()
    if fit == "stretch":
        return im.resize((width, height), Image.LANCZOS)
    if fit == "cover":
        return ImageOps.fit(im, (width, height), Image.LANCZOS)
    if fit == "inside":
        c = im.copy(); c.thumbnail((width, height), Image.LANCZOS); return c
    if fit != "contain":
        raise EditError("fit: contain, cover, inside ya stretch.")
    c = im.copy(); c.thumbnail((width, height), Image.LANCZOS)
    if c.size == (width, height):
        return c
    if bg in ("transparent", "none"):
        canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        canvas.paste(c.convert("RGBA"), ((width - c.width) // 2, (height - c.height) // 2))
        return canvas
    canvas = Image.new("RGB", (width, height), _rgb(bg))
    src = c.convert("RGBA")
    canvas.paste(src, ((width - c.width) // 2, (height - c.height) // 2), src)
    return canvas


def op_crop(im, box=None, aspect=None, gravity="center", **_):
    w, h = im.size
    if box:
        if not (isinstance(box, (list, tuple)) and len(box) == 4):
            raise EditError("box [left, top, right, bottom] hona chahiye.")
        v = [float(x) for x in box]
        if all(0 <= x <= 1 for x in v):
            v = [v[0] * w, v[1] * h, v[2] * w, v[3] * h]
        l, t, r, b = (int(round(x)) for x in v)
        l, t, r, b = max(0, l), max(0, t), min(w, r), min(h, b)
        if r - l < 2 or b - t < 2:
            raise EditError("Crop box khaali hai ya photo ke bahar hai.")
        return im.crop((l, t, r, b))
    if aspect:
        a = _aspect(aspect)
        gx, gy = _GRAV.get(str(gravity or "center").lower(), (.5, .5))
        if w / h > a:
            cw, ch = round(h * a), h
        else:
            cw, ch = w, round(w / a)
        l = round((w - cw) * gx); t = round((h - ch) * gy)
        return im.crop((l, t, l + cw, t + ch))
    raise EditError("crop ke liye box ya aspect bataiye.")


def op_rotate(im, degrees=90, expand=True, fill="white", **_):
    d = _num(degrees, "degrees", -360, 360) % 360
    if d == 0:
        return im
    if d in (90, 180, 270):
        return im.transpose({90: Image.ROTATE_90, 180: Image.ROTATE_180, 270: Image.ROTATE_270}[int(d)])
    rgba = im.convert("RGBA")
    fillc = (0, 0, 0, 0) if str(fill) in ("transparent", "none") else (*_rgb(fill), 255)
    out = rgba.rotate(d, resample=Image.BICUBIC, expand=bool(expand), fillcolor=fillc)
    _check_size(*out.size)
    return out if fillc[3] == 0 else flatten(out, fill) if im.mode != "RGBA" else out


def op_flip(im, direction="h", **_):
    d = str(direction or "h").lower()
    if d in ("h", "horizontal", "mirror"):
        return ImageOps.mirror(im)
    if d in ("v", "vertical"):
        return ImageOps.flip(im)
    raise EditError("direction: h ya v.")


def _scale_rgb(im, fn):
    if im.mode == "RGBA":
        r, g, b, a = im.split()
        out = fn(Image.merge("RGB", (r, g, b)))
        out.putalpha(a)
        return out
    return fn(im.convert("RGB") if im.mode != "L" else im)


def op_adjust(im, brightness=0, contrast=0, saturation=0, sharpness=0, gamma=None, warmth=0, exposure=0, **_):
    """brightness / contrast / saturation / sharpness are percent changes (-100..100, 0 = unchanged)."""
    b = _num(brightness, "brightness", -100, 100, 0); c = _num(contrast, "contrast", -100, 100, 0)
    s = _num(saturation, "saturation", -100, 100, 0); sh = _num(sharpness, "sharpness", -100, 300, 0)
    wm = _num(warmth, "warmth", -100, 100, 0); ex = _num(exposure, "exposure", -3, 3, 0)

    def fn(x):
        if ex:
            x = x.point(lambda v: max(0, min(255, int(round(v * (2 ** ex))))))
        if gamma not in (None, ""):
            g = _num(gamma, "gamma", 0.2, 5)
            lut = [round(255 * ((i / 255) ** (1 / g))) for i in range(256)]
            x = x.point(lut * (len(x.getbands())))
        if b:
            x = ImageEnhance.Brightness(x).enhance(1 + b / 100)
        if c:
            x = ImageEnhance.Contrast(x).enhance(1 + c / 100)
        if s and x.mode != "L":
            x = ImageEnhance.Color(x).enhance(1 + s / 100)
        if sh:
            x = ImageEnhance.Sharpness(x).enhance(1 + sh / 100)
        if wm and x.mode == "RGB":
            r, g_, bl = x.split()
            k = wm / 100 * 40
            r = r.point(lambda v: max(0, min(255, int(v + k))))
            bl = bl.point(lambda v: max(0, min(255, int(v - k))))
            x = Image.merge("RGB", (r, g_, bl))
        return x
    return _scale_rgb(im, fn)


def op_auto_enhance(im, strength=1.0, **_):
    k = _num(strength, "strength", 0, 2, 1.0)

    def fn(x):
        x2 = ImageOps.autocontrast(x, cutoff=1)
        x = Image.blend(x, x2, min(1.0, k))
        if x.mode != "L":
            x = ImageEnhance.Color(x).enhance(1 + 0.08 * k)
        return x.filter(ImageFilter.UnsharpMask(radius=1.6, percent=int(60 * k), threshold=3))
    return _scale_rgb(im, fn)


def _np():
    import numpy as np
    return np


def op_filter(im, name="grayscale", amount=None, **_):
    n = str(name or "").lower()
    np = _np()
    a = None if amount in (None, "") else float(amount)

    def fn(x):
        if n in ("grayscale", "greyscale", "bw", "mono"):
            g = ImageOps.grayscale(x)
            return g.convert("RGB") if x.mode == "RGB" else g
        if n == "sepia":
            arr = np.asarray(x.convert("RGB"), dtype=np.float32)
            m = np.array([[.393, .769, .189], [.349, .686, .168], [.272, .534, .131]], dtype=np.float32)
            return Image.fromarray(np.clip(arr @ m.T, 0, 255).astype("uint8"), "RGB")
        if n == "invert":
            return ImageOps.invert(x.convert("RGB"))
        if n == "blur":
            return x.filter(ImageFilter.GaussianBlur(radius=_num(a, "amount", 0.5, 60, 4)))
        if n == "sharpen":
            return x.filter(ImageFilter.UnsharpMask(radius=2, percent=int(_num(a, "amount", 10, 400, 150)), threshold=2))
        if n == "denoise":
            return x.filter(ImageFilter.MedianFilter(size=3 if _num(a, "amount", 1, 3, 1) < 2 else 5))
        if n == "pixelate":
            px = int(_num(a, "amount", 2, 200, 12))
            w, h = x.size
            return x.resize((max(1, w // px), max(1, h // px)), Image.NEAREST).resize((w, h), Image.NEAREST)
        if n == "posterize":
            return ImageOps.posterize(x.convert("RGB"), int(_num(a, "amount", 1, 8, 3)))
        if n == "vignette":
            xr = x.convert("RGB")
            w, h = xr.size
            yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
            d = np.sqrt(((xx - w / 2) / (w / 2)) ** 2 + ((yy - h / 2) / (h / 2)) ** 2)
            k = _num(a, "amount", 0.1, 1.5, 0.6)
            mask = np.clip(1 - k * np.clip(d - 0.55, 0, None) ** 1.5, 0.15, 1)[..., None]
            return Image.fromarray((np.asarray(xr, dtype=np.float32) * mask).astype("uint8"), "RGB")
        if n == "sketch":
            g = ImageOps.grayscale(x)
            inv = ImageOps.invert(g).filter(ImageFilter.GaussianBlur(radius=_num(a, "amount", 2, 40, 12)))
            ga, ia = np.asarray(g, dtype=np.float32), np.asarray(inv, dtype=np.float32)
            return Image.fromarray(np.clip(ga * 255 / (255 - ia + 1), 0, 255).astype("uint8"), "L").convert("RGB")
        if n == "scan":                       # photo of a paper -> flat white page, dark text
            g = np.asarray(ImageOps.grayscale(x), dtype=np.float32)
            bgl = np.asarray(ImageOps.grayscale(x).filter(ImageFilter.GaussianBlur(radius=max(8, min(x.size) // 20))),
                             dtype=np.float32)
            flat = np.clip(g / (bgl + 1) * 255, 0, 255)           # divide out the uneven lighting
            white = max(1.0, float(np.percentile(flat, 90)))      # the paper is most of the page: that is the white point
            flat = np.clip(flat * 255 / white, 0, 255)
            flat = 255 * (flat / 255) ** 1.8                        # pull the greys of text darker, keep the paper white
            return Image.fromarray(np.clip(flat, 0, 255).astype("uint8"), "L")
        raise EditError("filter: grayscale, sepia, invert, blur, sharpen, denoise, pixelate, posterize, vignette, "
                        "sketch, scan.")
    return _scale_rgb(im, fn)


def op_redact(im, regions=None, mode="blur", strength=None, **_):
    """regions = [[l,t,r,b], ...] (0-1 fractions of the photo, or pixels). Privacy cover: blur / pixelate / black."""
    if not regions or not isinstance(regions, (list, tuple)):
        raise EditError("regions [[left, top, right, bottom], ...] bataiye - kaun si jagah chhupani hai.")
    if len(regions) > 40:
        raise EditError("Ek baar mein 40 jagah tak.")
    out = im.convert("RGBA") if im.mode != "RGBA" else im.copy()
    w, h = out.size
    for r in regions:
        if not (isinstance(r, (list, tuple)) and len(r) == 4):
            raise EditError("Har region [left, top, right, bottom] hona chahiye.")
        v = [float(x) for x in r]
        if all(0 <= x <= 1 for x in v):
            v = [v[0] * w, v[1] * h, v[2] * w, v[3] * h]
        l, t, rr, b = max(0, int(v[0])), max(0, int(v[1])), min(w, int(v[2])), min(h, int(v[3]))
        if rr - l < 2 or b - t < 2:
            raise EditError("Ek region photo ke bahar hai ya khaali hai.")
        patch = out.crop((l, t, rr, b))
        m = str(mode or "blur").lower()
        if m == "black":
            patch = Image.new("RGBA", patch.size, (0, 0, 0, 255))
        elif m == "pixelate":
            px = max(4, int(_num(strength, "strength", 4, 120, max(8, min(patch.size) // 6))))
            patch = patch.resize((max(1, patch.width // px), max(1, patch.height // px)), Image.NEAREST).resize(patch.size, Image.NEAREST)
        elif m == "blur":
            rad = _num(strength, "strength", 2, 80, max(10, min(patch.size) // 4))
            patch = patch.filter(ImageFilter.GaussianBlur(radius=rad))
        else:
            raise EditError("mode: blur, pixelate ya black.")
        out.paste(patch, (l, t))
    return out if im.mode == "RGBA" else out.convert(im.mode if im.mode in ("RGB", "L") else "RGB")


def op_border(im, size=20, color="white", percent=False, **_):
    s = _num(size, "size", 0, 800)
    px = round(min(im.size) * s / 100) if percent else round(s)
    if px == 0:
        return im
    _check_size(im.width + 2 * px, im.height + 2 * px)
    if str(color) in ("transparent", "none"):
        out = Image.new("RGBA", (im.width + 2 * px, im.height + 2 * px), (0, 0, 0, 0))
        out.paste(im.convert("RGBA"), (px, px))
        return out
    return ImageOps.expand(im.convert("RGB") if im.mode == "L" else im, border=px, fill=_rgb(color) if im.mode != "RGBA" else (*_rgb(color), 255))


def op_pad(im, aspect="1:1", color="white", **_):
    """Grow the canvas (never crop) to an aspect ratio - the 'square for marketplace' job."""
    a = _aspect(aspect)
    w, h = im.size
    if w / h < a:
        nw, nh = round(h * a), h
    else:
        nw, nh = w, round(w / a)
    _check_size(nw, nh)
    if str(color) in ("transparent", "none"):
        canvas = Image.new("RGBA", (nw, nh), (0, 0, 0, 0))
        canvas.paste(im.convert("RGBA"), ((nw - w) // 2, (nh - h) // 2))
        return canvas
    canvas = Image.new("RGB", (nw, nh), _rgb(color))
    src = im.convert("RGBA")
    canvas.paste(src, ((nw - w) // 2, (nh - h) // 2), src)
    return canvas


def op_round_corners(im, radius=40, percent=False, **_):
    r = _num(radius, "radius", 0, 2000)
    px = round(min(im.size) * r / 100 / 2) if percent else round(r)
    rgba = im.convert("RGBA")
    mask = Image.new("L", rgba.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, rgba.width - 1, rgba.height - 1), radius=px, fill=255)
    rgba.putalpha(ImageChops.multiply(rgba.getchannel("A"), mask))
    return rgba


def op_bg_color(im, color="white", **_):
    return flatten(im, color)


_DEV = re.compile(r"[\u0900-\u097f\u1cd0-\u1cff\ua8e0-\ua8ff]")


def _load_font(name: str, px: int):
    for cand in (FONT_DIR / name, Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")):
        try:
            return ImageFont.truetype(str(cand), px)
        except OSError:
            continue
    return ImageFont.load_default()


_FALLBACK = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")


@functools.lru_cache(maxsize=8)
def _cmap(path: str) -> frozenset:
    try:
        from fontTools.ttLib import TTFont
        return frozenset(TTFont(path).getBestCmap())
    except Exception:
        return frozenset()


def _pick(ch: str, stack: list[tuple[str, Any]]):
    for path, f in stack:
        cm = _cmap(path)
        if not cm or ord(ch) in cm:
            return f
    return stack[-1][1]


def _runs(text: str, px: int) -> list[tuple[str, Any]]:
    """Split into (piece, font) by the first font in the stack that HAS each character: Devanagari -> Noto Devanagari,
    Latin / digits -> Poppins, then Noto (rupee sign) and DejaVu (dots, bullets, arrows). No missing-glyph boxes."""
    def mk(path: Path):
        try:
            return str(path), ImageFont.truetype(str(path), px)
        except OSError:
            return None
    dev, lat, fb = mk(FONT_DIR / "NotoSansDevanagari-Bold.ttf"), mk(FONT_DIR / "Poppins-Bold.ttf"), mk(_FALLBACK)
    stack = [x for x in ((dev, lat) if _DEV.search(text) else (lat, dev)) + (fb,) if x]
    if not stack:
        return [(text, ImageFont.load_default())]
    out: list[tuple[str, Any]] = []
    for ch in text:
        f = _pick(ch, stack) if ch != " " else (out[-1][1] if out else stack[0][1])
        if out and out[-1][1] is f:
            out[-1] = (out[-1][0] + ch, f)
        else:
            out.append((ch, f))
    return out


def op_text(im, text="", position="bottom-right", size_pct=5, color="white", opacity=100, stroke=0, margin_pct=3,
            tile=False, angle=0, box=None, **_):
    """Text over the photo (a caption, a price, a watermark with her OWN name). position: a corner / edge / center."""
    t = str(text or "").strip()
    if not t:
        raise EditError("text likhiye.")
    if len(t) > 140:
        raise EditError("Text 140 akshar tak.")
    base = im.convert("RGBA")
    w, h = base.size
    px = max(8, round(min(w, h) * _num(size_pct, "size_pct", 1, 40) / 100))
    runs = _runs(t, px)
    op = int(_num(opacity, "opacity", 5, 100) * 2.55)
    rgb = _rgb(color)
    sw = int(_num(stroke, "stroke", 0, 12))
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    widths = [d.textlength(piece, font=f) for piece, f in runs]
    tw = int(sum(widths)) + 2 * sw
    asc = max(f.getmetrics()[0] for _, f in runs)
    desc = max(f.getmetrics()[1] for _, f in runs)
    th = asc + desc + 2 * sw
    stamp = Image.new("RGBA", (tw + 16, th + 16), (0, 0, 0, 0))
    sd = ImageDraw.Draw(stamp)
    if box:
        sd.rounded_rectangle((0, 0, stamp.width - 1, stamp.height - 1), radius=px // 4, fill=(*_rgb(box), int(op * .75)))
    x = 8 + sw
    for (piece, f), wdt in zip(runs, widths):
        sd.text((x, 8 + sw + asc - f.getmetrics()[0]), piece, font=f, fill=(*rgb, op), stroke_width=sw, stroke_fill=(0, 0, 0, op))
        x += wdt
    ang = _num(angle, "angle", -90, 90)
    if ang:
        stamp = stamp.rotate(ang, expand=True, resample=Image.BICUBIC)
    if tile:
        gx, gy = stamp.width * 2, stamp.height * 3
        for yy in range(-stamp.height, h + gy, gy):
            for xx in range(-stamp.width, w + gx, gx):
                layer.paste(stamp, (xx, yy), stamp)
    else:
        m = round(min(w, h) * _num(margin_pct, "margin_pct", 0, 30) / 100)
        pos = str(position or "bottom-right").lower()
        gx, gy = _GRAV.get(pos, (1, 1))
        x = round(m + (w - 2 * m - stamp.width) * gx)
        y = round(m + (h - 2 * m - stamp.height) * gy)
        layer.alpha_composite(stamp, (max(0, x), max(0, y)))
    out = Image.alpha_composite(base, layer)
    return out if im.mode == "RGBA" else out.convert("RGB")


def op_upscale_local(im, factor=2, **_):
    """Plain enlargement (Lanczos + a light sharpen). It makes the picture bigger, it does NOT invent detail."""
    f = _num(factor, "factor", 1.1, 4, 2)
    w, h = round(im.width * f), round(im.height * f)
    _check_size(w, h)
    big = im.resize((w, h), Image.LANCZOS)
    return _scale_rgb(big, lambda x: x.filter(ImageFilter.UnsharpMask(radius=1.2, percent=70, threshold=2)))


def op_convert(im, **_):               # the format is chosen at save time (format= / compress_kb= on the run itself)
    return im


OPS: dict[str, Callable[..., Image.Image]] = {
    "resize": op_resize, "crop": op_crop, "rotate": op_rotate, "flip": op_flip, "adjust": op_adjust,
    "auto_enhance": op_auto_enhance, "filter": op_filter, "redact": op_redact, "border": op_border, "pad": op_pad,
    "round_corners": op_round_corners, "bg_color": op_bg_color, "text": op_text, "watermark": op_text,
    "upscale_local": op_upscale_local, "convert": op_convert,
}


def run(im: Image.Image, steps: list[dict]) -> tuple[Image.Image, list[dict]]:
    """Run the local steps in order. Returns the image and one report row per step."""
    if len(steps) > MAX_STEPS:
        raise EditError(f"Ek baar mein {MAX_STEPS} steps tak.")
    rep = []
    for i, st in enumerate(steps, 1):
        name = str((st or {}).get("op") or "").lower()
        fn = OPS.get(name)
        if fn is None:
            raise EditError(f"Step {i}: '{name}' local op nahi hai. Local ops: " + ", ".join(sorted(OPS)))
        before = im.size
        params = {k: v for k, v in st.items() if k != "op"}
        try:
            im = fn(im, **params)
        except EditError as e:
            raise EditError(f"Step {i} ({name}): {e}") from None
        except TypeError as e:
            raise EditError(f"Step {i} ({name}): galat parameter ({e}).") from None
        rep.append({"op": name, "from": f"{before[0]}x{before[1]}", "to": f"{im.width}x{im.height}"})
    return im, rep


def collage(images: list[Image.Image], cols: int = 0, gap: int = 12, bg: str = "white", cell: int = 800) -> Image.Image:
    n = len(images)
    if not 2 <= n <= 20:
        raise EditError("Collage ke liye 2 se 20 photo chahiye.")
    cols = int(cols) or math.ceil(math.sqrt(n))
    cols = max(1, min(cols, n))
    rows = math.ceil(n / cols)
    cell = int(_num(cell, "cell", 100, 1500, 800))
    gap = int(_num(gap, "gap", 0, 200, 12))
    W, H = cols * cell + (cols + 1) * gap, rows * cell + (rows + 1) * gap
    _check_size(W, H)
    canvas = Image.new("RGB", (W, H), _rgb(bg))
    for i, im in enumerate(images):
        tile = ImageOps.fit(flatten(im), (cell, cell), Image.LANCZOS)
        canvas.paste(tile, (gap + (i % cols) * (cell + gap), gap + (i // cols) * (cell + gap)))
    return canvas


def before_after(a: Image.Image, b: Image.Image, gap: int = 16, label: bool = True) -> Image.Image:
    h = min(1200, max(a.height, b.height))
    pa = flatten(a); pb = flatten(b)
    pa = pa.resize((max(1, round(pa.width * h / pa.height)), h), Image.LANCZOS)
    pb = pb.resize((max(1, round(pb.width * h / pb.height)), h), Image.LANCZOS)
    canvas = Image.new("RGB", (pa.width + pb.width + gap, h), (255, 255, 255))
    canvas.paste(pa, (0, 0)); canvas.paste(pb, (pa.width + gap, 0))
    if label:
        canvas = op_text(canvas, text="BEFORE", position="top-left", size_pct=4, color="white", stroke=2)
        canvas = op_text(canvas, text="AFTER", position="top-right", size_pct=4, color="white", stroke=2)
    return canvas
