"""D0 THE PC CARD - owner-only routes (/api/quality/pccard*). main.py:
app.include_router(make_router(require_key, current_tenant)).

GET  /api/quality/pccard       the 40 tasks + the last saved card + the history + the running status
POST /api/quality/pccard/run   {pc, ids?, confirm_not_her_pc?, skip_needs?, budget_minutes?, label?} -> starts in the
                               background and returns at once (the run drives a real PC for many minutes)
POST /api/quality/pccard/stop  stops the running card (the current task stops at once, nothing more starts)"""
from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

log = logging.getLogger("santosh.pccard")
_TASK: dict[str, asyncio.Task] = {}


class RunBody(BaseModel):
    pc: str = Field(default="", max_length=120)
    ids: list[str] | None = None
    confirm_not_her_pc: bool = False
    skip_needs: list[str] | None = None
    budget_minutes: float = Field(default=240, ge=1, le=720)
    label: str = Field(default="", max_length=80)


def _owner(tenant: str) -> None:
    from ..config import get_settings
    if tenant != get_settings().tenant_id:
        raise HTTPException(403, "The PC card is only for the Hoola owner.")


def make_router(require_key, current_tenant) -> APIRouter:
    from . import pccard as PC
    from .pccard_tasks import SET_V, TASKS

    r = APIRouter(prefix="/api/quality/pccard", dependencies=[Depends(require_key)])

    @r.get("")
    async def overview(tenant: str = Depends(current_tenant)):
        _owner(tenant)
        last = await asyncio.to_thread(PC.last)
        return {"set": SET_V, "tasks": [{k: t[k] for k in ("id", "group", "ask", "max_minutes")}
                                        | ({"needs": t["needs"]} if t.get("needs") else {}) for t in TASKS],
                "running": dict(PC.STATUS), "last": last, "lines": PC.lines(last) if last else [],
                "saved": await asyncio.to_thread(PC.saved)}

    @r.post("/run")
    async def run(body: RunBody, tenant: str = Depends(current_tenant)):
        _owner(tenant)
        if PC.running():
            raise HTTPException(409, "A PC card is already running.")
        try:
            PC.guard(tenant, body.pc, body.confirm_not_her_pc)   # refuse here, not silently in the background
        except ValueError as e:
            raise HTTPException(400, str(e))

        async def _go():
            try:
                await PC.run_card(tenant, body.pc, ids=body.ids, budget_minutes=body.budget_minutes,
                                  confirm_not_her_pc=body.confirm_not_her_pc, skip_needs=body.skip_needs,
                                  label=body.label)
            except Exception as e:
                log.warning("pc card run failed: %s", e)
                PC.STATUS.update(running=False, error=str(e)[:300])

        _TASK["run"] = asyncio.create_task(_go())
        return {"started": True, "pc": body.pc, "tasks": len(body.ids or TASKS)}

    @r.post("/stop")
    async def stop(tenant: str = Depends(current_tenant)):
        _owner(tenant)
        return {"stopped": PC.request_stop()}

    return r
