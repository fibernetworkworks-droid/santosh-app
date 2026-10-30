"""v0.256.0 Claude's sidebar type (Schibsted Grotesk, 14 / 12 / 34px) and crisp text (no layers without a solid background)."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CON = ROOT / "server" / "app" / "static" / "console"
CSS = (CON / "v2.css").read_text()


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.263.0"
    assert "0.263.0+303" in (ROOT / "pubspec.yaml").read_text()


def test_schibsted_is_the_interface_sans():
    html = (CON / "v2.html").read_text()
    assert "family=Schibsted+Grotesk:wght@400..700" in html and "Manrope" not in html
    root = CSS[CSS.index(":root{"):CSS.index("*,*::before")]
    assert "--fb:'Schibsted Grotesk'" in root and "--fd:'Schibsted Grotesk'" in root
    tail = CSS[CSS.index("v0.256 CLAUDE'S SIDEBAR TYPE"):]
    assert "#app .side .sn,#app .side .newc{min-height:34px" in tail
    assert "#app .side .rc{min-height:34px;padding-top:6px;padding-bottom:6px;font-size:14px;font-weight:400}" in tail


def test_crisp_text_rules():
    assert not re.search(r"animation:[^;}]*\b(both|forwards)\b", CSS)              # no held entry animations
    assert "*{-webkit-backdrop-filter:none !important;backdrop-filter:none !important}" in CSS
    assert "#app .halo .ring{background:conic-gradient(from var(--a)" in CSS        # paint, not a rotating layer
    assert "#app .dock,#app .main,#app .view{background:var(--bg)}" in CSS
    assert CSS.count("--chat-paper:var(--bg);") == 2 and "--chat-paper:transparent" not in CSS
    assert "#app .dock{position:relative;z-index:2}" in CSS
    assert CSS.count("{") == CSS.count("}")


def test_sidebar_ink_and_grey_pill_like_claude():
    assert "#app .side .sn,#app .side .rc{color:var(--ink)}" in CSS
    assert '#app .side .sn[aria-current="true"],#app .side .rcw.cur .rc{background:rgb(var(--fg-rgb) / .08);box-shadow:none' in CSS
