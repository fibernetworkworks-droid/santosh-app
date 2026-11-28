# OmniRoute, read for Hoola (28 Nov 2026)

Repo: github.com/cheaper-inference/OmniRoute, commit 5c36ba1c (28 Nov 2026), version 3.8.55, MIT licence
(Cheaper Inference / Diego Souza). Same project Hoola already points at with `OMNIROUTE_URL` since v0.698
(it moved from diegosouzapw/OmniRoute). TypeScript / Next.js 16 / Node 22+, SQLite, ~30,900 files.

## What it is

An AI gateway: one OpenAI-style address (`/v1/...`, also Anthropic `/v1/messages`, Gemini `/v1beta`,
Ollama) in front of hundreds of model providers. A request names a model, a "combo" (an ordered list of
provider/model pairs) or `auto/...`, and OmniRoute picks the target, translates the format, retries and
falls back. Around that: a dashboard of ~60 pages (providers, combos, costs, health, logs, cache,
compression, playground, media, memory, skills, MCP / A2A servers, tunnels, Electron app).

## The parts that are good engineering (ideas Hoola can use)

| Idea | What OmniRoute does | What Hoola has today |
|---|---|---|
| Combos + routing strategies | 22 strategies: priority, weighted, round-robin, cost, p95 latency + error penalty, SLA, last-known-good (LKGP) sticky, reset-aware quota, fusion | The Box (`pipeline/`): kind + level + model from public leaderboards, 2 backups, same model 30 min, hand-overs |
| `auto/<category>:<tier>` | coding / reasoning / vision / chat x fast / cheap / reliable / free / pro, fail-closed when nothing fits | Tiers ULTRA / HIGH / MEDIUM / LOW per user + jobs (`tiers.py`) |
| Per-request budget | `X-OmniRoute-Budget` (max USD) + `strict` (refuse) or `cheapest` (step down) | Credits meter + OpenRouter max_price 1.25x; no per-ask ceiling |
| 3-layer resilience | provider circuit breaker, connection cooldown, model lockout; first-byte watchdog | `runner` hand-over on error / 8 s no first word / race; banned model off 24 h |
| Fusion | ask a panel of models in parallel, a judge writes one answer; tool calls bypass the panel | Nothing like it for chat |
| Context relay | a hand-off summary when the route moves to another model / account | The Box's fixed hand-off package (plan), partly built |
| Semantic cache | same model + same messages + temperature 0 -> cached answer, hit/miss headers | None |
| Prompt compression | lite..ultra modes, "RTK" filters that shrink tool / command output | Tool results cleared past a size, big outputs spilled to files |
| Analytics | tokens, cost, latency percentiles, errors per provider / model / key, heatmaps | `usage` + credits + `pipeline/watch.py` on disk; no page to see it |
| Playground | one prompt on any model, streaming | Model dropdown in chat only |
| Model + price sync | 24 h model list refresh, LiteLLM price table | Daily OpenRouter list + LMArena feed (`pipeline/feed.py`) |
| Guardrails | PII masker, prompt-injection guard, error text cleaned before clients | `guard.py`, `pii.mask_sensitive`, draft / claim checks |

## The parts Hoola must NOT take (our non-negotiable rules)

1. **Subscription logins as an API.** The "OAuth providers" (Claude Code, Codex, GitHub Copilot, Cursor,
   Kiro, Windsurf, Antigravity, Kimi Coding...) turn a person's monthly plan into a general API. The
   providers' terms do not allow this, and CLAUDE.md says "no consumer-subscription OAuth" (v0.698:
   "official keys only... never subscription logins").
2. **Stealth.** `docs/security/STEALTH_GUIDE.md`: TLS fingerprints that pretend to be Chrome, CLI
   fingerprint and body-shape copying, "integrity tokens", built so providers' checks for unofficial
   clients do not catch it. That is detection evasion; Hoola refuses it.
3. **Web-cookie providers.** Claude web, ChatGPT web, Perplexity, Grok, Notion, LMArena through a
   browser session's cookies. Not an official route.
4. **Embedded "public" credentials.** `PUBLIC_CREDS.md`: other apps' OAuth client ids / Firebase keys
   XOR-masked in the source so secret scanners do not see them.
5. **MITM proxy + CA certificates** (`src/mitm/`) to intercept other tools' traffic.
6. **"Free tier" pools that are really the above.** Free tiers with an official key (Groq, Gemini AI
   Studio, NVIDIA, OpenRouter :free) are fine; keyless or cookie ones are not.
7. **Reselling model access.** An address that sells raw model calls to other people is forbidden by the
   providers; Hoola's own API sells Hoola's tools, never a raw model pipe (v0.877).

## What this means for a new Hoola section

Hoola already has most of the routing brain (the Box, tiers, hand-overs, credits) but **no page where she
can see or steer it**. The useful new section is that page, built in Python on Hoola's own engine, with
the good ideas above added, and with official keys only.

Working name: **Hoola Models** (console sidebar row, phone Tools tile). Proposed pages:

1. **Today** - calls, cost, median and slow (p95) answer time, errors, hand-overs, per model and per
   feature (chat, Hoola Code, Web Studio, calls, studios), from the meter and the Box's watch.
2. **Providers** - which official providers have a key (OpenRouter, Anthropic, Gemini, Groq, Mistral,
   NVIDIA, Z.ai, AIHubMix, her own OpenAI-compatible server), a free check of each key, live health
   (open / cooling / closed), the models each offers with price.
3. **Routes** - what each job uses (tier rows from `tiers.py`, the Box's level tables), her pin per job,
   a combo she can build (ordered models + strategy: priority / cheapest / fastest / last-good).
4. **Budgets** - a ceiling per ask, per day, per feature, and what happens at the ceiling (refuse or step
   to a cheaper model).
5. **Playground** - one prompt on 2-4 models side by side, with time, tokens and price.
6. **Log** - every model call (no message text): model, feature, time, tokens, price, outcome, hand-over
   reason.
7. **Settings** - fusion for hard asks (panel + judge, off by default, priced first), answer cache for
   repeated exact asks (off by default; never for her personal data), tool-output compression.

OmniRoute itself stays optional: when `OMNIROUTE_URL` is set it shows as one provider on page 2, and
only its official-key routes are used.

## Not verified

Nothing was run: this is a read of the docs and source at commit 5c36ba1c. Strategy behaviour is as the
docs describe it.
