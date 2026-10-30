"""v0.281 - the bullet gutter (owner: "FIX THE BULLET INDENT 22 TO 30").

Measured off her Claude screenshots while hunting the "not exactly as Claude does" report: every other placement
in the reply already matched on the LIVE server (paragraph pitch 40px, paragraph width 680px, reply text / tool
rows / headings all flush at the column edge, avatar hanging 44px outside, turn gap 61px). The one real mismatch
left was the bullet gutter - Claude's list text sits ~30px in from the paragraph's left edge, ours sat at 22px.

The PHONE is deliberately left at its own number: md_text.dart puts the text 20px in (4px padding + a 16px bullet
column), and 30px of a 360px phone screen is 8% of the width where Claude's 30px is 4.5% of a 674px column. The
phone is already proportionally right; forcing 30 there would eat the narrow screen.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CON = ROOT / "server/app/static/console"


def test_the_bullet_gutter_matches_claude():
    css = (CON / "v2.css").read_text()
    rule = [ln for ln in css.splitlines() if ln.startswith(".textmd ul,.textmd ol{")]
    assert len(rule) == 1, rule
    assert "padding-left:30px" in rule[0]
    assert "padding-left:22px" not in css
    # v0.274's list spacing rides along unchanged
    assert "gap:8px" in rule[0] and "margin:0 0 16px" in rule[0]


def test_the_phone_keeps_its_own_narrower_gutter():
    """20px on a 360px screen is the same share of the width as 30px on Claude's 674px column."""
    md = (ROOT / "lib/ui/md_text.dart").read_text()
    assert "padding: EdgeInsets.only(left: 4.0 + 16.0 * b.level)" in md
    assert "? 8 : 16)" in md                                   # v0.274 block spacing, still there


def test_everything_else_measured_on_live_is_untouched():
    css = (CON / "v2.css").read_text()
    assert "margin:0 0 16px}" in [ln for ln in css.splitlines() if ln.startswith(".textmd p{")][0]
    assert "#app .col{gap:44px}" in css
    assert ".textmd table,.textmd blockquote,.textmd .cb,.textmd pre{margin:0 0 16px}" in css
    assert len([ln for ln in css.splitlines() if ln.startswith("#app .mh .txt>p,")]) == 1
    assert "--fr:'Literata'" in css


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.304.0"
    assert "0.304.0+344" in (ROOT / "pubspec.yaml").read_text()
