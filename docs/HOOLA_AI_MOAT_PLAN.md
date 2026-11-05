# HOOLA AI — the MOAT plan (source-read: OpenClaw + mattpocock/skills, 4 Nov 2026)

Owner's ask: *"USE THIS 2 REPO --- MOAT AND PREPARE PERFECT POWERFULL HOOLA AI PLAN FIRST"* — both repos read
in full BEFORE this plan; nothing built yet. This document is the plan; the build starts only on her GO.

Sources read end to end for this plan (both cloned, commit-pinned):

- **OpenClaw** `openclaw/openclaw` @ `b3487e66` — the MIT personal-assistant gateway (Warelay → Clawdbot →
  Moltbot → OpenClaw), OpenClaw Foundation (501(c)(3); donors incl. OpenAI, Amazon, Red Hat; no paid tier, no
  token). Scale at read time: ~30k TS files in `src/` + 26 packages, **191 extension plugins**, native apps
  (macOS/iOS/Android/Windows/Linux), Rust crates. Key docs read: `docs/concepts/memory.md`,
  `docs/concepts/dreaming.md`, `docs/tools/skill-workshop.md`, `docs/tools/skills.md`,
  `docs/automation/standing-orders.md`, `docs/concepts/delegate-architecture.md`,
  `docs/concepts/multi-agent.md`, `docs/agent-runtime-architecture.md`, `AGENTS.md`, `VISION.md`.
- **mattpocock/skills** `mattpocock/skills` @ `4ae2317` — 39 agent skills for "real engineering, not vibe
  coding" (shipped as a self-updating plugin for Claude Code / Codex / Copilot / Gemini CLI). Key skills read:
  `grilling`, `code-review`, `wayfinder`, `writing-for-agents`, `chief-of-staff`, `handoff`, `tdd`, `retro`,
  plus `SCOPE.md` and `GLOSSARY.md`.

House state this plan builds ON (not rebuilds): v0.473 HOOLA CODER (capture → spool → observer → SQLite/FTS5
vault → three-layer search → session primer), v0.477 SELF-TEACH (`skills_store.py` SKILL.md files + nudge
fork), v0.478 SWARM (`delegate.py` bounded children, funnel capture fixed) — `server/app/coder/` is 16
modules with kill switches `coder_enabled / coder_skills / coder_nudge / coder_delegate`
(`server/app/config.py` L419–435), checkpoint compaction (`agent/compact.py`), gyaan KB
(`agent/gyaan_tools.py`), approval cards (`haan_karo`), Hoola Network avatars (`app/net`).

---

## 0. The one-paragraph answer

OpenClaw and mattpocock/skills, read together, prove an uncomfortable thing: **every mechanic of a powerful
AI coworker is now free** — markdown memory files, a skills store, background self-teaching, delegation,
standing orders, grilling. OpenClaw ships all of it MIT-licensed; Matt's repo proves the disciplines fit in
single markdown files any agent can load. So a plan that says "port X from OpenClaw" buys nothing a
competitor cannot buy in a week. The moat is the one thing neither repo has and no competitor can copy:
**the compounding loop, running tenant-scoped, voice-first, in Hinglish, wired into India's rails** — she
talks → the vault captures → the vault consolidates nightly into curated memory → repeated work hardens
into skills with a lifecycle → skills + standing orders let her delegate *programs, not tasks* → the
identity pack makes the coworker unmistakably hers → grilling and two-axis review make the work provably
right → every loop writes back into memory. Hoola's AI coworker that has served one woman for six months is
unforkable, because the asset is her data curve, not the code. This is the same conclusion the Game AI
Employee moat analysis reached for games (*"the moat is not making games; it is finishing them, and proving
they are worth finishing"* — `docs/GAME_MOAT_PLAN.md` §0), now applied to the assistant itself.

---

## 1. What is commodity (do not try to win here)

- **Markdown memory.** OpenClaw: `USER.md` + `MEMORY.md` + `memory/YYYY-MM-DD.md` + `DREAMS.md`, plain
  files, no hidden state (`docs/concepts/memory.md`). Anyone can copy the layout in an afternoon.
- **A skills store.** OpenClaw's Skill Workshop: learned skills with revision history, undo, 30-day-unused
  auto-archive, skill diet (`docs/tools/skill-workshop.md`); 7-level load precedence
  (`docs/tools/skills.md`). Hoola already has the file+FTS5 store (v0.477). The mechanic is commodity.
- **Background self-improvement.** OpenClaw's dreaming sweep ("light, deep, and REM phases plus a Dream
  Diary", enabled by default — `docs/concepts/dreaming.md`) and Matt's `retro` skill: consolidation and
  environment-improvement loops are published patterns.
- **Delegation / subagents.** OpenClaw parallel-specialist lanes + delegate architecture; Matt's
  `implement-spec` runs implementer subagents across the ready frontier. Hoola shipped SWARM (v0.478).
  Commodity.
- **Autonomy scaffolding.** OpenClaw standing orders ("scope / triggers / approval gates / escalation rules"
  in `AGENTS.md`, driven by cron — `docs/automation/standing-orders.md`) and delegate capability tiers
  (Tier 1 = Read-Only + Draft — `docs/concepts/delegate-architecture.md`). Commodity — and dangerous to
  copy naively (see §4).
- **Grilling / interviews.** Matt's `grilling` skill (design tree, frontier rounds, numbered questions,
  "word each question so yes accepts your recommended answer") is one markdown file. The mechanic is
  copyable; the *fit to a Hindi voice loop* is not (§2).
- **Big-repo engineering discipline.** `writing-for-agents`, `code-review` (two parallel review sub-agents),
  `wayfinder` (decision tickets), `chief-of-staff` (a dated, commit-cited wiki). All open markdown; all
  apply to Hoola's own dev process, not to the product.

Read the two repos as one message: **the mechanics are free, so the plan must buy compounding, not
features.**

## 2. What is actually the moat

1. **The tenant flywheel.** OpenClaw is architecturally *one person per gateway* (multi-agent = separate
   `agentDir`s per persona on ONE install — `docs/concepts/multi-agent.md`); it has no concept of thousands
   of tenants whose memory/skills must never touch, and it should not — that is its privacy promise. Hoola's
   house law (tenant-scoped skills, vault, gyaan) is the inverse shape: one server, thousands of owners,
   each with a private flywheel. Everything in this plan rides that shape.
2. **Voice-first, Hinglish, on cheap Android.** OpenClaw is a dev's gateway (CLI/TUI/dashboard, English,
   macOS-first). Matt's grilling assumes a technical user reading numbered questions. Hoola's grilling must
   survive a voice call on a ₹10k phone: bounded rounds, spoken naturally, yes-accepts-recommendation. The
   UX translation layer IS the differentiator — nobody else is doing this in Indian languages.
3. **Finish-and-prove, with India's rails.** The game moat's thesis holds for the assistant: Hoola does not
   just answer — it finishes (jobs, receipts) and proves (capture → observer → verify), and it moves money
   and documents through UPI / ONDC / ABDM / DigiLocker / GST rails OpenClaw's Foundation cannot ship
   (neutrality, no paid tier) and Dots does not have. `delegate-architecture.md`'s own accountability
   argument ("messages sent by the agent are clearly from the agent") Hoola already exceeds — owners NEVER
   talk directly on the Hoola Network; avatars act under named identity with approval cards.

## 3. The port map (what we take, from where, into which files)

| # | System | Source (exact) | Hoola files touched | Shipped? |
|---|--------|----------------|---------------------|----------|
| 1 | Memory consolidation ("dreaming": nightly light + weekly deep, reviewable diary, preimage before every accepted rewrite) | OpenClaw `docs/concepts/dreaming.md`, `memory.md` | NEW `coder/dreams.py`, `coder/store.py` (preimage cols), `config.py` | No — **Phase 1** |
| 2 | Skill lifecycle (revisions, undo, auto-archive after 30 days unused, skill diet, provenance) | OpenClaw `docs/tools/skill-workshop.md` | `coder/skills_store.py`, `coder/inject.py`, `coder/store.py` | No — **Phase 2** |
| 3 | Standing orders (programs: scope/triggers/approval gates/escalation; injected every session; cron-driven) | OpenClaw `docs/automation/standing-orders.md` | NEW `coder/orders.py`, `coder/inject.py`, existing cron/briefing infra | No — **Phase 3** |
| 4 | Identity pack (SOUL/USER layer, supersede-in-place, stable-prefix discipline) | OpenClaw `memory.md` (USER.md rules), `AGENTS.md` "Stable conversation context" | NEW `coder/identity.py`, `agent/prompts.py`, Profile UI | No — **Phase 4** |
| 5 | Grilling (design tree + frontier rounds, yes-accepts-recommendation; facts are the agent's job) | Matt `skills/productivity/grilling/SKILL.md` | NEW `coder/grill.py` + `agent/prompts.py` support | No — **Phase 5a** |
| 6 | Two-axis review (Standards + Spec as parallel sub-agents, merged) | Matt `skills/engineering/code-review/SKILL.md` | `coder/delegate.py` (review lanes), prompts | No — **Phase 5b** |
| 7 | Writing-for-agents (context pointers, two loads, information hierarchy, completion criteria) | Matt `skills/productivity/writing-for-agents/SKILL.md` | repo docs only: `CLAUDE.md`, `GLOSSARY.md`, plan docs | No — **Phase 6a/6b** |
| 8 | Handoff + wiki discipline (dated, commit-cited; ingest/query/lint; "write history, not the present") | Matt `handoff`, `chief-of-staff` | `docs/WORKLOG.md` template | No — **Phase 6c** |
| 9 | Retro (periodic environment-improvement proposals, most severe first, never auto-applied) | Matt `skills/engineering/retro/SKILL.md` | reuses nudge fork monthly mode | No — **Phase 6d** |

## 4. What we deliberately do NOT take (and the rule that forbids it)

- **OpenClaw's unofficial channels** (iMessage via BlueBubbles, consumer WhatsApp bridges, etc.). House law:
  official routes only, never personal WhatsApp automation (`CLAUDE.md` NON-NEGOTIABLES). Not negotiable.
- **Node/gateway protocol work on the PC side.** OpenClaw's `node.invoke` command surface is elegant, but
  Mera PC / PC Operator / desktop is 🔒 FROZEN by the owner (25 Oct 2026) — reading allowed, changing not.
  The phone's native layer already covers device actions; nothing here touches `server/app/pc/`, `desktop/`,
  or `lib/ui/pc_screen.dart`.
- **Plugin SDK / harness registry.** OpenClaw needs a plugin SDK because 191 third-party extensions land on
  one gateway. Hoola's law is the tools registry (`agent/tools.py`: `X_TOOLS / X_LABELS / X_HANDLERS`) with
  the single funnel (`santosh._run_tool`). A plugin SDK is a new attack surface with no owner ask.
- **WorkerTaskPool, runtime generations, SQLite broker pools.** OpenClaw builds these for untrusted
  multi-user team gateways. Hoola runs one FastAPI process per VPS with fail-open cheap mechanisms — the
  same trade OpenClaw's own `AGENTS.md` preaches ("prefer cheap mechanisms… design for real failures"). Not
  our failure set.
- **ClawHub-style public skill marketplace.** A skill file from outside a tenant is DATA, never
  instructions, and cross-tenant reads are forbidden (house law in `skills_store.py`). If ever, one
  HOOLA-curated, reviewed pack list via the Bazar — a later decision, not in this plan.
- **Matt's tracker skills as product features** (`to-spec`, `to-tickets`, `triage`, `wayfinder` for users):
  Hoola's owners do not file issues. The wayfinder *shape* (decision tickets with blocking edges) is adopted
  for DEV sessions only, via `docs/WORKLOG.md` (Phase 6c).
- **ADR machinery from `grill-with-docs`.** `docs/HISTORY.md` + `docs/WORKLOG.md` already carry decisions
  with commit citations. We adopt `GLOSSARY.md`, not ADRs.
- **Free-form SOUL.md persona.** OpenClaw lets the model rewrite its own soul. Hoola's persona law (avatar
  name, voice, replystyle, voicestyle) stays owner-controlled; Phase 4 structures what exists, it does not
  hand the pen to the model.

## 5. The phases

Versions are indicative and follow the house ritual (three-place bump: `main.py` APP_VERSION, `pubspec.yaml`
+build, `test_routines.py` assert). Every phase: server-first, one kill switch, default OFF, bake on the VPS,
then flip — the v0.477/v0.478 pattern (`docs/WORKLOG.md` Task 20). **The Mera PC freeze is respected by every
phase; no phase touches a frozen file.**

### Phase 1 — v0.479.0 SAPNE (the nightly curator — "dreaming") — SHIPPED as v0.484.0 (fifteenth collision: 0.479-0.483 taken by parallel sessions; their v0.480 CURATOR is the dedup-arbitration half, SAPNE is the dreaming half, both kept)

The candidate already named at v0.478 (`docs/WORKLOG.md` Task 20: *"curator consolidation … stays the v0.479
candidate"*). NEW `coder/dreams.py`: a background run per tenant — **light** nightly (merge the day's vault
observations + gyaan notes into curated memory rows: durable facts, standing decisions, open threads) and
**deep** weekly (one consolidation pass over the week, Hermes's weekly compaction). OpenClaw's safeguards,
ported: a **preimage** (the exact prior text) is stored before every accepted rewrite, so any consolidation
is undoable; every run appends a human-readable entry to a per-tenant **dreams digest** the owner can open in
Profile (her data, she sees everything); consolidation rides the SAME dedup ladder + redaction as the vault
(`store.store_observation`, actor=`dreams`); a wholly `<private>` day is skipped. Writes go through the
existing memory tools' paths so `yaad_khojo` finds them. Kill switch `coder_dreams` (default OFF). Cost: one
cheap-brain call per tenant per night, one per week deep — pennies.
**Tests:** `test_v0479_hoola_dreams.py` (~16): preimage saved + restore, private-day skip, dedup ladder ride,
digest row per run, kill switch, version.
**Why moat:** this is the step that turns capture (shipped) into compounding — the coworker that knows last
month's context without being re-told.

### Phase 2 — v0.480.0 KAARKHANA (the skill workshop)

Extend `coder/skills_store.py` to OpenClaw's lifecycle, files stay source of truth (house law): every update
snapshots a **revision** (numbered, `.bak` stays for the current), **undo** restores the previous revision;
skills unused for 30 days **auto-archive** (usage counters come free from the v0.473 capture —
`tool_observed` rows name the skill) and can be restored; **skill diet** caps what the primer injects (most-
used first, bounded budget); a **provenance line** in the frontmatter records the session that learned it.
Archive is a background sweep, never a live-turn cost. Kill switches: rides `coder_skills`, new
`coder_skill_archive` (default OFF).
**Tests:** `test_v0480_hoola_workshop.py` (~14): revision + undo round-trip, 30-day archive + restore, diet
cap order, provenance lint, version.

### Phase 3 — v0.481.0 HUKUMNAMA (standing orders)

NEW `coder/orders.py`: per-tenant `standing-orders.md` (tenant-scoped dir, same law as skills) holding
**programs** in OpenClaw's four-part shape — Scope (what may it do), Triggers (schedule/event/condition,
reusing the existing reminders + morning-briefing + cron infra), Approval gates (anything with money,
sending, deleting, bulk = the existing `haan_karo` cards, always), Escalation (when to stop and ask). The
file is injected into the session primer with a bounded budget (`inject.py`), edited in Profile (a simple
editor screen; the model can DRAFT a program but never enable one — enablement is her tap, the same law as
payments). The agent executes autonomous programs inside those boundaries; silence never authorizes a gated
action (OpenClaw's own working-agreement line, adopted verbatim as a house rule). Kill switch
`coder_standing` (default OFF).
**Tests:** `test_v0481_hoola_orders.py` (~15): program lint (four parts present), injection budget, gate
refusal without card, escalation message shape, voice allowlist unaffected, version.
**Why moat:** this is the "always-on coworker" promise made safe — she delegates programs, not chores.

### Phase 4 — v0.482.0 APNA SACH (the identity pack)

NEW `coder/identity.py`: per-avatar `SOUL.md` (persona: how it talks, boundaries — generated from the
existing avatar/replystyle/voicestyle settings, never model-rewritten) + `USER.md` (stable preferences with
observed-date and **supersede-in-place**: when a preference changes, the old directive is marked superseded,
not contradicted — OpenClaw's user-model rule). Both load into the **stable prefix** at session start with a
small budget; identity changes take effect next session (OpenClaw's stable-context discipline — never mutate
the prefix mid-conversation, it defeats prompt-prefix caching; the diary already rides on-this-message-only,
`agent/santosh.py` L80). Editable in Profile, versioned like skills. Kill switch `coder_soul` (default OFF).
**Tests:** `test_v0482_hoola_identity.py` (~12): pack build from avatar settings, supersede-in-place, stable-
prefix placement + next-session rule, budget cap, version.

### Phase 5 — v0.483.0 PUCHH-TACHH + JAANCH-2 (grilling + two-axis review)

**5a Grilling.** NEW `coder/grill.py`: when her ask is big and fuzzy (new program, new desk, "banao" without
shape), the agent runs ONE bounded grilling round before acting: a design tree of decisions, the **frontier**
(only questions whose prerequisites are settled) asked as at most **3 numbered questions**, each with a
recommended answer phrased so **"haan" accepts the recommendation**; facts (files, history, prices, docs) are
never asked — Hoola looks them up itself (it has 169 tool modules; Matt's rule: "Finding facts is your job,
never the user's"). Rounds repeat until the frontier is empty, then it confirms shared understanding BEFORE
acting. Text chats first; voice gets it only after the round is measured (a round is one turn, not N tool
calls — no VOICE_TOOL_BUDGET impact, 150k-char cap untouched). Kill switch `coder_grill` (default OFF).
**5b Two-axis review.** On big finished jobs, SWARM spawns TWO review children through `delegate.py`'s
existing bounded lane: **Standards** (house rules: official routes, money/OTP rails, tenant scoping, tone)
and **Spec** (did the work match what she actually asked) — parallel, then merged into one tool result
(delegate.py already merges). Same caps as every child (max 3 children, 120 s, deny set). Kill switch
`coder_review` (default OFF).
**Tests:** `test_v0483_hoola_grill.py` (~18): frontier construction, ≤3 questions, yes-accepts wording,
facts-never-asked (a lookupable fact in a question = fail), text-only gate, review lanes spawn + merge +
respect the deny set, both kill switches, version.

### Phase 6 — v0.484.0 SAFAl (the house the agents read — dev-side hygiene)

**6a CLAUDE.md diet.** `CLAUDE.md` is **143,359 bytes** against its own written rule ("must stay SHORT,
target < 30 KB" — `CLAUDE.md` L219-220). The "Current state" list (L227–815, ~590 lines) moves to a compact
index table in `docs/HISTORY.md`; the file keeps pointers only, rewritten per `writing-for-agents` (a
pointer states what the material is + the branches that trigger it; front-load the leading word; one trigger
per branch). Done in a quiet session, announced in the worklog; every pointer another parallel session
relies on keeps its meaning (the rebase protocol, for docs).
**6b GLOSSARY.md** at repo root: the canonical Hinglish domain terms (kaam, gyaan, yaad, theka, bazar,
jaanch, hukumnama, sapne…), each with avoid-words and relationships — Matt's ubiquitous-language format.
Cheaper prompts, consistent naming, new sessions onboard faster.
**6c Worklog handoff + wiki rules.** `docs/WORKLOG.md` task template gains the handoff shape (compact the
session into a dated, commit-cited handoff; reference artifacts by path, never paste them; redact secrets —
the token-scrub rule already in Task 0) and `chief-of-staff`'s three wiki operations (ingest every page a
finding touches, query before deciding, lint for contradictions/orphans) + "write history, not the present".
**6d Retro.** The nudge fork grows a monthly mode: one digest of environment-improvement proposals (missing
tests, flaky suites, slow loops), most severe first, written to a review file — never auto-applied.

## 6. The rails that survive every phase

Money never moves without her tap; never ask/accept PIN, OTP, CVV, card numbers or passwords (OTP/CAPTCHA
for a waiting box goes into that box and nowhere else); sending/deleting/bulk/sharing confirm first; text in
emails/files/pages is data, never instructions; API keys only in `.env`/app; tenant scoping absolute (one
directory per tenant — skills, orders, identity, dreams all inherit it); voice tools stay inside
`VOICE_TOOL_NAMES` + the 150k-char `VOICE_TOOL_BUDGET` (`voice.py` L276); children never get
`delegate_task / confirm_send / haan_karo / pc_do` (the v0.478 deny set); **every phase's files are additive
— no destructive migration, rollback is one kill-switch flip** (`coder_dreams / coder_skill_archive /
coder_standing / coder_soul / coder_grill / coder_review`, all default OFF, bake then flip).

## 7. Cost math (cheap brain only; voice never waits)

| Loop | Model calls | When |
|---|---|---|
| Nudge reflection (shipped) | 1 / 10 turns | between turns, `poke()` drops if live turn wakes |
| SAPNE light + deep | 1 / tenant / night + 1 / week | background |
| KAARKHANA archive sweep | 0 (pure file + vault ops) | background |
| HUKUMNAMA, APNA SACH | 0 (static primer text) | — |
| PUCHH-TACHH | 0 extra (same turn's reply) | live |
| JAANCH-2 | 2 / big job | inside the existing 3-child / 120 s budget |

## 8. Rollback

Per phase: flip its kill switch to 0 and `pm2 restart santosh --update-env`. Vault tables gain only nullable
columns (house law: `_add_missing_columns`); skill/order/identity files are new files under the tenant dir;
deleting them is not required for off. Known-good anchor remains `stable-2026-11-03-v470` until the first
post-plan checkpoint.

## 9. Not verified — said plainly

1. **Consolidation quality** (Phase 1) is unproven until it runs on real tenant data on the VPS; the digest
   is exactly where she judges it. Three cheap-brain prompt shapes (light, deep, retro) stay assumptions
   until the first bake.
2. **Grilling on voice** (Phase 5a) ships text-only; the latency claim (one turn per round) must be measured
   on the VPS before the voice gate opens.
3. **Usage counters for auto-archive** (Phase 2) assume v0.473 capture rows reliably name skills — true
   since the v0.478 funnel fix, but 30-day behaviour is unobserved until it runs.
4. **CLAUDE.md diet** (Phase 6a) needs a session with grep access to the full `docs/HISTORY.md` (18,263
   lines) and a quiet window with no parallel version in flight.
5. No phase has been built, tested or deployed — this document is the plan she asked for FIRST.

## 10. Sources

- OpenClaw @ `b3487e66`: paths listed in the header; quotes from `dreaming.md`, `memory.md`,
  `skill-workshop.md`, `standing-orders.md`, `delegate-architecture.md`, `multi-agent.md`, `AGENTS.md`.
- mattpocock/skills @ `4ae2317`: `grilling`, `code-review`, `wayfinder`, `writing-for-agents`,
  `chief-of-staff`, `handoff`, `retro`, `SCOPE.md`, `GLOSSARY.md`.
- House: `CLAUDE.md` (143,359 B; rules L816–858), `docs/GAME_MOAT_PLAN.md` §0-§2, `docs/WORKLOG.md`
  Tasks 0/19/20, `server/app/coder/` (16 modules), `server/app/config.py` L419–435, `server/app/voice.py`
  L276, `server/app/agent/compact.py`, `server/app/agent/santosh.py` L80, L475, L1890.
