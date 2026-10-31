"""v0.323 STUDIO HOME + DIRECTOR (Phase 2 of the Create Studio design audit): the ask box carries its mode's settings and
price, rails show arrows only where more is hidden, pictures paint on the FIRST open, Film projects is the Director's list
(search + sort, the step in words, Continue), and one film shows its next step with the price under the steps, a
timeline of its shots, time ranges on every shot, a More menu, and failed shots in plain words."""
from __future__ import annotations

from pathlib import Path

CON = Path(__file__).resolve().parents[1] / "app" / "static" / "console"
CSS = (CON / "studio.css").read_text()
JS = (CON / "studio.js").read_text()
BLK = CSS[CSS.index("v0.320 PHASE 2: HOME + DIRECTOR"):]


def test_home_ask_box_settings_and_price():
    assert "const hsList = m => ({" in JS and "const hsPrice = m =>" in JS and '<span class="hset" id="homeSet">${hsHTML()}</span>' in JS
    assert "director: 'Storyboard free'" in JS and "image: '~' + inr(imgCost())" in JS
    assert "$('#homeSet').innerHTML = hsHTML();" in JS and "if (b.dataset.hs) {" in JS
    assert "#homeAgent{display:none}" in BLK                          # one mode switch: the tabs
    assert "menu(e.currentTarget, AGENTS.map(" in JS                 # the v0.304 dropdown code stays (pinned)


def test_rails_and_first_open_painting():
    assert "function rails(root = R)" in JS and "rails(el);" in JS
    assert "r.classList.toggle('canr', t.scrollLeft + t.clientWidth < t.scrollWidth - 4)" in JS
    assert ".rail.canl .rarr.prev,.rail.canr .rarr.next{opacity:1;pointer-events:auto}" in BLK
    # the studio opens hidden: every canvas used to stay an unpainted 300x150 on the first open
    assert "new ResizeObserver(es => es.forEach(e => { if (e.target.clientWidth) paint(e.target); }))" in JS
    assert "artRO?.observe(c)" in JS and "artRO?.disconnect(); VIEW = v;" in JS


def test_one_film_list():
    assert "if (v === 'projects') { DIR.project = ''; DIR.view = null; v = 'director'; }" in JS
    assert 'id="fq" type="search"' in JS and "data-fsort" in JS and "DIR.fsort === 'step'" in JS
    assert "`Step ${i + 1} of ${STEPS.length} · ${STEPS[i][1]}`" in JS and "'Continue'" in JS
    assert "return initTile(p.project);" in JS and "function initTile(name)" in JS
    assert "${art('film', 'dirhero')}" not in JS                      # the painted banner under the brief is gone
    assert ".finit{" in BLK and "color-mix(in srgb,hsl(var(--fh)" in BLK  # follows Light / Dark / System via tokens


def test_film_page_next_step_timeline_more():
    assert '<div class="nextc' in JS and 'class="create nxb" data-next=' in JS and "NEXT_WHY" in JS
    assert "function timeline(shots)" in JS and "data-jump=" in JS and 'class="scenes story"' in JS
    assert "sceneCard(s, i, t0 = 0)" in JS and '<span class="sct num">${clock(t0)} – ${clock(t0 + (+s.duration || 0))}</span>' in JS
    assert "data-dmore" in JS and "el.querySelector(`[data-${v}]`)?.click()" in JS
    assert ".nextc{" in BLK and ".tlr{" in BLK and ".tls.made{" in BLK and ".scene .sm .ib{width:32px;height:32px}" in BLK


def test_plain_shot_errors():
    assert "esc(plainErr(s.error))" in JS and 'title="${esc(s.error)}"' in JS
    assert "filtergraph" in JS and "'This shot could not be made. Try again, or change its words.'" in JS


def test_small_floor_and_crisp():
    assert "small{font-size:12.5px}" in CSS                          # a bare <small> came out 10.4px on Brand kit
    assert "infinite" not in BLK and "backdrop-filter" not in BLK and " both" not in BLK
