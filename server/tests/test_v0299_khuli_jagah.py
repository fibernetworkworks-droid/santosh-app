"""v0.299 KHULI JAGAH - three asks in one message, and the first and third were one problem.

    1) "PANEL WHERE CHAT LANDS ... IS EXCEEDING THE SIZE LENGHT OF CHAT BOX MAKE IT SLIGH INSIDE"
    2) "WHEN HOOLA PERFECOM LONG TASK THE LODING, THINGING SECTION GET HIDE FOR WHILE - FIND ROUTE CAUSE AND FIX"
    3) "REMOVE AVATHAR ICON ENTIERLY FROM CHAT SPACE"

(1) and (3): v0.252 pulled the reply row `margin-left:-44px` so the AVATAR could hang outside the column while
the words still began at the composer's left edge. That pull is exactly why the row measured 924px against the
composer's 880 and stuck 44px past its left edge. Remove the face and the overhang has no reason to exist.
Measured in a browser, composer 236.5..1116.5 both times:

                               row              past the composer        avatars
    before      192.5..1116.5 (924px)      44px out on the left             2
    after       252.5..1100.5 (848px)      16px INSIDE on both sides        0

(2) The root cause, found in code rather than guessed: `seg()` hides the progress row the moment a text block
starts streaming - which is right, the words themselves show it is working - but NOTHING ever brought it back.
It was only un-hidden by the NEXT progress event. So a long job read: narration line arrives, row hides, a
40-second tool runs with no events to send, and the screen sits dead with no loader and no clock until the next
step. `placeProgress()` is now called again the moment a block finishes streaming while the turn is still live.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CON = ROOT / "server/app/static/console"


def _js() -> str:
    return (CON / "v2.js").read_text()


def _css() -> str:
    return (CON / "v2.css").read_text()


# ---------------------------------------------------------------- 3. the avatar is gone, not hidden
def test_no_avatar_is_drawn_in_the_chat():
    js = _js()
    assert 'd.innerHTML = `<div class="bd"></div>`;' in js          # the reply row builds without a face
    assert "avatar.className='progress-avatar av'" not in js        # nor does the working row
    assert "SIMPLE_PROGRESS.append(label,dots,secs)" in js


def test_the_dead_avatar_rules_were_deleted_not_left_behind():
    """The v0.294 lesson: a stale rule for something that no longer exists misleads the next change."""
    css = _css()
    for dead in ("progress-avatar", "#app .mh>.av", ".simple-progress.tail"):
        assert dead not in css, dead
    assert css.count("{") == css.count("}")


# ---------------------------------------------------------------- 1. inside the composer
def test_the_chat_sits_inside_the_box_she_types_in():
    css = _css()
    col = [ln for ln in css.splitlines() if ln.startswith("#app .col{width:min(")]
    assert len(col) == 1 and "min(848px,calc(100% - 20px))" in col[0], col
    assert "#app #slotDock{width:min(880px,100%)" in css              # the composer itself is untouched
    assert "margin-left:-44px" not in css                             # the overhang went with the avatar


# ---------------------------------------------------------------- 2. the loader never goes silent
def test_the_loader_comes_back_when_a_block_finishes():
    js = _js()
    assert "if (fin && TYPING) placeProgress();" in js
    assert "function placeProgress()" in js
    assert "SIMPLE_PROGRESS.hidden=false" in js


def test_the_hide_while_words_stream_is_still_there():
    """The hiding itself was never the bug - only that nothing undid it. Keep one 'busy' signal at a time."""
    assert "if (SIMPLE_PROGRESS) SIMPLE_PROGRESS.hidden = true;" in _js()


def test_the_clock_and_the_row_still_die_with_the_turn():
    js = _js()
    line = [ln for ln in js.splitlines() if ln.startswith("function clearSimpleProgress()")]
    assert len(line) == 1 and "clearInterval(PROGRESS_TIMER)" in line[0] and "SIMPLE_PROGRESS=null" in line[0]


# ---------------------------------------------------------------- nothing earlier is undone
def test_v0293_clock_and_v0286_renderer_still_stand():
    css, js = _css(), _js()
    assert "#app .progress-secs{" in css and "font-variant-numeric:tabular-nums" in css
    assert "PROGRESS_TIMER=setInterval(progressTick,1000)" in js
    assert "function nodesOf(html)" in (CON / "md.js").read_text()
    assert "max-width:680px" in css                                   # v0.276 prose width


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.321.0"
    assert "0.321.0+361" in (ROOT / "pubspec.yaml").read_text()
