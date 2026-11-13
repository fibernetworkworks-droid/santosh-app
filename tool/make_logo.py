"""Build every size of the Hoola app logo from the one 1024px master.

    usage: python3 tool/make_logo.py <master.png> <repo root>

The master lives in the repo at assets/images/hoola_logo.png, so every size can be rebuilt from it and
none of them can quietly drift away from the others.

v0.874 EK RANG: the logo is the mark in solid WHITE on a flat Hoola violet tile (#5B45E0). Both
sources are drawn by tool/make_mark.js from the one vector (server/app/static/console/mark.js):

  * the FULL square (violet included) - the legacy launcher icon, the favicon, the PWA / Apple icons;
  * a TRANSPARENT foreground inside Android's adaptive safe zone (assets/images/hoola_logo_fg.png) -
    the launcher crops an adaptive icon to a circle/squircle at about 66% of the canvas, so the mark is
    drawn smaller there and the violet is handed to adaptive_icon_background.

Run node tool/make_mark.js first, then this.
"""
import sys
from pathlib import Path

from PIL import Image

SRC = Path(sys.argv[1])
ROOT = Path(sys.argv[2])
BG = (0x5B, 0x45, 0xE0)       # Hoola violet - the tile under the white mark

master = Image.open(SRC).convert("RGB")
assert master.size == (1024, 1024), master.size



def write(im: Image.Image, rel: str, size: int | None = None) -> None:
    p = ROOT / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    out = im.resize((size, size), Image.LANCZOS) if size and im.size != (size, size) else im
    out.save(p, optimize=True)
    print(f"{rel}  {out.size[0]}x{out.size[1]}  {p.stat().st_size // 1024} KB")


# --- the app's own icon sources (Flutter launcher icons reads these) ------------------------------
write(master, "assets/images/hoola_logo.png")

fg = Image.open(ROOT / "assets/images/hoola_logo_fg.png").convert("RGBA")   # drawn by make_mark.js
assert fg.size == (1024, 1024) and fg.getpixel((0, 0))[3] == 0, "hoola_logo_fg.png must be the transparent foreground"
assert master.getpixel((4, 4)) == BG, "the master's corner must be the violet tile"

# --- the web: favicon, PWA, Apple, and the brand mark in the console ------------------------------
st = "server/app/static/"
write(master, st + "hoola-logo.png", 512)
write(master, st + "hoola-icon-192.png", 192)
write(master, st + "hoola-icon-512.png", 512)
write(master, st + "hoola-apple-touch.png", 180)                    # Apple ignores transparency anyway
write(master, st + "favicon-32.png", 32)
