#!/usr/bin/env python3
"""v0.781.0 CONNECTORS PAGE version ritual (built as 0.776 on their v0.775 tip; their HOOLA CODE PHASE 2 took 0.776.0,
CHAT JAISA 0.777.0, HOOLA FLOW 0.778.0, HOOLA CODE PHASE 3 0.779.0 and HOOLA FLOW REDRAWN 0.780.0 while it sat built - REBASE
PROTOCOL twice, rebased on their fd95eb905 tip, all kept).

0.780.0/+779 -> 0.781.0/+780 across the test pins (the v-prefixed own stamps of other suites stay), pubspec, the console
cache-buster stamps (the v0179 law: stamps == APP_VERSION), the APP_VERSION story (their CHAT JAISA story kept verbatim
as Previous), the console stamp COUNT 27 -> 28 (connectors.js joined v2.html), and the new suite renamed to v0778.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NEW, NEW_B, OLD, OLD_B = "0.781.0", "+780", "0.780.0", "+779"

# 1. the new suite: renamed + its own pins
src = ROOT / "server/tests/test_v0776_connectors_page.py"
dst = ROOT / "server/tests/test_v0781_connectors_page.py"
if src.exists():
    t = src.read_text().replace('"0.776.0"', f'"{NEW}"').replace("0.776.0+775", NEW + NEW_B).replace('"""v0.776 CONNECTORS', '"""v0.781 CONNECTORS')
    dst.write_text(t)
    src.unlink()

# 2. the test-file sweep
n_files = 0
for f in sorted((ROOT / "server/tests").glob("*.py")):
    t = f.read_text(encoding="utf-8")
    o = t
    t = re.sub(r"(?<!v)0\.780\.0", NEW, t)
    t = re.sub(r"\+779\b", NEW_B, t)
    if f.name == "test_v0475_console_frames.py":
        t = t.replace("    assert s.count(f'v={APP_VERSION}') == 27, f\"expected 27 stamps",
                      "    # v0.781: 27 -> 28. connectors.js joined the console page (the Connectors page).\n"
                      "    assert s.count(f'v={APP_VERSION}') == 28, f\"expected 28 stamps")
    if t != o:
        f.write_text(t, encoding="utf-8")
        n_files += 1
print("tests swept:", n_files)

# 3. pubspec
p = ROOT / "pubspec.yaml"
t, n = re.subn(r"version: 0\.\d+\.\d+\+\d+", f"version: {NEW}{NEW_B}", p.read_text(), count=1)
p.write_text(t)
print("pubspec:", n)

# 4. console stamps
for f in sorted((ROOT / "server/app/static/console").glob("*.html")):
    t = f.read_text()
    if f"v={OLD}" in t:
        f.write_text(t.replace(f"v={OLD}", f"v={NEW}"))
        print("stamps:", f.name, t.count(f"v={OLD}"))

# 5. the APP_VERSION story
m = ROOT / "server/app/main.py"
t = m.read_text()
old_line = re.search(r'^APP_VERSION = "0\.780\.0"   # (.*)$', t, re.M)
assert old_line
story = ('v0.781.0 CONNECTORS PAGE (built as 0.776; their HOOLA CODE PHASE 2 took 0.776.0, CHAT JAISA 0.777.0, HOOLA FLOW 0.778.0, '
         'HOOLA CODE PHASE 3 0.779.0 and HOOLA FLOW REDRAWN 0.780.0 - REBASE PROTOCOL twice, all kept; owner: "LETS WORK ON CONNECTOR IN WEB CONSOLE --- CURRENTLY IT IS ONLY AT APP SIDE" -> "GO BUILD '
         'FULL CONNECTORS PAGE -- MAKE IT MORE PREMIUM, PROFESSIONAL AND ADVANCE AND A SHORT 1 LINER BELOW EVERY CONNECTOR -- AS '
         'WE USE COMPOSIO FOR THIS"): the phone-only Connect tab as a console page (sidebar row Connectors, connectors.js): Apps '
         '(Composio ~1,600: search, categories, Connect in a sign-in window / Add key / Remove, a drawer with try lines), '
         'Connected, MCP servers (68 official, her own servers with tools on / off / ask first, change key, add by address, the '
         'directory), Built in (plugins + linked accounts), Public APIs (keys), Limits & safety; every connector carries a '
         'one-line `line` from bazar/oneline.py; the two sign-in callbacks share bazar/donepage.py - a console sign-in tells '
         'the console tab (BroadcastChannel + localStorage) and closes itself, the phone keeps its santosh:// deep link (before, '
         'a web sign-in ended on a dead santosh:// page). Previous: ')
t = t.replace(old_line.group(0), f'APP_VERSION = "{NEW}"   # ' + story + old_line.group(1))
m.write_text(t)
print("APP_VERSION ->", NEW)
