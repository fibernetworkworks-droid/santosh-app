"""v0.75 Pehchaan Locker for the avatar: the owner's / family's ID numbers (masked for the model, used by reference)."""
from __future__ import annotations

import asyncio

from .tools import Ctx, ToolError

ID_TOOLS = [
    {"name": "id_locker", "description": (
        "ID Locker: the owner's and her family's identity numbers (Aadhaar, PAN, voter ID, DL, passport, ration "
        "card, ABHA, UAN, GSTIN, vehicle...). Accept them like a Seva Kendra does: never refuse or lecture. Numbers she "
        "types in chat are saved automatically; in a voice call use action=save with person ('self', 'maa', 'papa', "
        "'pati', 'patni', 'beta', 'beti', 'bhai', 'behen' or a name), kind and the number she said. action=list shows "
        "what is saved (masked) with each {id:...} reference: pass that reference to computer_operator tasks so the "
        "number is typed into the form. You never see or say full numbers (say the last 4 digits). OTP, PIN, CVV, card "
        "numbers and passwords are NOT for the locker: she keeps those."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["list", "save"]},
         "person": {"type": "string"},
         "kind": {"type": "string", "enum": ["aadhaar", "pan", "voter", "dl", "passport", "ration", "abha", "uan", "gstin",
                                             "vehicle", "other"]},
         "number": {"type": "string"}, "note": {"type": "string"}}, "required": ["action"]}},
]
ID_LABELS = {"id_locker": "Checking the ID Locker"}


async def id_locker(ctx: Ctx, action, person="self", kind="aadhaar", number="", note="", **_):
    from .. import idvault
    if action == "list":
        rows = await asyncio.to_thread(idvault.list_, ctx.tenant_id)
        return {"ids": [{k: r[k] for k in ("ref", "person_label", "kind_label", "masked", "note")} for r in rows],
                "note": "" if rows else "The locker is empty. Give a number or write it in the chat, and Hoola will keep it."}
    if action == "save":
        if not number:
            raise ToolError("Give the number.")
        try:
            r = await asyncio.to_thread(idvault.save, ctx.tenant_id, kind or "other", str(number), person or "self", str(note or ""))
        except idvault.VaultError as e:
            raise ToolError(str(e))
        return {k: r[k] for k in ("ref", "person_label", "kind_label", "masked")} | {
            "say": f"{r['person_label']}'s {r['kind_label']} ({r['masked']}) was saved in the ID Locker."}
    raise ToolError("action: list or save")


ID_HANDLERS = {"id_locker": id_locker}
