"""Santosh only ever touches the folders the user shared, and writes only into the Santosh Inbox folder."""
from __future__ import annotations

import os
from pathlib import Path


class Denied(Exception):
    pass


def _real(p: str | Path) -> Path:
    return Path(os.path.realpath(os.path.expanduser(str(p))))


def roots(folders: list[str]) -> list[Path]:
    out = []
    for f in folders:
        r = _real(f)
        if r.is_dir():
            out.append(r)
    return out


def inside(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def allowed(path: str, folders: list[str], inbox: str = "") -> Path:
    """The real path if it is inside a shared folder (or the inbox); otherwise Denied. Symlinks are resolved first."""
    if not path:
        raise Denied("No file given")
    rs = roots(folders) + ([_real(inbox)] if inbox else [])
    p = _real(path)
    if not any(inside(p, r) for r in rs):
        # a bare name or a path relative to a shared folder
        for r in rs:
            cand = _real(r / path)
            if inside(cand, r) and cand.exists():
                return cand
        raise Denied("Yeh file un folders mein nahi hai jo aapne Santosh ke saath share kiye hain.")
    return p


def unique(dest_dir: Path, name: str) -> Path:
    dest_dir.mkdir(parents=True, exist_ok=True)
    base = Path(name).name or "file"
    stem, suf = Path(base).stem, Path(base).suffix
    p = dest_dir / base
    i = 2
    while p.exists():
        p = dest_dir / f"{stem} ({i}){suf}"
        i += 1
    return p
