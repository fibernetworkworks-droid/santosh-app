"""v0.49 What a file REALLY is (Google Magika, Apache-2.0), whatever its name says.

real_type(name, data) -> {label, group, mime, score, claimed, mismatch, danger, note}
  danger   = the name says document / photo / media but the bytes are a program or script (classic trick:
             "bill.pdf" that is an .exe). Owner uploads like that are refused; peer files are declined.
  mismatch = the content is another harmless type than the name says (just noted).
Magika is optional: without it (or on any error) the old name-based checks still run.
"""
from __future__ import annotations

import logging
import threading
from pathlib import Path
from typing import Any

log = logging.getLogger("santosh.filecheck")

SAFE_CLAIMS = {
    "document": {".pdf", ".doc", ".docx", ".odt", ".rtf", ".txt", ".md", ".xls", ".xlsx", ".csv", ".ods", ".ppt", ".pptx",
                 ".odp", ".epub", ".json", ".xml", ".html", ".htm"},
    "image": {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".heic", ".heif", ".tif", ".tiff"},
    "media": {".mp3", ".m4a", ".aac", ".ogg", ".opus", ".wav", ".amr", ".mp4", ".mov", ".m4v", ".webm", ".3gp", ".mkv"},
}
DANGER_GROUPS = {"executable"}
DANGER_LABELS = {"shell", "batch", "powershell", "vba", "javascript", "vbs", "hta", "jar", "msi", "lnk", "dex", "apk",
                 "elf", "pebin", "macho", "dmg", "deb", "rpm", "scr"}
# text that legitimately looks like code (a .txt with a script inside is still not run by anyone)
TEXT_OK = {".txt", ".md", ".json", ".xml", ".html", ".htm", ".csv"}
_M = None
_LOCK = threading.Lock()


def _magika():
    global _M
    if _M is None:
        with _LOCK:
            if _M is None:
                try:
                    from magika import Magika
                    _M = Magika()
                except Exception as e:          # not installed / model missing: name checks only
                    log.info("magika unavailable: %s", e)
                    _M = False
    return _M or None


def available() -> bool:
    return _magika() is not None


def real_type(name: str, data: bytes) -> dict[str, Any]:
    ext = Path(name or "").suffix.lower()
    claimed = next((k for k, v in SAFE_CLAIMS.items() if ext in v), "other")
    out: dict[str, Any] = {"claimed": claimed, "ext": ext, "label": "", "group": "", "mime": "", "score": 0.0,
                           "mismatch": False, "danger": False, "note": ""}
    m = _magika()
    if m is None or not data:
        return out
    try:
        r = m.identify_bytes(data[:2_000_000] if len(data) > 2_000_000 else data)
        o = r.output
        out.update(label=str(o.label), group=str(o.group), mime=str(o.mime_type), score=round(float(r.score), 3))
    except Exception as e:
        log.info("magika failed for %s: %s", name, e)
        return out
    label, group = out["label"], out["group"]
    risky = group in DANGER_GROUPS or label in DANGER_LABELS
    if claimed in ("document", "image", "media") and risky and out["score"] >= 0.6 and not (ext in TEXT_OK and group == "code"):
        out["danger"] = True
        out["note"] = f"naam '{ext}' file jaisa hai par andar program / script ({label}) hai"
    elif claimed != "other" and group not in ("", "unknown") and group != claimed and not (
            claimed == "document" and group in ("text", "code", "archive")) and not (claimed == "media" and group in ("audio", "video")):
        out["mismatch"] = True
        out["note"] = f"naam '{ext}' hai par andar {label} ({group}) hai"
    return out
