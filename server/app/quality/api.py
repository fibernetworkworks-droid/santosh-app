"""HTTP routes of the quality scorecard (/api/quality/*). main.py: app.include_router(make_router(require_key)).

Read-only plus the FREE card (no model, no keys): the live run costs real model calls and minutes, so it stays a
command on the VPS - `python -m app.quality --live` - and this only shows what it saved."""
from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, HTTPException


def make_router(require_key) -> APIRouter:
    from . import run as R
    from .asks import ASKS, SET_V, turns_of

    r = APIRouter(prefix="/api/quality", dependencies=[Depends(require_key)])

    @r.get("")
    async def overview():
        snaps = await asyncio.to_thread(R.snapshots)
        newest = None
        if snaps:
            try:
                newest = await asyncio.to_thread(R.load, snaps[0]["file"])
            except Exception:
                newest = None
        return {"set": SET_V, "asks": len(ASKS), "snapshots": snaps[:30],
                "newest": newest, "lines": R.lines(newest) if newest else [],
                "how": "live run: python -m app.quality --live   |   compare: python -m app.quality compare a.json b.json"}

    @r.get("/asks")
    async def asks():
        return {"set": SET_V, "asks": [{"id": a["id"], "kind": a["kind"], "turns": turns_of(a),
                                        "band": list(a.get("band", ())), "want": a.get("want", [])} for a in ASKS]}

    @r.get("/tools")
    async def tools():
        """v0.245 tool choice: the free router card now + the saved live cards (python -m app.quality tools --live)."""
        from . import toolchoice as T
        card = await asyncio.to_thread(T.router_card)
        return {"router": {k: v for k, v in card.items() if k != "rows"}, "lines": T.lines(card),
                "saved": await asyncio.to_thread(T.saved),
                "how": "live: python -m app.quality tools --live   (one model call per ask, nothing is run)"}

    @r.get("/report/{name}")
    async def report(name: str):
        try:
            snap = await asyncio.to_thread(R.load, name)
        except Exception:
            raise HTTPException(404, "not found")
        return {"snapshot": snap, "lines": R.lines(snap)}

    @r.post("/pipeline")
    async def pipeline(label: str = ""):
        snap = await R.snapshot(live=False, label=label)      # pure CPU + one small file write
        return {"snapshot": snap, "lines": R.lines(snap)}

    @r.get("/compare")
    async def compare(before: str, after: str):
        try:
            a, b = await asyncio.to_thread(R.load, before), await asyncio.to_thread(R.load, after)
        except Exception:
            raise HTTPException(404, "not found")
        return R.compare(a, b)

    return r
