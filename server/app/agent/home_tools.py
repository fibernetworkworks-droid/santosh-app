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
        "[GHAR] Home Assistant link ka status, aur jab juda na ho to poori setup guide. Bina koi call ke "
        "bata deta hai: ghar ka control ON hai ya nahi (home_control switch), HA URL set hai ya nahi, token "
        "mask hone ke baad dikhata hai. Setup owner VPS .env mein karta hai (HOME_ASSISTANT_URL + "
        "HOME_ASSISTANT_TOKEN) - token chat mein kabhi mat maango."),
     "input_schema": {"type": "object", "properties": {}}},
    {"name": "home_devices", "description": (
        "[GHAR] Home Assistant ke devices: naam, entity_id, domain, state (on/off, temperature, brightness...). "
        "'drawing room ki light' jaise naam ko entity se milane ke liye pehle yehi poochein. domain=light|switch|"
        "fan|cover|media_player|climate|scene|script|button se filter, q=naam se search. Bahut saare devices "
        "ho to q/domain se seedha karein."),
     "input_schema": {"type": "object", "properties": {
         "domain": {"type": "string", "description": "sirf isi domain ke devices"},
         "q": {"type": "string", "description": "naam ya entity_id mein search"},
         "limit": {"type": "number"}}},
     },
    {"name": "home_on", "description": (
        "[GHAR] Ek device ON (light/fan/switch/scene/script/button/cover=kholna; climate ko temperature do; "
        "lock=band karna, SIRF user se poochne ke baad confirm=true). extra mein light brightness (1-255), "
        "climate temperature (20-28, isse bahar refuse), media volume_level (0.0-1.0, 90 % se upar clamp). "
        "Fridge / washing machine / geyser / heater main kabhi nahi chalata. Jawab mein Hinglish 'say' aata hai."),
     "input_schema": {"type": "object", "properties": {
         "entity": {"type": "string", "description": "entity_id (light.hall) ya device ka naam"},
         "confirm": {"type": "boolean", "description": "locks ke liye: user ne kaha 'haan' tab hi true"},
         "extra": {"type": "object", "description": "brightness / temperature / volume_level"}},
         "required": ["entity"]}},
    {"name": "home_off", "description": (
        "[GHAR] Ek device OFF (light/fan/switch/cover=band karna; climate off = HVAC off; lock kholna SIRF "
        "user se poochne ke baad confirm=true). Fridge / washing machine / geyser / heater main kabhi nahi "
        "chalata. Jawab mein Hinglish 'say' aata hai."),
     "input_schema": {"type": "object", "properties": {
         "entity": {"type": "string"},
         "confirm": {"type": "boolean", "description": "locks ke liye hi"}},
         "required": ["entity"]}},
    {"name": "home_state", "description": (
        "[GHAR] Ek device ka abhi ka haal (state, temperature, humidity, brightness...). entity_id ya naam "
        "dono chalte hain. Sensors bhi isse padhe jaate hain - unhe control karne ki koshish mat karo."),
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
    out = {"gate_on": not gate, "gate_note": gate or ("Ghar ka control ON hai."), **st}
    if not st.get("linked"):
        out["say"] = "Ghar abhi juda nahi hai. Setup steps bata deta hoon."
    elif gate:
        out["say"] = "Link juda hua hai, par home_control switch OFF hai - owner VPS .env mein HOME_CONTROL=1 karein."
    else:
        ping = await home.ping()
        out["connected"] = ping.get("ok", False)
        out["say"] = ("Ghar juda hua hai aur Home Assistant jawab de raha hai." if ping.get("ok")
                      else f"Link set hai par HA tak pahunch nahi: {ping.get('why', 'wajah nahi mili')}")
    return out


async def home_devices(ctx: Ctx, domain: str = "", q: str = "", limit: int = 200, **_: Any) -> dict:
    r = await home.states(domain=domain, q=q, limit=limit)   # reads are gate-free; the gate guards switching
    if not r.get("ok"):
        raise ToolError(r.get("why", "HA se devices nahi mile."))
    r["say"] = f"{r.get('count', 0)} device mile." if r.get("count") else "Is naam/domain ka koi device nahi mila."
    return r


async def home_on(ctx: Ctx, entity: str, confirm: bool = False, extra: dict | None = None, **_: Any) -> dict:
    # no pre-gate here: home.switch() gates FIRST and audits the attempt - one gate, one audit place
    r = await home.switch(entity, True, ctx.tenant_id, ctx.conversation_id, actor=ctx.actor,
                          confirm=confirm, extra=extra)
    if not r.get("ok"):
        raise ToolError(r.get("why", "on nahi ho paya."))
    return r


async def home_off(ctx: Ctx, entity: str, confirm: bool = False, **_: Any) -> dict:
    r = await home.switch(entity, False, ctx.tenant_id, ctx.conversation_id, actor=ctx.actor,
                          confirm=confirm, extra=None)
    if not r.get("ok"):
        raise ToolError(r.get("why", "off nahi ho paya."))
    return r


async def home_state(ctx: Ctx, entity: str, **_: Any) -> dict:
    r = await home.state_one(entity)
    if not r.get("ok"):
        raise ToolError(r.get("why", "device ka haal nahi mila."))
    return r


HOME_HANDLERS = {"home_link": home_link, "home_devices": home_devices, "home_on": home_on,
                 "home_off": home_off, "home_state": home_state}
