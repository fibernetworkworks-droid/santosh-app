#!/usr/bin/env python3
"""v0.799.0 DESK ROOM version ritual (built as 0.796; re-versioned on the v0.798.0 tip). 0.798.0/+797 -> 0.799.0/+798 across the test pins, pubspec,
the console stamps and the APP_VERSION story (theirs kept verbatim as Previous). One console file added (deptdesk.js)."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NEW, NEW_B, OLD, OLD_B = "0.846.0", "+845", "0.845.0", "+844"
n = 0
for f in sorted((ROOT / "server/tests").glob("*.py")):
    t = f.read_text(encoding="utf-8")
    o = t
    t = re.sub(r"(?<!v)0\.845\.0", NEW, t)
    t = re.sub(r"\+844\b", NEW_B, t)
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
ol = re.search(r'^APP_VERSION = "0\.845\.0"   # (.*)$', t, re.M)
assert ol
story = ('v0.846.0 BAHI A7 - bank and UPI reconciliation, stored (owner: "GO A7"): NEW bahi/bank.py - a statement she gives (CSV, Excel, MT940, or a PDF whose password she '
         'types once and Hoola never keeps) becomes stored lines (acc_bank_lines; a re-import adds nothing, identical lines on one day are both kept); each narration is '
         'read for mode, reference (UPI RRN / NEFT-IMPS UTR / cheque no), payer and UPI id; matching PROPOSES (invoice number in the narration 0.97, a payer she confirmed '
         'before 0.92, payer name + amount 0.85, the only document that fits 0.70) with a reason, and links nothing until she confirms; a confirmed UPI payer is remembered '
         '(acc_bank_learn); unmatched lines are categorised (fees, UPI, ...) and the category she sets is remembered; gateway settlements she hands over explain one bank '
         'credit (gross - fees - GST); a month-end reconciliation (matched, bank-only, books-only, a balance check) is stored (acc_bank_recon); /api/bahi/bank/*; console Bank '
         'tab; 7 tests. NOT BUILT: fetching settlements from the gateway, a cheque register, any bank API. NOT VERIFIED on real statements. Previous: ')
t = t.replace(ol.group(0), f'APP_VERSION = "{NEW}"   # ' + story + ol.group(1))
m.write_text(t)
print("APP_VERSION ->", NEW)
