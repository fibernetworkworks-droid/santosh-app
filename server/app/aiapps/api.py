"""v0.785 HOOLA AI APPS - the owner routes (/api/aiapps/*). main.py: app.include_router(make_router(require_key,
current_tenant)).

HER taps live only here: publish {hash, note} (bound to the draft hash she looked at), restore {version}, status
{status} and delete. Every route is fenced to her tenant: another business's app id answers 404.
"""
from __future__ import annotations

import asyncio
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field


class CreateBody(BaseModel):
    name: str = ""
    kind: str = "chat"
    soul: Optional[dict[str, Any]] = None


class DraftBody(BaseModel):
    soul: dict[str, Any]


class PublishBody(BaseModel):
    hash: str = Field(..., description="the draft hash she was looking at")
    note: str = ""


class RestoreBody(BaseModel):
    version: int


class StatusBody(BaseModel):
    status: str


class ChannelsBody(BaseModel):
    page: Optional[bool] = None
    embed: Optional[bool] = None
    api: Optional[bool] = None
    mcp: Optional[bool] = None
    whatsapp: Optional[str] = None


class PreviewBody(BaseModel):
    text: str = ""
    inputs: Optional[dict[str, Any]] = None
    session_id: str = ""


class CorrectBody(BaseModel):
    answer: str


def make_router(require_key, current_tenant) -> APIRouter:
    from . import ops as OP
    from . import runtime as RT
    from . import store as ST
    from .models import AiAppSession

    r = APIRouter(prefix="/api/aiapps", dependencies=[Depends(require_key)])

    async def run(fn, *a, **k):
        try:
            return await asyncio.to_thread(fn, *a, **k)
        except ST.AppError as e:
            raise HTTPException(e.code, str(e))

    @r.get("")
    async def list_apps(tenant: str = Depends(current_tenant)):
        return {"apps": await run(ST.apps, tenant)}

    @r.post("")
    async def create(body: CreateBody, tenant: str = Depends(current_tenant)):
        return await run(ST.create, tenant, body.name, body.kind, body.soul, "blank")

    @r.get("/{ref}")
    async def get_app(ref: str, tenant: str = Depends(current_tenant)):
        return await run(ST.get, tenant, ref)

    @r.put("/{ref}/draft")
    async def draft(ref: str, body: DraftBody, tenant: str = Depends(current_tenant)):
        return await run(ST.save_draft, tenant, ref, body.soul)

    @r.post("/{ref}/publish")
    async def publish(ref: str, body: PublishBody, tenant: str = Depends(current_tenant)):
        return await run(ST.publish, tenant, ref, body.hash, body.note, "owner")

    @r.get("/{ref}/versions")
    async def versions(ref: str, tenant: str = Depends(current_tenant)):
        return {"versions": await run(ST.versions, tenant, ref)}

    @r.post("/{ref}/restore")
    async def restore(ref: str, body: RestoreBody, tenant: str = Depends(current_tenant)):
        return await run(ST.restore, tenant, ref, body.version, "owner")

    @r.post("/{ref}/status")
    async def status(ref: str, body: StatusBody, tenant: str = Depends(current_tenant)):
        return await run(ST.set_status, tenant, ref, body.status)

    @r.post("/{ref}/channels")
    async def channels(ref: str, body: ChannelsBody, tenant: str = Depends(current_tenant)):
        kw = {k: v for k, v in body.model_dump(exclude_unset=True).items() if v is not None}
        return await run(ST.set_channels, tenant, ref, **kw)

    @r.delete("/{ref}")
    async def delete(ref: str, tenant: str = Depends(current_tenant)):
        def go():
            a = ST.row(tenant, ref)
            out = ST.delete(tenant, ref)
            try:
                OP.forget_alerts(a.id)
            except Exception:                           # noqa: BLE001
                pass
            return out
        return await run(go)

    @r.post("/{ref}/preview")
    async def preview(ref: str, body: PreviewBody, tenant: str = Depends(current_tenant)):
        """Her own test chat on the DRAFT soul (channel preview): the public keeps the live version meanwhile."""
        def go():
            a = ST.row(tenant, ref)
            sid = (body.session_id or "").strip()
            if sid:
                from ..db import session
                with session() as s:
                    x = s.get(AiAppSession, sid)
                    if x is None or x.app_id != a.id or x.channel != "preview":
                        raise ST.AppError("That preview chat was not found; start a new one.", 404)
            else:
                sid, _tok = RT.open_session(a, "preview", visitor="owner", consent=True)
            out = RT.answer(a, body.text, channel="preview", session_id=sid, inputs=body.inputs, use_draft=True)
            return {**out, "session_id": sid}
        return await run(go)

    # ---- D3: run & improve
    @r.get("/{ref}/logs")
    async def logs(ref: str, outcome: str = "", q: str = "", limit: int = 100, channel: str = "",
                   tenant: str = Depends(current_tenant)):
        return {"logs": await run(OP.logs, tenant, ref, outcome, q, limit, channel)}

    @r.post("/{ref}/logs/{mid}/correct")
    async def correct(ref: str, mid: str, body: CorrectBody, tenant: str = Depends(current_tenant)):
        return await run(OP.correct, tenant, ref, mid, body.answer)

    @r.get("/{ref}/stats")
    async def stats(ref: str, days: int = 7, tenant: str = Depends(current_tenant)):
        return await run(OP.stats, tenant, ref, days)

    @r.get("/{ref}/gaps")
    async def gaps(ref: str, days: int = 30, tenant: str = Depends(current_tenant)):
        return {"gaps": await run(OP.gaps, tenant, ref, days)}

    return r
