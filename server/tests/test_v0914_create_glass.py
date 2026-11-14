"""v0.914 CREATE GLASS: the Create glass reads as glass on black (her screenshots of v0.913 showed flat grey panes).
Pins the painted glass, the light over the whole page, the solid dock and the main button's words that shrink, not cut."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CREATE = ROOT / "lib/ui/create"


def test_glass_is_painted_with_a_rim_sheen_and_tint():
    s = (CREATE / "create_colour.dart").read_text()
    assert "class CrGlassDecoration extends Decoration" in s and "class _GlassBoxPainter extends BoxPainter" in s
    assert "Decoration crGlass(" in s and "Color? tint" in s and "Color? base" in s
    assert "PaintingStyle.stroke" in s, "the rim"
    assert "class _GrainPainter" in s, "a still film grain over the light"
    assert "BackdropFilter" not in s and "ImageFilter.blur" not in s


def test_cards_and_trays_carry_the_page_hue():
    src = "\n".join(p.read_text() for p in CREATE.glob("*.dart"))
    assert src.count("tint: CrHue.of(context)") >= 7


def test_dock_and_main_button():
    kit = (CREATE / "create_kit.dart").read_text()
    assert "base: c.bg" in kit, "the dock hides what scrolls under it"
    assert "fit: BoxFit.scaleDown" in kit, "the main button's words shrink instead of being cut"
    assert "foregroundDecoration:" in kit


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.914.0"
    assert "version: 0.914.0+913" in (ROOT / "pubspec.yaml").read_text()
