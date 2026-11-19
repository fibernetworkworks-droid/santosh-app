"""v0.918 SLAB REVERTED: v0.917's slab-everywhere is undone; the slab stays only on the Every studio card."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_slab_only_on_the_studios_card():
    colour = (ROOT / "lib/ui/create/create_colour.dart").read_text()
    assert "final slab = !d.circle" not in colour
    assert "class _SlabGlass extends CustomPainter" in (ROOT / "lib/ui/create/create_home.dart").read_text()


def test_chat_back_to_plain_surfaces():
    assert "crGlass" not in (ROOT / "lib/ui/shell/hoola_shell.dart").read_text()
    assert "crGlass" not in (ROOT / "lib/ui/chat/hoola_card.dart").read_text()


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.999.15"
    assert "version: 0.999.15+1013" in (ROOT / "pubspec.yaml").read_text()
