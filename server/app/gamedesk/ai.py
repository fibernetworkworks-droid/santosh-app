"""Model calls for the Game Desk: Claude (Opus first, the chat model as fallback, the cheap brain last) writes the design
doc from her words, then the GDScript from the approved design, fixes it from the REAL errors (headless play, export,
playtest), and changes it from her words. Every call is counted in AI kharcha (feature 'game', set by service).
Tests replace `ask`."""
from __future__ import annotations

import logging
import threading
import re
import time

from ..config import get_settings

log = logging.getLogger("santosh.gamedesk")
_CLIENT = None


class AiError(Exception):
    pass


def _client():
    global _CLIENT
    if _CLIENT is None:
        from anthropic import Anthropic
        _CLIENT = Anthropic(api_key=get_settings().anthropic_api_key, timeout=600, max_retries=2)   # v0.560 thinking needs room
    return _CLIENT


# v0.455 PROVENANCE: which model actually answered. Steam's Content Survey, Unity's Asset Store and Fab all put the
# disclosure on whoever publishes, and she cannot declare what nobody wrote down. Thread-local because builds run in
# parallel; `used()` reads and clears, so a caller records exactly its own call. A FALLBACK to the cheap brain is a
# different model and is named as one - that is the whole point.
_SEEN = threading.local()


def _mark(name: str) -> None:
    try:
        got = getattr(_SEEN, "models", None)
        if got is None:
            got = _SEEN.models = []
        if name and name not in got:
            got.append(name)
    except Exception:                                   # noqa: BLE001  (provenance must never break a build)
        pass


def used(clear: bool = True) -> list[str]:
    """The model(s) that answered on this thread since the last read. Never raises."""
    try:
        got = list(getattr(_SEEN, "models", None) or [])
        if clear:
            _SEEN.models = []
        return got
    except Exception:                                   # noqa: BLE001
        return []


def ask(system: str, prompt: str, max_tokens: int = 16000, job: str = "game_code") -> str:
    st = get_settings()
    if st.anthropic_api_key:
        last: Exception | None = None
        for model in dict.fromkeys([getattr(st, "game_model", "") or "claude-opus-5-5", st.anthropic_model]):
            for attempt in range(2):
                try:
                    from ..agent import door   # v0.560 EK DARWAZA: adaptive thinking + effort + her skill, the Claude way
                    msg = door.create(_client(), door.shape(job, model, max_tokens, system,
                                                            [{"role": "user", "content": prompt}]))
                    _mark(model)
                    return "".join(getattr(b, "text", "") for b in msg.content)
                except Exception as e:
                    last = e
                    log.info("game model %s failed (%s): %s", model, attempt, e)
                    time.sleep(1.5 * (attempt + 1))
        log.warning("game: Claude unavailable, trying the cheap brain: %s", last)
    from ..net.ai import llm
    try:
        out = llm(system, prompt, min(max_tokens, 8000), timeout=300)
        _mark("fallback: the cheap brain, not Claude")
        return out
    except Exception as e:
        raise AiError(f"Model nahi mila: {e}")


DESIGN = """You are the lead game designer at Hoola. Write a SHORT game design doc (max 350 words, Markdown) for a small
ORIGINAL game that Hoola will build in Godot 4 and run in the phone browser. Sections, in this order:
# <Title>
**Pitch:** one sentence.
## Core loop
## Controls (touch AND keyboard; one-thumb play on a phone)
## Goal and game over
## Difficulty (how it ramps over the first 2 minutes)
## Screens (title "Tap to start", playing with score, game over with score + best + "Tap to restart")
## Look (3-5 hex colours, simple shapes drawn in code; no image files)
## Numbers (speeds, sizes, timings a programmer needs)
If she asks for a 3D game, say "3D" in the pitch and design it for Hoola's 3D kit: third person (or first person),
ONE small level (a courtyard or a few rooms), a player who walks and jumps, things to collect, guards that patrol or
chase, one goal to reach, three lives; low-poly shapes drawn in code.
Rules: original names, characters and levels only - never copy a specific existing game (if she names one, design an
ORIGINAL game in that genre and say so in one line); no real-money, betting or gambling mechanics; no violence against
real groups; fit the orientation given. Write in clear English (game text may use her language if she asked)."""

GUIDE = """You write a complete small game in GODOT 4.7 GDScript (typed GDScript 2). It is exported to the WEB and
played on phones. Hoola provides project.godot, a root scene `main.tscn` = a plain `Node` with script res://main.gd,
and an autoload you must ignore (HoolaProbe). YOU WRITE ONLY .gd FILES.

HARD RULES (the build fails otherwise)
- main.gd starts with `extends Node`. Build EVERYTHING in code in _ready(): no .tscn, no images, no fonts, no sounds,
  no preload()/load() of files except your own scripts. Extra helper scripts: their own file with `class_name Foo` +
  `extends ...` (created with Foo.new()), or without class_name used as `const Foo = preload("res://foo.gd")`.
- Indent with TABS only. Typed variables (`var speed: float = 300.0`). No `yield` (use `await`). No `onready` keyword
  for nodes you create (assign them in _ready()).
- Layout from `get_viewport().get_visible_rect().size` (the viewport is W x H given below; stretch mode keeps it).
- INPUT must work by touch AND keyboard: handle `_input(event)` (NOT _unhandled_input): InputEventScreenTouch /
  InputEventScreenDrag for touch (mouse is emulated as touch), InputEventKey (event.pressed, event.keycode == KEY_SPACE,
  KEY_LEFT ...). Every decorative Control (ColorRect, Label, Panel) you add MUST get
  `mouse_filter = Control.MOUSE_FILTER_IGNORE`, or it swallows the taps.
- Drawing: ColorRect, Polygon2D, Line2D, Label (font size via add_theme_font_size_override("font_size", 48)), or a
  Node2D subclass with _draw() + queue_redraw(). Physics if needed: Area2D / CharacterBody2D / RigidBody2D with
  CollisionShape2D + RectangleShape2D / CircleShape2D created in code. 3D only if the design asks: Node3D, Camera3D,
  DirectionalLight3D, MeshInstance3D with BoxMesh / SphereMesh / PlaneMesh + StandardMaterial3D (Compatibility renderer).
- States: TITLE ("Tap to start") -> PLAYING (score visible) -> GAME_OVER (score + best + "Tap to restart"). Restart
  without reloading the page (reset your own state, or get_tree().reload_current_scene()).
- Best score: optional, only in user://best.save with FileAccess.open("user://best.save", ...).
- Performance (60 fps on a mid phone): no new nodes / arrays inside _process every frame (pool and reuse), under 500
  nodes, delta-based movement.
- FORBIDDEN (refused by Hoola's guard): any network class (HTTPRequest, WebSocketPeer ...), OS.execute / shell_open /
  get_environment, JavaScriptBridge, Engine.get_singleton, DirAccess, ClassDB, Expression, files outside user://.
- Original game only; no real-money / betting mechanics.
- GODOT 4.5-4.7 CHANGES (newer than most training data; the build is 4.7):
  * an override of a method with a typed return now has that return type too - give it an explicit `return` on
    every path (e.g. `return null`), or the script does not parse;
  * mouse and keyboard events no longer report device 0 - tell inputs apart by type (`event is InputEventKey`,
    `InputEventMouseButton`, `InputEventScreenTouch`), never by `event.device == 0`;
  * CanvasItem lines (draw_line, Line2D) have no extra antialias feather - set the width you want to see;
  * RichTextLabel: ImageUpdateMask.UPDATE_WIDTH_IN_PERCENT is now UPDATE_WIDTH_UNIT; add_image width/height are float;
  * AudioStreamPlayer2D/3D area_mask defaults to 0; AudioEffectSpectrumAnalyzer.tap_back_pos is gone;
  * 4.5 added variadic functions and @abstract; 4.6 made Jolt the 3D physics and Quaternion() starts as identity;
  * still Godot 4 rules: TileMapLayer (not TileMap), instantiate() (not instance()), await (not yield),
    signal.connect(callable), Time.get_ticks_msec(), VisibleOnScreenNotifier2D.
- QA PROBE: report to Hoola's test bots (HoolaProbe is always there): HoolaProbe.state("state", "title" / "playing" /
  "game_over") whenever the screen state changes, HoolaProbe.state("score", score) when the score changes,
  HoolaProbe.state("level", n), and HoolaProbe.event("game_over") / event("level_up") / event("win") when they happen.
  These calls never change the game.
- ASSETS: if the files include hoola_assets.gd (the HoolaAssets autoload, written by Hoola - NEVER edit or re-output
  it), use its approved art and sound: HoolaAssets.has(key), HoolaAssets.tex(key) -> Texture2D for a Sprite2D /
  TextureRect, HoolaAssets.play(key) for a sound, HoolaAssets.sound(key) -> AudioStream (music: a looping
  AudioStreamPlayer), HoolaAssets.scene(key) -> PackedScene for a 3D model. Keys follow the Game Bible ids (enemy
  "red_bat" -> sprite "red_bat", level "l1" -> background "bg_l1"; sounds "sfx_jump" ...). ALWAYS keep the drawn
  fallback when has(key) is false. If HoolaAssets.CREDITS is not empty, show it in small text on the title screen.
  Load no other files.
- WORLD: if the files include hoola_world.gd (the HoolaWorld autoload, written by Hoola from an approved generated world -
  NEVER edit or re-output it), build the map from it instead of inventing one: HoolaWorld.keys(), HoolaWorld.size(key)
  -> Vector2i, tile(x, y, key) -> int, tile_name(id, key), walkable(x, y, key), solid(x, y, key), height(x, y, key)
  0..1, spawn(key) -> Vector2i, points("villages" / "rooms" / "exit" / "treasure" / "goal" / "coins", key) -> Array of
  Vector2i, sprite(key, cell_px) -> Sprite2D of the whole map (fast; add it under a Node2D), color(id, key).
  key "" = the first world. A "side" view world is a platformer level (y = 0 is the top row).
- PHYSICS: if the files include hoola_physics.gd (the HoolaPhysics autoload, settings PROVED in Hoola's physics lab -
  NEVER edit or re-output it), never set physics ticks or gravity yourself: it already did. Use
  HoolaPhysics.jump_velocity(height_px) for jumps, jump_height(v), air_time(v), range_of(vx, vy), gravity(), and call
  HoolaPhysics.fast(body) on every fast RigidBody2D when HoolaPhysics.needs_ccd(speed) is true.
- AUDIO: if the files include hoola_audio.gd (the HoolaAudio autoload, MEASURED by Hoola - NEVER edit or re-output it),
  make positional players with HoolaAudio.player2d(stream) / player3d(stream) (distance set already), call
  HoolaAudio.set_zone(key) when the player enters a place named in HoolaAudio.zones(), and HoolaAudio.occlude(player,
  true / false) when a wall is between a sound and the player.
- HAPTICS: if the files include hoola_haptics.gd (the HoolaHaptics autoload - NEVER edit or re-output it), call
  HoolaHaptics.play(name) for the moments in HoolaHaptics.names() (e.g. "jump", "coin", "hit", "game_over"); put
  HoolaHaptics.set_enabled(on) and set_intensity(0..1) on the settings / pause screen. Never vibrate any other way.
- XR: if the files include hoola_xr.gd (the HoolaXR autoload - NEVER edit or re-output it), build the 3D scene with an
  XROrigin3D holding an XRCamera3D plus a normal Camera3D at head height for players without a headset; start XR only
  from a tap with HoolaXR.start(origin); move only by HoolaXR.teleport(point) and turn only by HoolaXR.snap_turn(+-1)
  (never smooth motion); read hand gestures with HoolaXR.gesture(joints) -> "pinch" / "grab" / "point" / "open".
- SIMULATOR: if the files include hoola_sim.gd (the HoolaSim autoload, a VALIDATED orbit model - NEVER edit or re-output
  it), move spacecraft only with HoolaSim.step([position_km, velocity_kms], dt_s) (RK4, two-body + J2); draw kilometres
  scaled to the screen; never invent another physics for orbits.
- RUNTIME: if the files include hoola_runtime.gd (the HoolaRuntime autoload: Hoola's replay recorder, test bot and
  opt-in telemetry - NEVER edit or re-output it), NEVER call randomize() and never seed from the clock: in Hoola's test
  runs HoolaRuntime seeds the game so a recorded play replays exactly (randf / randi are fine; real players still get
  a fresh random start). On the title screen call
  `if HoolaRuntime.needs_consent(): HoolaRuntime.ask_consent(self)` (it asks the player once; nothing is sent without yes).
  SCENES (v0.456): this game may have real .tscn scenes beside the scripts, generated by Hoola from a checked spec.
  Load one with `preload("res://level1.tscn").instantiate()` and add it as a child; a scene's root carries the script
  named in its spec, so write that script as a normal class for that node type. Never write a .tscn yourself and never
  put code inside one. A 3D scene (root Node3D) brings its own Camera3D, light and WorldEnvironment: add it with
  add_child() from main.gd; for a 3D game, main.gd only loads the level and wires the HUD (a CanvasLayer).
  LIVE OPS: read tunable numbers through HoolaRuntime so live events and A/B tests can change them without a new build:
  `HoolaRuntime.num("player.hp", HoolaBible.DATA["player"]["hp"])` (paths = player.<field>, economy.<field>,
  <kind>.<id>.<field> of the Bible), switches with `HoolaRuntime.flag("double_coins")`; report game moments with
  `HoolaRuntime.track("level_up", level)` / `track("game_over", level)` / `track("purchase")` (sent only with the
  player's yes). Never build paid random items (loot boxes) or pressure to buy.
- GAME BIBLE: if the files include hoola_bible.gd (the HoolaBible autoload), it is the source of truth written by Hoola -
  NEVER edit or re-output it. Read every name, colour and number that exists there from HoolaBible.DATA (e.g.
  HoolaBible.DATA["player"]["hp"], HoolaBible.DATA["by_id"]["enemy"]["red_bat"]["speed"], HoolaBible.DATA["entities"]["level"])
  instead of typing the value into the code, so a Bible change rebuilds the game without new code. Colours are hex
  strings: Color(HoolaBible.DATA["style"]["palette"][0]). Levels play in "order"; waves are {enemy, count, at_s}.

OUTPUT FORMAT (nothing else):
=== main.gd ===
<the whole file>
=== other_file.gd ===
<the whole file>
=== NOTES ===
<2-4 short lines: controls and what to try>"""

FILE_RE = re.compile(r"^===\s*([A-Za-z0-9_.\-]+)\s*===\s*$", re.M)


def parse(raw: str) -> dict[str, str]:
    """{'main.gd': code, ..., '__notes__': text} from the === name === blocks (code fences stripped)."""
    raw = raw or ""
    parts = FILE_RE.split(raw)
    out: dict[str, str] = {}
    for i in range(1, len(parts) - 1, 2):
        name, body = parts[i].strip(), parts[i + 1]
        body = re.sub(r"^\s*```[a-zA-Z]*\s*\n", "", body)
        body = re.sub(r"\n\s*```\s*$", "\n", body.rstrip()) + "\n"
        if name.upper() == "NOTES":
            out["__notes__"] = body.strip()[:800]
        elif name.endswith(".gd"):
            out[name.lower()] = body.replace("\r\n", "\n")
    return out


def design(brief: str, orientation: str, feedback: str = "", old: str = "") -> str:
    p = f"Her words: {brief}\nOrientation: {orientation}."
    if old and feedback:
        p += f"\n\nThe current design doc:\n{old}\n\nHer changes to the design (apply them, keep the rest): {feedback}"
    txt = ask(DESIGN, p, max_tokens=2500, job="game_design").strip()
    if not txt.startswith("#"):
        txt = "# " + txt
    return txt[:6000]


def _ctx(orientation: str, size: tuple[int, int], design_doc: str = "") -> str:
    out = f"Viewport: {size[0]} x {size[1]} ({orientation})."
    try:                                                # v0.806: a 3D design gets Hoola's 3D kit and its API
        from . import kit3d
        if kit3d.wants(design_doc):
            out += "\n\n" + kit3d.API
    except Exception:                                   # noqa: BLE001  (a game is written without the kit note)
        log.exception("3d kit note")
    return out


def code(design_doc: str, orientation: str, size: tuple[int, int]) -> dict[str, str]:
    return parse(ask(GUIDE, f"{_ctx(orientation, size, design_doc)}\n\nThe approved design doc:\n{design_doc}\n\nWrite the game."))


def _listing(files: dict[str, str]) -> str:
    return "\n".join(f"=== {n} ===\n{c}" for n, c in files.items() if n.endswith(".gd"))


def fix(design_doc: str, files: dict[str, str], problems: list[str], orientation: str, size: tuple[int, int]) -> dict[str, str]:
    p = (f"{_ctx(orientation, size, design_doc)}\n\nDesign doc:\n{design_doc}\n\nCurrent files:\n{_listing(files)}\n\n"
         "These REAL problems came from running / exporting / playing it - fix every one and return ALL files again "
         "(whole files, same format):\n- " + "\n- ".join(problems[:12]))
    return parse(ask(GUIDE, p))


def change(design_doc: str, files: dict[str, str], words: str, orientation: str, size: tuple[int, int]) -> dict[str, str]:
    p = (f"{_ctx(orientation, size, design_doc)}\n\nDesign doc:\n{design_doc}\n\nCurrent files:\n{_listing(files)}\n\n"
         f"Her change (do exactly this, keep everything else working; return ALL files, whole, same format): {words}")
    return parse(ask(GUIDE, p))


PLAN = """You are the producer of a long game project at Hoola. Break the work into SMALL tasks the Hoola game developer
can do ONE AT A TIME, each a single change to the current Godot game (5 minutes to 2 hours of work): one mechanic, one
screen, one enemy type, one level, one tuning pass, one fix. Each task must be checkable by playing the game.
Rules: build on what exists (never "rewrite the game"); the order matters - earlier milestones first, a task only
needs tasks above it; no art / sound files (everything is drawn in code for now); original content only; no
real-money mechanics. Use the milestone keys given. 6 to 15 tasks.
Each task belongs to ONE studio role (the crew list is given) and has 2-4 acceptance criteria: each is one checkable
sentence and says how it is checked - "screen" (visible in a screenshot), "test" (Hoola's automatic play run) or
"her" (only she can judge it, e.g. feel or fun).
OUTPUT: only a JSON array, each item {"title": "<= 70 chars, starts with a doing word", "detail": "1-3 sentences, exact
numbers where they matter", "milestone": "<key>", "kind": "feature|content|polish|fix|test", "priority": 1|2|3,
"role": "<crew role key>", "criteria": [{"text": "...", "by": "screen|test|her"}]}"""


def plan_tasks(design_doc: str, goal: str, milestones: list[dict], tasks: list[dict], decisions: list[str],
               words: str = "", roles: list[dict] | None = None) -> list[dict]:
    import json
    ms = ", ".join(f"{m['key']} = {m['name']}" for m in milestones)
    if roles:
        crew_txt = "\n".join(f"- {r['key']}: {r['name']} - {r['does']}" + ("" if r.get("mode") == "builds" else " (writes, does not change the game)")
                              for r in roles)
        decisions = list(decisions) + [f"CREW (give each task one of these role keys, in this order of work):\n{crew_txt}"]
    have = "\n".join(f"- {t['number']} [{t['status']}] {t['title']}" for t in tasks[-60:]) or "(none yet)"
    dec = "\n".join(f"- {d}" for d in decisions[-22:]) or "(none yet)"
    p = (f"Project goal: {goal}\nMilestones (in order): {ms}\n\nThe game's design doc:\n{design_doc}\n\n"
         f"Tasks already on the board:\n{have}\n\nDecisions she made (follow them):\n{dec}\n\n"
         + (f"What she asked for now: {words}\n\n" if words else "") + "Write the next tasks.")
    raw = ask(PLAN, p, max_tokens=4000, job="game_plan")
    m = re.search(r"\[.*\]", raw or "", re.S)
    try:
        items = json.loads(m.group(0)) if m else []
    except ValueError:
        items = []
    return [i for i in items if isinstance(i, dict) and str(i.get("title") or "").strip()][:15]


def ask_with_images(system: str, text: str, images: list[bytes], max_tokens: int = 2000) -> str:
    """v0.406 the crew's review: Claude reads the playtest screenshots too (PNG). Without Claude, text only."""
    import base64
    st = get_settings()
    if st.anthropic_api_key and images:
        content = [{"type": "image", "source": {"type": "base64", "media_type": "image/png",
                                                "data": base64.b64encode(b).decode()}} for b in images[:3]]
        content.append({"type": "text", "text": text})
        for model in dict.fromkeys([getattr(st, "game_model", "") or "claude-opus-5-5", st.anthropic_model]):
            try:
                from ..agent import door   # v0.560 EK DARWAZA
                msg = door.create(_client(), door.shape("game_review", model, max_tokens, system,
                                                        [{"role": "user", "content": content}]))
                _mark(model)
                return "".join(getattr(b, "text", "") for b in msg.content)
            except Exception as e:
                log.info("game review model %s failed: %s", model, e)
    return ask(system, text + ("\n\n(No screenshots could be shown.)" if images else ""), max_tokens=max_tokens)


# ---------------------------------------------------------------- v0.456 scenes as checked data
SCENE = """You design one Godot 4 SCENE for her game, as DATA. You never write a .tscn file: you answer with a spec and
Hoola generates the scene, checks it and loads it in the real engine.

Answer with ONE JSON object and nothing else:
{"name": "Level1",
 "root": {"type": "Node2D", "name": "Level", "script": "level.gd",
   "children": [
     {"type": "CharacterBody2D", "name": "Player", "script": "player.gd", "props": {"position": [100, 300]},
      "children": [
        {"type": "CollisionShape2D", "name": "Shape", "shape": {"kind": "rect", "size": [24, 48]}},
        {"type": "ColorRect", "name": "Body", "props": {"size": [24, 48], "color": "#4CC2FF"}},
        {"type": "AnimationPlayer", "name": "Anim", "animations": [
          {"name": "idle", "length": 0.6, "loop": true,
           "tracks": [{"path": "Body:position", "keys": [[0, [0, 0]], [0.3, [0, -6]], [0.6, [0, 0]]]}]}]}]},
     {"instance": "coin.tscn", "name": "Coin1", "props": {"position": [200, 250]}}]}}

RULES, each of which Hoola checks and will refuse:
- A node has either a "type" from the allowed list OR an "instance" of another scene of this game, never both.
- INSTANCES ARE HOW CONTENT SCALES: one coin.tscn placed forty times is data. Prefer them over forty hand-made nodes.
- "script" is the FILE NAME of a .gd file that already exists in this game. You may not write new code here.
- A SCENE MAY NEVER CARRY SCRIPT SOURCE in any form - no "source", "code" or "script/source" key. An embedded script
  inside a .tscn runs and escapes Hoola's code guard, so any such key is refused outright.
- Names: a letter then letters / digits / underscore. Siblings may not share a name.
- Properties: only the ones Hoola writes (position, scale, size, rotation, color, modulate, text, visible, z_index,
  flip_h, one_shot, wait_time, value, max_value...). Anything else is dropped and named, so do not invent one.
- Animation tracks: "Node:property" paths relative to the AnimationPlayer's parent, keys in time order.
- Shapes: rect (size), circle (radius), capsule (radius + height).
- 3D (v0.79x): a scene whose root is a 3D node (Node3D...) is a 3D scene. There, position / rotation_degrees / scale are
  THREE numbers [x, y, z]. Allowed 3D nodes: Node3D, MeshInstance3D, Camera3D, DirectionalLight3D, OmniLight3D,
  SpotLight3D, WorldEnvironment, StaticBody3D, RigidBody3D, CharacterBody3D, AnimatableBody3D, Area3D, CollisionShape3D,
  Path3D, PathFollow3D, Marker3D, GPUParticles3D, CPUParticles3D, AudioStreamPlayer3D, VisibleOnScreenNotifier3D.
  * A MeshInstance3D carries "mesh": {"kind": box|sphere|cylinder|capsule|plane|prism|torus, "size": [x,y,z] (plane: [x,z]),
    "radius", "height", "material": {"color": "#hex", "metallic": 0-1, "roughness": 0-1, "emission": "#hex",
    "emission_energy": 0-16}}.
  * A CollisionShape3D shape: box (size [x,y,z]), sphere (radius), capsule / cylinder (radius + height).
  * One WorldEnvironment with "environment": {"sky": {"top": "#hex", "horizon": "#hex", "ground": "#hex"} OR
    "background": "#hex", "ambient": "#hex", "ambient_energy", "fog": true, "fog_density": 0-1, "glow": true}.
  * Lights: light_energy, light_color, shadow_enabled. The camera: fov, current: true (exactly one camera is current).
  * A REAL MODEL is placed with {"model": "<asset name>", "name": ..., "props": {...}} - only from "3D models you may
    place" below (her approved assets). Never invent one; with none listed, build with meshes.
  * A stunning 3D scene = a sky, one sun with shadows, a little fog, a camera framing the action, materials with real
    roughness / metal values, emission on the things that should glow, and instances / models for repeated objects.
- TileMaps and shaders are NOT available here."""


def scene_spec(design: str, scripts: list[str], scenes: list[str], words: str, name: str = "",
               models: list[str] | None = None) -> dict:
    """Her words -> one scene spec. Returns a dict; the caller checks it (never trust this shape)."""
    import json as _json
    import re as _re
    p = (f"The game's design:\n{(design or '')[:4000]}\n\nScripts you may attach: {', '.join(scripts) or 'none'}\n"
         f"Scenes you may instance: {', '.join(scenes) or 'none'}\n"
         f"3D models you may place: {', '.join(models or []) or 'none'}\n"
         f"Screen: portrait 720x1280 unless the design says otherwise.\n\nShe asked for: {words}\n"
         + (f"Call the scene {name}.\n" if name else ""))
    raw = ask(SCENE, p, max_tokens=8000, job="game_scene")
    t = _re.sub(r"^```(?:json)?\s*|\s*```$", "", (raw or "").strip())
    i, j = t.find("{"), t.rfind("}")
    if i < 0 or j <= i:
        raise AiError("Scene ka jawab JSON mein nahi aaya.")
    try:
        out = _json.loads(t[i:j + 1])
    except ValueError as e:
        raise AiError(f"Scene ka JSON padha nahi gaya: {e}")
    if not isinstance(out, dict):
        raise AiError("Scene spec ek object hona chahiye.")
    return out
