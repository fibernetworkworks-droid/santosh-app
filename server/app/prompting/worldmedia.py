"""World prompts' pictures and videos (the ones the authors made with their prompts on prompts.chat, CC0).

Her browser never loads the author's host: GET /api/prompting/world-media/<id>?size=thumb|full fetches the file ONCE
from the host recorded in the shelf (https, a fixed list of hosts, no redirects), checks the bytes really are a
picture / video / sound, and keeps a small copy under the data folder; every later view is served from that copy.
  thumb: a picture -> 640 px WebP; a video -> one frame at 1 s as a 640 px WebP (ffmpeg; none = 404, the page shows
         a plain video tile); a sound -> 404 (the page shows a sound tile)
  full:  a picture -> up to 1600 px WebP; a video / sound -> the file itself (video up to 40 MB, sound 10 MB)
Public (no sign-in): <img> / <video> cannot send her token, and the files are public domain. Only ids on the shelf
with a recorded file are served, never an address from the request, and nothing for a prompt Hoola's checks flagged.
A failed fetch is remembered for an hour so a dead link is not asked again on every view."""
from __future__ import annotations

import asyncio
import io
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from . import world as W

MAX_IMAGE, MAX_VIDEO, MAX_AUDIO = 15 << 20, 40 << 20, 10 << 20
THUMB_W, FULL_W = 640, 1600
_FAILED: dict[str, float] = {}
_LOCKS: dict[str, asyncio.Lock] = {}
FAIL_TTL = 3600


DIR: list[Path] = [Path("data") / "prompting" / "world_media"]      # tests point DIR[0] at a temp folder


def cache_dir() -> Path:
    d = DIR[0]
    d.mkdir(parents=True, exist_ok=True)
    return d


def _fetch(url: str, limit: int) -> bytes:
    """The file from its recorded host: https only, no redirects, size-capped while reading."""
    import httpx
    if not W.media_url(url):
        raise ValueError("not an allowed address")
    with httpx.Client(timeout=30, follow_redirects=False, headers={"User-Agent": "Hoola-Prompting/1.0"}) as c:
        with c.stream("GET", url) as r:
            if r.status_code != 200:
                raise ValueError(f"the host answered {r.status_code}")
            buf = bytearray()
            for chunk in r.iter_bytes():
                buf += chunk
                if len(buf) > limit:
                    raise ValueError("the file is too big")
    return bytes(buf)


FETCH: list[Any] = [_fetch]        # tests replace FETCH[0]


def sniff(data: bytes) -> str:
    """What the bytes really are: image / video / audio / ''."""
    h = data[:16]
    if h[:3] == b"\xff\xd8\xff" or h[:8] == b"\x89PNG\r\n\x1a\n" or h[:6] in (b"GIF87a", b"GIF89a") \
            or (h[:4] == b"RIFF" and data[8:12] == b"WEBP"):
        return "image"
    if data[4:8] == b"ftyp" or h[:4] == b"\x1aE\xdf\xa3":
        return "video"
    if (h[:4] == b"RIFF" and data[8:12] == b"WAVE") or h[:3] == b"ID3" or h[:2] in (b"\xff\xfb", b"\xff\xf3") \
            or h[:4] == b"OggS":
        return "audio"
    return ""


def _webp(data: bytes, width: int) -> bytes:
    from PIL import Image
    Image.MAX_IMAGE_PIXELS = 60_000_000
    with Image.open(io.BytesIO(data)) as im:
        im.draft("RGB", (width * 2, width * 4))
        im = im.convert("RGB")
        if im.width > width:
            im = im.resize((width, max(1, round(im.height * width / im.width))), Image.LANCZOS)
        out = io.BytesIO()
        im.save(out, "WEBP", quality=80, method=4)
        return out.getvalue()


def _poster(video: Path) -> bytes:
    ff = shutil.which("ffmpeg")
    if not ff:
        raise ValueError("no ffmpeg on this server")
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "p.png"
        for at in ("1", "0"):
            subprocess.run([ff, "-loglevel", "error", "-y", "-ss", at, "-i", str(video), "-frames:v", "1", str(out)],
                           timeout=60, check=False, stdin=subprocess.DEVNULL)
            if out.exists() and out.stat().st_size:
                return _webp(out.read_bytes(), THUMB_W)
    raise ValueError("no frame in the video")


def _entry(wid: str) -> dict[str, Any]:
    e = W._load()["by_id"].get(str(wid or "").removeprefix(W.PREFIX)) if W.on() else None
    if not e or not e.get("media") or any(n in W.SAFETY for n in e.get("notes") or ()):
        raise KeyError(wid)
    return e


def make(wid: str, size: str) -> Path:
    """The cached copy for this prompt and size, made the first time it is asked for."""
    e = _entry(wid)
    kind = W.media_type(e["media"])
    d = cache_dir()
    key = e["id"]
    if size == "thumb" and kind == "audio":
        raise KeyError(wid)
    path = d / (f"{key}-t.webp" if size == "thumb" else f"{key}-f.webp" if kind == "image" else f"{key}.{'mp4' if kind == 'video' else 'bin'}")
    if path.exists() and path.stat().st_size:
        return path
    if _FAILED.get(f"{key}:{size}", 0) > time.time():
        raise ValueError("this file could not be fetched a short while ago")
    try:
        if kind == "image":
            raw = FETCH[0](e["media"], MAX_IMAGE)
            if sniff(raw) != "image":
                raise ValueError("the file is not a picture")
            data = _webp(raw, THUMB_W if size == "thumb" else FULL_W)
        else:
            src = d / f"{key}.{'mp4' if kind == 'video' else 'bin'}"
            if not (src.exists() and src.stat().st_size):
                raw = FETCH[0](e["media"], MAX_VIDEO if kind == "video" else MAX_AUDIO)
                if sniff(raw) != kind:
                    raise ValueError(f"the file is not a {kind}")
                tmp = src.with_suffix(".part")
                tmp.write_bytes(raw)
                os.replace(tmp, src)
            if size == "full":
                return src
            data = _poster(src)
        tmp = path.with_suffix(".part")
        tmp.write_bytes(data)
        os.replace(tmp, path)
        return path
    except ValueError:
        _FAILED[f"{key}:{size}"] = time.time() + FAIL_TTL
        raise
    except Exception as ex:        # noqa: BLE001 - a broken file or a network fault: remembered, said as not found
        _FAILED[f"{key}:{size}"] = time.time() + FAIL_TTL
        raise ValueError(str(ex)[:120]) from None


_TYPES = {".webp": "image/webp", ".mp4": "video/mp4"}


def make_router() -> APIRouter:
    r = APIRouter(prefix="/api/prompting")

    @r.get("/world-media/{wid}")
    async def world_media(wid: str, size: str = "thumb"):
        size = "full" if size == "full" else "thumb"
        lock = _LOCKS.setdefault(f"{wid}:{size}", asyncio.Lock())
        async with lock:
            try:
                path = await asyncio.to_thread(make, wid, size)
            except (KeyError, ValueError):
                raise HTTPException(404, "No picture for this prompt.") from None
        media = _TYPES.get(path.suffix, "")
        if not media:
            e = _entry(wid)
            raw = path.read_bytes()[:16]
            media = "audio/wav" if raw[:4] == b"RIFF" else "audio/ogg" if raw[:4] == b"OggS" else "audio/mpeg"
            if W.media_type(e["media"]) == "video":
                media = "video/mp4"
        return FileResponse(path, media_type=media, headers={"Cache-Control": "public, max-age=604800",
                                                              "X-Content-Type-Options": "nosniff"})

    return r
