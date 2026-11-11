"""D2 stamps: page numbers (every iLovePDF option + Bates + Devanagari digits), watermark (text in Hindi / English, or
her logo; 9 positions or mosaic; opacity; any angle; over or under the page), header / footer, and the drawing layer
that edit.py uses (text, picture, shapes, highlight, white box).

How: ReportLab draws one transparent page the size of the original, pikepdf lays it over (or under) that page. The
drawing is done in what she SEES - the visible (crop) box, with the page's own rotation undone - so 'bottom right'
is bottom right on screen even on a page that was scanned sideways. Devanagari runs use the bundled Noto font with
HarfBuzz shaping (conjuncts join); Latin text uses Inter (has the rupee sign)."""
from __future__ import annotations

import io
import re
from datetime import date
from pathlib import Path
from typing import Any, Callable

from . import core
from .core import DocError

FONT_DIR = Path(__file__).resolve().parent.parent / "fonts"
_REG: dict[str, str] = {}
POSITIONS = ("top-left", "top-center", "top-right", "middle-left", "center", "middle-right",
             "bottom-left", "bottom-center", "bottom-right")
MARGIN_PT = {"small": 18.0, "recommended": 30.0, "big": 48.0}
DEV_DIGITS = str.maketrans("0123456789", "०१२३४५६७८९")
MM = 72 / 25.4


# ----------------------------------------------------------------------------------------------- text
def _latin(bold: bool = False) -> str:
    key = "lb" if bold else "l"
    if key not in _REG:
        name = "Helvetica-Bold" if bold else "Helvetica"
        try:
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont
            f = FONT_DIR / "print" / "Inter.ttf"
            if f.exists():
                pdfmetrics.registerFont(TTFont("HoolaInter", str(f)))
                name = "HoolaInter"
        except Exception:
            pass
        _REG[key] = name
    return _REG[key]


def _dev(bold: bool = False) -> str | None:
    from .. import indicpdf
    return indicpdf.dev_font(bold)


def _runs(text: str, bold: bool) -> list[tuple[str, str]]:
    from .. import indicpdf
    lat, dev = _latin(bold), _dev(bold)
    out = []
    for part, is_dev in indicpdf.runs(text):
        if is_dev and dev:
            out.append((part, dev))
        else:
            if lat.startswith("Helvetica"):
                part = part.replace("₹", "Rs ").encode("latin-1", "replace").decode("latin-1")
            out.append((part, lat))
    return out


def text_width(text: str, size: float, bold: bool = False) -> float:
    from reportlab.pdfbase.pdfmetrics import stringWidth
    w = 0.0
    for p, f in _runs(text, bold):
        try:
            w += stringWidth(p, f, size)
        except Exception:
            w += len(p) * size * 0.55
    return w


def draw_text(c, x: float, y: float, text: str, size: float, bold: bool = False, align: str = "left") -> float:
    """Draw one line at baseline y; align left / center / right around x. Returns the width."""
    w = text_width(text, size, bold)
    x0 = x - w if align == "right" else x - w / 2 if align == "center" else x
    for p, f in _runs(text, bold):
        try:
            c.setFont(f, size)
            c.drawString(x0, y, p)
            from reportlab.pdfbase.pdfmetrics import stringWidth
            x0 += stringWidth(p, f, size)
        except Exception:
            continue
    return w


def color(v: Any, default: str = "#000000") -> tuple[float, float, float]:
    names = {"black": "#000000", "red": "#d32f2f", "blue": "#1565c0", "green": "#2e7d32", "grey": "#757575",
             "gray": "#757575", "white": "#ffffff", "orange": "#ef6c00", "yellow": "#fdd835", "purple": "#6a1b9a",
             "saffron": "#ff9933", "navy": "#0d1b4c"}
    s = str(v or default).strip().lower()
    s = names.get(s, s)
    m = re.fullmatch(r"#?([0-9a-f]{6}|[0-9a-f]{3})", s)
    if not m:
        raise DocError(f"Colour '{v}' was not understood (a name like red / blue / grey, or #RRGGBB).")
    h = m.group(1)
    if len(h) == 3:
        h = "".join(ch * 2 for ch in h)
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))  # type: ignore[return-value]


# ----------------------------------------------------------------------------------------------- the frame
def frame(page) -> dict[str, float]:
    """Media box, the visible box inside it (local coords) and the rotation -> the size she sees."""
    mb = [float(x) for x in page.mediabox]
    try:
        cb = [float(x) for x in page.obj.get("/CropBox", page.mediabox)]
    except Exception:
        cb = mb
    cx0, cy0 = max(cb[0], mb[0]) - mb[0], max(cb[1], mb[1]) - mb[1]
    cw, ch = min(cb[2], mb[2]) - max(cb[0], mb[0]), min(cb[3], mb[3]) - max(cb[1], mb[1])
    rot = int(page.obj.get("/Rotate", 0) or 0) % 360
    vw, vh = (ch, cw) if rot in (90, 270) else (cw, ch)
    return {"mw": mb[2] - mb[0], "mh": mb[3] - mb[1], "cx": cx0, "cy": cy0, "cw": cw, "ch": ch, "rot": rot,
            "vw": vw, "vh": vh, "mx": mb[0], "my": mb[1]}


def to_visual(f: dict[str, float], x: float, y: float) -> tuple[float, float]:
    """A point in the page's own space -> where she sees it (bottom-left origin of the visible box, rotation undone)."""
    xl, yl = x - f["mx"] - f["cx"], y - f["my"] - f["cy"]
    r, cw, ch = f["rot"], f["cw"], f["ch"]
    if r == 90:
        return yl, cw - xl
    if r == 180:
        return cw - xl, ch - yl
    if r == 270:
        return ch - yl, xl
    return xl, yl


def layer(pdf, page, draw: Callable[[Any, float, float], None], under: bool = False, keep: list | None = None) -> None:
    """Draw with ReportLab on a transparent sheet the size she SEES (w x h, the visible box with the rotation undone)
    and lay it over / under `page`. pikepdf places it upright inside the visible box (it inverts the page's
    rotation), so 'bottom right' is bottom right on screen."""
    import pikepdf
    from reportlab.pdfgen import canvas
    f = frame(page)
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(f["vw"], f["vh"]), pageCompression=1)
    draw(c, f["vw"], f["vh"])
    c.showPage()
    c.save()
    src = pikepdf.open(io.BytesIO(buf.getvalue()))
    if keep is not None:
        keep.append(src)
    x0, y0 = f["mx"] + f["cx"], f["my"] + f["cy"]
    rect = pikepdf.Rectangle(x0, y0, x0 + f["cw"], y0 + f["ch"])
    if under:
        page.add_underlay(src.pages[0], rect)
    else:
        page.add_overlay(src.pages[0], rect)


def _xy(pos: str, w: float, h: float, m: float, tw: float, th: float) -> tuple[float, float, str]:
    """A named position -> (x, baseline y, align) for a line tw wide and th high inside margin m."""
    p = (pos or "bottom-center").lower().replace("_", "-").replace(" ", "-").replace("centre", "center")
    p = {"top": "top-center", "bottom": "bottom-center", "middle": "center", "left": "middle-left",
         "right": "middle-right"}.get(p, p)
    if p not in POSITIONS:
        raise DocError(f"position = {' | '.join(POSITIONS)}.")
    v, hz = ("middle", "center") if p == "center" else p.split("-")
    y = h - m - th * 0.8 if v == "top" else m if v == "bottom" else h / 2 - th * 0.35
    x = m if hz == "left" else w - m if hz == "right" else w / 2
    return x, y, hz if hz != "center" else "center"


# ----------------------------------------------------------------------------------------------- page numbers
def _fmt(template: str, n: int, p: int, r: int, start: int, digits: str, title: str) -> str:
    def num(v: int) -> str:
        s = str(v)
        return s.translate(DEV_DIGITS) if digits == "devanagari" else s

    def bates(m: re.Match) -> str:
        return num(n).zfill(int(m.group(1)))
    t = re.sub(r"\{n:0?(\d+)\}", bates, template)
    return (t.replace("{n}", num(n)).replace("{p}", num(p)).replace("{rf}", num(start + r - 1))
             .replace("{r}", num(r)).replace("{date}", date.today().strftime("%d %b %Y")).replace("{title}", title))


TEMPLATES = {"number": "{n}", "page_n": "Page {n}", "page_n_of_p": "Page {n} of {p}", "n_of_p": "{n} / {p}",
             "hindi": "पृष्ठ {n}", "hindi_of": "पृष्ठ {n} / {p}"}


def page_numbers(data: bytes, *, text: str = "{n}", position: str = "bottom-center", start: int = 1, pages: Any = "all",
                 margin: str = "recommended", size: float = 11, color_: Any = "#333333", opacity: float = 1.0,
                 bold: bool = False, digits: str = "latin", facing: bool = False, skip_first: int = 0,
                 skip_last: int = 0, bates_prefix: str = "") -> bytes:
    """{n} the number, {p} pages in the file, {r} pages numbered, {rf} the last number, {n:06} Bates width,
    {date}, {title}. facing = left / right mirrored on even pages (books). skip_first / skip_last = cover pages."""
    tpl = TEMPLATES.get(str(text or "{n}"), str(text or "{n}"))
    if bates_prefix:
        tpl = f"{bates_prefix}{{n:06}}" if text in ("{n}", "", None) else tpl
    if "{n" not in tpl and "{p}" not in tpl:
        raise DocError("The number text needs {n} (e.g. 'Page {n} of {p}').")
    if digits not in ("latin", "devanagari"):
        raise DocError("digits = latin | devanagari.")
    if not 4 <= float(size) <= 72:
        raise DocError("size must be between 4 and 72 points.")
    m = MARGIN_PT.get(str(margin or "recommended"))
    if m is None:
        raise DocError("margin = small | recommended | big.")
    rgb, op = color(color_, "#333333"), max(0.05, min(1.0, float(opacity)))
    with core.open_pdf(data) as pdf:
        n_all = len(pdf.pages)
        idx = core.pages(pages or "all", n_all)
        idx = idx[int(skip_first or 0): len(idx) - int(skip_last or 0) if skip_last else None]
        if not idx:
            raise DocError("No pages are left to number after the skipped ones.")
        title = str(pdf.docinfo.get("/Title", "")) if pdf.docinfo else ""
        keep: list = []
        for k, i in enumerate(idx):
            label = _fmt(tpl, int(start) + k, n_all, len(idx), int(start), digits, title)
            pos = position
            if facing and (i % 2 == 1):
                pos = pos.replace("right", "@").replace("left", "right").replace("@", "left")

            def draw(c, w, h, label=label, pos=pos):
                c.setFillColorRGB(*rgb)
                c.setFillAlpha(op)
                x, y, al = _xy(pos, w, h, m, text_width(label, size, bold), size)
                draw_text(c, x, y, label, size, bold, al)
            layer(pdf, pdf.pages[i], draw, keep=keep)
        out = core.save(pdf)
        for s in keep:
            s.close()
        return out


def header_footer(data: bytes, *, header: dict | None = None, footer: dict | None = None, pages: Any = "all",
                  size: float = 9, color_: Any = "#555555", margin: str = "small", line: bool = False) -> bytes:
    """header / footer = {left, center, right} strings with {n} {p} {date} {title}."""
    parts = [("top", header or {}), ("bottom", footer or {})]
    if not any(v for _, d in parts for v in d.values()):
        raise DocError("Give some header or footer text (left / center / right).")
    m = MARGIN_PT.get(str(margin or "small"), 18.0)
    rgb = color(color_, "#555555")
    with core.open_pdf(data) as pdf:
        n_all = len(pdf.pages)
        idx = core.pages(pages or "all", n_all)
        title = str(pdf.docinfo.get("/Title", "")) if pdf.docinfo else ""
        keep: list = []
        for k, i in enumerate(idx):
            def draw(c, w, h, k=k, i=i):
                c.setFillColorRGB(*rgb)
                c.setStrokeColorRGB(*rgb)
                for vert, d in parts:
                    for hz in ("left", "center", "right"):
                        t = str(d.get(hz) or d.get("centre" if hz == "center" else hz) or "")
                        if not t:
                            continue
                        lab = _fmt(t, i + 1, n_all, len(idx), 1, "latin", title)
                        x, y, al = _xy(f"{vert}-{hz}", w, h, m, text_width(lab, size), size)
                        draw_text(c, x, y, lab, size, False, al)
                    if line and any(d.values()):
                        yy = h - m - size * 1.1 if vert == "top" else m + size * 1.2
                        c.setLineWidth(0.4)
                        c.line(m, yy, w - m, yy)
            layer(pdf, pdf.pages[i], draw, keep=keep)
        out = core.save(pdf)
        for s in keep:
            s.close()
        return out


# ----------------------------------------------------------------------------------------------- watermark
def watermark(data: bytes, *, text: str = "", image: bytes | None = None, position: str = "center",
              mosaic: bool = False, size: float = 0, color_: Any = "#9e9e9e", opacity: float = 0.25,
              rotation: float = 45, layer_: str = "over", pages: Any = "all", bold: bool = True,
              scale: float = 0.35) -> bytes:
    """Text (Hindi / English) or her logo picture. size 0 = fitted to the page. scale = logo width as a share of the page."""
    if not text and not image:
        raise DocError("Give the watermark text, or her logo picture (image file_id).")
    if layer_ not in ("over", "under"):
        raise DocError("layer = over | under.")
    op = max(0.03, min(1.0, float(opacity)))
    rgb = color(color_, "#9e9e9e")
    reader = None
    if image is not None:
        from PIL import Image
        from reportlab.lib.utils import ImageReader
        try:
            im = Image.open(io.BytesIO(image))
            im.load()
        except Exception:
            raise DocError("The logo is not a readable picture (PNG / JPG).")
        if im.mode not in ("RGB", "RGBA", "L", "LA"):
            im = im.convert("RGBA")
        reader = ImageReader(im)
        iw, ih = im.size
    with core.open_pdf(data) as pdf:
        idx = core.pages(pages or "all", len(pdf.pages))
        keep: list = []
        for i in idx:
            def draw(c, w, h):
                c.saveState()
                c.setFillColorRGB(*rgb)
                c.setFillAlpha(op)
                spots = []
                if mosaic:
                    step_x, step_y = w / 3, h / 4
                    spots = [(step_x * (a + 0.5), step_y * (b + 0.5)) for a in range(3) for b in range(4)]
                else:
                    if (position or "center") == "center":
                        spots = [(w / 2, h / 2)]
                    else:
                        x, y, _ = _xy(position, w, h, w * 0.18, 0, 0)
                        spots = [(x, y)]
                for (x, y) in spots:
                    c.saveState()
                    c.translate(x, y)
                    c.rotate(float(rotation or 0))
                    if reader is not None:
                        lw = w * (float(scale) if not mosaic else 0.2)
                        lh = lw * ih / iw
                        c.drawImage(reader, -lw / 2, -lh / 2, lw, lh, mask="auto")
                    else:
                        fs = float(size) if size else max(14.0, min(110.0, (w if not mosaic else w / 3) * 0.9 /
                                                                     max(1.0, text_width(text, 1.0, bold))))
                        if mosaic and not size:
                            fs = min(fs, 28.0)
                        draw_text(c, 0, -fs * 0.35, text, fs, bold, "center")
                    c.restoreState()
                c.restoreState()
            layer(pdf, pdf.pages[i], draw, under=(layer_ == "under"), keep=keep)
        out = core.save(pdf)
        for s in keep:
            s.close()
        return out
