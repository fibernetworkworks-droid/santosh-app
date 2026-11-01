"""v0.370 GAME DESK: install Godot 4 headless + ONLY its Web export templates (no 1.25 GB download).

    python3 setup_godot.py [--version 4.7.2] [--dir ~/apps/godot]

The official export templates come as one ~1.25 GB zip for every platform. This reads that zip over HTTP range requests
(the zip's own index sits at its end), and pulls out just templates/web_*.zip + version.txt (~40 MB) into Godot's
template folder for the user running it: ~/.local/share/godot/export_templates/<version>.stable/.
Official files only (github.com/godotengine/godot/releases); stdlib only; checks the binary runs at the end."""
from __future__ import annotations

import argparse
import io
import os
import shutil
import stat
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path

BASE = "https://github.com/godotengine/godot/releases/download/{v}-stable/"


class HttpFile(io.RawIOBase):
    """A seekable read-only file over HTTP range requests (enough for zipfile)."""

    def __init__(self, url: str):
        self.url, self.pos = url, 0
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=60) as r:
            self.url = r.geturl()
            self.size = int(r.headers["Content-Length"])

    def seekable(self) -> bool:
        return True

    def readable(self) -> bool:
        return True

    def tell(self) -> int:
        return self.pos

    def seek(self, off: int, whence: int = 0) -> int:
        self.pos = off if whence == 0 else self.pos + off if whence == 1 else self.size + off
        return self.pos

    def read(self, n: int = -1) -> bytes:
        if n is None or n < 0:
            n = self.size - self.pos
        if n == 0 or self.pos >= self.size:
            return b""
        end = min(self.size, self.pos + n) - 1
        for attempt in range(5):
            try:
                req = urllib.request.Request(self.url, headers={"Range": f"bytes={self.pos}-{end}"})
                with urllib.request.urlopen(req, timeout=120) as r:
                    data = r.read()
                break
            except Exception:
                if attempt == 4:
                    raise
        self.pos += len(data)
        return data


def fetch(url: str, dest: Path) -> None:
    with urllib.request.urlopen(url, timeout=300) as r, open(dest, "wb") as f:
        shutil.copyfileobj(r, f)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", default="4.7.2")
    ap.add_argument("--dir", default=os.environ.get("GODOT_DIR", str(Path.home() / "apps" / "godot")))
    a = ap.parse_args()
    v, home = a.version, Path(a.dir)
    home.mkdir(parents=True, exist_ok=True)
    binp = home / f"Godot_v{v}-stable_linux.x86_64"
    if not binp.exists():
        z = home / "godot.zip"
        print("downloading Godot", v)
        fetch(BASE.format(v=v) + f"Godot_v{v}-stable_linux.x86_64.zip", z)
        with zipfile.ZipFile(z) as zz:
            zz.extract(binp.name, home)
        z.unlink()
        binp.chmod(binp.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    link = home / "godot"
    if link.exists() or link.is_symlink():
        link.unlink()
    link.symlink_to(binp.name)
    tdir = Path.home() / ".local/share/godot/export_templates" / f"{v}.stable"
    tdir.mkdir(parents=True, exist_ok=True)
    print("reading the templates index (range requests)")
    with zipfile.ZipFile(HttpFile(BASE.format(v=v) + f"Godot_v{v}-stable_export_templates.tpz")) as tz:
        names = [n for n in tz.namelist() if n in ("templates/version.txt", "templates/web_nothreads_release.zip",
                                                   "templates/web_release.zip")]
        for n in names:
            print("  ", n)
            with tz.open(n) as src, open(tdir / Path(n).name, "wb") as dst:
                shutil.copyfileobj(src, dst)
    out = subprocess.run([str(link), "--headless", "--version"], capture_output=True, text=True, timeout=60)
    print("godot:", out.stdout.strip() or out.stderr.strip()[-200:])
    print("templates:", tdir, sorted(p.name for p in tdir.iterdir()))
    print(f"Hoola finds it at {link} (~/apps/godot/godot is looked up by itself; else set GODOT_BIN in .env)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
