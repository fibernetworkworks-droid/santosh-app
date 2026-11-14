"""v0.911 DARK LIKE CLAUDE: the new-design dark palette measured against her Claude screenshot."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _dark():
    src = (ROOT / "lib/ui/hoola_theme.dart").read_text()
    block = src[src.index("static const darkSet"):]
    block = block[:block.index(");")]
    return {k: v for k, v in re.findall(r"(\w+): Color\(0x([0-9A-F]{8})\)", block)}


def test_dark_palette_is_claude_like():
    d = _dark()
    assert d["bg"] == "FF141413" and d["ink"] == "FFE6E5E1" and d["pill"] == "FF3A3936"
    assert d["nav"] == d["surface"] == "FF1E1E1C"
    light = (ROOT / "lib/ui/hoola_theme.dart").read_text()
    assert "bg: Color(0xFFFAF9F6)" in light and "pill: Color(0xFF1B1A17)" in light, "light untouched"


def test_wired():
    assert "dark_like_claude_test.dart" in (ROOT / ".github/workflows/app-screens.yml").read_text()
    assert "activeTrackColor: c.pill" not in (ROOT / "lib/ui/shell/hoola_sessions.dart").read_text()


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.911.0"
    assert "version: 0.911.0+910" in (ROOT / "pubspec.yaml").read_text()
