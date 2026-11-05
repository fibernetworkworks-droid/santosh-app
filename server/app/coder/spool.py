"""HOOLA CODER spool - the durable hand-off (v0.473.0).

Claude-mem's core process lesson, ported: the capture hook (hot path, inside the agent's tool
funnel) must NEVER wait on the worker. It writes ONE atomic JSON file and returns. The worker
drains the folder later - exactly once (the filename IS the dedupe key, a consumed marker is
stamped only after success), with a 7-day retry window (undeliverable files age out to expired/,
corrupt JSON goes to corrupt/), and a hard per-event size bound.

Everything here fails open: a spool failure is logged and swallowed - capture can never break
a tool call, a call, or a turn.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import time

log = logging.getLogger("coder.spool")

MAX_EVENT_BYTES = 1 * 1024 * 1024          # a tool payload bigger than this is dropped, not queued
RETRY_WINDOW_S = 7 * 86400                 # claude-mem's HOOK_SPOOL_RETRY_WINDOW_MS
KINDS = ("observation", "summarize", "session_end", "note")


def root() -> str:
    import os
    d = os.path.join(_coder_root(), "spool")
    os.makedirs(d, exist_ok=True)
    for sub in ("corrupt", "expired"):
        os.makedirs(os.path.join(d, sub), exist_ok=True)
    return d


def _coder_root() -> str:
    from ..config import get_settings
    return getattr(get_settings(), "coder_dir", "./data/coder") or "./data/coder"


def event_key(kind: str, payload: dict) -> str:
    """The dedupe key: kind + a hash of the identity fields (claude-mem: session+platform+tool_use_id)."""
    ident = "\0".join([str(payload.get("conv", "")), str(payload.get("turn_id", "")),
                       str(payload.get("tool", "")), str(payload.get("seq", "")),
                       str(payload.get("text", ""))[:512]])
    return f"{kind}-{hashlib.sha256(ident.encode('utf-8')).hexdigest()[:24]}.json"


def spool_event(kind: str, payload: dict) -> bool:
    """Fire-and-forget: one atomic file. Returns False only when the event is too big or insane."""
    try:
        if kind not in KINDS:
            return False
        raw = json.dumps({"kind": kind, "enqueued_at_epoch": int(time.time()), **payload},
                         ensure_ascii=False, default=str)
        if len(raw.encode("utf-8")) > MAX_EVENT_BYTES:
            log.info("coder event too big (%s bytes, kind=%s) - dropped, never queued", len(raw), kind)
            return False
        name = event_key(kind, payload)
        path = os.path.join(root(), name)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(raw)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)              # atomic: readers never see a half event
        return True
    except Exception:
        log.exception("coder spool write failed (capture continues without memory)")
        return False


def drain(limit: int = 200) -> list[dict]:
    """List the spool in enqueue order. Does NOT consume; the observer confirms each event."""
    try:
        d = root()
        files = [f for f in os.listdir(d) if f.endswith(".json")]
        out = []
        for f in sorted(files, key=lambda n: os.path.getmtime(os.path.join(d, n)))[:limit]:
            p = os.path.join(d, f)
            try:
                with open(p, encoding="utf-8") as fh:
                    ev = json.load(fh)
                ev["_file"], ev["_mtime"] = f, os.path.getmtime(p)
                out.append(ev)
            except Exception:
                _quarantine(p, "corrupt")
        return out
    except Exception:
        log.exception("coder spool drain failed")
        return []


def consume(name: str) -> None:
    """Exactly-once confirm: stamp the marker, unlink the file."""
    try:
        from . import store
        store.mark_consumed(name)
        with _suppress():
            os.unlink(os.path.join(root(), name))
    except Exception:
        log.exception("coder spool consume failed")


def is_consumed(name: str) -> bool:
    try:
        from . import store
        return store.is_consumed(name)
    except Exception:
        return False


def sweep() -> None:
    """Retry window: files older than 7 days that were never consumed go to expired/."""
    try:
        d = root()
        now = time.time()
        for f in os.listdir(d):
            if not f.endswith(".json"):
                continue
            p = os.path.join(d, f)
            if now - os.path.getmtime(p) > RETRY_WINDOW_S:
                _quarantine(p, "expired")
    except Exception:
        log.exception("coder spool sweep failed")


def _quarantine(p: str, sub: str) -> None:
    try:
        dst = os.path.join(os.path.dirname(p), sub, os.path.basename(p) + "." + str(int(time.time())))
        os.replace(p, dst)
    except Exception:
        log.exception("coder spool quarantine failed")


class _suppress:
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return True
