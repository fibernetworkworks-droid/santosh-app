# Worker prices, checked live, and the worker card (19 Nov 2026)

Owner's ask: "LETS WORK ON WORKER --- GIVE ME PERFECT DATA". This page corrects the prices in `08_worker_atlas.md` and
says how the real numbers will be measured. Nothing in Hoola changes until she picks.

## What was wrong in the atlas

1. **One price per model is not what Hoola pays.** On OpenRouter one model is run by up to 50 companies ("providers"),
   at prices up to 19x apart. The atlas used one list price each. For some models that was the cheapest provider
   (GLM-5.3), for others the batch price (DeepSeek V4.1 Flash: the atlas said Rs 0.10 a step; the maker's own price is
   Rs 0.61).
2. **Hoola asks for the fastest provider, not the cheapest.** Every Box call sends `provider.sort = latency`
   (`pipeline_provider_sort`, `agent/llm.py` `_target`). The fastest provider is often a `/fast` or `priority`
   tier that costs 2x the standard price. Which provider really answers is only known from a real call.
3. **Thinking is billed and not counted.** Box calls ask for reasoning (effort low). The hidden thinking tokens are
   billed as output, so "Rs a step" for 800 written tokens is too low for every thinking model.
4. **Boards are not Hoola's jobs.** They rate general answers people prefer, not a Hinglish sum, an order turned into
   JSON, the right tool or a plan count.

## Live prices (OpenRouter endpoints, 19 Nov 2026, Rs 88 to the dollar)

Rs a step = one worker step that reads 20,000 tokens and writes 800 (thinking not included). "Cheapest" is often a
lower-precision copy of the model (fp4 / fp8); "flex" is a slower tier from the maker itself.

| Model | Providers | Cheapest (who, precision) | Maker's own (standard) | Middle provider | Dearest (who) | Atlas said |
|---|---|---|---|---|---|---|
| DeepSeek V4.1 Flash | 50 | Rs 0.07 (Particle AI) | Rs 0.61 | Rs 0.36 | Rs 1.22 (Morph `morph/fast`) | Rs 0.10 |
| GLM-5.3 | 49 | Rs 0.22 (Wafer, fp4) | Rs 2.77 | Rs 2.50 | Rs 4.16 (Parasail `parasail/fast`) | Rs 0.22 |
| GLM-5.3-Flash | 42 | Rs 0.08 (Relace, fp4) | Rs 0.30 | Rs 0.26 | Rs 0.45 (Fireworks `fireworks/us`) | Rs 0.30 |
| Qwen 3.8 27B | 25 | Rs 0.16 (Chutes, fp8) | Rs 0.93 | Rs 0.53 | Rs 1.85 (Cerebras `cerebras/fp16`) | Rs 0.26 |
| Qwen 3.8 Flash | 2 | Rs 0.30 (Alibaba) | Rs 0.30 | Rs 0.30 | Rs 0.30 (Alibaba `alibaba/us-east-1`) | not in atlas |
| MiMo-V2.6-Pro | 5 | Rs 0.62 (GMICloud, bf16) | Rs 0.83 | Rs 0.83 | Rs 7.60 (PrimaLabs `primalabs/fp8`) | Rs 0.83 |
| MiMo-V2.6-Flash | 7 | Rs 0.20 (Darkbloom, fp4) | Rs 0.27 | Rs 0.27 | Rs 0.38 (Makora `makora/fp8`) | Rs 0.27 |
| Gemini 3.8 Flash | 6 | Rs 0.79 (Google, `flex` = slower tier) | Rs 1.58 | Rs 1.58 | Rs 2.85 (Google AI Studio `google-ai-studio/priority`) | Rs 1.74 |
| Gemini 3.5 Flash-Lite | 6 | Rs 0.35 (Google, `flex` = slower tier) | Rs 0.70 | Rs 0.70 | Rs 1.27 (Google `google-vertex/global/priority`) | not in atlas |
| Hy4 | 1 | Rs 0.82 (Tencent, fp4) | Rs 0.82 | Rs 0.82 | Rs 0.82 (Tencent `tencent/fp4`) | Rs 0.82 |
| Hy4-Flash | 1 | Rs 0.07 (Tencent, fp8) | Rs 0.07 | Rs 0.07 | Rs 0.07 (Tencent `tencent/fp8`) | not in atlas |
| Hy3 | 3 | Rs 0.27 (Tencent, fp8) | Rs 0.27 | Rs 0.29 | Rs 0.29 (Novita `novita`) | Rs 0.17 |
| GPT-6.1 Terra | 4 | Rs 1.06 (OpenAI, `flex` = slower tier) | Rs 2.11 | Rs 2.11 | Rs 4.22 (OpenAI `openai/fast`) | Rs 2.11 |
| GPT-5.6 Luna | 5 | Rs 0.22 (OpenAI, `flex` = slower tier) | Rs 0.44 | Rs 0.44 | Rs 0.87 (OpenAI `openai/fast`) | Rs 0.44 |
| Kimi K3.1 Pro | 27 | Rs 1.01 (Relace, fp4) | Rs 4.22 | Rs 4.22 | Rs 9.29 (Amazon Bedrock `amazon-bedrock/us-east-1`) | Rs 1.01 |
| Muse Spark 1.3 | 2 | Rs 2.50 (Google) | Rs 2.50 | Rs 2.50 | Rs 2.50 (Google `google-vertex/global`) | Rs 2.50 |
| Qwen3.8-Max | 2 | Rs 3.94 (Alibaba) | Rs 3.94 | Rs 3.94 | Rs 3.94 (Alibaba `alibaba/us-east-1`) | Rs 3.94 |
| Claude Haiku 5.5 | 5 | Rs 0.21 (Google) | Rs 0.21 | Rs 0.21 | Rs 0.21 (Google `google-vertex/global`) | not in atlas |
| Claude Sonnet 4.6 | 5 | Rs 6.34 (Claude Platform on AWS) | Rs 6.34 | Rs 6.34 | Rs 6.34 (Claude Platform on AWS `claude-on-aws`) | Rs 6.34 |
| Claude Opus 4.6 | 5 | Rs 10.56 (Claude Platform on AWS) | Rs 10.56 | Rs 10.56 | Rs 10.56 (Claude Platform on AWS `claude-on-aws`) | Rs 10.56 |
| Claude Sonnet 5.5 | 5 | Rs 4.22 (Google) | Rs 4.22 | Rs 4.22 | Rs 4.22 (Google `google-vertex/global`) | Rs 4.22 |
| Claude Opus 5.5 | 6 | Rs 8.45 (Amazon Bedrock) | Rs 8.45 | Rs 8.45 | Rs 16.90 (Anthropic `anthropic/fast`) | Rs 8.45 |

What this shows:
- **GLM-5.3, the writer, costs Rs 0.22 to Rs 4.16 a step** depending on who serves it. Z.AI's own price is Rs 2.77;
  the atlas used the cheapest (Wafer, fp4). The writer's real cost is unknown until the card reads it.
- **DeepSeek V4.1 Flash is still cheap, but 6x the atlas number at the maker** (Rs 0.61, not Rs 0.10).
- **New cheap candidates the atlas did not have:** Hy4-Flash (Rs 0.07), GLM-5.3-Flash (Rs 0.08 at the cheapest),
  Claude Haiku 5.5 (Rs 0.21; it already runs Hoola's planner, checker and memory), Qwen 3.8 Flash (Rs 0.30).
- Models served by their maker alone (Claude, Hy4, Qwen3.8-Max, Muse Spark) cost the same whichever route.

## The worker card (`server/tools/worker_card.py`)

Every candidate does the same 11 Hoola worker jobs, each checked by code (never by another model):

| Job | Worker kind | Passes when |
|---|---|---|
| October profit in Hinglish | working out | profit 28,500 and margin 15.49% |
| Rs 4,500 + 18% GST inside Maharashtra | working out | CGST 405, SGST 405, total 5,310 |
| A WhatsApp order to JSON | extraction / tables | customer, phone, 3 items, total 3,205 all exact |
| A table and nothing else | extraction / tables | 5 lines, the right header, no extra words |
| Answer only from a supplier note | facts from her papers | rate + days right, says the GST number is not in the note, invents none |
| Today's gold rate | tool choice | calls web_search about gold |
| What is GST composition | tool choice | answers directly, no tool |
| How many worker parts for 4 asks | planner | 1, 3, 1, 1 (the rule from W1) |
| UPI QR steps, asked in Hindi | Indian languages | answer at least 60% Hindi script, 3 steps |
| A bill picture: total and GSTIN | reading pictures | 2,940 and the exact GSTIN |
| A Python function for rupee text | code | all 6 cases right when run (in a locked process) |

How it runs: sent exactly like a Box call (reasoning low and streamed, the server's own `provider.sort`), 3 runs per
candidate, 1 run per expensive Claude reference, plus one run per job on the cheapest route (`provider.sort = price`)
to show what the cheaper route costs and whether it still passes. Each call records the provider that answered, the
first-token and whole time, tokens including thinking, and the rupees OpenRouter charged (`usage.cost`).

Picks by rule, per worker kind: a model must pass every run of every job of that kind; then the cheapest median rupees
per job wins (within 10% the faster one); the backup is the next cheapest from another company.

Run it: Actions -> VPS ops -> **worker_card** (stops itself at Rs 400; about 15-25 min; the script is read from main,
so the running server is not touched). **worker_card_status** prints the last card again for free. Locally:
`python tools/worker_card.py --selftest` (the checkers on planted answers, no network).

## Limits, said plainly

- 11 jobs is a small set: a model that passes all of them is fit for these jobs, not proven for every job.
- Provider speed changes by the hour; the card is one evening's reading. Run it again before a switch.
- The Claude references get one run each to keep the cost down, so their "every run" is one run.
- Long tool jobs (an AI employee working for many steps) are not in this card; the agent board and Hoola's long card cover those.
