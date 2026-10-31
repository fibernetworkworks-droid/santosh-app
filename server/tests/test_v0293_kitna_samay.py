"""v0.293 KITNA SAMAY - the seconds beside the working avatar (owner: "NOW A TIMING ON AVATAR THINKING").

Two clocks already existed and neither answered what she was asking for:

    tool group     "4 steps - 12 s"      only AFTER the work is finished
    Soch card      counts live           only when the model actually REASONED (v0.235 adaptive thinking,
                                         so an ordinary ask has no card at all)

For a plain wait there was no number anywhere, which means a slow turn and a stuck turn looked identical. The new
clock starts with the TURN and runs across every phase, so it reads total elapsed rather than time-in-this-step.
It stays blank for the first second so a quick reply never flashes "0s". Checked in a browser driving the real
code: 1s / 2s / 3s / 4s on the tick, tabular figures, and the label never moves as the number grows.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CON = ROOT / "server/app/static/console"


# ---------------------------------------------------------------- the console
def test_the_row_carries_a_clock():
    js = (CON / "v2.js").read_text()
    assert "secs.className='progress-secs'" in js
    assert "SIMPLE_PROGRESS.append(label,dots,secs)" in js      # v0.299 dropped the avatar from this row
    assert "PROGRESS_TIMER=setInterval(progressTick,1000)" in js


def test_the_clock_starts_with_the_turn_and_is_blank_under_a_second():
    js = (CON / "v2.js").read_text()
    assert "PROGRESS_T0=Date.now()" in js
    assert "const s = Math.floor((Date.now() - PROGRESS_T0) / 1000);" in js
    assert "const want = s >= 1 ? fmtSecs(s) : '';" in js        # no "0s" flash on a fast reply


def test_the_format_turns_over_at_a_minute():
    """fmtSecs is pure, so the rule itself is checked rather than a screenshot of it."""
    js = (CON / "v2.js").read_text()
    m = re.search(r"function fmtSecs\(s\) \{ return (.+?); \}", js)
    assert m, "fmtSecs moved"
    body = m.group(1)
    assert "s < 60 ? s + 's'" in body
    assert "Math.floor(s / 60) + 'm '" in body and "padStart(2, '0') + 's'" in body


def test_the_clock_dies_with_the_row():
    js = (CON / "v2.js").read_text()
    line = [ln for ln in js.splitlines() if ln.startswith("function clearSimpleProgress()")]
    assert len(line) == 1 and "clearInterval(PROGRESS_TIMER)" in line[0], line


def test_the_numbers_do_not_jiggle_and_the_label_is_what_is_read_aloud():
    css = (CON / "v2.css").read_text()
    rule = [ln for ln in css.splitlines() if ln.startswith("#app .progress-secs{")]
    assert len(rule) == 1
    assert "font-variant-numeric:tabular-nums" in rule[0]
    assert "color:var(--dim)" in rule[0]                          # quieter than the label
    js = (CON / "v2.js").read_text()
    assert "secs.setAttribute('aria-hidden','true')" in js        # a number changing every second is not news


# ---------------------------------------------------------------- the phone
def test_the_phone_counts_the_same_way():
    d = (ROOT / "lib/ui/chat_screen.dart").read_text()
    assert "Timer? _clock;" in d
    assert "Timer.periodic(const Duration(seconds: 1)" in d
    assert "static String fmtSecs(int s) => s < 60 ? '${s}s'" in d
    assert "if (_secs >= 1) ..." in d                             # the same blank first second
    assert "FontFeature.tabularFigures()" in d
    assert "import 'dart:ui' show FontFeature;" in d              # not relied on via material's re-exports
    assert "_clock?.cancel();" in d


# ---------------------------------------------------------------- nothing earlier is undone
def test_the_two_older_clocks_still_exist():
    js = (CON / "v2.js").read_text()
    assert "thought for" in js                                    # v0.171 Soch card
    assert "step${g.n > 1 ? \"s\" : \"\"} · ${secs < 1 ? '<1' : secs} s" in js   # the tool group's own total
    assert "ThinkCard" in (ROOT / "lib/ui/think_card.dart").read_text()


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.340.0"
    assert "0.340.0+380" in (ROOT / "pubspec.yaml").read_text()
