"""v0.904 NAV BLACK: the open tab is a solid black pill with a white icon; the Hoola tab keeps its own violet logo."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_black_pill_and_the_hoola_logo():
    shell = (ROOT / "lib/ui/shell/hoola_shell.dart").read_text()
    nav = shell[shell.index("class HoolaNav "):shell.index("/// While a call runs")]
    assert "color: c.pill" in nav and "c.accentSoft" not in nav and "c.accent," not in nav
    assert "Color.lerp(c.ink2, c.onPill, t)" in nav and "cut: c.pill" in nav
    assert "HoolaMark(" in nav and "NavGlyph.hoola" in nav and "HoolaColors.darkSet.accent" in nav


def test_phone_test_pins_it():
    t = (ROOT / "test/nav_pro_test.dart").read_text()
    assert "HoolaColors.light.pill" in t and "no violet tile any more" in t


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION.startswith("0.911.0")
    assert "version: 0.911.0+910" in (ROOT / "pubspec.yaml").read_text()
