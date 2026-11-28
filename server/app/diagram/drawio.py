"""The draw.io editor (jgraph/drawio, Apache-2.0) for engine C, fetched at setup - never kept in git.

The release next-ai-draw-io pins (vendor/drawio-ai/src/drawio-version.json: version + the SHA-256 GitHub lists for its
draw.war) is downloaded once, refused unless its SHA-256 matches, and only the files the editor needs are unpacked (the
list next-ai-draw-io keeps in vendor/drawio-ai/drawio-files.txt; `*` = inside one folder, `**` = across folders) into
data/diagram/drawio/<version>/. The editor is then served from Hoola's own origin, offline: nothing is loaded from
diagrams.net. Same steps as next-ai-draw-io's scripts/fetch-drawio.mjs, written in Python here."""
from __future__ import annotations

import hashlib
import io
import os
import re
import shutil
import urllib.request
import zipfile
from pathlib import Path
from typing import Any

from . import vendor as V

MAX_WAR = 400 * 1024 * 1024        # draw.war is ~100 MB; anything far larger is not the release


def base_dir() -> Path:
    try:
        from ..config import get_settings
        d = str(getattr(get_settings(), "diagram_drawio_dir", "") or "")
    except Exception:  # noqa: BLE001
        d = ""
    return Path(d) if d else Path("data") / "diagram" / "drawio"


def editor_dir() -> Path:
    return base_dir() / V.drawio_pin()["version"]


def ready() -> bool:
    d = editor_dir()
    return (d / "index.html").is_file() and (d / "js" / "app.min.js").is_file() and (d / ".hoola-ok").is_file()


def patterns() -> list[str]:
    out = []
    for line in (V.DRAWIO_AI / "drawio-files.txt").read_text("utf-8").splitlines():
        s = line.strip()
        if s and not s.startswith("#"):
            out.append(s)
    return out


def _rx(pattern: str) -> re.Pattern:
    out, i = "", 0
    while i < len(pattern):
        if pattern.startswith("**", i):
            out += ".*"
            i += 2
        elif pattern[i] == "*":
            out += "[^/]*"
            i += 1
        else:
            out += re.escape(pattern[i])
            i += 1
    return re.compile("^" + out + "$")


def wanted(name: str, rxs: list[re.Pattern] | None = None) -> bool:
    rxs = rxs if rxs is not None else [_rx(p) for p in patterns()]
    return any(r.match(name) for r in rxs)


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _download(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "hoola-diagram-setup"})
    with urllib.request.urlopen(req, timeout=300) as r:   # noqa: S310 - the pinned GitHub release URL only
        buf = io.BytesIO()
        while True:
            chunk = r.read(1 << 20)
            if not chunk:
                break
            buf.write(chunk)
            if buf.tell() > MAX_WAR:
                raise RuntimeError("the download is far larger than the draw.io release - stopped")
        return buf.getvalue()


def setup(war_path: str = "", force: bool = False) -> dict[str, Any]:
    """Fetch (or take `war_path`), check the SHA-256, unpack the needed files. {ok, version, files, said}."""
    pin = V.drawio_pin()
    if ready() and not force:
        return {"ok": True, "version": pin["version"], "files": None, "said": f"draw.io {pin['version']} is already set up."}
    url = pin["downloadUrl"]
    if not url.startswith("https://github.com/jgraph/drawio/releases/download/"):
        return {"ok": False, "said": "The pinned draw.io address is not jgraph's GitHub release - refused."}
    cache = base_dir() / f"draw-{pin['version']}.war"
    data = b""
    src = war_path or os.environ.get("DRAWIO_WAR", "")
    if src:
        data = Path(src).read_bytes()
    elif cache.is_file():
        data = cache.read_bytes()
        if _sha(data) != pin["sha256"]:
            data = b""
    if not data:
        data = _download(url)
    got = _sha(data)
    if got != pin["sha256"]:
        return {"ok": False, "said": f"The download is not draw.io {pin['version']} (SHA-256 {got[:16]}...) - nothing unpacked."}
    base_dir().mkdir(parents=True, exist_ok=True)
    if not cache.is_file():
        tmp = cache.with_suffix(".tmp")
        tmp.write_bytes(data)
        tmp.replace(cache)
    out = editor_dir()
    tmp_dir = out.with_name(out.name + ".tmp")
    shutil.rmtree(tmp_dir, ignore_errors=True)
    rxs = [_rx(p) for p in patterns()]
    n = 0
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        for info in z.infolist():
            name = info.filename
            if info.is_dir() or name.startswith("/") or ".." in name.split("/"):
                continue
            if not wanted(name, rxs):
                continue
            dest = tmp_dir / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(z.read(info))
            n += 1
        lic = ""
        for cand in ("WEB-INF/LICENSE", "LICENSE"):
            if cand in z.namelist():
                lic = z.read(cand).decode("utf-8", "replace")
                break
    (tmp_dir / "LICENSE").write_text(
        f"The files in this directory are an unmodified subset of draw.io {pin['version']}\n"
        "(https://github.com/jgraph/drawio), Copyright (c) JGraph Ltd, redistributed under the Apache License,\n"
        "Version 2.0. The icon sets under img/lib and the stencils have additional terms: img/LICENSE,\n"
        "shapes/LICENSE and stencils/LICENSE.\n\n" + lic, "utf-8")
    (tmp_dir / ".hoola-ok").write_text(f"{pin['version']} {pin['sha256']} {n}\n", "utf-8")
    shutil.rmtree(out, ignore_errors=True)
    tmp_dir.replace(out)
    return {"ok": True, "version": pin["version"], "files": n,
            "said": f"draw.io {pin['version']} set up: {n} files, SHA-256 checked."}
