"""Gyaan: bytes of a file -> plain text, on the VPS CPU only (no paid vision call at ingest).

Word / Excel / PowerPoint / HTML / EPUB / CSV via MarkItDown (docread), PDFs via pypdf, scanned PDFs and photos via the
owner's-language Tesseract (ocr.py) when it is installed. Audio / video are not indexed (said plainly)."""
from __future__ import annotations

import mimetypes
from pathlib import Path
from typing import Any

MAX_CHARS = 600_000
SHEET_EXT = {".csv", ".tsv", ".xlsx", ".xls", ".ods"}
IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff", ".heic"}
AV_EXT = {".mp3", ".m4a", ".wav", ".ogg", ".opus", ".aac", ".mp4", ".mov", ".mkv", ".webm", ".3gp", ".avi"}


def _lang(tenant: str) -> str:
    try:
        from ..agent.file_tools import _owner_lang
        return _owner_lang(tenant)
    except Exception:
        return ""


def text_of(name: str, data: bytes, tenant: str = "", mime: str = "") -> dict[str, Any]:
    """-> {text, kind (doc|sheet|pdf|image|slides), ocr (bool), note}"""
    ext = Path(name or "").suffix.lower()
    mime = mime or mimetypes.guess_type(name or "")[0] or "application/octet-stream"
    if ext in AV_EXT or mime.startswith(("audio/", "video/")):
        return {"text": "", "kind": "media", "ocr": False,
                "note": "Audio / video Gyaan mein nahi jaata (sirf likha hua). Iska transcript chahiye to chat mein bhejiye."}
    if ext in IMAGE_EXT or mime.startswith("image/"):
        from .. import ocr
        r = ocr.read(data, _lang(tenant)) if ocr.available() else None
        if r and (r.get("text") or "").strip():
            return {"text": r["text"][:MAX_CHARS], "kind": "image", "ocr": True, "note": "" if r.get("good") else "Photo saaf nahi thi; kuch shabd galat ho sakte hain."}
        return {"text": "", "kind": "image", "ocr": False,
                "note": "Photo se text nahi nikla (OCR nahi hai ya photo dhundhli hai)."}
    from ..docread import read_text
    r = read_text(name or "file", mime, data, limit=MAX_CHARS, max_pages=300)
    text = (r.get("text") or "").strip()
    kind = "sheet" if ext in SHEET_EXT else ("slides" if ext in (".ppt", ".pptx") else ("pdf" if ext == ".pdf" else "doc"))
    if not text and ext == ".pdf":
        from .. import ocr
        o = ocr.read_pdf(data, _lang(tenant), max_pages=20) if ocr.available() else None
        if o and (o.get("text") or "").strip():
            return {"text": o["text"][:MAX_CHARS], "kind": "pdf", "ocr": True,
                    "note": "" if o.get("good") else "Scan saaf nahi tha; kuch shabd galat ho sakte hain."}
        return {"text": "", "kind": "pdf", "ocr": False, "note": "Scan kiya hua PDF hai aur OCR nahi chala; text nahi mila."}
    if not text:
        return {"text": "", "kind": kind, "ocr": False, "note": "Is file mein padhne layak text nahi mila."}
    if ext in (".doc", ".docx", ".rtf", ".pdf", ".odt"):      # legacy Kruti Dev font lives in typed Word / PDF files only
        try:
            from ..lekhak.krutidev import looks_krutidev, to_unicode
            if looks_krutidev(text):
                text = to_unicode(text)
        except Exception:
            pass
    return {"text": text, "kind": kind, "ocr": False, "note": "Bahut lambi file; pehla hissa liya." if r.get("truncated") else ""}
