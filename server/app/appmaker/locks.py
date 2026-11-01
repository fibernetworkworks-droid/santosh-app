"""v0.388 PAKKI NEEV (App Sahayak Pillar B): locks that hold across server PROCESSES, not just threads.

Before this, stock / coupons / slots / GST numbers / udhaar / approvals each had a `threading.Lock()` - safe inside ONE
process only, and each feature had its OWN lock while they all rewrite the same `AppProject.backend` JSON, so a stock
change and a coupon change at the same moment could overwrite each other even in one process.

Now there is ONE lock per key, re-entrant per thread, held across processes:
  * Postgres (DATABASE_URL = postgresql...): `pg_advisory_lock` on a dedicated pooled connection (lock_timeout bounded);
  * SQLite: an fcntl file lock next to the database file (every worker on the box sees it) + a thread lock.
`app(app_id)` = the app's one lock for every read-modify-write of its backend JSON and its money / stock / slot / number
counters. Keys never nest in a different order (only `appr:` -> `app:`), so there is no deadlock."""
from __future__ import annotations

import contextlib
import hashlib
import logging
import os
import threading
import time
from pathlib import Path
from typing import Iterator

log = logging.getLogger(__name__)
WAIT_SECONDS = 15
STATS = {"taken": 0, "waited_ms_max": 0, "timeouts": 0, "pg": 0, "file": 0}
_local = threading.local()
_thread_locks: dict[str, threading.RLock] = {}
_guard = threading.Lock()


class LockTimeout(RuntimeError):
    pass


def _held() -> dict[str, int]:
    h = getattr(_local, "held", None)
    if h is None:
        h = _local.held = {}
    return h


def _tlock(key: str) -> threading.RLock:
    with _guard:
        lk = _thread_locks.get(key)
        if lk is None:
            lk = _thread_locks[key] = threading.RLock()
        return lk


def _key64(key: str) -> int:
    return int.from_bytes(hashlib.sha1(key.encode()).digest()[:8], "big", signed=True)


def _lock_dir() -> Path:
    from ..config import get_settings
    url = get_settings().database_url
    base = Path(url.split("///", 1)[1]).resolve().parent if url.startswith("sqlite:///") and "///" in url else Path(".").resolve()
    d = base / ".hoola_locks"
    d.mkdir(parents=True, exist_ok=True)
    return d


@contextlib.contextmanager
def hold(key: str, wait: float = WAIT_SECONDS) -> Iterator[None]:
    """One named lock across threads AND processes. Re-entrant: the same thread may take it again inside."""
    held = _held()
    if held.get(key):
        held[key] += 1
        try:
            yield
        finally:
            held[key] -= 1
        return
    t0 = time.monotonic()
    tl = _tlock(key)
    if not tl.acquire(timeout=wait):
        STATS["timeouts"] += 1
        raise LockTimeout(f"busy: {key}")
    release = None
    try:
        release = _cross_process(key, max(0.5, wait - (time.monotonic() - t0)))
        waited = int((time.monotonic() - t0) * 1000)
        STATS["taken"] += 1
        STATS["waited_ms_max"] = max(STATS["waited_ms_max"], waited)
        held[key] = 1
        try:
            yield
        finally:
            held.pop(key, None)
    finally:
        if release is not None:
            try:
                release()
            except Exception:                       # noqa: BLE001 - a lock release never breaks the write it guarded
                log.exception("lock release failed: %s", key)
        tl.release()


def _cross_process(key: str, wait: float):
    from .. import db
    eng = db._engine
    if eng is not None and eng.dialect.name == "postgresql":
        conn = eng.raw_connection()
        try:
            cur = conn.cursor()
            cur.execute(f"SET lock_timeout = '{int(wait * 1000)}ms'")
            try:
                cur.execute("SELECT pg_advisory_lock(%s)", (_key64(key),))
            except Exception:
                STATS["timeouts"] += 1
                conn.rollback()
                conn.close()
                raise LockTimeout(f"busy: {key}")
            conn.commit()
        except LockTimeout:
            raise
        except Exception:
            conn.close()
            raise
        STATS["pg"] += 1

        def release():
            try:
                c2 = conn.cursor()
                c2.execute("SELECT pg_advisory_unlock(%s)", (_key64(key),))
                c2.execute("RESET lock_timeout")
                conn.commit()
            finally:
                conn.close()                         # back to the pool
        return release
    try:
        import fcntl
    except ImportError:                              # not a POSIX box: the thread lock is all there is
        return None
    path = _lock_dir() / (hashlib.sha1(key.encode()).hexdigest()[:24] + ".lock")
    fd = os.open(str(path), os.O_RDWR | os.O_CREAT, 0o600)
    deadline = time.monotonic() + wait
    while True:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            break
        except BlockingIOError:
            if time.monotonic() > deadline:
                os.close(fd)
                STATS["timeouts"] += 1
                raise LockTimeout(f"busy: {key}")
            time.sleep(0.005)
    STATS["file"] += 1

    def release():
        try:
            fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            os.close(fd)
    return release


def app(app_id: str):
    """THE lock of one app: its backend JSON, stock, coupons, slots, GST numbers, udhaar."""
    return hold(f"app:{app_id}")
