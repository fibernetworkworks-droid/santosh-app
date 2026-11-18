"""C1 ONE WRITER PER CHAT (docs/CLAUDE_CHAT_100_PLAN.md, owner: "1 WRITER, SEVERAL WORKER, SEVERAL CHECKER").

The writer is the model that talks to her: it reads her message, uses the workers' results and writes the one reply. It
is chosen ONCE, on the first Box message of a chat, and the chat keeps it - so every reply in a chat has one voice,
one way of formatting, one reading of the chat so far (and one prompt cache). Workers (parts.py) and checkers
(checkers.py) may be any model; they never speak to her.

The writer changes only for a reason she is told about, in one short line (a `model_switch` event):
  up      a later ask needs a higher level than the writer was chosen at -> the chat moves UP to that level's model
          (never down: an easy message after a hard one keeps the stronger writer)
  moved   the writer is off (banned / gone / paused after failures) or cannot do this message (a picture it cannot
          read, no tools) -> the Box's pick for this message becomes the writer
  handed  the writer failed in the middle of a reply and a backup finished it -> the backup is the writer from now on
Her own pick in the model dropdown is always the writer (she chose it; nothing is said).

The first writer is chosen at least at `pipeline_writer_floor` (MID): a chat that opens with "hi" must not keep a LOW
model for the real work that follows. Kept in data/pipeline/writers.db (survives a restart), 90 days.
"""
from __future__ import annotations

import logging
import sqlite3
import threading
import time
from typing import Any

from ..config import get_settings
from . import choose as C
from . import store
from .kinds import LEVELS

log = logging.getLogger("santosh.pipeline")
KEEP_S = 90 * 86400
_LOCK = threading.Lock()
STATS = {"pinned": 0, "kept": 0, "up": 0, "moved": 0, "handed": 0, "pick": 0}


def on() -> bool:
    return bool(getattr(get_settings(), "pipeline_one_writer", True))


def fixed() -> list[str]:
    """v0.999 her chosen writers, in order (`pipeline_writers`); [] = the Box chooses."""
    raw = str(getattr(get_settings(), "pipeline_writers", "") or "")
    out: list[str] = []
    for x in raw.split(","):
        x = x.strip()
        if x and x not in out:
            out.append(x)
    return out


def _fixed(conv: str, r: dict, fx: list[str], cur: dict | None, *, doc: dict | None, health: dict | None,
           lv: str, kind: str, t: float, out: dict) -> dict[str, Any]:
    """Her writers: the first one able to write (not paused, can take this message) writes; a chat keeps the one it
    has while that one can still write; the others are its backups. None can = the Box's pick for this message only."""
    models = (doc or {}).get("models") or {}
    ok: list[dict] = []
    why: dict[str, str] = {}
    for mid in fx:
        m = {"id": mid, "route": "openrouter", "status": "ready", "level": lv, "name": mid}
        h = (health or {}).get(mid) or {}
        w = "is not answering right now" if h.get("paused") else C._can(m, models.get(mid), kind,
                                                                         {"tools": True, "kind": kind}).strip()
        if w:
            why[mid] = w
        else:
            ok.append(m)
    box = r.get("model") or {}
    if not ok:                                         # none of hers can: this message only, nothing pinned
        STATS["moved"] += 1
        names = " and ".join(_name(x) for x in fx)
        first = next(iter(why.values()), "cannot write this")
        log.warning("pipeline writer %s: none of %s can write (%s) - %s for this message", conv, fx, why,
                    box.get("id"))
        return {**out, "event": "moved",
                "note": f"{names} cannot take this message ({first}) - {_name(box.get('id') or '')} answers it."}
    prev = (cur or {}).get("model") or ""
    first = next((m for m in ok if m["id"] == prev), ok[0])
    extra = [box] if box.get("id") and box["id"] not in fx else []     # one last safety after her writers
    backups = [C._public(m) for m in ok if m["id"] != first["id"]] + [C._public(m) for m in extra[:1]]
    res = {"model": C._public(first), "backups": backups, "level": lv, "event": "kept", "note": ""}
    if not cur:
        STATS["pinned"] += 1
        res["event"] = "pinned"
        _put(conv, first["id"], lv, kind, "her writer", False, t)
        log.warning("pipeline writer %s: %s (her writer) for this chat", conv, first["id"])
    elif prev == first["id"]:
        STATS["kept"] += 1
        _put(conv, prev, lv, kind, cur.get("why") or "her writer", False, t)
    else:
        STATS["moved"] += 1
        res["event"] = "moved"
        _put(conv, first["id"], lv, kind, f"{prev} {why.get(prev, 'replaced by her writers')}", True, t)
        if prev in fx:                                  # her writer is down: say it; an old pick from before: quietly
            res["note"] = f"{_name(prev)} {why.get(prev, 'cannot write now')} - this chat continues with {_name(first['id'])}."
        log.warning("pipeline writer %s: %s -> %s (%s)", conv, prev, first["id"], why.get(prev, "her writers"))
    return res


def _db() -> sqlite3.Connection:
    store.root().mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(str(store.root() / "writers.db"), timeout=5)
    c.execute("CREATE TABLE IF NOT EXISTS writers (conv TEXT PRIMARY KEY, model TEXT, level TEXT, kind TEXT, "
              "why TEXT, at REAL, changes INTEGER DEFAULT 0)")
    return c


def get(conv: str, now: float | None = None) -> dict | None:
    if not conv:
        return None
    t = now if now is not None else time.time()
    try:
        with _LOCK, _db() as c:
            r = c.execute("SELECT model, level, kind, why, at, changes FROM writers WHERE conv=?", (conv,)).fetchone()
    except Exception as e:   # noqa: BLE001 - no record = the Box chooses as before
        log.warning("pipeline writer: read failed (%s)", str(e)[:100])
        return None
    if not r or t - float(r[4] or 0) > KEEP_S:
        return None
    return {"model": r[0], "level": r[1], "kind": r[2], "why": r[3], "at": r[4], "changes": int(r[5] or 0)}


def _put(conv: str, model: str, level: str, kind: str, why: str, changed: bool, now: float) -> None:
    try:
        with _LOCK, _db() as c:
            c.execute("INSERT INTO writers (conv, model, level, kind, why, at, changes) VALUES (?,?,?,?,?,?,?) "
                      "ON CONFLICT(conv) DO UPDATE SET model=excluded.model, level=excluded.level, kind=excluded.kind, "
                      "why=excluded.why, at=excluded.at, changes=writers.changes + ?",
                      (conv, model, level, kind, why[:200], now, int(changed), int(changed)))
            c.execute("DELETE FROM writers WHERE at < ?", (now - KEEP_S,))
    except Exception as e:   # noqa: BLE001
        log.warning("pipeline writer: write failed (%s)", str(e)[:100])


def forget(conv: str) -> None:
    try:
        with _LOCK, _db() as c:
            c.execute("DELETE FROM writers WHERE conv=?", (conv,))
    except Exception:   # noqa: BLE001
        pass


def _idx(level: str) -> int:
    try:
        return LEVELS.index(str(level or "MID").upper())
    except ValueError:
        return 1


def _name(mid: str) -> str:
    try:
        from .receipt import pretty
        return pretty(mid)
    except Exception:   # noqa: BLE001
        return mid


def _backups(first: dict, r: dict) -> list[dict]:
    """Two backups for the writer: the Box's pick for this message (when it is not the writer) + its backups."""
    pool = [m for m in [r.get("model") or {}] + list(r.get("backups") or []) if m and m.get("id")]
    return C._spread(pool, first, 2)


def decide(conv: str, r: dict, *, doc: dict | None = None, health: dict | None = None, pin: str = "",
           surface: str = "chat", now: float | None = None) -> dict[str, Any]:
    """Who writes this message. `r` = the Box's choice for it (box.choose_for or a P3 writer part).

    -> {model, backups, level, event, note}. `event`: pinned / kept / up / moved / pick / none; `note` = the one
    line she is shown ('' when nothing changed for her)."""
    t = now if now is not None else time.time()
    m, lv = (r.get("model") or {}), (r.get("level_used") or r.get("level") or "MID")
    out = {"model": m, "backups": list(r.get("backups") or []), "level": lv, "event": "none", "note": ""}
    if not on() or not conv or not m.get("id"):
        return out
    kind = r.get("kind") or "chat"
    if pin:                                           # her own pick: always the writer, nothing to say
        STATS["pick"] += 1
        _put(conv, m["id"], lv, kind, "her own pick", False, t)
        return {**out, "event": "pick"}
    cur = get(conv, t)
    fx = fixed()
    if fx:                                            # v0.999 her writers decide, not the Box's tables
        return _fixed(conv, r, fx, cur, doc=doc, health=health, lv=lv, kind=kind, t=t, out=out)
    if surface != "chat" and not cur:                 # a routine / wake never chooses the chat's writer
        return out
    if not cur:
        floor = str(getattr(get_settings(), "pipeline_writer_floor", "MID") or "MID").upper()
        if _idx(lv) < _idx(floor) and doc:
            try:
                r2 = C.choose(C.snapshot(doc), {"kind": kind, "level": floor, "language": r.get("language") or "",
                                                "surface": "chat", "tools": True}, health=health, now=t)
                if (r2.get("model") or {}).get("id"):
                    m, lv = r2["model"], r2.get("level_used") or floor
                    out.update(model=m, backups=list(r2.get("backups") or []), level=lv)
            except Exception as e:   # noqa: BLE001 - the message's own pick then
                log.warning("pipeline writer: floor choice failed (%s)", str(e)[:100])
        STATS["pinned"] += 1
        _put(conv, m["id"], lv, kind, "first message of the chat", False, t)
        log.warning("pipeline writer %s: %s at %s for this chat", conv, m["id"], lv)
        return {**out, "event": "pinned"}

    cid = cur["model"]
    wm = {"id": cid, "route": "openrouter", "status": "ready", "level": cur["level"], "name": cid}
    info = ((doc or {}).get("models") or {}).get(cid)
    h = (health or {}).get(cid) or {}
    cant = ""
    if h.get("paused"):
        cant = "is not answering right now"
    else:
        cant = C._can(wm, info, kind, {"tools": True, "kind": kind}).strip()
    if cant and m["id"] != cid:
        STATS["moved"] += 1
        _put(conv, m["id"], lv, kind, f"{cid} {cant}", True, t)
        note = (f"{_name(cid)} {cant} - this chat continues with {_name(m['id'])}." if h.get("paused")
                else f"Switched to {_name(m['id'])} for this chat: {_name(cid)} {cant}.")
        log.warning("pipeline writer %s: %s -> %s (%s)", conv, cid, m["id"], cant)
        return {**out, "event": "moved", "note": note}
    if _idx(lv) > _idx(cur["level"]):
        STATS["up"] += 1
        _put(conv, m["id"], lv, kind, f"needed {lv}", m["id"] != cid, t)
        note = ("" if m["id"] == cid else
                f"This needs a stronger model - this chat now continues on {_name(m['id'])}.")
        log.warning("pipeline writer %s: up %s -> %s (%s -> %s)", conv, cur["level"], lv, cid, m["id"])
        return {**out, "event": "up", "note": note}
    STATS["kept"] += 1
    first = {**wm, "level": cur["level"]}
    _put(conv, cid, cur["level"], cur.get("kind") or kind, cur.get("why") or "", False, t)
    return {"model": C._public(first), "backups": [C._public(b) for b in _backups(first, r)],
            "level": cur["level"], "event": "kept", "note": ""}


def handed(conv: str, ran_on: str, level: str, why: str, now: float | None = None) -> str:
    """The writer failed mid-reply and `ran_on` finished it: the chat keeps `ran_on` from now on. -> the line to
    show ('' when nothing changed)."""
    if not on() or not conv or not ran_on:
        return ""
    cur = get(conv, now)
    if not cur or cur["model"] == ran_on:
        return ""
    fx = fixed()
    if fx and ran_on not in fx:                       # a safety model finished this reply; her writers stay
        STATS["handed"] += 1
        return f"{_name(cur['model'])} stopped answering - {_name(ran_on)} finished this reply."
    STATS["handed"] += 1
    _put(conv, ran_on, level or cur["level"], cur.get("kind") or "chat", f"took over: {why}"[:200], True,
         now if now is not None else time.time())
    return f"{_name(cur['model'])} stopped answering - {_name(ran_on)} finished this reply and continues this chat."


def say(conv: str, note: str, frm: str = "", to: str = "", event: str = "") -> None:
    """The one quiet line under the chat (a `model_switch` event; local to its chat, never pushed)."""
    if not note:
        return
    try:
        from ..events import bus
        bus.publish(conv, "model_switch", {"text": note, "from": frm, "to": to, "event": event})
    except Exception as e:   # noqa: BLE001
        log.warning("pipeline writer: note failed (%s)", str(e)[:100])
