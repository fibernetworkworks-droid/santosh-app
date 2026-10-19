"""Home devices ("Ghar") routes for the Santosh app.

Mounted from app.main:
  router  -> /api/bazar/devices/...  (API key / signed-in session; the tenant comes from current_tenant)
  public  -> /bazar/devices/callback/{provider}  (OAuth redirect from SmartThings / Home Connect)
"""
from __future__ import annotations

import asyncio
from html import escape
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from .. import devices as svc
from ..connectors.base import ToolError

router = APIRouter(prefix="/api/bazar/devices", tags=["devices"])
public = APIRouter(tags=["devices"])


def _tenant(request: Request) -> str:
    from ...main import current_tenant   # resolved at request time (main imports this module)
    return current_tenant(request)


def _call(fn, *a):
    try:
        return fn(*a)
    except ToolError as e:
        raise HTTPException(400, str(e))
    except LookupError as e:
        raise HTTPException(404, str(e).strip("'\""))


class DeviceIn(BaseModel):
    kind: Literal["speaker", "tv", "ac"]
    name: str = Field(min_length=1, max_length=80)
    room: str = Field("", max_length=40)
    brand: str = Field("", max_length=40)
    target: dict[str, Any] = {}   # tv: {"bt_address": "AA:BB:..", "ip": "192.168.1.20"}; speaker: {"max_percent": 90}


class ProtocolIn(BaseModel):
    protocol: str = Field(max_length=30)


class ResultIn(BaseModel):
    ok: bool
    error: str = Field("", max_length=500)


class PatIn(BaseModel):
    token: str = Field(min_length=10, max_length=4000)


@router.get("")
def list_devices(tenant: str = Depends(_tenant)):
    return svc.list_devices(tenant)


@router.post("")
def add_device(body: DeviceIn, tenant: str = Depends(_tenant)):
    return _call(svc.add_device, tenant, body.kind, body.name, body.room, body.brand, body.target)


@router.delete("/{did}")
def remove_device(did: str, tenant: str = Depends(_tenant)):
    return _call(svc.remove_device, tenant, did)


@router.post("/{did}/ir-test")
def ir_test(did: str, body: ProtocolIn, tenant: str = Depends(_tenant)):
    return _call(svc.ir_test, tenant, did, body.protocol)


@router.post("/{did}/ir-confirm")
def ir_confirm(did: str, body: ProtocolIn, tenant: str = Depends(_tenant)):
    return _call(svc.ir_confirm, tenant, did, body.protocol)


@router.post("/{did}/tv-test")
def tv_test(did: str, tenant: str = Depends(_tenant)):
    return _call(svc.tv_test, tenant, did)


@router.post("/commands/{cid}/result")
def command_result(cid: str, body: ResultIn, tenant: str = Depends(_tenant)):
    return _call(svc.command_result, tenant, cid, body.ok, body.error)


@router.post("/link/lg_thinq")
async def link_lg(body: PatIn, tenant: str = Depends(_tenant)):
    return await asyncio.to_thread(_call, svc.link_lg, tenant, body.token)


@router.post("/link/{provider}")
async def link_start(provider: str, tenant: str = Depends(_tenant)):
    return await asyncio.to_thread(_call, svc.link_start, tenant, provider)


@router.delete("/link/{provider}")
def unlink(provider: str, tenant: str = Depends(_tenant)):
    return _call(svc.unlink, tenant, provider)


@router.post("/sync")
async def sync_all(tenant: str = Depends(_tenant)):
    return await asyncio.to_thread(_call, svc.sync_all, tenant)


@router.get("/alerts")
async def alerts(tenant: str = Depends(_tenant)):
    return {"alerts": await asyncio.to_thread(_call, svc.alerts, tenant)}


@public.get("/bazar/devices/callback/{provider}", response_class=HTMLResponse)
async def oauth_callback(provider: str, code: str = "", state: str = "", error: str = ""):
    from ...config import get_settings as core_settings
    scheme = core_settings().app_redirect_scheme
    if provider not in svc.OAUTH_PROVIDERS:
        raise HTTPException(404, "Unknown provider")
    name = svc.PROVIDERS[provider]
    status = 200
    if error or not code:
        msg, ok, status = f"{name} was not linked ({escape(error or 'cancelled')}).", False, 400
    else:
        try:
            _, names = await asyncio.to_thread(svc.link_finish, provider, state, code)
            msg, ok = f"{name} linked to Santosh. Found: {escape(', '.join(names) or 'no supported appliances yet')}.", True
        except ToolError as e:
            msg, ok, status = escape(str(e)), False, 400
    link = f"{scheme}://bazar?linked={'1' if ok else '0'}&ghar=1"
    return HTMLResponse(f"""<!doctype html><meta name=viewport content="width=device-width,initial-scale=1">
<body style="font-family:sans-serif;padding:32px;text-align:center"><h2>{'✅' if ok else '⚠️'} {msg}</h2>
<p><a href="{link}" style="font-size:18px">Back to Santosh</a></p><script>setTimeout(()=>location.href="{link}",1200)</script>""",
                        status_code=status)
