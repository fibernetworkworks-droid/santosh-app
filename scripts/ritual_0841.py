#!/usr/bin/env python3
"""v0.799.0 DESK ROOM version ritual (built as 0.796; re-versioned on the v0.798.0 tip). 0.798.0/+797 -> 0.799.0/+798 across the test pins, pubspec,
the console stamps and the APP_VERSION story (theirs kept verbatim as Previous). One console file added (deptdesk.js)."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NEW, NEW_B, OLD, OLD_B = "0.841.0", "+840", "0.840.0", "+839"
n = 0
for f in sorted((ROOT / "server/tests").glob("*.py")):
    t = f.read_text(encoding="utf-8")
    o = t
    t = re.sub(r"(?<!v)0\.840\.0", NEW, t)
    t = re.sub(r"\+839\b", NEW_B, t)
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
ol = re.search(r'^APP_VERSION = "0\.840\.0"   # (.*)$', t, re.M)
assert ol
story = ('v0.841.0 BAHI A4 (built as 0.840; their GITHUB DO TARAF took 0.840.0 - REBASE PROTOCOL, both kept) - GSTR-3B and the payment plan (owner: "GO A4"): NEW bahi/gstr3b.py - prepares the return through GST Sahayak after bringing '
         'her A2 work in (the 2B she pulled and her accept / pending / reject become the credit this 3B counts; no 2B = credit zero, said), least-cash set-off, '
         'interest and late fee; compares the portal\'s own auto-liability (and says plainly when its layout is not recognised); save_draft (retsave) and '
         'apply_setoff (retoffset, ledger ids read from the portal\'s own summary, refused when absent) each only on her confirm bound to a plan hash; '
         'payment_plan = the cash she must pay at her bank vs her ledger (Hoola creates no challan and moves no money); EVC filing built but refused unless '
         'BAHI_FILING is on; wb.py primitives; /api/bahi/gstr3b/*; console GSTR-3B tab; 7 tests. NOT BUILT: PMT-06 challan generation, CMP-08. NOT VERIFIED '
         'on a live portal: the retsave / retoffset bodies, the portal summary layout, the EVC call. Previous: ')
t = t.replace(ol.group(0), f'APP_VERSION = "{NEW}"   # ' + story + ol.group(1))
m.write_text(t)
print("APP_VERSION ->", NEW)
