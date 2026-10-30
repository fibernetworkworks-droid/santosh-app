"""v0.234.0 one avatar while Hoola replies; no greeting row in the console thread."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CON = ROOT / "server/app/static/console"


def test_empty_reply_row_hidden():
    css = (CON / "v2.css").read_text()
    assert "#app .mh:has(>.bd:empty){display:none}" in css
    js = (CON / "v2.js").read_text()
    assert "TURN.bd.childElementCount>0" in js          # the progress row keeps its avatar under an empty reply row


def test_greeting_never_drawn():
    js = (CON / "v2.js").read_text()
    assert "if (p.source === 'greeting') return;" in js
    assert "else if (!any || p.source === 'greeting') continue;" in js


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.278.0"
    assert "0.278.0+318" in (ROOT / "pubspec.yaml").read_text()
    # v0.240: follow the release instead of a hardcoded number, so a version bump cannot fail this
    assert (CON / "v2.html").read_text().count(f"?v={APP_VERSION}") == 14   # v0.243 + theme.js, v0.248 + pdfview.js, v0.259 + studio.js
