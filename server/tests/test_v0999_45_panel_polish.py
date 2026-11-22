"""v0.999.45 A PROFESSIONAL PREVIEW PANEL (owner: "STILL NEED POLISH AND PROFESIONALIIOM IN WEBSITE SHOW PANEL").

The address bar names the site and says it is a private draft (it said only "preview"), the desktop page fills the
stage instead of leaving an empty band under it, a phone / tablet is fitted whole, the header hides the title and the
address on a narrow panel instead of cutting them to one letter, and the Code files read as a list with a type chip."""
import os
import re
from pathlib import Path

import pytest

ST = Path(__file__).resolve().parents[1] / "app" / "static" / "console"
JS = (ST / "webstudio.js").read_text()
CSS = (ST / "webstudio.css").read_text()


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION.startswith("0.999.107")


def test_address_bar_names_the_site_and_the_draft():
    assert "${EDIT ? 'Edit mode · ' : ''}preview</span>" not in JS
    assert '<span class="un">${esc(name(v))}</span>' in JS
    assert "'Draft · not live'" in JS and "'Editing'" in JS
    assert ".url .ubadge{" in CSS and ".url .ubadge.ed{" in CSS


def test_frame_fills_the_stage_and_fits_a_device_whole():
    body = JS[JS.index("function fit()"):JS.index("function preview(")]
    assert "classList.contains('stage')" in body
    assert "h = Math.max(h, Math.floor(ah / k))" in body          # the desktop page fills the stage height
    assert "(ah - bd) / h" in body                               # a phone / tablet is scaled to fit the height too
    assert ".stage>.frame.pc{max-width:none}" in CSS


def test_narrow_header_and_code_list():
    assert "@container wpane (max-width:640px){.phd:not(.lv) .pttl{display:none}" in CSS
    assert "@container wpane (max-width:520px){.phd:not(.lv) .url{display:none}" in CSS
    assert 'class="fty ' in JS and "Pick a file to read or change" in JS
    assert ".subnav button .fty.html{" in CSS and ".code .cempty{" in CSS
    # the new block sits before the chat kit block, which must stay last
    assert CSS.index("v0.999.45 A PROFESSIONAL PREVIEW PANEL") < CSS.index("HOOLA CHAT KIT in the Web Studio")


CHROME = os.environ.get("HOOLA_CHROMIUM", "")
from tests.test_v0312_arena_screen import arena_server  # noqa: E402,F401
from tests.test_v0407_ek_dimaag import arch_env  # noqa: E402,F401
from tests.test_v0664_asli_samay import _slow_fake  # noqa: E402
from tests.test_v121_site import site_env  # noqa: E402,F401


@pytest.mark.skipif(not CHROME, reason="needs HOOLA_CHROMIUM")
def test_browser_ready_panel(arena_server, arch_env, monkeypatch):
    base, browser, key = arena_server
    monkeypatch.setenv("SITE_FULL_LOOKS", "false"); monkeypatch.setenv("SITE_PARALLEL", "2"); monkeypatch.setenv("SITE_WORKER", "true")
    from app.config import get_settings
    get_settings.cache_clear()
    from app.site import checks as C
    monkeypatch.setattr(C, "run", lambda *a, **k: (_ for _ in ()).throw(C.CheckError("no screenshots")))
    _slow_fake(monkeypatch, per=0.02, n=4)
    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    page = ctx.new_page()
    page.goto(base + "/console/web")
    page.wait_for_selector("#wsAsk", timeout=20000)
    page.fill("#wsAsk", "Sharma Sweets mithai dukaan ki website, online order WhatsApp par")
    page.keyboard.press("Enter")
    page.wait_for_selector("#ws .lks button", timeout=120000)
    page.click("#ws [data-act='pick-look']")
    page.wait_for_selector("#ws #wsPane .url .un", timeout=180000)
    page.wait_for_timeout(1200)
    assert page.inner_text("#wsPane .url .ubadge") == "Draft · not live"
    gap = page.evaluate("""() => { const st = document.querySelector('#wsPane .stage'), f = st.querySelector('.frame');
      return st.getBoundingClientRect().bottom - f.getBoundingClientRect().bottom; }""")
    assert gap < 40, gap                                         # no empty band under the desktop page
    page.click("#wsPane [data-dev='phone']"); page.wait_for_timeout(800)
    inside = page.evaluate("""() => { const st = document.querySelector('#wsPane .stage').getBoundingClientRect(),
      f = document.querySelector('#wsPane .stage .frame').getBoundingClientRect(); return f.bottom <= st.bottom + 1 && f.top >= st.top - 1; }""")
    assert inside                                                # the whole phone is in view
    page.set_viewport_size({"width": 390, "height": 844}); page.wait_for_timeout(800)
    assert not page.is_visible("#wsPane .phd .url")              # no one-letter address on a narrow panel
    assert not page.is_visible("#wsPane .phd .pttl")
    page.click("#wsPane .pvseg [data-view='code']")
    page.wait_for_selector("#wsPane .subnav .fty", timeout=20000)
    assert re.match(r"(HTML|CSS|JS|File)", page.inner_text("#wsPane .subnav .fty"))
