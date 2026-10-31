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
    """v0.299 settled this differently: the owner asked for the avatar to go from the chat entirely, so there is
    no second face to avoid and no `tail` class to toggle. What still matters from v0.227 is the OTHER half of the
    rule - the progress row hides while the words stream, so there is only ever one thing saying "busy"."""
    js = _read("v2.js")
    assert "if (SIMPLE_PROGRESS) SIMPLE_PROGRESS.hidden = true;" in js
    css = _read("v2.css")
    assert "progress-avatar" not in css and "#app .mh>.av" not in css      # gone, not merely hidden
    assert "#app .simple-progress[hidden]{display:none}" in css
    assert css.count("{") == css.count("}")


def test_version_pin():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.323.0"
    assert "0.323.0+363" in (ROOT / "pubspec.yaml").read_text()
