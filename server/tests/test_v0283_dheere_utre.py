"""v0.283 DHEERE UTRE - the reply LANDS at reading speed (owner: "ALSO A RESULT SPEED :: CURRENTLY HOOLA SHOW
RESULT INSTANTLY IN FLASH IT MUST LAND SMOTLY LIKE CLAUDE").

Measured by driving the console's own Pacer in a real browser, before and after:

                        300 words, one piece   300 streamed   80 words   30 words
    before (10 ms, /25)        244 w/s             165 w/s      105 w/s     67 w/s
    after  (20 ms, /80 cap 2)   79 w/s              72 w/s       60 w/s     60 w/s
    Claude                                    roughly 40-80 w/s

The bug was never the server (api.stream -> livereply.feed, batched every 50 ms, TAIL=24: re-checked, correct).
It was the pacer's UNCAPPED catch-up term, which grew with the backlog, so the longer the answer the faster it
dumped. The phone had the same shape of bug from the other direction: a sane 28 ms a word overridden by a
1600 ms clamp ceiling, so anything over ~57 words landed in 1.6s.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_the_console_paces_at_reading_speed():
    js = (ROOT / "server/app/static/console/stream.js").read_text()
    assert "Math.floor((now - this.t) / 20)" in js          # 20 ms a word, not 10
    assert "Math.min(2, Math.floor(this.queue.length / 80))" in js   # catch-up capped, and only above 80
    assert "this.queue.length / 25" not in js               # the uncapped term is gone
    assert "/ 10)" not in js


def test_the_phone_paces_the_same_way():
    d = (ROOT / "lib/ui/chat_screen.dart").read_text()
    assert "(_words.length * 14).clamp(250, 5000)" in d
    assert "(_words.length * 28).clamp(250, 1600)" not in d  # the ceiling that dumped long replies


def test_the_three_instant_paths_are_untouched():
    """A hidden tab, the reply's end and a reset still show everything at once - pacing is for live words only."""
    js = (ROOT / "server/app/static/console/stream.js").read_text()
    assert "if (document.hidden)" in js
    assert "flush() {" in js and "cancelAnimationFrame(this.raf)" in js
    assert "reset() {" in js


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.325.0"
    assert "0.325.0+365" in (ROOT / "pubspec.yaml").read_text()
