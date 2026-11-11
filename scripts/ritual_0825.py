#!/usr/bin/env python3
"""v0.819.0 WHITEBOOKS PASTE CHECK version ritual (built as 0.814). 0.818.0/+817 -> 0.819.0/+818 across the test pins, pubspec,
the console stamps and the APP_VERSION story (theirs kept verbatim as Previous)."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NEW, NEW_B, OLD, OLD_B = "0.825.0", "+824", "0.824.0", "+823"
n = 0
for f in sorted((ROOT / "server/tests").glob("*.py")):
    t = f.read_text(encoding="utf-8")
    o = t
    t = re.sub(r"(?<!v)0\.824\.0", NEW, t)
    t = re.sub(r"\+823\b", NEW_B, t)
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
ol = re.search(r'^APP_VERSION = "0\.824\.0"   # (.*)$', t, re.M)
assert ol
story = ('v0.825.0 WHITEBOOKS ERROR WORDS - the owner shared WhiteBooks own files (GST API doc, 3 Postman collections, the '
         'return-filing guide, the released-API list, the GSTN + e-invoice error lists, the e-invoice + e-way bill preparation sheets); '
         'read end to end: Hoola calls match their specs exactly, and the GST sandbox is a separate switch-on by WhiteBooks support '
         '(their sign-up step 3) - which is why GST search failed while the e-invoice + e-way bill sandbox logins PASS on her server; '
         'the 123 GSTN + 128 NIC IRP error codes are now data (bahi/wb_errors.json, provider-spec, source + checked_on + review_by) and '
         'wb.known_error says every code in the system own words (+ the e-invoice fix) instead of a bare code; wb_check adds '
         'WhiteBooks own reply when ours is generic; docs/research/accounts/05_whitebooks_files.md maps the files to phases; 1 test. '
         'Previous: ')
t = t.replace(ol.group(0), f'APP_VERSION = "{NEW}"   # ' + story + ol.group(1))
m.write_text(t)
print("APP_VERSION ->", NEW)
