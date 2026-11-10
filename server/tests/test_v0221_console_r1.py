"""v0.221 CONSOLE R1 - first phase of the web console redesign: one stylesheet, one cache-buster, one language
rule. No layout change: workspace.css (the dev web layer) is merged at the end of v2.css, where its old <link>
put it in the cascade, so every rule it won before it still wins."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONSOLE = ROOT / "server" / "app" / "static" / "console"


def _read(name: str) -> str:
    return (CONSOLE / name).read_text()


def test_one_stylesheet():
    html = _read("v2.html")
    sheets = re.findall(r'<link rel="stylesheet" href="(/static/console/[^"]+)"', html)
    assert len(sheets) == 1 and sheets[0].startswith("/static/console/v2.css?v="), sheets
    assert not (CONSOLE / "workspace.css").exists()
    css = _read("v2.css")
    tail = css[css.index("v0.221 R1: the web workspace layer"):]
    # the workspace rules sit AFTER the base rules (same cascade position as the old separate file)
    # v0.461: `#app .progress-avatar` was pinned here until v0.298 KHULI JAGAH stopped DRAWING the avatar and
    # deleted the rule - the pin went stale that day and has been red ever since. The working row it belonged to
    # is still there under its own name, so the pin moves to the new truth rather than being dropped.
    for rule in ("#app #slotDock{width:min(880px,100%);margin-inline:auto}", "#app #slotDock #composer{width:100%}",
                 "#app .simple-progress{", "#app .side{width:224px"):
        assert rule in tail, rule
    assert css.index("--bg:#FFFFFF") < css.index("v0.221 R1")   # brand tokens first (v0.243 Light / Dark / System)
    assert css.count("{") == css.count("}")                       # the merged file still balances


def test_one_cache_buster_on_every_asset():
    # Re-pointed at v0.489.0 to main's 0.536.0 x21 (the BYOX chain changed the console): the
    # maintained convention (pinned in test_v0475_console_frames) is that console stamps move
    # only when the console itself changes; a server-only release leaves them coherent at the
    # last console version. The guard's real job: ONE app stamp across every non-vendor asset.
    html = _read("v2.html")
    refs = re.findall(r'(?:src|href)="/static/console/([\w/.-]+)\?([^"]*)"', html)
    assert refs, "no console assets found"
    stamps = {q for name, q in refs if name != "vendor/qrcode.js"}
    assert stamps == {"v=0.543.0"}, f"mixed console cache stamps: {sorted(stamps)}"
    assert all(q == "v=1.4.4" for name, q in refs if name == "vendor/qrcode.js")


def test_deploy_ships_the_merged_set():
    import importlib.util
    spec = importlib.util.spec_from_file_location("web_deploy", ROOT / "server/deploy/deploy_console_static.py")
    d = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(d)
    assert "workspace.css" not in d.FILES and "v2.css" in d.FILES
    for f in d.FILES:
        assert (CONSOLE / f).exists(), f
    wf = (ROOT / ".github/workflows/deploy-web-console.yml").read_text()
    tar = next(l for l in wf.splitlines() if "tar -czf /tmp/hoola-console.tar.gz" in l)
    assert set(tar.split("server/app/static/console", 1)[1].split()) == set(d.FILES)
    assert "workspace.css?web=" not in wf and "?web=progress" not in wf


def test_console_chrome_speaks_english():
    """Labels, menus, toasts, settings and errors are English. Haan / Mana stay (Hoola's approval words);
    lines the console sends TO Hoola (ctx.say / C.say) and kaam.js starters stay in her own words."""
    hinglish = re.compile(r"\b(karein|kijiye|dhoondh\w*|hatao|hatayein|kholo|chahiye|Wapas lo|Dobara|banao|jodiye|"
                          r"chal raha|ho gaya|nahi mili|Dikkat|Hidayat|aapki zaroorat|Naye tab)\b")
    for f in ("v2.html", "v2.js", "chatlist.js", "panel.js", "projects.js", "build.js"):
        for i, line in enumerate(_read(f).splitlines(), 1):
            code = line.strip()
            if code.startswith(("//", "/*", "*")) or ".say(" in line:
                continue
            code = re.sub(r"//.*$", "", code)                       # trailing comments are not UI
            code = re.sub(r'"(?:EMI calculator|Diwali poster) banao"', '""', code)   # example asks in her words
            assert not hinglish.search(code), f"{f}:{i}: {code[:160]}"
    js = _read("v2.js")
    for label in ("Slide for Haan", "'Mana'", "Take back", "Find in this chat", "Search all chats", "Connect Google apps"):
        assert label in js, label


def test_version_pin():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.764.0"    # conscious-bump guard: moves with every release (bump with pubspec)
    assert "0.764.0+763" in (ROOT / "pubspec.yaml").read_text()
