"""Home devices API (v0.3): add devices, confirm the AC remote, phone command results, link appliance clouds, alerts."""
from __future__ import annotations

import hashlib
import hmac
import secrets
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..connectors import device_ir as ir
from ..connectors.base import Ctx, ToolError
from ..connectors.device import DeviceExecutor, check_alerts, cloud_transport
from ..connectors.device_cloud import PROVIDERS, Token, authorize_url, exchange_code
from ..db import Connection, Device, DeviceCommand, User, get_session
from ..packs.registry import registry
from ..security import vault

router = APIRouter(tags=["devices"])          # mounted with the API token
public = APIRouter(tags=["devices"])          # OAuth browser redirects

LOCAL_PACKS = {"speaker": "bluetooth-speaker", "tv": "smart-tv-remote", "ac": "ac-ir-remote"}
PROVIDER_PACK = {"smartthings": "samsung-smartthings", "lg_thinq": "lg-thinq", "home_connect": "bosch-home-connect"}


class DeviceIn(BaseModel):
    kind: Literal["speaker", "tv", "ac"]
    name: str = Field(min_length=1, max_length=80)
    room: str = ""
    brand: str = ""
    target: dict[str, Any] = {}   # tv: {"bt_address": "AA:BB:..", "ip": "192.168.1.20"}; speaker: {"max_percent": 90}


class ProtocolIn(BaseModel):
    protocol: str


class ResultIn(BaseModel):
    ok: bool
    error: str = ""


class PatIn(BaseModel):
    token: str = Field(min_length=10)


def _user(s: Session, uid: str) -> User:
    u = s.get(User, uid)
    if not u:
        raise HTTPException(404, "User not found")
    return u


def _ctx(s: Session, u: User) -> Ctx:
    return Ctx(s, u, None, get_settings())


def _dev_out(d: Device) -> dict[str, Any]:
    out = {"id": d.id, "name": d.name, "room": d.room, "kind": d.kind, "channel": d.channel, "brand": d.brand,
           "pack_id": d.pack_id, "provider": d.provider, "protocol": d.protocol, "target": d.target}
    if d.kind == "ac" and d.state.get("ac"):
        out["last_set"] = d.state["ac"]
    return out


def _own_device(s: Session, did: str) -> Device:
    d = s.get(Device, did)
    if not d or not d.active:
        raise HTTPException(404, "Device not found")
    return d


# ------------------------------------------------------------------ local devices (phone routes)
@router.post("/v1/users/{uid}/devices")
def add_device(uid: str, body: DeviceIn, s: Session = Depends(get_session)):
    _user(s, uid)
    channel = {"speaker": "phone_media", "tv": "bt_hid", "ac": "ir"}[body.kind]
    d = Device(user_id=uid, pack_id=LOCAL_PACKS[body.kind], name=body.name.strip(), room=body.room.strip(), kind=body.kind,
               channel=channel, brand=body.brand.strip(), target=body.target)
    if body.kind == "ac":
        d.state = {"ac": ir.AcState().to_dict()}
    s.add(d)
    s.commit()
    out = _dev_out(d)
    if body.kind == "ac":
        out["setup"] = {"try_protocols": [{"protocol": p, "label": ir.PROTOCOLS[p]["label"]} for p in ir.try_order(body.brand)],
                        "how": "POST /v1/devices/{id}/ir-test for each protocol until the AC beeps, then /ir-confirm."}
    if body.kind == "tv":
        out["setup"] = {"how": "Open the TV's Bluetooth settings and pair 'Santosh Remote' from the phone app. "
                               "For YouTube/Netflix keep the phone on the same Wi-Fi as the TV."}
    return out


@router.get("/v1/users/{uid}/devices")
def list_devices(uid: str, s: Session = Depends(get_session)):
    _user(s, uid)
    return [_dev_out(d) for d in s.scalars(select(Device).where(Device.user_id == uid, Device.active.is_(True))
                                            .order_by(Device.created_at)).all()]


@router.delete("/v1/users/{uid}/devices/{did}")
def remove_device(uid: str, did: str, s: Session = Depends(get_session)):
    d = _own_device(s, did)
    if d.user_id != uid:
        raise HTTPException(404, "Device not found")
    d.active = False
    s.commit()
    return {"removed": did}


@router.post("/v1/devices/{did}/ir-test")
def ir_test(did: str, body: ProtocolIn, s: Session = Depends(get_session)):
    d = _own_device(s, did)
    if d.channel != "ir":
        raise HTTPException(400, "Not an IR device")
    out = DeviceExecutor().ir_test(_ctx(s, s.get(User, d.user_id)), d, body.protocol)
    s.commit()
    return out


@router.post("/v1/devices/{did}/ir-confirm")
def ir_confirm(did: str, body: ProtocolIn, s: Session = Depends(get_session)):
    d = _own_device(s, did)
    if body.protocol not in ir.PROTOCOLS:
        raise HTTPException(400, "Unknown remote type")
    d.protocol = body.protocol
    d.state = {**d.state, "ac": ir.AcState(True, "cool", ir.DEFAULT_TEMP_C, "auto").to_dict()}  # the test turned it on
    s.commit()
    return {**_dev_out(d), "message": f"{d.name} is ready. Try: '{d.name} 24 pe karo' or '{d.name} band karo'."}


@router.post("/v1/device-commands/{cid}/result")
def command_result(cid: str, body: ResultIn, s: Session = Depends(get_session)):
    """The phone reports whether it carried out a command. IR AC state is saved only when ok=true."""
    c = s.get(DeviceCommand, cid)
    if not c:
        raise HTTPException(404, "Command not found")
    if c.status != "sent":
        return {"id": c.id, "status": c.status}
    c.status, c.error = ("done", "") if body.ok else ("failed", body.error[:300])
    if body.ok and c.new_state:
        d = s.get(Device, c.device_id)
        if d:
            d.state = {**d.state, **c.new_state}
    s.commit()
    hint = ""
    if not body.ok:
        hint = {"ir": "This phone may not have an IR blaster, or it wasn't pointed at the AC.",
                "bt_hid": "The TV isn't connected to 'Santosh Remote' — check the TV's Bluetooth.",
                "phone_media": "No music app or speaker responded."}.get(c.channel, "")
    return {"id": c.id, "status": c.status, "hint": hint}


# ------------------------------------------------------------------ appliance clouds
def _state_token(uid: str, provider: str) -> str:
    nonce = secrets.token_urlsafe(8)
    key = (get_settings().secret_key or get_settings().webhook_secret or "dev-state-key").encode()
    sig = hmac.new(key, f"{uid}.{provider}.{nonce}".encode(), hashlib.sha256).hexdigest()[:24]
    return f"{uid}.{nonce}.{sig}"


def _check_state(state: str, provider: str) -> str:
    try:
        uid, nonce, sig = state.split(".")
    except ValueError as e:
        raise HTTPException(400, "Bad state") from e
    key = (get_settings().secret_key or get_settings().webhook_secret or "dev-state-key").encode()
    good = hmac.new(key, f"{uid}.{provider}.{nonce}".encode(), hashlib.sha256).hexdigest()[:24]
    if not hmac.compare_digest(sig, good):
        raise HTTPException(400, "Bad state")
    return uid


def _save_connection(s: Session, uid: str, provider: str, tok: Token) -> None:
    for c in s.scalars(select(Connection).where(Connection.user_id == uid, Connection.provider == provider)).all():
        c.status = "replaced"
    s.add(Connection(user_id=uid, provider=provider, token_enc=vault().seal(tok.dump()), status="active"))
    s.flush()


def _sync(s: Session, u: User, provider: str) -> dict[str, Any]:
    pack = registry().get(PROVIDER_PACK[provider])
    return DeviceExecutor().sync(_ctx(s, u), pack)


@router.get("/v1/users/{uid}/devices/link/{provider}")
def link_start(uid: str, provider: str):
    if provider not in PROVIDERS:
        raise HTTPException(404, "Unknown provider")
    st = get_settings()
    url = authorize_url(provider, st, _state_token(uid, provider)) if provider != "lg_thinq" else authorize_url(provider, st, "")
    how = ("Open this page, sign in to LG, create a personal access token with device permissions, then paste it in Santosh."
           if provider == "lg_thinq" else "Open this page, sign in and allow Santosh. You'll come back to the app automatically.")
    return {"provider": provider, "name": PROVIDERS[provider], "url": url, "how": how}


@router.post("/v1/users/{uid}/devices/link/lg_thinq")
def link_lg(uid: str, body: PatIn, s: Session = Depends(get_session)):
    u = _user(s, uid)
    _save_connection(s, uid, "lg_thinq", Token(body.token.strip()))
    try:
        res = _sync(s, u, "lg_thinq")
    except ToolError:
        s.rollback()
        raise
    s.commit()
    return {"linked": "lg_thinq", **res}


@public.get("/v1/oauth/callback/{provider}", response_class=HTMLResponse)
def oauth_callback(provider: str, code: str = "", state: str = "", error: str = "", s: Session = Depends(get_session)):
    if provider not in ("smartthings", "home_connect"):
        raise HTTPException(404, "Unknown provider")
    if error or not code:
        return HTMLResponse(f"<h3>{PROVIDERS[provider]} was not linked.</h3><p>You can close this page.</p>", status_code=400)
    uid = _check_state(state, provider)
    u = _user(s, uid)
    tok = exchange_code(provider, get_settings(), code, transport=cloud_transport(get_settings()))
    _save_connection(s, uid, provider, tok)
    res = _sync(s, u, provider)
    s.commit()
    names = ", ".join(res["devices"]) or "no supported appliances yet"
    return HTMLResponse(f"<h3>{PROVIDERS[provider]} linked to Santosh.</h3><p>Found: {names}.</p><p>You can go back to the app.</p>")


@router.post("/v1/users/{uid}/devices/sync")
def sync_all(uid: str, s: Session = Depends(get_session)):
    u = _user(s, uid)
    provs = set(s.scalars(select(Connection.provider).where(Connection.user_id == uid, Connection.status == "active")).all())
    out = {p: _sync(s, u, p)["devices"] for p in PROVIDER_PACK if p in provs}
    s.commit()
    return out


@router.get("/v1/users/{uid}/devices/alerts")
def alerts(uid: str, s: Session = Depends(get_session)):
    """Polled by the notification worker: fridge door open / fridge warm / washing done. Each alert is returned once."""
    u = _user(s, uid)
    out = check_alerts(_ctx(s, u), registry().packs)
    s.commit()
    return out
