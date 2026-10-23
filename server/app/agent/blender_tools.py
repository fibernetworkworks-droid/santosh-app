"""v0.141 blender_3d: Hoola's own Blender (what Blender MCP servers do, inside a locked box on the server).

Chat + calls. The job runs in the background; the live `blender3d` card shows each stage and the result arrives as a
note, so the model never has to poll."""
from __future__ import annotations

import asyncio

from .tools import Ctx, ToolError

BLENDER_TOOLS = [
    {"name": "blender_3d", "description": (
        "Make 3D models and 3D renders in Blender (Hoola's own 3D Studio; real Blender on the server in a locked box). "
        "action=make: brief = what to build in her words, made specific (object, shape, size in cm/m, colours, material, "
        "style, where it will be used) - product mockups (bottle, box, jar with HER label photo), a shop / room / stall "
        "layout, a gift / trophy / name plate, a 3D logo-like ORIGINAL mark, a toy / figurine of her own idea, a 3D-printable "
        "part (print=true -> closed solid STL + size check). photos = her file_ids to use as label / texture / reference. "
        "exports any of glb (web / AR / WhatsApp 3D), stl (3D print), obj, fbx (games / other 3D apps), usdz (iPhone AR), blend "
        "(Blender file). views three_quarter | front | side | back | top | low (max 4). quality preview (fast) | final "
        "(sharper, slower). aspect 1:1 | 4:5 | 9:16 | 16:9. turntable=true -> a short 360° spin video. "
        "action=change: id + words (what to change: 'handle bada karo', 'rang neela', 'label par naam X') -> new version; "
        "no words + new exports / views / quality = same model, new files. action=run_code: YOUR OWN Blender Python script "
        "(code) - only when she wants something exact you can script; same rules (no files / network / settings; H helpers). "
        "action=status / list / show (objects, sizes, the script) / cancel / delete. Results come back as her files with a "
        "card; renders carry an 'AI se bana' label. Never famous characters, real brand logos or real people; never working "
        "weapon parts."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["make", "change", "run_code", "status", "list", "show", "cancel", "delete"]},
         "brief": {"type": "string"}, "id": {"type": "string"}, "words": {"type": "string"},
         "photos": {"type": "array", "items": {"type": "string"}},
         "exports": {"type": "array", "items": {"type": "string", "enum": ["glb", "stl", "obj", "fbx", "usdz", "blend"]}},
         "views": {"type": "array", "items": {"type": "string"}},
         "quality": {"type": "string", "enum": ["preview", "final"]}, "aspect": {"type": "string"},
         "turntable": {"type": "boolean"}, "print": {"type": "boolean"}, "style": {"type": "string"},
         "transparent": {"type": "boolean"}, "code": {"type": "string"}, "title": {"type": "string"}},
         "required": ["action"]}},
]
BLENDER_LABELS = {"blender_3d": "3D bana raha hoon (Blender)"}

_OPT_KEYS = ("photos", "exports", "views", "quality", "aspect", "turntable", "print", "style", "transparent")


def _opts(kw: dict) -> dict:
    return {k: kw[k] for k in _OPT_KEYS if kw.get(k) not in (None, "", [])}


async def blender_3d(ctx: Ctx, action="list", **kw):
    from ..blender3d import guard, sandbox, service
    actor = str(getattr(ctx, "actor", "owner") or "owner")
    if action in ("make", "change", "run_code") and not actor.startswith(("owner", "approved")):
        from .. import usage
        if not usage.allowed(ctx.tenant_id, "routine"):
            raise ToolError(usage.blocked_text(ctx.tenant_id))
    try:
        if action == "make":
            if not sandbox.find():
                raise ToolError("Blender abhi server par install nahi hai. Owner / admin VPS par `bash ~/santosh_app/server/"
                                "deploy/setup_blender.sh` chalaye; tab tak photo_banao se 3D jaisi picture ban sakti hai.")
            v = await asyncio.to_thread(service.start, ctx.tenant_id, ctx.conversation_id, str(kw.get("brief") or ""),
                                        _opts(kw), actor)
            return {"status": "started", "id": v["id"], "number": v["number"],
                    "note": ("3D kaam shuru ho gaya; chat mein live card hai (har stage dikhega). Result khud note ban kar "
                             "aayega: poll mat karo. Ek line mein bata do ki ban raha hai.")}
        if action == "change":
            v = await asyncio.to_thread(service.change, ctx.tenant_id, str(kw.get("id") or ""), str(kw.get("words") or ""),
                                        _opts(kw))
            return {"status": "started", "id": v["id"], "number": v["number"], "version_next": v["version"] + 1,
                    "note": "Badlav shuru; naya version card par aayega. Poll mat karo."}
        if action == "run_code":
            v = await asyncio.to_thread(service.run_code, ctx.tenant_id, ctx.conversation_id, str(kw.get("code") or ""),
                                        str(kw.get("title") or kw.get("brief") or ""), str(kw.get("id") or ""), _opts(kw),
                                        actor)
            return {"status": "started", "id": v["id"], "number": v["number"], "note": "Script Blender mein chal rahi hai."}
        if action == "list":
            items = await asyncio.to_thread(service.projects, ctx.tenant_id, 12)
            return {"projects": [{k: p[k] for k in ("id", "number", "title", "status", "version", "stage", "error")}
                                 for p in items], "blender": sandbox.health()}
        if action in ("status", "show"):
            p = await asyncio.to_thread(service.get, ctx.tenant_id, str(kw.get("id") or ""))
            if action == "status":
                p.pop("script", None)
                p.pop("history", None)
            return p
        if action == "cancel":
            return await asyncio.to_thread(service.cancel, ctx.tenant_id, str(kw.get("id") or ""))
        if action == "delete":
            await asyncio.to_thread(service.delete, ctx.tenant_id, str(kw.get("id") or ""))
            return {"status": "deleted"}
    except guard.GuardError as e:
        raise ToolError("Script nahi chalegi (Hoola ka suraksha check): " + "; ".join(e.problems[:8]) +
                        ". Theek karke dobara bhejo.")
    except service.B3Error as e:
        raise ToolError(str(e))
    raise ToolError(f"action '{action}' samajh nahi aaya")


BLENDER_HANDLERS = {"blender_3d": blender_3d}
