"""D4 PDF/A (archival PDF) and web page -> PDF.

PDF/A without Ghostscript (owner decision D2): mode keep = the file as it is + the sRGB output intent + PDF/A XMP
identity + scripts / attachments out - only when every font is embedded (that is checked first, font by font);
mode pages = each page redrawn as a picture with an OCR text layer (always possible, the text stays searchable,
but the original text objects are replaced - said). It is called PDF/A ONLY when veraPDF validates it; without
veraPDF on the server the card says 'made to PDF/A-2b rules, not validated' - never 'compliant'.

Web page -> PDF: Hoola's own Chromium prints the page; every request the page makes passes the house SSRF guard
(public http(s) hosts only), and the run is capped in time."""
from __future__ import annotations

import io
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import core
from .core import DocError

LEVELS = {"2b": ("2", "B"), "3b": ("3", "B"), "1b": ("1", "B")}


def font_problems(data: bytes) -> list[str]:
    """Fonts that are used but not embedded (a PDF/A rule)."""
    import pikepdf
    bad: set[str] = set()
    with core.open_pdf(data) as pdf:
        for page in pdf.pages:
            fonts = page.obj.get("/Resources", {}).get("/Font", {}) or {}
            try:                                   # only fonts that really DRAW text (Tf then Tj / TJ / ' / ")
                used, cur = set(), None
                for ops, op in pikepdf.parse_content_stream(page):
                    o = str(op)
                    if o == "Tf" and ops:
                        cur = str(ops[0])
                    elif o in ("Tj", "TJ", "'", '"') and cur:
                        used.add(cur)
            except Exception:
                used = {str(k) for k in fonts.keys()}
            for key, f in fonts.items():
                if str(key) not in used:
                    continue
                try:
                    sub = str(f.get("/Subtype", ""))
                    if sub == "/Type3":
                        continue
                    desc = f.get("/FontDescriptor")
                    if sub == "/Type0":
                        desc = f.DescendantFonts[0].get("/FontDescriptor")
                    if desc is None or not any(k in desc for k in ("/FontFile", "/FontFile2", "/FontFile3")):
                        bad.add(str(f.get("/BaseFont", "?")).lstrip("/"))
                except Exception:
                    bad.add("?")
    return sorted(bad)


def _srgb() -> bytes:
    from PIL import ImageCms
    return ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()


def _mark(data: bytes, level: str, title: str = "") -> bytes:
    import pikepdf
    part, conf = LEVELS[level]
    with core.open_pdf(data) as pdf:
        names = pdf.Root.get("/Names")
        if names is not None:
            for k in ("/JavaScript", "/EmbeddedFiles"):
                if k in names and not (k == "/EmbeddedFiles" and part == "3"):
                    del names[k]
        for k in ("/OpenAction", "/AA"):
            if k in pdf.Root:
                del pdf.Root[k]
        icc = pdf.make_stream(_srgb())
        icc.N = 3
        intent = pikepdf.Dictionary(Type=pikepdf.Name.OutputIntent, S=pikepdf.Name.GTS_PDFA1,
                                    OutputConditionIdentifier=pikepdf.String("sRGB IEC61966-2.1"),
                                    Info=pikepdf.String("sRGB IEC61966-2.1"), DestOutputProfile=icc)
        pdf.Root.OutputIntents = pikepdf.Array([intent])
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with pdf.open_metadata(set_pikepdf_as_editor=False) as m:
            m["pdfaid:part"] = part
            m["pdfaid:conformance"] = conf
            if title:
                m["dc:title"] = title
            m["xmp:CreatorTool"] = "Hoola"
            m["xmp:ModifyDate"] = now
        if pdf.docinfo is not None:
            pdf.docinfo["/Producer"] = pikepdf.String("Hoola")
        buf = io.BytesIO()
        pdf.save(buf, compress_streams=True, object_stream_mode=pikepdf.ObjectStreamMode.disable,
                 fix_metadata_version=True)
        return buf.getvalue()


def verapdf_ready() -> bool:
    return bool(shutil.which("verapdf"))


def validate(data: bytes, level: str = "2b") -> dict[str, Any]:
    exe = shutil.which("verapdf")
    if not exe:
        return {"validated": False, "compliant": None, "why": "veraPDF is not installed on the server, so it is "
                "made to PDF/A rules but NOT validated (owner: vps-ops > docs_setup)."}
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "a.pdf"
        p.write_bytes(data)
        try:
            out = subprocess.run([exe, "--flavour", level, "--format", "text", str(p)], capture_output=True, text=True,
                                 timeout=240).stdout
        except Exception as e:
            return {"validated": False, "compliant": None, "why": f"veraPDF did not finish ({type(e).__name__})."}
    ok = out.strip().upper().startswith("PASS")
    return {"validated": True, "compliant": ok, "why": out.strip()[:300]}


def to_pdfa(data: bytes, level: str = "2b", mode: str = "auto", language: str = "") -> dict[str, Any]:
    level = (level or "2b").lower().replace("pdf/a-", "").replace("pdfa", "")
    if level not in LEVELS:
        raise DocError(f"level = {' | '.join(LEVELS)}.")
    mode = (mode or "auto").lower()
    if mode not in ("auto", "keep", "pages"):
        raise DocError("mode = auto | keep | pages.")
    fonts = font_problems(data)
    notes: list[str] = []
    if mode == "keep" and fonts:
        raise DocError(f"These fonts are not inside the file: {', '.join(fonts[:6])}. PDF/A needs every font inside; "
                       "use mode=pages (each page redrawn with a text layer) instead.")
    if mode == "pages" or (mode == "auto" and fonts):
        from . import ocrlayer
        if not ocrlayer.ready():
            raise DocError("This PDF uses fonts that are not inside it, and turning its pages into archival pictures "
                           "needs the text reader (Tesseract) on the server, which is not installed yet.")
        pages_pdf = _redraw_all(data)
        data = ocrlayer.searchable(pages_pdf, language, force=True)["bytes"]
        notes.append("Each page was redrawn as a picture with a searchable text layer, because the original used fonts "
                     "that were not inside the file" if fonts else "Each page was redrawn as a picture with a "
                     "searchable text layer")
    out = _mark(data, level)
    v = validate(out, level)
    if v["validated"] and not v["compliant"]:
        notes.append("veraPDF found problems: " + v["why"][:200])
    return {"bytes": out, "level": f"PDF/A-{level.upper()}", "validated": v["validated"], "compliant": v["compliant"],
            "why": v["why"], "fonts_not_embedded": fonts, "notes": notes}


def _redraw_all(data: bytes) -> bytes:
    import pypdfium2 as pdfium
    doc = pdfium.PdfDocument(data)
    pics = []
    try:
        if len(doc) > core.RENDER_MAX_PAGES:
            raise DocError(f"At most {core.RENDER_MAX_PAGES} pages can be redrawn in one go.")
        for i in range(len(doc)):
            pg = doc[i]
            try:
                w, h = pg.get_size()
                im = pg.render(scale=200 / 72).to_pil().convert("RGB")
            finally:
                pg.close()
            b = io.BytesIO()
            im.save(b, "JPEG", quality=88)
            pics.append((w, h, b.getvalue()))
    finally:
        doc.close()
    from .secure import _picture_page
    import pikepdf
    out = pikepdf.new()
    keep = []
    for w, h, jpg in pics:
        src = pikepdf.open(io.BytesIO(_picture_page(jpg, w, h)))
        keep.append(src)
        out.pages.append(src.pages[0])
    blob = core.save(out)
    for k in keep:
        k.close()
    return blob


# --------------------------------------------------------------------------------------------- web page -> PDF
def url_to_pdf(url: str, page_size: str = "A4", landscape: bool = False, timeout_s: int = 45) -> tuple[bytes, str]:
    """-> (pdf bytes, page title). Only public http(s) pages; every request the page makes is checked too."""
    import os
    from ..agent.scrape_tools import _guard_url
    from ..agent.tools import ToolError
    try:
        url = _guard_url(url)
    except ToolError as e:
        raise DocError(str(e))
    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        raise DocError("The web printer (Chromium) is not installed on the server.")
    kw: dict[str, Any] = {"headless": True, "args": ["--no-sandbox", "--disable-dev-shm-usage"]}
    if os.environ.get("HOOLA_CHROMIUM"):
        kw["executable_path"] = os.environ["HOOLA_CHROMIUM"]
    blocked: list[str] = []

    def route(r):
        u = r.request.url
        if u.startswith(("data:", "blob:", "about:")):
            return r.continue_()
        try:
            _guard_url(u)
        except Exception:
            blocked.append(u[:80])
            return r.abort()
        return r.continue_()
    with sync_playwright() as pw:
        try:
            browser = pw.chromium.launch(**kw)
        except Exception as e:
            raise DocError(f"The web printer could not start ({type(e).__name__}).")
        try:
            ctx = browser.new_context(java_script_enabled=True, accept_downloads=False,
                                      user_agent="Mozilla/5.0 (Hoola document kit)")
            page = ctx.new_page()
            page.route("**/*", route)
            try:
                page.goto(url, wait_until="networkidle", timeout=timeout_s * 1000)
            except Exception as e:
                if "Timeout" not in type(e).__name__:
                    raise DocError(f"The page could not be opened ({str(e)[:120]}).")
            title = page.title()[:120]
            pdf = page.pdf(format=page_size if page_size in ("A4", "Letter", "Legal", "A3", "A5") else "A4",
                           landscape=bool(landscape), print_background=True,
                           margin={"top": "12mm", "bottom": "12mm", "left": "10mm", "right": "10mm"})
        finally:
            browser.close()
    if not pdf:
        raise DocError("The page printed empty.")
    return pdf, title or url
