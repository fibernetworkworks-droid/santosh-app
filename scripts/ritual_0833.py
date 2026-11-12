#!/usr/bin/env python3
"""v0.799.0 DESK ROOM version ritual (built as 0.796; re-versioned on the v0.798.0 tip). 0.798.0/+797 -> 0.799.0/+798 across the test pins, pubspec,
the console stamps and the APP_VERSION story (theirs kept verbatim as Previous). One console file added (deptdesk.js)."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NEW, NEW_B, OLD, OLD_B = "0.833.0", "+832", "0.832.0", "+831"
n = 0
for f in sorted((ROOT / "server/tests").glob("*.py")):
    t = f.read_text(encoding="utf-8")
    o = t
    t = re.sub(r"(?<!v)0\.832\.0", NEW, t)
    t = re.sub(r"\+831\b", NEW_B, t)
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
ol = re.search(r'^APP_VERSION = "0\.832\.0"   # (.*)$', t, re.M)
assert ol
story = ('v0.833.0 BAHI A1 - connect her GSTIN + supplier checks (owner: "GO A1"; docs/ACCOUNTS_EMPLOYEE_PLAN.md): NEW bahi/connect.py - the OTP '
         'walk (start asks the GST system to send HER the OTP, verify passes it straight through to WhiteBooks and never stores / logs / returns it, '
         'refresh, disconnect that says how to cut access on the GST portal; only txn + dates kept in acc_gst_conn, never returned) and supplier_check '
         '(API Setu first, WhiteBooks public search second, filing track this FY then last, every part naming its source and what it could NOT find - '
         'no source = unknown, not fine); /api/bahi/connect[/start|/verify|/refresh|/disconnect] + /supplier-check; console Connection tab form + '
         'supplier box; wb_check rettrack now sends type R1 and tries last FY too; nothing files or pays; 6 tests. NOT VERIFIED on production '
         '(sandbox login only); rettrack still unconfirmed. Previous: ')
t = t.replace(ol.group(0), f'APP_VERSION = "{NEW}"   # ' + story + ol.group(1))
m.write_text(t)
print("APP_VERSION ->", NEW)
