"""v0.274 SAAF JAGAH - the air between the blocks (owner: "ALSO SEE A VISUAL PROPER PLACEMENT OF SENTANCE THAT
USER CAN READ IT REALIBLY. ALSO A PERFECT PARAGRAP, SPALCING ETC. CHECK THIS FIRST", then "GO SPACING").

Her three Claude screenshots were measured block by block:

    paragraph length            1-3 lines, almost never more
    gap BETWEEN paragraphs      22-32px
    gap between lines INSIDE    6-8px
    ratio between / inside      3.2x to 4.3x        <- this is the whole trick
    line length                 median ~600px, max 674px (65-75 characters)

Hoola, measured in a real browser before this version: 2px between paragraphs against ~7px between the lines
inside one - a ratio of 0.3x. The space BETWEEN blocks was SMALLER than the space inside them, so after v0.249
(the serif), v0.253 (Literata + contrast) and v0.256 (the sidebar type) the words were right and the page still
read as one wall. Four numbers fix it, on both surfaces. The column width (880px vs Claude's ~674px) was left
alone on purpose: v0.252 set it to match the composer, and that is another session's decision to change.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CON = ROOT / "server/app/static/console"


def _css() -> str:
    return (CON / "v2.css").read_text()


def _rule(start: str) -> str:
    hit = [ln for ln in _css().splitlines() if ln.startswith(start)]
    assert len(hit) == 1, (start, hit)
    return hit[0]


# ---------------------------------------------------------------- the console
def test_a_paragraph_gets_one_line_of_air():
    assert "margin:0 0 16px}" in _rule(".textmd p{")
    assert ".textmd p:last-child{margin-bottom:0}" in _css()      # no dead space under the reply
    assert "margin:0 0 2px}" not in _css()                        # the old 2px is gone everywhere


def test_the_gap_between_blocks_beats_the_gap_inside_one():
    """The point of the whole version: between > inside. At 16px/1.5 the inside gap is ~7px, so 16px is ~2.3x."""
    import re
    m = re.search(r"\.textmd p\{[^}]*margin:0 0 (\d+)px", _css())
    assert m and int(m.group(1)) >= 14, "a paragraph gap under ~14px disappears against the line gap"


def test_a_heading_belongs_to_the_text_under_it():
    r = _rule(".textmd .mdh{")
    assert "margin:24px 0 8px" in r                               # lots above, little below
    assert ".textmd .mdh:first-child{margin-top:0}" in _css()     # never a hole at the top of a reply


def test_list_items_stop_fusing():
    r = _rule(".textmd ul,.textmd ol{")
    assert "gap:8px" in r and "margin:0 0 16px" in r
    assert "gap:3px" not in r
    assert ".textmd ul:last-child,.textmd ol:last-child{margin-bottom:0}" in _css()


# ---------------------------------------------------------------- the phone
def test_the_phone_got_the_same_air():
    md = (ROOT / "lib/ui/md_text.dart").read_text()
    assert "? 8 : 16)" in md                                      # 8 between list items, 16 between blocks
    assert "? 4 : 9)" not in md                                   # the old cramped pair is gone
    assert "SAAF JAGAH" in md


# ---------------------------------------------------------------- nothing earlier is undone
def test_the_type_itself_is_untouched():
    css = _css()
    assert "--fr:'Literata'" in css                               # v0.253
    live = [ln for ln in css.splitlines() if ln.startswith("#app .mh .txt{") and "font-family" in ln]
    assert len(live) == 1 and "font-size:16px" in live[0] and "line-height:1.5" in live[0]
    assert "--chat-ink:#1A1A1F; --chat-paper:#FFFFFF;" in css
    assert "GoogleFonts.literata" in (ROOT / "lib/ui/glass.dart").read_text()


def test_the_reading_width_was_deliberately_left_alone():
    """v0.252 made the column match the composer. v0.274 left 880px alone and put the choice to the owner; she
    said "GO WIDTH", so v0.276 capped the PROSE at 680px while this column stays 880 and keeps the composer's
    left edge. Both are true at once - see test_v0276_padhne_ki_chaudai.py."""
    assert "#app .col{max-width:880px" in _css() or "max-width:880px" in _css()


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.329.0"
    assert "0.329.0+369" in (ROOT / "pubspec.yaml").read_text()
