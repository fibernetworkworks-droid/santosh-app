---
name: cs-zoo-radar
description: Zoo expansion radar - catalog first, never invented ids
when_to_use: new AI model, better model, which model, image model, video model, model list, compare AI models, latest model
---
GOAL: she asks "naya ya better model?" ya zoo search khaali aata hai - tab
CATALOG pehle, radar baad mein. The zoo is a 436-model BYOK catalog
(zoo_catalog.json: 186 image, 221 video, 29 audio; gateways muapi 211 + kie
225). Jo catalog mein nahi, woh zoo mein NAHI hai - invented model id se make
kabhi nahi. Roz-marra kaam curated studios (video_studio, photo_banao,
create_studio) se hi; zoo tab jab koi khaas model/style/aspect chahiye.

THE RADAR FAMILIES (awesome-generative-ai ke vetted names - yeh SEARCH TERMS
hain, model ids nahi; zoo action=models ke q= mein inhe daalo):
- IMAGE: flux, nano-banana, seedream, ideogram, stable diffusion / sdxl,
  imagen, recraft, dall-e
- VIDEO: kling, sora, runway, luma, pika, hailuo / minimax, wan, veo, seedance
- AUDIO: suno, udio, stable audio, elevenlabs, whisper, kokoro, xtts, bark
- TEXT/AGENTS: gpt, claude, gemini, llama, qwen, deepseek, mistral - par chat
  brain ka kaam zoo nahi karta; zoo sirf image/video/audio models ka hai.

THE PROTOCOL:
1. zoo action=models kind=image|video|audio, mode=t2i|i2i|t2v|i2v|t2s..., q=<
   family>. Catalog hi source of truth hai. Mil gaya? Wahin khatam - model_id
   catalog wala hi, aur aspect/resolution/duration SIRF catalog wali values
   (extra ke documented params alag se).
2. Nahi mila to family variants se 2-3 aur search (q=flux, q=flux pro...).
3. Phir bhi khaali? Model ka naam dena theek hai, par status honestly
   "unverified - zoo catalog mein nahi" bolo. "Zoo mein hai" jhooth nahi.
4. EXPANSION owner ke tap se hi: khud catalog edit karne ka door hai hi nahi.
   Owner ko append shape do (REAL zoo_catalog.json shape):
   {"id": "t2i:nano-banana", "name": "Nano Banana", "kind": "image",
    "mode": "t2i", "endpoint": "nano-banana", "aspects": ["1:1", "16:9", ...]}
   kie entry mein upar "gateway": "kie" aur endpoint uska apna naam. Gateway
   ka sawaal owner se poochho (Muapi ya kie serve karta hai?) - kabhi assume
   nahi. Badi private catalog ke liye HOOLA_ZOO_CATALOG ka zikr karo.
NEVER: invented model_id se make; catalog se bahar aspect/duration; key ka
intzaar bina make (ZOO_MUAPI_KEY / ZOO_KIE_KEY owner env mein - bina key make
clear refusal deta hai, usse pehle models search free hai); video ke baad
status na poochhna (make sirf request_id deta hai, minutes lagte hain -
action=status se poll).
