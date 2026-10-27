"""v0.56 The avatar can explain why it was quiet: "mera reminder kyun nahi baja?" -> the phone's own last health check
(battery saver, restricted, how often the phone maker stopped Hoola) and what to switch on."""
from __future__ import annotations

from typing import Any

from .tools import Ctx

DEVICE_TOOLS = [
    {"name": "phone_health", "description": (
        "Check whether the owner's phone lets Hoola run in the background (battery saver, Autostart, the phone maker "
        "stopping the app). Use when a reminder / alarm / notification / call did not come, or the owner asks why Hoola "
        "stopped. Returns problems in plain words; tell her the fix and that 'Profile > Hoola band na ho' opens the "
        "right settings. You can only open settings for her, never change them yourself."),
     "input_schema": {"type": "object", "properties": {}}},
]
DEVICE_LABELS = {"phone_health": "Phone ki settings dekh raha hoon"}


async def phone_health(ctx: Ctx, **_) -> dict[str, Any]:
    from .. import keepalive
    h = keepalive.last_health(ctx.tenant_id)
    if not h:
        return {"known": False, "note": "Phone ne abhi tak report nahi bheji. Owner app kholke Profile > 'Hoola band na ho' dekhein."}
    return {"known": True, "phone": " ".join(x for x in (h.get("brand"), h.get("model")) if x),
            "ok": h.get("ok"), "problems": [p["title"] + ": " + p["fix"] for p in h.get("problems") or []],
            "stopped_by_phone_7d": (h.get("counts") or {}).get("oem_kill", 0),
            "where": "Profile > Hoola band na ho (har line par 'Kholo' button)"}


DEVICE_HANDLERS = {"phone_health": phone_health}
