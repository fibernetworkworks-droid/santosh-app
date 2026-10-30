"""v0.252.0 the console conversation column is exactly the composer's width (Claude-style)."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CSS = (ROOT / "server" / "app" / "static" / "console" / "v2.css").read_text()


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.296.0"
    assert "0.296.0+336" in (ROOT / "pubspec.yaml").read_text()


def test_column_matches_the_composer():
    tail = CSS[CSS.index("v0.249 ONE READING WIDTH"):]
    assert "#app .col{width:min(880px,calc(100% - 20px));max-width:none;" in tail
    assert "#app #slotDock{width:min(880px,100%)" in CSS                    # the composer's own width
    assert "#app .thread{container-type:inline-size;container-name:thread}" in tail
    assert "@container thread (min-width: 980px)" in tail and "#app .mh{margin-left:-44px;width:calc(100% + 44px)" in tail
    assert "#app .thread{scrollbar-gutter:stable both-edges}" in CSS       # the -20px assumes these gutters
    assert CSS.count("{") == CSS.count("}")
