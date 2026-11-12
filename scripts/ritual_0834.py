#!/usr/bin/env python3
"""v0.799.0 DESK ROOM version ritual (built as 0.796; re-versioned on the v0.798.0 tip). 0.798.0/+797 -> 0.799.0/+798 across the test pins, pubspec,
the console stamps and the APP_VERSION story (theirs kept verbatim as Previous). One console file added (deptdesk.js)."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NEW, NEW_B, OLD, OLD_B = "0.834.0", "+833", "0.833.0", "+832"
n = 0
for f in sorted((ROOT / "server/tests").glob("*.py")):
    t = f.read_text(encoding="utf-8")
    o = t
    t = re.sub(r"(?<!v)0\.833\.0", NEW, t)
    t = re.sub(r"\+832\b", NEW_B, t)
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
ol = re.search(r'^APP_VERSION = "0\.833\.0"   # (.*)$', t, re.M)
assert ol
story = ('v0.834.0 BAHI A2 - the monthly credit (ITC) loop (owner: "GO A2"; docs/ACCOUNTS_EMPLOYEE_PLAN.md): NEW bahi/itc.py - pull her GSTR-2B through '
         'the A1 connection (acc_2b, her earlier decisions kept on a re-pull), match it with the purchase register (exact, tax within Rs 10, same tax '
         'under another number, duplicate, reverse charge, already-ineligible) and propose accept / pending / reject WITH A REASON and a confidence '
         '(a non-duplicate is never proposed for reject), list purchases missing from 2B with a drafted supplier nudge (wa.me link - Hoola sends '
         'nothing); her decisions are saved per row and reach the portal IMS ONLY on her confirm bound to a plan hash of the exact list, then status '
         'and a 2B recompute are asked; every step an acc_events row; /api/bahi/itc/*; console Credit (ITC) tab; wb_check pins the 2B + IMS read '
         'shapes (the IMS write is never in a check); 5 tests. NOT VERIFIED on a live portal: the IMS body is built to the OpenAPI spec, the 2B '
         'paging and the status words are unseen. Previous: ')
t = t.replace(ol.group(0), f'APP_VERSION = "{NEW}"   # ' + story + ol.group(1))
m.write_text(t)
print("APP_VERSION ->", NEW)
