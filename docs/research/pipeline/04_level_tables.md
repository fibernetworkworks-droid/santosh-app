# Pipeline 04 - the first level tables (16 Nov 2026, for her approval)

Cut by hand from research 01-03 (`01_text.md`, `02_media_languages.md`, `03_indian_languages.md`). This is the FIRST
copy, for her to approve; once the feed is built (plan P0) the tables are cut by code from the same sources on a
schedule and these are replaced.

**Every model id below was checked against OpenRouter's `/api/v1/models?output_modalities=all` on 16 Nov 2026 (723
models) - all are listed.** Ids are in the key at the end.

Rules used to cut them:
- Order inside a level = leaderboard order; the Box still ranks by reliability -> speed -> score at run time (plan 4).
- **A level with no scored model uses the nearest filled level above it** (then below). A model on no board for that
  kind of work is not used for it (plan 8.2.4).
- Only models reachable through OpenRouter (her words: "INPUT WILL BE OPENROUTER"). Better models that are not on
  OpenRouter are listed under each table as "not reachable yet".

## The tables

| Kind | LOW | MID | HIGH | MAX | ULTRA | From |
|---|---|---|---|---|---|---|
| `route` | DeepSeek V4.1 Flash, Haiku 5.5 | Gemini 3.6 Flash, Gemini 4 Hydrogen | = `chat` HIGH | = `chat` MAX | = `chat` ULTRA | speed + chat |
| `plan` | Gemini 4 Hydrogen, Haiku 5.5 | Kimi K3.1 Pro, Grok 4.6 | Sonnet 5.5, GPT-6.1 Terra | Opus 5.5, Gemini 4 Argon | Fable 5.2, GPT-6 Astra | reasoning |
| `chat` | Gemini 4 Hydrogen, Haiku 5.5 | Gemini 3.8 Flash, Muse Spark 1.3 | Fable 5.1, GPT-6 Astra | Gemini 4 Argon, Opus 5.5, Muse Wonder | Gemini 4 Carbon, Fable 5.2 | Arena Text, AA, LiveBench |
| `write` | Gemini 4 Hydrogen, Haiku 5.5 | Gemini 3.8 Flash, Muse Spark 1.3 | Fable 5.1, GPT-6 Astra | Gemini 4 Argon, Opus 5.5, Muse Wonder | Gemini 4 Carbon, Fable 5.2 | same as chat |
| `summarise` | Haiku 5.5, Gemini 4 Hydrogen | Gemini 3.8 Flash, Sonnet 5.5 | Fable 5.1, Opus 5.5 | Kimi K3.1 Pro, Step 5 Preview | Kimi K3, Fable 5.2 | chat + long docs |
| `write.lang` (world) | Gemma 4 31B, Gemini 3.5 Flash-Lite | Qwen3.8 Max, GLM 5.3 Flash | Gemini 4 Hydrogen, Gemini 3.8 Flash | Fable 5.1, Opus 5.5 | Gemini 4 Carbon, Gemini 4 Argon | Arena non-English + per-language views |
| `write.lang` (Indian) **thin** | as world | as world | as world | as world | as world | Arena non-English only (no Indian board) |
| `translate` | as `write.lang` | | | | | same |
| `reason` | Gemini 4 Hydrogen, DeepSeek V4.1 Flash | Kimi K3.1 Pro, Grok 4.6 | Sonnet 5.5, Gemini 4 Carbon, GPT-6.1 Terra | GPT-6.1 Sol, Gemini 4 Argon, Opus 5.5 | Fable 5.2, GPT-6 Astra | LiveBench, FrontierMath |
| `research` | Gemini 3.5 Flash | Qwen3.8 Max, GPT-6.1 Terra | Fable 5.1, GPT-6 Sol | GPT-5.6 Sol, Gemini 4 Carbon, Opus 5.5 | GPT-6.1 Sol, GPT-6 Astra | Arena Search, FACTS Search, Vals |
| `facts` | Gemini 4 Hydrogen, GPT-6 Luna | GPT-6.1 Terra, Opus 5.5 | GPT-6 Astra, GPT-6.1 Sol | Gemini 4 Carbon, Gemini 4 Argon | Fable 5.2 | SimpleQA Verified, AA-Omniscience, FACTS |
| `check` | as `facts` | | | | | same |
| `extract` *(proxy)* | Gemini 4 Hydrogen, MiniMax M3 | GPT-6.1 Terra, Muse Wonder | GPT-6.1 Sol, Fable 5.2 | Gemini 4 Argon, GPT-6 Astra | Gemini 4 Carbon | LiveBench Data Analysis, IFBench |
| `read.long` | Haiku 5.5 | Sonnet 5.5, GPT-6 Astra | Fable 5.1, Opus 5.5, MiMo V2.6 Pro | Kimi K3.1 Pro, Step 5 Preview | Kimi K3, Fable 5.2 | AA-LCR, MLCR, Arena Document |
| `read.pdf` | Gemma 4 31B | Gemini 3.5 Flash | Gemini 3.8 Flash, Gemini 3.7 Flash | Fable 5, GPT-5.5 | Fable 5.1, Opus 5 | Arena Document |
| `read.image` | Gemma 4 31B, Gemini 3.5 Flash-Lite | GLM 5.3 Flash, GPT-5.5 | Qwen3.8 Max, Muse Spark 1.3 | Fable 5.1, Gemini 3.8 Flash | Fable 5, Opus 5.5 | Arena Vision |
| `tools` | Gemini 3.5 Flash, GLM 4.7 Flash | GLM 5.3, Qwen3.8 Max | Gemini 4 Carbon, Sonnet 5.5 | GPT-6 Astra, Fable 5.1, Opus 5.5 | Fable 5.2, Gemini 4 Argon | MCP Atlas, LiveBench Agentic, tau3 |
| `code` | DeepSeek V4.1 Flash | GPT-6.1 Terra, MiniMax M3.1 Flash | Sonnet 5.5, Fable 5.1, Qwen4 Max | Gemini 4 Carbon, GPT-6 Astra, Kimi K3.1 Pro | Fable 5.2, Opus 5.5 | Arena WebDev, SWE-Bench Pro V2, Terminal-Bench 4, LiveBench |
| `code.small` | as `code` | | | | | same |
| `image.make` | Nano Banana 2, Seedream 5.5 | MAI-Image-2.6, Grok Imagine Image 2 | GPT-Image-2, Nano Banana 2.1 | GPT-Image-2.6 Flare, GPT-Image-2.5 Flare | GPT-Image-2.6 Sunburst, GPT-Image-2.5 Sunburst | Arena T2I, AA |
| `image.edit` | MAI-Image-2.6 Flash | Seedream 5.5, Nano Banana 2.1, MAI-Image-2.6 | GPT-Image-2, Grok Imagine Image 2 | GPT-Image-2.5 Flare, GPT-Image-2.6 Flare | GPT-Image-2.5 Sunburst, GPT-Image-2.6 Sunburst | Arena Edit, AA |
| `video.make` | = MID (no scored small model) | Gemini Omni 1.1 Flash, HeyGen Video 1 | Seedance 2.0, FLUX 3 Video, Grok Imagine Video 1.5 | Wan 3.0 | Gemini Omni 1.2 Flash (text), Seedance 2.5 (picture) | Arena T2V / I2V, AA |
| `speech.in` (world) | Qwen3 ASR 1.7B, Voxtral Mini Transcribe 3 | Voxtral Small Transcribe 3, Gemini 3.5 Transcribe | Nemotron 3.5 Transcribe, Universal 3.5 Pro | Scribe v2, MAI-Transcribe-2 | GPT Transcribe, Muse Voice Transcribe | AA WER, Open ASR |
| `speech.in` (Indian) | Nemotron 3.5 Transcribe | GPT Transcribe, Scribe v2 | Gemini 3.8 Flash, Muse Voice Transcribe | Gemini 3.5 Transcribe | MAI-Transcribe-2 | voiceofindia STT (15 languages) + Open ASR Hindi |
| `speech.out` (world) | Gemini 3.8 Flash-Lite TTS, Gemini 3.1 Flash TTS | Qwen Audio 3.0 TTS Plus, MiniMax Speech 2.8 HD | Simba 3.5, Fish Drama 3 | Eleven v4 Turbo, Gemini 3.8 Flash TTS | Eleven v4 | AA TTS, TTS Arena |
| `speech.out` (Indian) | = MID | Gemini 3.8 Flash-Lite TTS | Gemini 3.1 Flash TTS | Gemini 3.8 Flash TTS | Eleven v4 | voiceofindia TTS (10 languages) |
| `music.make` | Lyria 3 Clip | Lyria 3 Pro | = MID | = MID | = MID | Music Arena, AA (only Lyria is on OpenRouter) |
| `embed` | not researched yet - Hoola keeps its current embedder | | | | | - |

**Per-language note for `write.lang` (world):** where a language has its own Arena view, its leader goes first in its
level - Chinese: Gemini 4 Hydrogen; Japanese / Korean: Fable 5.1; Spanish: Opus 5; French / German / Russian: Gemini 4
Argon / Carbon.

## Not reachable yet (better on a board, not on OpenRouter)
| Kind | Models |
|---|---|
| `read.pdf` | specialist OCR models (OXR-1.0, PaddleOCR-VL-1.6, MinerU2.5-Pro, GLM-OCR) - open weights, self-host |
| `video.make` | Utopai X, SkyReels V4, Muse Video, HiDream-O1 |
| `speech.in` | Alibaba Fun-Realtime-ASR, ElevenLabs Scribe v3, Azure Speech, Fonada Kapture-v3; Indian: Bodhan Indic Transcribe, Sarvam Saaras v3, Amazon Transcribe |
| `speech.out` | Cartesia Sonic 3.6, Qwen-Audio 3.1 TTS Plus, Inworld, Hume Octave, Gradium, Maya 2 Native |
| `music.make` | ACE Music v1, Suno v6, Mureka V9.5, Lyria 3.5, Eleven Music, Stable Audio 3, Riffusion FUZZ |
| `image.make` | Kling Image 4.0, Reve 2.1, Canva Craft |

## Weak spots (said plainly)
- **Indian-language text, translation and Hinglish:** no public board ranks current models. The Indian rows use the
  pooled non-English Arena view as a stand-in. See plan section 12.
- **`extract`:** no real board; proxy boards only.
- **Several numbers came through one aggregator (BenchLeader)** and were not checked on each board's own site.
- **Name matches guessed:** MiniMax H3 = hailuo-3 (left out of the video table for that reason).
- **Low-vote board entries** (GPT-Image-2.6, Gemini Omni 1.2) can move a lot week to week.

## Key: short name -> OpenRouter id
| Short name | Id | Short name | Id |
|---|---|---|---|
| Fable 5.2 | anthropic/claude-fable-5.2 | Fable 5.1 | anthropic/claude-fable-5.1 |
| Fable 5 | anthropic/claude-fable-5 | Opus 5.5 | anthropic/claude-opus-5.5 |
| Opus 5 | anthropic/claude-opus-5 | Sonnet 5.5 | anthropic/claude-sonnet-5.5 |
| Haiku 5.5 | anthropic/claude-haiku-5.5 | Gemini 4 Carbon | google/gemini-4-carbon |
| Gemini 4 Argon | google/gemini-4-argon | Gemini 4 Hydrogen | google/gemini-4-hydrogen |
| Gemini 3.8 Flash | google/gemini-3.8-flash | Gemini 3.7 Flash | google/gemini-3.7-flash |
| Gemini 3.6 Flash | google/gemini-3.6-flash | Gemini 3.5 Flash | google/gemini-3.5-flash |
| Gemini 3.5 Flash-Lite | google/gemini-3.5-flash-lite | Gemma 4 31B | google/gemma-4-31b-it |
| GPT-6 Astra | openai/gpt-6-astra | GPT-6.1 Sol | openai/gpt-6.1-sol |
| GPT-6 Sol | openai/gpt-6-sol | GPT-5.6 Sol | openai/gpt-5.6-sol |
| GPT-6.1 Terra | openai/gpt-6.1-terra | GPT-6 Luna | openai/gpt-6-luna |
| GPT-5.5 | openai/gpt-5.5 | Muse Wonder | meta/muse-wonder |
| Muse Spark 1.3 | meta/muse-spark-1.3 | Kimi K3 | moonshotai/kimi-k3 |
| Kimi K3.1 Pro | moonshotai/kimi-k3.1-pro | Grok 4.6 | x-ai/grok-4.6 |
| Qwen4 Max | qwen/qwen4-max | Qwen3.8 Max | qwen/qwen3.8-max-0902 |
| GLM 5.3 | z-ai/glm-5.3 | GLM 5.3 Flash | z-ai/glm-5.3-flash |
| GLM 4.7 Flash | z-ai/glm-4.7-flash | DeepSeek V4.1 Flash | deepseek/deepseek-v4.1-flash-1017 |
| MiniMax M3.1 Flash | minimax/minimax-m3.1-flash | MiniMax M3 | minimax/minimax-m3 |
| Step 5 Preview | stepfun/step-5-preview | MiMo V2.6 Pro | xiaomi/mimo-v2.6-pro |
| GPT-Image-2.6 Sunburst | openai/gpt-image-2.6-sunburst | GPT-Image-2.5 Sunburst | openai/gpt-image-2.5-sunburst |
| GPT-Image-2.6 Flare | openai/gpt-image-2.6-flare | GPT-Image-2.5 Flare | openai/gpt-image-2.5-flare |
| GPT-Image-2 | openai/gpt-image-2 | Nano Banana 2.1 | google/gemini-nano-banana-2.1 |
| Nano Banana 2 | google/gemini-3.1-flash-image | MAI-Image-2.6 | microsoft/mai-image-2.6 |
| MAI-Image-2.6 Flash | microsoft/mai-image-2.6-flash | Grok Imagine Image 2 | x-ai/grok-imagine-image-2.0 |
| Seedream 5.5 | bytedance-seed/seedream-5-5 | Gemini Omni 1.2 Flash | google/gemini-omni-1.2-flash |
| Gemini Omni 1.1 Flash | google/gemini-omni-1.1-flash | Seedance 2.5 | bytedance/seedance-2.5 |
| Seedance 2.0 | bytedance/seedance-2.0 | Wan 3.0 | alibaba/wan-3.0 |
| FLUX 3 Video | black-forest-labs/flux-3-video | Grok Imagine Video 1.5 | x-ai/grok-imagine-video-1.5 |
| HeyGen Video 1 | heygen/heygen-video-1 | GPT Transcribe | openai/gpt-transcribe |
| Muse Voice Transcribe | meta/muse-voice-transcribe-1.0 | Scribe v2 | elevenlabs/scribe-v2 |
| MAI-Transcribe-2 | microsoft/mai-transcribe-2 | Nemotron 3.5 Transcribe | nvidia/nemotron-3.5-transcribe |
| Universal 3.5 Pro | assemblyai/universal-3-5-pro | Voxtral Small Transcribe 3 | mistralai/voxtral-small-transcribe-3-0 |
| Gemini 3.5 Transcribe | google/gemini-3.5-transcribe | Qwen3 ASR 1.7B | qwen/qwen3-asr-1.7b |
| Voxtral Mini Transcribe 3 | mistralai/voxtral-mini-transcribe-3-0 | Eleven v4 | elevenlabs/eleven-v4 |
| Eleven v4 Turbo | elevenlabs/eleven-v4-turbo | Gemini 3.8 Flash TTS | google/gemini-3.8-flash-tts |
| Gemini 3.8 Flash-Lite TTS | google/gemini-3.8-flash-lite-tts | Gemini 3.1 Flash TTS | google/gemini-3.1-flash-tts-preview |
| Simba 3.5 | speechify/simba-3.5 | Fish Drama 3 | fish-audio/drama-3 |
| Qwen Audio 3.0 TTS Plus | qwen/qwen-audio-3.0-tts-plus | MiniMax Speech 2.8 HD | minimax/speech-2.8-hd |
| Lyria 3 Pro | google/lyria-3-pro-preview | Lyria 3 Clip | google/lyria-3-clip-preview |
