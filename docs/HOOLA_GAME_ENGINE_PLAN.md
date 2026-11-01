# Hoola Game Engine — plan for "Hoola does ALL gaming-industry work, low to very complex"

Owner (1 Nov 2026): *"WE WANT SAME HOOLA AI TO PERFORM ALL GAMING INDUSTRY WORK — 100 % FROM LOW TO VERY COMPLEX. WE
DON'T WANT HOOLA AI TO DESIGN ENTIRE WORK IN 1 DAY. IT MAY BE 1000 DAYS BUT USER WILL USE HOOLA FOR EVERY TASK AND CAN
COMPLETE THAT TASK IN LESS TIME AND WITH REPETITIVE PRECISION. MAKE A HOOLA GAME ENGINE. — FIRST PLAN"*

Builds on `docs/GAME_DESK_PLAN.md` (v0.370 Game Desk Phase 1: design doc → Godot 4 → headless play → Web export →
Hoola playtest → play link).

---

## 0. The idea in one paragraph

A real game is not made in one prompt. It is made in **thousands of small tasks over months or years**: a design
section, a character sheet, a walk cycle, a level blockout, a bug fix, a balance pass, a store page, a patch. The
**Hoola Game Engine** is the system that lets one user (or a whole studio) do **every one of those tasks with Hoola**,
each faster and the same way every time, while the project **remembers everything** across 1,000 days: what was
decided, which asset is final, what the numbers are, what broke last week. Hoola never "invents the whole game"; it
does the next task well, checks it, and keeps the project consistent.

---

## 1. What "Hoola Game Engine" is (and what it is not)

**It is four layers:**

| Layer | What it is | Built on |
|---|---|---|
| **1. Hoola Runtime** | The engine the game runs on: rendering, physics, input, audio, UI, scripting, export to Web / Android / iOS / PC | **Godot 4** (MIT licence), branded and extended as "Hoola Runtime"; kept close to upstream so every Godot improvement flows in |
| **2. Hoola Studio** | The production system around it: project repo, task board, asset registry, build farm, test farm, playtest bots, telemetry, releases | Hoola's server (`app/gamedesk/` grows into it), her GitHub, Hoola's existing App Builder / Hosting / Create Studio / Blender 3D |
| **3. Hoola Crew** | One AI per discipline (designer, writer, artist, animator, level designer, gameplay / engine / network programmer, audio, VFX, QA, producer, marketer, live-ops) working on the same project memory | The Employee frame (`employee/hire.py`) + the Game Desk roles |
| **4. Precision layer** | What makes the 500th task as exact as the 1st: the Game Bible, specs as data, generators, validators, regression tests, golden screenshots, deterministic builds | New `gamestudio/` modules |

**It is not** a brand-new engine written from zero. Writing a new 3D engine to Godot / Unity / Unreal quality takes
hundreds of engineer-years; Godot already gives a mature, free, open engine we may fork, rename and ship (MIT keeps
the copyright notice, nothing else). Our value is layers 2-4: **the production brain**. Where Godot is not enough, we
add modules to the runtime (Section 7).

**For big studios on Unreal / Unity:** Hoola Crew also works **inside their engine** through its official editor
scripting (Unreal Python + Editor Utility, Unity Editor scripting) and MCP plugins, on the studio's own machines and
licences. Hoola never ships Unreal / Unity on Newtika's server.

---

## 2. Scale ladder — honest ceilings

| Tier | Example | Calendar time with Hoola | Team | Hoola's share of the work |
|---|---|---|---|---|
| **T1 Hyper-casual / promo** | Tap game for a shop, quiz, runner | Hours to 3 days | 1 user | ~95 % (user decides, approves) |
| **T2 Casual mobile** | Match-3, idle, puzzle with 100 levels, ads / IAP | 2-8 weeks | 1-2 | ~80 % |
| **T3 Indie 2D / small 3D** | Platformer, roguelite, story game, small multiplayer | 3-12 months | 1-5 | ~60-70 % of hours |
| **T4 AA indie 3D** | Third-person action-adventure, 5-10 hour story, open zones | 1-3 years | 5-30 people + Hoola | ~40-50 % of hours |
| **T5 AAA** | Valhalla-scale open world | 3-5 years | hundreds of people | Hoola as studio-wide assistant: 20-40 % of hours (docs, scripting, tools, QA, localisation, builds, data), people own art direction, performance capture, final quality |

The ceiling is not code; it is **taste, art direction, acting and polish**, which stay human-led. Hoola makes every
person on the project 2-5x faster and keeps the whole thing consistent.

---

## 3. The whole industry, task by task — what Hoola does

The full pipeline every studio follows: **Concept → Pre-production → Production → Alpha → Beta → Launch → Live ops**.
Every row is a set of repeatable tasks with a template, a generator, a checker and a human tap where it matters.

### 3.1 Game design
- Game Design Document as **structured data** (pillars, core loop, systems, progression, economy, controls, UX flows)
  — every other task reads from it.
- Systems design: combat, crafting, skill trees, quests, AI behaviour specs; **balance tables in sheets** with
  formulas, simulations (thousands of simulated runs) and charts.
- Economy design (soft / hard currency, sinks / sources) with Monte-Carlo simulation; ethics checks (no pay-to-win
  traps for children, no loot boxes for minors, no real-money gambling).
- Level design docs, beat charts, difficulty curves; paper prototypes → playable greyboxes.

### 3.2 Narrative and writing
- Story bible, world lore, factions, timeline, character bios — kept consistent by the Game Bible (Section 5).
- Quest scripts, branching dialogue (Yarn / Ink-style graphs exported to Godot), barks, item text, tutorials.
- Continuity checker: every new line is checked against the bible (names, ages, places, events).

### 3.3 Art — 2D
- Concept art, mood boards, style guide (palette, shapes, line weight) via photogen / image models in her style.
- Sprites, tilesets, UI kits, icons, splash screens; sprite-sheet packing; consistent style through a locked style
  reference + automatic similarity check.

### 3.4 Art — 3D
- Props, environments, characters via Blender (already in Hoola) + AI 3D generators where licences allow; retopology,
  UVs, LODs, texture baking, PBR materials; polycount / texture budgets checked per platform.
- Modular kits (walls, floors, trims) with snapping rules for level designers.

### 3.5 Animation
- Rigging (auto-rig humanoids), animation retargeting, procedural animation (IK, look-at), state machines / blend
  trees in Godot; motion-capture clean-up from her own mocap or licensed libraries (Mixamo-style terms checked).

### 3.6 Level design and world building
- Blockouts from the level doc, playable greybox, then art pass; procedural terrain / cities / dungeons with seeds
  (Game Desk role 6); navigation meshes; encounter placement; "can every area be reached" bot checks.

### 3.7 Programming
- **Gameplay**: player controller, combat, inventory, quests, save / load, UI logic — from the spec, with unit tests.
- **Engine / performance** (Game Desk role 1): profiling, frame budget, memory budget, shaders, C++ modules.
- **Physics** (role 4), **network / multiplayer** (role 3: authoritative server, prediction, rollback, bots),
  **tools** (editor plugins, importers, data pipelines), **platform** (Android / iOS / PC / Web builds).
- Every change through Developer Sahayak's loop: rules first, branch, tests, CI green, PR, her merge.

### 3.8 Audio
- Music (Create Studio Lyria), SFX (generated / CC0 libraries with licence list), voice-over (Hoola voices or real
  actors with written consent), spatial audio (role 8), mixing and loudness rules per platform.

### 3.9 VFX and technical art
- Particle effects, shaders (water, fire, dissolve, toon), post-processing; VFX pipeline for cinematics (role 7).

### 3.10 UX / UI
- Wireframes → mock-ups → Godot UI scenes; accessibility (subtitles, colour-blind modes, remapping, text size);
  first-time-user funnel checked with bots and her playtesters.

### 3.11 QA
- Automated playtests every build (already started in v0.370): bots that walk levels, press every button, try to
  break the game; **replay tests** (recorded inputs must give the same result); **golden screenshots** (any visual
  change is flagged); crash and error collection; performance per device class; bug tracker with repro steps.

### 3.12 Localisation
- String tables, Indian languages first (Hindi, Marathi, Tamil, Telugu, Bengali...) + world languages; text-fit
  checks in every UI screen; culture review list.

### 3.13 Production management
- Producer agent: milestones, task board, estimates vs actual, risk list, weekly report, scope cuts proposed (never
  made) — the backbone of the 1,000-day project.

### 3.14 Release, platforms and compliance
- Web (Hoola hosting), Android (Play Store via App Builder), iOS (App Store via App Builder), PC (Steam / itch.io
  store pages and builds), consoles only through the studio's own licensed dev kits.
- Age rating (IARC questionnaire drafts), privacy (DPDP; children's data with parent consent), store listing,
  screenshots, trailers; submission always **her tap**.

### 3.15 Marketing and community
- Trailers (Video Studio), store art, press kit, social posts (Social Media Manager), Discord / community FAQ drafts,
  influencer outreach drafts (her send).

### 3.16 Live ops and analytics
- Telemetry events (opt-in), dashboards (retention D1/D7/D30, funnels, balance outliers), A/B tests, events
  calendar, patches and hotfix pipeline, crash monitoring; monetisation reports.

---

## 4. Long projects — how 1,000 days work

**4.1 The Studio Project.** A project is not a chat; it is a **long-lived workspace**: her GitHub repo (code,
scenes, data), an asset store (big files, versioned), the Game Bible, the task board, builds, test results and
releases. Every Hoola task belongs to a project and a milestone.

**4.2 One task at a time, small and checkable.** Every task has: inputs (from the Bible / specs), a template, the
work, automatic checks, a preview, and her approval where it matters. Typical task size: 5 minutes to 2 hours of
Hoola work. A 1,000-day game ≈ 20,000-60,000 such tasks.

**4.3 Daily rhythm.** Morning: producer summary (yesterday, today, blockers). During the day: she asks or approves;
the crew works in parallel in the background. Night: full build + test farm + report.

**4.4 Memory that never forgets.** Decisions log ("we chose 30 fps lock on low phones because…"), changelog per
asset, who approved what and when — searchable in chat ("why is the jump height 3.2?").

**4.5 Humans in the loop.** Creative direction, final art approval, acting, legal, money and publishing stay with
her (or her team). Roles and permissions per team member (the existing Employee trust levels: seekh / saathi / bharosa).

---

## 5. Repetitive precision — the mechanisms

1. **Game Bible** = single source of truth as data: characters, places, items, stats, style guide, terminology. Every
   generator reads it; every checker validates against it.
2. **Specs as data, not prose**: balance tables, level specs, dialogue graphs, asset specs (polycount, texture size,
   naming) in structured files under version control.
3. **Templates + generators** for each task type (a new enemy, a new level, a new UI screen, a new quest) so the 50th
   enemy is built exactly like the 1st.
4. **Validators** per asset type: naming, budgets, style similarity, missing references, broken links, text fit,
   continuity.
5. **Tests that never sleep**: unit tests, replay tests, golden screenshots, bot playthroughs, performance budgets —
   every build, every night.
6. **Deterministic builds**: pinned engine version, pinned tools, same inputs → same build (hash-checked).
7. **Review gates**: nothing reaches "final" without passing checks + her approval; a failed change never breaks the
   last good build (already true in v0.370).
8. **Measured quality**: per discipline score cards (like Hoola's Design Arena / Code Card) so we know each version
   of the crew got better, not worse.

---

## 6. Hoola Crew — the employees

Phase-wise, inside Employees under "Game Development, Simulation & VR" (10 already listed) plus the studio roles:

| Discipline | Employee |
|---|---|
| Design | Game Designer, Systems & Economy Designer, Level Designer |
| Writing | Narrative Designer / Writer |
| Art | Concept Artist, 2D Artist, 3D Artist, Technical Artist, Animator |
| Engineering | Game Developer (live), Engine Programmer, Gameplay Programmer, Network Programmer, Physics Developer, Tools Programmer |
| Audio | Sound Designer, Spatial Audio Programmer |
| VFX / XR / Sim | VFX TD, AR / VR Engineer, Simulation Engineer, Digital Twin Architect, Haptics Engineer, Procedural World Engineer |
| Quality | QA Tester, Performance Analyst, Localisation Specialist |
| Business | Producer, Release Manager, Marketing (Social Media Manager), Live-Ops & Analytics, Community Manager |

All share one project memory; each can be hired alone (a solo developer hires two) or together (a studio hires all).

---

## 7. Hoola Runtime — what we add to Godot over time

- **Hoola modules** (C++ / GDExtension): telemetry (opt-in), replay recorder, bot-input driver, golden-screenshot
  hooks, save-game cloud sync, in-game feedback, Indian-language text shaping checks, UPI-friendly IAP hooks via the
  stores' official billing only.
- **Hoola editor plugins**: Bible browser, spec-to-scene generators, asset validators, "ask Hoola" panel inside the
  Godot editor (Godot editor plugin + MCP), task board panel.
- **Builds**: Web, Android, iOS, Windows, Linux, macOS from the build farm; console ports only via the studio's own
  licensed SDKs.
- Branding: "Hoola Runtime, based on Godot Engine" with the MIT notice; upstream contributions where fair.

---

## 8. Phases (each ships as a Hoola version: server + tests + console + phone + CI green)

| Phase | What | Rough time | Unlocks |
|---|---|---|---|
| **1 (done, v0.370)** | Game Desk: design doc → Godot → test-play → play link | done | T1 |
| **2 Studio Project (BUILT, v0.386.0)** | Long-lived projects: task board, milestones, decisions log, nightly build + test, morning summary, versions + restore, her GitHub (card) | built | T1-T2 over weeks |
| **3 Game Bible + specs as data (BUILT, v0.395.0)** | Bible as data, templates per kind, validators, seeded balance + economy simulation, curve-made numbers, drafts for her OK, data-only rebuilds | built | repeatable content at T2 |
| **3.5 Game Crew + fixes (BUILT, v0.406.0)** | 49 studio roles as data, role + acceptance criteria per task, lead review, team plans, milestone gates, NOT ASSESSED honesty, Godot 4.7 notes, import step | built | precision per discipline |
| **4 Asset pipeline (BUILT, v0.416.0)** | style-locked 2D art, code-made sound effects, music, voice, 3D models via the 3D Studio, checks in code, price card + her tap, her OK, HoolaAssets in every build | built | real-looking T2 / T3 |
| **5 QA farm (BUILT, v0.416.0)** | seeded bot playthroughs on phone speeds, replays, golden screenshots, speed vs last run, numbered bug tracker, fixes verified by the bot, debug-build playtests | built | precision at scale |
| **6 Platforms (BUILT, v0.416.0)** | Linux / Windows / macOS downloads made on the server, Android APK / AAB in her builds repo with the game's own upload key, store kit (itch / Steam / Play texts in limits, images in exact sizes, AI disclosure, Steam scripts), age-rating draft, itch.io upload by her tap; iOS not built (needs her Apple account + a Mac runner) | 6-8 weeks | shipping T2 / T3 |
| **7 Crew roles (batch 1 BUILT, v0.419.0)** | The Game Desk roles 2-10 in batches (Game Desk plan phases 2-5). Batch 1: Procedural World Engineer + Physics Engine Developer live (role packs = Hoola-owned autoloads HoolaWorld / HoolaPhysics, checks in code, real-engine physics lab). Batches 2-4 (audio + haptics, multiplayer + AR/VR, VFX + simulation + twin) not built | 6-9 months | T3 |
| **8 Hoola Runtime modules + editor plugin** | Replay / bot / telemetry modules, Godot editor "ask Hoola" panel via MCP | 3-4 months | T3-T4 teams in the editor |
| **9 Live ops** | Telemetry dashboards, A/B, events, patches | 2-3 months | games that run for years |
| **10 Big-studio mode** | Hoola Crew inside Unreal / Unity via official editor scripting + MCP on their machines | 3-6 months | T4-T5 assistance |

Total to "every discipline covered": roughly **18-24 months** of Hoola development, delivered in usable slices; a
user can start a long project from Phase 2.

---

## 9. Costs and limits (to confirm)

- Model calls per task (most tasks small); heavy work (3D generation, video, voice, builds, bot farms) priced on a card
  before it runs — same rule as Create Studio.
- Compute: builds and bot farms need a separate build / test machine as usage grows (never on the chat server).
- Storage: art and audio grow large; per-project storage quota with off-server backup.

## 10. Never

Copy an existing game's world, characters, levels, story or art; use cracked engines, tools or assets; train on or
reuse assets without a licence; real-money gambling or loot boxes for children; dark patterns; cheats / bots for other
people's games; weapon targeting sims; publish anything or spend money without her tap; claim a game is
"AI-free" when it is not.

## 11. Decisions for the owner

1. Name: **"Hoola Engine"** for the whole system, runtime = "Hoola Runtime (based on Godot)" — OK?
2. Phase 2 next (Studio Project, long-lived game projects with task board + nightly build) — OK?
3. Target first: solo creators and small Indian studios (T1-T3), big studios later (Phase 10) — OK?
4. Pricing model for heavy work (per-task cards vs a monthly studio plan).
5. A separate build / test machine when Phase 5 starts.

## 12. Not verified yet

Godot fork maintenance cost; AI 3D-model generator licences for commercial use; store policies on AI-made content
(Steam disclosure, Play / App Store); IARC flow for small developers in India; real task counts and hours per tier
(measured as projects run).
