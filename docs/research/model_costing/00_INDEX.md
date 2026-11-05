# Model costing: high-performance models with very low API cost (5 Nov 2026)

Owner's ask: *"GO DEEP ON COSTING AND FIND THE HIGH PERFORMANCE MODEL WITH VERY LOW API COSTING, GIVE ME THE LIST"*.

## How honest this is (read first)
- Six web searches. Results were **secondary blogs and price aggregators that disagree with each other** (several prices appear in two versions); I could not open the vendors' own price pages.
  Every price below is "reported", not verified. Rows marked `*` come from **Hoola's own price table** (`server/app/usage.py`, "from the official price pages on 22 Oct 2026").
- **Price is not quality.** No quality number below was measured by us. Quality signals quoted come from the same secondary sources. The only way to rank "performance per rupee" for *our* jobs is to run our own cards
  (REPEAT card proposed in the last report; Hoola already has tool, hard, long, research, maps cards). Until then this is a **shortlist to test**, not a verdict.
- Names, versions and discounts change quarterly (one source: Alibaba reprices and renames models every quarter; DeepSeek's 75% discount was reported both as ending 31 May and as made permanent).

## The list (USD per 1M tokens; cost of 1,000 typical repetitive tasks = 4,000 input + 600 output tokens each, no caching, USD at Rs 88)
| # | Model (reported) | In | Out | $ / 1,000 tasks | Rs / 1,000 tasks | Quality signal reported (unverified) |
|---|---|---|---|---|---|---|
| 1 | GPT-5 nano | 0.05 | 0.40 | 0.44 | 39 | small model; consistent across sources |
| 2 | Gemini 2.5 Flash-Lite `*` | 0.10 | 0.40 | 0.64 | 56 | small model; audio input supported |
| 3 | **Claude Haiku 5.5** `*` | 0.10 | 0.50 | 0.70 | 62 | Hoola already uses it as hard-card judge |
| 4 | **DeepSeek V4 Flash** | 0.14 | 0.28 | 0.73 | 64 | OpenRouter's June 2026 post called it the value pick on the price/performance frontier; cached input reported ~$0.0028 (V4 Flash); peak-hour rates apply |
| 5 | Qwen3.8-Flash | ~0.15 | ~0.47 | 0.88 | 78 | conflicting listings ($0.14/$0.42 vs $0.15/$0.47) |
| 6 | Gemini 3.1 Flash-Lite | 0.125-0.25 | 0.75-1.00 | 1.0-1.6 | 88-141 | two conflicting listings; claimed to beat GPT-5 mini |
| 7 | Qwen3.6-Flash | 0.25 | 1.50 | 1.90 | 167 | first-party price, 17 Oct 2026 |
| 8 | **MiniMax M2 / M2.5** | 0.30 | 1.20 | 1.92 | 169 | M2.5 reported 80.2% on SWE-bench Verified (May 2026), top among open-weight models listed |
| 9 | Qwen3.7-Plus | 0.40 | 1.60 | 2.56 | 225 | "price-performance tier" in one source |
| 10 | GPT-5 mini | 0.40 | 1.60-2.00 | 2.6-2.8 | 225-246 | two conflicting output prices |
| 11 | DeepSeek V4 Pro (discounted) | 0.435 | 0.87 | 2.26 | 199 | list price $1.74/$3.48 = $9.05 / Rs 796 per 1,000 tasks; discount status disputed |
| 12 | Gemini 3 Flash | 0.50 | 3.00 | 3.80 | 334 | listed as stronger than GPT-5 mini on most benchmarks (llm-stats) |
| 13 | GLM-4.7 `*` (what Hoola's cheap chat brain uses now) | 0.60 | 2.20 | 3.72 | 327 | in production here |
| 14 | Kimi K2-0905 | 0.60 | 2.50 | 3.90 | 343 | newer Kimi releases exist (no prices found) |
| 15 | GLM-5 | 1.00 | 3.20 | 5.92 | 521 | 200K context; GLM-5.1 reported $1.40/$4.40 |
| 16 | Qwen3.8-Max | 2.00 | 6.00 | 11.60 | 1,021 | Aug 2026 release |
| ref | Claude Sonnet 5.5 `*` | 2.00 | 10.00 | 14.00 | 1,232 | our premium tier today |
| ref | Claude Opus 5.5 `*` | 4.00 | 20.00 | 28.00 | 2,464 | our hard-reasoning tier today |

Other names found without prices (test-list only): DeepSeek V4.1 Flash, MiniMax M3.1 Flash, Kimi K3.1 Pro, Muse Spark Open (late-October 2026 guide); Qwen3-Coder-Next (reported $0.11 input, 70.6% SWE-bench Verified); GPT-6 Luna (reported $0.04 blended, Intelligence Index 38, ~$0.07 per index task, on the Artificial Analysis OpenAI page); Ling 2.6 Flash ($0.010 input, price-only).
Reported top end (for scale): Artificial Analysis-style indices put Opus 5.5 around 58 and one source Gemini 4 Carbon at 59, at roughly $6-8 per index task, versus ~$0.07 for GPT-6 Luna at 38. That is the real trade: the cheap tier gives roughly two-thirds of the top score for about 1% of the cost per task (reported, secondary sources).

## What it means for Hoola (reasoned, not measured)
1. **A three-tier router beats any single cheap model.**
   - Tier 1 (routine reading, extraction, classification, drafting a standard message): one of rows 1-5 (about Rs 40-80 per 1,000 tasks).
   - Tier 2 (planning, multi-step tool use, code, Hinglish writing quality): rows 7-12 (about Rs 170-340).
   - Tier 3 (exceptions, hard reasoning, legal/financial checks): Sonnet/Opus, used only on the 5-15% of cases flagged by the checks.
   At a 90/8/2 mix the blended cost is roughly Rs 100-120 per 1,000 tasks instead of Rs 1,232 on Sonnet alone: about a tenth. (Arithmetic on the table above; the mix is an assumption.)
2. **Input tokens dominate repetitive work**, so cache hits matter more than headline price: DeepSeek V4 Flash reports ~98% off cached input; Anthropic cache reads are in our table (Haiku 5.5 read $0.01). Design playbooks with a fixed prefix.
3. **Code does the arithmetic** (the playbook rule): the cheap model only reads and drafts, so a weaker model costs little accuracy on matching and totals.
4. **Voice, vision and image are separate price lists** (Hoola's table has them: Gemini live/audio, image models); this list is text only.
5. **Risks of the cheapest providers**: data residency and DPDP for health, finance and ID data (Chinese-hosted endpoints should not receive these; pin an India/EU host or self-host open weights, which the config comment already allows for GLM), peak-hour pricing, rate limits, deprecation notices, and quality drift when a provider swaps weights. Use `USAGE_PRICES` to keep our meter honest when we switch.

## How to turn this shortlist into a decision (cheap, measurable)
- Run each of rows 1-12 on the same cards (REPEAT card tasks R1-R12, tool card, hard card), same prompts, `pass^3`, planted traps, and report **correct tasks per rupee** and **silent-error rate**, not price alone.
- Route by measured result: promote a cheap model to Tier 1 only if its silent-error rate is no worse than Haiku 5.5 on our traps.
- Re-run monthly (prices and models change).
- Cost to do the run: with a 60-task card and ~12 models, under Rs 1,000 for the cheap tier (estimate).

## Sources (secondary; verify on vendor pages before wiring)
[Artificial Analysis OpenAI provider page](https://artificialanalysis.ai/providers/openai) · [Artificial Analysis rankings Oct 2026 snapshot](https://www.token360.ai/en-US/blog/artificial-analysis-rankings-october-2026-9511b9cb-f83b-40eb-8e6a-e2b3e1eba549) ·
[DeepSeek pricing roundup](https://dev.to/hassann/deepseek-v4-api-pricing-2j8f) · [DeepSeek discount made permanent](https://www.pulse.bot/ai/news/deepseek-makes-its-75-percent-discount-permanent-pricing-output-tokens-at-least-34x-below-gpt-55-bc55d971-c112-4615-b74a-8da763a5bfff/) ·
[Qwen API pricing Sep 2026](https://developer.puter.com/tutorials/qwen-api-pricing/) · [Qwen3.6-Flash](https://www.developersdigest.tech/models/qwen3-6-flash) ·
[GLM-5 pricing](https://anotherwrapper.com/llm-pricing/glm-5) · [GLM-5 vs MiniMax M2](https://anotherwrapper.com/llm-pricing/minimax-m2/glm-5) · [Gemini 3 Flash pricing](https://anotherwrapper.com/llm-pricing/gemini-3-flash-preview) ·
[Gemini 3.5 Flash-Lite pricing](https://anotherwrapper.com/llm-pricing/gemini-3.5-flash-lite) · [GPT-5 nano vs Gemini 2.5 Flash-Lite](https://anotherwrapper.com/tools/llm-pricing/gemini-2.5-flash-lite/gpt-5-nano-2025-08-07) ·
[OpenRouter: open-weight models that matter, June 2026](https://openrouter.ai/blog/insights/the-open-weight-models-that-matter-june-2026/) · [Coding model cost-performance matrix](https://tkmxai.it.com/the-2026-coding-model-cost-performance-matrix) ·
[Cheapest credible coding agent API (Qwen3-Coder-Next)](https://dev.to/jovan_chan_9500711396d4e6/qwen3-coder-next-review-2026-80b-params-3b-active-and-the-cheapest-credible-coding-agent-api-5h3j) · [Hoola price table: `server/app/usage.py`].
