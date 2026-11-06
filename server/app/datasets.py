"""v0.238 DATA DESK: big data stays in a file on the server, Hoola only sees a short summary.

The root cause of the "top 100 AI repos PDF" failure: every tool result reaching the model is cut to 6,000
characters, so a GitHub search reply showed ~2 repos; Hoola then escaped to its cloud PC, where the data got stuck.
Claude's way: a script fetches, keeps only the needed fields, saves a file, and the model reads small slices.

A dataset = a list of flat rows (dicts) + meta, saved as JSON at DATASETS_DIR/<tenant>/<id>.json (kept 14 days).
`pick` turns any JSON reply into rows with only the fields asked for ("owner.login", "stars=stargazers_count").
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import time
from pathlib import Path
from typing import Any

KEEP_DAYS = 14
MAX_ROWS = 5000
MAX_CELL = 600          # one cell's text in a saved row
_ID = re.compile(r"^ds_[a-f0-9]{10}$")


class DataError(ValueError):
    pass


def _root(tenant: str) -> Path:
    base = Path(os.environ.get("DATASETS_DIR", "data/datasets"))
    d = base / hashlib.sha256(str(tenant or "default").encode()).hexdigest()[:16]
    d.mkdir(parents=True, exist_ok=True)
    return d


def _path(tenant: str, ds: str) -> Path:
    ds = str(ds or "").strip()
    if not _ID.match(ds):
        raise DataError("dataset id galat hai (ds_xxxxxxxxxx).")
    return _root(tenant) / f"{ds}.json"


# ---------------------------------------------------------------- shaping
def _get(obj: Any, path: str) -> Any:
    cur = obj
    for part in [p for p in str(path or "").split(".") if p]:
        if isinstance(cur, dict):
            cur = cur.get(part)
        elif isinstance(cur, list) and part.isdigit() and int(part) < len(cur):
            cur = cur[int(part)]
        elif isinstance(cur, list):               # "topics.name" over a list of dicts -> list of values
            cur = [x.get(part) for x in cur if isinstance(x, dict)]
        else:
            return None
    return cur


def find_items(data: Any, items_path: str = "") -> list:
    """The list of records in an API reply: the given dot path, the top level, or the first list of dicts."""
    if items_path:
        got = _get(data, items_path)
        if not isinstance(got, list):
            raise DataError(f"items_path '{items_path}' par list nahi mili.")
        return got
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for k in ("items", "data", "results", "records", "rows", "entries", "list", "hits"):
            v = data.get(k)
            if isinstance(v, list):
                return v
            if isinstance(v, dict):               # e.g. {"data": {"children": [...]}}
                for v2 in v.values():
                    if isinstance(v2, list) and v2 and isinstance(v2[0], dict):
                        return v2
        for v in data.values():
            if isinstance(v, list) and v and isinstance(v[0], dict):
                return v
        return [data]
    return []


def _spec(fields: list[str] | str | None) -> list[tuple[str, str]]:
    """'stars=stargazers_count' -> (stars, stargazers_count); 'owner.login' -> (owner_login, owner.login)."""
    if isinstance(fields, str):
        fields = [f for f in re.split(r"[,\n]", fields)]
    out = []
    for f in fields or []:
        f = str(f).strip()
        if not f:
            continue
        if "=" in f:
            name, path = [x.strip() for x in f.split("=", 1)]
        else:
            name, path = f.replace(".", "_"), f
        if name and path:
            out.append((name[:60], path[:200]))
    return out[:40]


def _clean(v: Any) -> Any:
    if isinstance(v, str):
        return v if len(v) <= MAX_CELL else v[:MAX_CELL] + "…"
    if isinstance(v, list):
        if all(not isinstance(x, (dict, list)) for x in v):
            return [_clean(x) for x in v[:30]]
        return json.dumps(v, ensure_ascii=False, default=str)[:MAX_CELL]
    if isinstance(v, dict):
        return json.dumps(v, ensure_ascii=False, default=str)[:MAX_CELL]
    return v


def pick(items: list, fields: list[str] | str | None = None) -> list[dict]:
    """Rows with only the asked fields. No fields: the record's own simple (non-nested) values, at most 12."""
    spec = _spec(fields)
    rows = []
    for it in items:
        if spec:
            rows.append({name: _clean(_get(it, path)) for name, path in spec})
        elif isinstance(it, dict):
            flat = {k: _clean(v) for k, v in it.items() if not isinstance(v, (dict, list)) and not str(k).endswith("_url")}
            rows.append(dict(list(flat.items())[:12]))
        else:
            rows.append({"value": _clean(it)})
    return rows


# ---------------------------------------------------------------- store
def save(tenant: str, rows: list[dict], name: str = "", source: str = "", meta: dict | None = None) -> dict:
    if not rows:
        raise DataError("Koi row nahi mili; kuch save nahi hua.")
    rows = rows[:MAX_ROWS]
    ds = "ds_" + secrets.token_hex(5)
    cols: list[str] = []
    for r in rows:
        for k in r:
            if k not in cols:
                cols.append(k)
    doc = {"id": ds, "name": str(name or ds)[:120], "source": str(source)[:500], "saved_at": int(time.time()),
           "count": len(rows), "columns": cols, "meta": meta or {}, "rows": rows}
    _path(tenant, ds).write_text(json.dumps(doc, ensure_ascii=False, default=str))
    sweep(tenant)
    return doc


def load(tenant: str, ds: str) -> dict:
    p = _path(tenant, ds)
    if not p.exists():
        raise DataError(f"Dataset {ds} nahi mila (14 din baad hat jata hai). Dobara data_fetch kijiye.")
    return json.loads(p.read_text())


def annotate(tenant: str, ds: str, notes: dict, key: str = "", column: str = "note") -> dict:
    """Write text into one column for the rows whose key matches (case-insensitive). Saved at once."""
    doc = load(tenant, ds)
    cols = doc.get("columns") or []
    key = key or (cols[0] if cols else "")
    column = re.sub(r"[^A-Za-z0-9_]", "_", column or "note")[:40] or "note"
    want = {str(k).strip().lower(): str(v)[:4000] for k, v in notes.items() if str(k).strip()}
    hit = 0
    for r in doc["rows"]:
        k = str(r.get(key, "")).strip().lower()
        if k in want:
            r[column] = want.pop(k)
            hit += 1
    if column not in cols:
        cols.append(column)
    doc["columns"] = cols
    _path(tenant, ds).write_text(json.dumps(doc, ensure_ascii=False, default=str))
    missing = [r.get(key) for r in doc["rows"] if not r.get(column)]
    return {"dataset": ds, "written": hit, "not_matched": list(want)[:10], "rows_without_" + column: len(missing),
            "next_to_write": missing[:15]}


def sweep(tenant: str) -> int:
    cut = time.time() - KEEP_DAYS * 86400
    n = 0
    for p in _root(tenant).glob("ds_*.json"):
        if p.stat().st_mtime < cut:
            p.unlink(missing_ok=True)
            n += 1
    return n


def rows_slice(doc: dict, offset: int = 0, limit: int = 20, fields: list[str] | str | None = None,
               sort: str = "", desc: bool = True, q: str = "") -> tuple[list[dict], int]:
    rows = list(doc.get("rows") or [])
    if q:
        ql = str(q).lower()
        rows = [r for r in rows if ql in json.dumps(r, ensure_ascii=False).lower()]
    if sort:
        try:
            rows.sort(key=lambda r: (r.get(sort) is None, r.get(sort) if not isinstance(r.get(sort), str) else
                                 r.get(sort).lower()), reverse=bool(desc))
        except TypeError:
            rows.sort(key=lambda r: str(r.get(sort) or ""), reverse=bool(desc))
        if desc:   # None values stay last after the reverse
            rows = [r for r in rows if r.get(sort) is not None] + [r for r in rows if r.get(sort) is None]
    total = len(rows)
    keep = [f.strip() for f in (fields.split(",") if isinstance(fields, str) else fields or []) if str(f).strip()]
    part = rows[max(0, int(offset)):max(0, int(offset)) + max(1, min(int(limit), 100))]
    if keep:
        part = [{k: r.get(k) for k in keep} for r in part]
    return part, total


def to_csv(doc: dict) -> bytes:
    import csv
    import io
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=doc.get("columns") or [], extrasaction="ignore")
    w.writeheader()
    for r in doc.get("rows") or []:
        w.writerow({k: (", ".join(map(str, v)) if isinstance(v, list) else v) for k, v in r.items()})
    return buf.getvalue().encode("utf-8-sig")


def as_text(rows: list[dict], limit: int = 5500) -> str:
    """Compact one-line-per-row preview the model can read (never the raw reply)."""
    lines = []
    for r in rows:
        parts = []
        for k, v in r.items():
            if isinstance(v, list):
                v = ", ".join(map(str, v[:8]))
            s = str(v)
            parts.append(f"{k}: {s[:240]}")
        lines.append(" | ".join(parts))
    out = "\n".join(lines)
    return out if len(out) <= limit else out[:limit] + "\n…(aur rows: data_read se offset badhakar padhiye)"
