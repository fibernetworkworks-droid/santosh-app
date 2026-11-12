---
name: cs-zoo-radar
description: Zoo expansion radar - catalog first, never invented ids
when_to_use: new AI model, better model, which model, image model, video model, model list, compare AI models, latest model
---
GOAL: when she asks "a new or better model?" or a zoo search comes back
empty - CATALOG first, radar after. The zoo is a 436-model BYOK catalog
(zoo_catalog.json: 186 image, 221 video, 29 audio; gateways muapi 211 +
kie 225). What is not in the catalog is NOT in the zoo - never make
with an invented model id. Everyday work goes only through the curated studios
(video_studio, photo_banao, create_studio); use the zoo when a
particular model/style/aspect is needed.

THE RADAR FAMILIES (vetted names from awesome-generative-ai - these are
SEARCH TERMS, not model ids; put them in the q= of zoo action=models):
- IMAGE: flux, nano-banana, seedream, ideogram, stable diffusion / sdxl,
  imagen, recraft, dall-e
- VIDEO: kling, sora, runway, luma, pika, hailuo / minimax, wan, veo, seedance
- AUDIO: suno, udio, stable audio, elevenlabs, whisper, kokoro, xtts, bark
- TEXT/AGENTS: gpt, claude, gemini, llama, qwen, deepseek, mistral - but
  the chat brain's work is not done by the zoo; the zoo is only for
  image/video/audio models.

THE PROTOCOL:
1. zoo action=models kind=image|video|audio, mode=t2i|i2i|t2v|i2v|t2s...,
   q=<family>. The catalog is the source of truth. Found it? Stop there
   - the model_id is the catalog's own, and aspect/resolution/duration
   are ONLY the catalog's values (plus the documented params under
   extra).
2. Not found? Search 2-3 more with family variants (q=flux, q=flux pro...).
3. Still empty? Giving the model's name is fine, but say the status
   honestly: "unverified - not in the zoo catalog". Never claim "it is
   in the zoo" falsely.
4. EXPANSION only by the owner's tap: there is simply no door to edit the
   catalog yourself. Give the owner the append shape (the REAL
   zoo_catalog.json shape):
   {"id": "t2i:nano-banana", "name": "Nano Banana", "kind": "image",
    "mode": "t2i", "endpoint": "nano-banana", "aspects": ["1:1", "16:9", ...]}
   A kie entry carries "gateway": "kie" on top and its own endpoint name.
   Ask the owner which gateway it is (does Muapi or kie serve it?) -
   never assume. For a big private catalog, mention HOOLA_ZOO_CATALOG.
NEVER: make with an invented model_id; an aspect/duration outside the
catalog; wait for a key before make (ZOO_MUAPI_KEY / ZOO_KIE_KEY are in
the owner's env - without a key make gives a clear refusal, and the
models search before it is free); skip asking for status after a video
(make only gives a request_id, it takes minutes - poll with
action=status).
