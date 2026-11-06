"""v0.327 STUDIO ASSETS + HELP (Phase 4 of the Create Studio design audit): Brand kit with logo upload on the page, colour pickers
with names, font choice shown in her tagline, phone + website, and a live poster / end-card preview; My creations scripts look
like a page and tiles can be ticked for Download / Delete together (with a confirm); templates show "Use this"; guides are
numbered steps; Engines shows the services and server steps only to the owner."""
from __future__ import annotations

from pathlib import Path

CON = Path(__file__).resolve().parents[1] / "app" / "static" / "console"
CSS = (CON / "studio.css").read_text()
JS = (CON / "studio.js").read_text()
V2 = (CON / "v2.js").read_text()
BLK = CSS[CSS.index("v0.327 PHASE 4: ASSETS + HELP"):]


def test_brand_kit():
    assert "No logo yet: send it in chat" not in JS                     # the old dead end
    assert "data-bklogo" in JS and "'/api/brand/logo', undefined, {form: fd}" in JS and "fd.append('clean_bg'" in JS
    assert 'type="color" id="bkc-${r}"' in JS and "data-bkfont" in JS and 'id="bkphone"' in JS and 'id="bkweb"' in JS
    assert "function bkPreview()" in JS and "onCol(p, dk, lt)" in JS and "contact: {phone: d.phone.trim(), website: d.website.trim()}" in JS
    assert ".bkposter{" in BLK and ".bkend{" in BLK and ".bkcol input[type=color]{width:48px;height:48px" in BLK


def test_my_creations_select_and_scripts():
    assert '<span class="paper"><small>Script</small>' in JS
    assert "const LSEL = new Set();" in JS and "data-pick=" in JS and "data-seldl" in JS and "data-seldel" in JS
    assert "confirm(`Delete ${ids.length} item" in JS                  # bulk delete asks first
    assert ".selbar{" in BLK and ".res .pick{" in BLK and ".btn.danger{" in BLK and ".bad{" not in BLK


def test_templates_guides_engines():
    assert '<span class="use">Use this</span>' in JS and ".tpl .use{opacity:1;transform:none}" in BLK
    assert '<ol class="gsteps">' in JS and ".gsteps{" in BLK
    assert "const OWNER = () => !!ctx.owner?.();" in JS and "OWNER() ? 'Engines' : 'What you can make'" in JS
    assert "owner: () => !!ME?.arena," in V2
    assert '<details class="eg-how">' in JS                             # folded, even for the owner
    assert "infinite" not in BLK and "backdrop-filter" not in BLK
