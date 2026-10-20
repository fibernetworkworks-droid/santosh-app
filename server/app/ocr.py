"""v0.59 Reads the text in photos and scanned PDFs on our own CPU (Tesseract, Apache-2.0, with the tessdata_best models
for Hindi, Marathi, Tamil, Telugu, Kannada, Malayalam, Bengali, Gujarati, Punjabi, Odia, Urdu, Sanskrit + English).

The paid vision models are only called when this read is weak (little text or low confidence), so most bills,
receipts, notices and screenshots are read for free. deploy/setup_ocr.sh installs the tesseract binary and downloads
the models into data/tessdata. Without tesseract, read() returns None and Hoola works exactly as before.
"""
from __future__ import annotations

import io
import logging
import os
import shutil
import subprocess
import tempfile
import threading
from pathlib import Path
from typing import Any

log = logging.getLogger("santosh.ocr")

TESSDATA = Path("data") / "tessdata"
GOOD_CONF = 60          # mean word confidence at which the read is trusted
GOOD_CHARS = 25
MAX_PIXELS = 4200        # longest side sent to tesseract
# owner's language -> tesseract models, English always added (bills mix both)
LANG_MODELS = {"hindi": "hin", "hinglish": "hin", "hi": "hin", "marathi": "mar", "mr": "mar", "tamil": "tam", "ta": "tam",
               "telugu": "tel", "te": "tel", "kannada": "kan", "kn": "kan", "malayalam": "mal", "ml": "mal",
               "bengali": "ben", "bn": "ben", "gujarati": "guj", "gu": "guj", "punjabi": "pan", "pa": "pan",
               "odia": "ori", "or": "ori", "urdu": "urd", "ur": "urd", "sanskrit": "san", "english": "", "en": ""}
_langs: set[str] | None = None
_lock = threading.Lock()


def _bin() -> str | None:
    return shutil.which("tesseract")


def _env() -> dict[str, str]:
    env = dict(os.environ)
    if (TESSDATA / "eng.traineddata").exists() or any(TESSDATA.glob("*.traineddata")):
        env["TESSDATA_PREFIX"] = str(TESSDATA.resolve())
    env["OMP_THREAD_LIMIT"] = "2"          # never eat the whole VPS
    return env


def available() -> bool:
    return bool(_bin()) and bool(installed_langs())


def installed_langs() -> set[str]:
    global _langs
    with _lock:
        if _langs is None:
            _langs = set()
            b = _bin()
            if b:
                try:
                    out = subprocess.run([b, "--list-langs"], capture_output=True, text=True, timeout=10, env=_env()).stdout
                    _langs = {x.strip() for x in out.splitlines()[1:] if x.strip()}
                except Exception as e:
                    log.info("tesseract langs: %s", e)
        return set(_langs)


def reset() -> None:          # tests / after setup_ocr.sh
    global _langs
    with _lock:
        _langs = None


def langs_for(language: str = "", extra: str = "") -> str:
    have = installed_langs()
    want = []
    for code in (LANG_MODELS.get((language or "").lower(), ""), *(extra.split("+") if extra else [])):
        if code and code in have and code not in want:
            want.append(code)
    if "eng" in have:
        want.append("eng")
    return "+".join(want) or "eng"


def _prepare(data: bytes) -> bytes:
    """Grey, upright, big enough: what tesseract reads best. Returns PNG bytes."""
    from PIL import Image, ImageOps
    im = Image.open(io.BytesIO(data))
    im = ImageOps.exif_transpose(im)
    if im.mode not in ("L", "RGB"):
        im = im.convert("RGB")
    im = ImageOps.grayscale(im)
    w, h = im.size
    long = max(w, h)
    if long < 1300:                          # phone thumbnails / screenshots of small text
        f = min(2.5, 1600 / max(1, long))
        im = im.resize((int(w * f), int(h * f)), Image.LANCZOS)
    elif long > MAX_PIXELS:
        f = MAX_PIXELS / long
        im = im.resize((int(w * f), int(h * f)), Image.LANCZOS)
    im = ImageOps.autocontrast(im, cutoff=1)
    buf = io.BytesIO()
    im.save(buf, "PNG")
    return buf.getvalue()


def _parse_tsv(tsv: str) -> tuple[str, float, int]:
    lines: dict[tuple, list[str]] = {}
    confs = []
    for row in tsv.splitlines()[1:]:
        p = row.split("\t")
        if len(p) < 12 or p[0] != "5":
            continue
        word = p[11].strip()
        try:
            conf = float(p[10])
        except ValueError:
            continue
        if not word or conf < 0:
            continue
        lines.setdefault((int(p[2]), int(p[3]), int(p[4])), []).append(word)
        confs.append(conf)
    text = "\n".join(" ".join(ws) for _, ws in sorted(lines.items()))
    return text, (sum(confs) / len(confs) if confs else 0.0), len(confs)


def read(data: bytes, language: str = "", langs: str = "", psm: int = 3, timeout: int = 60) -> dict[str, Any] | None:
    """{text, conf (0-100), words, langs, good} or None when OCR is not installed / the picture can't be read."""
    b = _bin()
    if not b or not data:
        return None
    try:
        png = _prepare(data)
    except Exception as e:
        log.info("ocr prepare: %s", e)
        return None
    lg = langs or langs_for(language)
    with tempfile.TemporaryDirectory(prefix="hoola-ocr-") as d:
        src = Path(d) / "in.png"
        src.write_bytes(png)
        try:
            r = subprocess.run([b, str(src), "stdout", "-l", lg, "--psm", str(psm), "-c", "tessedit_create_tsv=1"], capture_output=True,
                               text=True, timeout=timeout, env=_env())
        except Exception as e:
            log.info("ocr run: %s", e)
            return None
    if r.returncode != 0 and not r.stdout:
        log.info("ocr failed: %s", (r.stderr or "")[:200])
        return None
    text, conf, words = _parse_tsv(r.stdout)
    return {"text": text, "conf": round(conf, 1), "words": words, "langs": lg,
            "good": len(text) >= GOOD_CHARS and conf >= GOOD_CONF}


def read_pdf(data: bytes, language: str = "", max_pages: int = 5) -> dict[str, Any] | None:
    """A scanned PDF (no text layer): each page as a picture, then read()."""
    if not _bin():
        return None
    try:
        import pypdfium2 as pdfium
        doc = pdfium.PdfDocument(data)
    except Exception as e:
        log.info("ocr pdf open: %s", e)
        return None
    texts, confs, words = [], [], 0
    try:
        for i in range(min(len(doc), max_pages)):
            page = doc[i]
            img = page.render(scale=200 / 72).to_pil()
            buf = io.BytesIO()
            img.save(buf, "PNG")
            r = read(buf.getvalue(), language)
            if r and r["text"]:
                texts.append(f"--- page {i + 1} ---\n{r['text']}")
                confs.append(r["conf"])
                words += r["words"]
        pages = len(doc)
    finally:
        doc.close()
    if not texts:
        return None
    conf = sum(confs) / len(confs)
    text = "\n".join(texts)
    return {"text": text, "conf": round(conf, 1), "words": words, "pages_read": len(texts), "pages": pages,
            "good": len(text) >= GOOD_CHARS and conf >= GOOD_CONF}
