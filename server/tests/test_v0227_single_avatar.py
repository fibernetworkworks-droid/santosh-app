"""v0.227.3 one Hoola at a time. The 5-second comfort line (server `ack` message) used to draw its own reply row with
a second avatar beside the progress row; now it is the progress line itself. The progress row under Hoola's own reply
drops its avatar (tail), and it hides while the words stream."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONSOLE = ROOT / "server" / "app" / "static" / "console"


def _read(name: str) -> str:
    return (CONSOLE / name).read_text()


def test_ack_is_the_progress_line_not_a_reply():
    js = _read("v2.js")
    assert "if (p.ack) { if (TYPING) simpleProgress('ack', p); return; }" in js
    assert "if(kind==='ack')return 'Still working on it…';" in _read("workspace.js")


def test_progress_row_never_shows_a_second_avatar():
    js = _read("v2.js")
    assert "SIMPLE_PROGRESS.classList.toggle('tail'," in js
    assert "if (SIMPLE_PROGRESS) SIMPLE_PROGRESS.hidden = true;" in js
    css = _read("v2.css")
    assert "#app .simple-progress.tail .progress-avatar{visibility:hidden" in css
    assert "#app .simple-progress[hidden]{display:none}" in css
    assert css.count("{") == css.count("}")


def test_version_pin():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.272.0"
    assert "0.272.0+312" in (ROOT / "pubspec.yaml").read_text()
