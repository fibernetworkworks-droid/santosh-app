#!/usr/bin/env python3
"""v0.799.0 DESK ROOM version ritual (built as 0.796; re-versioned on the v0.798.0 tip). 0.798.0/+797 -> 0.799.0/+798 across the test pins, pubspec,
the console stamps and the APP_VERSION story (theirs kept verbatim as Previous). One console file added (deptdesk.js)."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NEW, NEW_B, OLD, OLD_B = "0.832.0", "+831", "0.831.0", "+830"
n = 0
for f in sorted((ROOT / "server/tests").glob("*.py")):
    t = f.read_text(encoding="utf-8")
    o = t
    t = re.sub(r"(?<!v)0\.831\.0", NEW, t)
    t = re.sub(r"\+830\b", NEW_B, t)
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
ol = re.search(r'^APP_VERSION = "0\.831\.0"   # (.*)$', t, re.M)
assert ol
story = ('v0.832.0 API SETU REPLY SHAPE - her live apisetu_check (v0.830 via her relay) got HTTP 200 with the keys accepted but no taxpayer '
         'record in the spec shape: bahi/apisetu.py now reads a record bare, wrapped (data / result / response / a list) or in GSTN short names '
         '(lgnm / sts / rgdt...), and a 200 with no record raises no_record naming the reply\'s FIELD NAMES only (never values); apisetucheck '
         'treats no_record as keys accepted and tells her to set APISETU_TEST_GSTIN to a real registered GSTIN; 2 tests. NOT VERIFIED: the real '
         'reply shape. Previous: ')
t = t.replace(ol.group(0), f'APP_VERSION = "{NEW}"   # ' + story + ol.group(1))
m.write_text(t)
print("APP_VERSION ->", NEW)
