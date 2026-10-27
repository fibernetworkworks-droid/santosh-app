"""v0.49 Reading documents for the avatar: Microsoft MarkItDown (MIT) first (tables stay tables, headings stay headings),
the older built-in readers (mailbox.mime.attachment_text) as the fallback. PDFs keep pypdf (page numbers)."""
from __future__ import annotations

import io
import logging
from pathlib import Path
from typing import Any

log = logging.getLogger("santosh.docread")
MARKITDOWN_EXT = {".docx", ".pptx", ".xlsx", ".xls", ".html", ".htm", ".epub", ".csv", ".json", ".xml", ".msg", ".ipynb"}
_MD = None


def _md():
    global _MD
    if _MD is None:
        try:
            from markitdown import MarkItDown
            _MD = MarkItDown(enable_plugins=False)
        except Exception as e:
            log.info("markitdown unavailable: %s", e)
            _MD = False
    return _MD or None


def read_text(name: str, mime: str, data: bytes, limit: int = 20000, max_pages: int = 60) -> dict[str, Any]:
    from .mailbox import mime as mm
    ext = Path(name or "").suffix.lower()
    if ext in MARKITDOWN_EXT and _md() is not None:
        try:
            from markitdown import StreamInfo
            r = _md().convert_stream(io.BytesIO(data), stream_info=StreamInfo(extension=ext, filename=name))
            text = (r.text_content or "").strip()
            if text:
                return {"kind": ext.lstrip("."), "text": text[:limit], "truncated": len(text) > limit, "reader": "markitdown"}
        except Exception as e:
            log.info("markitdown could not read %s: %s", name, e)
    out = mm.attachment_text(name, mime or "application/octet-stream", data, limit=limit, max_pages=max_pages)
    out.setdefault("reader", "builtin")
    return out
