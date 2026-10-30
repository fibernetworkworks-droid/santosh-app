"""v0.278 PURA SAANS - the gaps v0.274 missed, and the paragraph itself (owner: "NOW LETS WORK ON PARAGRAP AND GAPS").

Measured in a real browser against her Claude screenshots, ink to ink. v0.274 gave paragraphs, headings and lists
their air; four things were still wrong, and three of them only showed up once the others were right:

    after a table          0px   -> 16px   (the next line sat on the table's last row)
    after a quote          4px   -> 16px
    after a code block     6px   -> 16px
    one turn to the next  39px   -> 61px   (Claude leaves 60px between her message and the reply's first line)

Two things were checked and found ALREADY correct, so they were left alone: the gap ABOVE a table / quote / code
(16px - the paragraph before carries it) and the gap between a narration line and a tool row (23px against
Claude's 23-26px). The `.bd` gap of 12px looked wrong on paper and measures right on screen.

And the paragraph itself: nothing in the rulebook had ever said how LONG one should be.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CON = ROOT / "server/app/static/console"


def _css() -> str:
    return (CON / "v2.css").read_text()


def test_a_table_a_quote_and_a_code_block_get_the_same_air_as_a_paragraph():
    css = _css()
    assert ".textmd table,.textmd blockquote,.textmd .cb,.textmd pre{margin:0 0 16px}" in css
    assert ".textmd table:last-child,.textmd blockquote:last-child,.textmd .cb:last-child{margin-bottom:0}" in css


def test_one_turn_is_clearly_a_new_turn():
    """39px read as one long scroll; 44px of gap gives 61px ink to ink, which is Claude's 60."""
    css = _css()
    rule = [ln for ln in css.splitlines() if ln == "#app .col{gap:44px}"]
    assert len(rule) == 1, "the turn gap must be the last .col gap rule so it wins"
    assert css.index("#app .col{gap:44px}") > css.index("#app .col{max-width:760px;gap:22px")


def test_the_gaps_that_were_already_right_were_left_alone():
    """Measured before touching them: above a table 16px, narration to tool row 23px. Both already Claude's."""
    css = _css()
    assert "#app .mh .bd{flex:1;gap:12px}" in css          # looked wrong on paper, measures right on screen
    assert "margin:0 0 16px}" in [ln for ln in css.splitlines() if ln.startswith(".textmd p{")][0]


def test_the_rulebook_says_how_long_a_paragraph_may_be():
    from app.agent import replystyle as R
    c = R.CHAT
    assert "two to four sentences, no more" in c
    assert "When the idea changes, start a new paragraph" in c
    assert "One sentence alone is a paragraph too" in c
    for other in (R.VOICE, R.QUICK):                        # a spoken answer has no paragraphs
        assert "two to four sentences" not in other
    for t in (R.CHAT, R.QUICK, R.VOICE):
        assert "{" not in t and "}" not in t


def test_v0274_and_v0276_are_untouched():
    css = _css()
    assert "margin:24px 0 8px" in [ln for ln in css.splitlines() if ln.startswith(".textmd .mdh{")][0]
    assert "gap:8px" in [ln for ln in css.splitlines() if ln.startswith(".textmd ul,.textmd ol{")][0]
    assert len([ln for ln in css.splitlines() if ln.startswith("#app .mh .txt>p,")]) == 1   # the 680px cap
    assert "--fr:'Literata'" in css


def test_the_phone_already_spaces_every_block_the_same():
    """md_text.dart puts one SizedBox between blocks whatever they are, so a table and a code block already
    get the same 16px a paragraph gets. Nothing to change there."""
    md = (ROOT / "lib/ui/md_text.dart").read_text()
    assert "? 8 : 16)" in md


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.281.0"
    assert "0.281.0+321" in (ROOT / "pubspec.yaml").read_text()
