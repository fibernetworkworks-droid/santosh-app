#!/usr/bin/env python3
"""v0.637.0 KAAN W3 APNI BOLI - the version ritual sweep.

W3 built fresh on their v0.636.0 tip (7723ddaa1): this sweep re-titles the version layer to
0.637.0 (+643) across ALL test files (the quoted pins), heals the kaan actions-enum pins to
the W3 arithmetic (12 + 4 = 16 actions), and bumps pubspec. Registry stays 606 - actions,
not tools, nothing to heal there.
"""
import re
from pathlib import Path

ROOT = Path("/home/z/my-project/santosh-app")
OLD, NEW = "0.636.0", "0.637.0"
OLD_BUILD, NEW_BUILD = "+642", "+643"

changed = []
for f in sorted((ROOT / "server" / "tests").glob("*.py")):
    text = f.read_text(encoding="utf-8")
    orig = text
    text = text.replace(OLD, NEW).replace(OLD_BUILD, NEW_BUILD)
    if text != orig:
        f.write_text(text, encoding="utf-8")
        changed.append(f.name)

# the kaan enum pins grow the four W3 actions (the newest-enum precedent, W2's own heal pattern)
ENUM_OLD = '"live_start", "live_chunk", "live_stop", "live_get", "live_list"]'
ENUM_NEW = ('"live_start", "live_chunk", "live_stop", "live_get", "live_list",\n'
            '                    "style", "vocab_add", "vocab_list", "vocab_remove"]  # W3 grew actions')
enum_files = []
for name in ("test_v0589_kaan.py", "test_v0607_kaan_w1.py", "test_v0618_kaan_w2.py"):
    f = ROOT / "server" / "tests" / name
    text = f.read_text(encoding="utf-8")
    if ENUM_OLD in text:
        f.write_text(text.replace(ENUM_OLD, ENUM_NEW), encoding="utf-8")
        enum_files.append(name)

pub = ROOT / "pubspec.yaml"
ptext = pub.read_text(encoding="utf-8")
assert f"version: {OLD}{OLD_BUILD}" in ptext, "pubspec anchor missing"
pub.write_text(ptext.replace(f"version: {OLD}{OLD_BUILD}", f"version: {NEW}{NEW_BUILD}"),
               encoding="utf-8")

resid = {}
for f in sorted((ROOT / "server" / "tests").glob("*.py")):
    t = f.read_text(encoding="utf-8")
    n1 = t.count(OLD) + t.count(OLD_BUILD)
    if n1:
        resid[f.name] = n1
print(f"swept files: {len(changed)}")
print(f"enum pins healed: {enum_files}")
print(f"pubspec: {NEW}{NEW_BUILD}")
print(f"residuals: {resid if resid else 'ZERO'}")
