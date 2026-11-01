"""The fixed part of every Hoola game: project.godot, the root scene, the Web export preset and Hoola's probe.

The model writes only GDScript files (main.gd + helpers). The root scene is a plain Node with main.gd, so a game builds
every node in code: one predictable shape that always exports. `hoola_probe.gd` is Hoola's own autoload (never the
model's): on the web it sets window.__hoola = {ready, fps, mem, frames, errors} so the playtest reads real engine numbers."""
from __future__ import annotations

SIZES = {"portrait": (720, 1280), "landscape": (1280, 720), "square": (1024, 1024)}

PROBE = '''extends Node
# Hoola's playtest probe (not part of the game logic): reports readiness, frames per second and memory to the page,
# and (v0.416 QA farm) what the game tells it: HoolaProbe.state("score", 12), HoolaProbe.event("game_over").
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


# Hoola's OWN autoloads (written by Hoola from approved data, never by the model): file -> autoload name. v0.395 Bible,
# v0.416 assets, v0.417 the role packs (World = Procedural World Engineer, Physics = Physics Engine Developer).
HOOLA_OWN = {"hoola_bible.gd": "HoolaBible", "hoola_assets.gd": "HoolaAssets", "hoola_world.gd": "HoolaWorld",
             "hoola_physics.gd": "HoolaPhysics"}


def files(title: str, orientation: str, scripts: dict[str, str]) -> dict[str, str]:
    """Every file of the Godot project: Hoola's fixed ones + her game's scripts."""
    proj = project_godot(title, orientation)
    for fname, node in HOOLA_OWN.items():               # an autoload is global with no class cache (works headless)
        if fname in scripts:
            proj = proj.replace('HoolaProbe="*res://hoola_probe.gd"', f'HoolaProbe="*res://hoola_probe.gd"\n{node}="*res://{fname}"')
    out = {"project.godot": proj, "main.tscn": MAIN_TSCN, "export_presets.cfg": EXPORT_PRESETS, "hoola_probe.gd": PROBE}
    out.update(scripts)
    return out


# ---------------------------------------------------------------- v0.416 GAME PLATFORMS
NATIVE = {"linux": "Linux", "windows": "Windows Desktop", "macos": "macOS", "android": "Android"}


def native_presets(title: str, package: str, version_code: int, version_name: str, orientation: str = "portrait",
                   android_format: str = "apk") -> str:
    """Web (as before) + desktop + Android presets. Android needs NO internet permission (Hoola games never use the
    network); its keystore comes from Godot's own GODOT_ANDROID_KEYSTORE_RELEASE_* environment variables at export time,
    never from this file. An AAB needs Godot's Gradle build (the builds repo installs the Android build template)."""
    safe = (title or "Hoola game").replace('"', "'")[:60]
    aab = android_format == "aab"
    out = EXPORT_PRESETS + f'''
[preset.1]

name="Linux"
platform="Linux"
runnable=true
export_filter="all_resources"
include_filter=""
exclude_filter=""
export_path="../dist/linux/game.x86_64"

[preset.1.options]

binary_format/embed_pck=true
binary_format/architecture="x86_64"
texture_format/s3tc_bptc=true
texture_format/etc2_astc=false

[preset.2]

name="Windows Desktop"
platform="Windows Desktop"
runnable=true
export_filter="all_resources"
include_filter=""
exclude_filter=""
export_path="../dist/windows/game.exe"

[preset.2.options]

binary_format/embed_pck=true
binary_format/architecture="x86_64"
texture_format/s3tc_bptc=true
texture_format/etc2_astc=false
application/modify_resources=false
application/product_name="{safe}"
application/file_version="{version_name}.0"
application/product_version="{version_name}.0"
codesign/enable=false

[preset.3]

name="macOS"
platform="macOS"
runnable=true
export_filter="all_resources"
include_filter=""
exclude_filter=""
export_path="../dist/macos/game.zip"

[preset.3.options]

binary_format/architecture="universal"
application/bundle_identifier="{package.replace('_', '')}"
application/short_version="{version_name}"
application/version="{version_code}"
application/name="{safe}"
codesign/codesign=1
notarization/notarization=0

[preset.4]

name="Android"
platform="Android"
runnable=true
export_filter="all_resources"
include_filter=""
exclude_filter=""
export_path="../dist/android/game.{'aab' if aab else 'apk'}"

[preset.4.options]

gradle_build/use_gradle_build={'true' if aab else 'false'}
gradle_build/export_format={1 if aab else 0}
architectures/armeabi-v7a=true
architectures/arm64-v8a=true
architectures/x86_64=false
package/unique_name="{package}"
package/name="{safe}"
version/code={int(version_code)}
version/name="{version_name}"
screen/immersive_mode=true
screen/support_small=true
screen/support_normal=true
screen/support_large=true
screen/support_xlarge=true
permissions/internet=false
'''
    return out                                         # orientation: project.godot window/handheld/orientation
