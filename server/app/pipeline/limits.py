"""P4 CALLS AT ONCE (plan 6.8): a cap per user and a cap per company, each company with its own queue, so Hoola never
runs into a company's rate limit and one person never takes every slot. A call waits its turn (first come, first
served) instead of being sent and refused. Per server process (one pm2 process today)."""
from __future__ import annotations

import asyncio
import contextlib
import time
from typing import AsyncIterator

from ..config import get_settings

_SEMS: dict[tuple[int, str], asyncio.Semaphore] = {}
STATS = {"waited": 0, "wait_s": 0.0, "running": 0}


def _cap(kind: str) -> int:
    st = get_settings()
    if kind == "user":
        return max(1, int(getattr(st, "pipeline_user_cap", 6) or 6))
    return max(1, int(getattr(st, "pipeline_company_cap", 8) or 8))


def _sem(key: str, cap: int) -> asyncio.Semaphore:
    k = (id(asyncio.get_running_loop()), key)   # a semaphore belongs to one event loop
    s = _SEMS.get(k)
    if s is None:
        s = _SEMS[k] = asyncio.Semaphore(cap)
    return s


def company_of(model_id: str) -> str:
    return str(model_id or "").split("/", 1)[0] or "unknown"


@contextlib.asynccontextmanager
async def slot(tenant: str, model_id: str) -> AsyncIterator[float]:
    """Hold one user slot and one company slot for one model call. Yields how long the call waited."""
    t0 = time.monotonic()
    u = _sem("user:" + str(tenant or "-"), _cap("user"))
    c = _sem("co:" + company_of(model_id), _cap("company"))
    async with u:
        async with c:
            waited = time.monotonic() - t0
            if waited > 0.05:
                STATS["waited"] += 1
                STATS["wait_s"] = round(STATS["wait_s"] + waited, 2)
            STATS["running"] += 1
            try:
                yield waited
            finally:
                STATS["running"] -= 1
