"""v0.462 (built as 0.461) HOOLA KA NISHAAN: the owner's logo is the app's mark on every surface Hoola itself owns.

Before this the launcher icon was the AVATAR's face, so the mark on her home screen was the character and not
the product. These tests pin the three things that are easy to half-do and impossible to notice:

  * every size really exists, is square, and is the size it claims (a 192 that is really 512 is a 33 KB
    download on a phone);
  * the adaptive foreground is TRANSPARENT and sits inside the circular mask - a launcher crops an adaptive
    icon to about 66 %, so a full-bleed foreground silently loses the outer orbit rings;
  * every page Hoola serves points at it, and the AVATAR pictures are left alone.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
STATIC = ROOT / "server/app/static"
WANT = {
    "assets/images/hoola_logo.png": 1024,
    "assets/images/hoola_logo_fg.png": 1024,
    "server/app/static/hoola-logo.png": 512,
    "server/app/static/hoola-icon-192.png": 192,
    "server/app/static/hoola-icon-512.png": 512,
    "server/app/static/hoola-apple-touch.png": 180,
    "server/app/static/favicon-32.png": 32,
}
PAGES = ["index.html", "terms.html", "privacy.html", "console/index.html", "console/v2.html",
         "appadmin/index.html", "prayog/index.html", "prayog/lab.html",
         "site/home.html", "site/studio.html", "site/employee.html", "site/network.html"]


def _png_size(p: Path) -> tuple[int, int]:
    b = p.read_bytes()
    assert b[:8] == b"\x89PNG\r\n\x1a\n", f"{p} is not a PNG"
    return int.from_bytes(b[16:20], "big"), int.from_bytes(b[20:24], "big")


@pytest.mark.parametrize("rel,size", sorted(WANT.items()))
def test_every_size_exists_and_is_that_size(rel: str, size: int):
    p = ROOT / rel
    assert p.exists(), f"{rel} missing - rebuild with tool/make_logo.py"
    assert _png_size(p) == (size, size), f"{rel} is {_png_size(p)}, not {size}x{size}"


def test_the_adaptive_foreground_is_transparent_and_inside_the_mask():
    """The glow must be cut out AND small enough to survive the launcher's circular crop."""
    from PIL import Image
    im = Image.open(ROOT / "assets/images/hoola_logo_fg.png")
    assert im.mode == "RGBA", "the adaptive foreground must carry alpha, not a navy square"
    a = im.getchannel("A")
    assert a.getextrema()[0] == 0, "nothing is transparent - this is still the full square"
    box = a.getbbox()                                   # everything that is not fully transparent
    assert box, "the foreground is empty"
    w = im.size[0]
    inset = min(box[0], box[1], w - box[2], w - box[3]) / w
    assert inset >= 0.14, f"only {inset:.0%} margin: a circular mask at 66% would cut the orbit rings"


def test_the_launcher_icon_is_the_logo_not_the_avatar():
    y = (ROOT / "pubspec.yaml").read_text()
    blk = y[y.index("flutter_launcher_icons:\n  #"):y.index("min_sdk_android")]
    assert "assets/images/hoola_logo.png" in blk and "assets/images/hoola_logo_fg.png" in blk
    assert "santosh_head" not in blk, "the app icon is the avatar's face again"
    assert '"#090F32"' in blk, "the adaptive background must be the logo's own navy"


def test_every_page_hoola_serves_carries_it():
    for rel in PAGES:
        t = (STATIC / rel).read_text()
        assert 'href="/static/favicon-32.png"' in t, rel
        assert 'rel="apple-touch-icon" href="/static/hoola-apple-touch.png"' in t, rel
        assert 'href="/static/hoola-icon-192.png" sizes="192x192"' in t, rel


def test_the_brand_mark_is_the_logo_and_the_avatar_is_still_the_avatar():
    for rel in ("console/v2.html", "console/index.html"):
        t = (STATIC / rel).read_text()
        brand = [l for l in t.splitlines() if 'class="brand"' in l or 'class="mk"' in l]
        assert brand, rel
        for line in brand:
            assert "/static/hoola-logo.png" in line, f"{rel}: brand mark is not the logo: {line[:80]}"
        # the avatar rows are untouched: that picture is the person she named, not the product
        assert "/static/santosh-head.png" in t, f"{rel}: the avatar picture went missing"


def test_the_status_bar_icon_is_the_logo_as_a_silhouette():
    """Android keeps only the SHAPE of a notification icon, so it has to be white on transparent."""
    v = (ROOT / "tool/android/res/drawable/ic_stat_santosh.xml").read_text()
    assert v.count('android:fillColor="#FFFFFFFF"') >= 2 and "strokeColor=\"#FFFFFFFF\"" in v
    assert "A8.3,8.3" in v and "A6.6,6.6" in v, "the two orbits"
    assert re.search(r'strokeWidth="1\.[4-9]"', v), "thinner than 1.4dp disappears in the status bar"


def test_the_sizes_can_be_rebuilt_from_the_master():
    assert (ROOT / "tool/make_logo.py").exists()
    src = (ROOT / "tool/make_logo.py").read_text()
    for rel in WANT:
        assert rel.split("/")[-1] in src, f"{rel} is not built by tool/make_logo.py"
