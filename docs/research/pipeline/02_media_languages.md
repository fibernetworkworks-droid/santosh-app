# Pipeline research 02 - pictures, documents, images, video, speech, music, languages (read 16 Nov 2026)

For `docs/HOOLA_PIPELINE_PLAN.md` section 8. Read live by a research agent on 16 Nov 2026.

**Main source:** LMArena's own data feed, the Hugging Face dataset `lmarena-ai/leaderboard-dataset` (CC-BY-4.0, modified
2026-11-16, boards published 2026-11-09 to 11-12). The arena.ai pages are behind Cloudflare and could not be fetched.
Others: Artificial Analysis (AA), HF Open ASR Leaderboard, TTS Arena V2, voiceofindia.ai, Music Arena, OmniDocBench.
OpenRouter ids checked against `/api/v1/models?output_modalities=all` (723 models).

**OpenRouter note:** plain `/models` lists only text-output models; add `?output_modalities=image|video|audio|all` for
the rest (outputs: image, video, speech, transcription, audio, embeddings, rerank, decisions). No Sarvam model is on
OpenRouter.

## 1. Reading images (`read.image`) - LMArena Vision
| # | Model | Rating | OpenRouter id |
|---|---|---|---|
| 1 | Claude Fable 5 (High) | 1326 (OCR 1337) | anthropic/claude-fable-5 |
| 2 | Claude Opus 5.5 (High) | 1324 | anthropic/claude-opus-5.5 |
| 3 | Claude Fable 5.1 (Max) | 1322 | anthropic/claude-fable-5.1 |
| 4 | Claude Opus 4.7 | 1319 | anthropic/claude-opus-4.7 |
| 6 | Gemini 3.8 Flash (High) | 1317 (OCR 1332, diagram 1353) | google/gemini-3.8-flash |
| 11 | Qwen3.8-Max | 1312 | qwen/qwen3.8-max-0902 |
| 12 | Muse Spark 1.3 (Max) | 1310 | meta/muse-spark-1.3 |
| 22 / 24 | GPT-5.5 / GLM-5.3-Flash | 1296 / 1295 | openai/gpt-5.5, z-ai/glm-5.3-flash |
| 36 / 42 / 45 | Gemma 4 31B / Qwen3.8-27B / Gemini 3.5 Flash-Lite | 1279 / 1270 / 1268 | google/gemma-4-31b-it, qwen/qwen3.8-27b, google/gemini-3.5-flash-lite |

MMMU: stale (last updated 09/05/2025, no rows shown).

Proposed: ULTRA Fable 5, Opus 5.5 · MAX Fable 5.1, Gemini 3.8 Flash · HIGH Qwen3.8-Max, Muse Spark 1.3 · MID
GLM-5.3-Flash, GPT-5.5 · LOW Gemma 4 31B, Gemini 3.5 Flash-Lite.

## 2. Reading PDFs / documents (`read.pdf`) - LMArena Document
| Model | Rating | OpenRouter id |
|---|---|---|
| Claude Fable 5.1 (Max) | 1515 (#1) | anthropic/claude-fable-5.1 |
| Claude Opus 5 (High) | 1509 | anthropic/claude-opus-5 |
| Claude Opus 4.6 (High) | 1508 | anthropic/claude-opus-4.6 |
| Claude Fable 5 | 1497 | anthropic/claude-fable-5 |
| GPT-5.5 (High) | 1484 | openai/gpt-5.5 |
| Gemini 3.8 Flash (High) | 1482 | google/gemini-3.8-flash |
| Gemini 3.7 Flash (High) | 1476 | google/gemini-3.7-flash |
| Gemini 3.5 Flash (High) | 1462 | google/gemini-3.5-flash |
| Gemma 4 31B | 1434 (#35) | google/gemma-4-31b-it |

OmniDocBench v1.7 (raw parsing, README 2026-11-12): small specialist OCR models lead (OXR-1.0 97.03, TeleOCR 96.91,
OvisOCR2 96.47, MiniCPM-OCR 1.0 96.44, PaddleOCR-VL-1.6 96.34, MinerU2.5-Pro 95.75, GLM-OCR 95.22); best general models
tested Gemini 3 Pro 92.91, GPT-5.2 86.59 (newer frontier models untested). None of the OCR specialists is on OpenRouter
(open weights, self-host). OmniDocBench's dataset is "for research purposes only and not for commercial use".

Proposed: ULTRA Fable 5.1, Opus 5 · MAX Fable 5, GPT-5.5 · HIGH Gemini 3.8 Flash, Gemini 3.7 Flash · MID Gemini 3.5
Flash · LOW Gemma 4 31B (or a self-hosted OCR model for plain text extraction).

## 3. Making images (`image.make`)
| Model | LMArena T2I | AA T2I | OpenRouter id |
|---|---|---|---|
| GPT-Image-2.5 Sunburst | 1429 (#1) | 1229 (#2) | openai/gpt-image-2.5-sunburst |
| GPT-Image-2.6 Sunburst | 1406 | 1261 (#1) | openai/gpt-image-2.6-sunburst |
| GPT-Image-2.5 / 2.6 Flare | 1398 / 1384 | 1210 / 1227 | openai/gpt-image-2.5-flare, openai/gpt-image-2.6-flare |
| GPT-Image-2 | 1382 | 1192 | openai/gpt-image-2 |
| MAI-Image-2.6 | 1330 | 1168 | microsoft/mai-image-2.6 |
| Nano Banana 2.1 | 1327 | 1176 | google/gemini-nano-banana-2.1 |
| Grok Imagine Image 2.0 | 1318 | 1167 | x-ai/grok-imagine-image-2.0 |
| Kling Image 4.0 (preview) | - | 1180 | not on OpenRouter (Kling API) |
| Reve 2.1 / Canva Craft | 1301 / - | - / 1158 | not on OpenRouter |
| Seedream 5.5 / Nano Banana 2 | - | 1134 / 1143 | bytedance-seed/seedream-5-5, google/gemini-3.1-flash-image |

Proposed: ULTRA GPT-Image-2.6 / 2.5 Sunburst · MAX GPT-Image-2.6 / 2.5 Flare · HIGH GPT-Image-2, Nano Banana 2.1 · MID
MAI-Image-2.6, Grok Imagine 2.0 · LOW Nano Banana 2, Seedream 5.5.

## 4. Editing images (`image.edit`)
| Model | LMArena Edit | AA Edit | OpenRouter id |
|---|---|---|---|
| GPT-Image-2.5 Sunburst | 1519 (#1) | 1202 | openai/gpt-image-2.5-sunburst |
| GPT-Image-2.5 Flare | 1484 | 1185 | openai/gpt-image-2.5-flare |
| GPT-Image-2.6 Sunburst | 1476 | 1211 (#1) | openai/gpt-image-2.6-sunburst |
| MAI-Image-2.7-Preview | 1471 | 1197 | not on OpenRouter (2.6 is) |
| GPT-Image-2 | 1462 | 1140 | openai/gpt-image-2 |
| Grok Imagine Image 2.0 | 1437 | - | x-ai/grok-imagine-image-2.0 |
| MAI-Image-2.6 | 1428 | 1150 | microsoft/mai-image-2.6 |
| Nano Banana 2.1 | 1427 | 1152 | google/gemini-nano-banana-2.1 |
| Seedream 5.5 / Krea 3 Ultra / MAI-2.6-Flash | - | 1160 / 1154 / 1145 | bytedance-seed/seedream-5-5, krea/k3-edit (match unconfirmed), microsoft/mai-image-2.6-flash |

Proposed: ULTRA GPT-Image-2.5 / 2.6 Sunburst · MAX GPT-Image-2.5 / 2.6 Flare · HIGH GPT-Image-2, Grok Imagine 2.0 · MID
Seedream 5.5, Nano Banana 2.1, MAI-Image-2.6 · LOW MAI-Image-2.6-Flash, krea/k3-edit.

## 5. Making video (`video.make`)
| Model | LMArena T2V | LMArena I2V | AA T2V (audio) | AA I2V | OpenRouter id |
|---|---|---|---|---|---|
| Gemini Omni 1.2 Flash | 1540 (#1) | 1503 (#1) | 1151 | - | google/gemini-omni-1.2-flash |
| Gemini Omni 1.1 Flash | 1513 | 1487 | - | - | google/gemini-omni-1.1-flash |
| Dreamina Seedance 2.5 | 1479 | 1494 | 1156 | 1161 (#1) | bytedance/seedance-2.5 |
| Seedance 2.0 | 1483 | 1480 | 1133 | 1141 | bytedance/seedance-2.0 |
| Wan 3.0 | 1476 | 1482 | 1174 (#1) | 1109 | alibaba/wan-3.0 |
| MiniMax H3 | - | 1493 | 1159 | 1134 | minimax/hailuo-3 (match unconfirmed) |
| FLUX 3 Video | 1491 | - | 1136 | - | black-forest-labs/flux-3-video |
| Grok Imagine Video 1.5 | 1488 | 1453 | - | - | x-ai/grok-imagine-video-1.5 |
| HeyGen Video 1 | - | - | 1149 | 1124 | heygen/heygen-video-1 |
| Utopai X, SkyReels V4, Muse Video, HiDream-O1 | - | - | 1168 / 1134 | 1151 / 1125 | not on OpenRouter |

Proposed: ULTRA Gemini Omni 1.2 Flash (text-to-video), Seedance 2.5 (image-to-video) · MAX Wan 3.0, MiniMax H3 · HIGH
Seedance 2.0, FLUX 3 Video, Grok Imagine Video 1.5 · MID Gemini Omni 1.1 Flash, HeyGen Video 1 · LOW none scored (the
lite / fast variants on OpenRouter - bytedance/seedance-2.0-mini, x-ai/grok-imagine-video-1.5-lite, google/veo-3.1-fast -
have no board score).

## 6. Speech to text (`speech.in`)
| Model | AA WER (en) | Open ASR multilingual avg | Open ASR Hindi WER | OpenRouter id |
|---|---|---|---|---|
| Fun-Realtime-ASR-preview (Alibaba) | 1.7 % (#1) | - | - | not on OpenRouter |
| ElevenLabs Scribe v3 / v2 | 1.9 / 2.2 % | - | - / 8.45 | v3 not on OpenRouter; elevenlabs/scribe-v2 |
| MAI-Transcribe-2 | 2.0 % | - | - | microsoft/mai-transcribe-2 |
| Voxtral Small / Mini Transcribe 3 | 2.1 / 2.2 % | - | - | mistralai/voxtral-small-transcribe-3-0, mistralai/voxtral-mini-transcribe-3-0 |
| Grok Voice Transcribe 2.0 | 2.3 % | - | - | x-ai/grok-stt-2.0 (match unconfirmed) |
| Gemini 3.5 Transcribe | 2.6 % | - | - | google/gemini-3.5-transcribe |
| Azure Speech 09-2026 | - | 3.27 (#1) | 9.14 | not on OpenRouter (Azure) |
| OpenAI gpt-transcribe | - | 4.20 | 8.59 | openai/gpt-transcribe |
| AssemblyAI Universal-3.5 Pro | - | 4.31 | 12.45 | assemblyai/universal-3-5-pro |
| Nemotron-3.5-Transcribe | - | 4.50 | 9.60 | nvidia/nemotron-3.5-transcribe |
| Meta Muse Voice Transcribe | - | 5.49 | 7.16 | meta/muse-voice-transcribe-1.0 |
| Fonada Kapture-v3 | - | - | 6.54 (#1 Hindi) | not on OpenRouter |
| AI4Bharat IndicConformer-600M | - | - | 8.78 | open weights, self-host |
| Qwen3-ASR-1.7B | - | 5.94 | - | qwen/qwen3-asr-1.7b |

English Open ASR leader: zoom/scribe_v2.1_pro (4.87 avg WER), not on OpenRouter. Sarvam claims Saaras v3 beats Gemini /
GPT-4o on IndicVoices - company's own figure; not on OpenRouter.

Proposed: ULTRA gpt-transcribe, muse-voice-transcribe (best Hindi on OpenRouter) · MAX scribe-v2, mai-transcribe-2 ·
HIGH nemotron-3.5-transcribe, universal-3-5-pro · MID voxtral-small-transcribe-3, gemini-3.5-transcribe · LOW
qwen3-asr-1.7b, voxtral-mini-transcribe-3.

## 7. Text to speech (`speech.out`)
| Model | AA TTS (en) | voiceofindia Hindi | TTS Arena V2 | OpenRouter id |
|---|---|---|---|---|
| Eleven v4 / v4 Turbo | 1340 / 1340 | 1119 (#1) | - | elevenlabs/eleven-v4, elevenlabs/eleven-v4-turbo |
| Qwen-Audio-3.1-TTS-Plus | 1298 | - | - | not on OpenRouter (3.0-plus is: qwen/qwen-audio-3.0-tts-plus, 1265) |
| Cartesia Sonic 3.6 | 1295 | 1100 | - | not on OpenRouter |
| Speechify Simba 3.5 | 1291 | - | - | speechify/simba-3.5 |
| Gemini 3.8 Flash TTS | 1283 | 1101 | - | google/gemini-3.8-flash-tts |
| Fish Audio Drama 3 | 1277 | - | - | fish-audio/drama-3 |
| Gemini 3.8 Flash-Lite TTS | 1259 | 1071 | - | google/gemini-3.8-flash-lite-tts |
| Gemini 3.1 Flash TTS | - | 1084 | - | google/gemini-3.1-flash-tts-preview |
| Inworld TTS MAX, Hume Octave, Gradium | - | - | 1567 / 1551 / 1588 (prelim) | not on OpenRouter |
| MiniMax Speech 2.8 HD | - | - | 1545 (prelim) | minimax/speech-2.8-hd |

TTS Arena V2's #1 and #2 are anonymous "stealth" models; its main board is English only, its Hindi board not live yet.

Proposed: ULTRA eleven-v4 · MAX eleven-v4-turbo, gemini-3.8-flash-tts · HIGH simba-3.5, fish drama-3 · MID
qwen-audio-3.0-tts-plus, minimax speech-2.8-hd · LOW gemini-3.8-flash-lite-tts, gemini-3.1-flash-tts-preview.

## 8. Music (`music.make`)
| Model | AA vocal | Music Arena (to 2026-07-31) instr / vocal | OpenRouter id |
|---|---|---|---|
| ACE Music v1 | 1160 (#1) | - | not on OpenRouter |
| Suno v6 / v6-mini | 1144 / 1132 | - | not on OpenRouter (no official API found) |
| Mureka V9.5 / V9 | 1101 / 1063 | - | not on OpenRouter |
| Lyria 3.5 / 3 Pro | 1050 / 1048 | Lyria 3 Pro 1394 (#1) / 1107 (#2) | google/lyria-3-pro-preview (3.5 not on OpenRouter) |
| Eleven Music v2.5 | 1016 | v1: 1055 / 998 | not on OpenRouter |
| Stable Audio 3 Medium | - | 1333 / - | not on OpenRouter |
| Riffusion FUZZ v1.0 | - | 1225 / 1132 (#1) | not on OpenRouter |
| Lyria 3 Clip | - | 1003 / 1019 | google/lyria-3-clip-preview |

Proposed: ULTRA ACE Music v1, Suno v6 · MAX Mureka V9.5 · HIGH Lyria 3.5, Lyria 3 Pro (the only top model reachable on
OpenRouter) · MID Eleven Music v2.5, Stable Audio 3 · LOW Lyria 3 Clip, ACE-Step 1.5 Turbo (open weights).

## 9. Languages (`write.lang`, `translate`)
LMArena Text (2026-11-11) language filters: non_english, spanish, chinese, french, german, japanese, korean, russian,
polish. **No Hindi / Indian language, no Arabic, no Portuguese.**

| Board | Top models (rating) |
|---|---|
| Non-English | Gemini 4 Carbon 1534, Gemini 4 Argon 1523, Fable 5.1 1507, Opus 5.5 1503, Opus 5 Max 1500, Gemini 4 Hydrogen 1495, Gemini 3.8 Flash 1492, Muse Wonder 1491 |
| Spanish | Opus 5 Max 1522, Fable 5.1 1510, Opus 5.5 1510, Gemini 4 Argon 1508 |
| Chinese | Gemini 4 Hydrogen 1631, Carbon 1613, Argon 1605, Fable 5.1 1582 |
| French / German | Gemini 4 Argon 1553 / 1582, then Opus 5 / Fable 5.1 |
| Japanese / Korean | Fable 5.1 1560 / 1505, Opus 5.5, Gemini 4 Argon |
| Russian | Gemini 4 Carbon 1560, Argon 1539 |
| AA multilingual (Global-MMLU-Lite: incl. Hindi, Bangla, Arabic, Portuguese) | All: Gemini 3.1 Pro Preview 93; Hindi: Gemini 3.1 Pro 94, Opus 4.6 92 - looks stale (no Gemini 4 / Fable) |
| MILU (10 Indic languages, via llm-stats.com) | only Anthropic's self-reported: Fable 5.2 0.941, Opus 5.5 0.931, Sonnet 5.5 0.916, Haiku 5.5 0.876 |

Proposed (non-English board): ULTRA Gemini 4 Carbon, Gemini 4 Argon · MAX Fable 5.1, Opus 5.5 · HIGH Gemini 4 Hydrogen,
Gemini 3.8 Flash · MID Qwen3.8-Max (1475), GLM-5.3-Flash (1462) · LOW Gemma 4 31B (1430), Gemini 3.5 Flash-Lite (1427).

## Sources and their terms
| Source | URL | Live | Last update | Data feed | Reuse terms |
|---|---|---|---|---|---|
| LMArena feed | huggingface.co/datasets/lmarena-ai/leaderboard-dataset | yes | 2026-11-16 | parquet: vision, document, text by language, T2I, edit, T2V, I2V, video edit | CC-BY-4.0 |
| LMArena site | arena.ai | blocked (Cloudflare) | - | api.lmarena.ai unreachable | not read |
| Artificial Analysis | artificialanalysis.ai | yes | no dates | free API with key ("Attribution is required"), paid data platform | site: "personal, noncommercial use", no commercial exploitation, no scraping - use the API |
| HF Open ASR | huggingface.co/spaces/hf-audio/open_asr_leaderboard | yes | v1.16.0, 13-11-2026 | Gradio `/config`; CSV repos private | not found |
| TTS Arena V2 | huggingface.co/spaces/TTS-AGI/TTS-Arena-V2 | yes | 2026-11-11 | JSON `/api/leaderboard?type=tts` | not found |
| voiceofindia.ai (arena.ai4bharat.org redirects) | voiceofindia.ai/leaderboards | yes, TTS only | live, 44,405 votes | none found | not found |
| Music Arena | beta.music-arena.org | yes | votes to 2026-07-31 | HF dataset music-arena/music-arena-dataset | CC-BY-4.0 |
| OmniDocBench | github.com/opendatalab/OmniDocBench | yes | 2026-11-12 | README tables | research only, not commercial |
| MMMU | mmmu-benchmark.github.io | stale | 09/05/2025 | none | CC BY-SA 4.0 |
| MILU | llm-stats.com/benchmarks/milu; HF ai4bharat/MILU (CC-BY-4.0, gated) | yes | 2026-11-16 | none | aggregator terms not read |
| Sarvam evals | news only | - | Feb 2026 | none | self-reported |

## Caveats
- **Indian languages are barely covered, almost nothing independent:** no public text board ranks Hindi, Marathi,
  Tamil, Telugu, Bengali, Gujarati, Kannada, Malayalam, Punjabi or Hinglish with current models; LMArena has no Indian
  filter; AA multilingual covers only Hindi + Bangla and looks months old; MILU has only self-reported numbers; the
  AI4Bharat Indic LLM Arena now redirects to voiceofindia.ai (TTS only); IndicGenBench / IndicXTREME / IN22 are static
  paper benchmarks; no current Indic translation board; Hinglish has no benchmark at all.
- Most usable Indian sources: Open ASR Hindi breakdown (speech-to-text), voiceofindia.ai (TTS, ~10 Indic languages),
  MILU as a test set to run on a shortlist (text).
- Some board -> OpenRouter name matches are guesses (MiniMax H3 ~ hailuo-3, Grok Voice Transcribe 2.0 ~ grok-stt-2.0,
  Krea 3 Ultra ~ k3-edit).
- "(High)" / "(Max)" are settings of one model, not separate OpenRouter ids.
- Newer models may be missing from boards (Fable 5.2, Haiku 5.5 not on the Vision board).
- Video boards disagree (LMArena: Gemini Omni first; AA with-audio: Wan 3.0 first).
- Low-vote entries are noisy (GPT-Image-2.6 ~2.7k votes, Gemini Omni 1.2 ~1.7k).
- Many top music / speech models are not on OpenRouter - the Box needs direct provider routes for those, or the level
  table falls back to what OpenRouter has.
