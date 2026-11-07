"""v0.462.x HOOLA INTERACTIVE live talk - the one route the student page needs.

POST /api/interactive/ticket {avatar_id}  ->  {address: "wss://...", ticket: "<2-minute signed pass>"}
Owner only for now (a live talk costs GPU rupees). The engine key stays on the server; the page gets a pass that works
for one avatar for two minutes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request

from ..config import get_settings
from . import lab


def router(require_key, current_tenant) -> APIRouter:
    r = APIRouter(prefix="/api/interactive", tags=["interactive"])

    @r.post("/ticket", dependencies=[Depends(require_key)])
    def ticket(request: Request, body: dict):
        if current_tenant(request) != get_settings().tenant_id:
            raise HTTPException(403, "Live talk is owner-only while it is being tested")
        try:
            avatar = str(body.get("avatar_id") or "lab-live")
            return {"address": lab.live_address(), "ticket": lab.make_ticket(avatar)}
        except lab.LabError as e:
            raise HTTPException(503, str(e))

    return r
