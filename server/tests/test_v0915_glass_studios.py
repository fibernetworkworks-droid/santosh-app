"""v0.915 GLASS STUDIOS: every studio bead is glass and every drawing has its own move."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CREATE = ROOT / "lib/ui/create"


def test_beads_are_glass_and_moves_exist():
    s = (CREATE / "create_colour.dart").read_text()
    assert "class _OrbGlass extends CustomPainter" in s and "foregroundDecoration" in s
    assert "Matrix4 crGlyphMove(" in s and "class CrRings" in s
    for kind in ("image", "video", "film", "music", "voice", "dub", "cut", "pen", "cast", "cinema", "brand", "grid"):
        assert f"case '{kind}':" in s, kind


def test_studios_play_a_wave_and_stand_still_when_asked():
    home = (CREATE / "create_home.dart").read_text()
    assert "class _StudiosState extends State<_Studios> with TickerProviderStateMixin" in home
    assert "beat: _beatOf(i)" in home
    i = home.index("class _StudiosState")
    assert "HoolaMotion.reduced(context)" in home[i:i + 2000]
    kit = (CREATE / "create_kit.dart").read_text()
    assert "this.beat" in kit and "crGlyphMove(glyph.name" in kit


def test_design_rules_hold():
    for p in CREATE.glob("*.dart"):
        s = p.read_text()
        assert "Color(0x" not in s and "BackdropFilter" not in s and "ImageFilter.blur" not in s, p.name


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.999.99"
    assert "version: 0.999.99+1094" in (ROOT / "pubspec.yaml").read_text()
