"""v0.144 Devanagari-safe PDFs for the Sahayaks that draw with ReportLab (Helvetica has no Hindi / Marathi glyphs: names came
out as '?' or boxes).

Two drop-in pieces, one rule: a PDF whose text is Latin-only is drawn EXACTLY as before; a PDF with Devanagari in it is printed
by the Lekhak Chromium printer (`lekhak.make_pdf`: HarfBuzz shaping, Mukta fonts, conjuncts and matras right). If Chromium is not
there, ReportLab draws it with the bundled Noto Sans Devanagari for the Devanagari runs (shaped when uharfbuzz is installed),
so names are at least readable.

- `Canvas`: records the small canvas API the modules use (setFont, drawString / Right / Centred, drawImage, rect, line,
  showPage, save) and on `save()` writes the PDF into the same buffer / path a reportlab Canvas would.
- `blocks_pdf(title, blocks, watermark)` for platypus-style documents (h1 / h / p / table blocks).
"""
from __future__ import annotations

import base64
import html
import io
import logging
import re
from pathlib import Path
from typing import Any

log = logging.getLogger("santosh.indicpdf")

DEV = re.compile(r"[ऀ-ॿ꣠-ꣿ᳐-᳿]")
_RUN = re.compile(r"([ऀ-ॿ꣠-ꣿ᳐-᳿‌‍]+(?:[  ]+[ऀ-ॿ꣠-ꣿ᳐-᳿‌‍]+)*)")
FONT_DIR = Path(__file__).resolve().parent / "fonts"
STATS = {"chromium": 0, "fallback": 0, "latin": 0}


def has_indic(*texts: Any) -> bool:
    return any(DEV.search(str(t or "")) for t in texts)


def keep(t: Any) -> str:
    """Text for a PDF line: Devanagari kept (this module draws it), other non-Latin-1 replaced as before."""
    out = []
    for ch in str(t if t is not None else "").replace("₹", "Rs "):
        if DEV.match(ch) or ch in "‌‍":
            out.append(ch)
        else:
            out.append(ch.encode("latin-1", "replace").decode("latin-1"))
    return "".join(out)


# ---------------------------------------------------------------- fonts for the ReportLab fallback
_REG: dict[str, str] = {}


def dev_font(bold: bool = False) -> str | None:
    key = "b" if bold else "r"
    if key in _REG:
        return _REG[key] or None
    name = ""
    try:
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        f = FONT_DIR / ("NotoSansDevanagari-Bold.ttf" if bold else "NotoSansDevanagari-Regular.ttf")
        if f.exists():
            name = "HoolaDev-Bold" if bold else "HoolaDev"
            try:
                font = TTFont(name, str(f), shapable=True)
            except Exception:
                font = TTFont(name, str(f))
            pdfmetrics.registerFont(font)
    except Exception as e:                       # pragma: no cover - fonts are bundled
        log.info("devanagari font not registered: %s", e)
        name = ""
    _REG[key] = name
    return name or None


def runs(text: str) -> list[tuple[str, bool]]:
    """[(piece, is_devanagari)] in order."""
    out: list[tuple[str, bool]] = []
    for i, part in enumerate(_RUN.split(text)):
        if part:
            out.append((part, i % 2 == 1))
    return out


def rl_markup(escaped: str, bold: bool = False) -> str:
    """Platypus Paragraph markup: Devanagari runs of already-escaped text wrapped in the bundled font."""
    f = dev_font(bold)
    if not f or not DEV.search(escaped):
        return escaped
    return "".join(f'<font name="{f}">{p}</font>' if d else p for p, d in runs(escaped))


# ---------------------------------------------------------------- recording canvas
class Canvas:
    """Stand-in for reportlab.pdfgen.canvas.Canvas (the subset the Sahayaks use)."""

    def __init__(self, target: Any, pagesize: tuple[float, float] | None = None, **kw: Any):
        from reportlab.lib.pagesizes import A4
        self._target, self._kw = target, kw
        self._size = tuple(pagesize or A4)
        self._pages: list[list[tuple]] = [[]]
        self._font = ("Helvetica", 12.0)
        self._fill = (0.0, 0.0, 0.0)
        self._title = ""

    # state
    def setFont(self, name: str, size: float, leading: float | None = None) -> None:
        self._font = (name, float(size))
        self._op("font", name, float(size))

    def setTitle(self, t: str) -> None:
        self._title = str(t)

    def setPageSize(self, size) -> None:
        self._size = tuple(size)

    def setFillColorRGB(self, r, g, b, alpha=None) -> None:
        self._fill = (float(r), float(g), float(b))
        self._op("fill", *self._fill)

    def setFillColor(self, c, alpha=None) -> None:
        try:
            self.setFillColorRGB(c.red, c.green, c.blue)
        except Exception:
            pass

    def setFillGray(self, g, alpha=None) -> None:
        self.setFillColorRGB(g, g, g)

    def setStrokeColorRGB(self, *a, **k) -> None:
        self._op("stroke", *a[:3])

    def setStrokeColor(self, c, alpha=None) -> None:
        try:
            self._op("stroke", c.red, c.green, c.blue)
        except Exception:
            pass

    def setStrokeGray(self, g, alpha=None) -> None:
        self._op("stroke", g, g, g)

    def setLineWidth(self, w) -> None:
        self._op("lw", float(w))

    def saveState(self) -> None:
        self._op("save")

    def restoreState(self) -> None:
        self._op("restore")

    def stringWidth(self, text: str, font: str | None = None, size: float | None = None) -> float:
        from reportlab.pdfbase.pdfmetrics import stringWidth
        return stringWidth(str(text), font or self._font[0], size or self._font[1])

    # drawing
    def _op(self, *op) -> None:
        self._pages[-1].append(op)

    def drawString(self, x, y, text, *a, **k) -> None:
        self._op("text", float(x), float(y), str(text), "l", self._font)

    def drawRightString(self, x, y, text, *a, **k) -> None:
        self._op("text", float(x), float(y), str(text), "r", self._font)

    def drawCentredString(self, x, y, text, *a, **k) -> None:
        self._op("text", float(x), float(y), str(text), "c", self._font)

    drawCentredText = drawCentredString

    def drawImage(self, image, x, y, width=None, height=None, mask=None, preserveAspectRatio=False, anchor="c", **k) -> None:
        self._op("img", image, float(x), float(y), width, height, preserveAspectRatio, mask)

    def rect(self, x, y, w, h, stroke=1, fill=0) -> None:
        self._op("rect", float(x), float(y), float(w), float(h), stroke, fill)

    def line(self, x1, y1, x2, y2) -> None:
        self._op("line", float(x1), float(y1), float(x2), float(y2))

    def showPage(self) -> None:
        self._pages.append([])

    # output
    def _texts(self) -> list[str]:
        return [op[3] for p in self._pages for op in p if op[0] == "text"]

    def getpdfdata(self) -> bytes:
        pages = self._pages if self._pages[-1] else self._pages[:-1] or [[]]
        if has_indic(*self._texts()):
            pdf = _chromium(_canvas_html(pages, self._size, self._title))
            if pdf:
                STATS["chromium"] += 1
                return pdf
            STATS["fallback"] += 1
            return self._replay(pages, indic=True)
        STATS["latin"] += 1
        return self._replay(pages, indic=False)

    def save(self) -> None:
        data = self.getpdfdata()
        t = self._target
        if hasattr(t, "write"):
            t.write(data)
        else:
            Path(t).write_bytes(data)

    def _replay(self, pages: list[list[tuple]], indic: bool) -> bytes:
        from reportlab.pdfgen import canvas
        bio = io.BytesIO()
        c = canvas.Canvas(bio, pagesize=self._size, **self._kw)
        if self._title:
            c.setTitle(self._title)
        for n, ops in enumerate(pages):
            if n:
                c.showPage()
            for op in ops:
                k = op[0]
                if k == "font":
                    c.setFont(op[1], op[2])
                elif k == "fill":
                    c.setFillColorRGB(*op[1:4])
                elif k == "stroke":
                    c.setStrokeColorRGB(*op[1:4])
                elif k == "lw":
                    c.setLineWidth(op[1])
                elif k == "save":
                    c.saveState()
                elif k == "restore":
                    c.restoreState()
                elif k == "rect":
                    c.rect(*op[1:5], stroke=op[5], fill=op[6])
                elif k == "line":
                    c.line(*op[1:5])
                elif k == "img":
                    _, image, x, y, w, h, keep_ratio, mask = op
                    c.drawImage(image, x, y, width=w, height=h, preserveAspectRatio=keep_ratio, mask=mask)
                elif k == "text":
                    _, x, y, text, align, (fname, size) = op
                    if not indic or not DEV.search(text):
                        {"l": c.drawString, "r": c.drawRightString, "c": c.drawCentredString}[align](x, y, text)
                        continue
                    _draw_runs(c, x, y, text, align, fname, size)
        c.save()
        return bio.getvalue()


def _draw_runs(c, x: float, y: float, text: str, align: str, fname: str, size: float) -> None:
    from reportlab.pdfbase.pdfmetrics import stringWidth
    dev = dev_font("Bold" in fname) or fname
    parts = [(p, dev if d else fname) for p, d in runs(text)]
    widths = []
    for p, f in parts:
        try:
            widths.append(stringWidth(p, f, size))
        except Exception:
            widths.append(len(p) * size * 0.5)
    total = sum(widths)
    x0 = x - total if align == "r" else x - total / 2 if align == "c" else x
    for (p, f), w in zip(parts, widths):
        try:
            c.setFont(f, size)
            c.drawString(x0, y, p)
        except Exception:
            c.setFont(fname, size)
            c.drawString(x0, y, p.encode("latin-1", "replace").decode("latin-1"))
        x0 += w
    c.setFont(fname, size)


def _img_data(image) -> str:
    try:
        raw: bytes | None = None
        if isinstance(image, (str, Path)):
            raw = Path(image).read_bytes()
        else:
            pil = getattr(image, "_image", None)
            if pil is None and hasattr(image, "fileName") and image.fileName:
                fn = image.fileName
                raw = fn.getvalue() if hasattr(fn, "getvalue") else Path(fn).read_bytes()
            if pil is not None:
                b = io.BytesIO()
                pil.convert("RGB").save(b, "JPEG", quality=85)
                raw = b.getvalue()
        if not raw:
            return ""
        from PIL import Image
        im = Image.open(io.BytesIO(raw))
        b = io.BytesIO()
        im.convert("RGB").save(b, "JPEG", quality=85)
        return "data:image/jpeg;base64," + base64.b64encode(b.getvalue()).decode()
    except Exception:
        return ""


def _font_css() -> str:
    try:
        from .lekhak.service import _font_css as lk
        return lk()
    except Exception:
        return ""


def _canvas_html(pages: list[list[tuple]], size: tuple[float, float], title: str) -> str:
    W, H = size
    e = html.escape
    out = [f"<!doctype html><html><head><meta charset='utf-8'><title>{e(title)}</title><style>{_font_css()}"
           f"@page{{size:{W}pt {H}pt;margin:0}}html,body{{margin:0;padding:0}}"
           f".pg{{position:relative;width:{W}pt;height:{H}pt;overflow:hidden;page-break-after:always;break-after:page}}"
           ".pg:last-child{page-break-after:auto;break-after:auto}"
           ".t{position:absolute;white-space:pre;line-height:1;font-family:'HoolaDoc','Noto Sans Devanagari',sans-serif}"
           ".i,.r,.l{position:absolute}.i{object-fit:contain}</style></head><body>"]
    for ops in pages:
        out.append("<div class='pg'>")
        fill, stroke, lw = (0, 0, 0), (0, 0, 0), 1.0
        for op in ops:
            k = op[0]
            if k == "fill":
                fill = op[1:4]
            elif k == "stroke":
                stroke = op[1:4]
            elif k == "lw":
                lw = op[1]
            elif k == "text":
                _, x, y, text, align, (fname, size) = op
                col = "rgb(%d,%d,%d)" % tuple(int(255 * v) for v in fill)
                wt = 700 if "Bold" in fname else 400
                base = y - 0.24 * size                      # CSS box bottom sits on the descent line
                pos = (f"left:{x}pt" if align == "l" else f"right:{W - x}pt" if align == "r"
                       else f"left:{x}pt;transform:translateX(-50%)")
                out.append(f"<div class='t' style='{pos};bottom:{base:.2f}pt;font-size:{size}pt;font-weight:{wt};color:{col}'>"
                           f"{e(text)}</div>")
            elif k == "rect":
                _, x, y, w, h, st, fl = op
                bg = ("background:rgb(%d,%d,%d);" % tuple(int(255 * v) for v in fill)) if fl else ""
                bd = ("border:%.2fpt solid rgb(%d,%d,%d);" % ((lw,) + tuple(int(255 * v) for v in stroke))) if st else ""
                out.append(f"<div class='r' style='left:{x}pt;bottom:{y}pt;width:{w}pt;height:{h}pt;box-sizing:border-box;{bg}{bd}'></div>")
            elif k == "line":
                _, x1, y1, x2, y2 = op
                if abs(y1 - y2) < 0.01 or abs(x1 - x2) < 0.01:
                    out.append(f"<div class='l' style='left:{min(x1, x2)}pt;bottom:{min(y1, y2)}pt;width:{max(abs(x2 - x1), lw)}pt;"
                               f"height:{max(abs(y2 - y1), lw)}pt;background:rgb(%d,%d,%d)'></div>" % tuple(int(255 * v) for v in stroke))
            elif k == "img":
                _, image, x, y, w, h, _r, _m = op
                src = _img_data(image)
                if src and w and h:
                    out.append(f"<img class='i' src='{src}' style='left:{x}pt;bottom:{y}pt;width:{w}pt;height:{h}pt'>")
        out.append("</div>")
    out.append("</body></html>")
    return "".join(out)


def _chromium(page_html: str) -> bytes | None:
    try:
        from .lekhak.service import make_pdf
        return make_pdf(page_html)
    except Exception as e:
        log.info("chromium pdf failed: %s", e)
        return None


# ---------------------------------------------------------------- block documents (platypus style)
def blocks_html(title: str, blocks: list[tuple], watermark: str = "", page: str = "A4") -> str:
    e = html.escape
    css = (_font_css() + f"@page{{size:{page};margin:13mm}}body{{font-family:'HoolaDoc','Noto Sans Devanagari',sans-serif;"
           "font-size:10pt;line-height:1.45;color:#111}h1{font-size:18pt;text-align:center;margin:0 0 8px}h2{font-size:13pt;margin:10px 0 4px}"
           "p{margin:0 0 6px;white-space:pre-wrap}table{border-collapse:collapse;width:100%;margin:0 0 8px;font-size:8.5pt}"
           "td,th{border:0.3pt solid #888;padding:3px 4px;vertical-align:top;text-align:left}th{background:#eee}"
           ".wm{position:fixed;top:45%;left:0;right:0;text-align:center;font-size:46pt;font-weight:700;color:rgba(217,51,51,.18);"
           "transform:rotate(-35deg)}")
    out = [f"<!doctype html><html><head><meta charset='utf-8'><title>{e(title)}</title><style>{css}</style></head><body>"]
    if watermark:
        out.append(f"<div class='wm'>{e(watermark)}</div>")
    for b in blocks:
        k = b[0]
        if k == "h1":
            out.append(f"<h1>{e(str(b[1]))}</h1>")
        elif k == "h":
            out.append(f"<h2>{e(str(b[1]))}</h2>")
        elif k == "p":
            out.append(f"<p>{e(str(b[1])) or '&nbsp;'}</p>")
        elif k == "table":
            rows = b[1] or []
            out.append("<table>")
            for i, r in enumerate(rows):
                tag = "th" if i == 0 else "td"
                out.append("<tr>" + "".join(f"<{tag}>{e(str(c if c is not None else ''))}</{tag}>" for c in r) + "</tr>")
            out.append("</table>")
    out.append("</body></html>")
    return "".join(out)


def blocks_pdf(title: str, blocks: list[tuple], watermark: str = "") -> bytes | None:
    """Chromium PDF of the blocks when they hold Devanagari; None when Chromium is not there (caller draws its own way)."""
    if not has_indic(*_block_texts(title, blocks, watermark)):
        return None
    pdf = _chromium(blocks_html(title, blocks, watermark))
    STATS["chromium" if pdf else "fallback"] += 1
    return pdf


def _block_texts(title: str, blocks: list[tuple], watermark: str) -> list[str]:
    out = [title, watermark]
    for b in blocks:
        if b[0] == "table":
            out += [str(c) for r in (b[1] or []) for c in r]
        elif len(b) > 1:
            out.append(str(b[1]))
    return out
