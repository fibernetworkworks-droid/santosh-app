"""v0.276 PADHNE KI CHAUDAI - the reading width (owner: "GO WIDTH", after v0.274 SAAF JAGAH fixed the spacing).

v0.274 measured everything except this and left the width alone on purpose. Measured properly now, with Literata
16px in a real browser: one character averages 7.45px, so

    880px (what we had)   118 characters a line
    680px (this version)   91
    674px (Claude's own)   90

118 is far past any comfortable measure - the eye loses the start of the next line. (v0.274's note said "~95
characters"; that estimate was wrong, the real figure is 118.)

The COLUMN stays 880px so the words still start at the composer's left edge, which is what v0.252 was for; only
the PROSE wraps at 680. A table, a code block or a card keeps the full width - those are read by scanning across,
not line by line, and Claude's own answer does the same.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CON = ROOT / "server/app/static/console"


def _css() -> str:
    return (CON / "v2.css").read_text()


def test_the_prose_wraps_at_claudes_measure():
    css = _css()
    rule = [ln for ln in css.splitlines() if ln.startswith("#app .mh .txt>p,")]
    assert len(rule) == 1, rule
    assert "max-width:680px" in rule[0]
    for part in (".txt>p", ".txt>ul", ".txt>ol", ".txt>.mdh", ".txt>blockquote"):
        assert part in rule[0], part


def test_a_table_and_a_code_block_keep_the_full_width():
    """They are scanned across, not read line by line - capping them would squeeze the columns."""
    rule = [ln for ln in _css().splitlines() if ln.startswith("#app .mh .txt>p,")][0]
    for never in (">table", ">pre", ">.cb", ">.tools"):
        assert never not in rule, never


def test_the_column_still_lines_up_with_the_composer():
    """v0.276 left the column flush with the composer and shortened only the PROSE. In v0.299 the owner asked for
    the chat to sit slightly INSIDE the box she types in, so the column is 848 against the composer's 880 - 16px
    in on each side. The prose cap below is untouched and is still the thing that sets the reading line."""
    css = _css()
    assert "#app .col{width:min(848px,calc(100% - 20px))" in css
    assert "#app #slotDock{width:min(880px,100%)" in css          # the composer itself never moved


def test_v0274_spacing_is_untouched():
    css = _css()
    assert "margin:0 0 16px}" in [ln for ln in css.splitlines() if ln.startswith(".textmd p{")][0]
    assert "margin:24px 0 8px" in [ln for ln in css.splitlines() if ln.startswith(".textmd .mdh{")][0]
    assert "gap:8px" in [ln for ln in css.splitlines() if ln.startswith(".textmd ul,.textmd ol{")][0]


def test_the_type_is_untouched():
    css = _css()
    assert "--fr:'Literata'" in css
    live = [ln for ln in css.splitlines() if ln.startswith("#app .mh .txt{") and "font-family" in ln]
    assert len(live) == 1 and "font-size:16px" in live[0] and "line-height:1.5" in live[0]


def test_the_phone_needs_no_cap():
    """A phone screen is 360-430px wide, far under 680, so the cap would never fire; md_text.dart is left alone."""
    md = (ROOT / "lib/ui/md_text.dart").read_text()
    assert "? 8 : 16)" in md                                      # v0.274's spacing, still there
    assert "maxWidth" not in md or "680" not in md


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.307.0"
    assert "0.307.0+347" in (ROOT / "pubspec.yaml").read_text()
