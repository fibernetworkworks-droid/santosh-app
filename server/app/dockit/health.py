"""D0: which document engines are on THIS server, each with one real, timed run (python -m app.dockit check).

LIVE = installed and a real conversion worked here. MISSING = not installed (the line to install it is printed).
BROKEN = installed but the real run failed (the reason is printed). Nothing is assumed from an import alone."""
from __future__ import annotations

import io
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any, Callable

APT = "sudo apt-get install -y"
PIP = "~/apps/santosh-core/.venv/bin/pip install"


def _sample_pdf(pages: int = 2, text: str = "Hoola check page") -> bytes:
    from reportlab.pdfgen import canvas
    b = io.BytesIO()
    c = canvas.Canvas(b)
    for i in range(pages):
        c.setFont("Helvetica", 18)
        c.drawString(72, 760, f"{text} {i + 1}")
        c.rect(72, 500, 200, 120)
        c.showPage()
    c.save()
    return b.getvalue()


def _timed(fn: Callable[[], str]) -> tuple[str, str, float]:
    t = time.monotonic()
    try:
        detail = fn()
        return "LIVE", detail, time.monotonic() - t
    except _Missing as e:
        return "MISSING", str(e), time.monotonic() - t
    except Exception as e:
        return "BROKEN", f"{type(e).__name__}: {str(e)[:160]}", time.monotonic() - t


class _Missing(Exception):
    pass


def _need_mod(mod: str, how: str):
    try:
        return __import__(mod)
    except Exception:
        raise _Missing(f"not installed -> {how}")


def _pikepdf() -> str:
    pk = _need_mod("pikepdf", f'{PIP} "pikepdf>=9.0"')
    from . import organize
    a = _sample_pdf(2)
    m = organize.merge([("a.pdf", a), ("b.pdf", a)])
    with pk.open(io.BytesIO(m)) as p:
        assert len(p.pages) == 4
    return f"pikepdf {pk.__version__} (qpdf {pk.__libqpdf_version__}): merge 2+2 = 4 pages"


def _pdfium() -> str:
    pd = _need_mod("pypdfium2", f'{PIP} "pypdfium2>=4"')
    from . import convert
    imgs = convert.pdf_to_images(_sample_pdf(1), dpi=72)
    t = convert.page_texts(_sample_pdf(1))[0]
    assert imgs and "Hoola" in t
    return f"pypdfium2 {getattr(pd, '__version__', '') or getattr(getattr(pd, 'version', None), 'PYPDFIUM_INFO', '')}: page drawn {imgs[0]['width']}x{imgs[0]['height']}, text read"


def _reportlab() -> str:
    rl = _need_mod("reportlab", f'{PIP} reportlab')
    return f"reportlab {rl.Version}: {len(_sample_pdf(1))} byte PDF made"


def _pillow() -> str:
    pil = _need_mod("PIL", f"{PIP} pillow")
    from PIL import Image
    from . import convert
    b = io.BytesIO()
    Image.new("RGB", (400, 300), (200, 30, 30)).save(b, "PNG")
    out = convert.images_to_pdf([("x.png", b.getvalue())], page_size="a4")
    return f"Pillow {pil.__version__}: picture -> A4 PDF {len(out)} bytes"


def _pypdf() -> str:
    pp = _need_mod("pypdf", f"{PIP} pypdf")
    r = pp.PdfReader(io.BytesIO(_sample_pdf(1)))
    return f"pypdf {pp.__version__}: {len(r.pages)} page read (forms come in D5)"


def _pyhanko() -> str:
    ph = _need_mod("pyhanko", f'{PIP} "pyhanko>=0.25"')
    return f"pyhanko {getattr(ph, '__version__', '')} (signatures: verify now, signing in D5)"


def _tesseract() -> str:
    exe = shutil.which("tesseract")
    if not exe:
        raise _Missing(f"not installed -> bash server/deploy/setup_ocr.sh (or {APT} tesseract-ocr)")
    out = subprocess.run([exe, "--version"], capture_output=True, text=True, timeout=20).stdout.splitlines()
    from ..ocr import TESSDATA as tess
    langs = sorted(p.stem for p in tess.glob("*.traineddata")) if tess.exists() else []
    return f"{out[0] if out else 'tesseract'}; Hoola models: {', '.join(langs) or 'system only'} (searchable PDF = D4)"


def _soffice() -> str:
    exe = shutil.which("soffice") or shutil.which("libreoffice")
    if not exe:
        raise _Missing(f"not installed -> {APT} libreoffice-core libreoffice-writer libreoffice-calc "
                       "libreoffice-impress --no-install-recommends  (Word / Excel / PowerPoint <-> PDF = D4)")
    with tempfile.TemporaryDirectory() as d:
        src = Path(d) / "check.txt"
        src.write_text("Hoola LibreOffice check\nदूसरी पंक्ति\n", encoding="utf-8")
        r = subprocess.run([exe, "--headless", "--norestore", f"-env:UserInstallation=file://{d}/lo",
                            "--convert-to", "pdf", "--outdir", d, str(src)], capture_output=True, text=True, timeout=180)
        pdf = Path(d) / "check.pdf"
        if not pdf.exists():
            raise RuntimeError((r.stderr or r.stdout or "no output")[-160:])
        return f"{exe}: text -> PDF {pdf.stat().st_size} bytes"


def _ocrmypdf() -> str:
    exe = shutil.which("ocrmypdf")
    if not exe:
        raise _Missing(f"not installed -> {APT} ocrmypdf  (searchable PDF + deskew = D4; Hoola's own OCR path works without it)")
    v = subprocess.run([exe, "--version"], capture_output=True, text=True, timeout=30).stdout.strip()
    return f"ocrmypdf {v}"


def _pdfplumber() -> str:
    pl = _need_mod("pdfplumber", f'{PIP} "pdfplumber>=0.11"  (PDF tables -> Excel = D4)')
    with pl.open(io.BytesIO(_sample_pdf(1))) as p:
        n = len(p.pages)
    return f"pdfplumber {pl.__version__}: {n} page opened"


def _verapdf() -> str:
    exe = shutil.which("verapdf")
    if not exe:
        java = shutil.which("java")
        raise _Missing("not installed (optional, PDF/A validation = D4) -> " +
                       ("download veraPDF from verapdf.org" if java else f"{APT} default-jre-headless, then veraPDF"))
    return f"veraPDF at {exe}"


def _ghostscript() -> str:
    exe = shutil.which("gs")
    note = "owner decision D2: NOT used (AGPL-3.0) - compression uses pikepdf + Pillow"
    if not exe:
        raise _Missing(note)
    return f"present at {exe}; {note}"


ENGINES: list[tuple[str, str, Callable[[], str]]] = [
    ("pikepdf", "D1 core", _pikepdf), ("pypdfium2", "D1 core", _pdfium), ("reportlab", "D1 core", _reportlab),
    ("pillow", "D1 core", _pillow), ("pypdf", "D5 forms", _pypdf), ("pyhanko", "D5 sign", _pyhanko),
    ("tesseract", "D4 ocr", _tesseract), ("libreoffice", "D4 office", _soffice), ("ocrmypdf", "D4 ocr", _ocrmypdf),
    ("pdfplumber", "D4 tables", _pdfplumber), ("verapdf", "D4 pdf/a", _verapdf), ("ghostscript", "not used", _ghostscript),
]
CORE = {"pikepdf", "pypdfium2", "reportlab", "pillow"}


def check() -> dict[str, Any]:
    rows = []
    for name, phase, fn in ENGINES:
        state, detail, secs = _timed(fn)
        rows.append({"engine": name, "phase": phase, "state": state, "detail": detail, "seconds": round(secs, 2)})
    core_ok = all(r["state"] == "LIVE" for r in rows if r["engine"] in CORE)
    return {"engines": rows, "core_ok": core_ok,
            "say": ("Every D1 action can run on this server." if core_ok else
                    "A core engine is missing or broken: D1 actions will refuse until it is fixed (see the lines above).")}


def ready() -> dict[str, bool]:
    """Cheap import-level flags for the tool's guide (the full check is the CLI)."""
    def has(m: str) -> bool:
        try:
            __import__(m)
            return True
        except Exception:
            return False
    return {"pikepdf": has("pikepdf"), "pypdfium2": has("pypdfium2"), "reportlab": has("reportlab"),
            "libreoffice": bool(shutil.which("soffice") or shutil.which("libreoffice")),
            "tesseract": bool(shutil.which("tesseract")), "ocrmypdf": bool(shutil.which("ocrmypdf")),
            "pdfplumber": has("pdfplumber")}


def lines(rep: dict[str, Any]) -> list[str]:
    out = ["HOOLA DOCUMENT KIT - engines on this server"]
    for r in rep["engines"]:
        out.append(f"  {r['state']:<8} {r['engine']:<12} [{r['phase']}] {r['seconds']:>6}s  {r['detail']}")
    out.append("")
    out.append(rep["say"])
    return out
