"""v0.463 Tool `zoo`: the BYOK model zoo - image/video models behind BYOK gateways (Muapi + kie.ai).

Purely additive: the curated studios (video_studio / photo_banao / create_studio) stay the everyday
path and keep their own specs untouched. The zoo is for a specific model / style / aspect they
don't cover. Actions: guide | models (search the registry) | make (submit + wait) | status (poll).
Same safety refusals as photo_banao, run BEFORE any gateway call. The owner's keys live in the
server env and go only to their gateway: ZOO_MUAPI_KEY -> api.muapi.ai, ZOO_KIE_KEY -> api.kie.ai.
"""
from __future__ import annotations

from typing import Any

from .. import zoo
from .tools import Ctx, ToolError

GUIDE = (
    "ZOO GUIDE. 200+ image/video models through two BYOK gateways (Muapi + kie.ai - each entry says which "
    "gateway; the full count comes from action=models or this guide). "
    "1) Search with action=models: kind image|video|audio, mode t2i| i2i (image edit) | t2v | i2v (start frame) | "
    "v2v (video edit) | t2s/t2m/a2a (speech/music/audio), q=search text (name or maker, e.g. 'flux', 'kling', "
    "'nano-banana'). Each entry: id, name, mode, gateway, aspects / resolutions / durations (allowed values), "
    "max_images (multi-reference models), audio_field (talk models: send the audio URL here in extra), params "
    "(documented input fields - send any you need besides prompt/aspect/duration in extra, e.g. for TTS "
    "extra = {\"text\": ..., \"voice\": ...}). "
    "2) action=make: model_id + prompt are required; i2i/i2v models need at least ONE reference in image_urls "
    "(a public URL, local file path or data-URI works - kie puts it on its own CDN). Talk models need extra "
    "= {audio_field_value: audio_url}. Send only the aspect / resolution / duration values from the catalog. "
    "num = number of outputs (Muapi models). extra = {field: value} straight to the gateway. Images are usually ready in ~1 min; "
    "video takes minutes - make returns a request_id at once, ask about it with action=status. "
    "3) Do everyday work through the CURATED studios (video_studio, photo_banao, create_studio) - quality tiers, "
    "price cards, lip sync and her voice are already wired there. Use Zoo only when a specific model/style/aspect is needed. "
    "Safety is the same as photo_banao: never fake documents, nudity, face swaps, or pictures of real people. "
    "The owner keeps the keys in the server env (ZOO_MUAPI_KEY for Muapi models, ZOO_KIE_KEY for kie models); "
    "if the needed key is there, generation runs; if not, say so plainly."
)

ZOO_TOOLS = [
    {"name": "zoo", "description": (
        "BYOK MODEL ZOO: 200+ image & video models (Flux, Midjourney, Seedream, Sora-class, Kling, Wan, Hailuo, "
        "Nano Banana, Ideogram, GPT Image, Seedance...) behind BYOK gateways (Muapi + kie.ai), for when the curated "
        "studios don't have the model, style or aspect she asked for. Actions: guide (read once) | models (kind "
        "image|video, mode t2i|i2i|t2v|i2v, q=search, limit: the registry with allowed aspects/resolutions/durations) "
        "| make (model_id, prompt, image_urls for i2i/i2v reference or start frame - public URL, local path ya "
        "data-URI, aspect, resolution, duration, num, extra) -> images usually finish in ~1 min; videos return "
        "request_id | status (request_id: pending / done with URLs / failed with reason). Everyday work stays with "
        "video_studio / photo_banao / create_studio. Same refusals as photo_banao: fake documents, nudity, face "
        "swap, real people - never. Needs the owner's gateway key on the server (ZOO_MUAPI_KEY for Muapi models, "
        "ZOO_KIE_KEY for kie models); without the right key models list fine but make refuses with a clear line - "
        "tell her that."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["guide", "models", "make", "status"]},
         "kind": {"type": "string", "enum": ["image", "video"]},
         "mode": {"type": "string", "enum": ["t2i", "i2i", "t2v", "i2v"]},
         "q": {"type": "string", "description": "search text: model name, id ya maker (flux, kling, seedream)"},
         "limit": {"type": "number"},
         "model_id": {"type": "string", "description": "full zoo id, e.g. t2i:nano-banana or i2v:kling-v2-1-i2v"},
         "prompt": {"type": "string"}, "image_urls": {"type": "array", "items": {"type": "string"}},
         "aspect": {"type": "string"}, "resolution": {"type": "string"}, "duration": {"type": "number"},
         "num": {"type": "number"}, "request_id": {"type": "string"},
         "extra": {"type": "object", "description": "merged straight into the gateway payload"},
     }, "required": ["action"]}},
]

ZOO_LABELS = {"zoo": "Working in the model zoo (BYOK)"}


async def zoo_tool(ctx: Ctx, action: str = "guide", **a: Any):
    action = (action or "guide").strip().lower()
    if action == "guide":
        return {"guide": GUIDE, "key_on_server": zoo.ready(),
                "count": len(zoo.load_catalog().get("models", []))}
    if action == "models":
        rows = zoo.list_models(a.get("kind", ""), a.get("mode", ""), a.get("q", ""), a.get("limit", 40))
        return {"count": len(rows), "key_on_server": zoo.ready(),
                "note": ("key is on the server - make can run" if zoo.ready()
                         else "key is NOT on the server: the owner must set the zoo key (ZOO_MUAPI_KEY / ZOO_KIE_KEY) before generating"),
                "models": [{**{k: m.get(k) for k in ("id", "name", "mode", "kind", "aspects", "resolutions",
                                                     "durations", "max_images", "family", "audio_field",
                                                     "params") if m.get(k)},
                            "gateway": zoo.gateway_of(m)} for m in rows]}
    if action == "make":
        mid = (a.get("model_id") or "").strip()
        if not mid:
            raise ToolError("model_id is needed (see the full id with action=models, e.g. t2i:nano-banana).")
        m = zoo.model(mid)
        prompt = (a.get("prompt") or "").strip()
        if m.get("has_prompt", True) and not prompt:
            raise ToolError("A prompt is needed - the model must be told what to make.")
        why = zoo.gate(prompt)
        if why:
            raise ToolError(why)
        r = await zoo.run(m, prompt, tenant=ctx.tenant_id,
                          image_urls=a.get("image_urls") or [], aspect=a.get("aspect") or "",
                          resolution=a.get("resolution") or "", duration=a.get("duration"),
                          num=a.get("num"), extra=a.get("extra") or {},
                          wait_s=110.0 if m.get("kind") == "image" else 25.0)
        if r["status"] == "done":
            r["say"] = (f"Ready from {m.get('name')}: " + " | ".join(r.get("urls", [])[:4])) if r.get("urls") \
                else f"{m.get('name')} answered (no URL was found)."
        elif r["status"] == "failed":
            r["say"] = f"{m.get('name')} failed: {r.get('error', 'no reason found')}"
        else:
            r["say"] = (f"{m.get('name')} is running (video takes time). Check again shortly with action=status "
                        f"request_id={r['request_id']}.")
        return r
    if action == "status":
        rid = (a.get("request_id") or "").strip()
        if not rid:
            raise ToolError("request_id is needed (make returned it).")
        r = await zoo.poll(rid)
        if r["status"] == "done":
            r["say"] = "Ready: " + " | ".join(r.get("urls", [])[:4])
        elif r["status"] == "failed":
            r["say"] = f"Failed: {r.get('error', 'no reason found')}"
        else:
            r["say"] = "Still running - ask again shortly."
        return r
    raise ToolError(f"zoo action '{action}' does not exist: guide | models | make | status.")


ZOO_HANDLERS = {"zoo": zoo_tool}
