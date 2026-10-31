"""v0.318 STUDIO DESIGN SYSTEM (Phase 1 of the Create Studio design audit): one text scale, three weights, a readable grey,
four corner sizes, 32 / 40 / 48 controls, one row style in the sidebar, a clean top bar, and phone mode tabs that never
run off the screen. Measured before: 15 text sizes, 246 texts below 4.5 : 1, 10 corner sizes, 50 controls under 30px."""
from __future__ import annotations

import re
from pathlib import Path

CON = Path(__file__).resolve().parents[1] / "app" / "static" / "console"
CSS = (CON / "studio.css").read_text()
JS = (CON / "studio.js").read_text()
POP = CSS[CSS.index(".pop{"):CSS.index("/* ---------- v0.262")]     # the v0.285 menu block keeps its own pinned values
REST = CSS.replace(POP, "")


def _px(src: str, prop: str) -> set[str]:
    found = set(re.findall(prop + r":([0-9.]+)px", src))
    for m in re.finditer(r"font:\s*(?:[0-9]{3}\s+)?([0-9.]+)px", src) if prop == "font-size" else ():
        found.add(m.group(1))
    return found


def test_one_text_scale():
    assert _px(REST, "font-size") <= {"12.5", "14", "15", "18", "26"}, _px(REST, "font-size")
    assert _px(JS, "font-size") <= {"12.5", "14", "15", "18", "26"}, _px(JS, "font-size")
    assert ".hero h1{font-size:clamp(30px,3.6vw,40px)}" in CSS and ".dhero h1{font:400 26px/1.2 var(--serif)}" in CSS


def test_three_weights_and_no_bold():
    assert "font-weight:450" not in REST and "font-weight:700" not in CSS and "font-weight:bold" not in CSS
    assert "b,strong{font-weight:600}" in CSS                       # <b> was the source of 48 texts at 700


def test_corners():
    assert set(re.findall(r"border-radius:([0-9.]+)px", REST)) <= {"8", "12", "16", "99"}


def test_readable_grey_and_status_words():
    assert ":host{--dim:color-mix(in srgb,var(--mut) 92%,var(--bg))}" in CSS      # #8B8B92 (3.4 : 1) -> ~#6A6A72 (5.4 : 1)
    for k in (".tag.new{color:color-mix(in srgb,var(--ok) 78%,var(--ink))}",
              ".tag.hot{color:color-mix(in srgb,var(--warn) 78%,var(--ink))}", ".perr,.res small.perr{color:color-mix("):
        assert k in CSS, k


def test_control_sizes():
    blk = CSS[CSS.index("v0.318 STUDIO DESIGN SYSTEM"):]
    for k in (".btn{height:40px;font-weight:500}", ".create{height:48px", ".res .acts button{width:32px;height:32px}",
              ".lnk{min-height:32px", ".sw{width:40px;height:24px}", ".sw[aria-checked=\"true\"] i{transform:translateX(16px)}",
              ".go{height:40px}", ".adv input{height:40px"):
        assert k in blk, k
    assert "infinite" not in blk and "backdrop-filter" not in blk and " both" not in blk       # CRISP TEXT


def test_sidebar_is_one_row_style():
    assert "['l', 'Studio']" not in JS                               # the first label repeated "Studio home"
    assert "TOOLS.map(([k, t, ic]) => `<button class=\"sn\" data-go=\"${k}\"" in JS and 'class="tgrid"' not in JS
    blk = CSS[CSS.index("v0.318 STUDIO DESIGN SYSTEM"):]
    assert ".agent{border:0;background:none" in blk and ".agent[aria-current=\"page\"]{background:var(--priSoft)" in blk
    assert ".sl{font-size:12.5px;font-weight:500;color:var(--dim)" in blk and ".sn{min-height:36px;font-weight:500}" in blk
    assert "left</b>" in JS and "spent · " in JS                     # credits: what is left leads, at 600


def test_top_bar_and_phone():
    top = JS[JS.index('<div class="top">'):JS.index('<div class="view" id="view">')]
    assert "pillbtn" not in top and "data-close" not in top          # Chat / My creations were duplicates of the sidebar
    assert "#view:focus,#view:focus-visible{outline:none}" in CSS    # the stray violet line under the top bar
    ph = CSS[CSS.index("@media (max-width:640px){\n  .modes"):]
    assert ".modes{display:flex;flex-wrap:wrap" in ph and "overflow:visible" in ph
