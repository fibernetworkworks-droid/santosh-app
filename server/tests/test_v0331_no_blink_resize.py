"""v0.331 NO BLINK + DRAG TO RESIZE (owner, with a screenshot of Create > Video: "YOUR VIDEO SECTION VIDEO BOX IS CONTINUOUSLY GOING
AND COMING BACK AFTER FEW INTERVAL" + "SLIDER FROM BOTH SIDE ... PROMPT WORKING SECTION WILL GET BIGGER AREA").
Root cause measured in the browser: the 4-15 s poll rebuilt every tile of "Your videos" (0 of 7 tiles kept after one poll), so
every video reloaded = the grid blinked. Now only a tile whose content changed is rebuilt (7 of 7 kept), and the Director film
page skips its 5 s re-draw when the film did not change. Two draggable dividers: the sidebar edge and prompt panel / results."""
from __future__ import annotations

from pathlib import Path

CON = Path(__file__).resolve().parents[1] / "app" / "static" / "console"
CSS = (CON / "studio.css").read_text()
JS = (CON / "studio.js").read_text()


def test_poll_keeps_unchanged_tiles():
    assert "function patch(el, html) {" in JS and "if (el._html === html) return false;" in JS
    i = JS.index("  function drawVideos() {")
    body = JS[i:JS.index("  function watchStudio(view, draw) {")]
    assert "patch(el, (D.studio" in body and "el.innerHTML =" not in body
    assert "if (p && sig === DIR.sig) { poll = setTimeout(tick, 5000); return; }" in JS
    assert "DIR.sig = DIR.view ? JSON.stringify(DIR.view) : '';" in JS


def test_two_dividers():
    assert 'class="rz rz-side" role="separator"' in JS and "rzBind($('.rz-side'), 'sbw');" in JS
    assert "rz rz-pane" in JS and "rzBind($('.rz-pane', gen), 'pw');" in JS
    assert "sbw: {min: 200, max: () => 360, def: 248" in JS and "pw: {min: 320, max: () => Math.max(320, ($('.gen')?.clientWidth || 1200) - 360), def: 380" in JS
    assert "ArrowLeft: -16, ArrowRight: 16" in JS and "'dblclick'" in JS and "localStorage.setItem(z.key" in JS
    blk = CSS[CSS.index("v0.331 DRAG TO RESIZE"):]
    assert "#shell:not(.collapsed){grid-template-columns:var(--sbw,248px) 1fr}" in blk
    assert ".gen{position:relative;grid-template-columns:minmax(0,var(--pw,380px)) minmax(0,1fr)}" in blk
    assert "@media (max-width:900px){.rz{display:none}.gen{grid-template-columns:1fr}#shell:not(.collapsed){grid-template-columns:1fr}}" in blk
    assert "infinite" not in blk and "backdrop-filter" not in blk
