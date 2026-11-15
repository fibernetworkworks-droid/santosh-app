"""v0.916 STUDIO SLAB: the Every studio card is a still thick glass slab (design C)."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HOME = ROOT / "lib/ui/create/create_home.dart"


def test_slab_is_still_glass_with_its_heading_inside():
    s = HOME.read_text()
    assert "the glass's thickness" in (ROOT / "lib/ui/create/create_colour.dart").read_text(), "v0.917: the slab is crGlass itself"
    assert "_TrayLight" not in s, "the slab never moves"
    assert "const CrHead('Every studio'" not in s and "Text('Every studio'" in s
    assert "tools'" in s and "crGlass(c, radius: 32, strong: true" in s
    assert "beat: _beatOf(i)" in s, "the drawings keep their moves"


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.917.0"
    assert "version: 0.917.0+916" in (ROOT / "pubspec.yaml").read_text()
