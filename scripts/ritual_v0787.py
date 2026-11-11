#!/usr/bin/env python3
"""v0.787.0 HOOLA CODE ENGINE version ritual (built as 0.784 on their v0.782 tip; their SAWAAL CARD took 0.784.0, the SAVE THE
STATE / HOOLA AI APPS 0.785.0 and HOOLA INTERACTIVE PREMIUM PASS 0.786.0 while it sat built - REBASE PROTOCOL, all kept).
0.786.0/+785 -> 0.787.0/+786 across the test pins, pubspec, the console stamps, the APP_VERSION story (theirs kept verbatim as
Previous). No console file added (code.js was already stamped), so the stamp COUNT stays. The new suite is renamed to v0787."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NEW, NEW_B, OLD, OLD_B = "0.787.0", "+786", "0.786.0", "+785"
src, dst = ROOT / "server/tests/test_v0784_hoola_code_engine.py", ROOT / "server/tests/test_v0787_hoola_code_engine.py"
if src.exists():
    dst.write_text(src.read_text().replace('"""v0.784 HOOLA CODE ENGINE', '"""v0.787 HOOLA CODE ENGINE (built as 0.784)'))
    src.unlink()
n = 0
for f in sorted((ROOT / "server/tests").glob("*.py")):
    t = f.read_text(encoding="utf-8")
    o = t
    t = re.sub(r"(?<!v)0\.786\.0", NEW, t)
    t = re.sub(r"\+785\b", NEW_B, t)
    if t != o:
        f.write_text(t, encoding="utf-8")
        n += 1
print("tests swept:", n)
p = ROOT / "pubspec.yaml"
t, k = re.subn(r"version: 0\.\d+\.\d+\+\d+", f"version: {NEW}{NEW_B}", p.read_text(), count=1)
p.write_text(t)
print("pubspec:", k)
for f in sorted((ROOT / "server/app/static/console").glob("*.html")):
    t = f.read_text()
    if f"v={OLD}" in t:
        print("stamps:", f.name, t.count(f"v={OLD}"))
        f.write_text(t.replace(f"v={OLD}", f"v={NEW}"))
m = ROOT / "server/app/main.py"
t = m.read_text()
ol = re.search(r'^APP_VERSION = "0\.786\.0"   # (.*)$', t, re.M)
assert ol
story = ('v0.787.0 HOOLA CODE ENGINE (built as 0.784; their SAWAAL CARD took 0.784.0, 0.785.0 and HOOLA INTERACTIVE PREMIUM PASS '
         '0.786.0 - REBASE PROTOCOL, all kept; owner: "NOW CHECK IS HOOLA CODE BACKEND IS SAME AS CLAUDE CODE" -> "GO STEP 1 AND 2 --- '
         '2 SESSIONS, USE CLAUDE"): step 1 devsahayak/brain.py = every Hoola Code call Claude\'s own (past SAB GLM / one-model, '
         'dev_claude), adaptive thinking, prompt caching, old tool output trimmed, a failed GitHub search said; step 2 '
         'devsahayak/engine.py = a real working copy per session (local git, secrets hidden), Claude Code\'s tools (read / write / '
         'edit / multi_edit / glob / grep / ls / bash in the locked box / todo_write / show_diff / done), compaction, a conversation '
         'that continues (follow-ups, CI fixes, explained sessions), a checkpoint per round + rewind, 2 sessions at once '
         '(dev_ws_live), the PR / CI / review / safety pipeline unchanged; page: commands, to-do, Working copy card, Browse files, '
         'Go back. Previous: ')
t = t.replace(ol.group(0), f'APP_VERSION = "{NEW}"   # ' + story + ol.group(1))
m.write_text(t)
print("APP_VERSION ->", NEW)
