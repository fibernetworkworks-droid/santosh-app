"""v0.999.324 THE PREVIEW'S CONSOLE AND NETWORK CALLS (from the Dyad read): the app's console lines and its network
calls in the Studio preview are kept so Hoola can read them (app_engine action=read_logs), not only the errors.

The preview helper (preview.js) sends them to the Studio, the Studio forwards them here. Kept per app in
`<app folder>/_logs.json`: the newest 1,000 lines / about 1 MB, each masked (card / ID / bank numbers) before it is kept,
network calls as method + path + query names + status + time only (never a body, a header or a query value).
Only from the Studio's own preview (her signed-in console); a live app sends nothing here.
"""
from __future__ import annotations

import json
import threading
import time
from typing import Any

MAX_ROWS = 1000
MAX_BYTES = 1_000_000
MAX_PER_CALL = 100
_IO = threading.Lock()


def _file(r):
    from . import service as S
    return S.pdir(r.tenant_id, r.id) / "_logs.json"


def _read(r) -> list[dict[str, Any]]:
    try:
        rows = json.loads(_file(r).read_text())
        return rows if isinstance(rows, list) else []
    except (OSError, ValueError):
        return []


def record(r, items: list[Any], version: int = 0) -> dict[str, Any]:
    from ..pii import mask_sensitive
    v = int(version or r.version or 0)
    new = []
    for it in (items or [])[:MAX_PER_CALL]:
        if not isinstance(it, dict):
            continue
        t = str(it.get("t") or "")
        if t == "log":
            level = str(it.get("l") or "log")
            level = level if level in ("log", "info", "warn", "error", "debug") else "log"
            text = mask_sensitive(str(it.get("a") or ""))[:65536]
            if text.strip():
                new.append({"kind": "console", "level": level, "text": text, "page": str(it.get("p") or "/")[:140], "v": v,
                            "at": time.time()})
        elif t == "net":
            new.append({"kind": "network", "method": str(it.get("m") or "GET")[:8], "url": mask_sensitive(str(it.get("u") or ""))[:400],
                        "status": int(it.get("s") or 0), "ms": max(0, int(it.get("ms") or 0)),
                        "error": mask_sensitive(str(it.get("e") or ""))[:200], "v": v, "at": time.time()})
    if not new:
        return {"kept": 0}
    with _IO:
        rows = _read(r) + new
        rows = rows[-MAX_ROWS:]
        blob = json.dumps(rows)
        while len(blob) > MAX_BYTES and len(rows) > 10:
            rows = rows[len(rows) // 10:]
            blob = json.dumps(rows)
        f = _file(r)
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(blob)
    return {"kept": len(new)}


def read(r, kind: str = "all", limit: int = 50, level: str = "", version: int | None = None) -> dict[str, Any]:
    """The newest lines (oldest first in the answer). Default 50, at most 200; this version's lines unless version=0."""
    kind = kind if kind in ("console", "network", "all") else "all"
    limit = max(1, min(int(limit or 50), 200))
    v = int(r.version or 0) if version is None else int(version)
    rows = [x for x in _read(r) if (kind == "all" or x.get("kind") == kind) and (not v or int(x.get("v") or 0) >= v)]
    if level:
        lv = {"error": {"error"}, "warn": {"warn", "error"}}.get(level, {level})

        def keep(x: dict[str, Any]) -> bool:
            if x.get("kind") == "network":           # error / warn also bring the calls that failed
                return level in ("error", "warn") and (int(x.get("status") or 0) >= 400 or bool(x.get("error")))
            return x.get("level") in lv
        rows = [x for x in rows if keep(x)]
    rows = rows[-limit:]
    failed = [x for x in rows if x.get("kind") == "network" and (x.get("status", 0) >= 400 or x.get("error"))]
    say = (f"{len(rows)} line(s) from the preview of version {v}" if v else f"{len(rows)} line(s) from the preview") + \
          (f"; {len(failed)} network call(s) failed" if failed else "")
    if not rows:
        say = ("Nothing logged yet" + (f" on version {v}" if v else "") +
               ": the preview sends its console and network calls while it is open in the Studio.")
    return {"lines": rows, "say": say}
