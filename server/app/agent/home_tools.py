"""v0.479.0 HOOLA SMART HOME tools — Santosh ghar ke devices chalata hai, Home Assistant ke official REST API se.

Purely additive, server-only: reads (link status, devices, state) gate-free hain par link ke bina kabhi
nahi chalte; CONTROLS (home_on/home_off) `home_control` gate ke peeche hain — the HOME gate, PC se alag —
OFF rahe to ek saaf line dete hain. Token VPS .env mein (zoo BYOK pattern) — kabhi chat mein, kabhi model
ko wapas nahi. Frozen-brief guards app/home.py mein executable hain: AC 20–28 °C, volume <= 90 %, fridge /
washer / geyser read-only, locks confirm-only (routine se kabhi nahi). Har koshish home_audit mein likhi
jaati hai. Routines mein bhi yeh tools chalte hain (routine turns the same surface ride karte hain) —
"raat 11 baje saari lights band" ka routine isliye turant kaam karta hai; locks us raaste se hamesha refuse.
"""
from __future__ import annotations

from typing import Any

from .. import home
from .tools import Ctx, ToolError

HOME_TOOLS = [
    {"name": "home_link", "description": (
        "[HOME] Home Assistant link status, and the full setup guide when not linked. Without any call it "
        "tells: whether home control is ON (home_control switch), whether the HA URL is set, and shows the token "
        "masked. The owner does setup in the VPS .env (HOME_ASSISTANT_URL + "
        "HOME_ASSISTANT_TOKEN) - never ask for the token in chat."),
     "input_schema": {"type": "object", "properties": {}}},
    {"name": "home_devices", "description": (
        "[HOME] Home Assistant devices: name, entity_id, domain, state (on/off, temperature, brightness...). "
        "Ask this first to match a name like 'drawing room light' to an entity. Filter with domain=light|switch|"
        "fan|cover|media_player|climate|scene|script|button, search by name with q. With many devices "
        "narrow down with q/domain."),
     "input_schema": {"type": "object", "properties": {
         "domain": {"type": "string", "description": "only devices of this domain"},
         "q": {"type": "string", "description": "search in name or entity_id"},
         "limit": {"type": "number"}}},
     },
    {"name": "home_on", "description": (
        "[HOME] Turn ONE device ON (light/fan/switch/scene/script/button; cover=open; give climate a temperature; "
        "lock=lock, ONLY after asking the user, with confirm=true). extra: light brightness (1-255), "
        "climate temperature (20-28, outside it is refused), media volume_level (0.0-1.0, clamped above 90 %). "
        "Never operates a fridge / washing machine / geyser / heater. The answer has a 'say' line."),
     "input_schema": {"type": "object", "properties": {
         "entity": {"type": "string", "description": "entity_id (light.hall) or the device name"},
         "confirm": {"type": "boolean", "description": "for locks: true only after the user said yes"},
         "extra": {"type": "object", "description": "brightness / temperature / volume_level"}},
         "required": ["entity"]}},
    {"name": "home_off", "description": (
        "[HOME] Turn ONE device OFF (light/fan/switch; cover=close; climate off = HVAC off; unlock ONLY "
        "after asking the user, with confirm=true). Never operates a fridge / washing machine / geyser / heater. "
        "The answer has a 'say' line."),
     "input_schema": {"type": "object", "properties": {
         "entity": {"type": "string"},
         "confirm": {"type": "boolean", "description": "for locks only"}},
         "required": ["entity"]}},
    {"name": "home_state", "description": (
        "[HOME] Current state of one device (state, temperature, humidity, brightness...). Either entity_id or name "
        "works. Sensors are read with this too - do not try to control them."),
     "input_schema": {"type": "object", "properties": {"entity": {"type": "string"}}, "required": ["entity"]}},
]

HOME_LABELS = {
    "home_link": "Ghar ka link dekh raha hoon",
    "home_devices": "Ghar ke devices dekh raha hoon",
    "home_on": "Ghar ka device chala raha hoon",
    "home_off": "Ghar ka device band kar raha hoon",
    "home_state": "Ghar ka device padh raha hoon",
}


def _gate_or_none() -> str:
    """'' when the HOME gate is on, else the refusal line (checked once, before anything else)."""
    from ..config import get_settings
    return "" if get_settings().home_control else home.GATE_OFF


async def home_link(ctx: Ctx) -> dict:
    gate = _gate_or_none()
    st = home.link_status()
    out = {"gate_on": not gate, "gate_note": gate or ("Home control is ON."), **st}
    if not st.get("linked"):
        out["say"] = "The home is not linked yet. I can explain the setup steps."
    elif gate:
        out["say"] = "The link is set, but the home_control switch is OFF - the owner should set HOME_CONTROL=1 in the VPS .env."
    else:
        ping = await home.ping()
        out["connected"] = ping.get("ok", False)
        out["say"] = ("The home is linked and Home Assistant is answering." if ping.get("ok")
                      else f"The link is set but HA could not be reached: {ping.get('why', 'no reason found')}")
    return out


async def home_devices(ctx: Ctx, domain: str = "", q: str = "", limit: int = 200, **_: Any) -> dict:
    r = await home.states(domain=domain, q=q, limit=limit)   # reads are gate-free; the gate guards switching
    if not r.get("ok"):
        raise ToolError(r.get("why", "Could not get devices from HA."))
    r["say"] = f"Found {r.get('count', 0)} device(s)." if r.get("count") else "No device found for this name/domain."
    return r


async def home_on(ctx: Ctx, entity: str, confirm: bool = False, extra: dict | None = None, **_: Any) -> dict:
    # no pre-gate here: home.switch() gates FIRST and audits the attempt - one gate, one audit place
    r = await home.switch(entity, True, ctx.tenant_id, ctx.conversation_id, actor=ctx.actor,
                          confirm=confirm, extra=extra)
    if not r.get("ok"):
        raise ToolError(r.get("why", "Could not turn it on."))
    return r


async def home_off(ctx: Ctx, entity: str, confirm: bool = False, **_: Any) -> dict:
    r = await home.switch(entity, False, ctx.tenant_id, ctx.conversation_id, actor=ctx.actor,
                          confirm=confirm, extra=None)
    if not r.get("ok"):
        raise ToolError(r.get("why", "Could not turn it off."))
    return r


async def home_state(ctx: Ctx, entity: str, **_: Any) -> dict:
    r = await home.state_one(entity)
    if not r.get("ok"):
        raise ToolError(r.get("why", "Could not get the device state."))
    return r


HOME_HANDLERS = {"home_link": home_link, "home_devices": home_devices, "home_on": home_on,
                 "home_off": home_off, "home_state": home_state}
