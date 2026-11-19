# Hoola worker atlas: models and prices for every kind of work (18 Nov 2026)

Owner's ask: "FIND THE PERFECT HOOLA POWERFULL MODELS EVERY FIELD WITH ATLIST 20 MODELS WITH PRISING COMPARISION ... FOR WORKER". Follows `07_worker_models.md` (when to use workers). Nothing in Hoola changes until she picks; the parity card (running since 22:24 IST) comes first.

> **Correction, 19 Nov:** the prices on this page use one list price per model. Hoola pays whichever provider answers (it asks for the fastest), which can be up to 19x more; GLM-5.3 costs Rs 0.22-4.16 a step, DeepSeek V4.1 Flash Rs 0.61 at its maker (not Rs 0.10). Live prices and the measured worker card: `09_worker_prices_live.md`.

## How to read it

- "Points" are arena ratings: people compare two answers without seeing the names. 100 points apart = the higher one wins about 64% of the time; under 10 points apart is a tie.
- "Rs / step" = one worker step that reads 20,000 tokens and writes 800, at the OpenRouter list price and Rs 88 to the dollar. A worker job is usually 5-20 steps. Code and long answers write more, so cheap output matters there.
- "$ per job" (agent board) is the median cost of one whole job measured by LMArena, not an estimate.
- Each model is shown once at its best effort setting. "#" is its place on the whole board, so gaps in the numbers are models already shown or merged. Rows under the line are cheaper models from further down, and the picks.
- Picks: Main = best value; Backup = another company for when the main one fails; Premium = only for hard jobs or when she pins it; Budget = cheapest that still does the job. Nothing changes in Hoola until she says so.

## The answer: one pick per field

| Field | Main (best value) | Backup | Premium (hard / pinned) | Budget | Hoola today |
|---|---|---|---|---|---|
| Coworker / AI employee: long jobs with tools | GPT-6.1 Terra ($0.872/job · Rs 2.11/step) | Hy4 ($0.572/job · Rs 0.82/step) | Claude Opus 5.5 ($5.65/job · Rs 8.45/step) | MiMo-V2.6-Pro ($0.16/job · Rs 0.83/step) | Box picked Claude Sonnet 4.6 / Opus 4.6 in her test |
| Computer use: working a PC screen (Hoola PC / her PC) | MiMo-V2.6-Pro | Claude Sonnet 5 | Qwen3.8-Max | MiMo-V2.6-Flash | Qwen 3.8 27B + Sonnet rescue |
| Coding: apps, websites, fixes | DeepSeek-V4.1-Flash (Rs 0.1/step) | MiMo-V2.6-Flash (Rs 0.27/step) | Claude Sonnet 5.5 (Rs 4.22/step) | Main is already the cheapest | Qwen 3.8 27B (Hoola Code) |
| Hard thinking and maths | Gemini 3.8 Flash (Rs 1.74/step) | GLM-5.3-Flash (Rs 0.3/step) | Gemini 4 Argon (Rs 4.22/step) | GLM-5.3 (Rs 0.22/step) | GLM-5.3 (writer) + pylab |
| Web research with sources | DeepSeek V4.1 Flash (not on this board) (Rs 0.1/step) | MiMo-V2.6-Pro (not on this board) (Rs 0.83/step) | Qwen3.8-Max (Rs 3.94/step) | Main is already the cheapest | the chat model inside the research engine |
| Facts without making things up (her data, RAG answers) | MiMo-V2.6-Pro (Rs 0.83/step) | Kimi K3.1 Pro (Rs 1.01/step) | Claude Opus 5.5 (Rs 8.45/step) | DeepSeek-V4.1-Flash (Rs 0.1/step) | DeepSeek V4.1 Flash (checker) |
| Exact instructions, tables, extraction | MiMo-V2.6-Pro (Rs 0.83/step) | GLM-5.3 (Rs 0.22/step) | Claude Opus 5.5 (Rs 8.45/step) | DeepSeek-V4.1-Flash (Rs 0.1/step) | the chat model |
| Writing: posts, emails, scripts | Gemini 3.8 Flash (Rs 1.74/step) | MiMo-V2.6-Pro (Rs 0.83/step) | Claude Opus 5.5 (Rs 8.45/step) | GLM-5.3 (Rs 0.22/step) | GLM-5.3 (writer) |
| Indian and other languages | Gemini 3.8 Flash (Rs 1.74/step) | MiMo-V2.6-Pro (Rs 0.83/step) | Claude Opus 5.5 (Rs 8.45/step) | GLM-5.3 (Rs 0.22/step) | GLM-5.3 (writer) |
| Everyday answers (overall) | MiMo-V2.6-Pro (Rs 0.83/step) | Gemini 3.8 Flash (Rs 1.74/step) | Claude Opus 5.5 (Rs 8.45/step) | GLM-5.3 (Rs 0.22/step) | GLM-5.3 (writer) |
| Fast and cheap: planner, router, quick checks | DeepSeek-V4.1-Flash (Rs 0.1/step) | GLM-5.3 (Rs 0.22/step) | GLM-5.3-Flash (Rs 0.3/step) | Hy3 (Rs 0.17/step) | LOW-level model from the Box tables |
| Long documents and long asks | MiMo-V2.6-Pro (Rs 0.83/step) | Gemini 3.8 Flash (Rs 1.74/step) | Claude Opus 5.5 (Rs 8.45/step) | GLM-5.3 (Rs 0.22/step) | GLM-5.3 (writer) |
| PDFs and documents | Gemini 3.8 Flash (Rs 1.74/step) | Muse Spark 1.3 (Rs 2.50/step) | Claude Opus 5 (Rs 10.6/step) | GPT-5.6 Luna (Rs 0.44/step) | the chat model |
| Pictures, screenshots, OCR | Gemini 3.8 Flash (Rs 1.74/step) | Muse Spark 1.3 (Rs 2.50/step) | Claude Opus 5.5 (Rs 8.45/step) | GLM-5.3-Flash (Rs 0.3/step) | the chat model |
| Making pictures | Grok Imagine Image 2.0 (≈Rs 1.41/picture) | Seedream 5.0 Pro (≈Rs 1.58/picture) | GPT-Image-2.5 Sunburst (≈Rs 3.41/picture) | Muse Image (≈Rs 0.35/picture) | Create engines (her price card) |
| Editing pictures | Muse Image (≈Rs 0.35/picture) | Grok Imagine Image 2.0 (≈Rs 1.41/picture) | GPT-Image-2.5 Sunburst (≈Rs 3.41/picture) | Muse Image (≈Rs 0.35/picture) | image_edit tool (local + Gemini / zoo) |
| Video from words | Gemini Omni 1.2 Flash (Rs 30.6 per 5 s (720p)) | Wan 3.0 (Rs 44.0 per 5 s (720p)) | Seedance 2.5 (Rs 250 per 5 s (1080p)) | Grok Imagine Video (Rs 30.8 per 5 s (720p)) | Video Studio (Hoola Auto, her price card) |
| Video from a picture | Gemini Omni 1.2 Flash (Rs 30.6 per 5 s (720p)) | MiniMax H3 (Rs 57.2 per 5 s (1080p)) | Seedance 2.5 (Rs 250 per 5 s (1080p)) | Grok Imagine Video (Rs 30.8 per 5 s (720p)) | Video Studio (Hoola Auto, her price card) |
| Editing video | Wan 3.0 (Rs 44.0 per 5 s (720p)) | Gemini Omni 1.2 Flash (Rs 30.6 per 5 s (720p)) | Seedance 2.5 (Rs 250 per 5 s (1080p)) | FLUX Video Edit (Rs 13.2 per 5 s (1080p)) | video_kit (ffmpeg, no AI model) |
| Talking avatar videos | HeyGen Avatar 6 Turbo (made) / own lab (live) | HeyGen Avatar IV | HeyGen Avatar 6 | own lab | Hoola Interactive lab (MuseTalk), not in production |
| Speech to text (Indian languages) | Saaras v3 (Sarvam) | MAI-Transcribe-2 | Indic Transcribe Core (Bodhan) | Nemotron 3.5 Transcribe | Whisper on own server (Kaan) |
| Text to speech (Indian voices) | Gemini 3.8 Flash TTS | Sonic-3.6 (Cartesia) | Eleven v4 | Gemini 3.8 Flash-Lite TTS | Gemini voices (calls) / Vocal studio engines |
| Live voice calls | Gemini Live (keep) | GPT-Live-1 | - | - | Gemini Live |
| Music | Lyria 3 Pro | Eleven Music | - | Lyria 3 Clip | Lyria (Create Music) |
| Embeddings: finding by meaning (memory, RAG) | Qwen3 Embedding 8B | Cohere Embed 5 Fast | Gemini Embedding 2 | Qwen3 Embedding 4B | own ONNX model (free) |
| Rerank: putting the best search results first | Cohere Rerank 5 Fast | Qwen3 Reranker 8B | Cohere Rerank 5 Pro | Qwen3 Reranker 0.6B | none |

## Proposed worker lists for the Box (`pipeline_workers`, W2)

| Worker kind | Main | Backup | Move up to |
|---|---|---|---|
| Long tool jobs (AI employee work) | GPT-6.1 Terra | Hy4 | Claude Opus 5.5 |
| Research notes (Hoola searches, the model reads) | DeepSeek V4.1 Flash | MiMo-V2.6-Pro | Qwen3.8-Max |
| Working out (sums, plans, comparisons) + pylab | Gemini 3.8 Flash | GLM-5.3-Flash | Gemini 4 Argon / Claude Opus 5 |
| Reading files, PDFs, pictures | Gemini 3.8 Flash | Muse Spark 1.3 | Claude Opus 5.5 |
| Tables, extraction, exact formats | MiMo-V2.6-Pro | DeepSeek V4.1 Flash | Claude Opus 5.5 |
| Code (only after the coding card) | DeepSeek V4.1 Flash | MiMo-V2.6-Flash | Claude Sonnet 5.5 |
| Planner, router, quick checks | DeepSeek V4.1 Flash | GLM-5.3 | - |

This updates the setup in `07_worker_models.md`: long tool jobs get their own list from the agent board, and code stays on Qwen 3.8 27B until DeepSeek passes Hoola's coding card.

## Key findings

1. **Price and quality are not linked.** In her 18 Nov test the Box gave helper parts to Claude Sonnet 4.6 and Opus 4.6. On these boards MiMo-V2.6-Pro scores 1492 on everyday answers against Sonnet 4.6's 1458, at Rs 0.83 a step against Rs 6.34.
2. **Two all-rounders cover most worker kinds.** MiMo-V2.6-Pro (Rs 0.83 a step: #12 of 350 overall, #10 on facts, 82% on OSWorld self-reported) and Gemini 3.8 Flash (Rs 1.74: #4 in maths, reads text in pictures as well as Claude Opus 5.5, reads PDFs, audio and video).
3. **For long tool jobs, the agent board is what counts.** GLM-5.3 (the writer) is #33 of 57 there and #54 at running commands. GPT-6.1 Terra is #10 at a measured $0.87 a job; Claude Opus 5.5 is #2 at $5.65; Fable 5.2 is #1 at $9.02.
4. **The cheapest worker that still works is DeepSeek V4.1 Flash.** Rs 0.10 a step: #17 of 131 at building web apps, the lowest measured rate of made-up facts. Right for planning, extraction, research notes and first drafts of code.
5. **In video, #1 is also cheap.** Gemini Omni 1.2 Flash leads both video boards and costs about Rs 31 for 5 seconds at 720p with sound; Seedance 2.5 at 1080p costs Rs 250 for the same 5 seconds.
6. **Pictures: one clear leader, one bargain.** GPT-Image-2.5 is best at about Rs 3.4 a picture. Muse Image edits at 1400 points for about Rs 0.35, roughly a tenth of the price.
7. **Memory search costs almost nothing.** Qwen3 Embedding 8B is the most cited multilingual leader (MTEB 70.58) at $0.01 per million tokens.
8. **Indian speech needs keys outside OpenRouter.** The best speech-to-text on Indian languages (Bodhan 3.39%, Sarvam Saaras v3 3.69% errors) is only on the makers' own APIs. Whisper, used today, is not rated on that board.
9. **Google models carry one risk.** Gemini 4 Carbon was refused ("is banned") on her OpenRouter account on 17 Nov. Every Gemini pick needs one test call first, and each has a backup from another company.
10. **What these boards do not tell.** They rate one answer as people judge it, not speed and not Hoola's own jobs. Hoola Code keeps Qwen 3.8 27B until DeepSeek passes the same coding card; the writer change waits for the parity card.

## Thinking and doing

### Coworker / AI employee: long jobs with tools

Many steps with tools (files, web, commands) until a job is finished. The board ranks 57 models on real multi-step jobs and measures the median cost of one job. Small columns = rank on four sub-boards (lower is better). Source: LMArena agent board (57 models) + 4 sub-boards.

Why these picks: GPT-6.1 Terra is #10 of 57 at a measured $0.87 a task, and among the best at not inventing tools (#6), following her (#5) and running commands (#4). Hy4 (another company) finishes jobs better than any model under Rs 1 a step. Today the Box picked Claude Sonnet 4.6 / Opus 4.6 for her test workers (rank about 30-40 here, 10-50x the price). GLM-5.3 is #33 and weak at commands (#54).

| # | Model | Maker | Board rank | $ per job | Rs / step | Finishes | No fake tools | Follows her | Commands | Pick |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Claude Fable 5.2 | anthropic | 1 | 9.02 | 16.9 | 1 | 6 | 1 | 3 |  |
| 2 | Claude Opus 5.5 | anthropic | 2 | 5.65 | 8.45 | 2 | 28 | 4 | 2 | Premium |
| 3 | Gemini 4 Carbon | google | 3 | 1.35 | 4.22 | 4 | 31 | 3 | 52 | Refused on her account |
| 4 | Claude Sonnet 5.5 | anthropic | 4 | 3.46 | 4.22 | 3 | 24 | 7 | 5 |  |
| 5 | Gemini 4 Hydrogen | google | 5 | 1.53 | 3.17 | 5 | 36 | 2 | 46 |  |
| 6 | Claude Fable 5.1 | anthropic | 6 | 7.83 | 21.1 | 6 | 27 | 9 | 11 |  |
| 7 | GPT-6 Astra | openai | 7 | 5.28 | 21.1 | 7 | 9 | 8 | 19 |  |
| 8 | GPT-6.1 Sol | openai | 9 | 0.985 | 4.22 | 10 | 3 | 10 | 26 |  |
| 9 | GPT-6.1 Terra | openai | 10 | 0.872 | 2.11 | 14 | 6 | 5 | 4 | Main |
| 10 | Gemini 4 Argon | google | 11 | 0.699 | 4.22 | 8 | 32 | 11 | 51 |  |
| 11 | Muse Wonder Full | meta | 13 | - | 8.45 | 11 | 39 | 20 | 18 |  |
| 12 | Qwen4-Max | alibaba | 14 | 1.47 | 2.81 | 13 | 21 | 19 | 29 |  |
| 13 | GPT-6 Sol | openai | 16 | 1.85 | 4.22 | 24 | 16 | 17 | 9 |  |
| 14 | Claude Fable 5 | anthropic | 17 | 3.33 | 21.1 | 20 | 29 | 21 | 10 |  |
| 15 | Claude Opus 5 | anthropic | 18 | 4.5 | 10.6 | 12 | 23 | 25 | 14 |  |
| 16 | Hy4 | tencent | 19 | 0.572 | 0.82 | 15 | 40 | 18 | 24 | Backup |
| 17 | Kimi K3.1 Pro | moonshot | 21 | 1.16 | 1.01 | 30 | 1 | 22 | 21 |  |
| 18 | GPT-5.6 Sol | openai | 22 | 1.59 | 8.45 | 32 | 10 | 23 | 8 |  |
| 19 | Inkling 2 Small | thinky | 23 | 0.256 | 0.6 | 21 | 48 | 16 | 32 |  |
| 20 | Grok 4.7 | xai | 24 | 3.2 | 3.94 | 19 | 17 | 44 | 16 |  |
|  | *cheaper ones further down* |  |  |  |  |  |  |  |  |  |
| 21 | Muse Ember | meta | 25 | 0.02 | 0.21 | 46 | 2 | 13 | 17 |  |
| 22 | MiMo-V2.6-Pro | xiaomi | 26 | 0.16 | 0.83 | 23 | 43 | 32 | 36 | Budget |
| 26 | DeepSeek-V4.1-Flash | deepseek | 30 | 0.141 | 0.1 | 31 | 38 | 24 | 35 |  |
| 27 | GPT-6 Luna | openai | 32 | 0.083 | 0.21 | 39 | 5 | 26 | 15 |  |
| 30 | Claude Haiku 5.5 | anthropic | 36 | 0.085 | 0.21 | 33 | 54 | 30 | 20 |  |
| 32 | MiMo-V2.6-Flash | xiaomi | 38 | 0.075 | 0.27 | 22 | 60 | 27 | 50 |  |
| 38 | GLM-5.3-Flash | zai | 45 | 0.143 | 0.3 | 35 | 11 | 48 | 62 |  |
| 46 | Hy3 | tencent | 54 | 0.083 | 0.17 | 57 | 61 | 47 | 61 |  |
| 28 | GLM-5.3 | zai | 33 | 0.86 | 0.22 | 29 | 13 | 42 | 54 | Hoola today |

### Computer use: working a PC screen (Hoola PC / her PC)

OSWorld-Verified: 361 real desktop tasks. Every number is SELF-REPORTED by the maker (leaderboard.steel.dev collects them); harnesses and step limits differ. Humans score about 72%. Source: OSWorld-Verified via leaderboard.steel.dev (23 entries).

Why these picks: MiMo-V2.6-Pro reports 82% at $0.43 / $0.87 - near Claude Fable 5 (85%) at 1/20th to 1/50th the price. Hoola PC code is FROZEN by the owner: nothing changes there without her word.

| # | Model / system | Maker | Tasks done | $ per M in / out | Rs / step | Pick |
|---|---|---|---|---|---|---|
| 1 | Qwen3.8-Max | Alibaba | 86.1% | 2 / 6 | 3.94 | Premium |
| 2 | Claude Mythos Preview | Anthropic | 85.4% | not on OpenRouter | - |  |
| 3 | Claude Mythos 5 | Anthropic | 85.0% | not on OpenRouter | - |  |
| 4 | Claude Fable 5 | Anthropic | 85.0% | 10 / 50 | 21.1 |  |
| 5 | Claude Opus 4.8 | Anthropic | 83.4% | 5 / 25 | 10.6 |  |
| 6 | MiMo-V2.6-Pro | Xiaomi | 82.0% | 0.435 / 0.87 | 0.83 | Main |
| 7 | Claude Sonnet 5 | Anthropic | 81.2% | 2 / 10 | 4.22 | Backup |
| 8 | MiMo-V2.6-Flash | Xiaomi | 80.8% | 0.14 / 0.28 | 0.27 | Budget |
| 9 | Claude Sonnet 4.6 | Anthropic | 78.5% | 3 / 15 | 6.34 |  |
| 10 | OSAgent (TheAGI, a system) | TheAGI | 76.26% | not on OpenRouter | - |  |
| 11 | GPT-5.4 | OpenAI | 75.0% | 2.5 / 15 | 5.46 |  |
| 12 | Claude Opus 4.6 | Anthropic | 72.7% | 5 / 25 | 10.6 |  |
| 13 | Claude Opus 4.5 | Anthropic | 66.3% | 5 / 25 | 10.6 |  |
| 14 | Kimi K2.5 | Moonshot | 63.3% | 0.5 / 2.5 | 1.06 |  |
| 15 | GLM-5V-Turbo | Zhipu | 62.3% | 1.2 / 4 | 2.39 |  |
| 16 | Claude Sonnet 4.5 | Anthropic | 61.4% | 3 / 15 | 6.34 |  |
| 17 | UiPath Screen Agent + GPT-5 (a system) | UiPath | 53.6% | not on OpenRouter | - |  |
| 18 | Claude Haiku 4.5 | Anthropic | 50.7% | 1 / 5 | 2.11 |  |
| 19 | Agent S2 + Claude 3.7 (a system) | Simular | 34.5% | not on OpenRouter | - |  |
| 20 | OpenAI Operator CUA (2025) | OpenAI | 32.6% | not on OpenRouter | - |  |
| 21 | Qwen3-VL-235B-A22B | Alibaba | 31.6% | not on OpenRouter | - |  |
| 22 | Qwen2.5 VL 72B | Alibaba | 8.8% | not on OpenRouter | - |  |
| 23 | Qwen2.5 VL 32B | Alibaba | 5.9% | not on OpenRouter | - |  |
| - | Qwen 3.8 27B (Hoola PC worker today) | Alibaba | 79-84% (aggregator sites, not this board) | 0.06 / 2.2 | 0.26 | Hoola today |

### Coding: apps, websites, fixes

Building web apps and fixing code (WebDev arena, people judge the running result). "Code chat" = the coding category of the text board. Source: LMArena webdev/overall (131 models rated).

Why these picks: DeepSeek V4.1 Flash is 165 points under the top for 1/85th of Opus 5.5's price and has the best code-chat score under Rs 1. MiMo-V2.6-Flash writes code at $0.28 per million out (code writes a lot). Qwen 3.8 27B (Hoola Code today) scored 11/12 on Hoola's own coding card; DeepSeek has not been put through that card yet - run it before any switch.

| # | Model | Maker | Points | Code chat | $ per M in / out | Rs / step | Reads | Pick |
|---|---|---|---|---|---|---|---|---|
| 1 | Claude Fable 5.2 | anthropic | 1826 | - | 8 / 40 | 16.9 | TIF |  |
| 2 | Claude Opus 5.5 | anthropic | 1816 | 1543 | 4 / 20 | 8.45 | TIF |  |
| 3 | Claude Sonnet 5.5 | anthropic | 1772 | 1501 | 2 / 10 | 4.22 | TIF | Premium |
| 4 | Gemini 4 Carbon | google | 1768 | 1564 | 2 / 10 | 4.22 | TIFAV | Refused on her account |
| 5 | GPT-6 Astra | openai | 1763 | 1494 | 10 / 50 | 21.1 | TIF |  |
| 6 | Qwen4-Max | alibaba | 1750 | - | 1.43 / 4.28 | 2.81 | TIV |  |
| 7 | Claude Fable 5.1 | anthropic | 1743 | 1527 | 10 / 50 | 21.1 | TIF |  |
| 8 | GPT-6.1 Sol | openai | 1742 | 1486 | 2 / 10 | 4.22 | TIF |  |
| 9 | Muse Wonder Full | meta | 1724 | 1516 | 4 / 20 | 8.45 | TIFAV |  |
| 10 | Gemini 4 Hydrogen | google | 1704 | 1516 | 1.5 / 7.5 | 3.17 | TIFAV |  |
| 11 | Claude Opus 5 | anthropic | 1691 | 1532 | 5 / 25 | 10.6 | TIF |  |
| 12 | Kimi K3.1 Pro | moonshot | 1686 | 1480 | 0.24 / 8.4 | 1.01 | TIV |  |
| 13 | GPT-6.1 Terra | openai | 1681 | - | 1 / 5 | 2.11 | TIF |  |
| 14 | Gemini 4 Argon | google | 1679 | 1540 | 2 / 10 | 4.22 | TIFAV |  |
| 15 | Qwen3.8-Max (0902) | alibaba | 1676 | 1502 | 2 / 6 | 3.94 | TIV |  |
| 16 | GPT-6 Sol | openai | 1673 | 1449 | 2 / 10 | 4.22 | TIF |  |
| 17 | DeepSeek-V4.1-Flash | deepseek | 1661 | 1504 | 0.036 / 0.5 | 0.1 | TI | Main |
| 18 | Kimi K3 | moonshot | 1658 | 1506 | 0.192 / 16 | 1.46 | TIV |  |
| 19 | Muse Spark 1.3 | meta | 1655 | 1509 | 1.25 / 4.25 | 2.50 | TIFV |  |
| 20 | Inkling 2 Small | thinky | 1645 | 1455 | 0.3 / 1 | 0.6 | TI |  |
|  | *cheaper ones further down* |  |  |  |  |  |  |  |
| 22 | MiMo-V2.6-Flash | xiaomi | 1639 | 1497 | 0.14 / 0.28 | 0.27 | TIAV | Backup |
| 27 | GLM-5.3 | zai | 1622 | 1499 | 0.07 / 1.4 | 0.22 | T |  |
| 31 | GLM-5.3-Flash | zai | 1609 | 1509 | 0.15 / 0.5 | 0.3 | TIV |  |
| 32 | Muse Ember | meta | 1608 | - | 0.1 / 0.5 | 0.21 | TIFAV |  |
| 33 | GLM-5.2 | zai | 1608 | 1488 | 0.007 / 6.8 | 0.49 | T |  |
| 34 | Claude Haiku 5.5 | anthropic | 1593 | 1454 | 0.1 / 0.5 | 0.21 | TIF |  |
| 35 | Qwen3.8-27B | alibaba | 1590 | 1479 | 0.06 / 2.2 | 0.26 | TIV | Hoola today |

### Hard thinking and maths

Maths and multi-step reasoning. "Hard asks" = the hard-prompts category. Source: LMArena text/math (334 models rated).

Why these picks: Gemini 3.8 Flash is #4 in maths at Rs 1.74 a step, above most Claude models. GLM-5.3 and GLM-5.3-Flash are 22-25 points under it at Rs 0.22-0.30. Every figure still goes through pylab. Gemini 4 Argon is #1 but its sibling Carbon was refused on her account - one test call first (else Claude Opus 5).

| # | Model | Maker | Points | Hard asks | $ per M in / out | Rs / step | Reads | Pick |
|---|---|---|---|---|---|---|---|---|
| 1 | Gemini 4 Argon | google | 1544 | 1542 | 2 / 10 | 4.22 | TIFAV | Premium |
| 2 | Claude Opus 5 | anthropic | 1532 | 1525 | 5 / 25 | 10.6 | TIF |  |
| 3 | Claude Fable 5.1 | anthropic | 1530 | 1527 | 10 / 50 | 21.1 | TIF |  |
| 4 | Gemini 3.8 Flash | google | 1525 | 1510 | 0.825 / 4.12 | 1.74 | TIFAV | Main |
| 5 | Claude Opus 5.5 | anthropic | 1520 | 1531 | 4 / 20 | 8.45 | TIF |  |
| 6 | Claude Opus 4.6 | anthropic | 1517 | 1524 | 5 / 25 | 10.6 | TIF |  |
| 7 | Claude Fable 5 | anthropic | 1516 | 1508 | 10 / 50 | 21.1 | TIF |  |
| 8 | Qwen3.8-Max | alibaba | 1509 | 1499 | 2 / 6 | 3.94 | TIV |  |
| 9 | Gemini 4 Hydrogen | google | 1507 | 1520 | 1.5 / 7.5 | 3.17 | TIFAV |  |
| 10 | Gemini 3.7 Flash | google | 1506 | 1498 | 0.75 / 3.75 | 1.58 | TIFAV |  |
| 11 | Gemini 3.6 Flash | google | 1505 | 1486 | 0.75 / 3.75 | 1.58 | TIFAV |  |
| 12 | Gemini 3.5 Flash | google | 1504 | 1489 | 1.5 / 9 | 3.27 | TIFAV |  |
| 13 | GLM-5.3-Flash | zai | 1503 | 1490 | 0.15 / 0.5 | 0.3 | TIV | Backup |
| 14 | GLM-5.3 | zai | 1500 | 1493 | 0.07 / 1.4 | 0.22 | T | Budget, Hoola today |
| 15 | Claude Opus 4.7 | anthropic | 1498 | 1506 | 5 / 25 | 10.6 | TIF |  |
| 16 | Muse Spark 1.3 | meta | 1498 | 1502 | 1.25 / 4.25 | 2.50 | TIFV |  |
| 17 | Kimi K3 | moonshot | 1496 | 1494 | 0.192 / 16 | 1.46 | TIV |  |
| 18 | MiMo-V2.6-Pro | xiaomi | 1495 | 1511 | 0.435 / 0.87 | 0.83 | TIAV |  |
| 19 | Qwen3.7-Max-Preview | alibaba | 1488 | 1482 | 1.48 / 4.42 | 2.91 | T |  |
| 20 | GPT-5.4 | openai | 1487 | 1485 | 2.5 / 15 | 5.46 | TIF |  |
|  | *cheaper ones further down* |  |  |  |  |  |  |  |
| 24 | GLM-5.2 | zai | 1483 | 1480 | 0.007 / 6.8 | 0.49 | T |  |
| 30 | DeepSeek-V4.1-Flash | deepseek | 1479 | 1483 | 0.036 / 0.5 | 0.1 | TI |  |
| 33 | Hy3 | tencent | 1477 | 1447 | 0.083 / 0.33 | 0.17 | T |  |
| 41 | Gemma 4 26B A4B | google | 1470 | 1439 | 0.09 / 0.3 | 0.18 | TIV |  |
| 43 | MiMo-V2.6-Flash | xiaomi | 1467 | 1468 | 0.14 / 0.28 | 0.27 | TIAV |  |
| 47 | Gemma 4 31B | google | 1462 | 1447 | 0.2 / 0.4 | 0.38 | TIV |  |

### Web research with sources

Models answering with their own web search tool. "Facts" = the search-factuality board. Source: LMArena search/overall (41 models rated).

Why these picks: This board rates models searching with their OWN search tool; the cheap models are not on it. Hoola searches and reads pages itself (research engine), so the worker only needs to read, note and not make things up: DeepSeek V4.1 Flash (lowest measured hallucination, Rs 0.10) and MiMo-V2.6-Pro (#10 on the facts board). Qwen3.8-Max is #1 here when a deep research job is worth Rs 3.94 a step.

| # | Model | Maker | Points | Facts | $ per M in / out | Rs / step | Reads | Pick |
|---|---|---|---|---|---|---|---|---|
| 1 | Qwen3.8-Max | alibaba | 1260 | 1243 | 2 / 6 | 3.94 | TIV | Premium |
| 2 | GPT-5.6 Sol | openai | 1258 | 1249 | 4 / 20 | 8.45 | TIF |  |
| 3 | Claude Opus 4.6 | anthropic | 1252 | 1227 | 5 / 25 | 10.6 | TIF |  |
| 4 | GPT-5.5 | openai | 1246 | 1246 | 5 / 30 | 10.9 | TIF |  |
| 5 | Claude Opus 5 | anthropic | 1239 | 1214 | 5 / 25 | 10.6 | TIF |  |
| 6 | Claude Fable 5.1 | anthropic | 1237 | 1214 | 10 / 50 | 21.1 | TIF |  |
| 7 | GPT-6 Astra | openai | 1231 | 1239 | 10 / 50 | 21.1 | TIF |  |
| 8 | GPT-6.1 Sol | openai | 1230 | 1237 | 2 / 10 | 4.22 | TIF |  |
| 9 | Claude Opus 4.7 | anthropic | 1230 | 1211 | 5 / 25 | 10.6 | TIF |  |
| 10 | Claude Fable 5 | anthropic | 1228 | 1212 | 10 / 50 | 21.1 | TIF |  |
| 11 | ERNIE 5.1 | baidu | 1227 | 1214 | not on OpenRouter | - |  |  |
| 12 | Claude Sonnet 4.6 | anthropic | 1221 | 1202 | 3 / 15 | 6.34 | TIF |  |
| 13 | Grok 4.5 | xai | 1216 | 1220 | 2 / 6 | 3.94 | TIF |  |
| 14 | Claude Opus 5.5 | anthropic | 1213 | 1206 | 4 / 20 | 8.45 | TIF |  |
| 15 | Gemini 3.1 Pro | google | 1210 | 1198 | 2 / 12 | 4.36 | TIFAV |  |
| 16 | GPT-5.2 | openai | 1207 | 1224 | 1.75 / 14 | 4.07 | TIF |  |
| 17 | Gemini 3 Pro | google | 1207 | 1193 | not on OpenRouter | - |  |  |
| 18 | Grok 4.20 Multi-Agent Beta (0309) | xai | 1205 | 1198 | not on OpenRouter | - |  |  |
| 19 | Claude Opus 4.8 | anthropic | 1202 | 1195 | 5 / 25 | 10.6 | TIF |  |
| 20 | GPT-5.1 | openai | 1199 | 1203 | 1.25 / 10 | 2.90 | TIF |  |
|  | *cheaper ones further down* |  |  |  |  |  |  |  |
| 30 | GPT-6 Luna | openai | 1160 | 1186 | 0.1 / 0.5 | 0.21 | TIF |  |

### Facts without making things up (her data, RAG answers)

People judge which answer is more correct on factual questions. Source: LMArena text_factuality/overall (160 models rated).

Why these picks: MiMo-V2.6-Pro is #10, 20 points under Opus 5.5, at 1/10th the price. DeepSeek (the checker today) is 37 points under the top at Rs 0.10.

| # | Model | Maker | Points | $ per M in / out | Rs / step | Reads | Pick |
|---|---|---|---|---|---|---|---|
| 1 | Gemini 4 Carbon | google | 1521 | 2 / 10 | 4.22 | TIFAV | Refused on her account |
| 2 | Claude Opus 5.5 | anthropic | 1505 | 4 / 20 | 8.45 | TIF | Premium |
| 3 | Claude Fable 5.1 | anthropic | 1499 | 10 / 50 | 21.1 | TIF |  |
| 4 | Gemini 4 Argon | google | 1497 | 2 / 10 | 4.22 | TIFAV |  |
| 5 | Muse Wonder | meta | 1494 | 4 / 20 | 8.45 | TIFAV |  |
| 6 | Gemini 4 Hydrogen | google | 1493 | 1.5 / 7.5 | 3.17 | TIFAV |  |
| 7 | Claude Opus 4.6 | anthropic | 1492 | 5 / 25 | 10.6 | TIF |  |
| 8 | Claude Opus 5 | anthropic | 1488 | 5 / 25 | 10.6 | TIF |  |
| 9 | GPT-5.5 | openai | 1485 | 5 / 30 | 10.9 | TIF |  |
| 10 | MiMo-V2.6-Pro | xiaomi | 1485 | 0.435 / 0.87 | 0.83 | TIAV | Main |
| 11 | GPT-5.4 | openai | 1484 | 2.5 / 15 | 5.46 | TIF |  |
| 12 | Claude Fable 5 | anthropic | 1483 | 10 / 50 | 21.1 | TIF |  |
| 13 | Gemini 3 Pro | google | 1482 | not on OpenRouter | - |  |  |
| 14 | Muse Spark 1.3 | meta | 1481 | 1.25 / 4.25 | 2.50 | TIFV |  |
| 15 | Qwen3.7-Max-Preview | alibaba | 1480 | 1.48 / 4.42 | 2.91 | T |  |
| 16 | Muse Spark 1.2 | meta | 1478 | 1.25 / 4.25 | 2.50 | TIFV |  |
| 17 | Gemini 3.5 Flash | google | 1478 | 1.5 / 9 | 3.27 | TIFAV |  |
| 18 | Claude Opus 4.7 | anthropic | 1478 | 5 / 25 | 10.6 | TIF |  |
| 19 | Kimi K3.1 Pro | moonshot | 1478 | 0.24 / 8.4 | 1.01 | TIV | Backup |
| 20 | GPT-5.6 Sol | openai | 1476 | 4 / 20 | 8.45 | TIF |  |
|  | *cheaper ones further down* |  |  |  |  |  |  |
| 31 | DeepSeek-V4.1-Flash | deepseek | 1468 | 0.036 / 0.5 | 0.1 | TI | Budget, Hoola today |
| 32 | GLM-5.3 | zai | 1468 | 0.07 / 1.4 | 0.22 | T |  |
| 36 | GPT-6 Luna | openai | 1466 | 0.1 / 0.5 | 0.21 | TIF |  |
| 41 | GLM-5.2 | zai | 1462 | 0.007 / 6.8 | 0.49 | T |  |
| 42 | GLM-5.3-Flash | zai | 1462 | 0.15 / 0.5 | 0.3 | TIV |  |
| 45 | GPT-5.6 Luna | openai | 1460 | 0.2 / 1.2 | 0.44 | TIF |  |

### Exact instructions, tables, extraction

The instruction-following category: formats, fields, exact rules. Source: LMArena text/instruction_following (350 models rated).

Why these picks: Tables, forms, exact formats: MiMo-V2.6-Pro #12, GLM-5.3 #17 at Rs 0.22, DeepSeek #26 at Rs 0.10.

| # | Model | Maker | Points | $ per M in / out | Rs / step | Reads | Pick |
|---|---|---|---|---|---|---|---|
| 1 | Gemini 4 Carbon | google | 1539 | 2 / 10 | 4.22 | TIFAV | Refused on her account |
| 2 | Gemini 4 Argon | google | 1536 | 2 / 10 | 4.22 | TIFAV |  |
| 3 | Claude Opus 5.5 | anthropic | 1535 | 4 / 20 | 8.45 | TIF | Premium |
| 4 | Claude Opus 4.6 | anthropic | 1521 | 5 / 25 | 10.6 | TIF |  |
| 5 | Claude Fable 5.1 | anthropic | 1520 | 10 / 50 | 21.1 | TIF |  |
| 6 | Gemini 4 Hydrogen | google | 1519 | 1.5 / 7.5 | 3.17 | TIFAV |  |
| 7 | Claude Opus 5 | anthropic | 1518 | 5 / 25 | 10.6 | TIF |  |
| 8 | Claude Fable 5 | anthropic | 1503 | 10 / 50 | 21.1 | TIF |  |
| 9 | Claude Opus 4.7 | anthropic | 1498 | 5 / 25 | 10.6 | TIF |  |
| 10 | Muse Wonder | meta | 1494 | 4 / 20 | 8.45 | TIFAV |  |
| 11 | Gemini 3.8 Flash | google | 1493 | 0.825 / 4.12 | 1.74 | TIFAV |  |
| 12 | MiMo-V2.6-Pro | xiaomi | 1492 | 0.435 / 0.87 | 0.83 | TIAV | Main |
| 13 | Claude Sonnet 5.5 | anthropic | 1487 | 2 / 10 | 4.22 | TIF |  |
| 14 | Gemini 3.7 Flash | google | 1485 | 0.75 / 3.75 | 1.58 | TIFAV |  |
| 15 | Kimi K3 | moonshot | 1484 | 0.192 / 16 | 1.46 | TIV |  |
| 16 | Qwen3.8-Max | alibaba | 1483 | 2 / 6 | 3.94 | TIV |  |
| 17 | GLM-5.3 | zai | 1483 | 0.07 / 1.4 | 0.22 | T | Backup |
| 18 | GPT-5.6 Sol | openai | 1483 | 4 / 20 | 8.45 | TIF |  |
| 19 | GLM-5.3-Flash | zai | 1480 | 0.15 / 0.5 | 0.3 | TIV |  |
| 20 | Muse Spark 1.3 | meta | 1479 | 1.25 / 4.25 | 2.50 | TIFV |  |
|  | *cheaper ones further down* |  |  |  |  |  |  |
| 26 | DeepSeek-V4.1-Flash | deepseek | 1473 | 0.036 / 0.5 | 0.1 | TI | Budget |
| 33 | GLM-5.2 | zai | 1467 | 0.007 / 6.8 | 0.49 | T |  |
| 46 | DeepSeek-V4-Pro (High, 20260813) | deepseek | 1448 | 0.111 / 4.44 | 0.51 | T |  |
| 49 | MiMo-V2.6-Flash | xiaomi | 1445 | 0.14 / 0.28 | 0.27 | TIAV |  |
| 55 | GPT-5.6 Luna | openai | 1437 | 0.2 / 1.2 | 0.44 | TIF |  |
| 60 | Gemma 4 31B | google | 1433 | 0.2 / 0.4 | 0.38 | TIV |  |

### Writing: posts, emails, scripts

The creative-writing category. Source: LMArena text/creative_writing (348 models rated).

Why these picks: Writing is mostly the writer's job, not a worker's. When a worker drafts (a long post, a script), Gemini 3.8 Flash is #9.

| # | Model | Maker | Points | $ per M in / out | Rs / step | Reads | Pick |
|---|---|---|---|---|---|---|---|
| 1 | Gemini 4 Argon | google | 1533 | 2 / 10 | 4.22 | TIFAV |  |
| 2 | Gemini 4 Carbon | google | 1533 | 2 / 10 | 4.22 | TIFAV | Refused on her account |
| 3 | Claude Opus 5.5 | anthropic | 1532 | 4 / 20 | 8.45 | TIF | Premium |
| 4 | Claude Fable 5.1 | anthropic | 1514 | 10 / 50 | 21.1 | TIF |  |
| 5 | Gemini 4 Hydrogen | google | 1509 | 1.5 / 7.5 | 3.17 | TIFAV |  |
| 6 | Claude Opus 4.6 | anthropic | 1504 | 5 / 25 | 10.6 | TIF |  |
| 7 | Claude Fable 5 | anthropic | 1494 | 10 / 50 | 21.1 | TIF |  |
| 8 | Claude Opus 5 | anthropic | 1494 | 5 / 25 | 10.6 | TIF |  |
| 9 | Gemini 3.8 Flash | google | 1493 | 0.825 / 4.12 | 1.74 | TIFAV | Main |
| 10 | Muse Wonder | meta | 1493 | 4 / 20 | 8.45 | TIFAV |  |
| 11 | Claude Opus 4.7 | anthropic | 1486 | 5 / 25 | 10.6 | TIF |  |
| 12 | Gemini 3.7 Flash | google | 1485 | 0.75 / 3.75 | 1.58 | TIFAV |  |
| 13 | Gemini 3.1 Pro Preview | google | 1483 | 2 / 12 | 4.36 | TIFAV |  |
| 14 | Qwen3.8-Max | alibaba | 1482 | 2 / 6 | 3.94 | TIV |  |
| 15 | Gemini 3 Pro | google | 1482 | not on OpenRouter | - |  |  |
| 16 | Gemini 3.5 Flash | google | 1471 | 1.5 / 9 | 3.27 | TIFAV |  |
| 17 | MiMo-V2.6-Pro | xiaomi | 1468 | 0.435 / 0.87 | 0.83 | TIAV | Backup |
| 18 | Muse Spark 1.3 | meta | 1467 | 1.25 / 4.25 | 2.50 | TIFV |  |
| 19 | Gemini 3.6 Flash | google | 1466 | 0.75 / 3.75 | 1.58 | TIFAV |  |
| 20 | Claude Sonnet 5.5 | anthropic | 1466 | 2 / 10 | 4.22 | TIF |  |
|  | *cheaper ones further down* |  |  |  |  |  |  |
| 22 | GLM-5.2 | zai | 1459 | 0.007 / 6.8 | 0.49 | T |  |
| 23 | GLM-5.3 | zai | 1459 | 0.07 / 1.4 | 0.22 | T | Budget, Hoola today |
| 33 | DeepSeek-V4-Pro | deepseek | 1446 | 0.111 / 4.44 | 0.51 | T |  |
| 37 | GLM-5.3-Flash | zai | 1442 | 0.15 / 0.5 | 0.3 | TIV |  |
| 43 | DeepSeek-V4.1-Flash | deepseek | 1438 | 0.036 / 0.5 | 0.1 | TI |  |
| 62 | Gemma 4 31B | google | 1415 | 0.2 / 0.4 | 0.38 | TIV |  |

### Indian and other languages

The non-English category (all languages together). Source: LMArena text/non_english (350 models rated).

Why these picks: LMArena has no Hindi or Indian-language board; this is its non-English board (all languages). For Indian speech see the speech sections below.

| # | Model | Maker | Points | $ per M in / out | Rs / step | Reads | Pick |
|---|---|---|---|---|---|---|---|
| 1 | Gemini 4 Carbon | google | 1534 | 2 / 10 | 4.22 | TIFAV | Refused on her account |
| 2 | Gemini 4 Argon | google | 1523 | 2 / 10 | 4.22 | TIFAV |  |
| 3 | Claude Fable 5.1 | anthropic | 1507 | 10 / 50 | 21.1 | TIF |  |
| 4 | Claude Opus 5.5 | anthropic | 1503 | 4 / 20 | 8.45 | TIF | Premium |
| 5 | Claude Opus 5 | anthropic | 1500 | 5 / 25 | 10.6 | TIF |  |
| 6 | Gemini 4 Hydrogen | google | 1495 | 1.5 / 7.5 | 3.17 | TIFAV |  |
| 7 | Gemini 3.8 Flash | google | 1492 | 0.825 / 4.12 | 1.74 | TIFAV | Main |
| 8 | Muse Wonder | meta | 1491 | 4 / 20 | 8.45 | TIFAV |  |
| 9 | Claude Opus 4.6 | anthropic | 1487 | 5 / 25 | 10.6 | TIF |  |
| 10 | Gemini 3.7 Flash | google | 1486 | 0.75 / 3.75 | 1.58 | TIFAV |  |
| 11 | Muse Spark 1.3 | meta | 1483 | 1.25 / 4.25 | 2.50 | TIFV |  |
| 12 | Claude Fable 5 | anthropic | 1482 | 10 / 50 | 21.1 | TIF |  |
| 13 | Claude Opus 4.7 | anthropic | 1481 | 5 / 25 | 10.6 | TIF |  |
| 14 | Muse Spark 1.2 | meta | 1478 | 1.25 / 4.25 | 2.50 | TIFV |  |
| 15 | Gemini 3.5 Flash | google | 1477 | 1.5 / 9 | 3.27 | TIFAV |  |
| 16 | Gemini 3.1 Pro Preview | google | 1476 | 2 / 12 | 4.36 | TIFAV |  |
| 17 | MiMo-V2.6-Pro | xiaomi | 1475 | 0.435 / 0.87 | 0.83 | TIAV | Backup |
| 18 | Qwen3.8-Max | alibaba | 1475 | 2 / 6 | 3.94 | TIV |  |
| 19 | Gemini 3 Pro | google | 1474 | not on OpenRouter | - |  |  |
| 20 | Qwen3.7-Max-Preview | alibaba | 1473 | 1.48 / 4.42 | 2.91 | T |  |
|  | *cheaper ones further down* |  |  |  |  |  |  |
| 28 | GLM-5.3 | zai | 1462 | 0.07 / 1.4 | 0.22 | T | Budget, Hoola today |
| 29 | GLM-5.3-Flash | zai | 1462 | 0.15 / 0.5 | 0.3 | TIV |  |
| 31 | GLM-5.2 | zai | 1458 | 0.007 / 6.8 | 0.49 | T |  |
| 37 | DeepSeek-V4.1-Flash | deepseek | 1450 | 0.036 / 0.5 | 0.1 | TI |  |
| 49 | DeepSeek-V4-Pro | deepseek | 1439 | 0.111 / 4.44 | 0.51 | T |  |
| 61 | Gemma 4 31B | google | 1430 | 0.2 / 0.4 | 0.38 | TIV |  |

### Everyday answers (overall)

The overall text board, every category together. Source: LMArena text/overall (350 models rated).

Why these picks: The overall board. MiMo-V2.6-Pro is 22 points under Opus 5.5 for 1/10th of the price; GLM-5.3 (the writer today) is 39 points under it for 1/38th.

| # | Model | Maker | Points | $ per M in / out | Rs / step | Reads | Pick |
|---|---|---|---|---|---|---|---|
| 1 | Gemini 4 Carbon | google | 1538 | 2 / 10 | 4.22 | TIFAV | Refused on her account |
| 2 | Gemini 4 Argon | google | 1529 | 2 / 10 | 4.22 | TIFAV |  |
| 3 | Claude Opus 5.5 | anthropic | 1514 | 4 / 20 | 8.45 | TIF | Premium |
| 4 | Claude Fable 5.1 | anthropic | 1512 | 10 / 50 | 21.1 | TIF |  |
| 5 | Claude Opus 5 | anthropic | 1507 | 5 / 25 | 10.6 | TIF |  |
| 6 | Muse Wonder | meta | 1503 | 4 / 20 | 8.45 | TIFAV |  |
| 7 | Gemini 4 Hydrogen | google | 1502 | 1.5 / 7.5 | 3.17 | TIFAV |  |
| 8 | Claude Opus 4.6 | anthropic | 1501 | 5 / 25 | 10.6 | TIF |  |
| 9 | Gemini 3.8 Flash | google | 1500 | 0.825 / 4.12 | 1.74 | TIFAV | Backup |
| 10 | Claude Fable 5 | anthropic | 1492 | 10 / 50 | 21.1 | TIF |  |
| 11 | Muse Spark 1.3 | meta | 1492 | 1.25 / 4.25 | 2.50 | TIFV |  |
| 12 | MiMo-V2.6-Pro | xiaomi | 1492 | 0.435 / 0.87 | 0.83 | TIAV | Main |
| 13 | Claude Opus 4.7 | anthropic | 1490 | 5 / 25 | 10.6 | TIF |  |
| 14 | Gemini 3.7 Flash | google | 1489 | 0.75 / 3.75 | 1.58 | TIFAV |  |
| 15 | Qwen3.8-Max | alibaba | 1485 | 2 / 6 | 3.94 | TIV |  |
| 16 | Muse Spark 1.2 | meta | 1483 | 1.25 / 4.25 | 2.50 | TIFV |  |
| 17 | Gemini 3.5 Flash | google | 1483 | 1.5 / 9 | 3.27 | TIFAV |  |
| 18 | Gemini 3.1 Pro Preview | google | 1480 | 2 / 12 | 4.36 | TIFAV |  |
| 19 | Gemini 3 Pro | google | 1480 | not on OpenRouter | - |  |  |
| 20 | Gemini 3.6 Flash | google | 1479 | 0.75 / 3.75 | 1.58 | TIFAV |  |
|  | *cheaper ones further down* |  |  |  |  |  |  |
| 22 | GLM-5.3 | zai | 1475 | 0.07 / 1.4 | 0.22 | T | Budget, Hoola today |
| 26 | GLM-5.3-Flash | zai | 1472 | 0.15 / 0.5 | 0.3 | TIV |  |
| 29 | GLM-5.2 | zai | 1469 | 0.007 / 6.8 | 0.49 | T |  |
| 35 | DeepSeek-V4.1-Flash | deepseek | 1464 | 0.036 / 0.5 | 0.1 | TI |  |
| 44 | DeepSeek-V4-Pro | deepseek | 1451 | 0.111 / 4.44 | 0.51 | T |  |
| 48 | MiMo-V2.6-Flash | xiaomi | 1451 | 0.14 / 0.28 | 0.27 | TIAV |  |

### Fast and cheap: planner, router, quick checks

Every model under Rs 0.60 a step, ordered by the overall chat board. "#" is the position on that whole board (350 models). Source: LMArena text/overall, filtered to <= Rs 0.60 a step.

Why these picks: The planner, router and quick checks run on every message, so price matters more than the last points. All of these are under Rs 0.30 a step.

| # | Model | Maker | Points | $ per M in / out | Rs / step | Reads | Pick |
|---|---|---|---|---|---|---|---|
| 22 | GLM-5.3 | zai | 1475 | 0.07 / 1.4 | 0.22 | T | Backup |
| 26 | GLM-5.3-Flash | zai | 1472 | 0.15 / 0.5 | 0.3 | TIV | Premium |
| 29 | GLM-5.2 | zai | 1469 | 0.007 / 6.8 | 0.49 | T |  |
| 35 | DeepSeek-V4.1-Flash | deepseek | 1464 | 0.036 / 0.5 | 0.1 | TI | Main |
| 44 | DeepSeek-V4-Pro | deepseek | 1451 | 0.111 / 4.44 | 0.51 | T |  |
| 48 | MiMo-V2.6-Flash | xiaomi | 1451 | 0.14 / 0.28 | 0.27 | TIAV |  |
| 62 | Gemma 4 31B | google | 1443 | 0.2 / 0.4 | 0.38 | TIV |  |
| 68 | Hy3 | tencent | 1439 | 0.083 / 0.33 | 0.17 | T | Budget |
| 73 | Qwen3.8-27B | alibaba | 1437 | 0.06 / 2.2 | 0.26 | TIV |  |
| 78 | Gemma 4 26B A4B | google | 1434 | 0.09 / 0.3 | 0.18 | TIV |  |
| 79 | DeepSeek-V4-Flash | deepseek | 1432 | 0.043 / 0.3 | 0.1 | T |  |
| 80 | GPT-5.6 Luna | openai | 1431 | 0.2 / 1.2 | 0.44 | TIF |  |
| 90 | DeepSeek-V3.2-Exp (Thinking) | deepseek | 1425 | 0.27 / 0.41 | 0.5 | T |  |
| 92 | DeepSeek-V3.2 | deepseek | 1425 | 0.26 / 0.38 | 0.48 | T |  |
| 93 | Beam 1.0 501B A23B | reflection | 1424 | 0.3 / 1 | 0.6 | T |  |
| 97 | Qwen3-VL-235B-A22B-Instruct | alibaba | 1420 | 0.21 / 1.9 | 0.5 | TI |  |
| 98 | DeepSeek-V3.1 | deepseek | 1420 | 0.25 / 0.95 | 0.51 | T |  |
| 101 | DeepSeek-V3.1-Terminus (Thinking) | deepseek | 1419 | 0.27 / 1 | 0.55 | T |  |
| 103 | Qwen3.5-122B-A10B | alibaba | 1417 | 0.26 / 2.08 | 0.6 | TIV |  |
| 105 | Qwen3-Next-80B-A3B-Instruct | alibaba | 1417 | 0.1 / 1.1 | 0.25 | T |  |
| 108 | Gemini 3.1 Flash-Lite Preview | google | 1416 | 0.25 / 1.5 | 0.55 | TIFAV |  |
| 122 | MiniMax-M2.7 | minimax | 1405 | 0.21 / 0.84 | 0.43 | T |  |

## Reading files, pictures, long text

### Long documents and long asks

The "longer query" category: long questions, long pasted text. Source: LMArena text/longer_query (328 models rated).

Why these picks: Long asks: MiMo-V2.6-Pro (#11) and Gemini 3.8 Flash (#9) are within 25 points of Opus 5.5. All four read about 1M tokens.

| # | Model | Maker | Points | $ per M in / out | Rs / step | Reads | Pick |
|---|---|---|---|---|---|---|---|
| 1 | Gemini 4 Carbon | google | 1549 | 2 / 10 | 4.22 | TIFAV | Refused on her account |
| 2 | Gemini 4 Argon | google | 1547 | 2 / 10 | 4.22 | TIFAV |  |
| 3 | Claude Opus 5.5 | anthropic | 1528 | 4 / 20 | 8.45 | TIF | Premium |
| 4 | Gemini 4 Hydrogen | google | 1524 | 1.5 / 7.5 | 3.17 | TIFAV |  |
| 5 | Claude Fable 5.1 | anthropic | 1523 | 10 / 50 | 21.1 | TIF |  |
| 6 | Claude Opus 4.6 | anthropic | 1518 | 5 / 25 | 10.6 | TIF |  |
| 7 | Claude Opus 5 | anthropic | 1516 | 5 / 25 | 10.6 | TIF |  |
| 8 | Claude Fable 5 | anthropic | 1510 | 10 / 50 | 21.1 | TIF |  |
| 9 | Gemini 3.8 Flash | google | 1508 | 0.825 / 4.12 | 1.74 | TIFAV | Backup |
| 10 | Claude Opus 4.7 | anthropic | 1506 | 5 / 25 | 10.6 | TIF |  |
| 11 | MiMo-V2.6-Pro | xiaomi | 1503 | 0.435 / 0.87 | 0.83 | TIAV | Main |
| 12 | Muse Wonder | meta | 1497 | 4 / 20 | 8.45 | TIFAV |  |
| 13 | Gemini 3.7 Flash | google | 1494 | 0.75 / 3.75 | 1.58 | TIFAV |  |
| 14 | Qwen3.8-Max | alibaba | 1493 | 2 / 6 | 3.94 | TIV |  |
| 15 | Kimi K3 | moonshot | 1490 | 0.192 / 16 | 1.46 | TIV |  |
| 16 | Muse Spark 1.3 | meta | 1489 | 1.25 / 4.25 | 2.50 | TIFV |  |
| 17 | Claude Sonnet 5.5 | anthropic | 1487 | 2 / 10 | 4.22 | TIF |  |
| 18 | GLM-5.3 | zai | 1486 | 0.07 / 1.4 | 0.22 | T | Budget, Hoola today |
| 19 | Claude Opus 4.8 | anthropic | 1484 | 5 / 25 | 10.6 | TIF |  |
| 20 | Gemini 3.5 Flash | google | 1484 | 1.5 / 9 | 3.27 | TIFAV |  |
|  | *cheaper ones further down* |  |  |  |  |  |  |
| 24 | GLM-5.3-Flash | zai | 1481 | 0.15 / 0.5 | 0.3 | TIV |  |
| 28 | GLM-5.2 | zai | 1479 | 0.007 / 6.8 | 0.49 | T |  |
| 34 | DeepSeek-V4.1-Flash | deepseek | 1474 | 0.036 / 0.5 | 0.1 | TI |  |
| 48 | DeepSeek-V4-Pro | deepseek | 1458 | 0.111 / 4.44 | 0.51 | T |  |
| 50 | MiMo-V2.6-Flash | xiaomi | 1455 | 0.14 / 0.28 | 0.27 | TIAV |  |
| 59 | Qwen3.8-27B | alibaba | 1446 | 0.06 / 2.2 | 0.26 | TIV |  |

### PDFs and documents

Questions about an uploaded document. Source: LMArena document/overall (40 models rated).

Why these picks: Only 40 models are rated on documents and the cheapest models are not among them. Gemini 3.8 Flash is #7 and reads PDF files directly, at 1/6th of Opus 5's price.

| # | Model | Maker | Points | $ per M in / out | Rs / step | Reads | Pick |
|---|---|---|---|---|---|---|---|
| 1 | Claude Fable 5.1 | anthropic | 1515 | 10 / 50 | 21.1 | TIF |  |
| 2 | Claude Opus 5 | anthropic | 1509 | 5 / 25 | 10.6 | TIF | Premium |
| 3 | Claude Opus 4.6 | anthropic | 1508 | 5 / 25 | 10.6 | TIF |  |
| 4 | Claude Fable 5 | anthropic | 1497 | 10 / 50 | 21.1 | TIF |  |
| 5 | Claude Opus 4.7 | anthropic | 1496 | 5 / 25 | 10.6 | TIF |  |
| 6 | GPT-5.5 | openai | 1484 | 5 / 30 | 10.9 | TIF |  |
| 7 | Gemini 3.8 Flash | google | 1482 | 0.825 / 4.12 | 1.74 | TIFAV | Main |
| 8 | Claude Sonnet 4.6 | anthropic | 1482 | 3 / 15 | 6.34 | TIF |  |
| 9 | GPT-5.6 Sol | openai | 1480 | 4 / 20 | 8.45 | TIF |  |
| 10 | Gemini 3.7 Flash | google | 1476 | 0.75 / 3.75 | 1.58 | TIFAV |  |
| 11 | Claude Opus 4.8 | anthropic | 1475 | 5 / 25 | 10.6 | TIF |  |
| 12 | GPT-5.4 | openai | 1473 | 2.5 / 15 | 5.46 | TIF |  |
| 13 | Muse Spark 1.3 | meta | 1473 | 1.25 / 4.25 | 2.50 | TIFV | Backup |
| 14 | GPT-5.6 Terra | openai | 1468 | 2 / 12 | 4.36 | TIF |  |
| 15 | GPT-6 Astra | openai | 1467 | 10 / 50 | 21.1 | TIF |  |
| 16 | Claude Opus 4.5 (20251101) | anthropic | 1466 | 5 / 25 | 10.6 | TIF |  |
| 17 | Muse Spark 1.1 | meta | 1463 | 1.25 / 4.25 | 2.50 | TIFV |  |
| 18 | Gemini 3.5 Flash | google | 1462 | 1.5 / 9 | 3.27 | TIFAV |  |
| 19 | Claude Sonnet 5 | anthropic | 1460 | 2 / 10 | 4.22 | TIF |  |
| 20 | Gemini 3.6 Flash | google | 1456 | 0.75 / 3.75 | 1.58 | TIFAV |  |
|  | *cheaper ones further down* |  |  |  |  |  |  |
| 21 | GPT-5.6 Luna | openai | 1454 | 0.2 / 1.2 | 0.44 | TIF | Budget |
| 30 | Gemma 4 31B | google | 1434 | 0.2 / 0.4 | 0.38 | TIV |  |

### Pictures, screenshots, OCR

Understanding pictures. "OCR" = reading text in pictures. Source: LMArena vision/overall (145 models rated).

Why these picks: Gemini 3.8 Flash reads text in pictures (OCR 1332) as well as Claude Opus 5.5 (1332) at 1/5th the price. GLM-5.3-Flash (OCR 1303) is the cheapest good reader.

| # | Model | Maker | Points | Ocr | $ per M in / out | Rs / step | Reads | Pick |
|---|---|---|---|---|---|---|---|---|
| 1 | Claude Fable 5 | anthropic | 1326 | 1337 | 10 / 50 | 21.1 | TIF |  |
| 2 | Claude Opus 5.5 | anthropic | 1324 | 1332 | 4 / 20 | 8.45 | TIF | Premium |
| 3 | Claude Fable 5.1 | anthropic | 1322 | 1329 | 10 / 50 | 21.1 | TIF |  |
| 4 | Claude Opus 4.7 | anthropic | 1319 | 1328 | 5 / 25 | 10.6 | TIF |  |
| 5 | Claude Opus 5 | anthropic | 1317 | 1325 | 5 / 25 | 10.6 | TIF |  |
| 6 | Gemini 3.8 Flash | google | 1317 | 1332 | 0.825 / 4.12 | 1.74 | TIFAV | Main |
| 7 | Claude Opus 4.6 | anthropic | 1316 | 1326 | 5 / 25 | 10.6 | TIF |  |
| 8 | Gemini 3.7 Flash | google | 1313 | 1321 | 0.75 / 3.75 | 1.58 | TIFAV |  |
| 9 | Qwen3.8-Max | alibaba | 1312 | 1322 | 2 / 6 | 3.94 | TIV |  |
| 10 | Muse Spark 1.3 | meta | 1310 | 1320 | 1.25 / 4.25 | 2.50 | TIFV | Backup |
| 11 | Gemini 3.5 Flash | google | 1308 | 1315 | 1.5 / 9 | 3.27 | TIFAV |  |
| 12 | Muse Spark | meta | 1306 | 1307 | not on OpenRouter | - |  |  |
| 13 | Muse Spark 1.2 | meta | 1305 | 1312 | 1.25 / 4.25 | 2.50 | TIFV |  |
| 14 | Gemini 3 Pro | google | 1305 | 1310 | not on OpenRouter | - |  |  |
| 15 | GPT-5.4 | openai | 1301 | 1310 | 2.5 / 15 | 5.46 | TIF |  |
| 16 | Gemini 3.6 Flash | google | 1297 | 1309 | 0.75 / 3.75 | 1.58 | TIFAV |  |
| 17 | Gemini 3.1 Pro Preview | google | 1296 | 1304 | 2 / 12 | 4.36 | TIFAV |  |
| 18 | GPT-5.5 | openai | 1296 | 1305 | 5 / 30 | 10.9 | TIF |  |
| 19 | Claude Opus 4.8 | anthropic | 1295 | 1303 | 5 / 25 | 10.6 | TIF |  |
| 20 | GLM-5.3-Flash | zai | 1295 | 1303 | 0.15 / 0.5 | 0.3 | TIV | Budget |
|  | *cheaper ones further down* |  |  |  |  |  |  |  |
| 29 | Gemma 4 31B | google | 1279 | 1285 | 0.2 / 0.4 | 0.38 | TIV |  |
| 30 | DeepSeek-V4.1-Flash | deepseek | 1279 | 1284 | 0.036 / 0.5 | 0.1 | TI |  |
| 35 | Qwen3.8-27B | alibaba | 1270 | 1280 | 0.06 / 2.2 | 0.26 | TIV |  |
| 47 | Gemma 4 26B A4B | google | 1260 | 1268 | 0.09 / 0.3 | 0.18 | TIV |  |
| 48 | MiMo-V2.6-Flash | xiaomi | 1260 | 1273 | 0.14 / 0.28 | 0.27 | TIAV |  |
| 50 | GPT-5.6 Luna | openai | 1256 | 1263 | 0.2 / 1.2 | 0.44 | TIF |  |

## Making pictures and video

### Making pictures

People compare pictures made from the same words. Price = about one 1024 picture (approximate; makers price per picture or per image token). Source: LMArena text_to_image/overall (79 models rated).

Why these picks: GPT-Image-2.5 is clearly best (1428) at about Rs 3.4 a picture. Grok Imagine Image 2.0 is 110 points under it for about 1/3rd. Muse Image (1266) costs well under Rs 1.

| # | Model | Maker | Points | ≈ $ / picture | ≈ Rs / picture | Pick |
|---|---|---|---|---|---|---|
| 1 | GPT-Image-2.5 Sunburst | openai | 1428 | 0.039 | 3.41 | Premium |
| 2 | GPT-Image-2.6 Sunburst | openai | 1410 | 0.039 | 3.41 |  |
| 3 | GPT-Image-2.5 Flare | openai | 1400 | 0.039 | 3.41 |  |
| 4 | MAI-Image-2.7 | microsoft-ai | 1387 | 0.044 | 3.86 |  |
| 5 | GPT-Image-2 | openai | 1382 | 0.039 | 3.41 |  |
| 6 | GPT-Image-2.6 Flare | openai | 1375 | 0.039 | 3.41 |  |
| 7 | MAI-Image-2.6 | microsoft-ai | 1331 | 0.049 | 4.31 |  |
| 8 | Gemini Nano Banana 2.1 | google | 1328 | 0.039 | 3.41 |  |
| 9 | Grok Imagine Image 2.0 | xai | 1318 | 0.016 | 1.41 | Main |
| 10 | Reve 2.1 | reve | 1302 | not on OpenRouter | - |  |
| 11 | Reve 2.0 | reve | 1268 | not on OpenRouter | - |  |
| 12 | Muse Image | meta | 1266 | 0.004 | 0.35 | Budget |
| 13 | Gemini 3.1 Flash Image (nano-banana-2, Web Search) | google | 1256 | 0.077 | 6.81 |  |
| 14 | Qwen-Image-3.0-Pro | alibaba | 1254 | 0.016 | 1.41 |  |
| 15 | MAI-Image-2.5 | microsoft-ai | 1253 | 0.061 | 5.34 |  |
| 16 | Seedream 5.0 Pro | bytedance | 1249 | 0.018 | 1.58 | Backup |
| 17 | Gemini 3.1 Flash-Lite Image (nano-banana-2-lite) | google | 1249 | 0.039 | 3.41 |  |
| 18 | Gemini 3 Pro Image (nano-banana-pro, 2K) | google | 1246 | 0.155 | 13.6 |  |
| 19 | GPT-Image-1.5 (High Fidelity) | openai | 1236 | not on OpenRouter | - |  |
| 20 | Qwen-Image-2.1 | alibaba | 1227 | 0.014 | 1.25 |  |
| 21 | Ideogram 4.0 (Quality) | ideogram | 1199 | not on OpenRouter | - |  |
| 22 | MiniMax H3-Image | minimax | 1198 | 0.0049 | 0.43 |  |

### Editing pictures

People compare edits of the same picture. Source: LMArena image_edit/overall (58 models rated).

Why these picks: Muse Image edits nearly as well as it does everything (1400, #12) at the lowest price of any rated editor. GPT-Image-2.5 is 119 points above it for about 10x.

| # | Model | Maker | Points | ≈ $ / picture | ≈ Rs / picture | Pick |
|---|---|---|---|---|---|---|
| 1 | GPT-Image-2.5 Sunburst | openai | 1519 | 0.039 | 3.41 | Premium |
| 2 | GPT-Image-2.5 Flare | openai | 1484 | 0.039 | 3.41 |  |
| 3 | GPT-Image-2.6 Sunburst | openai | 1481 | 0.039 | 3.41 |  |
| 4 | MAI-Image-2.7 | microsoft-ai | 1475 | 0.044 | 3.86 |  |
| 5 | GPT-Image-2 | openai | 1462 | 0.039 | 3.41 |  |
| 6 | GPT-Image-2.6 Flare | openai | 1461 | 0.039 | 3.41 |  |
| 7 | Grok Imagine Image 2.0 | xai | 1437 | 0.016 | 1.41 | Backup |
| 8 | MAI-Image-2.6 | microsoft-ai | 1427 | 0.049 | 4.31 |  |
| 9 | Gemini Nano Banana 2.1 | google | 1427 | 0.039 | 3.41 |  |
| 10 | Krea 3 Ultra | krea | 1412 | not on OpenRouter | - |  |
| 11 | MAI-Image-2.5 | microsoft-ai | 1400 | 0.061 | 5.34 |  |
| 12 | Muse Image | meta | 1400 | 0.004 | 0.35 | Main, Budget |
| 13 | Seedream 5.0 Pro | bytedance | 1392 | 0.018 | 1.58 |  |
| 14 | Grok Imagine Image (Quality, 20260519) | xai | 1391 | not on OpenRouter | - |  |
| 15 | Gemini 3 Pro Image (nano-banana-pro, 2K) | google | 1391 | 0.155 | 13.6 |  |
| 16 | ChatGPT Image Latest (High Fidelity, 20251216) | openai | 1387 | not on OpenRouter | - |  |
| 17 | Gemini 3.1 Flash Image (nano-banana-2, Web Search) | google | 1387 | 0.077 | 6.81 |  |
| 18 | Reve 2.1 | reve | 1373 | not on OpenRouter | - |  |
| 19 | GPT-Image-1.5 (High Fidelity) | openai | 1367 | not on OpenRouter | - |  |
| 20 | Qwen-Image-2.1 | alibaba | 1363 | 0.014 | 1.25 |  |
| 21 | Reve 2.0 | reve | 1359 | not on OpenRouter | - |  |
| 22 | MiniMax H3-Image | minimax | 1358 | 0.0049 | 0.43 |  |

### Video from words

People compare clips made from the same words. Price at the listed resolution; "Rs / min" = 60 seconds of finished video. Source: LMArena text_to_video/overall (46 models rated).

Why these picks: Rare case: the #1 video model is also one of the cheapest (about Rs 30 for 5 seconds at 720p, with sound). Wan 3.0 (another company, with sound) is the backup in case Google models are refused on her account. Seedance 2.5 only when 1080p is a must (8x the price).

| # | Model | Maker | Points | $ / second | Rs per 5 s | Rs per minute | Sound | Pick |
|---|---|---|---|---|---|---|---|---|
| 1 | Gemini Omni 1.2 Flash | google | 1540 | 0.07 @ 720p | 30.6 | 367 | yes | Main |
| 2 | Gemini Omni 1.1 Flash | google | 1513 | 0.101 @ 720p | 44.6 | 535 | yes |  |
| 3 | gemini-omni-flash | google | 1509 | not on OpenRouter | - | - |  |  |
| 4 | FLUX 3 Video | bfl | 1491 | 0.17 @ 720p | 74.8 | 898 | yes |  |
| 5 | Grok Imagine Video 1.5 | xai | 1488 | 0.14 @ 720p | 61.6 | 739 | yes |  |
| 6 | Seedance 2.0 | bytedance | 1483 | 0.374 @ 1080p | 165 | 1,976 | yes |  |
| 7 | Seedance 2.5 | bytedance | 1479 | 0.569 @ 1080p | 250 | 3,002 | yes | Premium |
| 8 | Wan 3.0 | alibaba | 1476 | 0.1 @ 720p | 44.0 | 528 | yes | Backup |
| 9 | SkyReels V4 | skyreel | 1459 | not on OpenRouter | - | - |  |  |
| 10 | Muse Video | meta | 1457 | not on OpenRouter | - | - |  |  |
| 11 | MiniMax H3 | minimax | 1456 | 0.13 @ 1080p | 57.2 | 686 | yes |  |
| 12 | HappyHorse 1.0 | aorizon | 1429 | 0.099 @ 720p | 43.5 | 522 | ? |  |
| 13 | Sora 2 Pro | openai | 1367 | not on OpenRouter | - | - |  |  |
| 14 | Veo 3.1 (Audio) | google | 1363 | 0.6 @ 4k | 264 | 3,168 | yes |  |
| 15 | Veo 3.1 Fast (Audio) | google | 1361 | 0.1 @ 720p | 44.0 | 528 | yes |  |
| 16 | Veo 3 Fast (Audio) | google | 1347 | not on OpenRouter | - | - |  |  |
| 17 | Sora 2 | openai | 1342 | not on OpenRouter | - | - |  |  |
| 18 | Grok Imagine Video | xai | 1341 | 0.07 @ 720p | 30.8 | 370 | ? | Budget |
| 19 | Veo 3 (Audio) | google | 1340 | not on OpenRouter | - | - |  |  |
| 20 | Wan 2.7 | alibaba | 1337 | 0.1 @ 1080p | 44.0 | 528 | yes |  |
| 21 | Wan 2.6 | alibaba | 1324 | 0.08 @ 720p | 35.2 | 422 | yes |  |
| 22 | Seedance 1.5 Pro | bytedance | 1256 | not on OpenRouter | - | - |  |  |
| 23 | Wan 2.5 Preview | alibaba | 1244 | not on OpenRouter | - | - |  |  |
| 24 | PixVerse V5.6 |  | 1238 | not on OpenRouter | - | - |  |  |
|  | *on OpenRouter, not rated yet* |  |  |  |  |  |  |  |
| · | mischief 1 | tbc | not rated | 0.01 @ 720p | 4.40 | 52.8 | no |  |
| · | Grok Imagine Video 1.5 Lite | x-ai | not rated | 0.03 @ 720p | 13.2 | 158 | yes |  |
| · | Veo 3.1 Lite | google | not rated | 0.05 @ 720p | 22.0 | 264 | yes |  |
| · | H3 Max | minimax | not rated | 0.08 @ 768p | 35.2 | 422 | no |  |
| · | Hailuo 2.3 | minimax | not rated | 0.082 @ 1080p | 35.9 | 431 | no |  |
| · | HappyHorse 1.1 | alibaba | not rated | 0.099 @ 720p | 43.5 | 522 | ? |  |
| · | Video O1 | kwaivgi | not rated | 0.112 @ 1080p | 49.3 | 591 | yes |  |
| · | Gen-4.5 | runway | not rated | 0.12 @ 1080p | 52.8 | 634 | no |  |
| · | Video v3.0 Standard | kwaivgi | not rated | 0.126 @ 1080p | 55.4 | 665 | yes |  |
| · | Wan 3.0 Prime | alibaba | not rated | 0.14 @ 720p | 61.6 | 739 | yes |  |
| · | Video v3.0 Pro | kwaivgi | not rated | 0.168 @ 1080p | 73.9 | 887 | yes |  |
| · | Seedance 2.0 Mini | bytedance | not rated | 0.17 @ 1080p | 74.8 | 898 | yes |  |
| · | Seedance 2.0 Fast | bytedance | not rated | 0.272 @ 1080p | 120 | 1,437 | yes |  |
| · | Seedance 2.5 Flash | bytedance | not rated | 0.34 @ 1080p | 150 | 1,796 | yes |  |

### Video from a picture

People compare clips that bring the same picture to life. Source: LMArena image_to_video/overall (45 models rated).

Why these picks: Gemini Omni 1.2 Flash is #1 again. MiniMax H3 is 10 points under it at 1080p.

| # | Model | Maker | Points | $ / second | Rs per 5 s | Rs per minute | Sound | Pick |
|---|---|---|---|---|---|---|---|---|
| 1 | Gemini Omni 1.2 Flash | google | 1503 | 0.07 @ 720p | 30.6 | 367 | yes | Main |
| 2 | Seedance 2.5 | bytedance | 1494 | 0.569 @ 1080p | 250 | 3,002 | yes | Premium |
| 3 | MiniMax H3 | minimax | 1493 | 0.13 @ 1080p | 57.2 | 686 | yes | Backup |
| 4 | Gemini Omni 1.1 Flash | google | 1487 | 0.101 @ 720p | 44.6 | 535 | yes |  |
| 5 | Wan 3.0 | alibaba | 1482 | 0.1 @ 720p | 44.0 | 528 | yes |  |
| 6 | Seedance 2.0 | bytedance | 1480 | 0.374 @ 1080p | 165 | 1,976 | yes |  |
| 7 | SkyReels V4 | skyreel | 1475 | not on OpenRouter | - | - |  |  |
| 8 | gemini-omni-flash | google | 1463 | not on OpenRouter | - | - |  |  |
| 9 | HiDream-O1-Video-1.0 | hidream | 1458 | not on OpenRouter | - | - |  |  |
| 10 | Grok Imagine Video 1.5 | xai | 1453 | 0.14 @ 720p | 61.6 | 739 | yes |  |
| 11 | FLUX 3 Video (20260811) | bfl | 1451 | 0.17 @ 720p | 74.8 | 898 | yes |  |
| 12 | HappyHorse 1.0 | aorizon | 1443 | 0.099 @ 720p | 43.5 | 522 | ? |  |
| 13 | Wan 2.7 | alibaba | 1427 | 0.1 @ 1080p | 44.0 | 528 | yes |  |
| 14 | Grok Imagine Video | xai | 1411 | 0.07 @ 720p | 30.8 | 370 | ? | Budget |
| 15 | Veo 3.1 (Audio) | google | 1399 | 0.6 @ 4k | 264 | 3,168 | yes |  |
| 16 | Veo 3.1 Fast (Audio) | google | 1386 | 0.1 @ 720p | 44.0 | 528 | yes |  |
| 17 | Vidu Q3 Pro | shengshu | 1363 | not on OpenRouter | - | - |  |  |
| 18 | Kling 3.0 Pro | kling | 1353 | 0.168 @ 1080p | 73.9 | 887 | yes |  |
| 19 | Veo 3 (Audio) | google | 1331 | not on OpenRouter | - | - |  |  |
| 20 | Veo 3 Fast (Audio) | google | 1327 | not on OpenRouter | - | - |  |  |
| 21 | Wan 2.5 Preview | alibaba | 1322 | not on OpenRouter | - | - |  |  |
| 22 | Wan 2.6 | alibaba | 1309 | 0.08 @ 720p | 35.2 | 422 | yes |  |
| 23 | Seedance 1.5 Pro | bytedance | 1307 | not on OpenRouter | - | - |  |  |
| 24 | PixVerse V5.6 |  | 1299 | not on OpenRouter | - | - |  |  |
|  | *on OpenRouter, not rated yet* |  |  |  |  |  |  |  |
| · | mischief 1 | tbc | not rated | 0.01 @ 720p | 4.40 | 52.8 | no |  |
| · | Grok Imagine Video 1.5 Lite | x-ai | not rated | 0.03 @ 720p | 13.2 | 158 | yes |  |
| · | Veo 3.1 Lite | google | not rated | 0.05 @ 720p | 22.0 | 264 | yes |  |
| · | H3 Max | minimax | not rated | 0.08 @ 768p | 35.2 | 422 | no |  |
| · | Hailuo 2.3 | minimax | not rated | 0.082 @ 1080p | 35.9 | 431 | no |  |
| · | HappyHorse 1.1 | alibaba | not rated | 0.099 @ 720p | 43.5 | 522 | ? |  |
| · | Video O1 | kwaivgi | not rated | 0.112 @ 1080p | 49.3 | 591 | yes |  |
| · | Gen-4.5 | runway | not rated | 0.12 @ 1080p | 52.8 | 634 | no |  |
| · | Video v3.0 Standard | kwaivgi | not rated | 0.126 @ 1080p | 55.4 | 665 | yes |  |
| · | Wan 3.0 Prime | alibaba | not rated | 0.14 @ 720p | 61.6 | 739 | yes |  |
| · | Seedance 2.0 Mini | bytedance | not rated | 0.17 @ 1080p | 74.8 | 898 | yes |  |
| · | Seedance 2.0 Fast | bytedance | not rated | 0.272 @ 1080p | 120 | 1,437 | yes |  |
| · | Seedance 2.5 Flash | bytedance | not rated | 0.34 @ 1080p | 150 | 1,796 | yes |  |

### Editing video

People compare edits of the same clip. Only 12 models are rated. Source: LMArena video_edit/overall (12 models rated).

Why these picks: Only 12 models are rated on video editing. Wan 3.0 is #1 at $0.10 a second.

| # | Model | Maker | Points | $ / second | Rs per 5 s | Rs per minute | Sound | Pick |
|---|---|---|---|---|---|---|---|---|
| 1 | Wan 3.0 | alibaba | 1424 | 0.1 @ 720p | 44.0 | 528 | yes | Main |
| 2 | Seedance 2.5 | bytedance | 1419 | 0.569 @ 1080p | 250 | 3,002 | yes | Premium |
| 3 | Gemini Omni 1.2 Flash | google | 1396 | 0.07 @ 720p | 30.6 | 367 | yes | Backup |
| 4 | gemini-omni-flash | google | 1380 | not on OpenRouter | - | - |  |  |
| 5 | MiniMax H3 | minimax | 1378 | 0.13 @ 1080p | 57.2 | 686 | yes |  |
| 6 | Seedance 2.0 | bytedance | 1368 | 0.374 @ 1080p | 165 | 1,976 | yes |  |
| 7 | SkyReels V4 | skyreel | 1364 | not on OpenRouter | - | - |  |  |
| 8 | HappyHorse 1.0 | aorizon | 1306 | 0.099 @ 720p | 43.5 | 522 | ? |  |
| 9 | Kling O3 Pro | kling | 1266 | not on OpenRouter | - | - |  |  |
| 10 | Grok Imagine Video | xai | 1250 | 0.07 @ 720p | 30.8 | 370 | ? |  |
| 11 | Kling O1 Pro | kling | 1190 | 0.112 @ 1080p | 49.3 | 591 | yes |  |
| 12 | Runway Gen-4 Aleph | runway | 1182 | not on OpenRouter | - | - |  |  |
|  | *on OpenRouter, not rated yet* |  |  |  |  |  |  |  |
| · | FLUX Video Edit | black-forest-labs | not rated | 0.03 @ 1080p | 13.2 | 158 | no | Budget |
| · | FLUX Video Upscale | black-forest-labs | not rated | 0.05 @ 1080p | 22.0 | 264 | no |  |
| · | Aleph 2.0 | runway | not rated | 0.28 @ 1080p | 123 | 1,478 | no |  |

### Talking avatar videos

A face speaking a script. No public board rates these yet, so only prices are compared. Fewer than 20 exist on OpenRouter. Source: OpenRouter video list + Hoola's own GPU lab.

Why these picks: A real person's face needs her recorded consent (Hoola Interactive rules).

| Model | Where | Price | Rs / min | Pick |
|---|---|---|---|---|
| Avatar 6 Turbo | HeyGen (OpenRouter) | $0.05/s @ 1080p | 264 | Main (finished videos) |
| Avatar IV | HeyGen (OpenRouter) | $0.05/s @ 1080p | 264 |  |
| Avatar 6 | HeyGen (OpenRouter) | $0.1/s @ 1080p | 528 |  |
| HeyGen Video | HeyGen (OpenRouter) | $0.18/s @ 1080p | 950 |  |
| Hoola Interactive lab (MuseTalk 1.5 on a rented L40S) | Hoola own | about $0.036 per live minute (measured) | 3.17 | Main (live teacher, own face engine) |
| Gemini Omni 1.2 Flash (general video with sound) | Google (OpenRouter) | $0.0695/s @ 720p | 367 | Backup (scenes, not lip-sync) |

## Voice and sound

### Speech to text (Indian languages)

Word error rate on Indian-language speech (lower is better), voiceofindia.ai board as in Hoola's feed snapshot. Source: voiceofindia.ai speech-to-text (32 models).

Why these picks: Sarvam and Bodhan are not on OpenRouter; each needs its own key in the VPS .env.

| # | Model | Maker | Errors (WER) | Price | Pick |
|---|---|---|---|---|---|
| 1 | Indic Transcribe Core | Bodhan | 3.39% | not on OpenRouter (maker's own API) | Premium |
| 2 | Saaras v3 | Sarvam AI | 3.69% | not on OpenRouter (maker's own API) | Main |
| 3 | Indic Transcribe Flex | Bodhan | 4.01% | not on OpenRouter (maker's own API) |  |
| 4 | Transcribe | Amazon | 4.69% | not on OpenRouter (maker's own API) |  |
| 5 | MAI-Transcribe-2 | Microsoft | 4.79% | listed as 0.1 (unit unclear, likely $ per hour) | Backup (on OpenRouter) |
| 6 | MAI-Transcribe-1.5 | Microsoft | 4.91% | listed as 0.36 (unit unclear, likely $ per hour) |  |
| 7 | Gemini 3.5 Transcribe | Google DeepMind | 5.59% | by tokens: $2 / $12 per M |  |
| 8 | Scribe v2 | ElevenLabs | 5.76% | $0.22 per hour (Rs 19.4) |  |
| 9 | Fast Transcription API | Microsoft | 5.77% | not on OpenRouter (maker's own API) |  |
| 10 | Maya Transcribe One | Maya Research | 5.85% | not on OpenRouter (maker's own API) |  |
| 11 | Gemini 3.8 Flash | Google DeepMind | 6.25% | not on OpenRouter (maker's own API) |  |
| 12 | Nemotron 3.5 Transcribe | NVIDIA | 6.59% | $0.06 per hour (Rs 5.28) | Budget |
| 13 | Realtime Transcription API | Microsoft | 6.8% | not on OpenRouter (maker's own API) |  |
| 14 | Gemini 3 Flash | Google DeepMind | 6.81% | not on OpenRouter (maker's own API) |  |
| 15 | GPT Transcribe | OpenAI | 6.94% | $0.27 per hour (Rs 23.8) |  |
| 16 | Prisma v2.5 | Gnani.ai | 7.24% | not on OpenRouter (maker's own API) |  |
| 17 | SraVaani | ARTPARK & IISc | 7.36% | not on OpenRouter (maker's own API) |  |
| 18 | Grok Voice Transcribe 2.0 | xAI | 7.84% | $0.1 per hour (Rs 8.80) |  |
| 19 | GPT Live Transcribe | OpenAI | 8.42% | not on OpenRouter (maker's own API) |  |
| 20 | Grok Voice Transcribe 2.0 Streaming | xAI | 8.51% | not on OpenRouter (maker's own API) |  |
| 21 | Gemma E4B | Google DeepMind | 8.8% | not on OpenRouter (maker's own API) |  |
| 22 | Nova 3 | Deepgram | 8.94% | $0.258 per hour (Rs 22.7) |  |
| 23 | OmniASR LLM 7B v2 | Meta | 9.21% | not on OpenRouter (maker's own API) |  |
| 24 | GPT Realtime | OpenAI | 10.01% | not on OpenRouter (maker's own API) |  |
| 25 | Qwen3-ASR | Alibaba Qwen | 10.51% | $0.027 per hour (Rs 2.38) |  |
| 26 | Nemotron 3.5 Streaming | NVIDIA | 11.37% | $0.012 per hour (Rs 1.05) |  |
| 27 | Ringg | Ringg AI | 11.37% | not on OpenRouter (maker's own API) |  |
| 28 | Heep Indic | — | 14.16% | not on OpenRouter (maker's own API) |  |
| 29 | GPT-4o mini Transcribe | OpenAI | 17.27% | by tokens: $1.25 / $5 per M |  |
| 30 | Scribe v2 Realtime | ElevenLabs | 26.58% | not on OpenRouter (maker's own API) |  |
| 31 | GPT-4o Transcribe | OpenAI | 32.27% | by tokens: $2.5 / $10 per M |  |
| 32 | Pingala V1 | Shunya Labs | 35.78% | not on OpenRouter (maker's own API) |  |
| - | Whisper (Kaan, on Hoola's own server) | OpenAI (open weights) | not rated on this board | free (own server) | Hoola today |

### Text to speech (Indian voices)

People pick the better Indian-language voice (Elo points, higher is better), voiceofindia.ai board as in Hoola's feed snapshot. Source: voiceofindia.ai text-to-speech (23 models).

Why these picks: Gemini 3.8 Flash TTS is 18 points under Eleven v4 for about 1/4 of its price per spoken minute.

| # | Model | Maker | Points | Price | Pick |
|---|---|---|---|---|---|
| 1 | Eleven v4 | ElevenLabs | 1119 | $80 per 1M characters (about $0.072 per spoken minute) | Premium |
| 2 | Gemini 3.8 Flash TTS | Google | 1101 | by tokens: about $0.017 per spoken minute | Main |
| 3 | Sonic-3.6 | Cartesia | 1100 | not on OpenRouter (maker's own API) | Backup |
| 4 | Gemini 3.1 Flash TTS | Google DeepMind | 1084 | by tokens: about $0.039 per spoken minute |  |
| 5 | Gemini 3.8 Flash-Lite TTS | Google | 1071 | by tokens: about $0.012 per spoken minute | Budget |
| 6 | Maya 2 Native | Maya Research | 1063 | not on OpenRouter (maker's own API) |  |
| 7 | Sonic-3.5 | Cartesia | 1052 | not on OpenRouter (maker's own API) |  |
| 8 | Gemini 2.5 Pro TTS | Google DeepMind | 1050 | not on OpenRouter (maker's own API) |  |
| 9 | Falcon | Murf AI | 1037 | not on OpenRouter (maker's own API) |  |
| 10 | Vachana TTS v3 | Gnani | 1028 | not on OpenRouter (maker's own API) |  |
| 11 | Eleven Labs v3 | ElevenLabs | 1028 | $80 per 1M characters (about $0.072 per spoken minute) |  |
| 12 | Lightning 3.1 Pro | Smallest AI | 1026 | not on OpenRouter (maker's own API) |  |
| 13 | Mira-TTS | Mirai Minds | 1007 | not on OpenRouter (maker's own API) |  |
| 14 | Chariot TTS-v0 | Chariot | 988 | not on OpenRouter (maker's own API) |  |
| 15 | Sonic 3 | Cartesia | 982 | not on OpenRouter (maker's own API) |  |
| 16 | Chirp 3 HD | Google | 972 | not on OpenRouter (maker's own API) |  |
| 17 | Bulbul v3 | Sarvam AI | 972 | not on OpenRouter (maker's own API) |  |
| 18 | Speech 2.8 HD | MiniMax | 965 | $100 per 1M characters (about $0.09 per spoken minute) |  |
| 19 | Teen-V1 | TeenageWorks | 963 | not on OpenRouter (maker's own API) |  |
| 20 | MAI Voice 1 | Microsoft AI | 924 | $22 per 1M characters (about $0.02 per spoken minute) (MAI Voice 2 shown; v1 not listed) |  |
| 21 | GPT-4o Mini TTS | OpenAI | 913 | not on OpenRouter (maker's own API) |  |
| 22 | Grok TTS | xAI | 912 | $15 per 1M characters (about $0.013 per spoken minute) |  |
| 23 | Azure TTS | Microsoft | 901 | not on OpenRouter (maker's own API) |  |

### Live voice calls

Talking live with her. No public board compares live call engines; these are the four Hoola already wires (Call voice setting) plus the audio chat models on OpenRouter. Fewer than 20 exist. Source: Hoola config (voice_*_usd_min) + her measured calls + OpenRouter.

Why these picks: A call is Gemini speaking + Hoola's brain working; the brain's model is chosen like a worker.

| Engine | Maker | Price | Pick |
|---|---|---|---|
| Gemini Live (Hoola today) | Google | measured on her calls: about Rs 1.2 a reply (Gemini's own token counts, 6 Nov) | Hoola today |
| GPT-Live-1 | OpenAI | $0.05 a minute (4.40 Rs) for the voice + Hoola's brain counted apart | Backup |
| Phonic 1 | Phonic | $0.07 a minute (6.16 Rs) all in |  |
| Grok Voice 3.0 | xAI | $0.08 a minute (7.04 Rs) list price |  |
| GPT Audio Mini (OpenRouter) | OpenAI | by tokens: $0.60 / $2.40 per M text, audio extra | Budget (turn by turn, not live) |
| GPT Audio (OpenRouter) | OpenAI | by tokens: $2.50 / $10 per M text, audio extra |  |

### Music

No public board rates music models; prices come from blogs that collect them and disagree in places. Fewer than 20 have an API. Source: web search 18 Nov 2026 (apiframe.ai, cometapi.com, costbench.com).

Why these picks: Check the maker's own price page before a paid run.

| Model | Maker | Price | Where | Pick |
|---|---|---|---|---|
| Lyria 3 Pro | Google | up to 3-minute songs; lowest per-minute rate at full length (one listing) | on OpenRouter (price shown there as 0) / Google API | Main (Hoola Create uses Lyria) |
| Lyria 3 Clip | Google | $0.04 for a 30-second clip (one listing) | on OpenRouter / Google API | Budget |
| Eleven Music | ElevenLabs | $0.15 a minute (official per one guide; $0.80 a minute through FAL) | own API | Backup |
| Stable Audio 3.0 | Stability | $0.26 a song, up to 6 minutes | own API |  |
| Stable Audio 2.5 | Stability | $0.20 a song, up to 3 minutes | own API |  |
| MiniMax Music | MiniMax | $0.035 a song (through FAL, 60 s there; 5 min native) | FAL / own API |  |
| Mureka | Mureka | from $0.045 a song | own API |  |
| Suno | Suno | no public per-song API price (plans $10-30 a month) | no public API |  |

## Search plumbing: memory and RAG

### Embeddings: finding by meaning (memory, RAG)

Turning text into numbers to search by meaning. Price per 1M tokens read. MTEB scores only where a source gave one. Source: OpenRouter embedding list (34 models) + MTEB where known.

Why these picks: Qwen3 Embedding 8B is the most cited multilingual leader and costs $0.01 per million tokens on OpenRouter.

| Model | Maker | $ per 1M | Rs per 1M | MTEB | Reads | Pick |
|---|---|---|---|---|---|---|
| Embed V1 0.6B | perplexity | $0.004 | Rs 0.352 | - | text |  |
| GTE-Base | thenlper | $0.005 | Rs 0.44 | - | text |  |
| E5-Base-v2 | intfloat | $0.005 | Rs 0.44 | - | text |  |
| paraphrase-MiniLM-L6-v2 | sentence-transformers | $0.005 | Rs 0.44 | - | text |  |
| all-MiniLM-L12-v2 | sentence-transformers | $0.005 | Rs 0.44 | - | text |  |
| bge-base-en-v1.5 | baai | $0.005 | Rs 0.44 | - | text |  |
| multi-qa-mpnet-base-dot-v1 | sentence-transformers | $0.005 | Rs 0.44 | - | text |  |
| all-mpnet-base-v2 | sentence-transformers | $0.005 | Rs 0.44 | - | text |  |
| all-MiniLM-L6-v2 | sentence-transformers | $0.005 | Rs 0.44 | - | text |  |
| GTE-Large | thenlper | $0.01 | Rs 0.88 | - | text |  |
| E5-Large-v2 | intfloat | $0.01 | Rs 0.88 | - | text |  |
| Multilingual-E5-Large | intfloat | $0.01 | Rs 0.88 | - | text |  |
| bge-large-en-v1.5 | baai | $0.01 | Rs 0.88 | - | text |  |
| bge-m3 | baai | $0.01 | Rs 0.88 | - | text |  |
| Qwen3 Embedding 8B | qwen | $0.01 | Rs 0.88 | 70.58 (multilingual, model card) | text | Main |
| Titan Text Embeddings V2 | amazon | $0.02 | Rs 1.76 | - | text |  |
| voyage-4-lite | mongodb | $0.02 | Rs 1.76 | - | text |  |
| Text Embedding 3 Small | openai | $0.02 | Rs 1.76 | - | text |  |
| Qwen3 Embedding 4B | qwen | $0.02 | Rs 1.76 | - | text | Budget |
| Embed V1 4B | perplexity | $0.03 | Rs 2.64 | - | text |  |
| voyage-4 | mongodb | $0.06 | Rs 5.28 | - | text |  |
| Embed 5 Fast | cohere | $0.08 | Rs 7.04 | - | text, image | Backup |
| Titan Embeddings G1 - Text | amazon | $0.1 | Rs 8.80 | - | text |  |
| Mistral Embed 2312 | mistralai | $0.1 | Rs 8.80 | - | text |  |
| Text Embedding Ada 002 | openai | $0.1 | Rs 8.80 | - | text |  |
| Embed 5 Pro | cohere | $0.12 | Rs 10.6 | - | text, image |  |
| voyage-code-4 | mongodb | $0.12 | Rs 10.6 | - | text |  |
| voyage-multimodal-3.5 | mongodb | $0.12 | Rs 10.6 | - | text, image |  |
| voyage-4-large | mongodb | $0.12 | Rs 10.6 | - | text |  |
| Text Embedding 3 Large | openai | $0.13 | Rs 11.4 | - | text |  |
| Gemini Embedding 001 | google | $0.15 | Rs 13.2 | 68.32 (one source) | text |  |
| Codestral Embed 2505 | mistralai | $0.15 | Rs 13.2 | - | text |  |
| Gemini Embedding 2 | google | $0.2 | Rs 17.6 | - | text, image, file, audio, video | Premium (pictures, audio, PDF too) |
| Titan Multimodal Embeddings G1 | amazon | $0.8 | Rs 70.4 | - | text, image |  |
| ONNX model on Hoola's own server (semantic search today) | own | 0 | 0 | - | text | Hoola today |

### Rerank: putting the best search results first

Re-orders found passages so the best come first (used after embeddings). No public board compares these here; only 11 are on OpenRouter. Source: OpenRouter rerank list (11 models).

| Model | Maker | Price | Pick |
|---|---|---|---|
| Rerank 5 Fast | cohere | not in the model list (priced per search by the maker) | Main |
| Rerank 5 Pro | cohere | not in the model list (priced per search by the maker) | Premium |
| rerank-3-lite | mongodb | not in the model list (priced per search by the maker) |  |
| rerank-3 | mongodb | not in the model list (priced per search by the maker) |  |
| Qwen3 Reranker 0.6B | qwen | not in the model list (priced per search by the maker) | Budget |
| Qwen3 Reranker 8B | qwen | not in the model list (priced per search by the maker) | Backup |
| rerank-2.5-lite | mongodb | not in the model list (priced per search by the maker) |  |
| rerank-2.5 | mongodb | not in the model list (priced per search by the maker) |  |
| Rerank 4 Pro | cohere | not in the model list (priced per search by the maker) |  |
| Rerank 4 Fast | cohere | not in the model list (priced per search by the maker) |  |
| Rerank v3.5 | cohere | not in the model list (priced per search by the maker) |  |

## Limits, said plainly

- Boards measure answers people prefer, on general asks. They do not measure speed, Hindi chat, or Hoola's own jobs. Before a switch, Hoola's own cards decide (parity card for writing, coding card for code, PC card for the PC).
- OSWorld numbers are self-reported by each maker with different harnesses.
- Picture prices are approximate: makers price per picture or per image token and the size changes the cost.
- Music, talking-avatar, live-call and rerank models have no public quality board; only prices are compared, and fewer than 20 exist with an API.
- Board names and OpenRouter names were joined by Hoola's own name matcher (`pipeline/names.py`); a model shown "not on OpenRouter" may still be reachable on its maker's own API with a separate key.
- Prices change; this is the 18 Nov 2026 list price at Rs 88 to the dollar.

## Sources

- [LMArena leaderboard dataset (boards dated 2026-11-11..17)](https://huggingface.co/datasets/lmarena-ai/leaderboard-dataset)
- [OpenRouter model list and prices (read 18 Nov 2026)](https://openrouter.ai/api/v1/models)
- [OpenRouter video model prices (read 18 Nov 2026)](https://openrouter.ai/api/v1/videos/models)
- [OSWorld-Verified collected results](https://leaderboard.steel.dev/leaderboards/osworld/)
- [voiceofindia.ai speech boards (Hoola feed snapshot)](https://voiceofindia.ai)
- [Music API prices (blog round-up)](https://apiframe.ai/blog/ai-music-api-pricing-2026)
- [Music API prices (blog round-up)](https://www.cometapi.com/ai-music-api-pricing/)
- [Stable Audio vs Suno prices](https://www.costbench.com/compare/stable-audio-vs-suno/)
- [Embedding models ranked by MTEB](https://blog.premai.io/best-embedding-models-for-rag-2026-ranked-by-mteb-score-cost-and-self-hosting)
- [MTEB multilingual v2 snapshot](https://www.llmreference.com/benchmark/mteb-multilingual-v2)
