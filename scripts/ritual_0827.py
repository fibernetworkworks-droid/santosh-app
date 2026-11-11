#!/usr/bin/env python3
"""v0.827.0 WHITEBOOKS GST GSTIN + API SETU version ritual (built as 0.825/0.826; their TEEN AWAAZEIN took 0.825 and APP ENGINE 2
took 0.826 - REBASE PROTOCOL, all kept). 0.826.0/+825 -> 0.827.0/+826 across test pins, pubspec, console stamps, APP_VERSION story."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NEW, NEW_B, OLD, OLD_B = "0.827.0", "+826", "0.826.0", "+825"
n = 0
for f in sorted((ROOT / "server/tests").glob("*.py")):
    t = f.read_text(encoding="utf-8")
    o = t
    t = re.sub(r"(?<!v)0\.826\.0", NEW, t)
    t = re.sub(r"\+825\b", NEW_B, t)
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
ol = re.search(r'^APP_VERSION = "0\.826\.0"   # (.*)$', t, re.M)
assert ol
story = ('v0.827.0 WHITEBOOKS GST GSTIN + API SETU (built as 0.825 / 0.826; their TEEN AWAAZEIN took 0.825.0 and APP ENGINE 2 0.826.0 '
         '- REBASE PROTOCOL, all kept) - (1) the owner shared WhiteBooks own files: Hoola calls match their specs; 123 GSTN + 128 NIC IRP '
         'error codes as data (bahi/wb_errors.json) said in the system own words (wb.known_error); research note 05. (2) WhiteBooks '
         'support gave the GST sandbox its own test GSTIN 27AAGCB1286QKZL + username MH_NT4.2823: new WHITEBOOKS_SANDBOX_GST_GSTIN drives '
         'GSTIN search, filing track, the OTP login and the ledger, e-invoice / e-way bill keep the shared 27AAGCB1286Q005 (her live '
         'wb_check at 10:18 UTC: GST OTP + auth token + refresh PASS, the three GSTIN steps still on the shared GSTIN = this fix). '
         '(3) API Setu GSTN Tax Payer API (her partner account): bahi/apisetu.py - GET apisetu.gov.in/gstn/v1/taxpayers/{gstin} with '
         'X-APISETU-CLIENTID / X-APISETU-APIKEY from the VPS .env only, check digit refused before any call, every error said plainly '
         '(keys refused vs app not subscribed vs no such taxpayer); python -m app.bahi.apisetucheck + vps-ops apisetu_check (names only, '
         'how the keys look, ONE lookup, reply shape saved); 10 tests. Previous: ')
t = t.replace(ol.group(0), f'APP_VERSION = "{NEW}"   # ' + story + ol.group(1))
m.write_text(t)
print("APP_VERSION ->", NEW)
