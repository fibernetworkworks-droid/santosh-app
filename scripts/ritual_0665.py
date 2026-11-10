#!/usr/bin/env python3
"""v0.665.0 KAAN W5 re-version ritual - the REBASE PROTOCOL's second half.

W5 built as 0.663.0; their ASLI SAMAY took 0.664.0 while W5 sat built and pushed -
REBASE PROTOCOL, rebuilt fresh on their 909e84de4 tip, all kept, their story chain
verbatim. This sweep re-applies the version layer coherently: 0.663.0/0.664.0 ->
0.665.0 (+669/+670 -> +671) across ALL test files, pubspec, and the APP_VERSION
story (their 0.664.0 ASLI SAMAY story spliced into the Previous chain untouched).
Registry stays 606 - actions, not tools; the kaan enum stays 18.
"""
import re
from pathlib import Path

ROOT = Path("/home/z/my-project/santosh-app")
NEW, NEW_BUILD = "0.665.0", "+671"
OLD_PAIRS = [("0.663.0", NEW), ("0.664.0", NEW), ("+669", NEW_BUILD), ("+670", NEW_BUILD)]

# ---------------------------------------------------------------- 1. the test-file sweep
changed = []
for f in sorted((ROOT / "server" / "tests").glob("*.py")):
    text = f.read_text(encoding="utf-8")
    orig = text
    for old, new in OLD_PAIRS:
        text = text.replace(old, new)
    if text != orig:
        f.write_text(text, encoding="utf-8")
        changed.append(f.name)
print(f"tests swept: {len(changed)} files")

# ---------------------------------------------------------------- 2. pubspec
pub = ROOT / "pubspec.yaml"
text = pub.read_text(encoding="utf-8")
text = re.sub(r"version: 0\.66[34]\.0\+\d{3}", f"version: {NEW}{NEW_BUILD}", text, count=1)
pub.write_text(text, encoding="utf-8")
print("pubspec ->", f"{NEW}{NEW_BUILD}")

# ---------------------------------------------------------------- 3. the APP_VERSION story splice
main = ROOT / "server" / "app" / "main.py"
lines = main.read_text(encoding="utf-8").split("\n")
line36 = lines[35]
assert line36.startswith('APP_VERSION = "0.663.0"'), "line 36 is not my W5 story"

# my story head: everything before my " Previous: v0.662.0" chain
my_marker = " Previous: v0.662.0"
idx = line36.index(my_marker)
my_head = line36[:idx]
my_chain = line36[idx + 1:]              # "Previous: v0.662.0 KAAM SAAF ..."

# their story: pulled from their commit (already on this tree's history)
import subprocess
their36 = subprocess.run(
    ["git", "show", "909e84de4:server/app/main.py"], capture_output=True, text=True, cwd=ROOT
).stdout.split("\n")[35]
assert "ASLI SAMAY" in their36, "their story not found on their tip"
t_idx = their36.index(" Previous: ")
their_story = their36[their36[their36.index("# "):].index("# ") + their36.index("# "):t_idx].strip()
# (their_story = the "# v0.664.0 ASLI SAMAY ... (owner: ...)" segment, chain removed)

# my head re-titled: the built-as preamble + the coherent re-version note
new_head = my_head.replace(
    'APP_VERSION = "0.663.0"   # v0.663.0 KAAN W5 - BOLI KE TEEN DARWAZE (owner:',
    'APP_VERSION = "0.665.0"   # v0.665.0 KAAN W5 - BOLI KE TEEN DARWAZE (built as 0.663.0; their ASLI SAMAY took 0.664.0 '
    'while W5 sat built and pushed - REBASE PROTOCOL, rebuilt fresh on their 909e84de4 tip, all kept, their story chain '
    'verbatim, the version layer re-applied coherently 0.663.0/+669 -> 0.665.0/+671, ritual_0665.py) (owner:',
)
# the ritual paragraph grows the re-version record
new_head = new_head.replace(
    "the webext permission-set pin healed (versions untouched)",
    "the webext permission-set pin healed (versions untouched); the rebase ritual re-swept their 0.664.0 layer "
    "to 0.665.0 (+671) across the suites, ZERO residual",
)
lines[35] = f"{new_head} Previous: {their_story} {my_chain}"
main.write_text("\n".join(lines), encoding="utf-8")
print("APP_VERSION story spliced: W5 0.665.0 + their ASLI SAMAY story verbatim in the Previous chain")

# ---------------------------------------------------------------- 4. the mirrors
h = ROOT / "docs" / "HISTORY.md"
t = h.read_text(encoding="utf-8")
t = t.replace("## v0.663.0 KAAN W5 — BOLI KE TEEN DARWAZE (7 Nov 2026)",
              "## v0.665.0 KAAN W5 — BOLI KE TEEN DARWAZE (7 Nov 2026, built as 0.663.0; their ASLI SAMAY took 0.664.0 - REBASE PROTOCOL, rebuilt on their tip, all kept)")
h.write_text(t, encoding="utf-8")

w = ROOT / "docs" / "WORKLOG.md"
t = w.read_text(encoding="utf-8")
t = t.replace("Task ID: v0.663.0 KAAN W5 BOLI KE TEEN DARWAZE",
              "Task ID: v0.665.0 KAAN W5 BOLI KE TEEN DARWAZE (built as 0.663.0; their ASLI SAMAY took 0.664.0 - REBASE PROTOCOL, all kept)")
w.write_text(t, encoding="utf-8")

c = ROOT / "CLAUDE.md"
t = c.read_text(encoding="utf-8")
t = t.replace("- v0.663 KAAN W5 BOLI KE TEEN DARWAZE:", "- v0.665 KAAN W5 BOLI KE TEEN DARWAZE (built as 0.663.0, rebased on their 0.664.0):")
c.write_text(t, encoding="utf-8")
print("mirrors re-titled")

# ---------------------------------------------------------------- 5. residual check
residual = []
for f in sorted((ROOT / "server" / "tests").glob("*.py")):
    text = f.read_text(encoding="utf-8")
    if "0.663.0" in text or "0.664.0" in text:
        residual.append(f.name)
print("residual 0.663.0/0.664.0 in tests:", residual or "ZERO")
