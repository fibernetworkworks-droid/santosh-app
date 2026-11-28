# Hoola coworker vs OpenClaw - capability check (28 Nov 2026)

Owner: "https://github.com/openclaw/openclaw.git --- NOW CHECK THAT -- HOOLA COWORKER HAS ALL THIS CAPABILTIES OR NOT AS OPENCLAW DOES"

Source read: github.com/openclaw/openclaw at commit fe1e82080 (27 Nov 2026), MIT licence - README, VISION.md, docs/ (concepts,
tools, channels, nodes, platforms, gateway, automation, plugins, providers) and the 198 folders under extensions/. Hoola side
checked against this repo (server/app, lib/, tool/android, desktop*, CLAUDE.md history). Nothing was run.

## What OpenClaw is, in one paragraph

An open-source personal assistant that runs on YOUR computer (a "Gateway" on Node), talks to you in 25+ chat apps and
native apps (macOS, iOS, Android, Windows, Linux), swaps models freely (hosted or local), and grows by plugins (about 200
bundled: chat apps, model providers, tools, memory, devices, meetings) plus skills from ClawHub. No hosted service, no
paid tier. Its own words: "the AI that actually does things ... on your devices, in your channels, with your rules".

## Verdict in short

Hoola already does most of what OpenClaw does - and much more on the business side (AI employees, Route with Make
parity, studios, website / app builders, Hoola PC pool, Telecaller, finance desks, wallet). OpenClaw is ahead in five
places: **how many chat apps you can talk to your own assistant from**, **joining meetings live**, **running on your own
machine with local models**, **an open plugin SDK + marketplace**, and **a few agent-runtime features** (Code Mode /
Swarm, side questions, standing intents, driving outside coding agents, a flight-recorder export).

Legend: **Has** = equal or better in Hoola · **Partly** = some of it · **Missing** = not in Hoola · **By design** = a
choice, not a gap.

## 1. Where you talk to it

| OpenClaw | Hoola | Verdict |
|---|---|---|
| Control UI (web dashboard), TUI, CLI | Web console + Route / Code / studio pages; no terminal UI | Has (no TUI/CLI: by design) |
| WhatsApp, Telegram, Slack, Teams to your own assistant | `bahar.py`: WhatsApp (her business number, official API), Telegram, Slack, Teams - owner only, one paired sender | Has |
| Discord, iMessage, Signal, Matrix, Google Chat, LINE, Mattermost, IRC, Nostr, Feishu, Zalo, WeChat, Twitch, Nextcloud Talk, Synology, SMS, X ... to your own assistant | Not as channels to HER assistant (Discord / Mattermost / Telegram only as Route Send steps; LINE / Viber / WeChat / Zalo / SMS / X only in the Support desk for her customers) | **Missing** |
| Group chats, several people in one room, mention gating, bot-loop protection | Owner-only DMs; customer chats go to the Support desk | **Missing** |
| Native apps macOS / iOS / Android / Windows / Linux | Android app (Flutter), web console, desktop agent for Windows / Mac / Linux; no iPhone / iPad app of Hoola itself | **Partly** (no iOS app) |
| Voice "Talk" realtime + voice wake word synced across devices | Gemini Live calls (24/7, parks when quiet), phone wake word (`train-wakeword.yml`) | Has (wake word phone-only) |
| Phone calls (voice-call plugin: Twilio / Telnyx) | Telecaller: calls out / in on 9 providers, any country | Has (more) |
| Join Google Meet / Zoom / Teams / Slack huddles as a participant | Transcribes recordings (Kaan), meeting notes; does not join a live meeting | **Missing** |
| A2A 1.0 (agents of other platforms) | `net/a2a.py` A2A 1.0 bridge + Hoola Network avatar-to-avatar | Has |
| Pairing unknown senders by code | 6-digit pairing for channels and PCs | Has |

## 2. Models

| OpenClaw | Hoola | Verdict |
|---|---|---|
| 80+ providers (Anthropic, OpenAI, Google, OpenRouter, Groq, Mistral, DeepSeek, Qwen, NVIDIA ...) | OpenRouter + Anthropic + Gemini / Groq / Mistral / NVIDIA / Z.ai / AIHubMix, per-user model dropdown, tiers | Has |
| Local models: Ollama, LM Studio, llama.cpp, vLLM, SGLang, MLX | Only by pointing the OpenAI-style base URL at one by hand; no local-model setup or checks | **Partly** |
| Model failover | The Box: backups at the same level, hand-over rules, banned models off a day | Has (more) |
| Prompt caching, usage / cost tracking | cache_control on Claude paths, usage meter, Hoola Credits | Has |
| Thinking levels per turn | adaptive thinking, effort by turn | Has |

## 3. Agent runtime

| OpenClaw | Hoola | Verdict |
|---|---|---|
| Agent loop, sessions, queue, steering (/steer) | LangGraph turn graph, turn inbox, notes into a running task, Stop | Has |
| /btw side question that stays out of the history | - | **Missing** |
| Compaction, session pruning, context engine | checkpoint compaction, 1M window, tool-result clearing | Has |
| Tool search (deferred tool schemas) | Claude-style tool_search + deferred tools | Has |
| **Code Mode** (model writes a script that calls tools instead of seeing all schemas) + **Swarm** (fan out sub-agents from that script) | pylab runs Python but cannot call Hoola's tools; crews / background agents, not scripted fan-out | **Missing** |
| Sub-agents, nesting, background agents, parallel specialist lanes | crews (49+ roles), background agents, Hoola Code agents | Has |
| Goal with token budget; progress card; progress drafts | long jobs (kaam_plan, goal rounds, research budgets), plan card, one working row | Has |
| Loop detection | same-tool loop breaker (v0.705) | Has |
| Lobster typed workflows with approval / input gates and resume tokens | Route (DHARA): approvals, waits, resume links, Make parity | Has (more) |
| Decision models (typed choice / score / boolean judge) | draft check, safety reviewer, judges - no general typed tool | **Partly** |
| Managed worktrees, cloud workers, sandbox, elevated exec | Hoola Code worktrees + locked box, Hoola PC pool, pylab | Has |
| ACP: drive outside coding harnesses (Claude Code, Codex, Cursor, Copilot) | Hoola Code is its own engine; cannot drive those | **Missing** |
| Trajectory export (flight-recorder bundle of a session) | request dump, PC step trace, Hoola Code /export - no one bundle for a chat | **Partly** |

## 4. Memory and self-learning

| OpenClaw | Hoola | Verdict |
|---|---|---|
| Built-in memory, memory search, active-memory deep recall | facts, diary, one memory door, coder vault, knowledge graph, yaad_khojo | Has |
| USER.md (user model) | "Mere baare mein" page (editable, daily) | Has |
| SOUL.md (agent's voice / personality file) | avatar name, voice, persona prompt; no free-text personality file she edits | **Partly** |
| Dreaming (light / deep / REM + Dream Diary), on by default | ported in v0.484 (`coder/dreams.py`) but **off by default** | **Partly** |
| Knowledge vault / memory-wiki with claims and evidence | gyaan, kgmemory, research dossiers - no compiled wiki pages | **Partly** |
| Standing intents ("when X is mentioned, remind me ...") | reminders, routines, Route triggers - nothing fires on words in a later chat | **Missing** |
| Standing orders (permanent authority for a program) | AI-employee trust ladder, Route switched on | Has |
| Self-learning: background review saves learned skills, Skill Workshop (undo, diet, /learn) | learned skills (v0.494), corrections become preferences (v0.615), video learner, skill desk | Has (no background review of finished work) |
| Import Claude / Codex sessions, migrate from Claude memory | - | **Missing** |

## 5. Tools

| OpenClaw | Hoola | Verdict |
|---|---|---|
| Browser control, Chrome extension, browser login hand-off | own browser, jharokha, PC Chrome via extension, private sign-in form | Has |
| Computer use on the gateway / paired desktops | her PC + Hoola PC pool, exams, routines | Has (more) |
| Exec / shell with approvals, permission modes | Hoola PC run with cards, Hoola Code modes + safety reviewer | Has |
| Web search (Brave, Exa, Tavily, Perplexity, SearXNG ...), web fetch, Firecrawl, readability | search, reach, scrape lane (own Firecrawl), Parallel, Exa | Has |
| Deep research | research engine R0-R9 with claims checks | Has (more) |
| PDF, documents, diffs, apply_patch | doc studio, HOOLA PRINT, Hoola Code diffs | Has |
| Image / video / music generation, TTS (ElevenLabs, Azure, local) | Create studios, Cinema, Vocal (Gemini + ElevenLabs), Music | Has (more) |
| show_widget (HTML widget inline, pin to dashboard), Canvas | artifact pages in chat, side panel | Has (no pin-to-dashboard) |
| MCP client and MCP events | MCP servers + repo .mcp.json, stdio in box | Has |
| 1Password, secrets, vault | 1Password sign-ins, Hoola Cred | Has |
| GitHub, team reports (GitHub + Discord digests) | Hoola Code + scheduled tasks; no team digest | **Partly** |
| Workboard (Kanban of agent cards) | Work list, Hoola Auto agents board | **Partly** |
| Ask user mid-run | ask_user, cards | Has |

## 6. Devices ("nodes")

| OpenClaw | Hoola | Verdict |
|---|---|---|
| Paired phone / desktop: camera, screen, location, file transfer, notifications, media playback, device commands | phone jobs, location, Bluetooth, home devices, file to chat, PC files | Has |
| iOS HealthKit day summaries | - (no iOS app) | **Missing** |
| Bonjour discovery, Tailscale / remote access | hosted server, pairing codes | By design |

## 7. Automation

| OpenClaw | Hoola | Verdict |
|---|---|---|
| Cron jobs, webhooks, Gmail / IMAP watch, hooks on events | Route (schedules, webhooks, app events, forms, chat, errors, MCP), mail rules, routines | Has (more) |

## 8. Platform, team, ops

| OpenClaw | Hoola | Verdict |
|---|---|---|
| Runs on your own hardware, no hosted service | Hoola is a hosted server; her PC agent is local | By design |
| Plugin SDK (channels, providers, tools, memory) + ClawHub marketplace with publisher review | Connectors (Composio, ~680 packs), MCP, Hoola Code plugins - no open SDK for others to extend her assistant, no marketplace | **Missing** |
| Multiplayer gateway: one assistant shared by a trusted team, several people in one session, session share | per-person tenants, team roles on desks, route sharing, read-only links | **Partly** |
| OpenAI-compatible /v1/chat/completions on the gateway | Hoola Agent API (tools), AI Apps API + MCP; no OpenAI-compatible endpoint | **Partly** |
| Tools-invoke HTTP API | Hoola Agent API run a tool | Has |
| doctor --fix, auto update, restart recovery | vps-ops deploy, turn resume after restart | Has |
| OpenTelemetry / Prometheus export, audit log | looplag, healthz, desk audit trails; no OTel / Prometheus | **Partly** |

## What Hoola has that OpenClaw does not

AI Employees with their own desks (finance, tax, payroll, books, support, SEO, social, leads, telecaller, construction,
insurance ...), Hoola Route with Make parity and the n8n library, Web / App / Game studios that publish, Create / Cinema /
Vocal / Music studios, Hoola PC cloud pool with exams and routines, Hoola Wallet, Hoola Network (avatars talking to
avatars), country packs and India's official rails, the Telecaller.

## Gaps worth closing, in order

1. **More chat apps to talk to her own Hoola** - Discord, Signal, Matrix, Google Chat, LINE, iMessage (via a Mac), plus
   group chats with mention gating. `bahar.py` is the place; each with its pairing.
2. **Join meetings live** - Google Meet / Zoom / Teams as a participant (listen, take notes, answer when asked), Chrome on
   Hoola PC.
3. **Hoola on iPhone / iPad** - the Flutter app built for iOS (also unlocks HealthKit summaries).
4. **Standing intents + /btw side questions** - small runtime features with daily value.
5. **Code Mode + Swarm** - the model writes one script that calls Hoola's tools and fans out sub-agents (fewer tool
   schemas per turn, cheaper long jobs).
6. **Dreaming on by default** with a Dream Diary she can read; a SOUL file she edits.
7. **Local models** - a checked setup for Ollama / LM Studio / vLLM.
8. **An open plugin SDK** (later: a marketplace) and an OpenAI-compatible endpoint.
9. **Trajectory export** of one chat, OTel / Prometheus metrics.

OpenClaw is MIT: ideas and code may be used with the notice kept.
