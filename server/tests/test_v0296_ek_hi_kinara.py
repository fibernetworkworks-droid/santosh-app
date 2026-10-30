"""v0.296 EK HI KINARA - the working row lines up with the reply above it (owner, with a screenshot of the new
clock: "now check the position of working after one responce by hoola - make all the rsponsece inline with that
woing now from both side properly").

Measured in a browser, not guessed. It was THREE misalignments, not one:

    "Working on it..." vs the sentence above it      44.0px right   -> 0.0
    the working avatar vs the reply avatar           46.0px right   -> 0.0
    the working row standing on its own              48.0px right   -> 0.0

The cause is v0.252. At a thread width of 980px and up, `#app .mh` is pulled `margin-left:-44px` so the reply's
words begin at the column edge and the avatar hangs OUTSIDE the column. `.simple-progress` never got that pull,
so it stayed where the column starts - exactly 44px to the right. The extra 2px and 4px came from
`.progress-avatar` being a 34px box where the message row's `.av` is 30px.

The phone was deliberately left alone: its typing indicator is a 74px bouncing avatar beside a rounded bubble,
not a flush row, so the same alignment does not translate. That was put to her rather than changed quietly.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CSS = (ROOT / "server/app/static/console/v2.css")


def _css() -> str:
    return CSS.read_text()


def test_the_working_row_is_pulled_with_the_message_row():
    css = _css()
    m = re.search(r"@container thread \(min-width: 980px\)\{(.+?)\n\}", css, re.S)
    assert m, "the container query moved"
    body = m.group(1)
    assert "#app .mh{margin-left:-44px;width:calc(100% + 44px);max-width:none}" in body
    assert "#app .simple-progress{margin-left:-44px;width:calc(100% + 44px)}" in body


def test_the_working_avatar_takes_the_same_slot_as_the_reply_avatar():
    """30px box + the 14px gap = the 44px the message row uses. The ring is drawn outside, so it still reads 34."""
    css = _css()
    av = [ln for ln in css.splitlines() if ln.startswith("#app .progress-avatar{")]
    assert len(av) == 1 and "width:30px;height:30px" in av[0], av
    assert "34px" not in av[0]
    msg = [ln for ln in css.splitlines() if ln.startswith("#app .mh>.av{")]
    assert msg and "width:30px;height:30px" in msg[0], msg          # the two now match
    img = [ln for ln in css.splitlines() if ln.startswith("#app .progress-avatar img{width:30px")]
    assert len(img) == 1 and "margin:0" in img[0], img              # the 2px inset went with the 34px box
    gap = [ln for ln in css.splitlines() if ln.startswith("#app .simple-progress{gap:")]
    assert gap and "gap:14px" in gap[0], gap


def test_the_glow_ring_still_sits_outside_the_box():
    """The circle must still LOOK 34px wide - only the slot changed."""
    css = _css()
    ring = [ln for ln in css.splitlines() if ln.startswith("#app .progress-avatar:before{")]
    assert ring, "the ring rule moved"
    assert any("inset:-2px" in ln or "inset:-3px" in ln for ln in ring), ring


def test_the_hidden_avatar_in_tail_mode_still_holds_the_same_44px():
    css = _css()
    tail = [ln for ln in css.splitlines() if ".simple-progress.tail .progress-avatar{" in ln]
    assert tail and "width:30px" in tail[0], tail


def test_v0293_clock_is_untouched():
    css = _css()
    assert "#app .progress-secs{" in css and "font-variant-numeric:tabular-nums" in css
    js = (ROOT / "server/app/static/console/v2.js").read_text()
    assert "PROGRESS_TIMER=setInterval(progressTick,1000)" in js


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.296.0"
    assert "0.296.0+336" in (ROOT / "pubspec.yaml").read_text()
