#!/usr/bin/env python3
"""v0.819.0 WHITEBOOKS PASTE CHECK version ritual (built as 0.814). 0.818.0/+817 -> 0.819.0/+818 across the test pins, pubspec,
the console stamps and the APP_VERSION story (theirs kept verbatim as Previous)."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NEW, NEW_B, OLD, OLD_B = "0.826.0", "+825", "0.825.0", "+824"
n = 0
for f in sorted((ROOT / "server/tests").glob("*.py")):
    t = f.read_text(encoding="utf-8")
    o = t
    t = re.sub(r"(?<!v)0\.825\.0", NEW, t)
    t = re.sub(r"\+824\b", NEW_B, t)
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
ol = re.search(r'^APP_VERSION = "0\.825\.0"   # (.*)$', t, re.M)
assert ol
story = ('v0.826.0 WHITEBOOKS ERROR WORDS + GST TEST GSTIN (built as 0.825; their TEEN AWAAZEIN took 0.825.0 - REBASE PROTOCOL, both kept) - (1) the owner shared WhiteBooks own files, read end to end: Hoola calls match their specs; 123 GSTN + 128 NIC IRP error codes as data (bahi/wb_errors.json) said in the system own words by wb.known_error; wb_check shows WhiteBooks own reply when ours is generic; research note 05. (2) WhiteBooks support answered: the GST sandbox (public taxpayer search) is tested with GSTIN '
         '27AAGCB1286QKZL and username MH_NT4.2823 - a different test GSTIN from the e-invoice / e-way bill one in their shared PDF '
         '(27AAGCB1286Q005); new WHITEBOOKS_SANDBOX_GST_GSTIN (empty = the shared one, as before): wb_check runs GSTIN search, filing '
         'track, the OTP login (state code from it) and the ledger with the GST GSTIN, e-invoice + e-way bill keep the shared one; the '
         'paste check and vps-ops wb_check list the new line; 1 test. Previous: ')
t = t.replace(ol.group(0), f'APP_VERSION = "{NEW}"   # ' + story + ol.group(1))
m.write_text(t)
print("APP_VERSION ->", NEW)
