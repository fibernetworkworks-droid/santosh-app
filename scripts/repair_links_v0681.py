#!/usr/bin/env python3
"""Repair v3: the v0.681 ritual's step 1 ran THREE times (two crashes landed after the sweep),
so 25 pin messages carry 3 kala arithmetic links. The seam between two links in the source is
close-quote + separator-space (the next link's own open-quote follows), i.e. P + '" ' + P.
This collapses every run back to exactly ONE link, then verifies."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
P = ('"608 + 1 kala (v0.681 KALA MANCH: the T5 knowledge-skill catalog family, '
     "owner 'GO' on the google/skills deploy plan). ")
DOUBLE = P + '" ' + P          # P's own open-quote closes the previous literal; the seam is '" '
fixed = []
for f in sorted((ROOT / "server" / "tests").glob("*.py")):
    text = f.read_text(encoding="utf-8")
    orig = text
    while DOUBLE in text:
        text = text.replace(DOUBLE, P, 1)
    if text != orig:
        f.write_text(text, encoding="utf-8")
        fixed.append(f.name)
print(f"collapsed: {len(fixed)} files")
bad = []
for f in sorted((ROOT / "server" / "tests").glob("*.py")):
    n = f.read_text(encoding="utf-8").count("608 + 1 kala")
    if n != 1 and f.name != "test_v0681_kala_manch.py" and f.name != "test_v0663_kaan_w5.py":
        bad.append((f.name, n))
print("unexpected link counts:", bad or "ZERO - every pinned file carries exactly one kala link")
