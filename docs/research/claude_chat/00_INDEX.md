# Claude chat research (18 Nov 2026) - index

Owner's ask: find every detail of Claude chat - every feature and the smoothness strategy - so Hoola chat can be the same.
The plan built from these files: `docs/CLAUDE_CHAT_100_PLAN.md`.

| File | What it holds |
|---|---|
| `01_features.md` | Every Claude.ai feature from the help centre and release notes: composer, model and effort, thinking display, tools, Research, artifacts, inline visuals, files, projects, memory, incognito, sharing, connectors, skills, voice, long tasks, limits and exact error messages |
| `02_reply_rules.md` | The rules in Anthropic's published claude.ai system prompts and prompting docs that make replies relevant and smooth: formatting, conversation, honesty, tools, pacing, what to leave out; ranked top 15 |
| `03_reliability.md` | How Claude finishes multi-step work reliably: the loop, done-checks, verification, plans and state, tool design, errors, context hygiene, caching, sub-agents, stop reasons, evals; ranked top 12 |
| `04_smoothness.md` | Screen techniques for a smooth streaming chat: stream events, pacing, incremental markdown, scrolling, tool / thinking rows, stop / retry / branch, resuming after leaving, mobile; ranked top 15 |
| `05_hoola_audit.md` | Code audit of Hoola chat at v0.997: switches, the real path of one message, what is added to replies, what answers without the model, long work, gaps |
| `06_writer_models.md` | Which model writes her replies (GLM-5.3, DeepSeek V4.1 Flash backup) |
| `07_worker_models.md` | When workers should run, and her 18 Nov test (comma splits, Sonnet / Opus workers) |
| `08_worker_atlas.md` | 26 kinds of worker jobs, 600+ model rows with 18 Nov prices, Main / Backup / Premium / Budget picks |
| `09_worker_prices_live.md` | Live prices per provider (up to 19x apart; Hoola asks for the fastest) + the worker card: 22 models on 11 Hoola jobs |
| `10_top_models.md` | The top-performing model in every field (text, industry boards, media, voice, PC) with cost |
| `11_model_tiers.md` | Four tiers ULTRA / HIGH / MEDIUM / LOW: the model for each job in each tier and what a message costs |
| `12_media_tiers.md` | The same four tiers for pictures, video, avatars, voice, speech to text and music, with the cost of common jobs |
| `13_coding_tiers.md` | Four tiers for coding (building apps / sites, coding questions, long Hoola Code sessions) + what Hoola uses today |
| `14_call_employee_tiers.md` | Four tiers for voice calls (voice + brain, cost a minute) and AI employees (cost a job, a month) |
| `15_tier_writers.md` | The chat writer for each tier, chosen on words AND tool calls (v0.999.11) |

Items marked UNCONFIRMED in these files came from non-Anthropic sources or could not be confirmed.
