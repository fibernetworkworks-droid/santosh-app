"""v0.208.1 memory janitor - why the voice-to-voice calls died mid-air.

The RCA (vps-ops mem job, 14 forced restarts in 5h) showed the server's RSS climbing
~100 MB/min during long tasks until the box (8 GB + 4 GB swap, swap 100% full) killed the
process while WebSockets were open. Two forces fed the climb:

1. DEAD EVENT-STREAM QUEUES: every SSE/WebSocket stream got an UNBOUNDED asyncio.Queue and a
   consumer that stalls or dies without unsubscribe keeps receiving EVERY later publish forever
   (events.py had put_nowait with no maxsize). That is the structural leak - fixed in events.py
   itself (Q_MAX + drop-oldest + sweep()); this janitor runs the sweep.

2. GLIBC HEAP RETENTION: Python frees memory back to glibc, but glibc keeps freed chunks in its
   per-thread arenas (the RCA saw one 1.5 GB heap arena + dozens of 64 MB arenas across 37-44
   threads) instead of giving pages back to the OS. mallopt(M_ARENA_MAX) caps how many arenas
   new threads may create (call it once at startup, before threads churn), and malloc_trim(0)
   walks ALL arenas and returns the free tops to the OS. Long tasks allocate big transient
   blocks (browser screenshots, base64, JSON) - trimming on a schedule lets RSS fall back
   after them instead of ratcheting up forever.

The janitor itself is tiny and safe: every 5 minutes it sweeps dead queues, trims the heap,
and writes ONE honest log line (RSS/swap + freed) so the next RCA can read the curve from
pm2 logs instead of guessing.
"""

from __future__ import annotations

import asyncio
import ctypes
import logging
import time

log = logging.getLogger("hoola.mem")

INTERVAL_S = 300          # 5 minutes
M_ARENA_MAX = -8          # glibc mallopt param (malloc.h)
_swapped_note = ""        # set once when swap is seen in use, so the log line says it


def _libc():
    try:
        return ctypes.CDLL("libc.so.6")
    except OSError:
        return None


def arena_cap(n: int = 2) -> bool:
    """Cap glibc per-thread arenas (M_ARENA_MAX). Call once at startup: it limits only arenas
    created AFTER the call, and threads churn constantly (37-44 at the RCA). Returns False on
    non-glibc platforms - everything here must be best-effort, never fatal."""
    libc = _libc()
    if libc is None:
        return False
    try:
        return bool(libc.mallopt(M_ARENA_MAX, n))
    except Exception:
        return False


def trim() -> bool:
    """malloc_trim(0): return free arena tops to the OS. True when pages were actually released."""
    libc = _libc()
    if libc is None:
        return False
    try:
        return bool(libc.malloc_trim(0))
    except Exception:
        return False


def rss_mb() -> dict[str, int]:
    """VmRSS / VmSwap of this process, in MB (0 when unreadable - sandbox, non-Linux)."""
    out = {"rss": 0, "swap": 0}
    try:
        with open("/proc/self/status") as f:
            for line in f:
                if line.startswith("VmRSS:"):
                    out["rss"] = int(line.split()[1]) // 1024
                elif line.startswith("VmSwap:"):
                    out["swap"] = int(line.split()[1]) // 1024
    except OSError:
        pass
    return out


async def run_forever(stop: asyncio.Event) -> None:
    """Sweep dead stream queues + trim the heap every 5 minutes until shutdown."""
    global _swapped_note
    arena_cap(2)   # idempotent, cheap, and a restart of the task re-applies it
    while not stop.is_set():
        try:
            await asyncio.wait_for(stop.wait(), timeout=INTERVAL_S)
            break   # stop set: shut down cleanly, no last trim dance
        except asyncio.TimeoutError:
            pass
        t0 = time.monotonic()
        try:
            from . import events
            swept = events.bus.sweep()
        except Exception:
            swept = -1
        freed = trim()
        m = rss_mb()
        if m["swap"] > 512 and not _swapped_note:
            _swapped_note = " (swap in use - the box is starved, expect slow turns)"
        log.info("janitor: swept=%s trim=%s rss=%sMB swap=%sMB in %.2fs%s",
                 swept, "yes" if freed else "no", m["rss"], m["swap"],
                 time.monotonic() - t0, _swapped_note)
