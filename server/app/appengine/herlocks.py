"""v0.999.322 HER LOCKED FILES (from the bolt.diy read): she locks a file or a whole folder of an App Engine app in the
Studio's Code tab, and Hoola's app_engine tool can no longer write, edit, rename, move into or delete it.

Her own taps (a click-edit in the preview, a GitHub pull, accepting a branch, the Code tab) are hers and stay open; the
lock binds Hoola. Hoola's OWN locks (package.json, vite.config.ts ... in rules.LOCKED) are a different thing and never
show as hers. Kept per app in `<app folder>/_locks.json`; a branch starts with a copy of the app's locks.
"""
from __future__ import annotations

import json
import shutil
import threading
from typing import Any

MAX_LOCKS = 200
_IO = threading.Lock()


class LockError(Exception):
    pass


def _file(r):
    from . import service as S
    return S.pdir(r.tenant_id, r.id) / "_locks.json"


def listing(r) -> list[dict[str, Any]]:
    try:
        rows = json.loads(_file(r).read_text())
    except (OSError, ValueError):
        return []
    return [x for x in rows if isinstance(x, dict) and x.get("path")] if isinstance(rows, list) else []


def _norm(path: str) -> tuple[str, bool]:
    from . import rules as RL
    raw = str(path or "").strip()
    folder = raw.endswith("/")
    try:
        rel = RL.norm(raw.rstrip("/"))
    except RL.RuleError as e:
        raise LockError(str(e))
    if not rel:
        raise LockError("Which file or folder?")
    return rel, folder


def locked_by(r, rel: str) -> str:
    """The lock that covers this path ('' = not locked by her): the file itself or a folder above it."""
    for x in listing(r):
        p = str(x["path"])
        if x.get("folder"):
            if rel == p or rel.startswith(p + "/"):
                return p + "/"
        elif rel == p:
            return p
    return ""


def set_lock(r, path: str, on: bool) -> dict[str, Any]:
    from . import rules as RL
    from . import service as S
    from ..db import now
    rel, folder = _norm(path)
    if not folder:
        p = S._path_in(r, rel)
        if p.is_dir():
            folder = True
        elif on and not p.is_file():
            raise LockError(f"{rel} does not exist in this app.")
    if on and not folder and rel in RL.LOCKED:
        raise LockError(f"{rel} is one of Hoola's own setup files; Hoola never changes it anyway.")
    with _IO:
        rows = [x for x in listing(r) if not (x["path"] == rel and bool(x.get("folder")) == folder)]
        if on:
            if len(rows) >= MAX_LOCKS:
                raise LockError(f"At most {MAX_LOCKS} locks per app.")
            rows.append({"path": rel, "folder": folder, "at": now().isoformat()})
        f = _file(r)
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps(sorted(rows, key=lambda x: x["path"])))
    shown = rel + ("/" if folder else "")
    return {"locks": listing(r), "path": shown, "locked": on,
            "say": (f"Locked {shown}: Hoola cannot change it until you unlock it." if on else f"Unlocked {shown}.")}


def guard(r, *rels: str) -> None:
    """Raises LockError naming her lock when any of these paths is covered."""
    for rel in rels:
        if not rel:
            continue
        lk = locked_by(r, rel)
        if lk:
            raise LockError(f"She locked {lk} in the Studio, so Hoola does not change {rel}. Nothing was written. Work "
                            f"around it, or tell her what you would change there and ask her to unlock {lk} (Code tab).")


def copy_to(src_app, dst_app) -> None:
    """A new branch starts with the app's locks."""
    try:
        f = _file(src_app)
        if f.is_file():
            d = _file(dst_app)
            d.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, d)
    except OSError:
        pass
