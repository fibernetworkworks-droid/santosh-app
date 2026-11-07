"""Build every size of the Hoola app logo from the one 1024px master.

    usage: python3 tool/make_logo.py <master.png> <repo root>

The master lives in the repo at assets/images/hoola_logo.png, so every size can be rebuilt from it and
none of them can quietly drift away from the others.

The logo is a glow on a flat navy (#090F32). Two different things are needed:

  * the FULL square (navy included) - the legacy launcher icon, the favicon, the brand mark;
  * a TRANSPARENT foreground inside Android's adaptive safe zone - the launcher crops an adaptive
    icon to a circle/squircle at about 66% of the canvas, so the glow has to be scaled down and the
    navy handed to adaptive_icon_background instead, or the mask would cut the orbit rings off.

The transparency is taken from how far each pixel is from that navy, so the glow keeps its soft
edge instead of getting a hard cut-out.
"""
import sys
from pathlib import Path

from PIL import Image

SRC = Path(sys.argv[1])
ROOT = Path(sys.argv[2])
BG = (9, 15, 50)

master = Image.open(SRC).convert("RGB")
assert master.size == (1024, 1024), master.size


def transparent(im: Image.Image) -> Image.Image:
    """Alpha from the distance to the flat navy, so the glow fades out as it does on the master."""
    px = im.load()
    out = Image.new("RGBA", im.size, (0, 0, 0, 0))
    op = out.load()
    w, h = im.size
    for y in range(h):
        for x in range(w):
            r, g, b = px[x, y]
            d = max(r - BG[0], g - BG[1], b - BG[2], 0)
            if d <= 2:
                continue
            a = min(255, int(d * 255 / 150))          # ~150 levels above the navy = fully opaque
            op[x, y] = (r, g, b, a)
    return out


def write(im: Image.Image, rel: str, size: int | None = None) -> None:
    p = ROOT / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    out = im.resize((size, size), Image.LANCZOS) if size and im.size != (size, size) else im
    out.save(p, optimize=True)
    print(f"{rel}  {out.size[0]}x{out.size[1]}  {p.stat().st_size // 1024} KB")


# --- the app's own icon sources (Flutter launcher icons reads these) ------------------------------
write(master, "assets/images/hoola_logo.png")

fg = Image.new("RGBA", (1024, 1024), (0, 0, 0, 0))                 # adaptive foreground, safe zone
glow = transparent(master).resize((648, 648), Image.LANCZOS)        # 63% - inside the circular mask
fg.paste(glow, ((1024 - 648) // 2, (1024 - 648) // 2), glow)
write(fg, "assets/images/hoola_logo_fg.png")

# --- the web: favicon, PWA, Apple, and the brand mark in the console ------------------------------
st = "server/app/static/"
write(master, st + "hoola-logo.png", 512)
write(master, st + "hoola-icon-192.png", 192)
write(master, st + "hoola-icon-512.png", 512)
write(master, st + "hoola-apple-touch.png", 180)                    # Apple ignores transparency anyway
write(master, st + "favicon-32.png", 32)
