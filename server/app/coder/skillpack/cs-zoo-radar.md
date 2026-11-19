---
name: cs-zoo-radar
description: Zoo expansion radar - catalog first, never invented ids
when_to_use: new AI model, better model, which model, image model, video model, model list, compare AI models, latest model
---
GOAL: the user asks "is there a new or better model?" or a zoo search comes
back empty - then the CATALOG first, the radar after. The zoo is a 436-model
BYOK catalog (zoo_catalog.json: 186 image, 221 video, 29 audio; gateways muapi
211 + kie 225). What is not in the catalog is NOT in the zoo - never make
anything with an invented model id. Everyday work goes through the
curated studios (video_studio, photo_banao, create_studio); the zoo is for
when a particular model / style / aspect is needed.

THE RADAR FAMILIES (vetted names from awesome-generative-ai - these are SEARCH
TERMS, not model ids; put them in q= of zoo action=models):
- IMAGE: flux, nano-banana, seedream, ideogram, stable diffusion / sdxl,
  imagen, recraft, dall-e
- VIDEO: kling, sora, runway, luma, pika, hailuo / minimax, wan, veo, seedance
- AUDIO: suno, udio, stable audio, elevenlabs, whisper, kokoro, xtts, bark
- TEXT/AGENTS: gpt, claude, gemini, llama, qwen, deepseek, mistral - but the
  zoo does not do the chat brain's job; the zoo is only for image / video /
  audio models.

THE PROTOCOL:
1. zoo action=models kind=image|video|audio, mode=t2i|i2i|t2v|i2v|t2s..., q=<
   family>. The catalog is the source of truth. Found it? Stop there - the
   model_id exactly as in the catalog, and aspect / resolution / duration ONLY
   from the catalog's values (documented params of extra go separately).
2. If not found, 2-3 more searches with family variants (q=flux, q=flux pro...).
3. Still empty? Naming the model is fine, but state the status honestly as
   "unverified - not in the zoo catalog". Never the lie "it is in the zoo".
4. EXPANSION only by the owner's tap: there is no door to edit the catalog
   yourself. Give the owner the append shape (the REAL zoo_catalog.json shape):
   {"id": "t2i:nano-banana", "name": "Nano Banana", "kind": "image",
    "mode": "t2i", "endpoint": "nano-banana", "aspects": ["1:1", "16:9", ...]}
   a kie entry adds "gateway": "kie" on top and its own endpoint name. Ask the
   owner the gateway question (does Muapi or kie serve it?) - never assume.
   For a big private catalog mention HOOLA_ZOO_CATALOG.
NEVER: make with an invented model_id; an aspect / duration outside the
catalog; make without waiting for the key (ZOO_MUAPI_KEY / ZOO_KIE_KEY live in
the owner's env - without a key make gives a clear refusal; before that, a
models search is free); forget to ask for status after a video (make returns
only a request_id and it takes minutes - poll with action=status).

ALSO ASKED AS (Hinglish asks this skill answers): kya naya video model aaya
hai jo better ho, zoo mein naya model dhoondo, kaunsa image model accha hai
