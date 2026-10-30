"""v0.254.0 the whole light console is white with neutral greys (brand violet kept) and the interface type is Claude-style."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CON = ROOT / "server" / "app" / "static" / "console"
CSS = (CON / "v2.css").read_text()


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.265.0"
    assert "0.265.0+305" in (ROOT / "pubspec.yaml").read_text()


def test_light_is_white_and_neutral_brand_kept():
    root = CSS[CSS.index(":root{"):CSS.index("@media (prefers-color-scheme: dark)")]
    for tok in ("--bg:#FFFFFF", "--side-bg:#F8F8F7", "--surface:#FFFFFF", "--line:#ECECEA", "--ink:#1A1A1F",
                "--sh-rgb:0 0 0", "--chat-ink:#1A1A1F; --chat-paper:#FFFFFF;"):
        assert tok in root, tok
    for brand in ("--pri:#5B45E0", "--saf:#EE8F35", "--mag:#B347E6", "--vio:#6E55F0"):
        assert brand in root, brand                                   # buttons, ring and glow stay the brand
    assert "#F5F4FA" not in root and "#EEECF7" not in root and "38 28 92" not in root   # no lavender left in light
    assert CSS.count("--bg:#110F20") == 2                                 # dark untouched
    assert '<meta name="theme-color" content="#FFFFFF"' in (CON / "v2.html").read_text()


def test_interface_type():
    tail = CSS[CSS.index("v0.254 CLAUDE-STYLE INTERFACE TYPE"):]
    for rule in ("#app .chead h1{font-family:var(--fb);font-size:14px;font-weight:500",
                 "#app .dock .box textarea,#app .landing .box textarea{font-size:16px",
                 "#app .side .slabel,#app .side .rg,#app .side .sgh .sgn{font-size:12px;font-weight:500;letter-spacing:0;text-transform:none",
                 "#app .ra{font-size:0", "#app .mdt{font-family:var(--fb);font-size:14px;font-variant-numeric:tabular-nums}",
                 "#app .landing h1{font-family:var(--fr);font-weight:400"):
        assert rule in tail, rule
    assert CSS.count("{") == CSS.count("}")
