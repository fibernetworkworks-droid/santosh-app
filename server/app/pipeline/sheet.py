"""P2 THE JOB SHEET + THE HAND-OFF PACKAGE (plan 6.1 + 6.3).

One sheet per message: the plan (P2 = one part), each part's state (waiting / running / waiting_tap / done / failed),
the model chosen and why, tries, the part's hand-off package and the final check. Every part reads only from the sheet
and writes only to it; the sheet is saved at every change, so a restart can see the last finished part.

Kept in its own small SQLite file beside the tables (`data/pipeline/sheets.db`) - nothing in the main database moves.
Her words are kept masked and cut to 200 characters (the chat itself keeps the message; the sheet only needs to say
which message it was).
"""
from __future__ import annotations

import json
import sqlite3
import threading
import time
import uuid
from typing import Any

from . import store

STATES = ("waiting", "running", "waiting_tap", "done", "failed")
_LOCK = threading.Lock()
KEEP_DAYS = 30


def _db() -> sqlite3.Connection:
    store.root().mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(str(store.root() / "sheets.db"), timeout=5)
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("CREATE TABLE IF NOT EXISTS sheets (id TEXT PRIMARY KEY, conv TEXT, tenant TEXT, at REAL, "
              "status TEXT, data TEXT)")
    c.execute("CREATE INDEX IF NOT EXISTS sheets_conv ON sheets (conv, at)")
    return c


def _mask(text: str) -> str:
    try:
        from ..pii import mask_sensitive
        text = mask_sensitive(text)
    except Exception:   # noqa: BLE001
        pass
    return str(text or "")[:200]


def package(result: str = "", facts: list[dict] | None = None, files: list[str] | None = None,
            notes: list[str] | None = None, not_done: list[str] | None = None) -> dict[str, Any]:
    """6.3: what one part passes on - never the previous model's whole working."""
    return {"result": str(result or ""), "facts": list(facts or []), "files": list(files or []),
            "notes": list(notes or []), "not_done": list(not_done or [])}


def new(conv: str, tenant: str, ask: str, parts: list[dict], read_on: str = "", surface: str = "chat",
        now: float | None = None) -> dict[str, Any]:
    t = now if now is not None else time.time()
    sh = {"id": "sh_" + uuid.uuid4().hex[:12], "conv": conv, "tenant": tenant, "at": t, "read_on": read_on,
          "surface": surface, "ask": _mask(ask), "status": "running", "parts": [], "check": None, "ended": None}
    for i, p in enumerate(parts, 1):
        sh["parts"].append({"n": i, "state": "waiting", "tries": 0, "out": None, **p})
    save(sh)
    return sh


def set_state(sh: dict, n: int, state: str, **extra: Any) -> None:
    if state not in STATES:
        raise ValueError(f"unknown part state {state!r}")
    p = sh["parts"][n - 1]
    p["state"] = state
    if state == "running":
        p["tries"] = int(p.get("tries") or 0) + 1
        p.setdefault("started", time.time())
    if state in ("done", "failed"):
        p["ended"] = time.time()
    p.update(extra)
    save(sh)


def finish(sh: dict, check: dict | None = None) -> None:
    sh["check"] = check
    sh["ended"] = time.time()
    if any(p["state"] == "waiting_tap" for p in sh["parts"]):
        sh["status"] = "waiting_tap"        # P3: a branch waits for her tap; parts.tick carries it on
    else:
        sh["status"] = "failed" if any(p["state"] == "failed" for p in sh["parts"]) else "done"
    save(sh)


def save(sh: dict) -> None:
    with _LOCK:
        c = _db()
        try:
            c.execute("INSERT OR REPLACE INTO sheets (id, conv, tenant, at, status, data) VALUES (?,?,?,?,?,?)",
                      (sh["id"], sh["conv"], sh["tenant"], sh["at"], sh["status"],
                       json.dumps(sh, ensure_ascii=False, default=str)))
            c.commit()
        finally:
            c.close()


def get(sheet_id: str) -> dict | None:
    with _LOCK:
        c = _db()
        try:
            r = c.execute("SELECT data FROM sheets WHERE id = ?", (sheet_id,)).fetchone()
        finally:
            c.close()
    return json.loads(r[0]) if r else None


def recent(conv: str = "", tenant: str = "", n: int = 20) -> list[dict]:
    q, args = "SELECT data FROM sheets", []
    where = []
    if conv:
        where.append("conv = ?")
        args.append(conv)
    if tenant:
        where.append("tenant = ?")
        args.append(tenant)
    if where:
        q += " WHERE " + " AND ".join(where)
    q += " ORDER BY at DESC LIMIT ?"
    args.append(int(n))
    with _LOCK:
        c = _db()
        try:
            rows = c.execute(q, args).fetchall()
        finally:
            c.close()
    return [json.loads(r[0]) for r in rows]


def unfinished(conv: str) -> dict | None:
    """The newest sheet of a chat that never finished (a restart cut it) - P3 continues from its last done part."""
    with _LOCK:
        c = _db()
        try:
            r = c.execute("SELECT data FROM sheets WHERE conv = ? AND status = 'running' ORDER BY at DESC LIMIT 1",
                          (conv,)).fetchone()
        finally:
            c.close()
    return json.loads(r[0]) if r else None


def waiting_tap(n: int = 50) -> list[dict]:
    """P3: the sheets with a branch waiting for her tap (newest first)."""
    with _LOCK:
        c = _db()
        try:
            rows = c.execute("SELECT data FROM sheets WHERE status = 'waiting_tap' ORDER BY at DESC LIMIT ?",
                             (int(n),)).fetchall()
        finally:
            c.close()
    return [json.loads(r[0]) for r in rows]


def sweep(now: float | None = None) -> int:
    cut = (now if now is not None else time.time()) - KEEP_DAYS * 86400
    with _LOCK:
        c = _db()
        try:
            n = c.execute("DELETE FROM sheets WHERE at < ?", (cut,)).rowcount
            c.commit()
        finally:
            c.close()
    return int(n or 0)


def main() -> int:
    """vps-ops `pipeline_sheets`: the newest 15 sheets, one block each (read-only)."""
    from ..config import get_settings
    print(f"pipeline_on = {bool(getattr(get_settings(), 'pipeline_on', False))}")
    cur = store.root() / "current.json"
    print(f"tables: {cur.resolve()} - {'present' if cur.exists() else 'MISSING (the Box stays off without them)'}")
    rows = recent(n=15)
    if not rows:
        print("no job sheets yet - a sheet is written for each chat message once pipeline_on is true")
        return 0
    for sh in rows:
        when = time.strftime("%d %b %H:%M:%S", time.localtime(sh["at"]))
        chk = sh.get("check") or {}
        surf = sh.get("surface") or "chat"
        print(f"\n{when}  {sh['status']}  box {sh.get('box_ms', '?')} ms" + (f"  [{surf}]" if surf != "chat" else "")
              + f"  ask: {sh.get('ask', '')[:80]!r}")
        if sh.get("multi"):
            print(f"  {len(sh['parts'])} parts, plan by {sh.get('plan_by', 'code')}"
                  + (f" ({sh.get('planner')}, {sh.get('plan_s')} s)" if sh.get("planner") else ""))
        for p in sh["parts"]:
            m = (p.get("model") or {}).get("id") or p.get("ran_on") or "-"
            bk = ", ".join(b["id"] for b in p.get("backups") or []) or "-"
            print(f"  part {p['n']}: {p.get('kind')} ({p.get('language')}) {p.get('level')} -> {m}  [backups {bk}]  "
                  f"{p['state']}" + (f"  after {p['after']}" if p.get("after") else "")
                  + (f"  {p['seconds']} s" if p.get("seconds") is not None else "")
                  + (f"  ({p['ask'][:60]!r})" if sh.get("multi") else ""))
            for nd in (p.get("out") or {}).get("not_done") or []:
                print(f"    not done: {nd[:140]}")
            for h in p.get("handover") or []:
                print(f"    hand-over ({h.get('event')}): {h.get('from')} -> {h.get('to')}  {str(h.get('why') or '')[:110]}")
            if p.get("applied"):
                print("    " + (f"ran on {p['ran_on']}" if p.get("ran_on") and p["ran_on"] != (p.get("model") or {}).get("id")
                                 else "ran on this model"))
            else:
                print(f"    not through the Box: {p.get('not_applied')}")
        if chk:
            print("  check: " + ("ok" if chk.get("ok") else "; ".join(chk.get("problems") or []))
                  + (f" (checked {', '.join(chk.get('checked') or [])})" if chk.get("checked") else " (no tools ran)"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
