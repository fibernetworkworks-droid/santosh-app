"""v0.970 WEB CONSOLE APP DESIGN (owner: "CURRENTLY IN WEBCONSOLE LOOK AI MADE --- CHECK THE APP DESIGN AND APPEND SAME
FOR WEBCONSOLE" -> design canvas claude.ai/artifact/QMSQEVcnpFv4aHq6JTJ4aL -> "GO BUILD"): the phone app's design
(lib/ui/hoola_theme.dart) on the web console - appdesign.css after v2.css while <html class="appd">, the app's four tabs
on top of the sidebar, the Hoola mark + serif greeting + start pills on the home, every studio on the Tools page."""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

from tests.test_v0312_arena_screen import arena_server  # noqa: F401
from tests.test_v121_site import site_env  # noqa: F401

ROOT = Path(__file__).resolve().parents[2]
CON = ROOT / "server/app/static/console"
CSS = (CON / "appdesign.css").read_text(encoding="utf-8")
JS = (CON / "v2.js").read_text(encoding="utf-8")
HTML = (CON / "v2.html").read_text(encoding="utf-8")
THEME = (ROOT / "lib/ui/hoola_theme.dart").read_text(encoding="utf-8")


def _app(name: str, dark: bool = False) -> str:
    """One colour role from the phone app's palette."""
    block = THEME[THEME.index("static const darkSet") if dark else THEME.index("static const light = HoolaColors("):]
    m = re.search(rf"\b{name}: Color\(0xFF([0-9A-F]{{6}})\)", block)
    return "#" + m.group(1)


def test_tokens_are_the_apps_own_colours():
    light = CSS[CSS.index("html.appd{"):CSS.index("@media (prefers-color-scheme: dark)")]
    dark = CSS[CSS.index('html.appd[data-theme="dark"]{'):]
    assert "--bg:#FFFFFF" in light   # v0.975 the page full white like Claude (the app keeps its paper)
    for token, role in [("--surface", "surface"), ("--sunk", "sunk"), ("--ink", "ink"), ("--mut", "ink2"),
                        ("--pri", "accent"), ("--line", "line"), ("--pill", "pill"), ("--ok", "ok"), ("--warn", "warn"),
                        ("--bad", "bad")]:
        assert f"{token}:{_app(role)}" in light, (token, role)
        assert f"{token}:{_app(role, dark=True)}" in dark, (token, role)
    # no gradients or glass on the app design: the brand glow tokens collapse to the one violet
    assert "--grad:linear-gradient(90deg,#5B45E0,#5B45E0)" in light


def test_scoped_behind_the_switch_and_loaded_after_v2():
    assert all(rule.strip().startswith(("html.appd", "html:not(.appd)", "@media", "}", "/*")) or not rule.strip()
               for rule in re.sub(r"/\*.*?\*/", "", CSS, flags=re.S).split("\n") if rule and not rule.startswith(" "))
    i_v2, i_app = HTML.index("/static/console/v2.css"), HTML.index("/static/console/appdesign.css")
    assert i_app > i_v2
    from app.config import Settings
    assert Settings().console_app_design is True
    src = (ROOT / "server/app/main.py").read_text(encoding="utf-8")
    assert '"app_design": bool(getattr(st, "console_app_design", False))' in src


def test_sidebar_home_and_tools_follow_the_app():
    # v0.973 CLAUDE-STYLE CHAT reshaped the sidebar: Claude's rows with Hoola's places
    assert "['hire', 'AI Employees'], ['kaam', 'Tools'], ['computer', 'Computer']" in JS
    assert "APPD = !!CONFIG.app_design" in JS and "classList.toggle('appd', APPD)" in JS
    assert "h < 12 ? 'Good morning' : h < 17 ? 'Good afternoon' : 'Good evening'" in JS
    assert "Make this month's GST summary" in JS and "data-send" in JS
    assert "class=\"apptools\"" in JS and "['code', 'Hoola Code'," in JS
    assert 'class="codepill" data-v="code"' in HTML


def test_the_console_in_a_real_browser(arena_server):  # noqa: F811
    base, browser, key = arena_server
    shots = os.environ.get("CONSOLE_SHOTS")
    for scheme in ("light", "dark"):
        ctx = browser.new_context(viewport={"width": 1440, "height": 900}, color_scheme=scheme)
        ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
        pg = ctx.new_page()
        errors = []
        pg.on("pageerror", lambda e: errors.append(str(e)))

        def config(route):
            r = route.fetch(); d = r.json(); d["app_design"] = True; d["human"] = True
            route.fulfill(response=r, body=json.dumps(d))
        pg.route("**/api/console/config", config)
        pg.goto(base + "/console/")
        pg.wait_for_selector("html.appd #snav .sn")
        pg.wait_for_timeout(400)
        m = pg.evaluate("""()=>{const g=s=>getComputedStyle(document.querySelector(s));
          return {rows:[...document.querySelectorAll('#snav .sn .txt')].slice(0,4).map(e=>e.textContent),
            mark:!!document.querySelector('.landing .hmark svg'), side:!!document.querySelector('.side .mk .hmk svg'),
            bg:g('body').backgroundColor, greet:document.getElementById('greet').textContent,
            gfont:g('#greet').fontFamily, pills:[...document.querySelectorAll('.landing .pill')].map(p=>p.textContent.trim()),
            newc:g('.side .newc').borderRadius}}""")
        assert m["rows"][:3] == ["AI Employees", "Tools", "Computer"], m   # v0.976 Work + Docs and files under More
        assert m["mark"], m
        assert m["bg"] == ("rgb(255, 255, 255)" if scheme == "light" else "rgb(20, 20, 19)"), m
        assert re.match(r"Good (morning|afternoon|evening)", m["greet"]), m
        assert "Literata" in m["gfont"], m
        assert "Make this month's GST summary" in m["pills"], m   # still drawn; v0.973 hides them like Claude
        assert m["newc"] == "8px", m   # v0.973 New chat is a plain row (v0.975 Claude's 8 px)
        if shots:
            pg.screenshot(path=f"{shots}/home-{scheme}.png")
        pg.click("#snav .sn[data-v=kaam]")
        pg.wait_for_selector(".apptools .apptool"); pg.wait_for_timeout(1200)
        n = pg.evaluate("document.querySelectorAll('.apptools .apptool').length")
        assert n >= 1
        if shots:
            pg.screenshot(path=f"{shots}/tools-{scheme}.png")
        pg.click("#snav .sn[data-v=hire]")
        pg.wait_for_timeout(1500)
        if shots:
            pg.screenshot(path=f"{shots}/employees-{scheme}.png")
        assert not errors, errors
        ctx.close()


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION.startswith("0.999.62")
