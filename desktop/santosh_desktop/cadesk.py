"""CA document desk on the CA's own PC (owner's freeze exception, 20 Nov 2026: "Yes, change desktop" for this one job).

Hoola keeps every client's documents arranged under ONE folder the CA uses (default Documents\\CA Clients):

    CA Clients\\Sharma Traders\\FY 2026-27\\10 October\\Purchase bills\\2026-10-06 Patel Steel PS-2611.pdf

`save_into` writes a file there (never over another file - a second copy gets "(2)"), and `drop_scan` lists files the CA
dropped into a client's "_Drop here" folder so the server can file them; a collected file is MOVED to
"_Drop here\\_Collected" (never deleted). Nothing outside the CA folder is written, read or moved.
"""
from __future__ import annotations

import os
import re
from pathlib import Path

from .safety import Denied, inside, unique

DROP = "_Drop here"
DONE = "_Collected"
_BAD = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_RESERVED = {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}


def default_root() -> Path:
    docs = Path.home() / "Documents"
    return (docs if docs.exists() else Path.home()) / "CA Clients"


def _system_dirs() -> list[Path]:
    out = []
    for v in ("SystemRoot", "WINDIR", "ProgramFiles", "ProgramFiles(x86)", "ProgramData", "APPDATA", "LOCALAPPDATA"):
        if os.environ.get(v):
            out.append(Path(os.path.realpath(os.environ[v])))
    for p in ("/etc", "/usr", "/bin", "/sbin", "/var", "/System", "/Library", "/Applications"):
        out.append(Path(p))
    return out


def root_of(path: str = "") -> Path:
    """The CA folder: the one she picked if it is a safe place for documents, else Documents\\CA Clients."""
    if not path:
        return default_root()
    p = Path(os.path.realpath(os.path.expanduser(str(path))))
    if not p.is_absolute() or p == Path(p.anchor):
        raise Denied("Pick a folder for CA Clients, not a whole drive.")
    for s in _system_dirs():
        if p == s or inside(p, s):
            raise Denied("That is a system folder. Pick a folder like D:\\CA Clients.")
    return p


def part(v: str) -> str:
    s = _BAD.sub(" ", str(v or "")).strip(" .")
    s = re.sub(r"\s+", " ", s)[:80].strip(" .")
    if s.upper() in _RESERVED:
        s = "_" + s
    if not s or s in (".", ".."):
        raise Denied("A folder name is empty.")
    return s


def target(root: str, parts: list[str], name: str) -> Path:
    """Where a file goes: root / each safe part / a new name that never replaces another file."""
    base = root_of(root)
    if not isinstance(parts, list) or not 1 <= len(parts) <= 6:
        raise Denied("The folder path is not right.")
    d = base
    for x in parts:
        d = d / part(x)
    real = Path(os.path.realpath(d)) if d.exists() else d
    if not inside(real, Path(os.path.realpath(base)) if base.exists() else base):
        raise Denied("That folder is outside CA Clients.")
    return unique(d, part(name) if name else "file")


def drop_scan(root: str, folders: list[str], limit: int = 20) -> list[tuple[str, Path]]:
    """[(client folder, file)] waiting in each client's '_Drop here' folder (never deeper, never a link)."""
    base = root_of(root)
    out: list[tuple[str, Path]] = []
    for f in folders or []:
        try:
            d = base / part(f) / DROP
        except Denied:
            continue
        if not d.is_dir():
            try:
                d.mkdir(parents=True, exist_ok=True)       # the drop folder is made for every client
            except OSError:
                pass
            continue
        for p in sorted(d.iterdir()):
            if p.is_file() and not p.is_symlink() and not p.name.startswith((".", "~$")) and not p.name.endswith(".part"):
                out.append((f, p))
                if len(out) >= limit:
                    return out
    return out


def collected(p: Path) -> Path:
    """Move a sent file to _Drop here\\_Collected (kept, never deleted)."""
    dest = unique(p.parent / DONE, p.name)
    p.replace(dest)
    return dest
