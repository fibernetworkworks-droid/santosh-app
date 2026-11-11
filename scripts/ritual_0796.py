#!/usr/bin/env python3
"""v0.796.0 DESK ROOM version ritual (built on the v0.795.0 tip). 0.795.0/+794 -> 0.796.0/+795 across the test pins, pubspec,
the console stamps and the APP_VERSION story (theirs kept verbatim as Previous). One console file added (deptdesk.js)."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NEW, NEW_B, OLD, OLD_B = "0.796.0", "+795", "0.795.0", "+794"
n = 0
for f in sorted((ROOT / "server/tests").glob("*.py")):
    t = f.read_text(encoding="utf-8")
    o = t
    t = re.sub(r"(?<!v)0\.795\.0", NEW, t)
    t = re.sub(r"\+794\b", NEW_B, t)
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
ol = re.search(r'^APP_VERSION = "0\.795\.0"   # (.*)$', t, re.M)
assert ol
story = ('v0.796.0 DESK ROOM (owner: "LOT OF EMPLOYEE HAS BEEN DEVELOPED IN APP BUT IT IS NOT AVAILABLE IN WEB CONSOLE CHECK THIS FIRST '
         'THEN CATEGORY WISE DEVELOP AND DESIGN IT IN CONSOLE"): the audit found 31 live AI employees whose Open desk pointed at a console '
         'view that did not exist - Finance & Banking 3, Retail & E-commerce 3, Health Insurance 3, Kaan, Construction & Real Estate 21 '
         '(the phone sends them to the SEO desk). Four department desks on the console (static/console/deptdesk.js, view deptdesk, '
         '`ddk-` styles): a hero with its own line drawing, lanes of employees (Construction in five: site & store, money & contracts, '
         'plan & approvals, design & survey, studio & learning), Work / Records tabs, one form per action read from the employee\'s OWN '
         'tool schema and full description (employee/deskroom.py: fields, choices, hints, list-of-rows tables with Paste from Excel, '
         'what the action gives back; 409 of 423 actions read exactly, the rest say so), runs through the same dispatch as chat as the '
         'owner (GET /api/deskroom, /api/deskroom/{dept}, POST /api/deskroom/{key}/run; hired only, paused refused, never another '
         'employee\'s tool, a full account number cut to its last four), results as tiles / tables / letters; Kaan opens Hoola Flow; '
         '8 tests incl. a browser walk. Previous: ')
t = t.replace(ol.group(0), f'APP_VERSION = "{NEW}"   # ' + story + ol.group(1))
m.write_text(t)
print("APP_VERSION ->", NEW)
