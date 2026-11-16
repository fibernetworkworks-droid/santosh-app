"""P0 store: one dated tables file per day + `current.json` (what the Box reads) + `changes.jsonl` (plan 8.2.6)."""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

from ..config import get_settings
from .kinds import LEVELS


def root() -> Path:
    d = str(getattr(get_settings(), "pipeline_dir", "") or "")
    return Path(d) if d else Path("data") / "pipeline"


def _write(p: Path, data: Any) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1, sort_keys=True))
    os.replace(tmp, p)


def read_current() -> dict | None:
    try:
        return json.loads((root() / "current.json").read_text())
    except Exception:
        return None


def age_s() -> float:
    try:
        return time.time() - (root() / "current.json").stat().st_mtime
    except Exception:
        return float("inf")


def _where(tables: dict) -> dict[tuple[str, str], int]:
    """(kind, id) -> level number (LOW 0 ... ULTRA 4)."""
    out = {}
    for kind, t in (tables or {}).items():
        for i, lv in enumerate(LEVELS):
            for m in (t.get("levels") or {}).get(lv, []):
                out[(kind, m["id"])] = i
    return out


def diff(old: dict | None, new: dict) -> list[dict]:
    """Joined / left / moved per kind. A move of two levels or more is marked big - and applied anyway (D9)."""
    a, b = _where((old or {}).get("tables") or {}), _where(new.get("tables") or {})
    ch = []
    for k in sorted(set(a) | set(b)):
        kind, mid = k
        if k not in a:
            ch.append({"kind": kind, "id": mid, "change": "joined", "to": LEVELS[b[k]]})
        elif k not in b:
            ch.append({"kind": kind, "id": mid, "change": "left", "from": LEVELS[a[k]]})
        elif a[k] != b[k]:
            ch.append({"kind": kind, "id": mid, "change": "moved", "from": LEVELS[a[k]], "to": LEVELS[b[k]],
                       "big": abs(a[k] - b[k]) >= 2})
    return ch


def save(doc: dict) -> list[dict]:
    old = read_current()
    changes = diff(old, doc) if old else []
    day = doc["read_on"]
    _write(root() / f"tables-{day}.json", doc)
    _write(root() / "current.json", doc)
    if changes:
        root().mkdir(parents=True, exist_ok=True)
        with open(root() / "changes.jsonl", "a", encoding="utf-8") as f:
            for c in changes:
                f.write(json.dumps({"on": day, **c}, ensure_ascii=False) + "\n")
    return changes


def recent_changes(n: int = 100) -> list[dict]:
    try:
        lines = (root() / "changes.jsonl").read_text().splitlines()[-n:]
        return [json.loads(x) for x in lines if x.strip()]
    except Exception:
        return []


def cache_get(name: str, max_age_s: float) -> Any:
    p = root() / "cache" / f"{name}.json"
    try:
        if time.time() - p.stat().st_mtime <= max_age_s:
            return json.loads(p.read_text())
    except Exception:
        pass
    return None


def cache_put(name: str, data: Any) -> None:
    _write(root() / "cache" / f"{name}.json", data)
