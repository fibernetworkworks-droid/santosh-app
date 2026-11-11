"""D4 searchable PDF: an invisible text layer on scanned pages, so they can be searched, copied, read aloud and
redacted - the page she sees is NOT changed (no re-compression, no 'cleaned' look).

How (no Ghostscript - owner decision D2): pypdfium2 draws each page that has no text (what she sees, rotation
applied), Tesseract reads it and writes a TEXT-ONLY page (glyph-less font, invisible text, `textonly_pdf=1`), and
pikepdf lays that page over the original's visible box. Hoola's own tessdata_best models (13 Indian languages)
are used when setup_ocr.sh put them there. Pages that already have text are left alone unless force=true."""
from __future__ import annotations

import io
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from . import core
from .core import DocError

MAX_OCR_PAGES = 300


def ready() -> bool:
    from .. import ocr
    return ocr.available()


def _langs(language: str) -> str:
    from .. import ocr
    if language and "+" in language:
        have = ocr.installed_langs()
        codes = [c for c in language.split("+") if c in have]
        return "+".join(codes) or ocr.langs_for("")
    return ocr.langs_for(language or "")


def _deskew_angle(im) -> int:
    """Tesseract's own page-orientation guess (0 / 90 / 180 / 270); 0 when it is not sure."""
    from .. import ocr
    exe = ocr._bin()
    if not exe or "osd" not in ocr.installed_langs():
        return 0
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "p.png"
        im.save(p)
        try:
            out = subprocess.run([exe, str(p), "-", "--psm", "0", "-l", "osd"], capture_output=True, text=True,
                                 timeout=60, env=ocr._env()).stdout
        except Exception:
            return 0
    rot, conf = 0, 0.0
    for line in out.splitlines():
        if line.startswith("Rotate:"):
            rot = int(line.split(":")[1].strip() or 0)
        if line.startswith("Orientation confidence:"):
            conf = float(line.split(":")[1].strip() or 0)
    return rot if conf >= 2.0 else 0


def _text_page(im, dpi: int, langs: str, timeout: int = 180) -> bytes:
    from .. import ocr
    exe = ocr._bin()
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "p.png"
        im.save(p, dpi=(dpi, dpi))
        out = Path(d) / "out"
        r = subprocess.run([exe, str(p), str(out), "-l", langs, "--dpi", str(dpi), "-c", "textonly_pdf=1", "pdf"],
                           capture_output=True, text=True, timeout=timeout, env=ocr._env())
        f = out.with_suffix(".pdf")
        if not f.exists():
            raise DocError(f"The reader could not read a page ({(r.stderr or 'no output')[-120:].strip()}).")
        return f.read_bytes()


def searchable(data: bytes, language: str = "", pages: Any = "all", force: bool = False, dpi: int = 300,
               auto_rotate: bool = True) -> dict[str, Any]:
    """-> {bytes, done: [page numbers read], skipped_text: [...], rotated: [...], langs, chars}."""
    import pikepdf
    import pypdfium2 as pdfium
    if not ready():
        raise DocError("The text reader (Tesseract) is not installed on the server yet (owner: vps-ops > docs_setup, "
                       "then the apt line in the DigitalOcean console).")
    dpi = max(150, min(400, int(dpi or 300)))
    langs = _langs(language)
    core.check_size(data)
    doc = pdfium.PdfDocument(data)
    layers: dict[int, bytes] = {}
    rotated: list[int] = []
    skipped: list[int] = []
    chars = 0
    try:
        idx = core.pages(pages or "all", len(doc))
        if len(idx) > MAX_OCR_PAGES:
            raise DocError(f"{len(idx)} pages; at most {MAX_OCR_PAGES} pages are read in one go (split it first).")
        for i in idx:
            page = doc[i]
            try:
                if not force and page.get_textpage().get_text_range().strip():
                    skipped.append(i + 1)
                    continue
                w, h = page.get_size()
                sc = dpi / 72
                if w * h * sc * sc > core.RENDER_MAX_PIXELS:
                    sc = (core.RENDER_MAX_PIXELS / (w * h)) ** 0.5
                im = page.render(scale=sc).to_pil().convert("L")
            finally:
                page.close()
            turn = _deskew_angle(im) if auto_rotate else 0
            if turn:
                rotated.append(i + 1)
                im = im.rotate(-turn, expand=True)
            layer = _text_page(im, round(sc * 72), langs)
            if turn:                                   # the text was read upright; turn the layer back to the page
                with pikepdf.open(io.BytesIO(layer)) as lp:
                    lp.pages[0].rotate(-turn, relative=True)
                    layer = core.save(lp)
            layers[i] = layer
    finally:
        doc.close()
    if not layers:
        return {"bytes": data, "done": [], "skipped_text": skipped, "rotated": [], "langs": langs, "chars": 0}
    keep = []
    with core.open_pdf(data) as pdf:
        from . import stamp
        for i, blob in layers.items():
            lp = pikepdf.open(io.BytesIO(blob))
            keep.append(lp)
            f = stamp.frame(pdf.pages[i])
            x0, y0 = f["mx"] + f["cx"], f["my"] + f["cy"]
            pdf.pages[i].add_overlay(lp.pages[0], pikepdf.Rectangle(x0, y0, x0 + f["cw"], y0 + f["ch"]))
        out = core.save(pdf)
    for k in keep:
        k.close()
    from . import convert
    texts = convert.page_texts(out, ",".join(str(i + 1) for i in sorted(layers)))
    chars = sum(len(t.strip()) for t in texts)
    empty = [sorted(layers)[k] + 1 for k, t in enumerate(texts) if not t.strip()]
    return {"bytes": out, "done": sorted(p + 1 for p in layers), "skipped_text": skipped, "rotated": rotated,
            "langs": langs, "chars": chars, "still_empty": empty}
