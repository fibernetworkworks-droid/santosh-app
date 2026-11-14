"""v0.898 CHAAR TAB: the phone's tab bar is Hoola / AI Employees / Tools / Computer; Tools opens each studio's own
web console page inside the app, so the console opens a requested page from /console/?v=<view>&a=<arg>."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_console_opens_the_requested_page():
    js = (ROOT / "server/app/static/console/v2.js").read_text()
    assert "new URLSearchParams(location.search), want = (P.get('v') || '').replace(/[^a-z_]/g, '')" in js
    assert "OWN.includes(want) || $('#v-' + want)" in js        # only a page the console really has
    assert "history.replaceState(null, '', '/console/')" in js   # the address does not keep reopening it


def test_phone_tabs_and_tools():
    shell = (ROOT / "lib/ui/shell/hoola_shell.dart").read_text()
    assert "'AI Employees'" in shell and "'Tools'" in shell and "'Computer'" in shell
    for gone in ("'Work'),", "'Connect'),", "'Made'),"):
        assert gone not in shell, gone
    tools = (ROOT / "lib/ui/shell/hoola_tools.dart").read_text()
    for t in ("Create", "Hoola Interactive", "Hoola Vocal", "Hoola Flow", "Web Development", "App Development",
              "Hoola Design", "Prompting", "Hoola Code", "Game Dev"):
        assert f"title: '{t}'" in tools, t
    page = (ROOT / "lib/ui/shell/hoola_console_page.dart").read_text()
    assert "localStorage.setItem('hoola.console.token'" in page and "/healthz" in page


def test_version():
    from app import main
    assert main.APP_VERSION == "0.906.0"
