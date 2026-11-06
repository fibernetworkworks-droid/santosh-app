"""v0.639 PAKDO: a watchdog that names what BLOCKS the server's event loop.

Her 16:52 call: the call brain's memory step was given 2.5 s and took 5.6 s, and ~6 s more went between the last timed
stage and the first model call - a quick DB read did not finish either. That is the shape of a BLOCKED event loop (some
code doing slow sync work on it) or a FULL default thread pool. A side thread pings the loop every 0.5 s; when a ping is
not answered within `threshold` seconds it captures what the loop thread is running at that moment and logs it
(`event loop blocked N s; it was running: ...`, at most once per 10 s). Reading only - it changes nothing."""
from __future__ import annotations

import asyncio
import logging
import sys
import threading
import time
import traceback

log = logging.getLogger("santosh.looplag")
STATS = {"stalls": 0, "worst_s": 0.0, "started": False}


def pool_queue(loop=None) -> int:
    """How many jobs wait in the loop's default thread pool (-1 when unknown)."""
    try:
        loop = loop or asyncio.get_running_loop()
        ex = getattr(loop, "_default_executor", None)
        return ex._work_queue.qsize() if ex is not None else 0
    except Exception:
        return -1


def start(threshold: float = 1.0) -> bool:
    if STATS["started"]:
        return False
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return False
    STATS["started"] = True
    tid = threading.get_ident()

    def run() -> None:
        last = 0.0
        while True:
            ev = threading.Event()
            t0 = time.monotonic()
            try:
                loop.call_soon_threadsafe(ev.set)
            except RuntimeError:
                return              # the loop is closed
            if not ev.wait(threshold):
                frame = sys._current_frames().get(tid)
                stack = "".join(traceback.format_stack(frame, limit=14)) if frame is not None else "?"
                ev.wait(60)
                lag = time.monotonic() - t0
                STATS["stalls"] += 1
                STATS["worst_s"] = max(STATS["worst_s"], round(lag, 1))
                if time.monotonic() - last > 10:
                    last = time.monotonic()
                    log.warning("event loop blocked %.1fs (pool queue %d); it was running:\n%s",
                                lag, pool_queue(loop), stack)
            time.sleep(0.5)

    threading.Thread(target=run, name="looplag", daemon=True).start()
    return True
