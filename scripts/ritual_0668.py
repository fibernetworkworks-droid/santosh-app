#!/usr/bin/env python3
"""v0.668.0 DUNIYA MANCH re-version ritual - the REBASE PROTOCOL's second half.

T4 built as 0.667.0; their PREMIUM STUDIO took 0.667.0 while T4 sat built and pushed -
REBASE PROTOCOL #13, rebased onto their 267774508 tip, both kept. This sweep re-applies
the version layer coherently on their base: 0.667.0/+673 -> 0.668.0/+674 across ALL test
files, pubspec, and the console cache-buster stamps (the test_v0179 law: stamps == APP_VERSION).
The PREMIUM STUDIO suites' own story tokens ("v0.667 PREMIUM STUDIO") are untouched - their
version fact, not this bump. The console stamp FILES change only inside ?v= (cache-busters),
which is exactly what the stamp pin reads.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NEW, NEW_BUILD = "0.668.0", "+674"
OLD_V, OLD_BUILD = "0.667.0", "+673"

# ---------------------------------------------------------------- 1. the test-file sweep
changed, tokens = [], 0
for f in sorted((ROOT / "server" / "tests").glob("*.py")):
    text = f.read_text(encoding="utf-8")
    orig = text
    tokens += len(re.findall(rf"\b{re.escape(OLD_V)}\b", text))
    text = text.replace(OLD_V, NEW).replace(OLD_BUILD, NEW_BUILD)
    if text != orig:
        f.write_text(text, encoding="utf-8")
        changed.append(f.name)
print(f"tests swept: {len(changed)} files ({tokens} version tokens)")

# ---------------------------------------------------------------- 2. pubspec
pub = ROOT / "pubspec.yaml"
text = pub.read_text(encoding="utf-8")
text, n = re.subn(r"version: 0\.\d+\.\d+\+\d+", f"version: {NEW}{NEW_BUILD}", text, count=1)
pub.write_text(text, encoding="utf-8")
print("pubspec ->", f"{NEW}{NEW_BUILD}" if n else "!! PATTERN MISS")

# ---------------------------------------------------------------- 3. the console cache-busters (the v0179 law)
stamped = 0
for f in sorted((ROOT / "server" / "app" / "static" / "console").glob("*")):
    if f.suffix not in (".html", ".htm"):
        continue
    text = f.read_text(encoding="utf-8")
    new_text, n = re.subn(rf"\?v={re.escape(OLD_V)}", f"?v={NEW}", text)
    if n:
        f.write_text(new_text, encoding="utf-8")
        stamped += n
print(f"console cache-busters: {stamped} stamps -> {NEW}")

# ---------------------------------------------------------------- 4. my HISTORY section re-titled
h = ROOT / "docs" / "HISTORY.md"
t = h.read_text(encoding="utf-8")
t = t.replace("## v0.667.0 DUNIYA MANCH — the T4 keyless-public-web family",
              "## v0.668.0 DUNIYA MANCH — the T4 keyless-public-web family (built as 0.667.0; their PREMIUM STUDIO took 0.667.0 while T4 sat built - REBASE PROTOCOL #13, both kept)", 1)
t = t.replace("(registry 607 -> 608) over the parts of the web that answer anyone",
              "(registry 607 -> 608, shipped as 0.668.0) over the parts of the web that answer anyone", 1)
t = t.replace("DUNIYA v0.667 (T4 keyless public web).", "DUNIYA v0.668 (T4 keyless public web).", 1)
h.write_text(t, encoding="utf-8")
print("HISTORY: my DUNIYA section re-titled v0.668.0")

# ---------------------------------------------------------------- 5. the residual check
res = []
for rel in ["pubspec.yaml", "server/app/main.py"]:
    body = (ROOT / rel).read_text(encoding="utf-8")
    hits = len(re.findall(rf"\b{re.escape(OLD_V)}\b", body))
    res.append(f"{rel}: {hits} '{OLD_V}' (story-chain history is expected)")
left = [f.name for f in (ROOT / "server" / "tests").glob("*.py") if OLD_BUILD in f.read_text(encoding="utf-8")]
stamps_left = len(re.findall(rf"\?v={re.escape(OLD_V)}", (ROOT / "server" / "app" / "static" / "console" / "v2.html").read_text(encoding="utf-8")))
print("residual checks:", *res, sep="\n  ")
print(f"tests with {OLD_BUILD}: {left or 'NONE'}; v2.html stale stamps: {stamps_left}")
print("RITUAL DONE ->", f"{NEW}{NEW_BUILD}")
