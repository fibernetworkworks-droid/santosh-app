"""v0.903 NAV PRO: the phone tab bar redrawn - vector icons on one grid, the selected pill behind the icon only."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_icons_are_vectors_for_all_four_tabs():
    src = (ROOT / "lib/ui/shell/hoola_nav_icons.dart").read_text()
    assert "enum NavGlyph { hoola, employees, tools, computer }" in src
    assert "class NavIconPainter extends CustomPainter" in src and "stroke = 1.7" in src
    assert "Image.asset" not in src and "Icons." not in src          # drawn, not a font glyph or a picture


def test_bar_uses_them_and_the_pill_sits_behind_the_icon():
    shell = (ROOT / "lib/ui/shell/hoola_shell.dart").read_text()
    nav = shell[shell.index("class HoolaNav "):shell.index("/// While a call runs")]
    assert "NavIcon(" in nav and "Icons." not in nav
    assert "FittedBox" in nav and "BoxFit.scaleDown" in nav
    assert "HapticFeedback.selectionClick" in nav and "onTap: widget.onTap" in nav


def test_ci_runs_the_nav_test_and_takes_the_picture():
    wf = (ROOT / ".github/workflows/app-screens.yml").read_text()
    assert "test/nav_pro_test.dart" in wf
    assert "60_tab_bar_" in (ROOT / "test/goldens/screens_test.dart").read_text()


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION.startswith("0.909.0")
    assert "version: 0.909.0+908" in (ROOT / "pubspec.yaml").read_text()
