"""v0.987 HOOLA LOGO (owner, her Web Studio home screenshot: "THIS PAGE IS GOOD AND PERFECT ::: JUST PUT THE HOOLA LOGO
THERE"): the Web Studio showed a gradient ring where the logo goes (sidebar brand + every workspace top bar). It now draws
the real Hoola mark from mark.js - the same drawing as the app and the console - in Hoola violet. Nothing else changed."""
from pathlib import Path

from tests.test_v0312_arena_screen import arena_server  # noqa: F401  (fixture: uvicorn + Chromium)
from tests.test_v121_site import site_env  # noqa: F401  (fixture)

CONSOLE = Path(__file__).parents[1] / "app" / "static" / "console"


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION.startswith("0.999.118")
    assert "v0.987.0 HOOLA LOGO" in (Path(__file__).parents[1] / "app" / "main.py").read_text()


def test_the_real_mark_everywhere_the_ring_was():
    js = (CONSOLE / "webstudio.js").read_text()
    html = (CONSOLE / "webstudio.html").read_text()
    css = (CONSOLE / "webstudio.css").read_text()
    assert '<div class="mark" aria-hidden="true"><span></span></div>' not in js     # no gradient ring left
    assert js.count('<div class="mark" aria-hidden="true">${hoolaMark()}</div>') == 4   # v0.988: the choices page (one of the 5) was removed
    assert "HoolaMark.svg({mono: true})" in js
    assert html.index("/static/console/mark.js") < html.index("/static/console/webstudio.js")
    assert ".mark:has(svg){background:none" in css and "color:var(--pri)" in css


def test_logo_in_a_browser(arena_server, site_env):
    base, browser, key = arena_server
    ctx = browser.new_context(viewport={"width": 1280, "height": 800})
    ctx.add_init_script(f"try {{ localStorage.setItem('hoola.console.token', '{key}') }} catch (e) {{}}")
    page = ctx.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(f"{base}/console/web#/")
    page.locator(".brand .mark svg").wait_for(timeout=20000)
    got = page.evaluate("""() => { const m = document.querySelector('.brand .mark'), r = m.getBoundingClientRect(),
        st = getComputedStyle(m); return {img: st.backgroundImage, w: r.width, paths: m.querySelectorAll('path').length} }""")
    assert got["img"] == "none" and got["w"] == 28 and got["paths"] >= 4, got
    import os
    if os.environ.get("CONSOLE_SHOTS"):
        page.screenshot(path=os.path.join(os.environ["CONSOLE_SHOTS"], "v0987-logo.png"), clip={"x": 0, "y": 0, "width": 400, "height": 140})
    ctx.close()
    assert not errors, errors
