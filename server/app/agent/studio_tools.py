"""v0.68 Tool `video_studio`: Hoola directs AI-generated videos (Higgsfield / Google Flow style) with the owner's
hoola-studio engine: Seedance 2.0 / 2.5, Veo 3.1, Kling 3.0, Wan 3.0 (OpenRouter), fal, BytePlus, Gemini Omni Flash.
Every paid step is a price card she taps; previews are free."""
from __future__ import annotations

from typing import Any

from .tools import Ctx, ToolError

STUDIO_TOOLS = [
    {"name": "video_studio", "description": (
        "AI VIDEO STUDIO: make NEW videos from a description when she has no footage (ads, product reels, festival "
        "greetings, explainers, invites, story shorts) with AI video models, the same person / product in every shot, "
        "Hindi dialogue with lip sync, narration in your voice, music, her logo, captions, an 'AI-generated' label. "
        "(Her OWN footage -> video_edit; animated text / graphics reels -> motion_video.) "
        "You are the director. Actions: guide (read once) | models | create (name, aspect 9:16|16:9|1:1|4:3|3:4, style, "
        "language, brief) | list | show | character (name, description, file_ids of her photos, consent=true only if she "
        "said the person agreed) | character_generate (name, description: fictional person / mascot / product) | "
        "storyboard (shots: [{prompt, duration 4-10, camera, characters, dialogue | voiceover, caption, transition, "
        "start_image_file_id}]) | shot_update (shot_id, changes) | estimate (quality) | generate (quality preview = FREE "
        "animatic; draft = cheap 480p; final = 1080p; shot_ids, variants, model) -> paid ones become a price card she "
        "taps (nothing spent before) | review (shot_id, take) | pick (shot_id, take) | voiceover (shot_id, text = you speak "
        "it free, or file_id) | music (mood upbeat|calm|festive free, or file_id) | logo (file_id) | assemble (captions, "
        "transition) -> final video arrives as a card | spend. project defaults to the latest one. Tell her prices in "
        "rupees. Never real people without permission, never imitate real brands, news, officials or politicians."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["guide", "models", "create", "list", "show", "character", "character_generate",
                                               "storyboard", "shot_update", "estimate", "generate", "review", "pick",
                                               "voiceover", "music", "logo", "assemble", "spend"]},
         "project": {"type": "string"}, "name": {"type": "string"}, "aspect": {"type": "string"},
         "style": {"type": "string"}, "language": {"type": "string"}, "brief": {"type": "string"},
         "description": {"type": "string"}, "file_ids": {"type": "array", "items": {"type": "string"}},
         "consent": {"type": "boolean"}, "shots": {"type": "array", "items": {"type": "object"}},
         "shot_id": {"type": "string"}, "changes": {"type": "object"},
         "quality": {"type": "string", "enum": ["preview", "draft", "final"]},
         "shot_ids": {"type": "array", "items": {"type": "string"}}, "variants": {"type": "integer"},
         "model": {"type": "string"}, "take": {"type": "integer"}, "text": {"type": "string"},
         "file_id": {"type": "string"}, "mood": {"type": "string"}, "volume": {"type": "number"},
         "position": {"type": "string"}, "captions": {"type": "boolean"}, "transition": {"type": "string"}},
         "required": ["action"]}},
]
STUDIO_LABELS = {"video_studio": "Video studio mein kaam kar raha hoon"}


async def video_studio(ctx: Ctx, action, **a: Any):
    from ..studio import service as ss
    t = ctx.tenant_id
    action = str(action)
    try:
        if action == "guide":
            return {"guide": ss.GUIDE}
        if action == "models":
            return {"ready": ss.ready_providers(t), "models": [{k: m[k] for k in ("model", "label", "ready", "usd_per_second",
                                                                                 "inr_per_second", "durations_s")}
                                                              for m in ss.models(t)]}
        if action == "list":
            return {"projects": ss.listing(t)[:15]}
        if action == "create":
            return await ss.create(t, a.get("name") or a.get("project") or "", a.get("aspect") or "9:16", a.get("style") or "reel",
                                   a.get("language") or "Hindi", a.get("brief") or "", ctx.conversation_id)
        project = a.get("project") or ss.latest(t)
        if not project:
            raise ToolError("Abhi koi video project nahi hai: pehle action=create.")
        if action == "show":
            v = ss.view(t, ss._load(t, project))
            v["outputs"] = [{k: o.get(k) for k in ("seconds", "takes", "preview", "file_id")} for o in v["outputs"]]
            return v
        if action == "character":
            return await ss.character(t, project, a.get("name") or "", a.get("description") or "", a.get("file_ids") or [],
                                      bool(a.get("consent")))
        if action == "character_generate":
            return await ss.character_generate(t, project, a.get("name") or "", a.get("description") or "")
        if action == "storyboard":
            return await ss.storyboard(t, project, a.get("shots") or [])
        if action == "shot_update":
            st = await ss.studio(t)
            r = st.shot_update(project, str(a.get("shot_id", "")), a.get("changes") or {})
            ss._changed(t, project)
            return r
        if action == "estimate":
            st = await ss.studio(t)
            e = st.estimate(project, a.get("quality") or "final", a.get("shot_ids"), int(a.get("variants") or 1), a.get("model"))
            e["inr"] = ss._inr(e["usd"])
            return e
        if action == "generate":
            return await ss.generate(t, project, a.get("quality") or "preview", a.get("shot_ids"), int(a.get("variants") or 1),
                                     a.get("model"), ctx.conversation_id)
        if action == "review":
            return await ss.review(t, project, str(a.get("shot_id", "")), a.get("take"))
        if action == "pick":
            st = await ss.studio(t)
            r = st.pick(project, str(a.get("shot_id", "")), int(a.get("take") or 0))
            ss._changed(t, project)
            return r
        if action == "voiceover":
            return await ss.voiceover(t, project, str(a.get("shot_id", "")), a.get("text") or "", a.get("file_id") or "")
        if action == "music":
            return await ss.music(t, project, a.get("mood") or "", a.get("file_id") or "", a.get("volume") or 0.25)
        if action == "logo":
            return await ss.logo(t, project, a.get("file_id") or "", a.get("position") or "top-right")
        if action == "assemble":
            return await ss.assemble(t, project, a.get("captions", True) is not False, a.get("transition"))
        if action == "spend":
            return await ss.spend(t, project)
    except ss.StudioJobError as e:
        raise ToolError(str(e))
    except ss.StudioError as e:
        raise ToolError(str(e))
    raise ToolError("unknown action")


STUDIO_HANDLERS = {"video_studio": video_studio}
