"""v0.240.0 CALM BRAND console: Light / Dark / System, the app brand colours, the edge and the live sheen."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CON = ROOT / "server" / "app" / "static" / "console"


def _read(name):
    return (CON / name).read_text(encoding="utf-8")


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.253.0"
    assert "0.253.0+293" in (ROOT / "pubspec.yaml").read_text()
    assert _read("v2.html").count("?v=0.253.0") == 13


def test_theme_loads_before_first_paint_without_inline_script():
    html = _read("v2.html")
    head = html[:html.index("</head>")]
    # the console CSP is script-src 'self': the theme must be a file, loaded in <head> before the stylesheet
    assert '<script src="/static/console/theme.js?v=' in head
    assert head.index("theme.js") < head.index("v2.css")
    assert not re.search(r"<script>(?!</script>)", html)
    assert '<meta name="color-scheme" content="light dark">' in head
    js = _read("theme.js")
    for k in ("hoola.theme", "hoola.size", "hoola.calm", "hoola.glow", "startViewTransition", "prefers-color-scheme: dark"):
        assert k in js, k


def test_light_dark_and_system_tokens():
    css = _read("v2.css")
    assert css.count("{") == css.count("}")
    root = css[css.index(":root{"):css.index("*,*::before")]
    assert "--bg:#F5F4FA" in root and "--pri:#5B45E0" in root                         # light is the bare :root
    assert '@media (prefers-color-scheme: dark){ :root:not([data-theme="light"]){' in root   # System on a dark computer
    assert ':root[data-theme="dark"]{' in root and "--bg:#110F20" in root            # her explicit Dark
    for tok in ("--fg-rgb", "--surf-rgb", "--sh-rgb", "--acc-rgb", "--ok-rgb", "--bad-rgb", "--on-acc", "--edge-hi"):
        assert root.count(tok + ":") == 3, tok                                     # light, system-dark, dark
    # every old dark-only literal now reads a token
    body = css[css.index("*,*::before"):]
    for lit in ("rgba(255,177,92", "rgba(124,92,255", "rgba(244,242,255", "rgba(11,10,26", "#1B1030"):
        assert lit not in body, lit
    assert "radial-gradient(120% 90% at 20% 0%" not in css                             # the night-sky body is gone


def test_edge_sheen_and_motion_switches():
    css = _read("v2.css")
    tail = css[css.index("v0.240 CALM BRAND - the approved prototype"):]
    assert "@property --a" in tail and "animation:cspin" in tail
    assert "#app .cd.ask::after" in tail and "#app .job.wait::after" in tail and "#app .box::after" in tail
    assert ":root.noglow #app .cd.ask::after" in tail                                  # Live border glow off
    assert ":root.calm *" in tail and "prefers-reduced-motion: reduce" in tail         # Reduce motion
    assert "::view-transition-new(root)" in tail
    assert ".aurora{display:none}" in tail


def test_switch_in_sidebar_and_appearance_in_account():
    html = _read("v2.html")
    side = html[html.index('<aside class="side"'):html.index("</aside>")]
    assert 'id="themeSeg"' in side
    for k in ("light", "dark", "system"):
        assert f'data-theme-set="{k}"' in side
    js = _read("v2.js")
    assert "box.innerHTML = appearanceHTML() +" in js
    for k in ('data-size-set="sm"', 'id="calmSw"', 'id="glowSw"', "TH.setTheme(b.dataset.themeSet, e)"):
        assert k in js, k
    for cmd in ("['appearance', 'Appearance'", "['light', 'Light theme'", "['dark', 'Dark theme'", "['system', 'System theme'"):
        assert cmd in js, cmd


def test_theme_js_is_served(env):
    from fastapi.testclient import TestClient
    from app.main import app
    r = TestClient(app).get("/static/console/theme.js")
    assert r.status_code == 200 and "HoolaTheme" in r.text
