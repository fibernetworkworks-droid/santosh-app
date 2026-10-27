"""Home devices ("Ghar") for Santosh tenants: speaker, TV, AC on the phone; SmartThings / LG ThinQ / Home Connect clouds.

The phone carries out IR / Bluetooth / DIAL commands that the server builds (connectors/device.py) and reports back to
POST /api/bazar/devices/commands/{id}/result. Only the owner (tenant) can see or command a device or a command.
Appliance-cloud tokens are stored encrypted (security.vault); LG's personal access token is entered in the app only.
"""
from __future__ import annotations

import json
import logging
import re
import secrets
import time
from typing import Any

from sqlalchemy import select

from ..db import session
from ..events import notify
from .config import get_settings
from .connectors import device_ir as ir
from .connectors.base import Ctx, ToolError
from .connectors.device import DeviceExecutor, check_alerts, cloud_transport
from .connectors.device_cloud import PROVIDERS, Token, authorize_url, exchange_code, redirect_uri
from .db import Connection, Device, DeviceCommand, KVState, Task, User
from .packs.registry import Pack, registry

log = logging.getLogger("santosh.bazar.devices")

LOCAL_PACKS = {"speaker": "bluetooth-speaker", "tv": "smart-tv-remote", "ac": "ac-ir-remote"}
CHANNEL = {"speaker": "phone_media", "tv": "bt_hid", "ac": "ir"}
PROVIDER_PACK = {"smartthings": "samsung-smartthings", "lg_thinq": "lg-thinq", "home_connect": "bosch-home-connect"}
OAUTH_PROVIDERS = ("smartthings", "home_connect")
STATE_TTL = 15 * 60
MAC = re.compile(r"^[0-9A-Fa-f]{2}(:[0-9A-Fa-f]{2}){5}$")
PRIVATE_IP = re.compile(r"^(10|192\.168|172\.(1[6-9]|2\d|3[01]))(\.\d{1,3}){1,3}$")
HINT = {"ir": "This phone may not have an IR blaster, or it wasn't pointed at the AC.",
        "bt_hid": "The TV isn't connected to Hoola's Bluetooth remote: say 'TV ko Bluetooth se jodo' (bluetooth action=tv_pair).",
        "phone_media": "No music app or speaker responded."}


def _ctx(s, user: User) -> Ctx:
    return Ctx(s, user, None, get_settings())


def _user(s, tenant: str) -> User:
    from .service import ensure_user
    return ensure_user(s, tenant)


def _active_conn(s, uid: str, provider: str) -> Connection | None:
    return s.scalars(select(Connection).where(Connection.user_id == uid, Connection.provider == provider,
                                              Connection.status == "active")).first()


def _needs_app(provider: str) -> bool:
    """Live mode needs Santosh's own SmartThings / Home Connect app registration."""
    st = get_settings()
    if st.device_cloud_mode == "sandbox" or provider == "lg_thinq":
        return False
    return not getattr(st, f"{provider}_client_id", "")


# ---------------------------------------------------------------- catalogue status
def device_pack_status(s, user: User, pack: Pack) -> str:
    ch = pack.config.get("channel")
    if ch == "phone_media":
        return "ready"   # the phone's own audio works even without a named speaker
    if ch == "cloud":
        prov = pack.config["provider"]
        if _active_conn(s, user.id, prov):
            return "ready"
        return "not_configured" if _needs_app(prov) else "no_device"
    have = s.scalars(select(Device.id).where(Device.user_id == user.id, Device.pack_id == pack.id,
                                             Device.active.is_(True))).first()
    return "ready" if have else "no_device"


# ---------------------------------------------------------------- local devices
def _dev_out(d: Device) -> dict[str, Any]:
    out = {"id": d.id, "name": d.name, "room": d.room, "kind": d.kind, "channel": d.channel, "brand": d.brand,
           "pack_id": d.pack_id, "provider": d.provider, "protocol": d.protocol,
           "target": {k: v for k, v in (d.target or {}).items() if k in ("bt_address", "ip", "max_percent")}}
    if d.kind == "ac" and (d.state or {}).get("ac"):
        out["last_set"] = d.state["ac"]
    if d.channel == "ir":
        out["ready"] = bool(d.protocol)
    return out


def _own(s, tenant: str, did: str) -> Device:
    d = s.get(Device, did)
    if not d or not d.active or d.user_id != tenant:
        raise LookupError("Device not found")
    return d


def _clean_target(kind: str, target: dict[str, Any] | None) -> dict[str, Any]:
    t = target or {}
    out: dict[str, Any] = {}
    if kind == "tv":
        if t.get("bt_address"):
            if not MAC.match(str(t["bt_address"])):
                raise ToolError("Bluetooth address looks wrong")
            out["bt_address"] = str(t["bt_address"]).upper()
        if t.get("ip"):
            if not PRIVATE_IP.match(str(t["ip"])):
                raise ToolError("TV IP must be a home Wi-Fi address like 192.168.1.20")
            out["ip"] = str(t["ip"])
    if kind == "speaker":
        try:
            out["max_percent"] = max(10, min(90, int(t.get("max_percent", 90))))
        except (TypeError, ValueError):
            out["max_percent"] = 90
    return out


def list_devices(tenant: str) -> dict[str, Any]:
    with session() as s:
        user = _user(s, tenant)
        devs = s.scalars(select(Device).where(Device.user_id == user.id, Device.active.is_(True))
                         .order_by(Device.created_at)).all()
        links = []
        for prov, pid in PROVIDER_PACK.items():
            links.append({"provider": prov, "name": PROVIDERS[prov], "pack_id": pid,
                          "linked": _active_conn(s, user.id, prov) is not None,
                          "configured": not _needs_app(prov), "token_in_app": prov == "lg_thinq"})
        return {"devices": [_dev_out(d) for d in devs], "links": links,
                "protocols": [{"protocol": p, "label": v["label"]} for p, v in ir.PROTOCOLS.items()]}


def add_device(tenant: str, kind: str, name: str, room: str = "", brand: str = "",
               target: dict[str, Any] | None = None) -> dict[str, Any]:
    if kind not in LOCAL_PACKS:
        raise ToolError("You can add a speaker, TV or AC here. Fridges and washers come from a linked brand account.")
    name = (name or "").strip()[:80]
    if not name:
        raise ToolError("Give the device a name, e.g. 'Bedroom AC'")
    with session() as s:
        user = _user(s, tenant)
        n = s.scalars(select(Device.id).where(Device.user_id == user.id, Device.active.is_(True))).all()
        if len(n) >= 30:
            raise ToolError("You have 30 devices already; remove one first.")
        d = Device(user_id=user.id, pack_id=LOCAL_PACKS[kind], name=name, room=(room or "").strip()[:40], kind=kind,
                   channel=CHANNEL[kind], brand=(brand or "").strip()[:40], target=_clean_target(kind, target))
        if kind == "ac":
            d.state = {"ac": ir.AcState().to_dict()}
        s.add(d)
        s.flush()
        out = _dev_out(d)
        if kind == "ac":
            out["setup"] = {"try_protocols": [{"protocol": p, "label": ir.PROTOCOLS[p]["label"]} for p in ir.try_order(d.brand)],
                            "how": "Point the phone at the AC and tap Test for each remote type until the AC beeps."}
        if kind == "tv":
            out["setup"] = {"how": "Tap 'Remote test / jodiye': Hoola connects to a TV already paired with the phone, or makes "
                                   "the phone visible so the TV can add it (TV > Bluetooth > Add accessory > this phone's "
                                   "name). For YouTube/Netflix keep the phone on the same Wi-Fi as the TV."}
        return out


def remove_device(tenant: str, did: str) -> dict[str, Any]:
    with session() as s:
        d = _own(s, tenant, did)
        d.active = False
        return {"removed": did}


def ir_test(tenant: str, did: str, protocol: str) -> dict[str, Any]:
    """Builds a 'cool 24°C' signal in one remote format. The app sends it and asks the user if the AC beeped."""
    with session() as s:
        d = _own(s, tenant, did)
        if d.channel != "ir":
            raise ToolError("Not an IR device")
        return DeviceExecutor().ir_test(_ctx(s, _user(s, tenant)), d, protocol)


def ir_confirm(tenant: str, did: str, protocol: str) -> dict[str, Any]:
    if protocol not in ir.PROTOCOLS:
        raise ToolError("Unknown remote type")
    with session() as s:
        d = _own(s, tenant, did)
        if d.channel != "ir":
            raise ToolError("Not an IR device")
        d.protocol = protocol
        d.state = {**(d.state or {}), "ac": ir.AcState(True, "cool", ir.DEFAULT_TEMP_C, "auto").to_dict()}  # the test turned it on
        return {**_dev_out(d), "message": f"{d.name} is ready. Try: '{d.name} 24 pe karo' or '{d.name} band karo'."}


def tv_test(tenant: str, did: str) -> dict[str, Any]:
    """Volume up then down once: proves the TV is paired with Hoola's Bluetooth remote."""
    from .connectors import device_hid as hid
    with session() as s:
        d = _own(s, tenant, did)
        if d.channel != "bt_hid":
            raise ToolError("Not a TV")
        return DeviceExecutor()._phone(_ctx(s, _user(s, tenant)), d, [hid.key_op("VOL_UP"), {"op": "wait", "ms": 400},
                                                                    hid.key_op("VOL_DOWN")],
                                       f"Testing {d.name}: volume goes up and back down.")


def command_result(tenant: str, cid: str, ok: bool, error: str = "") -> dict[str, Any]:
    """The phone reports whether it carried out a command. IR AC state is saved only when ok=true."""
    conv = ""
    with session() as s:
        c = s.get(DeviceCommand, cid)
        if not c or c.user_id != tenant:
            raise LookupError("Command not found")
        if c.status != "sent":
            return {"id": c.id, "status": c.status}
        c.status, c.error = ("done", "") if ok else ("failed", (error or "")[:300])
        if ok and c.new_state:
            d = s.get(Device, c.device_id)
            if d and d.user_id == tenant:
                d.state = {**(d.state or {}), **c.new_state}
        hint = "" if ok else HINT.get(c.channel, "")
        if not ok and c.task_id:
            t = s.get(Task, c.task_id)
            conv = t.conversation_id if t else ""
        out = {"id": c.id, "status": c.status, "hint": hint}
    if conv:
        notify(conv, f"Ghar ka device nahi chala: {(error or 'phone ne mana kiya')[:120]}. {hint}".strip())
    return out


# ---------------------------------------------------------------- appliance clouds
def _save_connection(s, uid: str, provider: str, tok: Token) -> None:
    from .security import vault
    for c in s.scalars(select(Connection).where(Connection.user_id == uid, Connection.provider == provider)).all():
        c.status, c.token_enc = "replaced", ""
    s.add(Connection(user_id=uid, provider=provider, token_enc=vault().seal(tok.dump()), status="active"))
    s.flush()


def _sync(s, user: User, provider: str) -> dict[str, Any]:
    return DeviceExecutor().sync(_ctx(s, user), registry().get(PROVIDER_PACK[provider]))


def link_start(tenant: str, provider: str) -> dict[str, Any]:
    if provider not in PROVIDERS:
        raise LookupError("Unknown provider")
    st = get_settings()
    if provider == "lg_thinq":
        return {"provider": provider, "name": PROVIDERS[provider], "url": authorize_url(provider, st, ""), "token_in_app": True,
                "how": "Open this page, sign in to LG, create a personal access token with device permissions, "
                       "then paste it in Santosh › Ghar › LG ThinQ. Never paste it in chat."}
    state = secrets.token_urlsafe(24)
    with session() as s:
        _user(s, tenant)
        s.merge(KVState(key=f"dev_state:{state}", value=json.dumps({"uid": tenant, "provider": provider,
                                                                     "exp": time.time() + STATE_TTL})))
    if st.device_cloud_mode == "sandbox" and not getattr(st, f"{provider}_client_id", ""):
        from urllib.parse import urlencode
        url = redirect_uri(provider, st) + "?" + urlencode({"code": "sandbox", "state": state})  # dev: no real sign-in page
    else:
        url = authorize_url(provider, st, state)
    return {"provider": provider, "name": PROVIDERS[provider], "url": url, "token_in_app": False,
            "how": "Open this page, sign in and allow Santosh. You'll come back to the app automatically."}


def link_finish(provider: str, state: str, code: str) -> tuple[str, list[str]]:
    """Public OAuth callback. The state is single-use, expires in 15 min and names both the user and the provider."""
    if provider not in OAUTH_PROVIDERS:
        raise LookupError("Unknown provider")
    with session() as s:
        row = s.get(KVState, f"dev_state:{state}") if state else None
        if row is None:
            raise ToolError("This sign-in link has expired. Start again from Santosh › Ghar.")
        data = json.loads(row.value or "{}")
        s.delete(row)
    if data.get("provider") != provider or float(data.get("exp", 0)) < time.time():
        raise ToolError("This sign-in link has expired. Start again from Santosh › Ghar.")
    uid = data["uid"]
    st = get_settings()
    tok = exchange_code(provider, st, code, transport=cloud_transport(st))
    with session() as s:
        user = _user(s, uid)
        _save_connection(s, uid, provider, tok)
        try:
            names = _sync(s, user, provider)["devices"]
        except ToolError:
            names = []
    return uid, names


def link_lg(tenant: str, token: str) -> dict[str, Any]:
    token = (token or "").strip()
    if len(token) < 10 or len(token) > 4000 or any(ch.isspace() for ch in token):
        raise ToolError("That doesn't look like an LG personal access token.")
    with session() as s:
        user = _user(s, tenant)
        _save_connection(s, tenant, "lg_thinq", Token(token))
        res = _sync(s, user, "lg_thinq")   # a bad token raises -> transaction rolls back, nothing saved
        return {"linked": "lg_thinq", "devices": res["devices"], "message": res["message"]}


def unlink(tenant: str, provider: str) -> dict[str, Any]:
    if provider not in PROVIDERS:
        raise LookupError("Unknown provider")
    with session() as s:
        rows = s.scalars(select(Connection).where(Connection.user_id == tenant, Connection.provider == provider,
                                                  Connection.status == "active")).all()
        for c in rows:
            c.status, c.token_enc = "revoked", ""
        for d in s.scalars(select(Device).where(Device.user_id == tenant, Device.provider == provider,
                                                Device.active.is_(True))).all():
            d.active = False
        return {"unlinked": bool(rows)}


def sync_all(tenant: str) -> dict[str, Any]:
    with session() as s:
        user = _user(s, tenant)
        out: dict[str, Any] = {}
        for p in PROVIDER_PACK:
            if _active_conn(s, user.id, p):
                try:
                    out[p] = _sync(s, user, p)["devices"]
                except ToolError as e:
                    out[p] = {"error": str(e)}
        return out


def alerts(tenant: str) -> list[dict[str, Any]]:
    """Fridge door open / fridge warm / washing done. Each alert is returned once."""
    with session() as s:
        user = _user(s, tenant)
        return check_alerts(_ctx(s, user), registry().packs)


def alerts_tick() -> int:
    """Worker hook: only users with a linked fridge or washer are checked; each alert goes to their latest chat once."""
    from .service import latest_conversation
    with session() as s:
        uids = sorted(set(s.scalars(select(Device.user_id).where(Device.channel == "cloud", Device.active.is_(True),
                                                                 Device.kind.in_(("fridge", "washer")))).all()))
    sent = 0
    for uid in uids[:200]:
        try:
            found = alerts(uid)
        except Exception:
            log.exception("device alerts failed for a user")
            continue
        if not found:
            continue
        with session() as s:
            conv = latest_conversation(s, uid)
        if conv:
            for a in found:
                notify(conv, a["text"])
                sent += 1
    return sent
