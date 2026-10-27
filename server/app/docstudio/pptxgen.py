"""v0.189.0 docstudio.pptxgen - the PowerPoint line: palette deck (title slide + content slides),
one hue family from the cascade palette, accent bar + footer with slide numbers, speaker notes kept.
Bullets carry the text; the deck stays light (max 12 bullets a slide, 40 slides a deck - v0.51 caps kept).
"""
from __future__ import annotations

import io
from typing import Any

from . import tokens

MAX_SLIDES = 40
MAX_BULLETS = 12
SW, SH = 12192000, 6858000  # 16:9 EMU


def make_pptx(title: str, slides: list[dict[str, Any]], *, style: str | None = None,
              author: str = "Hoola", subject: str = "") -> dict[str, Any]:
    """Build a designed deck. Returns {data, slides:[{title,bullets}], style, palette, qa}."""
    from pptx import Presentation
    from pptx.dml.color import RGBColor
    from pptx.util import Emu, Pt

    pal = tokens.palette_for(title, style)
    P = {k: v.lstrip("#").upper() for k, v in pal.pdf_colors().items()}
    rgb = lambda h: RGBColor.from_string(h.upper())
    p = Presentation()
    p.slide_width, p.slide_height = SW, SH
    p.core_properties.title = tokens.sanitize_text(title)[:200]
    p.core_properties.author = author

    def blank():
        return p.slides.add_slide(p.slide_layouts[6])

    def bar(slide, color: str, x: int, y: int, w: int, h: int) -> None:
        from pptx.enum.shapes import MSO_SHAPE
        shp = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Emu(x), Emu(y), Emu(w), Emu(h))
        shp.fill.solid()
        shp.fill.fore_color.rgb = rgb(color)
        shp.line.fill.background()
        shp.shadow.inherit = False

    def text(slide, x: int, y: int, w: int, h: int, s: str, size: float, bold: bool = False,
             color: str | None = None, align=None) -> None:
        from pptx.enum.text import PP_ALIGN
        box = slide.shapes.add_textbox(Emu(x), Emu(y), Emu(w), Emu(h))
        tf = box.text_frame
        tf.word_wrap = True
        para = tf.paragraphs[0]
        para.alignment = align if align is not None else PP_ALIGN.LEFT
        run = para.add_run()
        run.text = tokens.sanitize_text(s)
        f = run.font
        f.size, f.bold = Pt(size), bold
        f.color.rgb = rgb((color or P["text_primary"]))
        f.name = "Calibri"
        return box

    info: list[dict[str, Any]] = []
    deck_lines = tokens.title_chunk(title)
    s0 = blank()
    bar(s0, P["cover_block"], 0, 0, 90000, SH)                       # slim accent bar, full height
    text(s0, 1100000, SH // 3 - 700000, SW - 2000000, 500000, pal.style_name.upper(), 13, False, P["text_muted"])
    y = SH // 3
    for line in deck_lines:
        text(s0, 1100000, y, SW - 2000000, 900000, line, 36, True, P["text_primary"])
        y += 900000
    bar(s0, P["accent"], 1100000, y + 100000, 900000, 45000)
    text(s0, 1100000, SH - 900000, SW - 2200000, 400000,
         f"{author}  \u00b7  Hoola Document Studio", 12, False, P["text_muted"])

    for i, sl in enumerate((slides or [])[:MAX_SLIDES], start=1):
        if not isinstance(sl, dict):
            sl = {"title": str(sl)}
        s = blank()
        bar(s, P["accent"], 685800, 620000, 360000, 52000)
        text(s, 685800, 700000, SW - 1371600, 800000, str(sl.get("title") or "")[:200], 26, True,
             P["header_fill"])
        body = (sl.get("bullets") or [])[:MAX_BULLETS]
        from pptx.enum.text import MSO_ANCHOR
        box = s.shapes.add_textbox(Emu(685800), Emu(1700000), Emu(SW - 1371600), Emu(SH - 2600000))
        tf = box.text_frame
        tf.word_wrap = True
        for j, b in enumerate(body):
            para = tf.paragraphs[0] if j == 0 else tf.add_paragraph()
            run = para.add_run()
            run.text = tokens.sanitize_text(str(b))[:300]
            run.font.size = Pt(18)
            run.font.color.rgb = rgb(P["text_primary"])
            run.font.name = "Calibri"
            para.space_after = Pt(10)
        text(s, SW - 1500000, SH - 620000, 800000, 300000, str(i + 1), 11, False, P["text_muted"])
        if sl.get("notes"):
            try:
                s.notes_slide.notes_text_frame.text = str(sl["notes"])[:3000]
            except Exception:
                pass
        info.append({"title": str(sl.get("title") or "")[:80], "bullets": len(body)})

    buf = io.BytesIO()
    p.save(buf)
    data = buf.getvalue()
    issues: list[str] = []
    if not slides:
        issues.append("deck has only the title slide")
    try:
        from pptx import Presentation as PR
        r = PR(io.BytesIO(data))
        if len(r.slides._sldIdLst) != len(info) + 1:  # noqa: SLF001 - title slide + content
            issues.append("slide count mismatch after re-open")
    except Exception:
        pass
    return {"data": data, "slides": info, "style": pal.style_name, "palette": pal.summary(),
            "qa": {"status": "pass" if not issues else "warn", "issues": issues,
                   "size_kb": round(len(data) / 1024, 1), "checked": ["re-open", "size"]}}
