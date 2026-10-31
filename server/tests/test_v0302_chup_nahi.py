"""v0.302 CHUP NAHI - the loader comes back whatever shape the words arrived in (owner, on the DEPLOYED v0.299
fix: "WORKING NOW SECTION DISAPPER FOR WHILE DRUING THE HOOLA BACKEND WORK - FEEL NO WORK IN PROGRESS AFTER HOOLA
SHORT FEED REGARDING WORK").

She was right: v0.299 fixed half of it. That version brought the row back when a block FINISHED, hooking the
pacer's `fin` flag. Driving the REAL pacer through every delivery shape in a browser showed `fin` only fires when
the pacer was handed a FINAL text:

    A  message event (pacer.final)                  fin fires      loader came back
    B  deltas, then reply_end's flush()             NO fin         loader stayed hidden
    C  deltas, then a message final                 fin fires      loader came back
    D  deltas that simply STOP while a tool runs    NO fin         loader stayed hidden   <- her screenshot

`flush()` reports `show(shown, this.finalText !== null)`, so with no final text it passes fin=false; and in D the
queue just drains with nothing following. Both leave the screen dead for the whole silent stretch.

So `fin` was the wrong signal. "No words have arrived for a moment" is true whatever the shape: LAST_WORD_AT is
stamped every time the pacer writes, and the clock interval already running for the seconds doubles as the
watchdog - no new timer. Re-measured: A, B, C and D all end with the loader VISIBLE, and a reply that is still
streaming correctly keeps it hidden, so it never flickers on between the words of a sentence.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CON = ROOT / "server/app/static/console"


def _js() -> str:
    return (CON / "v2.js").read_text()


def test_the_watchdog_exists_and_rides_the_clock_that_was_already_running():
    js = _js()
    assert "let LAST_WORD_AT = 0;" in js
    assert "if (TYPING && SIMPLE_PROGRESS.hidden && Date.now() - LAST_WORD_AT > 600) placeProgress();" in js
    assert js.count("setInterval(progressTick,1000)") == 1          # one timer, not a second one
    assert "function progressTick()" in js


def test_every_write_stamps_the_clock():
    js = _js()
    assert "LAST_WORD_AT = Date.now();" in js
    i_cb = js.index("new HoolaStream.Pacer((text, fin) =>")
    assert js.index("LAST_WORD_AT = Date.now();", i_cb) - i_cb < 400   # inside the pacer callback


def test_the_fin_hook_is_kept_for_the_shapes_that_do_end_in_a_final():
    """The watchdog takes up to ~1.6s; when a block really is finished, come back at once."""
    assert "if (fin && TYPING) placeProgress();" in _js()


def test_the_watchdog_runs_before_the_seconds_are_drawn():
    """progressTick returns early when the clock element is missing, so the watchdog must come first."""
    js = _js()
    body = js[js.index("function progressTick()"):]
    body = body[:body.index("\n}")]
    assert body.index("placeProgress()") < body.index("querySelector('.progress-secs')")


def test_the_hide_while_words_stream_still_stands():
    """The control case: a reply still arriving must NOT flicker the loader on between its words."""
    js = _js()
    assert "if (SIMPLE_PROGRESS) SIMPLE_PROGRESS.hidden = true;" in js


def test_v0299_layout_is_untouched():
    css = (CON / "v2.css").read_text()
    assert "#app .col{width:min(848px,calc(100% - 20px))" in css
    assert "progress-avatar" not in css and "margin-left:-44px" not in css
    assert 'd.innerHTML = `<div class="bd"></div>`;' in _js()


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.314.0"
    assert "0.314.0+354" in (ROOT / "pubspec.yaml").read_text()
