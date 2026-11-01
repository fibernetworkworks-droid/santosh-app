"""The fixed part of every Hoola game: project.godot, the root scene, the Web export preset and Hoola's probe.

The model writes only GDScript files (main.gd + helpers). The root scene is a plain Node with main.gd, so a game builds
every node in code: one predictable shape that always exports. `hoola_probe.gd` is Hoola's own autoload (never the
model's): on the web it sets window.__hoola = {ready, fps, mem, frames, errors} so the playtest reads real engine numbers."""
from __future__ import annotations

SIZES = {"portrait": (720, 1280), "landscape": (1280, 720), "square": (1024, 1024)}

PROBE = '''extends Node
# Hoola's playtest probe (not part of the game logic): reports readiness, frames per second and memory to the page,
# and (v0.415 QA farm) what the game tells it: HoolaProbe.state("score", 12), HoolaProbe.event("game_over").
var _t := 0.0
var _frames := 0
var _state := {}
var _events: Array = []
var _dirty := false

func _ready() -> void:
	if OS.has_feature("web"):
		JavaScriptBridge.eval("window.__hoola = {ready: true, fps: 0, mem: 0, frames: 0, state: {}, events: []}", true)

func state(key: String, value: Variant) -> void:
	_state[key] = value
	_dirty = true

func event(name: String) -> void:
	_events.append({"e": name, "f": _frames})
	if _events.size() > 60:
		_events.pop_front()
	_dirty = true

func _process(delta: float) -> void:
	_frames += 1
	_t += delta
	if _t >= 0.5 and OS.has_feature("web"):
		_t = 0.0
		var extra := ""
		if _dirty:
			_dirty = false
			extra = "window.__hoola.state = %s; window.__hoola.events = %s;" % [JSON.stringify(_state), JSON.stringify(_events)]
		JavaScriptBridge.eval("if (window.__hoola) { window.__hoola.fps = %d; window.__hoola.mem = %d; window.__hoola.frames = %d; %s }"
			% [Engine.get_frames_per_second(), OS.get_static_memory_usage(), _frames, extra], true)
'''


def project_godot(title: str, orientation: str = "portrait") -> str:
    w, h = SIZES.get(orientation, SIZES["portrait"])
    safe = (title or "Hoola game").replace('"', "'")[:60]
    orient = {"portrait": 1, "landscape": 0}.get(orientation, 1)
    return f'''; Engine configuration file. Made by Hoola (Godot 4).
config_version=5

[application]

config/name="{safe}"
run/main_scene="res://main.tscn"
config/features=PackedStringArray("4.7", "GL Compatibility")

[autoload]

HoolaProbe="*res://hoola_probe.gd"

[display]

window/size/viewport_width={w}
window/size/viewport_height={h}
window/stretch/mode="canvas_items"
window/stretch/aspect="expand"
window/handheld/orientation={orient}

[input_devices]

pointing/emulate_touch_from_mouse=true

[rendering]

renderer/rendering_method="gl_compatibility"
renderer/rendering_method.mobile="gl_compatibility"
textures/vram_compression/import_etc2_astc=true
'''


MAIN_TSCN = '''[gd_scene load_steps=2 format=3]

[ext_resource type="Script" path="res://main.gd" id="1"]

[node name="Main" type="Node"]
script = ExtResource("1")
'''

EXPORT_PRESETS = '''[preset.0]

name="Web"
platform="Web"
runnable=true
export_filter="all_resources"
include_filter=""
exclude_filter=""
export_path="../build/index.html"

[preset.0.options]

custom_template/debug=""
custom_template/release=""
variant/extensions_support=false
variant/thread_support=false
vram_texture_compression/for_desktop=true
vram_texture_compression/for_mobile=true
html/export_icon=true
html/custom_html_shell=""
html/head_include=""
html/canvas_resize_policy=2
html/focus_canvas_on_start=true
html/experimental_virtual_keyboard=false
progressive_web_app/enabled=false
'''


def files(title: str, orientation: str, scripts: dict[str, str]) -> dict[str, str]:
    """Every file of the Godot project: Hoola's fixed ones + her game's scripts."""
    proj = project_godot(title, orientation)
    if "hoola_bible.gd" in scripts:                     # v0.395 the Game Bible is an autoload: global with no class cache
        proj = proj.replace('HoolaProbe="*res://hoola_probe.gd"', 'HoolaProbe="*res://hoola_probe.gd"\nHoolaBible="*res://hoola_bible.gd"')
    if "hoola_assets.gd" in scripts:                    # v0.414 the approved assets
        proj = proj.replace('HoolaProbe="*res://hoola_probe.gd"', 'HoolaProbe="*res://hoola_probe.gd"\nHoolaAssets="*res://hoola_assets.gd"')
    out = {"project.godot": proj, "main.tscn": MAIN_TSCN, "export_presets.cfg": EXPORT_PRESETS, "hoola_probe.gd": PROBE}
    out.update(scripts)
    return out
