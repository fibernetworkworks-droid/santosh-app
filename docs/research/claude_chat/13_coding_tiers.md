# Four tiers for coding (19 Nov 2026)

Owner's ask: "NOW FOR CODING" (after `11_model_tiers.md` and `12_media_tiers.md`).

Coding in Hoola is three different jobs, each measured on its own public board (LMArena, 11 Nov 2026, 1,000+ votes):
building whole apps and websites (WebDev board: Web Studio, App Studio), coding questions and small fixes (text
"coding" board), and long coding sessions that run commands (agent board: Hoola Code; its cost per job is measured by
LMArena). Same rule as the other tiers: points below the best, the cheapest model that reaches the tier. Gemini 4
Carbon left out (refused on her account). Price = the maker's own standard price, read 19 Nov, Rs 88 to the dollar.

| Job | ULTRA (best, burns credit) | HIGH | MEDIUM | LOW |
|---|---|---|---|---|
| Building apps and websites | Claude Opus 5.5 (10 below #1 Claude Fable 5.2, half its price) | Claude Sonnet 5.5 (54 below) | Qwen4-Max (76 below) | DeepSeek V4.1 Flash (165 below) |
| cost of one site, estimated (30 calls, 10k read + 4k written each) | Rs 317 (Fable 5.2: Rs 634) | Rs 158 | Rs 83 | Rs 21 |
| Coding questions, explain code, small fixes (one ask, 2,500 written) | Gemini 4 Argon, Rs 5.72 (24 below) | MiMo-V2.6-Pro, Rs 0.96 (31 below; only 1,091 votes) | GLM-5.3-Flash, Rs 0.37 (55 below) | MiMo-V2.6-Flash, Rs 0.31 / Claude Haiku 5.5, Rs 0.29 |
| Hoola Code: long sessions with commands (one job, measured) | Claude Fable 5.2, #1, Rs 794 (Opus 5.5, #2, Rs 497) | GPT-6.1 Terra, #10, Rs 77 (#4 at running commands, rarely invents tools); Claude Sonnet 5.5, #4, Rs 305 | DeepSeek V4.1 Flash, #30, Rs 12 | GPT-6 Luna, #32, Rs 7 (#5 at not inventing tools) |
| Backup (another company) | Gemini 4 Argon | GPT-6.1 Terra / Gemini 3.8 Flash | GLM-5.3-Flash | Claude Haiku 5.5 |

100 points apart = the higher wins about 64 times in 100; 165 apart = about 72 times in 100.

## What Hoola uses today

| Where | Model today | Its place |
|---|---|---|
| Hoola Code | Qwen 3.8 27B (v0.926) | agent board #48 of 57 at Rs 34 a job; 236 below on apps. Hoola's own coding card: 11 of 12 (Claude Opus: 12 of 12) |
| Web Studio | Qwen 3.8 27B (v0.984) | 236 below the best on apps and websites = under the LOW tier |
| App Studio / App Engine | the chat's model / Claude by setting | - |

Findings:
1. **Claude owns building.** The top 3 for apps and websites are Claude Fable 5.2, Opus 5.5, Sonnet 5.5; the first
   other company is 58+ points behind, the cheap models 165+.
2. **Qwen 3.8 27B is weaker AND dearer than DeepSeek V4.1 Flash on the boards** (agent #48 at Rs 34 a job against #30
   at Rs 12; apps 236 below against 165). But Hoola's own coding card gave Qwen 11 of 12, and her own card outranks
   any board: DeepSeek should run the same card before anything changes.
3. **The Web Studio builds on a model below LOW for building.** Moving it to DeepSeek (LOW, about Rs 21 a site) or
   Claude Sonnet 5.5 (HIGH, about Rs 158 a site) is the biggest quality step in coding.

Site cost is an ESTIMATE (call count and sizes assumed); the agent-board job costs are LMArena's measured medians on
their tasks, not Hoola's.
