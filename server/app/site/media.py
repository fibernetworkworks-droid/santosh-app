"""v0.338 EDIT MEIN SAB JODO (owner: "IN EDIT MODE ADD ALL ATTACHMENT FUNCTIONS IMAGE, VIDEO, FILES ETC").

Her own files on her website, by her own hand in Edit mode (no AI): a VIDEO (mp4 / webm) that plays on the page, an AUDIO
clip (mp3 / m4a / ogg / wav), or a FILE visitors download (PDF, Word, Excel, PowerPoint, text / CSV) - next to the
photos the site already had. A file is accepted only when its first bytes match its kind (a renamed .exe is refused),
within size limits; it is kept in the site's source folder (src/media) with a small manifest, and copied into a built
site only when a page uses it. Sections never carry a path: the markup says `data-hoola-media="NAME"` (video / audio)
or `data-hoola-file="NAME"` (download link) and the builder writes the address for each page's depth, like photos.
"""
from __future__ import annotations

import html as _html
import json
import re
import shutil
from pathlib import Path
from typing import Any

# kind -> (extensions, max bytes)
KINDS: dict[str, tuple[tuple[str, ...], int]] = {
    "video": (("mp4", "webm", "m4v"), 60 * 1024 * 1024),
    "audio": (("mp3", "m4a", "ogg", "oga", "wav"), 20 * 1024 * 1024),
    "file": (("pdf", "docx", "xlsx", "pptx", "txt", "csv"), 20 * 1024 * 1024),
}
SITE_LIMIT = 400 * 1024 * 1024
MIME = {"mp4": "video/mp4", "m4v": "video/mp4", "webm": "video/webm", "mp3": "audio/mpeg", "m4a": "audio/mp4",
        "ogg": "audio/ogg", "oga": "audio/ogg", "wav": "audio/wav", "pdf": "application/pdf",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "txt": "text/plain", "csv": "text/csv"}
LABEL = {"pdf": "PDF", "docx": "Word", "xlsx": "Excel", "pptx": "PowerPoint", "txt": "Text", "csv": "CSV"}


class MediaError(Exception):
    pass


def _ext(filename: str) -> str:
    return (filename.rsplit(".", 1)[-1] if "." in (filename or "") else "").lower()[:6]


def sniff(data: bytes, ext: str) -> bool:
    """Do the first bytes really belong to this kind of file?"""
    h = data[:16]
    if ext in ("mp4", "m4v", "m4a"):
        return len(data) > 12 and data[4:8] == b"ftyp"
    if ext == "webm":
        return h.startswith(b"\x1a\x45\xdf\xa3")
    if ext == "mp3":
        return h.startswith(b"ID3") or (len(h) > 1 and h[0] == 0xFF and (h[1] & 0xE0) == 0xE0)
    if ext in ("ogg", "oga"):
        return h.startswith(b"OggS")
    if ext == "wav":
        return h.startswith(b"RIFF") and data[8:12] == b"WAVE"
    if ext == "pdf":
        return h.startswith(b"%PDF-")
    if ext in ("docx", "xlsx", "pptx"):
        if not h.startswith(b"PK\x03\x04"):
            return False
        import io
        import zipfile
        want = {"docx": "word/", "xlsx": "xl/", "pptx": "ppt/"}[ext]
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as z:
                return any(n.startswith(want) for n in z.namelist()[:400])
        except zipfile.BadZipFile:
            return False
    if ext in ("txt", "csv"):
        try:
            data[:200000].decode("utf-8")
        except UnicodeDecodeError:
            return False
        return b"\x00" not in data[:200000]
    return False


def kind_of(ext: str) -> str:
    return next((k for k, (exts, _) in KINDS.items() if ext in exts), "")


def size_text(n: int) -> str:
    return f"{n / 1024 / 1024:.1f} MB" if n >= 1024 * 1024 else f"{max(1, round(n / 1024))} KB"


def _dir(src: Path) -> Path:
    d = src / "media"
    d.mkdir(parents=True, exist_ok=True)
    return d


def manifest(src: Path) -> list[dict[str, Any]]:
    f = src / "media" / "_media.json"
    try:
        return json.loads(f.read_text()) if f.exists() else []
    except Exception:
        return []


def _save_manifest(src: Path, items: list[dict[str, Any]]) -> None:
    f = _dir(src) / "_media.json"
    tmp = f.with_suffix(".tmp")
    tmp.write_text(json.dumps(items, ensure_ascii=False))
    tmp.replace(f)


def add(src: Path, data: bytes, filename: str, about: str = "") -> dict[str, Any]:
    """Keep one of her files for the site. Raises MediaError in plain words."""
    ext = _ext(filename)
    kind = kind_of(ext)
    if not kind:
        raise MediaError("Yeh file nahi lagti: video (MP4 / WebM), audio (MP3 / M4A / OGG / WAV) ya file (PDF, Word, "
                         "Excel, PowerPoint, TXT, CSV) bhejiye. Photo ke liye photo wala button.")
    if not data:
        raise MediaError("File khaali hai.")
    limit = KINDS[kind][1]
    if len(data) > limit:
        raise MediaError(f"Yeh {kind} {size_text(len(data))} ki hai; {size_text(limit)} tak chalegi.")
    if not sniff(data, ext):
        raise MediaError(f"Yeh file sach mein .{ext} nahi lag rahi (andar kuch aur hai). Asli file bhejiye.")
    items = manifest(src)
    if sum(int(i.get("bytes") or 0) for i in items) + len(data) > SITE_LIMIT:
        raise MediaError("Is website ki files ki jagah bhar gayi (400 MB); purani hataiye ya video chhota kijiye.")
    base = re.sub(r"[^a-z0-9]+", "-", (about or filename.rsplit(".", 1)[0] or kind).lower()).strip("-")[:30] or kind
    name, n = base, 2
    while any(i["name"] == name for i in items):
        name, n = f"{base}-{n}", n + 1
    (_dir(src) / f"{name}.{ext}").write_bytes(data)
    item = {"name": name, "kind": kind, "ext": ext, "bytes": len(data), "about": re.sub(r"\s+", " ", about or "")[:120],
            "file": re.sub(r"[^\w .()-]+", "", filename)[:80]}
    items.append(item)
    _save_manifest(src, items)
    return item


def find(src: Path, name: str) -> dict[str, Any] | None:
    return next((i for i in manifest(src) if i["name"] == name), None)


# ---------------------------------------------------------------- what Edit mode inserts (built here, never from her text as html)
def block(item: dict[str, Any] | None, kind: str, caption: str = "", url: str = "", photo: str = "") -> str:
    """The markup for one thing she adds. Every word of hers is escaped; addresses are written later by the builder."""
    cap = _html.escape(re.sub(r"\s+", " ", caption or "").strip()[:160])
    fig = f"<figcaption>{cap}</figcaption>" if cap else ""
    if kind == "photo":
        return (f'<figure class="hs-emedia"><img data-hoola-img="{_html.escape(photo)}" alt="{cap or "Photo"}" '
                f'loading="lazy">{fig}</figure>')
    if kind == "youtube":
        return f'<div class="hs-emedia" data-hoola-video="{_html.escape(url)}" data-title="{cap or "Video"}"></div>'
    if not item:
        raise MediaError("Yeh file nahi mili; dobara upload kijiye.")
    nm = _html.escape(item["name"])
    if kind == "video":
        return (f'<figure class="hs-emedia"><video data-hoola-media="{nm}" controls preload="metadata" playsinline '
                f'aria-label="{cap or "Video"}"></video>{fig}</figure>')
    if kind == "audio":
        return (f'<figure class="hs-emedia"><audio data-hoola-media="{nm}" controls preload="none" '
                f'aria-label="{cap or "Audio"}"></audio>{fig}</figure>')
    label = cap or _html.escape(item.get("about") or item.get("file") or item["name"])
    meta = f'{LABEL.get(item["ext"], item["ext"].upper())}, {size_text(int(item["bytes"]))}'
    return (f'<p class="hs-efile"><a class="btn btn-ghost" data-hoola-file="{nm}" download>'
            f'<i data-icon="download"></i> {label} ({meta})</a></p>')


def link_or_copy(src: str, dst: str) -> str:
    """A hard link when the disk allows (her files are never changed in place, so every build / version can share one
    copy of a 60 MB video); a real copy otherwise."""
    import os
    try:
        os.link(src, dst)
    except OSError:
        shutil.copy2(src, dst)
    return dst


# ---------------------------------------------------------------- the builder: placeholders -> addresses + files copied
MEDIA_TAG = re.compile(r'<(video|audio)\b([^>]*)\sdata-hoola-media="([\w-]+)"([^>]*)>', re.I)
FILE_TAG = re.compile(r'<a\b([^>]*)\sdata-hoola-file="([\w-]+)"([^>]*)>', re.I)


def expand(html_text: str, src: Path, out: Path, rel: str) -> tuple[str, list[str]]:
    """video / audio get a src, download links an href, for a page at this depth; the files used are copied into the
    site (assets/media, assets/files). Unknown names are reported and the element left without an address."""
    if "data-hoola-media" not in html_text and "data-hoola-file" not in html_text:
        return html_text, []
    missing: list[str] = []
    items = {i["name"]: i for i in manifest(src)}

    def copy(item: dict[str, Any], sub: str) -> str:
        fn = f'{item["name"]}.{item["ext"]}'
        dest = out / "assets" / sub / fn
        if not dest.exists():
            dest.parent.mkdir(parents=True, exist_ok=True)
            link_or_copy(str(src / "media" / fn), str(dest))
        return f"{rel}assets/{sub}/{fn}"

    def media(m: re.Match) -> str:
        it = items.get(m.group(3))
        if not it or it["kind"] not in ("video", "audio"):
            missing.append(m.group(3))
            return m.group(0)
        return f'<{m.group(1)}{m.group(2)} data-hoola-media="{m.group(3)}" src="{copy(it, "media")}"{m.group(4)}>'

    def files(m: re.Match) -> str:
        it = items.get(m.group(2))
        if not it or it["kind"] != "file":
            missing.append(m.group(2))
            return m.group(0)
        rest = re.sub(r'\shref="[^"]*"', "", m.group(1) + m.group(3))
        return f'<a{rest} data-hoola-file="{m.group(2)}" href="{copy(it, "files")}">'
    return FILE_TAG.sub(files, MEDIA_TAG.sub(media, html_text)), missing
