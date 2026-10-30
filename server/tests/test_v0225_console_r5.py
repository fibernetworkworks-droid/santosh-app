"""v0.225 CONSOLE R5 - the create studio. A settings rail (type tabs, prompt with a counter and an example, reference
photos, Style / Shape / Quality chips, the price on the button) beside her real creations from the panel library.
Every field the browser walkthrough uses keeps its id; the hidden selects still carry aspect and quality."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONSOLE = ROOT / "server" / "app" / "static" / "console"


def _read(name: str) -> str:
    return (CONSOLE / name).read_text()


def test_rail_keeps_every_field():
    js = _read("workspace.js")
    for needle in ('id="cw-form"', 'id="cw-prompt"', 'id="cw-files"', 'id="cw-refs"', 'id="cw-submit"', 'id="cw-aspect"',
                   'id="cw-quality"', 'id="cw-seconds"', 'id="cw-language"', 'id="cw-sources"', 'id="cw-format"',
                   'data-mode="${k}"', 'data-cw="example"', 'data-cw="attach"', 'id="cw-count"'):
        assert needle in js, needle
    # chips drive the hidden selects that take() reads
    assert "chips('style'" in js and "chips('aspect'" in js and "chips('quality'" in js
    assert "sel.value=b.dataset[k]" in js
    assert "Style: ${d.style}." in js                                     # the style rides the brief to photo_banao


def test_price_on_the_button_is_an_estimate():
    js = _read("workspace.js")
    assert "COST = {fast:'~₹3', best:'~₹12'}" in js
    assert "Create image · ${COST[" in js and "Prepare storyboard · free" in js
    assert "Prices are estimates" in js


def test_gallery_reads_her_library_with_her_login():
    js = _read("workspace.js")
    assert "/api/panel/library?kind=" in js and "/api/panel/files/" in js
    assert "URL.createObjectURL(b)" in js and "URL.revokeObjectURL" in js and "dropThumbs()" in js
    assert "b.type.startsWith('image/')" in js                           # only real pictures become thumbnails
    v2 = _read("v2.js")
    assert "gallery: () => !!PN, open: item => PN?.open(item)," in v2
    assert "Dhoondhiye" not in _read("panel.js")


def test_styles():
    css = _read("v2.css")
    tail = css[css.index("v0.225 R5: the create studio"):]
    for rule in ("#app .cw-studio{", "#app .cw-rail{", "#app .cw-chip[aria-pressed=\"true\"]{", "#app .cw-ggrid{",
                 "#app .cw-thumb img{", "#app .cw-box #cw-prompt{", "@media(prefers-reduced-motion:reduce){#app .cw-tile"):
        assert rule in tail, rule
    assert css.count("{") == css.count("}")


def test_version_pin():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.289.0"
    assert "0.289.0+329" in (ROOT / "pubspec.yaml").read_text()
