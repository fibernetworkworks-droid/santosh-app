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


# v0.299 SUPERSEDED THE MECHANISM, NOT THE GOAL. The owner then asked for the avatar to go from the chat
# entirely, so there is no face to align and no 44px slot to match: the row simply sits in the column like every
# other row, and the label starts on the reply's own left edge because nothing is pulled any more. The four tests
# that pinned the pull, the 30px avatar box, its glow ring and the hidden tail slot are gone with the thing they
# described. What is kept below is the GOAL they existed to protect - one left edge for the whole turn.


def test_the_working_row_starts_on_the_reply_s_own_left_edge():
    css = _css()
    js = (ROOT / "server/app/static/console/v2.js").read_text()
    assert "margin-left:-44px" not in css                  # nothing is pulled outside the column any more
    assert "progress-avatar" not in css                    # and nothing holds a slot the reply row does not
    assert "function placeProgress()" in js                # the row is positioned in one place, as the last child
    assert "col.appendChild(SIMPLE_PROGRESS)" in js


def test_the_column_is_the_one_that_sets_the_edge():
    css = _css()
    assert "#app .col{width:min(848px,calc(100% - 20px))" in css


def test_v0293_clock_is_untouched():
    css = _css()
    assert "#app .progress-secs{" in css and "font-variant-numeric:tabular-nums" in css
    js = (ROOT / "server/app/static/console/v2.js").read_text()
    assert "PROGRESS_TIMER=setInterval(progressTick,1000)" in js


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.314.0"
    assert "0.314.0+354" in (ROOT / "pubspec.yaml").read_text()
