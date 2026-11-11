"""Uploaded images of HOOLA DESIGN: checked by CONTENT (never by the name or the type the browser claims) and
kept on disk under `data/design/<tenant>/assets/<sha256>`. Thumbnails sit beside them.

An SVG is only ever used as an image, but it is still a program a browser would run if it were opened as a
page - so one that carries a script, an event handler or embedded HTML is refused at the door.
"""
from __future__ import annotations

import hashlib
import io
import os
import re
import struct
from pathlib import Path
from xml.etree import ElementTree

from ..config import get_settings

ASSET_MAX = 10 * 1024 * 1024
THUMB_MAX = 300 * 1024
PIXELS_MAX = 64_000_000
_PNG = b"\x89PNG\r\n\x1a\n"
_SVG_BAD_TAGS = frozenset("script foreignobject iframe embed object handler listener set animate".split())
_SVG_BAD_TEXT = re.compile(r"<!entity|<\?xml-stylesheet|<script|javascript:", re.I)
_SHA = re.compile(r"^[0-9a-f]{64}$")


class BadImage(ValueError):
    """The bytes are not an image Hoola Design keeps; the message says why in plain words."""


def _raster_kind(head: bytes) -> str:
    if head.startswith(_PNG):
        return "image/png"
    if head.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if head[:6] in (b"GIF87a", b"GIF89a"):
        return "image/gif"
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "image/webp"
    return ""


def _check_raster(data: bytes, mime: str) -> tuple[int, int]:
    """Decode-check the picture: the right first bytes on a broken or made-up body are not an image."""
    try:
        from PIL import Image
    except ImportError:                                  # no Pillow on this server: the PNG header is still checked
        if mime == "image/png" and data[12:16] == b"IHDR" and len(data) > 33:
            return struct.unpack(">II", data[16:24])
        if mime == "image/png":
            raise BadImage("This PNG is damaged.") from None
        return 0, 0
    try:
        with Image.open(io.BytesIO(data)) as im:
            if Image.MIME.get(im.format or "") != mime:
                raise BadImage("The file is not the kind of image its first bytes claim.")
            w, h = im.size
            if w * h > PIXELS_MAX:
                raise BadImage("This image is too large (more than 64 megapixels).")
            im.verify()
    except BadImage:
        raise
    except Exception:                                    # noqa: BLE001 - whatever Pillow raises, it is not a usable image
        raise BadImage("This file is damaged or is not really an image.") from None
    return w, h


def _local(name: str) -> str:
    return name.rsplit("}", 1)[-1].lower()


def _check_svg(data: bytes) -> tuple[int, int]:
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise BadImage("This file is not a PNG, JPEG, WebP, GIF or SVG image.") from None
    if "<svg" not in text[:4096].lower():
        raise BadImage("This file is not a PNG, JPEG, WebP, GIF or SVG image.")
    if _SVG_BAD_TEXT.search(text):
        raise BadImage("This SVG carries a script or an outside reference, so it is not kept.")
    try:
        root = ElementTree.fromstring(text)
    except ElementTree.ParseError:
        raise BadImage("This SVG is not well formed.") from None
    if _local(root.tag) != "svg":
        raise BadImage("This file is not an SVG image.")
    for el in root.iter():
        if not isinstance(el.tag, str):
            continue
        if _local(el.tag) in _SVG_BAD_TAGS:
            raise BadImage("This SVG carries a script, an animation or embedded HTML, so it is not kept.")
        for key, value in el.attrib.items():
            if _local(key).startswith("on") or "javascript:" in "".join(value.split()).lower():
                raise BadImage("This SVG carries an event handler, so it is not kept.")

    def px(value: str | None) -> int:
        m = re.match(r"\s*([0-9.]+)\s*(px)?\s*$", value or "")
        return int(float(m.group(1))) if m else 0
    w, h = px(root.get("width")), px(root.get("height"))
    box = (root.get("viewBox") or "").replace(",", " ").split()
    if not (w and h) and len(box) == 4:
        try:
            w, h = int(float(box[2])), int(float(box[3]))
        except ValueError:
            w = h = 0
    return w, h


def sniff(data: bytes) -> tuple[str, int, int]:
    """(mime, width, height) of a real PNG / JPEG / WebP / GIF / safe SVG; BadImage for anything else."""
    if not data:
        raise BadImage("The upload is empty.")
    mime = _raster_kind(data[:16])
    if mime:
        return (mime, *_check_raster(data, mime))
    return ("image/svg+xml", *_check_svg(data))


def stored_mime(path: Path) -> str:
    """The type of a file already in the store (only the five checked kinds are ever written there)."""
    with open(path, "rb") as fh:
        return _raster_kind(fh.read(16)) or "image/svg+xml"


# ------------------------------------------------------------------------------------------------ disk
def _tenant_dir(tenant: str) -> Path:
    root = str(getattr(get_settings(), "design_dir", "") or "")
    safe = re.sub(r"[^A-Za-z0-9_-]+", "_", tenant or "")[:80] or "main"
    return (Path(root) if root else Path("data") / "design") / safe


def _write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    tmp.write_bytes(data)
    os.replace(tmp, path)                                # a reader never sees half a file


def asset_path(tenant: str, sha: str) -> Path | None:
    if not _SHA.match(sha or ""):
        return None
    path = _tenant_dir(tenant) / "assets" / sha
    return path if path.is_file() else None


def save_asset(tenant: str, data: bytes) -> dict:
    """Check and keep one image; the same bytes are stored once (the name is their SHA-256)."""
    mime, w, h = sniff(data)
    sha = hashlib.sha256(data).hexdigest()
    path = _tenant_dir(tenant) / "assets" / sha
    if not path.is_file():
        _write(path, data)
    return {"hash": sha, "mime": mime, "w": w, "h": h, "size": len(data)}


def thumb_path(tenant: str, file_id: str) -> Path:
    return _tenant_dir(tenant) / "thumbs" / (re.sub(r"[^A-Za-z0-9_-]+", "_", file_id)[:64] + ".png")


def save_thumb(tenant: str, file_id: str, data: bytes) -> None:
    if sniff(data)[0] != "image/png":
        raise BadImage("A thumbnail must be a PNG image.")
    _write(thumb_path(tenant, file_id), data)


def drop_thumb(tenant: str, file_id: str) -> None:
    thumb_path(tenant, file_id).unlink(missing_ok=True)
