#!/usr/bin/env python3
"""v0.799.0 DESK ROOM version ritual (built as 0.796; re-versioned on the v0.798.0 tip). 0.798.0/+797 -> 0.799.0/+798 across the test pins, pubspec,
the console stamps and the APP_VERSION story (theirs kept verbatim as Previous). One console file added (deptdesk.js)."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NEW, NEW_B, OLD, OLD_B = "0.843.0", "+842", "0.842.0", "+841"
n = 0
for f in sorted((ROOT / "server/tests").glob("*.py")):
    t = f.read_text(encoding="utf-8")
    o = t
    t = re.sub(r"(?<!v)0\.842\.0", NEW, t)
    t = re.sub(r"\+841\b", NEW_B, t)
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
ol = re.search(r'^APP_VERSION = "0\.842\.0"   # (.*)$', t, re.M)
assert ol
story = ('v0.843.0 BAHI A5 - e-invoice (IRN) and e-way bill (built as 0.842; their PROOF took 0.842.0 - REBASE PROTOCOL, both kept; owner: "GO A5"): NEW '
         'bahi/einv.py - connect her e-invoice portal login (password sealed, returned by no route; seller name / address kept for INV-01), build INV-01 v1.1 '
         'from a register sales document and LIST what is missing (customer address, HSN, a 16-character invoice number) instead of inventing it, generate the IRN '
         'only on her confirm bound to a plan hash with the attempt row (acc_irn) written BEFORE the call and the reply stored as it arrives, a duplicate (NIC '
         '2150) or a timeout recovered by asking the IRP for the document and adopting its IRN, the 30-day report limit (turnover Rs 10 crore and above) checked '
         'before the call, cancel only within 24 hours and never while an e-way bill is live (NIC 2174), e-way bill by IRN with the 180-day limit, e-way bill '
         'cancel, a watch list of sales still without an IRN; /api/bahi/einv/*; console e-Invoice tab; wb_check adds a read-only GSTIN-details call that proves the '
         'auth-token header; 6 tests. NOT BUILT: standalone e-way bills, Part-B / extend / consolidate, QR on the PDFs. NOT VERIFIED on a live IRP: the success '
         'reply fields, the e-way cancel path. Previous: ')
t = t.replace(ol.group(0), f'APP_VERSION = "{NEW}"   # ' + story + ol.group(1))
m.write_text(t)
print("APP_VERSION ->", NEW)
