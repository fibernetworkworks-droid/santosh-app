"""v0.406 HOOLA GAME CREW - a whole game studio's roles inside the Game Developer's desk (owner: "USE THIS FOR HOOLA
GAMING DEVELOPMENT", after studying Claude-Code-Game-Studios; ideas only, see THIRD_PARTY_NOTICES.md).

57 roles in four tiers (49 + 8 engine roles from The Agency in v0.814) - 3 directors, 8 department leads, 23
specialists, 23 engine specialists (Godot / Unity / Unreal / Roblox / Blender). Each role is DATA: what it does, how it thinks (`lens`, added to the model call when it works), what it
checks (`checks`, which become a task's acceptance criteria), who reviews it (`lead`), and whether it can BUILD in
Hoola today:
- builds  = changes the game itself (Godot 4 GDScript, Web export) through the usual pipeline;
- writes  = produces a written result (a spec, checklist, store text, sound list...) that waits for her OK - for work
            Hoola cannot build yet (audio files: asset pipeline, Phase 4; network play: the game sandbox has no
            network; Unity / Unreal: big-studio mode, Phase 10).
Nothing here decides for her: reviews and gates ADVISE, her OK closes a task."""
from __future__ import annotations

import re
from typing import Any

D, L, S, E = "director", "lead", "specialist", "engine"

# key: (name, tier, department, mode, lead, does, lens, checks, keywords)
_R: dict[str, tuple] = {
    # ---------------------------------------------------------------- directors
    "creative_director": ("Creative Director", D, "direction", "writes", "",
        "Guards the vision: pillars, tone, the feeling the game must give.",
        "Judge every change against the game's pillars and audience; cut what does not serve them.",
        ["The change serves at least one pillar of the game", "Tone and look match the Game Bible style"],
        ["vision", "pillar", "tone", "feel of the game", "creative"]),
    "technical_director": ("Technical Director", D, "direction", "writes", "",
        "Owns the technical health: architecture, performance budgets, risk.",
        "Prefer simple, data-driven code that stays fast on a mid-range phone; name the technical risk.",
        ["No new performance risk on a mid-range phone", "Code stays data-driven (numbers from the Game Bible)"],
        ["architecture", "technical risk", "tech debt", "refactor"]),
    "producer": ("Producer", D, "direction", "writes", "",
        "Owns scope, order and dates: what ships in which milestone.",
        "Keep tasks small and in order; flag scope creep and slipping milestones.",
        ["Fits the current milestone's scope", "Has a clear finish line"],
        ["scope", "schedule", "milestone", "deadline", "plan"]),
    # ---------------------------------------------------------------- leads
    "game_designer": ("Game Designer", L, "design", "builds", "creative_director",
        "Designs mechanics, rules, the core loop and difficulty.",
        "Make the rule clear in one sentence, teach it in play, keep the loop tight and fair.",
        ["The new rule is explained or obvious in play", "Difficulty stays fair in the first two minutes"],
        ["mechanic", "rule", "core loop", "gameplay", "difficulty", "power-up", "power up", "combo"]),
    "lead_programmer": ("Lead Programmer", L, "programming", "builds", "technical_director",
        "Owns code quality and structure across the game.",
        "Small clear functions, no copy-paste, delta-time movement, no allocations every frame.",
        ["Builds and plays without script errors", "No new nodes or arrays created every frame"],
        ["code quality", "clean up code", "restructure", "bug"]),
    "art_director": ("Art Director", L, "art", "builds", "creative_director",
        "Owns the visual identity: palette, shapes, readability.",
        "Every colour from the palette; the player, hazards and rewards read apart at a glance.",
        ["Every colour comes from the Bible palette", "Player, danger and rewards are easy to tell apart"],
        ["look", "visual", "colour", "color", "art style", "palette"]),
    "audio_director": ("Audio Director", L, "audio", "writes", "creative_director",
        "Owns the sound identity: music mood, sound list, mix rules.",
        "Every action the player takes gets feedback; list sounds by moment, loudness and length.",
        ["Every player action has a planned sound", "Music mood matches the game's tone"],
        ["sound", "music", "audio", "sfx"]),
    "narrative_director": ("Narrative Director", L, "narrative", "writes", "creative_director",
        "Owns story, world and characters' consistency.",
        "Keep names, places and events consistent with the Game Bible; short lines a player actually reads.",
        ["Names and facts match the Game Bible", "Story beats are short and skippable"],
        ["story", "narrative", "plot", "lore"]),
    "qa_lead": ("QA Lead", L, "qa", "writes", "producer",
        "Owns the test plan and what 'done' means.",
        "Every criterion is checkable by a test, a screenshot or her answer; untested is not passed.",
        ["Each acceptance criterion says how it is checked", "The critical path is in the test plan"],
        ["test plan", "qa plan", "regression"]),
    "release_manager": ("Release Manager", L, "release", "writes", "producer",
        "Owns builds that go out: version, checklist, store readiness.",
        "Nothing ships without a green build, notes and her tap; list what could block the release.",
        ["Release checklist covers build, store page and rollback", "Patch notes in player language"],
        ["release", "launch", "store page", "patch notes", "publish"]),
    "localization_lead": ("Localization Lead", L, "localization", "builds", "narrative_director",
        "Owns languages: text in tables, fonts, layouts that fit.",
        "No player text hard-coded; leave room for longer Indian-language strings; fonts cover the script.",
        ["Player-facing text comes from one table", "Longer translations still fit on screen"],
        ["language", "hindi", "translate", "localization", "localisation", "marathi", "tamil"]),
    # ---------------------------------------------------------------- specialists
    "gameplay_programmer": ("Gameplay Programmer", S, "programming", "builds", "lead_programmer",
        "Builds player controls, abilities, scoring, game states.",
        "Read numbers from HoolaBible.DATA, move with delta, keep touch and keyboard both working.",
        ["Works by touch and by keyboard", "Uses Game Bible numbers, not typed-in values"],
        ["player", "control", "jump", "shoot", "score", "ability", "movement", "speed", "health", "lives"]),
    "engine_programmer": ("Engine Programmer", S, "programming", "builds", "lead_programmer",
        "Builds low-level systems: pooling, scene flow, save / load.",
        "Pool and reuse nodes, keep frame time flat, save only to user://.",
        ["Frame rate stays steady as objects grow", "Save / load survives a restart"],
        ["pool", "save", "load game", "performance system", "scene flow"]),
    "ai_programmer": ("AI Programmer", S, "programming", "builds", "lead_programmer",
        "Builds enemy and NPC behaviour: chase, patrol, decisions.",
        "Behaviour as small states with clear switches; tunable numbers in the Bible; never unfair-perfect aim.",
        ["Enemy behaviour matches its Bible behaviour type", "Enemies can be beaten (not perfect aim)"],
        ["enemy ai", "npc", "chase", "patrol", "behaviour", "behavior", "boss"]),
    "network_programmer": ("Network Programmer", S, "programming", "writes", "lead_programmer",
        "Plans multiplayer and online features (the game sandbox has no network yet).",
        "Server decides, client shows; plan messages, cheating and lag before any code.",
        ["Who decides each outcome (server / client) is written down", "Cheating risks are listed"],
        ["multiplayer", "online", "leaderboard", "network", "pvp"]),
    "tools_programmer": ("Tools Programmer", S, "programming", "builds", "lead_programmer",
        "Builds in-game debug tools and helpers for the team.",
        "Debug overlays behind a switch that is off in the player build.",
        ["Debug tools are off by default for players"],
        ["debug", "tool", "cheat menu", "overlay"]),
    "ui_programmer": ("UI Programmer", S, "programming", "builds", "lead_programmer",
        "Builds menus, HUD, buttons and screens.",
        "Big touch targets (48 px+), readable text, UI never owns game state, every screen has a way back.",
        ["Touch targets are at least 48 px", "Text is readable and fits its box"],
        ["menu", "hud", "button", "screen", "ui", "pause", "settings screen"]),
    "systems_designer": ("Systems Designer", S, "design", "builds", "game_designer",
        "Designs connected systems: progression, crafting, upgrades.",
        "Write the formula in the Bible curves first, then the code reads it; check with the balance simulation.",
        ["Numbers come from Bible curves", "Balance simulation shows no new spike"],
        ["progression", "upgrade", "level up", "xp", "crafting", "skill tree", "system"]),
    "level_designer": ("Level Designer", S, "design", "builds", "game_designer",
        "Designs levels, waves, pacing and difficulty curve.",
        "Each level teaches or tests one thing; waves in the Bible; rest moments between hard ones.",
        ["Level is in the Bible with its waves", "First level is winnable by a new player"],
        ["level", "wave", "stage", "map", "pacing"]),
    "economy_designer": ("Economy Designer", S, "design", "builds", "game_designer",
        "Designs coins, prices, rewards and sinks (soft currency only).",
        "Every coin has a source and a sink; check levels-to-afford in the simulation; no real money, no loot boxes.",
        ["Every item is affordable within the game", "No real-money or gambling mechanic"],
        ["coin", "shop", "price", "economy", "reward", "currency"]),
    "technical_artist": ("Technical Artist", S, "art", "builds", "art_director",
        "Makes effects and polish in code: particles, tweens, shaders.",
        "Juice that helps reading the game (hit flash, shake, trails) and stays cheap on phones.",
        ["Effects keep 60 fps on the playtest", "Effects never hide the player or danger"],
        ["effect", "particle", "shader", "glow", "animation", "tween", "juice", "shake"]),
    "sound_designer": ("Sound Designer", S, "audio", "writes", "audio_director",
        "Writes the sound list: each sound, when it plays, how it feels.",
        "One line per sound: moment, feel, length, loudness, variations (files come with the asset pipeline).",
        ["Every sound has a moment, length and loudness", "No two sounds fight for the same moment"],
        ["sound effect", "sfx list", "sound list"]),
    "writer": ("Writer", S, "narrative", "builds", "narrative_director",
        "Writes in-game text: tutorials, item text, dialogue, barks.",
        "Short, warm, in the player's language; names from the Bible; one idea per line.",
        ["Lines are short enough to read in play", "Names match the Game Bible"],
        ["text", "dialogue", "tutorial", "line", "write", "copy"]),
    "world_builder": ("World Builder", S, "narrative", "writes", "narrative_director",
        "Builds the world: places, factions, history (in the Game Bible).",
        "Add to the Bible, never contradict it; every place has a reason to visit.",
        ["New lore does not contradict the Bible"],
        ["world", "faction", "history", "place"]),
    "ux_designer": ("UX Designer", S, "design", "builds", "game_designer",
        "Designs flows: first-time experience, onboarding, menus that make sense.",
        "A new player knows what to do within 5 seconds; fewest taps to play.",
        ["A first-time player knows what to do in 5 seconds", "Play starts within two taps"],
        ["onboarding", "first time", "flow", "ux", "usability"]),
    "prototyper": ("Prototyper", S, "design", "builds", "game_designer",
        "Builds quick throwaway tests of an idea to see if it is fun.",
        "Fastest playable version of the one question being tested; keep, change or drop it.",
        ["The question being tested is written down", "Result is keep / change / drop"],
        ["prototype", "try an idea", "experiment", "test idea"]),
    "performance_analyst": ("Performance Analyst", S, "programming", "builds", "lead_programmer",
        "Measures and fixes speed, memory and download size.",
        "Measure first (fps, load time, MB), change one thing, measure again.",
        ["fps, start time and download size are not worse", "The cause of slowness is named"],
        ["slow", "lag", "fps", "performance", "optimi", "memory", "download size"]),
    "devops_engineer": ("DevOps Engineer", S, "release", "writes", "release_manager",
        "Owns build and deploy steps: versions, builds per platform, rollback.",
        "Every build reproducible from the same code; one-step rollback.",
        ["Build steps are repeatable", "Rollback path is written"],
        ["build pipeline", "deploy", "ci", "platform build"]),
    "analytics_engineer": ("Analytics Engineer", S, "live", "writes", "producer",
        "Plans what to measure: events, funnels, retention (privacy first).",
        "Measure only what answers a question; no personal data; players opt in.",
        ["Each event answers a written question", "No personal data collected"],
        ["analytics", "telemetry", "retention", "funnel", "metrics"]),
    "security_engineer": ("Security Engineer", S, "programming", "writes", "technical_director",
        "Finds cheating, save tampering and data risks.",
        "Assume the player edits the save and the browser; list what that breaks.",
        ["Save tampering effects are listed", "No secret lives in the game code"],
        ["cheat", "security", "tamper", "hack"]),
    "qa_tester": ("QA Tester", S, "qa", "builds", "qa_lead",
        "Plays and breaks the game: edge cases, repro steps, regressions.",
        "Try the odd path: double taps, pause mid-move, restart twice, tiny and huge scores.",
        ["Restart works twice in a row", "No error during 10 seconds of play"],
        ["test", "qa", "edge case", "regression test", "playtest"]),
    "accessibility_specialist": ("Accessibility Specialist", S, "design", "builds", "game_designer",
        "Makes the game playable for more people: contrast, size, motion, colour blindness.",
        "Text contrast 4.5:1, never colour alone, option to reduce shake / flashes.",
        ["Text contrast is at least 4.5:1", "Nothing is shown by colour alone"],
        ["accessib", "colour blind", "color blind", "contrast", "font size", "reduce motion"]),
    "live_ops_designer": ("Live Ops Designer", S, "live", "writes", "producer",
        "Plans events, seasons and updates after launch.",
        "Each event has a goal, a start / end, rewards inside the economy, and no dark patterns.",
        ["Event has goal, dates and rewards", "No pressure tactics on children"],
        ["event", "season", "live ops", "daily reward", "update plan"]),
    "community_manager": ("Community Manager", S, "live", "writes", "producer",
        "Writes for players: store text, posts, replies to feedback.",
        "Honest, warm, short; never promise a date the team has not agreed.",
        ["No promise without a date the team agreed", "Matches the game's tone"],
        ["community", "store description", "post", "player feedback", "review reply"]),
    # ---------------------------------------------------------------- engine specialists
    "godot_specialist": ("Godot Specialist", E, "engine", "builds", "technical_director",
        "Knows Godot 4.7: nodes, scenes, signals, Web export limits.",
        "Use the right node for the job, signals between systems, nothing Web export cannot run.",
        ["Uses Godot 4.7 APIs (no deprecated calls)", "Runs in the Web export"],
        ["godot", "node", "signal", "scene tree", "web export"]),
    "godot_gdscript": ("GDScript Specialist", E, "engine", "builds", "godot_specialist",
        "Writes typed, idiomatic GDScript 2.",
        "Typed variables, await not yield, explicit returns on typed overrides (4.7), no per-frame allocations.",
        ["Typed GDScript, no deprecated syntax", "Typed overrides return on every path"],
        ["gdscript", "script", "typed"]),
    "godot_shader": ("Godot Shader Specialist", E, "engine", "builds", "technical_artist",
        "Writes Godot shaders for the Compatibility renderer (web).",
        "canvas_item / spatial shaders that run on GL Compatibility; cheap on phones.",
        ["Shader runs on the Compatibility (web) renderer", "No big fps drop on the playtest"],
        ["shader", "gdshader", "visual effect shader"]),
    "godot_gdextension": ("GDExtension Specialist", E, "engine", "writes", "godot_specialist",
        "Plans native C++ extensions (not in Hoola's web builds).",
        "Only when GDScript is measured too slow; plan the API and the platforms it must build for.",
        ["The measured reason for native code is written"],
        ["gdextension", "c++ extension", "native module"]),
    "godot_csharp": ("Godot C# Specialist", E, "engine", "writes", "godot_specialist",
        "Advises on Godot C# (Hoola's web builds use GDScript).",
        "Note that Godot C# does not export to the Web; plan GDScript or a desktop build.",
        ["Web export limits of C# are stated"],
        ["c#", "csharp", ".net"]),
    "unity_specialist": ("Unity Specialist", E, "engine", "writes", "technical_director",
        "Advises on Unity 6 projects (Hoola big-studio mode, Phase 10).",
        "Plan scenes, prefabs, ScriptableObjects and data; Hoola builds in Godot today.",
        ["Unity plan names scenes, prefabs and data assets"],
        ["unity"]),
    "unity_dots": ("Unity DOTS Specialist", E, "engine", "writes", "unity_specialist",
        "Advises on Unity DOTS / ECS for very many objects.",
        "Use ECS only where object counts demand it; measure first.",
        ["The object count that needs ECS is stated"],
        ["dots", "ecs", "entities"]),
    "unity_shader": ("Unity Shader / VFX Specialist", E, "engine", "writes", "unity_specialist",
        "Advises on Unity Shader Graph and VFX Graph.",
        "Per-platform cost first; URP vs HDRP choice explained.",
        ["Render pipeline choice is explained"],
        ["shader graph", "vfx graph", "urp", "hdrp"]),
    "unity_addressables": ("Unity Addressables Specialist", E, "engine", "writes", "unity_specialist",
        "Advises on Unity asset loading and memory (Addressables).",
        "Group by when assets load; plan memory per platform.",
        ["Asset groups follow load time"],
        ["addressables", "asset bundle"]),
    "unity_ui": ("Unity UI Toolkit Specialist", E, "engine", "writes", "unity_specialist",
        "Advises on Unity UI Toolkit / uGUI screens.",
        "UI Toolkit for menus, data binding, safe areas on phones.",
        ["Safe areas on phones are handled"],
        ["ui toolkit", "ugui"]),
    "unreal_specialist": ("Unreal Specialist", E, "engine", "writes", "technical_director",
        "Advises on Unreal Engine 5 projects (Hoola big-studio mode, Phase 10).",
        "Plan maps, actors, data assets and the C++ / Blueprint split; Hoola builds in Godot today.",
        ["Unreal plan names maps, actors and data assets"],
        ["unreal", "ue5"]),
    "ue_blueprint": ("Unreal Blueprint Specialist", E, "engine", "writes", "unreal_specialist",
        "Advises on Blueprint logic and when to move it to C++.",
        "Blueprints for flow, C++ for hot paths; keep graphs readable.",
        ["Hot paths named for C++"],
        ["blueprint"]),
    "ue_gas": ("Unreal GAS Specialist", E, "engine", "writes", "unreal_specialist",
        "Advises on Unreal's Gameplay Ability System.",
        "Abilities, effects and attributes as data; tags for states.",
        ["Abilities and attributes listed as data"],
        ["gas", "gameplay ability"]),
    "ue_replication": ("Unreal Replication Specialist", E, "engine", "writes", "unreal_specialist",
        "Advises on Unreal multiplayer replication.",
        "Server-authoritative; replicate only what clients must see.",
        ["Authority for each replicated value stated"],
        ["replication", "unreal multiplayer"]),
    "ue_umg": ("Unreal UMG / CommonUI Specialist", E, "engine", "writes", "unreal_specialist",
        "Advises on Unreal UI with UMG and CommonUI.",
        "CommonUI for input routing across touch / gamepad; widgets reuse.",
        ["Input routing for touch and gamepad planned"],
        ["umg", "commonui"]),
}

# v0.814 THE AGENCY (owner: "GO 1 2 3"): 8 more engine roles (Roblox x3, Blender add-ons, Unity editor tools / netcode,
# Unreal world building / technical art) and deeper expert notes for 21 roles, from github.com/msitarzewski/agency-agents
# (MIT) - text only, in gamedesk/agency.py; `expert(role)` rides the model call beside `lens(role)`.
try:
    from .agency import EXPERT as _EXPERT, NEW_ROLES as _NEW_ROLES
    _R.update({k: v for k, v in _NEW_ROLES.items() if k not in _R})
except Exception:                                       # noqa: BLE001 - the crew works without the notes
    _EXPERT = {}

ROLES: dict[str, dict[str, Any]] = {
    k: {"key": k, "name": v[0], "tier": v[1], "dept": v[2], "mode": v[3], "lead": v[4], "does": v[5], "lens": v[6],
        "checks": list(v[7]), "keywords": list(v[8])} for k, v in _R.items()}
TIERS = [(D, "Directors"), (L, "Department leads"), (S, "Specialists"), (E, "Engine specialists")]

TEAMS: dict[str, dict[str, Any]] = {
    "combat": {"name": "Combat team", "roles": ["game_designer", "gameplay_programmer", "ai_programmer", "technical_artist",
                                               "sound_designer", "qa_tester"]},
    "narrative": {"name": "Story team", "roles": ["narrative_director", "writer", "world_builder", "level_designer"]},
    "ui": {"name": "UI team", "roles": ["ux_designer", "ui_programmer", "accessibility_specialist", "qa_tester"]},
    "level": {"name": "Level team", "roles": ["level_designer", "narrative_director", "world_builder", "art_director",
                                             "systems_designer", "qa_tester"]},
    "polish": {"name": "Polish team", "roles": ["performance_analyst", "technical_artist", "sound_designer", "qa_tester"]},
    "audio": {"name": "Audio team", "roles": ["audio_director", "sound_designer", "technical_artist", "gameplay_programmer"]},
    "live_ops": {"name": "Live-ops team", "roles": ["live_ops_designer", "economy_designer", "analytics_engineer",
                                                   "community_manager", "writer"]},
    "qa": {"name": "QA team", "roles": ["qa_lead", "qa_tester"]},
    "release": {"name": "Release team", "roles": ["release_manager", "qa_lead", "devops_engineer", "producer"]},
}

KIND_DEFAULT = {"feature": "gameplay_programmer", "content": "level_designer", "polish": "technical_artist",
                "fix": "lead_programmer", "test": "qa_tester"}
AUTO_CHECKS = [{"text": "Builds, plays 10 seconds and exports with no script errors", "by": "test"},
               {"text": "Hoola's playtest: frames move, screen not blank, taps / keys reach the game", "by": "test"}]
BY = ("test", "screen", "her")


def pick_role(title: str, detail: str = "", kind: str = "feature") -> str:
    """The role whose words match the task best (longest match wins, ties keep roster order); else by task kind."""
    text = f" {title} {detail} ".lower()
    best, score = "", 0
    for k, r in ROLES.items():
        for w in r["keywords"]:
            if re.search(rf"(?<![a-z]){re.escape(w)}", text) and len(w) > score:
                best, score = k, len(w)
    return best or KIND_DEFAULT.get(kind, "gameplay_programmer")


def builds(role: str) -> bool:
    return ROLES.get(role, {}).get("mode") == "builds"


def reviewer(role: str) -> str:
    """Who reviews this role's work: its lead (a director reviews a lead; a director's work goes to the producer)."""
    r = ROLES.get(role) or {}
    return r.get("lead") or ("producer" if role != "producer" else "creative_director")


def criteria_for(role: str, given: list | None = None) -> list[dict[str, Any]]:
    """A task's acceptance criteria: hers / the planner's first, then the role's checks, then Hoola's automatic ones."""
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for c in (given or []):
        txt = re.sub(r"\s+", " ", str((c.get("text") if isinstance(c, dict) else c) or "")).strip()[:200]
        by = (c.get("by") if isinstance(c, dict) else "") or "screen"
        if txt and txt.lower() not in seen:
            out.append({"text": txt, "by": by if by in BY else "screen", "status": "untested", "evidence": {}})
            seen.add(txt.lower())
    for t in (ROLES.get(role) or {}).get("checks", []):
        if t.lower() not in seen and len(out) < 6:
            out.append({"text": t, "by": "screen" if builds(role) else "her", "status": "untested", "evidence": {}})
            seen.add(t.lower())
    if builds(role):
        out += [{**a, "status": "untested", "evidence": {}} for a in AUTO_CHECKS]
    return out[:8]


def verdict(criteria: list[dict]) -> str:
    """COMPLETE / COMPLETE WITH NOTES / BLOCKED / NOT ASSESSED - from the criteria in code, never a model's word."""
    if not criteria:
        return "NOT ASSESSED"
    st = [c.get("status") for c in criteria]
    if "failed" in st:
        return "BLOCKED"
    if all(s == "covered" for s in st):
        return "COMPLETE"
    if any(s == "covered" for s in st):
        return "COMPLETE WITH NOTES"
    return "NOT ASSESSED"


def lens(role: str) -> str:
    r = ROLES.get(role)
    if not r:
        return ""
    return f"You work as the {r['name']} of this game studio: {r['does']} {r['lens']}"


def expert(role: str) -> str:
    """v0.814 The Agency's expert notes for this role ('' when it has none or `game_agency_experts` is off)."""
    try:
        from ..config import get_settings
        if not bool(getattr(get_settings(), "game_agency_experts", True)):
            return ""
    except Exception:                                   # noqa: BLE001
        pass
    return _EXPERT.get(role, "")


def roster() -> dict[str, Any]:
    tiers = []
    for t, label in TIERS:
        rows = [{k: r[k] for k in ("key", "name", "dept", "mode", "lead", "does", "checks")} for r in ROLES.values() if r["tier"] == t]
        tiers.append({"tier": t, "label": label, "roles": rows})
    return {"count": len(ROLES), "tiers": tiers, "teams": [{"key": k, **v} for k, v in TEAMS.items()],
            "builds": sum(1 for r in ROLES.values() if r["mode"] == "builds"),
            "experts": sorted(k for k in _EXPERT if k in ROLES),
            "note": "Builders change the game (Godot 4, web). Writers produce a written result for your OK: sound "
                    "files come with the asset pipeline, online play needs a network the game box does not have, "
                    "and Unity / Unreal are big-studio mode."}
