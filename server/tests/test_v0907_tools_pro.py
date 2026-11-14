"""v0.907 TOOLS PRO: the Tools tab = option B of the design canvas (own drawing per studio, black circle, motion)."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_tools_use_their_own_drawings_on_black():
    tools = (ROOT / "lib/ui/shell/hoola_tools.dart").read_text()
    icons = (ROOT / "lib/ui/shell/hoola_tool_icons.dart").read_text()
    assert "c.accentSoft" not in tools and "c.accent," not in tools, "no violet tiles"
    assert "color: c.pill, shape: BoxShape.circle" in tools and "color: c.onPill" in tools
    assert "mainAxisAlignment: MainAxisAlignment.center" in tools and "textAlign: TextAlign.center" in tools
    for g in ("create", "interactive", "vocal", "flow", "web", "app", "design", "prompting", "code", "game", "connectors"):
        assert f"ToolGlyph.{g}:" in icons, g
    assert "HoolaMotion.reduced(context)" in tools, "reduce motion = still"


def test_pinned_by_flutter_test():
    t = (ROOT / "test/tools_pro_test.dart").read_text()
    assert "icon centred" in t and "no two the same" in t and "nothing moves" in t
    assert "tools_pro_test.dart" in (ROOT / ".github/workflows/app-screens.yml").read_text()


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.913.0"
    assert "version: 0.913.0+912" in (ROOT / "pubspec.yaml").read_text()
