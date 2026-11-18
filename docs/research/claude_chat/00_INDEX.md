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

Items marked UNCONFIRMED in these files came from non-Anthropic sources or could not be confirmed.
