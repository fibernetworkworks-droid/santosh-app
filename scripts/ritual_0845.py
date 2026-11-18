#!/usr/bin/env python3
"""v0.799.0 DESK ROOM version ritual (built as 0.796; re-versioned on the v0.798.0 tip). 0.798.0/+797 -> 0.799.0/+798 across the test pins, pubspec,
the console stamps and the APP_VERSION story (theirs kept verbatim as Previous). One console file added (deptdesk.js)."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NEW, NEW_B, OLD, OLD_B = "0.845.0", "+844", "0.844.0", "+843"
n = 0
for f in sorted((ROOT / "server/tests").glob("*.py")):
    t = f.read_text(encoding="utf-8")
    o = t
    t = re.sub(r"(?<!v)0\.844\.0", NEW, t)
    t = re.sub(r"\+843\b", NEW_B, t)
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
ol = re.search(r'^APP_VERSION = "0\.844\.0"   # (.*)$', t, re.M)
assert ol
story = ('v0.845.0 BAHI A6 - bills in, checked (built as 0.844; their G7 took 0.844.0 - REBASE PROTOCOL, both kept; owner: "GO A6"): NEW bahi/intake.py - a purchase '
         'bill (a stored file, or pasted text) is read locally (the PDF text, else the OCR the server has; no model call) into supplier GSTIN, invoice number, date, '
         'taxable, CGST / SGST / IGST / cess, total and HSN, then cross-checked: supplier GSTIN check digit and status (API Setu / WhiteBooks), the bill is addressed '
         'to HER GSTIN, taxable + tax = total, CGST = SGST, intra- vs inter-state tax, the rate is a slab in force on the date, a duplicate of a bill already held, '
         'a date that makes sense, a hard-to-read photo; the result is a DRAFT (acc_intake) with a confidence and reasons and enters the register (source intake) '
         'only on her tap - errors must be fixed or accepted by her in writing; /api/bahi/bills*; console Bills tab; 6 tests. NOT WIRED: the WhatsApp number, the '
         'mailbox bucket and PC folders handing a file to intake_file; no vision call for a weak read. Previous: ')
t = t.replace(ol.group(0), f'APP_VERSION = "{NEW}"   # ' + story + ol.group(1))
m.write_text(t)
print("APP_VERSION ->", NEW)
