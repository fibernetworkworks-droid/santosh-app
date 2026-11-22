"""v0.916 STUDIO SLAB: the Every studio card is a still thick glass slab (design C)."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HOME = ROOT / "lib/ui/create/create_home.dart"


def test_slab_is_still_glass_with_its_heading_inside():
    s = HOME.read_text()
    assert "class _SlabGlass extends CustomPainter" in s
    assert "_TrayLight" not in s, "the slab never moves"
    assert "const CrHead('Every studio'" not in s and "Text('Every studio'" in s
    assert "tools'" in s and "crGlass(c, radius: 32, strong: true" in s
    assert "beat: _beatOf(i)" in s, "the drawings keep their moves"


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.999.113"
    assert "version: 0.999.113+1108" in (ROOT / "pubspec.yaml").read_text()
