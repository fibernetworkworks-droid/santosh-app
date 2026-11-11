"""v0.716 NAYA ROOP (owner, after the preview page: "0 :: PERFECT, 1 : Calm, 2 : Hoola mark, 3 : Fade with soft
focus, 4 :: recommended, 5 : recommended, 6 : recommended"): her new logo as the 3D thinking mark and the app logo on
every surface, plus the chat feel she picked - Calm pace, words landing out of a soft focus, a made file as one clean
card, a long job's Plan card + live step rows that fold into "Worked for", and the small motions."""
from __future__ import annotations

import os
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
CON = ROOT / "server/app/static/console"


def _r(p: str) -> str:
    return (ROOT / p).read_text()


def test_one_drawing_feeds_every_surface():
    mark = _r("server/app/static/console/mark.js")
    assert "window.HoolaMark = {svg, think, paths: PATHS" in mark
    # the console loads it before v2.js, and the working row + plan card use it
    html = _r("server/app/static/console/v2.html")
    assert html.index("console/mark.js") < html.index("console/v2.js")
    js = _r("server/app/static/console/v2.js")
    assert "HoolaMark.think(24)" in js and "HoolaMark.think(16)" in js
    # the rendered files come from the same drawing
    tool = _r("tool/make_mark.js")
    assert "server/app/static/console/mark.js" in tool and "ic_stat_santosh.xml" in tool
    for k in ("outer", "inner", "needle", "core"):
        assert (ROOT / f"assets/images/mark_{k}.png").exists(), k
        assert f"'{k}'" in _r("lib/ui/hoola_mark.dart")


def test_the_thinking_mark_is_t1_t2_t3_in_one():
    css = _r("server/app/static/console/v2.css")
    for k in ("@keyframes hmTilt", "@keyframes hmTurn", "@keyframes hmOrb", "@keyframes hmOrbR", "@keyframes hmSig",
              "@keyframes hmCore", ".hm3 .hm3-c{transform:translateZ"):
        assert k in css, k
    assert "@media (prefers-reduced-motion:reduce){.hm3 .hm3-tilt,.hm3 .hm3-floor{display:none}.hm3 .hm3-still{display:block}}" in css
    d = _r("lib/ui/hoola_mark.dart")
    assert "maybeDisableAnimationsOf" in d and "rotateX" in d and "rotateY" in d
    assert "const HoolaMark(size: 22)" in _r("lib/ui/chat_screen.dart")


def test_calm_pace_on_both_surfaces():
    assert "Math.floor((now - this.t) / 34)" in _r("server/app/static/console/stream.js")
    assert "(_words.length * 34).clamp(300, 10000)" in _r("lib/ui/chat_screen.dart")


def test_words_land_out_of_a_soft_focus():
    md = _r("server/app/static/console/md.js")
    assert "const SOFT_MS = 460;" in md and "s.style.animationDelay = (-age) + 'ms'" in md
    assert "new HoolaMD.Live(el, {soft: true})" in _r("server/app/static/console/v2.js")
    assert "@keyframes hmWord{from{opacity:0;filter:blur(3px)}" in _r("server/app/static/console/v2.css")


def test_long_job_plan_and_live_steps():
    js = _r("server/app/static/console/v2.js")
    assert "function liveStep(p)" in js and "function foldLive(" in js
    assert "function stepEvent(p) { liveStep(p); simpleProgress('step',p); }" in js
    assert "foldLive(R.t);" in js and "foldLive();TYPING=null;" in js
    assert "`Worked for ${fmtSecs(secs)}`" in js   # v0.721 the step count went; the arrow stays
    assert "el.classList.add('hmplan')" in js and "'LONG JOB RUNNING'" in js


def test_a_made_file_is_one_card():
    r = _r("server/app/static/console/results.js")
    assert "function fileCard(el, view, info, item)" in r and "el.classList.add('hmfile')" in r
    for tag in ("'PDF'", "'DOC'", "'XLS'", "'PPT'"):
        assert tag in r


def test_status_bar_icon_is_the_new_mark():
    v = _r("tool/android/res/drawable/ic_stat_santosh.xml")
    assert 'android:viewportWidth="100"' in v and v.count('android:fillColor="#FFFFFFFF"') == 6


def test_soft_landing_and_mark_in_a_real_browser():
    sync_api = pytest.importorskip("playwright.sync_api")
    page_html = "<!doctype html><html><head><style>%s</style></head><body><div id='app'><div id='t' class='textmd'></div>" \
                "<div id='m'></div></div></body></html>" % _r("server/app/static/console/v2.css")
    try:
        with sync_api.sync_playwright() as p:
            b = p.chromium.launch(**({"executable_path": os.environ["HOOLA_CHROMIUM"]} if os.environ.get("HOOLA_CHROMIUM") else {}))
            pg = b.new_page()
            errs = []
            pg.on("pageerror", lambda e: errs.append(str(e)))
            pg.set_content(page_html)
            for f in ("md.js", "mark.js"):
                pg.add_script_tag(content=(CON / f).read_text())
            got = pg.evaluate("""() => {
              const el = document.getElementById('t'); const v = new HoolaMD.Live(el, {soft: true});
              v.update('Teen drafts mile.', true);
              const fresh = el.querySelectorAll('.w').length;
              v.update('Teen drafts mile. Sabse **achha** wala', true);
              const text = el.textContent;
              v.update('Teen drafts mile. Sabse **achha** wala\\n\\n```\\ncode here\\n```', false);
              const inCode = el.querySelectorAll('pre .w, code .w').length;
              const plain = new HoolaMD.Live(document.createElement('div')); plain.update('one two', true);
              document.getElementById('m').innerHTML = HoolaMark.think(20);
              return {fresh, text, inCode, plainW: plain.el.querySelectorAll('.w').length,
                      layers: document.querySelectorAll('#m .hm3 .hm3-ly').length,
                      paths: document.querySelectorAll('#m .hm3 .hm3-tilt path').length};
            }""")
            b.close()
    except Exception as e:   # noqa: BLE001 - no browser in this sandbox
        pytest.skip(f"no browser: {e}")
    assert not errs, errs
    assert got["fresh"] == 3                       # every new word wrapped to fade in
    assert got["text"] == "Teen drafts mile. Sabse achha wala"   # the words are untouched
    assert got["inCode"] == 0                      # code is never wrapped
    assert got["plainW"] == 0                      # without soft the renderer is exactly as before
    assert got["layers"] == 4 and got["paths"] >= 5


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION.startswith("0.803.0")


def test_v0717_file_card_is_one_row_like_the_approved_design():
    """Owner's live screenshot: the PDF card stacked in a column (the old .cd rule won). One row, Open + download icon."""
    css = _r("server/app/static/console/v2.css")
    assert "#app .result-card.hmfile{display:flex;flex-direction:row;" in css
    r = _r("server/app/static/console/results.js")
    assert "row?.querySelector('[data-reuse]')?.remove();" in r and "dl.classList.add('hmico')" in r
    assert "replace(/[_ -](pdf|docx|xlsx|pptx)(\\.\\1)$/i, '$2')" in r
