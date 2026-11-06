#!/usr/bin/env python3
"""v0.620.0 REBASE PROTOCOL #11 - the version layer re-applied coherently on their v0.619.0 tip.

Their chain took 0.618.0 (HAMESHA JUDA, tag v0.618.0-b1789) and 0.619.0 (KAAN W2, tag
v0.619.0-b1791) while BHANDAR sat built as 0.618.0. Their base kept whole; this sweep re-titles
the version layer to 0.620.0 (+626) and heals the registry count pins to the merged arithmetic
(605 theirs + 1 bhandar = 606) across ALL test files - theirs now, mine too.
"""
import re
from pathlib import Path

ROOT = Path("/home/z/my-project/hoola-project")
OLD, NEW = "0.619.0", "0.620.0"
OLD_BUILD, NEW_BUILD = "+625", "+626"

changed = []
for f in sorted((ROOT / "server" / "tests").glob("*.py")):
    text = f.read_text(encoding="utf-8")
    orig = text
    text = text.replace(OLD, NEW).replace(OLD_BUILD, NEW_BUILD)
    text = re.sub(r"(len\((?:tools\.)?TOOLS\)\s*==\s*)605\b", r"\g<1>606", text)
    text = re.sub(r"\bregistry (?:stays )?605\b", "registry 606", text)
    text = re.sub(r"\bregistry stays 605\b", "registry stays 606", text)
    text = re.sub(r"\b(605) tools\b", "606 tools", text)
    if text != orig:
        f.write_text(text, encoding="utf-8")
        changed.append(f.name)

pub = ROOT / "pubspec.yaml"
ptext = pub.read_text(encoding="utf-8")
assert f"version: {OLD}{OLD_BUILD}" in ptext
pub.write_text(ptext.replace(f"version: {OLD}{OLD_BUILD}", f"version: {NEW}{NEW_BUILD}"),
               encoding="utf-8")

resid = {}
for f in sorted((ROOT / "server" / "tests").glob("*.py")):
    t = f.read_text(encoding="utf-8")
    n1 = t.count(OLD) + t.count(OLD_BUILD)
    n2 = len(re.findall(r"TOOLS\)\s*==\s*605\b", t))
    if n1 or n2:
        resid[f.name] = (n1, n2)
print(f"swept files: {len(changed)}")
print(f"pubspec: {NEW}{NEW_BUILD}")
print(f"residuals: {resid if resid else 'ZERO'}")
