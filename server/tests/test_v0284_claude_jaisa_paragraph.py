"""v0.284 CLAUDE JAISA PARAGRAPH (owner: "STILL PARAGRAP, WORD SETUP AND GAP AT PROPER INTERVAL IN NOT PROPER ---
CHECK HOW CLUDE CHAT DO THIS PROPERLY --- PERFECT PARAGRAP, WORDING, GAP, SPACING ETC --- CLONE SAME AS IT IS").

v0.274 / v0.276 / v0.278 / v0.281 measured every NUMBER against her Claude screenshots and matched them - paragraph
gap 16px, 24 above a heading / 8 below, prose 680px, turn gap 61px, bullet gutter 30px. She still reported the
reply reading wrong, and she was right: the remaining faults were in the RENDERER, which no CSS measurement could
see, because the probe pages those versions used wrote each paragraph as a single source line.

Three faults, all found by running her own md.js and reading the computed styles back out of a real browser:

1. A single newline inside a paragraph became a <br>. CommonMark - which Claude's chat follows - calls that a SOFT
   break: the lines join with a SPACE and the paragraph reflows to the column. So wherever the model wrapped its
   own output, that wrap froze into the page as a short ragged line with NO gap under it, sitting right beside
   real paragraphs that had 16px. That is "word setup" and "gap at proper interval" in one bug.
2. The heading hierarchy was upside down. md.js maps # -> h3, ## -> h4, ### -> h5, and `.textmd h3.mdh` was pinned
   at 17px while h4 / h5 kept the 20px default, so a reply's own title came out SMALLER than its sections.
3. A reply used two typefaces. `#app h1,#app h2,#app h3{font-family:var(--fb)}` (console chrome) outranks
   `.textmd .mdh` on specificity, so the # heading rendered in the interface sans with tightened tracking while
   ## and ### stayed in the serif.

Measured after the fix, in the browser: 0 <br> in a wrapped reply, paragraphs reflowing to 625-658px of the 680px
column, headings 22 / 20 / 17 at weight 600 all in Literata at normal tracking, block gaps 16 / 24 / 8.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CON = ROOT / "server/app/static/console"


# ---------------------------------------------------------------- 1. the soft break
def test_a_wrapped_paragraph_reflows_instead_of_freezing_the_models_wrap():
    js = (CON / "md.js").read_text()
    assert ".replace(/<\\/p><p>/g, '<br>')" not in js and '.replace(/<\\/p><p>/g,' not in js
    assert "a single newline inside a paragraph is a SOFT break" in js
    assert "hard ? '<br>' : ' '" in js                      # only an explicit hard break stays a break
    assert "/(\\s{2,}|\\\\)$/" in js                        # two trailing spaces, or a backslash


def test_a_wrapped_list_item_joins_with_a_space_too():
    js = (CON / "md.js").read_text()
    assert "+ ' ' + inline(streaming && k === lines.length - 1" in js
    assert "+ '<br>' + inline(" not in js


def test_the_phone_follows_the_same_rule():
    md = (ROOT / "lib/ui/md_text.dart").read_text()
    assert "String _soft(List<String> lines)" in md
    assert "MdBlock('p', _soft(para))" in md
    assert "MdBlock('quote', _soft(q))" in md
    assert "para.join('\\n')" not in md and "q.join('\\n')" not in md
    assert "b.write(hard ? '\\n' : ' ')" in md


# ---------------------------------------------------------------- 2. the heading hierarchy
def test_the_heading_sizes_run_the_right_way_round():
    css = (CON / "v2.css").read_text()
    size = lambda sel: int(re.search(re.escape(sel) + r"\{font-size:(\d+)px", css).group(1))
    h3, h4 = size(".textmd h3.mdh"), size(".textmd h4.mdh")
    h5 = int(re.search(r"\.textmd h5\.mdh,\.textmd h6\.mdh\{font-size:(\d+)px", css).group(1))
    assert h3 > h4 > h5, (h3, h4, h5)                       # # is the biggest, ### the smallest
    assert (h3, h4, h5) == (22, 20, 17)                     # the three sizes the phone already uses
    md = (ROOT / "lib/ui/md_text.dart").read_text()
    assert "b.level <= 1 ? 22.0 : b.level == 2 ? 20.0 : 17.0" in md   # both surfaces agree


# ---------------------------------------------------------------- 3. one typeface in a reply
def test_a_reply_heading_is_the_serif_like_the_rest_of_the_reply():
    css = (CON / "v2.css").read_text()
    assert "#app .textmd .mdh{font-family:var(--fr);letter-spacing:normal}" in css
    # it must come AFTER the chrome rule it is correcting, and that rule is left alone for the chrome
    chrome = css.index("#app h1,#app h2,#app h3,#app .vh h2")
    assert css.index("#app .textmd .mdh{font-family") > chrome


# ---------------------------------------------------------------- nothing earlier is undone
def test_the_measured_numbers_from_v0274_to_v0281_still_hold():
    css = (CON / "v2.css").read_text()
    assert ".textmd p{margin:0 0 16px}" in css                        # v0.274
    assert "margin:24px 0 8px" in css
    assert "padding-left:30px" in css                                 # v0.281 bullet gutter
    assert "--fr:'Literata'" in css                                   # v0.253
    assert "max-width:680px" in css                                   # v0.276


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.291.0"
    assert "0.291.0+331" in (ROOT / "pubspec.yaml").read_text()
