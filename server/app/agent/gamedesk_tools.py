"""v0.379 GAME DESK tool: `game_desk` = the Game Developer employee (gamedesk/service.py). Original games from her words
in Godot 4: a design doc first (her OK), then code -> headless play -> Web export -> Hoola plays it -> a private play
link. Only while the Game Developer is hired (Employees). Nothing is published: the link is hers to share."""
from __future__ import annotations

import asyncio

from .tools import Ctx, ToolError

KEY = "game_dev"

GAMEDESK_TOOLS = [
    {"name": "game_desk", "description": (
        "Game Developer employee (Godot 4): makes an ORIGINAL small game from her words and gives a private link she plays "
        "on any phone. action=new (brief = her idea in her words, orientation portrait|landscape|square) writes a short "
        "design doc FIRST and waits; show her the design and ask for OK. action=approve (id; feedback = her changes, empty = "
        "build it): builds in the background (code, headless play, Web export, Hoola plays it, fixes its own errors) - the "
        "card updates live and carries the play link. action=change (id, words) = a new version from the current game. "
        "action=status / list / cancel. Refuses copies of a named existing game, real-money / betting games and weapon "
        "targeting; offers an original game in the same genre instead."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["new", "approve", "change", "status", "list", "cancel"]},
         "brief": {"type": "string", "description": "action=new: her game idea, in her words"},
         "orientation": {"type": "string", "enum": ["portrait", "landscape", "square"]},
         "id": {"type": "string", "description": "Game id or number (G-0001)"},
         "feedback": {"type": "string", "description": "action=approve: her changes to the design (empty = build it)"},
         "words": {"type": "string", "description": "action=change: what to change in the game"}},
         "required": ["action"]}},
]

GAMEDESK_TOOLS.append(
    {"name": "game_studio", "description": (
        "Studio Project: her LONG game project around one Game Desk game - task board, milestones, decisions log, "
        "nightly build, morning report, and a CREW of 49 studio roles (each task has one: builders change the game, "
        "writers write a result). Every task = ONE small change with acceptance criteria; it WAITS for her OK. Actions: "
        "new (game = G-0001 or brief; title, goal) / list / status / add (title, detail, milestone, priority, role, "
        "criteria) / plan (words) / team (team, words): that team's roles plan linked tasks / start (task) / ok (task, "
        "note) / back (task, note): the version before plays again / drop / review (task): its lead checks screenshots + "
        "code against the criteria / gate (milestone_key): PASS|CONCERNS|FAIL|NOT ASSESSED counted in code, advice only / "
        "crew / decide (text, why) / why (q): answer ONLY from what it returns / summary / nightly / restore (n) / "
        "settings / github (repo, private): a card for her tap. Quote only returned verdicts and numbers. id = S-0001 "
        "(optional with one project). Only while the Game Developer is hired."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["new", "list", "status", "add", "plan", "start", "ok", "back", "drop",
                                               "decide", "why", "summary", "nightly", "restore", "settings", "github",
                                               "crew", "team", "gate", "review"]},
         "id": {"type": "string", "description": "Studio project id or number (S-0001)"},
         "game": {"type": "string", "description": "action=new: an existing game (G-0001)"},
         "brief": {"type": "string", "description": "action=new without game: the new game's idea in her words"},
         "orientation": {"type": "string", "enum": ["portrait", "landscape", "square"]},
         "title": {"type": "string"}, "goal": {"type": "string"},
         "task": {"type": "string", "description": "Task id or number (T-0001)"},
         "detail": {"type": "string"}, "milestone": {"type": "string", "enum": ["proto", "playable", "alpha", "beta", "release"]},
         "priority": {"type": "integer"}, "note": {"type": "string"}, "words": {"type": "string"},
         "text": {"type": "string"}, "why": {"type": "string"}, "q": {"type": "string"}, "n": {"type": "integer"},
         "auto": {"type": "boolean"}, "nightly_on": {"type": "boolean"}, "summary_on": {"type": "boolean"},
         "summary_hour": {"type": "integer"}, "repo": {"type": "string"}, "private": {"type": "boolean"},
         "role": {"type": "string", "description": "action=add: a crew role key (optional; picked from the words)"},
         "criteria": {"type": "array", "items": {"type": "string"}, "description": "action=add: how 'done' is checked"},
         "team": {"type": "string"}, "milestone_key": {"type": "string"}, "status": {"type": "string", "enum": ["active", "paused", "archived"]}},
         "required": ["action"]}})

GAMEDESK_TOOLS.append(
    {"name": "game_bible", "description": (
        "Game Bible of a Studio Project: the game's names and numbers as DATA (meta, style palette, glossary, player, "
        "curves, and entities: character, enemy, item, level, quest, screen). Every change is checked in code (types, "
        "ranges, references, palette, banned words, no real money); the game reads it (HoolaBible.DATA). Actions: show / "
        "template (kind) / set (kind, entity = JSON object; her edit, applies at once) / remove (kind, eid) / section "
        "(section, value) / seed: first Bible from the design doc as a DRAFT / generate (kind, n, words): a DRAFT - names "
        "from the model, numbers from the curves / accept (ids optional) / reject / check / simulate: seeded balance runs "
        "(win rate per level, spikes, levels to afford items) - quote ONLY its numbers / apply: the Bible into the live "
        "game with no new code / recurve (kind). Show a draft to her and ask before accept. id = S-0001 (optional with "
        "one project). Only while the Game Developer is hired."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["show", "template", "set", "remove", "section", "seed", "generate", "accept",
                                               "reject", "check", "simulate", "apply", "recurve"]},
         "id": {"type": "string", "description": "Studio project (S-0001)"},
         "kind": {"type": "string", "enum": ["character", "enemy", "item", "level", "quest", "screen"]},
         "entity": {"type": "object", "description": "action=set: the entry, e.g. {id, name, tier, behaviour, color}"},
         "eid": {"type": "string"}, "section": {"type": "string", "enum": ["meta", "style", "terms", "player", "curves", "economy"]},
         "value": {"type": "object"}, "n": {"type": "integer"}, "words": {"type": "string"},
         "ids": {"type": "array", "items": {"type": "string"}}, "runs": {"type": "integer"}},
         "required": ["action"]}})

GAMEDESK_TOOLS.append(
    {"name": "game_assets", "description": (
        "Asset pipeline of a Studio Project: the game's art (sprite, icon, ui, background - style-locked to the Game "
        "Bible palette), sounds (sfx made in code: free, preset + seed), music, voice lines and 3D models (Hoola's 3D "
        "Studio). Every file is checked in code and enters the game only after her OK. Actions: list / suggest (what the "
        "Bible still needs) / make (kind, key, words; sprite size, quality fast|best, palette_lock check|strict; sfx preset, "
        "seed; voice text) - PAID kinds (pictures, music, voice) only get a PRICE CARD: tell her the rupees and that her "
        "tap on the card starts it, you can never start a paid one / approve (key, v optional) / reject (key) / apply: "
        "approved assets into the live game with no new code / library (words, kind model|texture, source optional): "
        "search the FREE library - Kenney low-poly models on Hoola's disk, Poly Haven models + textures, ambientCG "
        "textures, all CC0, not AI / library_add (source, item, kind, key): one item as a draft (free; her OK still needed). "
        "For a 3D game look in the library BEFORE making or generating a model. Keys follow the Bible ids (enemy red_bat -> "
        "sprite red_bat, level l1 -> bg_l1, sounds sfx_jump). id = S-0001 (optional with one project). Only while the Game "
        "Developer is hired."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["list", "suggest", "make", "approve", "reject", "apply", "library", "library_add"]},
         "id": {"type": "string"}, "kind": {"type": "string", "enum": ["sprite", "icon", "ui", "background", "sfx", "music",
                                                                        "voice", "model", "texture"]},
         "source": {"type": "string", "enum": ["kenney", "polyhaven", "ambientcg"]}, "item": {"type": "string"},
         "key": {"type": "string"}, "words": {"type": "string"}, "size": {"type": "integer"},
         "quality": {"type": "string", "enum": ["fast", "best"]}, "palette_lock": {"type": "string", "enum": ["off", "check", "strict"]},
         "preset": {"type": "string"}, "seed": {"type": "integer"}, "text": {"type": "string"}, "v": {"type": "integer"}},
         "required": ["action"]}})

GAMEDESK_TOOLS.append(
    {"name": "game_qa", "description": (
        "QA farm + bug tracker of a Studio Project: Hoola's bots (idle, monkey, tapper, keys, restarter; seeded = "
        "repeatable) play a DEBUG web build on desktop / mid phone / low phone speeds, compare the start screen with the "
        "golden one she approved, measure fps / load / memory against the last run, and file numbered bugs with the "
        "exact bot + seed that finds them. Actions: run (background, 2-4 min; also every night after the nightly build) "
        "/ report (the last verdict PASS|CONCERNS|FAIL|NOT ASSESSED, quote only its facts) / bugs / report_bug (title, "
        "detail, severity crash|blocker|major|minor|visual|perf) / fix (bug = B-0001): a board task whose criterion is "
        "that the same bot no longer finds it - a bot bug is FIXED only when its bot cannot find it again / status (bug, "
        "status open|wontfix|duplicate) / golden: her OK that the last start screen is how the game should look. "
        "id = S-0001 (optional with one project). Only while the Game Developer is hired."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["run", "report", "bugs", "report_bug", "fix", "status", "golden"]},
         "id": {"type": "string"}, "bug": {"type": "string"}, "title": {"type": "string"}, "detail": {"type": "string"},
         "severity": {"type": "string", "enum": ["crash", "blocker", "major", "minor", "visual", "perf"]},
         "status": {"type": "string", "enum": ["open", "wontfix", "duplicate"]}},
         "required": ["action"]}})

GAMEDESK_TOOLS.append(
    {"name": "game_release", "description": (
        "Platforms of a Studio Project: the live game as real downloads - linux / windows / macos (built on Hoola's "
        "server) and android (APK to install, AAB for Google Play; built in her private builds repo, signed with the "
        "game's own upload key). Each file is checked in code; macOS is not notarised and Windows not code-signed (the "
        "README says what players see). Actions: targets (where each platform can be built now) / build (platforms, "
        "android_format apk|aab; background) / list / store_kit (store texts for itch.io / Steam / Google Play within "
        "their limits, store images in exact sizes, AI disclosure, Steam upload scripts - a ZIP, nothing published) / "
        "rating (an IARC-style DRAFT; the real rating comes from IARC) / itch (release, target user/game): a CARD - only "
        "her tap uploads; her itch.io key is typed in the app, never in chat. Hoola never logs into her Steam or "
        "publishes alone. id = S-0001 (optional with one project). Only while the Game Developer is hired."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["targets", "build", "list", "store_kit", "rating", "itch"]},
         "id": {"type": "string"}, "platforms": {"type": "array", "items": {"type": "string", "enum": ["linux", "windows", "macos", "android"]}},
         "android_format": {"type": "string", "enum": ["apk", "aab"]}, "release": {"type": "string", "description": "R-001 or the id"},
         "target": {"type": "string", "description": "itch.io page: user/game"}},
         "required": ["action"]}})

GAMEDESK_LABELS = {"game_desk": "Game bana raha hoon", "game_studio": "Game project dekh raha hoon",
                   "game_bible": "Game Bible dekh raha hoon", "game_assets": "Game ke assets dekh raha hoon",
                   "game_qa": "Game ki QA dekh raha hoon", "game_release": "Game ki release dekh raha hoon"}

# v0.420 Phase 7 batch 1: the Game Desk ROLE PACKS - each its own employee, each gated on ITS hire
GAMEDESK_TOOLS.append(
    {"name": "game_world", "description": (
        "Procedural World Generation Engineer employee: makes a world from RULES and a SEED in code (no model, free) - "
        "kind terrain (island / map: biomes, rivers, villages), dungeon (rooms + corridors, exit), city (roads, blocks, "
        "buildings) or level (side-view platformer: gaps, steps, platforms, spikes, goal; jump_h / jump_w = her player's "
        "jump in tiles). Every world is CHECKED in code: made twice (same seed = same world), every village / room / exit "
        "/ goal reachable from the spawn, a level walked with her jump. Actions: make (words; or kind + params, seed, key, "
        "id = S-0001 to attach it to her game project) -> a DRAFT with preview + checks / list / status (world W-001) / "
        "approve / reject / demo (world): Hoola builds a walk-it link in Godot and plays it (background) / apply (id): "
        "the approved worlds go into her game as HoolaWorld, no new code. Quote only the checks and numbers it returns. "
        "Only while this employee is hired."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["make", "list", "status", "approve", "reject", "demo", "apply"]},
         "words": {"type": "string", "description": "action=make: her world in her words"},
         "kind": {"type": "string", "enum": ["terrain", "dungeon", "city", "level"]},
         "params": {"type": "object", "description": "exact numbers, e.g. {w, h, sea, rivers, rooms, jump_h, jump_w}"},
         "seed": {"type": "integer"}, "key": {"type": "string", "description": "the name the game uses (default = kind)"},
         "id": {"type": "string", "description": "Studio project (S-0001) - attach / apply"},
         "world": {"type": "string", "description": "W-001 or the id"}},
         "required": ["action"]}})

GAMEDESK_TOOLS.append(
    {"name": "game_physics", "description": (
        "Physics Engine Developer employee: sets up her game's physics and PROVES it in the real engine (Godot run "
        "headless, free). Her numbers - fastest body speed (px/s), thinnest wall (px), physics ticks, gravity (px/s^2) - "
        "come from her words, the inputs, or her Game Bible's biggest 'speed'. Settings are worked out in code (ticks or "
        "cast-ray continuous collision so nothing tunnels: safe without CCD only when one step <= half the wall), then "
        "Hoola's lab checks free fall, projectile range, an elastic collision, tunnelling at HER speed (6 start points, "
        "with and without CCD), a box stack, a 3D drop, and the whole lab run twice - each against its formula. Actions: "
        "setup (words / inputs, id = S-0001) -> the lab runs in the background / list / status (setup P-001) / approve "
        "(only a PASS) / reject / apply (id): HoolaPhysics goes into her game. Quote only measured numbers. Fluids are "
        "not part of this yet - say so if asked. Only while this employee is hired."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["setup", "list", "status", "approve", "reject", "apply"]},
         "words": {"type": "string"},
         "inputs": {"type": "object", "description": "{speed, wall, ticks, gravity, g3d}"},
         "id": {"type": "string", "description": "Studio project (S-0001)"},
         "setup": {"type": "string", "description": "P-001 or the id"}},
         "required": ["action"]}})

GAMEDESK_LABELS.update({"game_world": "World bana raha hoon", "game_physics": "Game ki physics jaanch raha hoon"})

# v0.421 Phase 7 batch 2: Spatial Audio + Haptics
GAMEDESK_TOOLS.append(
    {"name": "game_audio", "description": (
        "Spatial Audio Systems Programmer employee: her game's sound space, MEASURED in code (free). Reverb zones (room, "
        "hall, cave, cathedral, outdoor or her own RT60 seconds), distance (min_d / max_d metres) and walls (occlusion "
        "-10 dB + low-pass). Renders binaural headphone demos (a sound walking round the head, distances, each zone) and "
        "measures: ear-to-ear time per direction vs Woodworth, level difference by side, 6 dB per doubling, each zone's "
        "RT60 measured back, loudness -16 LUFS / peak -1 dBFS, the render twice. Actions: setup (words / plan, id = "
        "S-0001) -> runs in the background / list / status (setup A-001) / approve (only a PASS) / reject / apply (id): "
        "HoolaAudio goes into her game. A round-head model gives no front/back or height cue - say so if asked; in-game "
        "sound uses Godot's panning + distance + zones. Only while this employee is hired."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["setup", "list", "status", "approve", "reject", "apply"]},
         "words": {"type": "string"}, "plan": {"type": "object", "description": "{zones: [{key, rt60, wet}], min_d, max_d}"},
         "id": {"type": "string", "description": "Studio project (S-0001)"}, "setup": {"type": "string", "description": "A-001"}},
         "required": ["action"]}})

GAMEDESK_TOOLS.append(
    {"name": "game_haptics", "description": (
        "Haptic Feedback Systems Engineer employee: ONE vibration pattern per meaning (jump, coin, hit, game over, level "
        "up...; from her words or exact patterns {name: [{t, d, a, s}]} in ms / 0-1), for actuator phone_lra | phone_erm "
        "| controller | drv2605_lra | drv2605_erm. Checked in code: pulse length for that motor, gaps >= 20 ms, no two "
        "patterns that feel the same, battery per play; an off switch + intensity always. Kit: iPhone .ahap files + "
        "Swift, Android Kotlin waveforms, a DRV2605 C driver compiled here, a pattern picture. Actions: make / list / "
        "status (set H-001) / approve (only a PASS) / reject / apply (id = S-0001): HoolaHaptics goes into her game. "
        "iPhone browsers have no vibration - say so. Only while this employee is hired."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["make", "list", "status", "approve", "reject", "apply"]},
         "words": {"type": "string"}, "patterns": {"type": "object"},
         "actuator": {"type": "string", "enum": ["phone_lra", "phone_erm", "controller", "drv2605_lra", "drv2605_erm"]},
         "id": {"type": "string"}, "set": {"type": "string", "description": "H-001"}},
         "required": ["action"]}})

GAMEDESK_LABELS.update({"game_audio": "Game ki awaaz jaanch raha hoon", "game_haptics": "Game ki vibration bana raha hoon"})

# v0.422 Phase 7 batch 3: Multiplayer + AR / VR
GAMEDESK_TOOLS.append(
    {"name": "game_net", "description": (
        "Multiplayer Network Programmer employee: netcode for her game proved by bots (free). Her numbers: players, tick "
        "(Hz), send (snapshots/s), speed (px/s), size (px), interest (px). Bots play over three networks (good 40 ms; the "
        "plan's 150 ms / 2 % loss / 20 ms jitter; bad mobile 300 ms / 5 % / 60 ms) with an authoritative server, client "
        "prediction + reconciliation, interpolation and lag compensation; MEASURED: rubber-banding, desync (must be 0), "
        "bandwidth per player, interpolation dry-outs, lag-compensated hit agreement; then the Godot netcode itself runs "
        "with a server + 3 clients. Actions: setup (words / inputs, id = S-0001) -> background / list / status (setup "
        "N-001) / approve / reject. A kit (game server for HER cloud + client code) is on the Multiplayer page. Hoola hosts "
        "no game server; the netcode is not inside the game build yet (the game cannot open sockets) - say so. Only while "
        "this employee is hired."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["setup", "list", "status", "approve", "reject"]},
         "words": {"type": "string"}, "inputs": {"type": "object"}, "id": {"type": "string"},
         "setup": {"type": "string", "description": "N-001"}},
         "required": ["action"]}})

GAMEDESK_TOOLS.append(
    {"name": "game_xr", "description": (
        "AR / VR Interaction Engineer employee: a WebXR setup (mode vr | ar, teleport, snap turn 30/45, seated mode, panel "
        "distance, text size, fps 72/90) with the comfort rules checked in code, hand gestures (pinch / grab / point / open) "
        "scored on a labelled set of SYNTHETIC hands and cross-checked in the real Godot, and a demo room that opens in a "
        "headset or phone browser (a play link). Actions: setup (words / settings, id = S-0001) -> background / list / "
        "status (setup X-001) / approve / reject / apply (id): HoolaXR goes into her game. Frame rate on her headset is not "
        "measured here - say so. Only while this employee is hired."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["setup", "list", "status", "approve", "reject", "apply"]},
         "words": {"type": "string"}, "settings": {"type": "object"}, "id": {"type": "string"},
         "setup": {"type": "string", "description": "X-001"}},
         "required": ["action"]}})

GAMEDESK_LABELS.update({"game_net": "Multiplayer netcode jaanch raha hoon", "game_xr": "VR / AR setup jaanch raha hoon"})

# v0.423 Phase 7 batch 4: training simulators, digital twin, VFX pipeline
GAMEDESK_TOOLS.append(
    {"name": "game_sim", "description": (
        "Simulation Software Engineer employee: a TRAINING model validated now (seconds, free). kind orbit (two-body + J2: "
        "params alt_km, inc_deg, dt_s, hours; scenario events {kind: burn, t, dv_mps}), flight (generic light aircraft glide: "
        "mass_kg, S_m2, CD0, k, V_mps; events {kind: gust, t, w_mps}) or driving (single-track car: mass_kg, a_m, b_m, Cf, "
        "Cr, V_mps, steer_deg). Each model is checked against its textbook case (orbit period, energy, J2 node drift; glide "
        "angle, phugoid; steady yaw rate) and run twice; the source, step and integrator are stated; an orbit model is also "
        "checked in the real Godot. Actions: setup / list / status (setup M-001) / approve / reject / apply (id = S-0001, "
        "orbit only). REFUSE weapon / targeting / combat simulators. A training aid, not a certified device. Only while hired."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["setup", "list", "status", "approve", "reject", "apply"]},
         "words": {"type": "string"}, "kind": {"type": "string", "enum": ["orbit", "flight", "driving"]},
         "params": {"type": "object"}, "scenario": {"type": "object"}, "id": {"type": "string"},
         "setup": {"type": "string", "description": "M-001"}},
         "required": ["action"]}})

GAMEDESK_TOOLS.append(
    {"name": "game_twin", "description": (
        "Digital Twin Architect employee: her line as data (stations: machines, cycle_s, cv, mtbf_h, mttr_min, buffer - each "
        "{value, source: 'tag:<her tag>' | 'assumption: ...'}; data_map entries READ-only: csv / mqtt-subscribe / opcua-read / "
        "historian-read), simulated by Hoola's event engine (checked against exact answers and queueing theory): throughput, "
        "utilisation, WIP, lead time, bottleneck, and what-ifs (one more machine, 20 % faster, a second shift). actual = her "
        "real daily output to validate (within 10 %); without it say NOT ASSESSED. No model given = a worked example to copy. "
        "Actions: setup / list / status (D-001) / approve / reject. It NEVER writes / commands / controls her plant. Only while hired."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["setup", "list", "status", "approve", "reject"]},
         "words": {"type": "string"}, "model": {"type": "object"}, "actual": {"type": "array", "items": {"type": "number"}},
         "setup": {"type": "string", "description": "D-001"}},
         "required": ["action"]}})

GAMEDESK_TOOLS.append(
    {"name": "game_vfx", "description": (
        "VFX Pipeline Technical Director employee: a CG pipeline checked now (free): naming <show>_<seq>_<shot>_<task>_v###.####.ext "
        "with versions, colour end to end (sources declared: srgb_texture / lin_srgb / logc3 / slog3 / acescg; working ACEScg; "
        "view srgb_display / rec709_display) converted and measured, a real ACEScg EXR test frame written and read back, a "
        "render queue with failed frames re-queued and cost per shot (her workers, cores, rate, fail_rate), every frame traced "
        "to its scene sha256. plan = {show, seq, shots: [{shot, frames: [a, b], frame_min}], sources, view, workers, cores, "
        "rate_inr_per_core_h, fail_rate}; none = a worked example. Actions: setup / list / status (V-001) / approve / reject. "
        "Blender / OpenColorIO / OpenUSD are not installed on the server - the render script is for her machines. Only while hired."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["setup", "list", "status", "approve", "reject"]},
         "words": {"type": "string"}, "plan": {"type": "object"}, "setup": {"type": "string", "description": "V-001"}},
         "required": ["action"]}})

GAMEDESK_LABELS.update({"game_sim": "Simulator jaanch raha hoon", "game_twin": "Digital twin chala raha hoon",
                        "game_vfx": "VFX pipeline jaanch raha hoon"})

# v0.425 Phase 8: Hoola Runtime (replay / bot / telemetry) + Ask Hoola in the editor
GAMEDESK_TOOLS.append(
    {"name": "game_runtime", "description": (
        "Hoola Runtime of a Studio project (part of the Game Developer desk): HoolaRuntime goes into every build - a replay "
        "recorder, an in-engine test bot and OPT-IN telemetry. Actions: status (settings + last replay tests) / replay_test: "
        "the bot plays the live version headless, the same seed again, then its recording is played back - the end states "
        "must match (deterministic, and every bug comes with a replay); a mismatch names its cause (randomize(), the clock) "
        "/ telemetry: the dashboard (installs, sessions, D1 / D7, funnel) / set (on, telemetry): telemetry needs her switch "
        "AND each player's yes, is refused for a children's game, keeps no personal data. Editor tokens and the Godot plugin "
        "are made in the console (Game Desk > Editor) - never in chat. id = S-0001 (optional with one project)."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["status", "replay_test", "telemetry", "set"]},
         "id": {"type": "string"}, "on": {"type": "boolean"}, "telemetry": {"type": "boolean"}},
         "required": ["action"]}})

GAMEDESK_LABELS.update({"game_runtime": "Game runtime jaanch raha hoon"})

# v0.428 Phase 9: live ops
GAMEDESK_TOOLS.append(
    {"name": "game_liveops", "description": (
        "Live ops of a shipped Studio game (part of the Game Developer desk), for games that run for years. Actions: "
        "status (tests, events, patch checks) / dashboard (installs, DAU, D1 / D7 / D30, funnel, balance outliers, "
        "difficulty-spike levels) / experiment_add (key, title, goal = event or d1, variants = [{name, weight %, set: "
        "{\"player.hp\": 120}}], first = control, mde = smallest difference worth knowing, 0.05 = 5 points) -> a DRAFT / "
        "experiment_start + experiment_stop (ship = a group name -> a board task for her OK) = her tap / experiment_result: "
        "MEASURED - players per group, sample-size target, split check, z-test; quote its verdict word for word, never call "
        "a winner before it does / event_add (key, title, starts, ends in India time '2026-11-15 18:00', set) -> a DRAFT, "
        "event_approve / event_cancel = her tap / crashes (grouped script errors from players who said yes, crash-free "
        "share per version) / hotfix (sig) -> a priority board task / patch_check: saved replays + a bot run on the newest "
        "version in the real engine (background, about a minute) / money: revenue ONLY from the CSV she imports in the "
        "console (Hoola sees no store). Live values only change Bible numbers within 1/4x - 4x, or flag.<name>. "
        "id = S-0001 (optional with one project)."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["status", "dashboard", "experiment_add", "experiment_start", "experiment_stop",
                                               "experiment_result", "event_add", "event_approve", "event_cancel", "crashes",
                                               "hotfix", "patch_check", "money"]},
         "id": {"type": "string"}, "key": {"type": "string"}, "title": {"type": "string"}, "goal": {"type": "string"},
         "variants": {"type": "array", "items": {"type": "object"}}, "mde": {"type": "number"}, "ship": {"type": "string"},
         "starts": {"type": "string"}, "ends": {"type": "string"}, "set": {"type": "object"}, "sig": {"type": "string"}},
         "required": ["action"]}})

GAMEDESK_LABELS.update({"game_liveops": "Game ke live ops dekh raha hoon"})

# v0.433 Phase 10: big-studio mode (the Hoola Crew inside Unity / Unreal on her machines)
GAMEDESK_TOOLS.append(
    {"name": "game_bigstudio", "description": (
        "Big-studio mode (part of the Game Developer desk): her game lives in HER own Unity / Unreal / Godot project on her "
        "machines, and the Hoola Crew works inside her editor through its official scripting (Unity package, Unreal Python "
        "plugin, any MCP client). Actions: projects / new_project (engine unity | unreal | godot, title, engine_version, "
        "about, module = Unreal C++ module) / add_task (project E-001, title, detail) / tasks / task (task T-0001: the "
        "proposal, checks, her editor's compile result) / reopen (task, note). Proposals are made when HER editor asks "
        "(Hoola Crew > Next task), checked on the server (paths, banned calls, syntax), and written ONLY when she clicks "
        "Apply in her editor; 'compiled' is said only when her editor reported it. Plugins + the editor token: console "
        "Game Desk > Big studio - never in chat."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["projects", "new_project", "add_task", "tasks", "task", "reopen"]},
         "project": {"type": "string"}, "engine": {"type": "string", "enum": ["unity", "unreal", "godot"]},
         "title": {"type": "string"}, "engine_version": {"type": "string"}, "about": {"type": "string"}, "module": {"type": "string"},
         "detail": {"type": "string"}, "task": {"type": "string"}, "note": {"type": "string"}},
         "required": ["action"]}})

GAMEDESK_LABELS.update({"game_bigstudio": "Studio project dekh raha hoon"})

# v0.447 Game Arena: "is a Hoola game any good?" as numbers (owner only)
GAMEDESK_TOOLS.append(
    {"name": "game_arena", "description": (
        "Hoola Game Arena (owner only): proves whether Hoola's games are getting BETTER, as numbers. A fixed set of 500 "
        "game briefs (every genre x an Indian setting, seeded) - a run builds n of them as a hidden tenant exactly as an "
        "owner would get them, then the QA bots PLAY each build and the card records what the engine said (started, fps, "
        "script errors, did any input change the game's state, did a bot reach an ending), an independent judge scores "
        "the first thirty seconds, and originality is measured as distance from every other game of the run (Apple 4.3(b) "
        "rejects games indistinguishable from what exists, so this is a shippability number). Actions: status (runs + duel "
        "table) / briefs (the fixed set) / start (n, seed, budget_inr, note) / run (id) / stop (id) / compare (a, b: two "
        "runs metric by metric) / duel (brief, rival, url: her rival's PUBLIC web game, both played by the same bots and "
        "judged blind as A / B). Whether a game is FUN is NOT ASSESSED and the card says so - never claim it. Quote only "
        "the numbers it returns."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["status", "briefs", "start", "run", "stop", "compare", "duel"]},
         "n": {"type": "integer"}, "seed": {"type": "integer"}, "budget_inr": {"type": "number"},
         "note": {"type": "string"}, "id": {"type": "string"}, "a": {"type": "string"}, "b": {"type": "string"},
         "genre": {"type": "string"}, "brief": {"type": "string"}, "rival": {"type": "string"}, "url": {"type": "string"}},
         "required": ["action"]}})

GAMEDESK_LABELS.update({"game_arena": "Game arena chala raha hoon"})

# v0.455 provenance: what shipped, and what of it is hers
GAMEDESK_TOOLS.append(
    {"name": "game_provenance", "description": (
        "Where every piece of a shipped game came from (part of the Game Developer desk), recorded when it happened and "
        "never worked out afterwards. Actions: sheet (everything: the model(s) that wrote the code, every APPROVED asset "
        "with how it was made, her own human record, and the store answers) / steam (a DRAFT answer to Steam's Content "
        "Survey) / disclosure (one line for a store page, Unity's Asset Store or Fab's CreatedWithAI tag) / human (what "
        "SHE chose, changed, rejected and uploaded). THREE THINGS NEVER MERGED: generated assets (a model made them - "
        "these are what a store survey asks about), code-made assets (a sound from a preset and a seed, a Blender-scripted "
        "mesh - arithmetic, NOT generative AI; calling them AI would be a false statement on her survey), and her own "
        "uploaded files (hers, and her copyright). Only APPROVED assets ship, so only those are counted. The game calls "
        "no model while it runs, so Steam's LIVE-generated question is a plain No. NEVER say the declaration is correct "
        "or give legal advice: she signs it, and the tool prints the judgement calls (the GDScript is one) for her to "
        "decide. id = S-0001 (optional with one project)."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["sheet", "steam", "disclosure", "human"]}, "id": {"type": "string"}},
         "required": ["action"]}})

GAMEDESK_LABELS.update({"game_provenance": "Dekh raha hoon kya kahan se aaya"})

# v0.456 scenes as checked data - the 12-file ceiling
GAMEDESK_TOOLS.append(
    {"name": "game_scenes", "description": (
        "Scenes as CHECKED DATA - 2D and 3D. Actions: list / new (words, name: her words become a scene SPEC that Hoola "
        "checks, generates and LOADS IN THE REAL ENGINE; a draft only if it really loaded) / approve (her tap: into the next "
        "build) / reject. THE MODEL NEVER WRITES A .tscn: an embedded script inside a scene RUNS and would escape the code "
        "guard (measured), so scripts attach only by file name. INSTANCES scale content: one coin.tscn placed forty times. "
        "3D: meshes with real materials, lights with shadows, a camera, a sky / fog / glow, 3D physics, and her APPROVED 3D "
        "models from the Assets tab placed by name - none is ever invented. Quote only what the ENGINE reported (nodes, "
        "meshes, lights, cameras, animations). The check proves a 3D scene loads; it cannot SEE how it looks, so never call "
        "one beautiful from the check. TileMaps / GridMaps and shaders are NOT available - say so. id = S-0001."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["list", "new", "approve", "reject"]},
         "id": {"type": "string"}, "words": {"type": "string"}, "name": {"type": "string"}},
         "required": ["action"]}})

GAMEDESK_LABELS.update({"game_scenes": "Scene bana raha hoon"})


def _short(v: dict) -> dict:
    out = {k: v.get(k) for k in ("id", "number", "title", "status", "say", "stage", "error", "play_url", "version", "notes",
                                 "numbers", "warnings") if v.get(k) not in (None, "", [], {})}
    if v.get("status") == "design_ready" and v.get("design"):
        out["design"] = v["design"]
        out["note"] = "Show her this design doc (short) and ask: build it as is, or what to change? Then action=approve."
    if v.get("status") in ("designing", "queued", "writing", "building", "testing"):
        out["note"] = "Working in the background; the card on her screen updates live. Do not wait or poll in a loop."
    if v.get("status") == "done" and v.get("play_url"):
        out["note"] = ("Give her the play link in one line (private until she shares it) and what to try. Never claim "
                       "numbers that are not here.")
    return out


async def game_desk(ctx: Ctx, action="", brief="", orientation="portrait", id="", feedback="", words="", **_):
    from ..employee import hire
    from ..gamedesk import service as G
    t = ctx.tenant_id
    if not await asyncio.to_thread(hire.is_hired, t, KEY):
        raise ToolError("Game Developer is not hired: hire it in Employees (Hoola app / console) with one tap, "
                        "then the game can be made.")
    if action in ("new", "approve", "change", "cancel") and str(getattr(ctx, "actor", "owner")).startswith(("customer:", "staff:")):
        raise ToolError("Making / changing a game is the owner's job only.")
    try:
        if action == "new":
            return _short(await asyncio.to_thread(G.start, t, ctx.conversation_id, brief, orientation, ctx.actor))
        if action == "approve":
            return _short(await asyncio.to_thread(G.approve, t, id, feedback))
        if action == "change":
            return _short(await asyncio.to_thread(G.change, t, id, words))
        if action == "cancel":
            return _short(await asyncio.to_thread(G.cancel, t, id))
        if action == "status":
            return _short(await asyncio.to_thread(G.get, t, id))
        if action == "list":
            return {"games": [_short(v) for v in await asyncio.to_thread(G.projects, t, 10)]}
    except G.GameError as e:
        raise ToolError(str(e))
    raise ToolError("action = new | approve | change | status | list | cancel")


def _brief_studio(v: dict) -> dict:
    keep = ("id", "number", "title", "goal", "status", "milestone", "counts", "auto", "night")
    out = {k: v.get(k) for k in keep if v.get(k) not in (None, "", [], {})}
    out["milestones"] = [{k: m.get(k) for k in ("key", "name", "done", "total", "pct", "target")} for m in v.get("milestones") or []]
    g = v.get("game") or {}
    out["game"] = {k: g.get(k) for k in ("number", "status", "say", "play_url", "version") if g.get(k)}
    tasks = v.get("tasks") or (v.get("review", []) + v.get("next", []))
    show = [t for t in tasks if t.get("status") in ("working", "review", "blocked")] + \
           [t for t in tasks if t.get("status") == "todo"][:8]
    out["tasks"] = [{**{k: t.get(k) for k in ("number", "title", "status", "milestone", "priority", "error", "version",
                                              "role_name", "verdict") if t.get(k) not in (None, "", 0)},
                     **({"notes": t["notes"][:600]} if t.get("notes") else {})} for t in show[:16]]
    if v.get("decisions"):
        out["decisions"] = [f"{d['text']} - {d['why']}" if d.get("why") else d["text"] for d in v["decisions"][:6]]
    return out


async def game_studio(ctx: Ctx, action="", id="", game="", brief="", orientation="portrait", title="", goal="", task="",
                      detail="", milestone="", priority=2, note="", words="", text="", why="", q="", n=0, auto=None,
                      nightly_on=None, summary_on=None, summary_hour=None, status="", repo="", private=True, role="",
                      criteria=None, team="", milestone_key="", **_):
    from ..employee import hire
    from ..gamedesk import service as G
    from ..gamedesk import studio as S
    t = ctx.tenant_id
    if not await asyncio.to_thread(hire.is_hired, t, KEY):
        raise ToolError("Game Developer is not hired: hire it in Employees with one tap, then the game project will run.")
    reads = ("list", "status", "why", "summary")
    if action not in reads and str(getattr(ctx, "actor", "owner")).startswith(("customer:", "staff:")):
        raise ToolError("Changing a game project is the owner's job only.")
    run = asyncio.to_thread
    try:
        if action == "new":
            return _brief_studio(await run(S.create, t, ctx.conversation_id, title, goal, game, brief, orientation, ctx.actor))
        if action == "list":
            return {"projects": [_brief_studio(v) for v in await run(S.studios, t)]}
        if action == "crew":
            from ..gamedesk import crew as CR
            ro = CR.roster()
            return {"count": ro["count"], "builds": ro["builds"], "note": ro["note"], "teams": [x["key"] for x in ro["teams"]],
                    "tiers": {x["label"]: [f"{r['key']} ({r['mode']})" for r in x["roles"]] for x in ro["tiers"]}}
        if not id:
            mine = await run(S.studios, t)
            if len(mine) == 1:
                id = mine[0]["id"]
            else:
                raise ToolError("Which project? Give the id / number (S-0001); see action=list.")
        if action == "status":
            return _brief_studio(await run(S.get, t, id))
        if action == "add":
            crit = [{"text": c, "by": "screen"} for c in criteria] if isinstance(criteria, list) else None
            return {"added": await run(S.add_task, t, id, title or words, detail, milestone, "feature", priority or 2, "her",
                                       role, crit),
                    "note": "Added to To do. It builds when started (action=start) or by itself if the project is on auto."}
        if action == "plan":
            res = await run(S.plan, t, id, words)
            return {"made": [f"{x['number']} [{x['milestone']}] {x['title']}" for x in res["made"]],
                    "note": "Show her these in a short list; she can drop or change any. Nothing is built yet."}
        if action == "team":
            res = await run(S.plan, t, id, words, team)
            return {"made": [f"{x['number']} [{x['role_name']}] {x['title']}" for x in res["made"]],
                    "note": "Show her the team's tasks in a short list; nothing is built yet."}
        if action == "review":
            v = await run(S.review_task, t, id, task)
            return {"task": v["number"], "verdict": v["verdict"], "review": v["review"],
                    "criteria": [f"[{c['status']}] {c['text']}" for c in v["criteria"]]}
        if action == "gate":
            return await run(S.gate, t, id, milestone_key or milestone)
        if action == "start":
            return {"started": await run(S.start_task, t, id, task),
                    "note": "Building in the background; it will wait for her OK. Do not poll in a loop."}
        if action == "ok":
            res = await run(S.approve_task, t, id, task, note)
            return {"done": res["done"], "next": (res.get("next") or {}).get("number", ""), "studio": _brief_studio(res["studio"])}
        if action == "back":
            return _brief_studio(await run(S.reject_task, t, id, task, note))
        if action == "drop":
            return {"task": await run(S.edit_task, t, id, task, status="dropped")}
        if action == "decide":
            return _brief_studio(await run(S.decide, t, id, text or note, why))
        if action == "why":
            return await run(S.why, t, id, q or words or text)
        if action == "summary":
            return {"summary": await run(S.summary, t, id)}
        if action == "nightly":
            return {"night": await run(S.nightly, t, id)}
        if action == "restore":
            return _brief_studio(await run(S.restore, t, id, int(n or 0)))
        if action == "github":
            from ..gamedesk import github as GGH
            from ..site.github import GithubError
            try:
                card = await run(GGH.request, t, id, repo, bool(private), ctx.conversation_id)
            except GithubError as e:
                raise ToolError(f"GitHub: {e} (add the GitHub token in the Hoola app > Website > GitHub)")
            return {"card": card["say"], "note": "The card is on her screen; only her tap pushes."}
        if action == "settings":
            return _brief_studio(await run(S.settings, t, id, title=title, goal=goal, auto=auto, nightly_on=nightly_on,
                                           summary_on=summary_on, summary_hour=summary_hour, status=status or None))
    except G.GameError as e:
        raise ToolError(str(e))
    raise ToolError("action = new | list | status | add | plan | start | ok | back | drop | decide | why | summary | "
                    "nightly | restore | settings | github")


def _bible_short(v: dict) -> dict:
    d = v.get("data") or {}
    out = {"version": v.get("version"), "in_game": v.get("applied"), "counts": v.get("counts"),
           "errors": (v.get("check") or {}).get("errors", [])[:8], "warnings": (v.get("check") or {}).get("warnings", [])[:8],
           "meta": d.get("meta"), "palette": (d.get("style") or {}).get("palette"), "player": d.get("player"),
           "entities": {k: [{f: e.get(f) for f in ("id", "name", "tier", "order", "hp", "damage", "price", "behaviour", "effect")
                             if e.get(f) not in (None, "")} for e in rows][:25]
                        for k, rows in (d.get("entities") or {}).items() if rows}}
    dr = v.get("draft") or {}
    if dr:
        out["draft"] = {"kind": dr.get("kind"), "add": [{f: e.get(f) for f in ("id", "name", "tier", "hp", "damage", "price", "order")
                                                         if e.get(f) not in (None, "")} for e in dr.get("add") or []],
                        "errors": (dr.get("check") or {}).get("errors", [])[:6]}
        out["note"] = "A DRAFT waits: show it to her briefly and ask; only her yes = action=accept."
    if v.get("applied", 0) < v.get("version", 0):
        out["note_game"] = "The live game has an older Bible; action=apply rebuilds it with no new code."
    return out


async def game_bible(ctx: Ctx, action="", id="", kind="", entity=None, eid="", section="", value=None, n=3, words="",
                     ids=None, runs=0, **_):
    from ..employee import hire
    from ..gamedesk import bible as B
    from ..gamedesk import service as G
    from ..gamedesk import studio as S
    t = ctx.tenant_id
    if not await asyncio.to_thread(hire.is_hired, t, KEY):
        raise ToolError("Game Developer is not hired: hire it in Employees with one tap.")
    if action not in ("show", "template", "check", "simulate") and str(getattr(ctx, "actor", "owner")).startswith(("customer:", "staff:")):
        raise ToolError("Changing the Game Bible is the owner's job only.")
    run = asyncio.to_thread
    try:
        if not id:
            mine = await run(S.studios, t)
            if len(mine) != 1:
                raise ToolError("Which project? Give the id (S-0001); see game_studio action=list.")
            id = mine[0]["id"]
        if action == "show":
            return _bible_short(await run(B.view, t, id))
        if action == "template":
            if kind not in B.KINDS:
                raise ToolError("kind = " + ", ".join(B.KINDS))
            return {"kind": kind, "fields": {f: {"type": ty, "default": d, **o} for f, (ty, d, o) in B.KINDS[kind]["fields"].items()},
                    "note": "Numbers of enemy / item / level come from the curves by tier; set only to override."}
        if action == "set":
            return _bible_short(await run(B.set_entity, t, id, kind, entity if isinstance(entity, dict) else {}))
        if action == "remove":
            return _bible_short(await run(B.remove_entity, t, id, kind, eid))
        if action == "section":
            return _bible_short(await run(B.set_section, t, id, section, value if isinstance(value, dict) else {}))
        if action == "seed":
            return _bible_short(await run(B.seed, t, id))
        if action == "generate":
            return _bible_short(await run(B.generate, t, id, kind, int(n or 3), words))
        if action == "accept":
            return _bible_short(await run(B.accept, t, id, list(ids) if ids else None))
        if action == "reject":
            return _bible_short(await run(B.reject, t, id))
        if action == "check":
            v = await run(B.view, t, id)
            return {"errors": v["check"]["errors"], "warnings": v["check"]["warnings"]}
        if action == "simulate":
            res = await run(B.sim, t, id, int(runs or B.SIM_RUNS))
            res["note"] = "Quote only these numbers. Same Bible = same numbers (seeded)."
            return res
        if action == "apply":
            await run(B.apply, t, id)
            return {"ok": True, "note": "Rebuilding the live game with the Bible (no new code); the card updates live."}
        if action == "recurve":
            return _bible_short(await run(B.recurve, t, id, kind))
    except (B.BibleError, G.GameError) as e:
        raise ToolError(str(e))
    raise ToolError("action = show | template | set | remove | section | seed | generate | accept | reject | check | "
                    "simulate | apply | recurve")


def _asset_short(v: dict) -> dict:
    return {"assets": [{k: a.get(k) for k in ("key", "kind", "status", "version", "approved", "cost_inr", "error")
                        if a.get(k) not in (None, "", 0)} | ({"problems": a["checks"].get("errors")} if (a.get("checks") or {}).get("errors") else {})
                       for a in v.get("assets", [])][:40],
            "price_card": v.get("card"), "in_game": v.get("in_game"), "spent_inr": v.get("spent_inr")}


async def game_assets(ctx: Ctx, action="", id="", kind="", key="", words="", size=0, quality="fast", palette_lock="check",
                      preset="", seed=0, text="", v=0, source="", item="", **_):
    from ..employee import hire
    from ..gamedesk import assets as A
    from ..gamedesk import service as G
    from ..gamedesk import studio as S
    t = ctx.tenant_id
    if not await asyncio.to_thread(hire.is_hired, t, KEY):
        raise ToolError("Game Developer is not hired: hire it in Employees with one tap.")
    if action not in ("list", "suggest", "library") and str(getattr(ctx, "actor", "owner")).startswith(("customer:", "staff:")):
        raise ToolError("Changing game assets is the owner's job only.")
    run = asyncio.to_thread
    try:
        if not id:
            mine = await run(S.studios, t)
            if len(mine) != 1:
                raise ToolError("Which project? Give the id (S-0001).")
            id = mine[0]["id"]
        if action == "list":
            await run(A.collect_models, t, id)
            return _asset_short(await run(A.assets, t, id))
        if action == "library":                            # v0.811 the free CC0 library: search only
            from ..gamedesk import library as L
            try:
                got = await run(L.search, words, kind if kind in ("model", "texture") else "model", source, 12)
            except L.LibraryError as e:
                raise ToolError(str(e)) from None
            return {"items": [{k: i.get(k) for k in ("source", "id", "name", "kind", "tags", "licence", "kb", "triangles") if i.get(k) is not None}
                              for i in got["items"]], "found": got["found"], "down": got["down"],
                    "note": "Free, CC0, made by people (not AI). Add one with action=library_add (source, item, kind, key); it is a draft until she approves it."}
        if action == "library_add":
            from ..gamedesk import library as L
            a = await run(L.add, t, id, source, item, kind if kind in ("model", "texture") else "model", key)
            return {"asset": a["key"], "kind": a["kind"], "status": a["status"], "error": a.get("error") or "",
                    "note": "From the free library (CC0). It is a DRAFT: only her OK on the Assets page puts it in the game. Never say it is in the game."}
        if action == "suggest":
            sug = await run(A.suggest, t, id)
            return {"suggest": sug, "total_inr_if_all": sum(x["cost_inr"] for x in sug),
                    "note": "Nothing is made or priced yet; ask her which ones to make."}
        if action == "make":
            spec = {"size": size or None, "quality": quality, "palette_lock": palette_lock, "preset": preset or None,
                    "seed": seed or None, "text": text or None}
            a = await run(A.request, t, id, kind, key, words, **{k: x for k, x in spec.items() if x is not None})
            if a["status"] == "priced":
                return {"asset": a["key"], "status": "priced", "cost_inr": a["cost_inr"],
                        "note": f"A price card for about Rs {a['cost_inr']} is on her Assets page; ONLY her tap starts it. Never say it is made."}
            return {"asset": a["key"], "status": a["status"], "note": "Free kind: being made now; it waits for her OK."}
        if action == "approve":
            return {"asset": (await run(A.approve, t, id, key, int(v or 0)))["key"], "status": "approved",
                    "note": "Approved. action=apply puts the approved assets into the game."}
        if action == "reject":
            return {"asset": (await run(A.reject, t, id, key))["key"], "status": "rejected"}
        if action == "apply":
            await run(A.apply, t, id)
            return {"ok": True, "note": "Rebuilding the live game with the approved assets (no new code)."}
    except G.GameError as e:
        raise ToolError(str(e))
    raise ToolError("action = list | suggest | make | approve | reject | apply")


async def game_qa(ctx: Ctx, action="", id="", bug="", title="", detail="", severity="major", status="", **_):
    from ..employee import hire
    from ..gamedesk import qa as Q
    from ..gamedesk import service as G
    from ..gamedesk import studio as S
    t = ctx.tenant_id
    if not await asyncio.to_thread(hire.is_hired, t, KEY):
        raise ToolError("Game Developer is not hired: hire it in Employees with one tap.")
    if action not in ("report", "bugs") and str(getattr(ctx, "actor", "owner")).startswith(("customer:", "staff:")):
        raise ToolError("Changing game QA is the owner's job only.")
    run = asyncio.to_thread
    try:
        if not id:
            mine = await run(S.studios, t)
            if len(mine) != 1:
                raise ToolError("Which project? Give the id (S-0001).")
            id = mine[0]["id"]
        if action == "run":
            res = await run(Q.start, t, id)
            return {**res, "note": "The bots play in the background (2-4 minutes); the report lands on the QA page. Do not poll."}
        if action in ("report", "bugs"):
            d = await run(Q.bugs, t, id)
            last = d.get("last") or {}
            out = {"open": d["open"], "crash_open": d["crash_open"],
                   "last": {k: last.get(k) for k in ("at", "version", "verdict", "blockers", "concerns", "missing", "filed", "fixed", "perf")}}
            if action == "bugs":
                out["bugs"] = [{k: b.get(k) for k in ("number", "title", "severity", "status", "seen", "regression", "task")}
                               for b in d["bugs"][:30]]
            return out
        if action == "report_bug":
            return {"bug": await run(Q.report_bug, t, id, title, detail, severity)}
        if action == "fix":
            res = await run(Q.fix_bug, t, id, bug)
            return {"bug": res["bug"]["number"], "task": res["task"]["number"],
                    "note": "A board task now carries the fix; the bug closes only when the same bot cannot find it again."}
        if action == "status":
            return {"bug": await run(Q.set_bug, t, id, bug, status)}
        if action == "golden":
            return await run(Q.approve_golden, t, id)
    except G.GameError as e:
        raise ToolError(str(e))
    raise ToolError("action = run | report | bugs | report_bug | fix | status | golden")


async def game_release(ctx: Ctx, action="", id="", platforms=None, android_format="apk", release="", target="", **_):
    from ..employee import hire
    from ..gamedesk import platforms as PF
    from ..gamedesk import service as G
    from ..gamedesk import studio as S
    t = ctx.tenant_id
    if not await asyncio.to_thread(hire.is_hired, t, KEY):
        raise ToolError("Game Developer is not hired: hire it in Employees with one tap.")
    if action not in ("targets", "list", "rating") and str(getattr(ctx, "actor", "owner")).startswith(("customer:", "staff:")):
        raise ToolError("Game release is the owner's job only.")
    run = asyncio.to_thread
    try:
        if action == "targets":
            return {"targets": PF.targets()}
        if not id:
            mine = await run(S.studios, t)
            if len(mine) != 1:
                raise ToolError("Which project? Give the id (S-0001).")
            id = mine[0]["id"]
        if action == "build":
            v = await run(PF.release, t, id, list(platforms or []), android_format)
            return {"release": v["number"], "version": v["version_name"], "platforms": list(v["platforms"]),
                    "note": "Building in the background; downloads appear on the Release page. A platform that cannot be built here says why."}
        if action == "list":
            d = await run(PF.releases, t, id)
            return {"releases": [{"number": x["number"], "status": x["status"], "version": x["version_name"],
                                  "platforms": {k: {kk: v.get(kk) for kk in ("status", "mb", "note") if v.get(kk)} for k, v in x["platforms"].items()}}
                                 for x in d["releases"][:8]], "targets": {k: v["ready"] for k, v in d["targets"].items()}}
        if action == "store_kit":
            k = await run(PF.store_kit, t, id)
            return {k2: k[k2] for k2 in ("itch", "steam", "play", "ai_disclosure", "notes", "images")} | {
                "note": "Show her the texts briefly; the ZIP (images, Steam scripts) is on the Release page. Nothing was published."}
        if action == "rating":
            st = await run(S.get, t, id)
            return await run(PF.rating_draft, t, st["id"])
        if action == "itch":
            d = await run(PF.releases, t, id)
            rel = next((x for x in d["releases"] if x["number"] == str(release).upper() or x["id"] == release), None)
            if rel is None:
                raise ToolError("Which release? Give R-001.")
            card = await run(PF.itch_card, t, id, rel["id"], target)
            return {"card": card["say"], "note": "The card waits for her tap on the Release page; you cannot upload."}
    except G.GameError as e:
        raise ToolError(str(e))
    raise ToolError("action = targets | build | list | store_kit | rating | itch")


def _owner_only(ctx: Ctx, what: str) -> None:
    if str(getattr(ctx, "actor", "owner")).startswith(("customer:", "staff:")):
        raise ToolError(f"{what} is the owner's job only.")


def _world_short(v: dict) -> dict:
    out = {k: v.get(k) for k in ("number", "key", "kind", "seed", "status", "version") if v.get(k) not in (None, "")}
    ch = v.get("checks") or {}
    out["checks"] = {"errors": ch.get("errors", []), "warnings": ch.get("warnings", []), "passed": ch.get("passed", [])[:6]}
    st = v.get("stats") or {}
    out["numbers"] = {k: st.get(k) for k in ("w", "h", "ms", "rivers", "rivers_to_sea", "rooms", "buildings", "reachable_share") if st.get(k) is not None}
    if (v.get("demo") or {}).get("status"):
        out["demo"] = {k: v["demo"].get(k) for k in ("status", "play_url", "errors", "numbers") if v["demo"].get(k)}
    return out


async def game_world(ctx: Ctx, action="", words="", kind="", params=None, seed=None, key="", id="", world="", **_):
    from ..employee import hire
    from ..gamedesk import service as G
    from ..gamedesk import world as W
    t = ctx.tenant_id
    if not await asyncio.to_thread(hire.is_hired, t, W.KEY):
        raise ToolError("Procedural World Engineer is not hired: hire it in Employees with one tap.")
    if action not in ("list", "status"):
        _owner_only(ctx, "World banana / badalna")
    run = asyncio.to_thread
    try:
        if action == "make":
            v = await run(W.make, t, words, kind, seed, params if isinstance(params, dict) else None, id, key)
            return _world_short(v) | {"note": ("Show her the checks in one or two lines and ask OK / another seed. The preview "
                                               "is on the World page; a walk-it link: action=demo.")}
        if action == "list":
            return {"worlds": [_world_short(v) for v in (await run(W.worlds, t, id))[:12]]}
        if action in ("status", "approve", "reject", "demo"):
            fn = {"status": W.get, "approve": W.approve, "reject": W.reject, "demo": W.demo}[action]
            v = await run(fn, t, world)
            out = _world_short(v)
            if action == "demo":
                out["note"] = "Building in the background; the walk-it link appears on the World page. Do not poll."
            return out
        if action == "apply":
            return await run(W.apply, t, id)
    except G.GameError as e:
        raise ToolError(str(e))
    raise ToolError("action = make | list | status | approve | reject | demo | apply")


def _phys_short(v: dict) -> dict:
    lab = v.get("lab") or {}
    out = {"number": v.get("number"), "status": v.get("status"), "inputs": v.get("inputs"),
           "settings": {k: (v.get("settings") or {}).get(k) for k in ("ticks", "gravity", "ccd", "ccd_min_speed", "why")},
           "risk": v.get("risk"), "fluids": "not built yet"}
    if lab:
        out["lab"] = {"verdict": lab.get("verdict"), "passed": f"{lab.get('passed')}/{lab.get('total')}",
                      "cases": [{"case": c["case"], "ok": c["ok"], "note": c["note"]} for c in lab.get("cases", [])],
                      "before": (lab.get("before") or {}).get("say")}
    if v.get("error"):
        out["error"] = v["error"]
    if v.get("status") == "testing":
        out["note"] = "The lab runs in the background (well under a minute); its result shows on the Physics page. Do not poll."
    return out


async def game_physics(ctx: Ctx, action="", words="", inputs=None, id="", setup="", **_):
    from ..employee import hire
    from ..gamedesk import physics as P
    from ..gamedesk import service as G
    t = ctx.tenant_id
    if not await asyncio.to_thread(hire.is_hired, t, P.KEY):
        raise ToolError("Physics Engine Developer is not hired: hire it in Employees with one tap.")
    if action not in ("list", "status"):
        _owner_only(ctx, "Physics setup")
    run = asyncio.to_thread
    try:
        if action == "setup":
            return _phys_short(await run(P.setup, t, words, inputs if isinstance(inputs, dict) else None, id))
        if action == "list":
            return {"setups": [_phys_short(v) for v in (await run(P.setups, t, id))[:10]]}
        if action in ("status", "approve", "reject"):
            fn = {"status": P.get, "approve": P.approve, "reject": P.reject}[action]
            return _phys_short(await run(fn, t, setup))
        if action == "apply":
            return await run(P.apply, t, id)
    except G.GameError as e:
        raise ToolError(str(e))
    raise ToolError("action = setup | list | status | approve | reject | apply")


def _audio_short(v: dict) -> dict:
    rep = v.get("report") or {}
    out = {"number": v.get("number"), "status": v.get("status"), "zones": (v.get("plan") or {}).get("zones"),
           "distance_m": {k: (v.get("plan") or {}).get(k) for k in ("min_d", "max_d")}}
    if rep:
        out["report"] = {"verdict": rep.get("verdict"), "passed": f"{rep.get('passed')}/{rep.get('total')}",
                         "checks": [{"check": c["check"], "ok": c["ok"], "note": c["note"]} for c in rep.get("checks", [])],
                         "limits": rep.get("limits"), "numbers": rep.get("numbers")}
    if v.get("status") == "testing":
        out["note"] = "Rendering and measuring in the background (a few seconds); the demos appear on the Audio page."
    if v.get("error"):
        out["error"] = v["error"]
    return out


async def game_audio(ctx: Ctx, action="", words="", plan=None, id="", setup="", **_):
    from ..employee import hire
    from ..gamedesk import audio as A
    from ..gamedesk import service as G
    t = ctx.tenant_id
    if not await asyncio.to_thread(hire.is_hired, t, A.KEY):
        raise ToolError("Spatial Audio Systems Programmer is not hired: hire it in Employees with one tap.")
    if action not in ("list", "status"):
        _owner_only(ctx, "Audio setup")
    run = asyncio.to_thread
    try:
        if action == "setup":
            return _audio_short(await run(A.setup, t, words, plan if isinstance(plan, dict) else None, id))
        if action == "list":
            return {"setups": [_audio_short(v) for v in (await run(A.setups, t, id))[:10]]}
        if action in ("status", "approve", "reject"):
            return _audio_short(await run({"status": A.get, "approve": A.approve, "reject": A.reject}[action], t, setup))
        if action == "apply":
            return await run(A.apply, t, id)
    except G.GameError as e:
        raise ToolError(str(e))
    raise ToolError("action = setup | list | status | approve | reject | apply")


def _haptics_short(v: dict) -> dict:
    rep = v.get("report") or {}
    return {"number": v.get("number"), "status": v.get("status"), "actuator": v.get("actuator_name"),
            "patterns": {k: len(e) for k, e in (v.get("patterns") or {}).items()}, "verdict": rep.get("verdict"),
            "errors": rep.get("errors", []), "warnings": rep.get("warnings", []), "passed": rep.get("passed", []),
            "battery": rep.get("rows"), "drv2605_compile": ((rep.get("kit") or {}).get("drv2605_compile") or {}).get("status")}


async def game_haptics(ctx: Ctx, action="", words="", patterns=None, actuator="phone_lra", id="", set="", **_):  # noqa: A002
    from ..employee import hire
    from ..gamedesk import haptics as H
    from ..gamedesk import service as G
    t = ctx.tenant_id
    if not await asyncio.to_thread(hire.is_hired, t, H.KEY):
        raise ToolError("Haptic Feedback Systems Engineer is not hired: hire it in Employees with one tap.")
    if action not in ("list", "status"):
        _owner_only(ctx, "Haptics")
    run = asyncio.to_thread
    try:
        if action == "make":
            return _haptics_short(await run(H.make, t, words, patterns if isinstance(patterns, dict) else None, actuator, id))
        if action == "list":
            return {"sets": [_haptics_short(v) for v in (await run(H.sets, t, id))[:10]]}
        if action in ("status", "approve", "reject"):
            return _haptics_short(await run({"status": H.get, "approve": H.approve, "reject": H.reject}[action], t, set))
        if action == "apply":
            return await run(H.apply, t, id)
    except G.GameError as e:
        raise ToolError(str(e))
    raise ToolError("action = make | list | status | approve | reject | apply")


def _report_short(v: dict, extra: dict) -> dict:
    rep = v.get("report") or {}
    out = {"number": v.get("number"), "status": v.get("status"), **extra}
    if rep:
        out["report"] = {"verdict": rep.get("verdict"), "passed": f"{rep.get('passed')}/{rep.get('total')}",
                         "checks": [{"check": c["check"], "ok": c["ok"], "note": c["note"]} for c in rep.get("checks", [])]}
    if v.get("status") == "testing":
        out["note"] = "Running in the background (under a minute); the result shows on its page. Do not poll."
    if v.get("error"):
        out["error"] = v["error"]
    return out


async def _pack_tool(ctx: Ctx, mod_name: str, who: str, action: str, ref: str, make, extra) -> dict:
    import importlib
    from ..employee import hire
    from ..gamedesk import service as G
    M = importlib.import_module(f"..gamedesk.{mod_name}", __package__)
    t = ctx.tenant_id
    if not await asyncio.to_thread(hire.is_hired, t, M.KEY):
        raise ToolError(f"{who} is not hired: hire it in Employees with one tap.")
    if action not in ("list", "status"):
        _owner_only(ctx, who)
    run = asyncio.to_thread
    try:
        if action == "setup":
            return _report_short(await run(make, M), extra)
        if action == "list":
            return {"setups": [_report_short(v, extra) for v in (await run(M.setups, t, ""))[:10]]}
        if action in ("status", "approve", "reject"):
            v = await run({"status": M.get, "approve": M.approve, "reject": M.reject}[action], t, ref)
            return _report_short(v, extra | ({"demo": v.get("demo")} if v.get("demo") else {}))
        if action == "apply":
            return await run(M.apply, t, ref)
    except G.GameError as e:
        raise ToolError(str(e))
    raise ToolError("action = setup | list | status | approve | reject" + (" | apply" if mod_name in ("xr", "sim") else ""))


async def game_net(ctx: Ctx, action="", words="", inputs=None, id="", setup="", **_):
    return await _pack_tool(ctx, "netcode", "Multiplayer Network Programmer", action, setup,
                            lambda M: M.setup(ctx.tenant_id, words, inputs if isinstance(inputs, dict) else None, id),
                            {"hosting": "her own cloud - Hoola hosts no game server", "in_game": "not yet (the game cannot open sockets)"})


async def game_xr(ctx: Ctx, action="", words="", settings=None, id="", setup="", **_):
    return await _pack_tool(ctx, "xr", "AR / VR Interaction Engineer", action, setup if action != "apply" else id,
                            lambda M: M.setup(ctx.tenant_id, words, settings if isinstance(settings, dict) else None, id),
                            {"headset_fps": "not measured here (no headset)"})


async def game_sim(ctx: Ctx, action="", words="", kind="", params=None, scenario=None, id="", setup="", **_):
    return await _pack_tool(ctx, "sim", "Simulation Software Engineer", action, setup if action != "apply" else id,
                            lambda M: M.setup(ctx.tenant_id, words, kind, params if isinstance(params, dict) else None,
                                              scenario if isinstance(scenario, dict) else None, id),
                            {"note_device": "a training aid, not a certified flight training device"})


async def game_twin(ctx: Ctx, action="", words="", model=None, actual=None, setup="", **_):
    out = await _pack_tool(ctx, "twin", "Digital Twin Architect", action, setup,
                           lambda M: M.setup(ctx.tenant_id, words, model if isinstance(model, dict) else None,
                                             actual if isinstance(actual, list) else None),
                           {"read_only": "the twin reads her data and never writes / commands / controls her plant"})
    return out


async def game_vfx(ctx: Ctx, action="", words="", plan=None, setup="", **_):
    return await _pack_tool(ctx, "vfx", "VFX Pipeline Technical Director", action, setup,
                            lambda M: M.setup(ctx.tenant_id, words, plan if isinstance(plan, dict) else None),
                            {"not_here": "Blender / OpenColorIO / OpenUSD are not installed on the server"})


async def game_scenes(ctx: Ctx, action="", id="", words="", name="", **_):
    from ..employee import hire
    from ..gamedesk import scene as SC
    from ..gamedesk import service as G
    from ..gamedesk import studio as S
    t = ctx.tenant_id
    if not await asyncio.to_thread(hire.is_hired, t, KEY):
        raise ToolError("Game Developer is not hired: hire it in Employees with one tap.")
    if action in ("new", "approve", "reject"):
        _owner_only(ctx, "Scenes")
    run = asyncio.to_thread
    try:
        if not id:
            mine = await run(S.studios, t)
            if len(mine) != 1:
                raise ToolError("Which project? Give the id (S-0001).")
            id = mine[0]["id"]
        if action == "list":
            v = await run(SC.view, t, id)
            return {"scenes": [{k: x[k] for k in ("name", "file", "status", "nodes")} for x in v["scenes"]],
                    "in_the_game": v["in_the_game"], "how": v["how"], "not_built": v["not_built"]}
        if action == "new":
            if len(str(words or "").strip()) < 3:
                raise ToolError("Describe the scene in one line.")
            return await run(SC.propose, t, id, words, name)
        if action == "approve":
            return await run(SC.approve, t, id, name)
        if action == "reject":
            return await run(SC.reject, t, id, name)
    except G.GameError as e:
        raise ToolError(str(e))
    raise ToolError("action = list | new | approve | reject")


async def game_provenance(ctx: Ctx, action="", id="", **_):
    from ..employee import hire
    from ..gamedesk import provenance as P
    from ..gamedesk import service as G
    from ..gamedesk import studio as S
    t = ctx.tenant_id
    if not await asyncio.to_thread(hire.is_hired, t, KEY):
        raise ToolError("Game Developer is not hired: hire it in Employees with one tap.")
    run = asyncio.to_thread
    try:
        if not id:
            mine = await run(S.studios, t)
            if len(mine) != 1:
                raise ToolError("Which project? Give the id (S-0001).")
            id = mine[0]["id"]
        if action == "sheet":
            v = await run(P.sheet, t, id)
            return {"studio": v["studio"], "title": v["title"], "code": v["code"],
                    "assets": v["assets"]["counts"] | {"procedural_warning": v["assets"]["procedural_warning"]},
                    "human": v["human"]["counts"] | {"why_it_matters": v["human"]["why_it_matters"],
                                                     "thin_warning": v["human"]["thin_warning"]},
                    "disclosure": v["disclosure"], "steam": v["steam"]}
        if action == "steam":
            return await run(P.steam_survey, t, id)
        if action == "disclosure":
            return await run(P.disclosure_line, t, id)
        if action == "human":
            return await run(P.human_record, t, id)
    except G.GameError as e:
        raise ToolError(str(e))
    raise ToolError("action = sheet | steam | disclosure | human")


async def game_arena(ctx: Ctx, action="", n=8, seed=1, budget_inr=0, note="", id="", a="", b="", genre="",
                     brief="", rival="", url="", **_):
    from ..gamedesk import arena as A
    from ..gamedesk import service as G
    _owner_only(ctx, "Arena")
    if ctx.tenant_id != "default":
        raise ToolError("The Arena is for the owner only.")
    run = asyncio.to_thread
    try:
        if action == "status":
            return {"runs": [{k: r[k] for k in ("number", "id", "version", "seed", "n", "status", "summary")}
                             for r in await run(A.runs, 12)], "set": A.SET_V, "total_briefs": len(A.brief_set()),
                    "duels": await run(A.duel_table)}
        if action == "briefs":
            return await run(A.catalogue, genre, 30)
        if action == "start":
            return await run(A.start, int(n or 8), int(seed or 1), float(budget_inr or 0), note) | {
                "note": "Runs in the background, one game at a time; it stops at its rupee ceiling. Do not poll - look at the Arena page."}
        if action == "run":
            v = await run(A.view, id)
            return {k: v[k] for k in ("number", "status", "version", "seed", "n", "summary")} | {
                "items": [{k: it.get(k) for k in ("brief", "genre", "playable", "started", "responds", "reached_end",
                                                  "fps", "errors", "sameness", "inr")} for it in v["items"]]}
        if action == "stop":
            return await run(A.stop, id)
        if action == "compare":
            return await run(A.compare, a, b)
        if action == "duel":
            return await run(A.duel, brief, rival, url)
    except G.GameError as e:
        raise ToolError(str(e))
    raise ToolError("action = status | briefs | start | run | stop | compare | duel")


async def game_bigstudio(ctx: Ctx, action="", project="", engine="", title="", engine_version="", about="", module="",
                         detail="", task="", note="", **_):
    from ..employee import hire
    from ..gamedesk import bigstudio as B
    from ..gamedesk import service as G
    t = ctx.tenant_id
    if not await asyncio.to_thread(hire.is_hired, t, KEY):
        raise ToolError("Game Developer is not hired: hire it in Employees with one tap.")
    if action in ("new_project", "add_task", "reopen"):
        _owner_only(ctx, "Studio project")
    run = asyncio.to_thread
    try:
        if action == "projects":
            return {"projects": [{k: p[k] for k in ("number", "engine_name", "title", "engine_version", "counts")} for p in await run(B.projects, t)],
                    "how": "Her editor's Hoola Crew plugin asks for the next task; plugins in the console (Game Desk > Big studio)."}
        if action == "new_project":
            return await run(B.new_project, t, engine, title, engine_version, about, module)
        if action == "add_task":
            return await run(B.add_task, t, project, title, detail)
        if action == "tasks":
            ps = [p for p in await run(B.projects, t) if not project or p["number"] == project.upper() or p["id"] == project]
            if not ps:
                raise ToolError("That studio project was not found.")
            return {"project": ps[0]["number"], "tasks": [{k: x[k] for k in ("number", "title", "status", "rounds", "files")} for x in ps[0]["tasks"]]}
        if action == "task":
            v = await run(B.task, t, project, task)
            pr = v.get("proposal") or {}
            return {k: v[k] for k in ("number", "title", "status", "rounds", "result")} | {
                "why": pr.get("why"), "files": [f["path"] for f in pr.get("files", [])], "checks": pr.get("checks", []),
                "problems": pr.get("problems", []), "manual": pr.get("manual", [])}
        if action == "reopen":
            return await run(B.reopen, t, project, task, note)
    except G.GameError as e:
        raise ToolError(str(e))
    raise ToolError("action = projects | new_project | add_task | tasks | task | reopen")


async def game_liveops(ctx: Ctx, action="", id="", key="", title="", goal="win", variants=None, mde=0.05, ship="",
                       starts="", ends="", set=None, sig="", **_):
    from ..employee import hire
    from ..gamedesk import liveops as L
    from ..gamedesk import service as G
    from ..gamedesk import studio as S
    t = ctx.tenant_id
    if not await asyncio.to_thread(hire.is_hired, t, KEY):
        raise ToolError("Game Developer is not hired: hire it in Employees with one tap.")
    if action in ("experiment_add", "experiment_start", "experiment_stop", "event_add", "event_approve", "event_cancel",
                  "hotfix", "patch_check"):
        _owner_only(ctx, "Live ops")
    run = asyncio.to_thread
    try:
        if not id:
            mine = await run(S.studios, t)
            if len(mine) != 1:
                raise ToolError("Which project? Give the id (S-0001).")
            id = mine[0]["id"]
        if action == "status":
            v = await run(L.view, t, id)
            return {"telemetry": v["telemetry"], "experiments": [{k: x.get(k) for k in ("key", "title", "goal", "status")} for x in v["experiments"]],
                    "events": [{k: e.get(k) for k in ("key", "title", "state", "starts_ist", "ends_ist", "set")} for e in v["events"]],
                    "patches": [{k: p.get(k) for k in ("at", "version", "verdict")} for p in v["patches"]], "how": v["how"]}
        if action == "dashboard":
            return await run(L.dashboard, t, id)
        if action == "experiment_add":
            return await run(L.add_experiment, t, id, key, title, goal, variants if isinstance(variants, list) else None, mde)
        if action == "experiment_start":
            return await run(L.start_experiment, t, id, key)
        if action == "experiment_stop":
            return await run(L.stop_experiment, t, id, key, ship)
        if action == "experiment_result":
            return await run(L.results, t, id, key)
        if action == "event_add":
            return await run(L.add_event, t, id, key, title, starts, ends, set)
        if action == "event_approve":
            return await run(L.approve_event, t, id, key)
        if action == "event_cancel":
            return await run(L.cancel_event, t, id, key)
        if action == "crashes":
            return await run(L.crashes, t, id)
        if action == "hotfix":
            return await run(L.hotfix, t, id, sig)
        if action == "patch_check":
            return await run(L.start_patch_check, t, id) | {"note": "Runs in the background; the result shows on the Live ops page. Do not poll."}
        if action == "money":
            return await run(L.money, t, id)
    except G.GameError as e:
        raise ToolError(str(e))
    raise ToolError("action = status | dashboard | experiment_* | event_* | crashes | hotfix | patch_check | money")


async def game_runtime(ctx: Ctx, action="", id="", on=None, telemetry=None, **_):
    from ..employee import hire
    from ..gamedesk import runtime as R
    from ..gamedesk import service as G
    from ..gamedesk import studio as S
    t = ctx.tenant_id
    if not await asyncio.to_thread(hire.is_hired, t, KEY):
        raise ToolError("Game Developer is not hired: hire it in Employees with one tap.")
    if action in ("replay_test", "set"):
        _owner_only(ctx, "Runtime")
    run = asyncio.to_thread
    try:
        if not id:
            mine = await run(S.studios, t)
            if len(mine) != 1:
                raise ToolError("Which project? Give the id (S-0001).")
            id = mine[0]["id"]
        if action == "status":
            st = await run(R.settings, t, id)
            return {k: st[k] for k in ("on", "telemetry", "kids")} | {"tests": [{k: x.get(k) for k in ("at", "version", "verdict", "deterministic", "frames", "inputs", "errors")} for x in st["tests"][-3:]]}
        if action == "replay_test":
            return await run(R.start_replay_test, t, id) | {"note": "Runs in the background (about half a minute); the result shows on the Runtime page. Do not poll."}
        if action == "telemetry":
            return await run(R.dashboard, t, id)
        if action == "set":
            return await run(R.set_runtime, t, id, on, telemetry)
    except G.GameError as e:
        raise ToolError(str(e))
    raise ToolError("action = status | replay_test | telemetry | set")


GAMEDESK_HANDLERS = {"game_desk": game_desk, "game_studio": game_studio, "game_bible": game_bible, "game_assets": game_assets,
                     "game_qa": game_qa, "game_release": game_release, "game_world": game_world,
                     "game_physics": game_physics, "game_audio": game_audio, "game_haptics": game_haptics,
                     "game_net": game_net, "game_xr": game_xr, "game_sim": game_sim, "game_twin": game_twin,
                     "game_vfx": game_vfx, "game_runtime": game_runtime,
                     "game_liveops": game_liveops, "game_bigstudio": game_bigstudio,
                     "game_arena": game_arena, "game_provenance": game_provenance,
                     "game_scenes": game_scenes}
