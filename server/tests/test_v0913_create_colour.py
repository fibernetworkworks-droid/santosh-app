"""v0.913 CREATE IN COLOUR: every phone Create screen in colour and glass (design canvas
claude.ai/artifact/HXF8gGUqohSnZBnohRkbtu). Pins the colour system, the moving pieces and the design rules."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CREATE = ROOT / "lib/ui/create"


def test_the_colour_system_lives_in_the_theme():
    theme = (ROOT / "lib/ui/hoola_theme.dart").read_text()
    assert "class CreateHues" in theme and "class CreateScene" in theme
    for kind in ("image", "video", "film", "song", "voice"):
        assert f"static const {kind} = [Color(" in theme, kind
    colour = (CREATE / "create_colour.dart").read_text()
    for part in ("enum CrHue", "class CrAura", "BoxDecoration crGlass(", "class CrScene", "class CrMove", "class CrArtCard",
                 "class CrBar", "class CrSheen", "class CrOrb"):
        assert part in colour, part
    # everything that moves stands still when the phone asks for less motion
    assert colour.count("HoolaMotion.reduced(context)") >= 4


def test_every_page_has_its_hue_and_the_home_follows_the_kind():
    src = "\n".join(p.read_text() for p in CREATE.glob("*.dart"))
    for hue in ("CrHue.image", "CrHue.video", "CrHue.film", "CrHue.song", "CrHue.voice"):
        assert f"hue: {hue}" in src, hue
    home = (CREATE / "create_home.dart").read_text()
    assert "hue: m.hue" in home and "_ModeSwitch" in home and "CrMove(move:" in home and "'Making now'" in home
    assert "CreateVideo(store: _store, prompt: words, camera: camera)" in home, "a camera card opens Video with that move"
    film = (CREATE / "create_film.dart").read_text()
    assert "_CameraGrid" in film and "this.camera = ''" in film


def test_design_rules_hold():
    for p in CREATE.glob("*.dart"):
        s = p.read_text()
        assert "Color(0x" not in s and "BackdropFilter" not in s and "ImageFilter.blur" not in s and "glass.dart'" not in s, p.name


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.913.0"
    assert "version: 0.913.0+912" in (ROOT / "pubspec.yaml").read_text()
