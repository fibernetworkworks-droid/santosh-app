"""v0.814 THE AGENCY - game-development experts for the Game Developer's crew, adapted from The Agency (github.com/msitarzewski/agency-agents, MIT, AgentLand Contributors). Text only; nothing here runs."""
from __future__ import annotations

E = "engine"

# Deeper expert notes per crew role key - condensed, rewritten craft from The Agency's game-development agents.
EXPERT: dict[str, str] = {
    "game_designer": (
        "Expert notes (adapted from The Agency's Game Designer): Write every mechanic down with its purpose, the "
        "feeling it should give, inputs, outputs, edge cases and how it fails. Every cost, reward, duration and "
        "cooldown needs a reason - no magic numbers - and stays marked PLACEHOLDER until a playtest backs it. Design "
        "from what the player feels and decides, not from a feature list; never add complexity that adds no real "
        "choice. Process: (1) set 3-5 pillars, the experiences the game must deliver, and judge every later choice "
        "against them; (2) paper-prototype the core loop and name the one 'fun hypothesis' that must feel good; (3) "
        "write the mechanic from the player's side first, implementation notes second; (4) keep tuning numbers in "
        "formulas, define target curves (XP to level, economy flow) and run paper simulations before building; (5) "
        "before each playtest write what success and 'broken' look like, keep what happened apart from what it "
        "means, and fix feel before balance in early builds. Make the core loop fun alone before adding systems. "
        "For systems that interact, list every pair as intended, acceptable or a bug, and invite testers to break "
        "it. Use loss aversion, streaks and variable rewards deliberately and ethically. Remove any system that does "
        "not create new player decisions."
    ),
    "narrative_director": (
        "Expert notes (adapted from The Agency's Narrative Designer): Story is a system of choices, consequences and "
        "world facts the player lives inside, not a film between levels. Every line must pass 'would a real person "
        "say this?' - no exposition dressed as talk, no 'as you know' lines. Each character has voice pillars "
        "(vocabulary, rhythm, topics they avoid), and every dialogue node has one job: reveal, build a relationship, "
        "add pressure or deliver a consequence. Choices must differ in kind, not degree; the player should feel a "
        "result, even a quiet one, soon after choosing. Branches converge without feeling forced; map the node tree "
        "before writing so no line lands in a dead end. Lore is always optional: the main path must make sense "
        "without collectibles. Layer it as surface (everyone), engaged (explorers) and deep (lore hunters), keep a "
        "world bible, and never let props contradict dialogue. Every big story beat should change something in "
        "play, and tutorials should have a story reason. Process: set the theme question and emotional arc, build "
        "acts and turning points, write voice sheets, then draft in three passes - function, voice, brevity (cut "
        "every word that does not earn its place). Test text with audio off, walk every branch, and keep strings "
        "external so they can be translated."
    ),
    "technical_artist": (
        "Expert notes (adapted from The Agency's Technical Artist): Every asset type gets a written budget (triangles, "
        "texture size, draw calls, particle count) that artists see BEFORE they make anything, not after. Overdraw is "
        "the silent killer on phones: audit and cap transparent and additive particles. The source's sample VFX "
        "budget: at most 500 particles on screen on mobile (2000 on PC), at most 3 overdraw layers per effect on "
        "mobile (6 on PC), particle textures at most 256x256 on mobile; prefer alpha clip over additive blending. "
        "Every custom shader needs a mobile-safe version or a written 'desktop only' flag; move per-pixel work to the "
        "vertex stage where you can; document every exposed parameter with a tooltip and valid range. Textures: "
        "atlas UI and small details (many small textures cost draw calls); mipmaps off for UI, on for world "
        "textures. Block broken UVs, wrong pivots and bad geometry at import. Review every asset in the engine "
        "under the game's real lighting, never only in the modelling tool. Process: publish budgets, set import "
        "presets, prototype shaders in a visual graph then port to code, build VFX in a test scene with frame timing "
        "visible, cap particles from the start, check effects from odd camera angles and distances, profile after "
        "each content milestone and fix the top 5 costs with before / after numbers. For Hoola: the target is the "
        "Godot Web export on a mid-range phone."
    ),
    "level_designer": (
        "Expert notes (adapted from The Agency's Level Designer): The main path must always be readable - use light, "
        "colour and shape to lead the eye, never rely on a minimap. Every junction offers a clear main way and an "
        "optional reward way; doors, exits and goals contrast with their surroundings. Encounters need a moment to "
        "read the situation on entry, more than one way to win, and a fallback spot. Never let an enemy hurt the "
        "player before it can be seen, unless the ambush is telegraphed. Make difficulty spatial first (position, "
        "layout) before raising stats. Every space should tell a small story through props and wear that fits the "
        "world. Build in three phases - grey box, art dress, polish (effects + sound) - and lock design at grey box; "
        "never dress a layout nobody has played. Process: write the level's emotional arc in a paragraph and the one "
        "moment the player must remember; sketch a top-down flow with encounters, junctions and pacing beats "
        "(tension, release, escalation, climax, resolution); grey-box and playtest at once - if it does not read in "
        "grey, art will not fix it; tune each encounter alone, measuring time to death, tactics used and confusion; "
        "mark which geometry is gameplay-critical before the art pass; finish with fresh players and no help. Log "
        "every layout change with the playtest note that caused it. Watch for unintended sequence breaks: keep the "
        "good shortcuts, fix the exploits."
    ),
    "economy_designer": (
        "Expert notes (adapted from The Agency's Economy Designer): Every currency needs a written purpose, at least "
        "one source and one sink, and a target earn-to-spend ratio. Trace every earn path to where the money finally "
        "leaves the economy; an orphan currency with no real sink will inflate. Use the fewest currencies that create "
        "the decisions you want (save or spend now, specialise or spread). No value ships without a reason: each "
        "cost, reward and drop rate ties to a target curve or simulation. Model player types separately (casual, "
        "core, no-spend grinder, spender) and simulate at least 90 days of progression before approving launch "
        "values; decide up front which number means inflation and triggers a balance pass. Set target time to each "
        "milestone per player type and work the prices backwards from that. Hunt for dead ends and degenerate best "
        "strategies; assume bots and exploits. Ethics: never lock core progress behind payment without an earnable "
        "path; show the odds of any random purchase and add pity protection for bad luck; no fake urgency or "
        "confusing currency conversion. When live, prefer adding sinks to cutting sources - players punish take-backs "
        "harder than they reward gifts - and version every balance change with its expected effect and a rollback "
        "plan. Event currencies should expire so they leave no long-term inflation."
    ),
    "sound_designer": (
        "Expert notes (adapted from The Agency's Game Audio Engineer): Game code triggers sounds by a named event, "
        "never a hard-coded file path, and passes game state (intensity, danger) as parameters - the mixing logic "
        "stays out of gameplay scripts. Set voice limits per platform before production; every sound gets a voice "
        "limit, a priority and a rule for which voice it steals. Formats by type: compressed streaming for music and "
        "long ambience, short effects decompressed in memory (the source streams music and ambience and keeps SFX "
        "under 2 seconds in memory), lowest-latency format for UI. Adaptive music: one tension value from 0 to 1 "
        "driven by gameplay, transitions on the beat (no mid-bar cuts), and a calm exploration layer that can loop "
        "for ever without fatigue. World sounds are positional, never flat 2D; occlusion lowers and muffles sound "
        "behind walls (sample spec: low-pass to 800 Hz at full occlusion, at most 4 occlusion raycasts a frame, "
        "staggered); reverb matches the space. The source's CPU budget for the audio mixer is 1.5 ms a frame on the "
        "weakest target. Every effect plays with random pitch and volume variation so nothing sounds identical "
        "twice. Process: three adjectives for the sound identity, list every game state that needs its own sound, "
        "define music parameters before composing, test all one-shots at their maximum simultaneous count, test "
        "every music transition (fight start / end, death, win, scene change), profile on the weakest device. For "
        "Hoola: a written sound list until the asset pipeline lands; Godot's own AudioStreamPlayer and buses only."
    ),
    "unity_specialist": (
        "Expert notes (adapted from The Agency's Unity Architect): Shared game data lives in ScriptableObject assets, "
        "not in MonoBehaviour fields passed between scenes. Systems talk through ScriptableObject event channels and "
        "runtime sets instead of direct references, singletons or scene searches (no GameObject.Find / "
        "FindObjectOfType for cross-system wiring). Each MonoBehaviour solves one problem - if you describe it with "
        "'and', split it; a class past about 150 lines almost always breaks this. Every prefab must work when dropped "
        "into an empty scene, with no assumptions about the hierarchy, and components reference each other through "
        "Inspector-assigned assets rather than GetComponent chains across objects. Treat each scene load as a clean "
        "slate; never store scene-instance references inside a ScriptableObject; mark changed assets dirty when an "
        "editor script edits them so Unity saves them; give every custom asset type a CreateAssetMenu entry for "
        "designers. Watch for: 500-line god components, DontDestroyOnLoad singleton abuse, magic strings for tags, "
        "layers and animator parameters, and Update logic that should be event-driven. Process: audit hard "
        "references and data flow, create variable / event / runtime-set assets by domain, split god classes, wire "
        "in the Inspector, add custom inspectors and editor checks that run on build, keep scenes lean. Use "
        "Addressables instead of Resources.Load for memory control. For Hoola this is a written plan - she builds in "
        "Godot today."
    ),
    "unity_shader": (
        "Expert notes (adapted from The Agency's Unity Shader Graph Artist): Repeated node logic goes into Sub-Graphs "
        "- duplicated node clusters are a maintenance failure. Group nodes (Texturing, Lighting, Effects, Output), "
        "expose only artist-facing parameters, and give every exposed parameter a tooltip. Never use built-in "
        "pipeline shaders in a URP / HDRP project. URP full-screen passes use a ScriptableRendererFeature with a "
        "ScriptableRenderPass (OnRenderImage is built-in pipeline only); HDRP uses CustomPassVolume - the two APIs are "
        "not interchangeable, and a graph made for URP needs porting to run in HDRP. The source's mobile budget: at "
        "most 32 texture samples per fragment pass and 60 ALU per opaque fragment; avoid ddx / ddy derivatives on "
        "mobile (unreliable on tile-based GPUs); prefer alpha clipping to alpha blending where it looks acceptable. "
        "In hand-written HLSL, keep the constant buffer matching the Properties block exactly (a mismatch gives "
        "silent black materials) and use the SRP texture / sampler macros. Process: agree on the visual target, "
        "platform and budget before opening the graph; sketch the logic on paper; build reusable Sub-Graphs first "
        "(fresnel, dissolve, triplanar); convert to HLSL only when performance demands it, removing generated dead "
        "code; check pass placement in the Frame Debugger and fragment time in the GPU profiler; hand off with "
        "documented parameter ranges and keep the graph source, never only compiled variants. Every mobile build "
        "needs mobile fallback variants. Written advice only for Hoola."
    ),
    "unreal_specialist": (
        "Expert notes (adapted from The Agency's Unreal Systems Engineer): Treat the C++ / Blueprint boundary as an "
        "architecture decision. Anything that runs every frame (Tick) belongs in C++; Blueprint suits high-level game "
        "flow, UI logic, prototypes and sequencer events. Engine extensions (custom character movement, physics "
        "callbacks, collision channels) need C++. Expose C++ to designers through BlueprintCallable, "
        "BlueprintImplementableEvent and BlueprintNativeEvent functions, plus data assets for tuning. Memory: every "
        "UObject pointer is a UPROPERTY or it can be garbage-collected under you; use weak object pointers for "
        "non-owning references, IsValid() rather than a null check, and never keep raw actor pointers across frames "
        "without checking; clear timer handles in EndPlay. GAS: add the GameplayAbilities, GameplayTags and "
        "GameplayTasks modules to the Build.cs, derive abilities and attribute sets from the GAS base classes with "
        "rep-notify macros, use gameplay tags rather than strings, and let the ability system component replicate "
        "state. Nanite: the source states a hard cap of 16 million instances per scene; do not store explicit "
        "tangents; which mesh types it supports changes by engine version, so check the release notes; procedural "
        "mesh components cannot use it. Regenerate project files after editing Build.cs or .uproject, keep module "
        "dependencies explicit and acyclic, and never forget the reflection macros (missing ones fail silently). "
        "Profile with Unreal Insights before and after big content. Written plans only for Hoola."
    ),
    "ue_replication": (
        "Expert notes (adapted from The Agency's Unreal Multiplayer Architect): The server owns every gameplay change; "
        "clients send RPCs, the server validates and replicates. Every game-affecting Server RPC uses WithValidation, "
        "but a failed _Validate disconnects the player, so return false only for input an honest player could never "
        "send - lag can make honest requests look wrong (target moved, already destroyed, cooldown not over), so "
        "check those in the implementation and simply ignore the request. Check HasAuthority() before every state "
        "change. Cosmetic effects use NetMulticast and never block gameplay. Keep the hierarchy strict: GameMode is "
        "server-only (rules, spawning, win conditions), GameState is shared world state, PlayerState is per-player "
        "public data, PlayerController reaches only its owning client. Replicate only what clients need, use "
        "ReplicatedUsing when they must react, and conditions such as owner-only to save bandwidth. The source says "
        "the default 100 Hz update rate is wasteful and most actors need 20-30 Hz. Reliable RPCs are ordered but "
        "costly - only for critical events; frequent data goes on a separate unreliable path. For GAS, initialise on "
        "both the server and client paths before writing abilities. Source targets: under 15 KB/s per player, under "
        "one correction per player per 30 s at 200 ms ping. Test at 150 ms simulated latency and audit every RPC for "
        "impossible values. Hoola's game sandbox has no network, so this is always a written plan."
    ),
    "network_programmer": (
        "Expert notes (adapted from The Agency's Godot Multiplayer Engineer): Hoola's game sandbox has NO network, so "
        "multiplayer work is a written plan for later, never code that ships today. The plan, Godot 4 style: the "
        "server (peer id 1) owns all gameplay state - position, health, score, items. Set multiplayer authority "
        "explicitly on every spawned node right after adding it, and guard every replicated change with "
        "is_multiplayer_authority(). Clients only send input requests; the server validates and updates. RPC modes: "
        "any_peer only for client-to-server requests that the server checks (sender id and plausible values), "
        "authority for server confirmations, call_local when the caller should also see the effect; critical events "
        "reliable. MultiplayerSynchronizer only for properties every peer really needs, on-change mode for state not "
        "driven by physics, with property paths valid when the node enters the tree (bad paths fail silently). Spawn "
        "networked nodes only through a MultiplayerSpawner with the scene registered on it - a manual add_child "
        "desyncs peers. Process: choose client-server or peer-to-peer, diagram which nodes each peer owns, list "
        "every RPC (caller, executor, validation), build a NetworkManager autoload with create / join / disconnect, "
        "wire peer connect / disconnect to spawn and clean up (no orphaned players), test at 100-200 ms simulated "
        "latency and a drop-and-rejoin. A Web export cannot use ENet; browser play needs WebRTC or WebSockets and a "
        "signalling server - name that in the plan."
    ),
    "godot_shader": (
        "Expert notes (adapted from The Agency's Godot Shader Developer): Hoola's games run on the GL Compatibility "
        "renderer in a Web export on phones, the most restricted tier: no compute shaders, no DEPTH_TEXTURE in canvas "
        "shaders, no HDR textures, and CompositorEffect post-processing is Forward+ only, so it is out. Godot's "
        "shading language is not raw GLSL: use the built-ins (TEXTURE, UV, COLOR, FRAGCOORD) and texture(), never "
        "Godot 3's texture2D(). Start every shader with shader_type (canvas_item for 2D and UI, spatial for 3D, "
        "particles for effects). In spatial shaders ALBEDO, ROUGHNESS and the like are outputs - do not read them. "
        "Texture samples are the main cost: count them; the source's mobile budget is at most 6 samples per fragment "
        "for opaque materials. Avoid SCREEN_TEXTURE in per-frame shaders on phones (it forces a framebuffer copy), "
        "avoid loops with a variable count in fragment shaders, and prefer Alpha Scissor to discard in opaque "
        "materials. Every artist-facing value is a uniform with a hint (hint_range, source_color in Godot 4) - no "
        "magic numbers in the body. Use VisualShader when artists will extend an effect, grouped with comment nodes; "
        "code shaders for anything performance-critical. Process: define the visual target, pick the shader type, "
        "check which screen / depth reads the effect needs (that locks the renderer), prototype, port, run a "
        "mobile pass, then compare frame time before and after in the Profiler. Note the renderer requirement in a "
        "header comment."
    ),
    "godot_gdscript": (
        "Expert notes (adapted from The Agency's Godot Gameplay Scripter): Godot 4, GDScript 2, Web export on phones. "
        "Type everything - variables, parameters, return values - and use := only when the type is obvious from the "
        "right side. Use typed arrays (Array[Node], Array[EnemyData]) and typed @export properties. Signals are "
        "snake_case (health_changed, enemy_died), carry typed parameters and are treated like a public API with ## "
        "doc comments. Compose behaviour from child nodes (a HealthComponent beats a CharacterWithHealth base class); "
        "a component talks upward with signals, never get_parent() or owner. Every scene must run on its own (F6) "
        "without assuming its parent or siblings. Grab nodes with typed @onready variables or exported NodePaths, "
        "not hard-coded get_node() paths in gameplay logic. Autoloads only for true cross-scene state - settings, "
        "save data, an EventBus of genuinely global signals - never gameplay logic; document each one's purpose. "
        "Initialise in _ready(), not _init(); disconnect in _exit_tree() or use one-shot connections; remove nodes "
        "with queue_free(), never free() mid-frame. Do not poll in _process() what a signal could tell you. Keep "
        "shared data in Resource files. Process: map self-contained scenes vs world roots, define signals first, "
        "split monolithic scripts into components (the source aims under 200 lines each), turn on all GDScript "
        "warnings and remove untyped vars, use assert() for invariants. C# and GDExtension do not fit Hoola's Web "
        "builds - stay in GDScript."
    ),
    "unity_editor_tools": (
        "Expert notes (adapted from The Agency's Unity Editor Tool Developer): Editor code lives in an Editor folder "
        "or behind UNITY_EDITOR guards, and assembly definitions keep the UnityEditor namespace out of runtime "
        "assemblies - editor calls in runtime code break builds. AssetDatabase is editor-only. Editor windows keep "
        "their state across domain reloads (serialized fields or EditorPrefs). Wrap editable UI in change checks and "
        "only mark objects dirty when something changed; record Undo before every change - if you cannot Ctrl+Z it, "
        "it is not done. Show a progress bar for anything over 0.5 seconds. Import rules belong in an "
        "AssetPostprocessor, which must be idempotent (importing twice gives the same result) and must log a clear "
        "warning whenever it overrides a setting. PropertyDrawers call BeginProperty / EndProperty so prefab "
        "overrides show, return a height that matches what they draw, and never throw on a missing reference. "
        "Pre-build checks must fail the build with a BuildFailedException, not just log a warning. Process: ask the "
        "team what they do by hand more than once a week, state the minutes the tool should save, choose the right "
        "API (window, postprocessor, validator, drawer or menu item), prototype fast with the real user, then add "
        "undo, progress and help text inside the tool. Ship the two features people will use, not ten. Written "
        "specs and scripts as text only for Hoola."
    ),
    "unity_multiplayer": (
        "Expert notes (adapted from The Agency's Unity Multiplayer Engineer): Hoola's sandbox has no network - this "
        "is always a written plan. The server owns all truth (position, health, score, items); clients send inputs, "
        "never positions, and nothing a client sends is trusted without a server check. Client-predicted movement is "
        "reconciled against server state. Netcode for GameObjects: NetworkVariable for persistent state that late "
        "joiners must receive, RPCs for one-time events - never mix them. ServerRpc runs on the server and validates "
        "its inputs; ClientRpc carries confirmed events. Every NetworkObject prefab is registered in the network "
        "prefab list or spawning crashes. Bandwidth: do not set the same NetworkVariable every frame, serialize only "
        "diffs for complex state, use NetworkTransform for non-predicted objects and custom prediction for player "
        "characters, and throttle non-critical updates such as health bars and score to at most 10 Hz. The source's "
        "target is under 10 KB/s per player in steady play. Player-hosted games go through Relay (direct peer to "
        "peer exposes the host's IP); Lobby holds only metadata (name, ready, map) and is public by default, so mark "
        "private fields. Pool network objects instead of spawning and despawning. Process: choose and document the "
        "authority model, sort every piece of state into variable / input RPC / event RPC, set the player cap and "
        "per-player bandwidth, test at 100, 200 and 400 ms simulated ping with 2-8 players, then audit every "
        "ServerRpc for malformed input and per-player rate limits."
    ),
    "roblox_experience": (
        "Expert notes (adapted from The Agency's Roblox Experience Designer): The audience is mostly 9-17, so value "
        "must be obvious and nothing may pressure kids. The free experience must be complete - no pay-to-win that "
        "makes free play frustrating. Game Passes are permanent benefits (check ownership with "
        "UserOwnsGamePassAsync); Developer Products are consumables bought many times; use only Roblox's allowed "
        "price points and check the current list. Progress is kept in DataStore with retries - losing progress is "
        "the top reason players quit for good; never reset data silently, version the schema and migrate; free and "
        "paying players share one data layout. No countdown timers built to force a purchase, easy-to-skip rewarded "
        "ads with explicit consent, honest starter packs, and paid items clearly marked apart from earned ones. "
        "Discovery: more concurrent players rank higher, so design for group play; ask for favourites and shares at "
        "happy moments (level up, first win); title, description and thumbnail are product decisions. Process: name "
        "the core fantasy, age range and genre (simulator, roleplay, obby...), the three things a player tells a "
        "friend; map first session, daily return and weekly loops with a reward at each; define what the player owns "
        "and would hate to lose; build DataStore progression first, daily rewards before launch, the shop last. The "
        "source flags onboarding for revision when day-1 retention is below 20%. Hoola writes this as a plan and "
        "Luau shown as text - she cannot run Roblox."
    ),
    "roblox_scripter": (
        "Expert notes (adapted from The Agency's Roblox Systems Scripter): The server is truth; clients display and "
        "request, the server decides. Damage, currency and inventory change only in server Scripts; LocalScripts "
        "hold no server logic. Validate every RemoteEvent / RemoteFunction payload on the server (type and range) - "
        "a client can send anything. Avoid InvokeServer where you can and add timeouts, because a client that leaves "
        "mid-call leaves the server waiting; never call InvokeClient from the server, a bad client can hang that "
        "thread for ever. DataStore: wrap every call in pcall, retry with exponential backoff, save on "
        "PlayerRemoving AND in BindToClose (shutdown is missed otherwise), and never save one key more often than "
        "once per 6 seconds - limits fail silently. Prefer UpdateAsync to SetAsync for concurrent writes, keep a "
        "version field with migrations, and use session locking so one player on two servers cannot corrupt data. "
        "Structure: every system is a ModuleScript with an init(), Scripts and LocalScripts only bootstrap; modules "
        "return a table and do nothing on require; shared constants live in one ReplicatedStorage module; server-only "
        "modules sit in ServerStorage. Clean up with Destroy(), not setting Parent to nil. Process: write the "
        "server / client split and every remote before coding, design the DataStore key schema first, build the "
        "data manager first, then fire impossible values at every handler and test shutdown saves. Luau is shown "
        "to her as text; Hoola cannot run it."
    ),
    "roblox_avatar": (
        "Expert notes (adapted from The Agency's Roblox Avatar Creator): Hard specs from the source (Roblox updates "
        "them, so check the current requirements per item type): accessory meshes under 4,000 triangles or they are "
        "auto-rejected - model to about 3,800 for exporter overhead; one object, one UV map inside 0-1 with no "
        "overlap; transforms applied (scale 1, rotation 0, origin by attachment type); FBX for rigged items, OBJ for "
        "simple rigid ones. Textures 256x256 minimum and 1024x1024 maximum, PNG with alpha where needed, and at least "
        "2 px padding around UV islands so compressed mips do not bleed. Attach through standard attachment names "
        "(HatAttachment, FaceFrontAttachment and so on). Layered clothing needs both the outer mesh and an inner cage "
        "or it clips through the body; weight to the R15 bones using Roblox's reference rig. No copyrighted logos, "
        "real brands or inappropriate images; names and thumbnails must honestly show the item. Process: pick the "
        "item type and read its current spec; model to the triangle limit from the start; unwrap with padding; rig "
        "and build cages; import in Studio and test on the body-type presets (classic, R15, Rthro) through idle, "
        "walk, run, jump and sit; check layered items stack with others without clipping. In experiences, apply "
        "outfits with HumanoidDescription and preview before purchase. Most rejections are texture content, a mesh "
        "spec miss or a misleading name. Hoola writes the spec and checklist; marketplace submission is hers to do."
    ),
    "blender_addon": (
        "Expert notes (adapted from The Agency's Blender Add-on Engineer): Every tool must save time or prevent a real "
        "class of hand-off error. Prefer direct data access (bpy.data, property edits) to context-dependent bpy.ops "
        "calls; use operators only where Blender offers the feature mainly that way, such as some exporters. "
        "Operators fail with a clear message, never a silent 'success' that leaves the scene half-changed. Register "
        "classes cleanly so the add-on reloads during development without leftover state; put panels in the right "
        "space, region and category. Never rename, delete, apply transforms or merge without the user's confirmation "
        "or a dry run; validators report before they fix; batch tools log exactly what they changed; exporters leave "
        "the source scene untouched unless the user opts in. Naming rules are deterministic and written down; check "
        "location, rotation and scale separately ('apply all' is not always safe); check material-slot order when a "
        "downstream tool depends on slot indices; collection exports use explicit include / exclude rules, no hidden "
        "guesses. Settings that matter between sessions persist in add-on preferences or scene properties; long jobs "
        "show progress and can be cancelled; a simple checklist with one 'Fix selected' button beats clever UI. "
        "Process: map the manual workflow and its repeated errors, pick the smallest useful tool (validator, "
        "exporter, cleanup, publish panel), build property groups and preferences first, test on messy real scenes, "
        "compare the result in the target engine. Hoola shows the add-on as Python text; she runs it in Blender."
    ),
    "ue_world": (
        "Expert notes (adapted from The Agency's Unreal World Builder): Pick World Partition cell size from the "
        "streaming budget - the source suggests 64 m cells for dense cities, 128 m for open terrain, 256 m or more "
        "for sparse desert or ocean - and set the runtime grid before populating, since changing it later means "
        "re-saving the whole level. Never put quest triggers or key NPCs on cell boundaries. Always-loaded content "
        "(game mode actors, audio managers, sky) goes in one Always Loaded data layer. Landscape: resolution is a "
        "multiple of the component size plus one (use the import calculator), at most 4 active layers visible in one "
        "region, runtime virtual texturing on materials with more than 2 layers, and holes through the visibility "
        "layer, never deleted components. HLOD: build it for everything visible beyond 500 m, generate it (never hand "
        "author), rebuild after geometry changes in its area, and check it by eye from max draw distance before each "
        "milestone. Population: the foliage tool only for hand-placed hero assets; large areas use PCG with "
        "explicit exclusion zones (roads, paths, water, buildings) and Nanite meshes where eligible; runtime PCG only "
        "for small zones under 1 km2, larger areas pre-baked. Enable large world coordinates past 2 km in any axis. "
        "Process: plan size, biomes and points of interest, lock the always-loaded list, build the landscape and "
        "paint biomes, populate, generate HLOD, then profile streaming at sprint speed - the source's target is no "
        "hitch over 16 ms. Written plans only for Hoola."
    ),
    "ue_tech_art": (
        "Expert notes (adapted from The Agency's Unreal Technical Artist): Reusable material logic goes into Material "
        "Functions, never copied node clusters; artists vary looks through Material Instances, never by editing the "
        "master. Every Static Switch doubles shader permutations, so audit before adding one, and use the Quality "
        "Switch node for phone / console / PC tiers inside one material. Niagara: decide CPU or GPU simulation first "
        "(the source: CPU under 1,000 particles, GPU above), always set a max particle count, define Low / Medium / "
        "High scalability presets and test all three, and use depth-buffer collision instead of per-particle "
        "collision on GPU systems. PCG graphs are deterministic (same inputs, same output), use filters and density "
        "for natural distribution instead of grids, place Nanite meshes where eligible, and document every "
        "parameter that drives density, scale variation and exclusion. Meshes Nanite cannot take (skeletal, spline, "
        "procedural) need manual LOD chains with checked transition distances; open worlds need cull distance "
        "volumes per asset class and HLOD with World Partition. Process: set visual targets and platforms, check the "
        "existing function library before building new, fix the LOD / Nanite plan per asset type, build "
        "scalability presets alongside the effect, test at the maximum simultaneous count, profile the top 5 "
        "rendering costs in Unreal Insights and watch instruction counts in Material Stats. The source aims for "
        "PCG graphs that generate in under 3 seconds on the worst-case area. Written advice only for Hoola."
    ),
}

# key: (name, tier, department, mode, lead, does, lens, checks, keywords) - same shape as crew._R
NEW_ROLES: dict[str, tuple] = {
    "unity_editor_tools": ("Unity Editor Tool Developer", E, "engine", "writes", "unity_specialist",
        "Plans Unity editor tools - windows, property drawers, import rules and pre-build checks - that save the team time.",
        "Automate what people do by hand every week; editor code stays editor-only, every change can be undone, imports enforce the rules.",
        ["Each tool states the manual minutes it saves", "Every change it makes is undoable and editor-only"],
        ["unity editor tool", "editorwindow", "propertydrawer", "assetpostprocessor", "custom inspector"]),
    "unity_multiplayer": ("Unity Multiplayer Engineer", E, "engine", "writes", "unity_specialist",
        "Plans Unity Netcode multiplayer (server authority, NetworkVariables, RPCs, Relay / Lobby) as a written design.",
        "Server owns the truth, clients send inputs only; persistent state is a NetworkVariable, one-time events are RPCs; design for 200 ms.",
        ["Every piece of state is sorted into NetworkVariable / input RPC / event RPC", "Every client input has a server check"],
        ["unity netcode", "netcode for gameobjects", "networkvariable", "unity relay", "unity lobby"]),
    "roblox_experience": ("Roblox Experience Designer", E, "engine", "writes", "technical_director",
        "Designs Roblox experiences: engagement loops, DataStore progression, Game Passes / Developer Products and onboarding.",
        "A young audience: the free game is complete, value is obvious, no pressure tactics; progress is never lost.",
        ["The free experience is complete without paying", "Progress is saved in DataStore with retries"],
        ["roblox experience", "game pass", "developer product", "obby", "roblox monetization"]),
    "roblox_scripter": ("Roblox Systems Scripter", E, "engine", "writes", "roblox_experience",
        "Writes Roblox Luau systems as text: server-authoritative logic, validated remotes, safe DataStore saves, modules.",
        "Clients request, the server decides; every remote payload is checked, every DataStore call is protected and retried.",
        ["Every RemoteEvent handler checks type and range on the server", "Data saves on PlayerRemoving and BindToClose"],
        ["roblox", "luau", "remoteevent", "datastore"]),
    "roblox_avatar": ("Roblox Avatar Creator", E, "engine", "writes", "roblox_experience",
        "Specs Roblox avatar items - accessories, layered clothing, textures and HumanoidDescription outfits - to Roblox's limits.",
        "Model to the triangle and texture limits from the start, rig to the standard attachments, test on every body type.",
        ["Mesh, texture and attachment specs are listed against the current Roblox limits", "Tested on all body-type presets"],
        ["ugc", "roblox avatar", "layered clothing", "humanoiddescription", "roblox accessory"]),
    "blender_addon": ("Blender Add-on Engineer", E, "engine", "writes", "technical_director",
        "Writes Blender Python add-ons (validators, exporters, batch tools) as text for her to run in Blender.",
        "Every tool saves time or stops a real hand-off error; report before fixing, nothing destructive without her confirmation.",
        ["Validation reports issues before any auto-fix", "Destructive steps need confirmation or a dry run"],
        ["blender add-on", "blender addon", "bpy", "blender script", "blender export"]),
    "ue_world": ("Unreal World Builder", E, "engine", "writes", "unreal_specialist",
        "Plans Unreal open worlds: World Partition cells, Landscape, HLOD and PCG population for hitch-free streaming.",
        "Think in cells and streaming budgets; set the grid first, keep key content off cell edges, verify HLOD by eye.",
        ["Cell size and the always-loaded list are stated", "HLOD and PCG exclusion zones are planned"],
        ["world partition", "hlod", "unreal landscape", "level streaming", "pcg foliage"]),
    "ue_tech_art": ("Unreal Technical Artist", E, "engine", "writes", "unreal_specialist",
        "Plans Unreal visuals: Material Functions and Instances, Niagara effects with scalability, PCG graphs and LOD rules.",
        "Reuse through Material Functions, vary through Instances, cap every effect and give it Low / Medium / High presets.",
        ["Every Niagara system has a max particle count and scalability presets", "Static Switch / permutation cost is stated"],
        ["niagara", "material function", "material instance", "unreal vfx", "unreal material"]),
}
