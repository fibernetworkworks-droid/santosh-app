#!/usr/bin/env python3
"""v0.799.0 DESK ROOM version ritual (built as 0.796; re-versioned on the v0.798.0 tip). 0.798.0/+797 -> 0.799.0/+798 across the test pins, pubspec,
the console stamps and the APP_VERSION story (theirs kept verbatim as Previous). One console file added (deptdesk.js)."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NEW, NEW_B, OLD, OLD_B = "0.847.0", "+846", "0.846.0", "+845"
n = 0
for f in sorted((ROOT / "server/tests").glob("*.py")):
    t = f.read_text(encoding="utf-8")
    o = t
    t = re.sub(r"(?<!v)0\.846\.0", NEW, t)
    t = re.sub(r"\+845\b", NEW_B, t)
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
ol = re.search(r'^APP_VERSION = "0\.846\.0"   # (.*)$', t, re.M)
assert ol
story = ('v0.847.0 BAHI A8 - payables, receivables, TDS (owner: "GO A8"): NEW bahi/payables.py - ONE party master (GSTIN, PAN + a valid-PAN flag, Udyam + micro / small / '
         'medium, days agreed in writing, bank details sealed and shown masked, every bank-detail change kept and warned about); ageing from the register where a document '
         'is settled only by a bank line she confirmed; the MSME alarm (15 days, or the agreed days up to 45, with the pay-before-31-March warning); the 180-day Rule 37 '
         'watch; collection reminders DRAFTED with a wa.me link (a party she stopped is skipped, no payment link); the TDS worksheet from a new rules file bahi/rules/tds.json '
         '(194C 1% individual / 2% others, 194J 10% / 2%, 194H, 194I, 194A: rate, single and yearly limits counted from what she recorded, the 20% no-PAN rate, GST shown '
         'separately excluded, due the 7th and 30 April for March), a register of what she deducted (recorded only on her confirm) and deposited (challan serial), the '
         'quarter laid out as Form 140 data and a 26AS match; /api/bahi/ageing|msme|rule37|reminders|parties|tds/*; console Pay + TDS tab; 7 tests. Hoola pays, deducts and files '
         'nothing (no deductor API). NOT VERIFIED: the section 393 ITEM numbers (each row shows its old section; rates are the old sections as amended by the Finance Act '
         '2025 and agree with audit/rules.py); the interest on delayed MSME payments is not computed. Previous: ')
t = t.replace(ol.group(0), f'APP_VERSION = "{NEW}"   # ' + story + ol.group(1))
m.write_text(t)
print("APP_VERSION ->", NEW)
