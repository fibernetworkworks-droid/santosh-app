"""v0.325 STUDIO TOOLS (Phase 3 of the Create Studio design audit): one way between tools (the sidebar; the tab rows are gone),
one tool layout (380px controls, sticky price bar), Video basics + More settings with a summary, one word of status on every
clip and ONE notice for failures, pictures captioned with date / style (never the engine's name), all styles visible, Dubbing's
most-asked languages first with a counter, voices as colour marks, and the Editor's empty player as the drop zone."""
from __future__ import annotations

from pathlib import Path

CON = Path(__file__).resolve().parents[1] / "app" / "static" / "console"
CSS = (CON / "studio.css").read_text()
JS = (CON / "studio.js").read_text()
BLK = CSS[CSS.index("v0.325 PHASE 3: THE SIX TOOLS"):]


def test_one_way_between_tools():
    assert "toolTabs" not in JS and 'aria-label="Studio"' not in JS
    assert ".gen{grid-template-columns:minmax(0,380px) minmax(0,1fr)}" in BLK


def test_video_more_settings_and_status():
    assert '<details class="adv vmore"' in JS and '<span class="vsum">' in JS and "VID.more = e.target.open" in JS
    for k in ("data-vres", "data-vaudio", "data-vtake"):        # still there (v0.262 pins), just folded
        assert k in JS
    assert "function projState(p)" in JS and "['Needs attention', 'na']" in JS and "['Draft', 'dr']" in JS
    assert "stc === 'ok' ? `<span class=\"dur num\">" in JS          # no "0 s" on a clip never made
    assert "function vnote(ps)" in JS and "Nothing was charged for them." in JS and "VIEW !== 'video'" in JS
    assert ".stchip.na{" in BLK and ".vnote{" in BLK and ".prow2{grid-template-columns:minmax(0,1fr) minmax(0,1fr)}" in BLK


def test_picture_captions_and_styles():
    assert "it.meta?.model" not in JS                                # "gemini-3.1-flash-image" under every picture
    assert "[when(it.created), it.meta?.style, it.meta?.aspect].filter(Boolean)" in JS
    assert ".stys{grid-template-columns:repeat(3,minmax(0,1fr))}" in BLK and ".panel .prow b{white-space:normal" in BLK


def test_dubbing_languages_and_voices():
    assert "const DUB_TOP = ['Hindi', 'Tamil', 'Telugu', 'Bengali', 'Marathi', 'English'];" in JS
    assert "All languages</summary>" in JS and "' of 4 picked'" in JS
    assert "k === 'mine' ? art(a, 'vo' + k) : initTile(n)" in JS


def test_editor_drop_zone():
    assert 'class="framemsg drop" data-addclip' in JS and "Drop videos, photos or music here" in JS
    assert "'dragover'" in JS and "'drop'" in JS and "ED.clips.length ? 'Make the edit' : 'Add clips to start'" in JS
    assert ".framemsg.drop{" in BLK and "infinite" not in BLK and "backdrop-filter" not in BLK
