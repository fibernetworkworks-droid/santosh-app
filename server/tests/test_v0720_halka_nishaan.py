"""v0.720 HALKA NISHAAN (owner, sidebar screenshot: "CHECK THE LOGO IS DARK -- MAKE IT LIGHT LOGO -- AS ALREADY DEVLOPED
DONT KEEP THAT RING ON IT"): the console logo is the light mark (the one drawing on transparent), no navy, no ring."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STATIC = ROOT / "server/app/static"


def test_light_mark_is_transparent_and_from_the_one_drawing():
    from PIL import Image
    im = Image.open(STATIC / "hoola-mark.png")
    assert im.mode == "RGBA" and im.size == (256, 256)
    assert im.getpixel((2, 2))[3] == 0 and im.getpixel((253, 253))[3] == 0   # no navy square
    assert im.getpixel((128, 128))[3] == 255                                  # the core is there
    assert "server/app/static/hoola-mark.png" in (ROOT / "tool/make_mark.js").read_text()


def test_console_uses_it_without_a_ring():
    for rel in ("console/v2.html", "console/index.html"):
        t = (STATIC / rel).read_text()
        assert t.count('src="/static/hoola-mark.png"') == 2, rel
        assert "hoola-logo.png" not in t, rel
    css = (STATIC / "console/v2.css").read_text()
    rule = '#app .mk img[src*="hoola-mark"],.mk img[src*="hoola-mark"],.lcard .brand img[src*="hoola-mark"]{border-radius:0;box-shadow:none'
    assert rule in css and css.index(rule) > css.index("0 0 0 3.5px var(--mag)")   # wins over the old ring rule
    assert "'/static/hoola-mark.png'" in (STATIC / "console/studio.js").read_text()
