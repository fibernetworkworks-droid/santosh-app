"""v0.252.0 the console conversation column is exactly the composer's width (Claude-style)."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CSS = (ROOT / "server" / "app" / "static" / "console" / "v2.css").read_text()


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.304.0"
    assert "0.304.0+344" in (ROOT / "pubspec.yaml").read_text()


def test_column_matches_the_composer():
    """v0.252 made the column EXACTLY the composer's width, with the reply row pulled -44px so the avatar could
    hang outside and the words still start at the composer's left edge. The owner reversed both in v0.298:
    "PANEL WHERE CHAT LANDS ... IS EXCEEDING THE SIZE LENGHT OF CHAT BOX MAKE IT SLIGH INSIDE" and "REMOVE
    AVATHAR ICON ENTIERLY FROM CHAT SPACE". The column is now 16px inside the composer on each side and there is
    no overhang, because there is no longer a face to hang. What survives is the pairing: the chat's width is
    still DERIVED from the composer's, not chosen independently."""
    tail = CSS[CSS.index("v0.249 ONE READING WIDTH"):]
    assert "#app .col{width:min(848px,calc(100% - 20px));max-width:none;" in tail
    assert "#app #slotDock{width:min(880px,100%)" in CSS                    # the composer's own width, unchanged
    assert "#app .thread{container-type:inline-size;container-name:thread}" in tail
    assert "margin-left:-44px" not in CSS                                   # the overhang went with the avatar
    assert "#app .thread{scrollbar-gutter:stable both-edges}" in CSS       # the -20px assumes these gutters
    assert CSS.count("{") == CSS.count("}")
