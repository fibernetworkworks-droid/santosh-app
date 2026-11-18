# Which model should be the writer (18 Nov 2026)

Owner's ask: "DO DEEP RESEARCH FIND MORE PERFECT WRITER WHICH WILL BE PERFECT AND COST EFFECTIVE".
Every number was read on 18 Nov 2026. No benchmark measures Hinglish; only a test on her own messages (C0) settles it.

## Sources
- LMArena text board (the same public dataset the Box ranks from), published 2026-11-11, read through `pipeline/sources.py`.
- OpenRouter /api/v1/models (prices, tool support, cache price) and /models/{id}/endpoints (providers, uptime).
- OpenRouter's own tau2-bench Airline run (openrouter.ai/benchmarks/tau2-bench-airline, run 17 Nov 2026, 146 models).
- Toolathlon-Verified (benchlm.ai, lab-reported), Vectara HHEM hallucination board (22 Oct 2026), SimpleQA (benchlm / Kaggle),
  Artificial Analysis Intelligence Index, MILU (Anthropic self-reported only).
- Not usable: BFCL (official board frozen 12 Apr 2026), MCPMark (Dec 2025), no live Indic text arena (voiceofindia.ai: "Soon").

## The candidates
Rs / step = one writer step of 20k tokens read + 800 written at list price, Rs 88 / $ (no cache).

| Model | Arena chat | Arena non-English | tau2 tools | Hallucination / facts | $/M in/out | Rs / step |
|---|---|---|---|---|---|---|
| Gemini 4 Argon | 1529 | 1523 | 78.7% | HHEM 12.1%, SimpleQA 71.2% | 2 / 10 | 4.22 |
| Gemini 3.8 Flash | 1500 | 1492 | 71.3% | SimpleQA 69.4% | 0.83 / 4.12 | 1.74 |
| MiMo-V2.6-Pro | 1492 | 1475 | - (Flash 77.9%) | - | 0.43 / 0.87 | 0.83 |
| GLM-5.3 (Max) | 1475 | 1462 | 77.3% | (GLM-5 HHEM 10.1%) | 0.07 / 1.4 | 0.22 |
| GLM-5.3-Flash | 1472 | 1462 | 75.6% | - | 0.15 / 0.5 | 0.30 |
| Claude Sonnet 5.5 | 1469 | 1455 | 78.8% | SimpleQA 46%, AA hallucination 43% | 2 / 10 | 4.22 |
| DeepSeek V4.1 Flash | 1464 | 1450 | 75.1% | HHEM 4.2% (best read), SimpleQA 43.5% | 0.036 / 0.5 | 0.10 |
| Qwen 3.8 27B (today's chat) | 1437 | 1424 | 77.1% | - | 0.06 / 2.2 | 0.26 |
| Gemini 3.5 Flash-Lite | 1435 | 1427 | 78.3% | - | 0.3 / 2.5 | 0.70 |
| Claude Haiku 5.5 | 1398 | 1385 | 72.8% | - | 0.1 / 0.5 | 0.22 |
| GPT-6 Luna | 1388 | 1380 | 67.3% | - | 0.1 / 0.5 | 0.22 |
| Claude Opus 5.5 | 1514 | 1503 | 75.3% | HHEM 9.9% | 4 / 20 | 8.45 |

Notes: arena scores for "(Max)/(High)" variants were made with thinking on - more output tokens and slower answers. The top
40 of the tau2 run are within ~5 points of each other (one run each). Gemini 4 Carbon (arena 1538) answered 403 "is banned"
on her OpenRouter account on 17 Nov; whether Argon / Flash are refused the same way is not known until one call is tried.

## Findings
1. Sonnet 5.5 is not the best value: GLM-5.3 matches it on chat (1475 vs 1469) and nearly on tools (77.3 vs 78.8) at
   about 1/20 of the price.
2. Gemini 4 Argon is the best quality at Sonnet's price: higher chat, non-English and factual scores, same tools score.
3. DeepSeek V4.1 Flash is the cheapest strong model and the least hallucinating one measured - a natural checker.
4. Qwen 3.8 27B is fine at tools (77.1%); its gap is reply quality (1437).
5. Haiku 5.5 / GPT-6 Luna are cheap but clearly weaker writers.

## Suggested setup (to be confirmed by C0)
- Writer: GLM-5.3. Moves up to Gemini 4 Argon (or Sonnet 5.5) for hard messages.
- Model checker: DeepSeek V4.1 Flash (another company, lowest hallucination, Rs 0.1 a check).
- C0 test set: GLM-5.3, DeepSeek V4.1 Flash, MiMo-V2.6-Pro, Gemini 4 Argon, Sonnet 5.5 (yardstick), Qwen 3.8 27B (today).
