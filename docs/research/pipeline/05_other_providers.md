# Pipeline research 05 - other providers for models not on OpenRouter (read 16 Nov 2026)

For `docs/HOOLA_PIPELINE_PLAN.md` D11 ("WE WILL GET IT FROM OTHER LLM PROVIDERS LIKE OPENROUTER"). Read live by a
research agent. Open model lists read: fal (`api.fal.ai/v1/models?q=`), AIML API (`api.aimlapi.com/models`, 998),
DeepInfra, Novita, AIHubMix, Eden AI (`api.edenai.run/v2/info/provider_subfeatures`), Kie.ai (`docs.kie.ai/llms.txt`),
Hugging Face (`api/models?expand[]=inferenceProviderMapping`). Replicate + WaveSpeed checked by page address only.
Not readable without an account key: Together, Fireworks, SiliconFlow, Runware, Segmind. Azure / Bedrock / Vertex not
checked model by model.

## The providers
| Provider | Model list | Use inside Hoola (their terms) | Billing | Region |
|---|---|---|---|---|
| **fal.ai** | open, no key | end users may use it "through the Customer Solution"; must "not expose any of the Services APIs directly to any End Users"; no "resell... or sublicense" - **fits the Box** (Hoola calls it, users never see the API) | prepaid USD credits, expire 365 days, no refunds | worldwide, US-embargoed countries out |
| **Kie.ai** | open docs index | terms silent on resale (already used by Hoola Cinema) | prepaid credits that "never expire", refunds possible | none stated |
| **Eden AI** | open | terms page 404 - **read before use** | not checked | not checked |
| **WaveSpeedAI** | per-model pages | licence "non-sublicensable", docs licence "internal, non-commercial purposes" - **written permission needed before use** | prepaid, no refunds | Singapore / Hong Kong law barred list; India not named |
| Replicate | web; API with key | may not "make available any Services to any person"; some models have extra terms | postpaid or prepaid (12 months) | US-embargoed out |
| AIML API | open (998 models) | not addressed | subscription / usage, no refunds | none stated |
| DeepInfra / Novita / AIHubMix (AIHubMix already a Hoola provider) / HF Inference | open | not checked | not checked | not checked |

None names India as restricted.

## Missing model -> route
| Model | Route |
|---|---|
| Sarvam Saaras v3, Sarvam Bulbul | **vendor only** (`api.sarvam.ai`; also self-host via AWS Marketplace / SageMaker) |
| Bodhan Indic Transcribe | **vendor only** (`api.bodhan.ai/v1`, OpenAI-style) |
| Amazon Transcribe | Eden AI (`amazon`), or AWS |
| Azure Speech | Eden AI (`microsoft`), or Azure |
| Fonada Kapture v3 | no API found |
| AI4Bharat IndicConformer | open weights only (self-host) |
| ElevenLabs Scribe v3 | ElevenLabs direct (`scribe_v3`); aggregators have v2 only |
| Alibaba Fun-Realtime-ASR | Alibaba Model Studio direct |
| Zoom Scribe | Zoom direct |
| Cartesia Sonic 3.6 | Cartesia direct; Together has Sonic 3 / 3.5 (older, unscored) |
| Maya 2 Native | Maya direct (open weights, reported Apache-2.0); Maya 1 on fal, deprecated |
| Inworld TTS 1.5 Max | fal `fal-ai/inworld-tts`, DeepInfra `inworld-ai/inworld-tts-1.5-max`, AIML `inworld/tts-1-5-max` |
| Hume Octave | **treat as gone** (Hume's TTS reported shut 13 Nov 2026) |
| Qwen-Audio 3.1 TTS Plus | Alibaba direct; 3.0 versions on AIHubMix / fal / AIML |
| ACE-Step | fal `fal-ai/ace-step`, DeepInfra, Replicate; "ACE Music v1" not found anywhere |
| Suno v6 | **Kie.ai** (`V6`, `V6_MINI`); Suno has no official API |
| Mureka V9.5 | fal `mureka/v9.5/generate/song`, AIML `mureka/v9.5` |
| Lyria 3.5 | fal `google/lyria-3.5`, Replicate |
| ElevenLabs Music v2.5 | fal `elevenlabs/music/v2.5`, AIML `elevenlabs/eleven_music_v2_5` |
| Stable Audio 3 | fal `fal-ai/stable-audio-3/medium/text-to-audio` |
| Riffusion FUZZ | no official API (unofficial resellers only - not used) |
| Kling Image 4.0 | not found anywhere |
| Reve 2.1 | fal `reve/2.1/text-to-image` (fal's search did not return it - check first); Reve direct |
| Ideogram 4 | fal `ideogram/v4` |
| SkyReels V4 | **WaveSpeed only** `skywork-ai/skyreels-v4/text-to-video` |
| Utopai X, Muse Video | no API |
| HiDream-O1-Video | vendor only, approval needed |
| Vidu Q3 Pro | Replicate `vidu/q3-pro`, WaveSpeed; fal has Vidu Q3 (Pro tier unconfirmed) |
| PixVerse V5.6 | fal `fal-ai/pixverse/v5.6/text-to-video` |
| Sora 2 Pro | fal `fal-ai/sora-2/text-to-video/pro`, AIHubMix `sora-2-pro` |
| Luma Ray3 | Luma direct; aggregators carry Ray 3.2 (unscored) |
| PaddleOCR-VL-1.6, MinerU2.5-Pro, MiniCPM-OCR | open weights only (older PaddleOCR-VL 0.9B on DeepInfra / Novita / AIHubMix) |
| GLM-OCR | AIML `zhipu/glm-ocr`, AIHubMix `glm-ocr`, HF `zai-org/GLM-OCR` |

## Recommended set
1. **fal.ai** - widest cover (~14 of the missing), open list, terms fit the Box.
2. **Kie.ai** - the only route for Suno v6; already in Hoola.
3. **Eden AI** - Amazon Transcribe + Azure Speech behind one key; terms to read first.
4. **WaveSpeedAI** - only after written permission (adds SkyReels V4; backup for Sora 2 Pro / Ideogram 4 / Mureka).

Still vendor-only: Sarvam, Bodhan, Scribe v3, Fun-ASR, Zoom Scribe, Cartesia Sonic 3.6, Maya 2, Qwen-Audio 3.1,
HiDream, Luma Ray3. No route: Fonada Kapture, Kling Image 4.0, Utopai X, Muse Video, Riffusion, Hume Octave.

## Direct makers (D12, owner 16 Nov: "WE WILL KEEP THERE API DIRECTLY")
One key each, VPS .env only. Speech in: Bodhan (`api.bodhan.ai/v1`), Sarvam (`api.sarvam.ai`), Maya Research, Gnani,
Microsoft Azure (or via Eden), OpenAI (GPT Live Transcribe). Speech out: Cartesia (`sonic-3.6`; Sonic 3 / 3.5 also on
Together), Maya Research, Murf, Gnani, Smallest AI, Mirai Minds, Chariot, TeenageWorks, Sarvam, Google (Gemini 2.5 Pro
TTS, Chirp 3 HD), Microsoft (MAI Voice 1). Others vendor-only from research 05: ElevenLabs Scribe v3, Alibaba Fun-ASR,
Zoom Scribe, Qwen-Audio 3.1, Luma Ray3, HiDream-O1 (approval needed). Each maker's terms are read before its key goes in.
