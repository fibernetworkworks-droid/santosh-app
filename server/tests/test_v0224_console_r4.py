"""v0.224 CONSOLE R4 - the work panel. Outlined tab chips (saffron edge on the open one), pill segmented Preview /
Code, a Desktop / Phone switch, live previews inside a browser frame, a tidy change footer; the build studio head,
tabs and workspace handle are rows again; panel + build-studio chrome in English. The sandbox on the preview frames
is unchanged (no allow-same-origin)."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONSOLE = ROOT / "server" / "app" / "static" / "console"


def _read(name: str) -> str:
    return (CONSOLE / name).read_text()


def test_device_switch_and_browser_frame():
    js = _read("panel.js")
    assert "function devSeg(phone)" in js and "function wireDev(t)" in js and "function browserFrame(f, label)" in js
    assert js.count("wireDev(t);") == 2                                     # page + website / app previews
    assert js.count("appendChild(browserFrame(f,") == 2
    assert "classList.toggle('phone', b.dataset.d === 'phone')" in js
    assert ".textContent = String(label" in js                              # the url line is text, never HTML
    # the frames keep their sandbox: scripts yes, same-origin never
    import re
    sandboxes = re.findall(r"setAttribute\('sandbox', '([^']+)'\)", js)
    assert len(sandboxes) >= 2 and all("allow-same-origin" not in x for x in sandboxes), sandboxes


def test_panel_and_studio_styles():
    css = _read("v2.css")
    tail = css[css.index("v0.224 R4: the work panel"):]
    for rule in ("#app .pntab.on{", "#app .bseg button[aria-pressed=\"true\"]{", "#app .pnbrowser{", "#app .pnchrome{",
                 "#app .pnview.phone .pnbrowser{", "#app .pnchg{", "#app.pn .dock .who,#app.st .dock .who{display:none}",
                 "#app .studio>.workspace-handle,#app .studio>.sthd,#app .studio>.sttabs{flex-direction:row",
                 "#app .studio .stchg{"):
        assert rule in tail, rule
    assert "rgb(var(--acc-rgb) / .55)" in tail                              # the accent edge (v0.243 token), not the gradient fill
    assert css.count("{") == css.count("}")


def test_studio_speaks_english():
    js = _read("build.js")
    for gone in ("'Jaanch'", "'Dhaancha'", "ban raha", "neeche tabs", "asli", "tasveer", "Tap karke", "Rang look"):
        assert gone not in js, gone
    for label in ("['jaanch', 'Checks']", "['dhaancha', 'Structure']", "bottom tabs:", "Every screen, as a real screenshot"):
        assert label in js, label
    assert "aria-label=\"Work panel\"" in _read("v2.html")


def test_version_pin():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.280.0"
    assert "0.280.0+320" in (ROOT / "pubspec.yaml").read_text()
