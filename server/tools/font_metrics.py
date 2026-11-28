"""v0.999.64 D3: measure every bundled font once (python tools/font_metrics.py) -> app/appengine/font_metrics.json.
The design genome uses it to give each font a size-matched stand-in (size-adjust + ascent / descent / line-gap
overrides on the visitor's own Arial / Times New Roman), so the page does not move when the real font arrives
(the CLS fix next/font and capsize use). Width = the average advance of English text (letters by frequency + spaces).
The stand-ins are measured from Liberation Sans / Serif, which have Arial's / Times New Roman's metrics."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from fontTools.ttLib import TTFont

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
from app.appengine import genome as GN  # noqa: E402

# English letter frequencies (per 100 letters) + spaces at about one in six characters
FREQ = {"e": 12.7, "t": 9.1, "a": 8.2, "o": 7.5, "i": 7.0, "n": 6.7, "s": 6.3, "h": 6.1, "r": 6.0, "d": 4.3, "l": 4.0,
        "c": 2.8, "u": 2.8, "m": 2.4, "w": 2.4, "f": 2.2, "g": 2.0, "y": 2.0, "p": 1.9, "b": 1.5, "v": 1.0, "k": 0.8,
        "j": 0.15, "x": 0.15, "q": 0.1, "z": 0.07, " ": 18.0}


def measure(path: str) -> dict:
    f = TTFont(path)
    upm = f["head"].unitsPerEm
    cmap = f.getBestCmap()
    hmtx = f["hmtx"]
    tot = wsum = 0.0
    for ch, w in FREQ.items():
        g = cmap.get(ord(ch))
        if g is None:
            continue
        tot += hmtx[g][0] * w
        wsum += w
    os2, hhea = f["OS/2"], f["hhea"]
    typo = bool(os2.fsSelection & (1 << 7))
    asc, desc, gap = ((os2.sTypoAscender, os2.sTypoDescender, os2.sTypoLineGap) if typo else
                      (hhea.ascent, hhea.descent, hhea.lineGap))
    return {"upm": upm, "xavg": round(tot / wsum, 2), "ascent": asc, "descent": desc, "line_gap": gap}


def main() -> None:
    lib = "/usr/share/fonts/truetype/liberation/"
    out = {"_fallback": {"sans": {"400": {"local": ["Arial", "Liberation Sans", "Arimo"], **measure(lib + "LiberationSans-Regular.ttf")},
                                  "700": {"local": ["Arial Bold", "Arial-BoldMT", "Liberation Sans Bold", "Arimo Bold"],
                                          **measure(lib + "LiberationSans-Bold.ttf")}},
                         "serif": {"400": {"local": ["Times New Roman", "TimesNewRomanPSMT", "Liberation Serif", "Tinos"],
                                           **measure(lib + "LiberationSerif-Regular.ttf")},
                                   "700": {"local": ["Times New Roman Bold", "TimesNewRomanPS-BoldMT", "Liberation Serif Bold", "Tinos Bold"],
                                           **measure(lib + "LiberationSerif-Bold.ttf")}}}}
    for fam in sorted(GN.FONTS):
        files = [x for x in GN.font_files(fam) if x[0] == "latin"]
        if files:
            out[fam] = {str(w): measure(str(GN.FONT_DIR / fn)) for _, w, fn in files}
    dest = HERE / "app" / "appengine" / "font_metrics.json"
    dest.write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
    print(f"{len(out) - 1} families -> {dest}")


if __name__ == "__main__":
    main()
