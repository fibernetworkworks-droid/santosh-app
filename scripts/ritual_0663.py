#!/usr/bin/env python3
"""v0.663.0 KAAN W5 - BOLI KE TEEN DARWAZE - the version ritual sweep.

W5 built fresh on the v0.662.0 tip (e2f117bbd): this sweep re-titles the version layer to
0.663.0 (+669) across ALL test files (the quoted pins), bumps pubspec, and heals the
extension version pin (the manifest went 1.9.0 -> 1.10.0 for tabCapture + offscreen).
Registry stays 606 and the kaan enum stays 18 - W5 adds transport doors, not tools.
"""
import re
from pathlib import Path

ROOT = Path("/home/z/my-project/santosh-app")
OLD, NEW = "0.662.0", "0.663.0"
OLD_BUILD, NEW_BUILD = "+668", "+669"

changed = []
for f in sorted((ROOT / "server" / "tests").glob("*.py")):
    text = f.read_text(encoding="utf-8")
    orig = text
    text = text.replace(OLD, NEW).replace(OLD_BUILD, NEW_BUILD)
    if text != orig:
        f.write_text(text, encoding="utf-8")
        changed.append(f.name)

print(f"tests swept: {len(changed)} files")
for n in changed[:8]:
    print("  ", n)

# the extension manifest version pin (the webext suite knows the manifest)
ext_pinned = []
for f in sorted((ROOT / "server" / "tests").glob("test_v0487_webext.py")):
    text = f.read_text(encoding="utf-8")
    if '"1.9.0"' in text:
        f.write_text(text.replace('"1.9.0"', '"1.10.0"'), encoding="utf-8")
        ext_pinned.append(f.name)
print("extension pins healed:", ext_pinned or "none needed")

# pubspec (the Android version layer)
pub = ROOT / "pubspec.yaml"
text = pub.read_text(encoding="utf-8")
assert f"version: {OLD}{OLD_BUILD}" in text, f"pubspec does not carry {OLD}{OLD_BUILD}"
pub.write_text(text.replace(f"version: {OLD}{OLD_BUILD}", f"version: {NEW}{NEW_BUILD}"), encoding="utf-8")
print("pubspec ->", f"{NEW}{NEW_BUILD}")

# residual check: the old literal must survive ONLY inside history-style prose (docs), not tests
residual = []
for f in sorted((ROOT / "server" / "tests").glob("*.py")):
    if OLD in f.read_text(encoding="utf-8"):
        residual.append(f.name)
print("residual", OLD, "in tests:", residual or "ZERO")
