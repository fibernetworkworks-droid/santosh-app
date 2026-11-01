# Hoola Game Desk — plan for "Game Development, Simulation & Virtual Reality" employees

Owner asks (1 Nov 2026): *"NOW LETS WORK ON EMPLOYEE SECTION. Game Development, Simulation & Virtual Reality. FIRST
READ EXISTING EMPLOYEE SECTION AND PLAN FOR THE ATTACHED ONE"* (her list VII, 10 roles).

Ten hireable AI employees on the frame SEO and Social built (`employee/hire.py`: hire → onboard → desk → jobs → trust →
report), the same way the Engineering Desk plan (`docs/ENGINEERING_DESK_PLAN.md`, list IX) does it. They share one new
base, the **Game Desk**: Hoola writes the game / simulation code, builds and test-plays it in a locked box on the
server, and puts a **playable link**, screenshots, a short gameplay clip, numbers and the source on her desk. Each role
then adds its own **pack** (engine + checks + report template).

---

## 1. What a good engineer in each role actually delivers

| # | Role | A real deliverable | What "good" means |
|---|------|--------------------|-------------------|
| 1 | Lead Game Engine Programmer | A playable game / prototype from her brief (Godot 4 or web), custom shaders / render passes, frame-time and memory budget, profiling report, engine modules (GDExtension C++) where speed matters | Holds 60 fps on a mid phone (frame time ≤ 16.6 ms), memory under her budget, no allocation in the hot loop, profiler numbers before / after every optimisation |
| 2 | AR / VR Interaction Engineer | A WebXR scene (opens in the phone / headset browser, no install) or a Godot OpenXR project: hand tracking + gestures (pinch, grab, point), UI in space, comfort settings | Gestures recognised in a test set (accuracy %), 72-90 fps target on the device class, comfort rules (no forced camera motion, snap turn, seated mode) |
| 3 | Multiplayer Network Programmer | Netcode for her game: authoritative server, client prediction + reconciliation, lag compensation, interest management; a test harness that plays N bots over bad networks | Measured under 150 ms / 2 % loss / jitter: no rubber-banding beyond a stated limit, bandwidth per player stated, desync = 0 in the bot run |
| 4 | Physics Engine Developer | Rigid-body / collision setup or a custom physics module (broad phase + narrow phase), fluid / particle simulation, deterministic stepping | Energy / momentum checks pass, no tunnelling at the stated speeds, fixed-step deterministic replay, compared with an analytic case (falling body, projectile, dam break) |
| 5 | Simulation Software Engineer | Flight / space / driving / equipment **training** simulator: flight dynamics model, orbit propagation, scenario scripts, instructor station, logs | Model cites its data source (aircraft data, TLE / ephemeris), validated against a reference case, time step and integrator stated, every scenario reproducible |
| 6 | Procedural World Generation Engineer | Terrain (heightmaps, biomes, rivers), cities (road graph, plots, buildings), dungeons / levels from rules; seeds; export to Godot / Blender / glTF | Same seed = same world, generation time and size stated, playable (reachable areas, no stuck spawns), a preview render + walkable link |
| 7 | VFX Pipeline Technical Director | A CG pipeline: shot / asset tracking, naming + versioning, colour management (ACES via OpenColorIO), EXR outputs, render queue, publish scripts (Blender / OpenUSD) | Every frame traceable to its scene version, colour space stated end to end, failed frames re-queued, render cost per shot reported |
| 8 | Spatial Audio Systems Programmer | 3D sound for game / VR / room: HRTF binaural rendering, distance + occlusion, reverb zones, audio middleware hooks; a listening demo | Positions audible correctly in a blind test set, latency stated, CPU per voice stated, loudness normalised |
| 9 | Digital Twin Architect | A live 3D twin of her factory / shop floor / building: layout model, data map (sensor → tag → asset), discrete-event simulation (what-if: shifts, machines, queues), dashboard | Every number on the twin traceable to a tag or a stated assumption, simulation validated against one real week, **read-only** to her plant |
| 10 | Haptic Feedback Systems Engineer | Haptic patterns + driver code: Android VibrationEffect / iOS Core Haptics (AHAP) libraries, game-controller rumble, LRA / ERM driver code (e.g. a DRV2605-class chip) for her device, a test app | Pattern timing measured, one pattern per meaning (no "buzz for everything"), battery cost stated, accessibility (can be turned off) |

Never, for every role: copy a specific existing game, its levels, characters, names or assets (Hoola builds original
games and games from her own designs only); use cracked engines, plugins or asset packs; build cheats, aimbots, wall
hacks or anti-cheat bypasses; build real-money / betting games (online money games are banned in India — Promotion and
Regulation of Online Gaming Act 2025, to re-check); build weapon targeting or combat / military targeting simulators
(training sims for flying, driving, space, machines, safety are fine); connect a twin or simulator to a live plant in
write mode; hide that the work is AI-made.

---

## 2. What Hoola already has

- **Hire frame:** `employee/hire.py` (hire / pause / let go, trust seekh / saathi / bharosa, catalogue with "coming"
  cards), Employee Hub (console `employees.js`, phone `employees_screen.dart`), desk pattern from SEO (`seo/desk.py`)
  and Social. The older staff roles (`employee/roles.py`, 85 roles from duties) stay as they are.
- **Locked code runner:** `blender3d/` = `guard.py` (AST check: allowed imports only), `runner.py`, `sandbox.py`
  (`unshare -rn` no network, no secrets, own folder, RLIMIT memory / file size, nice, wall-clock kill), price + limits
  per tenant, signed file URLs, progress events. The Engineering Desk plans the same sandbox with engineering libraries;
  the Game Desk shares it (one sandbox, a game pack of allowed tools).
- **3D and art:** Blender 3D (`blender3d/`: models, renders), photogen (sprites, textures, concept art), Create Studio
  (`create/`: Lyria music, voice-over, dubbing), Hoola Motion + Video Studio (trailers, gameplay clips).
- **Hosting:** websites are hosted and served by nginx with signed previews (`site/hosting.py`, `site/edge.py`): a web
  game build is just static files, so a playable link can ride the same hosting.
- **Apps:** App builder (`appmaker/` Android + iPhone, Play Store / App Store launch, device check on an emulator): a
  finished game can ship as her own app.
- **Code work:** Developer Sahayak (GitHub PRs), QA (`qa/`), Docs writer, App Jaanch / REA static analysis.
- **Reports:** Hoola Print (`docstudio/htmlpdf.py`): designed PDFs with charts.
- **Missing:** no game engine on the server, no headless build / export, no automatic playtest, no netcode harness, no
  physics / flight / orbit / audio / haptics libraries, no game desk.

---

## 3. The engines (free, open-source, run as separate programs on the server)

| Use | Engine | Licence | Install |
|-----|--------|---------|---------|
| Game engine (2D / 3D, headless build + Web / Android export, GDScript, C++ GDExtension) | Godot 4 | MIT | official binary + export templates |
| Web 2D games | Phaser | MIT | npm (bundled into the build) |
| Web 3D / XR | three.js, Babylon.js, A-Frame (WebXR) | MIT / Apache-2.0 / MIT | npm |
| Hand tracking in the browser | MediaPipe Hands / Gesture Recognizer | Apache-2.0 | npm (runs on her device) |
| Rigid-body physics | Jolt (Godot 4.4+ built in), Rapier, Box2D | MIT / Apache-2.0 / MIT | engine / npm / pip |
| Physics research / robotics | MuJoCo, PyBullet | Apache-2.0 / zlib | pip |
| Fluids / particles | Taichi, PySPH | Apache-2.0 / BSD-3 | pip |
| Multiplayer servers | Colyseus, Nakama | MIT / Apache-2.0 | npm / docker |
| Rollback netcode | GGPO | MIT | build |
| Flight dynamics | JSBSim | LGPL-2.1 | pip `jsbsim` |
| Orbits / space | Skyfield, Orekit | MIT / Apache-2.0 | pip / Java |
| Robots / vehicles sim | Gazebo | Apache-2.0 | apt (Phase 5, heavy) |
| Procedural noise / WFC | FastNoiseLite, OpenSimplex, Wave Function Collapse | MIT | pip / npm |
| Real-world city base | OpenStreetMap data | ODbL (attribution) | download per area |
| VFX colour / images / scenes | OpenColorIO (ACES), OpenEXR, OpenImageIO, OpenUSD | BSD-3 / BSD-3 / Apache-2.0 / modified Apache-2.0 | pip / apt |
| Render queue | Flamenco (Blender) | GPL-3.0 | separate program |
| Spatial audio | Steam Audio, Resonance Audio, Web Audio HRTF, pyroomacoustics | Apache-2.0 / Apache-2.0 / browser / MIT | pip / npm |
| Digital twin data / sim | SimPy (discrete events), asyncua / open62541 (OPC-UA), Mosquitto (MQTT) | MIT / LGPL-3.0 / MPL-2.0 / EPL-2.0 | pip / apt |
| Haptics | Android VibrationEffect, iOS Core Haptics (AHAP), Web Vibration API, CHAI3D (force-feedback devices) | platform / platform / browser / BSD-3 | in the app builder kits |
| Headless playtest | Playwright + Chromium (already on the server for websites) | Apache-2.0 | present |

Unity and Unreal are commercial: Hoola can write C# / C++ for her own licensed Unity / Unreal project (as code in her
repo, through Developer Sahayak), but never runs them on Newtika's server. GPL / LGPL engines run as separate programs;
nothing GPL is linked into Hoola or shipped in the APK. Every licence is re-checked before its phase ships
(`THIRD_PARTY_NOTICES.md`).

---

## 4. The Game Desk (shared base, Phase 1)

**4.1 Hire and onboarding (same frame as SEO / Social).** One catalogue entry per role in `hire.CATALOG`, grouped
under "Game Development, Simulation & VR". Onboarding asks: what she is making (game / sim / twin / XR), platform
(web, Android, iPhone, PC, headset), target device class, art style, audience (children → stricter rules), her own
engine if any (Godot / Unity / Unreal), and who signs off.

**4.2 Projects.** `gamedesk/` module: a Project = brief + design doc + assets + builds + playtests + report. Tables
`game_projects` / `game_builds` (self-healing, registered in `db.init_db`). A design doc (game design / sim spec) is
written first and approved by her before code.

**4.3 Build and run in the locked box.** Godot headless (`--headless --export-release`) and web bundling run in the
shared sandbox (no network, no secrets, own folder, memory / CPU / wall-clock caps, one job per user, global queue).
Hoola's helpers do the file I/O; scripts never open files, sockets or processes themselves.

**4.4 Playable link.** Every web build gets a private signed link (`/play/<token>`) served as static files with a strict
Content-Security-Policy (no outside calls unless the game needs its own server); she taps it on her phone. Android
builds go through the app builder; headset builds through WebXR in the headset browser.

**4.5 Automatic playtest before she sees it.** Playwright opens the web build: it loads, the frame time is measured,
inputs are sent (a scripted path or a bot), screenshots and a 10-second clip are taken, console errors are collected.
Godot builds run their own test scenes headless. A failed check = Hoola fixes and rebuilds (max 2) or tells her plainly.

**4.6 Assets.** Concept art / sprites / textures via photogen (her style), 3D models via Blender 3D, music and voice via
Create Studio, sound effects from licence-clean libraries (CC0) with a licence list in every project. Each paid asset
step shows its price card first, exactly like Create Studio.

**4.7 Price before every heavy run.** Builds, long simulations, fluid runs, render-queue jobs and bot tests are priced
(CPU minutes + model calls + any paid assets) and shown as a card; she taps Approve. Small builds and quick playtests
stay inside a free daily allowance. Monthly cap per user.

**4.8 The desk (console + phone).** Projects list; per project: design doc, playable link + QR, screenshots and clip,
frame-time / memory / bandwidth numbers, builds with prices, playtest results (pass / fail), asset list with licences,
source download (zip / her GitHub through Developer Sahayak), and the report. Chat: "ek endless runner game banao jismein
chai wala bhaagta hai" starts the same flow.

**4.9 Agent tool.** `game_desk` (family `gamedesk`, admitted on game / simulation / VR / twin words): `new_project`,
`design`, `build` (price card if heavy), `playtest`, `result`, `report`, `export` (zip / GitHub / app builder).

---

## 5. Role packs and phases

| Phase | Roles | Why this order |
|-------|-------|----------------|
| **1** | Game Desk base + **Lead Game Engine Programmer** | Most demand (shops, schools, creators want a small branded game; studios want prototypes), result is instantly visible (a link she plays) |
| **2 (BUILT v0.420.0)** | **Procedural World Generation** + **Physics Engine Developer** | Reuse the base and Blender; give every game bigger worlds and believable motion; fluid runs share the Engineering sandbox |
| **3 (BUILT v0.421.0)** | **Spatial Audio** + **Haptic Feedback** | Light libraries, quick wins that make games and apps feel premium; haptics ride the app builder kits |
| **4** | **Multiplayer Network Programmer** + **AR / VR Interaction** | Need a running game server (Colyseus / Nakama on her cloud or Hoola hosting, priced) and device testing on her phone / headset |
| **5** | **VFX Pipeline TD**, **Simulation Software Engineer**, **Digital Twin Architect** | Niche, heavier (render queue, flight / orbit models, plant data); twin data is read-only and needs her gateway |

Each phase ships like every Hoola version: server + tests + console + phone + CI green + HISTORY section.

**Phase 1 detail — BUILT in v0.370.0 (1 Nov 2026), Godot 4.7.2:**
1. `gamedesk/` base: projects, builds, sandbox game pack, price card, caps, desk API (`/api/game/*`), self-check
   `python -m app.gamedesk check` (Godot + templates installed, sandbox has no network, a sample game builds and loads).
2. Engine Programmer pack: brief → design doc (her OK) → Godot 4 project (GDScript; shaders where asked) → headless
   web export → playtest (load, frame time, inputs, screenshots, clip) → playable link + source zip + short report with
   the frame-time / memory budget.
3. Hire card "Game Developer" live; the other 9 shown under the new group as "Coming soon".
4. Console desk with an embedded player (iframe with CSP), phone desk with the link, QR and screenshots.
5. VPS: Godot 4 headless binary + Web export templates (sizes to measure; tested in the sandbox first).

---

## 6. Costs and limits (to confirm with real runs)

- Small 2D web game build: under a minute of CPU + a few model calls; inside the free daily allowance.
- 3D web build with assets: a few minutes of CPU; asset generation (pictures / music) priced by Create Studio's cards.
- Playtest: ~30 s of headless Chromium per run.
- Fluid / physics research runs, multiplayer bot tests (N bots × minutes), flight / orbit runs: price card each time.
- Hosting: web builds are static files (a few MB to ~50 MB); a game server for multiplayer is a separate, priced
  service (her cloud or a Hoola box), never on the chat server.

---

## 7. Never

Recreate a specific existing game or use its characters, levels, names or art; use cracked engines, plugins or asset
packs; build cheats, bots that play other people's online games, or anti-cheat bypasses; build real-money / betting
games; build weapon targeting or combat simulators; write commands to a live plant from a digital twin (read-only data
only); collect children's data in a game without the parent's consent (DPDP); ship a VR scene without comfort settings;
hide AI involvement; export controlled technology on request (SCOMET / ITAR items get a plain refusal).

---

## 8. Decisions for the owner

1. Phase 1 engine: **Godot 4** (one engine for web, Android, desktop; MIT) — or web-only first (Phaser / three.js)?
2. Free daily allowance and monthly cap per user for builds and playtests.
3. Multiplayer servers (Phase 4): on her own cloud only, or a priced Hoola game-server box?
4. Digital twin data (Phase 5): read-only through her MQTT / OPC-UA gateway or CSV upload — confirm "never write".

## 9. Not verified yet (checked during each phase)

Godot 4 headless export on the VPS (binary + templates size, RAM per build); Jolt inside the Godot version shipped;
Steam Audio licence and packaging at the version used; OpenUSD licence terms; JSBSim / Orekit installs; the Online
Gaming Act 2025 rules as notified; real CPU cost per build and playtest on her server.
