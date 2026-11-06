#!/usr/bin/env python3
"""v0.618.0 BHANDAR MANCH version ritual - the mechanical sweep (pins heal, zero residual).

- server/tests/*.py: 0.617.0 -> 0.618.0 (full-string), +623 -> +624 (bare build),
  len(TOOLS) == 605 -> == 606 (three assertion shapes) and the 'registry 605' / '605 tools'
  wording in comments/docstrings, but NOT version-number coincidences like 'v0.605'.
- pubspec.yaml: 0.617.0+623 -> 0.618.0+624.
- Prints the residual counts; a nonzero residual for the version tokens is a failure.
"""
import re
from pathlib import Path

ROOT = Path("/home/z/my-project/hoola-project")
OLD, NEW = "0.617.0", "0.618.0"
OLD_BUILD, NEW_BUILD = "+623", "+624"

changed = []
for f in sorted((ROOT / "server" / "tests").glob("*.py")):
    text = f.read_text(encoding="utf-8")
    orig = text
    text = text.replace(OLD, NEW).replace(OLD_BUILD, NEW_BUILD)
    # registry count pins: three shapes + wording (never bare 605 - 'v0.605' must survive)
    text = re.sub(r"(len\((?:tools\.)?TOOLS\)\s*==\s*)605\b", r"\g<1>606", text)
    text = re.sub(r"\bregistry 605\b", "registry 606", text)
    text = re.sub(r"\b(605) tools\b", "606 tools", text)
    if text != orig:
        f.write_text(text, encoding="utf-8")
        changed.append(f.name)

pub = ROOT / "pubspec.yaml"
ptext = pub.read_text(encoding="utf-8")
assert f"version: {OLD}{OLD_BUILD}" in ptext, ptext.splitlines()[4]
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
print(f"residuals (version/build/registry): {resid if resid else 'ZERO'}")
