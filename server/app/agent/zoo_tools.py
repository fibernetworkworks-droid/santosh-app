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
    "ZOO GUIDE. Do BYOK gateways ke through 233 image/video models (Muapi + kie.ai - har entry batati hai kaunsa "
    "gateway). "
    "1) action=models se dhoondein: kind image|video, mode t2i| i2i (image edit) | t2v | i2v (start frame), "
    "q=search text (name ya maker, jaise 'flux', 'kling', 'nano-banana'). Har entry: id, name, mode, gateway, "
    "aspects / resolutions / durations (allowed values), max_images (multi-reference models), audio_field (talk "
    "models: extra mein audio URL yahan bhejein). "
    "2) action=make: model_id + prompt zaroori; i2i/i2v models ko image_urls mein kam se kam EK reference chahiye "
    "(public URL, local file path ya data-URI chalega - kie use apne CDN par daal dega). talk models ke liye extra "
    "= {audio_field_value: audio_url} zaroori. aspect / resolution / duration sirf catalog wali values hi bhejein. "
    "num = kitne outputs (Muapi models). extra = {field: value} seedha gateway ko. Images aksar ~1 min mein ready; "
    "video minutes leti hai - make turant request_id de dega, usse action=status se poochein. "
    "3) Roz-marra kaam CURATED studios se hi karein (video_studio, photo_banao, create_studio) - wahan quality tiers, "
    "price cards, lip sync, uski voice sab pehle se juda hai. Zoo tab jab koi khaas model/style/aspect chahiye. "
    "Safety photo_banao jaisi hi: nakli documents, nude, face swap, asli logon ki tasveer kabhi nahi. "
    "Keys owner server env mein rakhta hai (ZOO_MUAPI_KEY Muapi models ke liye, ZOO_KIE_KEY kie models ke liye); "
    "jo key chahiye ho to generate chalta hai, na ho to seedha bataiye."
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
         "model_id": {"type": "string", "description": "poora zoo id, jaise t2i:nano-banana ya i2v:kling-v2-1-i2v"},
         "prompt": {"type": "string"}, "image_urls": {"type": "array", "items": {"type": "string"}},
         "aspect": {"type": "string"}, "resolution": {"type": "string"}, "duration": {"type": "number"},
         "num": {"type": "number"}, "request_id": {"type": "string"},
         "extra": {"type": "object", "description": "seedha gateway payload mein merge ho jaata hai"},
     }, "required": ["action"]}},
]

ZOO_LABELS = {"zoo": "Model zoo (BYOK) mein kaam kar raha hoon"}


async def zoo_tool(ctx: Ctx, action: str = "guide", **a: Any):
    action = (action or "guide").strip().lower()
    if action == "guide":
        return {"guide": GUIDE, "key_on_server": zoo.ready(),
                "count": len(zoo.load_catalog().get("models", []))}
    if action == "models":
        rows = zoo.list_models(a.get("kind", ""), a.get("mode", ""), a.get("q", ""), a.get("limit", 40))
        return {"count": len(rows), "key_on_server": zoo.ready(),
                "note": ("key server par hai - make chal sakta hai" if zoo.ready()
                         else "key server par NAHI hai: generate se pehle owner zoo key (ZOO_MUAPI_KEY / ZOO_KIE_KEY) set karein"),
                "models": [{**{k: m.get(k) for k in ("id", "name", "mode", "kind", "aspects", "resolutions",
                                                     "durations", "max_images", "family", "audio_field") if m.get(k)},
                            "gateway": zoo.gateway_of(m)} for m in rows]}
    if action == "make":
        mid = (a.get("model_id") or "").strip()
        if not mid:
            raise ToolError("model_id bataiye (action=models se poora id dekhein, jaise t2i:nano-banana).")
        m = zoo.model(mid)
        prompt = (a.get("prompt") or "").strip()
        if m.get("has_prompt", True) and not prompt:
            raise ToolError("prompt likhiye - is model ko batana hai kya banana hai.")
        why = zoo.gate(prompt)
        if why:
            raise ToolError(why)
        r = await zoo.run(m, prompt, tenant=ctx.tenant_id,
                          image_urls=a.get("image_urls") or [], aspect=a.get("aspect") or "",
                          resolution=a.get("resolution") or "", duration=a.get("duration"),
                          num=a.get("num"), extra=a.get("extra") or {},
                          wait_s=110.0 if m.get("kind") == "image" else 25.0)
        if r["status"] == "done":
            r["say"] = (f"{m.get('name')} se tayyar: " + " | ".join(r.get("urls", [])[:4])) if r.get("urls") \
                else f"{m.get('name')} ne jawab de diya (koi URL nahi mila)."
        elif r["status"] == "failed":
            r["say"] = f"{m.get('name')} fail: {r.get('error', 'wajah nahi mili')}"
        else:
            r["say"] = (f"{m.get('name')} chal raha hai (video ko waqt lagta hai). Thodi der baad action=status "
                        f"request_id={r['request_id']} se poochein.")
        return r
    if action == "status":
        rid = (a.get("request_id") or "").strip()
        if not rid:
            raise ToolError("request_id bataiye (make ne diya tha).")
        r = await zoo.poll(rid)
        if r["status"] == "done":
            r["say"] = "Tayyar: " + " | ".join(r.get("urls", [])[:4])
        elif r["status"] == "failed":
            r["say"] = f"Fail hua: {r.get('error', 'wajah nahi mili')}"
        else:
            r["say"] = "Abhi chal raha hai - thodi der baad phir poochein."
        return r
    raise ToolError(f"zoo action '{action}' nahi hai: guide | models | make | status.")


ZOO_HANDLERS = {"zoo": zoo_tool}
