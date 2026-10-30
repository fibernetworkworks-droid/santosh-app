"""v0.255.0 one type system on every console page: no weight > 600, no all-caps, nothing under 12px, Sora only on the logo."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CON = ROOT / "server" / "app" / "static" / "console"
CSS = (CON / "v2.css").read_text()


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.284.0"
    assert "0.284.0+324" in (ROOT / "pubspec.yaml").read_text()


def test_no_heavy_weights_caps_or_tiny_text():
    body = CSS[CSS.index("*,*::before"):]
    assert not re.search(r"font-weight:\s*(700|750|800|900)\b", body)
    assert not re.search(r"\bfont:\s*(700|750|800|900)\s", body)
    assert "text-transform:uppercase" not in CSS
    for m in re.finditer(r"([^{}]+)\{([^{}]*)\}", body):
        if "kbd" in m.group(1):
            continue
        assert not re.search(r"font-size:\s*(9|9\.5|10|10\.5|11|11\.5)px", m.group(2)), m.group(1).strip()[:80]
    assert ":where(#app,#login) :is(h1,h2,h3,h4,b,strong,th){font-weight:600}" in CSS


def test_sora_only_on_the_logo():
    root = CSS[CSS.index(":root{"):CSS.index("*,*::before")]
    assert "--fd:'Schibsted Grotesk'" in root and "--logo:'Sora'" in root   # v0.256 the interface sans
    assert CSS.count("var(--logo)") == 1 and "#app .mk,#app .mk span{font-family:var(--logo)}" in CSS
    for f in ("v2.js", "panel.js", "build.js"):
        assert 'style="font-weight:700"' not in (CON / f).read_text(), f
