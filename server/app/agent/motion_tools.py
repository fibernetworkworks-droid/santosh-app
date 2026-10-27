"""Hoola Motion for the avatar: make a short animated reel (business, recipe, logo intro, offer, or any idea)."""
from __future__ import annotations

import asyncio

from .tools import Ctx, ToolError

MOTION_TOOLS = [
    {"name": "motion_video", "description": (
        "Hoola Motion: make a short animated video / reel (MP4, vertical 9:16 by default) that Hoola writes as code and "
        "renders on the server in 1-3 minutes. action=make with kind: 'explainer' (a business reel: problem, what we do, "
        "3 steps, proof, contact), 'recipe' (ingredients drop into the kadhai, steps, final dish), 'logo' (10 s brand "
        "intro), 'offer' (sale / festival offer with dates and contact), or 'custom' (any idea: Hoola writes the whole "
        "animation, beta, slower). 'brief' = everything the owner said (names, phone, place, prices, dates exactly as "
        "given: never invent them). aspect '9:16' (reels / status), '1:1', '16:9'; music 'upbeat' / 'calm' / 'festive' / "
        "'none'. The finished video appears as a card in chat and in Connect > Hoola Motion, where the owner can share it "
        "or post it to their own YouTube (with their tap). action=list: recent videos; action=status: one video (id). "
        "Every video is labelled as AI-made. To EDIT the owner's own recorded footage use video_edit instead."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["make", "list", "status"]},
         "kind": {"type": "string", "enum": ["explainer", "recipe", "logo", "offer", "custom"]},
         "brief": {"type": "string"}, "aspect": {"type": "string", "enum": ["9:16", "1:1", "16:9"]},
         "music": {"type": "string", "enum": ["upbeat", "calm", "festive", "none"]}, "id": {"type": "string"}},
         "required": ["action"]}},
]
MOTION_LABELS = {"motion_video": "Video bana raha hoon"}


async def motion_video(ctx: Ctx, action, kind="explainer", brief="", aspect="9:16", music="upbeat", id="", **_):
    from ..motion import service as mo
    try:
        if action == "list":
            vids = await asyncio.to_thread(mo.list_, ctx.tenant_id, 8)
            return {"videos": [{k: v.get(k) for k in ("id", "title", "kind", "status", "duration")} for v in vids]}
        if action == "status":
            v = await asyncio.to_thread(mo.get, ctx.tenant_id, str(id))
            return {k: v.get(k) for k in ("id", "title", "status", "progress", "error", "duration")}
        if action == "make":
            if kind not in mo.KIND_IDS:
                raise ToolError("kind: explainer, recipe, logo, offer ya custom")
            if kind == "custom":
                v = await asyncio.to_thread(mo.create, ctx.tenant_id, kind, None, aspect, music, str(brief), ctx.conversation_id)
            else:
                p = await asyncio.to_thread(mo.plan, kind, str(brief))
                v = await asyncio.to_thread(mo.create, ctx.tenant_id, kind, p["data"], aspect, music, "", ctx.conversation_id)
            return {"id": v["id"], "title": v["title"], "status": v["status"], "ai_label": v["ai_label"],
                    "note": "Video ban rahi hai (1-3 minute). Poori hote hi chat mein card aayega; Connect > Hoola Motion "
                            "mein bhi milegi."}
    except mo.MotionError as e:
        raise ToolError(str(e))
    raise ToolError("action: make, list ya status")


MOTION_HANDLERS = {"motion_video": motion_video}
