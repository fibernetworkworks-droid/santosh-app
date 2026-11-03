"""v0.476 R5 - /api/research/*: what her research costs, and her runs. Key-protected, tenant-scoped."""
from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, HTTPException


def make_router(require_key, current_tenant) -> APIRouter:
    from . import bill, runner, store

    r = APIRouter(prefix="/api/research", dependencies=[Depends(require_key)])

    @r.get("/usage")
    async def usage(tenant: str = Depends(current_tenant)):
        """Today / this month in rupees, the ceilings and what is left, the measured cost per goal (once 3 runs exist), and - said plainly -
        which parts of every figure are assumed or unpriced."""
        return await asyncio.to_thread(bill.usage_report, tenant)

    @r.get("/runs")
    async def runs(tenant: str = Depends(current_tenant)):
        return {"runs": await asyncio.to_thread(runner.status, tenant)}

    @r.post("/runs/{run_id}/stop")
    async def stop(run_id: str, tenant: str = Depends(current_tenant)):
        got = await asyncio.to_thread(runner.stop, tenant, run_id)
        if got == "missing":
            raise HTTPException(404, "Yeh research run nahi mila.")
        return {"status": got}

    return r
