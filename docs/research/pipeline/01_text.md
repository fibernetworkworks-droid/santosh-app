# Pipeline research 01 - text work leaderboards (read 16 Nov 2026)

For `docs/HOOLA_PIPELINE_PLAN.md` section 8. Read live by a research agent on 16 Nov 2026. Model names and ids are as
the boards and OpenRouter's `/api/v1/models` (468 models) showed them that day. Every model listed supports `tools` and
`structured_outputs` on OpenRouter unless marked.

**How it was read.** arena.ai (LMArena's new name) blocks automated reads (Cloudflare 403). Artificial Analysis (AA)
draws its charts in the browser, so only partial tables came through. Where a primary board could not be read, numbers
came from **BenchLeader** (benchleader.com, an aggregator that mirrors and dates each publisher's numbers, "data as of
16 Nov 2026"). Rows marked (BL) were not read on the primary site.

## 1. General chat / writing (`chat`, `write`, `summarise`)
| Model | Arena Text (BL, 11 Nov) | AA Intelligence (live) | LiveBench 2.0 (BL, 6 Nov) | OpenRouter id |
|---|---|---|---|---|
| Gemini 4 Carbon (high) | 1526 | 60 | 83.5 | google/gemini-4-carbon |
| Gemini 4 Argon (high) | 1522 | 50 | 77.7 | google/gemini-4-argon |
| Muse Wonder (max) | 1511 | 44 | - | meta/muse-wonder |
| Claude Opus 5.5 | 1507 | 59 | 83.4 | anthropic/claude-opus-5.5 |
| Claude Fable 5 / 5.1 | 1504 / 1502 | - | 84.0 (5.1) | anthropic/claude-fable-5, anthropic/claude-fable-5.1 |
| Gemini 3.8 Flash (high) | 1497 | - | - | google/gemini-3.8-flash |
| Muse Spark 1.3 | 1497 | - | - | meta/muse-spark-1.3 |
| Gemini 4 Hydrogen (high) | 1490 | 54 | 77.0 | google/gemini-4-hydrogen |
| Claude Fable 5.2 | not in Arena top 15 | 65 (#1) | 84.9 (#1) | anthropic/claude-fable-5.2 |
| GPT-6 Astra | not in Arena top 15 | 57 | 84.5 | openai/gpt-6-astra |

Proposed: ULTRA Gemini 4 Carbon, Claude Fable 5.2 · MAX Gemini 4 Argon, Claude Opus 5.5, Muse Wonder · HIGH Claude
Fable 5.1, GPT-6 Astra · MID Gemini 3.8 Flash, Muse Spark 1.3 · LOW Gemini 4 Hydrogen, Claude Haiku 5.5
(anthropic/claude-haiku-5.5, AA 36).

## 2. Hard reasoning & maths (`reason`)
| Model | LiveBench Reasoning (BL) | FrontierMath T1-3 (Epoch via BL) | LiveBench Maths (frozen 25 Jun) | id |
|---|---|---|---|---|
| Claude Fable 5.2 | - | 95.1 | - | anthropic/claude-fable-5.2 |
| GPT-6 Astra | 92.7 | 93.7 | 96.8 | openai/gpt-6-astra |
| GPT-6.1 Sol | 92.6 | 93.7 | 96.8 | openai/gpt-6.1-sol |
| Gemini 4 Argon | 95.1 | - | - | google/gemini-4-argon |
| Claude Opus 5.5 | 92.2 | 91.2 | 97.1 | anthropic/claude-opus-5.5 |
| GPT-6.1 Terra | - | 90.9 | - | openai/gpt-6.1-terra |
| Gemini 4 Carbon | 90.6 | 90.5 | - | google/gemini-4-carbon |
| Claude Sonnet 5.5 | 91.6 | 88.8 | 96.7 | anthropic/claude-sonnet-5.5 |
| Grok 4.6 / Kimi K3.1 Pro | 91.2 / 91.1 | - | - | x-ai/grok-4.6, moonshotai/kimi-k3.1-pro |

Proposed: ULTRA Claude Fable 5.2, GPT-6 Astra · MAX GPT-6.1 Sol, Gemini 4 Argon, Claude Opus 5.5 · HIGH Claude Sonnet
5.5, Gemini 4 Carbon, GPT-6.1 Terra · MID Kimi K3.1 Pro, Grok 4.6 · LOW Gemini 4 Hydrogen, DeepSeek V4.1 Flash.

## 3. Coding (`code`, `code.small`)
| Model | Arena WebDev (BL, 15 Nov) | SWE-Bench Pro V2 (BL) | Terminal-Bench 4.0 (BL) | LiveBench Coding (BL) | id |
|---|---|---|---|---|---|
| Claude Fable 5.2 | 1826 | - | 61.6 | - | anthropic/claude-fable-5.2 |
| Claude Opus 5.5 | 1816 | - | 59.6 | 87.1 | anthropic/claude-opus-5.5 |
| Claude Sonnet 5.5 | 1772 | 95.8 | 63.6 | - | anthropic/claude-sonnet-5.5 |
| Gemini 4 Carbon | 1768 | - | 65.2 | 91.0 | google/gemini-4-carbon |
| GPT-6 Astra | 1763 | 96.9 | 59.6 | 87.5 | openai/gpt-6-astra |
| Claude Fable 5.1 | 1743 | 99.1 | - | 89.7 | anthropic/claude-fable-5.1 |
| Kimi K3.1 Pro / K3 | - | 97.7 (K3) | 67.2 | - | moonshotai/kimi-k3.1-pro, moonshotai/kimi-k3 |
| Qwen4 Max | 1750 | - | - | - | qwen/qwen4-max |
| Gemini 4 Argon | - | 99.2 | - | 85.7 | google/gemini-4-argon |
| GPT-6.1 Terra | - | - | - | 89.2 | openai/gpt-6.1-terra |

Proposed: ULTRA Claude Fable 5.2, Claude Opus 5.5 · MAX Gemini 4 Carbon, GPT-6 Astra, Kimi K3.1 Pro · HIGH Claude
Sonnet 5.5, Claude Fable 5.1, Qwen4 Max · MID GPT-6.1 Terra, MiniMax M3.1 Flash (minimax/minimax-m3.1-flash), Inkling 2
Small (thinkingmachines/inkling-2-small) · LOW DeepSeek V4.1 Flash 1017 (deepseek/deepseek-v4.1-flash-1017).

## 4. Tools / multi-step agents (`tools`)
| Model | MCP Atlas (BL) | LiveBench Long Agentic (BL, 6 Nov) | tau3-Banking (live) | id |
|---|---|---|---|---|
| Claude Fable 5.2 | - | 82.9 | - | anthropic/claude-fable-5.2 |
| Gemini 4 Argon | 90.7 | 58.5 | - | google/gemini-4-argon |
| GPT-6 Astra | - | 75.6 | - | openai/gpt-6-astra |
| Claude Fable 5.1 | 87.2 | 74.2 | - | anthropic/claude-fable-5.1 |
| Claude Opus 5.5 | 85.4 | 72.8 | - | anthropic/claude-opus-5.5 |
| Gemini 4 Carbon | - | 72.7 | - | google/gemini-4-carbon |
| Muse Spark 1.1 | 88.1 | - | - | meta/muse-spark-1.1 |
| Qwen3.8 Max | 84.5 | - | 55.2 | qwen/qwen3.8-max-0902 |
| GLM 5.3 | 84.2 | - | - | z-ai/glm-5.3 |
| Gemini 3.5 Flash | 83.6 | - | - | google/gemini-3.5-flash |

Proposed: ULTRA Claude Fable 5.2, Gemini 4 Argon · MAX GPT-6 Astra, Claude Fable 5.1, Claude Opus 5.5 · HIGH Gemini 4
Carbon, Claude Sonnet 5.5 · MID GLM 5.3, Qwen3.8 Max · LOW Gemini 3.5 Flash, GLM 4.7 Flash (z-ai/glm-4.7-flash).

## 5. Web research (`research`)
| Model | Arena Search (BL, 9 Nov) | FACTS Search (BL) | Vals Web Search (4 Nov) | id |
|---|---|---|---|---|
| GPT-5.6 Sol | 1255 | 92.9 | 43.6 | openai/gpt-5.6-sol |
| GPT-6.1 Sol | 1249 | 92.8 | - | openai/gpt-6.1-sol |
| GPT-6 Astra | 1245 | 93.3 | - | openai/gpt-6-astra |
| GPT-6 Sol | 1229 | 92.7 | - | openai/gpt-6-sol |
| Claude Fable 5 / 5.1 | 1229 / 1227 | - | 46.9 (5) | anthropic/claude-fable-5, -5.1 |
| Qwen3.8 Max | 1227 | - | - | qwen/qwen3.8-max-0902 |
| Gemini 4 Carbon | - | 94.4 | - | google/gemini-4-carbon |
| Claude Opus 5.5 | - | 88.4 | 53.8 | anthropic/claude-opus-5.5 |
| GPT-6.1 Terra | - | 92.7 | - | openai/gpt-6.1-terra |

Proposed: ULTRA GPT-6.1 Sol, GPT-6 Astra · MAX GPT-5.6 Sol, Gemini 4 Carbon, Claude Opus 5.5 · HIGH Claude Fable 5.1,
GPT-6 Sol · MID Qwen3.8 Max, GPT-6.1 Terra · LOW Gemini 3.5 Flash.

## 6. Factual accuracy (`facts`, `check`)
| Model | SimpleQA Verified (BL) | AA-Omniscience (live) | FACTS Grounding (BL) | id |
|---|---|---|---|---|
| Claude Fable 5.2 | 94.0 | index 67, accuracy 79 % | - | anthropic/claude-fable-5.2 |
| Gemini 4 Carbon | 77.7 | hallucination 4 % | 77.2 | google/gemini-4-carbon |
| Gemini 4 Argon | 76.0 | hallucination 4 % | 73.3 | google/gemini-4-argon |
| GPT-6 Astra | 75.6 | - | 80.1 | openai/gpt-6-astra |
| GPT-6.1 Sol | 73.9 | - | 78.0 | openai/gpt-6.1-sol |
| Claude Opus 5.5 | 72.2 | - | - | anthropic/claude-opus-5.5 |
| GPT-6.1 Terra | - | - | 84.2 | openai/gpt-6.1-terra |
| Gemini 4 Hydrogen | - | hallucination 8 % | - | google/gemini-4-hydrogen |
| GPT-6 Luna | - | - | 76.7 | openai/gpt-6-luna |

Proposed: ULTRA Claude Fable 5.2 · MAX Gemini 4 Carbon, Gemini 4 Argon · HIGH GPT-6 Astra, GPT-6.1 Sol · MID GPT-6.1
Terra, Claude Opus 5.5 · LOW Gemini 4 Hydrogen, GPT-6 Luna.

## 7. Long documents (`read.long`)
| Model | AA-LCR v1.1 (BL) | MLCR (BL) | Arena Document (BL, 9 Nov) | id |
|---|---|---|---|---|
| Kimi K3 | 88.7 | - | - | moonshotai/kimi-k3 |
| Step 5 Preview | 88.3 | - | - | stepfun/step-5-preview |
| Kimi K3.1 Pro | 86.3 | 38.3 | - | moonshotai/kimi-k3.1-pro |
| MiMo-V2.6-Pro | 86.3 | - | - | xiaomi/mimo-v2.6-pro |
| Claude Fable 5.1 | 85.3 | - | 1498 | anthropic/claude-fable-5.1 |
| Claude Opus 5.5 | 84.7 | - | - | anthropic/claude-opus-5.5 |
| Claude Fable 5.2 | - | 43.9 | - | anthropic/claude-fable-5.2 |
| GPT-6 Astra / Claude Sonnet 5.5 | - | 41.7 / 41.7 | - | openai/gpt-6-astra, anthropic/claude-sonnet-5.5 |
| Claude Fable 5 | - | - | 1500 | anthropic/claude-fable-5 |
| Claude Haiku 5.5 | - | 35.0 | - | anthropic/claude-haiku-5.5 |

Proposed: ULTRA Kimi K3, Claude Fable 5.2 · MAX Kimi K3.1 Pro, Step 5 Preview · HIGH Claude Fable 5.1, Claude Opus 5.5,
MiMo-V2.6-Pro · MID Claude Sonnet 5.5, GPT-6 Astra · LOW Claude Haiku 5.5.

## 8. Structured output (`extract`)
No maintained multi-model board found (only papers). Proxies: LiveBench Data Analysis + AA IFBench.

| Model | LiveBench Data Analysis (BL) | AA IFBench (BL) | id |
|---|---|---|---|
| Gemini 4 Carbon | 86.5 | - | google/gemini-4-carbon |
| Gemini 4 Argon | 85.2 | - | google/gemini-4-argon |
| Gemini 4 Hydrogen | 83.2 | - | google/gemini-4-hydrogen |
| GPT-6 Astra | 83.0 | - | openai/gpt-6-astra |
| GPT-6.1 Sol / Terra | 82.7 / 82.3 | - | openai/gpt-6.1-sol, openai/gpt-6.1-terra |
| Muse Wonder | 81.6 | - | meta/muse-wonder |
| Claude Fable 5.2 | 81.5 | - | anthropic/claude-fable-5.2 |
| Grok 4.3 | - | 83.3 | x-ai/grok-4.3 |
| MiniMax M3 | - | 82.9 | minimax/minimax-m3 |

Proposed (proxy only): ULTRA Gemini 4 Carbon · MAX Gemini 4 Argon, GPT-6 Astra · HIGH GPT-6.1 Sol, Claude Fable 5.2 ·
MID GPT-6.1 Terra, Muse Wonder · LOW Gemini 4 Hydrogen, MiniMax M3.

## 9. Speed (a ranking input, not a kind of work)
| Model | tok/s (BL, 16 Nov) | First token | id |
|---|---|---|---|
| Grok 4.20 Multi-Agent | 349 | 12 s | x-ai/grok-4.20-multi-agent |
| Claude Haiku 5.5 (xhigh) | 229 | 1.08 s | anthropic/claude-haiku-5.5 |
| Muse Spark 1.2 | 205 | 2.97 s | meta/muse-spark-1.2 |
| GPT-5.4 Mini | 199 | 1.07 s | openai/gpt-5.4-mini |
| Gemini 3 Flash | 199 | 1.15 s | google/gemini-3-flash-preview |
| Gemini 3.5 / 3.6 Flash | 175 / 174 | 1.47 / 1.27 s | google/gemini-3.5-flash, google/gemini-3.6-flash |
| DeepSeek V4.1 Flash 1017 | 173 | 0.78 s | deepseek/deepseek-v4.1-flash-1017 |
| Gemini 4 Hydrogen | 170 | 1.72 s | google/gemini-4-hydrogen |
| Qwen3.7 Max | 159 | 1.12 s | qwen/qwen3.7-max |

BenchLeader's list only includes models >= 100 tok/s and above a minimum score.

## Sources and their terms
| Source | URL | Live | Last update | Data feed | Reuse terms |
|---|---|---|---|---|---|
| LMArena (now Arena) | arena.ai/leaderboard | yes, blocks automated reads | dataset 2026-11-16 | Hugging Face dataset `lmarena-ai/leaderboard-dataset` | dataset tagged **cc-by-4.0**; site terms not fetched |
| Artificial Analysis | artificialanalysis.ai | yes | changelog to 15 Nov | free Data API (key, 100 req/day) | API: "Attribution is required for all use of our free API." Site: "personal, noncommercial use", no "scrape, or mine data" |
| LiveBench | livebench.ai | yes (JS app) | results 6 Nov 2026 | not found | not found |
| SWE-bench | swebench.com | yes | newest 2026-02-26 | GitHub | not found |
| Aider | aider.chat/docs/leaderboards | yes | newest 2025-08 | repo | not found |
| LiveCodeBench | livecodebench.github.io | yes | 2025 models only | `performances_generation.json` | not found |
| BFCL | gorilla.cs.berkeley.edu | yes | 2026-04-12 (V4) | GitHub + result repo | no licence stated |
| tau-bench | taubench.com | yes | no date | GitHub | not stated |
| Fiction.LiveBench | fiction.live | yes | no results since 27 Jan 2026 | not found | not found |
| Epoch (SimpleQA Verified, FrontierMath) | epoch.ai (via BL) | via BL | to 9-10 Nov 2026 | Epoch hub (not checked) | not checked |
| BenchLeader | benchleader.com | yes | 16 Nov 2026, rebuilt every 6 h | files under /data | its own index "CC BY 4.0 ... credit BenchLeader with a link"; third-party scores not relicensed; must not "scrape it at a rate that disrupts service" |
| OpenRouter | openrouter.ai/api/v1/models | yes | weekly usage to 15 Nov | models API + per-model endpoints API (uptime filled; latency / throughput null) | terms section 7 bars crawlers scraping the Site; the API is the allowed route |

## Caveats
- Arena and AA disagree at the top: Claude Fable 5.2 leads AA, LiveBench, SimpleQA, FrontierMath, WebDev but is not in
  Arena Text top 15 (probably too new). GPT-6 Astra also missing from Arena Text.
- **Stale, do not route on:** SWE-bench Verified (Feb 2026), Aider Polyglot (Aug 2025), LiveCodeBench (2025 models),
  BFCL (Apr 2026), tau2-bench, Fiction.LiveBench (Jan 2026), LiveBench Maths + Agentic Coding (frozen 25 Jun 2026).
- SWE-Bench Pro V2 is near saturation (95.8-99.4) - barely separates the leaders.
- No live RULER board; AA-LCR, MLCR, Arena Document stand in for long context.
- Structured output has no real board; its levels are proxy-only.
- Scores are per reasoning setting (max / xhigh / high); one OpenRouter id can mean several settings.
- Almost all numbers came through one mirror (BenchLeader), not cross-checked on arena.ai or Epoch directly.
