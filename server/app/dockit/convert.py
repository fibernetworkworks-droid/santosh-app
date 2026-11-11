"""Convert (D1 part): pictures -> PDF (Pillow + ReportLab), PDF pages -> pictures (pypdfium2), the pictures inside a
PDF as they are (pikepdf), PDF -> text / markdown (pypdfium2 text, markitdown when installed).

Office <-> PDF, HTML -> PDF, OCR, PDF -> Word / Excel / PowerPoint and PDF/A are D4 (they need LibreOffice / ocrmypdf
/ pdfplumber on the server - `python -m app.dockit check` says which are there)."""
from __future__ import annotations

import io
from typing import Any

from . import core
from .core import DocError

IMAGE_MAGIC = (b"\xff\xd8\xff", b"\x89PNG", b"GIF8", b"RIFF", b"BM", b"II*\x00", b"MM\x00*")
PAGE_SIZES = {"a4": (595.28, 841.89), "letter": (612.0, 792.0), "legal": (612.0, 1008.0), "a5": (419.53, 595.28)}
MARGINS = {"none": 0, "small": 18, "big": 42}


def is_image(data: bytes) -> bool:
    head = data[:12]
    if head[:4] == b"RIFF" and data[8:12] != b"WEBP":
        return False
    return any(head.startswith(m) for m in IMAGE_MAGIC) or data[4:12] in (b"ftypheic", b"ftypheix", b"ftypmif1")


def _pil(name: str, data: bytes):
    from PIL import Image, ImageOps
    try:
        im = Image.open(io.BytesIO(data))
        im.load()
    except Exception:
        raise DocError(f"{name} could not be read as a picture (JPG, PNG, WEBP, GIF, TIFF, BMP work).")
    im = ImageOps.exif_transpose(im)
    if im.mode not in ("RGB", "L"):
        bg = Image.new("RGB", im.size, (255, 255, 255))
        rgba = im.convert("RGBA")
        bg.paste(rgba, mask=rgba.split()[-1])
        im = bg
    return im


def images_to_pdf(images: list[tuple[str, bytes]], page_size: str = "fit", orientation: str = "auto",
                  margin: str = "none", quality: int = 85) -> bytes:
    """One page per picture, in her order. page_size fit = the page IS the picture; a4 / letter / legal / a5 = the
    picture centred and fitted inside the margin. Metadata (camera, GPS) never travels: pixels only."""
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfgen import canvas
    if not images:
        raise DocError("Give at least one picture.")
    if len(images) > core.RENDER_MAX_PAGES:
        raise DocError(f"At most {core.RENDER_MAX_PAGES} pictures in one PDF.")
    ps = (page_size or "fit").lower()
    if ps != "fit" and ps not in PAGE_SIZES:
        raise DocError(f"page_size = fit | {' | '.join(PAGE_SIZES)}.")
    m = MARGINS.get((margin or "none").lower())
    if m is None:
        raise DocError("margin = none | small | big.")
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pageCompression=1)
    c.setTitle("Hoola")
    c.setAuthor("")
    c.setCreator("Hoola")
    for name, data in images:
        im = _pil(name, data)
        if max(im.size) > 4000:                       # a 48 MP phone photo is ~5 MB of PDF for no visible gain
            im.thumbnail((4000, 4000))
        jb = io.BytesIO()
        im.save(jb, "JPEG", quality=int(quality), optimize=True)
        jb.seek(0)
        w, h = im.size
        if ps == "fit":
            pw, ph = w * 72 / 150, h * 72 / 150       # 150 dpi: sensible print size for a phone photo
            pw, ph = pw + 2 * m, ph + 2 * m
        else:
            pw, ph = PAGE_SIZES[ps]
            o = (orientation or "auto").lower()
            if o == "landscape" or (o == "auto" and w > h):
                pw, ph = ph, pw
        c.setPageSize((pw, ph))
        aw, ah = pw - 2 * m, ph - 2 * m
        s = min(aw / w, ah / h)
        dw, dh = w * s, h * s
        c.drawImage(ImageReader(jb), (pw - dw) / 2, (ph - dh) / 2, dw, dh)
        c.showPage()
    c.save()
    return buf.getvalue()


def pdf_to_images(data: bytes, spec: Any = "all", dpi: int = 150, fmt: str = "jpg") -> list[dict[str, Any]]:
    """Each chosen page drawn as a picture. dpi 72-300 (600 for small pages)."""
    import pypdfium2 as pdfium
    fmt = (fmt or "jpg").lower().replace("jpeg", "jpg")
    if fmt not in ("jpg", "png", "webp"):
        raise DocError("format = jpg | png | webp.")
    dpi = int(dpi or 150)
    if not 36 <= dpi <= 600:
        raise DocError("dpi must be between 36 and 600 (150 is good for screens, 300 for print).")
    core.check_size(data)
    try:
        doc = pdfium.PdfDocument(data)
    except Exception as e:
        raise DocError(f"This PDF could not be opened ({type(e).__name__}); a password PDF needs an unlocked copy.")
    out = []
    try:
        idx = core.pages(spec or "all", len(doc))
        if len(idx) > core.RENDER_MAX_PAGES:
            raise DocError(f"{len(idx)} pages; at most {core.RENDER_MAX_PAGES} pages become pictures in one go.")
        for i in idx:
            page = doc[i]
            try:
                w, h = page.get_size()
                scale = dpi / 72
                if w * h * scale * scale > core.RENDER_MAX_PIXELS:
                    scale = (core.RENDER_MAX_PIXELS / (w * h)) ** 0.5
                im = page.render(scale=scale).to_pil().convert("RGB")
            finally:
                page.close()
            b = io.BytesIO()
            if fmt == "jpg":
                im.save(b, "JPEG", quality=88, optimize=True)
            elif fmt == "webp":
                im.save(b, "WEBP", quality=85)
            else:
                im.save(b, "PNG", optimize=True)
            out.append({"page": i + 1, "ext": fmt, "width": im.width, "height": im.height, "bytes": b.getvalue()})
    finally:
        doc.close()
    return out


def extract_images(data: bytes, spec: Any = "all", min_px: int = 64) -> list[dict[str, Any]]:
    """The pictures stored inside the PDF, at their own resolution (each one once, even if it repeats)."""
    import pikepdf
    seen, out = set(), []
    with core.open_pdf(data) as pdf:
        for i in core.pages(spec or "all", len(pdf.pages)):
            for _, raw in list(core.images_of(pdf.pages[i]).items()):
                if raw.objgen in seen:
                    continue
                seen.add(raw.objgen)
                try:
                    pim = pikepdf.PdfImage(raw)
                    if pim.width < min_px or pim.height < min_px:
                        continue
                    b = io.BytesIO()
                    ext = pim.extract_to(stream=b).lstrip(".")
                    if ext not in ("jpg", "png", "jp2", "tif"):
                        b = io.BytesIO()
                        pim.as_pil_image().convert("RGB").save(b, "PNG")
                        ext = "png"
                    out.append({"page": i + 1, "ext": ext, "width": pim.width, "height": pim.height,
                                "bytes": b.getvalue()})
                except Exception:
                    continue
                if len(out) >= core.RENDER_MAX_PAGES:
                    return out
    return out


def page_texts(data: bytes, spec: Any = "all") -> list[str]:
    import pypdfium2 as pdfium
    core.check_size(data)
    try:
        doc = pdfium.PdfDocument(data)
    except Exception as e:
        raise DocError(f"This PDF could not be opened ({type(e).__name__}).")
    try:
        texts = []
        for i in core.pages(spec or "all", len(doc)):
            page = doc[i]
            try:
                texts.append(page.get_textpage().get_text_range().replace("\r\n", "\n").replace("\r", "\n"))
            finally:
                page.close()
        return texts
    finally:
        doc.close()


def pdf_to_text(data: bytes, fmt: str = "txt", spec: Any = "all") -> dict[str, Any]:
    """Plain text or markdown (a heading per page). Pages with no text are named: they are pictures (scans) and need
    OCR - file_read reads them now; a searchable PDF comes with D4."""
    fmt = (fmt or "txt").lower()
    if fmt not in ("txt", "md"):
        raise DocError("format = txt | md.")
    texts = page_texts(data, spec)
    empty = [i + 1 for i, t in enumerate(texts) if not t.strip()]
    if fmt == "md":
        md = ""
        try:
            if spec in (None, "", "all"):
                from markitdown import MarkItDown
                md = MarkItDown().convert_stream(io.BytesIO(data), file_extension=".pdf").text_content or ""
        except Exception:
            md = ""
        if not md.strip():
            md = "\n\n".join(f"## Page {i + 1}\n\n{t.strip()}" for i, t in enumerate(texts) if t.strip())
        body = md
    else:
        body = "\n\n".join(t.strip() for t in texts)
    return {"text": body, "pages": len(texts), "no_text_pages": empty, "chars": len(body)}


# ------------------------------------------------------------------ Office / text -> PDF (LibreOffice headless)
OFFICE_EXT = {".doc", ".docx", ".odt", ".rtf", ".txt", ".xls", ".xlsx", ".ods", ".csv", ".ppt", ".pptx", ".odp"}
_LO_LOCK = None


def office_ready() -> bool:
    import shutil
    return bool(shutil.which("soffice") or shutil.which("libreoffice"))


def office_to_pdf(name: str, data: bytes, timeout: int = 240) -> bytes:
    """Word / Excel / PowerPoint / OpenDocument / RTF / text -> PDF with LibreOffice on the server (her file never
    leaves it). One conversion at a time (LibreOffice is memory-heavy), own throwaway profile, killed on timeout."""
    import os
    import shutil
    import signal
    import subprocess
    import tempfile
    import threading
    from pathlib import Path
    global _LO_LOCK
    exe = shutil.which("soffice") or shutil.which("libreoffice")
    if not exe:
        raise DocError("Word / Excel / PowerPoint to PDF needs LibreOffice on the server, and it is not installed yet "
                       "(owner: run vps-ops > docs_setup).")
    ext = Path(name or "").suffix.lower()
    if ext not in OFFICE_EXT:
        raise DocError(f"{name} is not an Office or text file ({', '.join(sorted(OFFICE_EXT))}).")
    core.check_size(data, name)
    if _LO_LOCK is None:
        _LO_LOCK = threading.Lock()
    with _LO_LOCK, tempfile.TemporaryDirectory(prefix="hoola-lo-") as d:
        src = Path(d) / f"in{ext}"
        src.write_bytes(data)
        env = {k: v for k, v in os.environ.items() if k in ("PATH", "LANG", "LC_ALL", "HOME", "TMPDIR")}
        env["HOME"] = d
        p = subprocess.Popen([exe, "--headless", "--norestore", "--nolockcheck", f"-env:UserInstallation=file://{d}/lo",
                              "--convert-to", "pdf", "--outdir", d, str(src)], stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE, env=env, start_new_session=True)
        try:
            _, err = p.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            os.killpg(p.pid, signal.SIGKILL)
            p.communicate()
            raise DocError(f"{name} took longer than {timeout} s to convert and was stopped.")
        out = Path(d) / "in.pdf"
        if not out.exists() or out.stat().st_size == 0:
            raise DocError(f"{name} could not be converted ({(err or b'').decode(errors='ignore')[-120:].strip() or 'no output'}).")
        return out.read_bytes()
