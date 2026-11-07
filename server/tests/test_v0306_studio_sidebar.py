"""v0.306 PREMIUM STUDIO SIDEBAR: readable labels, scrollbar only on hover, a fade only while more list is below,
the open page a violet pill with a growing bar, agent cards lift + tilt + arrow, tool icons pop, a press on every
button, one top-to-bottom entrance, a meter that fills and says the %; all of it off under reduced motion / calm."""
from __future__ import annotations

from pathlib import Path

CON = Path(__file__).resolve().parents[1] / "app" / "static" / "console"


def _blk() -> str:
    css = (CON / "studio.css").read_text()
    return css[css.index("v0.306 PREMIUM STUDIO SIDEBAR"):]


def test_motion_is_short_and_switchable():
    b = _blk()
    assert "@keyframes sidein" in b and "animation:sidein .42s var(--out) backwards" in b   # backwards: nothing held after
    assert "infinite" not in b and "backdrop-filter" not in b and " both" not in b           # CRISP TEXT
    assert "@media (prefers-reduced-motion:reduce)" in b and ":host-context(.calm)" in b


def test_states_and_presses():
    b = _blk()
    for k in (".sn[aria-current=\"page\"]::before{transform:scaleY(1)", ".agent:hover .ai{transform:rotate(-6deg) scale(1.07)}",
              ".agent:hover .ago{opacity:1", ".tg:hover .ic{transform:scale(1.14)", ":active{transform:scale(.97)",
              ".back:hover .ic{transform:translateX(-3px)}", ".snav:hover{scrollbar-color:var(--line2) transparent}"):
        assert k in b, k
    assert ".snav.fadeb{" in b and ".snav.more" not in b      # `.more` is taken by the studio's violet links


def test_js_wiring():
    js = (CON / "studio.js").read_text()
    assert "style=\"--i:${i++}\"" in js and "class=\"ago\"" in js
    assert "sn.classList.toggle('fadeb'" in js
    # v0.318: what is LEFT leads the meter, the spend sits under the bar (was "N% of this month's limit used")
    assert "left</b>" in js and "spent · " in js and "b.style.width = pct.toFixed(1) + '%'" in js
