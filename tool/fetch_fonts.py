"""R0: bundle the app's fonts as assets (OFL fonts from Google Fonts).

google_fonts looks in the asset bundle FIRST for a file named <Family>-<Variant>.ttf (Family without spaces,
Variant = Regular / Medium / SemiBold / Bold / ExtraBold, + Italic), so a bundled file is used with no network
fetch: no text flicker on first open, works offline, and golden screenshots render real glyphs.
Run: python3 tool/fetch_fonts.py   (writes assets/fonts/)
"""
import re
import sys
import urllib.request
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "assets" / "fonts"
NAMES = {400: "Regular", 500: "Medium", 600: "SemiBold", 700: "Bold", 800: "ExtraBold"}
WANT = {
    "Manrope": ([400, 500, 600, 700, 800], []),          # today's interface font (Night Glass)
    "Sora": ([400, 500, 600, 700, 800], []),             # today's display font
    "Literata": ([400, 500, 600], [400]),                # replies (v0.253) + new headings
    "Schibsted Grotesk": ([400, 500, 600, 700], []),     # the new interface font (same as the console)
    "JetBrains Mono": ([400, 500], []),                  # code
}


def css(family: str, weights: list[int], italics: list[int]) -> str:
    axes = [f"0,{w}" for w in weights] + [f"1,{w}" for w in italics]
    url = f"https://fonts.googleapis.com/css2?family={family.replace(' ', '+')}:ital,wght@{';'.join(axes)}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/4.0"})   # an old agent gets static TTF files
    return urllib.request.urlopen(req, timeout=30).read().decode()


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    for family, (weights, italics) in WANT.items():
        text = css(family, weights, italics)
        for block in text.split("@font-face")[1:]:
            style = re.search(r"font-style:\s*(\w+)", block).group(1)
            weight = int(re.search(r"font-weight:\s*(\d+)", block).group(1))
            src = re.search(r"url\((https://[^)]+\.ttf)\)", block).group(1)
            name = NAMES[weight] + ("Italic" if style == "italic" else "")
            if name == "RegularItalic":
                name = "Italic"
            dest = OUT / f"{family.replace(' ', '')}-{name}.ttf"
            dest.write_bytes(urllib.request.urlopen(src, timeout=60).read())
            print(f"{dest.name:40} {dest.stat().st_size // 1024} KB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
